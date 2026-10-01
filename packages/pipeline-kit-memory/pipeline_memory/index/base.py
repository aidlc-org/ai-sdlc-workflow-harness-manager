"""Search backend protocol."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class SearchHit:
    path: str
    slug: str
    kind: str
    title: str
    excerpt: str
    score: float
    project_id: str = ""


class SearchBackend(Protocol):
    def rebuild(self, db_path: Path, root: Path, *, project_id: str | None = None) -> int:
        """Index *root*; return chunk count."""

    def search(
        self,
        db_path: Path,
        query: str,
        *,
        limit: int = 10,
        slug: str | None = None,
        kind: str | None = None,
        project_id: str | None = None,
    ) -> list[SearchHit]:
        """Ranked hits for *query*."""
