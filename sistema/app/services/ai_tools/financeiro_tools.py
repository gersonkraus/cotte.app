"""Tools financeiras: saldo, movimentações e criação de movimentação."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.models import MovimentacaoCaixa, Usuario
from app.services import financeiro_service

from ._base import ToolSpec


# ── obter_saldo_caixa ──────────────────────────────────────────────────────
class ObterSaldoCaixaInput(BaseModel):
    pass  # sem parâmetros — usa empresa do usuário


async def _obter_saldo_caixa(
    inp: ObterSaldoCaixaInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    stats = financeiro_service._calcular_estatisticas_caixa(
        current_user.empresa_id, db
    )
    # Decimal -> float para serializar
    return {
        "saldo_atual": float(stats.get("saldo_atual", 0) or 0),
        "entradas_confirmadas": float(stats.get("entradas_confirmadas", 0) or 0),
        "saidas_confirmadas": float(stats.get("saidas_confirmadas", 0) or 0),
        "saldo_inicial": float(stats.get("saldo_inicial", 0) or 0),
    }


obter_saldo_caixa = ToolSpec(
    name="obter_saldo_caixa",
    description=(
        "Retorna o saldo atual do caixa operacional da empresa do usuário "
        "(saldo inicial + entradas confirmadas - saídas confirmadas)."
    ),
    input_model=ObterSaldoCaixaInput,
    handler=_obter_saldo_caixa,
    destrutiva=False,
    cacheable_ttl=30,
    permissao_recurso="financeiro",
    permissao_acao="leitura",
)


# ── listar_movimentacoes_financeiras ───────────────────────────────────────
class ListarMovimentacoesInput(BaseModel):
    tipo: Optional[str] = Field(
        default=None, description="'entrada' ou 'saida'. Omitir para listar ambos."
    )
    dias: int = Field(
        default=30, ge=1, le=365, description="Janela em dias retroativos."
    )
    limit: int = Field(default=20, ge=1, le=100)


async def _listar_movimentacoes(
    inp: ListarMovimentacoesInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    desde = date.today() - timedelta(days=inp.dias)
    q = (
        db.query(MovimentacaoCaixa)
        .filter(
            MovimentacaoCaixa.empresa_id == current_user.empresa_id,
            MovimentacaoCaixa.data >= desde,
        )
        .order_by(MovimentacaoCaixa.data.desc(), MovimentacaoCaixa.id.desc())
    )
    if inp.tipo:
        q = q.filter(MovimentacaoCaixa.tipo == inp.tipo)
    items = q.limit(inp.limit).all()
    return {
        "total": len(items),
        "movimentacoes": [
            {
                "id": m.id,
                "tipo": m.tipo,
                "valor": float(m.valor),
                "descricao": m.descricao,
                "categoria": m.categoria,
                "data": m.data.isoformat() if m.data else None,
                "confirmado": m.confirmado,
            }
            for m in items
        ],
    }


listar_movimentacoes_financeiras = ToolSpec(
    name="listar_movimentacoes_financeiras",
    description=(
        "Lista movimentações de caixa (entradas/saídas manuais) da empresa "
        "do usuário em uma janela de dias."
    ),
    input_model=ListarMovimentacoesInput,
    handler=_listar_movimentacoes,
    destrutiva=False,
    cacheable_ttl=15,
    permissao_recurso="financeiro",
    permissao_acao="leitura",
)


# ── criar_movimentacao_financeira (DESTRUTIVA) ─────────────────────────────
class CriarMovimentacaoInput(BaseModel):
    tipo: str = Field(description="'entrada' ou 'saida'.")
    valor: float = Field(gt=0, description="Valor positivo em reais.")
    descricao: str = Field(min_length=2, max_length=300)
    categoria: str = Field(default="geral", max_length=100)
    data: Optional[str] = Field(
        default=None, description="ISO date (YYYY-MM-DD). Omitir = hoje."
    )


async def _criar_movimentacao(
    inp: CriarMovimentacaoInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    if inp.tipo not in ("entrada", "saida"):
        return {"error": "tipo inválido", "code": "invalid_input"}
    data_mov = (
        datetime.fromisoformat(inp.data).date() if inp.data else date.today()
    )
    mov = MovimentacaoCaixa(
        empresa_id=current_user.empresa_id,
        tipo=inp.tipo,
        valor=Decimal(str(inp.valor)),
        descricao=inp.descricao,
        categoria=inp.categoria or "geral",
        data=data_mov,
        confirmado=True,
        criado_por_id=current_user.id,
    )
    db.add(mov)
    db.commit()
    db.refresh(mov)
    return {
        "id": mov.id,
        "tipo": mov.tipo,
        "valor": float(mov.valor),
        "descricao": mov.descricao,
        "data": mov.data.isoformat(),
        "criado": True,
    }


criar_movimentacao_financeira = ToolSpec(
    name="criar_movimentacao_financeira",
    description=(
        "Registra uma entrada ou saída manual no caixa. AÇÃO DESTRUTIVA — "
        "exige confirmação do usuário."
    ),
    input_model=CriarMovimentacaoInput,
    handler=_criar_movimentacao,
    destrutiva=True,
    permissao_recurso="financeiro",
    permissao_acao="escrita",
)


# ── registrar_pagamento_recebivel (DESTRUTIVA) ─────────────────────────────
class RegistrarPagamentoRecebivelInput(BaseModel):
    conta_id: int = Field(
        gt=0,
        description="ID da conta a receber (obtenha via listar_orcamentos ou consulta prévia).",
    )
    valor: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="Valor pago. Omitir para quitar o saldo integral em aberto.",
    )
    forma_pagamento_id: Optional[int] = Field(
        default=None, gt=0, description="ID opcional da forma de pagamento cadastrada."
    )
    data_pagamento: Optional[str] = Field(
        default=None, description="ISO date (YYYY-MM-DD). Omitir = hoje."
    )
    observacao: Optional[str] = Field(default=None, max_length=500)


async def _registrar_pagamento_recebivel(
    inp: RegistrarPagamentoRecebivelInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    from fastapi import HTTPException

    data_pg = (
        datetime.fromisoformat(inp.data_pagamento).date()
        if inp.data_pagamento
        else None
    )
    try:
        pagamento = financeiro_service.registrar_pagamento_conta_receber(
            conta_id=inp.conta_id,
            empresa_id=current_user.empresa_id,
            usuario=current_user,
            db=db,
            valor=inp.valor,
            forma_pagamento_id=inp.forma_pagamento_id,
            observacao=inp.observacao,
            data_pagamento=data_pg,
        )
    except HTTPException as e:
        code = "not_found" if e.status_code == 404 else "invalid_input"
        return {"error": str(e.detail), "code": code}

    db.commit()
    db.refresh(pagamento)
    return {
        "id": pagamento.id,
        "conta_id": pagamento.conta_id,
        "orcamento_id": pagamento.orcamento_id,
        "valor": float(pagamento.valor),
        "data_pagamento": pagamento.data_pagamento.isoformat()
        if pagamento.data_pagamento
        else None,
        "status": pagamento.status.value
        if hasattr(pagamento.status, "value")
        else str(pagamento.status),
        "criado": True,
    }


registrar_pagamento_recebivel = ToolSpec(
    name="registrar_pagamento_recebivel",
    description=(
        "Registra o pagamento de uma conta a receber (avulsa ou vinculada a "
        "orçamento aprovado). Se o valor for omitido, quita o saldo integral. "
        "AÇÃO DESTRUTIVA — exige confirmação."
    ),
    input_model=RegistrarPagamentoRecebivelInput,
    handler=_registrar_pagamento_recebivel,
    destrutiva=True,
    permissao_recurso="financeiro",
    permissao_acao="escrita",
)


# ── listar_despesas ────────────────────────────────────────────────────────
class ListarDespesasInput(BaseModel):
    status: Optional[str] = Field(
        default=None,
        description="Filtrar por status: 'pendente', 'pago', 'vencido', 'cancelado'.",
    )
    busca: Optional[str] = Field(
        default=None, description="Busca parcial por descrição/favorecido."
    )
    dias: int = Field(
        default=60, ge=1, le=365, description="Janela (dias) em torno do vencimento."
    )
    limit: int = Field(default=20, ge=1, le=100)


async def _listar_despesas(
    inp: ListarDespesasInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    from app.models.models import StatusConta

    status_enum: Optional[StatusConta] = None
    if inp.status:
        try:
            status_enum = StatusConta(inp.status.lower())
        except ValueError:
            return {"error": f"status inválido: {inp.status}", "code": "invalid_input"}

    hoje = date.today()
    desde = hoje - timedelta(days=inp.dias)
    ate = hoje + timedelta(days=inp.dias)

    items = financeiro_service.listar_despesas(
        empresa_id=current_user.empresa_id,
        db=db,
        status=status_enum,
        data_inicio=desde,
        data_fim=ate,
        busca=inp.busca,
    )[: inp.limit]

    return {
        "total": len(items),
        "despesas": [
            {
                "id": d.id,
                "descricao": d.descricao,
                "favorecido": d.favorecido,
                "valor": float(d.valor or 0),
                "valor_pago": float(d.valor_pago or 0),
                "status": d.status.value if hasattr(d.status, "value") else str(d.status),
                "data_vencimento": d.data_vencimento.isoformat() if d.data_vencimento else None,
                "categoria": d.categoria_slug,
            }
            for d in items
        ],
    }


listar_despesas = ToolSpec(
    name="listar_despesas",
    description=(
        "Lista contas a pagar (despesas) da empresa do usuário, com filtros por "
        "status, busca e janela de vencimento. Use antes de marcar uma despesa como paga."
    ),
    input_model=ListarDespesasInput,
    handler=_listar_despesas,
    destrutiva=False,
    cacheable_ttl=15,
    permissao_recurso="financeiro",
    permissao_acao="leitura",
)


# ── criar_despesa (DESTRUTIVA) ─────────────────────────────────────────────
class CriarDespesaInput(BaseModel):
    descricao: str = Field(min_length=2, max_length=300)
    valor: Decimal = Field(gt=0)
    data_vencimento: str = Field(description="ISO date (YYYY-MM-DD).")
    favorecido: Optional[str] = Field(default=None, max_length=200)
    categoria_slug: Optional[str] = Field(default=None, max_length=100)


async def _criar_despesa(
    inp: CriarDespesaInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    try:
        venc = datetime.fromisoformat(inp.data_vencimento).date()
    except ValueError:
        return {"error": "data_vencimento inválida (use YYYY-MM-DD)", "code": "invalid_input"}

    conta = financeiro_service.criar_despesa(
        empresa_id=current_user.empresa_id,
        dados={
            "descricao": inp.descricao.strip(),
            "valor": inp.valor,
            "data_vencimento": venc,
            "favorecido": (inp.favorecido or "").strip() or None,
            "categoria_slug": inp.categoria_slug,
        },
        db=db,
    )
    db.commit()
    db.refresh(conta)
    return {
        "id": conta.id,
        "descricao": conta.descricao,
        "valor": float(conta.valor or 0),
        "data_vencimento": conta.data_vencimento.isoformat() if conta.data_vencimento else None,
        "status": conta.status.value if hasattr(conta.status, "value") else str(conta.status),
        "criado": True,
    }


criar_despesa = ToolSpec(
    name="criar_despesa",
    description=(
        "Cria uma conta a pagar (despesa) manualmente. AÇÃO DESTRUTIVA — exige confirmação."
    ),
    input_model=CriarDespesaInput,
    handler=_criar_despesa,
    destrutiva=True,
    permissao_recurso="financeiro",
    permissao_acao="escrita",
)


# ── marcar_despesa_paga (DESTRUTIVA) ───────────────────────────────────────
class MarcarDespesaPagaInput(BaseModel):
    conta_id: int = Field(gt=0, description="ID da despesa (use listar_despesas antes).")
    valor: Optional[Decimal] = Field(
        default=None, ge=0, description="Valor pago. Omitir para quitar saldo integral."
    )
    forma_pagamento_id: Optional[int] = Field(default=None, gt=0)
    observacao: Optional[str] = Field(default=None, max_length=500)


async def _marcar_despesa_paga(
    inp: MarcarDespesaPagaInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    from fastapi import HTTPException

    try:
        pagamento = financeiro_service.registrar_pagamento_despesa(
            conta_id=inp.conta_id,
            empresa_id=current_user.empresa_id,
            usuario=current_user,
            db=db,
            valor=inp.valor,
            forma_pagamento_id=inp.forma_pagamento_id,
            observacao=inp.observacao,
        )
    except HTTPException as e:
        code = "not_found" if e.status_code == 404 else "invalid_input"
        return {"error": str(e.detail), "code": code}

    db.commit()
    db.refresh(pagamento)
    return {
        "id": pagamento.id,
        "conta_id": pagamento.conta_id,
        "valor": float(pagamento.valor),
        "data_pagamento": pagamento.data_pagamento.isoformat()
        if pagamento.data_pagamento
        else None,
        "criado": True,
    }


marcar_despesa_paga = ToolSpec(
    name="marcar_despesa_paga",
    description=(
        "Registra o pagamento (quitação total ou parcial) de uma despesa. "
        "Se o valor for omitido, quita o saldo integral. AÇÃO DESTRUTIVA — exige confirmação."
    ),
    input_model=MarcarDespesaPagaInput,
    handler=_marcar_despesa_paga,
    destrutiva=True,
    permissao_recurso="financeiro",
    permissao_acao="escrita",
)


# ── criar_parcelamento (DESTRUTIVA) ────────────────────────────────────────
class CriarParcelamentoInput(BaseModel):
    tipo: str = Field(description="'receber' (conta a receber) ou 'pagar' (despesa).")
    descricao: str = Field(min_length=2, max_length=300)
    valor_total: Decimal = Field(gt=0, description="Valor total do parcelamento.")
    parcelas: int = Field(ge=2, le=60, description="Número de parcelas (>=2).")
    primeira_data: str = Field(description="Data da 1ª parcela em ISO (YYYY-MM-DD).")
    cliente_id: Optional[int] = Field(
        default=None, gt=0, description="Obrigatório se tipo='receber'."
    )
    favorecido: Optional[str] = Field(
        default=None, max_length=200, description="Usado em tipo='pagar'."
    )


async def _criar_parcelamento(
    inp: CriarParcelamentoInput, *, db: Session, current_user: Usuario
) -> dict[str, Any]:
    from app.models.models import TipoConta
    from app.schemas.financeiro import ContaRapidoCreate

    try:
        venc = datetime.fromisoformat(inp.primeira_data).date()
    except ValueError:
        return {"error": "primeira_data inválida (use YYYY-MM-DD)", "code": "invalid_input"}

    tipo = inp.tipo.lower().strip()
    if tipo not in ("receber", "pagar"):
        return {"error": "tipo deve ser 'receber' ou 'pagar'", "code": "invalid_input"}

    if tipo == "receber":
        if not inp.cliente_id:
            return {"error": "cliente_id é obrigatório para receber", "code": "invalid_input"}
        try:
            dados = ContaRapidoCreate(
                tipo=TipoConta.RECEBER,
                cliente_id=inp.cliente_id,
                valor=inp.valor_total,
                vencimento=venc,
                descricao=inp.descricao.strip(),
                parcelas=inp.parcelas,
            )
            conta = financeiro_service.criar_conta_rapido(
                current_user.empresa_id, dados, current_user, db
            )
        except ValueError as e:
            return {"error": str(e), "code": "invalid_input"}
        db.commit()
        db.refresh(conta)
        return {
            "conta_id": conta.id,
            "tipo": "receber",
            "parcelas_criadas": inp.parcelas,
            "valor_total": float(inp.valor_total),
            "grupo_parcelas_id": conta.grupo_parcelas_id,
            "criado": True,
        }

    # tipo == "pagar" — cria N despesas vinculadas por grupo_parcelas_id
    from uuid import uuid4
    from dateutil.relativedelta import relativedelta

    grupo = str(uuid4())
    valor_parcela = (inp.valor_total / inp.parcelas).quantize(Decimal("0.01"))
    contas_ids: list[int] = []
    for n in range(inp.parcelas):
        data_n = venc + relativedelta(months=n)
        conta = financeiro_service.criar_despesa(
            empresa_id=current_user.empresa_id,
            dados={
                "descricao": f"{inp.descricao.strip()} ({n + 1}/{inp.parcelas})",
                "valor": valor_parcela,
                "data_vencimento": data_n,
                "favorecido": (inp.favorecido or "").strip() or None,
                "numero_parcela": n + 1,
                "total_parcelas": inp.parcelas,
                "grupo_parcelas_id": grupo,
            },
            db=db,
        )
        contas_ids.append(conta.id)
    db.commit()
    return {
        "tipo": "pagar",
        "parcelas_criadas": inp.parcelas,
        "valor_total": float(inp.valor_total),
        "valor_parcela": float(valor_parcela),
        "grupo_parcelas_id": grupo,
        "contas_ids": contas_ids,
        "criado": True,
    }


criar_parcelamento = ToolSpec(
    name="criar_parcelamento",
    description=(
        "Cria um parcelamento de receita ou despesa: divide o valor total em N parcelas "
        "mensais com datas sequenciais. Para 'receber' exige cliente_id. AÇÃO DESTRUTIVA — "
        "exige confirmação."
    ),
    input_model=CriarParcelamentoInput,
    handler=_criar_parcelamento,
    destrutiva=True,
    permissao_recurso="financeiro",
    permissao_acao="escrita",
)
