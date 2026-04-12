from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import extract, func
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import secrets
import re
import unicodedata
import logging

from app.core.database import get_db, SessionLocal
from app.core.auth import get_usuario_atual, exigir_permissao
from app.models.models import (
    Orcamento,
    ItemOrcamento,
    Cliente,
    Usuario,
    StatusOrcamento,
    HistoricoEdicao,
    Empresa,
    Servico,
    PagamentoFinanceiro,
    LogEmailOrcamento,
    Notificacao,
    DocumentoEmpresa,
    OrcamentoDocumento,
    StatusDocumentoEmpresa,
    ModoAgendamentoOrcamento,
)
from app.schemas.schemas import (
    OrcamentoCreate,
    OrcamentoUpdate,
    OrcamentoOut,
    DadosPIXUpdate,
    PixGerarRequest,
    PixGerarResponse,
    PixSinalUpdate,
    IAInterpretacaoRequest,
    HistoricoEdicaoOut,
    TimelineEventOut,
    DocumentoEmpresaOut,
    OrcamentoDocumentoOut,
    OrcamentoDocumentoCreate,
    OrcamentoDocumentoUpdate,
    OrcamentoDocumentosReorderRequest,
    PagamentoRecebidoBody,
    RegistrarSinalBody,
    OrcamentoListItem,
    ClienteListagemOrcamentoOut,
    ItemOrcamentoOut,
)
from decimal import Decimal
from app.services.plano_service import (
    checar_limite_orcamentos,
    exigir_ia_dashboard,
    lembretes_automaticos_habilitados,
)
from app.services import financeiro_service
from app.schemas.financeiro import PagamentoCreate
from app.models.models import TipoPagamento, OrigemRegistro
from app.services.pdf_service import gerar_pdf_orcamento
from app.services.whatsapp_service import (
    enviar_orcamento_completo,
    enviar_lembrete_cliente,
    enviar_mensagem_texto,
)
from app.services.email_service import email_habilitado, enviar_orcamento_por_email
from app.services.ia_service import interpretar_mensagem, interpretar_comando_operador
from app.services.quote_notification_service import (
    handle_quote_status_changed,
    notify_quote_expired,
)
from app.utils.desconto import (
    erro_validacao_desconto,
    resolver_max_percent_desconto,
    aplicar_desconto,
)
from app.utils.orcamento_status import texto_transicao_negada, transicao_permitida
from app.utils.orcamento_utils import (
    gerar_numero,
    renomear_numero_aprovado,
    brl_fmt,
    listar_itens_txt,
)
from app.utils.pdf_utils import get_orcamento_dict_for_pdf, get_empresa_dict_for_pdf
from app.utils.csv_utils import gerar_csv_response
from app.services.audit_service import registrar_auditoria
from app.services.orcamento_bot_service import executar_comando_bot

router = APIRouter(prefix="/orcamentos", tags=["Orçamentos"])

logger = logging.getLogger(__name__)


def _aplicar_regra_pagamento(
    orcamento: Orcamento,
    regra_id_solicitado,
    empresa_id: int,
    db: Session,
) -> None:
    """Aplica snapshot de regra de pagamento ao orçamento.

    Se regra_id_solicitado for None/0, busca a forma padrão da empresa.
    Delega lógica ao financeiro_service.aplicar_regra_no_orcamento().
    """
    from app.models.models import FormaPagamentoConfig

    regra_id = regra_id_solicitado or None
    if not regra_id:
        # Buscar padrão da empresa
        forma_padrao = (
            db.query(FormaPagamentoConfig)
            .filter_by(empresa_id=empresa_id, padrao=True, ativo=True)
            .first()
        )
        if forma_padrao:
            regra_id = forma_padrao.id

    if regra_id:
        orcamento.regra_pagamento_id = regra_id
        financeiro_service.aplicar_regra_no_orcamento(orcamento, db)


def _orcamento_para_list_item(o: Orcamento) -> OrcamentoListItem:
    """Monta DTO leve da listagem (sem PIX copia-e-cola / QR e sem pagamentos financeiros)."""
    validade_ate = None
    if o.criado_em is not None and o.validade_dias is not None:
        validade_ate = o.criado_em + timedelta(days=int(o.validade_dias))

    cli = o.cliente
    nome_cliente = (cli.nome if cli else "") or ""
    cliente_row_id = int(cli.id) if cli else int(o.cliente_id)

    itens_out = [ItemOrcamentoOut.model_validate(i) for i in (o.itens or [])]
    primeira_desc = itens_out[0].descricao if itens_out else None

    return OrcamentoListItem(
        id=o.id,
        numero=o.numero or "",
        status=o.status,
        total=o.total if o.total is not None else Decimal("0"),
        desconto=o.desconto if o.desconto is not None else Decimal("0"),
        desconto_tipo=o.desconto_tipo or "percentual",
        forma_pagamento=o.forma_pagamento,
        validade_dias=o.validade_dias if o.validade_dias is not None else 7,
        observacoes=o.observacoes,
        criado_em=o.criado_em,
        lembrete_enviado_em=o.lembrete_enviado_em,
        exigir_otp=bool(o.exigir_otp),
        regra_pagamento_id=o.regra_pagamento_id,
        regra_pagamento_nome=o.regra_pagamento_nome,
        regra_entrada_percentual=o.regra_entrada_percentual,
        regra_entrada_metodo=o.regra_entrada_metodo,
        regra_saldo_percentual=o.regra_saldo_percentual,
        regra_saldo_metodo=o.regra_saldo_metodo,
        cliente=ClienteListagemOrcamentoOut(id=cliente_row_id, nome=nome_cliente),
        cliente_id=int(o.cliente_id),
        cliente_nome=nome_cliente,
        cliente_endereco=(cli.endereco if cli else None),
        itens=itens_out,
        validade_ate=validade_ate,
        descricao_resumo=primeira_desc,
    )


def _resolver_agendamento_modo_criacao(
    solicitado: Optional[ModoAgendamentoOrcamento],
    empresa: Optional[Empresa],
) -> ModoAgendamentoOrcamento:
    """Define agendamento_modo na criação do orçamento.

    Se a empresa exige escolha explícita, o body deve trazer agendamento_modo.
    Caso contrário, valor omitido usa agendamento_modo_padrao da empresa.
    """
    if solicitado is not None:
        return solicitado
    if empresa is not None and getattr(
        empresa, "agendamento_escolha_obrigatoria", False
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Informe se haverá agendamento neste orçamento (Sim ou Não). "
                "A configuração da empresa exige escolha explícita em cada proposta."
            ),
        )
    if (
        empresa is not None
        and getattr(empresa, "agendamento_modo_padrao", None) is not None
    ):
        return empresa.agendamento_modo_padrao
    return ModoAgendamentoOrcamento.NAO_USA


@router.post("/", response_model=OrcamentoOut, status_code=status.HTTP_201_CREATED)
async def criar_orcamento(
    dados: OrcamentoCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("orcamentos", "escrita")),
):
    """Cria um novo orçamento com itens e desconto."""
    # Limite por plano: quantidade máxima de orçamentos
    if usuario.empresa:
        checar_limite_orcamentos(db, usuario.empresa)
    # Valida cliente
    cliente = (
        db.query(Cliente)
        .filter(
            Cliente.id == dados.cliente_id, Cliente.empresa_id == usuario.empresa_id
        )
        .first()
    )
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    empresa_ctx = usuario.empresa
    if empresa_ctx is None:
        empresa_ctx = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    modo_agendamento = _resolver_agendamento_modo_criacao(
        dados.agendamento_modo, empresa_ctx
    )

    # Calcula total com desconto
    subtotal = sum(item.quantidade * item.valor_unit for item in dados.itens)
    max_pct = resolver_max_percent_desconto(usuario, usuario.empresa)
    err_desconto = erro_validacao_desconto(
        subtotal, dados.desconto, dados.desconto_tipo, max_pct
    )
    if err_desconto:
        raise HTTPException(status_code=400, detail=err_desconto)
    total = aplicar_desconto(subtotal, dados.desconto, dados.desconto_tipo)

    # Cria orçamento — tenta até 3x em caso de colisão de número (race condition)
    orcamento = None
    for tentativa in range(3):
        db.rollback() if tentativa > 0 else None
        _numero, _seq = gerar_numero(usuario.empresa, db, offset=tentativa)
        orcamento = Orcamento(
            empresa_id=usuario.empresa_id,
            cliente_id=dados.cliente_id,
            criado_por_id=usuario.id,
            numero=_numero,
            sequencial_numero=_seq,
            forma_pagamento=dados.forma_pagamento,
            validade_dias=dados.validade_dias,
            observacoes=dados.observacoes,
            desconto=dados.desconto,
            desconto_tipo=dados.desconto_tipo,
            total=total,
            link_publico=secrets.token_urlsafe(24),
            agendamento_modo=modo_agendamento,
        )
        db.add(orcamento)
        try:
            db.flush()  # pega o ID antes do commit; levanta IntegrityError se número duplicado
            break
        except IntegrityError as e:
            if "ix_orcamentos" in str(e.orig) or "orcamentos_numero" in str(e.orig):
                logger.warning(
                    "Colisão de número de orçamento (tentativa %d): %s",
                    tentativa + 1,
                    e,
                )
                db.rollback()
                continue
            raise
    else:
        raise HTTPException(
            status_code=500,
            detail="Não foi possível gerar número de orçamento único. Tente novamente.",
        )

    # Cria itens
    for item_data in dados.itens:
        item = ItemOrcamento(
            orcamento_id=orcamento.id,
            servico_id=getattr(item_data, "servico_id", None),
            descricao=item_data.descricao,
            quantidade=item_data.quantidade,
            valor_unit=item_data.valor_unit,
            total=item_data.quantidade * item_data.valor_unit,
        )
        db.add(item)

    # Aplicar regra de pagamento (f002)
    _aplicar_regra_pagamento(
        orcamento, dados.regra_pagamento_id, usuario.empresa_id, db
    )

    # Registro inicial no histórico
    db.add(
        HistoricoEdicao(
            orcamento_id=orcamento.id,
            editado_por_id=usuario.id,
            descricao=f"Orçamento criado via painel (Total: R$ {total:.2f}).",
        )
    )

    db.commit()
    db.refresh(orcamento)

    return orcamento


