"""Router do Módulo Financeiro COTTE.

Endpoints finos — toda lógica de negócio em financeiro_service.py.
"""

import csv
import io
import json
import logging
from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import (
    get_usuario_atual as get_current_user,
    exigir_permissao,
    exigir_modulo,
)
from app.utils.csv_utils import gerar_csv_response
from app.models.models import (
    CategoriaFinanceira,
    ConfiguracaoFinanceira,
    ContaFinanceira,
    FormaPagamentoConfig,
    HistoricoCobranca,
    MovimentacaoCaixa,
    Orcamento,
    Cliente,
    SaldoCaixaConfig,
    PagamentoFinanceiro,
    StatusConta,
    TipoConta,
    TemplateNotificacao,
    Usuario,
)
from app.schemas.financeiro import (
    CancelarContaRequest,
    CategoriaFinanceiraCreate,
    CategoriaFinanceiraOut,
    CategoriaFinanceiraUpdate,
    ClienteBuscaOut,
    ConfiguracaoFinanceiraOut,
    ConfiguracaoFinanceiraUpdate,
    ContaFinanceiraCreate,
    ContaFinanceiraOut,
    ContaFinanceiraUpdate,
    ContaRapidoCreate,
    ContaRapidoOut,
    DespesaCreate,
    EntradaCaixaRequest,
    EstornoRequest,
    ExcluirContaRequest,
    FinanceiroResumoOut,
    FluxoCaixaOut,
    FormaPagamentoConfigCreate,
    FormaPagamentoConfigOut,
    FormaPagamentoConfigUpdate,
    HistoricoCobrancaOut,
    MovimentacaoCaixaCreate,
    MovimentacaoCaixaOut,
    OrcamentoBuscaOut,
    PagamentoCreate,
    PagamentoOut,
    ReceberContaRequest,
    SaidaCaixaRequest,
    SaldoCaixaOut,
    SaldoDetalhadoOut,
    SaldoInicialRequest,
    TemplateNotificacaoOut,
    TemplateNotificacaoUpdate,
    TipoCategoria,
)
from app.services import financeiro_service as svc
from app.services.audit_service import registrar_auditoria

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/financeiro",
    tags=["Financeiro"],
    dependencies=[Depends(exigir_modulo("financeiro"))],
)


# ── HELPERS ──────────────────────────────────────────────────────────────────


def _enrich_pagamento(p: PagamentoFinanceiro) -> dict:
    """Acrescenta campos calculados ao pagamento para serialização."""
    return {
        **{c.key: getattr(p, c.key) for c in p.__table__.columns},
        "forma_pagamento_nome": p.forma_pagamento_config.nome
        if p.forma_pagamento_config
        else None,
        "forma_pagamento_icone": p.forma_pagamento_config.icone
        if p.forma_pagamento_config
        else None,
        "confirmado_por_nome": p.confirmado_por.nome if p.confirmado_por else None,
        "orcamento_numero": p.orcamento.numero if p.orcamento else None,
        "cliente_nome": p.orcamento.cliente.nome
        if p.orcamento and p.orcamento.cliente
        else None,
    }


def _enrich_conta(c: ContaFinanceira) -> dict:
    """Acrescenta campos calculados à conta para serialização."""
    from decimal import Decimal

    saldo = (c.valor or Decimal("0")) - (c.valor_pago or Decimal("0"))
    pagamentos = [_enrich_pagamento(p) for p in c.pagamentos]
    return {
        **{col.key: getattr(c, col.key) for col in c.__table__.columns},
        "saldo_devedor": saldo,
        "orcamento_numero": c.orcamento.numero if c.orcamento else None,
        "cliente_nome": c.orcamento.cliente.nome
        if c.orcamento and c.orcamento.cliente
        else None,
        "pagamentos": pagamentos,
    }


# ── FORMAS DE PAGAMENTO ───────────────────────────────────────────────────────


