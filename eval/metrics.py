"""Retrieval metrics and the statistics needed to compare stages honestly.

Pages are always 1-indexed PDF pages. FinanceBench-style datasets are 0-indexed,
so convert with `to_one_indexed` before comparing.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

Page = tuple[str, int]  # (doc_id, 1-indexed page)


def to_one_indexed(zero_indexed_page: int) -> int:
    """Convert a 0-indexed page number to the 1-indexed convention used here."""
    return zero_indexed_page + 1


def hit_at_k(ranked: Sequence[Page], gold: set[Page], k: int) -> bool:
    """True if any gold (doc, page) appears in the top k results."""
    return any(item in gold for item in ranked[:k])


def reciprocal_rank(ranked: Sequence[Page], gold: set[Page]) -> float:
    """1/rank of the first gold page, or 0.0 if none is retrieved."""
    for rank, item in enumerate(ranked, start=1):
        if item in gold:
            return 1.0 / rank
    return 0.0


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion (z=1.96)."""
    if n <= 0:
        raise ValueError("n must be positive")
    if not 0 <= successes <= n:
        raise ValueError("successes must be between 0 and n")
    p = successes / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return max(0.0, centre - margin), min(1.0, centre + margin)


def mcnemar_exact(only_a_correct: int, only_b_correct: int) -> float:
    """Two-sided exact McNemar test for two systems on the same questions.

    Pass the number of questions only system A got right and only system B got right.
    Returns the p-value. Questions both got right or both got wrong are ignored.
    """
    n = only_a_correct + only_b_correct
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(only_a_correct, only_b_correct) + 1))
    return min(1.0, 2 * tail / 2**n)


def format_count(successes: int, n: int) -> str:
    """Report counts with a confidence interval, e.g. '117/150 (78.0%, 95% CI 70.7-83.9)'."""
    low, high = wilson_interval(successes, n)
    return f"{successes}/{n} ({100 * successes / n:.1f}%, 95% CI {100 * low:.1f}-{100 * high:.1f})"
