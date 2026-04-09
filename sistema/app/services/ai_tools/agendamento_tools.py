"""Tools de agendamento: listar, criar, cancelar, remarcar."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.models import StatusAgendamento, Usuario

from ._base import ToolSpec


# ── criar_agendamento (DESTRUTIVA) ────────────────────────────────────────
class CriarAgendamentoInput(BaseModel):
    cliente_id: int = Field(gt=0, description="ID do cliente (use listar_clientes antes).")
    data_agendada: datetime = Field(
        description="Data/hora do agendamento em ISO 8601 (ex: 2026-04-10T14:30:00)."
    )
    duracao_estimada_min: int = Field(default=60, ge=15, le=1440)
    orcamento_id: Optional[int] = Field(default=None, gt=0, description="Opcional: vincular a orçamento aprovado.")
    endereco: Optional[str] = Field(default=None, max_length=500)
    observacoes: Optional[str] = Field(default=None, max_length=500)
    tipo: str = Field(default="servico", max_length=50)


async def _criar_agendamento(
    inp: CriarAgendamentoInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    from app.services.agendamento_service import criar_agendamento as _svc_criar

    agendamento, erro = _svc_criar(
        db=db,
        empresa_id=current_user.empresa_id,
        usuario_id=current_user.id,
        cliente_id=inp.cliente_id,
        data_agendada=inp.data_agendada,
        tipo=inp.tipo,
        orcamento_id=inp.orcamento_id,
        duracao_estimada_min=inp.duracao_estimada_min,
        endereco=inp.endereco,
        observacoes=inp.observacoes,
        origem="assistente_tool",
    )
    if erro or not agendamento:
        return {"error": erro or "Falha ao criar agendamento", "code": "create_error"}
    db.commit()
    db.refresh(agendamento)
    return {
        "id": agendamento.id,
        "numero": agendamento.numero,
        "data_agendada": agendamento.data_agendada.isoformat() if agendamento.data_agendada else None,
        "criado": True,
    }


criar_agendamento = ToolSpec(
    name="criar_agendamento",
    description=(
        "Cria um agendamento (visita/serviço) para um cliente em data/hora específica. "
        "Se vincular a um orçamento, este deve estar APROVADO. "
        "AÇÃO DESTRUTIVA — exige confirmação."
    ),
    input_model=CriarAgendamentoInput,
    handler=_criar_agendamento,
    destrutiva=True,
    permissao_recurso="agendamentos",
    permissao_acao="escrita",
)


# ── listar_agendamentos ────────────────────────────────────────────────────
class ListarAgendamentosInput(BaseModel):
    status: Optional[str] = Field(
        default=None,
        description="Status: pendente, confirmado, em_andamento, concluido, cancelado, etc.",
    )
    cliente_id: Optional[int] = Field(default=None, gt=0)
    dias: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Janela em dias (de hoje-dias até hoje+dias).",
    )
    limit: int = Field(default=20, ge=1, le=100)


async def _listar_agendamentos(
    inp: ListarAgendamentosInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    from app.services import agendamento_service

    agora = datetime.utcnow()
    de = agora - timedelta(days=inp.dias)
    ate = agora + timedelta(days=inp.dias)

    items, total = agendamento_service.listar_agendamentos(
        db=db,
        empresa_id=current_user.empresa_id,
        status=inp.status,
        cliente_id=inp.cliente_id,
        data_de=de,
        data_ate=ate,
        page=1,
        per_page=inp.limit,
    )
    return {
        "total": total,
        "agendamentos": [
            {
                "id": a.get("id"),
                "numero": a.get("numero"),
                "status": a.get("status"),
                "cliente_id": a.get("cliente_id"),
                "cliente_nome": a.get("cliente_nome"),
                "data_agendada": a.get("data_agendada"),
                "orcamento_id": a.get("orcamento_id"),
            }
            for a in items
        ],
    }


listar_agendamentos = ToolSpec(
    name="listar_agendamentos",
    description=(
        "Lista agendamentos da empresa com filtros por status, cliente e janela de dias. "
        "Use para obter o ID antes de cancelar ou remarcar."
    ),
    input_model=ListarAgendamentosInput,
    handler=_listar_agendamentos,
    destrutiva=False,
    cacheable_ttl=15,
    permissao_recurso="agendamentos",
    permissao_acao="leitura",
)


# ── cancelar_agendamento (DESTRUTIVA) ──────────────────────────────────────
class CancelarAgendamentoInput(BaseModel):
    agendamento_id: int = Field(gt=0, description="ID do agendamento (use listar_agendamentos antes).")
    motivo: Optional[str] = Field(default=None, max_length=500)


async def _cancelar_agendamento(
    inp: CancelarAgendamentoInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    from app.services import agendamento_service

    ag, erro = agendamento_service.atualizar_status(
        db=db,
        empresa_id=current_user.empresa_id,
        agendamento_id=inp.agendamento_id,
        usuario_id=current_user.id,
        novo_status=StatusAgendamento.CANCELADO,
        motivo=inp.motivo,
    )
    if erro or not ag:
        code = "not_found" if "não encontrado" in (erro or "") else "invalid_input"
        return {"error": erro or "Falha ao cancelar", "code": code}
    return {
        "id": ag.id,
        "numero": ag.numero,
        "status": ag.status.value if hasattr(ag.status, "value") else str(ag.status),
        "cancelado": True,
    }


cancelar_agendamento = ToolSpec(
    name="cancelar_agendamento",
    description=(
        "Cancela um agendamento existente. Só funciona em status ativos "
        "(pendente, confirmado, em_andamento). AÇÃO DESTRUTIVA — exige confirmação."
    ),
    input_model=CancelarAgendamentoInput,
    handler=_cancelar_agendamento,
    destrutiva=True,
    permissao_recurso="agendamentos",
    permissao_acao="escrita",
)


# ── remarcar_agendamento (DESTRUTIVA) ──────────────────────────────────────
class RemarcarAgendamentoInput(BaseModel):
    agendamento_id: int = Field(gt=0)
    nova_data: datetime = Field(description="Nova data/hora em ISO 8601.")
    motivo: Optional[str] = Field(default=None, max_length=500)


async def _remarcar_agendamento(
    inp: RemarcarAgendamentoInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    from app.services import agendamento_service

    novo, erro = agendamento_service.reagendar(
        db=db,
        empresa_id=current_user.empresa_id,
        agendamento_id=inp.agendamento_id,
        usuario_id=current_user.id,
        nova_data=inp.nova_data,
        motivo=inp.motivo,
    )
    if erro or not novo:
        code = "not_found" if "não encontrado" in (erro or "") else "invalid_input"
        return {"error": erro or "Falha ao remarcar", "code": code}
    return {
        "id": novo.id,
        "numero": novo.numero,
        "data_agendada": novo.data_agendada.isoformat() if novo.data_agendada else None,
        "reagendado_de": inp.agendamento_id,
        "criado": True,
    }


remarcar_agendamento = ToolSpec(
    name="remarcar_agendamento",
    description=(
        "Reagenda um agendamento para nova data/hora. Cria um novo registro vinculado "
        "ao original (que fica marcado como REAGENDADO). AÇÃO DESTRUTIVA — exige confirmação."
    ),
    input_model=RemarcarAgendamentoInput,
    handler=_remarcar_agendamento,
    destrutiva=True,
    permissao_recurso="agendamentos",
    permissao_acao="escrita",
)
