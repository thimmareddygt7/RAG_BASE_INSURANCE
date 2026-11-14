"""Incremental indexing: hash each file, skip unchanged ones, replace chunks of changed ones."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.embeddings import Embedder
from app.ingest.chunking import DocMeta, build_chunks
from app.ingest.loaders import load_document, ocr_page_with_tesseract
from app.ingest.sources import SourceDoc
from app.models import Chunk
from app.store.base import VectorStore


@dataclass
class SyncReport:
    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    empty: list[str] = field(default_factory=list)  # parsed but produced no chunks
    chunks_written: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def index_fingerprint(cfg: dict[str, Any]) -> str:
    """Hash of every setting that changes what gets stored, so a stage switch triggers reindex."""
    relevant = {k: cfg.get(k) for k in ("ingest", "ocr", "tables", "embedding")}
    relevant["sparse_model"] = cfg.get("vector_store", {}).get("sparse_model")
    blob = json.dumps(relevant, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def build_doc_chunks(doc: SourceDoc, cfg: dict[str, Any],
                     ocr_fn=ocr_page_with_tesseract) -> list[Chunk]:
    assert doc.path is not None
    loaded = load_document(doc.path, cfg["ingest"], cfg["ocr"], cfg["tables"], ocr_fn)
    title = str(loaded.front_matter.get("title") or doc.title)
    meta = DocMeta(doc.doc_id, title, doc.version, doc.product, doc.allowed_groups, doc.is_latest)
    return build_chunks(meta, loaded.pages, cfg["ingest"])


def _load_manifest(path: Path) -> dict[str, dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _save_manifest(path: Path, manifest: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def sync_corpus(docs: list[SourceDoc], store: VectorStore, embedder: Embedder,
                cfg: dict[str, Any], manifest_path: Path,
                ocr_fn=ocr_page_with_tesseract) -> SyncReport:
    """Bring the store in line with `docs`, touching only what changed."""
    report = SyncReport()
    manifest = _load_manifest(manifest_path)
    if store.count() == 0:  # store was wiped or is new: the manifest is stale
        manifest = {}
    fingerprint = index_fingerprint(cfg)
    batch = int(cfg["ingest"]["batch_size"])

    for doc in docs:
        if doc.path is None or not doc.path.exists():
            report.missing.append(doc.doc_id)
            continue
        sha = file_sha256(doc.path)
        entry = manifest.get(doc.doc_id)
        same = (entry and entry["sha256"] == sha and entry["fingerprint"] == fingerprint
                and entry["allowed_groups"] == list(doc.allowed_groups)
                and entry["version"] == doc.version)
        if same:
            if entry["is_latest"] != doc.is_latest:
                store.set_is_latest(doc.doc_id, doc.is_latest)
                entry["is_latest"] = doc.is_latest
            report.unchanged.append(doc.doc_id)
            continue

        if entry:
            store.delete_doc(doc.doc_id)
        chunks = build_doc_chunks(doc, cfg, ocr_fn)
        for i in range(0, len(chunks), batch):
            part = chunks[i:i + batch]
            store.upsert(part, embedder.embed_documents([c.text for c in part]))
        report.chunks_written += len(chunks)
        if not chunks:
            report.empty.append(doc.doc_id)
        (report.updated if entry else report.added).append(doc.doc_id)
        manifest[doc.doc_id] = {"sha256": sha, "fingerprint": fingerprint,
                                "allowed_groups": list(doc.allowed_groups),
                                "version": doc.version, "is_latest": doc.is_latest,
                                "chunks": len(chunks)}

    wanted = {d.doc_id for d in docs}
    for doc_id in sorted(set(manifest) - wanted):
        store.delete_doc(doc_id)
        del manifest[doc_id]
        report.removed.append(doc_id)

    _save_manifest(manifest_path, manifest)
    return report
