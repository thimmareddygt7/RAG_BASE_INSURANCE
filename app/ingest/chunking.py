"""Chunkers. Chunks never cross a page boundary, so every citation points at one exact page."""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from typing import Any

from app.models import Chunk, Page
from app.text import count_tokens, token_spans

_NAMESPACE = uuid.UUID("6f0c1f4e-52a1-4c0e-9a55-3b1b6a2c7d10")

MD_HEADING = re.compile(r"^#{1,6}\s+\S")
NUMBERED_HEADING = re.compile(r"^(?:\d+(?:\.\d+)*[.)]?|[A-Z]\.)\s+[A-Z][^|]{2,80}$")
KEYWORD_HEADING = re.compile(r"^(?:section|part|annexure|schedule|chapter)\b.{0,70}$", re.I)


@dataclass(frozen=True)
class DocMeta:
    doc_id: str
    title: str
    version: str
    product: str
    allowed_groups: tuple[str, ...]
    is_latest: bool = True


@dataclass(frozen=True)
class Block:
    kind: str  # heading | table | text
    text: str


def make_chunk_id(meta: DocMeta, page: int, index: int, text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    return str(uuid.uuid5(_NAMESPACE, f"{meta.doc_id}|{meta.version}|{page}|{index}|{digest}"))


def is_heading(line: str) -> bool:
    s = line.strip()
    if not s or s.startswith("|") or len(s) > 90:
        return False
    if MD_HEADING.match(s) or NUMBERED_HEADING.match(s) or KEYWORD_HEADING.match(s):
        return not s.endswith(".") or bool(MD_HEADING.match(s))
    letters = [c for c in s if c.isalpha()]
    return (len(letters) >= 4 and s.upper() == s and len(s.split()) <= 8
            and not s.rstrip().endswith((".", ":", ",")))


def split_blocks(text: str) -> list[Block]:
    """Split page text into headings, whole tables and paragraphs."""
    blocks: list[Block] = []
    para: list[str] = []
    table: list[str] = []

    def flush_para() -> None:
        if para:
            blocks.append(Block("text", "\n".join(para)))
            para.clear()

    def flush_table() -> None:
        if table:
            blocks.append(Block("table", "\n".join(table)))
            table.clear()

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            flush_para()
            table.append(stripped)
            continue
        flush_table()
        if not stripped:
            flush_para()
        elif is_heading(stripped):
            flush_para()
            blocks.append(Block("heading", stripped.lstrip("#").strip()))
        else:
            para.append(stripped)
    flush_para()
    flush_table()
    return blocks


def _windows(text: str, size: int, overlap: int) -> list[str]:
    spans = token_spans(text)
    if not spans:
        return []
    if len(spans) <= size:
        return [text.strip()]
    step = size - overlap
    out = []
    start = 0
    while start < len(spans):
        end = min(start + size, len(spans))
        out.append(text[spans[start][0]:spans[end - 1][1]].strip())
        if end == len(spans):
            break
        start += step
    return out


def fixed_chunks(meta: DocMeta, pages: list[Page], cfg: dict[str, Any]) -> list[Chunk]:
    """Baseline: sliding token windows over each page."""
    size, overlap = int(cfg["chunk_size"]), int(cfg["chunk_overlap"])
    if not 0 <= overlap < size:
        raise ValueError("chunk_overlap must be >= 0 and smaller than chunk_size")
    chunks: list[Chunk] = []
    for page in pages:
        for i, piece in enumerate(_windows(page.text, size, overlap)):
            if len(piece) < int(cfg["min_chunk_chars"]):
                continue
            chunks.append(Chunk(make_chunk_id(meta, page.number, i, piece), meta.doc_id,
                                meta.title, meta.version, meta.product, page.number, "",
                                piece, meta.allowed_groups, "text", meta.is_latest))
    return chunks


def _split_table(table: str, size: int) -> list[str]:
    """Split an oversized table by rows, repeating its header in every part."""
    lines = table.splitlines()
    header = lines[:2] if len(lines) > 1 and set(lines[1].replace("|", "").strip()) <= set("-: ") \
        else lines[:1]
    rows = lines[len(header):]
    parts: list[str] = []
    current: list[str] = []
    for row in rows:
        candidate = "\n".join(header + current + [row])
        if current and count_tokens(candidate) > size:
            parts.append("\n".join(header + current))
            current = []
        current.append(row)
    if current:
        parts.append("\n".join(header + current))
    return parts or [table]


def structure_chunks(meta: DocMeta, pages: list[Page], cfg: dict[str, Any]) -> list[Chunk]:
    """Section-aware chunks: tables kept whole, title and heading prepended."""
    size, overlap = int(cfg["chunk_size"]), int(cfg["chunk_overlap"])
    keep_tables = bool(cfg["keep_tables_whole"])
    prepend = bool(cfg["prepend_heading"])
    heading = ""
    chunks: list[Chunk] = []

    def _emit(body: str, kind: str, cur_page: Page, cur_heading: str, cur_index: int) -> int:
        body = body.strip()
        if len(body) < int(cfg["min_chunk_chars"]):
            return cur_index
        text = f"{meta.title}\n{cur_heading}\n\n{body}".replace("\n\n\n", "\n\n") if prepend \
            else body
        chunks.append(Chunk(make_chunk_id(meta, cur_page.number, cur_index, text), meta.doc_id,
                            meta.title, meta.version, meta.product, cur_page.number, cur_heading,
                            text, meta.allowed_groups, kind, meta.is_latest))
        return cur_index + 1

    def _flush(buf: list[str], cur_page: Page, cur_heading: str, cur_index: int) -> int:
        if buf:
            cur_index = _emit("\n\n".join(buf), "text", cur_page, cur_heading, cur_index)
            buf.clear()
        return cur_index

    for page in pages:
        index = 0
        buffer: list[str] = []

        for block in split_blocks(page.text):
            if block.kind == "heading":
                index = _flush(buffer, page, heading, index)
                heading = block.text
            elif block.kind == "table" and keep_tables:
                index = _flush(buffer, page, heading, index)
                for part in _split_table(block.text, size):
                    index = _emit(part, "table", page, heading, index)
            else:
                pieces = [block.text]
                if count_tokens(block.text) > size:
                    pieces = _windows(block.text, size, overlap)
                for piece in pieces:
                    joined = "\n\n".join(buffer + [piece])
                    if buffer and count_tokens(joined) > size:
                        index = _flush(buffer, page, heading, index)
                    buffer.append(piece)
        index = _flush(buffer, page, heading, index)
    return chunks


def build_chunks(meta: DocMeta, pages: list[Page], cfg: dict[str, Any]) -> list[Chunk]:
    strategy = cfg["strategy"]
    if strategy == "fixed":
        return fixed_chunks(meta, pages, cfg)
    if strategy == "structure":
        return structure_chunks(meta, pages, cfg)
    raise ValueError(f"Unknown chunking strategy '{strategy}'")
