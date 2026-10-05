"""Local admin web dashboard for pipeline-kit.

Read-only by default: renders what hooks and pack state files already wrote
(install marker, config.json, run/board JSON, the observability ledger).
Writes are limited to the seven named feature flags, the two optional
plugins, and the observability toggle — the same config paths the
``pipeline-kit features`` / ``plugins`` / ``obs`` commands already write.

Never imports or executes a target project's own Python (no
``pipeline_extensions/*.py``, no copied ``.pipeline/loader`` scripts) —
multiple repos are read through plain JSON files on disk, not by importing
project code into the portal process.
"""

from __future__ import annotations
