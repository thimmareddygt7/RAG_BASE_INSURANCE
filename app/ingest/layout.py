"""Layout helpers: multi-column reading order and header/footer removal."""

from __future__ import annotations

import re
from collections import Counter

Block = tuple[float, float, float, float, str]  # x0, y0, x1, y1, text


def order_blocks(blocks: list[Block], page_width: float) -> list[Block]:
    """Reading order for one page.

    If the blocks form two clear columns (narrow blocks starting in the left or right half,
    both halves populated), read the left column top to bottom, then the right column.
    Full-width blocks (headings) are kept in place by splitting the page at them.
    """
    if not blocks:
        return []
    mid = page_width / 2

    def is_wide(b: Block) -> bool:
        return (b[2] - b[0]) > 0.6 * page_width

    ordered: list[Block] = []
    segment: list[Block] = []

    def flush() -> None:
        if not segment:
            return
        left = [b for b in segment if b[0] < mid * 0.9 and b[2] <= mid * 1.1]
        right = [b for b in segment if b[0] >= mid * 0.9]
        if left and right and len(left) + len(right) == len(segment):
            ordered.extend(sorted(left, key=lambda b: (b[1], b[0])))
            ordered.extend(sorted(right, key=lambda b: (b[1], b[0])))
        else:
            ordered.extend(sorted(segment, key=lambda b: (b[1], b[0])))
        segment.clear()

    for b in sorted(blocks, key=lambda b: (b[1], b[0])):
        if is_wide(b):
            flush()
            ordered.append(b)
        else:
            segment.append(b)
    flush()
    return ordered


_DIGITS = re.compile(r"\d+")
_PAGE_NUMBER = re.compile(r"(?i)\bpage\s*\d+|^\s*\d+\s*(?:of|/)\s*\d+\s*$|^\s*-?\s*\d+\s*-?\s*$")


def _normalise(line: str) -> str:
    """Lowercase and trim. Digits are collapsed only on page-number lines, so body lines that
    differ by a number ('Section 3' vs 'Section 4') are never mistaken for a footer."""
    text = line.strip().lower()
    return _DIGITS.sub("#", text) if _PAGE_NUMBER.search(text) else text


def strip_repeated_lines(pages: list[str], edge_lines: int = 3,
                         min_fraction: float = 0.5) -> list[str]:
    """Remove running headers and footers (lines repeated at page edges across pages).

    Page numbers are caught because digits are normalised ('Page 3 of 40' = 'page # of #').
    Needs at least 3 pages to judge repetition.
    """
    if len(pages) < 3:
        return pages
    edge_counts: Counter[str] = Counter()
    split = [p.splitlines() for p in pages]
    for lines in split:
        non_empty = [ln for ln in lines if ln.strip()]
        edge = non_empty[:edge_lines] + non_empty[-edge_lines:]
        edge_counts.update({_normalise(ln) for ln in edge})
    threshold = min_fraction * len(pages)
    repeated = {norm for norm, n in edge_counts.items() if n >= threshold and norm}
    cleaned = []
    for lines in split:
        non_empty_idx = [i for i, ln in enumerate(lines) if ln.strip()]
        edge_idx = set(non_empty_idx[:edge_lines] + non_empty_idx[-edge_lines:])
        kept = [ln for i, ln in enumerate(lines)
                if not (i in edge_idx and _normalise(ln) in repeated)]
        cleaned.append("\n".join(kept))
    return cleaned
