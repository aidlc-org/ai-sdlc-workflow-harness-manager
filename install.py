#!/usr/bin/env python3
"""Install and inspect the portable pipeline pack.

    python3 install.py                          # creates ./.pipeline
    python3 install.py --project /path/to/app   # creates <app>/.pipeline
    python3 install.py --user                   # creates ~/.pipeline
    python3 install.py --sync-kit               # refresh the bundled pack from this repo
    python3 install.py --uninstall --project
    python3 install.py --uninstall --user

The packaged ``pipeline-kit`` command provides the preferred subcommand-based
interface. The legacy flags above remain supported for existing users.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
MARKER_NAME = "install.json"
PACK_DIRS = (
    "loader",
    "skills",
    "agents",
    "rules",
    "workflows",
    "wiki",
    "commands",
    "adapters",
    "docs",
    "hooks",
    "eval",
)
PACK_FILES = ("README.md",)
SKIP_NAMES = {"state", "config.json", "install.json"}
IDE_SKILL_REL = {
    "cursor": Path(".cursor") / "skills" / "run-workflow" / "SKILL.md",
    "claude-code": Path(".claude") / "skills" / "run-workflow" / "SKILL.md",
    "github": Path(".github") / "skills" / "run-workflow" / "SKILL.md",
}


_SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:[-+][0-9A-Za-z.-]+)?$")
_VERSION_PARTS = ("major", "minor", "patch")
KIT_REPO_ENV = "PIPELINE_KIT_REPO"


def version() -> str:
    return (HERE / "VERSION").read_text(encoding="utf-8").strip()


def parse_semver(value: str) -> tuple[int, int, int]:
    match = _SEMVER.fullmatch(value.strip())
    if not match:
        raise ValueError(f"not a semver X.Y.Z: {value}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def bump_semver(current: str, part: str) -> str:
    if part not in _VERSION_PARTS:
        raise ValueError(f"bump part must be major, minor, or patch: {part}")
    major, minor, patch = parse_semver(current)
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def is_kit_source(root: Path) -> bool:
    return (
        (root / "VERSION").is_file()
        and (root / "install.py").is_file()
        and (root / "pyproject.toml").is_file()
        and (root / "kit" / "pipeline").is_dir()
    )


def is_kit_checkout(root: Path) -> bool:
    return is_kit_source(root) and (root / ".git").exists()


def _validated_checkout(value: str, origin: str) -> Path:
    root = Path(value).expanduser().resolve()
    if not is_kit_source(root):
        raise ValueError(f"{origin} is not a pipeline-kit source tree: {root}")
    if not (root / ".git").exists():
        raise ValueError(f"{origin} is not a git checkout: {root}")
    return root


def resolve_kit_checkout(explicit: str | None = None) -> Path:
    """Locate the kit's own git checkout. Never the installed copy or a customer project."""
    if explicit:
        return _validated_checkout(explicit, "--repo")
    configured = os.environ.get(KIT_REPO_ENV, "").strip()
    if configured:
        return _validated_checkout(configured, KIT_REPO_ENV)
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if is_kit_checkout(candidate):
            return candidate
    if is_kit_checkout(HERE):
        return HERE
    raise ValueError(
        "no pipeline-kit git checkout found. Release from the kit clone, "
        f"pass --repo PATH, or set {KIT_REPO_ENV}.\n"
        f"the running copy ({HERE}) is installed, not a checkout — "
        "bumping it would publish nothing."
    )


def _sync_website_package_version(pkg: Path, new: str) -> bool:
    text = pkg.read_text(encoding="utf-8")
    updated, count = re.subn(
        r'("version"\s*:\s*")([^"]*)(")',
        rf"\g<1>{new}\g<3>",
        text,
        count=1,
    )
    if count:
        pkg.write_text(updated, encoding="utf-8")
    return count > 0


def write_kit_version(root: Path, new: str) -> list[str]:
    parse_semver(new)
    changed: list[str] = []
    version_file = root / "VERSION"
    version_file.write_text(new + "\n", encoding="utf-8")
    changed.append("VERSION")
    website_pkg = root / "website" / "package.json"
    if website_pkg.is_file() and _sync_website_package_version(website_pkg, new):
        changed.append("website/package.json")
    return changed


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run git inside the kit checkout only — never the caller's project."""
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _git_failed(result: subprocess.CompletedProcess[str], action: str) -> int:
    detail = (result.stderr or result.stdout).strip()
    print(f"{action} failed: {detail}" if detail else f"{action} failed", file=sys.stderr)
    return 70


def commit_release(root: Path, new: str, paths: list[str], *, tag: bool) -> int:
    message = f"Release {new}"
    commit = _git(root, "commit", "-m", message, "--", *paths)
    if commit.returncode != 0:
        return _git_failed(commit, "git commit")
    print(f"committed in {root}: {message}")
    if not tag:
        return 0
    name = f"v{new}"
    if _git(root, "rev-parse", "-q", "--verify", f"refs/tags/{name}").returncode == 0:
        print(f"tag {name} already exists in {root}", file=sys.stderr)
        return 70
    tagged = _git(root, "tag", "-a", name, "-m", message)
    if tagged.returncode != 0:
        return _git_failed(tagged, "git tag")
    print(f"tagged {name}")
    return 0


def cmd_version(
    action: str = "show",
    value: str = "",
    *,
    repo: str = "",
    dry_run: bool = False,
    commit: bool = False,
    tag: bool = False,
) -> int:
    if action == "show":
        print(version())
        try:
            root = resolve_kit_checkout(repo or None)
        except ValueError:
            return 0
        in_checkout = (root / "VERSION").read_text(encoding="utf-8").strip()
        if in_checkout != version():
            print(f"checkout {root}: {in_checkout} (not the running copy)", file=sys.stderr)
        return 0
    try:
        root = resolve_kit_checkout(repo or None)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 64
    if tag and not commit:
        print("--tag requires --commit", file=sys.stderr)
        return 64
    current = (root / "VERSION").read_text(encoding="utf-8").strip()
    try:
        if action == "bump":
            part = (value or "patch").strip().lower()
            new = bump_semver(current, part)
        elif action == "set":
            if not value.strip():
                print("version set requires X.Y.Z", file=sys.stderr)
                return 64
            new = value.strip().lstrip("v")
            parse_semver(new)
        else:
            print(f"unknown version action: {action}", file=sys.stderr)
            return 64
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 64
    if new == current:
        print(f"already {current} in {root}")
        return 0
    if dry_run:
        print(f"would set {current} -> {new} in {root}")
        if commit:
            print(f"would commit 'Release {new}'" + (f" and tag v{new}" if tag else ""))
        return 0
    changed = write_kit_version(root, new)
    print(f"{root}: {current} -> {new}")
    print("updated: " + ", ".join(changed))
    if not commit:
        print(f"next: git -C {root} commit -m 'Release {new}' -- {' '.join(changed)}")
        print(f"next: git -C {root} tag -a v{new} -m 'Release {new}'")
        return 0
    code = commit_release(root, new, changed, tag=tag)
    if code == 0:
        print(f"next: git -C {root} push --follow-tags")
    return code


def bundled_pack() -> Path:
    return HERE / "kit" / "pipeline"


def live_pack() -> Path:
    """Optional working copy for maintainers (`./.pipeline`). Defaults to the bundle."""
    return HERE / ".pipeline"


def _is_pack_dir(path: Path) -> bool:
    return (path / "workflows").is_dir() and (path / "loader").is_dir()


def source_pack() -> Path:
    """Bundled kit first so install works even if this repo has no .pipeline."""
    bundled = bundled_pack()
    if _is_pack_dir(bundled):
        return bundled
    live = live_pack()
    if _is_pack_dir(live):
        return live
    raise FileNotFoundError(
        "pipeline pack source is missing. Run: python3 install.py --sync-kit"
    )


