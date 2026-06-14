# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 DOORM AI PTE. LTD. and Genmount OS Contributors
"""sync chain: download + sha256 gate + Modelfile (repeat_penalty pinned) + CLI flow."""

from __future__ import annotations

import hashlib

import httpx
import pytest
from typer.testing import CliRunner

from genmount import api, config, ollama
from genmount.cli import app
from genmount.errors import IntegrityError

runner = CliRunner()

_PAYLOAD = b"fake-gguf-bytes" * 1024
_SHA = hashlib.sha256(_PAYLOAD).hexdigest()


def _stream_patch(monkeypatch, status=200, payload=_PAYLOAD):
    transport = httpx.MockTransport(lambda request: httpx.Response(status, content=payload))
    real_stream = httpx.stream

    def fake_stream(method, url, **kw):
        kw.pop("timeout", None)
        kw.pop("follow_redirects", None)
        client = httpx.Client(transport=transport)
        return client.stream(method, url)

    monkeypatch.setattr(httpx, "stream", fake_stream)
    return real_stream


def test_download_model_verifies_sha256(tmp_path, monkeypatch):
    _stream_patch(monkeypatch)
    dest = tmp_path / "m" / "model.gguf"
    out = api.download_model("https://cdn.example.com/m.gguf", dest, _SHA.upper())
    assert out == dest and dest.exists()
    assert api.file_sha256(dest) == _SHA
    assert not dest.with_suffix(".gguf.part").exists()


def test_download_model_rejects_corrupt_file(tmp_path, monkeypatch):
    _stream_patch(monkeypatch)
    dest = tmp_path / "model.gguf"
    with pytest.raises(IntegrityError):
        api.download_model("https://cdn.example.com/m.gguf", dest, "0" * 64)
    assert not dest.exists()
    assert not dest.with_suffix(".gguf.part").exists()


def test_modelfile_pins_repeat_penalty():
    text = ollama.modelfile_text("model.gguf")
    assert "FROM ./model.gguf" in text
    assert "PARAMETER repeat_penalty 1.15" in text


def test_sync_end_to_end_flow(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "config_dir", lambda: tmp_path / "cfg")
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path / "data")

    entries = {
        "entries": [
            {
                "adapter_version": "v1-aaaabbbb-00000000",
                "tier": "L2",
                "sha256": _SHA,
                "size_bytes": len(_PAYLOAD),
                "base_model": "llama3.2-3b",
                "quant": "Q4_K_M",
                "gguf_url": "https://cdn.example.com/v1.gguf",
            },
            {
                "adapter_version": "v1-ccccdddd-00000000",
                "tier": "L3",
                "sha256": _SHA,
                "size_bytes": 1,
                "base_model": "llama3.1-8b",
                "quant": None,
                "gguf_url": None,
            },
        ]
    }
    monkeypatch.setattr("genmount.api.CloudClient.list_models", lambda self: entries)
    _stream_patch(monkeypatch)
    installed: list[tuple[str, str]] = []
    monkeypatch.setattr(
        ollama,
        "install_gguf",
        lambda host, name, path: installed.append((name, path.name)),
    )

    result = runner.invoke(app, ["sync", "--use"])
    assert result.exit_code == 0, result.output
    assert installed == [("genmount-v1-aaaabbbb-00000000", "v1-aaaabbbb-00000000.gguf")]
    assert "sha256 verified" in result.output
    assert "not a diagnosis" in result.output

    cfg = config.Config.load()
    assert cfg.model_tag == "genmount-v1-aaaabbbb-00000000"

    result2 = runner.invoke(app, ["sync"])
    assert result2.exit_code == 0, result2.output
    assert "skipping download" in result2.output


def test_sync_no_entries_message(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "config_dir", lambda: tmp_path / "cfg")
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path / "data")
    monkeypatch.setattr("genmount.api.CloudClient.list_models", lambda self: {"entries": []})
    result = runner.invoke(app, ["sync"])
    assert result.exit_code == 0
    assert "No downloadable models" in result.output


def test_init_register_flow(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "config_dir", lambda: tmp_path / "cfg")
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path / "data")

    captured: dict = {}

    def fake_register(self, **kw):
        captured.update(kw)
        return {"activation_code": "a" * 32, "user_id": "u-x", "tier": "L2"}

    def fake_activate(self, code):
        captured["activated_with"] = code
        return {"device_id": "d-1", "tier": "L2", "jwt": "j", "refresh_token": "r"}

    monkeypatch.setattr("genmount.api.CloudClient.register", fake_register)
    monkeypatch.setattr("genmount.api.CloudClient.activate", fake_activate)

    result = runner.invoke(
        app,
        [
            "init",
            "--register",
            "--name",
            "Tester",
            "--org",
            "Clinic",
            "--email",
            "t@example.com",
            "--use-case",
            "education",
        ],
        input="y\ny\n",
    )
    assert result.exit_code == 0, result.output
    assert captured["email"] == "t@example.com"
    assert captured["activated_with"] == "a" * 32
    assert "Registered" in result.output
    assert "activated" in result.output


def test_init_register_declined_license_aborts(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "config_dir", lambda: tmp_path / "cfg")
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path / "data")
    called = []
    monkeypatch.setattr(
        "genmount.api.CloudClient.register",
        lambda self, **kw: called.append(kw) or {},
    )
    result = runner.invoke(
        app,
        [
            "init",
            "--register",
            "--name",
            "T",
            "--org",
            "O",
            "--email",
            "t@e.com",
            "--use-case",
            "edu",
        ],
        input="n\n",
    )
    assert result.exit_code == 1
    assert called == []
