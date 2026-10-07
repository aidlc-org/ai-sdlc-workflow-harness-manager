"""Org license gates the paid areas (orchestrator, jira, governance, evidence, assess, portal). Kit mode stays open."""

from __future__ import annotations

import importlib.util
import json
import runpy
import stat
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
INSTALL = REPO / "install.py"


def _cli(argv: list[str]) -> int:
    ns = runpy.run_path(str(INSTALL))
    return int(ns["cli_main"](argv))


def _clear(monkeypatch: pytest.MonkeyPatch, home: Path) -> None:
    import pipeline_license as eng
    from pipeline_kit import license as lic

    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.delenv(lic.ENV_LICENSE, raising=False)
    monkeypatch.setattr(eng.Path, "home", lambda: home)


def test_kit_mode_stays_open_without_a_license(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _clear(monkeypatch, tmp_path / "home")
    app = tmp_path / "app"
    app.mkdir()
    assert _cli(["init", str(app), "--ide", "none"]) == 0
    assert (app / ".pipeline" / "workflows" / "ask.json").is_file()
    assert _cli(["features", "enable", "telemetry", str(app)]) == 0


def test_paid_commands_exit_73_without_a_license(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _clear(monkeypatch, tmp_path / "home")
    app = tmp_path / "app"
    app.mkdir()
    assert _cli(["init", str(app), "--ide", "none"]) == 0
    assert _cli(["init", str(app), "--ide", "none", "--mode", "orchestrator"]) == 73
    assert (
        _cli(
            [
                "run",
                str(app),
                "--slug",
                "preview",
                "--workflow",
                "feature-development",
                "--runner",
                "fake",
            ]
        )
        == 73
    )
    assert _cli(["features", "enable", "jira-intake", str(app)]) == 73
    assert _cli(["features", "enable", "agent-observability", str(app)]) == 73
    assert _cli(["obs", "install", str(app), "--ide", "cursor"]) == 73
    assert _cli(["eval", "judges", "sync", str(app)]) == 73
    assert _cli(["portal", "connect", str(app), "--url", "http://127.0.0.1:9", "--key", "x"]) == 73
    assert _cli(["portal", "push", str(app)]) == 73
    assert _cli(["obs", "report", str(app)]) == 1
    err = capsys.readouterr().err
    assert "pipeline-kit license activate" in err or "pipeline-kit-license" in err
    assert "PIPELINE_KIT_LICENSE=" not in err


def test_governance_needs_its_own_area(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    enterprise_license: dict,
):
    from pipeline_kit import license as lic

    token = lic.sign_token(
        enterprise_license["signing_key"],
        org="orch-only",
        exp=int(time.time()) + 3600,
        features=["orchestrator"],
    )
    monkeypatch.setenv(lic.ENV_LICENSE, token)
    app = tmp_path / "app"
    app.mkdir()
    assert _cli(["init", str(app), "--ide", "none", "--mode", "orchestrator"]) == 0
    assert (
        _cli(
            [
                "run",
                str(app),
                "--slug",
                "pci",
                "--workflow",
                "security-review",
                "--runner",
                "fake",
            ]
        )
        == 73
    )


def test_activate_stores_a_private_file_and_status_hides_the_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    enterprise_license: dict,
    capsys: pytest.CaptureFixture[str],
):
    from pipeline_kit import license as lic

    token = lic.sign_token(
        enterprise_license["signing_key"],
        org="Acme",
        exp=int(time.time()) + 86400 * 30,
        features=["jira", "evidence"],
    )
    monkeypatch.setenv(lic.ENV_LICENSE, token)
    home = tmp_path / "home"
    assert _cli(["license", "activate", "--home", str(home)]) == 0
    stored = home / ".pipeline" / "license.json"
    assert json.loads(stored.read_text(encoding="utf-8"))["token"] == token
    # POSIX owner-only mode; Windows ACLs do not map to 0o600 the same way.
    if sys.platform != "win32":
        assert stat.S_IMODE(stored.stat().st_mode) == 0o600
    monkeypatch.delenv(lic.ENV_LICENSE, raising=False)
    monkeypatch.setattr(lic.Path if hasattr(lic, "Path") else Path, "home", lambda: home)
    # Engine stores/reads under Path.home when --home is not enough for status path helpers
    import pipeline_license as eng

    monkeypatch.setattr(eng.Path, "home", lambda: home)
    assert _cli(["license", "status", "--home", str(home)]) == 0
    out = capsys.readouterr().out
    assert "org: Acme" in out
    assert "jira: on" in out
    assert "orchestrator: off" in out
    assert "portal: off" in out
    assert token not in out


def test_expired_token_is_rejected(enterprise_license: dict, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from pipeline_kit import license as lic

    token = lic.sign_token(
        enterprise_license["signing_key"],
        org="old",
        exp=int(time.time()) - 10,
        features=list(lic.FEATURES),
    )
    monkeypatch.setenv(lic.ENV_LICENSE, token)
    assert lic.require("orchestrator", home=tmp_path) == 73


def test_issue_requires_a_kit_checkout(tmp_path: Path):
    assert (
        _cli(
            [
                "license",
                "issue",
                "--repo",
                str(tmp_path),
                "--org",
                "Acme",
                "--expires",
                "2027-01-01",
            ]
        )
        == 64
    )


def test_issue_signs_a_token_that_activates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    enterprise_license: dict,
    capsys: pytest.CaptureFixture[str],
):
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
    )

    from pipeline_kit import license as lic

    key_file = tmp_path / "signing.pem"
    key_file.write_bytes(
        enterprise_license["signing_key"].private_bytes(
            Encoding.PEM,
            PrivateFormat.PKCS8,
            NoEncryption(),
        )
    )
    monkeypatch.setenv(lic.ENV_SIGNING_KEY, str(key_file))
    assert (
        _cli(
            [
                "license",
                "issue",
                "--repo",
                str(REPO),
                "--org",
                "Northline",
                "--expires",
                "2027-06-01",
                "--features",
                "orchestrator,jira",
            ]
        )
        == 0
    )
    token = capsys.readouterr().out.strip().splitlines()[-1]
    claims = lic.verify_token(token)
    assert claims["org"] == "Northline"
    assert claims["features"] == ["jira", "orchestrator"]


