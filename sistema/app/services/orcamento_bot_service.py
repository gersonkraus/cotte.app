"""
Service para comandos do bot de orçamentos.
Lógica de negócio extraída do router orcamentos.py (comando-bot).
"""

import secrets
import logging
from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import or_ as sa_or

from app.models.models import (
    Orcamento,
    ItemOrcamento,
    Cliente,
    HistoricoEdicao,
    StatusOrcamento,
    OrcamentoDocumento,
)
from app.services.whatsapp_service import enviar_orcamento_completo
from app.services.pdf_service import gerar_pdf_orcamento
from app.services.plano_service import exigir_ia_dashboard
from app.services.ia_service import interpretar_mensagem, interpretar_comando_operador
from app.services import financeiro_service
from app.services.quote_notification_service import (
    ensure_quote_approval_metadata,
    handle_quote_status_changed,
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
from app.core.config import settings

logger = logging.getLogger(__name__)


def _registrar_mudanca_status(
    db: Session,
    orcamento_id: int,
    novo_status: StatusOrcamento,
    editado_por_id: int | None = None,
    descricao: str | None = None,
) -> None:
    """Registra mudança de status no histórico."""
    desc = descricao or f"Status alterado para {novo_status.value}"
    db.add(
        HistoricoEdicao(
            orcamento_id=orcamento_id, editado_por_id=editado_por_id, descricao=desc
        )
    )


def _encontrar_servico_catalogo_orc(empresa, servico_nome: str, db: Session):
    """Busca serviço no catálogo pelo nome normalizado."""
    from app.models.models import Servico

    if not servico_nome:
        return None

    servico_nome_norm = servico_nome.lower().strip()

    servico = (
        db.query(Servico)
        .filter(
            Servico.empresa_id == empresa.id,
            Servico.ativo == True,
            Servico.nome.ilike(f"%{servico_nome_norm}%"),
        )
        .first()
    )
    return servico


def _buscar_orcamento_empresa(
    db: Session,
    orc_id: int,
    empresa_id: int,
    *,
    with_lock: bool = False,
) -> Orcamento | None:
    """Busca orçamento pelo ID interno ou número sequencial."""
    q = db.query(Orcamento).filter(
        Orcamento.empresa_id == empresa_id,
        sa_or(
            Orcamento.id == orc_id,
            Orcamento.numero.like(f"ORC-{orc_id}-%"),
        ),
    )
    if with_lock:
        q = q.with_for_update()
    return q.first()


async def executar_comando_bot(
    mensagem: str,
    usuario,
    db: Session,
    empresa,
) -> dict:
    """
    Executa comando do bot de orçamentos.
    Retorna dict com 'sucesso' e 'resposta' (e opcionalmente 'orcamento', 'analise').
    """
    if empresa:
        exigir_ia_dashboard(empresa)

    mensagem = (mensagem or "").strip()
    if not mensagem:
        return {
            "sucesso": False,
            "resposta": "Digite um comando ou descreva um orçamento.",
        }

    cmd = await interpretar_comando_operador(mensagem)
    acao = (cmd.get("acao") or "DESCONHECIDO").upper()
    orc_id = cmd.get("orcamento_id") if cmd.get("orcamento_id") is not None else None

    empresa_id = usuario.empresa_id

    # ── AJUDA ──
    if acao == "AJUDA":
        return {
            "sucesso": True,
            "resposta": (
                "🤖 **Comandos disponíveis**\n\n"
                '📋 **Ver** — "ver o 5", "mostra orçamento 3"\n'
                '✅ **Aprovar** — "aprovar 5", "aprovar orçamento 3"\n'
                '❌ **Recusar** — "recusar 5"\n'
                '🏷️ **Desconto** — "10% no 5", "50 reais de desconto no 3"\n'
                '➕ **Adicionar item** — "adiciona limpeza 80 reais no 3"\n'
                '➖ **Remover item** — "remove item 2 do orçamento 5"\n'
                '📲 **Enviar** — "envia o 5 pro cliente"\n\n'
                '📊 **Análise Financeira** — "Como estão as finanças?", "Analisar conversão"\n'
                '💡 **Sugestões de Negócio** — "Como aumentar vendas?", "Quais clientes devendo?"\n'
                '🎯 **Ticket Médio** — "Qual meu ticket médio?", "Serviço mais vendido"\n'
                '📈 **Caixa Futuro** — "caixa futuro", "previsão de caixa", "quanto vou receber"\n\n'
                'Ou descreva um **novo orçamento**: "Pintura 800 reais para João"\n\n'
                "🔗 **Assistente IA Completo**: Acesse a página **Assistente IA** para análises detalhadas!"
            ),
        }

    # ── APROVAR ──
    if acao == "APROVAR" and orc_id:
        return await _acao_aprovar(orc_id, usuario, empresa, db)

    # ── RECUSAR ──
    if acao == "RECUSAR" and orc_id:
        return await _acao_recusar(orc_id, usuario, db)

    # ── VER ──
    if acao == "VER" and orc_id:
        return _acao_ver(orc_id, db, empresa_id)

    # ── DESCONTO ──
    if acao == "DESCONTO" and orc_id:
        return await _acao_desconto(orc_id, cmd, usuario, empresa, db)

    # ── ADICIONAR ──
    if (
        acao == "ADICIONAR"
        and orc_id
        and cmd.get("descricao") is not None
        and cmd.get("valor") is not None
    ):
        return await _acao_adicionar_item(orc_id, cmd, db, empresa_id)

    # ── REMOVER ──
    if acao == "REMOVER" and orc_id and cmd.get("num_item") is not None:
        return await _acao_remover_item(orc_id, cmd, db, empresa_id)

    # ── ENVIAR (WhatsApp) ──
    if acao == "ENVIAR" and orc_id:
        return await _acao_enviar(orc_id, usuario, db, empresa_id)

    # ── AÇÃO OPERACIONAL SEM ID ──
    acoes_operacionais = {
        "VER",
        "APROVAR",
        "RECUSAR",
        "ENVIAR",
        "DESCONTO",
        "ADICIONAR",
        "REMOVER",
    }
    if acao in acoes_operacionais and not orc_id:
        mensagens_falta_id = {
            "VER": "Qual orçamento você quer ver? Digite: ver 5",
            "APROVAR": "Qual orçamento você quer aprovar? Digite: aprovar 5",
            "RECUSAR": "Qual orçamento você quer recusar? Digite: recusar 5",
            "ENVIAR": "Qual orçamento você quer enviar? Digite: enviar 5",
            "DESCONTO": "Qual orçamento para aplicar o desconto? Digite: 10% no 5",
            "ADICIONAR": "Em qual orçamento você quer adicionar o item? Digite: adiciona pintura 80 no 5",
            "REMOVER": "De qual orçamento você quer remover o item? Digite: remove item 2 do 5",
        }
        return {
            "sucesso": False,
            "resposta": mensagens_falta_id.get(
                acao, "Não entendi. Digite ajuda para ver os comandos."
            ),
        }

    # ── CRIAR ou DESCONHECIDO: tenta criar orçamento ──
    return await _acao_criar(mensagem, cmd, usuario, empresa, db)


async def _acao_aprovar(orc_id: int, usuario, empresa, db: Session) -> dict:
    """Aprova um orçamento."""
    orc = _buscar_orcamento_empresa(db, int(orc_id), usuario.empresa_id, with_lock=True)
    if not orc:
        return {"sucesso": False, "resposta": f"Orçamento #{orc_id} não encontrado."}

    old_status = orc.status
    if not transicao_permitida(old_status, StatusOrcamento.APROVADO):
        return {
            "sucesso": False,
            "resposta": texto_transicao_negada(
                old_status, StatusOrcamento.APROVADO, para_bot=True
            ),
        }

    orc.status = StatusOrcamento.APROVADO
    ensure_quote_approval_metadata(orc, source="bot_command")
    renomear_numero_aprovado(orc, empresa)
    _registrar_mudanca_status(
        db,
        orc.id,
        StatusOrcamento.APROVADO,
        editado_por_id=usuario.id,
        descricao="Aprovado pelo comando do bot (dashboard).",
    )
    financeiro_service.criar_contas_receber_aprovacao(orc, usuario.empresa_id, db)

    # Agendamento automático ou fila de pré-agendamento
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
        source="bot_command",
    )

    return {"sucesso": True, "resposta": f"✅ Orçamento {orc.numero} aprovado!"}


