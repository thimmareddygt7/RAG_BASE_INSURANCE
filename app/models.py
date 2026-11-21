"""Plain data types shared by the whole pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Page:
    number: int  # 1-indexed
    text: str
    ocr: bool = False


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    version: str
    product: str
    page: int
    section: str
    text: str
    allowed_groups: tuple[str, ...]
    kind: str = "text"  # text | table
    is_latest: bool = True

    def payload(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "version": self.version,
            "product": self.product,
            "page": self.page,
            "section": self.section,
            "text": self.text,
            "allowed_groups": list(self.allowed_groups),
            "kind": self.kind,
            "is_latest": self.is_latest,
        }

    @classmethod
    def from_payload(cls, chunk_id: str, p: dict[str, Any]) -> Chunk:
        return cls(
            chunk_id=str(chunk_id),
            doc_id=p["doc_id"],
            title=p.get("title", ""),
            version=p.get("version", ""),
            product=p.get("product", ""),
            page=int(p["page"]),
            section=p.get("section", ""),
            text=p["text"],
            allowed_groups=tuple(p.get("allowed_groups", ())),
            kind=p.get("kind", "text"),
            is_latest=bool(p.get("is_latest", True)),
        )


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float
    source: str  # dense | sparse | fused | rerank


@dataclass
class Citation:
    doc_id: str
    page: int
    in_context: bool  # the cited doc/page was actually retrieved
    verified: bool  # the claim is supported by the cited page text
    claim: str = ""


@dataclass
class AskResult:
    question: str
    group: str
    answer: str
    refused: bool
    refusal_reason: str = ""
    citations: list[Citation] = field(default_factory=list)
    retrieved: list[Hit] = field(default_factory=list)  # full ranked candidate list
    context_hits: list[Hit] = field(default_factory=list)  # chunks given to the LLM
    prompt: str = ""  # exactly what the LLM saw (never returned by the API)
    timings_ms: dict[str, float] = field(default_factory=dict)
    stage: str | None = None
    answer_model: str = ""  # model that really produced the reply (empty if no LLM call)
    llm_cached: bool = False  # reply came from the disk cache (latency is the stored live time)

    @property
    def context_doc_ids(self) -> set[str]:
        return {h.chunk.doc_id for h in self.context_hits}

    @property
    def citation_ok(self) -> bool:
        """At least one citation and every citation verified."""
        return bool(self.citations) and all(c.verified for c in self.citations)
