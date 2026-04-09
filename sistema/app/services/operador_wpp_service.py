"""
Orquestra o fluxo completo do operador via WhatsApp:
1. Usa assistente_unificado_v2 (motor unificado com Tool Use nativo)
2. Interpreta AIResponse e envia interação adequada (Poll, Lista ou texto)
3. Gerencia confirmações pendentes via SessionStore (banco + RAM)
"""

import logging
from sqlalchemy.orm import Session

from app.utils.orcamento_utils import brl_fmt

logger = logging.getLogger(__name__)

# ── Palavras-chave para detecção de resposta de poll ────────────────────────

_CONFIRMAR = {"confirmar", "sim", "ok", "1", "s"}
_CANCELAR = {"cancelar", "não", "nao", "2", "n"}


def _wpp_sessao_id(telefone: str) -> str:
    return f"wpp-op-{telefone}"


def _salvar_pending_wpp(sessao_id: str, pending: dict):
    """Guarda o pending_action na sessão RAM."""
    try:
        from app.services.cotte_context_builder import _sessions

        if sessao_id not in _sessions:
            _sessions[sessao_id] = {}
        _sessions[sessao_id]["wpp_pending"] = pending
    except Exception:
        pass


def _recuperar_pending_wpp(sessao_id: str) -> dict | None:
    try:
        from app.services.cotte_context_builder import _sessions

        return _sessions.get(sessao_id, {}).get("wpp_pending")
    except Exception:
        return None


def _limpar_pending_wpp(sessao_id: str):
    try:
        from app.services.cotte_context_builder import _sessions

        if sessao_id in _sessions:
            _sessions[sessao_id].pop("wpp_pending", None)
    except Exception:
        pass


def _titulo_confirmacao_tool(tool: str) -> str:
    """Título curto para enquete de confirmação (WhatsApp)."""
    m = {
        "criar_orcamento": "Novo orçamento",
        "editar_orcamento": "Editar orçamento",
        "editar_item_orcamento": "Editar item do orçamento",
        "aprovar_orcamento": "Aprovar orçamento",
        "recusar_orcamento": "Recusar orçamento",
        "enviar_orcamento_whatsapp": "Enviar orçamento (WhatsApp)",
        "enviar_orcamento_email": "Enviar orçamento (e-mail)",
        "duplicar_orcamento": "Duplicar orçamento",
        "anexar_documento_orcamento": "Anexar documento ao orçamento",
        "criar_cliente": "Cadastrar cliente",
        "editar_cliente": "Editar cliente",
        "excluir_cliente": "Excluir cliente",
        "criar_movimentacao_financeira": "Lançamento no caixa",
        "criar_despesa": "Nova despesa",
        "marcar_despesa_paga": "Quitar despesa",
        "registrar_pagamento_recebivel": "Registrar recebimento",
        "criar_parcelamento": "Criar parcelamento",
        "criar_agendamento": "Novo agendamento",
        "cancelar_agendamento": "Cancelar agendamento",
        "remarcar_agendamento": "Remarcar agendamento",
        "cadastrar_material": "Cadastrar material/serviço",
    }
    if tool in m:
        return m[tool]
    return (tool or "ação").replace("_", " ").strip().title()


