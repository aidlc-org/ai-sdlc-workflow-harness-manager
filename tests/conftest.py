"""Expose source-tree packages under their stable import names."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ASSESS = ROOT / "packages" / "pipeline-kit-assess"
MEMORY = ROOT / "packages" / "pipeline-kit-memory"
for entry in (ROOT, ASSESS, MEMORY):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from layout import install_source_importers

install_source_importers()


@pytest.fixture(autouse=True)
def enterprise_license(monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory):
    """Grant every paid area so existing command tests keep running."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    from pipeline_kit import license as lic

    signing_key = Ed25519PrivateKey.generate()
    pem = signing_key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode()
    body = "".join(line for line in pem.splitlines() if "PUBLIC KEY" not in line)
    path = tmp_path_factory.mktemp("license-pub") / "license_public_key.txt"
    path.write_text("# test\n" + body + "\n", encoding="utf-8")
    monkeypatch.setattr(lic, "public_key_path", lambda: path)
    token = lic.sign_token(
        signing_key,
        org="test",
        exp=int(time.time()) + 86400 * 365,
        features=list(lic.FEATURES),
    )
    monkeypatch.setenv(lic.ENV_LICENSE, token)
    return {"signing_key": signing_key, "public": path}