async def _acao_recusar(orc_id: int, usuario, db: Session) -> dict:
    """Recusa um orçamento."""
    orc = _buscar_orcamento_empresa(db, int(orc_id), usuario.empresa_id, with_lock=True)
    if not orc:
        return {"sucesso": False, "resposta": f"Orçamento #{orc_id} não encontrado."}

    old_status = orc.status
    if not transicao_permitida(old_status, StatusOrcamento.RECUSADO):
        return {
            "sucesso": False,
            "resposta": texto_transicao_negada(
                old_status, StatusOrcamento.RECUSADO, para_bot=True
            ),
        }

    orc.status = StatusOrcamento.RECUSADO
    _registrar_mudanca_status(
        db,
        orc.id,
        StatusOrcamento.RECUSADO,
        editado_por_id=usuario.id,
        descricao="Recusado pelo comando do bot (dashboard).",
    )
    db.commit()
    db.refresh(orc)
    await handle_quote_status_changed(
        db=db,
        quote=orc,
        old_status=old_status,
        new_status=orc.status,
        source="bot_command",
    )
    return {
        "sucesso": True,
        "resposta": f"❌ Orçamento {orc.numero} marcado como recusado.",
    }


def _acao_ver(orc_id: int, db: Session, empresa_id: int) -> dict:
    """Mostra detalhes de um orçamento."""
    orc = _buscar_orcamento_empresa(db, int(orc_id), empresa_id)
    if not orc:
        return {"sucesso": False, "resposta": f"Orçamento #{orc_id} não encontrado."}

    itens_txt = listar_itens_txt(orc.itens)
    desc_txt = ""
    if orc.desconto and orc.desconto > 0:
        desc_label = (
            f"{orc.desconto:.0f}%"
            if orc.desconto_tipo == "percentual"
            else brl_fmt(orc.desconto)
        )
        desc_txt = f"🏷️ Desconto: {desc_label}\n"

    return {
        "sucesso": True,
        "resposta": (
            f"📋 **{orc.numero}** — {orc.cliente.nome}\n\n"
            f"{itens_txt}\n\n{desc_txt}"
            f"💰 Total: {brl_fmt(orc.total)}\n"
            f"📊 Status: {orc.status}"
        ),
    }


