"""SQLite FTS5 backend — default offline lexical search."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from pipeline_memory.index.base import SearchHit
from pipeline_memory.index.chunk import chunk_file, iter_text_files

KIND_BOOST = {
    "decision": 1.35,
    "request": 1.25,
    "handoff": 1.2,
    "architecture": 1.15,
    "plan": 1.1,
    "signoff": 1.05,
}


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY,
            project_id TEXT NOT NULL DEFAULT '',
            slug TEXT NOT NULL DEFAULT '',
            rel_path TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT 'other',
            title TEXT NOT NULL DEFAULT '',
            body TEXT NOT NULL,
            mtime REAL NOT NULL DEFAULT 0
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            title,
            body,
            content='chunks',
            content_rowid='id',
            tokenize='porter unicode61'
        );
        """
    )
    conn.commit()


def _fts_query(raw: str) -> str:
    """Build a safe FTS5 query from free text."""
    tokens = re.findall(r"[A-Za-z0-9_./-]+", raw)
    if not tokens:
        return '""'
    parts = []
    for tok in tokens:
        if tok.upper() in {"AND", "OR", "NOT", "NEAR"}:
            continue
        safe = tok.replace('"', "")
        if not safe:
            continue
        parts.append(f'"{safe}"*')
    return " AND ".join(parts) if parts else '""'


class Fts5Backend:
    def rebuild(self, db_path: Path, root: Path, *, project_id: str | None = None) -> int:
        root = Path(root).resolve()
        conn = _connect(db_path)
        try:
            _ensure_schema(conn)
            conn.execute("DELETE FROM chunks")
            conn.execute("DELETE FROM chunks_fts")
            count = 0
            for path in iter_text_files(root):
                try:
                    rel = path.relative_to(root).as_posix()
                except ValueError:
                    continue
                mtime = path.stat().st_mtime
                for chunk in chunk_file(path, rel):
                    pid = project_id if project_id is not None else chunk.project_id
                    cur = conn.execute(
                        """
                        INSERT INTO chunks (project_id, slug, rel_path, kind, title, body, mtime)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (pid or "", chunk.slug, chunk.rel_path, chunk.kind, chunk.title, chunk.body, mtime),
                    )
                    rowid = cur.lastrowid
                    conn.execute(
                        """
                        INSERT INTO chunks_fts (rowid, title, body)
                        VALUES (?, ?, ?)
                        """,
                        (rowid, chunk.title, chunk.body),
                    )
                    count += 1
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES ('root', ?)",
                (str(root),),
            )
            conn.commit()
            return count
        finally:
            conn.close()

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
        if not Path(db_path).is_file():
            return []
        q = _fts_query(query)
        conn = _connect(db_path)
        try:
            _ensure_schema(conn)
            sql = """
                SELECT c.rel_path, c.slug, c.kind, c.title, c.body, c.project_id, c.mtime,
                       bm25(chunks_fts) AS rank
                FROM chunks_fts
                JOIN chunks c ON c.id = chunks_fts.rowid
                WHERE chunks_fts MATCH ?
            """
            params: list[object] = [q]
            if slug:
                sql += " AND c.slug = ?"
                params.append(slug)
            if kind:
                sql += " AND c.kind = ?"
                params.append(kind)
            if project_id:
                sql += " AND c.project_id = ?"
                params.append(project_id)
            sql += " ORDER BY rank LIMIT ?"
            params.append(max(limit * 4, limit))
            try:
                rows = conn.execute(sql, params).fetchall()
            except sqlite3.OperationalError:
                return []

            hits: list[SearchHit] = []
            for row in rows:
                body = row["body"] or ""
                excerpt = body[:400].replace("\n", " ").strip()
                if len(body) > 400:
                    excerpt += "…"
                boost = KIND_BOOST.get(row["kind"], 1.0)
                # bm25: lower is better in sqlite; invert for display score
                raw_rank = float(row["rank"] or 0.0)
                score = boost / (1.0 + abs(raw_rank))
                hits.append(
                    SearchHit(
                        path=row["rel_path"],
                        slug=row["slug"] or "",
                        kind=row["kind"] or "other",
                        title=row["title"] or "",
                        excerpt=excerpt,
                        score=round(score, 6),
                        project_id=row["project_id"] or "",
                    )
                )
            hits.sort(key=lambda h: h.score, reverse=True)
            return hits[:limit]
        finally:
            conn.close()
