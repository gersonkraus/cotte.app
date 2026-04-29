from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any


@dataclass
class InsightEngine:
    ttl_minutes: int = 5

    @staticmethod
    async def build_snapshot(db: Any, empresa_id: int) -> dict[str, Any]:
        """
        Constroi snapshot de dados para geracao de insights.
        Reutiliza ContextBuilder._ctx_financeiro e _ctx_orcamentos.
        Retorna {"financeiro": {...}, "orcamentos": [...]} ou snapshot vazio em caso de erro.
        """
        try:
            from app.services.cotte_context_builder import ContextBuilder

            fin = await ContextBuilder._ctx_financeiro(db, empresa_id)
            saldo_info = (fin or {}).get("saldo") or {}
            saldo_atual = saldo_info.get("atual") if isinstance(saldo_info, dict) else None
            try:
                saldo_projetado = float(saldo_atual) if saldo_atual is not None else None
            except (TypeError, ValueError):
                saldo_projetado = None

            orc_ctx = await ContextBuilder._ctx_orcamentos(db, empresa_id)
            pendentes_raw = (orc_ctx or {}).get("pendentes_acao") or []
            orcamentos = []
            for p in pendentes_raw:
                if not isinstance(p, dict):
                    continue
                dias = p.get("dias_aguardando")
                try:
                    dias_pendente = int(dias) if dias is not None else None
                except (TypeError, ValueError):
                    dias_pendente = None
                orcamentos.append({
                    "id": p.get("id"),
                    "dias_pendente": dias_pendente,
                    "status": p.get("status"),
                })

            return {
                "financeiro": {
                    "saldo_projetado": saldo_projetado,
                    "inadimplencia_pct": 0,
                },
                "orcamentos": orcamentos,
            }
        except Exception:
            return {"financeiro": {}, "orcamentos": []}

    def build_for_empresa(
        self,
        *,
        empresa_id: int,
        contexto: dict[str, Any],
        snapshot: dict[str, Any],
        limit: int | None = None,
    ) -> list[dict]:
        expira_em = (datetime.now(UTC) + timedelta(minutes=self.ttl_minutes)).isoformat()
        insights: list[dict] = []

        financeiro = snapshot.get("financeiro") or {}
        saldo_projetado = self._numeric_value(financeiro.get("saldo_projetado"))
        if saldo_projetado is not None and saldo_projetado < 0:
            insights.append(
                self._build_insight(
                    empresa_id=empresa_id,
                    tipo="saldo_projetado_negativo",
                    prioridade="critica",
                    dominio="financeiro",
                    titulo="Saldo projetado negativo",
                    descricao="O saldo financeiro projetado está abaixo de zero.",
                    acao="executar_prompt",
                    contexto={
                        **contexto,
                        "saldo_projetado": saldo_projetado,
                    },
                    score=100,
                    expira_em=expira_em,
                )
            )

        inadimplencia_pct = self._numeric_value(financeiro.get("inadimplencia_pct"))
        if inadimplencia_pct is not None and inadimplencia_pct >= 20:
            insights.append(
                self._build_insight(
                    empresa_id=empresa_id,
                    tipo="inadimplencia_alta",
                    prioridade="alta",
                    dominio="financeiro",
                    titulo="Inadimplência elevada",
                    descricao="A inadimplência está acima do limite de atenção.",
                    acao="executar_prompt",
                    contexto={
                        **contexto,
                        "inadimplencia_pct": inadimplencia_pct,
                    },
                    score=80,
                    expira_em=expira_em,
                )
            )

        for orcamento in snapshot.get("orcamentos") or []:
            if not isinstance(orcamento, dict):
                continue

            dias_pendente = self._numeric_value(orcamento.get("dias_pendente"))
            if (
                orcamento.get("status") in {"ENVIADO", "RASCUNHO"}
                and dias_pendente is not None
                and dias_pendente > 5
            ):
                insights.append(
                    self._build_insight(
                        empresa_id=empresa_id,
                        tipo="orcamento_pendente",
                        prioridade="alta",
                        dominio="orcamentos",
                        titulo="Orçamento pendente há mais de 5 dias",
                        descricao="Há orçamento enviado ou em rascunho aguardando ação.",
                        acao="executar_prompt",
                        contexto={
                            **contexto,
                            "orcamento_id": orcamento.get("id"),
                            "dias_pendente": dias_pendente,
                            "status": orcamento.get("status"),
                        },
                        score=70,
                        expira_em=expira_em,
                    )
                )

        insights = self.dedupe(insights)
        if limit is not None:
            return self.limit(insights, limit)
        return self.limit(insights, len(insights))

    def dedupe(self, insights: list[dict]) -> list[dict]:
        melhores_por_id: dict[str, dict] = {}
        sem_id: list[dict] = []

        for item in insights or []:
            if not isinstance(item, dict):
                continue

            insight_id = item.get("id")
            if not insight_id:
                sem_id.append(item)
                continue

            insight_id = str(insight_id)
            atual = melhores_por_id.get(insight_id)
            if atual is None or self._score_value(item) > self._score_value(atual):
                melhores_por_id[insight_id] = item

        return self.limit(
            [*melhores_por_id.values(), *sem_id],
            len(melhores_por_id) + len(sem_id),
        )

    def limit(self, insights: list[dict], n: int) -> list[dict]:
        if not isinstance(n, int) or n <= 0:
            return []

        validos = [item for item in (insights or []) if isinstance(item, dict)]
        return sorted(validos, key=self._score_value, reverse=True)[:n]

    def _score_value(self, item: dict) -> float:
        score = item.get("score")
        if isinstance(score, (int, float)):
            return float(score)
        return 0.0

    def _numeric_value(self, value: Any) -> int | float | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return value
        return None

    def _build_insight(
        self,
        *,
        empresa_id: int,
        tipo: str,
        prioridade: str,
        dominio: str,
        titulo: str,
        descricao: str,
        acao: str,
        contexto: dict[str, Any],
        score: int,
        expira_em: str,
    ) -> dict:
        return {
            "id": self._deterministic_id(empresa_id, tipo, dominio, contexto),
            "tipo": tipo,
            "prioridade": prioridade,
            "dominio": dominio,
            "titulo": titulo,
            "descricao": descricao,
            "acao": acao,
            "contexto": contexto,
            "score": score,
            "fonte": "rule_engine",
            "expira_em": expira_em,
        }

    def _deterministic_id(
        self,
        empresa_id: int,
        tipo: str,
        dominio: str,
        contexto: dict[str, Any],
    ) -> str:
        raw = f"{empresa_id}:{dominio}:{tipo}:{sorted(contexto.items())}"
        return sha256(raw.encode("utf-8")).hexdigest()[:12]
