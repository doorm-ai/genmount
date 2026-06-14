# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 DOORM AI PTE. LTD. and Genmount OS Contributors
"""Tests for the cloud transport: error-envelope parsing + neutrality.

Critically asserts that the client never surfaces the server's human
message/title (which may carry server-side vocabulary) — only neutral fields.
"""

from __future__ import annotations

import base64
import json

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from genmount import auth, config
from genmount.api import CloudClient, _error_from_response
from genmount.config import Config
from genmount.errors import CloudUnavailableError


def _resp(status: int, payload: dict) -> httpx.Response:
    return httpx.Response(status_code=status, json=payload)


@pytest.fixture
def tmp_home(tmp_path, monkeypatch):
    """Isolate the data/config dirs so a real device key can be generated."""
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path / "data")
    monkeypatch.setattr(config, "config_dir", lambda: tmp_path / "cfg")
    return tmp_path


class _Capture:
    """Captures the outgoing request and returns a canned response."""

    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.method: str | None = None
        self.url: str | None = None
        self.headers: dict | None = None
        self.body: bytes | None = None

    def __call__(self, method, url, *, content=b"", headers=None, timeout=None):
        self.method = method
        self.url = url
        self.headers = dict(headers or {})
        self.body = content
        return self.response

    @property
    def sent(self) -> dict:
        assert self.body is not None
        return json.loads(self.body.decode("utf-8"))


def test_error_surfaces_only_neutral_fields():
    # The server's human title/message may carry server-side vocabulary; the
    # client must surface ONLY neutral fields (code / trace_id / retriable) and
    # never echo the human strings. Sentinels stand in for whatever the server
    # sends, so this test never embeds real server vocabulary in client source.
    payload = {
        "error": {
            "code": "WMOS-TCM-0001",
            "title": "SERVER_TITLE_SENTINEL",  # server vocabulary — must NOT leak
            "message": "SERVER_MESSAGE_SENTINEL must not leak",  # must NOT leak
            "retriable": True,
            "trace_id": "abc123",
        }
    }
    err = _error_from_response(_resp(422, payload))
    text = str(err)
    assert "WMOS-TCM-0001" in text
    assert "abc123" in text
    assert "retriable" in text
    # neutrality: server human strings must not appear on the client surface
    assert "SERVER_TITLE_SENTINEL" not in text
    assert "SERVER_MESSAGE_SENTINEL" not in text


def test_error_handles_malformed_envelope():
    err = _error_from_response(_resp(500, {"unexpected": "shape"}))
    assert isinstance(err, CloudUnavailableError)
    assert "HTTP 500" in str(err)


def test_request_unreachable_cloud_raises(monkeypatch):
    # avoid needing a real device key — focus on transport behaviour
    monkeypatch.setattr("genmount.auth.signed_headers", lambda *a, **k: {})

    def boom(*a, **k):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(httpx, "request", boom)
    client = CloudClient(Config(cloud_endpoint="https://nope.example", device_id=None))
    try:
        client._request("GET", "/ping")
    except CloudUnavailableError as exc:
        assert "not reachable" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected CloudUnavailableError")


# --- /auth/activate contract -------------------------------------------------


