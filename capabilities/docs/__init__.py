"""Module-scoped codebase docs platform (wiki/codebase). Free open kit."""

from pipeline_docs.commands import (  # noqa: F401
    cmd_extract_modules,
    cmd_init_modules,
    cmd_link_agents,
    cmd_link_index,
    cmd_merge_modules,
    cmd_status,
)

__all__ = [
    "cmd_extract_modules",
    "cmd_init_modules",
    "cmd_link_agents",
    "cmd_link_index",
    "cmd_merge_modules",
    "cmd_status",
]
