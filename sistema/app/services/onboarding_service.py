"""
Serviço de Onboarding — COTTE (v2)

Calcula progresso orientado a ativação e vendas.
Guia o usuário até o primeiro orçamento enviado.
Funciona com Session síncrona (mesmo padrão do assistente).
"""

from __future__ import annotations

import logging
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)


# ── Etapas obrigatórias (5 × peso 20 = 100%) ────────────────────────────────

_ETAPAS = [
    {
        "chave": "empresa_configurada",
        "titulo": "Configurar empresa",
        "peso": 20,
        "mensagem": (
            "🏢 Primeiro, vamos deixar sua empresa com aparência profissional.\n\n"
            "Preencha seus dados básicos. Isso aparece na proposta do cliente.\n\n"
            "Quer fazer isso agora?"
        ),
        "acao_label": "Abrir configurações da empresa",
        "acao_destino": "configuracoes.html",
    },
    {
        "chave": "servico_cadastrado",
        "titulo": "Cadastrar pelo menos 1 serviço",
        "peso": 20,
        "mensagem": (
            "🧰 Agora vamos agilizar seus orçamentos.\n\n"
            "Cadastre seus principais serviços — assim você cria orçamentos em segundos.\n\n"
            "💡 Dica: você pode importar uma lista de serviços de uma vez!\n\n"
            "Vamos cadastrar agora?"
        ),
        "acao_label": "Abrir catálogo de serviços",
        "acao_destino": "catalogo.html",
    },
    {
        "chave": "cliente_cadastrado",
        "titulo": "Cadastrar pelo menos 1 cliente",
        "peso": 20,
        "mensagem": (
            "👤 Agora cadastre seu primeiro cliente.\n\n"
            "Você vai precisar dele para criar orçamentos.\n\n"
            "Quer fazer isso agora?"
        ),
        "acao_label": "Abrir clientes",
        "acao_destino": "clientes.html",
    },
    {
        "chave": "orcamento_criado",
        "titulo": "Criar primeiro orçamento",
        "peso": 20,
        "mensagem": (
            "📄 Agora vamos criar seu primeiro orçamento.\n\n"
            "Quer criar agora?"
        ),
        "acao_label": "Abrir orçamentos",
        "acao_destino": "orcamentos.html",
    },
    {
        "chave": "orcamento_enviado",
        "titulo": "Enviar orçamento ao cliente",
        "peso": 20,
        "mensagem": (
            "📤 Seu orçamento está pronto!\n\n"
            "Agora envie para o cliente.\n\n"
            "Quer enviar agora?"
        ),
        "acao_label": "Ver orçamentos",
        "acao_destino": "orcamentos.html",
    },
]

# ── Etapas opcionais (aparecem como sugestões no assistente) ─────────────────

_ETAPAS_OPCIONAIS = [
    {
        "chave": "forma_pagamento_configurada",
        "sugestao": "💳 Cadastre seu PIX para receber com 1 clique",
        "acao_destino": "configuracoes.html#formas-pagamento",
    },
    {
        "chave": "whatsapp_conectado",
        "sugestao": "📱 Conecte WhatsApp para enviar orçamentos direto do sistema",
        "acao_destino": "configuracoes.html#integracoes",
    },
]

_MENSAGEM_BOAS_VINDAS = (
    "👋 Bem-vindo ao COTTE!\n\n"
    "Vou te ajudar a deixar tudo pronto para você começar a enviar orçamentos ainda hoje.\n\n"
    "Leva menos de 10 minutos.\n\n"
    "Vamos começar?"
)

_MENSAGEM_CONCLUIDO = "🎉 Perfeito! Você já está usando o COTTE de verdade."


# ── Funções públicas ────────────────────────────────────────────────────────

def get_onboarding_status(db: Session, empresa_id: int) -> dict:
    """
    Calcula progresso de onboarding orientado a ativação.
    Retorna payload estruturado. Nunca lança exceção.
    """
    try:
        return _calcular_status(db, empresa_id)
    except Exception as e:
        logger.warning(f"[Onboarding] Erro empresa {empresa_id}: {e}")
        return _payload_vazio()


def formatar_resposta_onboarding(status: dict) -> str:
    """
    Formata resposta para o chat mostrando apenas etapas obrigatórias pendentes.

    Se progresso == 0  → boas-vindas
    Se concluido       → mensagem final + sugestões opcionais pendentes
    Senão              → lista de pendentes + CTA
    """
    progresso = status.get("progresso_pct", 0)
    checklist = status.get("checklist", [])
    mensagem  = status.get("mensagem", "")
    concluido = status.get("concluido", False)
    sugestoes = status.get("sugestoes", [])

    if progresso == 0:
        return mensagem

    if concluido:
        if sugestoes:
            dicas = "\n".join(f"• {s}" for s in sugestoes)
            return (
                f"{mensagem}\n\n"
                f"💡 Dicas para turbinar ainda mais:\n\n"
                f"{dicas}"
            )
        return mensagem

    pendentes = [item for item in checklist if not item["concluida"]]
    if not pendentes:
        return mensagem

    linhas = "\n".join(f"• ⬜ {item['titulo']}" for item in pendentes)

    return (
        f"👋 Vamos continuar seu setup.\n\n"
        f"Falta só isso:\n\n"
        f"{linhas}\n\n"
        f"Vamos fazer agora?"
    )


