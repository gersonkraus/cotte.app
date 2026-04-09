# services/whatsapp_bot_service.py
"""
Logica de negocio do bot WhatsApp (COTTE Bot).
Contem todas as funcoes processar_* e helpers que antes estavam no router.

Mantem separacao clara: router = HTTP/webhook, service = negocio.
"""
from __future__ import annotations

import logging
import re
import secrets
import unicodedata
from datetime import datetime, timezone, timedelta
from decimal import Decimal as _Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import SessionLocal
from app.models.models import (
    Cliente,
    Orcamento,
    ItemOrcamento,
    Empresa,
    StatusOrcamento,
    Notificacao,
    Servico,
    Usuario,
    HistoricoEdicao,
    FormaPagamentoConfig,
)
from app.services.ia_service import (
    interpretar_mensagem,
    interpretar_comando_operador,
    gerar_resposta_bot,
)
from app.services.plano_service import (
    ia_automatica_habilitada,
    checar_limite_orcamentos,
)
from app.services.whatsapp_service import (
    enviar_mensagem_texto,
    enviar_orcamento_completo,
)
from app.services.pdf_service import gerar_pdf_orcamento
from app.services.quote_notification_service import handle_quote_status_changed
from app.services import financeiro_service
from app.utils.phone import normalize_phone_number
from app.utils.desconto import (
    erro_validacao_desconto,
    resolver_max_percent_desconto,
    aplicar_desconto,
)
from app.utils.orcamento_utils import gerar_numero, renomear_numero_aprovado

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT — Processamento principal de mensagem
# ══════════════════════════════════════════════════════════════════════════════


async def processar_mensagem(
    telefone: str,
    mensagem: str,
    empresa_id: int | None = None,
):
    """
    Processa a mensagem em background para nao bloquear o webhook.
    Cria sua propria sessao de banco para evitar uso de sessao ja fechada
    pelo FastAPI apos o retorno da response.
    Se `empresa_id` e fornecido, o bot opera no contexto dessa empresa.
    """
    db = SessionLocal()
    try:
        empresa_contexto: "Empresa | None" = (
            db.query(Empresa).filter(Empresa.id == empresa_id).first()
            if empresa_id
            else None
        )
        msg_upper = mensagem.strip().upper()
        msg_limpa = msg_upper.rstrip(".,!?;:")

        if msg_limpa in ["SIM", "CONFIRMO", "CORRETO", "CONFIRMAR"]:
            if await _confirmar_aceite_pendente(telefone, db, empresa_contexto):
                return

        if msg_limpa in ["ACEITO", "ACEITO!", "SIM", "OK"] or msg_upper.startswith("ACEITO"):
            await _processar_aprovacao(telefone, db, empresa_contexto)
            return

        if (
            msg_limpa in ["NAO", "RECUSO", "DESISTO"]
            or "NAO QUERO" in msg_upper
            or "RECUSO" in msg_upper
        ):
            await _processar_recusa(telefone, db, empresa_contexto)
            return

        match = re.match(r"^EMP-(\d+)$", msg_upper)
        if match:
            await _processar_codigo_empresa(telefone, int(match.group(1)), mensagem, db)
            return

        empresa_operador = empresa_contexto or _empresa_por_operador(telefone, db)
        if empresa_operador:
            try:
                from app.services.ai_intention_classifier import detectar_intencao_assistente_async
                _classif = await detectar_intencao_assistente_async(mensagem)
                _intencao_gestor = _classif.intencao.value
            except Exception:
                _intencao_gestor = "OPERADOR"

            _INTENCOES_ASSISTENTE_GESTOR = {
                "SALDO_RAPIDO", "FATURAMENTO", "CONTAS_RECEBER", "CONTAS_PAGAR",
                "DASHBOARD", "PREVISAO", "INADIMPLENCIA", "ANALISE",
                "CONVERSAO", "NEGOCIO", "ONBOARDING", "AJUDA_SISTEMA", "CONVERSACAO",
            }
            if _intencao_gestor in _INTENCOES_ASSISTENTE_GESTOR:
                await _processar_assistente_gestor(telefone, mensagem, empresa_operador, db)
                return

            _ag_cmd = _is_agendamento_cmd(mensagem)
            if _ag_cmd == "AGENDAR":
                await _processar_comando_agendamento(telefone, mensagem, db, empresa_operador)
                return
            elif _ag_cmd == "AGENDAMENTOS_HOJE":
                await _listar_agendamentos_hoje(telefone, db, empresa_operador)
                return
            elif _ag_cmd == "MEUS_AGENDAMENTOS":
                await _listar_meus_agendamentos(telefone, db, empresa_operador)
                return

            cmd = await interpretar_comando_operador(mensagem)
            acao = cmd.get("acao", "DESCONHECIDO")
            orc_id = cmd.get("orcamento_id")

            await _despachar_comando_operador(
                acao, orc_id, cmd, telefone, mensagem, db, empresa_operador
            )
            return

        if any(kw in mensagem.lower() for kw in ["orçamento", "orcamento", "fazer", "valor", "serviço", "servico"]):
            await _criar_orcamento_via_bot(telefone, mensagem, db, empresa=empresa_contexto)
            return

        cliente_existente = _cliente_por_telefone(telefone, db, empresa_contexto.id if empresa_contexto else None)
        if not cliente_existente:
            empresa = empresa_contexto or _empresa_por_telefone_cliente(telefone, db)
            if empresa and getattr(empresa, "boas_vindas_ativo", True):
                texto_cfg = (empresa.msg_boas_vindas or "").strip()
                if not texto_cfg:
                    texto_cfg = (
                        "Ola! Seja bem-vindo(a) a {empresa_nome}!\n\n"
                        "Sou o assistente virtual e posso ajudar com orcamentos.\n\n"
                        "Para solicitar um orcamento, descreva o servico que precisa. Exemplo:\n"
                        '_"Pintura de 2 quartos"_\n\n'
                        "Estamos a disposição!"
                    )
                texto = texto_cfg.replace("{empresa_nome}", empresa.nome or "sua empresa")
                await enviar_mensagem_texto(telefone, texto, empresa=empresa)
                return

        empresa = empresa_contexto or _empresa_por_telefone_cliente(telefone, db)
        nome_empresa = empresa.nome if empresa else "COTTE"
        resposta = await gerar_resposta_bot(mensagem, {"nome": nome_empresa})
        await enviar_mensagem_texto(telefone, resposta, empresa=empresa)

    except Exception as e:
        logger.warning("[webhook] Erro ao processar mensagem de %s: %s", telefone, e)
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
# DESPACHO DE COMANDOS DO OPERADOR
# ══════════════════════════════════════════════════════════════════════════════


