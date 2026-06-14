# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 DOORM AI PTE. LTD. and Genmount OS Contributors

from __future__ import annotations

import subprocess
from pathlib import Path

import httpx

from genmount.errors import OllamaUnavailableError

_PROBE_TIMEOUT = 2.0


def is_up(host: str, timeout: float = _PROBE_TIMEOUT) -> bool:
    try:
        resp = httpx.get(f"{host.rstrip('/')}/api/version", timeout=timeout)
        return resp.status_code == 200
    except (httpx.HTTPError, OSError):
        return False


def version(host: str, timeout: float = _PROBE_TIMEOUT) -> str | None:
    try:
        resp = httpx.get(f"{host.rstrip('/')}/api/version", timeout=timeout)
        if resp.status_code == 200:
            ver = resp.json().get("version")
            return ver if isinstance(ver, str) else None
    except (httpx.HTTPError, OSError, ValueError):
        return None
    return None


def local_models(host: str) -> list[str]:
    from ollama import Client

    if not is_up(host):
        return []
    try:
        result = Client(host=host).list()
    except Exception:
        return []
    models = getattr(result, "models", None) or []
    names: list[str] = []
    for m in models:
        name = getattr(m, "model", None) or (m.get("model") if isinstance(m, dict) else None)
        if name:
            names.append(name)
    return names


def has_model(host: str, model_tag: str) -> bool:
    return any(model_tag == n or model_tag in n for n in local_models(host))


def require_up(host: str) -> None:
    if not is_up(host):
        raise OllamaUnavailableError(
            "Ollama is not reachable at "
            f"{host}.\n"
            "  Install: https://ollama.com/download\n"
            "  Then start it (it usually auto-starts; on Linux: `ollama serve`)."
        )


REPEAT_PENALTY = "1.15"


def modelfile_text(gguf_filename: str) -> str:
    return (
        f"FROM ./{gguf_filename}\n"
        f"PARAMETER repeat_penalty {REPEAT_PENALTY}\n"
    )


def install_gguf(host: str, model_name: str, gguf_path: Path) -> None:
    require_up(host)
    mf = gguf_path.parent / "Modelfile"
    mf.write_text(modelfile_text(gguf_path.name), encoding="utf-8")
    proc = subprocess.run(
        ["ollama", "create", model_name, "-f", str(mf)],
        cwd=str(gguf_path.parent),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise OllamaUnavailableError(
            f"`ollama create {model_name}` failed.\n{detail}"
        )
