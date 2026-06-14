# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 DOORM AI PTE. LTD. and Genmount OS Contributors
"""Tests for device keypair generation + request signing."""

from __future__ import annotations

import base64
import sys

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from genmount import auth, config


@pytest.fixture
def tmp_home(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path / "data")
    monkeypatch.setattr(config, "config_dir", lambda: tmp_path / "cfg")
    return tmp_path


def _unb64u(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def test_generate_creates_key_and_returns_pubkey(tmp_home):
    pub = auth.generate_device_key()
    assert len(pub) == 32
    assert auth.device_key_exists()
    if sys.platform != "win32":
        mode = auth.private_key_path().stat().st_mode & 0o777
        assert mode == 0o600


def test_generate_refuses_overwrite_without_force(tmp_home):
    auth.generate_device_key()
    with pytest.raises(FileExistsError):
        auth.generate_device_key()
    auth.generate_device_key(overwrite=True)  # force must work


def test_signed_headers_verify_against_public_key(tmp_home):
    pub_raw = auth.generate_device_key()
    headers = auth.signed_headers("post", "/v1/chat", body=b"hi", key_id="k1", jwt="jwt")

    assert headers["X-Key-Id"] == "k1"
    assert headers["Authorization"] == "Bearer jwt"

    canonical = "\n".join(
        ["POST", "/v1/chat", headers["X-Timestamp"], headers["X-Nonce"], headers["X-Body-Sha256"]]
    ).encode("utf-8")
    Ed25519PublicKey.from_public_bytes(pub_raw).verify(
        _unb64u(headers["X-Signature"]), canonical
    )  # raises InvalidSignature if tampered


def test_signed_headers_tamper_fails(tmp_home):
    pub_raw = auth.generate_device_key()
    headers = auth.signed_headers("GET", "/v1/ping")
    forged = "\n".join(
        ["GET", "/v1/EVIL", headers["X-Timestamp"], headers["X-Nonce"], headers["X-Body-Sha256"]]
    ).encode("utf-8")
    with pytest.raises(InvalidSignature):
        Ed25519PublicKey.from_public_bytes(pub_raw).verify(_unb64u(headers["X-Signature"]), forged)


def test_device_public_key_std_b64_is_standard_padded(tmp_home):
    """The activation pubkey must be standard base64 (server uses base64.b64decode)."""
    pub_raw = auth.generate_device_key()
    std = auth.device_public_key_std_b64()
    # standard alphabet, padded → round-trips through base64.b64decode
    decoded = base64.b64decode(std)
    assert decoded == pub_raw
    # URL-safe chars must NOT appear (would break server-side standard decode)
    assert "-" not in std and "_" not in std


def test_sign_refresh_verifies_against_device_public_key(tmp_home):
    """sign_refresh must produce a valid ED25519 sig over refresh_token + nonce."""
    pub_raw = auth.generate_device_key()
    sig_b64 = auth.sign_refresh("rt-123", "nonce-abc")
    sig = base64.b64decode(sig_b64)  # standard base64
    payload = ("rt-123" + "nonce-abc").encode("utf-8")
    Ed25519PublicKey.from_public_bytes(pub_raw).verify(sig, payload)  # raises if bad


def test_sign_refresh_rejects_wrong_payload(tmp_home):
    pub_raw = auth.generate_device_key()
    sig = base64.b64decode(auth.sign_refresh("rt-123", "nonce-abc"))
    wrong = ("rt-123" + "nonce-OTHER").encode("utf-8")
    with pytest.raises(InvalidSignature):
        Ed25519PublicKey.from_public_bytes(pub_raw).verify(sig, wrong)


def test_device_fingerprint_is_stable_and_non_secret(tmp_home):
    """Fingerprint is deterministic and derived only from the public key."""
    auth.generate_device_key()
    fp1 = auth.device_fingerprint()
    fp2 = auth.device_fingerprint()
    assert fp1 == fp2  # stable across calls
    assert len(fp1) == 64  # sha256 hex
    # it must NOT be the private key material in any form
    assert fp1 != auth.private_key_path().read_bytes().hex()


def test_token_store_roundtrip_and_clear(tmp_home):
    store = config.TokenStore(jwt="jwt-1", refresh_token="rt-1")
    path = store.save()
    assert path.exists()
    if sys.platform != "win32":
        assert path.stat().st_mode & 0o777 == 0o600

    loaded = config.TokenStore.load()
    assert loaded.jwt == "jwt-1"
    assert loaded.refresh_token == "rt-1"

    loaded.clear()
    assert not path.exists()
    # load() on a missing store yields empty credentials, not an error
    assert config.TokenStore.load().jwt is None


def test_token_store_not_written_to_toml_config(tmp_home):
    """Bearer credentials must never land in the plaintext TOML config."""
    config.TokenStore(jwt="secret-jwt", refresh_token="secret-rt").save()
    cfg = config.Config(device_id="dev-1")
    cfg_path = cfg.save()
    raw = cfg_path.read_text(encoding="utf-8")
    assert "secret-jwt" not in raw
    assert "secret-rt" not in raw