async def _despachar_comando_operador(
    acao: str, orc_id, cmd, telefone, mensagem, db, empresa_operador
):
    if acao == "AJUDA":
        await _enviar_ajuda(telefone, empresa_operador)

    elif acao == "VER" and orc_id:
        await _ver_orcamento(orc_id, telefone, db, empresa_operador)

    elif acao == "DESCONTO" and orc_id:
        valor_str = str(cmd.get("valor") or 0)
        sufixo = "REAIS" if cmd.get("desconto_tipo") == "fixo" else "%"
        await _editar_desconto_orcamento(orc_id, valor_str, sufixo, telefone, db, empresa_operador)

    elif acao == "ADICIONAR" and orc_id and cmd.get("descricao") and cmd.get("valor"):
        await _adicionar_item_orcamento(orc_id, cmd["descricao"], float(cmd["valor"]), telefone, db, empresa_operador)

    elif acao == "REMOVER" and orc_id and cmd.get("num_item"):
        await _remover_item_orcamento(orc_id, int(cmd["num_item"]), telefone, db, empresa_operador)

    elif acao == "ENVIAR" and orc_id:
        await _enviar_orcamento_para_cliente(orc_id, telefone, db, empresa_operador)

    elif acao == "APROVAR" and orc_id:
        await _aprovar_orcamento_via_bot(orc_id, telefone, db, empresa_operador)

    elif acao == "RECUSAR" and orc_id:
        await _recusar_orcamento_via_bot(orc_id, telefone, db, empresa_operador)

    elif acao == "CRIAR":
        await _criar_orcamento_via_bot(telefone, mensagem, db, empresa=empresa_operador)

    elif acao == "AGENDAR":
        await _processar_comando_agendamento(telefone, mensagem, db, empresa_operador)

    elif acao == "AGENDAMENTOS_HOJE":
        await _listar_agendamentos_hoje(telefone, db, empresa_operador)

    elif acao == "MEUS_AGENDAMENTOS":
        await _listar_meus_agendamentos(telefone, db, empresa_operador)

    elif acao in {"VER", "APROVAR", "RECUSAR", "ENVIAR", "DESCONTO", "ADICIONAR", "REMOVER"} and not orc_id:
        msg_sem_id = {
            "VER": "Qual orcamento voce quer ver? Digite: ver 5",
            "APROVAR": "Qual orcamento voce quer aprovar? Digite: aprovar 5",
            "RECUSAR": "Qual orcamento voce quer recusar? Digite: recusar 5",
            "ENVIAR": "Qual orcamento voce quer enviar? Digite: enviar 5",
            "DESCONTO": "Em qual orcamento? Digite: 10% no 5",
            "ADICIONAR": "Em qual orcamento? Digite: adiciona pintura 80 no 5",
            "REMOVER": "De qual orcamento? Digite: remove item 2 do 5",
            "AGENDAR": "Para agendar a partir de um orcamento: agendar 5 amanha 14h",
            "AGENDAMENTOS_HOJE": "",
            "MEUS_AGENDAMENTOS": "",
        }
        await enviar_mensagem_texto(telefone, msg_sem_id.get(acao, "Nao entendi. Digite ajuda."), empresa=empresa_operador)

    else:
        await _criar_orcamento_via_bot(telefone, mensagem, db, empresa=empresa_operador)


# ══════════════════════════════════════════════════════════════════════════════
# ASSISTENTE GESTOR
# ══════════════════════════════════════════════════════════════════════════════


async def _processar_assistente_gestor(
    telefone: str,
    mensagem: str,
    empresa: "Empresa",
    db: Session,
) -> None:
    """
    Processa query financeira/conversacional do gestor usando o assistente IA completo.
    """
    from app.services.cotte_ai_hub import assistente_unificado

    usuario = _resolver_usuario_criador_orcamento(empresa, telefone, db)
    sessao_id = f"wpp_{telefone}"

    try:
        ai_resp = await assistente_unificado(
            mensagem=mensagem,
            sessao_id=sessao_id,
            db=db,
            empresa_id=empresa.id,
            usuario_id=usuario.id if usuario else 0,
        )
        texto = (ai_resp.resposta or "").strip() or "Nao consegui processar sua mensagem."
    except Exception:
        texto = "Ocorreu um erro ao processar sua mensagem. Tente novamente."

    await enviar_mensagem_texto(telefone, texto, empresa=empresa)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS DE TELEFONE E BUSCA
# ══════════════════════════════════════════════════════════════════════════════


def _digitos_telefone(telefone: str) -> str:
    return "".join(filter(str.isdigit, telefone or ""))


def _is_postgresql(db: Session) -> bool:
    return db.get_bind().dialect.name == "postgresql"


def _cliente_por_telefone(
    telefone: str, db: Session, empresa_id: int | None = None
) -> "Cliente | None":
    dig = _digitos_telefone(telefone)
    if len(dig) < 8:
        return None
    sufixo = dig[-8:]

    if _is_postgresql(db):
        digits_expr = func.regexp_replace(Cliente.telefone, r"[^0-9]", "", "g")
        suffix_expr = func.right(digits_expr, 8)
        q = db.query(Cliente).filter(
            Cliente.telefone.isnot(None),
            Cliente.telefone != "",
            suffix_expr == sufixo,
        )
        if empresa_id is not None:
            q = q.filter(Cliente.empresa_id == empresa_id)
        return q.first()

    q = db.query(Cliente).filter(Cliente.telefone.isnot(None), Cliente.telefone != "")
    if empresa_id is not None:
        q = q.filter(Cliente.empresa_id == empresa_id)
    for c in q.all():
        dig_cli = _digitos_telefone(c.telefone)
        if len(dig_cli) >= 8 and dig_cli[-8:] == sufixo:
            return c
    return None


def _empresa_por_operador(telefone: str, db: Session) -> "Empresa | None":
    dig = _digitos_telefone(telefone)
    if len(dig) < 8:
        return None
    sufixo = dig[-8:]

    if _is_postgresql(db):
        digits_expr = func.regexp_replace(Empresa.telefone_operador, r"[^0-9]", "", "g")
        suffix_expr = func.right(digits_expr, 8)
        return (
            db.query(Empresa)
            .filter(
                Empresa.telefone_operador.isnot(None),
                Empresa.telefone_operador != "",
                suffix_expr == sufixo,
            )
            .first()
        )

    empresas = db.query(Empresa).filter(Empresa.telefone_operador.isnot(None)).all()
    for emp in empresas:
        dig_emp = _digitos_telefone(emp.telefone_operador or "")
        if len(dig_emp) >= 8 and dig_emp[-8:] == sufixo:
            return emp
    return None