@router.put("/{orcamento_id}", response_model=OrcamentoOut)
async def editar_orcamento(
    orcamento_id: int,
    dados: OrcamentoUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("orcamentos", "escrita")),
):
    """Edita um orçamento existente (itens, desconto e forma de pagamento)."""
    orc = (
        db.query(Orcamento)
        .filter(
            Orcamento.id == orcamento_id, Orcamento.empresa_id == usuario.empresa_id
        )
        .first()
    )
    if not orc:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")

    # Bloquear edição de orçamentos em estados finais (aprovação é um compromisso do cliente)
    _ESTADOS_BLOQUEADOS_EDICAO = {
        StatusOrcamento.APROVADO,
        StatusOrcamento.EM_EXECUCAO,
        StatusOrcamento.AGUARDANDO_PAGAMENTO,
    }
    if orc.status in _ESTADOS_BLOQUEADOS_EDICAO:
        raise HTTPException(
            status_code=409,
            detail=f"Não é possível editar orçamento com status '{orc.status.value}'. "
            "Reverta o status antes de editar.",
        )

    # Atualiza campos
    subtotal = sum(i.quantidade * i.valor_unit for i in dados.itens)
    max_pct = resolver_max_percent_desconto(usuario, usuario.empresa)
    err_desconto = erro_validacao_desconto(
        subtotal, dados.desconto, dados.desconto_tipo, max_pct
    )
    if err_desconto:
        raise HTTPException(status_code=400, detail=err_desconto)
    orc.forma_pagamento = dados.forma_pagamento
    orc.validade_dias = dados.validade_dias
    orc.observacoes = dados.observacoes
    orc.desconto = dados.desconto
    orc.desconto_tipo = dados.desconto_tipo
    orc.total = aplicar_desconto(subtotal, dados.desconto, dados.desconto_tipo)
    if dados.exigir_otp is not None:
        orc.exigir_otp = dados.exigir_otp
    if dados.agendamento_modo is not None:
        orc.agendamento_modo = dados.agendamento_modo

    # Remove itens antigos e recria
    db.query(ItemOrcamento).filter(ItemOrcamento.orcamento_id == orc.id).delete()
    for item_data in dados.itens:
        db.add(
            ItemOrcamento(
                orcamento_id=orc.id,
                servico_id=getattr(item_data, "servico_id", None),
                descricao=item_data.descricao,
                quantidade=item_data.quantidade,
                valor_unit=item_data.valor_unit,
                total=item_data.quantidade * item_data.valor_unit,
            )
        )

    # Aplicar regra de pagamento (f002) — regra_pagamento_id pode vir no PUT também
    regra_id = getattr(dados, "regra_pagamento_id", None)
    _aplicar_regra_pagamento(orc, regra_id, usuario.empresa_id, db)

    # Registra histórico de edição
    descricao_hist = f"Editado: {len(dados.itens)} item(ns), total {brl_fmt(orc.total)}"
    db.add(
        HistoricoEdicao(
            orcamento_id=orc.id,
            editado_por_id=usuario.id,
            descricao=descricao_hist,
        )
    )

    db.commit()
    db.refresh(orc)

    return orc


@router.post("/criar-pelo-texto")
async def criar_orcamento_pelo_texto(
    dados: IAInterpretacaoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("orcamentos", "escrita")),
):
    """Cria um orçamento a partir de texto em linguagem natural (usado pelo bot no dashboard)."""
    if usuario.empresa:
        exigir_ia_dashboard(usuario.empresa)
        checar_limite_orcamentos(db, usuario.empresa)
    mensagem = (dados.mensagem or "").strip()
    if not mensagem:
        return {
            "sucesso": False,
            "resposta": "Digite uma mensagem para criar o orçamento.",
        }

    interpretado = await interpretar_mensagem(mensagem)
    if interpretado.confianca < 0.5:
        return {
            "sucesso": False,
            "resposta": 'Não entendi bem. Tente assim: "Orçamento de [serviço] no valor de R$ [valor] para [nome do cliente]"',
        }

    cliente_nome = (interpretado.cliente_nome or "A definir").strip() or "A definir"
    cliente = (
        db.query(Cliente)
        .filter(
            Cliente.empresa_id == usuario.empresa_id,
            Cliente.nome.ilike(f"%{cliente_nome}%"),
        )
        .first()
    )
    if not cliente:
        cliente = Cliente(empresa_id=usuario.empresa_id, nome=cliente_nome)
        db.add(cliente)
        db.flush()

    subtotal = interpretado.valor
    desconto = interpretado.desconto or 0.0
    desconto_tipo = interpretado.desconto_tipo or "percentual"
    if desconto > 0:
        max_pct = resolver_max_percent_desconto(usuario, usuario.empresa)
        err_desconto = erro_validacao_desconto(
            subtotal, desconto, desconto_tipo, max_pct
        )
        if err_desconto:
            raise HTTPException(status_code=400, detail=err_desconto)
        if desconto_tipo == "percentual":
            total_calc = max(Decimal("0.0"), subtotal - subtotal * (desconto / 100))
        else:
            total_calc = max(Decimal("0.0"), subtotal - desconto)
    else:
        total_calc = subtotal

    validade_padrao = (
        (usuario.empresa.validade_padrao_dias or 7) if usuario.empresa else 7
    )  # #10

    agendamento_modo_ia = ModoAgendamentoOrcamento.NAO_USA
    if usuario.empresa and getattr(usuario.empresa, "agendamento_modo_padrao", None):
        agendamento_modo_ia = usuario.empresa.agendamento_modo_padrao
    if usuario.empresa and getattr(
        usuario.empresa, "agendamento_escolha_obrigatoria", False
    ):
        agendamento_modo_ia = ModoAgendamentoOrcamento.NAO_USA

    orcamento = None
    for tentativa in range(3):
        _numero, _seq = gerar_numero(usuario.empresa, db, offset=tentativa)
        orcamento = Orcamento(
            empresa_id=usuario.empresa_id,
            cliente_id=cliente.id,
            criado_por_id=usuario.id,
            numero=_numero,
            sequencial_numero=_seq,
            total=total_calc,
            forma_pagamento="pix",
            validade_dias=validade_padrao,
            observacoes=interpretado.observacoes,
            desconto=desconto,
            desconto_tipo=desconto_tipo,
            link_publico=secrets.token_urlsafe(24),
            origem_whatsapp=False,
            mensagem_ia=mensagem,
            agendamento_modo=agendamento_modo_ia,
        )
        db.add(orcamento)
        sp = db.begin_nested()
        try:
            db.flush()
            sp.commit()
            break
        except IntegrityError as e:
            sp.rollback()
            db.expunge(orcamento)
            if "uq_orcamentos_empresa_numero" in str(
                e.orig
            ) or "orcamentos_numero" in str(e.orig):
                continue
            raise
    else:
        raise HTTPException(
            status_code=500,
            detail="Não foi possível gerar número de orçamento único. Tente novamente.",
        )

    item = ItemOrcamento(
        orcamento_id=orcamento.id,
        descricao=interpretado.servico or "Serviço",
        quantidade=1,
        valor_unit=subtotal,
        total=subtotal,
    )
    db.add(item)
    db.commit()
    db.refresh(orcamento)

    background_tasks.add_task(_gerar_e_salvar_pdf, orcamento.id)

    total_fmt = (
        f"R$ {total_calc:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
    resposta = f"✅ Orçamento {orcamento.numero} criado para {cliente_nome}! Total {total_fmt}. Veja na lista acima e clique em 📄 para o PDF."
    return {
        "sucesso": True,
        "resposta": resposta,
        "orcamento": {
            "id": orcamento.id,
            "numero": orcamento.numero,
            "total": orcamento.total,
            "cliente": {"nome": cliente.nome},
        },
    }


@router.post("/comando-bot")
async def comando_bot(
    dados: IAInterpretacaoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("orcamentos", "escrita")),
):
    """Interpreta comando em linguagem natural e executa: criar, ver, aprovar, recusar, desconto, adicionar, remover, enviar, ajuda."""
    empresa = usuario.empresa if usuario else None

    # Executa comando via service
    resultado = await executar_comando_bot(
        mensagem=dados.mensagem,
        usuario=usuario,
        db=db,
        empresa=empresa,
    )

    # Gera PDF em background se orçamento foi criado
    if resultado.get("sucesso") and resultado.get("orcamento"):
        background_tasks.add_task(_gerar_e_salvar_pdf, resultado["orcamento"]["id"])

    return resultado