@router.get("/formas-pagamento", response_model=List[FormaPagamentoConfigOut])
def listar_formas(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Lista formas de pagamento ativas da empresa."""
    formas = svc.listar_formas_pagamento(usuario.empresa_id, db)
    if not formas:
        # Seed lazy: cria formas padrão na primeira chamada
        with db.begin_nested():
            svc._seed_formas_padrao(usuario.empresa_id, db)
        db.commit()
        formas = svc.listar_formas_pagamento(usuario.empresa_id, db)
    return formas


@router.post(
    "/formas-pagamento", response_model=FormaPagamentoConfigOut, status_code=201
)
def criar_forma(
    dados: FormaPagamentoConfigCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "escrita")),
):
    with db.begin_nested():
        forma = svc.criar_forma_pagamento(usuario.empresa_id, dados.model_dump(), db)
    db.commit()
    db.refresh(forma)
    return forma


@router.patch("/formas-pagamento/{forma_id}", response_model=FormaPagamentoConfigOut)
def atualizar_forma(
    forma_id: int,
    dados: FormaPagamentoConfigUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "escrita")),
):
    forma = (
        db.query(FormaPagamentoConfig)
        .filter_by(id=forma_id, empresa_id=usuario.empresa_id)
        .first()
    )
    if not forma:
        raise HTTPException(
            status_code=404, detail="Forma de pagamento não encontrada."
        )
    update_data = dados.model_dump(exclude_unset=True)
    # Se estiver marcando como padrão, garantir unicidade
    if update_data.get("padrao") is True:
        db.query(FormaPagamentoConfig).filter(
            FormaPagamentoConfig.empresa_id == usuario.empresa_id,
            FormaPagamentoConfig.id != forma_id,
        ).update({"padrao": False})
    for campo, val in update_data.items():
        setattr(forma, campo, val)
    db.commit()
    db.refresh(forma)
    return forma


@router.post(
    "/formas-pagamento/{forma_id}/padrao", response_model=FormaPagamentoConfigOut
)
def set_padrao(
    forma_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "escrita")),
):
    """Define uma forma de pagamento como padrão da empresa."""
    try:
        with db.begin_nested():
            forma = svc.set_forma_padrao(usuario.empresa_id, forma_id, db)
        db.commit()
        db.refresh(forma)
        return forma
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/formas-pagamento/{forma_id}", status_code=204)
def desativar_forma(
    forma_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "admin")),
):
    """Desativa (soft-delete) uma forma de pagamento."""
    forma = (
        db.query(FormaPagamentoConfig)
        .filter_by(id=forma_id, empresa_id=usuario.empresa_id)
        .first()
    )
    if not forma:
        raise HTTPException(
            status_code=404, detail="Forma de pagamento não encontrada."
        )
    forma.ativo = False
    if forma.padrao:
        forma.padrao = False
    db.commit()


# ── PAGAMENTOS ────────────────────────────────────────────────────────────────


@router.post("/pagamentos", response_model=PagamentoOut, status_code=201)
def registrar_pagamento(
    request: Request,
    dados: PagamentoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "escrita")),
    idempotency_key_header: Optional[str] = Header(
        None, alias="Idempotency-Key", convert_underscores=False
    ),
):
    """Registra um pagamento. Cria conta a receber se não existir.
    Se tipo=SINAL, gera conta do saldo automaticamente.
    Idempotência: header Idempotency-Key ou campo idempotency_key no JSON (mesma empresa)."""
    chave = idempotency_key_header or dados.idempotency_key
    dados_final = (
        dados.model_copy(update={"idempotency_key": chave}) if chave else dados
    )
    with db.begin_nested():
        pagamento = svc.registrar_pagamento(
            usuario.empresa_id, dados_final, usuario, db
        )
    db.commit()
    db.refresh(pagamento)
    registrar_auditoria(
        db=db,
        usuario=usuario,
        acao="financeiro_pagamento_registrado",
        recurso="pagamento",
        recurso_id=str(pagamento.id),
        detalhes={
            "valor": str(pagamento.valor),
            "tipo": str(dados.tipo) if hasattr(dados, "tipo") else None,
        },
        request=request,
    )
    return _enrich_pagamento(pagamento)


@router.get("/pagamentos", response_model=List[PagamentoOut])
def listar_pagamentos(
    orcamento_id: Optional[int] = Query(None),
    cliente: Optional[str] = Query(None),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    todos: bool = Query(False, description="Incluir estornados"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "leitura")),
):
    pagamentos = svc.listar_pagamentos(
        empresa_id=usuario.empresa_id,
        db=db,
        orcamento_id=orcamento_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        cliente_nome=cliente,
        apenas_confirmados=not todos,
        limit=limit,
        offset=offset,
    )
    return [_enrich_pagamento(p) for p in pagamentos]


@router.post("/pagamentos/{pagamento_id}/estornar", response_model=PagamentoOut)
def estornar_pagamento(
    pagamento_id: int,
    request: Request,
    body: EstornoRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "admin")),
):
    """Estorna um pagamento (status → ESTORNADO). Recalcula conta e orçamento."""
    with db.begin_nested():
        pagamento = svc.estornar_pagamento(
            pagamento_id, usuario.empresa_id, body.motivo, db
        )
    db.commit()
    db.refresh(pagamento)
    registrar_auditoria(
        db=db,
        usuario=usuario,
        acao="financeiro_pagamento_estornado",
        recurso="pagamento",
        recurso_id=str(pagamento_id),
        detalhes={"motivo": body.motivo},
        request=request,
    )
    return _enrich_pagamento(pagamento)


# ── CONTAS FINANCEIRAS ────────────────────────────────────────────────────────


@router.post("/contas", response_model=ContaFinanceiraOut, status_code=201)
def criar_conta(
    dados: ContaFinanceiraCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "escrita")),
):
    with db.begin_nested():
        conta = svc.criar_conta(usuario.empresa_id, dados, db)
    db.commit()
    db.refresh(conta)
    return _enrich_conta(conta)


@router.get("/contas", response_model=List[ContaFinanceiraOut])
def listar_contas(
    id: Optional[int] = Query(None),
    tipo: Optional[TipoConta] = Query(None),
    status: Optional[str] = Query(
        None,
        description="Um ou mais status separados por vírgula: pendente,parcial,vencido",
    ),
    orcamento_id: Optional[int] = Query(None),
    busca: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "leitura")),
):
    # Aceita status único ou lista separada por vírgula (case-insensitive)
    status_list: Optional[List[StatusConta]] = None
    if status:
        raw = [s.strip().lower() for s in status.split(",") if s.strip()]
        try:
            status_list = [StatusConta(s) for s in raw if s]
        except ValueError:
            status_list = None
    contas = svc.listar_contas(
        empresa_id=usuario.empresa_id,
        db=db,
        id=id,
        tipo=tipo,
        status_list=status_list,
        orcamento_id=orcamento_id,
        busca=busca,
    )
    return [_enrich_conta(c) for c in contas]


@router.get("/contas/exportar/csv")
def exportar_contas_csv(
    tipo: Optional[TipoConta] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "leitura")),
):
    """Exporta contas financeiras como CSV."""
    status_list: Optional[List[StatusConta]] = None
    if status:
        raw = [s.strip().lower() for s in status.split(",") if s.strip()]
        try:
            status_list = [StatusConta(s) for s in raw if s]
        except ValueError:
            status_list = None
    contas = svc.listar_contas(
        empresa_id=usuario.empresa_id,
        db=db,
        tipo=tipo,
        status_list=status_list,
    )
    header = [
        "Orçamento",
        "Cliente",
        "Descrição",
        "Tipo",
        "Parcela",
        "Valor",
        "Pago",
        "Saldo",
        "Vencimento",
        "Status",
        "Método",
    ]
    from decimal import Decimal

    rows = []
    for c in contas:
        saldo = (c.valor or Decimal("0")) - (c.valor_pago or Decimal("0"))
        rows.append(
            [
                c.orcamento.numero if c.orcamento else "",
                c.orcamento.cliente.nome
                if c.orcamento and c.orcamento.cliente
                else (c.favorecido or ""),
                c.descricao or "",
                c.tipo.value if c.tipo else "",
                c.numero_parcela or "",
                str(c.valor or 0).replace(".", ","),
                str(c.valor_pago or 0).replace(".", ","),
                str(saldo).replace(".", ","),
                c.data_vencimento.strftime("%d/%m/%Y") if c.data_vencimento else "",
                c.status.value if c.status else "",
                c.metodo_previsto or "",
            ]
        )
    return gerar_csv_response(header, rows, "contas_financeiras")


@router.get("/contas/inadimplentes", response_model=List[ContaFinanceiraOut])
def listar_inadimplentes(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "leitura")),
):
    """Contas a receber com vencimento expirado."""
    contas = svc.listar_inadimplentes(usuario.empresa_id, db)
    return [_enrich_conta(c) for c in contas]


@router.patch("/contas/{conta_id}", response_model=ContaFinanceiraOut)
def atualizar_conta(
    conta_id: int,
    dados: ContaFinanceiraUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "escrita")),
):
    conta = (
        db.query(ContaFinanceira)
        .filter_by(id=conta_id, empresa_id=usuario.empresa_id)
        .first()
    )
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")
    with db.begin_nested():
        svc.atualizar_conta(conta, dados, db)
    db.commit()
    db.refresh(conta)
    return _enrich_conta(conta)


@router.delete("/contas/{conta_id}", status_code=204)
def excluir_conta(
    conta_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "admin")),
):
    """Exclui uma conta financeira, se não houver pagamentos associados."""
    conta = (
        db.query(ContaFinanceira)
        .filter_by(id=conta_id, empresa_id=usuario.empresa_id)
        .first()
    )
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")
    try:
        with db.begin_nested():
            svc.excluir_conta(conta, db)
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── DASHBOARD ─────────────────────────────────────────────────────────────────


@router.get("/resumo", response_model=FinanceiroResumoOut)
def resumo_financeiro(
    busca: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "leitura")),
):
    """KPIs e dados de gráfico para o dashboard financeiro."""
    return svc.calcular_resumo(usuario.empresa_id, db, busca=busca)


# ── TEMPLATES DE NOTIFICAÇÃO ──────────────────────────────────────────────────


@router.get("/templates", response_model=List[TemplateNotificacaoOut])
def listar_templates(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "leitura")),
):
    return svc.obter_ou_criar_templates(usuario.empresa_id, db)


@router.patch("/templates/{template_id}", response_model=TemplateNotificacaoOut)
def atualizar_template(
    template_id: int,
    dados: TemplateNotificacaoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "escrita")),
):
    tmpl = (
        db.query(TemplateNotificacao)
        .filter_by(id=template_id, empresa_id=usuario.empresa_id)
        .first()
    )
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template não encontrado.")
    for campo, val in dados.model_dump(exclude_unset=True).items():
        setattr(tmpl, campo, val)
    db.commit()
    db.refresh(tmpl)
    return tmpl


# ── DESPESAS (Contas a Pagar) ─────────────────────────────────────────────────


@router.post("/despesas", response_model=ContaFinanceiraOut, status_code=201)
def criar_despesa(
    dados: DespesaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "escrita")),
):
    """Cria uma despesa (conta a pagar) manualmente."""
    with db.begin_nested():
        conta = svc.criar_despesa(usuario.empresa_id, dados.model_dump(), db)
    db.commit()
    db.refresh(conta)
    return _enrich_conta(conta)


@router.get("/despesas", response_model=List[ContaFinanceiraOut])
def listar_despesas(
    id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    categoria_slug: Optional[str] = Query(None),
    busca: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "leitura")),
):
    status_list: Optional[List[StatusConta]] = None
    if status:
        raw = [s.strip().lower() for s in status.split(",") if s.strip()]
        try:
            status_list = [StatusConta(s) for s in raw if s]
        except ValueError:
            status_list = None
    contas = svc.listar_despesas(
        empresa_id=usuario.empresa_id,
        db=db,
        id=id,
        status_list=status_list,
        data_inicio=data_inicio,
        data_fim=data_fim,
        categoria_slug=categoria_slug,
        busca=busca,
    )
    return [_enrich_conta(c) for c in contas]


@router.get("/despesas/exportar/csv")
def exportar_despesas_csv(
    status: Optional[str] = Query(None),
    categoria_slug: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "leitura")),
):
    """Exporta despesas como CSV."""
    status_list: Optional[List[StatusConta]] = None
    if status:
        raw = [s.strip().lower() for s in status.split(",") if s.strip()]
        try:
            status_list = [StatusConta(s) for s in raw if s]
        except ValueError:
            status_list = None
    contas = svc.listar_despesas(
        empresa_id=usuario.empresa_id,
        db=db,
        status_list=status_list,
        categoria_slug=categoria_slug,
    )
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(
        [
            "Favorecido",
            "Descrição",
            "Categoria",
            "Valor",
            "Vencimento",
            "Competência",
            "Status",
        ]
    )
    for c in contas:
        writer.writerow(
            [
                c.favorecido or "",
                c.descricao or "",
                c.categoria_slug or "",
                str(c.valor or 0).replace(".", ","),
                c.data_vencimento.strftime("%d/%m/%Y") if c.data_vencimento else "",
                c.data_competencia.strftime("%d/%m/%Y") if c.data_competencia else "",
                c.status.value if c.status else "",
            ]
        )
    output.seek(0)

    filename = f"despesas_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.patch("/despesas/{conta_id}", response_model=ContaFinanceiraOut)
def atualizar_despesa(
    conta_id: int,
    dados: ContaFinanceiraUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "escrita")),
):
    conta = (
        db.query(ContaFinanceira)
        .filter_by(id=conta_id, empresa_id=usuario.empresa_id, tipo=TipoConta.PAGAR)
        .first()
    )
    if not conta:
        raise HTTPException(status_code=404, detail="Despesa não encontrada.")
    with db.begin_nested():
        svc.atualizar_conta(conta, dados, db)
    db.commit()
    db.refresh(conta)
    return _enrich_conta(conta)


@router.post("/despesas/{conta_id}/pagar", response_model=PagamentoOut, status_code=201)
def pagar_despesa(
    conta_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "escrita")),
    idempotency_key_header: Optional[str] = Header(
        None, alias="Idempotency-Key", convert_underscores=False
    ),
):
    """Marca uma despesa como paga."""
    with db.begin_nested():
        pagamento = svc.registrar_pagamento_despesa(
            conta_id=conta_id,
            empresa_id=usuario.empresa_id,
            usuario=usuario,
            db=db,
            idempotency_key=idempotency_key_header,
        )
    db.commit()
    db.refresh(pagamento)
    return _enrich_pagamento(pagamento)


@router.post("/contas/{conta_id}/receber", response_model=PagamentoOut, status_code=201)
def receber_conta(
    conta_id: int,
    body: Optional[ReceberContaRequest] = Body(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "escrita")),
    idempotency_key_header: Optional[str] = Header(
        None, alias="Idempotency-Key", convert_underscores=False
    ),
):
    """Marca uma conta a receber como paga (para contas avulsas ou vinculadas a orçamento)."""
    payload = body or ReceberContaRequest()
    if payload.valor is not None and payload.valor <= 0:
        raise HTTPException(
            status_code=400, detail="Valor do pagamento deve ser maior que zero"
        )

    idem = idempotency_key_header or payload.idempotency_key

    with db.begin_nested():
        pagamento = svc.registrar_pagamento_conta_receber(
            conta_id=conta_id,
            empresa_id=usuario.empresa_id,
            usuario=usuario,
            db=db,
            valor=payload.valor,
            forma_pagamento_id=payload.forma_pagamento_id,
            observacao=payload.observacao,
            data_pagamento=payload.data_pagamento,
            idempotency_key=idem,
        )
    db.commit()
    db.refresh(pagamento)
    return _enrich_pagamento(pagamento)


# ── COBRANÇA VIA WHATSAPP ──────────────────────────────────────────────────────


@router.post("/contas/{conta_id}/cobrar")
async def cobrar_conta(
    conta_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "escrita")),
):
    """Envia cobrança WhatsApp ao cliente da conta."""
    resultado = await svc.cobrar_via_whatsapp(conta_id, usuario.empresa_id, db)
    db.commit()
    if not resultado["ok"]:
        raise HTTPException(status_code=400, detail=resultado["erro"])
    return {"mensagem": "Cobrança enviada com sucesso."}


@router.get("/historico-cobrancas", response_model=List[HistoricoCobrancaOut])
def listar_historico_cobrancas(
    conta_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "leitura")),
):
    q = db.query(HistoricoCobranca).filter_by(empresa_id=usuario.empresa_id)
    if conta_id:
        q = q.filter(HistoricoCobranca.conta_id == conta_id)
    return q.order_by(HistoricoCobranca.enviado_em.desc()).limit(200).all()


# ── FLUXO DE CAIXA ─────────────────────────────────────────────────────────────


@router.get("/fluxo-caixa", response_model=FluxoCaixaOut)
def fluxo_caixa(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "leitura")),
):
    hoje = date.today()
    inicio = data_inicio or hoje
    fim = data_fim or (hoje + timedelta(days=30))
    return svc.calcular_fluxo_caixa(usuario.empresa_id, inicio, fim, db)


# ── CATEGORIAS DE DESPESAS ────────────────────────────────────────────────────


@router.get("/categorias", response_model=List[CategoriaFinanceiraOut])
def listar_categorias(
    tipo: Optional[str] = Query(
        None, description="Tipo de categoria: receita, despesa ou ambos"
    ),
    ativas: bool = Query(True, description="Apenas categorias ativas"),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "leitura")),
):
    """Lista categorias financeiras da empresa."""
    categorias = svc.listar_categorias_sync(
        empresa_id=usuario.empresa_id,
        db=db,
        tipo=tipo,
        ativas=ativas,
    )
    return [
        CategoriaFinanceiraOut(
            id=c.id,
            empresa_id=c.empresa_id,
            nome=c.nome,
            tipo=TipoCategoria(c.tipo),  # Convert string to enum
            cor=c.cor,
            icone=c.icone,
            ativo=c.ativo,
            ordem=c.ordem,
            criado_em=c.criado_em,
        )
        for c in categorias
    ]


@router.post("/categorias", response_model=CategoriaFinanceiraOut, status_code=201)
def criar_categoria(
    dados: CategoriaFinanceiraCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "escrita")),
):
    """Cria uma nova categoria financeira."""
    with db.begin_nested():
        categoria = svc.criar_categoria_financeira(usuario.empresa_id, dados, db)
    db.commit()
    db.refresh(categoria)
    return CategoriaFinanceiraOut(
        id=categoria.id,
        empresa_id=categoria.empresa_id,
        nome=categoria.nome,
        tipo=TipoCategoria(categoria.tipo),
        cor=categoria.cor,
        icone=categoria.icone,
        ativo=categoria.ativo,
        ordem=categoria.ordem,
        criado_em=categoria.criado_em,
    )


@router.patch("/categorias/{categoria_id}", response_model=CategoriaFinanceiraOut)
def atualizar_categoria(
    categoria_id: int,
    dados: CategoriaFinanceiraUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "escrita")),
):
    """Atualiza uma categoria financeira."""
    categoria = svc.obter_categoria_financeira_por_id(
        categoria_id, usuario.empresa_id, db
    )
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada.")

    svc.atualizar_categoria_financeira(categoria, dados, db)
    db.commit()
    db.refresh(categoria)
    return CategoriaFinanceiraOut(
        id=categoria.id,
        empresa_id=categoria.empresa_id,
        nome=categoria.nome,
        tipo=TipoCategoria(categoria.tipo),
        cor=categoria.cor,
        icone=categoria.icone,
        ativo=categoria.ativo,
        ordem=categoria.ordem,
        criado_em=categoria.criado_em,
    )


@router.delete("/categorias/{categoria_id}", status_code=204)
def excluir_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "admin")),
):
    """Exclui (soft delete) uma categoria financeira."""
    categoria = svc.obter_categoria_financeira_por_id(
        categoria_id, usuario.empresa_id, db
    )
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada.")

    with db.begin_nested():
        svc.excluir_categoria_financeira(categoria, db)
    db.commit()


# ── CONFIGURAÇÕES FINANCEIRAS ──────────────────────────────────────────────────


@router.get("/configuracoes", response_model=ConfiguracaoFinanceiraOut)
def obter_configuracoes(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "leitura")),
):
    cfg = svc.obter_ou_criar_configuracao(usuario.empresa_id, db)
    db.commit()
    return cfg


@router.patch("/configuracoes", response_model=ConfiguracaoFinanceiraOut)
def atualizar_configuracoes(
    dados: ConfiguracaoFinanceiraUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "escrita")),
):
    with db.begin_nested():
        cfg = svc.atualizar_configuracao(
            usuario.empresa_id, dados.model_dump(exclude_unset=True), db
        )
    db.commit()
    db.refresh(cfg)
    return cfg


# ── SWEEP / AUTOMAÇÕES ────────────────────────────────────────────────────────


@router.post("/sweep", include_in_schema=False)
async def executar_sweep(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "escrita")),
):
    """Executa sweep manual: atualiza contas vencidas e envia lembretes automáticos."""
    resultado_sweep = svc.sweep_contas_vencidas(db)
    db.commit()
    resultado_lembretes = await svc.enviar_lembretes_vencimento(db)
    db.commit()
    return {**resultado_sweep, **resultado_lembretes}


# ── WEBHOOK PIX (Stub) ────────────────────────────────────────────────────────


@router.post("/webhooks/pix/{provedor}", include_in_schema=True)
async def webhook_pix(provedor: str, request: Request, db: Session = Depends(get_db)):
    """Stub para conciliação automática PIX.
    Futuramente: validar assinatura HMAC, buscar txid, confirmar pagamento.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    logger.info(
        "Webhook PIX recebido | provedor=%s | payload=%s", provedor, str(body)[:200]
    )

    # TODO: implementar integração bancária real (Open Finance / API do banco)
    # 1. Validar assinatura (header X-Signature ou similar)
    # 2. Extrair txid do payload
    # 3. Buscar PagamentoFinanceiro por txid_pix
    # 4. Confirmar pagamento automaticamente

    return {"status": "recebido", "provedor": provedor}


# ═══════════════════════════════════════════════════════════════════════════════
# FASE 1 - SPRINTS 1.1, 1.2, 1.3
# ═══════════════════════════════════════════════════════════════════════════════

# ── SPRINT 1.1: ENDPOINT SIMPLIFICADO ──────────────────────────────────────────


@router.post("/contas/rapido", response_model=ContaRapidoOut, status_code=201)
def criar_conta_rapido(
    dados: ContaRapidoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "escrita")),
):
    """Endpoint simplificado para criar conta a receber rapidamente."""
    try:
        with db.begin_nested():
            conta = svc.criar_conta_rapido(usuario.empresa_id, dados, usuario, db)
        db.commit()
        db.refresh(conta)
        return ContaRapidoOut(
            sucesso=True,
            conta_id=conta.id,
            mensagem="Conta criada com sucesso",
            parcelas_criadas=dados.parcelas,
        )
    except ValueError as e:
        return ContaRapidoOut(sucesso=False, mensagem=str(e), parcelas_criadas=0)


