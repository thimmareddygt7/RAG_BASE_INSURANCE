"""No-API-key demo: the same question asked by three users, with permissions enforced.

Uses deterministic offline stand-ins (hashing embedder, extractive answerer), so answers are
simple quotes. It demonstrates access control and citations, not language-model quality.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_settings  # noqa: E402
from app.dataset import get_dataset, sync_dataset  # noqa: E402
from app.pipeline import build_pipeline  # noqa: E402

QUESTIONS = [
    "What is the room rent limit per day?",
    "What is the Gold tier commission?",
    "How did the room rent limit change between versions?",
]

if __name__ == "__main__":
    settings = load_settings(stage="stage4_rerank")
    pipeline = build_pipeline(settings, offline=True)
    sync_dataset(pipeline, settings, get_dataset(settings, "synthetic"), True)
    print(f"{settings.get('app.disclaimer')} | offline stand-ins, synthetic documents\n")
    for question in QUESTIONS:
        print(f"Q: {question}")
        for group in ("policyholder", "agent", "admin"):
            scope = "all" if "versions" in question else "latest"
            r = pipeline.ask(question, group, scope)
            cites = ", ".join(f"{c.doc_id} p.{c.page}{'' if c.verified else ' (UNVERIFIED)'}"
                              for c in r.citations) or "no citations"
            print(f"  {group:13s} -> {r.answer[:95]}  [{cites}]")
        print()
