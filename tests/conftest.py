"""Expose source-tree packages under their stable import names."""

from __future__ import annotations

import importlib.util
import os
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ASSESS = ROOT / "packages" / "pipeline-kit-assess"
MEMORY = ROOT / "packages" / "pipeline-kit-memory"
# Optional local sibling for maintainers. Public CI does not have this package.
# Set PIPELINE_KIT_TEST_WITHOUT_LICENSE=1 to simulate public CI on a maintainer machine.
_FORCE_NO_LICENSE = os.environ.get("PIPELINE_KIT_TEST_WITHOUT_LICENSE", "").strip() in {
    "1",
    "true",
    "yes",
}
LICENSE_PKG = ROOT.parent / "pipeline-kit-license"
_path_entries = [ROOT, ASSESS, MEMORY]
if not _FORCE_NO_LICENSE:
    _path_entries.append(LICENSE_PKG)
for entry in _path_entries:
    if entry.is_dir() and str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from layout import install_source_importers

install_source_importers()

HAS_LICENSE_ENGINE = (not _FORCE_NO_LICENSE) and importlib.util.find_spec("pipeline_license") is not None


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "license_absent: do not grant a test license (fail-closed / missing-token paths)",
    )
    config.addinivalue_line(
        "markers",
        "requires_license_engine: skip when private pipeline-kit-license is not installed",
    )


@pytest.fixture(autouse=True)
def enterprise_license(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
):
    """Grant paid areas when the private engine is present.

    Behaviour:
    - Engine present (maintainer machine / private install): same as before —
      real Ed25519 test token for every paid feature.
    - Engine absent (public CI): open ``require`` / ``has_feature`` so unit tests
      for kit, orchestrator, and portal client still run. Production CLI still
      fails closed without the private package; that path is covered by
      ``license_absent`` tests and by local runs with the engine installed.
    - ``license_absent``: no grant and no open-gate patch (real fail-closed).
    - ``requires_license_engine``: skip when the private package is missing.
    """
    from pipeline_kit import license as lic

    if request.node.get_closest_marker("requires_license_engine") and not HAS_LICENSE_ENGINE:
        pytest.skip("private pipeline-kit-license package is not installed")

    if request.node.get_closest_marker("license_absent"):
        monkeypatch.delenv(lic.ENV_LICENSE, raising=False)
        return None

    if not HAS_LICENSE_ENGINE:
        # Keep production fail-closed code paths intact; only relax gates in tests
        # so the public suite does not require a private sibling checkout.
        monkeypatch.setattr(lic, "require", lambda feature, home=None: 0)
        monkeypatch.setattr(
            lic,
            "has_feature",
            lambda feature, home=None: feature in lic.FEATURES,
        )
        return None

    import pipeline_license as eng
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    signing_key = Ed25519PrivateKey.generate()
    pem = signing_key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode()
    body = "".join(line for line in pem.splitlines() if "PUBLIC KEY" not in line)
    path = tmp_path_factory.mktemp("license-pub") / "license_public_key.txt"
    path.write_text("# test\n" + body + "\n", encoding="utf-8")
    monkeypatch.setattr(eng, "public_key_path", lambda: path)
    token = eng.sign_token(
        signing_key,
        org="test",
        exp=int(time.time()) + 86400 * 365,
        features=list(eng.FEATURES),
    )
    monkeypatch.setenv(lic.ENV_LICENSE, token)
    return {"signing_key": signing_key, "public": path, "engine": eng}
