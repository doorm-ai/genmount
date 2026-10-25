# -*- coding: utf-8 -*-
"""check_public_terms must fail closed without a denylist or with an empty one (L149)."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_public_terms.py"


def test_no_denylist_exits_nonzero(monkeypatch, capsys):
    monkeypatch.delenv("GENMOUNT_TERM_DENYLIST", raising=False)
    monkeypatch.setattr(sys, "argv", ["check_public_terms.py", "--root", "src"])
    # Execute main via runpy-ish: import as module
    import importlib.util
    spec = importlib.util.spec_from_file_location("check_public_terms", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    rc = mod.main()
    assert rc == 2


def test_with_empty_denylist_file_fails_closed(tmp_path, monkeypatch):
    d = tmp_path / "deny.txt"
    d.write_text("# no terms\n", encoding="utf-8")
    monkeypatch.setattr(
        sys, "argv", ["check_public_terms.py", "--denylist", str(d), "--root", "src"]
    )
    import importlib.util
    spec = importlib.util.spec_from_file_location("check_public_terms2", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    # root relative to cwd — run from package root
    monkeypatch.chdir(Path(__file__).resolve().parents[1])
    rc = mod.main()
    assert rc == 2