def test_activate_sends_exact_server_dto_fields(tmp_home, monkeypatch):
    """Request body must match ActivateRequest byte-for-byte (extra='forbid')."""
    auth.generate_device_key()
    cap = _Capture(
        _resp(
            200,
            {
                "device_id": "dev-123",
                "jwt": "jwt.token.here",
                "refresh_token": "refresh-abc",
                "tier": "L2",
                "registry_url": "/registry/list",
            },
        )
    )
    monkeypatch.setattr(httpx, "request", cap)

    client = CloudClient(Config(cloud_endpoint="https://api.example"))
    result = client.activate("a1b2c3d4")

    # exact request fields (the server's ActivateRequest is frozen + extra=forbid)
    assert cap.url == "https://api.example/auth/activate"
    assert set(cap.sent.keys()) == {
        "activation_code",
        "device_public_key_b64",
        "device_fingerprint",
    }
    assert cap.sent["activation_code"] == "a1b2c3d4"

    # device_public_key_b64 must be STANDARD base64 (server uses base64.b64decode)
    pub = base64.b64decode(cap.sent["device_public_key_b64"])  # raises if not std b64
    assert len(pub) == 32
    Ed25519PublicKey.from_public_bytes(pub)  # valid ed25519 public key

    # response parsing reads the server's ActivateResponse fields
    assert result["device_id"] == "dev-123"
    assert result["jwt"] == "jwt.token.here"
    assert result["refresh_token"] == "refresh-abc"
    assert result["tier"] == "L2"
    assert result["registry_url"] == "/registry/list"

    # activate is unauthenticated/allowlisted: no Bearer, no signing headers
    assert "Authorization" not in cap.headers
    assert "X-Signature" not in cap.headers


# --- /auth/refresh contract --------------------------------------------------


def test_refresh_sends_exact_server_dto_fields_and_valid_signature(tmp_home, monkeypatch):
    """Request body must match RefreshRequest; signature must verify against the key."""
    pub_raw = auth.generate_device_key()
    cap = _Capture(_resp(200, {"jwt": "new.jwt", "expires_at": "2026-06-08T12:00:00+00:00"}))
    monkeypatch.setattr(httpx, "request", cap)

    client = CloudClient(Config(cloud_endpoint="https://api.example"))
    result = client.refresh("refresh-token-xyz")

    assert cap.url == "https://api.example/auth/refresh"
    assert set(cap.sent.keys()) == {"refresh_token", "device_signature_b64", "nonce"}
    assert cap.sent["refresh_token"] == "refresh-token-xyz"

    # the signature must be a valid ED25519 sig over (refresh_token + nonce),
    # standard base64 (the server decodes it with base64.b64decode)
    nonce = cap.sent["nonce"]
    sig = base64.b64decode(cap.sent["device_signature_b64"])
    payload = ("refresh-token-xyz" + nonce).encode("utf-8")
    Ed25519PublicKey.from_public_bytes(pub_raw).verify(sig, payload)  # raises if bad

    # response parsing reads RefreshResponse fields
    assert result["jwt"] == "new.jwt"
    assert result["expires_at"] == "2026-06-08T12:00:00+00:00"


def test_refresh_nonce_is_fresh_per_call(tmp_home, monkeypatch):
    """Each refresh call must use a fresh nonce (server rejects replays)."""
    auth.generate_device_key()
    seen: list[str] = []

    def fake_request(method, url, *, content=b"", headers=None, timeout=None):
        seen.append(json.loads(content.decode("utf-8"))["nonce"])
        return _resp(200, {"jwt": "j", "expires_at": "2026-06-08T12:00:00+00:00"})

    monkeypatch.setattr(httpx, "request", fake_request)
    client = CloudClient(Config(cloud_endpoint="https://api.example"))
    client.refresh("rt")
    client.refresh("rt")
    assert len(seen) == 2
    assert seen[0] != seen[1]


def test_activate_maps_server_error_to_neutral_message(tmp_home, monkeypatch):
    """A FastAPI-nested error envelope surfaces only neutral fields."""
    auth.generate_device_key()
    cap = _Capture(
        _resp(
            422,
            {
                "detail": {
                    "error": {
                        "code": "WMOS-AUTH-0001",
                        "title": "activation failed",
                        "message": "activation code not found",
                        "retriable": False,
                        "trace_id": "tr-9",
                    }
                }
            },
        )
    )
    monkeypatch.setattr(httpx, "request", cap)
    client = CloudClient(Config(cloud_endpoint="https://api.example"))
    with pytest.raises(CloudUnavailableError) as exc:
        client.activate("badcode1")
    text = str(exc.value)
    assert "WMOS-AUTH-0001" in text
    assert "tr-9" in text
    # server human strings must not leak
    assert "activation failed" not in text
    assert "not found" not in text
