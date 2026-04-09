"""Tools de catálogo: listar materiais/serviços."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.models import Servico, Usuario

from ._base import ToolSpec


class ListarMateriaisInput(BaseModel):
    busca: Optional[str] = Field(
        default=None, description="Filtro parcial por nome ou descrição."
    )
    limit: int = Field(default=20, ge=1, le=100)


async def _listar_materiais(
    inp: ListarMateriaisInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    q = db.query(Servico).filter(
        Servico.empresa_id == current_user.empresa_id,
        Servico.ativo == True,  # noqa: E712
    )
    if inp.busca:
        termo = f"%{inp.busca.strip()}%"
        q = q.filter((Servico.nome.ilike(termo)) | (Servico.descricao.ilike(termo)))
    items = q.order_by(Servico.nome.asc()).limit(inp.limit).all()
    return {
        "total": len(items),
        "materiais": [
            {
                "id": s.id,
                "nome": s.nome,
                "descricao": s.descricao,
                "preco_padrao": float(s.preco_padrao or 0),
                "unidade": s.unidade,
            }
            for s in items
        ],
    }


listar_materiais = ToolSpec(
    name="listar_materiais",
    description=(
        "Lista materiais/serviços do catálogo da empresa do usuário. "
        "Usar antes de propor itens em um orçamento."
    ),
    input_model=ListarMateriaisInput,
    handler=_listar_materiais,
    destrutiva=False,
    cacheable_ttl=60,
    permissao_recurso="catalogo",
    permissao_acao="leitura",
)


# ── cadastrar_material (DESTRUTIVA) ────────────────────────────────────────
class CadastrarMaterialInput(BaseModel):
    nome: str = Field(min_length=2, max_length=200, description="Nome do material/serviço.")
    preco_padrao: Decimal = Field(default=Decimal("0"), ge=0, description="Preço padrão.")
    unidade: str = Field(default="un", max_length=20, description="Unidade (un, m², hora, etc).")
    descricao: Optional[str] = Field(default=None, max_length=500)


async def _cadastrar_material(
    inp: CadastrarMaterialInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    servico = Servico(
        empresa_id=current_user.empresa_id,
        nome=inp.nome.strip(),
        descricao=(inp.descricao.strip() if inp.descricao else None),
        preco_padrao=inp.preco_padrao,
        unidade=inp.unidade.strip() or "un",
        ativo=True,
    )
    db.add(servico)
    db.commit()
    db.refresh(servico)
    return {
        "id": servico.id,
        "nome": servico.nome,
        "preco_padrao": float(servico.preco_padrao or 0),
        "unidade": servico.unidade,
        "criado": True,
    }


cadastrar_material = ToolSpec(
    name="cadastrar_material",
    description=(
        "Cria um novo material/serviço no catálogo. Apenas o NOME é obrigatório; "
        "preço padrão e unidade têm defaults. AÇÃO DESTRUTIVA — exige confirmação."
    ),
    input_model=CadastrarMaterialInput,
    handler=_cadastrar_material,
    destrutiva=True,
    permissao_recurso="catalogo",
    permissao_acao="escrita",
)
