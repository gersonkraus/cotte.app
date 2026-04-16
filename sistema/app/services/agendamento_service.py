"""
Agendamento Service — lógica de negócio do módulo de agendamentos.

Regras de negócio:
- Orçamento deve estar APROVADO para criar agendamento vinculado
- Data não pode ser no passado
- Data deve estar dentro do horário de trabalho (config)
- Slot não pode conflitar com agendamentos existentes do responsável
- Slot não pode estar bloqueado (empresa ou individual)
- Antecedência mínima deve ser respeitada
- Reagendamento só de pendente/confirmado
- Cancelamento não retroativo (se já passou → nao_compareceu)
- Idempotência: não criar duplicado pro mesmo orçamento
"""

import logging
from datetime import datetime, timedelta, timezone, time
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, exists

from app.models.models import (
    Agendamento,
    AgendamentoOpcao,
    ConfigAgendamento,
    ConfigAgendamentoUsuario,
    ContaFinanceira,
    SlotBloqueado,
    Empresa,
    HistoricoAgendamento,
    Orcamento,
    Cliente,
    Usuario,
    Notificacao,
    StatusAgendamento,
    StatusConta,
    StatusOrcamento,
    TipoConta,
    OrigemAgendamento,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS INTERNOS
# ══════════════════════════════════════════════════════════════════════════════


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_to_utc(dt: datetime) -> datetime:
    """Converte datetime para UTC. Valores naive usam o fuso local do servidor."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc)
    local_tz = datetime.now().astimezone().tzinfo
    if local_tz is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.replace(tzinfo=local_tz).astimezone(timezone.utc)


def _registrar_historico(
    db: Session,
    agendamento_id: int,
    status_anterior: Optional[str],
    status_novo: str,
    descricao: Optional[str] = None,
    editado_por_id: Optional[int] = None,
):
    h = HistoricoAgendamento(
        agendamento_id=agendamento_id,
        status_anterior=status_anterior,
        status_novo=status_novo,
        descricao=descricao,
        editado_por_id=editado_por_id,
    )
    db.add(h)


def _gerar_numero(db: Session, empresa_id: int) -> str:
    """Gera número sequencial AGD-{empresa_id}-{seq}."""
    ultimo = (
        db.query(Agendamento)
        .filter(Agendamento.empresa_id == empresa_id)
        .order_by(Agendamento.id.desc())
        .first()
    )
    seq = 1
    if ultimo and ultimo.numero:
        try:
            partes = ultimo.numero.split("-")
            seq = int(partes[-1]) + 1
        except (ValueError, IndexError):
            pass
    return f"AGD-{empresa_id}-{seq:03d}"


def _obter_config(db: Session, empresa_id: int) -> ConfigAgendamento:
    """Busca ou cria config padrão da empresa."""
    config = (
        db.query(ConfigAgendamento)
        .filter(ConfigAgendamento.empresa_id == empresa_id)
        .first()
    )
    if not config:
        config = ConfigAgendamento(empresa_id=empresa_id)
        db.add(config)
        db.flush()
    return config


def _obter_config_usuario(
    db: Session, empresa_id: int, usuario_id: int
) -> Optional[ConfigAgendamentoUsuario]:
    return (
        db.query(ConfigAgendamentoUsuario)
        .filter(
            ConfigAgendamentoUsuario.empresa_id == empresa_id,
            ConfigAgendamentoUsuario.usuario_id == usuario_id,
            ConfigAgendamentoUsuario.ativo == True,
        )
        .first()
    )


def _merge_config(
    config_empresa: ConfigAgendamento,
    config_usuario: Optional[ConfigAgendamentoUsuario],
) -> dict:
    """Merge: config do usuário sobrepõe a da empresa."""
    return {
        "horario_inicio": (
            config_usuario.horario_inicio
            if config_usuario and config_usuario.horario_inicio
            else config_empresa.horario_inicio
        ),
        "horario_fim": (
            config_usuario.horario_fim
            if config_usuario and config_usuario.horario_fim
            else config_empresa.horario_fim
        ),
        "dias_trabalho": (
            config_usuario.dias_trabalho
            if config_usuario and config_usuario.dias_trabalho
            else config_empresa.dias_trabalho
        ),
        "duracao_padrao_min": (
            config_usuario.duracao_padrao_min
            if config_usuario and config_usuario.duracao_padrao_min
            else config_empresa.duracao_padrao_min
        ),
        "intervalo_minimo_min": config_empresa.intervalo_minimo_min,
        "antecedencia_minima_horas": config_empresa.antecedencia_minima_horas,
    }


def _verificar_antecedencia(config: dict, data_agendada: datetime) -> Tuple[bool, str]:
    """Verifica se a data respeita a antecedência mínima."""
    min_horas = config.get("antecedencia_minima_horas", 1)
    if min_horas <= 0:
        return True, ""
    limite = _now() + timedelta(hours=min_horas)
    if data_agendada < limite:
        return (
            False,
            f"Agendamento precisa ser com pelo menos {min_horas}h de antecedência.",
        )
    return True, ""


def _verificar_dia_trabalho(config: dict, data: datetime) -> Tuple[bool, str]:
    """Verifica se o dia da semana é dia de trabalho. 0=seg..6=dom."""
    dias = config.get("dias_trabalho", [0, 1, 2, 3, 4])
    # Python weekday: 0=seg..6=dom — mesmo padrão
    if data.weekday() not in dias:
        nome_dia = [
            "segunda",
            "terça",
            "quarta",
            "quinta",
            "sexta",
            "sábado",
            "domingo",
        ][data.weekday()]
        return False, f"{nome_dia.capitalize()} não é dia de trabalho."
    return True, ""


def _verificar_horario_trabalho(
    config: dict, data_inicio: datetime, data_fim: datetime
) -> Tuple[bool, str]:
    """Verifica se o horário está dentro da janela de trabalho."""
    h_inicio_str = config.get("horario_inicio", "08:00")
    h_fim_str = config.get("horario_fim", "18:00")
    h_inicio = time(*map(int, h_inicio_str.split(":")))
    h_fim = time(*map(int, h_fim_str.split(":")))
    if data_inicio.time() < h_inicio or data_fim.time() > h_fim:
        return False, f"Horário fora do expediente ({h_inicio_str} às {h_fim_str})."
    return True, ""


def _verificar_conflito(
    db: Session,
    empresa_id: int,
    data_inicio: datetime,
    data_fim: datetime,
    responsavel_id: Optional[int] = None,
    excluir_id: Optional[int] = None,
) -> Tuple[bool, str]:
    """Verifica se existe conflito com outros agendamentos do responsável."""
    query = db.query(Agendamento).filter(
        Agendamento.empresa_id == empresa_id,
        Agendamento.status.notin_(
            [
                StatusAgendamento.CANCELADO,
                StatusAgendamento.NAO_COMPARECEU,
                StatusAgendamento.CONCLUIDO,
            ]
        ),
        Agendamento.data_agendada < data_fim,
        or_(
            Agendamento.data_fim > data_inicio,
            Agendamento.data_fim.is_(None),
            Agendamento.data_agendada
            + func.make_interval(0, 0, 0, 0, 0, Agendamento.duracao_estimada_min)
            > data_inicio,
        ),
    )
    if responsavel_id:
        query = query.filter(Agendamento.responsavel_id == responsavel_id)
    if excluir_id:
        query = query.filter(Agendamento.id != excluir_id)

    conflito = query.first()
    if conflito:
        return False, f"Conflito com agendamento {conflito.numero} no mesmo horário."
    return True, ""


def _verificar_slot_bloqueado(
    db: Session,
    empresa_id: int,
    data_inicio: datetime,
    data_fim: datetime,
    responsavel_id: Optional[int] = None,
) -> Tuple[bool, str]:
    """Verifica se o slot está bloqueado (empresa ou individual)."""
    query = db.query(SlotBloqueado).filter(
        SlotBloqueado.empresa_id == empresa_id,
        SlotBloqueado.data_inicio < data_fim,
        SlotBloqueado.data_fim > data_inicio,
    )
    # Bloqueios empresa (NULL) OU do responsável específico
    if responsavel_id:
        query = query.filter(
            or_(
                SlotBloqueado.usuario_id.is_(None),
                SlotBloqueado.usuario_id == responsavel_id,
            )
        )
    else:
        query = query.filter(SlotBloqueado.usuario_id.is_(None))

    bloqueio = query.first()
    if bloqueio:
        quem = "empresa" if not bloqueio.usuario_id else f"usuário"
        motivo = f" ({bloqueio.motivo})" if bloqueio.motivo else ""
        return False, f"Horário bloqueado ({quem}){motivo}."
    return True, ""


def _validar_opcao_data_hora(
    db: Session,
    empresa_id: int,
    responsavel_id: Optional[int],
    duracao_estimada_min: int,
    data_hora: datetime,
    excluir_agendamento_id: Optional[int] = None,
) -> Tuple[bool, str]:
    """Valida uma opção de data com as mesmas regras da criação normal."""
    data_fim = _calcular_data_fim(data_hora, duracao_estimada_min)
    config_empresa = _obter_config(db, empresa_id)
    config_usuario = (
        _obter_config_usuario(db, empresa_id, responsavel_id)
        if responsavel_id
        else None
    )
    config = _merge_config(config_empresa, config_usuario)

    ok, erro = _verificar_antecedencia(config, data_hora)
    if not ok:
        return False, erro
    ok, erro = _verificar_dia_trabalho(config, data_hora)
    if not ok:
        return False, erro
    ok, erro = _verificar_horario_trabalho(config, data_hora, data_fim)
    if not ok:
        return False, erro
    ok, erro = _verificar_conflito(
        db=db,
        empresa_id=empresa_id,
        data_inicio=data_hora,
        data_fim=data_fim,
        responsavel_id=responsavel_id,
        excluir_id=excluir_agendamento_id,
    )
    if not ok:
        return False, erro
    ok, erro = _verificar_slot_bloqueado(
        db=db,
        empresa_id=empresa_id,
        data_inicio=data_hora,
        data_fim=data_fim,
        responsavel_id=responsavel_id,
    )
    if not ok:
        return False, erro
    return True, ""


def _montar_mensagem_agendamento_template(
    template: Optional[str],
    agendamento: Agendamento,
    nova_data: datetime,
) -> Optional[str]:
    """Renderiza mensagens customizadas de agendamento com placeholders simples."""
    if not template:
        return None
    mensagem = template
    cliente_nome = agendamento.cliente.nome if agendamento.cliente else "Cliente"
    placeholders = {
        "{cliente_nome}": cliente_nome,
        "{agendamento_numero}": agendamento.numero or "",
        "{data}": nova_data.strftime("%d/%m/%Y"),
        "{hora}": nova_data.strftime("%H:%M"),
    }
    for chave, valor in placeholders.items():
        mensagem = mensagem.replace(chave, valor)
    return mensagem.strip() or None


def _enriquecer_out(
    ag: Agendamento,
    db: Session,
    *,
    calendario_data_de: Optional[datetime] = None,
    calendario_data_ate: Optional[datetime] = None,
) -> dict:
    """Adiciona campos extras ao dict de saída.

    Para calendário, passe calendario_data_de/ate: em aguardando_escolha a data
    exibida é a primeira opção que cai nesse intervalo (visão do mês/semana).
    """
    d = {
        "id": ag.id,
        "empresa_id": ag.empresa_id,
        "cliente_id": ag.cliente_id,
        "orcamento_id": ag.orcamento_id,
        "criado_por_id": ag.criado_por_id,
        "responsavel_id": ag.responsavel_id,
        "numero": ag.numero,
        "status": ag.status,
        "tipo": ag.tipo,
        "origem": ag.origem,
        "data_agendada": ag.data_agendada,
        "data_fim": ag.data_fim,
        "duracao_estimada_min": ag.duracao_estimada_min,
        "endereco": ag.endereco,
        "observacoes": ag.observacoes,
        "motivo_cancelamento": ag.motivo_cancelamento,
        "confirmado_em": ag.confirmado_em,
        "cancelado_em": ag.cancelado_em,
        "concluido_em": ag.concluido_em,
        "reagendamento_anterior_id": ag.reagendamento_anterior_id,
        "criado_em": ag.criado_em,
        "atualizado_em": ag.atualizado_em,
    }
    # Dados enriquecidos
    try:
        cliente = db.query(Cliente).filter(Cliente.id == ag.cliente_id).first()
        d["cliente_nome"] = cliente.nome if cliente else None
    except AttributeError:
        d["cliente_nome"] = None
    try:
        if ag.responsavel_id:
            resp = db.query(Usuario).filter(Usuario.id == ag.responsavel_id).first()
            d["responsavel_nome"] = resp.nome if resp else None
        else:
            d["responsavel_nome"] = None
    except AttributeError:
        d["responsavel_nome"] = None
    try:
        if ag.orcamento_id:
            orc = db.query(Orcamento).filter(Orcamento.id == ag.orcamento_id).first()
            d["orcamento_numero"] = orc.numero if orc else None
        else:
            d["orcamento_numero"] = None
    except AttributeError:
        d["orcamento_numero"] = None

    d["primeira_opcao_data_hora"] = None
    if ag.status == StatusAgendamento.AGUARDANDO_ESCOLHA:
        base = db.query(AgendamentoOpcao.data_hora).filter(
            AgendamentoOpcao.agendamento_id == ag.id,
            AgendamentoOpcao.disponivel.is_(True),
        )
        if calendario_data_de or calendario_data_ate:
            q_iv = base
            if calendario_data_de:
                q_iv = q_iv.filter(AgendamentoOpcao.data_hora >= calendario_data_de)
            if calendario_data_ate:
                q_iv = q_iv.filter(AgendamentoOpcao.data_hora <= calendario_data_ate)
            no_intervalo = q_iv.order_by(AgendamentoOpcao.data_hora.asc()).first()
            if no_intervalo:
                d["primeira_opcao_data_hora"] = no_intervalo[0]
            else:
                fallback = base.order_by(AgendamentoOpcao.data_hora.asc()).first()
                if fallback:
                    d["primeira_opcao_data_hora"] = fallback[0]
        else:
            primeira = base.order_by(AgendamentoOpcao.data_hora.asc()).first()
            if primeira:
                d["primeira_opcao_data_hora"] = primeira[0]
    return d


def _calcular_data_fim(data_inicio: datetime, duracao_min: int) -> datetime:
    return data_inicio + timedelta(minutes=duracao_min)


def _verificar_pagamento_100(orcamento: Orcamento, db: Session) -> bool:
    """Retorna True se todas as contas a receber do orçamento estão pagas.

    Política atual: se não houver contas a receber vinculadas, retorna False.
    """
    contas = (
        db.query(ContaFinanceira)
        .filter(
            ContaFinanceira.orcamento_id == orcamento.id,
            ContaFinanceira.tipo == TipoConta.RECEBER,
            ContaFinanceira.status != StatusConta.CANCELADO,
        )
        .all()
    )
    if not contas:
        return False
    return all(c.status == StatusConta.PAGO for c in contas)


def percentual_pago_orcamento(orcamento: Orcamento, db: Session) -> float:
    """Percentual pago nas contas a receber do orçamento (0–100)."""
    from decimal import Decimal

    contas = (
        db.query(ContaFinanceira)
        .filter(
            ContaFinanceira.orcamento_id == orcamento.id,
            ContaFinanceira.tipo == TipoConta.RECEBER,
            ContaFinanceira.status != StatusConta.CANCELADO,
        )
        .all()
    )
    if not contas:
        return 0.0
    total = sum(Decimal(str(c.valor or 0)) for c in contas)
    pago = sum(Decimal(str(c.valor_pago or 0)) for c in contas)
    if total <= 0:
        return 0.0
    return float((pago / total) * Decimal("100"))


# ══════════════════════════════════════════════════════════════════════════════
# CRUD
# ══════════════════════════════════════════════════════════════════════════════


def criar_agendamento(
    db: Session,
    empresa_id: int,
    usuario_id: int,
    cliente_id: int,
    data_agendada: datetime,
    tipo: str = "servico",
    orcamento_id: Optional[int] = None,
    responsavel_id: Optional[int] = None,
    data_fim: Optional[datetime] = None,
    duracao_estimada_min: int = 60,
    endereco: Optional[str] = None,
    observacoes: Optional[str] = None,
    origem: str = "manual",
) -> Tuple[Optional[Agendamento], str]:
    """
    Cria um agendamento com todas as validações.
    Retorna (agendamento, erro). Se sucesso, erro="".
    """
    now = _now()

    # 1. Validar orçamento (se informado)
    if orcamento_id:
        existente = (
            db.query(Agendamento)
            .filter(
                Agendamento.empresa_id == empresa_id,
                Agendamento.orcamento_id == orcamento_id,
                Agendamento.status.notin_(
                    [
                        StatusAgendamento.CANCELADO,
                        StatusAgendamento.NAO_COMPARECEU,
                    ]
                ),
            )
            .first()
        )
        if existente:
            return (
                None,
                f"Já existe agendamento ativo ({existente.numero}) para este orçamento.",
            )

        orc = (
            db.query(Orcamento)
            .filter(
                Orcamento.id == orcamento_id,
                Orcamento.empresa_id == empresa_id,
            )
            .first()
        )
        if not orc:
            return None, "Orçamento não encontrado."
        if orc.status != StatusOrcamento.APROVADO:
            return (
                None,
                f"Orçamento deve estar aprovado. Status atual: {orc.status.value}.",
            )

    # 2. Validar cliente
    cliente = (
        db.query(Cliente)
        .filter(
            Cliente.id == cliente_id,
            Cliente.empresa_id == empresa_id,
        )
        .first()
    )
    if not cliente:
        return None, "Cliente não encontrado."

    # 3. Calcular data_fim
    if not data_fim:
        data_fim = _calcular_data_fim(data_agendada, duracao_estimada_min)

    # 4. Validar data não no passado
    if data_agendada < now:
        return None, "Não é possível agendar no passado."

    # 5. Obter config (empresa + usuário)
    config_empresa = _obter_config(db, empresa_id)
    responsavel_efetivo = responsavel_id or usuario_id
    config_usuario = _obter_config_usuario(db, empresa_id, responsavel_efetivo)
    config = _merge_config(config_empresa, config_usuario)

    # 6. Validar antecedência
    ok, erro = _verificar_antecedencia(config, data_agendada)
    if not ok:
        return None, erro

    # 7. Validar dia de trabalho
    ok, erro = _verificar_dia_trabalho(config, data_agendada)
    if not ok:
        return None, erro

    # 8. Validar horário de trabalho
    ok, erro = _verificar_horario_trabalho(config, data_agendada, data_fim)
    if not ok:
        return None, erro

    # 9. Verificar conflitos
    ok, erro = _verificar_conflito(
        db, empresa_id, data_agendada, data_fim, responsavel_efetivo
    )
    if not ok:
        return None, erro

    # 10. Verificar bloqueios
    ok, erro = _verificar_slot_bloqueado(
        db, empresa_id, data_agendada, data_fim, responsavel_efetivo
    )
    if not ok:
        return None, erro

    # 11. Criar agendamento
    numero = _gerar_numero(db, empresa_id)
    status_inicial = (
        StatusAgendamento.CONFIRMADO
        if not config_empresa.requer_confirmacao
        else StatusAgendamento.PENDENTE
    )

    ag = Agendamento(
        empresa_id=empresa_id,
        cliente_id=cliente_id,
        orcamento_id=orcamento_id,
        criado_por_id=usuario_id,
        responsavel_id=responsavel_efetivo,
        numero=numero,
        status=status_inicial,
        tipo=tipo,
        origem=origem,
        data_agendada=data_agendada,
        data_fim=data_fim,
        duracao_estimada_min=duracao_estimada_min,
        endereco=endereco or cliente.endereco,
        observacoes=observacoes,
    )
    db.add(ag)
    db.flush()

    # 12. Vincular orçamento (se informado)
    if orcamento_id:
        orc = db.query(Orcamento).filter(Orcamento.id == orcamento_id).first()
        if orc:
            orc.agendamento_id = ag.id

    # 13. Herdar endereço do orçamento se não informado
    if not endereco and orcamento_id:
        orc = db.query(Orcamento).filter(Orcamento.id == orcamento_id).first()
        if orc and orc.cliente:
            ag.endereco = orc.cliente.endereco

    # 14. Histórico
    _registrar_historico(
        db,
        ag.id,
        None,
        status_inicial.value,
        f"Agendamento criado ({origem}).",
        editado_por_id=usuario_id,
    )

    db.commit()
    db.refresh(ag)
    logger.info(f"Agendamento criado: {ag.numero} (empresa={empresa_id})")
    return ag, ""


def criar_do_orcamento(
    db: Session,
    empresa_id: int,
    usuario_id: int,
    orcamento_id: int,
    data_agendada: datetime,
    responsavel_id: Optional[int] = None,
    tipo: str = "servico",
    data_fim: Optional[datetime] = None,
    duracao_estimada_min: int = 60,
    observacoes: Optional[str] = None,
) -> Tuple[Optional[Agendamento], str]:
    """Atalho: cria agendamento a partir de um orçamento aprovado."""
    orc = (
        db.query(Orcamento)
        .filter(
            Orcamento.id == orcamento_id,
            Orcamento.empresa_id == empresa_id,
        )
        .first()
    )
    if not orc:
        return None, "Orçamento não encontrado."

    return criar_agendamento(
        db=db,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        cliente_id=orc.cliente_id,
        data_agendada=data_agendada,
        tipo=tipo,
        orcamento_id=orcamento_id,
        responsavel_id=responsavel_id,
        data_fim=data_fim,
        duracao_estimada_min=duracao_estimada_min,
        endereco=orc.cliente.endereco if orc.cliente else None,
        observacoes=observacoes,
        origem="automatico",
    )


def atualizar_agendamento(
    db: Session,
    empresa_id: int,
    agendamento_id: int,
    usuario_id: int,
    cliente_id: Optional[int] = None,
    orcamento_id: Optional[int] = None,
    responsavel_id: Optional[int] = None,
    tipo: Optional[str] = None,
    data_agendada: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
    duracao_estimada_min: Optional[int] = None,
    endereco: Optional[str] = None,
    observacoes: Optional[str] = None,
) -> Tuple[Optional[Agendamento], str]:
    """Atualiza campos básicos de um agendamento pendente/confirmado."""
    ag = (
        db.query(Agendamento)
        .filter(
            Agendamento.id == agendamento_id,
            Agendamento.empresa_id == empresa_id,
        )
        .first()
    )
    if not ag:
        return None, "Agendamento não encontrado."

    if ag.status in (
        StatusAgendamento.CANCELADO,
        StatusAgendamento.CONCLUIDO,
        StatusAgendamento.NAO_COMPARECEU,
    ):
        return None, f"Agendamento com status '{ag.status.value}' não pode ser editado."

    # Se mudando data, re-validar
    nova_data = data_agendada or ag.data_agendada
    nova_duracao = duracao_estimada_min or ag.duracao_estimada_min
    nova_data_fim = data_fim or _calcular_data_fim(nova_data, nova_duracao)
    resp = responsavel_id or ag.responsavel_id

    if data_agendada or duracao_estimada_min or responsavel_id:
        if nova_data < _now():
            return None, "Não é possível agendar no passado."

        config_empresa = _obter_config(db, empresa_id)
        config_usuario = _obter_config_usuario(db, empresa_id, resp) if resp else None
        config = _merge_config(config_empresa, config_usuario)

        ok, erro = _verificar_antecedencia(config, nova_data)
        if not ok:
            return None, erro
        ok, erro = _verificar_dia_trabalho(config, nova_data)
        if not ok:
            return None, erro
        ok, erro = _verificar_horario_trabalho(config, nova_data, nova_data_fim)
        if not ok:
            return None, erro
        ok, erro = _verificar_conflito(
            db, empresa_id, nova_data, nova_data_fim, resp, excluir_id=ag.id
        )
        if not ok:
            return None, erro
        ok, erro = _verificar_slot_bloqueado(
            db, empresa_id, nova_data, nova_data_fim, resp
        )
        if not ok:
            return None, erro

    if cliente_id is not None:
        ag.cliente_id = cliente_id
    if orcamento_id is not None:
        ag.orcamento_id = orcamento_id
    if responsavel_id is not None:
        ag.responsavel_id = responsavel_id
    if tipo is not None:
        ag.tipo = tipo
    if data_agendada is not None:
        ag.data_agendada = data_agendada
    if data_fim is not None:
        ag.data_fim = data_fim
    elif data_agendada is not None or duracao_estimada_min is not None:
        ag.data_fim = nova_data_fim
    if duracao_estimada_min is not None:
        ag.duracao_estimada_min = duracao_estimada_min
    if endereco is not None:
        ag.endereco = endereco
    if observacoes is not None:
        ag.observacoes = observacoes

    _registrar_historico(
        db,
        ag.id,
        ag.status.value,
        ag.status.value,
        "Agendamento atualizado.",
        editado_por_id=usuario_id,
    )

    db.commit()
    db.refresh(ag)
    return ag, ""


def reagendar(
    db: Session,
    empresa_id: int,
    agendamento_id: int,
    usuario_id: int,
    nova_data: datetime,
    nova_data_fim: Optional[datetime] = None,
    motivo: Optional[str] = None,
) -> Tuple[Optional[Agendamento], str]:
    """Reagenda um agendamento (cria novo registro com vínculo)."""
    ag = (
        db.query(Agendamento)
        .filter(
            Agendamento.id == agendamento_id,
            Agendamento.empresa_id == empresa_id,
        )
        .first()
    )
    if not ag:
        return None, "Agendamento não encontrado."

    if ag.status not in (
        StatusAgendamento.PENDENTE,
        StatusAgendamento.CONFIRMADO,
        StatusAgendamento.AGUARDANDO_ESCOLHA,
    ):
        return (
            None,
            f"Agendamento com status '{ag.status.value}' não pode ser reagendado.",
        )

    if nova_data < _now():
        return None, "Nova data não pode ser no passado."

    # Validar novo slot
    resp = ag.responsavel_id
    config_empresa = _obter_config(db, empresa_id)
    config_usuario = _obter_config_usuario(db, empresa_id, resp) if resp else None
    config = _merge_config(config_empresa, config_usuario)

    duracao = ag.duracao_estimada_min or 60
    nfim = nova_data_fim or _calcular_data_fim(nova_data, duracao)

    ok, erro = _verificar_antecedencia(config, nova_data)
    if not ok:
        return None, erro
    ok, erro = _verificar_dia_trabalho(config, nova_data)
    if not ok:
        return None, erro
    ok, erro = _verificar_horario_trabalho(config, nova_data, nfim)
    if not ok:
        return None, erro
    ok, erro = _verificar_conflito(db, empresa_id, nova_data, nfim, resp)
    if not ok:
        return None, erro
    ok, erro = _verificar_slot_bloqueado(db, empresa_id, nova_data, nfim, resp)
    if not ok:
        return None, erro

    # Marcar antigo como reagendado
    status_anterior = ag.status.value
    ag.status = StatusAgendamento.REAGENDADO
    _registrar_historico(
        db,
        ag.id,
        status_anterior,
        "reagendado",
        motivo or "Reagendado pelo operador.",
        editado_por_id=usuario_id,
    )

    # Criar novo
    numero = _gerar_numero(db, empresa_id)
    novo = Agendamento(
        empresa_id=ag.empresa_id,
        cliente_id=ag.cliente_id,
        orcamento_id=ag.orcamento_id,
        criado_por_id=usuario_id,
        responsavel_id=ag.responsavel_id,
        numero=numero,
        status=StatusAgendamento.PENDENTE
        if config_empresa.requer_confirmacao
        else StatusAgendamento.CONFIRMADO,
        tipo=ag.tipo,
        origem=ag.origem,
        data_agendada=nova_data,
        data_fim=nfim,
        duracao_estimada_min=duracao,
        endereco=ag.endereco,
        observacoes=ag.observacoes,
        reagendamento_anterior_id=ag.id,
    )
    msg_reagendamento = _montar_mensagem_agendamento_template(
        config_empresa.mensagem_reagendamento,
        ag,
        nova_data,
    )
    if msg_reagendamento:
        novo.observacoes = (
            f"{ag.observacoes}\n\n{msg_reagendamento}"
            if ag.observacoes
            else msg_reagendamento
        )
    db.add(novo)
    db.flush()

    _registrar_historico(
        db,
        novo.id,
        None,
        novo.status.value,
        f"Reagendamento de {ag.numero}. {motivo or ''}",
        editado_por_id=usuario_id,
    )

    # Atualizar vínculo no orçamento
    if ag.orcamento_id:
        orc = db.query(Orcamento).filter(Orcamento.id == ag.orcamento_id).first()
        if orc:
            orc.agendamento_id = novo.id

    db.commit()
    db.refresh(novo)
    return novo, ""


def atualizar_status(
    db: Session,
    empresa_id: int,
    agendamento_id: int,
    usuario_id: int,
    novo_status: StatusAgendamento,
    motivo: Optional[str] = None,
) -> Tuple[Optional[Agendamento], str]:
    """Atualiza o status de um agendamento com validações de transição."""
    ag = (
        db.query(Agendamento)
        .filter(
            Agendamento.id == agendamento_id,
            Agendamento.empresa_id == empresa_id,
        )
        .first()
    )
    if not ag:
        return None, "Agendamento não encontrado."

    # Transições permitidas
    transicoes = {
        StatusAgendamento.PENDENTE: [
            StatusAgendamento.CONFIRMADO,
            StatusAgendamento.CANCELADO,
        ],
        StatusAgendamento.AGUARDANDO_ESCOLHA: [
            StatusAgendamento.CANCELADO,
        ],
        StatusAgendamento.CONFIRMADO: [
            StatusAgendamento.EM_ANDAMENTO,
            StatusAgendamento.CANCELADO,
            StatusAgendamento.NAO_COMPARECEU,
        ],
        StatusAgendamento.EM_ANDAMENTO: [
            StatusAgendamento.CONCLUIDO,
            StatusAgendamento.CANCELADO,
        ],
        # CONCLUIDO, CANCELADO, NAO_COMPARECEU, REAGENDADO são finais (exceto reagendamento)
    }
    permitidos = transicoes.get(ag.status, [])
    if novo_status not in permitidos:
        return (
            None,
            f"Transição não permitida: {ag.status.value} → {novo_status.value}.",
        )

    now = _now()

    if novo_status == StatusAgendamento.CONFIRMADO:
        # Bloqueio: pagamento 100% exigido antes de confirmar.
        # A validação ocorre antes da mutação do status para evitar estado transitório.
        if ag.orcamento_id:
            empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
            if empresa and empresa.agendamento_exige_pagamento_100:
                orc = (
                    db.query(Orcamento).filter(Orcamento.id == ag.orcamento_id).first()
                )
                if orc and not _verificar_pagamento_100(orc, db):
                    return (
                        None,
                        "Pagamento 100% necessário para confirmar agendamento.",
                    )

    status_anterior = ag.status.value
    ag.status = novo_status

    if novo_status == StatusAgendamento.CONFIRMADO:
        ag.confirmado_em = now
    elif novo_status == StatusAgendamento.CANCELADO:
        ag.cancelado_em = now
        ag.motivo_cancelamento = motivo
        if ag.orcamento_id:
            orc = db.query(Orcamento).filter(Orcamento.id == ag.orcamento_id).first()
            if orc and orc.agendamento_id == ag.id:
                orc.agendamento_id = None
    elif novo_status == StatusAgendamento.CONCLUIDO:
        ag.concluido_em = now
    elif novo_status == StatusAgendamento.NAO_COMPARECEU:
        ag.cancelado_em = now
        ag.motivo_cancelamento = motivo or "Cliente não compareceu."
        if ag.orcamento_id:
            orc = db.query(Orcamento).filter(Orcamento.id == ag.orcamento_id).first()
            if orc and orc.agendamento_id == ag.id:
                orc.agendamento_id = None

    # Automação de status do orçamento
    if ag.orcamento_id and novo_status in (
        StatusAgendamento.CONFIRMADO,
        StatusAgendamento.EM_ANDAMENTO,
        StatusAgendamento.CONCLUIDO,
    ):
        empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
        if empresa and empresa.auto_status_orcamento:
            orc = db.query(Orcamento).filter(Orcamento.id == ag.orcamento_id).first()
            if orc and orc.status != StatusOrcamento.CONCLUIDO:
                if novo_status in (
                    StatusAgendamento.CONFIRMADO,
                    StatusAgendamento.EM_ANDAMENTO,
                ):
                    if orc.status == StatusOrcamento.APROVADO:
                        orc.status = StatusOrcamento.EM_EXECUCAO
                elif novo_status == StatusAgendamento.CONCLUIDO:
                    if orc.status in (
                        StatusOrcamento.APROVADO,
                        StatusOrcamento.EM_EXECUCAO,
                    ):
                        if _verificar_pagamento_100(orc, db):
                            orc.status = StatusOrcamento.CONCLUIDO
                        else:
                            orc.status = StatusOrcamento.AGUARDANDO_PAGAMENTO

    descricao = f"Status: {status_anterior} → {novo_status.value}."
    if motivo:
        descricao += f" Motivo: {motivo}"

    _registrar_historico(
        db,
        ag.id,
        status_anterior,
        novo_status.value,
        descricao,
        editado_por_id=usuario_id,
    )

    db.commit()
    db.refresh(ag)
    return ag, ""


def buscar_agendamento(
    db: Session, empresa_id: int, agendamento_id: int
) -> Optional[dict]:
    ag = (
        db.query(Agendamento)
        .filter(
            Agendamento.id == agendamento_id,
            Agendamento.empresa_id == empresa_id,
        )
        .first()
    )
    if not ag:
        return None
    return _enriquecer_out(ag, db)


def listar_agendamentos(
    db: Session,
    empresa_id: int,
    status: Optional[str] = None,
    tipo: Optional[str] = None,
    responsavel_id: Optional[int] = None,
    cliente_id: Optional[int] = None,
    data_de: Optional[datetime] = None,
    data_ate: Optional[datetime] = None,
    orcamento_id: Optional[int] = None,
    page: int = 1,
    per_page: int = 50,
) -> Tuple[List[dict], int]:
    """Lista agendamentos com filtros e paginação."""
    query = db.query(Agendamento).filter(Agendamento.empresa_id == empresa_id)

    if status:
        query = query.filter(Agendamento.status == status)
    if tipo:
        query = query.filter(Agendamento.tipo == tipo)
    if responsavel_id:
        query = query.filter(Agendamento.responsavel_id == responsavel_id)
    if cliente_id:
        query = query.filter(Agendamento.cliente_id == cliente_id)
    if orcamento_id:
        query = query.filter(Agendamento.orcamento_id == orcamento_id)
    if data_de or data_ate:
        # Agendamentos com data fixa no intervalo OU aguardando escolha do cliente
        # com ao menos uma opção proposta no intervalo (data_agendada fica NULL até a escolha).
        cond_normal = [Agendamento.data_agendada.isnot(None)]
        if data_de:
            cond_normal.append(Agendamento.data_agendada >= data_de)
        if data_ate:
            cond_normal.append(Agendamento.data_agendada <= data_ate)

        opcao_parts = [
            AgendamentoOpcao.agendamento_id == Agendamento.id,
            AgendamentoOpcao.disponivel.is_(True),
        ]
        if data_de:
            opcao_parts.append(AgendamentoOpcao.data_hora >= data_de)
        if data_ate:
            opcao_parts.append(AgendamentoOpcao.data_hora <= data_ate)
        opcao_no_intervalo = exists().where(and_(*opcao_parts))

        cond_escolha = and_(
            Agendamento.status == StatusAgendamento.AGUARDANDO_ESCOLHA,
            opcao_no_intervalo,
        )
        query = query.filter(or_(and_(*cond_normal), cond_escolha))

    total = query.count()
    agendamentos = (
        query.order_by(
            Agendamento.data_agendada.asc().nulls_last(),
            Agendamento.id.asc(),
        )
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return [
        _enriquecer_out(
            ag,
            db,
            calendario_data_de=data_de if (data_de or data_ate) else None,
            calendario_data_ate=data_ate if (data_de or data_ate) else None,
        )
        for ag in agendamentos
    ], total


def listar_hoje(db: Session, empresa_id: int) -> List[dict]:
    """Agendamentos de hoje."""
    from datetime import date

    hoje = date.today()
    inicio = datetime.combine(hoje, time.min).replace(tzinfo=timezone.utc)
    fim = datetime.combine(hoje, time.max).replace(tzinfo=timezone.utc)

    agendamentos = (
        db.query(Agendamento)
        .filter(
            Agendamento.empresa_id == empresa_id,
            Agendamento.data_agendada >= inicio,
            Agendamento.data_agendada <= fim,
            Agendamento.status.notin_(
                [
                    StatusAgendamento.CANCELADO,
                    StatusAgendamento.NAO_COMPARECEU,
                ]
            ),
        )
        .order_by(Agendamento.data_agendada.asc())
        .all()
    )
    return [_enriquecer_out(ag, db) for ag in agendamentos]


def dashboard(db: Session, empresa_id: int) -> dict:
    """Resumo para dashboard de agendamentos."""
    from datetime import date

    hoje = date.today()
    inicio_hoje = datetime.combine(hoje, time.min).replace(tzinfo=timezone.utc)
    fim_hoje = datetime.combine(hoje, time.max).replace(tzinfo=timezone.utc)
    fim_7d = datetime.combine(hoje + timedelta(days=7), time.max).replace(
        tzinfo=timezone.utc
    )
    inicio_semana = datetime.combine(
        hoje - timedelta(days=hoje.weekday()), time.min
    ).replace(tzinfo=timezone.utc)

    def _count(filtros):
        return (
            db.query(Agendamento)
            .filter(Agendamento.empresa_id == empresa_id, *filtros)
            .count()
        )

    return {
        "total_hoje": _count(
            [
                Agendamento.data_agendada >= inicio_hoje,
                Agendamento.data_agendada <= fim_hoje,
                Agendamento.status.notin_(
                    [StatusAgendamento.CANCELADO, StatusAgendamento.NAO_COMPARECEU]
                ),
            ]
        ),
        "pendentes_confirmacao": _count(
            [Agendamento.status == StatusAgendamento.PENDENTE]
        ),
        "confirmados_hoje": _count(
            [
                Agendamento.data_agendada >= inicio_hoje,
                Agendamento.data_agendada <= fim_hoje,
                Agendamento.status == StatusAgendamento.CONFIRMADO,
            ]
        ),
        "em_andamento": _count([Agendamento.status == StatusAgendamento.EM_ANDAMENTO]),
        "proximos_7_dias": _count(
            [
                Agendamento.data_agendada > fim_hoje,
                Agendamento.data_agendada <= fim_7d,
                Agendamento.status.notin_(
                    [StatusAgendamento.CANCELADO, StatusAgendamento.NAO_COMPARECEU]
                ),
            ]
        ),
        "cancelados_semana": _count(
            [
                Agendamento.data_agendada >= inicio_semana,
                Agendamento.status == StatusAgendamento.CANCELADO,
            ]
        ),
    }


def slots_disponiveis(
    db: Session,
    empresa_id: int,
    data: datetime,
    responsavel_id: Optional[int] = None,
) -> List[dict]:
    """Retorna slots livres para uma data específica."""
    config_empresa = _obter_config(db, empresa_id)
    config_usuario = (
        _obter_config_usuario(db, empresa_id, responsavel_id)
        if responsavel_id
        else None
    )
    config = _merge_config(config_empresa, config_usuario)

    # Validar se é dia de trabalho
    ok, _ = _verificar_dia_trabalho(config, data)
    if not ok:
        return []

    h_inicio = time(*map(int, config["horario_inicio"].split(":")))
    h_fim = time(*map(int, config["horario_fim"].split(":")))
    duracao = config["duracao_padrao_min"]
    intervalo = config["intervalo_minimo_min"]

    inicio_dia = datetime.combine(data.date(), h_inicio).replace(tzinfo=timezone.utc)
    fim_dia = datetime.combine(data.date(), h_fim).replace(tzinfo=timezone.utc)

    # Buscar agendamentos existentes do dia
    agendamentos = (
        db.query(Agendamento)
        .filter(
            Agendamento.empresa_id == empresa_id,
            Agendamento.data_agendada >= inicio_dia,
            Agendamento.data_agendada < fim_dia,
            Agendamento.status.notin_(
                [
                    StatusAgendamento.CANCELADO,
                    StatusAgendamento.NAO_COMPARECEU,
                    StatusAgendamento.CONCLUIDO,
                ]
            ),
        )
        .order_by(Agendamento.data_agendada.asc())
        .all()
    )
    if responsavel_id:
        agendamentos = [a for a in agendamentos if a.responsavel_id == responsavel_id]

    # Buscar bloqueios
    bloqueios = (
        db.query(SlotBloqueado)
        .filter(
            SlotBloqueado.empresa_id == empresa_id,
            SlotBloqueado.data_inicio < fim_dia,
            SlotBloqueado.data_fim > inicio_dia,
        )
        .all()
    )
    if responsavel_id:
        bloqueios = [
            b
            for b in bloqueios
            if b.usuario_id is None or b.usuario_id == responsavel_id
        ]
    else:
        bloqueios = [b for b in bloqueios if b.usuario_id is None]

    # Gerar slots
    slots = []
    cursor = inicio_dia
    while cursor + timedelta(minutes=duracao) <= fim_dia:
        slot_fim = cursor + timedelta(minutes=duracao)
        ocupado = False

        # Verificar agendamentos
        for ag in agendamentos:
            ag_fim = ag.data_fim or (
                ag.data_agendada + timedelta(minutes=ag.duracao_estimada_min or 60)
            )
            if ag.data_agendada < slot_fim and ag_fim > cursor:
                ocupado = True
                break

        # Verificar bloqueios
        if not ocupado:
            for bl in bloqueios:
                if bl.data_inicio < slot_fim and bl.data_fim > cursor:
                    ocupado = True
                    break

        if not ocupado:
            slots.append(
                {
                    "inicio": cursor,
                    "fim": slot_fim,
                    "duracao_min": duracao,
                }
            )

        cursor += timedelta(minutes=duracao + intervalo)

    return slots


# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════


def obter_config(db: Session, empresa_id: int) -> ConfigAgendamento:
    return _obter_config(db, empresa_id)


def salvar_config(db: Session, empresa_id: int, dados: dict) -> ConfigAgendamento:
    config = _obter_config(db, empresa_id)
    for key, val in dados.items():
        if val is not None and hasattr(config, key):
            setattr(config, key, val)
    db.commit()
    db.refresh(config)
    return config


def salvar_config_usuario(
    db: Session, empresa_id: int, usuario_id: int, dados: dict
) -> ConfigAgendamentoUsuario:
    config = _obter_config_usuario(db, empresa_id, usuario_id)
    if not config:
        config = ConfigAgendamentoUsuario(
            empresa_id=empresa_id,
            usuario_id=usuario_id,
        )
        db.add(config)
    for key, val in dados.items():
        if hasattr(config, key):
            setattr(config, key, val)
    db.commit()
    db.refresh(config)
    return config


def remover_config_usuario(db: Session, empresa_id: int, usuario_id: int) -> bool:
    config = _obter_config_usuario(db, empresa_id, usuario_id)
    if config:
        db.delete(config)
        db.commit()
        return True
    return False


def listar_config_usuarios(db: Session, empresa_id: int) -> List[dict]:
    configs = (
        db.query(ConfigAgendamentoUsuario)
        .filter(
            ConfigAgendamentoUsuario.empresa_id == empresa_id,
            ConfigAgendamentoUsuario.ativo == True,
        )
        .all()
    )
    result = []
    for c in configs:
        d = {
            "id": c.id,
            "empresa_id": c.empresa_id,
            "usuario_id": c.usuario_id,
            "horario_inicio": c.horario_inicio,
            "horario_fim": c.horario_fim,
            "dias_trabalho": c.dias_trabalho,
            "duracao_padrao_min": c.duracao_padrao_min,
            "ativo": c.ativo,
        }
        try:
            u = db.query(Usuario).filter(Usuario.id == c.usuario_id).first()
            d["usuario_nome"] = u.nome if u else None
        except Exception:
            d["usuario_nome"] = None
        result.append(d)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# SLOTS BLOQUEADOS
# ══════════════════════════════════════════════════════════════════════════════


def criar_slot_bloqueado(
    db: Session,
    empresa_id: int,
    data_inicio: datetime,
    data_fim: datetime,
    usuario_id: Optional[int] = None,
    motivo: Optional[str] = None,
    recorrente: bool = False,
    recorrencia_tipo: Optional[str] = None,
) -> SlotBloqueado:
    slot = SlotBloqueado(
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        motivo=motivo,
        recorrente=recorrente,
        recorrencia_tipo=recorrencia_tipo,
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot


def listar_slots_bloqueados(
    db: Session,
    empresa_id: int,
    usuario_id: Optional[int] = None,
    data_de: Optional[datetime] = None,
    data_ate: Optional[datetime] = None,
) -> List[dict]:
    query = db.query(SlotBloqueado).filter(SlotBloqueado.empresa_id == empresa_id)
    if usuario_id is not None:
        query = query.filter(
            or_(
                SlotBloqueado.usuario_id.is_(None),
                SlotBloqueado.usuario_id == usuario_id,
            )
        )
    if data_de:
        query = query.filter(SlotBloqueado.data_fim >= data_de)
    if data_ate:
        query = query.filter(SlotBloqueado.data_inicio <= data_ate)

    slots = query.order_by(SlotBloqueado.data_inicio.asc()).all()
    result = []
    for s in slots:
        d = {
            "id": s.id,
            "empresa_id": s.empresa_id,
            "usuario_id": s.usuario_id,
            "data_inicio": s.data_inicio,
            "data_fim": s.data_fim,
            "motivo": s.motivo,
            "recorrente": s.recorrente,
            "recorrencia_tipo": s.recorrencia_tipo,
            "criado_em": s.criado_em,
        }
        try:
            if s.usuario_id:
                u = db.query(Usuario).filter(Usuario.id == s.usuario_id).first()
                d["usuario_nome"] = u.nome if u else None
            else:
                d["usuario_nome"] = None
        except Exception:
            d["usuario_nome"] = None
        result.append(d)
    return result


def remover_slot_bloqueado(db: Session, empresa_id: int, slot_id: int) -> bool:
    slot = (
        db.query(SlotBloqueado)
        .filter(
            SlotBloqueado.id == slot_id,
            SlotBloqueado.empresa_id == empresa_id,
        )
        .first()
    )
    if slot:
        db.delete(slot)
        db.commit()
        return True
    return False


def listar_responsaveis(db: Session, empresa_id: int) -> List[dict]:
    """Lista usuários da empresa que podem ser responsáveis por agendamentos."""
    usuarios = (
        db.query(Usuario)
        .filter(
            Usuario.empresa_id == empresa_id,
            Usuario.ativo == True,
        )
        .order_by(Usuario.nome)
        .all()
    )
    return [{"id": u.id, "nome": u.nome} for u in usuarios]


def historico_agendamento(
    db: Session, empresa_id: int, agendamento_id: int
) -> List[dict]:
    """Retorna histórico de um agendamento."""
    ag = (
        db.query(Agendamento)
        .filter(
            Agendamento.id == agendamento_id,
            Agendamento.empresa_id == empresa_id,
        )
        .first()
    )
    if not ag:
        return []

    historico = (
        db.query(HistoricoAgendamento)
        .filter(HistoricoAgendamento.agendamento_id == agendamento_id)
        .order_by(HistoricoAgendamento.criado_em.desc())
        .all()
    )
    result = []
    for h in historico:
        d = {
            "id": h.id,
            "agendamento_id": h.agendamento_id,
            "status_anterior": h.status_anterior,
            "status_novo": h.status_novo,
            "descricao": h.descricao,
            "editado_por_id": h.editado_por_id,
            "criado_em": h.criado_em,
        }
        try:
            if h.editado_por_id:
                u = db.query(Usuario).filter(Usuario.id == h.editado_por_id).first()
                d["editado_por_nome"] = u.nome if u else None
            else:
                d["editado_por_nome"] = None
        except Exception:
            d["editado_por_nome"] = None
        result.append(d)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# OPÇÕES DE DATA/HORA
# ══════════════════════════════════════════════════════════════════════════════


def criar_agendamento_com_opcoes(
    db: Session,
    empresa_id: int,
    usuario_id: int,
    cliente_id: int,
    opcoes_datas: list,
    orcamento_id: Optional[int] = None,
    responsavel_id: Optional[int] = None,
    tipo: str = "servico",
    duracao_estimada_min: int = 60,
    endereco: Optional[str] = None,
    observacoes: Optional[str] = None,
) -> Tuple[Optional[Agendamento], str]:
    """
    Cria agendamento com opções de data/hora. Status inicial: AGUARDANDO_ESCOLHA.
    data_agendada fica NULL até o cliente escolher.
    """
    now = _now()

    # Validar orçamento
    if orcamento_id:
        existente = (
            db.query(Agendamento)
            .filter(
                Agendamento.empresa_id == empresa_id,
                Agendamento.orcamento_id == orcamento_id,
                Agendamento.status.notin_(
                    [
                        StatusAgendamento.CANCELADO,
                        StatusAgendamento.NAO_COMPARECEU,
                    ]
                ),
            )
            .first()
        )
        if existente:
            return (
                None,
                f"Já existe agendamento ativo ({existente.numero}) para este orçamento.",
            )

        orc = (
            db.query(Orcamento)
            .filter(
                Orcamento.id == orcamento_id,
                Orcamento.empresa_id == empresa_id,
            )
            .first()
        )
        if not orc:
            return None, "Orçamento não encontrado."
        if orc.status != StatusOrcamento.APROVADO:
            return (
                None,
                f"Orçamento deve estar aprovado. Status atual: {orc.status.value}.",
            )

    # Validar cliente
    cliente = (
        db.query(Cliente)
        .filter(
            Cliente.id == cliente_id,
            Cliente.empresa_id == empresa_id,
        )
        .first()
    )
    if not cliente:
        return None, "Cliente não encontrado."

    # Validar opções (não no passado, não duplicadas)
    datas_validadas = []
    responsavel_validacao = responsavel_id or usuario_id
    for op_data in opcoes_datas:
        dt = (
            op_data.get("data_hora") if isinstance(op_data, dict) else op_data.data_hora
        )
        dt = _normalize_to_utc(dt)
        if dt < now:
            return None, f"Data {dt.strftime('%d/%m/%Y %H:%M')} está no passado."
        if dt in datas_validadas:
            return None, "Datas duplicadas não são permitidas."
        ok, erro = _validar_opcao_data_hora(
            db=db,
            empresa_id=empresa_id,
            responsavel_id=responsavel_validacao,
            duracao_estimada_min=duracao_estimada_min,
            data_hora=dt,
        )
        if not ok:
            return None, erro
        datas_validadas.append(dt)

    # Criar agendamento (sem data_agendada definida)
    numero = _gerar_numero(db, empresa_id)
    ag = Agendamento(
        empresa_id=empresa_id,
        cliente_id=cliente_id,
        orcamento_id=orcamento_id,
        criado_por_id=usuario_id,
        responsavel_id=responsavel_id or usuario_id,
        numero=numero,
        status=StatusAgendamento.AGUARDANDO_ESCOLHA,
        tipo=tipo,
        origem=OrigemAgendamento.MANUAL,
        data_agendada=None,  # NULL até cliente escolher
        duracao_estimada_min=duracao_estimada_min,
        endereco=endereco or cliente.endereco,
        observacoes=observacoes,
    )
    db.add(ag)
    db.flush()

    # Criar opções
    for dt in datas_validadas:
        opcao = AgendamentoOpcao(
            agendamento_id=ag.id,
            data_hora=dt,
            disponivel=True,
        )
        db.add(opcao)

    # Vincular orçamento
    if orcamento_id:
        orc = db.query(Orcamento).filter(Orcamento.id == orcamento_id).first()
        if orc:
            orc.agendamento_id = ag.id  # type: ignore

    _registrar_historico(
        db,
        ag.id,
        None,
        "aguardando_escolha",
        f"Agendamento criado com {len(datas_validadas)} opções de data.",
        editado_por_id=usuario_id,
    )

    db.commit()
    db.refresh(ag)
    logger.info(
        f"Agendamento com opções criado: {ag.numero} ({len(datas_validadas)} opções)"
    )
    return ag, ""


def escolher_opcao(
    db: Session,
    agendamento_id: int,
    opcao_id: int,
    empresa_id: Optional[int] = None,
) -> Tuple[Optional[Agendamento], str]:
    """
    Cliente escolhe uma opção de data/hora.
    Marca a opção como escolhida, define data_agendada, atualiza status.
    """
    filtro = [Agendamento.id == agendamento_id]
    if empresa_id:
        filtro.append(Agendamento.empresa_id == empresa_id)

    ag = db.query(Agendamento).filter(*filtro).first()
    if not ag:
        return None, "Agendamento não encontrado."

    if ag.status != StatusAgendamento.AGUARDANDO_ESCOLHA:
        return (
            None,
            f"Agendamento não está aguardando escolha. Status: {ag.status.value}.",
        )

    # Buscar opção
    opcao = (
        db.query(AgendamentoOpcao)
        .filter(
            AgendamentoOpcao.id == opcao_id,
            AgendamentoOpcao.agendamento_id == agendamento_id,
            AgendamentoOpcao.disponivel == True,
        )
        .first()
    )
    if not opcao:
        return None, "Opção não encontrada ou não disponível."

    # Lock para evitar race condition
    ag = (
        db.query(Agendamento)
        .filter(Agendamento.id == agendamento_id)
        .with_for_update()
        .first()
    )

    # Marcar opção como escolhida
    ok, erro = _validar_opcao_data_hora(
        db=db,
        empresa_id=ag.empresa_id,
        responsavel_id=ag.responsavel_id,
        duracao_estimada_min=ag.duracao_estimada_min or 60,
        data_hora=opcao.data_hora,
        excluir_agendamento_id=ag.id,
    )
    if not ok:
        db.rollback()
        return None, erro

    opcao.escolhida = True
    ag.data_agendada = opcao.data_hora
    ag.data_fim = opcao.data_hora + timedelta(minutes=ag.duracao_estimada_min or 60)
    db.flush()

    db.flush()  # Forçar gravação para evitar duplicação em requests simultâneos

    # Marcar outras opções como indisponíveis e não escolhidas
    db.query(AgendamentoOpcao).filter(
        AgendamentoOpcao.agendamento_id == agendamento_id,
        AgendamentoOpcao.id != opcao_id,
    ).update({"disponivel": False, "escolhida": False}, synchronize_session=False)

    # Atualizar status
    config = _obter_config(db, ag.empresa_id)
    if config.requer_confirmacao:
        ag.status = StatusAgendamento.PENDENTE
        novo_status = "pendente"
        desc = f"Cliente escolheu {opcao.data_hora.strftime('%d/%m/%Y às %H:%M')}. Aguardando confirmação."
    else:
        ag.status = StatusAgendamento.CONFIRMADO
        ag.confirmado_em = _now()
        novo_status = "confirmado"
        desc = f"Cliente escolheu {opcao.data_hora.strftime('%d/%m/%Y às %H:%M')}. Confirmado automaticamente."

    _registrar_historico(db, ag.id, "aguardando_escolha", novo_status, desc)

    db.commit()
    db.refresh(ag)
    logger.info(f"Opção escolhida: agendamento {ag.numero} → {opcao.data_hora}")
    return ag, ""


def buscar_agendamento_publico_por_orcamento(
    db: Session, link_publico: str
) -> Optional[dict]:
    """
    Busca agendamento vinculado a um orçamento público (pelo link).
    Retorna dados do agendamento + opções disponíveis.
    """
    orc = db.query(Orcamento).filter(Orcamento.link_publico == link_publico).first()
    if not orc:
        return None

    ag = (
        db.query(Agendamento)
        .filter(
            Agendamento.orcamento_id == orc.id,
            Agendamento.status.notin_(
                [
                    StatusAgendamento.CANCELADO,
                    StatusAgendamento.NAO_COMPARECEU,
                    StatusAgendamento.CONCLUIDO,
                ]
            ),
        )
        .first()
    )
    if not ag and orc.numero:
        # Fallback para cenários de reenvio/versionamento do orçamento em que o link público muda.
        orc_relacionado = (
            db.query(Orcamento)
            .filter(
                Orcamento.empresa_id == orc.empresa_id,
                Orcamento.numero == orc.numero,
            )
            .order_by(Orcamento.id.desc())
            .first()
        )
        if orc_relacionado:
            ag = (
                db.query(Agendamento)
                .filter(
                    Agendamento.orcamento_id == orc_relacionado.id,
                    Agendamento.status.notin_(
                        [
                            StatusAgendamento.CANCELADO,
                            StatusAgendamento.NAO_COMPARECEU,
                            StatusAgendamento.CONCLUIDO,
                        ]
                    ),
                )
                .first()
            )
    if not ag:
        return None

    # Verificar se empresa permite agendamento pelo cliente
    config = _obter_config(db, ag.empresa_id)

    opcao_escolhida_id = (
        db.query(AgendamentoOpcao.id)
        .filter(
            AgendamentoOpcao.agendamento_id == ag.id,
            AgendamentoOpcao.escolhida.is_(True),
        )
        .scalar()
    )

    opcoes = (
        db.query(AgendamentoOpcao)
        .filter(
            AgendamentoOpcao.agendamento_id == ag.id,
            AgendamentoOpcao.disponivel == True,
        )
        .order_by(AgendamentoOpcao.data_hora.asc())
        .all()
    )

    return {
        "id": ag.id,
        "numero": ag.numero,
        "status": ag.status.value,
        "tipo": ag.tipo.value if ag.tipo else None,
        "data_agendada": ag.data_agendada,
        "data_fim": ag.data_fim,
        "duracao_estimada_min": ag.duracao_estimada_min,
        "endereco": ag.endereco,
        "observacoes": ag.observacoes,
        "opcao_escolhida_id": opcao_escolhida_id,
        "opcoes": [
            {
                "id": o.id,
                "agendamento_id": o.agendamento_id,
                "data_hora": o.data_hora,
                "disponivel": o.disponivel,
                "escolhida": o.escolhida,
            }
            for o in opcoes
        ],
        "permite_agendamento_cliente": config.permite_agendamento_cliente,
        "requer_confirmacao": config.requer_confirmacao,
    }


def adicionar_opcoes(
    db: Session,
    empresa_id: int,
    agendamento_id: int,
    novas_datas: list,
) -> Tuple[Optional[list], str]:
    """Adiciona novas opções de data a um agendamento existente."""
    from app.models.models import AgendamentoOpcao

    ag = (
        db.query(Agendamento)
        .filter(
            Agendamento.id == agendamento_id,
            Agendamento.empresa_id == empresa_id,
        )
        .first()
    )
    if not ag:
        return None, "Agendamento não encontrado."

    if ag.status not in (
        StatusAgendamento.AGUARDANDO_ESCOLHA,
        StatusAgendamento.PENDENTE,
    ):
        return None, f"Não é possível adicionar opções com status '{ag.status.value}'."

    now = _now()
    opcoes_criadas = []
    for dt in novas_datas:
        dt = _normalize_to_utc(dt)
        if dt < now:
            continue
        # Verificar duplicata
        existe = (
            db.query(AgendamentoOpcao)
            .filter(
                AgendamentoOpcao.agendamento_id == ag.id,
                AgendamentoOpcao.data_hora == dt,
            )
            .first()
        )
        if existe:
            continue
        opcao = AgendamentoOpcao(agendamento_id=ag.id, data_hora=dt, disponivel=True)
        db.add(opcao)
        opcoes_criadas.append(opcao)

    if ag.status == StatusAgendamento.PENDENTE:
        ag.status = StatusAgendamento.AGUARDANDO_ESCOLHA
        _registrar_historico(
            db,
            ag.id,
            "pendente",
            "aguardando_escolha",
            f"Novas opções adicionadas. Cliente deve escolher novamente.",
        )

    db.commit()
    return opcoes_criadas, ""


def remover_opcao(
    db: Session,
    empresa_id: int,
    agendamento_id: int,
    opcao_id: int,
) -> bool:
    """Remove uma opção de data (marca como indisponível)."""
    from app.models.models import AgendamentoOpcao

    ag = (
        db.query(Agendamento)
        .filter(
            Agendamento.id == agendamento_id,
            Agendamento.empresa_id == empresa_id,
        )
        .first()
    )
    if not ag:
        return False

    opcao = (
        db.query(AgendamentoOpcao)
        .filter(
            AgendamentoOpcao.id == opcao_id,
            AgendamentoOpcao.agendamento_id == ag.id,
        )
        .first()
    )
    if opcao:
        opcao.disponivel = False
        db.commit()
        return True
    return False


def _ja_notificado_agendamento(
    db: Session,
    agendamento_id: int,
    marcador: str,
) -> bool:
    return (
        db.query(HistoricoAgendamento)
        .filter(
            HistoricoAgendamento.agendamento_id == agendamento_id,
            HistoricoAgendamento.descricao.like(f"%[{marcador}]%"),
        )
        .first()
        is not None
    )


def processar_followups_pendentes(db: Session) -> dict:
    """
    Job de follow-up para agendamentos em AGUARDANDO_ESCOLHA.
    - Cria notificação após 2 dias sem escolha.
    - Em modo opcional, cria um segundo lembrete após 4 dias.
    """
    agora = _now()
    limite_followup = agora - timedelta(days=2)
    limite_segundo_lembrete = agora - timedelta(days=4)
    total_followup = 0
    total_opcional = 0

    ags = (
        db.query(Agendamento)
        .filter(
            Agendamento.status == StatusAgendamento.AGUARDANDO_ESCOLHA,
            Agendamento.criado_em <= limite_followup,
        )
        .all()
    )

    for ag in ags:
        config = _obter_config(db, ag.empresa_id)
        if not _ja_notificado_agendamento(db, ag.id, "followup_escolha"):
            db.add(
                Notificacao(
                    empresa_id=ag.empresa_id,
                    orcamento_id=ag.orcamento_id,
                    tipo="agendamento_followup",
                    titulo=f"Agendamento {ag.numero} sem escolha de data",
                    mensagem="Cliente ainda não escolheu uma opção de agendamento.",
                )
            )
            _registrar_historico(
                db,
                ag.id,
                ag.status.value,
                ag.status.value,
                "[followup_escolha] Follow-up automático para operador.",
            )
            total_followup += 1

        modo_orc = ag.orcamento.agendamento_modo if ag.orcamento else None
        modo_orc_valor = (
            modo_orc.value if hasattr(modo_orc, "value") else str(modo_orc or "")
        ).lower()
        if (
            ag.orcamento
            and modo_orc_valor == "opcional"
            and ag.criado_em <= limite_segundo_lembrete
            and not _ja_notificado_agendamento(db, ag.id, "lembrete_opcional_2")
        ):
            msg = config.mensagem_lembrete or (
                "Lembrete: este orçamento foi aceito, mas ainda falta definir a data do agendamento."
            )
            db.add(
                Notificacao(
                    empresa_id=ag.empresa_id,
                    orcamento_id=ag.orcamento_id,
                    tipo="agendamento_lembrete",
                    titulo=f"Lembrete de agendamento opcional ({ag.numero})",
                    mensagem=msg,
                )
            )
            _registrar_historico(
                db,
                ag.id,
                ag.status.value,
                ag.status.value,
                "[lembrete_opcional_2] Segundo lembrete automático (modo opcional).",
            )
            total_opcional += 1

    if total_followup or total_opcional:
        db.commit()

    return {
        "followups_criados": total_followup,
        "lembretes_opcional_criados": total_opcional,
    }