def _mensagem_confirmacao_whatsapp(
    tool: str, dados: dict, resposta_ia: str | None
) -> str:
    """Monta texto da enquete com contexto operacional (cliente, orçamento, alterações)."""
    linhas: list[str] = []
    titulo = _titulo_confirmacao_tool(tool)
    linhas.append(f"⚠️ *{titulo} — confirma?*")

    if dados.get("conta_descricao"):
        linhas.append(f"📝 Conta: {dados['conta_descricao']}")
        if dados.get("conta_saldo_aberto") is not None:
            linhas.append(
                f"💳 Saldo em aberto: {brl_fmt(float(dados['conta_saldo_aberto']))}"
            )
    if dados.get("despesa_favorecido"):
        linhas.append(f"🏢 Favorecido: {dados['despesa_favorecido']}")

    if dados.get("agendamento_numero"):
        linhas.append(f"📅 Agendamento: {dados['agendamento_numero']}")
    if dados.get("agendamento_data_atual"):
        linhas.append(f"🕐 Data/hora atual: {dados['agendamento_data_atual']}")

    if dados.get("orcamento_numero"):
        linhas.append(f"📄 Orçamento: {dados['orcamento_numero']}")

    cn = (
        dados.get("cliente_nome")
        or dados.get("cliente_nome_resolvido")
        or dados.get("cliente_nome_registro")
    )
    if cn:
        tag = " (novo cliente)" if dados.get("cliente_auto_criar") else ""
        linhas.append(f"👤 Cliente: {cn}{tag}")

    if dados.get("total_atual") is not None:
        linhas.append(f"💰 Total atual: {brl_fmt(float(dados['total_atual']))}")
    if dados.get("status_orcamento"):
        linhas.append(f"📌 Status: {dados['status_orcamento']}")

    mud = dados.get("mudancas")
    if isinstance(mud, list) and mud:
        linhas.append("")
        linhas.append("*Alterações:*")
        for m in mud[:14]:
            if m:
                linhas.append(f"• {m}")

    # Campos dos args quando extras não cobriram (ex.: movimentação)
    if tool == "criar_movimentacao_financeira":
        if dados.get("tipo"):
            linhas.append(f"↕️ Tipo: {dados['tipo']}")
        if dados.get("descricao"):
            linhas.append(f"📋 Descrição: {dados['descricao']}")
        v = dados.get("valor")
        if v is not None:
            linhas.append(f"💵 Valor: {brl_fmt(float(v))}")
    elif tool == "criar_despesa":
        if dados.get("descricao"):
            linhas.append(f"📋 {dados['descricao']}")
        if dados.get("valor") is not None:
            linhas.append(f"💵 Valor: {brl_fmt(float(dados['valor']))}")
        if dados.get("data_vencimento"):
            linhas.append(f"📆 Vencimento: {dados['data_vencimento']}")
    elif tool == "criar_parcelamento":
        if dados.get("tipo"):
            linhas.append(f"↕️ Tipo: {dados['tipo']}")
        if dados.get("descricao"):
            linhas.append(f"📋 {dados['descricao']}")
        if dados.get("valor_total") is not None:
            linhas.append(f"💵 Total: {brl_fmt(float(dados['valor_total']))}")
        if dados.get("parcelas"):
            linhas.append(f"🔢 Parcelas: {dados['parcelas']}")
        if dados.get("primeira_data"):
            linhas.append(f"📆 1ª parcela: {dados['primeira_data']}")

    corpo = [x for x in linhas[1:] if x]
    if len(corpo) < 1:
        tail = (resposta_ia or "").strip()
        if tail:
            linhas.append("")
            linhas.append(tail[:450])
        else:
            linhas.append("")
            linhas.append("Confira no painel e responda *Confirmar* ou *Cancelar*.")

    return "\n".join(linhas)


def _detectar_resposta_poll(mensagem: str) -> str | None:
    """Retorna 'CONFIRMAR', 'CANCELAR' ou None."""
    norm = mensagem.strip().lower().rstrip(".,!?")
    if norm in _CONFIRMAR:
        return "CONFIRMAR"
    if norm in _CANCELAR:
        return "CANCELAR"
    return None


# ── Entry point principal ────────────────────────────────────────────────────


