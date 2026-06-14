# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 DOORM AI PTE. LTD. and Genmount OS Contributors

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomli_w
from platformdirs import PlatformDirs

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

APP_NAME = "genmount"
APP_AUTHOR = "Genmount"

_DIRS = PlatformDirs(APP_NAME, APP_AUTHOR)

DEFAULT_CLOUD_ENDPOINT = "https://api.genmount.com"
DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL_TAG = "genmount/genmount-small"


def config_dir() -> Path:
    return Path(_DIRS.user_config_dir)


def data_dir() -> Path:
    return Path(_DIRS.user_data_dir)


def keys_dir() -> Path:
    d = data_dir() / "keys"
    d.mkdir(parents=True, exist_ok=True)
    if sys.platform != "win32":
        d.chmod(0o700)
    return d


def config_path() -> Path:
    return config_dir() / "config.toml"


@dataclass
class Config:

    cloud_endpoint: str = DEFAULT_CLOUD_ENDPOINT
    ollama_host: str = DEFAULT_OLLAMA_HOST
    model_tag: str = DEFAULT_MODEL_TAG
    device_id: str | None = None
    tier: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls) -> Config:
        path = config_path()
        if not path.exists():
            return cls()
        with path.open("rb") as f:
            data = tomllib.load(f)
        known = {"cloud_endpoint", "ollama_host", "model_tag", "device_id", "tier"}
        return cls(
            cloud_endpoint=data.get("cloud_endpoint", DEFAULT_CLOUD_ENDPOINT),
            ollama_host=data.get("ollama_host", DEFAULT_OLLAMA_HOST),
            model_tag=data.get("model_tag", DEFAULT_MODEL_TAG),
            device_id=data.get("device_id"),
            tier=data.get("tier"),
            extra={k: v for k, v in data.items() if k not in known},
        )

    def save(self) -> Path:
        path = config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "cloud_endpoint": self.cloud_endpoint,
            "ollama_host": self.ollama_host,
            "model_tag": self.model_tag,
            **self.extra,
        }
        if self.device_id is not None:
            payload["device_id"] = self.device_id
        if self.tier is not None:
            payload["tier"] = self.tier
        with path.open("wb") as f:
            tomli_w.dump(payload, f)
        return path


def token_store_path() -> Path:
    return data_dir() / "tokens.json"


@dataclass
class TokenStore:

    jwt: str | None = None
    refresh_token: str | None = None

    @classmethod
    def load(cls) -> TokenStore:
        path = token_store_path()
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return cls()
        jwt = data.get("jwt")
        refresh = data.get("refresh_token")
        return cls(
            jwt=jwt if isinstance(jwt, str) else None,
            refresh_token=refresh if isinstance(refresh, str) else None,
        )

    def save(self) -> Path:
        path = token_store_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"jwt": self.jwt, "refresh_token": self.refresh_token}
        blob = json.dumps(payload).encode("utf-8")
        if sys.platform != "win32":
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            try:
                os.write(fd, blob)
            finally:
                os.close(fd)
            path.chmod(0o600)
        else:
            path.write_bytes(blob)
        return path

    def clear(self) -> None:
        path = token_store_path()
        if path.exists():
            path.unlink()
