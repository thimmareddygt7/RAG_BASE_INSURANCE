"""Check that every gold row's evidence text really appears on the page the gold file names.

Run this on a machine that has the PDFs (python scripts/generate_sample_pdfs.py first for the
generated corpus). Needs PyMuPDF or pdfplumber.

  python scripts/check_gold_evidence.py                  # report only
  python scripts/check_gold_evidence.py --write-verified # mark exactly-matched rows `verified`

IMPORTANT: this proves the evidence text is on the stated page. It does NOT prove the gold
answer is right. A person must still read the answers before the benchmark is frozen.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ingest.sources import resolve_path  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MIN_SEGMENT = 6
WEAK_COVERAGE = 0.9


def norm(text: str) -> str:
    text = text.lower().replace("|", " ").replace("\u2019", "'").replace("\u00a0", " ")
    return re.sub(r"\s+", " ", text).strip()


def classify(evidence: str, page_text: str) -> str:
    """exact: every segment of the evidence is on the page. weak: most words are. else missing."""
    page = norm(page_text)
    segments = [norm(s) for s in re.split(r"\.\.\.|\u2026", evidence)]
    segments = [s for s in segments if len(s) >= MIN_SEGMENT]
    if not segments:
        return "missing"
    if all(s in page for s in segments):
        return "exact"
    tokens = set(" ".join(segments).split())
    if tokens and len(tokens & set(page.split())) / len(tokens) >= WEAK_COVERAGE:
        return "weak"
    return "missing"


def read_pages(path: Path, ocr: bool = False) -> dict[int, str]:
    """Page texts from a PDF, using PyMuPDF if installed, else pdfplumber."""
    try:
        import fitz

        with fitz.open(path) as pdf:
            out = {i: p.get_text("text") for i, p in enumerate(pdf, start=1)}
        if ocr:
            from app.ingest.loaders import ocr_fitz_page
            with fitz.open(path) as pdf:
                for i, p in enumerate(pdf, start=1):
                    if len(out[i].strip()) < 30:
                        out[i] = ocr_fitz_page(p, "eng")
        return out
    except ImportError:
        pass
    try:
        import pdfplumber
    except ImportError as exc:
        raise SystemExit("Install PyMuPDF or pdfplumber to read the PDFs.") from exc
    out = {}
    with pdfplumber.open(path) as pdf:
        for i, p in enumerate(pdf.pages, start=1):
            text = p.extract_text() or ""
            if ocr and len(text.strip()) < 30:
                from app.ingest.loaders import ocr_plumber_page
                text = ocr_plumber_page(p, "eng")
            out[i] = text
    return out


def check_rows(rows: list[dict[str, str]],
               pages_of: Callable[[str], dict[int, str] | None]) -> list[dict[str, str]]:
    """One result per answerable row: id, level (exact | weak | missing | no_pdf | no_text |
    bad_page) and a short detail."""
    results = []
    for r in rows:
        if r["answerable"] != "yes":
            continue
        pages = pages_of(r["doc_id"])
        if pages is None:
            results.append({"id": r["id"], "level": "no_pdf", "detail": r["doc_id"]})
            continue
        page_no = int(r["page"])
        if page_no not in pages:
            results.append({"id": r["id"], "level": "bad_page",
                            "detail": f"{r['doc_id']} has {len(pages)} pages, row says {page_no}"})
            continue
        if not pages[page_no].strip():
            results.append({"id": r["id"], "level": "no_text",
                            "detail": f"page {page_no} has no text layer (needs --ocr)"})
            continue
        level = classify(r["evidence_text"], pages[page_no])
        detail = "" if level == "exact" else f"{r['doc_id']} p.{page_no}: {r['evidence_text'][:70]}"
        if r.get("page_2", "").strip():
            doc2 = r.get("doc_id_2") or r["doc_id"]
            pages2 = pages_of(doc2)
            if pages2 is None or int(r["page_2"]) not in pages2:
                level, detail = "bad_page", f"second page {doc2} p.{r['page_2']} does not exist"
        results.append({"id": r["id"], "level": level, "detail": detail})
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gold", type=Path, default=ROOT / "data/gold/gold_questions.csv")
    parser.add_argument("--sources", type=Path, default=ROOT / "data/gold/sources.csv")
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data/raw")
    parser.add_argument("--ocr", action="store_true", help="OCR pages that have no text layer")
    parser.add_argument("--write-verified", action="store_true")
    parser.add_argument("--confirm-absent", action="store_true",
                        help="with --write-verified, also mark unanswerable rows verified. Pass "
                             "this ONLY after you searched the PDFs yourself for each one")
    args = parser.parse_args()

    with args.gold.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields, rows = list(reader.fieldnames or []), list(reader)
    with args.sources.open(newline="", encoding="utf-8") as f:
        paths = {r["doc_id"]: resolve_path(r, args.raw_dir) for r in csv.DictReader(f)}
    cache: dict[str, dict[int, str] | None] = {}

    def pages_of(doc_id: str):
        if doc_id not in cache:
            p = paths.get(doc_id)
            cache[doc_id] = read_pages(p, args.ocr) if p and p.exists() else None
        return cache[doc_id]

    results = check_rows(rows, pages_of)
    counts: dict[str, int] = {}
    for res in results:
        counts[res["level"]] = counts.get(res["level"], 0) + 1
        if res["level"] != "exact":
            print(f"{res['level'].upper():8s} {res['id']}: {res['detail']}")
    print(f"\nchecked {len(results)} answerable rows: {counts}")
    exact = {r["id"] for r in results if r["level"] == "exact"}
    if args.write_verified:
        changed = 0
        for r in rows:
            if r["id"] in exact and r["status"] == "drafted":
                r["status"], changed = "verified", changed + 1
            elif (r["answerable"] == "no" and r["status"] == "drafted"
                  and args.confirm_absent):
                r["status"], changed = "verified", changed + 1
        with args.gold.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        print(f"marked {changed} rows verified. Unanswerable rows stay `drafted` unless you pass "
              "--confirm-absent after searching the PDFs for each one. Read the gold answers "
              "yourself before freezing the file.")
    return 1 if any(r["level"] in ("missing", "bad_page", "no_pdf") for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
