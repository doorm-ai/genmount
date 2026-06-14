# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 DOORM AI PTE. LTD. and Genmount OS Contributors
"""CLI wiring smoke tests (command registration, help, advisory doctor)."""

from __future__ import annotations

from typer.testing import CliRunner

from genmount import config, ollama
from genmount.cli import app

runner = CliRunner()


def test_help_lists_all_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("init", "doctor", "chat", "sync", "upgrade"):
        assert cmd in result.output


def test_doctor_is_advisory_pre_init(monkeypatch, tmp_path):
    # Hermetic: empty dirs (no config/key yet) + Ollama down.
    monkeypatch.setattr(config, "config_dir", lambda: tmp_path / "cfg")
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path / "data")
    monkeypatch.setattr(ollama, "is_up", lambda *a, **k: False)

    result = runner.invoke(app, ["doctor"])
    # Fresh machine (no config/key, Ollama down) is all WARN, never FAIL.
    assert result.exit_code == 0
    assert "genmount" in result.output


def test_no_args_shows_help():
    result = runner.invoke(app, [])
    # no_args_is_help=True → help shown, non-zero exit (Typer convention)
    assert "init" in result.output
