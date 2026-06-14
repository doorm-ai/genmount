# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 DOORM AI PTE. LTD. and Genmount OS Contributors

from __future__ import annotations

import hashlib
import json as _json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from genmount import auth
from genmount.config import Config
from genmount.errors import CloudUnavailableError, IntegrityError

_TIMEOUT = 30.0


@dataclass
class CloudClient:
    config: Config
    jwt: str | None = None

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        signed: bool = True,
    ) -> dict[str, Any]:
        body = _json.dumps(payload).encode("utf-8") if payload is not None else b""
        if signed:
            headers = auth.signed_headers(
                method, path, body=body, key_id=self.config.device_id, jwt=self.jwt
            )
        else:
            headers = {}
            if self.jwt:
                headers["Authorization"] = f"Bearer {self.jwt}"
        if payload is not None:
            headers["Content-Type"] = "application/json"
        url = self.config.cloud_endpoint.rstrip("/") + path
        try:
            resp = httpx.request(method, url, content=body, headers=headers, timeout=_TIMEOUT)
        except (httpx.HTTPError, OSError):
            raise CloudUnavailableError(
                f"Cloud not reachable at {self.config.cloud_endpoint}."
            ) from None
        if resp.status_code >= 400:
            raise _error_from_response(resp)
        try:
            data = resp.json()
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}

    def activate(self, activation_code: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/auth/activate",
            {
                "activation_code": activation_code,
                "device_public_key_b64": auth.device_public_key_std_b64(),
                "device_fingerprint": auth.device_fingerprint(),
            },
            signed=False,
        )

    def refresh(self, refresh_token: str) -> dict[str, Any]:
        nonce = uuid.uuid4().hex
        signature_b64 = auth.sign_refresh(refresh_token, nonce)
        return self._request(
            "POST",
            "/auth/refresh",
            {
                "refresh_token": refresh_token,
                "device_signature_b64": signature_b64,
                "nonce": nonce,
            },
            signed=False,
        )

    def register(
        self, *, name: str, organization: str, email: str, use_case: str
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/auth/register",
            {
                "name": name,
                "organization": organization,
                "email": email,
                "use_case": use_case,
                "accept_license": True,
                "accept_disclaimer": True,
            },
            signed=False,
        )

    def list_models(self) -> dict[str, Any]:
        return self._request("GET", "/registry/list", None, signed=False)

    def chat(self, prompt: str) -> str:
        raise CloudUnavailableError("Cloud chat is not available yet.")

    def sync(self) -> None:
        raise CloudUnavailableError("Cloud sync is not available yet.")


def _error_from_response(resp: httpx.Response) -> CloudUnavailableError:
    code = trace = None
    retriable = False
    try:
        root = resp.json()
        err = root.get("detail", root) if isinstance(root, dict) else {}
        if isinstance(err, dict):
            err = err.get("error", err)
        if isinstance(err, dict):
            code = err.get("code")
            trace = err.get("trace_id")
            retriable = bool(err.get("retriable"))
    except (ValueError, AttributeError):
        pass

    parts = [f"Cloud request failed (HTTP {resp.status_code})"]
    if code:
        parts.append(f"code={code}")
    if trace:
        parts.append(f"trace={trace}")
    if retriable:
        parts.append("retriable")
    return CloudUnavailableError("; ".join(parts))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_model(
    url: str, dest: Path, expected_sha256: str, *, timeout: float = 600.0
) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    digest = hashlib.sha256()
    try:
        with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as resp:
            if resp.status_code >= 400:
                raise CloudUnavailableError(
                    f"Model download failed (HTTP {resp.status_code})."
                )
            with open(tmp, "wb") as fh:
                for chunk in resp.iter_bytes():
                    fh.write(chunk)
                    digest.update(chunk)
    except (httpx.HTTPError, OSError):
        tmp.unlink(missing_ok=True)
        raise CloudUnavailableError("Model download interrupted.") from None
    if digest.hexdigest() != expected_sha256.lower():
        tmp.unlink(missing_ok=True)
        raise IntegrityError(
            "Downloaded file failed sha256 verification and was discarded."
        )
    tmp.replace(dest)
    return dest
