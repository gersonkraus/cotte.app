"""
Serviço de biblioteca de prompts salvos por empresa.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.models.models import AssistentePromptEmpresa


class AssistantPromptLibraryService:
    CATEGORIAS_VALIDAS = {
        "ranking",
        "comissao",
        "inadimplencia",
        "comparativo_mensal",
    }

    @classmethod
    def normalizar_categoria(cls, categoria: Optional[str]) -> str:
        value = (categoria or "").strip().lower()
        if value not in cls.CATEGORIAS_VALIDAS:
            raise ValueError("Categoria inválida")
        return value

    @staticmethod
    def _serialize(prompt: AssistentePromptEmpresa) -> dict:
        return {
            "id": int(prompt.id),
            "titulo": prompt.titulo,
            "conteudo_prompt": prompt.conteudo_prompt,
            "categoria": prompt.categoria,
            "favorito": bool(prompt.favorito),
            "uso_count": int(prompt.uso_count or 0),
            "ativo": bool(prompt.ativo),
            "criado_em": prompt.criado_em.isoformat() if prompt.criado_em else None,
            "atualizado_em": prompt.atualizado_em.isoformat() if prompt.atualizado_em else None,
        }

    @classmethod
    def list_prompts(
        cls,
        db: Session,
        *,
        empresa_id: int,
        categoria: Optional[str] = None,
        favorito: Optional[bool] = None,
        q: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[int] = None,
    ) -> dict:
        query = db.query(AssistentePromptEmpresa).filter(
            AssistentePromptEmpresa.empresa_id == empresa_id,
            AssistentePromptEmpresa.ativo == True,  # noqa: E712
        )
        categoria_normalizada: Optional[str] = None
        if categoria:
            categoria_normalizada = cls.normalizar_categoria(categoria)
            query = query.filter(AssistentePromptEmpresa.categoria == categoria_normalizada)
        if favorito is not None:
            query = query.filter(AssistentePromptEmpresa.favorito == bool(favorito))
        if q:
            term = f"%{q.strip()}%"
            query = query.filter(
                or_(
                    AssistentePromptEmpresa.titulo.ilike(term),
                    AssistentePromptEmpresa.conteudo_prompt.ilike(term),
                )
            )
        if cursor:
            query = query.filter(AssistentePromptEmpresa.id < int(cursor))

        items = (
            query.order_by(
                desc(AssistentePromptEmpresa.favorito),
                desc(AssistentePromptEmpresa.uso_count),
                desc(AssistentePromptEmpresa.id),
            )
            .limit(int(limit) + 1)
            .all()
        )
        has_more = len(items) > int(limit)
        records = items[: int(limit)]
        next_cursor = int(records[-1].id) if has_more and records else None
        return {
            "items": [cls._serialize(item) for item in records],
            "next_cursor": next_cursor,
            "has_more": has_more,
            "limit": int(limit),
            "filters": {
                "categoria": categoria_normalizada,
                "favorito": favorito,
                "q": (q or "").strip() or None,
            },
            "categorias": sorted(cls.CATEGORIAS_VALIDAS),
        }

    @classmethod
    def create_prompt(
        cls,
        db: Session,
        *,
        empresa_id: int,
        usuario_id: int,
        titulo: str,
        conteudo_prompt: str,
        categoria: str,
        favorito: bool = False,
    ) -> dict:
        prompt = AssistentePromptEmpresa(
            empresa_id=empresa_id,
            titulo=(titulo or "").strip(),
            conteudo_prompt=(conteudo_prompt or "").strip(),
            categoria=cls.normalizar_categoria(categoria),
            favorito=bool(favorito),
            uso_count=0,
            ativo=True,
            criado_por_id=usuario_id,
            atualizado_por_id=usuario_id,
        )
        db.add(prompt)
        db.commit()
        db.refresh(prompt)
        return cls._serialize(prompt)

    @classmethod
    def get_prompt_for_empresa(
        cls, db: Session, *, empresa_id: int, prompt_id: int
    ) -> AssistentePromptEmpresa | None:
        return (
            db.query(AssistentePromptEmpresa)
            .filter(
                AssistentePromptEmpresa.id == int(prompt_id),
                AssistentePromptEmpresa.empresa_id == int(empresa_id),
                AssistentePromptEmpresa.ativo == True,  # noqa: E712
            )
            .first()
        )

    @classmethod
    def update_prompt(
        cls,
        db: Session,
        *,
        prompt: AssistentePromptEmpresa,
        usuario_id: int,
        titulo: Optional[str] = None,
        conteudo_prompt: Optional[str] = None,
        categoria: Optional[str] = None,
        favorito: Optional[bool] = None,
    ) -> dict:
        if titulo is not None:
            prompt.titulo = titulo.strip()
        if conteudo_prompt is not None:
            prompt.conteudo_prompt = conteudo_prompt.strip()
        if categoria is not None:
            prompt.categoria = cls.normalizar_categoria(categoria)
        if favorito is not None:
            prompt.favorito = bool(favorito)
        prompt.atualizado_por_id = usuario_id
        db.add(prompt)
        db.commit()
        db.refresh(prompt)
        return cls._serialize(prompt)

    @classmethod
    def soft_delete_prompt(
        cls,
        db: Session,
        *,
        prompt: AssistentePromptEmpresa,
        usuario_id: int,
    ) -> None:
        prompt.ativo = False
        prompt.atualizado_por_id = usuario_id
        db.add(prompt)
        db.commit()

    @classmethod
    def register_usage(
        cls,
        db: Session,
        *,
        prompt: AssistentePromptEmpresa,
        usuario_id: int,
    ) -> dict:
        prompt.uso_count = int(prompt.uso_count or 0) + 1
        prompt.atualizado_por_id = usuario_id
        db.add(prompt)
        db.commit()
        db.refresh(prompt)
        return cls._serialize(prompt)

    @classmethod
    def seed_defaults_if_empty(cls, db: Session, *, empresa_id: int, usuario_id: int) -> int:
        existing_count = (
            db.query(AssistentePromptEmpresa.id)
            .filter(
                AssistentePromptEmpresa.empresa_id == int(empresa_id),
                AssistentePromptEmpresa.ativo == True,  # noqa: E712
            )
            .count()
        )
        if existing_count > 0:
            return 0

        defaults = [
            (
                "Ranking de clientes por faturamento",
                "Monte um ranking dos 10 clientes com maior faturamento no mês atual, com ticket médio e variação vs mês anterior.",
                "ranking",
            ),
            (
                "Comissão por vendedor",
                "Calcule comissão por vendedor no período atual, com base em vendas aprovadas e destaque top 3.",
                "comissao",
            ),
            (
                "Clientes inadimplentes",
                "Liste clientes inadimplentes por faixa de atraso (1-7, 8-30, +30 dias) e valor total pendente.",
                "inadimplencia",
            ),
            (
                "Comparativo mensal de receita",
                "Faça comparativo dos últimos 6 meses de receita, custos e margem, destacando tendência e alertas.",
                "comparativo_mensal",
            ),
        ]
        for titulo, conteudo, categoria in defaults:
            db.add(
                AssistentePromptEmpresa(
                    empresa_id=int(empresa_id),
                    titulo=titulo,
                    conteudo_prompt=conteudo,
                    categoria=categoria,
                    favorito=False,
                    uso_count=0,
                    ativo=True,
                    criado_por_id=usuario_id,
                    atualizado_por_id=usuario_id,
                )
            )
        db.commit()
        return len(defaults)
