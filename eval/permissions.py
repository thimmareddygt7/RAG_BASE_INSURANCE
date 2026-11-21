"""Permission tests: restricted text must never reach retrieval, the prompt, or the answer."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from app.ingest.sources import SourceDoc
from app.pipeline import RagPipeline


def read_permission_tests(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run_permission_tests(pipeline: RagPipeline, docs: list[SourceDoc],
                         rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Run every case. A `forged_group_in_request` is ignored by design: the pipeline only
    ever receives the group from the verified token (see tests/test_api.py for the HTTP check)."""
    allowed = {d.doc_id: set(d.allowed_groups) for d in docs}
    results = []
    for row in rows:
        group = row["user_group"]
        res = pipeline.ask(row["question"], group=group)
        seen_docs = ({h.chunk.doc_id for h in res.retrieved} | res.context_doc_ids
                     | {c.doc_id for c in res.citations})
        leaked = sorted(d for d in seen_docs if group not in allowed.get(d, set()))
        haystack = " ".join([res.answer, res.prompt] +
                            [h.chunk.text for h in res.retrieved])
        banned = [b for b in row["must_not_contain"].split("|") if b]
        found_banned = [b for b in banned if b in haystack]
        failures = []
        if leaked:
            failures.append(f"leaked documents: {leaked}")
        if found_banned:
            failures.append(f"forbidden text present: {found_banned}")
        if (row["expect_refusal"] == "yes") != res.refused:
            failures.append(f"expect_refusal={row['expect_refusal']} but refused={res.refused}")
        if row["expect_citation_doc"] and row["expect_citation_doc"] not in {
                c.doc_id for c in res.citations}:
            failures.append(f"expected citation of {row['expect_citation_doc']}")
        if row["must_contain"] and row["must_contain"].lower() not in res.answer.lower():
            failures.append(f"answer missing '{row['must_contain']}'")
        results.append({"id": row["id"], "group": group, "passed": not failures,
                        "failures": failures, "leaked": leaked})
    return results