def _empresa_por_telefone_cliente(telefone: str, db: Session) -> "Empresa | None":
    cliente = _cliente_por_telefone(telefone, db)
    return cliente.empresa if cliente else None


def _resolver_usuario_criador_orcamento(
    empresa: Empresa,
    telefone_operador: str,
    db: Session,
) -> "Usuario | None":
    email_empresa = (empresa.email or "").strip().lower()
    if email_empresa:
        dono = (
            db.query(Usuario)
            .filter(
                Usuario.empresa_id == empresa.id,
                Usuario.ativo.is_(True),
                Usuario.email.ilike(email_empresa),
            )
            .first()
        )
        if dono:
            return dono

    gestor = (
        db.query(Usuario)
        .filter(
            Usuario.empresa_id == empresa.id,
            Usuario.ativo.is_(True),
            Usuario.is_gestor.is_(True),
        )
        .order_by(Usuario.id.asc())
        .first()
    )
    if gestor:
        return gestor

    return (
        db.query(Usuario)
        .filter(
            Usuario.empresa_id == empresa.id,
            Usuario.ativo.is_(True),
        )
        .order_by(Usuario.id.asc())
        .first()
    )


def _normalizar_texto(txt: str) -> str:
    if not txt:
        return ""
    txt = txt.lower()
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(ch for ch in txt if not unicodedata.combining(ch))
    txt = re.sub(r"[^a-z0-9]+", " ", txt)
    return " ".join(txt.split())


def _encontrar_servico_catalogo(
    empresa: Empresa, descricao: str, db: Session
) -> "Servico | None":
    desc_norm = _normalizar_texto(descricao)
    if not desc_norm:
        return None

    palavras = [p for p in desc_norm.split() if len(p) >= 3]
    if not palavras:
        return None

    servicos = (
        db.query(Servico)
        .filter(Servico.empresa_id == empresa.id, Servico.ativo == True)
        .all()
    )
    if not servicos:
        return None

    for srv in servicos:
        if _normalizar_texto(srv.nome or "") == desc_norm:
            return srv

    melhor = None
    melhor_score = 0.0
    for srv in servicos:
        nome_norm = _normalizar_texto(srv.nome or "")
        if not nome_norm:
            continue
        tokens_nome = set(nome_norm.split())
        if not tokens_nome:
            continue
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


# ══════════════════════════════════════════════════════════════════════════════
# CONFIRMACAO DE ACEITE PENDENTE
# ══════════════════════════════════════════════════════════════════════════════


async def _confirmar_aceite_pendente(
    telefone: str, db: Session, empresa_contexto: "Empresa | None" = None
) -> bool:
    _TTL = timedelta(minutes=10)
    empresa_id = empresa_contexto.id if empresa_contexto else None
    cliente = _cliente_por_telefone(telefone, db, empresa_id)
    if not cliente:
        return False

    cutoff = datetime.now(timezone.utc) - _TTL
    orcamento = (
        db.query(Orcamento)
        .filter(
            Orcamento.cliente_id == cliente.id,
            Orcamento.aceite_pendente_em.isnot(None),
            Orcamento.aceite_pendente_em > cutoff,
        )
        .with_for_update()
        .first()
    )
    if not orcamento:
        return False

    orcamento.aceite_pendente_em = None

    if orcamento.status != StatusOrcamento.ENVIADO:
        db.commit()
        await enviar_mensagem_texto(
            telefone,
            "Este orcamento nao esta mais disponivel para aceite. Entre em contato com a empresa.",
            empresa=empresa_contexto or orcamento.empresa,
        )
        return True

    old_status = orcamento.status
    orcamento.status = StatusOrcamento.APROVADO
    renomear_numero_aprovado(orcamento, empresa_contexto)
    db.add(
        HistoricoEdicao(
            orcamento_id=orcamento.id,
            editado_por_id=None,
            descricao="Aprovado pelo cliente via WhatsApp.",
        )
    )
    financeiro_service.criar_contas_receber_aprovacao(orcamento, orcamento.empresa_id, db)
    try:
        from app.services.agendamento_auto_service import (
            processar_agendamento_apos_aprovacao,
        )

        processar_agendamento_apos_aprovacao(db, orcamento, canal="whatsapp")
    except Exception:
        logger.exception(
            "Falha ao processar agendamento pós-aprovação (WhatsApp aceite, orcamento_id=%s)",
            orcamento.id,
        )
    db.commit()
    db.refresh(orcamento)
    empresa = empresa_contexto or orcamento.empresa

    await handle_quote_status_changed(
        db=db,
        quote=orcamento,
        old_status=old_status,
        new_status=orcamento.status,
        source="whatsapp_aceito",
    )
    db.add(
        Notificacao(
            empresa_id=orcamento.empresa_id,
            orcamento_id=orcamento.id,
            tipo="aprovado",
            titulo="Orcamento aprovado",
            mensagem=f"Cliente {orcamento.cliente.nome} aprovou o orcamento {orcamento.numero}.",
        )
    )
    db.commit()

    await enviar_mensagem_texto(
        telefone,
        f"Perfeito! Orcamento *{orcamento.numero}* aprovado!\n"
        f"Em breve a empresa entrara em contato para confirmar.",
        empresa=empresa,
    )
    return True


# ══════════════════════════════════════════════════════════════════════════════
# PROCESSAR APROVACAO E RECUSA (CLIENTE)
# ══════════════════════════════════════════════════════════════════════════════


async def _processar_aprovacao(
    telefone: str, db: Session, empresa_contexto: "Empresa | None" = None
):
    cliente = _cliente_por_telefone(telefone, db, empresa_contexto.id if empresa_contexto else None)
    if not cliente:
        await enviar_mensagem_texto(
            telefone,
            "Nao encontrei seu cadastro. Entre em contato com a empresa para enviar o orcamento pelo sistema.",
            empresa=empresa_contexto,
        )
        return {"status": "cliente_nao_encontrado"}

    orcamento = (
        db.query(Orcamento)
        .filter(
            Orcamento.cliente_id == cliente.id,
            Orcamento.status == StatusOrcamento.ENVIADO,
        )
        .order_by(Orcamento.criado_em.desc())
        .first()
    )

    if not orcamento:
        await enviar_mensagem_texto(
            telefone,
            "Nao encontrei um orcamento enviado recente para aprovar. Se ja recebeu o PDF, aguarde o contato da empresa.",
            empresa=empresa_contexto,
        )
        return {"status": "nenhum_orcamento_enviado"}

    empresa = empresa_contexto or orcamento.empresa
    empresa_nome = empresa.nome or "a empresa"
    valor_fmt = _brl_fmt(float(orcamento.total or 0))

    await enviar_mensagem_texto(
        telefone,
        f"Confirmando aceite do orcamento *{orcamento.numero}* no valor de {valor_fmt} para *{empresa_nome}*.\n\n"
        f"Correto? Responda *SIM* para confirmar.",
        empresa=empresa,
    )

    orcamento.aceite_pendente_em = datetime.now(timezone.utc)
    db.commit()
    return {"status": "confirmacao_enviada", "orcamento_id": orcamento.id}


