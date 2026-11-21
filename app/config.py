"""Configuration loading with locked experiment stages and secret checks."""

from __future__ import annotations

import copy
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
MIN_SECRET_LENGTH = 32
PLACEHOLDER_SECRETS = {
    "",
    "CHANGE_ME",
    "CHANGE_ME_IN_PRODUCTION",
    "replace_with_a_long_random_string_min_32_chars",
    "your_groq_api_key_here",
}


class ConfigError(ValueError):
    """Raised for invalid configuration or unsafe secrets."""


def deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    """Return a new dict with `override` merged recursively into `base`."""
    merged = copy.deepcopy(dict(base))
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def leaf_paths(tree: Mapping[str, Any], prefix: str = "") -> list[str]:
    """List dotted paths of every leaf value in a nested mapping."""
    paths: list[str] = []
    for key, value in tree.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            paths.extend(leaf_paths(value, path))
        else:
            paths.append(path)
    return paths


def apply_stage(cfg: Mapping[str, Any], stages_doc: Mapping[str, Any],
                stage: str) -> dict[str, Any]:
    """Apply a named stage's overrides, refusing to touch locked settings."""
    stages = stages_doc.get("stages", {})
    if stage not in stages:
        raise ConfigError(f"Unknown stage '{stage}'. Known stages: {sorted(stages)}")
    overrides = stages[stage].get("overrides", {})
    for path in leaf_paths(overrides):
        for locked in stages_doc.get("locked", []):
            if path == locked or path.startswith(locked + "."):
                raise ConfigError(f"Stage '{stage}' tries to change locked setting '{path}'")
    return deep_merge(cfg, overrides)


@dataclass(frozen=True)
class Settings:
    cfg: dict[str, Any]
    stage: str | None
    qdrant_host: str
    qdrant_port: int
    groq_api_key: str | None
    auth_secret_key: str | None

    def get(self, dotted: str, default: Any = None) -> Any:
        """Read a nested value, e.g. settings.get('retrieval.top_k')."""
        node: Any = self.cfg
        for part in dotted.split("."):
            if not isinstance(node, Mapping) or part not in node:
                return default
            node = node[part]
        return node

    def require_groq_key(self) -> str:
        if not self.groq_api_key or self.groq_api_key in PLACEHOLDER_SECRETS:
            raise ConfigError("GROQ_API_KEY is missing. Set it in .env")
        return self.groq_api_key

    def require_auth_secret(self) -> str:
        secret = self.auth_secret_key
        if not secret or secret in PLACEHOLDER_SECRETS or len(secret) < MIN_SECRET_LENGTH:
            raise ConfigError(
                f"AUTH_SECRET_KEY must be set to a random value of at least {MIN_SECRET_LENGTH} "
                "characters. Generate one with: "
                "python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )
        return secret


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(ROOT / ".env")


def load_settings(
    config_path: Path | None = None,
    stages_path: Path | None = None,
    stage: str | None = None,
    env: Mapping[str, str] | None = None,
) -> Settings:
    """Load config.yaml, apply the selected stage, and read secrets from the environment."""
    if env is None:
        _load_dotenv()
        env = os.environ

    config_path = Path(env.get("RAG_CONFIG") or config_path or ROOT / "config.yaml")
    stages_path = Path(stages_path or ROOT / "eval" / "stages.yaml")

    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    stage = stage or env.get("RAG_STAGE") or None
    if stage:
        stages_doc = yaml.safe_load(stages_path.read_text(encoding="utf-8"))
        cfg = apply_stage(cfg, stages_doc, stage)

    vs = cfg.get("vector_store", {})
    return Settings(
        cfg=cfg,
        stage=stage,
        qdrant_host=env.get("QDRANT_HOST") or vs.get("host", "localhost"),
        qdrant_port=int(env.get("QDRANT_PORT") or vs.get("port", 6333)),
        groq_api_key=env.get("GROQ_API_KEY"),
        auth_secret_key=env.get("AUTH_SECRET_KEY"),
    )