def test_public_signing_helpers_match_private_aliases(
    tmp_path: Path,
    enterprise_license: dict,
):
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
    )

    from pipeline_kit import license as lic

    key_file = tmp_path / "signing.pem"
    key_file.write_bytes(
        enterprise_license["signing_key"].private_bytes(
            Encoding.PEM,
            PrivateFormat.PKCS8,
            NoEncryption(),
        )
    )
    exp = lic.expiry_day("2027-06-01")
    assert exp == lic._expiry_day("2027-06-01")
    key = lic.load_signing_key(key_file)
    assert type(key) is type(lic._load_signing_key(key_file))
    token = lic.sign_token(key, org="Northline", exp=exp, features=["assess"])
    assert lic.verify_token(token)["features"] == ["assess"]


def test_issue_defaults_to_every_paid_area_including_portal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    enterprise_license: dict,
    capsys: pytest.CaptureFixture[str],
):
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
    )

    from pipeline_kit import license as lic

    key_file = tmp_path / "signing.pem"
    key_file.write_bytes(
        enterprise_license["signing_key"].private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    )
    monkeypatch.setenv(lic.ENV_SIGNING_KEY, str(key_file))
    argv = ["license", "issue", "--repo", str(REPO), "--org", "Northline", "--expires", "2027-06-01"]
    assert _cli(argv) == 0
    token = capsys.readouterr().out.strip().splitlines()[-1]
    assert lic.verify_token(token)["features"] == sorted(lic.FEATURES)
    assert "assess" in lic.FEATURES
    assert "portal" in lic.FEATURES


def test_scan_needs_the_assess_area(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    _clear(monkeypatch, tmp_path / "home")
    app = tmp_path / "app"
    app.mkdir()
    assert _cli(["scan", str(app)]) == 73
    err = capsys.readouterr().err
    assert "pipeline-kit license activate" in err or "pipeline-kit-license" in err


def test_shim_available_when_private_package_present():
    from pipeline_kit import license as lic

    assert lic.available() is True
    assert "portal" in lic.FEATURES