async def _processar_recusa(
    telefone: str, db: Session, empresa_contexto: "Empresa | None" = None
):
    cliente = _cliente_por_telefone(telefone, db, empresa_contexto.id if empresa_contexto else None)
    if not cliente:
        await enviar_mensagem_texto(telefone, "Nao encontrei seu cadastro.", empresa=empresa_contexto)
        return {"status": "cliente_nao_encontrado"}

    orcamento = (
        db.query(Orcamento)
        .filter(
            Orcamento.cliente_id == cliente.id,
            Orcamento.status == StatusOrcamento.ENVIADO,
        )
        .order_by(Orcamento.criado_em.desc())
        .with_for_update()
        .first()
    )

    if not orcamento:
        await enviar_mensagem_texto(telefone, "Nao encontrei um orcamento enviado recente.", empresa=empresa_contexto)
        return {"status": "nenhum_orcamento_enviado"}

    orcamento.status = StatusOrcamento.RECUSADO
    db.add(
        HistoricoEdicao(
            orcamento_id=orcamento.id,
            editado_por_id=None,
            descricao="Recusado pelo cliente via WhatsApp.",
        )
    )
    db.commit()
    db.refresh(orcamento)

    empresa = empresa_contexto or orcamento.empresa
    db.add(
        Notificacao(
            empresa_id=orcamento.empresa_id,
            orcamento_id=orcamento.id,
            tipo="recusado",
            titulo="Orcamento recusado",
            mensagem=f"Cliente {orcamento.cliente.nome} recusou o orcamento {orcamento.numero}.",
        )
    )
    db.commit()

    await enviar_mensagem_texto(
        telefone,
        f"Orcamento *{orcamento.numero}* registrado como recusado. Qualquer duvida, entre em contato com a empresa.",
        empresa=empresa,
    )
    return {"status": "rejected", "orcamento_id": orcamento.id}


async def _processar_codigo_empresa(
    telefone: str, empresa_id: int, mensagem_original: str, db: Session
):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        await enviar_mensagem_texto(
            telefone,
            f"Empresa EMP-{empresa_id} nao encontrada. Verifique o codigo com a empresa.",
        )
        return {"status": "empresa_nao_encontrada"}

    await enviar_mensagem_texto(
        telefone,
        f"Empresa *{empresa.nome}* identificada!\n\n"
        f"Agora me diga o que voce precisa:\n"
        f"_Orcamento de [servico] no valor de [R$] para [nome do cliente]_",
    )
    return {"status": "empresa_identificada", "empresa_id": empresa_id}


# ══════════════════════════════════════════════════════════════════════════════
# OPERACOES DE ORÇAMENTO VIA WHATSAPP
# ══════════════════════════════════════════════════════════════════════════════


