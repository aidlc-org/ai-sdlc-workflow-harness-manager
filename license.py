"""License facade for pipeline-kit.

Crypto issue/validate live in the private ``pipeline-kit-license`` package
(``import pipeline_license``). This module keeps stable names for the CLI and
call sites. Without the private package, paid checks fail closed (exit 73).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Public constants for CLI routing and docs when the private package is absent.
ENV_LICENSE = "PIPELINE_KIT_LICENSE"
ENV_SIGNING_KEY = "PIPELINE_KIT_LICENSE_SIGNING_KEY"
EXIT_LICENSE = 73

FEATURES = ("orchestrator", "jira", "governance", "evidence", "assess", "portal")
JIRA_WORKFLOWS = frozenset({"jira-story", "jira-epic", "jira-bug"})
GOVERNANCE_WORKFLOWS = frozenset(
    {
        "security-review",
        "ci-audit",
        "dependency-audit",
        "accessibility-review",
    }
)
PAID_FLAGS = {
    "jira-intake": "jira",
    "agent-observability": "evidence",
}

_MISSING = (
    "license: install the private pipeline-kit-license package, "
    "then run: pipeline-kit license activate"
)


class LicenseError(ValueError):
    """Token cannot be accepted or license engine is unavailable."""


def feature_for_workflow(name: str) -> str:
    key = name.strip().lower()
    if key in JIRA_WORKFLOWS:
        return "jira"
    if key in GOVERNANCE_WORKFLOWS:
        return "governance"
    return "orchestrator"


def available() -> bool:
    try:
        import pipeline_license  # noqa: F401
    except ImportError:
        return False
    return True


def _engine():
    try:
        import pipeline_license as eng
    except ImportError as exc:
        raise LicenseError(
            "pipeline-kit-license is not installed (private enterprise package)"
        ) from exc
    return eng


def require(feature: str, *, home: Path | None = None) -> int:
    if feature not in FEATURES:
        raise LicenseError(f"unknown feature: {feature}")
    try:
        eng = _engine()
    except LicenseError:
        print(_MISSING, file=sys.stderr)
        return EXIT_LICENSE
    return int(eng.require(feature, home=home))


def has_feature(feature: str, *, home: Path | None = None) -> bool:
    """True when a valid token includes ``feature``. Never prints; False if unavailable."""
    if feature not in FEATURES:
        return False
    try:
        eng = _engine()
        claims = eng.verify_token(eng.read_token(home=home))
    except Exception:  # noqa: BLE001
        return False
    return feature in claims.get("features", [])


def verify_token(token: str) -> dict:
    return _engine().verify_token(token)


def sign_token(signing_key, *, org: str, exp: int, features: list[str]) -> str:
    return _engine().sign_token(signing_key, org=org, exp=exp, features=features)


def read_token(*, home: Path | None = None) -> str:
    return _engine().read_token(home=home)


def license_path(home: Path | None = None) -> Path:
    try:
        return _engine().license_path(home)
    except LicenseError:
        return (home or Path.home()) / ".pipeline" / "license.json"


def public_key_path() -> Path:
    return _engine().public_key_path()


def expiry_day(text: str) -> int:
    return _engine().expiry_day(text)


def load_signing_key(path: Path):
    return _engine().load_signing_key(path)


_expiry_day = expiry_day
_load_signing_key = load_signing_key


def signing_key_path() -> str:
    try:
        return _engine().signing_key_path()
    except LicenseError:
        return ""


def cmd_issue(*, org: str, expires: str, features: str) -> int:
    try:
        eng = _engine()
    except LicenseError:
        print(_MISSING, file=sys.stderr)
        return 64
    return int(eng.cmd_issue(org=org, expires=expires, features=features))


def cmd_activate(*, home: Path | None = None) -> int:
    try:
        eng = _engine()
    except LicenseError:
        print(_MISSING, file=sys.stderr)
        return EXIT_LICENSE
    return int(eng.cmd_activate(home=home))


def cmd_status(*, home: Path | None = None) -> int:
    try:
        eng = _engine()
    except LicenseError:
        print(_MISSING, file=sys.stderr)
        return EXIT_LICENSE
    return int(eng.cmd_status(home=home))
