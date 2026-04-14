"""Store vetorial incremental (fallback lexical quando embeddings indisponíveis)."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any


_WORD_RE = re.compile(r"[a-z0-9À-ÿ]{3,}", re.IGNORECASE)


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _WORD_RE.findall(text or "")}


@dataclass
class TenantDocument:
    text: str
    source: str
    metadata: dict[str, Any]


class TenantVectorStore:
    """
    Armazém por tenant.

    Implementação atual:
    - mantém docs em memória por empresa;
    - usa score lexical (Jaccard) como fallback seguro e determinístico.
    """

    def __init__(self) -> None:
        self._docs: dict[int, list[TenantDocument]] = {}

    def upsert_many(self, *, empresa_id: int, docs: list[TenantDocument]) -> None:
        self._docs[empresa_id] = docs

    def similarity_search(
        self,
        *,
        empresa_id: int,
        query: str,
        top_k: int = 4,
    ) -> list[TenantDocument]:
        items = self._docs.get(empresa_id, [])
        if not items:
            return []
        q = _tokens(query)
        if not q:
            return items[:top_k]

        scored: list[tuple[float, TenantDocument]] = []
        for item in items:
            d = _tokens(item.text)
            if not d:
                continue
            inter = len(q.intersection(d))
            union = len(q.union(d))
            score = inter / union if union else 0.0
            # leve boost para conteúdo de chat mais recente via metadata
            boost = float(item.metadata.get("boost", 0.0) or 0.0)
            scored.append((score + math.tanh(boost) * 0.05, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in scored if score > 0][:top_k]

