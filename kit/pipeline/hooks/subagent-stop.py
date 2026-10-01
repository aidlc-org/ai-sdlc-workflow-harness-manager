#!/usr/bin/env python3
"""subagentStop: remind the specialist to leave a HANDOFF on disk (follow-up, not parent orchestration)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import portal_owns_gate, emit_followup, emit_permission, load_payload, subagent_type

ROOT = Path(__file__).resolve().parents[2]

HANDOFF_HINT = {
    "intake-agent": "features/{slug}/HANDOFF-intake.md",
    "product-manager-agent": "features/{slug}/HANDOFF-pm.md",
    "ui-designer-agent": "features/{slug}/HANDOFF-ui.md",
    "ba-agent": "features/{slug}/HANDOFF.md",
    "bug-analyst-agent": "features/{slug}/HANDOFF-bug-analyst.md",
    "ba-critic-agent": "features/{slug}/HANDOFF-ba-critic.md",
    "telemetry-agent": "features/{slug}/HANDOFF-telemetry.md",
    "developer-agent": "features/{slug}/HANDOFF-developer.md",
    "developer-critic-agent": "features/{slug}/HANDOFF-developer-critic.md",
    "tester-agent": "features/{slug}/HANDOFF-tester.md",
    "devops-agent": "features/{slug}/HANDOFF-devops.md",
    "retro-agent": "features/{slug}/HANDOFF-retro.md",
}


def main() -> int:
    if portal_owns_gate():
        return emit_permission(True, "skip")
    payload = load_payload()
    kind = subagent_type(payload)
    path = HANDOFF_HINT.get(kind)
    if not path:
        return emit_followup("")
    # Empty followup is useless; only nudge if no features/ tree exists yet.
    features = ROOT / "features"
    if features.is_dir() and any(features.glob("**/HANDOFF*.md")):
        return emit_followup("")
    return emit_followup(
        f"Before you finish: write {path} (replace {{slug}}) and paste that HANDOFF in your final message. "
        "Do not spawn the next pipeline agent."
    )


if __name__ == "__main__":
    raise SystemExit(main())
