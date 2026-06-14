# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 DOORM AI PTE. LTD. and Genmount OS Contributors
"""Tests for Ollama liveness probe (graceful when the server is down)."""

from __future__ import annotations

import httpx

from genmount import ollama
from genmount.errors import OllamaUnavailableError


def test_is_up_false_on_connection_error(monkeypatch):
    def boom(*a, **k):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(httpx, "get", boom)
    assert ollama.is_up("http://127.0.0.1:11434") is False


def test_is_up_true_on_200(monkeypatch):
    class _Resp:
        status_code = 200

        def json(self):
            return {"version": "0.1.2"}

    monkeypatch.setattr(httpx, "get", lambda *a, **k: _Resp())
    assert ollama.is_up("http://h") is True
    assert ollama.version("http://h") == "0.1.2"


def test_require_up_raises_when_down(monkeypatch):
    monkeypatch.setattr(ollama, "is_up", lambda *a, **k: False)
    try:
        ollama.require_up("http://127.0.0.1:11434")
    except OllamaUnavailableError as exc:
        assert "Ollama is not reachable" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected OllamaUnavailableError")
