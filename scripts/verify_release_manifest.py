#!/usr/bin/env python3
"""Verify SHA-256 hashes for the public reviewer artifact."""

from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "MANIFEST.sha256"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    if not MANIFEST.is_file():
        raise SystemExit("missing MANIFEST.sha256")
    checked = 0
    for line_number, line in enumerate(MANIFEST.read_text().splitlines(), 1):
        if not line.strip():
            continue
        expected, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.is_file():
            raise SystemExit(f"missing file at manifest line {line_number}: {relative}")
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(
                f"hash mismatch at manifest line {line_number}: {relative}"
            )
        checked += 1
    print(f"release manifest verified: {checked} files")


if __name__ == "__main__":
    main()