async def _acao_desconto(orc_id: int, cmd: dict, usuario, empresa, db: Session) -> dict:
    """Aplica ou remove desconto de um orçamento."""
    orc = _buscar_orcamento_empresa(db, int(orc_id), usuario.empresa_id)
    if not orc:
        return {"sucesso": False, "resposta": f"Orçamento #{orc_id} não encontrado."}

    valor = Decimal(str(cmd.get("valor") or 0))
    tipo = "fixo" if cmd.get("desconto_tipo") == "fixo" else "percentual"
    subtotal = sum(i.total for i in orc.itens)

    if valor > 0:
        max_pct = resolver_max_percent_desconto(usuario, empresa)
        err_desconto = erro_validacao_desconto(subtotal, valor, tipo, max_pct)
        if err_desconto:
            return {"sucesso": False, "resposta": err_desconto}

    if valor > 0:
        novo_total = max(
            Decimal("0.0"),
            subtotal - (subtotal * valor / 100 if tipo == "percentual" else valor),
        )
    else:
        novo_total = subtotal

    orc.desconto = valor
    orc.desconto_tipo = tipo
    orc.total = novo_total

    _registrar_mudanca_status(
        db,
        orc.id,
        orc.status,
        editado_por_id=usuario.id,
        descricao=f"Desconto atualizado: {valor} {tipo}",
    )

    db.commit()
    db.refresh(orc)

    desc_label = f"{valor:.0f}%" if tipo == "percentual" else brl_fmt(valor)
    if valor == 0:
        msg = f"✅ Desconto removido do {orc.numero}! Total: {brl_fmt(novo_total)}"
    else:
        msg = f"✅ Desconto aplicado em {orc.numero}: {desc_label}. Novo total: {brl_fmt(novo_total)}"

    return {"sucesso": True, "resposta": msg}


async def _acao_adicionar_item(
    orc_id: int, cmd: dict, db: Session, empresa_id: int
) -> dict:
    """Adiciona item a um orçamento."""
    orc = _buscar_orcamento_empresa(db, int(orc_id), empresa_id)
    if not orc:
        return {"sucesso": False, "resposta": f"Orçamento #{orc_id} não encontrado."}

    db.add(
        ItemOrcamento(
            orcamento_id=orc.id,
            descricao=str(cmd["descricao"]),
            quantidade=1,
            valor_unit=Decimal(str(cmd["valor"])),
            total=Decimal(str(cmd["valor"])),
        )
    )
    db.flush()
    db.refresh(orc)
    subtotal = sum(i.total for i in orc.itens)
    orc.total = aplicar_desconto(
        subtotal, orc.desconto or 0, orc.desconto_tipo or "percentual"
    )
    db.commit()
    db.refresh(orc)

    return {
        "sucesso": True,
        "resposta": f"✅ Item adicionado em {orc.numero}!\n\n{listar_itens_txt(orc.itens)}\n\n💰 Total: {brl_fmt(orc.total)}",
    }


