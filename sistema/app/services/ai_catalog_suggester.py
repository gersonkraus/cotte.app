"""
ai_catalog_suggester.py

Busca itens do catálogo similares ao serviço detectado na mensagem e
formata a resposta no padrão AIResponse para o frontend exibir como card.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.repositories.servico_repository import ServicoRepository

logger = logging.getLogger(__name__)

_repo = ServicoRepository()


async def buscar_sugestoes_catalogo(
    db: AsyncSession,
    empresa_id: int,
    termo: str,
    limite: int = 3,
) -> list:
    """
    Busca serviços no catálogo da empresa com nome similar ao termo.
    Retorna lista de Servico (apenas ativos, máx `limite` itens).
    """
    try:
        resultados = await _repo.buscar_por_nome(
            db, nome=termo, empresa_id=empresa_id, limit=limite * 2
        )
        # Filtrar apenas ativos e limitar
        ativos = [s for s in resultados if getattr(s, "ativo", True)]
        return ativos[:limite]
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

    contexto_orcamento: dados parciais do orçamento em andamento
    (ex: cliente_nome, cliente_id) para o frontend usar ao confirmar.
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
