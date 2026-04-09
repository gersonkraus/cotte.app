"""
Serviço de criação automática de agendamento ao aprovar orçamento.
"""

import logging
from datetime import datetime, timedelta, time, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.models import (
    Orcamento,
    ModoAgendamentoOrcamento,
    ConfigAgendamento,
    Agendamento,
    StatusAgendamento,
    StatusOrcamento,
    Usuario,
    Empresa,
    Notificacao,
    Cliente,
)
from app.services.agendamento_service import (
    criar_agendamento_com_opcoes,
    _obter_config_usuario,
    _merge_config,
    _verificar_conflito,
    _verificar_slot_bloqueado,
)

logger = logging.getLogger(__name__)


def _gerar_opcoes_automaticas(
    db: Session,
    empresa_id: int,
    responsavel_id: Optional[int],
    duracao_estimada_min: int,
) -> list[dict]:
    """
    Gera 3 opções de data/hora baseadas na configuração da agenda.
    Usa horário de início configurado e próximos dias úteis disponíveis.
    """
    config = (
        db.query(ConfigAgendamento)
        .filter(ConfigAgendamento.empresa_id == empresa_id)
        .first()
    )

    horario_inicio = time(9, 0)
    dias_trabalho = [0, 1, 2, 3, 4]

    if config:
        if config.horario_inicio:
            try:
                partes = str(config.horario_inicio).split(":")
                horario_inicio = time(int(partes[0]), int(partes[1]))
            except (ValueError, IndexError):
                pass
        if config.dias_trabalho:
            dias_trabalho = config.dias_trabalho

    config_usuario = (
        _obter_config_usuario(db, empresa_id, responsavel_id) if responsavel_id else None
    )
    config_validacao = _merge_config(config, config_usuario) if config else {}
    opcoes = []
    hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    cursor = hoje + timedelta(days=1)

    while len(opcoes) < 3:
        if cursor.weekday() in dias_trabalho:
            data_opcao = datetime.combine(cursor.date(), horario_inicio)
            data_fim = data_opcao + timedelta(minutes=duracao_estimada_min)
            ok_conflito, _ = _verificar_conflito(
                db,
                empresa_id,
                data_opcao,
                data_fim,
                responsavel_id,
            )
            if not ok_conflito:
                cursor += timedelta(days=1)
                continue

            ok_bloqueio, _ = _verificar_slot_bloqueado(
                db,
                empresa_id,
                data_opcao,
                data_fim,
                responsavel_id,
            )
            if not ok_bloqueio:
                cursor += timedelta(days=1)
                continue

            if config_validacao:
                antecedencia_horas = config_validacao.get("antecedencia_minima_horas", 1)
                limite = datetime.now() + timedelta(hours=antecedencia_horas)
                if data_opcao < limite:
                    cursor += timedelta(days=1)
                    continue

            opcoes.append({"data_hora": data_opcao})
        cursor += timedelta(days=1)
        if cursor > hoje + timedelta(days=30):
            break

    return opcoes


