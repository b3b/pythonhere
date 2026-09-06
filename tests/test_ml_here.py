import hashlib
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

from pythonhere.ml_here import (
    discover_models,
    model_path,
    models_directory,
    require_model,
    storage,
)
from pythonhere.ml_here.huggingface import (
    HFCancelled,
    HFClient,
    HFError,
    HFRateLimitError,
    RemoteFile,
    download_hf_model,
)


def test_models_directory_uses_linux_user_data(monkeypatch, tmp_path):
    monkeypatch.delenv("ANDROID_ARGUMENT", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    result = models_directory(create=True)

    assert result == str(tmp_path / ".local" / "share" / "pythonhere" / "models")
    assert Path(result).is_dir()


def test_models_directory_uses_lowercase_android_directory(monkeypatch):
    external_files = SimpleNamespace(getAbsolutePath=lambda: "/android/files")
    activity = SimpleNamespace(getExternalFilesDir=lambda _kind: external_files)
    python_activity = SimpleNamespace(mActivity=activity)
    jnius = SimpleNamespace(autoclass=lambda _class_name: python_activity)
    monkeypatch.setitem(sys.modules, "jnius", jnius)
    monkeypatch.setattr(storage.sys, "platform", "android")

    assert models_directory() == "/android/files/models"


def test_discover_models_reads_pythonhere_directory(monkeypatch, tmp_path):
    monkeypatch.delenv("ANDROID_ARGUMENT", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    models = tmp_path / ".local" / "share" / "pythonhere" / "models"
    repository = models / "owner" / "zebra"
    extra = tmp_path / "extra"
    repository.mkdir(parents=True)
    extra.mkdir()
    (repository / "zebra.litertlm").write_bytes(b"zebra")
    (models / "model.tflite").write_bytes(b"tflite")
    (models / "unfinished.tflite.part").write_bytes(b"partial")
    (models / "unfinished.tflite.part.json").write_text("{}", encoding="utf-8")
    (extra / "Alpha.LITERTLM").write_bytes(b"alpha")

    assert models_directory() == str(models)
    assert discover_models(extra, extensions="litertlm") == [
        str(extra / "Alpha.LITERTLM"),
        str(repository / "zebra.litertlm"),
    ]
    assert discover_models(extensions=(".tflite",)) == [str(models / "model.tflite")]
    assert discover_models(extra) == [
        str(extra / "Alpha.LITERTLM"),
        str(repository / "zebra.litertlm"),
    ]
    assert discover_models(extra, extensions=None) == [
        str(extra / "Alpha.LITERTLM"),
        str(models / "model.tflite"),
        str(repository / "zebra.litertlm"),
    ]


def test_model_path_is_namespaced_and_does_not_create_directories(
    monkeypatch, tmp_path
):
    monkeypatch.delenv("ANDROID_ARGUMENT", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    result = model_path("owner/repository", "variants/model.litertlm")

    expected = (
        tmp_path
        / ".local"
        / "share"
        / "pythonhere"
        / "models"
        / "owner"
        / "repository"
        / "variants"
        / "model.litertlm"
    )
    assert result == str(expected)
    assert not expected.parent.exists()


@pytest.mark.parametrize(
    ("repo_id", "filename"),
    [
        ("../owner", "model.litertlm"),
        ("owner/repository", "../model.litertlm"),
        ("/owner/repository", "model.litertlm"),
        ("owner/repository", "/model.litertlm"),
    ],
)
def test_model_path_rejects_unsafe_components(monkeypatch, tmp_path, repo_id, filename):
    monkeypatch.delenv("ANDROID_ARGUMENT", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    with pytest.raises(ValueError):
        model_path(repo_id, filename)


def test_require_model_returns_installed_model(monkeypatch, tmp_path):
    monkeypatch.delenv("ANDROID_ARGUMENT", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    path = Path(model_path("owner/repository", "model.litertlm"))
    path.parent.mkdir(parents=True)
    path.write_bytes(b"model")

    assert require_model("owner/repository", "model.litertlm") == str(path)


def test_require_model_reports_missing_model(monkeypatch, tmp_path):
    monkeypatch.delenv("ANDROID_ARGUMENT", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    expected = model_path("owner/repository", "model.litertlm")

    with pytest.raises(
        FileNotFoundError,
        match=r"ML model is not installed: owner/repository/model\.litertlm",
    ) as error:
        require_model("owner/repository", "model.litertlm")

    assert str(error.value).endswith(f"({expected})")


@pytest.fixture
def model_server():
    content = b"portable LiteRT model fixture"
    etag = hashlib.sha256(content).hexdigest()

    class Handler(BaseHTTPRequestHandler):
        def do_HEAD(self):
            self.send_response(200)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("ETag", etag)
            self.end_headers()

        def do_GET(self):
            start = 0
            requested_range = self.headers.get("Range")
            if requested_range:
                start = int(requested_range.removeprefix("bytes=").removesuffix("-"))
                self.send_response(206)
                self.send_header(
                    "Content-Range", f"bytes {start}-{len(content) - 1}/{len(content)}"
                )
            else:
                self.send_response(200)
            body = content[start:]
            self.send_header("Content-Length", str(len(body)))
            self.send_header("ETag", etag)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, content, etag
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_hf_client_downloads_and_resumes_on_desktop(model_server, tmp_path):
    server, content, etag = model_server
    endpoint = f"http://127.0.0.1:{server.server_port}"
    destination = tmp_path / "model.litertlm"
    part = tmp_path / "model.litertlm.part"
    metadata = tmp_path / "model.litertlm.part.json"
    partial_size = 9
    part.write_bytes(content[:partial_size])
    metadata.write_text(
        "{"
        '"repo_id":"owner/model",'
        '"filename":"model.litertlm",'
        '"revision":"main",'
        f'"etag":"{etag}",'
        '"commit":null,'
        f'"expected_size":{len(content)}'
        "}",
        encoding="utf-8",
    )
    client = HFClient(endpoint=endpoint, max_retries=0, chunk_size=4)

    result = client.download(
        "owner/model",
        "model.litertlm",
        destination,
        expected_sha256=etag,
    )

    assert result == destination
    assert destination.read_bytes() == content
    assert not part.exists()
    assert not metadata.exists()


def test_download_hf_model_uses_portable_default_directory(monkeypatch, tmp_path):
    models = tmp_path / ".local" / "share" / "pythonhere" / "models"
    content = b"downloaded model"
    monkeypatch.delenv("ANDROID_ARGUMENT", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(
        HFClient,
        "file_info",
        lambda _self, repo_id, filename, *, revision: RemoteFile(
            repo_id=repo_id,
            filename=filename,
            revision=revision,
            size=len(content),
            etag=None,
            commit=None,
            url="https://example.invalid/model.litertlm",
        ),
    )
    monkeypatch.setattr(
        HFClient,
        "git_lfs_info",
        lambda _self, _repo_id, _filename, *, revision: None,
    )

    def fake_download(_self, _repo_id, _filename, destination, **_kwargs):
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return destination

    monkeypatch.setattr(HFClient, "download", fake_download)

    result = download_hf_model("owner/model", "nested/model.litertlm")

    assert result == str(models / "owner" / "model" / "nested" / "model.litertlm")
    assert result == require_model("owner/model", "nested/model.litertlm")
    assert Path(result).read_bytes() == content


def test_download_hf_model_accepts_non_litert_lm_files(monkeypatch, tmp_path):
    monkeypatch.setattr(
        HFClient,
        "file_info",
        lambda _self, repo_id, filename, *, revision: RemoteFile(
            repo_id=repo_id,
            filename=filename,
            revision=revision,
            size=5,
            etag=None,
            commit=None,
            url="https://example.invalid/model.tflite",
        ),
    )
    monkeypatch.setattr(
        HFClient,
        "git_lfs_info",
        lambda _self, _repo_id, _filename, *, revision: None,
    )

    destination = tmp_path / "model.tflite"

    def fake_download(_self, _repo_id, _filename, path, **_kwargs):
        path = Path(path)
        path.write_bytes(b"model")
        return path

    monkeypatch.setattr(HFClient, "download", fake_download)

    assert download_hf_model(
        "owner/model", "model.tflite", destination=destination
    ) == str(destination)


def test_hf_cancellation_keeps_partial_and_resume_reports_progress(
    model_server, tmp_path
):
    server, content, etag = model_server
    client = HFClient(
        endpoint=f"http://127.0.0.1:{server.server_port}", chunk_size=4, max_retries=0
    )
    destination = tmp_path / "model.litertlm"
    reports = []

    with pytest.raises(HFCancelled):
        client.download(
            "owner/model",
            "model.litertlm",
            destination,
            progress=reports.append,
            progress_interval=0,
            cancelled=lambda: bool(reports),
        )

    part = destination.with_suffix(".litertlm.part")
    partial_size = part.stat().st_size
    assert 0 < partial_size < len(content)
    assert part.read_bytes() == content[:partial_size]
    assert not destination.exists()
    assert destination.with_suffix(".litertlm.part.json").exists()

    reports.clear()
    client.download(
        "owner/model",
        "model.litertlm",
        destination,
        progress=reports.append,
        progress_interval=0,
        expected_sha256=etag,
    )

    assert destination.read_bytes() == content
    assert reports[0].downloaded > partial_size
    assert reports[-1].downloaded == len(content)
    assert reports[-1].total == len(content)
    assert reports[-1].percent == 100
    assert reports[-1].destination == str(destination)
    assert not part.exists()


@pytest.fixture
def fake_hf_transfer(mocker):
    content = b"abcdefgh"
    session = mocker.Mock()
    client = HFClient(session=session, max_retries=1, backoff=0)
    mocker.patch.object(
        client,
        "file_info",
        return_value=RemoteFile(
            "owner/model",
            "model.bin",
            "main",
            len(content),
            None,
            None,
            "https://example.invalid/model.bin",
        ),
    )

    def response(status, chunks=()):
        result = mocker.MagicMock(spec=requests.Response)
        result.status_code = status
        result.headers = {}

        def stream(**_kwargs):
            for chunk in chunks:
                if isinstance(chunk, Exception):
                    raise chunk
                yield chunk

        result.iter_content.side_effect = stream
        return result

    return client, session, response, content


@pytest.mark.parametrize("resume_status", [200, 206])
def test_hf_interrupted_stream_retries_without_duplicate_bytes(
    fake_hf_transfer, tmp_path, resume_status
):
    client, session, response, content = fake_hf_transfer
    interrupted = response(
        200, [content[:4], requests.exceptions.ChunkedEncodingError("disconnected")]
    )
    resumed = response(
        resume_status, [content[4:] if resume_status == 206 else content]
    )
    session.get.side_effect = [interrupted, resumed]
    destination = tmp_path / "model.bin"

    client.download("owner/model", "model.bin", destination)

    assert destination.read_bytes() == content
    assert session.get.call_count == 2
    assert session.get.call_args_list[1].kwargs["headers"]["Range"] == "bytes=4-"
    assert interrupted.__exit__.called
    assert resumed.__exit__.called


@pytest.mark.parametrize(
    "status, error_type", [(429, HFRateLimitError), (503, HFError)]
)
def test_hf_exhausted_http_retries_preserve_error_and_partial(
    fake_hf_transfer, tmp_path, status, error_type
):
    client, session, response, _content = fake_hf_transfer
    responses = [response(status), response(status)]
    session.get.side_effect = responses
    destination = tmp_path / "model.bin"

    with pytest.raises(error_type):
        client.download("owner/model", "model.bin", destination)

    assert session.get.call_count == 2
    assert all(item.close.called for item in responses)
    assert not destination.exists()
    assert destination.with_suffix(".bin.part").exists()