@router.get("/orcamentos/buscar", response_model=List[OrcamentoBuscaOut])
def buscar_orcamentos(
    q: str = Query(
        ..., min_length=2, description="Número do orçamento ou nome do cliente"
    ),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "leitura")),
):
    """Busca orçamentos por número ou nome do cliente para autocomplete."""
    orcamentos = (
        db.query(Orcamento)
        .join(Orcamento.cliente)
        .filter(
            Orcamento.empresa_id == usuario.empresa_id,
            Orcamento.status.in_(["aprovado", "enviado"]),
            db.or_(
                Orcamento.numero.ilike(f"%{q}%"),
                Cliente.nome.ilike(f"%{q}%"),
            ),
        )
        .order_by(Orcamento.data_criacao.desc())
        .limit(limit)
        .all()
    )
    return [
        OrcamentoBuscaOut(
            id=o.id,
            numero=o.numero,
            cliente_nome=o.cliente.nome if o.cliente else None,
            cliente_telefone=o.cliente.telefone if o.cliente else None,
            total=o.total,
            status=o.status.value,
            data_criacao=o.data_criacao.date() if o.data_criacao else date.today(),
        )
        for o in orcamentos
    ]


@router.get("/clientes/buscar", response_model=List[ClienteBuscaOut])
def buscar_clientes(
    q: str = Query(..., min_length=2, description="Nome ou telefone do cliente"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "leitura")),
):
    """Busca clientes por nome ou telefone para autocomplete."""
    clientes = (
        db.query(Cliente)
        .filter(
            Cliente.empresa_id == usuario.empresa_id,
            db.or_(
                Cliente.nome.ilike(f"%{q}%"),
                Cliente.telefone.ilike(f"%{q}%"),
            ),
        )
        .order_by(Cliente.nome)
        .limit(limit)
        .all()
    )
    return [
        ClienteBuscaOut(
            id=c.id,
            nome=c.nome,
            telefone=c.telefone,
            email=c.email,
        )
        for c in clientes
    ]