def _brl_fmt(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _calcular_total(subtotal: float, desconto: float | None, tipo: str | None) -> float:
    d = desconto or 0.0
    t = tipo or "percentual"
    if d <= 0:
        return subtotal
    if t == "percentual":
        return max(0.0, subtotal - subtotal * (d / 100))
    return max(0.0, subtotal - d)


def _listar_itens_txt(orc: Orcamento) -> str:
    linhas = []
    for i, item in enumerate(orc.itens, 1):
        qtd = int(item.quantidade) if item.quantidade == int(item.quantidade) else item.quantidade
        linhas.append(
            f"{i}. {item.descricao} -- {_brl_fmt(item.total)}"
            + (f" (x{qtd})" if qtd != 1 else "")
        )
    return "\n".join(linhas)


def _buscar_orcamento(
    orc_id: int, db: Session, empresa_id: int | None = None
) -> "Orcamento | None":
    q = db.query(Orcamento)
    if empresa_id:
        q = q.filter(Orcamento.empresa_id == empresa_id)
    orc = q.filter(Orcamento.numero.like(f"ORC-{orc_id}-%")).first()
    if not orc:
        orc = q.filter(Orcamento.id == orc_id).first()
    return orc


def _regenerar_pdf(orc: Orcamento, db: Session):
    empresa = orc.empresa
    subtotal = sum(i.total for i in orc.itens)
    orc_dict = {
        "numero": orc.numero,
        "total": orc.total,
        "subtotal": subtotal,
        "desconto": orc.desconto or 0.0,
        "desconto_tipo": orc.desconto_tipo or "percentual",
        "validade_dias": orc.validade_dias or 7,
        "observacoes": orc.observacoes,
        "forma_pagamento": str(orc.forma_pagamento),
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
    }
    empresa_dict = {
        "nome": empresa.nome,
        "telefone": empresa.telefone,
        "cor_primaria": empresa.cor_primaria,
        "logo_url": empresa.logo_url,
    }
    pdf_bytes = gerar_pdf_orcamento(orc_dict, empresa_dict)
    orc.pdf_url = f"/o/{orc.link_publico}/pdf"
    db.commit()


async def _enviar_ajuda(telefone: str, empresa: "Empresa | None" = None):
    await enviar_mensagem_texto(
        telefone,
        "*Comandos COTTE*\n\n"
        "*VER {id}* -- ver itens do orcamento\n"
        "*ADICIONAR {id} {descricao} {valor}* -- adicionar item\n"
        "*REMOVER {id} {n item}* -- remover item\n"
        "*DESCONTO {id} {valor}%* -- desconto percentual\n"
        "*DESCONTO {id} {valor} REAIS* -- desconto fixo\n"
        "*ENVIAR {id}* -- enviar PDF ao cliente\n\n"
        "Ou descreva um novo orcamento normalmente:\n"
        '_Ex: Pintura 800 reais 10% desconto para Joao_',
        empresa=empresa,
    )


async def _aprovar_orcamento_via_bot(
    orc_id: int, telefone: str, db: Session, empresa_op: "Empresa | None" = None
):
    orc = _buscar_orcamento(orc_id, db, empresa_id=empresa_op.id if empresa_op else None)
    if not orc:
        await enviar_mensagem_texto(telefone, f"Orcamento #{orc_id} nao encontrado.", empresa=empresa_op)
        return
    empresa_check = empresa_op or _empresa_por_operador(telefone, db)
    if not empresa_check or empresa_check.id != orc.empresa_id:
        await enviar_mensagem_texto(telefone, "Sem permissao para aprovar este orcamento.", empresa=empresa_op)
        return
    _STATUS_APROVAVEL = {StatusOrcamento.ENVIADO, StatusOrcamento.PENDENTE}
    if orc.status not in _STATUS_APROVAVEL:
        await enviar_mensagem_texto(
            telefone,
            f"Orcamento {orc.numero} nao pode ser aprovado (status atual: {orc.status.value}).",
            empresa=empresa_op,
        )
        return
    old_status = orc.status
    orc.status = StatusOrcamento.APROVADO
    renomear_numero_aprovado(orc, empresa_op)
    db.add(HistoricoEdicao(orcamento_id=orc.id, editado_por_id=None, descricao="Aprovado pelo operador via WhatsApp."))
    financeiro_service.criar_contas_receber_aprovacao(orc, orc.empresa_id, db)
    try:
        from app.services.agendamento_auto_service import (
            processar_agendamento_apos_aprovacao,
        )

        processar_agendamento_apos_aprovacao(db, orc, canal="whatsapp")
    except Exception:
        logger.exception(
            "Falha ao processar agendamento pós-aprovação (WhatsApp operador, orcamento_id=%s)",
            orc.id,
        )
    db.commit()
    db.refresh(orc)
    await handle_quote_status_changed(db=db, quote=orc, old_status=old_status, new_status=orc.status, source="bot_whatsapp")
    await enviar_mensagem_texto(
        telefone,
        f"Orcamento *{orc.numero}* aprovado!\n"
        f"Cliente: {orc.cliente.nome}\n"
        f"Valor: {_brl_fmt(orc.total)}",
        empresa=empresa_op,
    )


async def _recusar_orcamento_via_bot(
    orc_id: int, telefone: str, db: Session, empresa_op: "Empresa | None" = None
):
    orc = _buscar_orcamento(orc_id, db, empresa_id=empresa_op.id if empresa_op else None)
    if not orc:
        await enviar_mensagem_texto(telefone, f"Orcamento #{orc_id} nao encontrado.", empresa=empresa_op)
        return
    empresa_check = empresa_op or _empresa_por_operador(telefone, db)
    if not empresa_check or empresa_check.id != orc.empresa_id:
        await enviar_mensagem_texto(telefone, "Sem permissao para recusar este orcamento.", empresa=empresa_op)
        return
    _STATUS_RECUSAVEL = {StatusOrcamento.ENVIADO, StatusOrcamento.PENDENTE, StatusOrcamento.APROVADO}
    if orc.status not in _STATUS_RECUSAVEL:
        await enviar_mensagem_texto(
            telefone,
            f"Orcamento {orc.numero} nao pode ser recusado (status atual: {orc.status.value}).",
            empresa=empresa_op,
        )
        return
    orc.status = StatusOrcamento.RECUSADO
    db.add(HistoricoEdicao(orcamento_id=orc.id, editado_por_id=None, descricao="Recusado pelo operador via WhatsApp."))
    db.commit()
    await enviar_mensagem_texto(telefone, f"Orcamento *{orc.numero}* recusado.", empresa=empresa_op)


async def _ver_orcamento(
    orc_id: int, telefone: str, db: Session, empresa: "Empresa | None" = None
):
    orc = _buscar_orcamento(orc_id, db, empresa_id=empresa.id if empresa else None)
    if not orc:
        await enviar_mensagem_texto(telefone, f"Orcamento #{orc_id} nao encontrado.", empresa=empresa)
        return

    itens_txt = _listar_itens_txt(orc)
    desc_txt = ""
    if orc.desconto and orc.desconto > 0:
        desc_label = f"{orc.desconto:.0f}%" if orc.desconto_tipo == "percentual" else _brl_fmt(orc.desconto)
        desc_txt = f"Desconto: {desc_label}\n"

    await enviar_mensagem_texto(
        telefone,
        f"*{orc.numero}* -- {orc.cliente.nome}\n\n"
        f"{itens_txt}\n\n"
        f"{desc_txt}"
        f"Total: {_brl_fmt(orc.total)}\n"
        f"Status: {orc.status}\n\n"
        f"*ADICIONAR {orc_id} [descricao] [valor]*\n"
        f"*REMOVER {orc_id} [n item]*\n"
        f"*DESCONTO {orc_id} [valor]%* ou *[valor] REAIS*\n"
        f"*ENVIAR {orc_id}* -- enviar ao cliente",
        empresa=empresa,
    )


async def _editar_desconto_orcamento(
    orc_id: int, valor_str: str, sufixo_raw: str | None, telefone: str, db: Session, empresa_op: "Empresa | None" = None,
):
    orc = _buscar_orcamento(orc_id, db, empresa_id=empresa_op.id if empresa_op else None)
    if not orc:
        await enviar_mensagem_texto(telefone, f"Orcamento #{orc_id} nao encontrado.", empresa=empresa_op)
        return

    empresa_check = empresa_op or _empresa_por_operador(telefone, db)
    if not empresa_check or empresa_check.id != orc.empresa_id:
        await enviar_mensagem_texto(telefone, "Sem permissao para editar este orcamento.", empresa=empresa_op)
        return

    valor = float(valor_str.replace(",", "."))
    sufixo = (sufixo_raw or "").strip()
    tipo = "fixo" if sufixo in ["REAIS", "REAL"] else "percentual"
    subtotal = sum(i.total for i in orc.itens)

    if valor > 0:
        novo_total = max(0.0, subtotal - (subtotal * valor / 100 if tipo == "percentual" else valor))
    else:
        novo_total = subtotal

    orc.desconto = valor
    orc.desconto_tipo = tipo
    orc.total = novo_total
    db.commit()
    _regenerar_pdf(orc, db)

    desc_label = f"{valor:.0f}%" if tipo == "percentual" else _brl_fmt(valor)
    if valor == 0:
        msg = f"Desconto removido do *{orc.numero}*! Total: {_brl_fmt(novo_total)}"
    else:
        msg = (
            f"Desconto aplicado em *{orc.numero}*!\n\n"
            f"Desconto: {desc_label}\n"
            f"Novo total: {_brl_fmt(novo_total)}\n\n"
            f"*ENVIAR {orc_id}* -- enviar ao cliente"
        )
    await enviar_mensagem_texto(telefone, msg, empresa=empresa_op)


async def _adicionar_item_orcamento(
    orc_id: int, descricao: str, valor: float, telefone: str, db: Session, empresa_op: "Empresa | None" = None,
):
    orc = _buscar_orcamento(orc_id, db, empresa_id=empresa_op.id if empresa_op else None)
    if not orc:
        await enviar_mensagem_texto(telefone, f"Orcamento #{orc_id} nao encontrado.", empresa=empresa_op)
        return

    empresa_check = empresa_op or _empresa_por_operador(telefone, db)
    if not empresa_check or empresa_check.id != orc.empresa_id:
        await enviar_mensagem_texto(telefone, "Sem permissao para editar este orcamento.", empresa=empresa_op)
        return

    db.add(ItemOrcamento(orcamento_id=orc.id, descricao=descricao, quantidade=1, valor_unit=valor, total=valor))
    db.flush()
    db.refresh(orc)

    subtotal = sum(i.total for i in orc.itens)
    orc.total = _calcular_total(subtotal, orc.desconto, orc.desconto_tipo)
    db.commit()
    db.refresh(orc)
    _regenerar_pdf(orc, db)

    await enviar_mensagem_texto(
        telefone,
        f"Item adicionado em *{orc.numero}*!\n\n"
        f"{_listar_itens_txt(orc)}\n\n"
        f"Novo total: {_brl_fmt(orc.total)}\n\n"
        f"*ENVIAR {orc_id}* -- enviar ao cliente",
        empresa=empresa_op,
    )


async def _remover_item_orcamento(
    orc_id: int, num_item: int, telefone: str, db: Session, empresa_op: "Empresa | None" = None,
):
    orc = _buscar_orcamento(orc_id, db, empresa_id=empresa_op.id if empresa_op else None)
    if not orc:
        await enviar_mensagem_texto(telefone, f"Orcamento #{orc_id} nao encontrado.", empresa=empresa_op)
        return

    empresa_check = empresa_op or _empresa_por_operador(telefone, db)
    if not empresa_check or empresa_check.id != orc.empresa_id:
        await enviar_mensagem_texto(telefone, "Sem permissao para editar este orcamento.", empresa=empresa_op)
        return

    itens = list(orc.itens)
    if num_item < 1 or num_item > len(itens):
        await enviar_mensagem_texto(
            telefone,
            f"Item {num_item} invalido. O orcamento tem {len(itens)} item(ns).\n"
            f"Use *VER {orc_id}* para ver a lista.",
            empresa=empresa_op,
        )
        return

    if len(itens) == 1:
        await enviar_mensagem_texto(
            telefone,
            "Nao e possivel remover o unico item.\n"
            f"Use *ADICIONAR {orc_id}* para adicionar outro item antes.",
            empresa=empresa_op,
        )
        return

    desc_removido = itens[num_item - 1].descricao
    db.delete(itens[num_item - 1])
    db.flush()
    db.refresh(orc)

    subtotal = sum(i.total for i in orc.itens)
    orc.total = _calcular_total(subtotal, orc.desconto, orc.desconto_tipo)
    db.commit()
    db.refresh(orc)
    _regenerar_pdf(orc, db)

    await enviar_mensagem_texto(
        telefone,
        f"Item removido de *{orc.numero}*!\n"
        f'"{desc_removido}" removido\n\n'
        f"{_listar_itens_txt(orc)}\n\n"
        f"Novo total: {_brl_fmt(orc.total)}\n\n"
        f"*ENVIAR {orc_id}* -- enviar ao cliente",
        empresa=empresa_op,
    )


async def _enviar_orcamento_para_cliente(
    orcamento_id: int, solicitante: str, db: Session, empresa_op: "Empresa | None" = None,
):
    if not empresa_op:
        await enviar_mensagem_texto(solicitante, "Sem permissao para enviar este orcamento.")
        return {"status": "forbidden"}

    orcamento = db.query(Orcamento).filter(Orcamento.id == orcamento_id).first()
    if not orcamento:
        await enviar_mensagem_texto(solicitante, f"Orcamento #{orcamento_id} nao encontrado.", empresa=empresa_op)
        return {"status": "not_found"}

    if orcamento.empresa_id != empresa_op.id:
        await enviar_mensagem_texto(solicitante, "Sem permissao para enviar este orcamento.", empresa=empresa_op)
        return {"status": "forbidden"}

    if not orcamento.cliente or not orcamento.cliente.telefone:
        await enviar_mensagem_texto(solicitante, "Cliente sem telefone cadastrado.", empresa=empresa_op)
        return {"status": "sem_telefone"}

    empresa = orcamento.empresa
    empresa_dict = {"nome": empresa.nome, "telefone": empresa.telefone, "cor_primaria": empresa.cor_primaria, "logo_url": empresa.logo_url}
    itens = [
        {"descricao": it.descricao, "quantidade": it.quantidade, "valor_unit": float(it.valor_unit), "total": float(it.total)}
        for it in orcamento.itens
    ]
    subtotal_env = sum(i["total"] for i in itens)
    orc_dict = {
        "numero": orcamento.numero, "total": float(orcamento.total), "subtotal": subtotal_env,
        "desconto": float(orcamento.desconto or 0.0), "desconto_tipo": orcamento.desconto_tipo or "percentual",
        "validade_dias": orcamento.validade_dias or 7, "observacoes": orcamento.observacoes,
        "forma_pagamento": str(orcamento.forma_pagamento),
        "cliente": {"nome": orcamento.cliente.nome, "telefone": orcamento.cliente.telefone},
        "cliente_nome": orcamento.cliente.nome, "empresa_nome": empresa.nome,
        "vendedor_nome": orcamento.criado_por.nome if orcamento.criado_por else None,
        "itens": itens,
    }
    pdf_bytes = gerar_pdf_orcamento(orc_dict, empresa_dict)

    enviado = await enviar_orcamento_completo(orcamento.cliente.telefone, orc_dict, pdf_bytes, empresa=empresa)
    if enviado:
        if orcamento.status == StatusOrcamento.RASCUNHO:
            orcamento.status = StatusOrcamento.ENVIADO
            db.add(HistoricoEdicao(orcamento_id=orcamento.id, editado_por_id=None, descricao="Enviado por WhatsApp (numero da empresa / Evolution)."))
        else:
            db.add(HistoricoEdicao(orcamento_id=orcamento.id, editado_por_id=None, descricao="Reenviado por WhatsApp."))
        db.commit()
        await enviar_mensagem_texto(solicitante, f"Orcamento *{orcamento.numero}* enviado para {orcamento.cliente.nome}!", empresa=empresa_op)
    else:
        await enviar_mensagem_texto(solicitante, "Falha ao enviar o orcamento. Tente pelo painel.", empresa=empresa_op)

    return {"status": "sent" if enviado else "error"}


# ══════════════════════════════════════════════════════════════════════════════
# CRIACAO DE ORCAMENTO VIA BOT
# ══════════════════════════════════════════════════════════════════════════════


async def _criar_orcamento_via_bot(
    telefone: str, mensagem: str, db: Session, empresa: "Empresa | None" = None
):
    if empresa is None:
        empresa = _empresa_por_telefone_cliente(telefone, db)

    if empresa is None:
        await enviar_mensagem_texto(
            telefone,
            "Ola! Para criar um orcamento, informe o codigo da empresa.\n\n"
            "Exemplo: *EMP-1*\n\n"
            "Se nao souber o codigo, entre em contato diretamente com a empresa.",
        )
        return {"status": "empresa_nao_identificada"}

    if not ia_automatica_habilitada(empresa):
        await enviar_mensagem_texto(
            telefone,
            "Esta empresa esta em um plano que nao inclui criacao automatica de orcamentos por IA.",
        )
        return {"status": "ia_desabilitada"}

    interpretado = await interpretar_mensagem(mensagem)

    servico_match = _encontrar_servico_catalogo(empresa, interpretado.servico, db)

    if interpretado.confianca < 0.5 and not servico_match:
        await enviar_mensagem_texto(
            telefone,
            "Nao entendi bem. Tente assim:\n\n"
            "_Orcamento de [servico] no valor de [R$] para [nome do cliente]_",
        )
        return {"status": "low_confidence"}

    cliente_nome = interpretado.cliente_nome
    cliente = (
        db.query(Cliente)
        .filter(Cliente.empresa_id == empresa.id, Cliente.nome.ilike(f"%{cliente_nome}%"))
        .first()
    )

    _cliente_novo_dados = None
    if not cliente:
        telefone_normalizado = normalize_phone_number(telefone)
        _cliente_novo_dados = dict(
            empresa_id=empresa.id,
            nome=cliente_nome,
            telefone=telefone_normalizado or telefone,
        )
        cliente = Cliente(**_cliente_novo_dados)
        db.add(cliente)
        db.flush()
    elif not cliente.telefone:
        cliente.telefone = normalize_phone_number(telefone) or telefone

    ia_valor = float(interpretado.valor or 0.0)
    subtotal = ia_valor
    if servico_match:
        preco_catalogo = float(servico_match.preco_padrao or 0.0)
        if preco_catalogo > 0:
            subtotal = preco_catalogo
            if ia_valor > 0:
                subtotal = ia_valor

    usuario_criador = _resolver_usuario_criador_orcamento(empresa, telefone, db)
    if not usuario_criador:
        await enviar_mensagem_texto(
            telefone,
            "Nao foi possivel identificar um usuario ativo da empresa para registrar este orcamento.",
            empresa=empresa,
        )
        return {"status": "usuario_criador_nao_encontrado"}

    desconto = interpretado.desconto or 0.0
    desconto_tipo = interpretado.desconto_tipo or "percentual"
    if desconto > 0:
        max_pct = resolver_max_percent_desconto(usuario_criador, empresa)
        err_desconto = erro_validacao_desconto(subtotal, desconto, desconto_tipo, max_pct)
        if err_desconto:
            await enviar_mensagem_texto(telefone, err_desconto, empresa=empresa)
            return {"status": "desconto_invalido", "erro": err_desconto}
    total_calc = float(aplicar_desconto(_Decimal(str(subtotal)), _Decimal(str(desconto)), desconto_tipo))

    checar_limite_orcamentos(db, empresa)

    orcamento = None
    for tentativa in range(3):
        if tentativa > 0:
            db.rollback()
            if _cliente_novo_dados:
                cliente = Cliente(**_cliente_novo_dados)
                db.add(cliente)
                db.flush()

        _numero, _seq = gerar_numero(empresa, db, offset=tentativa)
        orcamento = Orcamento(
            empresa_id=empresa.id,
            cliente_id=cliente.id,
            criado_por_id=usuario_criador.id,
            numero=_numero,
            sequencial_numero=_seq,
            total=total_calc,
            desconto=desconto,
            desconto_tipo=desconto_tipo,
            observacoes=interpretado.observacoes,
            link_publico=secrets.token_urlsafe(12),
            origem_whatsapp=True,
            mensagem_ia=mensagem,
        )
        db.add(orcamento)
        try:
            db.flush()
            break
        except Exception as e:
            orig = str(getattr(e, "orig", e))
            if any(k in orig for k in ("orcamentos_numero", "uq_orcamentos", "ix_orcamentos")):
                logger.warning("Colisao de numero de orcamento via WhatsApp (tentativa %d)", tentativa + 1)
                continue
            raise
    else:
        await enviar_mensagem_texto(
            telefone,
            "Nao foi possivel gerar o orcamento agora. Tente novamente.",
            empresa=empresa,
        )
        return {"status": "numero_indisponivel"}

    numero = orcamento.numero
    descricao_item = servico_match.nome if servico_match else interpretado.servico

    item = ItemOrcamento(
        orcamento_id=orcamento.id,
        servico_id=servico_match.id if servico_match else None,
        descricao=descricao_item,
        quantidade=1,
        valor_unit=subtotal,
        total=subtotal,
    )
    db.add(item)

    forma_padrao = (
        db.query(FormaPagamentoConfig)
        .filter_by(empresa_id=empresa.id, padrao=True, ativo=True)
        .first()
    )
    if forma_padrao:
        orcamento.regra_pagamento_id = forma_padrao.id
        financeiro_service.aplicar_regra_no_orcamento(orcamento, db)

    db.commit()
    db.refresh(orcamento)

    empresa_dict = {"nome": empresa.nome, "telefone": empresa.telefone, "cor_primaria": empresa.cor_primaria}
    orc_dict = {
        "numero": numero, "total": total_calc, "subtotal": subtotal,
        "desconto": desconto, "desconto_tipo": desconto_tipo, "validade_dias": 7,
        "observacoes": interpretado.observacoes, "forma_pagamento": "pix",
        "cliente": {"nome": cliente_nome, "telefone": None},
        "itens": [{"descricao": interpretado.servico, "quantidade": 1, "valor_unit": subtotal, "total": subtotal}],
    }
    pdf_bytes = gerar_pdf_orcamento(orc_dict, empresa_dict)
    orcamento.pdf_url = f"/o/{orcamento.link_publico}/pdf"
    db.commit()

    total_fmt = f"R$ {total_calc:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    desc_txt = ""
    if desconto > 0:
        if desconto_tipo == "percentual":
            desc_txt = f"\nDesconto: {desconto:.0f}%"
        else:
            desc_fmt = f"R$ {desconto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            desc_txt = f"\nDesconto: {desc_fmt}"

    _seq = re.search(r"ORC-(\d+)-", numero) or re.search(r"(\d+)", numero)
    num_enviar = _seq.group(1) if _seq else str(orcamento.id)
    confirmacao = (
        f"*Orcamento {numero} criado!*\n\n"
        f"Cliente: {cliente_nome}\n"
        f"Servico: {interpretado.servico}"
        f"{desc_txt}\n"
        f"Total: {total_fmt}\n\n"
        f"Deseja enviar para o cliente agora?\nResponda *ENVIAR {num_enviar}*"
    )
    await enviar_mensagem_texto(telefone, confirmacao, empresa=empresa)
    return {"status": "created", "orcamento_id": orcamento.id}


# ══════════════════════════════════════════════════════════════════════════════
# AGENDAMENTOS — Comandos via WhatsApp
# ══════════════════════════════════════════════════════════════════════════════


def _fmt_data_br(dt) -> str:
    if not dt:
        return "--"
    from datetime import timezone as tz, timedelta as td

    brt = tz(td(hours=-3))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz.utc)
    local = dt.astimezone(brt)
    return local.strftime("%d/%m/%Y as %H:%M")


