#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 DOORM AI PTE. LTD. and Genmount OS Contributors
"""Public-term scan — fail if a forbidden internal term appears in the source.

The denylist is intentionally **NOT stored in this public repo** — governance is
its single source. Supply it at scan time via:

  python scripts/check_public_terms.py --denylist PATH
  GENMOUNT_TERM_DENYLIST=PATH python scripts/check_public_terms.py

Denylist file format: one term per line; blank lines and `#` comments ignored.
If no denylist is supplied, or the file yields 0 terms, the scan **fails closed** (exit 2). CI must wire it
(e.g. write a repository secret to a file, then pass --denylist).

This script ships only the *mechanism*; it embeds no forbidden words, so the
public client surface never carries the internal vocabulary (CLAUDE.md §2).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def load_denylist(path: str) -> list[str]:
    terms: list[str] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            terms.append(s)
    return terms


def main() -> int:
    ap = argparse.ArgumentParser(description="Scan source for forbidden public terms.")
    ap.add_argument("--denylist", default=os.environ.get("GENMOUNT_TERM_DENYLIST"))
    ap.add_argument("--root", default="src", help="directory to scan")
    args = ap.parse_args()

    if not args.denylist:
        print(
            "[term-scan] FAIL: no denylist supplied (--denylist / GENMOUNT_TERM_DENYLIST). "
            "Refusing to pass open. CI must wire the governance denylist.",
            file=sys.stderr,
        )
        return 2
    if not Path(args.denylist).exists():
        print(
            f"[term-scan] FAIL: denylist path does not exist: {args.denylist}",
            file=sys.stderr,
        )
        return 2

    terms = load_denylist(args.denylist)
    if not terms:
        print(
            "[term-scan] FAIL: denylist is empty (0 terms). "
            "Refusing to pass open ? CI secret missing/blank would otherwise fail open.",
            file=sys.stderr,
        )
        return 2
    hits: list[tuple[str, str]] = []
    for p in Path(args.root).rglob("*.py"):
        text = p.read_text(encoding="utf-8", errors="ignore")
        for term in terms:
            if term in text:
                hits.append((str(p), term))

    if hits:
        print("[term-scan] FORBIDDEN terms found in public surface:")
        for f, t in hits:
            print(f"  {f}: {t!r}")
        return 1

    print(f"[term-scan] clean — {len(terms)} terms checked over '{args.root}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
