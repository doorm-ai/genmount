# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 DOORM AI PTE. LTD. and Genmount OS Contributors

from __future__ import annotations

import base64
import hashlib
import os
import sys
import time
import uuid
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from genmount.config import keys_dir
from genmount.errors import NotActivatedError

_PRIV_NAME = "device_ed25519"


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64std(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def private_key_path() -> Path:
    return keys_dir() / _PRIV_NAME


def device_key_exists() -> bool:
    return private_key_path().exists()


def generate_device_key(*, overwrite: bool = False) -> bytes:
    path = private_key_path()
    if path.exists() and not overwrite:
        raise FileExistsError(f"device key already exists at {path}")

    priv = Ed25519PrivateKey.generate()
    priv_raw = priv.private_bytes_raw()
    pub_raw = priv.public_key().public_bytes_raw()

    if sys.platform != "win32":
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, priv_raw)
        finally:
            os.close(fd)
        path.chmod(0o600)
    else:
        path.write_bytes(priv_raw)

    return pub_raw


def load_private_key() -> Ed25519PrivateKey:
    path = private_key_path()
    if not path.exists():
        raise NotActivatedError("No device key found. Run `genmount init` first.")
    return Ed25519PrivateKey.from_private_bytes(path.read_bytes())


def public_key_b64() -> str:
    return _b64u(load_private_key().public_key().public_bytes_raw())


def device_public_key_std_b64() -> str:
    return _b64std(load_private_key().public_key().public_bytes_raw())


def device_fingerprint() -> str:
    pub_raw = load_private_key().public_key().public_bytes_raw()
    return hashlib.sha256(b"genmount-device:" + pub_raw).hexdigest()


def sign_refresh(refresh_token: str, nonce: str) -> str:
    payload = (refresh_token + nonce).encode("utf-8")
    sig = load_private_key().sign(payload)
    return _b64std(sig)


def signed_headers(
    method: str,
    path: str,
    *,
    body: bytes = b"",
    key_id: str | None = None,
    jwt: str | None = None,
) -> dict[str, str]:
    priv = load_private_key()
    ts = str(int(time.time()))
    nonce = uuid.uuid4().hex
    body_hash = _b64u(hashlib.sha256(body).digest())
    canonical = "\n".join([method.upper(), path, ts, nonce, body_hash]).encode("utf-8")
    sig = priv.sign(canonical)

    headers = {
        "X-Timestamp": ts,
        "X-Nonce": nonce,
        "X-Body-Sha256": body_hash,
        "X-Signature": _b64u(sig),
    }
    if key_id:
        headers["X-Key-Id"] = key_id
    if jwt:
        headers["Authorization"] = f"Bearer {jwt}"
    return headers
