"""Reads sources.csv into typed records and works out which version of each policy is latest."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True)
class SourceDoc:
    doc_id: str
    kind: str
    insurer: str
    product: str
    version: str
    path: Path | None
    allowed_groups: tuple[str, ...]
    is_latest: bool = True

    @property
    def title(self) -> str:
        label = f"{self.insurer} {self.product}".strip()
        return f"{label} ({self.version})" if label and self.version else (label or self.doc_id)


def version_key(version: str) -> tuple[int, ...]:
    """'v2' -> (2,), '2024-06' -> (2024, 6), '1.10' -> (1, 10). Empty -> ()."""
    return tuple(int(n) for n in re.findall(r"\d+", version))


def compute_latest(docs: list[SourceDoc]) -> dict[str, bool]:
    """Within each (insurer, product) group, only the highest version is latest."""
    groups: dict[tuple[str, str], list[SourceDoc]] = {}
    for d in docs:
        if d.product:
            groups.setdefault((d.insurer, d.product), []).append(d)
    latest = {d.doc_id: True for d in docs}
    for members in groups.values():
        best = max(members, key=lambda d: version_key(d.version))
        for d in members:
            latest[d.doc_id] = d.doc_id == best.doc_id
    return latest


def resolve_path(row: dict[str, str], raw_dir: Path) -> Path | None:
    url = row.get("source_url", "").strip()
    if url.startswith("local:"):
        return ROOT / url[len("local:"):]
    name = row.get("local_filename", "").strip()
    return raw_dir / name if name else None


def load_sources(csv_path: Path, raw_dir: Path, valid_groups: list[str]) -> list[SourceDoc]:
    with csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    docs = []
    for r in rows:
        groups = tuple(g.strip() for g in r.get("allowed_groups", "").split("|") if g.strip())
        unknown = set(groups) - set(valid_groups)
        if not groups or unknown:
            raise ValueError(f"{r['doc_id']}: allowed_groups {groups} invalid; "
                             f"valid groups are {valid_groups}")
        docs.append(SourceDoc(r["doc_id"], r.get("kind", ""), r.get("insurer", ""),
                              r.get("product", ""), r.get("version", ""),
                              resolve_path(r, raw_dir), groups))
    latest = compute_latest(docs)
    return [SourceDoc(d.doc_id, d.kind, d.insurer, d.product, d.version, d.path,
                      d.allowed_groups, latest[d.doc_id]) for d in docs]