async def _acao_remover_item(
    orc_id: int, cmd: dict, db: Session, empresa_id: int
) -> dict:
    """Remove item de um orçamento."""
    orc = _buscar_orcamento_empresa(db, int(orc_id), empresa_id)
    if not orc:
        return {"sucesso": False, "resposta": f"Orçamento #{orc_id} não encontrado."}

    itens = list(orc.itens)
    num_item = int(cmd["num_item"])

    if num_item < 1 or num_item > len(itens):
        return {
            "sucesso": False,
            "resposta": f'Item {num_item} inválido. O orçamento tem {len(itens)} item(ns). Use "ver {orc_id}" para listar.',
        }

    if len(itens) == 1:
        return {
            "sucesso": False,
            "resposta": "Não é possível remover o único item. Adicione outro antes.",
        }

    desc_removido = itens[num_item - 1].descricao
    db.delete(itens[num_item - 1])
    db.flush()
    db.refresh(orc)
    subtotal = sum(i.total for i in orc.itens)
    orc.total = aplicar_desconto(
        subtotal, orc.desconto or 0, orc.desconto_tipo or "percentual"
    )
    db.commit()
    db.refresh(orc)

    return {
        "sucesso": True,
        "resposta": f'✅ Item "{desc_removido}" removido de {orc.numero}.\n\n{listar_itens_txt(orc.itens)}\n\n💰 Total: {brl_fmt(orc.total)}',
    }


async def _acao_enviar(orc_id: int, usuario, db: Session, empresa_id: int) -> dict:
    """Envia orçamento por WhatsApp."""
    orc = _buscar_orcamento_empresa(db, int(orc_id), empresa_id, with_lock=True)
    if not orc:
        return {"sucesso": False, "resposta": f"Orçamento #{orc_id} não encontrado."}

    old_status = orc.status
    if not transicao_permitida(old_status, StatusOrcamento.ENVIADO):
        return {
            "sucesso": False,
            "resposta": texto_transicao_negada(
                old_status, StatusOrcamento.ENVIADO, para_bot=True
            ),
        }

    if not orc.cliente.telefone:
        return {
            "sucesso": False,
            "resposta": f"Cliente {orc.cliente.nome} não tem telefone cadastrado. Cadastre o WhatsApp do cliente para enviar.",
        }

    empresa_dict = {
        "nome": orc.empresa.nome,
        "telefone": orc.empresa.telefone,
        "cor_primaria": orc.empresa.cor_primaria,
    }
    subtotal_env = sum(i.total for i in orc.itens)
    docs_vinc = (
        db.query(OrcamentoDocumento)
        .filter(OrcamentoDocumento.orcamento_id == orc.id)
        .order_by(OrcamentoDocumento.ordem.asc(), OrcamentoDocumento.id.asc())
        .all()
    )
    orc_dict = {
        "numero": orc.numero,
        "total": orc.total,
        "validade_dias": orc.validade_dias,
        "subtotal": subtotal_env,
        "desconto": orc.desconto or 0.0,
        "desconto_tipo": orc.desconto_tipo or "percentual",
        "observacoes": orc.observacoes,
        "forma_pagamento": orc.forma_pagamento,
        "link_publico": orc.link_publico,
        "cliente": {"nome": orc.cliente.nome, "telefone": orc.cliente.telefone},
        "itens": [
            {
                "descricao": i.descricao,
                "quantidade": i.quantidade,
                "valor_unit": i.valor_unit,
                "total": i.total,
            }
            for i in orc.itens
        ],
        "documentos": [
            {
                "nome": d.documento_nome,
                "tipo": d.documento_tipo,
                "versao": d.documento_versao,
            }
            for d in docs_vinc
        ],
    }
    pdf_bytes = gerar_pdf_orcamento(orc_dict, empresa_dict)

    orc_dict_whatsapp = {
        "numero": orc.numero,
        "cliente_nome": orc.cliente.nome,
        "total": orc.total,
        "validade_dias": orc.validade_dias or 7,
        "empresa_nome": orc.empresa.nome,
        "vendedor_nome": orc.criado_por.nome if orc.criado_por else None,
        "link_publico": orc.link_publico,
    }

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
    orc_dict_whatsapp["documentos_whatsapp"] = [
        {
            "nome": d.documento_nome,
            "url": f"{base_url}/o/{orc.link_publico}/documentos/{d.id}",
        }
        for d in docs_whats
    ]

    await enviar_orcamento_completo(
        orc.cliente.telefone, orc_dict_whatsapp, pdf_bytes, empresa=orc.empresa
    )

    orc.status = StatusOrcamento.ENVIADO
    orc.enviado_em = datetime.now(timezone.utc)
    _registrar_mudanca_status(
        db,
        orc.id,
        StatusOrcamento.ENVIADO,
        editado_por_id=usuario.id,
        descricao="Enviado por WhatsApp (comando do bot).",
    )
    db.commit()

    return {
        "sucesso": True,
        "resposta": f"📲 Orçamento {orc.numero} enviado por WhatsApp para {orc.cliente.nome}!",
    }


