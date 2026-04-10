"""Pré-visualização read-only (extras) para cards de confirmação de ações destrutivas.

Usado pelo tool_executor ao emitir confirmation_token — enriquece contexto (cliente,
número do orçamento, totais) sem executar a ação.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.models.models import (
    Agendamento,
    Cliente,
    ContaFinanceira,
    Orcamento,
    StatusConta,
    Usuario,
)
from app.utils.orcamento_utils import brl_fmt

from .orcamento_tools import _get_orcamento_da_empresa

# Tools que referenciam um orçamento por orcamento_id (string ou int)
_ORC_TOOLS_COM_ID = frozenset(
    {
        "editar_orcamento",
        "editar_item_orcamento",
        "aprovar_orcamento",
        "recusar_orcamento",
        "enviar_orcamento_whatsapp",
        "enviar_orcamento_email",
        "duplicar_orcamento",
        "anexar_documento_orcamento",
    }
)


def _safe_float(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _mudancas_editar_orcamento(args: dict[str, Any]) -> list[str]:
    linhas: list[str] = []
    vt = _safe_float(args.get("valor_total"))
    if vt is not None:
        linhas.append(f"Novo total: {brl_fmt(vt)}")
    if args.get("observacoes") is not None:
        obs = str(args["observacoes"]).strip()
        if len(obs) > 120:
            obs = obs[:117] + "..."
        linhas.append(f"Observações: {obs}")
    if args.get("desconto") is not None:
        dt = args.get("desconto_tipo") or "?"
        dv = args.get("desconto")
        linhas.append(f"Desconto: {dv} ({dt})")
    if args.get("validade_dias") is not None:
        linhas.append(f"Validade: {args['validade_dias']} dias")
    return linhas


def _mudancas_editar_item(args: dict[str, Any], orc) -> list[str]:
    linhas: list[str] = []
    num = int(args.get("num_item") or 0)
    itens = list(orc.itens or [])
    item = itens[num - 1] if 0 < num <= len(itens) else None
    if item:
        q = float(item.quantidade or 1)
        vu = float(item.valor_unit or 0)
        linhas.append(
            f"Item {num} (atual): {item.descricao} — {q} × {brl_fmt(vu)}"
        )
    if args.get("descricao") is not None:
        linhas.append(f"→ Nova descrição: {args['descricao']}")
    vu_n = _safe_float(args.get("valor_unit"))
    if vu_n is not None:
        linhas.append(f"→ Novo valor unit.: {brl_fmt(vu_n)}")
    q_n = _safe_float(args.get("quantidade"))
    if q_n is not None:
        linhas.append(f"→ Nova quantidade: {q_n}")
    return linhas


async def build_destructive_extras(
    tool_name: str,
    args_dict: dict[str, Any],
    *,
    db: Session,
    current_user: Usuario,
) -> dict[str, Any]:
    """Retorna campos extras para merge em pending_action (além dos args crus)."""
    if tool_name == "criar_orcamento":
        from app.services.ai_tools.orcamento_tools import preview_criar_orcamento

        return await preview_criar_orcamento(
            args_dict, db=db, current_user=current_user
        )

    extras: dict[str, Any] = {}
    raw_oid = args_dict.get("orcamento_id")
    orc = None
    if tool_name in _ORC_TOOLS_COM_ID and raw_oid is not None:
        orc = _get_orcamento_da_empresa(db, raw_oid, current_user.empresa_id)
        if orc:
            extras["orcamento_numero"] = orc.numero
            extras["cliente_nome"] = orc.cliente.nome if orc.cliente else "—"
            extras["total_atual"] = float(orc.total or 0)
            extras["status_orcamento"] = orc.status.value if orc.status else ""

    if tool_name == "editar_orcamento":
        extras["mudancas"] = _mudancas_editar_orcamento(args_dict)

    elif tool_name == "editar_item_orcamento" and orc:
        extras["mudancas"] = _mudancas_editar_item(args_dict, orc)

    elif tool_name == "recusar_orcamento":
        motivo = args_dict.get("motivo")
        if motivo:
            m = str(motivo).strip()
            if len(m) > 160:
                m = m[:157] + "..."
            extras["mudancas"] = [f"Motivo da recusa: {m}"]
        else:
            extras["mudancas"] = []

        if orc:
            contas_pendentes = (
                db.query(ContaFinanceira)
                .filter(
                    ContaFinanceira.orcamento_id == orc.id,
                    ContaFinanceira.status == StatusConta.PENDENTE,
                    ContaFinanceira.valor_pago == 0,
                )
                .all()
            )
            qtd_pendentes = len(contas_pendentes)
            total_pendente = sum(float(c.valor or 0) for c in contas_pendentes)
            extras["impacto_financeiro"] = {
                "contas_pendentes_removidas": qtd_pendentes,
                "valor_total_pendente_removido": round(total_pendente, 2),
            }
            extras["mudancas"].append(
                "Impacto financeiro: ao sair de APROVADO, contas a receber pendentes e sem pagamento são removidas automaticamente."
            )
            if qtd_pendentes > 0:
                extras["mudancas"].append(
                    f"Previsão para este orçamento: {qtd_pendentes} conta(s) pendente(s), total {brl_fmt(total_pendente)}."
                )
            else:
                extras["mudancas"].append(
                    "Previsão para este orçamento: não há contas pendentes sem pagamento para remover."
                )

    elif tool_name == "anexar_documento_orcamento":
        extras["mudancas"] = []
        mud = extras["mudancas"]
        doc_id = args_dict.get("documento_id")
        if doc_id is not None:
            mud.append(f"Documento (biblioteca) ID: {doc_id}")
        if args_dict.get("enviar_por_whatsapp"):
            mud.append("Enviar cópia por WhatsApp")
        if args_dict.get("enviar_por_email"):
            mud.append("Enviar cópia por e-mail")
        if args_dict.get("obrigatorio"):
            mud.append("Marcar como obrigatório no portal")

    # Cliente: excluir / editar
    if tool_name in ("excluir_cliente", "editar_cliente"):
        cid = args_dict.get("cliente_id")
        if cid:
            c = (
                db.query(Cliente)
                .filter(
                    Cliente.id == int(cid),
                    Cliente.empresa_id == current_user.empresa_id,
                )
                .first()
            )
            if c:
                extras["cliente_nome_registro"] = c.nome

    # Conta financeira (recebível / despesa)
    if tool_name == "registrar_pagamento_recebivel":
        cid = args_dict.get("conta_id")
        if cid:
            cf = (
                db.query(ContaFinanceira)
                .filter(
                    ContaFinanceira.id == int(cid),
                    ContaFinanceira.empresa_id == current_user.empresa_id,
                )
                .first()
            )
            if cf:
                extras["conta_descricao"] = cf.descricao
                extras["conta_valor"] = float(cf.valor or 0)
                saldo = float(cf.valor or 0) - float(cf.valor_pago or 0)
                extras["conta_saldo_aberto"] = saldo
                if cf.orcamento_id:
                    o = (
                        db.query(Orcamento)
                        .options(joinedload(Orcamento.cliente))
                        .filter(Orcamento.id == cf.orcamento_id)
                        .first()
                    )
                    if o:
                        extras["orcamento_numero"] = o.numero
                        if o.cliente:
                            extras["cliente_nome"] = o.cliente.nome

    if tool_name == "marcar_despesa_paga":
        cid = args_dict.get("conta_id")
        if cid:
            cf = (
                db.query(ContaFinanceira)
                .filter(
                    ContaFinanceira.id == int(cid),
                    ContaFinanceira.empresa_id == current_user.empresa_id,
                )
                .first()
            )
            if cf:
                extras["conta_descricao"] = cf.descricao
                extras["despesa_favorecido"] = cf.favorecido or "—"
                extras["conta_valor"] = float(cf.valor or 0)
                saldo = float(cf.valor or 0) - float(cf.valor_pago or 0)
                extras["conta_saldo_aberto"] = saldo

    if tool_name == "criar_parcelamento" and args_dict.get("cliente_id"):
        c = (
            db.query(Cliente)
            .filter(
                Cliente.id == int(args_dict["cliente_id"]),
                Cliente.empresa_id == current_user.empresa_id,
            )
            .first()
        )
        if c:
            extras["cliente_nome"] = c.nome

    if tool_name in ("cancelar_agendamento", "remarcar_agendamento"):
        aid = args_dict.get("agendamento_id")
        if aid:
            ag = (
                db.query(Agendamento)
                .options(joinedload(Agendamento.cliente))
                .filter(
                    Agendamento.id == int(aid),
                    Agendamento.empresa_id == current_user.empresa_id,
                )
                .first()
            )
            if ag:
                extras["agendamento_numero"] = getattr(ag, "numero", None) or str(
                    ag.id
                )
                if ag.data_agendada:
                    extras["agendamento_data_atual"] = ag.data_agendada.strftime(
                        "%d/%m/%Y %H:%M"
                    )
                if ag.cliente:
                    extras["cliente_nome"] = ag.cliente.nome

    if tool_name == "remarcar_agendamento" and args_dict.get("nova_data"):
        nd = args_dict["nova_data"]
        extras["mudancas"] = [f"Nova data: {nd}"]
        if args_dict.get("motivo"):
            extras["mudancas"].append(f"Motivo: {args_dict['motivo']}")

    if tool_name == "cancelar_agendamento" and args_dict.get("motivo"):
        extras["mudancas"] = [f"Motivo: {args_dict['motivo']}"]

    if tool_name == "criar_agendamento" and args_dict.get("cliente_id"):
        c = (
            db.query(Cliente)
            .filter(
                Cliente.id == int(args_dict["cliente_id"]),
                Cliente.empresa_id == current_user.empresa_id,
            )
            .first()
        )
        if c:
            extras["cliente_nome"] = c.nome

    return extras