# ── SPRINT 1.2: CANCELAMENTO E SOFT DELETE ─────────────────────────────────────


@router.post("/contas/{conta_id}/cancelar", response_model=ContaFinanceiraOut)
def cancelar_conta(
    conta_id: int,
    body: CancelarContaRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "escrita")),
):
    """Cancela uma conta financeira com motivo."""
    conta = (
        db.query(ContaFinanceira)
        .filter_by(id=conta_id, empresa_id=usuario.empresa_id)
        .first()
    )
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")

    if conta.status == StatusConta.CANCELADO:
        raise HTTPException(status_code=400, detail="Conta já está cancelada.")

    with db.begin_nested():
        conta.status = StatusConta.CANCELADO
        conta.cancelado_em = datetime.now()
        conta.cancelado_por_id = usuario.id
        conta.motivo_cancelamento = body.motivo

    db.commit()
    db.refresh(conta)
    return _enrich_conta(conta)


@router.delete("/contas/{conta_id}/soft", status_code=204)
def excluir_conta_soft(
    conta_id: int,
    body: ExcluirContaRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "admin")),
):
    """Soft delete de conta com motivo (não exclui fisicamente)."""
    conta = (
        db.query(ContaFinanceira)
        .filter_by(id=conta_id, empresa_id=usuario.empresa_id)
        .first()
    )
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")

    if conta.excluido_em:
        raise HTTPException(status_code=400, detail="Conta já está excluída.")

    with db.begin_nested():
        conta.excluido_em = datetime.now()
        conta.excluido_por_id = usuario.id
        conta.motivo_exclusao = body.motivo
        conta.status = StatusConta.CANCELADO

    db.commit()


