"""Prompt construction. Context blocks carry headers the model must cite from."""

from __future__ import annotations

from app.models import Hit


def format_context(hits: list[Hit]) -> str:
    blocks = []
    for h in hits:
        c = h.chunk
        header = f"### SOURCE doc={c.doc_id} version={c.version or '-'} page={c.page}"
        if c.section:
            header += f" section={c.section}"
        blocks.append(f"{header}\n{c.text}")
    return "\n\n".join(blocks)


def build_user_prompt(question: str, hits: list[Hit]) -> str:
    return f"CONTEXT:\n{format_context(hits)}\n\nQUESTION: {question.strip()}"
