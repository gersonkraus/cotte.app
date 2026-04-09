from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone

from app.core.database import get_db
from app.core.auth import get_usuario_atual, exigir_permissao, exigir_modulo
from app.models.models import Orcamento, StatusOrcamento, Usuario
from app.services.plano_service import exigir_relatorios

router = APIRouter(prefix="/relatorios", tags=["Relatórios"], dependencies=[Depends(exigir_modulo("relatorios"))])


@router.get("/resumo")
def relatorio_resumo(
    data_inicio: str = Query(None, description="YYYY-MM-DD"),
    data_fim: str = Query(None, description="YYYY-MM-DD"),
    filtro_aprovacao: str = Query(
        "todos", description="todos | aprovados | nao_aprovados"
    ),
    filtro_envio: str = Query("todos", description="todos | enviados | nao_enviados"),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("relatorios", "leitura")),
):
    """Gera resumo de relatórios com faturamento, métricas e dados por cliente."""

    # Verifica se o plano atual permite acessar relatórios
    if usuario.empresa:
        exigir_relatorios(usuario.empresa)
    query = db.query(Orcamento).filter(Orcamento.empresa_id == usuario.empresa_id)

    if data_inicio:
        try:
            d_ini = datetime.strptime(data_inicio, "%Y-%m-%d").date()
            query = query.filter(func.date(Orcamento.criado_em) >= d_ini)
        except ValueError:
            pass
    if data_fim:
        try:
            d_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
            query = query.filter(func.date(Orcamento.criado_em) <= d_fim)
        except ValueError:
            pass

    todos_periodo = query.all()

    # Totais do período inteiro (sem filtros de aprovação/envio) — usados nos cards de contagem
    tot_aprovados = sum(
        1 for o in todos_periodo if o.status == StatusOrcamento.APROVADO
    )
    tot_recusados = sum(
        1 for o in todos_periodo if o.status == StatusOrcamento.RECUSADO
    )
    tot_enviados = sum(1 for o in todos_periodo if o.status == StatusOrcamento.ENVIADO)
    tot_rascunho = sum(1 for o in todos_periodo if o.status == StatusOrcamento.RASCUNHO)
    tot_expirados = sum(
        1 for o in todos_periodo if o.status == StatusOrcamento.EXPIRADO
    )
    tot_em_execucao = sum(1 for o in todos_periodo if o.status == StatusOrcamento.EM_EXECUCAO)
    tot_aguardando_pagamento = sum(
        1 for o in todos_periodo if o.status == StatusOrcamento.AGUARDANDO_PAGAMENTO
    )

    # Filtro por aprovação: aprovados / não aprovados
    orcamentos = todos_periodo
    if filtro_aprovacao == "aprovados":
        orcamentos = [o for o in orcamentos if o.status == StatusOrcamento.APROVADO]
    elif filtro_aprovacao == "nao_aprovados":
        orcamentos = [o for o in orcamentos if o.status != StatusOrcamento.APROVADO]

    # Filtro por envio: enviados / não enviados
    if filtro_envio == "enviados":
        orcamentos = [o for o in orcamentos if o.status == StatusOrcamento.ENVIADO]
    elif filtro_envio == "nao_enviados":
        orcamentos = [o for o in orcamentos if o.status != StatusOrcamento.ENVIADO]

    faturamento_aprovado = sum(
        o.total for o in orcamentos if o.status == StatusOrcamento.APROVADO
    )
    qtd_aprovados = sum(1 for o in orcamentos if o.status == StatusOrcamento.APROVADO)
    qtd_recusados = sum(1 for o in orcamentos if o.status == StatusOrcamento.RECUSADO)
    qtd_enviados = sum(1 for o in orcamentos if o.status == StatusOrcamento.ENVIADO)
    qtd_rascunho = sum(1 for o in orcamentos if o.status == StatusOrcamento.RASCUNHO)
    qtd_expirados = sum(1 for o in orcamentos if o.status == StatusOrcamento.EXPIRADO)

    # ── #6: Taxa de aprovação ──────────────────────────────────────────────────
    # Considera apenas orçamentos que saíram do rascunho (excluindo RASCUNHO)
    decididos = qtd_aprovados + qtd_recusados + qtd_expirados + qtd_enviados
    taxa_aprovacao = (
        round((qtd_aprovados / decididos * 100), 1) if decididos > 0 else 0.0
    )

    # ── #6: Ticket médio ───────────────────────────────────────────────────────
    ticket_medio = (
        round(faturamento_aprovado / qtd_aprovados, 2) if qtd_aprovados > 0 else 0.0
    )

    # ── #6: Tempo médio de aprovação (dias entre criado_em e aceite_em) ────────
    tempos = []
    for o in orcamentos:
        if o.status == StatusOrcamento.APROVADO and o.aceite_em and o.criado_em:
            criado = o.criado_em
            aceite = o.aceite_em
            if criado.tzinfo is None:
                criado = criado.replace(tzinfo=timezone.utc)
            if aceite.tzinfo is None:
                aceite = aceite.replace(tzinfo=timezone.utc)
            delta = (aceite - criado).total_seconds() / 86400  # em dias
            if delta >= 0:
                tempos.append(delta)
    tempo_medio_aprovacao = round(sum(tempos) / len(tempos), 1) if tempos else None

    # ── #6: Orçamentos prestes a expirar (próximos 3 dias, status ENVIADO) ─────
    agora = datetime.now(timezone.utc)
    prestes_expirar = []
    # Busca TODOS os enviados da empresa (não só do período filtrado)
    todos_enviados = (
        db.query(Orcamento)
        .filter(
            Orcamento.empresa_id == usuario.empresa_id,
            Orcamento.status == StatusOrcamento.ENVIADO,
        )
        .all()
    )
    for o in todos_enviados:
        if not o.criado_em or not o.validade_dias:
            continue
        criado = o.criado_em
        if criado.tzinfo is None:
            criado = criado.replace(tzinfo=timezone.utc)
        expira = criado + timedelta(days=o.validade_dias)
        dias_restantes = (expira - agora).total_seconds() / 86400
        if 0 < dias_restantes <= 3:
            prestes_expirar.append(
                {
                    "id": o.id,
                    "numero": o.numero,
                    "cliente": o.cliente.nome if o.cliente else "—",
                    "total": round(o.total, 2),
                    "expira_em": expira.strftime("%d/%m/%Y"),
                    "dias_restantes": round(dias_restantes, 1),
                }
            )
    prestes_expirar.sort(key=lambda x: x["dias_restantes"])

    # ── Por cliente ───────────────────────────────────────────────────────────
    por_cliente: dict = {}
    for o in orcamentos:
        nome = o.cliente.nome if o.cliente else "Sem cliente"
        if nome not in por_cliente:
            por_cliente[nome] = {"total": Decimal("0"), "quantidade": 0, "aprovados": 0}
        por_cliente[nome]["quantidade"] += 1
        if o.status == StatusOrcamento.APROVADO:
            por_cliente[nome]["total"] += o.total
            por_cliente[nome]["aprovados"] += 1

    lista_clientes = [
        {
            "cliente": k,
            "total": round(v["total"], 2),
            "quantidade": v["quantidade"],
            "aprovados": v["aprovados"],
        }
        for k, v in por_cliente.items()
    ]
    lista_clientes.sort(key=lambda x: (-x["total"], -x["quantidade"]))

    return {
        "periodo": {"data_inicio": data_inicio, "data_fim": data_fim},
        "filtros": {"aprovacao": filtro_aprovacao, "envio": filtro_envio},
        "faturamento_aprovado": round(faturamento_aprovado, 2),
        # totais do período completo (sem filtros de aprovação/envio) — para os cards de contagem
        "totais_periodo": {
            "aprovados": tot_aprovados,
            "recusados": tot_recusados,
            "enviados": tot_enviados,
            "rascunho": tot_rascunho,
            "expirados": tot_expirados,
            "em_execucao": tot_em_execucao,
            "aguardando_pagamento": tot_aguardando_pagamento,
            "total": len(todos_periodo),
        },
        # quantidades do conjunto filtrado — para o gráfico
        "quantidades": {
            "aprovados": qtd_aprovados,
            "recusados": qtd_recusados,
            "enviados": qtd_enviados,
            "rascunho": qtd_rascunho,
            "expirados": qtd_expirados,
            "total": len(orcamentos),
        },
        # #6 — novas métricas
        "taxa_aprovacao": taxa_aprovacao,  # % de aprovação
        "ticket_medio": ticket_medio,  # R$ médio dos aprovados
        "tempo_medio_aprovacao": tempo_medio_aprovacao,  # dias (pode ser null)
        "prestes_a_expirar": prestes_expirar,  # lista dos que vencem em 3 dias
        "por_cliente": lista_clientes[:20],
    }
