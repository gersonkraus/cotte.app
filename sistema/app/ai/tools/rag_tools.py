"""Tools para busca na base de conhecimento (RAG)."""

from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai.tools._base import ToolSpec
from app.ai.rag.service import SemanticRAGService

class BuscarConhecimentoInput(BaseModel):
    query: str = Field(description="A pergunta ou termo de busca para pesquisar nos manuais e documentos da empresa.")
    top_k: int = Field(default=3, description="Número de trechos relevantes a retornar.")

async def _buscar_conhecimento(
    input_data: BuscarConhecimentoInput,
    db: Session,
    empresa_id: int,
    **kwargs
) -> dict:
    """Busca trechos relevantes nos documentos de conhecimento da empresa."""
    results = await SemanticRAGService.search_documents(
        db=db,
        empresa_id=empresa_id,
        query=input_data.query,
        top_k=input_data.top_k
    )
    
    if not results:
        return {"resultado": "Nenhuma informação encontrada na base de conhecimento para esta busca."}
    
    formatted_results = []
    for res in results:
        formatted_results.append({
            "fonte": res.fonte,
            "conteudo": res.conteudo,
            "relevancia": "Alta" # O pgvector retorna por distância, aqui poderíamos calcular score
        })
        
    return {
        "resultado": "Trechos encontrados nos manuais da empresa:",
        "contexto": formatted_results
    }

buscar_conhecimento = ToolSpec(
    name="buscar_conhecimento",
    description=(
        "Busca informações em manuais, PDFs e documentos de texto subidos pela empresa. "
        "Use esta ferramenta sempre que o usuário tiver dúvidas sobre regras do negócio, "
        "procedimentos internos ou como operar partes específicas do sistema que dependam de manuais."
    ),
    input_model=BuscarConhecimentoInput,
    handler=_buscar_conhecimento,
    destrutiva=False,
    permissao_recurso="ia",
    permissao_acao="leitura"
)
