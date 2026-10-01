"""Scaffold a memory-bank git repository."""

from __future__ import annotations

import subprocess
from pathlib import Path

README = """# Pipeline memory bank

This repository stores **pipeline-kit feature artifacts** outside product source trees.

## Layout

- **Flat** (one product ↔ one memory repo): `features/{slug}/…`
- **Namespaced** (shared org bank): `projects/{project_id}/features/{slug}/…`

Do not commit `.memory/` (local search index). Commit markdown and JSON artifacts.

## Agent access

1. Link from a product repo: `pipeline-kit memory link <this-path>`
2. Index: `pipeline-kit memory index`
3. CLI search: `pipeline-kit memory search "<terms>"`
4. **MCP (optional):** the IDE does **not** pick this up automatically.
   Each user adds a **stdio** MCP server in their client config, then restarts:

   - command: `pipeline-memory-mcp`
   - args: `--project` `<absolute path to the product repo>` (the one with `.pipeline/config.json`)

   Examples (Cursor / Claude Desktop use `mcpServers`; VS Code may use `servers`):

   ```json
   {
     "mcpServers": {
       "pipeline-memory": {
         "command": "pipeline-memory-mcp",
         "args": ["--project", "C:/path/to/your-product-repo"]
       }
     }
   }
   ```

   Daily use: the IDE starts the process; you do not leave `memory mcp` running
   in a terminal. Re-run `memory index` after large artifact changes.

Full install, client-specific snippets, tools, and troubleshooting:
`packages/pipeline-kit-memory/README.md` in the pipeline-kit distribution.
"""

GITIGNORE = """# Local FTS index
.memory/
*.sqlite
*.sqlite-*

# OS / editor
.DS_Store
Thumbs.db
*.swp
.idea/
.vscode/
"""


def scaffold_memory_repo(root: Path, *, git_init: bool = True) -> list[str]:
    """Create memory-repo skeleton. Returns human-readable actions taken."""
    root = Path(root).expanduser().resolve()
    actions: list[str] = []
    root.mkdir(parents=True, exist_ok=True)
    actions.append(f"root: {root}")

    readme = root / "README.md"
    if not readme.is_file():
        readme.write_text(README, encoding="utf-8")
        actions.append("wrote README.md")

    gi = root / ".gitignore"
    if not gi.is_file():
        gi.write_text(GITIGNORE, encoding="utf-8")
        actions.append("wrote .gitignore")

    (root / "features").mkdir(exist_ok=True)
    (root / "projects").mkdir(exist_ok=True)
    (root / ".memory").mkdir(exist_ok=True)
    actions.append("ensured features/, projects/, .memory/")

    if git_init and not (root / ".git").exists():
        try:
            subprocess.run(
                ["git", "init"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            actions.append("git init")
        except (OSError, subprocess.CalledProcessError) as exc:
            actions.append(f"git init skipped: {exc}")

    return actions
