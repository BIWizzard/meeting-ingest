"""Content hashing helpers."""

from __future__ import annotations

from pathlib import Path

import hashlib


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def short_hash(value: str, *, length: int = 8) -> str:
    if length <= 0:
        raise ValueError("length must be positive")
    if len(value) < length:
        raise ValueError("value shorter than requested short hash length")
    return value[:length]
