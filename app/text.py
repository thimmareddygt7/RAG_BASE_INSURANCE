"""Deterministic text helpers (no external tokenizer, so chunking is reproducible)."""

from __future__ import annotations

import re

TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)
WORD_RE = re.compile(r"\w+", re.UNICODE)
NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")

STOPWORDS = frozenset(
    """a an and are as at be by for from has have how in is it its of on or that the this to
    was what when where which who will with under per does do did can may must not any all
    their there than then they them his her you your we our i if into over after before
    about between should would could many much""".split()
)


def token_spans(text: str) -> list[tuple[int, int]]:
    """Character spans of word and punctuation tokens."""
    return [m.span() for m in TOKEN_RE.finditer(text)]


def count_tokens(text: str) -> int:
    return len(TOKEN_RE.findall(text))


def words(text: str) -> list[str]:
    return [w.lower() for w in WORD_RE.findall(text)]


def _stem(word: str) -> str:
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def content_words(text: str) -> list[str]:
    """Lowercase, stopword-free, lightly stemmed words (digits excluded)."""
    return [_stem(w) for w in words(text) if w not in STOPWORDS and not w.isdigit()]


def numbers(text: str) -> set[str]:
    """Numbers with thousands separators removed: '5,00,000' -> '500000'."""
    return {n.replace(",", "").rstrip(".") for n in NUMBER_RE.findall(text)}
