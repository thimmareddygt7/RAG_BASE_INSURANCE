"""Download the documents listed in data/gold/sources.csv into data/raw/.

Safety rules:
  * only rows with license_checked == "yes" are downloaded
  * local_filename must be a plain file name (no folders)
  * if sha256 is filled in, the download is verified against it
  * --pin writes the sha256 of newly downloaded files back into sources.csv
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_BYTES = 200 * 1024 * 1024
SCHEMES = ("http://", "https://", "file://")  # file:// supports offline mirrors and tests


def read_sources(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def write_sources(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch(url: str, dest: Path) -> None:
    """Download to a temp file, enforce a size cap, then move into place."""
    request = urllib.request.Request(url, headers={"User-Agent": "insurance-rag-downloader/0.1"})
    tmp = dest.with_suffix(dest.suffix + ".part")
    size = 0
    with urllib.request.urlopen(request, timeout=60) as response, tmp.open("wb") as out:
        for block in iter(lambda: response.read(1 << 20), b""):
            size += len(block)
            if size > MAX_BYTES:
                tmp.unlink(missing_ok=True)
                raise RuntimeError(f"{url} exceeds the {MAX_BYTES // (1 << 20)} MB limit")
            out.write(block)
    tmp.replace(dest)


def process(row: dict[str, str], raw_dir: Path, pin: bool) -> str:
    """Handle one row. Returns a status: downloaded, exists, skipped or failed."""
    doc_id, url, name = row["doc_id"], row["source_url"].strip(), row["local_filename"].strip()

    if url.startswith("local:"):
        print(f"[bundled] {doc_id}: {url[6:]}")
        return "skipped"
    if not url.startswith(SCHEMES):
        print(f"[skip]    {doc_id}: no usable source_url")
        return "skipped"
    if row["license_checked"].strip().lower() != "yes":
        print(f"[skip]    {doc_id}: license_checked is not 'yes'")
        return "skipped"
    if not name or Path(name).name != name or name.startswith("."):
        print(f"[fail]    {doc_id}: local_filename must be a plain file name")
        return "failed"

    dest = raw_dir / name
    existed = dest.exists()
    if not existed:
        try:
            fetch(url, dest)
        except Exception as exc:  # network errors vary widely
            print(f"[fail]    {doc_id}: {exc}")
            return "failed"

    digest = sha256_of(dest)
    expected = row.get("sha256", "").strip()
    if expected and digest != expected:
        print(f"[fail]    {doc_id}: sha256 mismatch (file changed or corrupted)")
        if not existed:
            dest.unlink()
        return "failed"
    if not expected and pin:
        row["sha256"] = digest
    print(f"[{'exists' if existed else 'ok'}]".ljust(10) + f" {doc_id}: {name}")
    return "exists" if existed else "downloaded"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, default=ROOT / "data/gold/sources.csv")
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data/raw")
    parser.add_argument("--pin", action="store_true", help="record sha256 for new files")
    args = parser.parse_args(argv)

    fields, rows = read_sources(args.sources)
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    results = [process(row, args.raw_dir, args.pin) for row in rows]
    if args.pin:
        write_sources(args.sources, fields, rows)

    failed = results.count("failed")
    print(f"done: {results.count('downloaded')} downloaded, {results.count('exists')} existing, "
          f"{results.count('skipped')} skipped, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