# ── Implementação interna ───────────────────────────────────────────────────

def _calcular_status(db: Session, empresa_id: int) -> dict:
    from app.models.models import (
        Empresa, Servico, Cliente, Orcamento, StatusOrcamento, FormaPagamentoConfig,
    )

    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        logger.warning(f"[Onboarding] Empresa {empresa_id} não encontrada")
        return _payload_vazio()

    # ── Critérios obrigatórios ─────────────────────────────────────────────

    empresa_ok = bool(empresa.nome and empresa.nome.strip())

    total_servicos = (
        db.query(func.count(Servico.id))
        .filter(Servico.empresa_id == empresa_id, Servico.ativo == True)
        .scalar() or 0
    )

    total_clientes = (
        db.query(func.count(Cliente.id))
        .filter(Cliente.empresa_id == empresa_id)
        .scalar() or 0
    )

    total_orcamentos = (
        db.query(func.count(Orcamento.id))
        .filter(Orcamento.empresa_id == empresa_id)
        .scalar() or 0
    )

    total_enviados = (
        db.query(func.count(Orcamento.id))
        .filter(
            Orcamento.empresa_id == empresa_id,
            Orcamento.status != StatusOrcamento.RASCUNHO,
        )
        .scalar() or 0
    )

    concluidas = {
        "empresa_configurada": empresa_ok,
        "servico_cadastrado":  total_servicos >= 1,
        "cliente_cadastrado":  total_clientes >= 1,
        "orcamento_criado":    total_orcamentos >= 1,
        "orcamento_enviado":   total_enviados >= 1,
    }

    # ── Critérios opcionais ────────────────────────────────────────────────

    total_formas_pag = (
        db.query(func.count(FormaPagamentoConfig.id))
        .filter(
            FormaPagamentoConfig.empresa_id == empresa_id,
            FormaPagamentoConfig.ativo == True,
        )
        .scalar() or 0
    )

    concluidas_opcionais = {
        "forma_pagamento_configurada": total_formas_pag >= 1,
        "whatsapp_conectado":          bool(empresa.whatsapp_conectado),
    }

    # ── Checklist (apenas obrigatórias) ───────────────────────────────────

    checklist = [
        {
            "chave":        e["chave"],
            "titulo":       e["titulo"],
            "concluida":    concluidas[e["chave"]],
            "acao_label":   e["acao_label"]   if not concluidas[e["chave"]] else None,
            "acao_destino": e["acao_destino"] if not concluidas[e["chave"]] else None,
        }
        for e in _ETAPAS
    ]

    progresso = sum(e["peso"] for e in _ETAPAS if concluidas[e["chave"]])

    proxima   = next((e for e in _ETAPAS if not concluidas[e["chave"]]), None)
    concluido = proxima is None

    # ── Sugestões (opcionais não concluídas) ──────────────────────────────

    sugestoes = [
        e["sugestao"]
        for e in _ETAPAS_OPCIONAIS
        if not concluidas_opcionais.get(e["chave"], True)
    ]

    if concluido:
        mensagem       = _MENSAGEM_CONCLUIDO
        etapa_atual    = "concluido"
        acao_principal = None
    elif progresso == 0:
        mensagem       = _MENSAGEM_BOAS_VINDAS
        etapa_atual    = proxima["chave"]
        acao_principal = {"label": proxima["acao_label"], "destino": proxima["acao_destino"]}
    else:
        mensagem       = proxima["mensagem"]
        etapa_atual    = proxima["chave"]
        acao_principal = {"label": proxima["acao_label"], "destino": proxima["acao_destino"]}

    return {
        "checklist":      checklist,
        "progresso_pct":  progresso,
        "etapa_atual":    etapa_atual,
        "mensagem":       mensagem,
        "acao_principal": acao_principal,
        "concluido":      concluido,
        "sugestoes":      sugestoes,
    }


def _payload_vazio() -> dict:
    return {
        "checklist":      [],
        "progresso_pct":  0,
        "etapa_atual":    "empresa_configurada",
        "mensagem":       _MENSAGEM_BOAS_VINDAS,
        "acao_principal": {
            "label":   "Abrir configurações da empresa",
            "destino": "configuracoes.html",
        },
        "concluido": False,
        "sugestoes": [],
    }
