"""Chunk text files and classify artifact kinds."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

TEXT_SUFFIXES = {".md", ".json", ".txt", ".env", ".yml", ".yaml", ".csv"}
SKIP_DIR_NAMES = {".git", ".memory", "node_modules", "__pycache__", ".venv", "venv"}

KIND_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?i)^request\.md$"), "request"),
    (re.compile(r"(?i)^decisions?\.md$"), "decision"),
    (re.compile(r"(?i)^HANDOFF"), "handoff"),
    (re.compile(r"(?i)architecture"), "architecture"),
    (re.compile(r"(?i)(prd|plan|implementation-plan)"), "plan"),
    (re.compile(r"(?i)^signoff-"), "signoff"),
    (re.compile(r"(?i)pipeline-state\.json$"), "state"),
    (re.compile(r"(?i)/state/.*\.json$"), "state"),
    (re.compile(r"(?i)(test|qa-|cases\.json|locators)"), "test"),
    (re.compile(r"(?i)context-pack\.json$"), "context"),
]

HEADING = re.compile(r"(?m)^(#{1,3})\s+(.+)$")
MAX_CHUNK = 3500


@dataclass(frozen=True)
class Chunk:
    rel_path: str
    slug: str
    kind: str
    title: str
    body: str
    project_id: str = ""


def classify_kind(rel_path: str) -> str:
    name = Path(rel_path).name
    posix = rel_path.replace("\\", "/")
    for pattern, kind in KIND_RULES:
        if pattern.search(name) or pattern.search(posix):
            return kind
    return "other"


def extract_slug(rel_path: str, artifact_dir: str = "features") -> str:
    parts = Path(rel_path).as_posix().split("/")
    art = artifact_dir.strip("/")
    if "projects" in parts:
        try:
            i = parts.index("projects")
            # projects/{id}/features/{slug}/...
            if len(parts) > i + 3 and parts[i + 2] == art:
                return parts[i + 3]
        except ValueError:
            pass
    if art in parts:
        i = parts.index(art)
        if len(parts) > i + 1:
            return parts[i + 1]
    return ""


def extract_project_id(rel_path: str) -> str:
    parts = Path(rel_path).as_posix().split("/")
    if "projects" in parts:
        i = parts.index("projects")
        if len(parts) > i + 1:
            return parts[i + 1]
    return ""


def chunk_markdown(text: str, rel_path: str) -> list[tuple[str, str]]:
    """Return list of (title, body) chunks."""
    text = text.replace("\r\n", "\n")
    if not text.strip():
        return []
    matches = list(HEADING.finditer(text))
    if not matches:
        body = text.strip()
        title = Path(rel_path).stem
        if len(body) <= MAX_CHUNK:
            return [(title, body)]
        return [
            (f"{title} [{i}]", body[i : i + MAX_CHUNK])
            for i in range(0, len(body), MAX_CHUNK)
        ]

    out: list[tuple[str, str]] = []
    # Preamble before first heading
    if matches[0].start() > 0:
        pre = text[: matches[0].start()].strip()
        if pre:
            out.append((Path(rel_path).stem, pre[:MAX_CHUNK]))

    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        section = text[start:end].strip()
        title = match.group(2).strip()
        if len(section) <= MAX_CHUNK:
            out.append((title, section))
        else:
            for j in range(0, len(section), MAX_CHUNK):
                out.append((f"{title} [{j // MAX_CHUNK}]", section[j : j + MAX_CHUNK]))
    return out


def chunk_file(path: Path, rel_path: str, *, artifact_dir: str = "features") -> list[Chunk]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    kind = classify_kind(rel_path)
    slug = extract_slug(rel_path, artifact_dir)
    project_id = extract_project_id(rel_path)
    suffix = path.suffix.lower()
    pieces: list[tuple[str, str]]
    if suffix in {".md", ".txt"}:
        pieces = chunk_markdown(text, rel_path)
    elif suffix == ".json":
        title = Path(rel_path).name
        body = text.strip()
        if len(body) <= MAX_CHUNK:
            pieces = [(title, body)]
        else:
            pieces = [(f"{title} [{i}]", body[i : i + MAX_CHUNK]) for i in range(0, len(body), MAX_CHUNK)]
    else:
        body = text.strip()[:MAX_CHUNK]
        pieces = [(Path(rel_path).name, body)] if body else []

    return [
        Chunk(
            rel_path=rel_path.replace("\\", "/"),
            slug=slug,
            kind=kind,
            title=title,
            body=body,
            project_id=project_id,
        )
        for title, body in pieces
        if body.strip()
    ]


def iter_text_files(root: Path) -> list[Path]:
    root = Path(root).resolve()
    found: list[Path] = []
    if not root.is_dir():
        return found
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        found.append(path)
    return found
