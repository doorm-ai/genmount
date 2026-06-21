# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 DOORM AI PTE. LTD. and Genmount OS Contributors
"""Output post-processing for local model replies.

The bundled L0 GGUF models are single-epoch QLoRA fine-tunes on long-form
classical corpora. They carry two known cosmetic artifacts in their output
(documented model-side; the real fix is a retrain, not this client):

1. ``corpus_hash=<hex>`` traceability tokens leak into the user-facing text
   (an internal training-data field that should never have reached the answer).
2. A repetition tail: the last lines loop, sometimes a citation tag or a
   ``Corpus <Field>:`` metadata block repeated many times.

This module strips those artifacts so the local chat reads cleanly. It is
deliberately conservative — it only removes unambiguous noise and collapses
*consecutive identical* lines; it never rewrites substantive content.
"""

from __future__ import annotations

import re

# ``corpus_hash=0x054f7a6c`` / ``corpus_hash=8c6b9fbaeacbfdfb`` — with an
# optional leading separator so "(同类, corpus_hash=0x..)" collapses to "(同类)".
_CORPUS_HASH_RE = re.compile(r"\s*[,，;；]?\s*corpus_hash\s*=\s*(?:0x)?[0-9a-f]{4,}", re.IGNORECASE)

# A dumped metadata block line, e.g. " Corpus Hash: 0a8b..", " Corpus Length: 102".
_CORPUS_META_LINE_RE = re.compile(r"^\s*Corpus\s+[A-Za-z]+\s*:.*$", re.IGNORECASE)

# The header that introduces such a dump.
_CORPUS_META_HEADER_RE = re.compile(r"^\s*出典信息\s*[:：]\s*$")

# Empty parentheses left behind after stripping an inner hash, e.g. "()" / "（）".
_EMPTY_PARENS_RE = re.compile(r"[(（]\s*[)）]")

# How many consecutive identical lines to keep before collapsing the rest.
_MAX_CONSECUTIVE_REPEATS = 1


def _strip_corpus_noise(text: str) -> str:
    """Remove corpus_hash tokens and dumped corpus-metadata lines."""
    kept: list[str] = []
    for line in text.splitlines():
        if _CORPUS_META_LINE_RE.match(line) or _CORPUS_META_HEADER_RE.match(line):
            continue
        line = _CORPUS_HASH_RE.sub("", line)
        line = _EMPTY_PARENS_RE.sub("", line)
        kept.append(line)
    return "\n".join(kept)


def _collapse_repeats(text: str) -> str:
    """Collapse runs of consecutive identical (non-blank) lines.

    Guards against the repetition tail where one line loops many times. Blank
    lines are passed through untouched so paragraph spacing is preserved.
    """
    out: list[str] = []
    prev_key: str | None = None
    run = 0
    for line in text.splitlines():
        key = line.strip()
        if not key:
            out.append(line)
            prev_key = None
            run = 0
            continue
        if key == prev_key:
            run += 1
            if run >= _MAX_CONSECUTIVE_REPEATS:
                continue
        else:
            prev_key = key
            run = 0
        out.append(line)
    return "\n".join(out)


def clean_output(text: str) -> str:
    """Strip known L0 output artifacts. Returns cleaned, trimmed text.

    Safe on already-clean text (no-op apart from trailing-whitespace trim).
    """
    if not text:
        return text
    cleaned = _strip_corpus_noise(text)
    cleaned = _collapse_repeats(cleaned)
    # Tidy: drop trailing spaces per line, collapse 3+ blank lines to one gap.
    cleaned = "\n".join(s.rstrip() for s in cleaned.splitlines())
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
