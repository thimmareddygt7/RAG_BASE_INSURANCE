"""LLM backends: Groq (real), an extractive offline stand-in, and a caching wrapper."""

from __future__ import annotations

import hashlib
import json
import logging
import random
import re
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.text import content_words

log = logging.getLogger(__name__)


class LLM(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class ModelUnavailableError(RuntimeError):
    """The configured model cannot answer now and falling back to another model is not allowed."""


@dataclass
class CallInfo:
    """What happened on the most recent call. `latency_ms` is always the LIVE call time, even
    when the reply came from the disk cache (it is stored with the cached reply)."""

    model: str
    latency_ms: float
    cached: bool = False


class GroqLLM:
    """Groq chat completion.

    The model is fixed. On a rate limit it waits and retries the SAME model. It only switches
    to another model if `allow_fallback` is True and `fallback_models` lists one, and every
    call records which model actually answered (`last_info`, `models_used`), so a run can be
    checked for model drift.
    """

    def __init__(self, api_key: str, model: str, temperature: float = 0.0,
                 max_tokens: int = 1024, max_retries: int = 5, allow_fallback: bool = False,
                 fallback_models: tuple[str, ...] | list[str] = (),
                 max_wait_seconds: float = 120.0, client=None, sleep=time.sleep):
        if client is None:
            from groq import Groq

            client = Groq(api_key=api_key, timeout=30.0)
        self._client = client
        self.model = model
        self._models = [model]
        if allow_fallback:
            self._models += [m for m in fallback_models if m not in self._models]
        self._allow_fallback = allow_fallback
        self._model_idx = 0
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._max_retries = max_retries
        self._max_wait = max_wait_seconds
        self._sleep = sleep
        self.last_info: CallInfo | None = None
        self.models_used: Counter[str] = Counter()

    @staticmethod
    def _parse_wait(message: str) -> float:
        m = re.search(r"try again in (?:(\d+)m)?([\d\.]+)s", message)
        if not m:
            return 0.0
        return (int(m.group(1)) if m.group(1) else 0) * 60 + float(m.group(2))

    def complete(self, system: str, user: str) -> str:
        for attempt in range(self._max_retries):
            current = self._models[self._model_idx]
            started = time.perf_counter()
            try:
                response = self._client.chat.completions.create(
                    model=current,
                    messages=[{"role": "system", "content": system},
                              {"role": "user", "content": user}],
                    temperature=self._temperature, max_tokens=self._max_tokens)
            except Exception as exc:
                message = str(exc)
                log.warning("Groq call %d/%d failed on %s: %s", attempt + 1,
                            self._max_retries, current, message[:200])
                daily = "tokens per day" in message.lower() or "tpd" in message.lower()
                wait = self._parse_wait(message)
                if daily or wait > self._max_wait:
                    if self._allow_fallback and self._model_idx + 1 < len(self._models):
                        self._model_idx += 1
                        log.warning("Switching model %s -> %s (fallback allowed)", current,
                                    self._models[self._model_idx])
                        continue
                    raise ModelUnavailableError(
                        f"{current} is rate limited ({'daily token limit' if daily else f'wait {wait:.0f}s'}). "
                        "Wait and rerun, or set llm.allow_fallback: true to permit other models "
                        "(the run will then be flagged as model drift).") from exc
                if attempt == self._max_retries - 1:
                    raise
                self._sleep(wait + 1.5 if wait > 0 else min(2**attempt, 30) + random.random())
                continue
            latency = (time.perf_counter() - started) * 1000
            self.last_info = CallInfo(current, latency, cached=False)
            self.models_used[current] += 1
            return response.choices[0].message.content or ""
        raise RuntimeError("unreachable")


CACHE_VERSION = "v2"  # bump when the cache format changes; old entries are then ignored


class CachedLLM:
    """Disk cache keyed by (version, model, system, user).

    Each entry stores the reply, the model that really produced it, and the live latency, so a
    cache hit still reports the true model and the true call time (never a fake 20 ms).
    """

    def __init__(self, inner: LLM, cache_dir: Path, model_name: str):
        self._inner = inner
        self._dir = cache_dir
        self._model = model_name
        self._dir.mkdir(parents=True, exist_ok=True)
        self.last_info: CallInfo | None = None
        self.models_used: Counter[str] = Counter()
        self.cache_hits = 0
        self.cache_misses = 0

    def complete(self, system: str, user: str) -> str:
        key = hashlib.sha256(
            json.dumps([CACHE_VERSION, self._model, system, user]).encode()).hexdigest()
        path = self._dir / f"{key}.json"
        if path.exists():
            entry = json.loads(path.read_text(encoding="utf-8"))
            self.last_info = CallInfo(entry["model"], entry["latency_ms"], cached=True)
            self.models_used[entry["model"]] += 1
            self.cache_hits += 1
            return entry["reply"]
        started = time.perf_counter()
        reply = self._inner.complete(system, user)
        info = getattr(self._inner, "last_info", None) or CallInfo(
            self._model, (time.perf_counter() - started) * 1000)
        path.write_text(json.dumps({"reply": reply, "model": info.model,
                                    "latency_ms": info.latency_ms}), encoding="utf-8")
        self.last_info = CallInfo(info.model, info.latency_ms, cached=False)
        self.models_used[info.model] += 1
        self.cache_misses += 1
        return reply


SOURCE_RE = re.compile(r"^### SOURCE doc=(\S+) version=\S* page=(\d+).*$", re.MULTILINE)


class ExtractiveLLM:
    """Offline stand-in that quotes the best-matching context sentence with a citation.

    It is NOT a language model. It exists so the pipeline, permissions and evaluation
    code can be exercised without an API key.
    """

    def __init__(self, refusal_message: str, min_overlap: float = 0.6):
        self._refusal = refusal_message
        self._min = min_overlap

    def complete(self, system: str, user: str) -> str:
        question = user.rsplit("QUESTION:", 1)[-1].strip()
        q_words = set(content_words(question))
        if not q_words:
            return self._refusal
        best = (0.0, "", "", 0, 0, 0)  # overlap, line, doc, page, heading hits, own hits
        matches = list(SOURCE_RE.finditer(user))
        for i, m in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else user.rfind("QUESTION:")
            body = user[m.end():end]
            heading_words: set[str] = set(content_words(m.group(0).split("section=")[-1])) \
                if "section=" in m.group(0) else set()
            table_header: set[str] = set()
            prev_was_table = False
            units: list[str] = []
            for raw in body.splitlines():
                raw = raw.strip()
                if raw.startswith(("#", "|")):
                    units.append(raw)  # headings and table rows are never split into sentences
                else:
                    units.extend(re.split(r"(?<=[.!?])\s+", raw))
            for line in units:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("#"):
                    heading_words = set(content_words(line))
                    prev_was_table = False
                    continue
                if line.startswith("|---"):
                    continue
                if line.startswith("|"):
                    if not prev_was_table:
                        table_header = set(content_words(line))
                    prev_was_table = True
                else:
                    prev_was_table = False
                    table_header = set()
                scoring_words = set(content_words(line)) | heading_words | table_header
                overlap = len(q_words & scoring_words) / len(q_words)
                heading_hits = len(q_words & heading_words)  # ties go to the matching section
                is_header_row = (line.startswith("|") and table_header
                                 and set(content_words(line)) == table_header)
                own_hits = len(q_words & set(content_words(line)))
                if (overlap, heading_hits, own_hits) > (best[0], best[4], best[5]) \
                        and not is_header_row:
                    best = (overlap, line, m.group(1), int(m.group(2)), heading_hits, own_hits)
        if best[0] < self._min:
            return self._refusal
        text = best[1].strip("| ").replace(" | ", ": ")
        return f"{text} [{best[2]} p.{best[3]}]"
