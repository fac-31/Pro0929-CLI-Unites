"""Deterministic placeholder embeddings for local similarity scoring.

This avoids extra dependencies while keeping the API surface that future
client-side embedding generation can hook into.
"""
from __future__ import annotations

import hashlib
from typing import List


def embed_text(text: str, dimensions: int = 12) -> List[float]:
    normalized = text.strip().lower().encode("utf-8")
    digest = hashlib.sha256(normalized).digest()
    # Convert the digest into a list of floats in the range [0, 1)
    chunk_size = len(digest) // dimensions
    if chunk_size == 0:
        chunk_size = len(digest)
        dimensions = 1
    vector = []
    for i in range(dimensions):
        start = i * chunk_size
        end = start + chunk_size
        chunk = digest[start:end]
        if not chunk:
            chunk = digest[-chunk_size:]
        value = int.from_bytes(chunk, "big")
        vector.append((value % 1000) / 1000.0)
    return vector


__all__ = ["embed_text"]