def _chmod_script(path: Path) -> None:
    if path.suffix in {".py", ".sh"}:
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _copy_file(src: Path, dest: Path, root: Path, copied: list[str]) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    _chmod_script(dest)
    copied.append(str(dest.relative_to(root)))


def _copy_tree(src: Path, dest: Path, root: Path, copied: list[str]) -> None:
    if not src.is_dir():
        return
    for item in sorted(src.rglob("*")):
        if item.is_dir():
            continue
        rel = item.relative_to(src)
        if any(part in SKIP_NAMES or part == "__pycache__" for part in rel.parts):
            continue
        _copy_file(item, dest / rel, root, copied)


GUARDRAIL_NEEDLE = ".pipeline/hooks/"
OBS_NEEDLE = ".pipeline/hooks/obs/"


def _hook_command_text(entry: Any) -> str:
    if not isinstance(entry, dict):
        return ""
    parts: list[str] = []
    for key in ("command", "bash", "powershell"):
        value = entry.get(key)
        if isinstance(value, str):
            parts.append(value)
    nested = entry.get("hooks")
    if isinstance(nested, list):
        parts.extend(_hook_command_text(item) for item in nested)
    return " ".join(parts)


PYTHON_PLACEHOLDER = "{{PYTHON}}"


def detect_python() -> str:
    """Interpreter token for hook command strings.

    Hook configs are plain command strings run by the harness, so they cannot
    use `sys.executable` at runtime. `python3` is absent on most Windows boxes
    (and is a non-functional Microsoft Store stub when the alias is enabled),
    while many Linux images ship only `python3`. So probe, and fall back to the
    absolute path of the interpreter running this installer.
    """
    marker = "pipeline-kit-ok"
    probe = "import sys; sys.stdout.write('" + marker + "')"
    candidates = ["python", "python3", "py -3"] if os.name == "nt" else ["python3", "python"]
    for candidate in candidates:
        try:
            proc = subprocess.run(
                candidate.split() + ["-c", probe],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if proc.returncode == 0 and marker in (proc.stdout or ""):
            return candidate
    fallback = sys.executable or "python3"
    return '"%s"' % fallback if " " in fallback else fallback


def _substitute_python(node: Any, interpreter: str) -> Any:
    """Replace the interpreter placeholder everywhere in a hook fragment."""
    if isinstance(node, str):
        return node.replace(PYTHON_PLACEHOLDER, interpreter)
    if isinstance(node, list):
        return [_substitute_python(item, interpreter) for item in node]
    if isinstance(node, dict):
        return {key: _substitute_python(value, interpreter) for key, value in node.items()}
    return node


def _is_guardrail_entry(entry: Any) -> bool:
    text = _hook_command_text(entry)
    return GUARDRAIL_NEEDLE in text and OBS_NEEDLE not in text


def _append_guardrail_entries(bucket: list[Any], entries: list[Any]) -> int:
    added = 0
    seen = {_hook_command_text(item) for item in bucket}
    for entry in entries:
        command = _hook_command_text(entry)
        if command and command in seen:
            continue
        bucket.append(entry)
        if command:
            seen.add(command)
        added += 1
    return added


def _merge_hook_object(existing: dict[str, Any], fragment: dict[str, Any]) -> int:
    hooks = existing.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("hooks must be an object")
    added = 0
    incoming = fragment.get("hooks") if isinstance(fragment.get("hooks"), dict) else {}
    for event, entries in incoming.items():
        if not isinstance(entries, list):
            continue
        bucket = hooks.setdefault(event, [])
        if not isinstance(bucket, list):
            raise ValueError(f"hooks.{event} must be an array")
        added += _append_guardrail_entries(bucket, entries)
    return added


def _strip_guardrail_entries(data: dict[str, Any]) -> dict[str, Any]:
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return data
    for event, entries in list(hooks.items()):
        if not isinstance(entries, list):
            continue
        kept = [item for item in entries if not _is_guardrail_entry(item)]
        if kept:
            hooks[event] = kept
        else:
            del hooks[event]
    return data


def merge_guardrail_hooks(*, ide: str, ide_root: Path, pack: Path) -> int:
    """Append policy-hook commands. Does not replace existing or obs entries."""
    if ide == "cursor":
        fragment_path = pack / "hooks" / "cursor.hooks.json"
        dest = ide_root / ".cursor" / "hooks.json"
    elif ide == "claude-code":
        fragment_path = pack / "hooks" / "claude.settings.json"
        dest = ide_root / ".claude" / "settings.json"
    elif ide == "github":
        fragment_path = pack / "hooks" / "copilot.hooks.json"
        dest = ide_root / ".github" / "hooks" / "pipeline-guardrails.json"
    else:
        return 0
    if not fragment_path.is_file():
        return 0
    fragment = json.loads(fragment_path.read_text(encoding="utf-8"))
    if not isinstance(fragment, dict):
        return 0
    fragment = _substitute_python(fragment, detect_python())
    if ide == "github":
        # Copilot discovers .github/hooks/*.json; this file is ours alone, so
        # write it whole rather than merging into someone else's config.
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(fragment, indent=2) + "\n", encoding="utf-8")
        return sum(len(v) for v in fragment.get("hooks", {}).values() if isinstance(v, list))
    existing: dict[str, Any] = {"version": 1, "hooks": {}} if ide == "cursor" else {}
    if dest.is_file():
        loaded = json.loads(dest.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            existing = loaded
            existing.setdefault("hooks", {})
            if ide == "cursor":
                existing.setdefault("version", 1)
    # Drop our own previous entries first. Without this, an upgrade leaves a stale
    # command (an older interpreter, or a POSIX env prefix) registered beside the
    # new one, so the hook runs twice and one invocation fails. On Copilot, whose
    # preToolUse is fail-closed, that failure denies the tool call outright.
    # Entries owned by the user or by obs do not match the needle and are kept.
    _strip_guardrail_entries(existing)
    existing.setdefault("hooks", {})
    added = _merge_hook_object(existing, fragment)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    return added


def strip_guardrail_hooks(*, ide_root: Path) -> None:
    owned = ide_root / ".github" / "hooks" / "pipeline-guardrails.json"
    if owned.is_file():
        owned.unlink()
    for rel in (Path(".cursor") / "hooks.json", Path(".claude") / "settings.json"):
        path = ide_root / rel
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        path.write_text(json.dumps(_strip_guardrail_entries(data), indent=2) + "\n", encoding="utf-8")


def generic_config(source: dict[str, Any]) -> dict[str, Any]:
    data = json.loads(json.dumps(source))
    data["_readme"] = (
        "Project-specific pipeline config. Add verify.rules and deploy.targets "
        "for this repo. Do not put secrets, hosts, or tracker site URLs in other pack files."
    )
    verify = data.get("verify")
    if isinstance(verify, dict):
        verify["rules"] = []
        verify["_note"] = "Add path-substring reminders for this repo after install."
    deploy = data.get("deploy")
    if isinstance(deploy, dict):
        deploy["target"] = "auto"
        deploy["targets"] = ["auto"]
        deploy["_note"] = "Set targets this repo's deploy runbook understands."
    return data


def load_source_config(pack: Path) -> dict[str, Any]:
    path = pack / "config.json"
    if path.is_file():
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            return loaded
    template = HERE / "kit" / "config.template.json"
    if template.is_file():
        loaded = json.loads(template.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            return loaded
    return {"version": 1, "workflows": {}}


def merge_config(dest: Path, incoming: dict[str, Any]) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file():
        loaded = json.loads(dest.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            for key, value in incoming.items():
                if key not in loaded:
                    loaded[key] = value
            src_wf = incoming.get("workflows")
            dest_wf = loaded.setdefault("workflows", {})
            if isinstance(src_wf, dict) and isinstance(dest_wf, dict):
                for name, cfg in src_wf.items():
                    dest_wf.setdefault(name, cfg)
            dest.write_text(json.dumps(loaded, indent=2) + "\n", encoding="utf-8")
            return "merged"
    dest.write_text(json.dumps(incoming, indent=2) + "\n", encoding="utf-8")
    return "wrote"


def adapter_skill(pack: Path, ide: str) -> Path | None:
    candidate = pack / "adapters" / ide / "skills" / "run-workflow" / "SKILL.md"
    if candidate.is_file():
        return candidate
    fallback = pack / "adapters" / "cursor" / "skills" / "run-workflow" / "SKILL.md"
    return fallback if fallback.is_file() else None


def write_agent_stubs(agents_src: Path, dest_dir: Path, root: Path, copied: list[str]) -> None:
    if not agents_src.is_dir():
        return
    dest_dir.mkdir(parents=True, exist_ok=True)
    for src in sorted(agents_src.glob("*.md")):
        name = src.stem
        dest = dest_dir / src.name
        dest.write_text(
            (
                f"---\nname: {name}\n"
                f"description: Thin Cursor stub. Read .pipeline/agents/{src.name}.\n"
                "---\n\n"
                f"# {name}\n\n"
                f"Read and follow `.pipeline/agents/{src.name}`. "
                "This file exists only so Cursor can register the Task type.\n"
            ),
            encoding="utf-8",
        )
        copied.append(str(dest.relative_to(root)))


def _copy_tree_plain(src: Path, dest: Path) -> None:
    if not src.is_dir():
        return
    dest.mkdir(parents=True, exist_ok=True)
    for item in sorted(src.rglob("*")):
        if not item.is_file():
            continue
        rel = item.relative_to(src)
        if any(part in SKIP_NAMES or part == "__pycache__" for part in rel.parts):
            continue
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, out)
        _chmod_script(out)


def sync_kit() -> int:
    """Copy this repo's live .pipeline into the bundled kit (generic config)."""
    live = live_pack()
    if not _is_pack_dir(live):
        print(f"no live pack at {live}", file=sys.stderr)
        return 1
    dest = bundled_pack()
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for name in PACK_DIRS:
        _copy_tree_plain(live / name, dest / name)
    for name in PACK_FILES:
        src = live / name
        if src.is_file():
            shutil.copy2(src, dest / name)
    cfg = generic_config(load_source_config(live))
    (dest / "config.json").write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    guide = HERE / "CUSTOMER-GUIDE.md"
    if guide.is_file():
        docs = dest / "docs"
        docs.mkdir(parents=True, exist_ok=True)
        shutil.copy2(guide, docs / "CUSTOMER-GUIDE.md")
    obs_guide = HERE / "OBSERVABILITY.md"
    if obs_guide.is_file():
        docs = dest / "docs"
        docs.mkdir(parents=True, exist_ok=True)
        shutil.copy2(obs_guide, docs / "OBSERVABILITY.md")
    print(f"synced kit ← {live}", file=sys.stderr)
    print(f"wrote {dest}", file=sys.stderr)
    return 0


def write_marker(pack_dest: Path, scope: str, files: list[str], mode: str = "kit") -> None:
    unique: list[str] = []
    for name in files:
        if name not in unique:
            unique.append(name)
    (pack_dest / MARKER_NAME).write_text(
        json.dumps(
            {
                "name": "pipeline-kit",
                "version": version(),
                "scope": scope,
                "mode": mode or "kit",
                "files": unique,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def read_install_mode(pack: Path) -> str:
    marker = pack / MARKER_NAME
    if not marker.is_file():
        return "kit"
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "kit"
    if isinstance(data, dict):
        return str(data.get("mode") or "kit")
    return "kit"


def adapter_orchestrator_skill(pack: Path, ide: str) -> Path | None:
    candidate = pack / "adapters" / ide / "skills" / "run-orchestrator" / "SKILL.md"
    if candidate.is_file():
        return candidate
    fallback = pack / "adapters" / "cursor" / "skills" / "run-orchestrator" / "SKILL.md"
    return fallback if fallback.is_file() else None


def install(
    *,
    scope: str,
    target: Path,
    ide: str,
    agent_stubs: bool,
    dry_run: bool,
    home: Path | None = None,
    mode: str = "kit",
) -> int:
    pack_src = source_pack()
    home_dir = home or Path.home()
    if scope == "user":
        pack_dest = home_dir / ".pipeline"
        ide_root = home_dir
        marker_root = home_dir
    else:
        pack_dest = target / ".pipeline"
        ide_root = target
        marker_root = target
    print(f"kit:     {HERE} (v{version()})", file=sys.stderr)
    print(f"source:  {pack_src}", file=sys.stderr)
    print(f"target:  {pack_dest} ({scope})", file=sys.stderr)
    if dry_run:
        print("[dry run] would copy pack, merge config.json, write install.json", file=sys.stderr)
        return 0

    mode = (mode or "kit").strip().lower()
    if mode not in {"kit", "orchestrator"}:
        print(f"unknown mode: {mode}", file=sys.stderr)
        return 64
    pack_dest.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    # hooks/obs collectors stay on disk so a leftover .cursor/hooks.json
    # from `obs install` does not fail when briefs are not copied.
    dirs = ("wiki", "hooks") if mode == "orchestrator" else PACK_DIRS
    for name in dirs:
        _copy_tree(pack_src / name, pack_dest / name, marker_root, copied)
    for name in PACK_FILES:
        src = pack_src / name
        if src.is_file():
            dest_file = pack_dest / name
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest_file)
            copied.append(str(dest_file.relative_to(marker_root)))

    guide = HERE / "CUSTOMER-GUIDE.md"
    if guide.is_file():
        dest_guide = pack_dest / "docs" / "CUSTOMER-GUIDE.md"
        dest_guide.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(guide, dest_guide)
        copied.append(str(dest_guide.relative_to(marker_root)))
    obs_guide = HERE / "OBSERVABILITY.md"
    if obs_guide.is_file():
        dest_obs = pack_dest / "docs" / "OBSERVABILITY.md"
        dest_obs.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(obs_guide, dest_obs)
        copied.append(str(dest_obs.relative_to(marker_root)))

    status = merge_config(pack_dest / "config.json", generic_config(load_source_config(pack_src)))
    print(f"config.json: {status}", file=sys.stderr)
    if ".pipeline/config.json" not in copied:
        copied.append(".pipeline/config.json")

    if ide != "none":
        if mode == "orchestrator":
            skill_src = adapter_orchestrator_skill(pack_src, ide) or adapter_skill(pack_src, ide)
        else:
            skill_src = adapter_skill(pack_src, ide) or adapter_skill(pack_dest, ide)
        skill_rel = IDE_SKILL_REL.get(ide)
        if skill_src and skill_rel:
            if scope == "user" and ide in {"cursor", "claude-code"}:
                skill_dest = home_dir / skill_rel
                _copy_file(skill_src, skill_dest, home_dir, copied)
            elif scope == "project":
                _copy_file(skill_src, ide_root / skill_rel, target, copied)
            else:
                print(f"note: --user --ide {ide} writes no IDE adapter (use cursor, claude-code, or --project)", file=sys.stderr)
        if scope == "project":
            added = merge_guardrail_hooks(ide=ide, ide_root=ide_root, pack=pack_dest)
            if added:
                print(f"policy hooks: merged {added} entries ({ide})", file=sys.stderr)

    if agent_stubs and mode != "orchestrator":
        stubs_dir = (
            (home_dir / ".cursor" / "agents")
            if scope == "user"
            else (target / ".cursor" / "agents")
        )
        stubs_root = home_dir if scope == "user" else target
        write_agent_stubs(pack_src / "agents", stubs_dir, stubs_root, copied)

    marker_pack = pack_dest
    write_marker(marker_pack, scope, copied, mode=mode)
    copied.append(".pipeline/install.json" if scope == "project" else MARKER_NAME)
    print(f"installed {version()}: {len(copied)} files ({mode})", file=sys.stderr)
    if mode == "orchestrator":
        (pack_dest / "state" / "runs").mkdir(parents=True, exist_ok=True)
        print("Done. Orchestrator: pipeline-kit run --slug <slug> --workflow feature-development", file=sys.stderr)
    else:
        print(
            f"Done. Loader: {detect_python()} {pack_dest / 'loader' / 'load_workflow.py'}",
            file=sys.stderr,
        )
    return 0


def uninstall(*, scope: str, target: Path, home: Path | None = None) -> int:
    home_dir = home or Path.home()
    pack = (home_dir / ".pipeline") if scope == "user" else (target / ".pipeline")
    marker = pack / MARKER_NAME
    if not marker.is_file():
        print(f"no pipeline-kit install at {pack} ({MARKER_NAME} missing)", file=sys.stderr)
        return 1
    meta = json.loads(marker.read_text(encoding="utf-8"))
    root = home_dir if scope == "user" else target
    removed = 0
    for rel in meta.get("files") or []:
        path = root / rel
        if path.is_file():
            path.unlink()
            removed += 1
    if marker.is_file():
        marker.unlink()
        removed += 1
    strip_guardrail_hooks(ide_root=root)
    print(f"removed {removed} kit files; features/ and local config edits were left.", file=sys.stderr)
    return 0


def resolved_pack(*, target: Path, user: bool, home: Path | None = None) -> Path:
    home_dir = home or Path.home()
    if user:
        return home_dir / ".pipeline"
    project_pack = target / ".pipeline"
    return project_pack if project_pack.is_dir() else home_dir / ".pipeline"


def _ensure_pkg_path() -> None:
    root = str(HERE)
    if root not in sys.path:
        sys.path.insert(0, root)
    try:
        from layout import install_source_importers
    except ImportError:
        return
    install_source_importers()


def _license_cli(args: argparse.Namespace) -> int:
    _ensure_pkg_path()
    from pipeline_kit.license import cmd_activate, cmd_issue, cmd_status

    home = Path(args.home).expanduser().resolve() if getattr(args, "home", "") else None
    if args.license_command == "issue":
        try:
            resolve_kit_checkout(args.repo or None)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 64
        return cmd_issue(org=args.org, expires=args.expires, features=args.features)
    if args.license_command == "activate":
        return cmd_activate(home=home)
    if args.license_command == "status":
        return cmd_status(home=home)
    print(f"unknown license command: {args.license_command}", file=sys.stderr)
    return 2


def _require_license(feature: str) -> int:
    _ensure_pkg_path()
    try:
        from pipeline_kit.license import require
    except ImportError:
        print(
            f"license: {feature} needs pipeline-kit license activate",
            file=sys.stderr,
        )
        return 73
    return int(require(feature))


def _feature_for_saved_run(project: Path, slug: str) -> str:
    from pipeline_kit.license import feature_for_workflow

    paths = [
        project / ".pipeline" / "state" / "runs" / f"{slug}.json",
    ]
    try:
        from pipeline_kit.paths import feature_dir

        paths.append(feature_dir(project, slug) / "pipeline-state.json")
    except Exception:
        paths.append(project / "features" / slug / "pipeline-state.json")
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        workflow = data.get("workflow") if isinstance(data, dict) else None
        if isinstance(workflow, str) and workflow.strip():
            return feature_for_workflow(workflow)
    return "orchestrator"


def _knowledge_commands():
    _ensure_pkg_path()
    from knowledge.commands import (  # noqa: WPS433
        cmd_extract,
        cmd_init,
        cmd_playwright,
        cmd_promote,
        cmd_promote_feature,
        cmd_render,
        cmd_status,
        cmd_validate,
    )

    return (
        cmd_extract,
        cmd_init,
        cmd_playwright,
        cmd_promote,
        cmd_promote_feature,
        cmd_render,
        cmd_status,
        cmd_validate,
    )


def _plugin_commands():
    _ensure_pkg_path()
    from pipeline_plugins.commands import (  # noqa: WPS433
        cmd_install,
        cmd_list,
        cmd_status,
        cmd_uninstall,
    )

    return cmd_install, cmd_list, cmd_status, cmd_uninstall


def _feature_commands():
    _ensure_pkg_path()
    from pipeline_features.commands import (  # noqa: WPS433
        cmd_disable,
        cmd_enable,
        cmd_list,
        cmd_status,
    )

    return cmd_disable, cmd_enable, cmd_list, cmd_status


def _obs_commands():
    _ensure_pkg_path()
    from pipeline_observability.commands import (  # noqa: WPS433
        cmd_flush,
        cmd_install,
        cmd_report,
        cmd_status,
        cmd_uninstall,
    )

    return cmd_flush, cmd_install, cmd_report, cmd_status, cmd_uninstall


def _memory_pkg_path() -> None:
    _ensure_pkg_path()
    mem = HERE / "packages" / "pipeline-kit-memory"
    if mem.is_dir() and str(mem) not in sys.path:
        sys.path.insert(0, str(mem))


def _memory_commands():
    _memory_pkg_path()
    try:
        from pipeline_memory.commands import (  # noqa: WPS433
            cmd_doctor,
            cmd_import_local,
            cmd_index,
            cmd_link,
            cmd_mcp,
            cmd_search,
            cmd_status,
            cmd_unlink,
        )
    except ImportError as exc:
        raise ImportError(
            'pipeline-kit-memory is not installed. Run: pip install -e ".[memory]" '
            "or add packages/pipeline-kit-memory to PYTHONPATH"
        ) from exc
    return {
        "link": cmd_link,
        "unlink": cmd_unlink,
        "status": cmd_status,
        "doctor": cmd_doctor,
        "index": cmd_index,
        "search": cmd_search,
        "mcp": cmd_mcp,
        "import-local": cmd_import_local,
    }


def doctor(
    *,
    target: Path,
    user: bool,
    ide: str | None,
    home: Path | None = None,
) -> int:
    home_dir = home or Path.home()
    pack = resolved_pack(target=target, user=user, home=home_dir)
    scope = "user" if pack == home_dir / ".pipeline" else "project"
    mode = read_install_mode(pack)
    checks = {
        f"Python {sys.version_info.major}.{sys.version_info.minor} (3.11+)": sys.version_info
        >= (3, 11),
        f"{scope} pack: {pack}": pack.is_dir(),
        "install marker": (pack / MARKER_NAME).is_file(),
        "configuration": (pack / "config.json").is_file(),
    }
    if mode == "orchestrator":
        checks["orchestrator mode"] = True
        checks["CURSOR_API_KEY"] = bool(__import__("os").environ.get("CURSOR_API_KEY", "").strip())
        print(f"info  mode: orchestrator (v{version()})")
    else:
        checks["workflow loader"] = (pack / "loader" / "load_workflow.py").is_file()
    if ide and ide != "none":
        root = home_dir if scope == "user" else target
        skill_rel = IDE_SKILL_REL.get(ide)
        if skill_rel:
            checks[f"{ide} adapter"] = (root / skill_rel).is_file()
    _ensure_pkg_path()
    from knowledge.doctor import graphify_doctor_checks
    from pipeline_plugins.archify import archify_doctor_checks
    from pipeline_observability.commands import obs_doctor_checks

    info_lines, required = graphify_doctor_checks(target)
    arch_info, arch_required = archify_doctor_checks(target)
    obs_info, obs_required = obs_doctor_checks(pack)
    info_lines.extend(arch_info)
    info_lines.extend(obs_info)
    required.update(arch_required)
    required.update(obs_required)
    try:
        _memory_pkg_path()
        from pipeline_memory.resolve import load_config as _mem_load
        from pipeline_memory.resolve import memory_enabled as _mem_on
        from pipeline_memory.resolve import resolve_memory_root as _mem_root

        mcfg = _mem_load(target)
        if _mem_on(mcfg):
            root = _mem_root(target, mcfg)
            info_lines.append(f"memory: enabled → {root}")
            required["memory root"] = bool(root and root.is_dir())
        else:
            info_lines.append("memory: disabled (default local features/)")
    except ImportError:
        info_lines.append("memory: package not installed (optional)")
    for line in info_lines:
        print(f"info  {line}")
    checks.update(required)
    for label, passed in checks.items():
        print(f"{'ok' if passed else 'missing'}  {label}")
    if all(checks.values()):
        print(f"pipeline-kit {version()} is ready")
        return 0
    print("pipeline-kit setup is incomplete", file=sys.stderr)
    return 1


def list_workflows(*, target: Path, user: bool, home: Path | None = None, scaffold: str = "") -> int:
    pack = resolved_pack(target=target, user=user, home=home)
    if scaffold:
        _ensure_pkg_path()
        from pipeline_orchestrator.scaffold import scaffold_workflow

        project = (home or Path.home()) if user else target
        return scaffold_workflow(project, scaffold)
    if read_install_mode(pack) == "orchestrator":
        _ensure_pkg_path()
        from pipeline_orchestrator.cli import cmd_list_orchestrator

        project = (home or Path.home()) if user else target
        return cmd_list_orchestrator(project)
    workflows_dir = pack / "workflows"
    if not workflows_dir.is_dir():
        print(f"no pipeline workflows found at {workflows_dir}", file=sys.stderr)
        return 1
    found = 0
    for path in sorted(workflows_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"invalid workflow {path.name}: {exc}", file=sys.stderr)
            return 1
        name = data.get("name", path.stem) if isinstance(data, dict) else path.stem
        print(name)
        found += 1
    if not found:
        print(f"no pipeline workflows found at {workflows_dir}", file=sys.stderr)
        return 1
    return 0


def _add_install_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ide", choices=("cursor", "claude-code", "github", "none"), default="cursor")
    parser.add_argument("--agent-stubs", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--mode",
        choices=("kit", "orchestrator"),
        default=None,
        help="kit copies the markdown pack (default). orchestrator uses the wheel engine.",
    )
    parser.add_argument("--home", default="", help=argparse.SUPPRESS)


_LAST_INVOCATION: dict[str, object] = {}


def cli_main(argv: list[str] | None = None) -> int:
    """Run a command, then (best effort) report local changes to a connected portal."""
    _LAST_INVOCATION.clear()
    code = _cli_run(argv)
    args = _LAST_INVOCATION.get("args")
    if code == 0 and args is not None and not getattr(args, "user", False) and args.command not in {"setup", "portal"}:
        sub = next((v for k, v in vars(args).items() if k.endswith("_command") and k != "command"), None)
        try:
            _ensure_pkg_path()
            from pipeline_kit import portal_link

            project = Path(getattr(args, "project", ".")).expanduser().resolve()
            portal_link.push_after(args.command, sub if isinstance(sub, str) else None, project)
        except Exception:  # noqa: BLE001 - never let reporting change a command's result
            pass
    return code


def _cli_run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pipeline-kit",
        description="Install and inspect portable AI delivery workflows.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {version()}")
    commands = parser.add_subparsers(dest="command", required=True)

    init_parser = commands.add_parser("init", help="install or update the pack in a project")
    init_parser.add_argument("project", nargs="?", default=".")
    _add_install_options(init_parser)

    setup_parser = commands.add_parser("setup", help="install or update the user-level pack")
    _add_install_options(setup_parser)

    update_parser = commands.add_parser("update", help="refresh an existing project or user pack")
    update_parser.add_argument("project", nargs="?", default=".")
    update_parser.add_argument("--user", action="store_true")
    _add_install_options(update_parser)

    uninstall_parser = commands.add_parser("uninstall", help="remove files managed by pipeline-kit")
    uninstall_parser.add_argument("project", nargs="?", default=".")
    uninstall_parser.add_argument("--user", action="store_true")
    uninstall_parser.add_argument("--home", default="", help=argparse.SUPPRESS)

    doctor_parser = commands.add_parser("doctor", help="verify the active pipeline-kit setup")
    doctor_parser.add_argument("project", nargs="?", default=".")
    doctor_parser.add_argument("--user", action="store_true")
    doctor_parser.add_argument("--ide", choices=("cursor", "claude-code", "github", "none"))
    doctor_parser.add_argument("--home", default="", help=argparse.SUPPRESS)

    workflows_parser = commands.add_parser("workflows", help="list workflows in the active pack")
    workflows_parser.add_argument("project", nargs="?", default=".")
    workflows_parser.add_argument("--user", action="store_true")
    workflows_parser.add_argument(
        "--scaffold",
        default="",
        help="create an associate workflow (orchestrator mode only; does not change kit mode)",
    )
    workflows_parser.add_argument("--home", default="", help=argparse.SUPPRESS)

    scan_parser = commands.add_parser(
        "scan",
        help="assess a repo from its Graphify graph (pipeline-kit-assess, license: assess)",
    )
    scan_parser.add_argument("project", nargs="?", default=".")
    scan_parser.add_argument(
        "--out",
        default="",
        help="directory for the assessment (default: features/assessment)",
    )
    scan_parser.add_argument("--yes", action="store_true", help="accept setup prompts in a terminal")
    scan_parser.add_argument(
        "--no-bootstrap",
        action="store_true",
        help="print setup steps and exit instead of installing Graphify or the pack",
    )
    scan_parser.add_argument("--json", action="store_true", help="print assessment.json on stdout")
    scan_parser.add_argument("--apply", default="", help="comma-separated recommendation ids to apply")
    scan_parser.add_argument("--dry-run", action="store_true", help="show apply changes without writing them")

    run_parser = commands.add_parser("run", help="run a workflow with the code orchestrator")
    run_parser.add_argument("project", nargs="?", default=".")
    run_parser.add_argument("--slug", required=True)
    run_parser.add_argument("--workflow", default="feature-development")
    run_parser.add_argument("--change-class", default="")
    run_parser.add_argument("--runner", default="cursor", choices=("cursor", "fake"))
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.add_argument(
        "--request",
        default="",
        help="verbatim user ask to pass into every step as USER_REQUEST",
    )
    run_parser.add_argument(
        "--request-file",
        default="",
        help="read USER_REQUEST from this file (default: features/<slug>/request.md)",
    )

    resume_parser = commands.add_parser("resume", help="continue a paused orchestrator run")
    resume_parser.add_argument("project", nargs="?", default=".")
    resume_parser.add_argument("--slug", required=True)
    resume_parser.add_argument("--runner", default="cursor", choices=("cursor", "fake"))

    approve_parser = commands.add_parser("approve", help="approve an orchestrator sign-off gate")
    approve_parser.add_argument("project", nargs="?", default=".")
    approve_parser.add_argument("--slug", required=True)
    approve_parser.add_argument("--gate", required=True)
    approve_parser.add_argument("--note", default="none")

    status_parser = commands.add_parser("status", help="print orchestrator run state")
    status_parser.add_argument("project", nargs="?", default=".")
    status_parser.add_argument("--slug", required=True)

    verify_parser = commands.add_parser("verify", help="report install mode and sealed graph")
    verify_parser.add_argument("project", nargs="?", default=".")

    export_parser = commands.add_parser("export-briefs", help="write a non-executing brief reference copy")
    export_parser.add_argument("project", nargs="?", default=".")

    knowledge_parser = commands.add_parser(
        "knowledge",
        help="init QA overlay and run official Graphify extract",
    )
    knowledge_commands = knowledge_parser.add_subparsers(dest="knowledge_command", required=True)
    k_init = knowledge_commands.add_parser("init", help="create test-knowledge overlay (opt-in)")
    k_init.add_argument("project", nargs="?", default=".")
    k_init.add_argument(
        "--ide",
        choices=("cursor", "claude-code", "github", "none"),
        default="cursor",
    )
    k_init.add_argument(
        "--register-skill",
        action="store_true",
        help="run official graphify install for this IDE",
    )
    k_extract = knowledge_commands.add_parser(
        "extract",
        help="run graphify extract --code-only (no homemade graph)",
    )
    k_extract.add_argument("project", nargs="?", default=".")
    k_extract.add_argument("--force", action="store_true")
    k_extract.add_argument(
        "--update",
        action="store_true",
        help="incremental graphify update (no model) instead of a full extract",
    )
    k_status = knowledge_commands.add_parser("status", help="Graphify CLI and graphify-out status")
    k_status.add_argument("project", nargs="?", default=".")
    k_validate = knowledge_commands.add_parser(
        "validate",
        help="validate a bootstrap candidate run (after human review)",
    )
    k_validate.add_argument("project", nargs="?", default=".")
    k_validate.add_argument("--run", required=True, dest="run_id")
    k_promote = knowledge_commands.add_parser(
        "promote",
        help="atomically promote a reviewed candidate run",
    )
    k_promote.add_argument("project", nargs="?", default=".")
    k_promote.add_argument("--run", required=True, dest="run_id")
    k_render = knowledge_commands.add_parser(
        "render",
        help="write feature Markdown views from cases.json",
    )
    k_render.add_argument("project", nargs="?", default=".")
    k_render.add_argument("--slug", required=True)
    k_playwright = knowledge_commands.add_parser(
        "playwright",
        help="write automation-tests specs from cases.json + locators.json",
    )
    k_playwright.add_argument("project", nargs="?", default=".")
    k_playwright.add_argument("--slug", required=True)
    k_promote_feature = knowledge_commands.add_parser(
        "promote-feature",
        help="merge planned feature overlay nodes into test-knowledge as inferred",
    )
    k_promote_feature.add_argument("project", nargs="?", default=".")
    k_promote_feature.add_argument("--slug", required=True)

    plugins_parser = commands.add_parser(
        "plugins",
        help="list, install, status, or uninstall optional Graphify/Archify plugins",
    )
    plugins_commands = plugins_parser.add_subparsers(dest="plugins_command", required=True)
    plugins_commands.add_parser("list", help="list optional plugins")
    p_install = plugins_commands.add_parser(
        "install",
        help="register an optional plugin (does not vendor Graphify or Archify)",
    )
    p_install.add_argument("name", choices=("graphify", "archify"))
    p_install.add_argument("project", nargs="?", default=".")
    p_install.add_argument(
        "--ide",
        choices=("cursor", "claude-code", "github", "none"),
        default="cursor",
    )
    p_install.add_argument("--scope", choices=("project", "user"), default="project")
    p_install.add_argument(
        "--hook",
        action="store_true",
        help="after Graphify registers, install its commit hook",
    )
    p_install.add_argument("--home", default="", help=argparse.SUPPRESS)
    p_status = plugins_commands.add_parser(
        "status",
        help="Graphify CLI / Archify skill status",
    )
    p_status.add_argument("project", nargs="?", default=".")
    p_status.add_argument("--plugin", choices=("graphify", "archify"))
    p_status.add_argument(
        "--ide",
        choices=("cursor", "claude-code", "github", "none"),
        default="cursor",
    )
    p_status.add_argument("--scope", choices=("project", "user"), default="project")
    p_status.add_argument("--home", default="", help=argparse.SUPPRESS)
    p_uninstall = plugins_commands.add_parser(
        "uninstall",
        help="remove a plugin skill; generated graphs/diagrams stay unless --purge",
    )
    p_uninstall.add_argument("name", choices=("graphify", "archify"))
    p_uninstall.add_argument("project", nargs="?", default=".")
    p_uninstall.add_argument(
        "--ide",
        choices=("cursor", "claude-code", "github", "none"),
        default="cursor",
    )
    p_uninstall.add_argument("--scope", choices=("project", "user"), default="project")
    p_uninstall.add_argument(
        "--purge",
        action="store_true",
        help="Graphify only: also delete graphify-out/. Archify never deletes diagrams.",
    )
    p_uninstall.add_argument("--home", default="", help=argparse.SUPPRESS)

    features_parser = commands.add_parser(
        "features",
        help="list or toggle kit capabilities (same keys as config.json)",
    )
    features_commands = features_parser.add_subparsers(dest="features_command", required=True)
    features_commands.add_parser("list", help="named capabilities")
    f_status = features_commands.add_parser("status", help="on/off for this project")
    f_status.add_argument("project", nargs="?", default=".")
    f_enable = features_commands.add_parser("enable", help="turn a capability on")
    f_enable.add_argument(
        "name",
        choices=(
            "test-design",
            "playwright",
            "telemetry",
            "tester",
            "archify",
            "jira-intake",
            "agent-observability",
        ),
    )
    f_enable.add_argument("project", nargs="?", default=".")
    f_disable = features_commands.add_parser("disable", help="turn a capability off")
    f_disable.add_argument(
        "name",
        choices=(
            "test-design",
            "playwright",
            "telemetry",
            "tester",
            "archify",
            "jira-intake",
            "agent-observability",
        ),
    )
    f_disable.add_argument("project", nargs="?", default=".")

    obs_parser = commands.add_parser(
        "obs",
        help="install or inspect agent-run observability (not customer telemetry-agent)",
    )
    obs_commands = obs_parser.add_subparsers(dest="obs_command", required=True)
    o_install = obs_commands.add_parser("install", help="merge fail-open hooks; never replaces existing entries")
    o_install.add_argument("project", nargs="?", default=".")
    o_install.add_argument("--ide", choices=("cursor", "claude-code", "github"), default="cursor")
    o_install.add_argument("--adapter", choices=("langfuse", "datadog", "otlp"), default="langfuse")
    o_uninstall = obs_commands.add_parser("uninstall", help="remove only obs hook entries")
    o_uninstall.add_argument("project", nargs="?", default=".")
    o_uninstall.add_argument("--ide", choices=("cursor", "claude-code", "github"), default="cursor")
    o_status = obs_commands.add_parser("status", help="enabled flag, adapter, ledger size")
    o_status.add_argument("project", nargs="?", default=".")
    o_flush = obs_commands.add_parser("flush", help="score new ledger rows and ship to the adapter")
    o_flush.add_argument("project", nargs="?", default=".")
    o_report = obs_commands.add_parser("report", help="print local scores without network")
    o_report.add_argument("project", nargs="?", default=".")

    eval_parser = commands.add_parser(
        "eval",
        help="evaluation harness (Langfuse score configs + judge setup)",
    )
    eval_commands = eval_parser.add_subparsers(dest="eval_command", required=True)
    e_judges = eval_commands.add_parser("judges", help="LLM-as-judge setup helpers")
    e_judges_commands = e_judges.add_subparsers(dest="judges_command", required=True)
    e_sync = e_judges_commands.add_parser(
        "sync", help="create Langfuse score configs and print evaluator/rule UI steps"
    )
    e_sync.add_argument("project", nargs="?", default=".")

    memory_parser = commands.add_parser(
        "memory",
        help="link external artifact bank, index/search, and run memory MCP (pipeline-kit-memory)",
    )
    memory_commands = memory_parser.add_subparsers(dest="memory_command", required=True)
    m_link = memory_commands.add_parser("link", help="point this project at an external memory repo")
    m_link.add_argument("root", help="path to memory git folder (created if missing with --init)")
    m_link.add_argument("project", nargs="?", default=".")
    m_link.add_argument("--project-id", default="", help="namespace under projects/{id}/")
    m_link.add_argument("--layout", choices=("", "flat", "namespaced"), default="")
    m_link.add_argument(
        "--init",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="scaffold README/gitignore/git (default: true)",
    )
    memory_commands.add_parser("unlink", help="disable memory without deleting the bank").add_argument(
        "project", nargs="?", default="."
    )
    memory_commands.add_parser("status", help="print memory link JSON").add_argument(
        "project", nargs="?", default="."
    )
    memory_commands.add_parser("doctor", help="verify memory root and index").add_argument(
        "project", nargs="?", default="."
    )
    m_index = memory_commands.add_parser("index", help="rebuild FTS index over the memory bank")
    m_index.add_argument("project", nargs="?", default=".")
    m_index.add_argument("--engine", default="", help="search backend (default fts5)")
    m_search = memory_commands.add_parser("search", help="query the memory index")
    m_search.add_argument("query")
    m_search.add_argument("project", nargs="?", default=".")
    m_search.add_argument("--limit", type=int, default=10)
    m_search.add_argument("--slug", default="")
    m_search.add_argument("--kind", default="")
    m_search.add_argument("--json", action="store_true")
    m_mcp = memory_commands.add_parser("mcp", help="run stdio MCP server (pipeline-memory)")
    m_mcp.add_argument("project", nargs="?", default=".")
    m_mcp.add_argument("--root", default="", help="override memory root")
    m_import = memory_commands.add_parser(
        "import-local",
        help="copy existing project features/ into the linked memory root",
    )
    m_import.add_argument("project", nargs="?", default=".")
    m_import.add_argument("--dry-run", action="store_true")

    portal_parser = commands.add_parser(
        "portal",
        help="report this project's local state to a pipeline portal (metadata only)",
    )
    portal_commands = portal_parser.add_subparsers(dest="portal_command", required=True)
    p_connect = portal_commands.add_parser("connect", help="connect this project with an ingest key from the portal")
    p_connect.add_argument("project", nargs="?", default=".")
    p_connect.add_argument("--url", required=True, help="portal URL, for example https://portal.example.com")
    p_connect.add_argument("--key", required=True, help="the project's ingest key (shown once in the portal)")
    p_connect.add_argument("--home", default="", help=argparse.SUPPRESS)
    for name, text in (
        ("status", "show the connection and when the portal last heard from this project"),
        ("push", "send the current state now"),
        ("disconnect", "forget the connection on this machine"),
    ):
        sub = portal_commands.add_parser(name, help=text)
        sub.add_argument("project", nargs="?", default=".")
        sub.add_argument("--home", default="", help=argparse.SUPPRESS)

    license_parser = commands.add_parser("license", help="issue or activate an org license")
    license_commands = license_parser.add_subparsers(dest="license_command", required=True)
    issue_parser = license_commands.add_parser(
        "issue",
        help="sign a token from a kit checkout",
    )
    issue_parser.add_argument("--org", required=True)
    issue_parser.add_argument("--expires", required=True, help="YYYY-MM-DD, valid through that UTC day")
    issue_parser.add_argument(
        "--features",
        default="orchestrator,jira,governance,evidence,assess",
        help="comma list: orchestrator, jira, governance, evidence, assess",
    )
    issue_parser.add_argument("--repo", default="", help="pipeline-kit checkout")
    activate_parser = license_commands.add_parser(
        "activate",
        help="store PIPELINE_KIT_LICENSE in the home pack",
    )
    activate_parser.add_argument("--home", default="", help=argparse.SUPPRESS)
    status_parser = license_commands.add_parser("status", help="print org, expiry, and paid areas")
    status_parser.add_argument("--home", default="", help=argparse.SUPPRESS)

    version_parser = commands.add_parser(
        "version",
        help="show or set the kit release version (maintainers)",
    )
    version_parser.add_argument(
        "action",
        nargs="?",
        choices=("show", "bump", "set"),
        default="show",
        help="show current, bump a semver part, or set an exact version",
    )
    version_parser.add_argument(
        "value",
        nargs="?",
        default="",
        help="patch|minor|major for bump, or X.Y.Z for set",
    )
    version_parser.add_argument(
        "--repo",
        default="",
        help=f"pipeline-kit checkout (default: ${KIT_REPO_ENV}, then search up from cwd)",
    )
    version_parser.add_argument(
        "--commit",
        action="store_true",
        help="commit the version files in the kit checkout, not the current project",
    )
    version_parser.add_argument(
        "--tag",
        action="store_true",
        help="with --commit, also create the vX.Y.Z tag in the kit checkout",
    )
    version_parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)
    _LAST_INVOCATION["args"] = args
    if args.command == "license":
        return _license_cli(args)
    if args.command == "version":
        return cmd_version(
            args.action,
            args.value,
            repo=args.repo,
            dry_run=args.dry_run,
            commit=args.commit,
            tag=args.tag,
        )
    home = Path(args.home).expanduser().resolve() if getattr(args, "home", "") else None
    project = Path(getattr(args, "project", ".")).expanduser().resolve()

    if args.command in {"init", "update"}:
        user = bool(getattr(args, "user", False))
        if not user and not project.is_dir():
            print(f"not a directory: {project}", file=sys.stderr)
            return 64
        dest = ((home or Path.home()) if user else project) / ".pipeline"
        mode = getattr(args, "mode", None) or read_install_mode(dest)
        if mode == "orchestrator":
            blocked = _require_license("orchestrator")
            if blocked:
                return blocked
        return install(
            scope="user" if user else "project",
            target=(home or Path.home()) if user else project,
            ide=args.ide,
            agent_stubs=args.agent_stubs,
            dry_run=args.dry_run,
            home=home,
            mode=mode,
        )
    if args.command == "setup":
        dest = (home or Path.home()) / ".pipeline"
        mode = getattr(args, "mode", None) or read_install_mode(dest)
        if mode == "orchestrator":
            blocked = _require_license("orchestrator")
            if blocked:
                return blocked
        return install(
            scope="user",
            target=home or Path.home(),
            ide=args.ide,
            agent_stubs=args.agent_stubs,
            dry_run=args.dry_run,
            home=home,
            mode=mode,
        )
    if args.command == "uninstall":
        return uninstall(
            scope="user" if args.user else "project",
            target=project,
            home=home,
        )
    if args.command == "doctor":
        return doctor(target=project, user=args.user, ide=args.ide, home=home)
    if args.command == "scan":
        _ensure_pkg_path()
        assess = HERE / "packages" / "pipeline-kit-assess"
        if assess.is_dir() and str(assess) not in sys.path:
            sys.path.insert(0, str(assess))
        blocked = _require_license("assess")
        if blocked:
            return blocked
        try:
            from pipeline_assess.commands import cmd_scan
        except ImportError:
            print(
                'pipeline-kit-assess is not installed. Run: uv tool install -e ".[assess]"',
                file=sys.stderr,
            )
            return 1
        out = Path(args.out).expanduser() if getattr(args, "out", "") else None
        return cmd_scan(
            project,
            out=out,
            yes=bool(getattr(args, "yes", False)),
            no_bootstrap=bool(getattr(args, "no_bootstrap", False)),
            as_json=bool(getattr(args, "json", False)),
            apply=getattr(args, "apply", "") or "",
            dry_run=bool(getattr(args, "dry_run", False)),
        )
    if args.command == "workflows":
        if getattr(args, "scaffold", "") or "":
            blocked = _require_license("orchestrator")
            if blocked:
                return blocked
        return list_workflows(
            target=project,
            user=args.user,
            home=home,
            scaffold=getattr(args, "scaffold", "") or "",
        )
    if args.command in {"run", "resume", "approve", "status", "verify", "export-briefs"}:
        _ensure_pkg_path()
        from pipeline_orchestrator.cli import (
            cmd_approve,
            cmd_export_briefs,
            cmd_resume,
            cmd_run,
            cmd_status,
        )
        from pipeline_orchestrator.verify import cmd_verify

        if not project.is_dir():
            print(f"not a directory: {project}", file=sys.stderr)
            return 64
        if args.command == "run":
            from pipeline_kit.license import feature_for_workflow

            blocked = _require_license(feature_for_workflow(args.workflow))
            if blocked:
                return blocked
            return cmd_run(
                project,
                slug=args.slug,
                workflow=args.workflow,
                change_class=args.change_class,
                runner=args.runner,
                dry_run=args.dry_run,
                request=getattr(args, "request", "") or "",
                request_file=getattr(args, "request_file", "") or "",
            )
        if args.command == "resume":
            blocked = _require_license(_feature_for_saved_run(project, args.slug))
            if blocked:
                return blocked
            return cmd_resume(project, slug=args.slug, runner=args.runner)
        if args.command == "approve":
            blocked = _require_license(_feature_for_saved_run(project, args.slug))
            if blocked:
                return blocked
            return cmd_approve(project, slug=args.slug, gate=args.gate, note=args.note)
        if args.command == "status":
            return cmd_status(project, slug=args.slug)
        if args.command == "verify":
            return cmd_verify(project)
        return cmd_export_briefs(project)
    if args.command == "knowledge":
        (
            cmd_extract,
            cmd_init,
            cmd_playwright,
            cmd_promote,
            cmd_promote_feature,
            cmd_render,
            cmd_status,
            cmd_validate,
        ) = _knowledge_commands()
        if not project.is_dir():
            print(f"not a directory: {project}", file=sys.stderr)
            return 64
        if args.knowledge_command == "init":
            return cmd_init(
                project,
                register_skill=args.register_skill,
                ide=args.ide,
            )
        if args.knowledge_command == "extract":
            return cmd_extract(project, force=args.force, update=bool(getattr(args, "update", False)))
        if args.knowledge_command == "status":
            return cmd_status(project)
        if args.knowledge_command == "validate":
            return cmd_validate(project, run_id=args.run_id)
        if args.knowledge_command == "promote":
            return cmd_promote(project, run_id=args.run_id)
        if args.knowledge_command == "render":
            return cmd_render(project, slug=args.slug)
        if args.knowledge_command == "playwright":
            return cmd_playwright(project, slug=args.slug)
        if args.knowledge_command == "promote-feature":
            return cmd_promote_feature(project, slug=args.slug)
        parser.error("unknown knowledge command")
        return 2
    if args.command == "memory":
        if not project.is_dir() and args.memory_command != "link":
            # link may create paths; still require project dir
            pass
        if not project.is_dir():
            print(f"not a directory: {project}", file=sys.stderr)
            return 64
        try:
            cmds = _memory_commands()
        except ImportError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        cmd = args.memory_command
        if cmd == "link":
            return cmds["link"](
                project,
                args.root,
                project_id=getattr(args, "project_id", "") or "",
                layout=getattr(args, "layout", "") or "",
                init=bool(getattr(args, "init", True)),
            )
        if cmd == "unlink":
            return cmds["unlink"](project)
        if cmd == "status":
            return cmds["status"](project)
        if cmd == "doctor":
            return cmds["doctor"](project)
        if cmd == "index":
            return cmds["index"](project, engine=getattr(args, "engine", "") or "")
        if cmd == "search":
            return cmds["search"](
                project,
                args.query,
                limit=int(getattr(args, "limit", 10) or 10),
                slug=getattr(args, "slug", "") or "",
                kind=getattr(args, "kind", "") or "",
                as_json=bool(getattr(args, "json", False)),
            )
        if cmd == "mcp":
            return cmds["mcp"](project, root=getattr(args, "root", "") or "")
        if cmd == "import-local":
            return cmds["import-local"](project, dry_run=bool(getattr(args, "dry_run", False)))
        parser.error("unknown memory command")
        return 2
    if args.command == "portal":
        _ensure_pkg_path()
        from pipeline_kit import portal_link

        action = args.portal_command
        if action == "connect":
            return portal_link.cmd_connect(project, url=args.url, key=args.key, home=home)
        if action == "status":
            return portal_link.cmd_status(project, home=home)
        if action == "push":
            return portal_link.cmd_push(project, home=home)
        return portal_link.cmd_disconnect(project, home=home)
    if args.command == "plugins":
        cmd_install, cmd_list, cmd_status, cmd_uninstall = _plugin_commands()
        if args.plugins_command == "list":
            return cmd_list()
        if not project.is_dir():
            print(f"not a directory: {project}", file=sys.stderr)
            return 64
        scope = getattr(args, "scope", "project")
        ide = getattr(args, "ide", "cursor")
        if args.plugins_command == "install":
            return cmd_install(
                project,
                args.name,
                ide=ide,
                scope=scope,
                home=home,
                hook=bool(getattr(args, "hook", False)),
            )
        if args.plugins_command == "status":
            return cmd_status(
                project,
                getattr(args, "plugin", None),
                ide=ide,
                scope=scope,
                home=home,
            )
        if args.plugins_command == "uninstall":
            return cmd_uninstall(
                project,
                args.name,
                ide=ide,
                scope=scope,
                purge=bool(getattr(args, "purge", False)),
                home=home,
            )
        parser.error("unknown plugins command")
        return 2
    if args.command == "features":
        cmd_disable, cmd_enable, cmd_list, cmd_status = _feature_commands()
        if args.features_command == "list":
            return cmd_list()
        if not project.is_dir():
            print(f"not a directory: {project}", file=sys.stderr)
            return 64
        if args.features_command == "status":
            return cmd_status(project)
        if args.features_command == "enable":
            from pipeline_kit.license import PAID_FLAGS

            paid = PAID_FLAGS.get(args.name)
            if paid:
                blocked = _require_license(paid)
                if blocked:
                    return blocked
            return cmd_enable(project, args.name)
        if args.features_command == "disable":
            return cmd_disable(project, args.name)
        parser.error("unknown features command")
        return 2
    if args.command == "obs":
        cmd_flush, cmd_install, cmd_report, cmd_status, cmd_uninstall = _obs_commands()
        if not project.is_dir():
            print(f"not a directory: {project}", file=sys.stderr)
            return 64
        if args.obs_command != "report":
            blocked = _require_license("evidence")
            if blocked:
                return blocked
        if args.obs_command == "install":
            return cmd_install(
                project,
                ide=args.ide,
                adapter=args.adapter,
                version=version(),
            )
        if args.obs_command == "uninstall":
            return cmd_uninstall(project, ide=args.ide)
        if args.obs_command == "status":
            return cmd_status(project)
        if args.obs_command == "flush":
            return cmd_flush(project)
        if args.obs_command == "report":
            return cmd_report(project)
        parser.error("unknown obs command")
        return 2
    if args.command == "eval":
        from pipeline_eval.commands import cmd_judges_sync  # noqa: WPS433

        if not project.is_dir():
            print(f"not a directory: {project}", file=sys.stderr)
            return 64
        blocked = _require_license("evidence")
        if blocked:
            return blocked
        if args.eval_command == "judges" and args.judges_command == "sync":
            return cmd_judges_sync(project)
        parser.error("unknown eval command")
        return 2
    parser.error(f"unknown command: {args.command}")
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create a .pipeline folder in a project or in your home directory."
    )
    scope = parser.add_mutually_exclusive_group(required=False)
    scope.add_argument(
        "--project",
        nargs="?",
        const=".",
        default=None,
        help="create <path>/.pipeline (default: current directory)",
    )
    scope.add_argument("--user", action="store_true", help="create ~/.pipeline")
    parser.add_argument("--ide", choices=("cursor", "claude-code", "github", "none"), default="cursor")
    parser.add_argument("--agent-stubs", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--sync-kit",
        action="store_true",
        help="refresh kit/pipeline from this repo's .pipeline (maintainers)",
    )
    parser.add_argument("--home", default="", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.sync_kit:
        return sync_kit()
    home = Path(args.home).expanduser().resolve() if args.home else None
    if args.user:
        target = home or Path.home()
        scope_name = "user"
    else:
        target = Path(args.project or ".").expanduser().resolve()
        scope_name = "project"
        if not target.is_dir():
            print(f"not a directory: {target}", file=sys.stderr)
            return 64
    if args.uninstall:
        return uninstall(scope=scope_name, target=target, home=home)
    return install(
        scope=scope_name,
        target=target,
        ide=args.ide,
        agent_stubs=args.agent_stubs,
        dry_run=args.dry_run,
        home=home,
    )


if __name__ == "__main__":
    raise SystemExit(main())
