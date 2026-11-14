"""Datasets: the real corpus or the bundled synthetic one (for offline demos and tests)."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.config import ROOT, Settings
from app.ingest.indexer import SyncReport, sync_corpus
from app.ingest.sources import SourceDoc, load_sources
from app.pipeline import RagPipeline, manifest_path


@dataclass(frozen=True)
class Dataset:
    name: str
    sources_csv: Path
    gold_csv: Path
    raw_dir: Path


def get_dataset(settings: Settings, name: str) -> Dataset:
    if name == "synthetic":
        return Dataset(name, ROOT / settings.get("data.synthetic_sources_csv"),
                       ROOT / settings.get("data.synthetic_gold_csv"),
                       ROOT / settings.get("data.synthetic_dir"))
    if name == "real":
        return Dataset(name, ROOT / settings.get("data.sources_csv"),
                       ROOT / settings.get("data.gold_questions_csv"),
                       ROOT / settings.get("data.raw_dir"))
    raise ValueError(f"Unknown dataset '{name}' (use 'real' or 'synthetic')")


def load_docs(settings: Settings, dataset: Dataset) -> list[SourceDoc]:
    return load_sources(dataset.sources_csv, dataset.raw_dir, settings.get("auth.groups"))


def sync_dataset(pipeline: RagPipeline, settings: Settings, dataset: Dataset, offline: bool,
                 manifest: Path | None = None) -> SyncReport:
    """Index (or update) the dataset incrementally.

    Offline runs use a throwaway manifest unless the caller passes one, so keep passing the
    same `manifest` if you want later syncs to see what the earlier one indexed.
    """
    docs = load_docs(settings, dataset)
    path = manifest or (Path(tempfile.mkdtemp()) / "manifest.json" if offline
                        else manifest_path(settings, offline))
    return sync_corpus(docs, pipeline.store, pipeline.embedder, settings.cfg, path)
