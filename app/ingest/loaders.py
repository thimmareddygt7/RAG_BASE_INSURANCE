"""Document loaders: Markdown, text, HTML and PDF (with optional tables, OCR and cleanup)."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import yaml

from app.ingest.layout import order_blocks, strip_repeated_lines
from app.models import Page

PAGE_MARKER = re.compile(r"^<!--\s*page\s+(\d+)\s*-->\s*$", re.I | re.M)
FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


@dataclass
class LoadedDoc:
    pages: list[Page]
    front_matter: dict[str, Any] = field(default_factory=dict)


def parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    m = FRONT_MATTER.match(text)
    if not m:
        return {}, text
    data = yaml.safe_load(m.group(1)) or {}
    return (data if isinstance(data, dict) else {}), text[m.end():]


def split_pages(text: str) -> list[Page]:
    """Split on `<!-- page N -->` markers. Without markers the file is a single page."""
    markers = list(PAGE_MARKER.finditer(text))
    if not markers:
        return [Page(1, text.strip())] if text.strip() else []
    pages = []
    for i, m in enumerate(markers):
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        body = text[m.end():end].strip()
        if body:
            pages.append(Page(int(m.group(1)), body))
    return pages


class _TextExtractor(HTMLParser):
    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "table"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = max(0, self._skip - 1)
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    text = "".join(parser.parts)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _inside(block, bbox) -> bool:
    cx, cy = (block[0] + block[2]) / 2, (block[1] + block[3]) / 2
    return bbox[0] <= cx <= bbox[2] and bbox[1] <= cy <= bbox[3]


def ocr_page_with_tesseract(page, lang: str) -> str:
    """Render a PDF page and run Tesseract on it. Needs pytesseract, Pillow and the binary."""
    import pytesseract
    from PIL import Image

    pix = page.get_pixmap(dpi=300)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return pytesseract.image_to_string(image, lang=lang)


def load_pdf(path: Path, ingest_cfg: dict[str, Any], ocr_cfg: dict[str, Any],
             tables_cfg: dict[str, Any],
             ocr_fn: Callable[[Any, str], str] = ocr_page_with_tesseract) -> LoadedDoc:
    """Extract text per page. Written against PyMuPDF 1.24 and not run on real PDFs in the
    build environment, so test it on 20 of your own pages (see docs/evaluation_plan.md)."""
    import fitz  # PyMuPDF

    use_tables = tables_cfg.get("parser") == "pymupdf"
    pages: list[Page] = []
    with fitz.open(path) as pdf:
        for number, page in enumerate(pdf, start=1):
            if use_tables:
                blocks = [(b[0], b[1], b[2], b[3], b[4]) for b in page.get_text("blocks")
                          if b[6] == 0]
                table_items, boxes = [], []
                for table in page.find_tables().tables:
                    boxes.append(table.bbox)
                    table_items.append((*table.bbox, table.to_markdown()))
                kept = [b for b in blocks if not any(_inside(b, bb) for bb in boxes)]
                ordered = order_blocks(kept + table_items, page.rect.width)
                text = "\n\n".join(b[4].strip() for b in ordered if b[4].strip())
            else:
                text = page.get_text("text")
            used_ocr = False
            if ocr_cfg.get("enabled") and len(text.strip()) < int(ocr_cfg["min_chars_per_page"]):
                text = ocr_fn(page, ocr_cfg.get("lang", "eng"))
                used_ocr = True
            pages.append(Page(number, text.strip(), used_ocr))
    if ingest_cfg.get("strip_headers_footers"):
        cleaned = strip_repeated_lines([p.text for p in pages])
        pages = [Page(p.number, t.strip(), p.ocr) for p, t in zip(pages, cleaned, strict=True)]
    return LoadedDoc([p for p in pages if p.text])


def load_document(path: Path, ingest_cfg: dict[str, Any], ocr_cfg: dict[str, Any],
                  tables_cfg: dict[str, Any], ocr_fn=ocr_page_with_tesseract) -> LoadedDoc:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return load_pdf(path, ingest_cfg, ocr_cfg, tables_cfg, ocr_fn)
    raw = path.read_text(encoding="utf-8")
    if suffix == ".html":
        return LoadedDoc([Page(1, html_to_text(raw))])
    if suffix in (".md", ".txt"):
        front, body = parse_front_matter(raw)
        return LoadedDoc(split_pages(body), front)
    raise ValueError(f"Unsupported file type: {path.suffix}")