@router.get("/", response_model=List[OrcamentoListItem])
def listar_orcamentos(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("orcamentos", "leitura")),
    status: str = None,
    status_filtro: str = None,
    limit: int = 200,
    offset: int = 0,
):
    """Lista os orçamentos da empresa do usuário logado (payload resumido).

    Usa ``selectinload`` nos itens para evitar produto cartesiano de múltiplos
    ``joinedload`` em coleções. Pagamentos financeiros não são carregados aqui
    (use GET /orcamentos/{id} para o corpo completo e N+1 evitado com eager load).
    """
    query = (
        db.query(Orcamento)
        .options(
            joinedload(Orcamento.cliente),
            selectinload(Orcamento.itens).joinedload(ItemOrcamento.servico),
        )
        .filter(Orcamento.empresa_id == usuario.empresa_id)
    )

    # Lógica de Visibilidade: 'meus' vs 'leitura/escrita/admin'
    perms = usuario.permissoes or {}
    perm_orc = perms.get("orcamentos", "leitura")

    # Se for apenas 'meus', filtra apenas os orçamentos criados por ele
    if perm_orc == "meus" and not usuario.is_gestor and not usuario.is_superadmin:
        query = query.filter(Orcamento.criado_por_id == usuario.id)

    if status or status_filtro:
        query = query.filter(Orcamento.status == (status or status_filtro))
    rows = query.order_by(Orcamento.criado_em.desc()).limit(limit).offset(offset).all()
    return [_orcamento_para_list_item(o) for o in rows]


@router.get("/exportar/csv")
def exportar_orcamentos_csv(
    data_inicio: str = None,
    data_fim: str = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("orcamentos", "leitura")),
):
    """Exporta orçamentos da empresa em CSV."""
    query = (
        db.query(Orcamento)
        .options(
            joinedload(Orcamento.cliente),
        )
        .filter(Orcamento.empresa_id == usuario.empresa_id)
    )
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

    # Mesma visibilidade que listar_orcamentos: permissão "meus" só exporta orçamentos do usuário
    perms = usuario.permissoes or {}
    perm_orc = perms.get("orcamentos", "leitura")
    if perm_orc == "meus" and not usuario.is_gestor and not usuario.is_superadmin:
        query = query.filter(Orcamento.criado_por_id == usuario.id)

    orcamentos = query.order_by(Orcamento.criado_em.desc()).limit(10_000).all()

    header = ["Número", "Cliente", "Total", "Status", "Data criação", "Forma pagamento"]
    rows = []
    for o in orcamentos:
        data_str = o.criado_em.strftime("%d/%m/%Y %H:%M") if o.criado_em else ""
        rows.append(
            [
                o.numero or "",
                o.cliente.nome if o.cliente else "",
                f"{o.total:.2f}".replace(".", ","),
                o.status.value if o.status else "",
                data_str,
                o.forma_pagamento.value if o.forma_pagamento else "",
            ]
        )
    return gerar_csv_response(header, rows, "orcamentos")


