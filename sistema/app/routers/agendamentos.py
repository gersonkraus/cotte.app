"""
Router de Agendamentos — CRUD + integração com orçamento + configurações.

ORDEM DAS ROTAS IMPORTANTE: rotas específicas ANTES de /{agendamento_id}
para evitar conflito de matching.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import exigir_permissao, get_usuario_atual
from app.services.audit_service import registrar_auditoria
from app.models.models import (
    Agendamento,
    Empresa,
    SlotBloqueado,
    StatusAgendamento,
    Usuario,
)
from app.schemas.agendamento import (
    AgendamentoCreate,
    AgendamentoUpdate,
    AgendamentoReagendar,
    AgendamentoStatusUpdate,
    AgendamentoOut,
    AgendamentoCalendario,
    AgendamentoDashboard,
    SlotDisponivel,
    ConfigAgendamentoCreate,
    ConfigAgendamentoUpdate,
    ConfigAgendamentoOut,
    ConfigAgendamentoUsuarioCreate,
    ConfigAgendamentoUsuarioUpdate,
    ConfigAgendamentoUsuarioOut,
    SlotBloqueadoCreate,
    SlotBloqueadoOut,
    HistoricoAgendamentoOut,
    CriarDoOrcamento,
    AgendamentoCreateComOpcoes,
    AgendamentoOpcaoCreate,
    AgendamentoOpcaoOut,
    AgendamentoComOpcoes,
    EscolherOpcaoRequest,
    PreAgendamentoFilaItem,
    PreAgendamentoLiberarRequest,
    PreAgendamentoLiberarResponse,
    PreAgendamentoLiberarResultado,
)
from app.services import agendamento_service

router = APIRouter(prefix="/agendamentos", tags=["Agendamentos"])
logger = logging.getLogger(__name__)


def exigir_permissao_config_agendamento(
    usuario: Usuario = Depends(get_usuario_atual),
) -> Usuario:
    """
    Permissão dedicada para configuração de agenda.
    Mantém fallback temporário para `agendamentos:admin` por compatibilidade.
    """
    try:
        return exigir_permissao("configuracao_agendamento", "admin")(usuario)
    except HTTPException:
        return exigir_permissao("agendamentos", "admin")(usuario)


# ══════════════════════════════════════════════════════════════════════════════
# 1) CRUD BÁSICO (rotas estáticas primeiro)
# ══════════════════════════════════════════════════════════════════════════════


@router.post("/", response_model=AgendamentoOut)
def criar_agendamento(
    dados: AgendamentoCreate,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("agendamentos", "escrita")),
):
    """Cria um novo agendamento."""
    ag, erro = agendamento_service.criar_agendamento(
        db=db,
        empresa_id=usuario.empresa_id,
        usuario_id=usuario.id,
        cliente_id=dados.cliente_id,
        data_agendada=dados.data_agendada,
        tipo=dados.tipo.value,
        orcamento_id=dados.orcamento_id,
        responsavel_id=dados.responsavel_id,
        data_fim=dados.data_fim,
        duracao_estimada_min=dados.duracao_estimada_min,
        endereco=dados.endereco,
        observacoes=dados.observacoes,
    )
    if erro:
        raise HTTPException(status_code=400, detail=erro)

    registrar_auditoria(
        db=db,
        usuario=usuario,
        acao="agendamento_criado",
        recurso="agendamento",
        recurso_id=str(ag.id),
        detalhes={"numero": ag.numero, "cliente_id": ag.cliente_id},
        request=request,
    )
    return agendamento_service._enriquecer_out(ag, db)


@router.post("/criar-do-orcamento/{orcamento_id}", response_model=AgendamentoOut)
def criar_do_orcamento(
    orcamento_id: int,
    dados: CriarDoOrcamento,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("agendamentos", "escrita")),
):
    """Cria agendamento a partir de um orçamento aprovado."""
    ag, erro = agendamento_service.criar_do_orcamento(
        db=db,
        empresa_id=usuario.empresa_id,
        usuario_id=usuario.id,
        orcamento_id=orcamento_id,
        data_agendada=dados.data_agendada,
        responsavel_id=dados.responsavel_id,
        tipo=dados.tipo.value,
        data_fim=dados.data_fim,
        duracao_estimada_min=dados.duracao_estimada_min,
        observacoes=dados.observacoes,
    )
    if erro:
        raise HTTPException(status_code=400, detail=erro)

    registrar_auditoria(
        db=db,
        usuario=usuario,
        acao="agendamento_criado_orcamento",
        recurso="agendamento",
        recurso_id=str(ag.id),
        detalhes={"numero": ag.numero, "orcamento_id": orcamento_id},
        request=request,
    )
    return agendamento_service._enriquecer_out(ag, db)


@router.get("/", response_model=List[AgendamentoOut])
def listar_agendamentos(
    status: Optional[str] = Query(None),
    tipo: Optional[str] = Query(None),
    responsavel_id: Optional[int] = Query(None),
    cliente_id: Optional[int] = Query(None),
    orcamento_id: Optional[int] = Query(None),
    data_de: Optional[datetime] = Query(None),
    data_ate: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("agendamentos", "leitura")),
):
    """Lista agendamentos com filtros."""
    itens, total = agendamento_service.listar_agendamentos(
        db=db,
        empresa_id=usuario.empresa_id,
        status=status,
        tipo=tipo,
        responsavel_id=responsavel_id,
        cliente_id=cliente_id,
        orcamento_id=orcamento_id,
        data_de=data_de,
        data_ate=data_ate,
        page=page,
        per_page=per_page,
    )
    return itens


@router.get("/dashboard", response_model=AgendamentoDashboard)
def get_dashboard(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("agendamentos", "leitura")),
):
    """Dashboard de agendamentos."""
    return agendamento_service.dashboard(db, usuario.empresa_id)


@router.get("/hoje", response_model=List[AgendamentoOut])
def listar_hoje(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("agendamentos", "leitura")),
):
    """Agendamentos de hoje."""
    return agendamento_service.listar_hoje(db, usuario.empresa_id)


@router.get("/disponiveis", response_model=List[SlotDisponivel])
def slots_disponiveis(
    data: datetime = Query(..., description="Data para buscar slots"),
    responsavel_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("agendamentos", "leitura")),
):
    """Retorna slots disponíveis para uma data."""
    return agendamento_service.slots_disponiveis(
        db, usuario.empresa_id, data, responsavel_id
    )


@router.get("/responsaveis")
def listar_responsaveis(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("agendamentos", "leitura")),
):
    """Lista usuários que podem ser responsáveis por agendamentos."""
    return agendamento_service.listar_responsaveis(db, usuario.empresa_id)


# ══════════════════════════════════════════════════════════════════════════════
# 2) CONFIGURAÇÃO (rotas específicas antes de /{agendamento_id})
# ══════════════════════════════════════════════════════════════════════════════


@router.get("/config/empresa", response_model=ConfigAgendamentoOut)
def get_config(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao_config_agendamento),
):
    """Configuração de agendamento da empresa."""
    return agendamento_service.obter_config(db, usuario.empresa_id)


@router.put("/config/empresa", response_model=ConfigAgendamentoOut)
def update_config(
    dados: ConfigAgendamentoUpdate,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao_config_agendamento),
):
    """Atualiza configuração de agendamento da empresa."""
    config = agendamento_service.salvar_config(
        db, usuario.empresa_id, dados.model_dump(exclude_unset=True)
    )
    registrar_auditoria(
        db=db,
        usuario=usuario,
        acao="config_agendamento_atualizada",
        recurso="config_agendamento",
        recurso_id=str(config.id),
        request=request,
    )
    return config


@router.get("/config/usuarios", response_model=List[ConfigAgendamentoUsuarioOut])
def listar_config_usuarios(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao_config_agendamento),
):
    """Lista configurações individuais dos usuários."""
    return agendamento_service.listar_config_usuarios(db, usuario.empresa_id)


@router.post("/config/usuario", response_model=ConfigAgendamentoUsuarioOut)
def criar_config_usuario(
    dados: ConfigAgendamentoUsuarioCreate,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao_config_agendamento),
):
    """Cria ou atualiza configuração individual de um funcionário."""
    config = agendamento_service.salvar_config_usuario(
        db,
        usuario.empresa_id,
        dados.usuario_id,
        dados.model_dump(exclude={"usuario_id"}, exclude_unset=True),
    )
    registrar_auditoria(
        db=db,
        usuario=usuario,
        acao="config_agendamento_usuario_salva",
        recurso="config_agendamento_usuario",
        recurso_id=str(config.id),
        detalhes={"usuario_id": dados.usuario_id},
        request=request,
    )
    return config


@router.delete("/config/usuario/{usuario_id}")
def remover_config_usuario(
    usuario_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao_config_agendamento),
):
    """Remove override de config de um funcionário (volta ao padrão da empresa)."""
    ok = agendamento_service.remover_config_usuario(db, usuario.empresa_id, usuario_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Configuração não encontrada.")
    registrar_auditoria(
        db=db,
        usuario=usuario,
        acao="config_agendamento_usuario_removida",
        recurso="config_agendamento_usuario",
        recurso_id=str(usuario_id),
        request=request,
    )
    return {"mensagem": "Configuração removida."}


# ══════════════════════════════════════════════════════════════════════════════
# 3) SLOTS BLOQUEADOS (rotas específicas antes de /{agendamento_id})
# ══════════════════════════════════════════════════════════════════════════════


@router.post("/bloquear-slot", response_model=SlotBloqueadoOut)
def bloquear_slot(
    dados: SlotBloqueadoCreate,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao_config_agendamento),
):
    """Bloqueia um horário (empresa toda ou funcionário específico)."""
    slot = agendamento_service.criar_slot_bloqueado(
        db=db,
        empresa_id=usuario.empresa_id,
        data_inicio=dados.data_inicio,
        data_fim=dados.data_fim,
        usuario_id=dados.usuario_id,
        motivo=dados.motivo,
        recorrente=dados.recorrente,
        recorrencia_tipo=dados.recorrencia_tipo,
    )
    registrar_auditoria(
        db=db,
        usuario=usuario,
        acao="slot_bloqueado_criado",
        recurso="slot_bloqueado",
        recurso_id=str(slot.id),
        detalhes={"usuario_id": dados.usuario_id, "motivo": dados.motivo},
        request=request,
    )
    return slot


@router.get("/bloqueados", response_model=List[SlotBloqueadoOut])
def listar_bloqueados(
    usuario_id: Optional[int] = Query(None),
    data_de: Optional[datetime] = Query(None),
    data_ate: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("agendamentos", "leitura")),
):
    """Lista slots bloqueados."""
    return agendamento_service.listar_slots_bloqueados(
        db, usuario.empresa_id, usuario_id, data_de, data_ate
    )


@router.delete("/bloquear-slot/{slot_id}")
def remover_slot_bloqueado(
    slot_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao_config_agendamento),
):
    """Remove um slot bloqueado."""
    ok = agendamento_service.remover_slot_bloqueado(db, usuario.empresa_id, slot_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Slot bloqueado não encontrado.")
    registrar_auditoria(
        db=db,
        usuario=usuario,
        acao="slot_bloqueado_removido",
        recurso="slot_bloqueado",
        recurso_id=str(slot_id),
        request=request,
    )
    return {"mensagem": "Slot desbloqueado."}




@router.get("/pre-agendamento/fila", response_model=List[PreAgendamentoFilaItem])
def fila_pre_agendamento(
    canal: Optional[str] = Query(None, description="Filtrar por canal: publico, whatsapp, manual, ia"),
    busca: Optional[str] = Query(None, description="Busca por nome do cliente ou número do orçamento"),
    ordem: str = Query(
        "aprovado_em_desc",
        description="aprovado_em_desc | aprovado_em_asc",
    ),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("agendamentos", "leitura")),
):
    """Lista orçamentos aprovados aguardando liberação das opções de agendamento."""
    from app.services import agendamento_auto_service
    from app.services.agendamento_service import (
        _verificar_pagamento_100,
        percentual_pago_orcamento,
    )

    empresa = (
        db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    )
    rows = agendamento_auto_service.listar_pre_agendamento_fila(
        db,
        usuario.empresa_id,
        canal=canal,
        busca=busca,
        ordem=ordem,
    )
    out: List[PreAgendamentoFilaItem] = []
    for orc in rows:
        pct = percentual_pago_orcamento(orc, db)
        exige = empresa and empresa.agendamento_exige_pagamento_100
        ok_lib = (not exige) or _verificar_pagamento_100(orc, db)
        modo = (
            orc.agendamento_modo.value
            if getattr(orc, "agendamento_modo", None)
            else None
        )
        out.append(
            PreAgendamentoFilaItem(
                orcamento_id=orc.id,
                numero=orc.numero,
                cliente_nome=orc.cliente.nome if orc.cliente else None,
                cliente_telefone=orc.cliente.telefone if orc.cliente else None,
                aprovado_canal=orc.aprovado_canal,
                aprovado_em=orc.aprovado_em,
                aceite_mensagem=orc.aceite_mensagem,
                total=float(orc.total) if orc.total is not None else None,
                percentual_pago=round(pct, 1),
                pagamento_ok_para_liberar=ok_lib,
                agendamento_modo=modo,
            )
        )
    return out


@router.post("/pre-agendamento/liberar", response_model=PreAgendamentoLiberarResponse)
def liberar_pre_agendamento(
    dados: PreAgendamentoLiberarRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("agendamentos", "escrita")),
):
    """Libera um ou mais orçamentos da fila e gera o agendamento com opções de data."""
    from app.services import agendamento_auto_service

    resultados_raw = agendamento_auto_service.liberar_pre_agendamento_lote(
        db,
        usuario.empresa_id,
        dados.orcamento_ids,
        usuario_id=usuario.id,
        observacao=dados.observacao,
    )
    registrar_auditoria(
        db=db,
        usuario=usuario,
        acao="pre_agendamento_liberado",
        recurso="orcamento",
        recurso_id=",".join(str(x) for x in dados.orcamento_ids),
        detalhes={"resultados": resultados_raw},
        request=request,
    )
    return PreAgendamentoLiberarResponse(
        resultados=[
            PreAgendamentoLiberarResultado(**r) for r in resultados_raw
        ]
    )


# ══════════════════════════════════════════════════════════════════════════════
# 4) AGENDAMENTO POR ID (DEVE VIR POR ÚLTIMO — captura /{param})
# ══════════════════════════════════════════════════════════════════════════════


@router.get("/{agendamento_id}/historico", response_model=List[HistoricoAgendamentoOut])
def historico_agendamento(
    agendamento_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("agendamentos", "leitura")),
):
    """Histórico de um agendamento."""
    return agendamento_service.historico_agendamento(
        db, usuario.empresa_id, agendamento_id
    )


@router.patch("/{agendamento_id}/reagendar", response_model=AgendamentoOut)
def reagendar(
    agendamento_id: int,
    dados: AgendamentoReagendar,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("agendamentos", "escrita")),
):
    """Reagenda um agendamento."""
    ag, erro = agendamento_service.reagendar(
        db=db,
        empresa_id=usuario.empresa_id,
        agendamento_id=agendamento_id,
        usuario_id=usuario.id,
        nova_data=dados.nova_data,
        nova_data_fim=dados.nova_data_fim,
        motivo=dados.motivo,
    )
    if erro:
        raise HTTPException(status_code=400, detail=erro)

    registrar_auditoria(
        db=db,
        usuario=usuario,
        acao="agendamento_reagendado",
        recurso="agendamento",
        recurso_id=str(ag.id),
        detalhes={"anterior": agendamento_id, "novo": ag.id},
        request=request,
    )
    return agendamento_service._enriquecer_out(ag, db)


@router.patch("/{agendamento_id}/status", response_model=AgendamentoOut)
def atualizar_status(
    agendamento_id: int,
    dados: AgendamentoStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("agendamentos", "escrita")),
):
    """Atualiza o status de um agendamento."""
    ag, erro = agendamento_service.atualizar_status(
        db=db,
        empresa_id=usuario.empresa_id,
        agendamento_id=agendamento_id,
        usuario_id=usuario.id,
        novo_status=dados.status,
        motivo=dados.motivo,
    )
    if erro:
        raise HTTPException(status_code=400, detail=erro)

    registrar_auditoria(
        db=db,
        usuario=usuario,
        acao=f"agendamento_{dados.status.value}",
        recurso="agendamento",
        recurso_id=str(agendamento_id),
        detalhes={"status": dados.status.value, "motivo": dados.motivo},
        request=request,
    )
    return agendamento_service._enriquecer_out(ag, db)


@router.get("/{agendamento_id}", response_model=AgendamentoOut)
def buscar_agendamento(
    agendamento_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("agendamentos", "leitura")),
):
    """Detalhe de um agendamento."""
    ag = agendamento_service.buscar_agendamento(db, usuario.empresa_id, agendamento_id)
    if not ag:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    return ag


@router.put("/{agendamento_id}", response_model=AgendamentoOut)
def atualizar_agendamento(
    agendamento_id: int,
    dados: AgendamentoUpdate,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("agendamentos", "escrita")),
):
    """Atualiza um agendamento."""
    ag, erro = agendamento_service.atualizar_agendamento(
        db=db,
        empresa_id=usuario.empresa_id,
        agendamento_id=agendamento_id,
        usuario_id=usuario.id,
        cliente_id=dados.cliente_id,
        orcamento_id=dados.orcamento_id,
        responsavel_id=dados.responsavel_id,
        tipo=dados.tipo.value if dados.tipo else None,
        data_agendada=dados.data_agendada,
        data_fim=dados.data_fim,
        duracao_estimada_min=dados.duracao_estimada_min,
        endereco=dados.endereco,
        observacoes=dados.observacoes,
    )
    if erro:
        raise HTTPException(status_code=400, detail=erro)

    registrar_auditoria(
        db=db,
        usuario=usuario,
        acao="agendamento_atualizado",
        recurso="agendamento",
        recurso_id=str(agendamento_id),
        request=request,
    )
    return agendamento_service._enriquecer_out(ag, db)


# ══════════════════════════════════════════════════════════════════════════════
# OPÇÕES DE DATA/HORA (rotas específicas)
# ══════════════════════════════════════════════════════════════════════════════


@router.post("/com-opcoes", response_model=AgendamentoOut)
def criar_com_opcoes(
    dados: AgendamentoCreateComOpcoes,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("agendamentos", "escrita")),
):
    """Cria agendamento com opções de data/hora para o cliente escolher."""
    ag, erro = agendamento_service.criar_agendamento_com_opcoes(
        db=db,
        empresa_id=usuario.empresa_id,
        usuario_id=usuario.id,
        cliente_id=dados.cliente_id,
        orcamento_id=dados.orcamento_id,
        responsavel_id=dados.responsavel_id,
        tipo=dados.tipo.value,
        duracao_estimada_min=dados.duracao_estimada_min,
        endereco=dados.endereco,
        observacoes=dados.observacoes,
        opcoes_datas=[o.model_dump() for o in dados.opcoes],
    )
    if erro:
        raise HTTPException(status_code=400, detail=erro)

    registrar_auditoria(
        db=db,
        usuario=usuario,
        acao="agendamento_criado_com_opcoes",
        recurso="agendamento",
        recurso_id=str(ag.id),
        detalhes={"numero": ag.numero, "opcoes": len(dados.opcoes)},
        request=request,
    )
    return agendamento_service._enriquecer_out(ag, db)
