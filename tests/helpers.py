"""Shared builders for tests: offline pipeline over the bundled synthetic corpus."""

from app.config import load_settings
from app.dataset import get_dataset, sync_dataset
from app.pipeline import build_pipeline


def offline_pipeline(stage=None, env=None):
    settings = load_settings(stage=stage, env=env if env is not None else {})
    pipeline = build_pipeline(settings, offline=True)
    dataset = get_dataset(settings, "synthetic")
    report = sync_dataset(pipeline, settings, dataset, True)
    return settings, pipeline, dataset, report
