"""Ferramenta de relatórios analíticos multi-domínio para o Assistente IA."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import (
    Agendamento,
    Cliente,
    ContaFinanceira,
    ItemOrcamento,
    MovimentacaoCaixa,
    Orcamento,
    StatusAgendamento,
    StatusConta,
    StatusOrcamento,
    TipoConta,
    Usuario,
)

from ._base import ToolSpec

# ── Paleta de cores COTTE para gráficos ───────────────────────────────────────
_CORES = [
    "#0f766e", "#0284c7", "#7c3aed", "#b45309",
    "#dc2626", "#16a34a", "#d97706", "#6d28d9",
]
_COR_OK = "#16a34a"
_COR_RUIM = "#dc2626"
_COR_AVISO = "#d97706"

# Status que indicam faturamento realizado
_STATUS_FATURADOS = [
    StatusOrcamento.APROVADO,
    StatusOrcamento.EM_EXECUCAO,
    StatusOrcamento.AGUARDANDO_PAGAMENTO,
    StatusOrcamento.CONCLUIDO,
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _f(v: Any) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _brl(v: Any) -> str:
    return f"R$ {_f(v):_.2f}".replace("_", ".").replace(".", ",", 1).replace(",", ".", 1)


def _periodo_label(dias: int) -> str:
    mapa = {7: "7 dias", 30: "30 dias", 60: "60 dias", 90: "90 dias", 180: "6 meses", 365: "1 ano"}
    return f"Últimos {mapa.get(dias, f'{dias} dias')}"


def _inicio(dias: int) -> datetime:
    return datetime.now(tz=timezone.utc) - timedelta(days=dias)


def _chart(tipo: str, labels: list, datasets: list) -> dict:
    return {"tipo": tipo, "dados": {"labels": labels, "datasets": datasets}}


# ── Domínio: orcamentos ───────────────────────────────────────────────────────

def _orcamentos(inp: "GerarRelatorioDinamicoInput", *, db: Session, empresa_id: int) -> dict:
    inicio = _inicio(inp.periodo_dias)

    q = db.query(Orcamento).filter(
        Orcamento.empresa_id == empresa_id,
        Orcamento.criado_em >= inicio,
    )
    if inp.filtro_usuario_id:
        q = q.filter(Orcamento.criado_por_id == inp.filtro_usuario_id)
    if inp.filtro_status:
        try:
            q = q.filter(Orcamento.status == StatusOrcamento(inp.filtro_status))
        except ValueError:
            pass

    # Contagem por status
    counts: dict[str, int] = {}
    for s in StatusOrcamento:
        n = q.filter(Orcamento.status == s).count()
        if n:
            counts[s.value] = n

    total = sum(counts.values())
    aprovados = sum(counts.get(s.value, 0) for s in _STATUS_FATURADOS)
    enviados = total - counts.get("rascunho", 0)
    reprovados = counts.get("recusado", 0) + counts.get("expirado", 0)
    taxa = round(aprovados / enviados * 100, 1) if enviados else 0.0

    # Faturamento
    fat_q = q.filter(Orcamento.status.in_(_STATUS_FATURADOS))
    res_fat = db.query(
        func.sum(Orcamento.total), func.count(Orcamento.id)
    ).filter(
        Orcamento.empresa_id == empresa_id,
        Orcamento.criado_em >= inicio,
        Orcamento.status.in_(_STATUS_FATURADOS),
        *(
            [Orcamento.criado_por_id == inp.filtro_usuario_id]
            if inp.filtro_usuario_id else []
        ),
    ).first()
    fat_sum = res_fat[0] if res_fat and res_fat[0] is not None else 0
    fat_cnt = res_fat[1] if res_fat and res_fat[1] is not None else 0

    total_fat = _f(fat_sum)
    qtde_ap = int(fat_cnt or 0)
    ticket = round(total_fat / qtde_ap, 2) if qtde_ap else 0.0

    agrup = inp.agrupamento
    if not agrup:
        if inp.metrica in ("faturamento", "total_vendido", "ticket_medio", "quantidade"):
            agrup = "cliente"
        else:
            agrup = "status"

    rows: list[dict] = []
    chart_spec = None
    titulo = "Relatório de Orçamentos"

    if agrup == "status":
        titulo = "Distribuição de Orçamentos por Status"
        label_map = {
            "rascunho": "Rascunho", "enviado": "Enviado", "aprovado": "Aprovado",
            "em_execucao": "Em execução", "aguardando_pagamento": "Aguard. pagamento",
            "recusado": "Recusado", "expirado": "Expirado", "concluido": "Concluído",
        }
        rows = [
            {
                "Status": label_map.get(s, s),
                "Qtd.": c,
                "% do total": f"{round(c / total * 100, 1)}%" if total else "0%",
            }
            for s, c in sorted(counts.items(), key=lambda x: -int(x[1] or 0))
        ]
        cores = [
            _COR_OK if any(k in r["Status"].lower() for k in ["prov", "exec", "conc", "aguard"])
            else _COR_RUIM if any(k in r["Status"].lower() for k in ["recus", "expir"])
            else _COR_AVISO
            for r in rows
        ]
        chart_spec = _chart(
            inp.tipo_grafico or "doughnut",
            [r["Status"] for r in rows],
            [{"label": "Orçamentos", "data": [r["Qtd."] for r in rows], "backgroundColor": cores}],
        )

    elif agrup == "cliente":
        titulo = "Faturamento por Cliente"
        if inp.metrica == "ticket_medio":
            titulo = "Ranking de Ticket Médio por Cliente"
        
        res = (
            db.query(Cliente.nome, func.count(Orcamento.id), func.sum(Orcamento.total))
            .join(Orcamento, Cliente.id == Orcamento.cliente_id)
            .filter(
                Orcamento.empresa_id == empresa_id,
                Orcamento.criado_em >= inicio,
                Orcamento.status.in_(_STATUS_FATURADOS),
            )
            .group_by(Cliente.id, Cliente.nome)
            .order_by(func.sum(Orcamento.total).desc())
            .limit(inp.limite)
            .all()
        )
        
        if inp.metrica == "ticket_medio":
            rows = [
                {
                    "Cliente": r[0] or "–",
                    "Orçamentos": int(r[1] or 0),
                    "Faturamento": _brl(r[2]),
                    "Ticket Médio": _brl((_f(r[2]) / int(r[1])) if int(r[1] or 0) > 0 else 0)
                }
                for r in res
            ]
        else:
            rows = [
                {
                    "Cliente": r[0] or "–", 
                    "Orçamentos": int(r[1] or 0), 
                    "Faturamento": _brl(r[2])
                } 
                for r in res
            ]
            
        if rows:
            chart_spec = _chart(
                inp.tipo_grafico or "bar",
                [r["Cliente"] for r in rows[:10]],
                [{"label": "Faturamento (R$)", "data": [_f(res[i][2]) for i in range(min(10, len(res)))], "backgroundColor": _CORES[0]}],
            )

    elif agrup == "vendedor":
        titulo = "Performance por Vendedor"
        res = (
            db.query(Usuario.nome, func.count(Orcamento.id), func.sum(Orcamento.total))
            .join(Orcamento, Usuario.id == Orcamento.criado_por_id)
            .filter(
                Orcamento.empresa_id == empresa_id,
                Orcamento.criado_em >= inicio,
                Orcamento.status.in_(_STATUS_FATURADOS),
            )
            .group_by(Usuario.id, Usuario.nome)
            .order_by(func.sum(Orcamento.total).desc())
            .limit(inp.limite)
            .all()
        )
        rows = [{"Vendedor": r[0] or "–", "Orçamentos": int(r[1] or 0), "Faturamento": _brl(r[2])} for r in res]
        if rows:
            chart_spec = _chart(
                inp.tipo_grafico or "bar",
                [r["Vendedor"] for r in rows],
                [{"label": "Faturamento (R$)", "data": [_f(res[i][2]) for i in range(len(res))], "backgroundColor": _CORES[1]}],
            )

    elif agrup == "servico":
        titulo = "Ticket Médio por Serviço" if inp.metrica == "ticket_medio" else "Vendas por Serviço"
        res = (
            db.query(
                ItemOrcamento.descricao,
                func.count(ItemOrcamento.id),
                func.sum(ItemOrcamento.total)
            )
            .join(Orcamento, ItemOrcamento.orcamento_id == Orcamento.id)
            .filter(
                Orcamento.empresa_id == empresa_id,
                Orcamento.criado_em >= inicio,
                Orcamento.status.in_(_STATUS_FATURADOS),
            )
            .group_by(ItemOrcamento.descricao)
            .order_by(func.sum(ItemOrcamento.total).desc())
            .limit(inp.limite)
            .all()
        )
        if inp.metrica == "ticket_medio":
            rows = [{"Serviço": r[0] or "–", "Quantidade": int(r[1] or 0), "Ticket Médio": _brl(_f(r[2])/int(r[1]) if int(r[1] or 0) > 0 else 0)} for r in res]
        else:
            rows = [{"Serviço": r[0] or "–", "Quantidade": int(r[1] or 0), "Faturamento": _brl(r[2])} for r in res]
        if rows:
            chart_spec = _chart(
                inp.tipo_grafico or "bar",
                [r["Serviço"] for r in rows],
                [{"label": "Valor (R$)", "data": [_f(res[i][2])/int(res[i][1] or 1) if inp.metrica == "ticket_medio" else _f(res[i][2]) for i in range(len(res))], "backgroundColor": _CORES[2]}],
            )

    # Override título por métrica
    metrica = inp.metrica or ""
    if metrica == "taxa_conversao":
        titulo = "Taxa de Conversão de Orçamentos"
    elif metrica in ("faturamento", "total_vendido"):
        titulo = "Relatório de Faturamento"
    elif metrica == "ticket_medio":
        titulo = "Ticket Médio de Orçamentos"

    return {
        "dominio": "orcamentos",
        "titulo": titulo,
        "subtitulo": _periodo_label(inp.periodo_dias),
        "periodo_label": _periodo_label(inp.periodo_dias),
        "periodo_dias": inp.periodo_dias,
        "rows": rows[: inp.limite],
        "metricas_resumo": {
            "total_orcamentos": total,
            "total_aprovados": aprovados,
            "total_enviados": enviados,
            "total_reprovados": reprovados,
            "taxa_conversao_pct": taxa,
            "total_faturado": total_fat,
            "ticket_medio": ticket,
        },
        "chart_spec": chart_spec,
        "insights_base": [
            f"Total de {total} orçamentos no período",
            f"Taxa de conversão: {taxa}% (aprovados/enviados)",
            f"Faturamento: {_brl(total_fat)}",
            f"Ticket médio: {_brl(ticket)}",
            f"Reprovados/expirados: {reprovados}",
        ],
    }


# ── Domínio: clientes ─────────────────────────────────────────────────────────

def _clientes(inp: "GerarRelatorioDinamicoInput", *, db: Session, empresa_id: int) -> dict:
    inicio = _inicio(inp.periodo_dias)

    # Se for pedido clientes inativos (sem compras aprovadas no periodo)
    if inp.metrica == "inativos":
        # Busca clientes da empresa que tem orçamento faturado no periodo
        clientes_ativos_subq = (
            db.query(Orcamento.cliente_id)
            .filter(
                Orcamento.empresa_id == empresa_id,
                Orcamento.criado_em >= inicio,
                Orcamento.status.in_(_STATUS_FATURADOS)
            )
            .subquery()
        )
        
        res = (
            db.query(Cliente.nome, Cliente.criado_em)
            .filter(
                Cliente.empresa_id == empresa_id,
                Cliente.id.notin_(clientes_ativos_subq)
            )
            .order_by(Cliente.nome.asc())
            .limit(inp.limite)
            .all()
        )
        
        rows = [{"Cliente": r[0] or "–", "Cliente desde": r[1].strftime("%d/%m/%Y") if r[1] else "-"} for r in res]
        total_fat = 0
        titulo_cli = "Clientes Inativos (Sem compras no período)"
    else:
        res = (
            db.query(Cliente.nome, func.count(Orcamento.id), func.sum(Orcamento.total))
            .join(
                Orcamento,
                (Cliente.id == Orcamento.cliente_id)
                & (Orcamento.empresa_id == empresa_id)
                & (Orcamento.criado_em >= inicio)
                & (Orcamento.status.in_(_STATUS_FATURADOS)),
            )
            .filter(Cliente.empresa_id == empresa_id)
            .group_by(Cliente.id, Cliente.nome)
            .order_by(func.sum(Orcamento.total).desc())
            .limit(inp.limite)
            .all()
        )
    
        if inp.metrica == "quantidade":
            res = sorted(res, key=lambda x: -int(x[1] or 0))
            titulo_cli = "Top Clientes por Quantidade de Orçamentos"
            rows = [
                {
                    "Cliente": r[0] or "–",
                    "Quantidade de Orçamentos": int(r[1] or 0),
                    "Faturamento Total": _brl(r[2]),
                }
                for r in res
            ]
        else:
            rows = [
                {
                    "Cliente": r[0] or "–",
                    "Orçamentos Aprovados": int(r[1] or 0),
                    "Faturamento Total": _brl(r[2]),
                }
                for r in res
            ]
            
        if "titulo_cli" not in locals() or titulo_cli == "Clientes Inativos (Sem compras no período)":
            titulo_cli = "Ranking de Clientes por Faturamento"
        total_fat = sum(_f(r[2]) for r in res)

    chart_spec = None
    if rows and inp.metrica != "inativos":
        chart_spec = _chart(
            inp.tipo_grafico or "bar",
            [r.get("Cliente", "–") for r in rows[:10]],
            [{"label": "Faturamento (R$)", "data": [_f(res[i][2]) for i in range(min(10, len(res)))], "backgroundColor": _CORES[0]}],
        )

    return {
        "dominio": "clientes",
        "titulo": titulo_cli,
        "subtitulo": _periodo_label(inp.periodo_dias),
        "periodo_label": _periodo_label(inp.periodo_dias),
        "periodo_dias": inp.periodo_dias,
        "rows": rows,
        "metricas_resumo": {
            "clientes_com_compra": len(rows),
            "faturamento_total": total_fat,
        },
        "chart_spec": chart_spec,
        "insights_base": [
            f"Top cliente: {rows[0]['Cliente']} com {rows[0]['Faturamento Total']}" if rows else "Sem dados no período",
            f"{len(rows)} clientes com orçamentos aprovados no período",
            f"Faturamento total: {_brl(total_fat)}",
        ],
    }


# ── Domínio: financeiro ───────────────────────────────────────────────────────

def _financeiro(inp: "GerarRelatorioDinamicoInput", *, db: Session, empresa_id: int) -> dict:
    inicio = _inicio(inp.periodo_dias)
    inicio_date = inicio.date()

    mov = (
        db.query(MovimentacaoCaixa.tipo, func.sum(MovimentacaoCaixa.valor))
        .filter(
            MovimentacaoCaixa.empresa_id == empresa_id,
            MovimentacaoCaixa.data >= inicio_date,
        )
        .group_by(MovimentacaoCaixa.tipo)
        .all()
    )
    entradas = next((_f(r[1]) for r in mov if r[0] == "entrada"), 0.0)
    saidas = next((_f(r[1]) for r in mov if r[0] == "saida"), 0.0)
    saldo = entradas - saidas

    a_receber = _f(
        db.query(func.sum(ContaFinanceira.valor - ContaFinanceira.valor_pago))
        .filter(
            ContaFinanceira.empresa_id == empresa_id,
            ContaFinanceira.tipo == TipoConta.RECEBER,
            ContaFinanceira.status.in_([StatusConta.PENDENTE, StatusConta.PARCIAL]),
            ContaFinanceira.excluido_em.is_(None),
        )
        .scalar()
    )
    a_pagar = _f(
        db.query(func.sum(ContaFinanceira.valor - ContaFinanceira.valor_pago))
        .filter(
            ContaFinanceira.empresa_id == empresa_id,
            ContaFinanceira.tipo == TipoConta.PAGAR,
            ContaFinanceira.status.in_([StatusConta.PENDENTE, StatusConta.PARCIAL]),
            ContaFinanceira.excluido_em.is_(None),
        )
        .scalar()
    )

    if inp.metrica == "despesas" or inp.agrupamento == "categoria":
        res_desp = (
            db.query(ContaFinanceira.categoria, func.sum(ContaFinanceira.valor))
            .filter(
                ContaFinanceira.empresa_id == empresa_id,
                ContaFinanceira.tipo == TipoConta.PAGAR,
                ContaFinanceira.status.in_([StatusConta.PAGO]),
                ContaFinanceira.data_vencimento >= inicio_date,
            )
            .group_by(ContaFinanceira.categoria)
            .order_by(func.sum(ContaFinanceira.valor).desc())
            .all()
        )
        rows = [
            {"Categoria": r[0] or "Geral", "Valor": _brl(r[1])}
            for r in res_desp
        ]
        chart_spec = _chart(
            inp.tipo_grafico or "bar",
            [r["Categoria"] for r in rows],
            [{"label": "R$", "data": [_f(r[1]) for r in res_desp],
              "backgroundColor": _CORES[:len(rows)]}],
        )
        return {
            "dominio": "financeiro",
            "titulo": "Despesas por Categoria",
            "subtitulo": _periodo_label(inp.periodo_dias),
            "periodo_label": _periodo_label(inp.periodo_dias),
            "periodo_dias": inp.periodo_dias,
            "rows": rows,
            "metricas_resumo": {"saidas": saidas},
            "chart_spec": chart_spec,
            "insights_base": [f"Total de saídas: {_brl(saidas)}"],
        }

    rows = [
        {"Categoria": "Entradas confirmadas", "Valor": _brl(entradas)},
        {"Categoria": "Saídas confirmadas", "Valor": _brl(saidas)},
        {"Categoria": "Saldo do período", "Valor": _brl(saldo)},
        {"Categoria": "A receber (pendente)", "Valor": _brl(a_receber)},
        {"Categoria": "A pagar (pendente)", "Valor": _brl(a_pagar)},
    ]

    chart_spec = _chart(
        inp.tipo_grafico or "bar",
        ["Entradas", "Saídas", "A receber", "A pagar"],
        [{"label": "R$", "data": [entradas, saidas, a_receber, a_pagar],
          "backgroundColor": [_COR_OK, _COR_RUIM, _CORES[1], _COR_AVISO]}],
    )

    return {
        "dominio": "financeiro",
        "titulo": "Fluxo de Caixa e Posição Financeira",
        "subtitulo": _periodo_label(inp.periodo_dias),
        "periodo_label": _periodo_label(inp.periodo_dias),
        "periodo_dias": inp.periodo_dias,
        "rows": rows,
        "metricas_resumo": {
            "entradas": entradas,
            "saidas": saidas,
            "saldo_periodo": saldo,
            "a_receber": a_receber,
            "a_pagar": a_pagar,
        },
        "chart_spec": chart_spec,
        "insights_base": [
            f"Entradas: {_brl(entradas)} | Saídas: {_brl(saidas)}",
            f"Saldo do período: {_brl(saldo)}",
            f"A receber: {_brl(a_receber)} | A pagar: {_brl(a_pagar)}",
        ],
    }


# ── Domínio: inadimplencia ────────────────────────────────────────────────────

def _inadimplencia(inp: "GerarRelatorioDinamicoInput", *, db: Session, empresa_id: int) -> dict:
    hoje = date.today()

    res = (
        db.query(
            Cliente.nome,
            func.count(ContaFinanceira.id),
            func.sum(ContaFinanceira.valor - ContaFinanceira.valor_pago),
            func.min(ContaFinanceira.data_vencimento),
        )
        .join(Orcamento, ContaFinanceira.orcamento_id == Orcamento.id, isouter=True)
        .join(Cliente, Orcamento.cliente_id == Cliente.id, isouter=True)
        .filter(
            ContaFinanceira.empresa_id == empresa_id,
            ContaFinanceira.tipo == TipoConta.RECEBER,
            ContaFinanceira.status.in_([StatusConta.PENDENTE, StatusConta.PARCIAL, StatusConta.VENCIDO]),
            ContaFinanceira.data_vencimento < hoje,
            ContaFinanceira.excluido_em.is_(None),
        )
        .group_by(Cliente.id, Cliente.nome)
        .order_by(func.sum(ContaFinanceira.valor - ContaFinanceira.valor_pago).desc())
        .limit(inp.limite)
        .all()
    )

    total_inad = sum(_f(r[2]) for r in res)
    if inp.metrica == "total_aberto":
        res_abertos = (
            db.query(
                func.sum(ContaFinanceira.valor - ContaFinanceira.valor_pago),
                func.count(ContaFinanceira.id)
            )
            .filter(
                ContaFinanceira.empresa_id == empresa_id,
                ContaFinanceira.tipo == TipoConta.RECEBER,
                ContaFinanceira.status.in_([StatusConta.PENDENTE, StatusConta.PARCIAL]),
                ContaFinanceira.excluido_em.is_(None),
            )
            .first()
        )
        total_inad_geral = _f(res_abertos[0] if res_abertos else 0)
        qnt_contas = int(res_abertos[1] if res_abertos else 0)
        
        rows = [
            {"Métrica": "Valor Total em Aberto", "Valor": _brl(total_inad_geral)},
            {"Métrica": "Quantidade de Contas", "Valor": qnt_contas},
            {"Métrica": "Inclui Atrasadas e a Vencer", "Valor": "Sim"}
        ]
        total_inad = total_inad_geral
    else:
        rows = [
            {
                "Cliente": r[0] or "Sem cliente",
                "Contas em atraso": int(r[1] or 0),
                "Valor em aberto": _brl(r[2]),
                "Vencimento mais antigo": str(r[3]) if r[3] else "–",
            }
            for r in res
        ]
        total_inad = sum(_f(r[2]) for r in res)

    chart_spec = None
    if rows and inp.metrica != "total_aberto":
        chart_spec = _chart(
            inp.tipo_grafico or "bar",
            [r.get("Cliente", "–") for r in rows[:10]],
            [{"label": "Valor em Aberto (R$)", "data": [_f(r[2]) for r in res[:10]], "backgroundColor": _COR_RUIM}],
        )

    return {
        "dominio": "inadimplencia",
        "titulo": "Relatório de Inadimplência",
        "subtitulo": f"Contas vencidas até {hoje.strftime('%d/%m/%Y')}",
        "periodo_label": "Vencidas até hoje",
        "periodo_dias": inp.periodo_dias,
        "rows": rows,
        "metricas_resumo": {
            "clientes_inadimplentes": len(rows),
            "total_inadimplente": total_inad,
        },
        "chart_spec": chart_spec,
        "insights_base": [
            f"{len(rows)} clientes com contas em atraso" if inp.metrica != "total_aberto" else "Relatório de contas em aberto",
            f"Total inadimplente: {_brl(total_inad)}",
            f"Maior devedor: {rows[0].get('Cliente', '–')} ({rows[0].get('Valor em aberto', '–')})" if rows and inp.metrica != "total_aberto" else "Geral",
        ],
    }


# ── Domínio: servicos ─────────────────────────────────────────────────────────

def _servicos(inp: "GerarRelatorioDinamicoInput", *, db: Session, empresa_id: int) -> dict:
    inicio = _inicio(inp.periodo_dias)

    res = (
        db.query(
            ItemOrcamento.descricao,
            func.count(ItemOrcamento.id),
            func.sum(ItemOrcamento.total),
            func.avg(ItemOrcamento.valor_unit),
        )
        .join(Orcamento, ItemOrcamento.orcamento_id == Orcamento.id)
        .filter(
            Orcamento.empresa_id == empresa_id,
            Orcamento.criado_em >= inicio,
            Orcamento.status.in_(_STATUS_FATURADOS),
        )
        .group_by(ItemOrcamento.descricao)
        .order_by(func.sum(ItemOrcamento.total).desc())
        .limit(inp.limite)
        .all()
    )

    if inp.metrica == "quantidade":
        res = sorted(res, key=lambda x: -x[1])
        rows = [
            {
                "Serviço": r[0] or "–",
                "Quantidade": int(r[1] or 0),
                "Faturamento": _brl(r[2]),
                "Preço médio": _brl(r[3]),
            }
            for r in res
        ]
        titulo = "Serviços Mais Vendidos por Quantidade"
    else:
        rows = [
            {
                "Serviço": r[0] or "–",
                "Vendas": int(r[1] or 0),
                "Faturamento": _brl(r[2]),
                "Preço médio": _brl(r[3]),
            }
            for r in res
        ]
        titulo = "Serviços Mais Vendidos por Valor"

    chart_spec = None
    if rows:
        chart_spec = _chart(
            inp.tipo_grafico or "bar",
            [r["Serviço"] for r in rows[:8]],
            [{"label": "Quantidade" if inp.metrica == "quantidade" else "Faturamento (R$)", "data": [int(res[i][1]) if inp.metrica == "quantidade" else _f(res[i][2]) for i in range(min(8, len(res)))], "backgroundColor": _CORES[2]}],
        )

    return {
        "dominio": "servicos",
        "titulo": titulo,
        "subtitulo": _periodo_label(inp.periodo_dias),
        "periodo_label": _periodo_label(inp.periodo_dias),
        "periodo_dias": inp.periodo_dias,
        "rows": rows,
        "metricas_resumo": {
            "servicos_distintos": len(rows),
            "top_servico": rows[0]["Serviço"] if rows else "–",
        },
        "chart_spec": chart_spec,
        "insights_base": [
            f"Serviço mais vendido: {rows[0]['Serviço']} ({rows[0]['Faturamento']})" if rows else "Sem dados",
            f"{len(rows)} serviços distintos faturados no período",
        ],
    }


# ── Domínio: agendamentos ─────────────────────────────────────────────────────

def _agendamentos(inp: "GerarRelatorioDinamicoInput", *, db: Session, empresa_id: int) -> dict:
    inicio = _inicio(inp.periodo_dias)

    res = (
        db.query(Agendamento.status, func.count(Agendamento.id))
        .filter(
            Agendamento.empresa_id == empresa_id,
            Agendamento.criado_em >= inicio,
        )
        .group_by(Agendamento.status)
        .all()
    )

    counts = {r[0]: int(r[1] or 0) for r in res}
    total = sum(counts.values())
    cancelados = counts.get(StatusAgendamento.CANCELADO, 0) + counts.get(StatusAgendamento.NAO_COMPARECEU, 0)
    concluidos = counts.get(StatusAgendamento.CONCLUIDO, 0)
    taxa_cancel = round(cancelados / total * 100, 1) if total else 0.0

    label_map = {
        StatusAgendamento.AGUARDANDO_ESCOLHA: "Aguard. escolha",
        StatusAgendamento.PENDENTE: "Pendente",
        StatusAgendamento.CONFIRMADO: "Confirmado",
        StatusAgendamento.EM_ANDAMENTO: "Em andamento",
        StatusAgendamento.CONCLUIDO: "Concluído",
        StatusAgendamento.REAGENDADO: "Reagendado",
        StatusAgendamento.CANCELADO: "Cancelado",
        StatusAgendamento.NAO_COMPARECEU: "Não compareceu",
    }

    if inp.metrica == "taxa_cancelamento":
        rows = [
            {"Métrica": "Total Agendado", "Valor": total},
            {"Métrica": "Concluídos", "Valor": concluidos},
            {"Métrica": "Cancelados/Não compareceu", "Valor": cancelados},
            {"Métrica": "Taxa de Cancelamento", "Valor": f"{taxa_cancel}%"}
        ]
    else:
        rows = [
            {
                "Status": label_map.get(s, str(s)),
                "Qtd.": c,
                "% do total": f"{round(c / total * 100, 1)}%" if total else "0%",
            }
            for s, c in sorted(counts.items(), key=lambda x: -x[1])
        ]

    chart_spec = None
    if rows and inp.metrica != "taxa_cancelamento":
        chart_spec = _chart(
            inp.tipo_grafico or "doughnut",
            [r["Status"] for r in rows],
            [{"label": "Agendamentos", "data": [r["Qtd."] for r in rows],
              "backgroundColor": _CORES[: len(rows)]}],
        )

    return {
        "dominio": "agendamentos",
        "titulo": "Relatório de Agendamentos" if inp.metrica != "taxa_cancelamento" else "Taxa de Cancelamento de Agendamentos",
        "subtitulo": _periodo_label(inp.periodo_dias),
        "periodo_label": _periodo_label(inp.periodo_dias),
        "periodo_dias": inp.periodo_dias,
        "rows": rows,
        "metricas_resumo": {
            "total_agendamentos": total,
            "concluidos": concluidos,
            "taxa_cancelamento_pct": taxa_cancel,
        },
        "chart_spec": chart_spec,
        "insights_base": [
            f"Total de {total} agendamentos no período",
            f"Concluídos: {concluidos} | Taxa de cancelamento: {taxa_cancel}%",
        ],
    }


# ── Domínio: operacional ──────────────────────────────────────────────────────

def _operacional(inp: "GerarRelatorioDinamicoInput", *, db: Session, empresa_id: int) -> dict:
    inicio = _inicio(inp.periodo_dias)

    total_orcs = db.query(func.count(Orcamento.id)).filter(
        Orcamento.empresa_id == empresa_id, Orcamento.criado_em >= inicio
    ).scalar() or 0

    enviados = db.query(func.count(Orcamento.id)).filter(
        Orcamento.empresa_id == empresa_id,
        Orcamento.criado_em >= inicio,
        Orcamento.status != StatusOrcamento.RASCUNHO,
    ).scalar() or 0

    res_fat2 = db.query(
        func.sum(Orcamento.total), func.count(Orcamento.id)
    ).filter(
        Orcamento.empresa_id == empresa_id,
        Orcamento.criado_em >= inicio,
        Orcamento.status.in_(_STATUS_FATURADOS),
    ).first()
    fat_sum = res_fat2[0] if res_fat2 and res_fat2[0] is not None else 0
    fat_cnt = res_fat2[1] if res_fat2 and res_fat2[1] is not None else 0

    aprovados = int(fat_cnt or 0)
    total_fat = _f(fat_sum)
    taxa = round(aprovados / enviados * 100, 1) if enviados else 0.0
    ticket = round(total_fat / aprovados, 2) if aprovados else 0.0

    clientes_ativos = db.query(func.count(func.distinct(Orcamento.cliente_id))).filter(
        Orcamento.empresa_id == empresa_id, Orcamento.criado_em >= inicio
    ).scalar() or 0

    inad = _f(
        db.query(func.sum(ContaFinanceira.valor - ContaFinanceira.valor_pago))
        .filter(
            ContaFinanceira.empresa_id == empresa_id,
            ContaFinanceira.tipo == TipoConta.RECEBER,
            ContaFinanceira.status.in_([StatusConta.PENDENTE, StatusConta.VENCIDO]),
            ContaFinanceira.data_vencimento < date.today(),
            ContaFinanceira.excluido_em.is_(None),
        )
        .scalar()
    )

    rows = [
        {"KPI": "Orçamentos criados", "Valor": str(total_orcs)},
        {"KPI": "Orçamentos aprovados", "Valor": str(aprovados)},
        {"KPI": "Taxa de conversão", "Valor": f"{taxa}%"},
        {"KPI": "Faturamento total", "Valor": _brl(total_fat)},
        {"KPI": "Ticket médio", "Valor": _brl(ticket)},
        {"KPI": "Clientes ativos no período", "Valor": str(clientes_ativos)},
        {"KPI": "Inadimplência em aberto", "Valor": _brl(inad)},
    ]

    chart_spec = _chart(
        inp.tipo_grafico or "bar",
        ["Criados", "Enviados", "Aprovados"],
        [{"label": "Orçamentos", "data": [total_orcs, enviados, aprovados],
          "backgroundColor": [_CORES[1], _COR_AVISO, _COR_OK]}],
    )

    return {
        "dominio": "operacional",
        "titulo": "Visão Operacional da Empresa",
        "subtitulo": _periodo_label(inp.periodo_dias),
        "periodo_label": _periodo_label(inp.periodo_dias),
        "periodo_dias": inp.periodo_dias,
        "rows": rows,
        "metricas_resumo": {
            "total_orcamentos": total_orcs,
            "aprovados": aprovados,
            "taxa_conversao_pct": taxa,
            "faturamento_total": total_fat,
            "ticket_medio": ticket,
            "clientes_ativos": clientes_ativos,
            "inadimplencia_total": inad,
        },
        "chart_spec": chart_spec,
        "insights_base": [
            f"Faturamento: {_brl(total_fat)} | Ticket médio: {_brl(ticket)}",
            f"Conversão: {taxa}% | Clientes ativos: {clientes_ativos}",
            f"Inadimplência em aberto: {_brl(inad)}",
        ],
    }


# ── Input model ───────────────────────────────────────────────────────────────

class GerarRelatorioDinamicoInput(BaseModel):
    dominio: str = Field(
        description=(
            "Área de dados para o relatório. Valores aceitos: "
            "'orcamentos' (visão geral, conversão, faturamento, ticket médio, status, "
            "ranking por cliente/vendedor), "
            "'clientes' (ranking por faturamento), "
            "'financeiro' (fluxo de caixa, despesas, contas a receber/pagar), "
            "'inadimplencia' (contas vencidas por cliente), "
            "'servicos' (mais vendidos, ticket médio por serviço), "
            "'agendamentos' (por período, taxa de cancelamento), "
            "'operacional' (KPIs combinados da empresa)."
        )
    )
    periodo_dias: int = Field(
        default=30, ge=1, le=365,
        description="Janela temporal retroativa em dias. Ex: 30 = último mês, 90 = trimestre.",
    )
    agrupamento: Optional[str] = Field(
        default=None,
        description="Como agrupar: 'status', 'cliente', 'vendedor', 'servico', 'periodo'.",
    )
    filtro_status: Optional[str] = Field(
        default=None,
        description="Filtrar por status específico (ex: 'aprovado', 'enviado', 'recusado').",
    )
    filtro_usuario_id: Optional[int] = Field(
        default=None,
        description="Filtrar por usuário/vendedor (ID).",
    )
    tipo_grafico: Optional[str] = Field(
        default=None,
        description="Tipo de gráfico: 'bar', 'line', 'pie', 'doughnut'. Omitir para automático.",
    )
    limite: int = Field(
        default=20, ge=1, le=100,
        description="Máximo de linhas a retornar.",
    )
    metrica: Optional[str] = Field(
        default=None,
        description=(
            "Métrica específica: 'taxa_conversao', 'faturamento', "
            "'ticket_medio', 'total_vendido'."
        ),
    )


# ── Handler principal ─────────────────────────────────────────────────────────

_HANDLERS: dict[str, Callable] = {
    "orcamentos": _orcamentos,
    "clientes": _clientes,
    "financeiro": _financeiro,
    "inadimplencia": _inadimplencia,
    "servicos": _servicos,
    "agendamentos": _agendamentos,
    "operacional": _operacional,
}


async def _handler_gerar_relatorio_dinamico(
    inp: GerarRelatorioDinamicoInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    dominio = inp.dominio.lower().strip()
    handler_fn = _HANDLERS.get(dominio)
    if not handler_fn:
        return {
            "erro": f"Domínio '{dominio}' não reconhecido.",
            "dominios_validos": list(_HANDLERS.keys()),
            "dominio": dominio,
            "rows": [],
            "metricas_resumo": {},
            "insights_base": [],
        }
    return handler_fn(inp, db=db, empresa_id=current_user.empresa_id)


# ── ToolSpec ──────────────────────────────────────────────────────────────────

gerar_relatorio_dinamico = ToolSpec(
    name="gerar_relatorio_dinamico",
    description=(
        "Gera relatórios analíticos completos sobre qualquer área do negócio: "
        "orçamentos (visão geral, taxa de conversão, faturamento, ticket médio, "
        "distribuição de status, ranking por cliente, performance por vendedor), "
        "clientes (ranking por faturamento), "
        "financeiro (fluxo de caixa, despesas, contas a receber/pagar), "
        "inadimplência (clientes com contas vencidas), "
        "serviços mais vendidos, agendamentos, "
        "e visão operacional geral (KPIs da empresa). "
        "Retorna dados estruturados com tabela, métricas-resumo, spec de gráfico e insights."
    ),
    input_model=GerarRelatorioDinamicoInput,
    handler=_handler_gerar_relatorio_dinamico,
    destrutiva=False,
    cacheable_ttl=60,
    permissao_recurso="ia",
    permissao_acao="leitura",
)
