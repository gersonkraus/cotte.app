"""
Fluxo de mensagens interativas (listas sendList) no WhatsApp.
Arquitetura híbrida:
  - Cliente → stateless: rowId codifica 'acao:entidade_id'
  - Operador → session-based: tabela sessao_whatsapp rastreia o wizard
"""
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.models.models import (
    SessaoWhatsapp,
    Orcamento,
    StatusOrcamento,
    Cliente,
    Empresa,
    CategoriaCatalogo,
    Servico,
    HistoricoEdicao,
)
from app.services.operador_interacao_service import enviar_lista_selecao
from app.services.whatsapp_service import enviar_mensagem_texto

logger = logging.getLogger(__name__)

SESSION_TTL_MINUTES = 15

# ── Helpers ──────────────────────────────────────────────────────────────────


def decodificar_row_id(row_id: str) -> tuple[str, str | None]:
    """'aprovar:123' → ('aprovar', '123') | 'finalizar' → ('finalizar', None)"""
    parts = row_id.split(":", 1)
    return (parts[0].strip(), parts[1].strip() if len(parts) > 1 else None)


def _agora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _instancia(empresa: Empresa) -> str | None:
    return getattr(empresa, "evolution_instance", None)


def _brl(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ── Gestão de sessão do operador ─────────────────────────────────────────────


def _buscar_sessao_ativa(db: Session, telefone: str) -> SessaoWhatsapp | None:
    sessao = db.query(SessaoWhatsapp).filter(SessaoWhatsapp.telefone == telefone).first()
    if not sessao:
        return None
    if sessao.expira_em < _agora():
        db.delete(sessao)
        db.commit()
        return None
    return sessao


def _criar_sessao(
    db: Session, telefone: str, empresa_id: int, etapa: str, contexto: dict
) -> SessaoWhatsapp:
    db.query(SessaoWhatsapp).filter(SessaoWhatsapp.telefone == telefone).delete()
    sessao = SessaoWhatsapp(
        telefone=telefone,
        empresa_id=empresa_id,
        etapa=etapa,
        contexto=contexto,
        expira_em=_agora() + timedelta(minutes=SESSION_TTL_MINUTES),
    )
    db.add(sessao)
    db.commit()
    db.refresh(sessao)
    return sessao


def _atualizar_sessao(
    db: Session, sessao: SessaoWhatsapp, etapa: str, contexto: dict
) -> None:
    sessao.etapa = etapa
    sessao.contexto = contexto
    sessao.expira_em = _agora() + timedelta(minutes=SESSION_TTL_MINUTES)
    db.commit()


def _encerrar_sessao(db: Session, telefone: str) -> None:
    db.query(SessaoWhatsapp).filter(SessaoWhatsapp.telefone == telefone).delete()
    db.commit()


# ── Roteador principal ────────────────────────────────────────────────────────


async def processar_resposta_lista(
    db: Session,
    telefone: str,
    row_id: str,
    empresa_instancia: Empresa | None = None,
) -> bool:
    """
    Chamado pelo webhook quando tipo == listResponseMessage.
    Sessão ativa → operador wizard. Sem sessão → ação stateless do cliente.
    """
    sessao = _buscar_sessao_ativa(db, telefone)
    if sessao:
        emp = empresa_instancia or db.query(Empresa).filter(Empresa.id == sessao.empresa_id).first()
        if emp:
            return await _processar_resposta_operador(db, sessao, row_id, emp)

    return await _processar_resposta_cliente(db, telefone, row_id, empresa_instancia)


# ── Fluxo do Cliente (Stateless) ─────────────────────────────────────────────


async def enviar_menu_orcamento_cliente(
    db: Session, orcamento_id: int, empresa: Empresa
) -> bool:
    """Envia menu interativo ao cliente: Aprovar / Recusar / Pedir desconto."""
    orc = (
        db.query(Orcamento)
        .filter(Orcamento.id == orcamento_id, Orcamento.empresa_id == empresa.id)
        .first()
    )
    if not orc or not orc.cliente or not orc.cliente.telefone:
        return False

    _STATUS_MENU = {StatusOrcamento.ENVIADO, StatusOrcamento.RASCUNHO}
    if orc.status not in _STATUS_MENU:
        return False

    total = _brl(float(orc.total))
    secoes = [
        {
            "titulo": "O que deseja fazer?",
            "itens": [
                {"id": f"aprovar:{orc.id}", "titulo": "✅ Aprovar orçamento", "desc": f"Total: {total}"},
                {"id": f"recusar:{orc.id}", "titulo": "❌ Recusar orçamento", "desc": "Não tenho interesse"},
                {"id": f"desconto:{orc.id}", "titulo": "💬 Solicitar desconto", "desc": "Pedir revisão de preço"},
            ],
        }
    ]
    return await enviar_lista_selecao(
        telefone=orc.cliente.telefone,
        titulo=f"Orçamento {orc.numero}",
        descricao=f"Olá, {orc.cliente.nome}! Selecione uma opção para o seu orçamento.",
        secoes=secoes,
        botao_texto="Ver opções",
        instancia=_instancia(empresa),
    )


async def _processar_resposta_cliente(
    db: Session, telefone: str, row_id: str, empresa: Empresa | None
) -> bool:
    """Decodifica rowId e executa ação do cliente."""
    acao, eid = decodificar_row_id(row_id)
    logger.info("[Interativo] Cliente %s → acao='%s' eid='%s'", telefone, acao, eid)

    # aprovar:123 → menu de pagamento
    if acao == "aprovar" and eid:
        orc = _buscar_orc_cliente(db, int(eid), telefone)
        if not orc:
            return False
        emp = empresa or db.query(Empresa).filter(Empresa.id == orc.empresa_id).first()
        return await _enviar_menu_pagamento(db, orc, telefone, emp)

    # recusar:123 → recusa imediata
    if acao == "recusar" and eid:
        orc = _buscar_orc_cliente(db, int(eid), telefone)
        if not orc:
            return False
        emp = empresa or db.query(Empresa).filter(Empresa.id == orc.empresa_id).first()
        return await _executar_recusar(db, orc, telefone, emp)

    # desconto:123 → notifica operador
    if acao == "desconto" and eid:
        orc = _buscar_orc_cliente(db, int(eid), telefone)
        if not orc:
            return False
        emp = empresa or db.query(Empresa).filter(Empresa.id == orc.empresa_id).first()
        return await _executar_solicitar_desconto(db, orc, telefone, emp)

    # pagamento:forma_id:orc_id → aprova com forma de pagamento
    if acao == "pagamento" and eid and ":" in eid:
        forma_id_str, orc_id_str = eid.split(":", 1)
        orc = _buscar_orc_cliente(db, int(orc_id_str), telefone)
        if not orc:
            return False
        emp = empresa or db.query(Empresa).filter(Empresa.id == orc.empresa_id).first()
        return await _executar_aprovar(db, orc, telefone, emp, regra_id=int(forma_id_str))

    logger.info("[Interativo] rowId desconhecido '%s' de %s", row_id, telefone)
    return False


def _telefones_compativeis(tel_wpp: str, tel_db: str) -> bool:
    """Compara telefones tolerando variações: DDI, formatação, 8 vs 9 dígitos."""
    import re
    d1 = re.sub(r"\D", "", tel_wpp or "")
    d2 = re.sub(r"\D", "", tel_db or "")
    if not d1 or not d2:
        return False
    if d1 == d2:
        return True
    # Normaliza ambos para 13 dígitos (55 + DDD + 9 dígitos)
    def _norm(d: str) -> str:
        if not d.startswith("55"):
            d = "55" + d
        return d
    n1, n2 = _norm(d1), _norm(d2)
    if n1 == n2:
        return True
    # Tolerância 8 vs 9 dígitos: compara os últimos 8 dígitos (número local sem DDD)
    if len(n1) >= 10 and len(n2) >= 10 and n1[-8:] == n2[-8:]:
        return True
    return False


def _buscar_orc_cliente(db: Session, orcamento_id: int, telefone: str) -> Orcamento | None:
    """Busca orçamento verificando que o telefone pertence ao cliente."""
    orc = db.query(Orcamento).filter(Orcamento.id == orcamento_id).first()
    if not orc or not orc.cliente:
        logger.warning("[Interativo] Orc %s não encontrado ou sem cliente", orcamento_id)
        return None

    tel_cliente_raw = orc.cliente.telefone or ""
    if not _telefones_compativeis(telefone, tel_cliente_raw):
        logger.warning(
            "[Interativo] Telefone webhook '%s' ≠ cliente do orc %s ('%s')",
            telefone, orcamento_id, tel_cliente_raw,
        )
        return None

    _ATIVOS = {StatusOrcamento.ENVIADO, StatusOrcamento.RASCUNHO}
    if orc.status not in _ATIVOS:
        logger.info("[Interativo] Orc %s status '%s' não permite ação", orcamento_id, orc.status)
        return None
    return orc


async def _enviar_menu_pagamento(
    db: Session, orc: Orcamento, telefone: str, empresa: Empresa | None
) -> bool:
    """Envia lista com formas de pagamento ativas da empresa."""
    from app.models.models import FormaPagamentoConfig

    formas = []
    if empresa:
        formas = (
            db.query(FormaPagamentoConfig)
            .filter(
                FormaPagamentoConfig.empresa_id == empresa.id,
                FormaPagamentoConfig.ativo == True,
            )
            .order_by(FormaPagamentoConfig.ordem)
            .limit(10)
            .all()
        )

    if not formas:
        # Sem formas configuradas → aprova diretamente
        logger.info("[Interativo] Orc %s sem formas de pagamento → aprovando direto", orc.id)
        return await _executar_aprovar(db, orc, telefone, empresa, regra_id=None)

    itens = [
        {
            "id": f"pagamento:{fp.id}:{orc.id}",
            "titulo": f"{fp.icone} {fp.nome}",
            "desc": fp.descricao or "",
        }
        for fp in formas
    ]
    logger.info("[Interativo] Orc %s → enviando menu de pagamento (%d formas)", orc.id, len(formas))
    ok = await enviar_lista_selecao(
        telefone=telefone,
        titulo="Como prefere pagar?",
        descricao="Ótimo! Para confirmar a aprovação do orçamento, selecione a forma de pagamento:",
        secoes=[{"titulo": "Formas de pagamento", "itens": itens}],
        botao_texto="Escolher",
        instancia=_instancia(empresa) if empresa else None,
    )
    if not ok:
        logger.error("[Interativo] Falha ao enviar menu de pagamento para %s (orc %s)", telefone, orc.id)
    return ok


async def _executar_aprovar(
    db: Session,
    orc: Orcamento,
    telefone: str,
    empresa: Empresa | None,
    regra_id: int | None,
) -> bool:
    from app.services.quote_notification_service import (
        handle_quote_status_changed,
        ensure_quote_approval_metadata,
    )
    import app.services.financeiro_service as financeiro_service

    old_status = orc.status
    orc.status = StatusOrcamento.APROVADO
    if regra_id:
        orc.regra_pagamento_id = regra_id
    ensure_quote_approval_metadata(orc, source="whatsapp_interativo_cliente")
    db.add(
        HistoricoEdicao(
            orcamento_id=orc.id,
            editado_por_id=None,
            descricao="Aprovado pelo cliente via WhatsApp interativo.",
        )
    )
    financeiro_service.criar_contas_receber_aprovacao(orc, orc.empresa_id, db)
    db.commit()
    db.refresh(orc)

    await handle_quote_status_changed(
        db=db,
        quote=orc,
        old_status=old_status,
        new_status=orc.status,
        source="whatsapp_interativo_cliente",
    )

    if empresa:
        await enviar_mensagem_texto(
            telefone,
            f"✅ *Orçamento {orc.numero} aprovado!*\n\nObrigado pela confirmação. Em breve entraremos em contato.",
            empresa=empresa,
        )
    return True


async def _executar_recusar(
    db: Session, orc: Orcamento, telefone: str, empresa: Empresa | None
) -> bool:
    from app.services.quote_notification_service import handle_quote_status_changed

    old_status = orc.status
    orc.status = StatusOrcamento.RECUSADO
    orc.recusa_em = _agora()
    db.add(
        HistoricoEdicao(
            orcamento_id=orc.id,
            editado_por_id=None,
            descricao="Recusado pelo cliente via WhatsApp interativo.",
        )
    )
    db.commit()
    db.refresh(orc)

    await handle_quote_status_changed(
        db=db,
        quote=orc,
        old_status=old_status,
        new_status=orc.status,
        source="whatsapp_interativo_cliente",
    )

    if empresa:
        await enviar_mensagem_texto(
            telefone,
            f"Recebemos sua recusa do orçamento *{orc.numero}*. Se mudar de ideia, estamos à disposição!",
            empresa=empresa,
        )
    return True


async def _executar_solicitar_desconto(
    db: Session, orc: Orcamento, telefone: str, empresa: Empresa | None
) -> bool:
    from app.services.quote_notification_service import (
        resolve_quote_responsible_user,
        resolve_responsible_phone,
    )

    responsavel = resolve_quote_responsible_user(db, orc)
    tel_op = resolve_responsible_phone(orc, responsavel) if responsavel else None

    if tel_op:
        nome_cliente = orc.cliente.nome if orc.cliente else "Cliente"
        total = _brl(float(orc.total))
        await enviar_mensagem_texto(
            tel_op,
            f"💬 *Solicitação de desconto*\n\nCliente *{nome_cliente}* pediu desconto no orçamento *{orc.numero}*.\nTotal atual: {total}",
            empresa=empresa,
        )

    if empresa:
        await enviar_mensagem_texto(
            telefone,
            "✅ Sua solicitação foi enviada ao responsável. Aguarde o retorno em breve!",
            empresa=empresa,
        )
    return True


# ── Fluxo do Operador (Session-based) ────────────────────────────────────────


async def iniciar_fluxo_operador(db: Session, telefone: str, empresa: Empresa) -> bool:
    """Cria sessão e envia lista de clientes recentes para iniciar o wizard."""
    clientes = (
        db.query(Cliente)
        .filter(Cliente.empresa_id == empresa.id)
        .order_by(Cliente.criado_em.desc())
        .limit(5)
        .all()
    )

    if not clientes:
        await enviar_mensagem_texto(
            telefone,
            "Nenhum cliente cadastrado. Cadastre um cliente no painel antes de criar um orçamento.",
            empresa=empresa,
        )
        return False

    _criar_sessao(db, telefone, empresa.id, "selecionando_cliente", {})

    itens = [
        {"id": f"cliente:{c.id}", "titulo": c.nome, "desc": c.telefone or ""}
        for c in clientes
    ]
    return await enviar_lista_selecao(
        telefone=telefone,
        titulo="Novo orçamento",
        descricao="Selecione o cliente para este orçamento:",
        secoes=[{"titulo": "Clientes recentes", "itens": itens}],
        botao_texto="Selecionar cliente",
        instancia=_instancia(empresa),
    )


async def _processar_resposta_operador(
    db: Session, sessao: SessaoWhatsapp, row_id: str, empresa: Empresa
) -> bool:
    """Router do wizard: avança a etapa conforme a seleção do operador."""
    acao, eid = decodificar_row_id(row_id)
    tel = sessao.telefone

    if acao == "cancelar":
        _encerrar_sessao(db, tel)
        await enviar_mensagem_texto(tel, "Criação de orçamento cancelada.", empresa=empresa)
        return True

    if sessao.etapa == "selecionando_cliente" and acao == "cliente" and eid:
        return await _step_cliente(db, sessao, int(eid), empresa)

    if sessao.etapa == "selecionando_categoria" and acao == "categoria" and eid:
        return await _step_categoria(db, sessao, int(eid), empresa)

    if sessao.etapa in ("selecionando_item", "selecionando_categoria") and acao == "mais_itens":
        return await _step_voltar_categorias(db, sessao, empresa)

    if sessao.etapa in ("selecionando_item", "selecionando_categoria") and acao == "finalizar":
        return await _step_finalizar(db, sessao, empresa)

    if sessao.etapa == "selecionando_item" and acao == "item" and eid:
        return await _step_item(db, sessao, int(eid), empresa)

    if sessao.etapa == "confirmando_envio" and acao == "enviar_cliente":
        return await _step_enviar_cliente(db, sessao, empresa)

    if sessao.etapa == "confirmando_envio" and acao == "salvar_rascunho":
        _encerrar_sessao(db, tel)
        numero = (sessao.contexto or {}).get("orcamento_numero", "")
        await enviar_mensagem_texto(
            tel, f"Orçamento *{numero}* salvo como rascunho no painel.", empresa=empresa
        )
        return True

    logger.warning("[Interativo] Etapa '%s' sem handler para '%s'", sessao.etapa, acao)
    return False


async def _step_cliente(
    db: Session, sessao: SessaoWhatsapp, cliente_id: int, empresa: Empresa
) -> bool:
    cliente = db.query(Cliente).filter(
        Cliente.id == cliente_id, Cliente.empresa_id == empresa.id
    ).first()
    if not cliente:
        await enviar_mensagem_texto(sessao.telefone, "Cliente não encontrado.", empresa=empresa)
        return False

    categorias = (
        db.query(CategoriaCatalogo)
        .filter(CategoriaCatalogo.empresa_id == empresa.id)
        .all()
    )

    novo_ctx = {"cliente_id": cliente_id, "cliente_nome": cliente.nome, "itens": []}

    if not categorias:
        return await _mostrar_itens_direto(db, sessao, novo_ctx, empresa)

    _atualizar_sessao(db, sessao, "selecionando_categoria", novo_ctx)

    itens = [{"id": f"categoria:{c.id}", "titulo": c.nome, "desc": ""} for c in categorias]
    itens.append({"id": "finalizar", "titulo": "✅ Finalizar orçamento", "desc": "Criar com itens já selecionados"})

    return await enviar_lista_selecao(
        telefone=sessao.telefone,
        titulo="Catálogo de serviços",
        descricao=f"Cliente: *{cliente.nome}*\nEscolha uma categoria:",
        secoes=[{"titulo": "Categorias", "itens": itens}],
        botao_texto="Selecionar",
        instancia=_instancia(empresa),
    )


async def _mostrar_itens_direto(
    db: Session, sessao: SessaoWhatsapp, contexto: dict, empresa: Empresa
) -> bool:
    """Fallback para empresas sem categorias: lista todos os serviços."""
    servicos = (
        db.query(Servico)
        .filter(Servico.empresa_id == empresa.id, Servico.ativo == True)
        .limit(10)
        .all()
    )
    if not servicos:
        await enviar_mensagem_texto(
            sessao.telefone, "Nenhum serviço no catálogo. Cadastre serviços no painel.", empresa=empresa
        )
        _encerrar_sessao(db, sessao.telefone)
        return False

    _atualizar_sessao(db, sessao, "selecionando_item", contexto)
    return await _enviar_lista_itens(sessao.telefone, servicos, empresa)


async def _step_categoria(
    db: Session, sessao: SessaoWhatsapp, categoria_id: int, empresa: Empresa
) -> bool:
    servicos = (
        db.query(Servico)
        .filter(
            Servico.empresa_id == empresa.id,
            Servico.categoria_id == categoria_id,
            Servico.ativo == True,
        )
        .limit(10)
        .all()
    )
    if not servicos:
        await enviar_mensagem_texto(
            sessao.telefone, "Nenhum serviço nesta categoria. Escolha outra.", empresa=empresa
        )
        return True

    _atualizar_sessao(db, sessao, "selecionando_item", dict(sessao.contexto or {}))
    return await _enviar_lista_itens(sessao.telefone, servicos, empresa)


async def _enviar_lista_itens(
    telefone: str, servicos: list[Servico], empresa: Empresa
) -> bool:
    itens = [
        {"id": f"item:{s.id}", "titulo": s.nome, "desc": _brl(float(s.preco_padrao))}
        for s in servicos
    ]
    itens.append({"id": "finalizar", "titulo": "✅ Finalizar orçamento", "desc": "Criar com itens selecionados"})
    return await enviar_lista_selecao(
        telefone=telefone,
        titulo="Selecionar item",
        descricao="Escolha um item para adicionar ao orçamento:",
        secoes=[{"titulo": "Itens disponíveis", "itens": itens}],
        botao_texto="Adicionar",
        instancia=_instancia(empresa),
    )


async def _step_voltar_categorias(
    db: Session, sessao: SessaoWhatsapp, empresa: Empresa
) -> bool:
    categorias = (
        db.query(CategoriaCatalogo)
        .filter(CategoriaCatalogo.empresa_id == empresa.id)
        .all()
    )
    if not categorias:
        return await _mostrar_itens_direto(db, sessao, dict(sessao.contexto or {}), empresa)

    _atualizar_sessao(db, sessao, "selecionando_categoria", dict(sessao.contexto or {}))
    itens = [{"id": f"categoria:{c.id}", "titulo": c.nome, "desc": ""} for c in categorias]
    itens.append({"id": "finalizar", "titulo": "✅ Finalizar orçamento", "desc": ""})

    return await enviar_lista_selecao(
        telefone=sessao.telefone,
        titulo="Adicionar mais itens",
        descricao="Escolha outra categoria:",
        secoes=[{"titulo": "Categorias", "itens": itens}],
        botao_texto="Selecionar",
        instancia=_instancia(empresa),
    )


async def _step_item(
    db: Session, sessao: SessaoWhatsapp, item_id: int, empresa: Empresa
) -> bool:
    servico = db.query(Servico).filter(
        Servico.id == item_id, Servico.empresa_id == empresa.id
    ).first()
    if not servico:
        await enviar_mensagem_texto(sessao.telefone, "Item não encontrado.", empresa=empresa)
        return False

    contexto = dict(sessao.contexto or {})
    itens = list(contexto.get("itens", []))
    itens.append({"servico_id": servico.id, "nome": servico.nome, "valor_unit": float(servico.preco_padrao), "quantidade": 1})
    contexto["itens"] = itens
    _atualizar_sessao(db, sessao, "selecionando_item", contexto)

    total_atual = sum(i["valor_unit"] * i["quantidade"] for i in itens)
    resumo = "\n".join(f"• {i['nome']} — {_brl(i['valor_unit'])}" for i in itens)

    secoes = [
        {
            "titulo": "Próximo passo",
            "itens": [
                {"id": "mais_itens", "titulo": "➕ Adicionar mais itens", "desc": "Escolher outra categoria"},
                {"id": "finalizar", "titulo": "✅ Finalizar orçamento", "desc": f"Total: {_brl(total_atual)}"},
            ],
        }
    ]
    return await enviar_lista_selecao(
        telefone=sessao.telefone,
        titulo=f"✅ {servico.nome} adicionado!",
        descricao=f"{resumo}\n\nTotal: {_brl(total_atual)}",
        secoes=secoes,
        botao_texto="Continuar",
        instancia=_instancia(empresa),
    )


async def _step_finalizar(
    db: Session, sessao: SessaoWhatsapp, empresa: Empresa
) -> bool:
    from app.services.orcamento_core_service import criar_orcamento_core
    from app.services.whatsapp_bot_service import _usuario_por_telefone_operador

    contexto = sessao.contexto or {}
    cliente_id = contexto.get("cliente_id")
    itens_raw = contexto.get("itens", [])

    if not cliente_id or not itens_raw:
        await enviar_mensagem_texto(
            sessao.telefone,
            "Nenhum item selecionado. Envie 'novo orçamento' para recomeçar.",
            empresa=empresa,
        )
        _encerrar_sessao(db, sessao.telefone)
        return False

    usuario = _usuario_por_telefone_operador(sessao.telefone, db)

    try:
        orc = criar_orcamento_core(
            db=db,
            empresa=empresa,
            usuario_criador=usuario,
            cliente_id=cliente_id,
            itens=itens_raw,
            origem="WhatsApp Interativo",
        )
    except ValueError as e:
        await enviar_mensagem_texto(sessao.telefone, f"Erro ao criar orçamento: {e}", empresa=empresa)
        _encerrar_sessao(db, sessao.telefone)
        return False

    _atualizar_sessao(db, sessao, "confirmando_envio", {
        "orcamento_id": orc.id,
        "orcamento_numero": orc.numero,
        "cliente_id": cliente_id,
        "cliente_nome": contexto.get("cliente_nome", ""),
    })

    nome_cliente = contexto.get("cliente_nome", "")
    secoes = [
        {
            "titulo": "O que deseja fazer?",
            "itens": [
                {"id": "enviar_cliente", "titulo": "📤 Enviar ao cliente agora", "desc": f"Envia WhatsApp para {nome_cliente}"},
                {"id": "salvar_rascunho", "titulo": "💾 Salvar como rascunho", "desc": "Enviar depois pelo painel"},
            ],
        }
    ]
    return await enviar_lista_selecao(
        telefone=sessao.telefone,
        titulo=f"✅ Orçamento {orc.numero} criado!",
        descricao=f"Total: {_brl(float(orc.total))}\nCliente: {nome_cliente}",
        secoes=secoes,
        botao_texto="Escolher",
        instancia=_instancia(empresa),
    )


async def _step_enviar_cliente(
    db: Session, sessao: SessaoWhatsapp, empresa: Empresa
) -> bool:
    from app.services.whatsapp_service import enviar_orcamento_completo

    contexto = sessao.contexto or {}
    orc_id = contexto.get("orcamento_id")
    if not orc_id:
        _encerrar_sessao(db, sessao.telefone)
        return False

    orc = db.query(Orcamento).filter(Orcamento.id == orc_id).first()
    if not orc or not orc.cliente or not orc.cliente.telefone:
        await enviar_mensagem_texto(sessao.telefone, "Erro: cliente sem telefone cadastrado.", empresa=empresa)
        _encerrar_sessao(db, sessao.telefone)
        return False

    try:
        from app.utils.pdf_utils import build_orcamento_dict
        orc_dict = build_orcamento_dict(orc)
    except Exception:
        orc_dict = {"numero": orc.numero, "cliente_nome": orc.cliente.nome, "total": float(orc.total)}

    try:
        await enviar_orcamento_completo(orc.cliente.telefone, orc_dict, empresa=empresa)
        await enviar_mensagem_texto(
            sessao.telefone,
            f"📤 Orçamento *{orc.numero}* enviado ao cliente *{orc.cliente.nome}*!",
            empresa=empresa,
        )
    except Exception as e:
        logger.error("[Interativo] Falha ao enviar ao cliente: %s", e)
        await enviar_mensagem_texto(
            sessao.telefone,
            "Erro ao enviar ao cliente. Tente pelo painel.",
            empresa=empresa,
        )

    _encerrar_sessao(db, sessao.telefone)
    return True
