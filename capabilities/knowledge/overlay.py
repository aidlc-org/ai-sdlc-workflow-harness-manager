"""QA overlay on disk. Agents read these files; Graphify owns graphify-out/."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from knowledge.const import (
    AREAS_DIR,
    CANDIDATES_DIR,
    CONFIG_REL,
    EVIDENCE_STATES,
    GRAPH_DIR,
    GRAPH_JSON,
    GRAPH_PROVIDER,
    ID_PATTERN,
    ITEM_CATALOGS,
    KNOWLEDGE_DIR,
    SECRET_PATTERNS,
)
from knowledge.graphify import graph_exists, graph_freshness, graph_json_path


class OverlayError(ValueError):
    """Overlay or candidate catalog is invalid."""


def knowledge_root(project: Path) -> Path:
    return project / KNOWLEDGE_DIR


def manifest_path(project: Path) -> Path:
    return knowledge_root(project) / "manifest.json"


def candidates_root(project: Path) -> Path:
    return knowledge_root(project) / CANDIDATES_DIR


def config_path(project: Path) -> Path:
    return project / CONFIG_REL


def test_design_config(project: Path) -> dict[str, Any]:
    path = config_path(project)
    if not path.is_file():
        return {}
    loaded = _read_json(path)
    block = loaded.get("test_design")
    return block if isinstance(block, dict) else {}


def test_design_enabled(project: Path) -> bool:
    return test_design_config(project).get("enabled") is True


def init_overlay(project: Path) -> Path:
    """Create the overlay skeleton. Never writes graphify-out/."""
    root = knowledge_root(project)
    (root / AREAS_DIR).mkdir(parents=True, exist_ok=True)
    (root / CANDIDATES_DIR).mkdir(parents=True, exist_ok=True)
    _write_json_if_absent(manifest_path(project), default_manifest(project))
    _write_json_if_absent(
        root / "application.json",
        {"version": 1, "name": "", "areas": [], "evidence": "inferred"},
    )
    for name in ("actions.json", "fixtures.json", "oracles.json"):
        _write_json_if_absent(root / name, {"version": 1, "items": []})
    _write_json_if_absent(root / "coverage.json", {"version": 1, "areas": {}})
    readme = root / "README.md"
    if not readme.is_file():
        readme.write_text(
            (
                "# QA knowledge overlay\n\n"
                "This folder is the reviewed catalog for test design. "
                "The structural graph lives in `graphify-out/` and is owned by "
                "Graphify. Do not invent a second graph here.\n"
            ),
            encoding="utf-8",
        )
    return root


def enable_test_design(project: Path) -> None:
    path = config_path(project)
    if not path.is_file():
        raise OverlayError("no .pipeline/config.json — run pipeline-kit init first")
    data = _read_json(path)
    block = data.get("test_design")
    if not isinstance(block, dict):
        block = {}
    block["enabled"] = True
    block.setdefault("graph_provider", GRAPH_PROVIDER)
    block.setdefault("graph_path", f"{GRAPH_DIR}/{GRAPH_JSON}")
    block["design_only"] = False
    block["playwright"] = True
    block.setdefault("playwright_dir", "automation-tests")
    data["test_design"] = block
    _replace_json(path, data)


def promote_feature_nodes(project: Path, slug: str) -> list[str]:
    """Merge planned overlay nodes from a feature into test-knowledge as inferred."""
    try:
        from pipeline_kit.paths import feature_dir as _fd
        design = _fd(project, slug) / "test-design"
    except Exception:
        design = project / "features" / slug / "test-design"
    if not design.is_dir():
        raise OverlayError(f"missing {design}")
    root = init_overlay(project)
    promoted: list[str] = []
    for catalog in ITEM_CATALOGS:
        incoming = design / f"new-{catalog}"
        if catalog == "actions.json":
            incoming = design / "new-actions.json"
        if not incoming.is_file():
            continue
        payload = _read_json(incoming)
        items = payload.get("items") if isinstance(payload, dict) else None
        if not isinstance(items, list):
            raise OverlayError(f"{incoming.name}: expected {{version, items[]}}")
        dest = root / catalog
        current = _read_json(dest) if dest.is_file() else {"version": 1, "items": []}
        existing = current.get("items")
        if not isinstance(existing, list):
            existing = []
        by_id = {
            item.get("id"): item
            for item in existing
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                continue
            merged = dict(item)
            merged["evidence"] = "inferred"
            by_id[merged["id"]] = merged
        current["items"] = list(by_id.values())
        _replace_json(dest, current)
        promoted.append(catalog)
    refresh_manifest_graph(project)
    return promoted


def refresh_manifest_graph(project: Path) -> None:
    path = manifest_path(project)
    if not path.is_file():
        return
    manifest = _read_json(path)
    graph = manifest.setdefault("graph", {})
    if not isinstance(graph, dict):
        graph = {}
        manifest["graph"] = graph
    graph["provider"] = GRAPH_PROVIDER
    graph["path"] = f"{GRAPH_DIR}/{GRAPH_JSON}"
    target = graph_json_path(project)
    graph["sha256"] = _sha256(target) if target.is_file() else None
    graph["updated_at"] = _now()
    fresh = graph_freshness(project)
    graph["freshness"] = fresh["state"]
    if fresh["state"] == "stale":
        graph["stale"] = True
    _replace_json(path, manifest)


def overlay_status(project: Path) -> dict[str, Any]:
    root = knowledge_root(project)
    return {
        "present": manifest_path(project).is_file(),
        "path": str(root) if root.is_dir() else None,
        "test_design_enabled": test_design_enabled(project),
        "graph_present": graph_exists(project),
        "graph_path": str(graph_json_path(project)),
        "graph_freshness": graph_freshness(project)["state"] if graph_exists(project) else "absent",
    }


def default_manifest(project: Path) -> dict[str, Any]:
    target = graph_json_path(project)
    return {
        "version": 1,
        "design_only": True,
        "graph": {
            "provider": GRAPH_PROVIDER,
            "path": f"{GRAPH_DIR}/{GRAPH_JSON}",
            "sha256": _sha256(target) if target.is_file() else None,
        },
    }


def candidate_dir(project: Path, run_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", run_id):
        raise OverlayError("run id must be a simple token")
    return candidates_root(project) / run_id


def validate_candidates(project: Path, run_id: str) -> list[str]:
    folder = candidate_dir(project, run_id)
    if not folder.is_dir():
        raise OverlayError(f"candidates not found: {folder}")
    errors: list[str] = []
    seen_ids: set[str] = set()
    for path in sorted(folder.rglob("*.json")):
        rel = path.relative_to(folder).as_posix()
        try:
            payload = _read_json(path)
        except OverlayError as exc:
            errors.append(f"{rel}: {exc}")
            continue
        errors.extend(_validate_payload(rel, payload, seen_ids))
        leaked = _secret_hits(path.read_text(encoding="utf-8"))
        errors.extend(f"{rel}: possible secret or PII — {hit}" for hit in leaked)
    return errors


def promote_candidates(project: Path, run_id: str) -> list[str]:
    errors = validate_candidates(project, run_id)
    if errors:
        raise OverlayError("validation failed:\n" + "\n".join(errors))
    folder = candidate_dir(project, run_id)
    root = init_overlay(project)
    promoted: list[str] = []
    for path in sorted(folder.rglob("*.json")):
        rel = path.relative_to(folder).as_posix()
        if Path(rel).name.startswith(".") or Path(rel).name.upper().startswith("REVIEW"):
            continue
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        _replace_bytes(dest, path.read_bytes())
        promoted.append(rel)
    refresh_manifest_graph(project)
    return promoted


def _validate_payload(rel: str, payload: Any, seen_ids: set[str]) -> list[str]:
    errors: list[str] = []
    name = Path(rel).name
    if name in ITEM_CATALOGS:
        items = payload.get("items") if isinstance(payload, dict) else None
        if not isinstance(items, list):
            return [f"{rel}: expected {{version, items[]}}"]
        for index, item in enumerate(items):
            errors.extend(_validate_item(f"{rel}[{index}]", item, seen_ids))
        return errors
    if name == "application.json" and isinstance(payload, dict):
        evidence = payload.get("evidence")
        if evidence not in EVIDENCE_STATES:
            errors.append(f"{rel}: evidence must be one of {sorted(EVIDENCE_STATES)}")
        return errors
    if isinstance(payload, dict) and "id" in payload:
        errors.extend(_validate_item(rel, payload, seen_ids))
    return errors


def _validate_item(label: str, item: Any, seen_ids: set[str]) -> list[str]:
    if not isinstance(item, dict):
        return [f"{label}: expected an object"]
    errors: list[str] = []
    ident = item.get("id")
    if not isinstance(ident, str) or not re.fullmatch(ID_PATTERN, ident):
        errors.append(f"{label}: id must match {ID_PATTERN}")
    elif ident in seen_ids:
        errors.append(f"{label}: duplicate id {ident}")
    else:
        seen_ids.add(ident)
    evidence = item.get("evidence")
    if evidence not in EVIDENCE_STATES:
        errors.append(f"{label}: evidence must be one of {sorted(EVIDENCE_STATES)}")
    return errors


def _secret_hits(text: str) -> list[str]:
    hits: list[str] = []
    for pattern in SECRET_PATTERNS:
        match = re.search(pattern, text)
        if match:
            hits.append(match.group(0)[:48])
    return hits


def _read_json(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OverlayError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise OverlayError(f"{path} must be a JSON object")
    return loaded


def _write_json_if_absent(path: Path, payload: dict[str, Any]) -> None:
    if path.is_file():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    _replace_json(path, payload)


def _replace_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _replace_bytes(path, (json.dumps(payload, indent=2) + "\n").encode("utf-8"))


def _replace_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