# ── SPRINT 1.3: SALDO DETALHADO ────────────────────────────────────────────────


@router.get("/saldo", response_model=SaldoDetalhadoOut)
def obter_saldo_detalhado(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "leitura")),
):
    """Retorna saldo em caixa detalhado com projeções."""
    return svc.calcular_saldo_detalhado(usuario.empresa_id, db)


@router.post("/saldo-inicial", status_code=204)
def definir_saldo_inicial(
    dados: SaldoInicialRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "escrita")),
):
    """Define o saldo inicial de caixa da empresa."""
    cfg = db.query(SaldoCaixaConfig).filter_by(empresa_id=usuario.empresa_id).first()
    if not cfg:
        cfg = SaldoCaixaConfig(empresa_id=usuario.empresa_id)
        db.add(cfg)

    cfg.saldo_inicial = dados.valor
    cfg.configurado_em = datetime.now()
    cfg.configurado_por_id = usuario.id
    db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# FASE 2 - SPRINTS 2.1, 2.2, 2.3
# ═══════════════════════════════════════════════════════════════════════════════

# ── SPRINT 2.1: MOVIMENTAÇÕES DE CAIXA ───────────────────────────────────────


@router.get("/caixa/movimentacoes", response_model=List[MovimentacaoCaixaOut])
def listar_movimentacoes_caixa(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    tipo: Optional[str] = Query(None, description="entrada ou saida"),
    categoria: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "leitura")),
):
    """Lista movimentações de caixa com filtros."""
    query = db.query(MovimentacaoCaixa).filter_by(empresa_id=usuario.empresa_id)

    if data_inicio:
        query = query.filter(MovimentacaoCaixa.data >= data_inicio)
    if data_fim:
        query = query.filter(MovimentacaoCaixa.data <= data_fim)
    if tipo:
        query = query.filter(MovimentacaoCaixa.tipo == tipo)
    if categoria:
        query = query.filter(MovimentacaoCaixa.categoria.ilike(f"%{categoria}%"))

    return query.order_by(MovimentacaoCaixa.data.desc()).limit(limit).all()