@router.post(
    "/{orcamento_id}/duplicar",
    response_model=OrcamentoOut,
    status_code=status.HTTP_201_CREATED,
)
async def duplicar_orcamento(
    orcamento_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("orcamentos", "escrita")),
):
    """Cria um novo orçamento com os mesmos dados (cliente, itens, desconto). Novo número e data."""
    orc = (
        db.query(Orcamento)
        .filter(
            Orcamento.id == orcamento_id,
            Orcamento.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not orc:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")

    numero_novo, seq_novo = gerar_numero(usuario.empresa, db)
    novo = Orcamento(
        empresa_id=usuario.empresa_id,
        cliente_id=orc.cliente_id,
        criado_por_id=usuario.id,
        numero=numero_novo,
        sequencial_numero=seq_novo,
        status=StatusOrcamento.RASCUNHO,
        forma_pagamento=orc.forma_pagamento,
        validade_dias=orc.validade_dias,
        observacoes=orc.observacoes,
        desconto=orc.desconto,
        desconto_tipo=orc.desconto_tipo,
        total=orc.total,
        link_publico=secrets.token_urlsafe(24),
        origem_whatsapp=False,
        agendamento_modo=orc.agendamento_modo,
    )
    db.add(novo)
    db.flush()
    for item in orc.itens:
        db.add(
            ItemOrcamento(
                orcamento_id=novo.id,
                descricao=item.descricao,
                quantidade=item.quantidade,
                valor_unit=item.valor_unit,
                total=item.total,
            )
        )
    db.commit()
    db.refresh(novo)
    return novo


@router.get("/{orcamento_id}", response_model=OrcamentoOut)
def buscar_orcamento(
    orcamento_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("orcamentos", "leitura")),
):
    """Busca um orçamento pelo ID com seus itens e cliente."""
    orc = (
        db.query(Orcamento)
        .options(
            joinedload(Orcamento.cliente),
            joinedload(Orcamento.itens).joinedload(ItemOrcamento.servico),
            selectinload(Orcamento.pagamentos_financeiros).joinedload(
                PagamentoFinanceiro.forma_pagamento_config
            ),
        )
        .filter(
            Orcamento.id == orcamento_id, Orcamento.empresa_id == usuario.empresa_id
        )
        .first()
    )
    if not orc:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
    return orc


@router.get("/{orcamento_id}/documentos", response_model=List[OrcamentoDocumentoOut])
def listar_documentos_vinculados(
    orcamento_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("orcamentos", "leitura")),
):
    """Lista documentos vinculados ao orçamento."""
    orc = (
        db.query(Orcamento)
        .filter(
            Orcamento.id == orcamento_id,
            Orcamento.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not orc:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
    docs = (
        db.query(OrcamentoDocumento)
        .filter(
            OrcamentoDocumento.orcamento_id == orc.id,
        )
        .order_by(OrcamentoDocumento.ordem.asc(), OrcamentoDocumento.id.asc())
        .all()
    )
    return docs


@router.get(
    "/{orcamento_id}/documentos/disponiveis", response_model=List[DocumentoEmpresaOut]
)
def listar_documentos_disponiveis(
    orcamento_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("orcamentos", "leitura")),
    q: str | None = None,
):
    """Lista documentos da empresa disponíveis para vincular ao orçamento."""
    orc = (
        db.query(Orcamento)
        .filter(
            Orcamento.id == orcamento_id,
            Orcamento.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not orc:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")

    query = db.query(DocumentoEmpresa).filter(
        DocumentoEmpresa.empresa_id == usuario.empresa_id,
        DocumentoEmpresa.deletado_em.is_(None),
        DocumentoEmpresa.status == StatusDocumentoEmpresa.ATIVO,
    )
    if q:
        query = query.filter(DocumentoEmpresa.nome.ilike(f"%{q.strip()}%"))
    return query.order_by(DocumentoEmpresa.nome.asc()).all()


@router.post(
    "/{orcamento_id}/documentos",
    response_model=OrcamentoDocumentoOut,
    status_code=status.HTTP_201_CREATED,
)
def vincular_documento_ao_orcamento(
    orcamento_id: int,
    dados: OrcamentoDocumentoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("orcamentos", "escrita")),
):
    """Vincula um documento da empresa ao orçamento."""
    orc = (
        db.query(Orcamento)
        .filter(
            Orcamento.id == orcamento_id,
            Orcamento.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not orc:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")

    doc = (
        db.query(DocumentoEmpresa)
        .filter(
            DocumentoEmpresa.id == dados.documento_id,
            DocumentoEmpresa.empresa_id == usuario.empresa_id,
            DocumentoEmpresa.deletado_em.is_(None),
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    existente = (
        db.query(OrcamentoDocumento)
        .filter(
            OrcamentoDocumento.orcamento_id == orc.id,
            OrcamentoDocumento.documento_id == doc.id,
        )
        .first()
    )
    if existente:
        raise HTTPException(
            status_code=400, detail="Documento já está vinculado a este orçamento"
        )

    max_ordem = (
        db.query(func.max(OrcamentoDocumento.ordem))
        .filter(OrcamentoDocumento.orcamento_id == orc.id)
        .scalar()
        or 0
    )

    vinc = OrcamentoDocumento(
        orcamento_id=orc.id,
        documento_id=doc.id,
        ordem=int(max_ordem) + 1,
        exibir_no_portal=bool(dados.exibir_no_portal),
        enviar_por_email=bool(dados.enviar_por_email),
        enviar_por_whatsapp=bool(dados.enviar_por_whatsapp),
        obrigatorio=bool(dados.obrigatorio),
        documento_nome=doc.nome,
        documento_tipo=getattr(doc.tipo, "value", str(doc.tipo)),
        documento_versao=doc.versao,
        arquivo_path=doc.arquivo_path,
        arquivo_nome_original=doc.arquivo_nome_original,
        mime_type=doc.mime_type,
        tamanho_bytes=doc.tamanho_bytes,
        conteudo_html=doc.conteudo_html,
        permite_download=bool(doc.permite_download),
    )
    db.add(vinc)
    db.commit()
    db.refresh(vinc)
    return vinc


@router.patch(
    "/{orcamento_id}/documentos/{orcamento_documento_id}",
    response_model=OrcamentoDocumentoOut,
)
def atualizar_vinculo_documento(
    orcamento_id: int,
    orcamento_documento_id: int,
    dados: OrcamentoDocumentoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("orcamentos", "escrita")),
):
    """Atualiza as configurações do vínculo de documento no orçamento."""
    orc = (
        db.query(Orcamento)
        .filter(
            Orcamento.id == orcamento_id,
            Orcamento.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not orc:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")

    vinc = (
        db.query(OrcamentoDocumento)
        .filter(
            OrcamentoDocumento.id == orcamento_documento_id,
            OrcamentoDocumento.orcamento_id == orc.id,
        )
        .first()
    )
    if not vinc:
        raise HTTPException(status_code=404, detail="Vínculo não encontrado")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(vinc, campo, valor)

    db.commit()
    db.refresh(vinc)
    return vinc


@router.put(
    "/{orcamento_id}/documentos/ordem", response_model=List[OrcamentoDocumentoOut]
)
def reordenar_documentos_vinculados(
    orcamento_id: int,
    dados: OrcamentoDocumentosReorderRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("orcamentos", "escrita")),
):
    """Reordena os documentos vinculados ao orçamento."""
    orc = (
        db.query(Orcamento)
        .filter(
            Orcamento.id == orcamento_id,
            Orcamento.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not orc:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")

    vincs = (
        db.query(OrcamentoDocumento)
        .filter(
            OrcamentoDocumento.orcamento_id == orc.id,
        )
        .all()
    )
    mapa = {v.id: v for v in vincs}
    ids = dados.ids_em_ordem or []
    if set(ids) != set(mapa.keys()):
        raise HTTPException(
            status_code=400, detail="Lista de IDs inválida para reordenação"
        )

    for idx, vid in enumerate(ids, start=1):
        mapa[vid].ordem = idx

    db.commit()
    return (
        db.query(OrcamentoDocumento)
        .filter(
            OrcamentoDocumento.orcamento_id == orc.id,
        )
        .order_by(OrcamentoDocumento.ordem.asc(), OrcamentoDocumento.id.asc())
        .all()
    )


@router.post(
    "/{orcamento_id}/documentos/{orcamento_documento_id}/sincronizar",
    response_model=OrcamentoDocumentoOut,
)
def sincronizar_documento_viculado(
    orcamento_id: int,
    orcamento_documento_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("orcamentos", "escrita")),
):
    """
    Atualiza o snapshot do documento no orçamento para a versão mais recente do template da empresa.
    """
    vinc = (
        db.query(OrcamentoDocumento)
        .join(Orcamento)
        .filter(
            OrcamentoDocumento.id == orcamento_documento_id,
            Orcamento.id == orcamento_id,
            Orcamento.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not vinc:
        raise HTTPException(
            status_code=404, detail="Vínculo de documento não encontrado"
        )

    if not vinc.documento_id:
        raise HTTPException(
            status_code=400,
            detail="Não é possível sincronizar: o template original foi deletado.",
        )

    doc = (
        db.query(DocumentoEmpresa)
        .filter(
            DocumentoEmpresa.id == vinc.documento_id,
            DocumentoEmpresa.empresa_id == usuario.empresa_id,
            DocumentoEmpresa.deletado_em.is_(None),
        )
        .first()
    )
    if not doc:
        raise HTTPException(
            status_code=404, detail="Template original não encontrado ou arquivado."
        )

    # Atualiza o snapshot
    vinc.documento_nome = doc.nome
    vinc.documento_tipo = getattr(doc.tipo, "value", str(doc.tipo))
    vinc.documento_versao = doc.versao
    vinc.arquivo_path = doc.arquivo_path
    vinc.arquivo_nome_original = doc.arquivo_nome_original
    vinc.mime_type = doc.mime_type
    vinc.tamanho_bytes = doc.tamanho_bytes
    vinc.conteudo_html = doc.conteudo_html
    vinc.permite_download = bool(doc.permite_download)

    db.commit()
    db.refresh(vinc)
    return vinc


@router.delete(
    "/{orcamento_id}/documentos/{orcamento_documento_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remover_documento_do_orcamento(
    orcamento_id: int,
    orcamento_documento_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("orcamentos", "escrita")),
):
    """Remove o vínculo de um documento do orçamento."""
    orc = (
        db.query(Orcamento)
        .filter(
            Orcamento.id == orcamento_id,
            Orcamento.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not orc:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")

    vinc = (
        db.query(OrcamentoDocumento)
        .filter(
            OrcamentoDocumento.id == orcamento_documento_id,
            OrcamentoDocumento.orcamento_id == orc.id,
        )
        .first()
    )
    if not vinc:
        raise HTTPException(status_code=404, detail="Vínculo não encontrado")

    db.delete(vinc)
    db.commit()
    return None


@router.post("/{orcamento_id}/enviar-whatsapp")
async def enviar_whatsapp(
    orcamento_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("orcamentos", "escrita")),
):
    """Envia o orçamento pelo WhatsApp para o cliente."""
    orc = (
        db.query(Orcamento)
        .filter(
            Orcamento.id == orcamento_id, Orcamento.empresa_id == usuario.empresa_id
        )
        .first()
    )
    if not orc:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
    if not orc.cliente.telefone:
        raise HTTPException(
            status_code=400,
            detail=f"cliente_sem_telefone:{orc.cliente.id}:{orc.cliente.nome}",
        )

    from app.core.config import settings

    base_url = (settings.APP_URL or "").rstrip("/")
    docs_whats = (
        db.query(OrcamentoDocumento)
        .filter(
            OrcamentoDocumento.orcamento_id == orc.id,
            OrcamentoDocumento.enviar_por_whatsapp == True,
        )
        .order_by(OrcamentoDocumento.ordem.asc(), OrcamentoDocumento.id.asc())
        .all()
    )

    from app.services.pdf_service import gerar_pdf_orcamento

    orc_dict = get_orcamento_dict_for_pdf(orc, db)
    empresa_dict = get_empresa_dict_for_pdf(orc.empresa)

    # Adicionar campo específico para WA que não está no utilitário genérico de PDF
    orc_dict["cliente_nome"] = orc.cliente.nome
    orc_dict["empresa_nome"] = orc.empresa.nome
    orc_dict["vendedor_nome"] = orc.criado_por.nome if orc.criado_por else None
    orc_dict["documentos_whatsapp"] = [
        {
            "nome": d.documento_nome,
            "url": f"{base_url}/o/{orc.link_publico}/documentos/{d.id}",
        }
        for d in docs_whats
    ]

    # Gerar PDF apenas se configurado
    pdf_bytes = b""
    wa_anexo_ativo = getattr(orc.empresa, "enviar_pdf_whatsapp", False)
    logger.info(
        f"[WA] Checando anexo PDF: empresa_id={orc.empresa_id}, flag={wa_anexo_ativo}"
    )

    if wa_anexo_ativo:
        try:
            pdf_bytes = gerar_pdf_orcamento(orc_dict, empresa_dict)
            logger.info(
                f"[WA] PDF gerado com {len(pdf_bytes)} bytes para orçamento {orc.numero}"
            )
        except Exception as e:
            logger.error(f"Erro ao gerar PDF para WhatsApp: {e}")
            pdf_bytes = b""
    else:
        logger.info(
            f"[WA] Anexo PDF desativado para empresa {orc.empresa_id}. Enviando apenas texto."
        )

    enviado = await enviar_orcamento_completo(
        telefone=orc.cliente.telefone,
        orcamento=orc_dict,
        pdf_bytes=pdf_bytes,
        empresa=orc.empresa,
    )

    if not enviado:
        raise HTTPException(
            status_code=502,
            detail="Falha ao enviar orçamento pelo WhatsApp. Verifique a conexão e tente novamente.",
        )

    # Só muda para ENVIADO se estiver em RASCUNHO; caso contrário mantém o status atual
    if orc.status == StatusOrcamento.RASCUNHO:
        orc.status = StatusOrcamento.ENVIADO
        orc.enviado_em = datetime.now(timezone.utc)
        _registrar_mudanca_status(
            db,
            orc.id,
            StatusOrcamento.ENVIADO,
            editado_por_id=usuario.id,
            descricao="Enviado por WhatsApp pelo painel.",
        )
    else:
        db.add(
            HistoricoEdicao(
                orcamento_id=orc.id,
                editado_por_id=usuario.id,
                descricao="Reenviado por WhatsApp pelo painel.",
            )
        )
    db.commit()
    return {"mensagem": "Orçamento enviado com sucesso via WhatsApp"}


@router.post("/{orcamento_id}/enviar-email")
async def enviar_email(
    orcamento_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("orcamentos", "escrita")),
):
    """Envia o orçamento por e-mail ao cliente. O anexo PDF é opcional por configuração da empresa."""
    if not email_habilitado():
        raise HTTPException(
            status_code=503,
            detail="Envio por e-mail não está configurado. Configure BREVO_API_KEY (Railway) ou SMTP nas variáveis de ambiente.",
        )
    orc = (
        db.query(Orcamento)
        .filter(
            Orcamento.id == orcamento_id,
            Orcamento.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not orc:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
    email_cliente = (orc.cliente.email or "").strip()
    if not email_cliente:
        raise HTTPException(
            status_code=400,
            detail="Cliente sem e-mail cadastrado. Cadastre o e-mail do cliente para enviar o orçamento.",
        )

    anexar_pdf_ativo = bool(getattr(orc.empresa, "anexar_pdf_email", False))
    pdf_bytes: bytes | None = None
    if anexar_pdf_ativo:
        try:
            orc_dict = get_orcamento_dict_for_pdf(orc, db)
            empresa_dict = get_empresa_dict_for_pdf(orc.empresa)
            pdf_bytes = gerar_pdf_orcamento(orc_dict, empresa_dict)
        except Exception as e:
            logging.warning(
                "Falha ao preparar PDF anexo para orçamento %s; envio seguirá sem anexo. Erro: %s",
                orc.numero,
                e,
            )
            pdf_bytes = None
    anexar_pdf_final = bool(anexar_pdf_ativo and pdf_bytes)

    # Registra log do envio
    log_email = LogEmailOrcamento(
        orcamento_id=orc.id,
        destinatario=email_cliente,
        status="pendente",
        pdf_anexado=anexar_pdf_final,
    )
    db.add(log_email)
    db.flush()  # pega o ID antes do commit
    log_email_id = log_email.id

    # Agenda envio em background (não bloqueia a resposta)
    validade_data = datetime.now() + timedelta(days=orc.validade_dias or 7)
    validade_texto = validade_data.strftime("%d/%m/%Y")
    contato_prestador = (orc.empresa.telefone or "").strip() or None
    contato_email = (orc.empresa.email or "").strip() or None
    responsavel_nome = (
        (orc.criado_por.nome or "").strip()
        if getattr(orc, "criado_por", None) and getattr(orc.criado_por, "nome", None)
        else None
    )
    link_pdf = (orc.pdf_url or "").strip() or None
    assinatura_email = (
        getattr(orc.empresa, "assinatura_email", None) or ""
    ).strip() or None
    background_tasks.add_task(
        _enviar_email_background,
        orcamento_id=orc.id,
        email_cliente=email_cliente,
        cliente_nome=orc.cliente.nome,
        numero_orcamento=orc.numero,
        empresa_nome=orc.empresa.nome,
        link_publico=orc.link_publico or "",
        pdf_bytes=pdf_bytes,
        anexar_pdf=anexar_pdf_final,
        log_email_id=log_email_id,
        validade_texto=validade_texto,
        valor_total=float(orc.total) if orc.total is not None else None,
        contato_prestador=contato_prestador,
        contato_email=contato_email,
        responsavel_nome=responsavel_nome,
        link_pdf=link_pdf,
        assinatura_email=assinatura_email,
    )

    # Só muda para ENVIADO se estiver em RASCUNHO; caso contrário mantém o status atual
    if orc.status == StatusOrcamento.RASCUNHO:
        orc.status = StatusOrcamento.ENVIADO
        _registrar_mudanca_status(
            db,
            orc.id,
            StatusOrcamento.ENVIADO,
            editado_por_id=usuario.id,
            descricao="Envio por e-mail solicitado (processamento em background).",
        )
    else:
        db.add(
            HistoricoEdicao(
                orcamento_id=orc.id,
                editado_por_id=usuario.id,
                descricao="Reenviado por e-mail pelo painel.",
            )
        )
    db.commit()
    return {
        "mensagem": "E-mail será enviado em breve. Você pode acompanhar o status no histórico."
    }


@router.patch("/{orcamento_id}/status")
async def atualizar_status(
    orcamento_id: int,
    novo_status: StatusOrcamento,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("orcamentos", "escrita")),
):
    """Atualiza o status do orçamento (ex.: Rascunho → Enviado ou Aprovado; Enviado → Aprovado)."""
    orc = (
        db.query(Orcamento)
        .filter(
            Orcamento.id == orcamento_id, Orcamento.empresa_id == usuario.empresa_id
        )
        .with_for_update()
        .first()
    )
    if not orc:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")

    old_status = orc.status
    if not transicao_permitida(old_status, novo_status):
        raise HTTPException(
            status_code=400,
            detail=texto_transicao_negada(old_status, novo_status, para_bot=False),
        )

    orc.status = novo_status
    _registrar_mudanca_status(
        db,
        orc.id,
        novo_status,
        editado_por_id=usuario.id,
        descricao=f"Status alterado de {old_status.value} para {novo_status.value} (painel).",
    )
    registrar_auditoria(
        db=db,
        usuario=usuario,
        acao=f"orcamento_{novo_status.value.lower()}",
        recurso="orcamento",
        recurso_id=str(orc.id),
        detalhes={
            "numero": orc.numero,
            "status_anterior": old_status.value,
            "novo_status": novo_status.value,
        },
        request=request,
    )
    # Cria contas a receber ao aprovar (idempotente)
    # A exceção PROPAGA — se falhar, o orçamento NÃO deve ser aprovado sem parcelas.
    if novo_status == StatusOrcamento.APROVADO:
        financeiro_service.criar_contas_receber_aprovacao(orc, usuario.empresa_id, db)
        try:
            from app.services.agendamento_auto_service import (
                processar_agendamento_apos_aprovacao,
            )

            processar_agendamento_apos_aprovacao(
                db, orc, canal="manual", usuario_id=usuario.id
            )
        except Exception:
            logger.exception(
                "Falha ao criar agendamento automático (orcamento_id=%s)", orc.id
            )
    db.commit()
    db.refresh(orc)
    await handle_quote_status_changed(
        db=db,
        quote=orc,
        old_status=old_status,
        new_status=orc.status,
        source="manual_status_update",
    )
    return {"mensagem": f"Status atualizado para {novo_status}"}


@router.get("/{orcamento_id}/historico", response_model=List[HistoricoEdicaoOut])
def historico_orcamento(
    orcamento_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("orcamentos", "leitura")),
):
    """Retorna o histórico de edições de um orçamento."""
    orc = (
        db.query(Orcamento)
        .filter(
            Orcamento.id == orcamento_id, Orcamento.empresa_id == usuario.empresa_id
        )
        .first()
    )
    if not orc:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")

    registros = (
        db.query(HistoricoEdicao)
        .filter(HistoricoEdicao.orcamento_id == orcamento_id)
        .order_by(HistoricoEdicao.editado_em.desc())
        .all()
    )

    # Monta a saída incluindo o nome do editor
    return [
        HistoricoEdicaoOut(
            id=r.id,
            editado_por_nome=r.editado_por.nome if r.editado_por else "Sistema",
            editado_em=r.editado_em,
            descricao=r.descricao,
        )
        for r in registros
    ]


@router.get("/timeline/recent")
def timeline_recent(
    limit: int = 14,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("orcamentos", "leitura")),
):
    """Retorna os N eventos mais recentes de todos os orçamentos da empresa (dashboard global)."""
    orcs = (
        db.query(Orcamento)
        .options(
            joinedload(Orcamento.historico).joinedload(HistoricoEdicao.editado_por),
            joinedload(Orcamento.criado_por),
            joinedload(Orcamento.cliente),
            joinedload(Orcamento.logs_email),
        )
        .filter(Orcamento.empresa_id == usuario.empresa_id)
        .order_by(Orcamento.criado_em.desc())
        .limit(20)
        .all()
    )

    eventos = []
    for orc in orcs:
        orc_id = orc.id
        orc_num = orc.numero or f"#{orc_id}"

        if orc.criado_em:
            eventos.append(
                {
                    "tipo": "criado",
                    "timestamp": orc.criado_em,
                    "titulo": "Orçamento criado",
                    "detalhe": None,
                    "autor": orc.criado_por.nome if orc.criado_por else "Sistema",
                    "orcamentoId": orc_id,
                    "orcamentoNumero": orc_num,
                }
            )
        if orc.enviado_em:
            eventos.append(
                {
                    "tipo": "enviado",
                    "timestamp": orc.enviado_em,
                    "titulo": "Proposta enviada via WhatsApp",
                    "detalhe": None,
                    "autor": None,
                    "orcamentoId": orc_id,
                    "orcamentoNumero": orc_num,
                }
            )
        if orc.visualizado_em:
            eventos.append(
                {
                    "tipo": "visualizado",
                    "timestamp": orc.visualizado_em,
                    "titulo": "Cliente abriu a proposta",
                    "detalhe": None,
                    "autor": None,
                    "orcamentoId": orc_id,
                    "orcamentoNumero": orc_num,
                }
            )
        if orc.aceite_em:
            eventos.append(
                {
                    "tipo": "aprovado",
                    "timestamp": orc.aceite_em,
                    "titulo": "Proposta aceita pelo cliente",
                    "detalhe": orc.aceite_mensagem or None,
                    "autor": orc.aceite_nome,
                    "orcamentoId": orc_id,
                    "orcamentoNumero": orc_num,
                }
            )
        if orc.recusa_em:
            eventos.append(
                {
                    "tipo": "recusado",
                    "timestamp": orc.recusa_em,
                    "titulo": "Proposta recusada pelo cliente",
                    "detalhe": orc.recusa_motivo or None,
                    "autor": None,
                    "orcamentoId": orc_id,
                    "orcamentoNumero": orc_num,
                }
            )
        for log in orc.logs_email or []:
            if log.status == "enviado":
                eventos.append(
                    {
                        "tipo": "email_enviado",
                        "timestamp": log.enviado_em or log.criado_em,
                        "titulo": "Proposta enviada por e-mail",
                        "detalhe": f"Para: {log.destinatario}",
                        "autor": None,
                        "orcamentoId": orc_id,
                        "orcamentoNumero": orc_num,
                    }
                )

    eventos.sort(
        key=lambda e: e["timestamp"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return eventos[:limit]


@router.get("/{orcamento_id}/timeline", response_model=List[TimelineEventOut])
def timeline_orcamento(
    orcamento_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("orcamentos", "leitura")),
):
    """Retorna a linha do tempo unificada de um orçamento (criação, envio, visualização, aceite, recusa, edições…)."""
    orc = (
        db.query(Orcamento)
        .options(
            joinedload(Orcamento.historico).joinedload(HistoricoEdicao.editado_por),
            joinedload(Orcamento.criado_por),
            joinedload(Orcamento.cliente),
            joinedload(Orcamento.logs_email),
        )
        .filter(
            Orcamento.id == orcamento_id, Orcamento.empresa_id == usuario.empresa_id
        )
        .first()
    )
    if not orc:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")

    eventos: list[TimelineEventOut] = []

    # 1. CRIADO
    if orc.criado_em:
        eventos.append(
            TimelineEventOut(
                tipo="criado",
                timestamp=orc.criado_em,
                titulo="Orçamento criado",
                autor=orc.criado_por.nome if orc.criado_por else "Sistema",
            )
        )

    # 2. ENVIADO via WhatsApp
    if orc.enviado_em:
        eventos.append(
            TimelineEventOut(
                tipo="enviado",
                timestamp=orc.enviado_em,
                titulo="Proposta enviada via WhatsApp",
            )
        )

    # 3. VISUALIZADO pelo cliente (primeira abertura)
    if orc.visualizado_em:
        detalhe = None
        if orc.visualizacoes and orc.visualizacoes > 1:
            detalhe = f"Aberto {orc.visualizacoes}× no total"
        eventos.append(
            TimelineEventOut(
                tipo="visualizado",
                timestamp=orc.visualizado_em,
                titulo="Cliente abriu a proposta",
                detalhe=detalhe,
            )
        )

    # 4. LEMBRETE enviado ao cliente
    if orc.lembrete_enviado_em:
        eventos.append(
            TimelineEventOut(
                tipo="lembrete",
                timestamp=orc.lembrete_enviado_em,
                titulo="Lembrete enviado ao cliente",
            )
        )

    # 5. EDIÇÕES (HistoricoEdicao)
    for h in orc.historico or []:
        eventos.append(
            TimelineEventOut(
                tipo="editado",
                timestamp=h.editado_em,
                titulo="Orçamento editado",
                detalhe=h.descricao,
                autor=h.editado_por.nome if h.editado_por else "Sistema",
            )
        )

    # 6. APROVADO pelo cliente
    if orc.aceite_em:
        eventos.append(
            TimelineEventOut(
                tipo="aprovado",
                timestamp=orc.aceite_em,
                titulo="Proposta aceita pelo cliente",
                detalhe=orc.aceite_mensagem or None,
                autor=orc.aceite_nome,
            )
        )

    # 7. RECUSADO pelo cliente
    if orc.recusa_em:
        eventos.append(
            TimelineEventOut(
                tipo="recusado",
                timestamp=orc.recusa_em,
                titulo="Proposta recusada pelo cliente",
                detalhe=orc.recusa_motivo or None,
            )
        )
    elif orc.status == StatusOrcamento.RECUSADO and not orc.recusa_em:
        # Legado: recusado antes do campo recusa_em existir — usa criado_em como fallback
        eventos.append(
            TimelineEventOut(
                tipo="recusado",
                timestamp=orc.aceite_em
                or orc.criado_em,  # melhor estimativa disponível
                titulo="Proposta recusada pelo cliente",
                detalhe=orc.recusa_motivo or None,
            )
        )

    # 8. EXPIRADO (timestamp calculado)
    if orc.status == StatusOrcamento.EXPIRADO and orc.criado_em and orc.validade_dias:
        criado = orc.criado_em
        if criado.tzinfo is None:
            criado = criado.replace(tzinfo=timezone.utc)
        expira_em = criado + timedelta(days=orc.validade_dias)
        eventos.append(
            TimelineEventOut(
                tipo="expirado",
                timestamp=expira_em,
                titulo="Orçamento expirado",
                detalhe=f"Proposta venceu após {orc.validade_dias} dias",
            )
        )

    # 8.1 Notificação interna de aprovação enviada por WhatsApp (idempotente)
    if getattr(orc, "approved_notification_sent_at", None):
        eventos.append(
            TimelineEventOut(
                tipo="notif_aprovacao_whatsapp",
                timestamp=orc.approved_notification_sent_at,
                titulo="Notificação interna de aprovação enviada por WhatsApp",
            )
        )

    # 8.2 Solicitações de ajuste pelo cliente (link público)
    notifs_ajuste = (
        db.query(Notificacao)
        .filter(Notificacao.orcamento_id == orc.id, Notificacao.tipo == "ajuste")
        .order_by(Notificacao.criado_em.asc())
        .all()
    )
    for notif in notifs_ajuste:
        eventos.append(
            TimelineEventOut(
                tipo="ajuste",
                timestamp=notif.criado_em,
                titulo="Cliente solicitou ajuste na proposta",
                detalhe=notif.mensagem or None,
            )
        )

    # 8.3 Eventos de documentos vinculados ao orçamento
    docs_vinculados = (
        db.query(OrcamentoDocumento)
        .filter(OrcamentoDocumento.orcamento_id == orc.id)
        .order_by(OrcamentoDocumento.criado_em.asc())
        .all()
    )
    for doc in docs_vinculados:
        # Documento vinculado
        if doc.criado_em:
            eventos.append(
                TimelineEventOut(
                    tipo="documento_vinculado",
                    timestamp=doc.criado_em,
                    titulo=f"Documento anexado: {doc.documento_nome}",
                    detalhe=f"Tipo: {doc.documento_tipo or 'N/A'}",
                    indicador="Obrigatório" if doc.obrigatorio else None,
                )
            )
        # Documento visualizado pelo cliente
        if doc.visualizado_em:
            eventos.append(
                TimelineEventOut(
                    tipo="documento_visualizado",
                    timestamp=doc.visualizado_em,
                    titulo=f"Cliente visualizou: {doc.documento_nome}",
                )
            )
        # Documento aceito pelo cliente (marcou checkbox obrigatório)
        if doc.aceito_em:
            eventos.append(
                TimelineEventOut(
                    tipo="documento_aceito",
                    timestamp=doc.aceito_em,
                    titulo=f"Cliente aceitou documento: {doc.documento_nome}",
                )
            )

    # 9. ENVIO POR E-MAIL (histórico de envio — lido via relationship logs_email)
    logs_email = sorted(orc.logs_email or [], key=lambda x: x.criado_em or x.id)
    for log in logs_email:
        indicador = "Com anexo" if getattr(log, "pdf_anexado", False) else "Sem anexo"
        if log.status == "enviado":
            eventos.append(
                TimelineEventOut(
                    tipo="email_enviado",
                    timestamp=log.enviado_em or log.criado_em,
                    titulo="Proposta enviada por e-mail",
                    detalhe=f"Destinatário: {log.destinatario}",
                    indicador=indicador,
                )
            )
        elif log.status == "erro":
            eventos.append(
                TimelineEventOut(
                    tipo="email_erro",
                    timestamp=log.criado_em,
                    titulo="Falha no envio por e-mail",
                    detalhe=log.mensagem_erro or f"Destinatário: {log.destinatario}",
                    indicador=indicador,
                )
            )
        else:
            eventos.append(
                TimelineEventOut(
                    tipo="email_pendente",
                    timestamp=log.criado_em,
                    titulo="Envio por e-mail em processamento",
                    detalhe=f"Destinatário: {log.destinatario}",
                    indicador=indicador,
                )
            )

    # Ordena cronologicamente
    eventos.sort(key=lambda e: e.timestamp)
    return eventos


# ── PIX E PAGAMENTO (v9) ───────────────────────────────────────────────────


@router.patch("/{orcamento_id}/pix", response_model=OrcamentoOut)
async def atualizar_pix_orcamento(
    orcamento_id: int,
    dados: DadosPIXUpdate,
    current_user: Usuario = Depends(exigir_permissao("orcamentos", "escrita")),
    db: Session = Depends(get_db),
):
    """
    Atualizar dados PIX de um orçamento e gerar QR code dinamicamente.
    """
    orcamento = (
        db.query(Orcamento)
        .options(
            joinedload(Orcamento.cliente),
            joinedload(Orcamento.itens).joinedload(ItemOrcamento.servico),
            joinedload(Orcamento.pagamentos_financeiros),
            joinedload(Orcamento.criado_por),
        )
        .filter(Orcamento.id == orcamento_id)
        .first()
    )

    if not orcamento:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")

    # Validar permissão (deve ser proprietário ou admin)
    if orcamento.criado_por_id != current_user.id and not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Sem permissão")

    # Atualizar dados
    orcamento.pix_chave = dados.pix_chave
    orcamento.pix_tipo = dados.pix_tipo
    orcamento.pix_titular = dados.pix_titular

    # Gerar payload EMV BRCode e QR code — usa valor do sinal se configurado
    financeiro_service.regenerar_pix_orcamento(orcamento)

    db.commit()
    db.refresh(orcamento)

    return OrcamentoOut.from_orm(orcamento)


@router.post("/{orcamento_id}/pix/gerar", response_model=PixGerarResponse)
async def gerar_qrcode_pix_preview(
    orcamento_id: int,
    dados: PixGerarRequest,
    current_user: Usuario = Depends(exigir_permissao("orcamentos", "escrita")),
    db: Session = Depends(get_db),
):
    """
    Gera QR code PIX para um valor específico (sinal ou total) sem persistir no banco.
    Requer que o orçamento já tenha PIX configurado (pix_chave).
    """
    orcamento = db.query(Orcamento).filter(Orcamento.id == orcamento_id).first()
    if not orcamento:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
    if orcamento.criado_por_id != current_user.id and not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Sem permissão")
    if not orcamento.pix_chave:
        raise HTTPException(
            status_code=400, detail="PIX não configurado neste orçamento"
        )

    from app.services.pix_service import gerar_qrcode_pix, gerar_payload_pix

    payload = gerar_payload_pix(
        orcamento.pix_chave, orcamento.pix_titular, valor=dados.valor
    )
    qrcode = gerar_qrcode_pix(
        orcamento.pix_chave, orcamento.pix_titular, valor=dados.valor
    )

    return PixGerarResponse(qrcode=qrcode, payload=payload, valor=dados.valor)


@router.patch("/{orcamento_id}/pix/sinal", response_model=OrcamentoOut)
async def salvar_sinal_pix(
    orcamento_id: int,
    dados: PixSinalUpdate,
    current_user: Usuario = Depends(exigir_permissao("orcamentos", "escrita")),
    db: Session = Depends(get_db),
):
    """
    Salva o valor do sinal PIX no orçamento e regenera o QR Code/payload armazenado.
    Se valor_sinal_pix for None, limpa o sinal e regenera QR para o total.
    Requer que o orçamento já tenha PIX configurado (pix_chave).
    """
    orcamento = (
        db.query(Orcamento)
        .options(
            joinedload(Orcamento.cliente),
            joinedload(Orcamento.itens).joinedload(ItemOrcamento.servico),
            joinedload(Orcamento.pagamentos_financeiros),
            joinedload(Orcamento.criado_por),
        )
        .filter(Orcamento.id == orcamento_id)
        .first()
    )
    if not orcamento:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
    if orcamento.criado_por_id != current_user.id and not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Sem permissão")
    if not orcamento.pix_chave:
        raise HTTPException(
            status_code=400,
            detail="PIX não configurado neste orçamento. Configure a chave PIX primeiro.",
        )

    orcamento.valor_sinal_pix = dados.valor_sinal_pix
    financeiro_service.regenerar_pix_orcamento(orcamento, valor=dados.valor_sinal_pix)

    db.commit()
    db.refresh(orcamento)
    return OrcamentoOut.from_orm(orcamento)


@router.post("/{orcamento_id}/pagamento-recebido", response_model=OrcamentoOut)
async def marcar_pagamento_recebido(
    orcamento_id: int,
    body: PagamentoRecebidoBody = None,
    current_user: Usuario = Depends(exigir_permissao("orcamentos", "escrita")),
    db: Session = Depends(get_db),
):
    """
    Marcar orçamento como pagamento recebido (confirmação manual pelo operador).
    Atualiza status E cria registro em pagamentos_financeiros para rastreabilidade.
    Body opcional: { valor, tipo, forma_pagamento_id }
    """
    orcamento = (
        db.query(Orcamento)
        .options(
            joinedload(Orcamento.cliente),
            joinedload(Orcamento.itens).joinedload(ItemOrcamento.servico),
            joinedload(Orcamento.pagamentos_financeiros),
            joinedload(Orcamento.criado_por),
        )
        .filter(Orcamento.id == orcamento_id)
        .first()
    )

    if not orcamento:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")

    # Validar permissão (deve ser proprietário ou admin)
    if orcamento.criado_por_id != current_user.id and not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Sem permissão")

    # ── Registrar no módulo financeiro ──────────────────────────────────────
    try:
        # Calcular saldo devedor (total - pagamentos já confirmados)
        pagamentos_confirmados = [
            p
            for p in orcamento.pagamentos_financeiros
            if p.status.value == "confirmado"
        ]
        total_pago = sum(Decimal(str(p.valor)) for p in pagamentos_confirmados)
        saldo = Decimal(str(orcamento.total)) - total_pago

        # Usa valor do body ou saldo devedor
        valor_registrar = (body.valor if body and body.valor else None) or saldo
        tipo_str = (body.tipo if body and body.tipo else None) or "quitacao"
        forma_id = body.forma_pagamento_id if body else None

        # Idempotência: não duplicar se já existe pagamento do mesmo tipo/valor/data
        from datetime import date as date_type

        hoje = date_type.today()
        ja_registrado = any(
            Decimal(str(p.valor)) == valor_registrar and p.tipo.value == tipo_str
            for p in pagamentos_confirmados
        )

        if valor_registrar > 0 and not ja_registrado:
            try:
                tipo_enum = TipoPagamento(tipo_str)
            except ValueError:
                tipo_enum = TipoPagamento.QUITACAO

            dados_pg = PagamentoCreate(
                orcamento_id=orcamento_id,
                valor=valor_registrar,
                tipo=tipo_enum,
                forma_pagamento_id=forma_id,
                data_pagamento=hoje,
                origem=OrigemRegistro.MANUAL,
                observacao="Confirmado pelo operador via dashboard",
            )
            financeiro_service.registrar_pagamento(
                empresa_id=orcamento.empresa_id,
                dados=dados_pg,
                usuario=current_user,
                db=db,
            )
    except Exception as e:
        logger.warning(
            "Falha ao registrar PagamentoFinanceiro para ORC %s: %s", orcamento_id, e
        )
        # Não bloqueia: o endpoint principal já funcionou

    db.commit()
    db.refresh(orcamento)

    return OrcamentoOut.from_orm(orcamento)


@router.post("/{orcamento_id}/registrar-sinal", status_code=201)
async def registrar_sinal_recebido(
    orcamento_id: int,
    body: RegistrarSinalBody,
    current_user: Usuario = Depends(exigir_permissao("orcamentos", "escrita")),
    db: Session = Depends(get_db),
):
    """
    Registra o sinal/entrada como recebido no módulo financeiro, sem marcar o orçamento como quitado.
    Chamado quando o operador confirma que o cliente pagou o sinal PIX.
    """
    orcamento = db.query(Orcamento).filter(Orcamento.id == orcamento_id).first()
    if not orcamento:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
    if orcamento.criado_por_id != current_user.id and not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Sem permissão")

    from datetime import date as date_type

    # Idempotência: não duplicar sinal do mesmo valor no mesmo dia
    pagamentos_confirmados = [
        p
        for p in orcamento.pagamentos_financeiros
        if p.status.value == "confirmado" and p.tipo.value == "sinal"
    ]
    ja_registrado = any(
        abs(Decimal(str(p.valor)) - body.valor) < Decimal("0.01")
        for p in pagamentos_confirmados
    )
    if ja_registrado:
        return {"detail": "Sinal já registrado.", "already_exists": True}

    dados_pg = PagamentoCreate(
        orcamento_id=orcamento_id,
        valor=body.valor,
        tipo=TipoPagamento.SINAL,
        data_pagamento=date_type.today(),
        origem=OrigemRegistro.MANUAL,
        observacao="Sinal PIX confirmado pelo operador",
    )
    with db.begin_nested():
        pagamento = financeiro_service.registrar_pagamento(
            empresa_id=orcamento.empresa_id,
            dados=dados_pg,
            usuario=current_user,
            db=db,
        )
    db.commit()
    db.refresh(pagamento)
    return {
        "detail": "Sinal registrado com sucesso.",
        "pagamento_id": pagamento.id,
        "valor": float(pagamento.valor),
    }


# ── HELPERS ────────────────────────────────────────────────────────────────


def _registrar_mudanca_status(
    db: Session,
    orcamento_id: int,
    novo_status: StatusOrcamento,
    editado_por_id: int | None = None,
    descricao: str | None = None,
) -> None:
    """Registra mudança de status no histórico para auditoria (editado_por_id=None = Sistema)."""
    desc = descricao or f"Status alterado para {novo_status.value}"
    db.add(
        HistoricoEdicao(
            orcamento_id=orcamento_id, editado_por_id=editado_por_id, descricao=desc
        )
    )


def _marcar_expirados(db: Session, empresa_id: int) -> None:
    """Marca como EXPIRADO orçamentos vencidos que ainda estão em rascunho ou enviado."""
    agora = datetime.now(timezone.utc)
    candidatos = (
        db.query(Orcamento)
        .options(
            joinedload(Orcamento.cliente),
            joinedload(Orcamento.criado_por),
        )
        .filter(
            Orcamento.empresa_id == empresa_id,
            Orcamento.status.in_([StatusOrcamento.RASCUNHO, StatusOrcamento.ENVIADO]),
        )
        .all()
    )
    atualizou = False
    for orc in candidatos:
        if orc.criado_em and orc.validade_dias:
            # Garante que criado_em seja timezone-aware
            criado = orc.criado_em
            if criado.tzinfo is None:
                from datetime import timezone as _tz

                criado = criado.replace(tzinfo=_tz.utc)
            expira = criado + timedelta(days=orc.validade_dias)
            if expira < agora:
                orc.status = StatusOrcamento.EXPIRADO
                _registrar_mudanca_status(
                    db,
                    orc.id,
                    StatusOrcamento.EXPIRADO,
                    editado_por_id=None,
                    descricao="Orçamento expirado automaticamente (validade vencida).",
                )
                notify_quote_expired(db, orc, source="auto_expiration")
                atualizou = True
    if atualizou:
        db.commit()


async def _enviar_lembretes_bg(empresa_id: int) -> None:
    """#3 — Verifica e envia lembretes automáticos aos clientes com orçamentos pendentes."""
    db = SessionLocal()
    try:
        empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
        if not empresa:
            return
        # Lembretes podem ser desativados tanto por configuração da empresa quanto pelo plano.
        if not lembretes_automaticos_habilitados(empresa):
            return

        agora = datetime.now(timezone.utc)
        limiar = agora - timedelta(days=empresa.lembrete_dias)

        candidatos = (
            db.query(Orcamento)
            .options(
                joinedload(Orcamento.cliente),
            )
            .filter(
                Orcamento.empresa_id == empresa_id,
                Orcamento.status == StatusOrcamento.ENVIADO,
                Orcamento.lembrete_enviado_em.is_(None),
            )
            .all()
        )

        para_enviar = []
        for orc in candidatos:
            if not orc.criado_em or not orc.cliente or not orc.cliente.telefone:
                continue
            criado = orc.criado_em
            if criado.tzinfo is None:
                criado = criado.replace(tzinfo=timezone.utc)
            expira = criado + timedelta(days=orc.validade_dias or 7)
            # Deve ter passado lembrete_dias desde a criação, e o orçamento não pode ter expirado
            if criado <= limiar and expira > agora:
                para_enviar.append(
                    {
                        "orc": orc,
                        "telefone": orc.cliente.telefone,
                        "cliente_nome": orc.cliente.nome,
                        "numero": orc.numero,
                        "link_publico": orc.link_publico or "",
                        "telefone_operador": empresa.telefone_operador,
                        "empresa_nome": empresa.nome,
                        "lembrete_texto": empresa.lembrete_texto,
                    }
                )

        if para_enviar:
            for item in para_enviar:
                try:
                    await enviar_lembrete_cliente(
                        item["telefone"],
                        item["cliente_nome"],
                        item["numero"],
                        item["link_publico"],
                        item["empresa_nome"],
                        lembrete_texto=item.get("lembrete_texto"),
                        empresa=empresa,
                    )
                    try:
                        item["orc"].lembrete_enviado_em = agora
                        db.commit()
                    except Exception:
                        db.rollback()
                        logger.exception(
                            "Falha ao marcar lembrete como enviado (empresa_id=%s, orcamento_id=%s)",
                            empresa_id,
                            getattr(item.get("orc"), "id", None),
                        )

                    if item["telefone_operador"]:
                        try:
                            await enviar_mensagem_texto(
                                item["telefone_operador"],
                                f"📨 Lembrete enviado para *{item['cliente_nome']}* sobre o orçamento *{item['numero']}*.",
                                empresa=empresa,
                            )
                        except Exception:
                            logger.exception(
                                "Falha ao notificar operador após lembrete (empresa_id=%s, orcamento_id=%s)",
                                empresa_id,
                                getattr(item.get("orc"), "id", None),
                            )
                except Exception:
                    logger.exception(
                        "Falha ao enviar lembrete (empresa_id=%s, orcamento_id=%s)",
                        empresa_id,
                        getattr(item.get("orc"), "id", None),
                    )
    except Exception:
        logger.exception("Falha no job de lembretes (empresa_id=%s)", empresa_id)
    finally:
        db.close()


def _normalizar_texto_orc(txt: str) -> str:
    if not txt:
        return ""
    txt = txt.lower()
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(ch for ch in txt if not unicodedata.combining(ch))
    txt = re.sub(r"[^a-z0-9]+", " ", txt)
    return " ".join(txt.split())


def _encontrar_servico_catalogo_orc(empresa: Empresa, descricao: str, db: Session):
    """Encontra serviço do catálogo da empresa pela descrição (match exato ou por palavras)."""
    desc_norm = _normalizar_texto_orc(descricao)
    if not desc_norm:
        return None
    palavras = [p for p in desc_norm.split() if len(p) >= 3]
    if not palavras:
        return None
    servicos = (
        db.query(Servico)
        .filter(
            Servico.empresa_id == empresa.id,
            Servico.ativo == True,
        )
        .all()
    )
    if not servicos:
        return None
    for srv in servicos:
        if _normalizar_texto_orc(srv.nome or "") == desc_norm:
            return srv
    melhor, melhor_score = None, 0.0
    for srv in servicos:
        nome_norm = _normalizar_texto_orc(srv.nome or "")
        if not nome_norm:
            continue
        tokens_nome = set(nome_norm.split())
        inter = tokens_nome.intersection(palavras)
        if not inter:
            continue
        score = len(inter) / len(palavras)
        if score > melhor_score:
            melhor_score = score
            melhor = srv
    if melhor and melhor_score >= 0.5:
        return melhor
    return None


def _regenerar_pdf_sync(orc: Orcamento, db: Session):
    """Atualiza pdf_url para o endpoint de geração on-the-fly."""
    if orc.link_publico and not orc.pdf_url:
        orc.pdf_url = f"/o/{orc.link_publico}/pdf"
        db.commit()


# ── BACKGROUND TASK ────────────────────────────────────────────────────────
# Usa sessão própria para funcionar após o fim da requisição (a sessão da rota já foi fechada).


def _enviar_email_background(
    orcamento_id: int,
    email_cliente: str,
    cliente_nome: str,
    numero_orcamento: str,
    empresa_nome: str,
    link_publico: str,
    pdf_bytes: bytes | None,
    anexar_pdf: bool,
    log_email_id: int,
    validade_texto: str | None = None,
    valor_total: float | None = None,
    contato_prestador: str | None = None,
    contato_email: str | None = None,
    responsavel_nome: str | None = None,
    link_pdf: str | None = None,
    assinatura_email: str | None = None,
):
    """Task em background para enviar email (não bloqueia a resposta HTTP)."""
    db = SessionLocal()
    try:
        from app.core.config import settings
        from app.services.documentos_service import (
            montar_nome_download,
            resolver_arquivo_path,
        )

        base_url = (settings.APP_URL or "").rstrip("/")

        docs_email = (
            db.query(OrcamentoDocumento)
            .filter(
                OrcamentoDocumento.orcamento_id == orcamento_id,
                OrcamentoDocumento.enviar_por_email == True,
            )
            .order_by(OrcamentoDocumento.ordem.asc(), OrcamentoDocumento.id.asc())
            .all()
        )

        documentos_email = []
        anexos_extra = []
        total_anexos = 0
        max_anexo = 2 * 1024 * 1024
        max_total = 6 * 1024 * 1024

        for d in docs_email:
            url = f"{base_url}/o/{link_publico}/documentos/{d.id}"
            documentos_email.append(
                {
                    "nome": d.documento_nome,
                    "url": url,
                    "permite_download": bool(d.permite_download),
                    "download_url": (url + "?download=1")
                    if d.permite_download
                    else None,
                }
            )
            if (
                d.mime_type == "application/pdf"
                and (d.tamanho_bytes or 0) > 0
                and (d.tamanho_bytes or 0) <= max_anexo
                and total_anexos + (d.tamanho_bytes or 0) <= max_total
            ):
                abs_path = resolver_arquivo_path(d.arquivo_path)
                with open(abs_path, "rb") as f:
                    content = f.read()
                anexos_extra.append(
                    {
                        "filename": montar_nome_download(
                            d.documento_nome, d.documento_versao, ext=".pdf"
                        ),
                        "content": content,
                        "mime": d.mime_type or "application/pdf",
                    }
                )
                total_anexos += d.tamanho_bytes or len(content)

        ok = enviar_orcamento_por_email(
            destinatario=email_cliente,
            cliente_nome=cliente_nome,
            numero_orcamento=numero_orcamento,
            empresa_nome=empresa_nome,
            link_publico=link_publico,
            pdf_bytes=pdf_bytes,
            anexar_pdf=anexar_pdf,
            validade_texto=validade_texto,
            valor_total=valor_total,
            contato_prestador=contato_prestador,
            contato_email=contato_email,
            responsavel_nome=responsavel_nome,
            link_pdf=link_pdf,
            assinatura_email=assinatura_email,
            documentos=documentos_email,
            anexos_extra=anexos_extra,
        )

        # Atualiza log do envio
        log_email = (
            db.query(LogEmailOrcamento)
            .filter(LogEmailOrcamento.id == log_email_id)
            .first()
        )
        if log_email:
            if ok:
                log_email.status = "enviado"
                log_email.enviado_em = datetime.now(timezone.utc)
                orc_row = (
                    db.query(Orcamento).filter(Orcamento.id == orcamento_id).first()
                )
                if orc_row and orc_row.enviado_em is None:
                    orc_row.enviado_em = log_email.enviado_em
            else:
                log_email.status = "erro"
                log_email.mensagem_erro = "Falha ao enviar e-mail do orçamento"
            db.commit()
    except Exception as e:
        import logging

        logging.error(f"Erro ao enviar email do orçamento {numero_orcamento}: {str(e)}")
        log_email = (
            db.query(LogEmailOrcamento)
            .filter(LogEmailOrcamento.id == log_email_id)
            .first()
        )
        if log_email:
            log_email.status = "erro"
            log_email.mensagem_erro = str(e)
            db.commit()
    finally:
        db.close()


def _gerar_e_salvar_pdf(orcamento_id: int):
    """Registra a URL do PDF on-the-fly no orçamento (não gera nem salva em disco)."""
    db = SessionLocal()
    try:
        orc = db.query(Orcamento).filter(Orcamento.id == orcamento_id).first()
        if not orc or not orc.link_publico:
            return
        orc.pdf_url = f"/o/{orc.link_publico}/pdf"
        db.commit()
    finally:
        db.close()
