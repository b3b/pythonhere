#!/usr/bin/env python3
"""Extract one version section from CHANGELOG.rst."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def extract_section(changelog: str, version: str) -> str:
    pattern = re.compile(
        rf"^{re.escape(version)}\n[-=~^`:#\"']+\n(?P<body>.*?)(?=\n[0-9]+[.][0-9]+[.][0-9]+\n[-=~^`:#\"']+\n|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(changelog)
    if match is None:
        raise SystemExit(f"CHANGELOG.rst does not contain a section for {version}")

    body = match.group("body").strip()
    if not body:
        raise SystemExit(f"CHANGELOG.rst section for {version} is empty")

    return body + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("version")
    parser.add_argument(
        "--changelog",
        default="CHANGELOG.rst",
        type=Path,
        help="Path to the RST changelog",
    )
    parser.add_argument(
        "--output",
        default="release-notes.rst",
        type=Path,
        help="Path to write the extracted release notes",
    )
    args = parser.parse_args()

    changelog = args.changelog.read_text(encoding="utf-8")
    args.output.write_text(extract_section(changelog, args.version), encoding="utf-8")


if __name__ == "__main__":
    main()
