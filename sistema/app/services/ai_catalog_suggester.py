"""
ai_catalog_suggester.py

Busca itens do catálogo similares ao serviço detectado na mensagem e
formata a resposta no padrão AIResponse para o frontend exibir como card.
"""

from typing import Optional
from sqlalchemy.orm import Session
import logging

from app.models.models import Servico

logger = logging.getLogger(__name__)


def buscar_sugestoes_catalogo(
    db: Session,
    empresa_id: int,
    termo: str,
    limite: int = 3,
) -> list:
    """
    Busca serviços ativos no catálogo da empresa com nome similar ao termo.
    Retorna lista de Servico (máx `limite` itens).
    """
    try:
        resultados = (
            db.query(Servico)
            .filter(
                Servico.empresa_id == empresa_id,
                Servico.ativo == True,
                Servico.nome.ilike(f"%{termo}%"),
            )
            .limit(limite)
            .all()
        )
        return resultados
    except Exception as e:
        logger.warning(f"ai_catalog_suggester: erro ao buscar '{termo}': {e}")
        return []


def formatar_resposta_sugestao(
    servicos: list,
    termo: str,
    contexto_orcamento: Optional[dict] = None,
) -> dict:
    """
    Monta o dict de resposta no formato AIResponse para o frontend renderizar
    o card 'catalogo_sugestao'.
    """
    sugestoes_json = []
    for s in servicos:
        categoria_nome = None
        if s.categoria:
            categoria_nome = s.categoria.nome
        sugestoes_json.append(
            {
                "id": s.id,
                "nome": s.nome,
                "preco": float(s.preco_padrao) if s.preco_padrao else None,
                "unidade": s.unidade or "un",
                "categoria": categoria_nome,
            }
        )

    qtd = len(sugestoes_json)
    plural = "opção" if qtd == 1 else "opções"
    resposta_txt = (
        f"Encontrei {qtd} {plural} para '{termo}' no seu catálogo. "
        "Usar uma delas ou informar outro valor?"
    )

    return {
        "sucesso": True,
        "resposta": resposta_txt,
        "tipo_resposta": "catalogo_sugestao",
        "dados": {
            "termo_buscado": termo,
            "sugestoes": sugestoes_json,
            "contexto_orcamento": contexto_orcamento or {},
        },
        "confianca": 1.0,
        "modulo_origem": "catalogo",
    }
