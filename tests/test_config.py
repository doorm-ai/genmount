# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 DOORM AI PTE. LTD. and Genmount OS Contributors
"""Tests for cross-platform config load/save (no secrets stored in config)."""

from __future__ import annotations

from genmount import config


def test_config_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "config_dir", lambda: tmp_path)
    cfg = config.Config(
        cloud_endpoint="https://x.example", model_tag="m", device_id="dev-1", tier="L2"
    )
    saved = cfg.save()
    assert saved.exists()

    loaded = config.Config.load()
    assert loaded.cloud_endpoint == "https://x.example"
    assert loaded.model_tag == "m"
    assert loaded.device_id == "dev-1"
    assert loaded.tier == "L2"


def test_config_defaults_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "config_dir", lambda: tmp_path / "absent")
    cfg = config.Config.load()
    assert cfg.cloud_endpoint == config.DEFAULT_CLOUD_ENDPOINT
    assert cfg.ollama_host == config.DEFAULT_OLLAMA_HOST
    assert cfg.device_id is None
