"""Chunking simples para contexto RAG."""

from __future__ import annotations

from typing import Iterable


def chunk_text(
    text: str,
    *,
    chunk_size: int = 600,
    overlap: int = 120,
) -> list[str]:
    clean = (text or "").strip()
    if not clean:
        return []
    if len(clean) <= chunk_size:
        return [clean]

    chunks: list[str] = []
    start = 0
    step = max(1, chunk_size - overlap)
    while start < len(clean):
        end = min(len(clean), start + chunk_size)
        chunks.append(clean[start:end].strip())
        if end >= len(clean):
            break
        start += step
    return [c for c in chunks if c]


def compact_join(parts: Iterable[str], *, max_chars: int = 2800) -> str:
    out = []
    total = 0
    for part in parts:
        txt = (part or "").strip()
        if not txt:
            continue
        extra = len(txt) + (2 if out else 0)
        if total + extra > max_chars:
            break
        out.append(txt)
        total += extra
    return "\n\n".join(out)

