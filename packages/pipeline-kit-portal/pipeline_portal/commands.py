"""pipeline-kit portal subcommands.

CLI shape deliberately uses an explicit verb for every action
(``serve`` / ``add`` / ``remove`` / ``list``) rather than a bare
``pipeline-kit portal [project]`` default-to-serve shortcut: argparse
cannot safely mix an optional (``nargs="?"``) positional with optional
subparsers on the same parser, and every other multi-verb command in this
CLI (``obs``, ``features``, ``knowledge``, ``memory``, ``plugins``) already
uses an explicit, required verb. This keeps ``portal`` consistent with
that convention instead of introducing a one-off parsing special case.
"""

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path
from typing import Any

from pipeline_portal import registry
from pipeline_portal.server import make_server, serve_forever


def cmd_portal_serve(
    project: Path,
    *,
    home: Path,
    host: str = "127.0.0.1",
    port: int = 7171,
    open_browser: bool = False,
    read_only: bool = False,
    use_token: bool = True,
    allow_remote: bool = False,
) -> int:
    project = Path(project).expanduser().resolve()
    if not project.is_dir():
        print(f"not a directory: {project}", file=sys.stderr)
        return 64
    try:
        server, url, token = make_server(
            project=project,
            home=home,
            host=host,
            port=port,
            read_only=read_only,
            use_token=use_token,
            allow_remote=allow_remote,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 64
    except OSError as exc:
        print(f"could not bind {host}:{port}: {exc}", file=sys.stderr)
        return 1
    print(f"portal: {url}")
    print(f"bound: {host} ({'loopback only' if host in ('127.0.0.1', 'localhost', '::1') else 'remote — see --allow-remote'})")
    if read_only:
        print("mode: read-only (no config writes)")
    if not token:
        print("warning: --no-token — anything on this machine can reach the write endpoints", file=sys.stderr)
    if open_browser:
        webbrowser.open(url)
    serve_forever(server)
    return 0


def cmd_portal_add(path: Path, *, home: Path, team: str = "", label: str = "") -> int:
    path = Path(path).expanduser().resolve()
    if not path.is_dir():
        print(f"not a directory: {path}", file=sys.stderr)
        return 64
    row = registry.add_project(home, path, team=team, label=label)
    print(f"registered: {row['path']}")
    if row.get("team"):
        print(f"team: {row['team']}")
    print(f"label: {row['label']}")
    return 0


def cmd_portal_remove(path: Path, *, home: Path) -> int:
    removed = registry.remove_project(home, path)
    if removed:
        print(f"removed: {Path(path).expanduser().resolve()}")
        return 0
    print(f"not registered: {path}", file=sys.stderr)
    return 1


def cmd_portal_list(*, home: Path) -> int:
    rows = registry.list_projects(home)
    if not rows:
        print("no projects registered. Run: pipeline-kit portal add <path>", file=sys.stderr)
        return 0
    width = max(len(row["path"]) for row in rows)
    for row in rows:
        team = row.get("team") or "-"
        label = row.get("label") or ""
        print(f"{row['path'].ljust(width)}  team={team}  {label}")
    return 0


def cmd_portal_entrypoint(args: Any = None, **kwargs: Any) -> int:
    """Entry point for ``pipeline_kit.commands`` discovery and direct invocation."""
    if isinstance(args, dict):
        kwargs = {**args, **kwargs}
        args = None
    command = kwargs.pop("command", "serve")
    home = Path(kwargs.pop("home", None) or Path.home())
    if command == "serve":
        project = Path(kwargs.pop("project", None) or ".")
        return cmd_portal_serve(project, home=home, **kwargs)
    if command == "add":
        path = kwargs.pop("path")
        return cmd_portal_add(path, home=home, team=kwargs.get("team", ""), label=kwargs.get("label", ""))
    if command == "remove":
        return cmd_portal_remove(kwargs.pop("path"), home=home)
    if command == "list":
        return cmd_portal_list(home=home)
    print(f"unknown portal command: {command}", file=sys.stderr)
    return 64
