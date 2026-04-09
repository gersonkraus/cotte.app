"""Tools de clientes: listar e criar."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.models import Cliente, Usuario
from app.schemas.schemas import ClienteCreate, ClienteUpdate
from app.services.cliente_service import ClienteService

from ._base import ToolSpec


# ── listar_clientes ────────────────────────────────────────────────────────
class ListarClientesInput(BaseModel):
    busca: Optional[str] = Field(
        default=None, description="Filtro por nome/telefone/e-mail (parcial)."
    )
    limit: int = Field(default=10, ge=1, le=50)


async def _listar_clientes(
    inp: ListarClientesInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    q = db.query(Cliente).filter(Cliente.empresa_id == current_user.empresa_id)
    if inp.busca:
        termo = f"%{inp.busca.strip()}%"
        q = q.filter(
            (Cliente.nome.ilike(termo))
            | (Cliente.telefone.ilike(termo))
            | (Cliente.email.ilike(termo))
        )
    items = q.order_by(Cliente.nome.asc()).limit(inp.limit).all()
    return {
        "total": len(items),
        "instrucao_para_assistente": (
            "Use SEMPRE o campo 'id' deste payload para qualquer ação subsequente "
            "(excluir, editar). NUNCA invente IDs nem use a posição na lista."
        ),
        "clientes": [
            {
                "id": c.id,  # ← USE ESTE CAMPO PARA AÇÕES (excluir/editar)
                "nome_exibicao": f"[ID {c.id}] {c.nome}",
                "nome": c.nome,
                "telefone": c.telefone,
                "email": c.email,
            }
            for c in items
        ],
    }


listar_clientes = ToolSpec(
    name="listar_clientes",
    description=(
        "Lista clientes da empresa do usuário, com filtro opcional por nome/telefone/e-mail. "
        "IMPORTANTE: cada cliente retorna um campo 'id' (inteiro do banco). Para ações "
        "subsequentes (excluir/editar), use SEMPRE esse 'id' — NUNCA a posição na lista. "
        "Se o usuário pedir uma ação por nome, prefira chamar esta tool com `busca` específica."
    ),
    input_model=ListarClientesInput,
    handler=_listar_clientes,
    destrutiva=False,
    cacheable_ttl=30,
    permissao_recurso="clientes",
    permissao_acao="leitura",
)


# ── criar_cliente (DESTRUTIVA) ─────────────────────────────────────────────
class CriarClienteInput(BaseModel):
    nome: str = Field(min_length=2, max_length=200, description="Nome do cliente — único campo obrigatório.")
    telefone: Optional[str] = Field(default=None, max_length=30, description="Opcional.")
    email: Optional[str] = Field(default=None, max_length=200, description="Opcional.")


async def _criar_cliente(
    inp: CriarClienteInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    service = ClienteService(db)
    payload = ClienteCreate(
        nome=inp.nome.strip(),
        telefone=(inp.telefone.strip() if inp.telefone else None),
        email=(inp.email or None),
    )
    novo = service.criar_cliente(payload, current_user)
    return {
        "id": novo.id,
        "nome": novo.nome,
        "telefone": novo.telefone,
        "email": novo.email,
        "criado": True,
    }


criar_cliente = ToolSpec(
    name="criar_cliente",
    description=(
        "Cria um novo cliente. Apenas o NOME é obrigatório — telefone e e-mail são "
        "opcionais e podem ser omitidos. NÃO peça telefone/e-mail ao usuário se ele "
        "não fornecer espontaneamente; chame a tool direto com só o nome. "
        "AÇÃO DESTRUTIVA — exige confirmação (o sistema mostra o card automaticamente)."
    ),
    input_model=CriarClienteInput,
    handler=_criar_cliente,
    destrutiva=True,
    permissao_recurso="clientes",
    permissao_acao="escrita",
)


# ── excluir_cliente ────────────────────────────────────────────────────────
class ExcluirClienteInput(BaseModel):
    cliente_id: int = Field(gt=0, description="ID do cliente a excluir.")


async def _excluir_cliente(
    inp: ExcluirClienteInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    service = ClienteService(db)
    ok = service.excluir_cliente(inp.cliente_id, current_user)
    return {"id": inp.cliente_id, "excluido": bool(ok)}


excluir_cliente = ToolSpec(
    name="excluir_cliente",
    description=(
        "Exclui um cliente pelo ID. AÇÃO DESTRUTIVA — exige confirmação. "
        "Se o usuário disser apenas o nome, busque o ID via listar_clientes antes."
    ),
    input_model=ExcluirClienteInput,
    handler=_excluir_cliente,
    destrutiva=True,
    permissao_recurso="clientes",
    permissao_acao="escrita",
)


# ── editar_cliente (DESTRUTIVA) ────────────────────────────────────────────
class EditarClienteInput(BaseModel):
    cliente_id: int = Field(gt=0, description="ID do cliente (use listar_clientes antes).")
    nome: Optional[str] = Field(default=None, min_length=2, max_length=200)
    telefone: Optional[str] = Field(default=None, max_length=30)
    email: Optional[str] = Field(default=None, max_length=200)
    endereco: Optional[str] = Field(default=None, max_length=500)
    cidade: Optional[str] = Field(default=None, max_length=120)
    cep: Optional[str] = Field(default=None, max_length=20)


async def _editar_cliente(
    inp: EditarClienteInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    dados_dict = {k: v for k, v in inp.model_dump().items() if k != "cliente_id" and v is not None}
    if not dados_dict:
        return {"error": "nenhum campo para atualizar", "code": "invalid_input"}
    service = ClienteService(db)
    atualizado = service.atualizar_cliente(
        inp.cliente_id, ClienteUpdate(**dados_dict), current_user
    )
    db.commit()
    db.refresh(atualizado)
    return {
        "id": atualizado.id,
        "nome": atualizado.nome,
        "telefone": atualizado.telefone,
        "email": atualizado.email,
        "atualizado": True,
    }


editar_cliente = ToolSpec(
    name="editar_cliente",
    description=(
        "Atualiza dados de um cliente existente (nome, telefone, e-mail, endereço). "
        "Informe apenas os campos que devem mudar. AÇÃO DESTRUTIVA — exige confirmação."
    ),
    input_model=EditarClienteInput,
    handler=_editar_cliente,
    destrutiva=True,
    permissao_recurso="clientes",
    permissao_acao="escrita",
)