def _is_agendamento_cmd(msg_upper: str) -> str | None:
    msg = msg_upper.strip().upper().rstrip(".,!?;:")
    if msg.startswith("AGENDAR"):
        return "AGENDAR"
    if msg in ("AGENDAMENTOS HOJE", "AGENDA HOJE", "HOJE AGENDAMENTOS"):
        return "AGENDAMENTOS_HOJE"
    if msg in ("MEUS AGENDAMENTOS", "MINHA AGENDA", "AGENDAMENTOS"):
        return "MEUS_AGENDAMENTOS"
    return None


async def _processar_comando_agendamento(
    telefone: str, mensagem: str, db: Session, empresa: "Empresa",
):
    from app.services.agendamento_service import criar_agendamento, criar_do_orcamento

    msg_lower = mensagem.lower()
    orc_match = re.search(r"agendar\s+(\d+)", mensagem.upper())

    usuario = (
        db.query(Usuario)
        .filter(Usuario.empresa_id == empresa.id, Usuario.ativo == True)
        .first()
    )
    if not usuario:
        await enviar_mensagem_texto(telefone, "Usuario nao encontrado.", empresa=empresa)
        return

    if orc_match:
        orc_id = int(orc_match.group(1))
        from datetime import datetime as dt, timedelta

        agora = dt.now(timezone.utc)
        data_agendada = agora + timedelta(days=1)
        if "amanhã" in msg_lower or "amanha" in msg_lower:
            data_agendada = agora + timedelta(days=1)
        elif "hoje" in msg_lower:
            data_agendada = agora + timedelta(hours=2)

        hora_match = re.search(r"(\d{1,2})[:h](\d{2})?", msg_lower)
        if hora_match:
            h = int(hora_match.group(1))
            m = int(hora_match.group(2) or 0)
            data_agendada = data_agendada.replace(hour=h, minute=m, second=0, microsecond=0)

        ag, erro = criar_do_orcamento(
            db=db, empresa_id=empresa.id, usuario_id=usuario.id,
            orcamento_id=orc_id, data_agendada=data_agendada,
        )
        if erro:
            await enviar_mensagem_texto(telefone, f"{erro}", empresa=empresa)
        else:
            cliente_nome = ag.cliente.nome if ag.cliente else "--"
            await enviar_mensagem_texto(
                telefone,
                f"Agendamento criado!\n\n"
                f"{ag.numero}\n"
                f"Cliente: {cliente_nome}\n"
                f"{_fmt_data_br(ag.data_agendada)}\n"
                f"Status: {ag.status.value}",
                empresa=empresa,
            )
    else:
        await enviar_mensagem_texto(
            telefone,
            "*Agendamento via WhatsApp*\n\n"
            "Formatos aceitos:\n"
            "agendar 5 amanha 14h -- cria a partir do orcamento #5\n"
            "agendar 3 hoje 16h -- cria a partir do orcamento #3\n\n"
            "Outros comandos:\n"
            "agendamentos hoje -- ver agendamentos de hoje\n"
            "meus agendamentos -- seus proximos agendamentos",
            empresa=empresa,
        )