@router.post("/caixa/entrada", response_model=MovimentacaoCaixaOut, status_code=201)
def registrar_entrada_caixa(
    dados: EntradaCaixaRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "escrita")),
):
    """Registra uma entrada no caixa."""
    mov = MovimentacaoCaixa(
        empresa_id=usuario.empresa_id,
        tipo="entrada",
        valor=dados.valor,
        descricao=dados.descricao,
        categoria=dados.categoria,
        data=dados.data or date.today(),
        criado_por_id=usuario.id,
    )
    db.add(mov)
    db.commit()
    db.refresh(mov)
    return mov


@router.post("/caixa/saida", response_model=MovimentacaoCaixaOut, status_code=201)
def registrar_saida_caixa(
    dados: SaidaCaixaRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "escrita")),
):
    """Registra uma saída do caixa."""
    mov = MovimentacaoCaixa(
        empresa_id=usuario.empresa_id,
        tipo="saida",
        valor=dados.valor,
        descricao=dados.descricao,
        categoria=dados.categoria,
        data=dados.data or date.today(),
        criado_por_id=usuario.id,
    )
    db.add(mov)
    db.commit()
    db.refresh(mov)
    return mov


@router.delete("/caixa/movimentacoes/{movimentacao_id}", status_code=204)
def excluir_movimentacao_caixa(
    movimentacao_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "admin")),
):
    """Exclui uma movimentação de caixa."""
    mov = (
        db.query(MovimentacaoCaixa)
        .filter(
            MovimentacaoCaixa.id == movimentacao_id,
            MovimentacaoCaixa.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not mov:
        raise HTTPException(status_code=404, detail="Movimentação não encontrada")
    db.delete(mov)
    db.commit()


@router.get("/caixa/saldo", response_model=SaldoCaixaOut)
def obter_saldo_caixa(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("financeiro", "leitura")),
):
    """Retorna saldo atual do caixa."""
    return svc.calcular_saldo_caixa(usuario.empresa_id, db)


# ═══════════════════════════════════════════════════════════════════════════════
# FIM DOS ENDPOINTS NOVOS
# ═══════════════════════════════════════════════════════════════════════════════
# FIM DOS ENDPOINTS NOVOS
# ═══════════════════════════════════════════════════════════════════════════════