async def processar_operador_wpp(
    telefone: str,
    mensagem: str,
    operador,  # Usuario
    db: Session,
    empresa,  # Empresa
) -> None:
    from app.services.whatsapp_service import enviar_mensagem_texto

    sessao_id = _wpp_sessao_id(telefone)

    # 1. Verificar se há pending_action esperando confirmação
    pending = _recuperar_pending_wpp(sessao_id)
    if pending:
        resposta_poll = _detectar_resposta_poll(mensagem)
        if resposta_poll == "CONFIRMAR":
            _limpar_pending_wpp(sessao_id)

            # Criação de orçamento (ação legada direta sem token V2)
            if pending.get("acao") == "CRIAR_ORCAMENTO" and not pending.get(
                "confirmation_token"
            ):
                from app.services.ai_tools.orcamento_tools import (
                    CriarOrcamentoInput,
                    _criar_orcamento,
                )
                from app.utils.orcamento_utils import brl_fmt

                dados = pending.get("dados", {})
                logger.info(
                    f"[OperadorWPP] Confirmando CRIAR_ORCAMENTO com dados: {dados}"
                )

                try:
                    valor_unit = float(dados.get("valor") or 0)
                except (ValueError, TypeError):
                    valor_unit = 0.1

                if valor_unit <= 0.0:
                    valor_unit = 0.1

                try:
                    inp = CriarOrcamentoInput(
                        cliente_id=dados.get("cliente_id"),
                        cliente_nome=dados.get("cliente_nome") or "A Definir",
                        itens=[
                            {
                                "descricao": dados.get("servico") or "Serviço",
                                "quantidade": 1.0,
                                "valor_unit": valor_unit,
                            }
                        ],
                        observacoes=dados.get("observacoes"),
                        cadastrar_materiais_novos=False,
                    )
                    res = await _criar_orcamento(inp, db=db, current_user=operador)

                    if res.get("error"):
                        await enviar_mensagem_texto(
                            telefone,
                            f"Erro ao criar orçamento: {res['error']}",
                            empresa=empresa,
                        )
                    else:
                        numero = res.get("numero", "")
                        total_fmt = brl_fmt(res.get("total", 0))
                        await enviar_mensagem_texto(
                            telefone,
                            f'✅ Orçamento {numero} criado com sucesso!\nTotal: {total_fmt}\n\nPara enviá-lo ao cliente, responda: "enviar {numero}"',
                            empresa=empresa,
                        )
                except Exception as e:
                    logger.error(
                        "[OperadorWPP] Erro interno ao criar orçamento confirmado: %s",
                        e,
                    )
                    import traceback

                    logger.error(traceback.format_exc())
                    await enviar_mensagem_texto(
                        telefone,
                        "Erro interno ao gerar orçamento. Tente novamente.",
                        empresa=empresa,
                    )
                return

            # Confirmação via token do V2
            if pending.get("confirmation_token"):
                try:
                    from app.services.cotte_ai_hub import assistente_unificado_v2

                    ai_resp = await assistente_unificado_v2(
                        mensagem=mensagem,
                        sessao_id=sessao_id,
                        db=db,
                        current_user=operador,
                        confirmation_token=pending["confirmation_token"],
                    )
                    await _enviar_resposta(telefone, ai_resp, sessao_id, empresa)
                except Exception as e:
                    logger.error("[OperadorWPP] Erro ao confirmar via V2: %s", e)
                    await enviar_mensagem_texto(
                        telefone, "Erro ao confirmar. Tente novamente.", empresa=empresa
                    )
                return

        elif resposta_poll == "CANCELAR":
            _limpar_pending_wpp(sessao_id)
            await enviar_mensagem_texto(telefone, "❌ Ação cancelada.", empresa=empresa)
            return

        # Mensagem não é resposta de poll → trata como novo comando
        _limpar_pending_wpp(sessao_id)

    # 2. Processar com assistente_unificado_v2 (engine unificado com Tool Use nativo)
    try:
        from app.services.cotte_ai_hub import assistente_unificado_v2
        from app.services.cotte_context_builder import SessionStore

        # Garante sessão persistida no banco para recovery pós-reinício
        SessionStore.ensure_sessao_db(
            sessao_id=sessao_id,
            empresa_id=empresa.id,
            usuario_id=operador.id,
            db=db,
        )

        ai_resp = await assistente_unificado_v2(
            mensagem=mensagem,
            sessao_id=sessao_id,
            db=db,
            current_user=operador,
        )
    except Exception as e:
        logger.error("[OperadorWPP] Erro no assistente V2: %s", e)
        await enviar_mensagem_texto(
            telefone, "Erro interno. Tente novamente.", empresa=empresa
        )
        return

    await _enviar_resposta(telefone, ai_resp, sessao_id, empresa)


