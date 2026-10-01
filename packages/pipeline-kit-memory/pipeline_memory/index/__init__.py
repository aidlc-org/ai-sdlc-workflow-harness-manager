"""Search index backends for the memory bank."""

from __future__ import annotations

from pipeline_memory.index.base import SearchBackend, SearchHit
from pipeline_memory.index.fts5 import Fts5Backend

__all__ = ["SearchBackend", "SearchHit", "Fts5Backend", "get_backend"]


def get_backend(name: str = "fts5") -> SearchBackend:
    key = (name or "fts5").strip().lower()
    if key in {"fts5", "sqlite", "default"}:
        return Fts5Backend()
    raise ValueError(f"unknown memory index engine: {name!r} (built-in: fts5)")
