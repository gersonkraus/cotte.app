"""Service layer do Módulo Financeiro COTTE.

Responsável por toda a lógica de negócio de pagamentos, contas a receber
e dashboard. Os routers devem ser finos — apenas validar auth e delegar aqui.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import func, extract, case, and_, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.repositories.categoria_financeira_repository import (
    CategoriaFinanceiraRepository,
)
from app.models.models import CategoriaFinanceira
from app.schemas.financeiro import CategoriaFinanceiraCreate, CategoriaFinanceiraUpdate
from app.core.exceptions import HTTPException

from app.models.models import (
    Agendamento,
    ConfiguracaoFinanceira,
    ContaFinanceira,
    Empresa,
    FormaPagamentoConfig,
    HistoricoCobranca,
    Orcamento,
    OrigemRegistro,
    PagamentoFinanceiro,
    StatusAgendamento,
    StatusConta,
    StatusOrcamento,
    StatusPagamentoFinanceiro,
    TipoConta,
    TipoPagamento,
    TemplateNotificacao,
    Usuario,
)
from app.schemas.financeiro import (
    ContaFinanceiraCreate,
    ContaFinanceiraUpdate,
    PagamentoCreate,
)

logger = logging.getLogger(__name__)


# ── HELPERS ─────────────────────────────────────────────────────────────────


def _assert_empresa(obj_empresa_id: int, empresa_id: int) -> None:
    """Lança 403 se o objeto não pertence à empresa autenticada."""
    if obj_empresa_id != empresa_id:
        from fastapi import HTTPException as _HTTPException

        raise _HTTPException(status_code=403, detail="Acesso negado.")


def _calcular_estatisticas_caixa(empresa_id: int, db: Session) -> dict:
    """Função interna centralizadora para cálculo de todas as métricas de caixa."""
    from app.models.models import SaldoCaixaConfig, MovimentacaoCaixa
    from decimal import Decimal

    # 1. Total de Entradas (Pagamentos de Orçamentos e Contas a Receber)
    total_entradas_pagamentos = db.query(func.sum(PagamentoFinanceiro.valor)).outerjoin(
        Orcamento, PagamentoFinanceiro.orcamento_id == Orcamento.id
    ).outerjoin(
        ContaFinanceira, PagamentoFinanceiro.conta_id == ContaFinanceira.id
    ).filter(
        or_(
            Orcamento.empresa_id == empresa_id, ContaFinanceira.empresa_id == empresa_id
        ),
        PagamentoFinanceiro.status == StatusPagamentoFinanceiro.CONFIRMADO,
        or_(
            PagamentoFinanceiro.orcamento_id != None,
            ContaFinanceira.tipo == TipoConta.RECEBER,
        ),
    ).scalar() or Decimal("0")

    # 2. Total de Saídas (Pagamentos de Contas a Pagar)
    total_saidas_pagamentos = db.query(func.sum(PagamentoFinanceiro.valor)).join(
        ContaFinanceira, PagamentoFinanceiro.conta_id == ContaFinanceira.id
    ).filter(
        ContaFinanceira.empresa_id == empresa_id,
        ContaFinanceira.tipo == TipoConta.PAGAR,
        PagamentoFinanceiro.status == StatusPagamentoFinanceiro.CONFIRMADO,
    ).scalar() or Decimal("0")

    # 3. Movimentações Manuais de Caixa
    movs_entrada = db.query(func.sum(MovimentacaoCaixa.valor)).filter(
        MovimentacaoCaixa.empresa_id == empresa_id,
        MovimentacaoCaixa.tipo == "entrada",
        MovimentacaoCaixa.confirmado == True,
    ).scalar() or Decimal("0")

    movs_saida = db.query(func.sum(MovimentacaoCaixa.valor)).filter(
        MovimentacaoCaixa.empresa_id == empresa_id,
        MovimentacaoCaixa.tipo == "saida",
        MovimentacaoCaixa.confirmado == True,
    ).scalar() or Decimal("0")

    # 4. Movimentações de hoje
    movs_hoje = (
        db.query(MovimentacaoCaixa)
        .filter(
            MovimentacaoCaixa.empresa_id == empresa_id,
            MovimentacaoCaixa.criado_em
            >= datetime.combine(date.today(), datetime.min.time()),
        )
        .count()
    )

    # 5. Saldo Inicial
    saldo_cfg = db.query(SaldoCaixaConfig).filter_by(empresa_id=empresa_id).first()
    saldo_inicial = Decimal(str(saldo_cfg.saldo_inicial)) if saldo_cfg else Decimal("0")

    total_entradas = total_entradas_pagamentos + movs_entrada
    total_saidas = total_saidas_pagamentos + movs_saida
    saldo_atual = total_entradas - total_saidas + saldo_inicial

    return {
        "saldo_atual": saldo_atual,
        "total_entradas": total_entradas,
        "total_saidas": total_saidas,
        "movimentacoes_hoje": movs_hoje,
        "saldo_inicial": saldo_inicial,
        "ultima_atualizacao": datetime.now(),
    }


def calcular_saldo_caixa_kpi(empresa_id: int, db: Session) -> Decimal:
    """Calcula o saldo em caixa operacional (Entradas reais - Saídas reais + Saldo Inicial)."""
    stats = _calcular_estatisticas_caixa(empresa_id, db)
    return stats["saldo_atual"]


def _recalcular_status_conta(conta: ContaFinanceira) -> None:
    """Recalcula StatusConta com base nos pagamentos confirmados."""
    from decimal import Decimal

    pagamentos_confirmados = [
        p for p in conta.pagamentos if p.status == StatusPagamentoFinanceiro.CONFIRMADO
    ]
    total_pago = sum(p.valor for p in pagamentos_confirmados)
    conta.valor_pago = total_pago

    hoje = date.today()
    valor_conta = Decimal(str(conta.valor)) if conta.valor else Decimal("0")
    total_pago_decimal = Decimal(str(total_pago)) if total_pago else Decimal("0")

    if total_pago_decimal >= valor_conta:
        conta.status = StatusConta.PAGO
    elif total_pago_decimal > Decimal("0"):
        conta.status = StatusConta.PARCIAL
    elif conta.data_vencimento and conta.data_vencimento < hoje:
        conta.status = StatusConta.VENCIDO
    else:
        conta.status = StatusConta.PENDENTE


def _tem_agendamento_pendente(orcamento: Orcamento, db: Session) -> bool:
    """Retorna True se o orçamento tem agendamento(s) não concluído(s)."""
    ags = (
        db.query(Agendamento)
        .filter(
            Agendamento.orcamento_id == orcamento.id,
            Agendamento.status.notin_(
                [
                    StatusAgendamento.CONCLUIDO,
                    StatusAgendamento.CANCELADO,
                    StatusAgendamento.NAO_COMPARECEU,
                ]
            ),
        )
        .count()
    )
    return ags > 0


def _atualizar_status_orcamento(orcamento: Orcamento, db: Session) -> None:
    """Atualiza pagamento_recebido_em e status do orçamento quando quitado."""
    contas_receber = (
        db.query(ContaFinanceira)
        .filter(
            ContaFinanceira.orcamento_id == orcamento.id,
            ContaFinanceira.tipo == TipoConta.RECEBER,
            ContaFinanceira.status != StatusConta.CANCELADO,
        )
        .all()
    )
    if not contas_receber:
        return
    todas_pagas = all(c.status == StatusConta.PAGO for c in contas_receber)
    if todas_pagas:
        if not orcamento.pagamento_recebido_em:
            orcamento.pagamento_recebido_em = datetime.utcnow()
        # Automação de status
        empresa = db.query(Empresa).filter(Empresa.id == orcamento.empresa_id).first()
        if (
            empresa
            and empresa.auto_status_orcamento
            and orcamento.status != StatusOrcamento.CONCLUIDO
        ):
            if orcamento.status == StatusOrcamento.AGUARDANDO_PAGAMENTO:
                orcamento.status = StatusOrcamento.CONCLUIDO
            elif orcamento.status == StatusOrcamento.EM_EXECUCAO:
                if not _tem_agendamento_pendente(orcamento, db):
                    orcamento.status = StatusOrcamento.CONCLUIDO
            elif orcamento.status == StatusOrcamento.APROVADO:
                # Só conclui automaticamente se não houver agendamento ativo/pendente.
                if not _tem_agendamento_pendente(orcamento, db):
                    orcamento.status = StatusOrcamento.CONCLUIDO


# ── FORMAS DE PAGAMENTO ─────────────────────────────────────────────────────


def listar_formas_pagamento(empresa_id: int, db: Session) -> list[FormaPagamentoConfig]:
    return (
        db.query(FormaPagamentoConfig)
        .filter(
            FormaPagamentoConfig.empresa_id == empresa_id,
            FormaPagamentoConfig.ativo == True,
        )
        .order_by(FormaPagamentoConfig.ordem)
        .all()
    )


def criar_forma_pagamento(
    empresa_id: int, dados: dict, db: Session
) -> FormaPagamentoConfig:
    forma = FormaPagamentoConfig(empresa_id=empresa_id, **dados)
    db.add(forma)
    db.flush()
    return forma


def _seed_formas_padrao(empresa_id: int, db: Session) -> None:
    """Cria formas de pagamento padrão para empresa recém-criada (idempotente)."""
    existentes = db.query(FormaPagamentoConfig).filter_by(empresa_id=empresa_id).count()
    if existentes > 0:
        return
    padrao = [
        dict(
            nome="PIX",
            slug="pix",
            icone="🏦",
            cor="#00e5a0",
            gera_pix_qrcode=True,
            ordem=0,
            padrao=True,
            exigir_entrada_na_aprovacao=True,
            percentual_entrada=Decimal("100"),
            metodo_entrada="pix",
            percentual_saldo=Decimal("0"),
            descricao="Pagamento integral via PIX no momento da aprovação.",
        ),
        dict(
            nome="Dinheiro",
            slug="dinheiro",
            icone="💵",
            cor="#4caf50",
            ordem=1,
            exigir_entrada_na_aprovacao=True,
            percentual_entrada=Decimal("100"),
            metodo_entrada="dinheiro",
            percentual_saldo=Decimal("0"),
            descricao="Pagamento em dinheiro no ato.",
        ),
        dict(
            nome="Cartão de Crédito",
            slug="cartao_credito",
            icone="💳",
            cor="#2196f3",
            aceita_parcelamento=True,
            max_parcelas=12,
            taxa_percentual=Decimal("2.99"),
            ordem=2,
            percentual_entrada=Decimal("0"),
            metodo_entrada="cartao",
            descricao="Pagamento via cartão de crédito.",
        ),
        dict(
            nome="Cartão de Débito",
            slug="cartao_debito",
            icone="💳",
            cor="#03a9f4",
            ordem=3,
            percentual_entrada=Decimal("0"),
            metodo_entrada="cartao",
            descricao="Pagamento via cartão de débito.",
        ),
        dict(
            nome="TED/DOC",
            slug="ted_doc",
            icone="🏛️",
            cor="#9c27b0",
            ordem=4,
            exigir_entrada_na_aprovacao=True,
            percentual_entrada=Decimal("100"),
            metodo_entrada="transferencia",
            descricao="Transferência bancária TED ou DOC.",
        ),
        dict(
            nome="Boleto",
            slug="boleto",
            icone="📄",
            cor="#ff9800",
            ordem=5,
            percentual_entrada=Decimal("0"),
            metodo_entrada="boleto",
            descricao="Pagamento via boleto bancário.",
        ),
    ]
    for d in padrao:
        db.add(FormaPagamentoConfig(empresa_id=empresa_id, **d))


# ── CONTAS FINANCEIRAS ───────────────────────────────────────────────────────


def criar_conta(
    empresa_id: int, dados: ContaFinanceiraCreate, db: Session
) -> ContaFinanceira:
    conta = ContaFinanceira(
        empresa_id=empresa_id,
        orcamento_id=dados.orcamento_id,
        tipo=dados.tipo,
        descricao=dados.descricao,
        valor=dados.valor,
        valor_pago=Decimal("0"),
        data_vencimento=dados.data_vencimento,
        categoria=dados.categoria or dados.categoria_slug,
        origem=dados.origem,
        status=StatusConta.PENDENTE,
        # Campos de parcelamento manual
        numero_parcela=dados.numero_parcela,
        total_parcelas=dados.total_parcelas,
        grupo_parcelas_id=dados.grupo_parcelas_id,
        metodo_previsto=dados.metodo_previsto,
        tipo_lancamento=dados.tipo_lancamento,
        favorecido=dados.favorecido,
        categoria_slug=dados.categoria_slug,
    )
    db.add(conta)
    db.flush()
    return conta


def _build_busca_filter(termo: str, include_cliente: bool = False):
    """
    Monta cláusula OR para busca inteligente.
    include_cliente: True para A Receber (busca em cliente), False para Despesas.
    """
    from sqlalchemy import or_, cast, String, func
    from app.models.models import Cliente

    t = f"%{termo.strip()}%"
    conditions = [
        ContaFinanceira.descricao.ilike(t),
        func.coalesce(ContaFinanceira.favorecido, "").ilike(t),
        func.coalesce(ContaFinanceira.categoria, "").ilike(t),
        func.coalesce(ContaFinanceira.categoria_slug, "").ilike(t),
    ]

    # Buscar no nome do cliente (para A Receber)
    if include_cliente:
        conditions.append(Cliente.nome.ilike(t))

    # Detecção de valor numérico
    valor_limpo = termo.replace("R$", "").replace(".", "").replace(",", ".").strip()
    if valor_limpo and valor_limpo.replace(".", "").isdigit():
        conditions.append(cast(ContaFinanceira.valor, String).ilike(t))

    # Detecção de status
    status_validos = ["pendente", "pago", "vencido", "parcial", "cancelado"]
    if termo.strip().lower() in status_validos:
        conditions.append(ContaFinanceira.status == termo.strip().lower())

    return or_(*conditions)


def listar_contas(
    empresa_id: int,
    db: Session,
    id: Optional[int] = None,
    tipo: Optional[TipoConta] = None,
    status: Optional[StatusConta] = None,
    status_list: Optional[list] = None,
    orcamento_id: Optional[int] = None,
    busca: Optional[str] = None,
) -> list[ContaFinanceira]:
    from app.models.models import Cliente
    from sqlalchemy import and_

    q = db.query(ContaFinanceira).filter(ContaFinanceira.empresa_id == empresa_id)

    # Se houver busca e precisar buscar no cliente, fazer join explícito
    if busca:
        q = q.outerjoin(Orcamento).outerjoin(Cliente)

    # Eager load: evita N+1 ao acessar orcamento.cliente
    q = q.options(
        joinedload(ContaFinanceira.orcamento).joinedload(Orcamento.cliente),
    )

    if id:
        q = q.filter(ContaFinanceira.id == id)
    if tipo:
        q = q.filter(ContaFinanceira.tipo == tipo)
    if status_list:
        q = q.filter(ContaFinanceira.status.in_(status_list))
    elif status:
        q = q.filter(ContaFinanceira.status == status)
    if orcamento_id:
        q = q.filter(ContaFinanceira.orcamento_id == orcamento_id)
    if busca:
        q = q.filter(_build_busca_filter(busca, include_cliente=True))
    return q.order_by(ContaFinanceira.data_criacao.desc()).all()


def atualizar_conta(
    conta: ContaFinanceira, dados: ContaFinanceiraUpdate, db: Session
) -> ContaFinanceira:
    for campo, val in dados.model_dump(exclude_unset=True).items():
        setattr(conta, campo, val)
    db.flush()
    return conta


def excluir_conta(conta: ContaFinanceira, db: Session) -> None:
    """Exclui uma conta financeira, se não houver pagamentos associados."""
    # Verificar se há pagamentos confirmados ou pendentes
    if conta.pagamentos and len(conta.pagamentos) > 0:
        raise ValueError(
            "Não é possível excluir uma conta que possui pagamentos registrados. "
            "Estorne os pagamentos primeiro."
        )

    # Verificar se a conta está vinculada a um orçamento (apenas alerta)
    if conta.orcamento_id:
        logger.warning(
            f"Excluindo conta {conta.id} vinculada ao orçamento {conta.orcamento_id}"
        )

    db.delete(conta)
    db.flush()


def listar_inadimplentes(empresa_id: int, db: Session) -> list[ContaFinanceira]:
    """Contas a receber com data_vencimento vencida e saldo devedor > 0."""
    hoje = date.today()
    return (
        db.query(ContaFinanceira)
        .filter(
            ContaFinanceira.empresa_id == empresa_id,
            ContaFinanceira.tipo == TipoConta.RECEBER,
            ContaFinanceira.status.in_(
                [StatusConta.PENDENTE, StatusConta.PARCIAL, StatusConta.VENCIDO]
            ),
            ContaFinanceira.data_vencimento < hoje,
        )
        .order_by(ContaFinanceira.data_vencimento)
        .all()
    )


# ── PAGAMENTOS ───────────────────────────────────────────────────────────────


def _normalizar_chave_idempotencia(key: Optional[str]) -> Optional[str]:
    if not key:
        return None
    k = key.strip()
    return k[:128] if k else None


def _buscar_pagamento_por_idempotencia(
    empresa_id: int,
    key: Optional[str],
    db: Session,
) -> Optional[PagamentoFinanceiro]:
    key = _normalizar_chave_idempotencia(key)
    if not key:
        return None
    return (
        db.query(PagamentoFinanceiro)
        .filter(
            PagamentoFinanceiro.empresa_id == empresa_id,
            PagamentoFinanceiro.idempotency_key == key,
            PagamentoFinanceiro.status == StatusPagamentoFinanceiro.CONFIRMADO,
        )
        .first()
    )


def _saldo_aberto_conta(conta: ContaFinanceira) -> Decimal:
    """Saldo em aberto da conta (valor original − pagamentos confirmados)."""
    pagamentos_confirmados = [
        p
        for p in (conta.pagamentos or [])
        if p.status == StatusPagamentoFinanceiro.CONFIRMADO
    ]
    total_pago = sum(Decimal(str(p.valor)) for p in pagamentos_confirmados)
    valor_conta = Decimal(str(conta.valor)) if conta.valor else Decimal("0")
    return valor_conta - total_pago


def _selecionar_conta_recebimento_orcamento(
    orc: Orcamento,
    empresa_id: int,
    dados: PagamentoCreate,
    db: Session,
) -> ContaFinanceira:
    """Escolhe a parcela correta (ordem: número da parcela, vencimento, id) ou cria conta legada."""
    contas = (
        db.query(ContaFinanceira)
        .options(joinedload(ContaFinanceira.pagamentos))
        .filter(
            ContaFinanceira.orcamento_id == orc.id,
            ContaFinanceira.tipo == TipoConta.RECEBER,
            ContaFinanceira.status != StatusConta.CANCELADO,
        )
        .order_by(
            ContaFinanceira.numero_parcela.asc().nulls_last(),
            ContaFinanceira.data_vencimento.asc().nulls_last(),
            ContaFinanceira.id.asc(),
        )
        .all()
    )

    if not contas:
        conta = ContaFinanceira(
            empresa_id=empresa_id,
            orcamento_id=orc.id,
            tipo=TipoConta.RECEBER,
            descricao=f"Recebimento {orc.numero}",
            valor=Decimal(str(orc.total)),
            valor_pago=Decimal("0"),
            origem=OrigemRegistro.SISTEMA,
        )
        db.add(conta)
        db.flush()
        db.refresh(conta)
        return conta

    if dados.parcela_numero is not None:
        for c in contas:
            if c.numero_parcela == dados.parcela_numero:
                return c
        raise HTTPException(
            status_code=400,
            detail=(
                f"Parcela {dados.parcela_numero} não encontrada para este orçamento."
            ),
        )

    for c in contas:
        if _saldo_aberto_conta(c) > Decimal("0"):
            return c

    raise HTTPException(
        status_code=400,
        detail="Não há saldo em aberto em nenhuma parcela deste orçamento.",
    )


def registrar_pagamento(
    empresa_id: int,
    dados: PagamentoCreate,
    usuario: Usuario,
    db: Session,
) -> PagamentoFinanceiro:
    """Registra um pagamento e atualiza a conta vinculada ao orçamento."""

    idem = _normalizar_chave_idempotencia(getattr(dados, "idempotency_key", None))
    existente = _buscar_pagamento_por_idempotencia(empresa_id, idem, db)
    if existente:
        return existente

    # Busca o orçamento garantindo escopo da empresa
    orc = (
        db.query(Orcamento)
        .filter(Orcamento.id == dados.orcamento_id, Orcamento.empresa_id == empresa_id)
        .first()
    )
    if not orc:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")

    conta = _selecionar_conta_recebimento_orcamento(orc, empresa_id, dados, db)

    saldo = _saldo_aberto_conta(conta)
    valor = Decimal(str(dados.valor)).quantize(Decimal("0.01"))
    if valor > saldo:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Valor excede o saldo em aberto da parcela (máx. R$ {saldo:.2f})."
            ),
        )

    pagamento = PagamentoFinanceiro(
        empresa_id=empresa_id,
        orcamento_id=dados.orcamento_id,
        conta_id=conta.id,
        forma_pagamento_id=dados.forma_pagamento_id,
        valor=valor,
        tipo=dados.tipo,
        data_pagamento=dados.data_pagamento,
        confirmado_por_id=usuario.id,
        observacao=dados.observacao,
        comprovante_url=dados.comprovante_url,
        origem=dados.origem,
        parcela_numero=dados.parcela_numero,
        txid_pix=dados.txid_pix,
        idempotency_key=idem,
        status=StatusPagamentoFinanceiro.CONFIRMADO,
    )
    db.add(pagamento)
    db.flush()

    db.refresh(conta)
    _recalcular_status_conta(conta)

    if dados.tipo == TipoPagamento.SINAL:
        _criar_conta_saldo_se_necessario(orc, empresa_id, conta, valor, db)

    _atualizar_status_orcamento(orc, db)

    db.flush()
    return pagamento


def _criar_conta_saldo_se_necessario(
    orc: Orcamento,
    empresa_id: int,
    conta_principal: ContaFinanceira,
    valor_sinal: Decimal,
    db: Session,
) -> None:
    """Após registrar sinal, cria conta a receber do saldo devedor."""
    saldo = Decimal(str(orc.total)) - valor_sinal
    if saldo <= 0:
        return
    # Verifica se já existe conta de saldo
    ja_existe = (
        db.query(ContaFinanceira)
        .filter(
            ContaFinanceira.orcamento_id == orc.id,
            ContaFinanceira.descricao.like("%Saldo%"),
            ContaFinanceira.tipo == TipoConta.RECEBER,
        )
        .count()
    )
    if ja_existe:
        return
    conta_saldo = ContaFinanceira(
        empresa_id=empresa_id,
        orcamento_id=orc.id,
        tipo=TipoConta.RECEBER,
        descricao=f"Saldo {orc.numero}",
        valor=saldo,
        valor_pago=Decimal("0"),
        origem=OrigemRegistro.SISTEMA,
    )
    db.add(conta_saldo)
    db.flush()


def estornar_pagamento(
    pagamento_id: int,
    empresa_id: int,
    motivo: Optional[str],
    db: Session,
) -> PagamentoFinanceiro:
    # Pagamento pode não ter orcamento_id (avulso). Valida empresa_id pela conta.
    pagamento = (
        db.query(PagamentoFinanceiro)
        .outerjoin(Orcamento, PagamentoFinanceiro.orcamento_id == Orcamento.id)
        .filter(PagamentoFinanceiro.id == pagamento_id)
        .first()
    )
    if not pagamento:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Pagamento não encontrado.")

    # Validação de empresa: pelo orçamento OU pela conta
    empresa_ref = None
    if pagamento.orcamento_id and pagamento.orcamento:
        empresa_ref = pagamento.orcamento.empresa_id
    elif pagamento.conta_id and pagamento.conta:
        empresa_ref = pagamento.conta.empresa_id
    if empresa_ref is None or empresa_ref != empresa_id:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Pagamento não encontrado.")
    if pagamento.status == StatusPagamentoFinanceiro.ESTORNADO:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Pagamento já estornado.")

    pagamento.status = StatusPagamentoFinanceiro.ESTORNADO
    if motivo:
        obs_atual = pagamento.observacao or ""
        pagamento.observacao = f"{obs_atual} [ESTORNO: {motivo}]".strip()

    if pagamento.conta_id:
        conta = db.get(ContaFinanceira, pagamento.conta_id)
        if conta:
            db.refresh(conta)
            _recalcular_status_conta(conta)

    # Desfaz pagamento_recebido_em se o orçamento não está mais quitado
    if pagamento.orcamento_id:
        orc = db.get(Orcamento, pagamento.orcamento_id)
        if orc and orc.pagamento_recebido_em:
            contas = [c for c in orc.contas_financeiras if c.tipo == TipoConta.RECEBER]
            todas_pagas = all(c.status == StatusConta.PAGO for c in contas)
            if not todas_pagas:
                orc.pagamento_recebido_em = None

    db.flush()
    return pagamento


def listar_pagamentos(
    empresa_id: int,
    db: Session,
    orcamento_id: Optional[int] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    cliente_nome: Optional[str] = None,
    apenas_confirmados: bool = True,
    limit: int = 100,
    offset: int = 0,
) -> list[PagamentoFinanceiro]:
    from app.models.models import Cliente, ContaFinanceira
    from sqlalchemy import or_

    q = (
        db.query(PagamentoFinanceiro)
        # outerjoin para incluir pagamentos de despesas (conta_id) sem orcamento_id
        .outerjoin(Orcamento, PagamentoFinanceiro.orcamento_id == Orcamento.id)
        .outerjoin(ContaFinanceira, PagamentoFinanceiro.conta_id == ContaFinanceira.id)
        .filter(
            or_(
                Orcamento.empresa_id == empresa_id,
                ContaFinanceira.empresa_id == empresa_id,
            )
        )
        # Eager load: evita N+1 (1 query em vez de 3 por pagamento)
        .options(
            selectinload(PagamentoFinanceiro.forma_pagamento_config),
            selectinload(PagamentoFinanceiro.confirmado_por),
            joinedload(PagamentoFinanceiro.orcamento).joinedload(Orcamento.cliente),
        )
    )
    if orcamento_id:
        q = q.filter(PagamentoFinanceiro.orcamento_id == orcamento_id)
    if apenas_confirmados:
        q = q.filter(PagamentoFinanceiro.status == StatusPagamentoFinanceiro.CONFIRMADO)
    if data_inicio:
        q = q.filter(PagamentoFinanceiro.data_pagamento >= data_inicio)
    if data_fim:
        q = q.filter(PagamentoFinanceiro.data_pagamento <= data_fim)
    if cliente_nome:
        q = q.outerjoin(Cliente, Orcamento.cliente_id == Cliente.id).filter(
            Cliente.nome.ilike(f"%{cliente_nome}%")
        )
    return (
        q.order_by(PagamentoFinanceiro.data_pagamento.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


# ── DASHBOARD ────────────────────────────────────────────────────────────────


def calcular_resumo(empresa_id: int, db: Session, busca: Optional[str] = None) -> dict:
    """Calcula KPIs e dados de gráfico para o dashboard financeiro, com filtro opcional por cliente."""
    from app.models.models import Cliente

    hoje = date.today()
    inicio_mes = hoje.replace(day=1)

    # Se houver busca, obter lista de IDs de clientes que batem
    cliente_ids = []
    if busca:
        t = f"%{busca.strip()}%"
        cliente_ids = [
            c.id for c in db.query(Cliente.id).filter(Cliente.nome.ilike(t)).all()
        ]
        if not cliente_ids:
            cliente_ids = [-1]  # Nenhum cliente encontrado, retornar zeros

    # Total recebido no mês corrente
    total_mes = db.query(func.sum(PagamentoFinanceiro.valor)).join(
        Orcamento, PagamentoFinanceiro.orcamento_id == Orcamento.id
    ).filter(
        Orcamento.empresa_id == empresa_id,
        PagamentoFinanceiro.status == StatusPagamentoFinanceiro.CONFIRMADO,
        PagamentoFinanceiro.data_pagamento >= inicio_mes,
        Orcamento.cliente_id.in_(cliente_ids) if cliente_ids else True,
    ).scalar() or Decimal("0")

    # Total a receber (pendente + parcial)
    q_receber = db.query(
        func.sum(ContaFinanceira.valor - ContaFinanceira.valor_pago)
    ).filter(
        ContaFinanceira.empresa_id == empresa_id,
        ContaFinanceira.tipo == TipoConta.RECEBER,
        ContaFinanceira.status.in_([StatusConta.PENDENTE, StatusConta.PARCIAL]),
    )
    if cliente_ids:
        q_receber = q_receber.join(Orcamento).filter(
            Orcamento.cliente_id.in_(cliente_ids)
        )
    total_a_receber = q_receber.scalar() or Decimal("0")

    # Total vencido
    q_vencido = db.query(
        func.sum(ContaFinanceira.valor - ContaFinanceira.valor_pago)
    ).filter(
        ContaFinanceira.empresa_id == empresa_id,
        ContaFinanceira.tipo == TipoConta.RECEBER,
        ContaFinanceira.status == StatusConta.VENCIDO,
    )
    if cliente_ids:
        q_vencido = q_vencido.join(Orcamento).filter(
            Orcamento.cliente_id.in_(cliente_ids)
        )
    total_vencido = q_vencido.scalar() or Decimal("0")

    # Ticket médio (orçamentos aprovados)
    q_ticket = db.query(func.avg(Orcamento.total)).filter(
        Orcamento.empresa_id == empresa_id,
        Orcamento.status == StatusOrcamento.APROVADO,
    )
    if cliente_ids:
        q_ticket = q_ticket.filter(Orcamento.cliente_id.in_(cliente_ids))
    ticket = q_ticket.scalar() or Decimal("0")

    # Receita dos últimos 6 meses
    receita_por_mes = _receita_ultimos_meses(empresa_id, db, meses=6)

    # Receita por forma de pagamento
    receita_por_meio = _receita_por_meio(empresa_id, db)

    # Total a pagar (despesas pendentes)
    total_a_pagar = db.query(
        func.sum(ContaFinanceira.valor - ContaFinanceira.valor_pago)
    ).filter(
        ContaFinanceira.empresa_id == empresa_id,
        ContaFinanceira.tipo == TipoConta.PAGAR,
        ContaFinanceira.status.in_([StatusConta.PENDENTE, StatusConta.PARCIAL]),
    ).scalar() or Decimal("0")

    # Contas vencendo hoje
    # Vencendo hoje
    q_vencendo_hoje = db.query(func.count(ContaFinanceira.id)).filter(
        ContaFinanceira.empresa_id == empresa_id,
        ContaFinanceira.data_vencimento == hoje,
        ContaFinanceira.status.in_([StatusConta.PENDENTE, StatusConta.PARCIAL]),
    )
    if cliente_ids:
        q_vencendo_hoje = q_vencendo_hoje.join(Orcamento).filter(
            Orcamento.cliente_id.in_(cliente_ids)
        )
    vencendo_hoje = q_vencendo_hoje.scalar() or 0

    # Contas em atraso (vencidas)
    q_em_atraso = db.query(func.count(ContaFinanceira.id)).filter(
        ContaFinanceira.empresa_id == empresa_id,
        ContaFinanceira.status == StatusConta.VENCIDO,
    )
    if cliente_ids:
        q_em_atraso = q_em_atraso.join(Orcamento).filter(
            Orcamento.cliente_id.in_(cliente_ids)
        )
    em_atraso = q_em_atraso.scalar() or 0

    # Previsão 7 e 30 dias
    def _previsao(dias: int) -> dict:
        fim = hoje + timedelta(days=dias)
        ent = db.query(
            func.sum(ContaFinanceira.valor - ContaFinanceira.valor_pago)
        ).filter(
            ContaFinanceira.empresa_id == empresa_id,
            ContaFinanceira.tipo == TipoConta.RECEBER,
            ContaFinanceira.status.in_([StatusConta.PENDENTE, StatusConta.PARCIAL]),
            ContaFinanceira.data_vencimento >= hoje,
            ContaFinanceira.data_vencimento <= fim,
        ).scalar() or Decimal("0")
        sai = db.query(
            func.sum(ContaFinanceira.valor - ContaFinanceira.valor_pago)
        ).filter(
            ContaFinanceira.empresa_id == empresa_id,
            ContaFinanceira.tipo == TipoConta.PAGAR,
            ContaFinanceira.status.in_([StatusConta.PENDENTE, StatusConta.PARCIAL]),
            ContaFinanceira.data_vencimento >= hoje,
            ContaFinanceira.data_vencimento <= fim,
        ).scalar() or Decimal("0")
        e = Decimal(str(ent))
        s = Decimal(str(sai))
        return {"entradas": e, "saidas": s, "saldo": e - s}

    # Saldo em caixa do KPI do dashboard (fonte única de verdade)
    saldo_caixa = calcular_saldo_caixa_kpi(empresa_id, db)

    return {
        "total_recebido_mes": Decimal(str(total_mes)),
        "total_a_receber": Decimal(str(total_a_receber)),
        "total_vencido": Decimal(str(total_vencido)),
        "ticket_medio": Decimal(str(ticket)),
        "receita_por_mes": receita_por_mes,
        "receita_por_meio": receita_por_meio,
        "total_a_pagar": Decimal(str(total_a_pagar)),
        "vencendo_hoje": int(vencendo_hoje),
        "em_atraso": int(em_atraso),
        "previsao_7_dias": _previsao(7),
        "previsao_30_dias": _previsao(30),
        "saldo_caixa": saldo_caixa,
    }


def _receita_ultimos_meses(empresa_id: int, db: Session, meses: int = 6) -> list[dict]:
    """Receita dos últimos N meses — 1 query com GROUP BY em vez de N queries."""
    hoje = date.today()
    meses_pt = [
        "Jan",
        "Fev",
        "Mar",
        "Abr",
        "Mai",
        "Jun",
        "Jul",
        "Ago",
        "Set",
        "Out",
        "Nov",
        "Dez",
    ]

    # Calcula o primeiro mês a incluir
    inicio = hoje.replace(day=1)
    for _ in range(meses - 1):
        inicio = (inicio - timedelta(days=1)).replace(day=1)

    # Única query com GROUP BY ano/mês
    rows = (
        db.query(
            extract("year", PagamentoFinanceiro.data_pagamento).label("ano"),
            extract("month", PagamentoFinanceiro.data_pagamento).label("mes"),
            func.sum(PagamentoFinanceiro.valor).label("total"),
        )
        .join(Orcamento, PagamentoFinanceiro.orcamento_id == Orcamento.id)
        .filter(
            Orcamento.empresa_id == empresa_id,
            PagamentoFinanceiro.status == StatusPagamentoFinanceiro.CONFIRMADO,
            PagamentoFinanceiro.data_pagamento >= inicio,
        )
        .group_by(
            extract("year", PagamentoFinanceiro.data_pagamento),
            extract("month", PagamentoFinanceiro.data_pagamento),
        )
        .all()
    )

    # Indexa por (ano, mês) para lookup O(1)
    mapa = {(int(r.ano), int(r.mes)): Decimal(str(r.total)) for r in rows}

    resultado = []
    ref = inicio
    for _ in range(meses):
        total = mapa.get((ref.year, ref.month), Decimal("0"))
        resultado.append(
            {
                "mes": ref.strftime("%Y-%m"),
                "label": f"{meses_pt[ref.month - 1]}/{str(ref.year)[2:]}",
                "total": total,
            }
        )
        # Avança para o próximo mês
        ref = (ref.replace(day=28) + timedelta(days=4)).replace(day=1)
    return resultado


def _receita_por_meio(empresa_id: int, db: Session) -> list[dict]:
    rows = (
        db.query(
            FormaPagamentoConfig.nome,
            FormaPagamentoConfig.icone,
            func.sum(PagamentoFinanceiro.valor).label("total"),
        )
        .join(
            PagamentoFinanceiro,
            PagamentoFinanceiro.forma_pagamento_id == FormaPagamentoConfig.id,
        )
        .join(Orcamento, PagamentoFinanceiro.orcamento_id == Orcamento.id)
        .filter(
            Orcamento.empresa_id == empresa_id,
            PagamentoFinanceiro.status == StatusPagamentoFinanceiro.CONFIRMADO,
        )
        .group_by(FormaPagamentoConfig.nome, FormaPagamentoConfig.icone)
        .all()
    )

    # Sem forma de pagamento vinculada
    sem_forma = db.query(func.sum(PagamentoFinanceiro.valor)).join(
        Orcamento, PagamentoFinanceiro.orcamento_id == Orcamento.id
    ).filter(
        Orcamento.empresa_id == empresa_id,
        PagamentoFinanceiro.status == StatusPagamentoFinanceiro.CONFIRMADO,
        PagamentoFinanceiro.forma_pagamento_id.is_(None),
    ).scalar() or Decimal("0")

    dados = [
        {"meio": r.nome, "icone": r.icone, "total": Decimal(str(r.total))} for r in rows
    ]
    if sem_forma > 0:
        dados.append(
            {"meio": "Outros", "icone": "💰", "total": Decimal(str(sem_forma))}
        )

    grand_total = sum(d["total"] for d in dados) or Decimal("1")
    for d in dados:
        d["percentual"] = float(d["total"] / grand_total * 100)

    return dados


# ── TEMPLATES DE NOTIFICAÇÃO ─────────────────────────────────────────────────

_TEMPLATES_PADRAO = {
    "cobranca_saldo": (
        "Olá {nome_cliente}! 👋\n\n"
        "Seu orçamento *{numero_orcamento}* tem um saldo pendente de *R$ {saldo_devedor}*.\n"
        "Data de vencimento: *{data_vencimento}*\n\n"
        "Chave PIX: `{chave_pix}`\n\n"
        "Qualquer dúvida, estamos à disposição. 🙂\n— {nome_empresa}"
    ),
    "confirmacao_pagamento": (
        "✅ Pagamento confirmado!\n\n"
        "Olá *{nome_cliente}*, recebemos seu pagamento de *R$ {valor}* "
        "referente ao orçamento *{numero_orcamento}*.\n\n"
        "Obrigado pela confiança! 🙏\n— {nome_empresa}"
    ),
}


# ── REGRAS DE PAGAMENTO (f002) ───────────────────────────────────────────────


def set_forma_padrao(
    empresa_id: int, forma_id: int, db: Session
) -> FormaPagamentoConfig:
    """Remove padrao=True de todas as formas da empresa e seta na forma_id."""
    db.query(FormaPagamentoConfig).filter(
        FormaPagamentoConfig.empresa_id == empresa_id,
        FormaPagamentoConfig.padrao == True,
    ).update({"padrao": False})
    forma = (
        db.query(FormaPagamentoConfig)
        .filter(
            FormaPagamentoConfig.id == forma_id,
            FormaPagamentoConfig.empresa_id == empresa_id,
        )
        .first()
    )
    if not forma:
        raise ValueError("Forma de pagamento não encontrada")
    forma.padrao = True
    db.flush()
    return forma


def regenerar_pix_orcamento(orc: Orcamento, valor: Decimal | None = None) -> None:
    """Regenera pix_payload e pix_qrcode no orçamento.

    Usa `valor` se fornecido; caso contrário usa valor_sinal_pix ou total.
    Não faz nada se o orçamento não tiver pix_chave.
    """
    if not orc.pix_chave:
        return
    try:
        from app.services.pix_service import gerar_payload_pix, gerar_qrcode_pix
        from datetime import datetime as _dt

        titular = orc.pix_titular or ""
        valor_efetivo = (
            valor
            if valor is not None
            else (
                orc.valor_sinal_pix
                if orc.valor_sinal_pix
                else (orc.total or Decimal("0"))
            )
        )
        orc.pix_payload = gerar_payload_pix(orc.pix_chave, titular, valor=valor_efetivo)
        orc.pix_qrcode = gerar_qrcode_pix(orc.pix_chave, titular, valor=valor_efetivo)
        orc.pix_informado_em = _dt.utcnow()
    except Exception as e:
        logger.warning("Falha ao regenerar PIX: %s", e)


def aplicar_regra_no_orcamento(orc: Orcamento, db: Session) -> None:
    """Aplica snapshot da FormaPagamentoConfig no orçamento.

    - Lê os campos da forma selecionada (regra_pagamento_id)
    - Faz snapshot: nome, percentuais e métodos
    - Calcula valor_sinal_pix se a entrada for via PIX
    - Regenera pix_payload / pix_qrcode se necessário
    """
    if not orc.regra_pagamento_id:
        return
    forma = (
        db.query(FormaPagamentoConfig)
        .filter(
            FormaPagamentoConfig.id == orc.regra_pagamento_id,
            FormaPagamentoConfig.ativo == True,
        )
        .first()
    )
    if not forma:
        orc.regra_pagamento_id = None
        return

    # Snapshot
    orc.regra_pagamento_nome = forma.nome
    orc.regra_entrada_percentual = forma.percentual_entrada or Decimal("0")
    orc.regra_entrada_metodo = forma.metodo_entrada
    orc.regra_saldo_percentual = forma.percentual_saldo or Decimal("0")
    orc.regra_saldo_metodo = forma.metodo_saldo

    # Calcular valor_sinal_pix quando entrada for via PIX
    total = Decimal(str(orc.total or 0))
    pct_entrada = Decimal(str(orc.regra_entrada_percentual or 0))

    if pct_entrada > 0 and forma.metodo_entrada == "pix" and total > 0:
        valor_entrada = (total * pct_entrada / Decimal("100")).quantize(Decimal("0.01"))
        orc.valor_sinal_pix = valor_entrada
        regenerar_pix_orcamento(orc, valor=valor_entrada)
    elif pct_entrada == 0:
        # Sem entrada PIX — limpar sinal se era de regra anterior
        orc.valor_sinal_pix = None


def criar_contas_receber_aprovacao(
    orc: Orcamento,
    empresa_id: int,
    db: Session,
) -> None:
    """Cria Contas a Receber ao aprovar orçamento. Idempotente.

    - Com regra de pagamento: gera entrada + N parcelas do saldo
    - Sem regra: cria conta integral
    - Guard contas_receber_geradas_em garante idempotência
    """
    if orc.contas_receber_geradas_em is not None:
        return  # Idempotência: já gerado

    hoje = date.today()
    total = Decimal(str(orc.total or 0))
    if total <= 0:
        return

    grupo_id = str(uuid4())
    numero = orc.numero or f"#{orc.id}"
    contas: list[ContaFinanceira] = []

    pct_entrada = Decimal(str(orc.regra_entrada_percentual or 0))
    pct_saldo = Decimal(str(orc.regra_saldo_percentual or 0))
    metodo_ent = orc.regra_entrada_metodo
    metodo_sal = orc.regra_saldo_metodo

    # Buscar dados da forma de pagamento para parcelamento
    dias_saldo = None
    n_parcelas = 1
    intervalo = 30
    if orc.regra_pagamento_id:
        forma = (
            db.query(FormaPagamentoConfig).filter_by(id=orc.regra_pagamento_id).first()
        )
        if forma:
            dias_saldo = forma.dias_vencimento_saldo
            n_parcelas = max(1, forma.numero_parcelas_saldo or 1)
            intervalo = max(1, forma.intervalo_dias_parcela or 30)

    # 1. Entrada (se configurada)
    if pct_entrada > 0:
        valor_ent = (total * pct_entrada / Decimal("100")).quantize(Decimal("0.01"))
        contas.append(
            ContaFinanceira(
                descricao=f"Entrada — {numero}",
                valor=valor_ent,
                tipo_lancamento="entrada",
                numero_parcela=1,
                total_parcelas=1,
                data_vencimento=hoje,
                metodo_previsto=metodo_ent,
                grupo_parcelas_id=grupo_id,
            )
        )

    # 2. Saldo parcelado em N parcelas
    if pct_saldo > 0:
        val_saldo = (total * pct_saldo / Decimal("100")).quantize(Decimal("0.01"))
        val_parcela = (val_saldo / n_parcelas).quantize(Decimal("0.01"))
        for i in range(n_parcelas):
            offset = (dias_saldo or 0) + (i * intervalo)
            if n_parcelas == 1:
                label = "Pagamento final"
            else:
                label = f"{i + 1}ª parcela"
            contas.append(
                ContaFinanceira(
                    descricao=f"{label} — {numero}",
                    valor=val_parcela,
                    tipo_lancamento="saldo",
                    numero_parcela=i + 1,
                    total_parcelas=n_parcelas,
                    data_vencimento=hoje + timedelta(days=offset),
                    metodo_previsto=metodo_sal,
                    grupo_parcelas_id=grupo_id,
                )
            )

    # 3. Sem regra → integral
    if not contas:
        contas.append(
            ContaFinanceira(
                descricao=f"Pagamento — {numero}",
                valor=total,
                tipo_lancamento="integral",
                numero_parcela=1,
                total_parcelas=1,
                grupo_parcelas_id=grupo_id,
            )
        )

    for c in contas:
        c.empresa_id = empresa_id
        c.orcamento_id = orc.id
        c.tipo = TipoConta.RECEBER
        c.origem = OrigemRegistro.SISTEMA
        c.valor_pago = Decimal("0")
        c.status = StatusConta.PENDENTE
        db.add(c)

    orc.contas_receber_geradas_em = datetime.now(timezone.utc)
    db.flush()


# ── DESPESAS (Contas a Pagar) ─────────────────────────────────────────────────


def criar_despesa(empresa_id: int, dados: dict, db: Session) -> ContaFinanceira:
    """Cria uma conta a pagar (despesa) manualmente."""
    conta = ContaFinanceira(
        empresa_id=empresa_id,
        tipo=TipoConta.PAGAR,
        origem=OrigemRegistro.MANUAL,
        tipo_lancamento=dados.get("tipo_lancamento") or "despesa",
        valor_pago=Decimal("0"),
        status=StatusConta.PENDENTE,
        descricao=dados.get("descricao", ""),
        valor=Decimal(str(dados.get("valor", 0))),
        favorecido=dados.get("favorecido"),
        categoria_slug=dados.get("categoria_slug"),
        data_vencimento=dados.get("data_vencimento"),
        data_competencia=dados.get("data_competencia"),
        categoria=dados.get("categoria_slug"),
        numero_parcela=dados.get("numero_parcela"),
        total_parcelas=dados.get("total_parcelas"),
        grupo_parcelas_id=dados.get("grupo_parcelas_id"),
    )
    db.add(conta)
    db.flush()
    return conta


def listar_despesas(
    empresa_id: int,
    db: Session,
    id: Optional[int] = None,
    status: Optional[StatusConta] = None,
    status_list: Optional[list] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    categoria_slug: Optional[str] = None,
    busca: Optional[str] = None,
) -> list[ContaFinanceira]:
    q = db.query(ContaFinanceira).filter(
        ContaFinanceira.empresa_id == empresa_id,
        ContaFinanceira.tipo == TipoConta.PAGAR,
    )
    if id:
        q = q.filter(ContaFinanceira.id == id)
    if status_list:
        q = q.filter(ContaFinanceira.status.in_(status_list))
    elif status:
        q = q.filter(ContaFinanceira.status == status)
    if data_inicio:
        q = q.filter(ContaFinanceira.data_vencimento >= data_inicio)
    if data_fim:
        q = q.filter(ContaFinanceira.data_vencimento <= data_fim)
    if categoria_slug:
        q = q.filter(ContaFinanceira.categoria_slug == categoria_slug)
    if busca:
        q = q.filter(_build_busca_filter(busca, include_cliente=False))
    return q.order_by(ContaFinanceira.data_vencimento).all()


def registrar_pagamento_despesa(
    conta_id: int,
    empresa_id: int,
    usuario: Usuario,
    db: Session,
    valor: Optional[Decimal] = None,
    forma_pagamento_id: Optional[int] = None,
    observacao: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> PagamentoFinanceiro:
    from decimal import Decimal as _Dec

    idem = _normalizar_chave_idempotencia(idempotency_key)
    existente = _buscar_pagamento_por_idempotencia(empresa_id, idem, db)
    if existente:
        return existente

    conta = (
        db.query(ContaFinanceira)
        .options(joinedload(ContaFinanceira.pagamentos))
        .filter_by(id=conta_id, empresa_id=empresa_id, tipo=TipoConta.PAGAR)
        .first()
    )
    if not conta:
        raise HTTPException(status_code=404, detail="Despesa não encontrada.")

    saldo_devedor = _saldo_aberto_conta(conta)
    if saldo_devedor <= _Dec("0"):
        raise HTTPException(status_code=400, detail="Despesa já quitada.")

    valor_efetivo = (
        _Dec(str(valor)).quantize(_Dec("0.01")) if valor is not None else saldo_devedor
    )

    if valor_efetivo > saldo_devedor:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Valor do pagamento (R$ {valor_efetivo:.2f}) excede o saldo devedor "
                f"(R$ {saldo_devedor:.2f})"
            ),
        )

    if valor_efetivo <= _Dec("0"):
        raise HTTPException(
            status_code=400, detail="Valor do pagamento deve ser maior que zero"
        )

    pagamento = PagamentoFinanceiro(
        empresa_id=empresa_id,
        conta_id=conta.id,
        forma_pagamento_id=forma_pagamento_id,
        valor=valor_efetivo,
        tipo=TipoPagamento.QUITACAO,
        data_pagamento=date.today(),
        confirmado_por_id=usuario.id,
        observacao=observacao,
        origem=OrigemRegistro.MANUAL,
        idempotency_key=idem,
        status=StatusPagamentoFinanceiro.CONFIRMADO,
    )
    db.add(pagamento)
    db.flush()
    db.refresh(conta)
    _recalcular_status_conta(conta)
    db.flush()
    return pagamento


def registrar_pagamento_conta_receber(
    conta_id: int,
    empresa_id: int,
    usuario: Usuario,
    db: Session,
    valor: Optional[Decimal] = None,
    forma_pagamento_id: Optional[int] = None,
    observacao: Optional[str] = None,
    data_pagamento: Optional[date] = None,
    idempotency_key: Optional[str] = None,
) -> PagamentoFinanceiro:
    """Registra um pagamento para uma conta a receber (avulsa ou vinculada a orçamento)."""
    idem = _normalizar_chave_idempotencia(idempotency_key)
    existente = _buscar_pagamento_por_idempotencia(empresa_id, idem, db)
    if existente:
        return existente

    conta = (
        db.query(ContaFinanceira)
        .options(joinedload(ContaFinanceira.pagamentos))
        .filter_by(id=conta_id, empresa_id=empresa_id, tipo=TipoConta.RECEBER)
        .first()
    )
    if not conta:
        raise HTTPException(status_code=404, detail="Conta a receber não encontrada.")

    saldo_devedor = _saldo_aberto_conta(conta)
    if saldo_devedor <= Decimal("0"):
        raise HTTPException(status_code=400, detail="Conta já quitada.")

    valor_efetivo = (
        Decimal(str(valor)).quantize(Decimal("0.01"))
        if valor is not None
        else saldo_devedor
    )

    if valor_efetivo > saldo_devedor:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Valor do pagamento (R$ {valor_efetivo:.2f}) excede o saldo em aberto "
                f"(R$ {saldo_devedor:.2f})"
            ),
        )
    if valor_efetivo <= Decimal("0"):
        raise HTTPException(
            status_code=400, detail="Valor do pagamento deve ser maior que zero"
        )

    pagamento = PagamentoFinanceiro(
        empresa_id=empresa_id,
        conta_id=conta.id,
        orcamento_id=conta.orcamento_id,
        forma_pagamento_id=forma_pagamento_id,
        valor=valor_efetivo,
        tipo=TipoPagamento.QUITACAO,
        data_pagamento=data_pagamento or date.today(),
        confirmado_por_id=usuario.id,
        observacao=observacao,
        origem=OrigemRegistro.MANUAL,
        idempotency_key=idem,
        status=StatusPagamentoFinanceiro.CONFIRMADO,
    )
    db.add(pagamento)
    db.flush()
    db.refresh(conta)
    _recalcular_status_conta(conta)
    if conta.orcamento_id:
        orc = db.get(Orcamento, conta.orcamento_id)
        if orc:
            _atualizar_status_orcamento(orc, db)
    db.flush()
    return pagamento


# ── COBRANÇA VIA WHATSAPP ─────────────────────────────────────────────────────


async def cobrar_via_whatsapp(conta_id: int, empresa_id: int, db: Session) -> dict:
    """Envia cobrança WhatsApp ao cliente da conta e salva histórico."""
    conta = (
        db.query(ContaFinanceira)
        .options(joinedload(ContaFinanceira.orcamento).joinedload(Orcamento.cliente))
        .filter_by(id=conta_id, empresa_id=empresa_id)
        .first()
    )
    if not conta:
        return {"ok": False, "erro": "Conta não encontrada."}
    if conta.status in (StatusConta.PAGO, StatusConta.CANCELADO):
        return {"ok": False, "erro": f"Conta já está {conta.status.value}."}
    if conta.tipo != TipoConta.RECEBER:
        return {"ok": False, "erro": "Cobrança apenas para contas a receber."}

    # Resolver telefone do cliente
    telefone = None
    nome_cliente = "Cliente"
    numero_orc = conta.descricao
    if conta.orcamento and conta.orcamento.cliente:
        telefone = conta.orcamento.cliente.telefone
        nome_cliente = conta.orcamento.cliente.nome
    if conta.orcamento:
        numero_orc = conta.orcamento.numero or numero_orc

    if not telefone:
        return {"ok": False, "erro": "Telefone do cliente não cadastrado."}

    # Buscar template de cobrança
    tmpl = (
        db.query(TemplateNotificacao)
        .filter_by(empresa_id=empresa_id, tipo="cobranca_saldo", ativo=True)
        .first()
    )
    corpo_tmpl = tmpl.corpo if tmpl else _TEMPLATES_PADRAO["cobranca_saldo"]

    saldo = (conta.valor or Decimal("0")) - (conta.valor_pago or Decimal("0"))
    venc = conta.data_vencimento.strftime("%d/%m/%Y") if conta.data_vencimento else "—"

    # Buscar empresa para nome e PIX
    from app.models.models import Empresa

    empresa = db.get(Empresa, empresa_id)
    nome_empresa = empresa.nome if empresa else ""
    chave_pix = (empresa.pix_chave_padrao or "") if empresa else ""

    mensagem = (
        corpo_tmpl.replace("{nome_cliente}", nome_cliente)
        .replace("{numero_orcamento}", numero_orc)
        .replace("{saldo_devedor}", f"{saldo:.2f}".replace(".", ","))
        .replace("{data_vencimento}", venc)
        .replace("{chave_pix}", chave_pix)
        .replace("{nome_empresa}", nome_empresa)
    )

    # Enviar via WhatsApp
    ok = False
    erro = None
    try:
        from app.services.whatsapp_service import send_whatsapp_message

        ok = await send_whatsapp_message(
            to_phone=telefone,
            message=mensagem,
            context={"empresa_id": empresa_id},
        )
        if not ok:
            erro = "Falha ao enviar (provider retornou false)."
    except Exception as exc:
        erro = str(exc)
        logger.error("cobrar_via_whatsapp: %s", exc)

    # Salvar histórico
    hist = HistoricoCobranca(
        empresa_id=empresa_id,
        conta_id=conta.id,
        canal="whatsapp",
        destinatario=telefone,
        status="enviado" if ok else "erro",
        erro=erro,
        mensagem_corpo=mensagem,
    )
    db.add(hist)

    if ok:
        conta.ultima_cobranca_em = datetime.now(timezone.utc)

    db.flush()
    return {"ok": ok, "erro": erro}


# ── FLUXO DE CAIXA ────────────────────────────────────────────────────────────


def calcular_fluxo_caixa(
    empresa_id: int,
    data_inicio: date,
    data_fim: date,
    db: Session,
) -> dict:
    """Calcula entradas e saídas por dia no período, com alertas de caixa negativo."""
    from decimal import Decimal

    # Contas a receber no período (não canceladas, não pagas)
    entradas_raw = (
        db.query(ContaFinanceira)
        .filter(
            ContaFinanceira.empresa_id == empresa_id,
            ContaFinanceira.tipo == TipoConta.RECEBER,
            ContaFinanceira.status.notin_([StatusConta.CANCELADO, StatusConta.PAGO]),
            ContaFinanceira.data_vencimento >= data_inicio,
            ContaFinanceira.data_vencimento <= data_fim,
        )
        .all()
    )

    # Contas a pagar no período (não canceladas, não pagas)
    saidas_raw = (
        db.query(ContaFinanceira)
        .filter(
            ContaFinanceira.empresa_id == empresa_id,
            ContaFinanceira.tipo == TipoConta.PAGAR,
            ContaFinanceira.status.notin_([StatusConta.CANCELADO, StatusConta.PAGO]),
            ContaFinanceira.data_vencimento >= data_inicio,
            ContaFinanceira.data_vencimento <= data_fim,
        )
        .all()
    )

    # Agrupa por data
    por_data: dict[date, dict] = {}
    delta = data_fim - data_inicio
    for i in range(delta.days + 1):
        d = data_inicio + timedelta(days=i)
        por_data[d] = {"entradas": Decimal("0"), "saidas": Decimal("0")}

    for c in entradas_raw:
        if c.data_vencimento in por_data:
            saldo = (c.valor or Decimal("0")) - (c.valor_pago or Decimal("0"))
            por_data[c.data_vencimento]["entradas"] += saldo

    for c in saidas_raw:
        if c.data_vencimento in por_data:
            saldo = (c.valor or Decimal("0")) - (c.valor_pago or Decimal("0"))
            por_data[c.data_vencimento]["saidas"] += saldo

    # Calcular saldo acumulado
    lista = []
    acumulado = Decimal("0")
    alertas = []
    total_entradas = Decimal("0")
    total_saidas = Decimal("0")

    for d in sorted(por_data.keys()):
        e = por_data[d]["entradas"]
        s = por_data[d]["saidas"]
        saldo_dia = e - s
        acumulado += saldo_dia
        total_entradas += e
        total_saidas += s
        if acumulado < 0:
            alertas.append(f"Saldo negativo em {d.strftime('%d/%m/%Y')}")
        lista.append(
            {
                "data": d,
                "entradas": e,
                "saidas": s,
                "saldo_dia": saldo_dia,
                "saldo_acumulado": acumulado,
            }
        )

    return {
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "total_entradas": total_entradas,
        "total_saidas": total_saidas,
        "saldo_periodo": total_entradas - total_saidas,
        "por_data": lista,
        "alertas": alertas,
    }


# ── CONFIGURAÇÃO FINANCEIRA ───────────────────────────────────────────────────


def obter_ou_criar_configuracao(empresa_id: int, db: Session) -> ConfiguracaoFinanceira:
    cfg = db.query(ConfiguracaoFinanceira).filter_by(empresa_id=empresa_id).first()
    if not cfg:
        cfg = ConfiguracaoFinanceira(empresa_id=empresa_id)
        db.add(cfg)
        db.flush()
    return cfg


def atualizar_configuracao(
    empresa_id: int, dados: dict, db: Session
) -> ConfiguracaoFinanceira:
    cfg = obter_ou_criar_configuracao(empresa_id, db)
    for campo, val in dados.items():
        if val is not None:
            setattr(cfg, campo, val)
    db.flush()
    return cfg


def obter_ou_criar_templates(empresa_id: int, db: Session) -> list[TemplateNotificacao]:
    existentes = (
        db.query(TemplateNotificacao)
        .filter(TemplateNotificacao.empresa_id == empresa_id)
        .all()
    )
    tipos_existentes = {t.tipo for t in existentes}
    for tipo, corpo in _TEMPLATES_PADRAO.items():
        if tipo not in tipos_existentes:
            db.add(TemplateNotificacao(empresa_id=empresa_id, tipo=tipo, corpo=corpo))
    db.flush()
    return (
        db.query(TemplateNotificacao)
        .filter(TemplateNotificacao.empresa_id == empresa_id)
        .all()
    )


# ═══════════════════════════════════════════════════════════════════════════════
# FASE 1 - SPRINTS 1.1, 1.2, 1.3: FUNÇÕES DE SERVIÇO
# ═══════════════════════════════════════════════════════════════════════════════


def criar_conta_rapido(empresa_id: int, dados, usuario, db: Session) -> ContaFinanceira:
    """Cria conta a receber rapidamente a partir do schema simplificado."""
    from uuid import uuid4
    from decimal import Decimal

    # Validações básicas
    if dados.parcelas <= 0:
        raise ValueError("O número de parcelas deve ser maior que zero")

    if dados.valor <= Decimal("0"):
        raise ValueError("O valor deve ser maior que zero")

    # Se tem orcamento_id, busca o orçamento
    orcamento = None
    cliente_nome = dados.cliente_nome

    if dados.orcamento_id:
        orcamento = (
            db.query(Orcamento)
            .filter_by(id=dados.orcamento_id, empresa_id=empresa_id)
            .first()
        )
        if orcamento and orcamento.cliente:
            cliente_nome = orcamento.cliente.nome

    # Cria descrição automática se não tiver cliente
    if not cliente_nome:
        cliente_nome = "Cliente"

    descricao = f"{dados.descricao} - {cliente_nome}"

    # Valor por parcela (com arredondamento correto)
    valor_total = Decimal(str(dados.valor))
    valor_parcela = (valor_total / Decimal(str(dados.parcelas))).quantize(
        Decimal("0.01")
    )

    # Ajusta a última parcela para compensar arredondamentos
    valor_ultima_parcela = valor_total - (valor_parcela * (dados.parcelas - 1))

    grupo_id = str(uuid4()) if dados.parcelas > 1 else None

    # Data de vencimento
    vencimento = dados.vencimento or (date.today() + timedelta(days=7))

    contas_criadas = []

    for i in range(dados.parcelas):
        parcela_vencimento = (
            vencimento + timedelta(days=30 * i) if i > 0 else vencimento
        )

        # Usa valor ajustado para a última parcela
        valor_final = valor_ultima_parcela if i == dados.parcelas - 1 else valor_parcela

        conta = ContaFinanceira(
            empresa_id=empresa_id,
            orcamento_id=dados.orcamento_id,
            tipo=TipoConta.RECEBER,
            descricao=f"{descricao} ({i + 1}/{dados.parcelas})"
            if dados.parcelas > 1
            else descricao,
            valor=valor_final,
            data_vencimento=parcela_vencimento,
            status=StatusConta.PENDENTE,
            origem=OrigemRegistro.MANUAL,
            numero_parcela=i + 1,
            total_parcelas=dados.parcelas,
            grupo_parcelas_id=grupo_id,
        )
        db.add(conta)
        contas_criadas.append(conta)

    db.flush()
    return contas_criadas[0] if contas_criadas else None


def calcular_saldo_detalhado(empresa_id: int, db: Session) -> dict:
    """Calcula saldo detalhado de caixa com projeções."""
    from decimal import Decimal

    hoje = date.today()

    # Usa a função centralizada para garantir consistência com o dashboard e KPIs
    stats = _calcular_estatisticas_caixa(empresa_id, db)
    saldo_caixa = stats["saldo_atual"]

    # A receber nos próximos 30 dias (apenas contas não excluídas)
    a_receber_30 = db.query(
        func.sum(ContaFinanceira.valor - ContaFinanceira.valor_pago)
    ).filter(
        ContaFinanceira.empresa_id == empresa_id,
        ContaFinanceira.tipo == TipoConta.RECEBER,
        ContaFinanceira.status.in_([StatusConta.PENDENTE, StatusConta.PARCIAL]),
        ContaFinanceira.data_vencimento <= hoje + timedelta(days=30),
        ContaFinanceira.data_vencimento >= hoje,  # Apenas futuras
        ContaFinanceira.excluido_em.is_(None),
        ContaFinanceira.cancelado_em.is_(None),  # Não considera canceladas
    ).scalar() or Decimal("0")

    # A pagar nos próximos 30 dias (apenas contas não excluídas)
    a_pagar_30 = db.query(
        func.sum(ContaFinanceira.valor - ContaFinanceira.valor_pago)
    ).filter(
        ContaFinanceira.empresa_id == empresa_id,
        ContaFinanceira.tipo == TipoConta.PAGAR,
        ContaFinanceira.status.in_([StatusConta.PENDENTE, StatusConta.PARCIAL]),
        ContaFinanceira.data_vencimento <= hoje + timedelta(days=30),
        ContaFinanceira.data_vencimento >= hoje,  # Apenas futuras
        ContaFinanceira.excluido_em.is_(None),
        ContaFinanceira.cancelado_em.is_(None),  # Não considera canceladas
    ).scalar() or Decimal("0")

    # Projeção de caixa em 30 dias
    projecao_30 = saldo_caixa + Decimal(str(a_receber_30)) - Decimal(str(a_pagar_30))

    return {
        "saldo_caixa": saldo_caixa,
        "saldo_banco": Decimal("0"),  # Futuro: integração bancária
        "total_disponivel": saldo_caixa,
        "a_receber_30_dias": Decimal(str(a_receber_30)),
        "a_pagar_30_dias": Decimal(str(a_pagar_30)),
        "projecao_30_dias": projecao_30,
        "saldo_inicial_configurado": saldo_inicial,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# FASE 2 - SPRINTS 2.1, 2.2, 2.3: FUNÇÕES DE SERVIÇO
# ═══════════════════════════════════════════════════════════════════════════════


def calcular_saldo_caixa(empresa_id: int, db: Session) -> dict:
    """Retorna saldo detalhado do caixa para a aba de Caixa (centralizado)."""
    return _calcular_estatisticas_caixa(empresa_id, db)


# ── CATEGORIAS FINANCEIRAS (Sprint 2.2) ───────────────────────────────────────


def listar_categorias_sync(
    empresa_id: int,
    db: Session,
    tipo: Optional[str] = None,
    ativas: bool = True,
) -> List[CategoriaFinanceira]:
    """Lista categorias financeiras customizáveis da empresa (versão sync)."""
    query = db.query(CategoriaFinanceira).filter_by(empresa_id=empresa_id)

    if ativas:
        query = query.filter(CategoriaFinanceira.ativo == True)

    if tipo:
        query = query.filter(CategoriaFinanceira.tipo == tipo)

    return query.order_by(CategoriaFinanceira.ordem, CategoriaFinanceira.nome).all()


def criar_categoria_financeira(
    empresa_id: int,
    dados: CategoriaFinanceiraCreate,
    db: Session,
) -> CategoriaFinanceira:
    """Cria uma nova categoria financeira, verificando duplicidade."""
    repo = CategoriaFinanceiraRepository(db)

    existe = repo.verificar_duplicidade(empresa_id, dados.nome, dados.tipo.value)
    if existe:
        raise HTTPException(
            status_code=400,
            detail="Já existe uma categoria ativa com o mesmo nome e tipo.",
        )

    categoria = CategoriaFinanceira(
        empresa_id=empresa_id,
        nome=dados.nome,
        tipo=dados.tipo.value,
        cor=dados.cor,
        icone=dados.icone,
        ordem=dados.ordem,
    )
    return repo.criar_categoria(categoria)


def listar_categorias_financeiras(
    empresa_id: int,
    db: Session,
    tipo: Optional[str] = None,
    ativas: bool = True,
) -> List[CategoriaFinanceira]:
    """Lista categorias financeiras customizáveis da empresa."""
    repo = CategoriaFinanceiraRepository(db)
    return repo.listar_categorias(empresa_id, tipo, ativas)


def obter_categoria_financeira_por_id(
    categoria_id: int,
    empresa_id: int,
    db: Session,
) -> Optional[CategoriaFinanceira]:
    """Obtém uma categoria financeira pelo ID e empresa_id."""
    repo = CategoriaFinanceiraRepository(db)
    return repo.get_by_id(categoria_id, empresa_id)


def atualizar_categoria_financeira(
    categoria: CategoriaFinanceira,
    dados: CategoriaFinanceiraUpdate,
    db: Session,
) -> CategoriaFinanceira:
    """Atualiza uma categoria financeira, verificando duplicidade se nome ou tipo forem alterados."""
    repo = CategoriaFinanceiraRepository(db)

    update_data = dados.model_dump(exclude_unset=True)
    novo_nome = update_data.get("nome", categoria.nome)
    novo_tipo = update_data.get("tipo", categoria.tipo)
    if isinstance(
        novo_tipo, CategoriaFinanceiraCreate
    ):  # Trata o caso de ser um Enum do Pydantic
        novo_tipo = novo_tipo.value

    # Se o nome ou o tipo foram alterados, verifica duplicidade
    if novo_nome != categoria.nome or novo_tipo != categoria.tipo:
        existe = repo.verificar_duplicidade(
            categoria.empresa_id, novo_nome, novo_tipo, categoria.id
        )
        if existe:
            raise HTTPException(
                status_code=400,
                detail="Já existe uma categoria ativa com o mesmo nome e tipo.",
            )

    return repo.atualizar_categoria(categoria, update_data)


def excluir_categoria_financeira(
    categoria: CategoriaFinanceira,
    db: Session,
) -> CategoriaFinanceira:
    """Desativa (soft delete) uma categoria financeira."""
    repo = CategoriaFinanceiraRepository(db)
    return repo.soft_delete_categoria(categoria)


# ── SWEEP E AUTOMAÇÕES ────────────────────────────────────────────────────────


def sweep_contas_vencidas(db: Session) -> dict:
    """Marca como VENCIDO todas as contas PENDENTE/PARCIAL com data_vencimento passada.

    Deve ser chamado no startup e/ou via endpoint admin.
    """
    hoje = date.today()
    contas = (
        db.query(ContaFinanceira)
        .filter(
            ContaFinanceira.status.in_([StatusConta.PENDENTE, StatusConta.PARCIAL]),
            ContaFinanceira.data_vencimento < hoje,
            ContaFinanceira.excluido_em.is_(None),
            ContaFinanceira.cancelado_em.is_(None),
        )
        .all()
    )
    total = 0
    for conta in contas:
        conta.status = StatusConta.VENCIDO
        total += 1
    if total:
        db.flush()
    logger.info("sweep_contas_vencidas: %d contas marcadas como VENCIDO", total)
    return {"vencidas_atualizadas": total}


async def enviar_lembretes_vencimento(db: Session) -> dict:
    """Envia lembretes automáticos de vencimento via WhatsApp para empresas com automacoes_ativas=True.

    - Pré-vencimento: dias_lembrete_antes antes do vencimento
    - Pós-vencimento: dias_lembrete_apos após o vencimento

    Não envia duplicado: verifica HistoricoCobranca do mesmo dia para a conta.
    """
    hoje = date.today()
    enviados = 0
    ignorados = 0
    erros = 0

    # Busca todas as configurações com automações ativas
    cfgs = (
        db.query(ConfiguracaoFinanceira)
        .filter(ConfiguracaoFinanceira.automacoes_ativas == True)
        .all()
    )

    for cfg in cfgs:
        empresa_id = cfg.empresa_id
        datas_alvo = [
            hoje + timedelta(days=cfg.dias_lembrete_antes),  # pré-vencimento
            hoje - timedelta(days=cfg.dias_lembrete_apos),  # pós-vencimento
        ]

        for data_alvo in datas_alvo:
            contas = (
                db.query(ContaFinanceira)
                .filter(
                    ContaFinanceira.empresa_id == empresa_id,
                    ContaFinanceira.tipo == TipoConta.RECEBER,
                    ContaFinanceira.status.in_(
                        [StatusConta.PENDENTE, StatusConta.PARCIAL, StatusConta.VENCIDO]
                    ),
                    ContaFinanceira.data_vencimento == data_alvo,
                    ContaFinanceira.excluido_em.is_(None),
                    ContaFinanceira.cancelado_em.is_(None),
                )
                .all()
            )

            for conta in contas:
                # Verifica se já foi cobrada hoje
                ja_cobrada = (
                    db.query(HistoricoCobranca)
                    .filter(
                        HistoricoCobranca.conta_id == conta.id,
                        HistoricoCobranca.status == "enviado",
                        func.date(HistoricoCobranca.criado_em) == hoje,
                    )
                    .first()
                )
                if ja_cobrada:
                    ignorados += 1
                    continue

                resultado = await cobrar_via_whatsapp(conta.id, empresa_id, db)
                if resultado["ok"]:
                    enviados += 1
                else:
                    erros += 1

    logger.info(
        "enviar_lembretes_vencimento: enviados=%d ignorados=%d erros=%d",
        enviados,
        ignorados,
        erros,
    )
    return {"enviados": enviados, "ignorados": ignorados, "erros": erros}


# ═══════════════════════════════════════════════════════════════════════════════
# FIM DAS FUNÇÕES DE SERVIÇO
# ═══════════════════════════════════════════════════════════════════════════════