def criar_agendamento_automatico(
    db: Session,
    orcamento: Orcamento,
    usuario_id: Optional[int] = None,
) -> Optional[dict]:
    """
    Cria automaticamente um agendamento com opções de data quando um
    orçamento com agendamento_modo OPCIONAL ou OBRIGATORIO é aprovado.

    Retorna dict com resultado ou None se não aplicável.
    É idempotente: não cria duplicata se já existe agendamento ativo.
    """
    empresa = (
        db.query(Empresa).filter(Empresa.id == orcamento.empresa_id).first()
    )
    if empresa is not None and not getattr(
        empresa, "utilizar_agendamento_automatico", True
    ):
        logger.info(
            "Agendamento automático desativado na empresa (orcamento_id=%s).",
            orcamento.id,
        )
        return None

    modo = orcamento.agendamento_modo
    if modo not in (
        ModoAgendamentoOrcamento.OPCIONAL,
        ModoAgendamentoOrcamento.OBRIGATORIO,
    ):
        return None

    existente = (
        db.query(Agendamento)
        .filter(
            Agendamento.empresa_id == orcamento.empresa_id,
            Agendamento.orcamento_id == orcamento.id,
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
        logger.info(
            "Agendamento %s já existe para orçamento %s. Pulando criação automática.",
            existente.numero,
            orcamento.numero,
        )
        return {"agendamento_id": existente.id, "mensagem": "Agendamento já existente."}

    config = (
        db.query(ConfigAgendamento)
        .filter(ConfigAgendamento.empresa_id == orcamento.empresa_id)
        .first()
    )
    duracao_padrao = config.duracao_padrao_min if config and config.duracao_padrao_min else 60

    responsavel_id = orcamento.criado_por_id
    if responsavel_id is None:
        fallback_usuario = (
            db.query(Usuario)
            .filter(
                Usuario.empresa_id == orcamento.empresa_id,
                Usuario.ativo == True,
            )
            .order_by(Usuario.is_gestor.desc(), Usuario.id.asc())
            .first()
        )
        responsavel_id = fallback_usuario.id if fallback_usuario else None

    if responsavel_id is None:
        logger.error(
            "Falha ao criar agendamento automático: sem responsável válido (orcamento_id=%s).",
            orcamento.id,
        )
        return {"erro": "Não foi possível definir responsável para o agendamento automático."}

    opcoes = _gerar_opcoes_automaticas(
        db,
        orcamento.empresa_id,
        responsavel_id=responsavel_id,
        duracao_estimada_min=duracao_padrao,
    )
    if not opcoes:
        logger.warning(
            "Não foi possível gerar opções de data para orçamento %s.",
            orcamento.numero,
        )
        return None

    ag, erro = criar_agendamento_com_opcoes(
        db=db,
        empresa_id=orcamento.empresa_id,
        usuario_id=usuario_id or responsavel_id,
        cliente_id=orcamento.cliente_id,
        opcoes_datas=opcoes,
        orcamento_id=orcamento.id,
        responsavel_id=responsavel_id,
        tipo="servico",
        duracao_estimada_min=duracao_padrao,
        endereco=orcamento.cliente.endereco if orcamento.cliente else None,
        observacoes=f"Agendamento criado automaticamente na aprovação do orçamento {orcamento.numero}.",
    )

    if erro:
        logger.error(
            "Erro ao criar agendamento automático para orçamento %s: %s",
            orcamento.numero,
            erro,
        )
        return {"erro": erro}

    logger.info(
        "Agendamento automático criado: %s para orçamento %s (%d opções, modo=%s)",
        ag.numero,
        orcamento.numero,
        len(opcoes),
        modo.value,
    )

    return {
        "agendamento_id": ag.id,
        "numero": ag.numero,
        "modo": modo.value,
        "opcoes_count": len(opcoes),
    }


def processar_agendamento_apos_aprovacao(
    db: Session,
    orcamento: Orcamento,
    *,
    canal: str,
    usuario_id: Optional[int] = None,
) -> Optional[dict]:
    """
    Registra canal/data de aprovação e cria agendamento automático ou enfileira
    conforme `agendamento_opcoes_somente_apos_liberacao` da empresa.
    """
    orcamento.aprovado_canal = (canal or "manual")[:20]
    orcamento.aprovado_em = datetime.now(timezone.utc)

    empresa = (
        db.query(Empresa).filter(Empresa.id == orcamento.empresa_id).first()
    )
    modo = orcamento.agendamento_modo
    if modo not in (
        ModoAgendamentoOrcamento.OPCIONAL,
        ModoAgendamentoOrcamento.OBRIGATORIO,
    ):
        return None

    if empresa is not None and not getattr(
        empresa, "utilizar_agendamento_automatico", True
    ):
        logger.info(
            "Agendamento automático desativado (orcamento_id=%s); metadados salvos.",
            orcamento.id,
        )
        return None

    if empresa is not None and getattr(
        empresa, "agendamento_opcoes_somente_apos_liberacao", False
    ):
        if not getattr(orcamento, "agendamento_opcoes_pendente_liberacao", False):
            orcamento.agendamento_opcoes_pendente_liberacao = True
            db.add(
                Notificacao(
                    empresa_id=orcamento.empresa_id,
                    orcamento_id=orcamento.id,
                    tipo="fila_agendamento",
                    titulo=f"Pré-agendamento: {orcamento.numero or orcamento.id}",
                    mensagem=(
                        "Orçamento aprovado aguardando liberação das opções de data. "
                        "Acesse Agendamentos → Pré-agendamento."
                    ),
                )
            )
        return {"situacao": "fila_pre_agendamento", "orcamento_id": orcamento.id}

    return criar_agendamento_automatico(db, orcamento, usuario_id=usuario_id)


def listar_pre_agendamento_fila(
    db: Session,
    empresa_id: int,
    *,
    canal: Optional[str] = None,
    busca: Optional[str] = None,
    ordem: str = "aprovado_em_desc",
) -> List[Orcamento]:
    """Orçamentos aprovados com opções de agendamento pendentes de liberação."""
    q = (
        db.query(Orcamento)
        .options(joinedload(Orcamento.cliente))
        .filter(
            Orcamento.empresa_id == empresa_id,
            Orcamento.status == StatusOrcamento.APROVADO,
            Orcamento.agendamento_opcoes_pendente_liberacao.is_(True),
        )
    )
    if canal:
        c = canal.strip().lower()[:20]
        q = q.filter(Orcamento.aprovado_canal == c)
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.join(Cliente, Orcamento.cliente_id == Cliente.id).filter(
            or_(Cliente.nome.ilike(term), Orcamento.numero.ilike(term))
        )
    if ordem == "aprovado_em_asc":
        q = q.order_by(Orcamento.aprovado_em.asc().nullslast(), Orcamento.id.asc())
    else:
        q = q.order_by(Orcamento.aprovado_em.desc().nullslast(), Orcamento.id.desc())
    return q.all()


def liberar_pre_agendamento_lote(
    db: Session,
    empresa_id: int,
    orcamento_ids: List[int],
    usuario_id: int,
    observacao: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Libera a fila e dispara criação do agendamento com opções para cada orçamento.
    Respeita `agendamento_exige_pagamento_100` da empresa.
    """
    from app.services.agendamento_service import (
        _verificar_pagamento_100,
        percentual_pago_orcamento,
    )

    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    obs = (observacao or "").strip() or None
    resultados: List[Dict[str, Any]] = []

    for oid in orcamento_ids:
        orc = (
            db.query(Orcamento)
            .filter(Orcamento.id == oid, Orcamento.empresa_id == empresa_id)
            .first()
        )
        if not orc:
            resultados.append(
                {
                    "orcamento_id": oid,
                    "ok": False,
                    "detalhe": "Orçamento não encontrado.",
                    "agendamento_id": None,
                }
            )
            continue
        if orc.status != StatusOrcamento.APROVADO:
            resultados.append(
                {
                    "orcamento_id": oid,
                    "ok": False,
                    "detalhe": "Orçamento não está aprovado.",
                    "agendamento_id": None,
                }
            )
            continue
        if not getattr(orc, "agendamento_opcoes_pendente_liberacao", False):
            resultados.append(
                {
                    "orcamento_id": oid,
                    "ok": False,
                    "detalhe": "Este orçamento não está na fila de pré-agendamento.",
                    "agendamento_id": None,
                }
            )
            continue
        if empresa and empresa.agendamento_exige_pagamento_100:
            if not _verificar_pagamento_100(orc, db):
                pct = percentual_pago_orcamento(orc, db)
                resultados.append(
                    {
                        "orcamento_id": oid,
                        "ok": False,
                        "detalhe": (
                            f"Pagamento 100% necessário para liberar (pago ~{pct:.0f}%)."
                        ),
                        "agendamento_id": None,
                    }
                )
                continue

        res = criar_agendamento_automatico(db, orc, usuario_id=usuario_id)
        aid = None
        err = None
        if isinstance(res, dict):
            aid = res.get("agendamento_id")
            err = res.get("erro")
        if not aid:
            msg = err or "Não foi possível gerar o agendamento automático."
            resultados.append(
                {
                    "orcamento_id": oid,
                    "ok": False,
                    "detalhe": msg,
                    "agendamento_id": None,
                }
            )
            continue

        orc_upd = (
            db.query(Orcamento)
            .filter(Orcamento.id == oid, Orcamento.empresa_id == empresa_id)
            .first()
        )
        if not orc_upd:
            resultados.append(
                {
                    "orcamento_id": oid,
                    "ok": False,
                    "detalhe": (
                        "Agendamento criado, mas falhou ao atualizar a fila. "
                        "Recarregue a página e verifique se o item sumiu da fila."
                    ),
                    "agendamento_id": aid,
                }
            )
            continue
        orc_upd.agendamento_opcoes_pendente_liberacao = False
        orc_upd.agendamento_opcoes_liberado_em = datetime.now(timezone.utc)
        orc_upd.agendamento_opcoes_liberado_por_id = usuario_id
        orc_upd.observacao_liberacao_agendamento = obs
        db.commit()
        resultados.append(
            {
                "orcamento_id": oid,
                "ok": True,
                "detalhe": None,
                "agendamento_id": aid,
            }
        )

    return resultados
