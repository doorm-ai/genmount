# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 DOORM AI PTE. LTD. and Genmount OS Contributors
"""Tests for local-output post-processing (genmount.sanitize).

Inputs mirror the real artifacts observed in the L0 GGUF end-to-end re-test:
inline corpus_hash tokens, dumped Corpus-metadata blocks, and repetition tails.
"""

from __future__ import annotations

from genmount.sanitize import clean_output


def test_empty_and_clean_text_passthrough():
    assert clean_output("") == ""
    clean = "病机:外感风寒。\n治法:解表散寒。"
    assert clean_output(clean) == clean


def test_strips_inline_corpus_hash_0x():
    text = "「香苏散」 → 「方剂学」(同类, corpus_hash=0x054f7a6c)"
    out = clean_output(text)
    assert "corpus_hash" not in out
    assert "0x054f7a6c" not in out
    assert out == "「香苏散」 → 「方剂学」(同类)"


def test_strips_inline_corpus_hash_plain_hex():
    text = "固经丸:main_entity = 方剂; corpus_hash=8c6b9fbaeacbfdfb"
    out = clean_output(text)
    assert "corpus_hash" not in out
    assert "8c6b9fbaeacbfdfb" not in out
    assert out.startswith("固经丸:main_entity = 方剂")


def test_strips_citation_with_trailing_hash_keeps_source():
    text = "出典:《金匮要略》;corpus_hash=0a8b7f9cbeebdce4"
    out = clean_output(text)
    assert "corpus_hash" not in out
    assert "《金匮要略》" in out


def test_drops_corpus_metadata_dump_block():
    text = (
        "出典:《傷寒論辯證廣注》\n"
        "出典信息:\n"
        " Corpus Hash: 0a8b7f9cbeebdce4\n"
        " Corpus Length: 102\n"
        " Corpus Offset: 0\n"
        " Corpus Encoding: utf-8\n"
        "结论:先表后里。"
    )
    out = clean_output(text)
    assert "Corpus Hash" not in out
    assert "Corpus Length" not in out
    assert "出典信息" not in out
    assert "《傷寒論辯證廣注》" in out
    assert "结论:先表后里。" in out


def test_collapses_consecutive_repetition_tail():
    text = "治法:疏肝。\n" + "\n".join(["(出典:《方剂学》)"] * 12)
    out = clean_output(text)
    assert out.count("(出典:《方剂学》)") == 1
    assert "治法:疏肝。" in out


def test_keeps_distinct_lines_and_blank_spacing():
    text = "病机:肝郁。\n\n治法:疏肝解郁。\n方:逍遥散。"
    out = clean_output(text)
    assert "病机:肝郁。" in out
    assert "治法:疏肝解郁。" in out
    assert "方:逍遥散。" in out
    # A genuine blank-line paragraph break survives.
    assert "\n\n" in out


def test_non_consecutive_duplicates_are_kept():
    # Same line twice but separated by other content — not a repetition loop.
    text = "见表证。\n另有里证。\n见表证。"
    out = clean_output(text)
    assert out.count("见表证。") == 2