async def _listar_agendamentos_hoje(telefone: str, db: Session, empresa: "Empresa"):
    from app.services.agendamento_service import listar_hoje

    agendamentos = listar_hoje(db, empresa.id)
    if not agendamentos:
        await enviar_mensagem_texto(telefone, "Nenhum agendamento para hoje.", empresa=empresa)
        return

    linhas = [f"*Agendamentos de Hoje* ({len(agendamentos)})\n"]
    for ag in agendamentos:
        status_icon = {
            "pendente": "[P]", "confirmado": "[C]", "em_andamento": "[E]", "concluido": "[OK]",
        }.get(ag.get("status", ""), "*")
        cliente = ag.get("cliente_nome", "--")
        hora = _fmt_data_br(ag.get("data_agendada"))
        resp = ag.get("responsavel_nome", "--")
        linhas.append(f"{status_icon} {ag.get('numero', '?')} -- {cliente}\n   {hora} | {resp}")

    await enviar_mensagem_texto(telefone, "\n".join(linhas), empresa=empresa)


async def _listar_meus_agendamentos(telefone: str, db: Session, empresa: "Empresa"):
    from app.services.agendamento_service import listar_agendamentos
    from datetime import datetime as dt

    usuario = (
        db.query(Usuario)
        .filter(Usuario.empresa_id == empresa.id, Usuario.ativo == True)
        .first()
    )
    if not usuario:
        await enviar_mensagem_texto(telefone, "Usuario nao encontrado.", empresa=empresa)
        return

    itens, total = listar_agendamentos(
        db=db, empresa_id=empresa.id, responsavel_id=usuario.id, data_de=dt.now(timezone.utc),
    )

    if not itens:
        await enviar_mensagem_texto(telefone, "Voce nao tem agendamentos futuros.", empresa=empresa)
        return

    linhas = [f"*Seus Proximos Agendamentos* ({total})\n"]
    for ag in itens[:10]:
        cliente = ag.get("cliente_nome", "--")
        hora = _fmt_data_br(ag.get("data_agendada"))
        status = ag.get("status", "")
        linhas.append(f"{ag.get('numero', '?')} -- {cliente}\n   {hora} | {status}")

    await enviar_mensagem_texto(telefone, "\n".join(linhas), empresa=empresa)