async def _enviar_resposta(
    telefone: str,
    ai_resp,  # AIResponse
    sessao_id: str,
    empresa,  # Empresa
) -> None:
    """Interpreta AIResponse e envia a mensagem/interação adequada."""
    from app.services.whatsapp_service import enviar_mensagem_texto
    from app.services.operador_interacao_service import (
        enviar_poll_confirmacao,
        texto_opcoes_numeradas,
        sanitizar_para_whatsapp,
    )

    # Caso 1: ação pendente do V2 (confirmation_token) — envia Poll de confirmação
    if ai_resp.pending_action:
        pending_data = {
            "acao": ai_resp.pending_action.get("tool", "ACAO"),
            "confirmation_token": ai_resp.pending_action.get("confirmation_token")
            or ai_resp.pending_action.get("token"),
            "dados": ai_resp.dados or {},
        }
        _salvar_pending_wpp(sessao_id, pending_data)

        dados = ai_resp.dados or {}
        tool = ai_resp.pending_action.get("tool", "")

        if tool == "criar_orcamento":
            cliente = (
                dados.get("cliente_nome")
                or dados.get("cliente_nome_resolvido")
                or ""
            )
            itens = dados.get("itens") or []
            total = dados.get("total", 0)
            if itens:
                servico = itens[0].get("descricao", "")
                if len(itens) > 1:
                    servico += f" (+{len(itens) - 1} item(ns))"
                total_calc = sum(
                    float(i.get("quantidade") or 1) * float(i.get("valor_unit") or 0)
                    for i in itens
                )
            else:
                servico = dados.get("servico", "")
                total_calc = float(total or 0)
            total_fmt = brl_fmt(total_calc)
            tag_cli = " (novo cliente)" if dados.get("cliente_auto_criar") else ""
            linhas = [
                f"⚠️ *{_titulo_confirmacao_tool('criar_orcamento')} — confirma?*",
                "",
                f"👤 Cliente: {cliente or '—'}{tag_cli}",
                f"🛍 Item: {servico or '—'}",
                f"💰 Total: {total_fmt}",
            ]
            pergunta = "\n".join(linhas)
        else:
            pergunta = _mensagem_confirmacao_whatsapp(
                tool, dados, ai_resp.resposta
            )

        ok = await enviar_poll_confirmacao(
            telefone, pergunta, ["Confirmar", "Cancelar"]
        )
        if not ok:
            texto = texto_opcoes_numeradas(
                "Confirmação necessária", pergunta, ["Confirmar", "Cancelar"]
            )
            await enviar_mensagem_texto(telefone, texto, empresa=empresa)
        return

    # Caso 2: orçamento criado — notificação rica
    if ai_resp.tipo_resposta == "orcamento_criado":
        dados = ai_resp.dados or {}
        numero = dados.get("numero", "?")
        total = dados.get("total", 0)
        seq = numero.split("-")[1] if "-" in numero else numero
        texto = (
            f"✅ *Orçamento {numero} criado!*\n"
            f"Total: *R$ {total:.2f}*\n\n"
            f"Para enviar ao cliente: *enviar {seq}*"
        )
        await enviar_mensagem_texto(telefone, texto, empresa=empresa)
        return

    # Caso 2b: orçamento atualizado — notificação
    if ai_resp.tipo_resposta == "orcamento_atualizado":
        dados = ai_resp.dados or {}
        numero = dados.get("numero", "?")
        total = dados.get("total", 0)
        seq = numero.split("-")[1] if "-" in numero else numero
        texto = (
            f"✅ *Orçamento {numero} atualizado!*\n"
            f"Total: *R$ {total:.2f}*\n\n"
            f"Para ver o orçamento: *ver {seq}*"
        )
        await enviar_mensagem_texto(telefone, texto, empresa=empresa)
        return

    # Caso 3: Preview de Orçamento legado (orcamento_preview)
    if ai_resp.tipo_resposta == "orcamento_preview":
        dados = ai_resp.dados or {}
        cliente = dados.get("cliente_nome", "A definir")
        servico = dados.get("servico", "")
        valor = float(dados.get("valor") or 0)
        desc = float(dados.get("desconto") or 0)
        tipo_desc = dados.get("desconto_tipo") or "percentual"

        texto_preview = f"📋 *Prévia do Orçamento*\n\n"
        texto_preview += f"👤 *Cliente:* {cliente}\n"
        texto_preview += f"🛠 *Serviço:* {servico}\n"
        texto_preview += f"💰 *Valor:* R$ {valor:.2f}\n"
        if desc > 0:
            texto_preview += f"🏷 *Desconto:* {desc:.0f}{'%' if tipo_desc == 'percentual' else ' R$'}\n"

        pergunta = f"{ai_resp.resposta}\n\n{texto_preview}"

        _salvar_pending_wpp(sessao_id, {"acao": "CRIAR_ORCAMENTO", "dados": dados})

        ok = await enviar_poll_confirmacao(
            telefone, pergunta, ["Confirmar", "Cancelar"]
        )
        if not ok:
            texto = texto_opcoes_numeradas(
                "Confirmação", pergunta, ["Confirmar", "Cancelar"]
            )
            await enviar_mensagem_texto(telefone, texto, empresa=empresa)
        return

    # Caso 4: resposta genérica — limpa markdown para WhatsApp
    texto = (ai_resp.resposta or "Sem resposta.").strip()
    texto = sanitizar_para_whatsapp(texto)
    if not ai_resp.sucesso:
        texto = f"❌ {texto}"
    await enviar_mensagem_texto(telefone, texto, empresa=empresa)