async def _acao_criar(mensagem: str, cmd: dict, usuario, empresa, db: Session) -> dict:
    """Cria orçamento a partir de mensagem em linguagem natural."""
    interpretado = await interpretar_mensagem(mensagem)

    servico_match = None
    if empresa:
        servico_match = _encontrar_servico_catalogo_orc(
            empresa, interpretado.servico, db
        )

    if interpretado.confianca < 0.5 and not servico_match:
        return {
            "sucesso": False,
            "resposta": 'Não entendi. Você pode: criar orçamento (ex: "Pintura 800 reais para João"), ver ("ver 5"), aprobar ("aprovar 5"), enviar ("envia 5"). Digite **ajuda** para ver todos os comandos.',
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

    descricao_item = servico_match.nome if servico_match else interpretado.servico
    subtotal = float(interpretado.valor or 0)
    if servico_match and servico_match.preco_padrao and servico_match.preco_padrao > 0:
        subtotal = float(servico_match.preco_padrao)
        if interpretado.valor and float(interpretado.valor) > 0:
            subtotal = float(interpretado.valor)

    desconto = float(interpretado.desconto or 0)
    desconto_tipo = interpretado.desconto_tipo or "percentual"

    if desconto > 0:
        max_pct = resolver_max_percent_desconto(usuario, empresa)
        err_desconto = erro_validacao_desconto(
            subtotal, desconto, desconto_tipo, max_pct
        )
        if err_desconto:
            return {"sucesso": False, "resposta": err_desconto}
        total_calc = max(
            Decimal("0.0"),
            Decimal(subtotal)
            - (
                Decimal(subtotal) * (desconto / 100)
                if desconto_tipo == "percentual"
                else Decimal(desconto)
            ),
        )
    else:
        total_calc = Decimal(subtotal)

    validade_padrao = (empresa.validade_padrao_dias or 7) if empresa else 7

    from app.models.models import ModoAgendamentoOrcamento

    agendamento_modo_ia = ModoAgendamentoOrcamento.NAO_USA
    if empresa and getattr(empresa, "agendamento_modo_padrao", None):
        agendamento_modo_ia = empresa.agendamento_modo_padrao
    if empresa and getattr(empresa, "agendamento_escolha_obrigatoria", False):
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
            if "uq_orcamentos_empresa_numero" in str(e) or "orcamentos_numero" in str(
                e
            ):
                continue
            raise
    else:
        return {
            "sucesso": False,
            "resposta": "Não foi possível gerar número de orçamento único. Tente novamente.",
        }

    db.add(
        ItemOrcamento(
            orcamento_id=orcamento.id,
            servico_id=servico_match.id if servico_match else None,
            descricao=descricao_item,
            quantidade=1,
            valor_unit=Decimal(subtotal),
            total=Decimal(subtotal),
        )
    )
    db.commit()
    db.refresh(orcamento)

    total_fmt = brl_fmt(float(total_calc))
    return {
        "sucesso": True,
        "resposta": f"✅ Orçamento {orcamento.numero} criado para {cliente_nome}! Total {total_fmt}. Veja na lista acima e clique em 📄 para o PDF.",
        "orcamento": {
            "id": orcamento.id,
            "numero": orcamento.numero,
            "total": orcamento.total,
            "cliente": {"nome": cliente.nome},
        },
    }
