"""Citation extraction and verification: does the cited page really support the claim?"""

from __future__ import annotations

import re

from app.models import Citation, Hit
from app.text import content_words, numbers

CITATION_RE = re.compile(r"\[\s*([A-Za-z0-9_.\-]+)\s*,?\s*p\.?\s*(\d+)\s*\]")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
MIN_OVERLAP = 0.6


def _last_sentence(segment: str) -> str:
    parts = [p.strip() for p in SENTENCE_SPLIT.split(segment) if p.strip()]
    return parts[-1] if parts else ""


def extract_claims(answer: str) -> list[tuple[str, int, str]]:
    """Return (doc_id, page, claim) for each citation marker.

    The claim is the last sentence before the marker. Adjacent markers share a claim.
    """
    answer = answer.replace("【", "[").replace("】", "]")
    claims: list[tuple[str, int, str]] = []
    cursor = 0
    previous = ""
    for m in CITATION_RE.finditer(answer):
        segment = answer[cursor:m.start()].lstrip(" .;:,-")
        claim = _last_sentence(segment) or previous
        claims.append((m.group(1), int(m.group(2)), claim))
        previous = claim
        cursor = m.end()
    return claims


def claim_supported(claim: str, evidence: str) -> bool:
    """Every number in the claim must appear in the evidence, and enough content words must."""
    if not claim:
        return False
    if not numbers(claim) <= numbers(evidence):
        return False
    words = set(content_words(claim))
    if not words:
        return False
    found = len(words & set(content_words(evidence)))
    return found / len(words) >= MIN_OVERLAP


def verify_citations(answer: str, context_hits: list[Hit]) -> list[Citation]:
    """Check each marker against the chunks of that doc and page that the LLM was shown."""
    by_page: dict[tuple[str, int], list[str]] = {}
    for h in context_hits:
        by_page.setdefault((h.chunk.doc_id, h.chunk.page), []).append(h.chunk.text)
    results = []
    for doc_id, page, claim in extract_claims(answer):
        texts = by_page.get((doc_id, page))
        in_context = texts is not None
        verified = in_context and claim_supported(claim, "\n".join(texts))
        results.append(Citation(doc_id, page, in_context, verified, claim))
    return results
