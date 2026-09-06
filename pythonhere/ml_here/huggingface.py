"""
A small cross-platform Hugging Face Hub downloader designed for PythonHere.

Uses requests to download public, private, or gated files with persistent resume,
progress callbacks, retries, integrity checks, and atomic completion. This module
implements only the Hub features needed for model downloads; it is not a general
replacement for huggingface_hub.

Typical use:

    from pythonhere.ml_here import download_hf_model

    path = download_hf_model(
        "litert-community/some-model",
        "model.tflite",
        token=oauth_access_token,
        progress=lambda p: print(p.percent, p.speed_mbps),
    )

For a public model, omit `token`.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

from .storage import model_path

__all__ = [
    "HFClient",
    "DownloadProgress",
    "RemoteFile",
    "HFError",
    "HFAuthError",
    "HFGatedError",
    "HFNotFoundError",
    "HFRateLimitError",
    "HFIntegrityError",
    "HFCancelled",
    "download_hf_model",
]


class HFError(RuntimeError):
    """Base error for Hugging Face Hub operations."""


class HFAuthError(HFError):
    """Authentication is missing, invalid, or insufficient."""


class HFGatedError(HFAuthError):
    """The model is gated and this user does not currently have access."""


class HFNotFoundError(HFError):
    """Repository, revision, or file was not found."""


class HFRateLimitError(HFError):
    """Hugging Face rejected the request because of rate limiting."""


class HFIntegrityError(HFError):
    """Downloaded data did not match expected size/hash."""


class HFCancelled(HFError):
    """Download was cancelled by the caller."""


@dataclass(frozen=True)
class RemoteFile:
    """Remote identity and metadata used to validate a download."""

    repo_id: str
    filename: str
    revision: str
    size: int | None
    etag: str | None
    commit: str | None
    url: str


@dataclass(frozen=True)
class DownloadProgress:
    """Byte counts and timing for a download progress notification."""

    repo_id: str
    filename: str
    destination: str
    downloaded: int
    total: int | None
    elapsed: float
    speed_bps: float

    @property
    def fraction(self) -> float | None:
        if not self.total:
            return None
        return min(1.0, self.downloaded / self.total)

    @property
    def percent(self) -> float | None:
        value = self.fraction
        return None if value is None else value * 100.0

    @property
    def speed_mbps(self) -> float:
        return self.speed_bps / (1024 * 1024)

    @property
    def remaining(self) -> int | None:
        if self.total is None:
            return None
        return max(0, self.total - self.downloaded)

    @property
    def eta(self) -> float | None:
        remaining = self.remaining
        if remaining is None or self.speed_bps <= 0:
            return None
        return remaining / self.speed_bps


@dataclass
class _PartialMeta:
    repo_id: str
    filename: str
    revision: str
    etag: str | None
    commit: str | None
    expected_size: int | None


@dataclass
class _ProgressReporter:
    remote: RemoteFile
    destination: Path
    callback: Callable[[DownloadProgress], None] | None
    interval: float
    started: float = field(init=False, default=0.0)
    initial_size: int = field(init=False, default=0)
    last_time: float = field(init=False, default=0.0)
    last_size: int = field(init=False, default=0)

    def start(self, size: int) -> None:
        self.started = self.last_time = time.monotonic()
        self.initial_size = self.last_size = size

    def report(self, current: int) -> None:
        now = time.monotonic()
        if self.callback and (
            now - self.last_time >= self.interval
            or (self.remote.size is not None and current >= self.remote.size)
        ):
            self.callback(
                DownloadProgress(
                    repo_id=self.remote.repo_id,
                    filename=self.remote.filename,
                    destination=str(self.destination),
                    downloaded=current,
                    total=self.remote.size,
                    elapsed=now - self.started,
                    speed_bps=(current - self.last_size)
                    / max(now - self.last_time, 1e-9),
                )
            )
            self.last_time = now
            self.last_size = current

    def finish(self) -> None:
        if self.callback:
            end = time.monotonic()
            size = self.destination.stat().st_size
            self.callback(
                DownloadProgress(
                    repo_id=self.remote.repo_id,
                    filename=self.remote.filename,
                    destination=str(self.destination),
                    downloaded=size,
                    total=self.remote.size or size,
                    elapsed=end - self.started,
                    speed_bps=(size - self.initial_size)
                    / max(end - self.started, 1e-9),
                )
            )


def _raise_download_error(response: requests.Response, filename: str) -> None:
    if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
        raise HFRateLimitError(
            f"Hugging Face rate limit exceeded while downloading {filename!r}."
        )
    raise HFError(f"HTTP {response.status_code} while downloading {filename!r}.")


_BYTES_PER_KIB = 1024
_SECONDS_PER_MINUTE = 60
_MINUTES_PER_HOUR = 60

_RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}
_SAFE_ETAG = re.compile(r'^(?:W/)?"?(.*?)"?$')


def _clean_etag(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    m = _SAFE_ETAG.match(value)
    return m.group(1) if m else value.strip('"')


def _int_header(
    headers: requests.structures.CaseInsensitiveDict, name: str
) -> int | None:
    value = headers.get(name)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _remote_size(response: requests.Response) -> int | None:
    # HF exposes the actual object size through X-Linked-Size for LFS-backed
    # files. On a final ranged/CDN response, Content-Range is the strongest
    # source. Fall back to ordinary Content-Length.
    linked = _int_header(response.headers, "X-Linked-Size")
    if linked is not None:
        return linked

    content_range = response.headers.get("Content-Range")
    if content_range and "/" in content_range:
        tail = content_range.rsplit("/", 1)[-1]
        if tail != "*":
            try:
                return int(tail)
            except ValueError:
                pass

    # Only trust Content-Length when the body is not content-encoded.
    encoding = response.headers.get("Content-Encoding", "identity").lower()
    if encoding == "identity":
        return _int_header(response.headers, "Content-Length")
    return None


def _retry_after(response: requests.Response) -> float | None:
    value = response.headers.get("Retry-After")
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


def _atomic_json_write(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


class HFClient:
    """
    Lightweight Hugging Face Hub download client.

    Parameters
    ----------
    token:
        Hugging Face user token or OAuth access token. Use None for public files.
    endpoint:
        Hub base URL. Mainly useful for testing or custom Hub-compatible hosts.
    user_agent:
        Sent on all requests.
    timeout:
        `(connect_timeout, read_timeout)` passed to requests.
        The read timeout is per socket read, not a total download timeout.
    chunk_size:
        Streaming chunk size.
    max_retries:
        Retries after transient network/server failures.
    backoff:
        Base exponential retry delay.
    """

    # Public connection options remain individually configurable.
    def __init__(  # noqa: PLR0913
        self,
        token: str | None = None,
        *,
        endpoint: str = "https://huggingface.co",
        user_agent: str = "pythonhere-hf-downloader/1.0",
        timeout: tuple[float, float] = (15.0, 60.0),
        chunk_size: int = 1024 * 1024,
        max_retries: int = 5,
        backoff: float = 1.0,
        session: requests.Session | None = None,
    ):
        # pylint: disable=too-many-arguments
        self.token = token
        self.endpoint = endpoint.rstrip("/")
        self.user_agent = user_agent
        self.timeout = timeout
        self.chunk_size = chunk_size
        self.max_retries = max_retries
        self.backoff = backoff
        self.session = session or requests.Session()

    def resolve_url(self, repo_id: str, filename: str, revision: str = "main") -> str:
        repo = "/".join(quote(part, safe="") for part in repo_id.split("/"))
        rev = quote(revision, safe="")
        file_path = "/".join(quote(part, safe="") for part in filename.split("/"))
        return f"{self.endpoint}/{repo}/resolve/{rev}/{file_path}"

    def raw_url(self, repo_id: str, filename: str, revision: str = "main") -> str:
        repo = "/".join(quote(part, safe="") for part in repo_id.split("/"))
        rev = quote(revision, safe="")
        file_path = "/".join(quote(part, safe="") for part in filename.split("/"))
        return f"{self.endpoint}/{repo}/raw/{rev}/{file_path}"

    def model_url(self, repo_id: str) -> str:
        return f"{self.endpoint}/{repo_id}"

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        # identity matters for reliable byte ranges / sizes.
        headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "identity",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if extra:
            headers.update(extra)
        return headers

    def model_info(
        self, repo_id: str, *, revision: str | None = None
    ) -> dict[str, Any]:
        """
        Return raw model metadata from the Hub REST API.

        The response includes useful fields such as `sha`, `gated`, and `siblings`.
        """
        repo = "/".join(quote(part, safe="") for part in repo_id.split("/"))
        if revision:
            rev = quote(revision, safe="")
            url = f"{self.endpoint}/api/models/{repo}/revision/{rev}"
        else:
            url = f"{self.endpoint}/api/models/{repo}"

        response = self._request_with_retry("GET", url, headers=self._headers())
        self._raise_hf_error(response, repo_id=repo_id)
        return response.json()

    def list_files(self, repo_id: str, *, revision: str | None = None) -> list[str]:
        info = self.model_info(repo_id, revision=revision)
        return [
            item["rfilename"]
            for item in info.get("siblings", [])
            if isinstance(item, dict) and item.get("rfilename")
        ]

    def file_info(
        self,
        repo_id: str,
        filename: str,
        *,
        revision: str = "main",
    ) -> RemoteFile:
        """
        Resolve a Hub file and return size/ETag/commit metadata without
        downloading the body.
        """
        url = self.resolve_url(repo_id, filename, revision)

        response = self._request_with_retry(
            "HEAD",
            url,
            headers=self._headers(),
            allow_redirects=True,
        )
        self._raise_hf_error(
            response,
            repo_id=repo_id,
            filename=filename,
        )

        etag = _clean_etag(
            response.headers.get("X-Linked-Etag") or response.headers.get("ETag")
        )
        commit = response.headers.get("X-Repo-Commit")
        size = _remote_size(response)

        return RemoteFile(
            repo_id=repo_id,
            filename=filename,
            revision=revision,
            size=size,
            etag=etag,
            commit=commit,
            # Intentionally expose the stable HF resolve URL, not an expiring
            # signed CDN/Xet redirect target.
            url=url,
        )

    def git_lfs_info(
        self,
        repo_id: str,
        filename: str,
        *,
        revision: str = "main",
    ) -> dict[str, Any] | None:
        """Return SHA-256 and size when the repository stores a Git LFS pointer."""

        response = self._request_with_retry(
            "GET",
            self.raw_url(repo_id, filename, revision),
            headers=self._headers({"Range": "bytes=0-1024"}),
            stream=True,
        )
        try:
            self._raise_hf_error(response, repo_id=repo_id, filename=filename)
            data = response.raw.read(1025)
        finally:
            response.close()

        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return None
        match = re.fullmatch(
            r"version https://git-lfs\.github\.com/spec/v1\r?\n"
            r"oid sha256:([0-9a-fA-F]{64})\r?\n"
            r"size ([0-9]+)\r?\n?",
            text,
        )
        if match:
            return {"sha256": match.group(1).lower(), "size": int(match.group(2))}
        if text.startswith("version https://git-lfs.github.com/spec/v1"):
            raise HFIntegrityError(f"Malformed Git LFS pointer for {filename}")
        return None

    # Preserve the public download keyword options.
    def download(  # noqa: PLR0913
        self,
        repo_id: str,
        filename: str,
        destination: str | os.PathLike[str],
        *,
        revision: str = "main",
        resume: bool = True,
        overwrite: bool = False,
        progress: Callable[[DownloadProgress], None] | None = None,
        cancelled: Callable[[], bool] | None = None,
        expected_sha256: str | None = None,
        progress_interval: float = 0.15,
    ) -> Path:
        """
        Download one file from a Hugging Face model repository.

        The final destination is written atomically:
            destination.part
            destination.part.json
            -> destination

        Existing partial downloads are resumed when their remote metadata still
        matches. If the revision/file changed, the stale partial is discarded.

        Parameters
        ----------
        progress:
            Callback receiving DownloadProgress. It runs on the thread calling
            `download`; for Kivy, marshal UI changes onto the UI thread.
        cancelled:
            Callback returning True when cancellation is requested. The .part
            file is preserved, so calling download() later resumes it.
        expected_sha256:
            Optional explicit SHA-256 integrity check. Usually unnecessary for
            ordinary HF use, but useful when your app ships a trusted catalog.
        """
        # Public options account for eleven of the seventeen local names.
        # pylint: disable=too-many-arguments,too-many-locals
        dest = Path(destination)
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")
        meta_path = dest.with_name(dest.name + ".part.json")

        remote = self.file_info(repo_id, filename, revision=revision)

        if dest.exists() and not overwrite:
            self._check_existing(dest, remote, expected_sha256)
            return dest

        # Files above regular HF HTTP's supported range require Xet.
        if remote.size is not None and remote.size > 50 * 1024**3:
            raise HFError(
                f"{filename!r} is larger than 50 GiB. Hugging Face does not "
                "serve files of this size through its regular HTTP download "
                "path; an Xet-capable client is required."
            )

        expected_meta = self._prepare_partial(part, meta_path, remote, resume)

        # If a previous invocation finished the bytes but died before rename,
        # finish locally without a network GET.
        if remote.size is not None and part.stat().st_size == remote.size:
            self._verify_and_commit(
                part,
                dest,
                meta_path,
                expected_size=remote.size,
                expected_sha256=expected_sha256,
            )
            return dest

        reporter = _ProgressReporter(remote, dest, progress, progress_interval)
        reporter.start(part.stat().st_size)
        self._download_with_retry(
            part, meta_path, expected_meta, reporter, cancelled=cancelled, resume=resume
        )

        self._verify_and_commit(
            part,
            dest,
            meta_path,
            expected_size=remote.size,
            expected_sha256=expected_sha256,
        )

        reporter.finish()

        return dest

    @staticmethod
    def _check_existing(dest: Path, remote: RemoteFile, expected_sha256: str | None):
        actual_size = dest.stat().st_size
        if remote.size is not None and actual_size != remote.size:
            raise HFIntegrityError(
                f"Existing {dest.name} has {actual_size} bytes; expected "
                f"{remote.size}. The file was left unchanged."
            )
        if expected_sha256 is not None:
            actual_sha256 = HFClient._sha256(dest)
            if actual_sha256.lower() != expected_sha256.lower():
                raise HFIntegrityError(
                    f"Existing {dest.name} has SHA-256 {actual_sha256}; "
                    f"expected {expected_sha256}. The file was left unchanged."
                )

    def _prepare_partial(self, part, meta_path, remote, resume):
        expected_meta = _PartialMeta(
            repo_id=remote.repo_id,
            filename=remote.filename,
            revision=remote.revision,
            etag=remote.etag,
            commit=remote.commit,
            expected_size=remote.size,
        )

        if not resume:
            self._remove_partial(part, meta_path)
        else:
            self._validate_partial(part, meta_path, expected_meta)

        if not part.exists():
            part.touch()
            _atomic_json_write(meta_path, asdict(expected_meta))

        return expected_meta

    def _download_with_retry(  # noqa: PLR0913
        self, part, meta_path, expected_meta, reporter, *, cancelled, resume
    ):
        # Retry state includes partial provenance and caller cancellation policy.
        # pylint: disable=too-many-arguments
        remote = reporter.remote
        filename = remote.filename
        attempt = 0
        while True:
            if cancelled and cancelled():
                raise HFCancelled(f"Download cancelled: {filename}")

            current = part.stat().st_size
            if remote.size is not None and current > remote.size:
                self._remove_partial(part, meta_path)
                part.touch()
                _atomic_json_write(meta_path, asdict(expected_meta))
                current = 0

            range_headers: dict[str, str] = {}
            if resume and current > 0:
                range_headers["Range"] = f"bytes={current}-"

            try:
                response = self.session.get(
                    remote.url,
                    headers=self._headers(range_headers),
                    stream=True,
                    allow_redirects=True,
                    timeout=self.timeout,
                )

                # A stale/exact-complete range can produce 416.
                if response.status_code == HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE:
                    if remote.size is not None and current == remote.size:
                        response.close()
                        break
                    response.close()
                    # Do not append to something the server rejects.
                    self._remove_partial(part, meta_path)
                    part.touch()
                    _atomic_json_write(meta_path, asdict(expected_meta))
                    attempt += 1
                    if attempt > self.max_retries:
                        raise HFIntegrityError(
                            f"Server rejected resume range for {filename!r}."
                        )
                    continue

                if response.status_code in _RETRYABLE_STATUS:
                    delay = _retry_after(response)
                    response.close()
                    if attempt >= self.max_retries:
                        _raise_download_error(response, filename)
                    self._sleep_backoff(attempt, delay)
                    attempt += 1
                    continue

                self._raise_hf_error(
                    response,
                    repo_id=remote.repo_id,
                    filename=filename,
                )

                self._stream_response(response, part, reporter, cancelled)

                # A cleanly closed response should be complete. Verify below.
                break

            except (
                requests.ConnectionError,
                requests.Timeout,
                requests.exceptions.ChunkedEncodingError,
            ) as exc:
                if attempt >= self.max_retries:
                    raise HFError(
                        f"Network error while downloading {filename!r} after "
                        f"{self.max_retries + 1} attempts: {exc}"
                    ) from exc
                self._sleep_backoff(attempt)
                attempt += 1
                # Loop reopens .part and resumes from its current byte count.

    def _stream_response(self, response, part, reporter, cancelled):
        current = part.stat().st_size
        # Never append a full response when the server ignores Range.
        if current > 0 and response.status_code == HTTPStatus.PARTIAL_CONTENT:
            mode = "ab"
        else:
            mode = "wb"
            current = 0

        with response, part.open(mode) as fp:
            for chunk in response.iter_content(chunk_size=self.chunk_size):
                if cancelled and cancelled():
                    fp.flush()
                    try:
                        os.fsync(fp.fileno())
                    except OSError:
                        pass
                    raise HFCancelled(f"Download cancelled: {reporter.remote.filename}")
                if not chunk:
                    continue
                fp.write(chunk)
                current += len(chunk)
                reporter.report(current)

    def _request_with_retry(
        self, method: str, url: str, **kwargs: Any
    ) -> requests.Response:
        last_exc: BaseException | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(
                    method,
                    url,
                    timeout=self.timeout,
                    **kwargs,
                )
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_exc = exc
                if attempt >= self.max_retries:
                    break
                self._sleep_backoff(attempt)
                continue

            if response.status_code not in _RETRYABLE_STATUS:
                return response

            if attempt >= self.max_retries:
                return response

            delay = _retry_after(response)
            response.close()
            self._sleep_backoff(attempt, delay)

        raise HFError(f"Network request failed: {last_exc}") from last_exc

    def _sleep_backoff(self, attempt: int, explicit: float | None = None) -> None:
        if explicit is not None:
            delay = explicit
        else:
            delay = self.backoff * (2**attempt)
            delay *= random.uniform(0.8, 1.2)
        time.sleep(min(delay, 30.0))

    def _validate_partial(
        self,
        part: Path,
        meta_path: Path,
        expected: _PartialMeta,
    ) -> None:
        if not part.exists():
            if meta_path.exists():
                meta_path.unlink()
            return

        if not meta_path.exists():
            # Unknown provenance: unsafe to resume.
            part.unlink()
            return

        try:
            saved_raw = json.loads(meta_path.read_text(encoding="utf-8"))
            saved = _PartialMeta(**saved_raw)
        except Exception:
            self._remove_partial(part, meta_path)
            return

        same_identity = (
            saved.repo_id == expected.repo_id
            and saved.filename == expected.filename
            and saved.revision == expected.revision
        )

        # Prefer commit/etag as version identity. If HF didn't expose either,
        # size still gives a weak but useful guard.
        version_matches = True
        if expected.commit and saved.commit:
            version_matches = expected.commit == saved.commit
        elif expected.etag and saved.etag:
            version_matches = expected.etag == saved.etag
        elif expected.expected_size is not None and saved.expected_size is not None:
            version_matches = expected.expected_size == saved.expected_size

        if not same_identity or not version_matches:
            self._remove_partial(part, meta_path)

    @staticmethod
    def _remove_partial(part: Path, meta_path: Path) -> None:
        for path in (part, meta_path):
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as fp:
            while True:
                chunk = fp.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()

    def _verify_and_commit(
        self,
        part: Path,
        dest: Path,
        meta_path: Path,
        *,
        expected_size: int | None,
        expected_sha256: str | None,
    ) -> None:
        # Paths and integrity expectations are explicit at the commit boundary.
        # pylint: disable=too-many-arguments
        actual_size = part.stat().st_size

        if expected_size is not None and actual_size != expected_size:
            raise HFIntegrityError(
                f"Incomplete download: expected {expected_size} bytes, "
                f"got {actual_size} bytes. Partial file was kept for resume."
            )

        if expected_sha256 is not None:
            actual = self._sha256(part)
            if actual.lower() != expected_sha256.lower():
                raise HFIntegrityError(
                    f"SHA-256 mismatch for {dest.name}: expected "
                    f"{expected_sha256}, got {actual}. Partial file was kept."
                )

        os.replace(part, dest)
        try:
            meta_path.unlink()
        except FileNotFoundError:
            pass

    def _raise_hf_error(
        self,
        response: requests.Response,
        *,
        repo_id: str | None = None,
        filename: str | None = None,
    ) -> None:
        status = response.status_code
        if HTTPStatus.OK <= status < HTTPStatus.BAD_REQUEST:
            return

        request_id = response.headers.get("X-Request-Id") or response.headers.get(
            "X-Amzn-Trace-Id"
        )

        body = ""
        try:
            body = response.text[:4096]
        except Exception:
            pass

        lower = body.lower()
        subject = repo_id or "Hugging Face resource"
        if filename:
            subject = f"{subject}/{filename}"

        suffix = f" [request id: {request_id}]" if request_id else ""

        if status == HTTPStatus.TOO_MANY_REQUESTS:
            raise HFRateLimitError(
                f"Hugging Face rate limit exceeded for {subject}.{suffix}"
            )

        # HF gated-resource responses are commonly 401/403 with an explanatory
        # body. Detect this before the generic auth case.
        if status in (401, 403) and (
            "gated" in lower
            or "access to model" in lower
            or "access to this model" in lower
            or "request access" in lower
        ):
            model_page = self.model_url(repo_id) if repo_id else self.endpoint
            raise HFGatedError(
                f"Access to {subject} is gated. The signed-in Hugging Face user "
                f"must be granted/accept access first: {model_page}{suffix}"
            )

        if status in (401, 403):
            if self.token:
                raise HFAuthError(
                    f"Hugging Face denied access to {subject}. The token may "
                    f"be invalid or lack permission.{suffix}"
                )
            raise HFAuthError(
                f"{subject} requires Hugging Face authentication.{suffix}"
            )

        if status == HTTPStatus.NOT_FOUND:
            raise HFNotFoundError(
                f"Hugging Face repository, revision, or file not found: "
                f"{subject}.{suffix}"
            )

        message = f"Hugging Face returned HTTP {status} for {subject}"
        if body:
            # Keep server text useful but bounded.
            compact = " ".join(body.split())
            message += f": {compact[:500]}"
        raise HFError(message + suffix)


# Keep the convenience wrapper compatible with existing callers.
def download_hf_model(  # noqa: PLR0913
    repo_id: str,
    filename: str,
    *,
    revision: str = "main",
    token: str | None = None,
    destination: str | os.PathLike[str] | None = None,
    progress: Callable[[DownloadProgress], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
    overwrite: bool = False,
    expected_sha256: str | None = None,
) -> str:
    """Download one Hugging Face model file and return its local path as a string."""

    # pylint: disable=too-many-arguments
    client = HFClient(token=token)
    remote = client.file_info(repo_id, filename, revision=revision)
    lfs_info = client.git_lfs_info(repo_id, filename, revision=revision)
    if lfs_info is not None:
        if remote.size is not None and lfs_info["size"] != remote.size:
            raise HFIntegrityError(
                f"Conflicting sizes for {filename}: download metadata reports "
                f"{remote.size}, Git LFS reports {lfs_info['size']}"
            )
        if expected_sha256 is None:
            expected_sha256 = lfs_info["sha256"]

    if destination is None:
        destination = model_path(repo_id, filename)
    else:
        destination = Path(destination)

    path = client.download(
        repo_id,
        filename,
        destination,
        revision=revision,
        overwrite=overwrite,
        progress=progress,
        cancelled=cancelled,
        expected_sha256=expected_sha256,
    )
    return str(path)


def format_bytes(value: int | None) -> str:
    if value is None:
        return "?"
    n = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if n < _BYTES_PER_KIB or unit == "TiB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= _BYTES_PER_KIB
    return f"{n:.1f} TiB"


def format_eta(seconds: float | None) -> str:
    if seconds is None:
        return "?"
    seconds = max(0, int(seconds))
    if seconds < _SECONDS_PER_MINUTE:
        return f"{seconds}s"
    minutes, sec = divmod(seconds, _SECONDS_PER_MINUTE)
    if minutes < _MINUTES_PER_HOUR:
        return f"{minutes}m {sec:02d}s"
    hours, minutes = divmod(minutes, _MINUTES_PER_HOUR)
    return f"{hours}h {minutes:02d}m"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download one file from Hugging Face.")
    parser.add_argument("repo_id")
    parser.add_argument("filename")
    parser.add_argument("destination")
    parser.add_argument("--revision", default="main")
    parser.add_argument("--token", default=os.environ.get("HF_TOKEN"))
    args = parser.parse_args()

    cli_client = HFClient(token=args.token)

    def show(p: DownloadProgress) -> None:
        pct = f"{p.percent:5.1f}%" if p.percent is not None else "  ?  "
        print(
            f"\r{pct}  {format_bytes(p.downloaded)} / {format_bytes(p.total)}  "
            f"{p.speed_mbps:.1f} MiB/s  ETA {format_eta(p.eta)}",
            end="",
            flush=True,
        )

    result = cli_client.download(
        args.repo_id,
        args.filename,
        args.destination,
        revision=args.revision,
        progress=show,
    )
    print(f"\nSaved to {result}")
