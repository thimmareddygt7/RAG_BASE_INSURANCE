"""Index (or incrementally update) the corpus in Qdrant.

Usage: python scripts/sync_index.py [--stage stage3_hybrid] [--dataset real|synthetic]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_settings  # noqa: E402
from app.dataset import get_dataset, sync_dataset  # noqa: E402
from app.pipeline import build_pipeline  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage")
    parser.add_argument("--dataset", choices=["real", "synthetic"], default="real")
    args = parser.parse_args()
    settings = load_settings(stage=args.stage)
    pipeline = build_pipeline(settings, offline=False)
    report = sync_dataset(pipeline, settings, get_dataset(settings, args.dataset), False)
    print(json.dumps(report.as_dict(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
