"""Run agent-security CLI: ``python -m pipeline_agent_security <command>``."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .commands import cmd_doctor, cmd_flush, cmd_install, cmd_scan, cmd_status, cmd_uninstall
from .providers.uber_adr import DEFAULT_SOURCES, scan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipeline_agent_security")
    parser.add_argument("--project", type=Path, default=Path("."))
    commands = parser.add_subparsers(dest="command", required=True)

    scan_cmd = commands.add_parser("scan", help="Collect session events (explicit, not inline).")
    scan_cmd.add_argument("--state-dir", type=Path, default=None)
    scan_cmd.add_argument(
        "--source",
        action="append",
        dest="sources",
        help=f"Source to scan; repeatable. Default: {', '.join(DEFAULT_SOURCES)}.",
    )

    commands.add_parser("status", help="Show enabled flag, mode, ledger sizes.")
    commands.add_parser("doctor", help="Validate config, providers, and source paths.")
    commands.add_parser("flush", help="Project pending findings into obs ledger.")
    install_cmd = commands.add_parser("install", help="Enable agent_security in config.")
    install_cmd.add_argument("--mode", choices=("audit", "warn", "block"), default="audit")
    commands.add_parser("uninstall", help="Disable agent_security; keep ledgers.")

    args = parser.parse_args(argv)
    project = args.project.expanduser().resolve()

    if args.command == "scan":
        if args.state_dir is not None:
            # Backward-compatible direct scan path used by tests and scripts.
            from .providers import copilot_cli
            from .providers import uber_adr

            state = args.state_dir
            sources = args.sources or list(DEFAULT_SOURCES)
            adr = uber_adr.scan(state, sources)
            payload = {
                "provider": adr.provider,
                "adr_version": adr.adr_version,
                "new_events": adr.new_events,
                "health": list(adr.health),
            }
            if any(s in {"copilot-cli", "copilot"} for s in sources):
                copilot = copilot_cli.scan(state, sources)
                payload = {
                    "new_events": int(adr.new_events) + int(copilot.get("new_events") or 0),
                    "providers": [payload, copilot],
                }
            print(json.dumps(payload, indent=2))
            return 0
        return cmd_scan(project, sources=args.sources)
    if args.command == "status":
        return cmd_status(project)
    if args.command == "doctor":
        return cmd_doctor(project)
    if args.command == "flush":
        return cmd_flush(project)
    if args.command == "install":
        return cmd_install(project, mode=args.mode)
    if args.command == "uninstall":
        return cmd_uninstall(project)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
