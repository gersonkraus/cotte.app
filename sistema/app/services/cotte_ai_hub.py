"""
COTTE AI Hub - Sistema centralizado de IA com validação robusta anti-delírios
Refatoração Senior 2025: Performance, Modularidade e Robustez

Melhorias implementadas:
1. Extração de JSON robusta com Regex (ai_json_extractor)
2. Queries agregadas SQLAlchemy func.sum (anti-bloqueio)
3. Prompts externalizados (ai_prompt_loader)
4. Classificador de intenção determinístico por regex (ai_intention_classifier)
"""

import json
import re
import hashlib
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Optional, Any, Literal

_TZ_BR = ZoneInfo("America/Sao_Paulo")
from functools import wraps
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, extract
from sqlalchemy.future import select
from pydantic import BaseModel, Field, model_validator, validator

from app.core.config import settings

# Importar novos módulos refatorados
from app.models.models import Usuario, CopilotoUserSkill, Orcamento, StatusOrcamento, ContaFinanceira # Importado globalmente para type hints
from app.services.ai_json_extractor import AIJSONExtractor
from app.services.ai_prompt_loader import get_prompt_loader
from app.services.ai_intention_classifier import (
    detectar_intencao_assistente,
    detectar_intencao_assistente_async,
)
from app.services.assistant_engine_registry import (
    DEFAULT_ENGINE,
    ENGINE_INTERNAL_COPILOT,
    build_engine_guardrails,
    get_engine_policy,
    is_code_rag_enabled,
    tools_payload_for_engine,
    resolve_engine,
)

logger = logging.getLogger(__name__)

PROMPT_DEFAULT_MODEL = "default"

# Inicializar loader de prompts (lazy loading)
_prompt_loader = get_prompt_loader()

# ── Schemas de Resposta ────────────────────────────────────────────────────


def _normalize_chart_data(chart_data: Any) -> Optional[dict]:
    if not isinstance(chart_data, dict):
        return None

    chart_type = chart_data.get("type") or chart_data.get("tipo")
    data = chart_data.get("data")

    if not isinstance(data, dict):
        dados = chart_data.get("dados")
        if isinstance(dados, dict):
            data = {
                "labels": list(dados.get("labels") or []),
                "datasets": list(dados.get("datasets") or []),
            }
        elif "labels" in chart_data or "datasets" in chart_data:
            data = {
                "labels": list(chart_data.get("labels") or []),
                "datasets": list(chart_data.get("datasets") or []),
            }

    normalized = dict(chart_data)
    if chart_type:
        normalized["type"] = chart_type
    if isinstance(data, dict):
        normalized["data"] = data

    return normalized


def _extract_chart_data_from_payload(payload: Any) -> Optional[dict]:
    if not isinstance(payload, dict):
        return None

    direct_chart = _normalize_chart_data(payload.get("chart_data"))
    if direct_chart:
        return direct_chart

    grafico = payload.get("grafico")
    grafico_chart = _normalize_chart_data(grafico)
    if grafico_chart:
        return grafico_chart

    semantic_contract = payload.get("semantic_contract")
    if isinstance(semantic_contract, dict):
        semantic_chart = semantic_contract.get("chart")
        normalized_semantic = _normalize_chart_data(semantic_chart)
        if normalized_semantic:
            return normalized_semantic

    return None


def _extract_table_data_from_payload(payload: Any) -> Optional[list]:
    if not isinstance(payload, dict):
        return None

    for key in ("table_data", "table", "rows"):
        value = payload.get(key)
        if isinstance(value, list):
            return list(value)

    semantic_contract = payload.get("semantic_contract")
    if isinstance(semantic_contract, dict) and isinstance(semantic_contract.get("table"), list):
        return list(semantic_contract.get("table") or [])

    return None


def _extract_actions_from_payload(payload: Any) -> Optional[list]:
    if not isinstance(payload, dict):
        return None

    for key in ("actions", "suggested_actions"):
        value = payload.get(key)
        if isinstance(value, list):
            return list(value)

    semantic_contract = payload.get("semantic_contract")
    if isinstance(semantic_contract, dict):
        for key in ("actions", "suggested_actions"):
            value = semantic_contract.get(key)
            if isinstance(value, list):
                return list(value)

    return None


def _extract_form_schema_from_payload(payload: Any) -> Optional[dict]:
    if not isinstance(payload, dict):
        return None

    for key in ("form_schema", "form"):
        value = payload.get(key)
        if isinstance(value, dict):
            return dict(value)

    semantic_contract = payload.get("semantic_contract")
    if isinstance(semantic_contract, dict):
        for key in ("form_schema", "form"):
            value = semantic_contract.get(key)
            if isinstance(value, dict):
                return dict(value)

    return None


def _extract_interactive_ai_payload(raw_text: str) -> Optional[dict]:
    parsed = AIJSONExtractor.extract(raw_text)
    if not isinstance(parsed, dict):
        return None

    supported_keys = {
        "resposta",
        "message",
        "tipo",
        "dados",
        "chart_data",
        "table_data",
        "actions",
        "form_schema",
    }
    if supported_keys.intersection(parsed.keys()):
        return parsed

    return None


def _build_user_skill_instruction(db: Session, current_user: Any) -> str:
    user_id = getattr(current_user, "id", None)
    if not user_id:
        return ""

    skill = (
        db.query(CopilotoUserSkill)
        .filter(CopilotoUserSkill.usuario_id == user_id)
        .first()
    )
    skill_text = (getattr(skill, "skill_text", "") or "").strip()
    if not skill_text:
        return ""

    return f"Instrução do usuário: {skill_text}"


class AIResponse(BaseModel):
    """Resposta padronizada do COTTE AI Hub"""

    sucesso: bool
    dados: Optional[dict] = None
    resposta: Optional[str] = None
    tipo_resposta: Optional[str] = None
    acao_sugerida: Optional[str] = None
    confianca: float = Field(ge=0.0, le=1.0)
    erros: list[str] = []
    fallback_utilizado: bool = False
    cache_hit: bool = False
    modulo_origem: str
    pending_action: Optional[dict] = None
    tool_trace: Optional[list[dict]] = None
    trace: Optional[list[dict]] = None  # Alias para tool_trace (compatibilidade debug)
    input_tokens: Optional[int] = 0
    output_tokens: Optional[int] = 0
    metrics: Optional[dict] = None
    chart_data: Optional[dict] = None
    table_data: Optional[list] = None
    actions: Optional[list] = None
    form_schema: Optional[dict] = None
    contexto_operacional: Optional[dict] = None

    @model_validator(mode="after")
    def _populate_interactive_fields(self):
        payload = self.dados or {}
        if self.chart_data is None:
            self.chart_data = _extract_chart_data_from_payload(payload)
        if self.table_data is None:
            self.table_data = _extract_table_data_from_payload(payload)
        if self.actions is None:
            self.actions = _extract_actions_from_payload(payload)
        if self.form_schema is None:
            self.form_schema = _extract_form_schema_from_payload(payload)
        
        # Sincronizar contexto operacional para o painel de debug
        if self.contexto_operacional is None:
            self.contexto_operacional = payload.get("contexto_operacional")

        # Sincronizar trace com tool_trace para o painel de debug
        if self.trace is None and self.tool_trace:
            self.trace = self.tool_trace
        elif self.tool_trace is None and self.trace:
            self.tool_trace = self.trace

        # Garantir que tokens estejam no nível superior se presentes em dados
        if self.input_tokens == 0 and "input_tokens" in payload:
            self.input_tokens = payload.get("input_tokens")
        if self.output_tokens == 0 and "output_tokens" in payload:
            self.output_tokens = payload.get("output_tokens")

        return self

    class Config:
        json_schema_extra = {
            "example": {
                "sucesso": True,
                "dados": {"cliente_nome": "João", "valor": 500.0},
                "confianca": 0.92,
                "modulo_origem": "orcamentos",
                "chart_data": None,
                "table_data": None,
                "actions": None,
                "form_schema": None,
            }
        }


def _extract_text_content_from_ia_response(response: dict | Any) -> str:
    try:
        if isinstance(response, dict):
            choices = response.get("choices") or []
            if not choices:
                return ""
            message = choices[0].get("message") or {}
            return str(message.get("content") or "").strip()

        choices = getattr(response, "choices", None) or []
        if not choices:
            return ""
        message = getattr(choices[0], "message", None)
        if isinstance(message, dict):
            return str(message.get("content") or "").strip()
        return str(getattr(message, "content", "") or "").strip()
    except Exception:
        return ""


def _fmt_brl(val: float) -> str:
    """Formata valor monetário em pt-BR (ex.: R$ 1.234,56)."""
    s = f"{abs(val):,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _linha_devedor_item(it: dict) -> Optional[str]:
    """Uma linha legível para inadimplência (IA costuma usar campos soltos ou em lista)."""
    if not isinstance(it, dict):
        return None
    nome = it.get("cliente") or it.get("cliente_nome") or it.get("nome")
    if not nome and it.get("descricao"):
        nome = it["descricao"]
    vd = it.get("valor_devido")
    if vd is None and str(it.get("tipo") or "").lower() != "saldo":
        vd = it.get("valor")
    if nome is None and vd is None:
        return None
    bits: list[str] = []
    if nome is not None:
        bits.append(str(nome).strip())
    if vd is not None:
        try:
            bits.append(_fmt_brl(float(vd)))
        except (TypeError, ValueError):
            bits.append(str(vd))
    dv = it.get("data_vencimento") or it.get("vencimento") or it.get("data_vcto")
    if dv:
        bits.append(f"venc. {dv}")
    return " — ".join(bits) if bits else None


def _append_financeiro_inadimplencia_texto(dados: dict, parts: list[str]) -> None:
    """Acrescenta texto para JSON de 'quem devê' (lista ou registro único no topo)."""
    for key in (
        "clientes",
        "inadimplentes",
        "contas_em_atraso",
        "devedores",
        "lista",
        "itens",
        "contas",
    ):
        lst = dados.get(key)
        if not isinstance(lst, list) or not lst:
            continue
        lines: list[str] = []
        for it in lst[:80]:
            if not isinstance(it, dict):
                continue
            line = _linha_devedor_item(it)
            if line:
                lines.append(line)
        if lines:
            parts.append(
                "Clientes com valores em atraso:\n"
                + "\n".join(f"• {ln}" for ln in lines)
            )
            return
    # Campos no nível raiz (um único registro)
    line = _linha_devedor_item(dados)
    if line:
        parts.append("Contas em atraso:\n• " + line)


def _texto_exibicao_para_modulo(modulo: str, dados: dict) -> str:
    """
    Monta texto legível para UI/SSE a partir do JSON validado pela IA.
    Usado quando o modelo retorna apenas estrutura (sem campo resposta no topo).
    """
    if not isinstance(dados, dict):
        return ""

    if modulo == "financeiro_analise":
        parts: list[str] = []
        resumo = (dados.get("resumo") or "").strip()
        if resumo:
            parts.append(resumo)
        tipo = str(dados.get("tipo") or "").lower()
        if tipo == "saldo" and dados.get("valor") is not None:
            try:
                v = float(dados["valor"])
                linha = f"Saldo do caixa: {_fmt_brl(v)}"
                if not parts:
                    parts.append(linha)
                elif linha.replace("Saldo do caixa: ", "") not in resumo:
                    parts.append(linha)
            except (TypeError, ValueError):
                pass
        elif not parts and dados.get("valor") is not None and tipo != "saldo":
            try:
                v = float(dados["valor"])
                parts.append(f"Valor: {_fmt_brl(v)}")
            except (TypeError, ValueError):
                pass
        kpi = dados.get("kpi_principal")
        if isinstance(kpi, dict) and not parts:
            try:
                nome = str(kpi.get("nome") or "Indicador")
                val = float(kpi.get("valor", 0))
                linha = f"{nome}: {_fmt_brl(val)}"
                comp = kpi.get("comparacao")
                if comp:
                    linha += f" ({comp})"
                parts.append(linha)
            except (TypeError, ValueError):
                pass
        for key, label in (("insights", "Insights"), ("recomendacoes", "Recomendações")):
            arr = dados.get(key)
            if isinstance(arr, list) and arr:
                bullets = "\n".join(
                    f"• {str(x).strip()}" for x in arr[:6] if str(x).strip()
                )
                if bullets:
                    parts.append(f"{label}:\n{bullets}")
        _append_financeiro_inadimplencia_texto(dados, parts)
        out = "\n\n".join(p for p in parts if p).strip()
        if out:
            return out
        tipo_an = dados.get("tipo_analise")
        if tipo_an:
            return f"Análise: {tipo_an}."
        return "Análise financeira concluída."

    if modulo == "conversao_analise":
        parts2: list[str] = []
        if dados.get("periodo"):
            parts2.append(f"Período: {dados['periodo']}")
        try:
            tx = float(dados.get("taxa_conversao", 0))
            parts2.append(f"Taxa de conversão: {tx * 100:.1f}%")
        except (TypeError, ValueError):
            pass
        if dados.get("orcamentos_enviados") is not None:
            parts2.append(f"Orçamentos enviados: {dados['orcamentos_enviados']}")
        if dados.get("orcamentos_aprovados") is not None:
            parts2.append(f"Aprovados: {dados['orcamentos_aprovados']}")
        if dados.get("ticket_medio") is not None:
            try:
                tm = float(dados["ticket_medio"])
                parts2.append(f"Ticket médio: {_fmt_brl(tm)}")
            except (TypeError, ValueError):
                pass
        if dados.get("servico_mais_vendido"):
            parts2.append(f"Serviço mais vendido: {dados['servico_mais_vendido']}")
        padroes = dados.get("padroes")
        if isinstance(padroes, list) and padroes:
            lines = []
            for p in padroes[:5]:
                if isinstance(p, dict) and p.get("descricao"):
                    lines.append(f"• {p.get('descricao')}")
            if lines:
                parts2.append("Padrões:\n" + "\n".join(lines))
        recs = dados.get("recomendacoes")
        if isinstance(recs, list) and recs:
            parts2.append(
                "Recomendações:\n"
                + "\n".join(f"• {str(x)}" for x in recs[:5] if str(x).strip())
            )
        out2 = "\n".join(p for p in parts2 if p).strip()
        return out2 or "Análise de conversão concluída."

    if modulo == "negocio_sugestoes":
        parts3: list[str] = []
        if dados.get("sugestao"):
            parts3.append(str(dados["sugestao"]))
        if dados.get("justificativa"):
            parts3.append(f"Justificativa: {dados['justificativa']}")
        if dados.get("impacto_estimado"):
            parts3.append(f"Impacto estimado: {dados['impacto_estimado']}")
        if dados.get("acao_imediata"):
            parts3.append(f"Ação imediata: {dados['acao_imediata']}")
        if dados.get("metrica_sucesso"):
            parts3.append(f"Métrica de sucesso: {dados['metrica_sucesso']}")
        tipo_s = dados.get("tipo_sugestao")
        if tipo_s and not parts3:
            parts3.append(f"Sugestão ({tipo_s})")
        out3 = "\n\n".join(p for p in parts3 if p).strip()
        return out3 or "Sugestão de negócio gerada."

    return ""


def _derive_ai_response_display_text(ai_response: AIResponse) -> str:
    """Texto para SSE/UI: usa resposta ou deriva de dados estruturados."""
    raw = (ai_response.resposta or "").strip()
    if raw:
        return raw
    dados = ai_response.dados
    if isinstance(dados, dict):
        mod = (ai_response.modulo_origem or "").strip()
        derived = _texto_exibicao_para_modulo(mod, dados).strip()
        if derived:
            return derived
    return ""


# ── Cache Inteligente ──────────────────────────────────────────────────────


class SimpleCache:
    """Cache TTL simples para reduzir chamadas à API"""

    def __init__(self, ttl_seconds: int = 300):
        self._cache = {}
        self._ttl = ttl_seconds

    def _generate_key(
        self, modulo: str, mensagem: str, empresa_id: Optional[int] = None
    ) -> str:
        """Gera chave única baseada no conteúdo"""
        content = f"{empresa_id or 0}:{modulo}:{mensagem.lower().strip()}"
        return hashlib.md5(content.encode()).hexdigest()

    def get(
        self, modulo: str, mensagem: str, empresa_id: Optional[int] = None
    ) -> Optional[AIResponse]:
        key = self._generate_key(modulo, mensagem, empresa_id)
        if key in self._cache:
            entry = self._cache[key]
            if datetime.now() < entry["expires_at"]:
                entry["data"].cache_hit = True
                return entry["data"]
            del self._cache[key]
        return None

    def set(
        self,
        modulo: str,
        mensagem: str,
        response: AIResponse,
        empresa_id: Optional[int] = None,
    ):
        key = self._generate_key(modulo, mensagem, empresa_id)
        self._cache[key] = {
            "data": response,
            "expires_at": datetime.now() + timedelta(seconds=self._ttl),
        }


# Instância global do cache
ai_cache = SimpleCache(ttl_seconds=300)


# ── Prompts Contextualizados por Módulo ────────────────────────────────────

PROMPTS = {
    "orcamentos": {
        "system": """Você é o assistente de orçamentos do COTTE. Extraia dados de orçamento de mensagens em linguagem natural.

REGRAS OBRIGATÓRIAS:
1. NUNCA invente valores ou nomes que não estejam explícitos na mensagem
2. Se não encontrar um dado, use null ou valores padrão indicados
3. Retorne APENAS JSON válido, sem explicações ou markdown extra
4. O campo 'confianca' deve refletir realmente a clareza da mensagem (0.0-1.0)

FORMATO DE SAÍDA:
{"cliente_nome":"string ou null","servico":"string ou null","valor":0.0,"desconto":0.0,"desconto_tipo":"percentual","observacoes":null,"confianca":0.0}

REGRAS DE NEGÓCIO:
- valor: número BRUTO (antes do desconto). "700 reais" → 700.0
- desconto: número puro (10 para 10%, 50 para R$50)
- desconto_tipo: "percentual" (se %) ou "fixo" (se R$)
- servico: use o nome EXATO escrito pelo usuário — não corrija ortografia, não normalize nomes incomuns (ex: "iphoney" → "iphoney", nunca "iPhone" ou "reparo em iPhone")
- sem valor → valor: 0.0, confianca: reduzida
- sem cliente → cliente_nome: "A definir"
- confianca < 0.5 se dados forem incompletos ou ambíguos""",
        "max_tokens": 150,
        "model": PROMPT_DEFAULT_MODEL,
    },
    "clientes": {
        "system": """Você é o assistente de cadastro de clientes do COTTE. Extraia informações de contato e identificação.

REGRAS OBRIGATÓRIAS:
1. NUNCA invente dados que não estejam na mensagem
2. Valide formatos de telefone e email quando presentes
3. Retorne APENAS JSON válido

FORMATO DE SAÍDA:
{"nome":"string ou null","telefone":"string formatado ou null","email":"string ou null","tipo":"pf ou pj ou null","documento":"cpf/cnpj ou null","endereco":{"cep":null,"logradouro":null,"numero":null},"confianca":0.0}

REGRAS DE NEGÓCIO:
- Telefone: remover caracteres não numéricos, adicionar +55 se necessário
- Nome: capitalizar (João Silva), nunca aceitar números ou símbolos estranhos
- Documento: validar dígitos (CPF=11, CNPJ=14)
- Tipo: inferir por documento ou contexto (empresa, oficina, comércio = pj)
- confianca < 0.6 se faltar nome ou dados forem ambíguos""",
        "max_tokens": 200,
        "model": PROMPT_DEFAULT_MODEL,
    },
    "financeiro": {
        "system": """Você é o assistente financeiro do COTTE. Categorize transações e identifique padrões.

REGRAS OBRIGATÓRIAS:
1. NUNCA invente valores ou categorias
2. Use apenas categorias predefinidas quando possível
3. Retorne APENAS JSON válido

FORMATO DE SAÍDA:
{"tipo":"receita ou despesa ou null","categoria":"string","valor":0.0,"data":"YYYY-MM-DD ou null","descricao":"string","recorrente":false,"confianca":0.0}

CATEGORIAS COMUNS:
Despesas: Material, Mão de Obra, Aluguel, Energia, Combustível, Marketing, Impostos
Receitas: Serviço, Produto, Consultoria, Recorrente

REGRAS DE NEGÓCIO:
- Valor sempre positivo, independente do tipo
- Data: usar data atual se não especificada
- Recorrente: true se mencionar "mensal", "todo mês", etc.
- confianca < 0.5 se categoria for incerta""",
        "max_tokens": 150,
        "model": PROMPT_DEFAULT_MODEL,
    },
    "comercial": {
        "system": """Você é o assistente comercial do COTTE. Qualifique leads e sugira abordagens.

REGRAS OBRIGATÓRIAS:
1. Baseie-se apenas nas informações fornecidas
2. Seja conservador nas qualificações
3. Retorne APENAS JSON válido

FORMATO DE SAÍDA:
{"qualificacao":"quente ou morno ou frio","prioridade":"alta ou media ou baixa","interesse":"string ou null","orcamento_estimado":0.0,"urgencia":"imediata ou curto_prazo ou longo_prazo","proximo_passo":"string","tags":[],"confianca":0.0}

REGRAS DE NEGÓCIO:
- Qualificação: quente (pronto para comprar), morno (interessado), frio (só pesquisa)
- Orçamento: 0.0 se não mencionado, nunca inventar
- Urgencia: basear-se em palavras como "urgente", "preciso", "amanhã"
- Tags: extrair serviços mencionados (pintura, reforma, elétrica)
- confianca < 0.6 se informações insuficientes""",
        "max_tokens": 180,
        "model": PROMPT_DEFAULT_MODEL,
    },
    "operador": {
        "system": """Você interpreta comandos de operadores do sistema COTTE.

REGRAS OBRIGATÓRIAS:
1. Identifique a ação principal com precisão
2. Extraia IDs de orçamento quando presentes
3. Retorne APENAS JSON válido

FORMATO DE SAÍDA:
{"acao":"VER ou DESCONTO ou ADICIONAR ou REMOVER ou ENVIAR ou CRIAR ou APROVAR ou RECUSAR ou AJUDA ou DESCONHECIDO","orcamento_id":null,"valor":null,"desconto_tipo":"percentual","descricao":null,"num_item":null,"confianca":0.0}

EXEMPLOS DE COMANDOS:
- "ver 5" → acao: VER, orcamento_id: 5, confianca: 1.0
- "10% no 3" → acao: DESCONTO, orcamento_id: 3, valor: 10, desconto_tipo: percentual, confianca: 1.0
- "adiciona filtro 80 no 3" → acao: ADICIONAR, orcamento_id: 3, descricao: "filtro", valor: 80, confianca: 1.0
- "remove item 2 do 5" → acao: REMOVER, orcamento_id: 5, num_item: 2, confianca: 1.0
- "aprovar 5" → acao: APROVAR, orcamento_id: 5, confianca: 1.0
- "ajuda" → acao: AJUDA, confianca: 1.0""",
        "max_tokens": 100,
        "model": PROMPT_DEFAULT_MODEL,
    },
    "conversacao": {
        "system": """Você é o assistente virtual do COTTE. Responda de forma amigável e profissional.

REGRAS:
1. Seja breve e direto (máximo 2-3 frases)
2. Use tom profissional mas caloroso
3. Sempre ofereça ajuda concreta quando possível
4. Se não souber, seja honesto e sugere falar com um humano""",
        "max_tokens": 120,
        "model": PROMPT_DEFAULT_MODEL,
    },
    "financeiro_analise": {
        "system": """Você é o assistente financeiro do COTTE. Você DEVE retornar APENAS JSON válido.

REGRAS:
1. Se a pergunta for sobre "saldo do caixa" ou "qual o saldo", retorne JSON simples com SOMENTE o valor
2. Se pedir "insights" ou "análise", inclua insights e recomendações
3. NÃO USE: markdown, blocos de código, asteriscos, emojis
4. Use campos vazios [] se não pedir insights/recomendações

FORMATO PARA SALDO SIMPLES:
{"valor":0.0,"tipo":"saldo"}

FORMATO COMPLETO:
{"tipo_analise":"string","resumo":"string","kpi_principal":{"nome":"string","valor":0.0,"comparacao":"string"},"insights":[],"recomendacoes":[],"confianca":0.0}

EXEMPLO - pergunta "qual o saldo?":
{"valor":4895.50,"tipo":"saldo"}

EXEMPLO - pergunta "mostre insights":
{"tipo_analise":"fluxo_caixa","resumo":"Saldo positivo","kpi_principal":{"nome":"Saldo","valor":4895.50,"comparacao":"+444%"},"insights":["Receitas pendentes"],"recomendacoes":["Acompanhar recebimentos"],"confianca":0.85}""",
        "max_tokens": 600,
        "model": PROMPT_DEFAULT_MODEL,
    },
    "conversao_analise": {
        "system": """Você é o analista de conversão do COTTE. Analise taxas de sucesso de orçamentos.

REGRAS OBRIGATÓRIAS:
1. Use apenas dados de orçamentos fornecidos
2. Calcule taxas e tendências reais
3. Identifique padrões de sucesso/falha
4. Retorne APENAS JSON válido

FORMATO DE SAÍDA:
{"periodo":"string","taxa_conversao":0.0,"orcamentos_enviados":0,"orcamentos_aprovados":0,"ticket_medio":0.0,"servico_mais_vendido":"string","padroes":[{"tipo":"string","descricao":"string","impacto":"alto medio baixo"}],"recomendacoes":["string"],"confianca":0.0}

REGRAS DE NEGÓCIO:
- taxa_conversao: aprovados / enviados (decimal 0-1)
- ticket_medio: valor médio dos orçamentos aprovados
- padrões: 3-5 padrões identificados
- recomendações: 2-4 sugestões para melhorar conversão
- confianca: baseada na quantidade de dados analisados""",
        "max_tokens": 250,
        "model": PROMPT_DEFAULT_MODEL,
    },
    "negocio_sugestoes": {
        "system": """Você é o consultor de negócios do COTTE. Forneça sugestões estratégicas baseadas em dados.

REGRAS OBRIGATÓRIAS:
1. Analise dados reais do negócio
2. Sugestões devem ser práticas e acionáveis
3. Priorize ações de maior impacto
4. Retorne APENAS JSON válido

FORMATO DE SAÍDA:
{"tipo_sugestao":"preco ou cliente ou operacao ou marketing","prioridade":"alta media baixa","sugestao":"string","justificativa":"string","impacto_estimado":"string","acao_imediata":"string","metrica_sucesso":"string","confianca":0.0}

TIPOS DE SUGESTÃO:
- "preco": ajustes de preços e margens
- "cliente": retenção e upsell
- "operacao": eficiência e processos
- "marketing": aquisição e divulgação

REGRAS DE NEGÓCIO:
- Prioridade: baseada no impacto potencial
- Impacto estimado: qualitativo (ex: "+15% receita")
- Ação imediata: primeiro passo concreto
- Métrica sucesso: como medir o resultado
- confianca: baseada na robustez da análise""",
        "max_tokens": 200,
        "model": PROMPT_DEFAULT_MODEL,
    },
}


# ── Sistema Anti-Delírios (4 Camadas) ───────────────────────────────────────


class AntiDeliriumSystem:
    """Sistema de 4 camadas para prevenir alucinações da IA"""

    # Valores máximos realistas por módulo
    LIMITES = {
        "orcamentos": {
            "valor_max": 500000.0,
            "valor_min": 0.0,
            "nome_min_chars": 2,
            "nome_max_chars": 100,
            "servicos_comuns": [
                "pintura",
                "reforma",
                "elétrica",
                "hidráulica",
                "gesso",
                "piso",
                "azulejo",
            ],
        },
        "clientes": {
            "nome_min_chars": 2,
            "nome_max_chars": 100,
            "telefone_min_digits": 10,
            "telefone_max_digits": 13,
            "caracteres_invalidos_nome": set("0123456789{}[]<>|\\/"),
        },
        "financeiro": {
            "valor_max": 1000000.0,
            "valor_min": 0.0,
            "categorias_validas": {
                "despesa": [
                    "Material",
                    "Mão de Obra",
                    "Aluguel",
                    "Energia",
                    "Água",
                    "Combustível",
                    "Marketing",
                    "Impostos",
                    "Manutenção",
                    "Outros",
                ],
                "receita": [
                    "Serviço",
                    "Produto",
                    "Consultoria",
                    "Recorrente",
                    "Outros",
                ],
            },
        },
        "financeiro_analise": {
            "valor_max": 10000000.0,
            "valor_min": 0.0,
            "periodo_max_dias": 365,
            "insights_max": 5,
            "recomendacoes_max": 4,
        },
        "conversao_analise": {
            "taxa_conversao_max": 1.0,
            "taxa_conversao_min": 0.0,
            "orcamentos_min_para_analise": 5,
            "padroes_max": 6,
            "recomendacoes_max": 5,
        },
        "negocio_sugestoes": {
            "impacto_max_caracteres": 50,
            "acao_max_caracteres": 100,
            "metrica_max_caracteres": 80,
        },
    }

    @classmethod
    def camada_1_sanitizar_entrada(
        cls, mensagem: str, modulo: str
    ) -> tuple[str, list[str]]:
        """Remove ruídos e caracteres problemáticos"""
        erros = []

        if not mensagem or len(mensagem.strip()) < 2:
            erros.append("Mensagem vazia ou muito curta")
            return "", erros

        # Limitar tamanho por módulo
        limites_tamanho = {
            "orcamentos": 500,
            "clientes": 300,
            "financeiro": 400,
            "comercial": 500,
        }
        max_len = limites_tamanho.get(modulo, 500)

        if len(mensagem) > max_len:
            mensagem = mensagem[:max_len]
            erros.append(f"Mensagem truncada para {max_len} caracteres")

        # Remover caracteres de controle (exceto newline/tab)
        cleaned = "".join(ch for ch in mensagem if ord(ch) >= 32 or ch in ("\n", "\t"))

        # Normalizar whitespace
        cleaned = " ".join(cleaned.split())

        return cleaned, erros

    @classmethod
    def camada_2_validar_schema(
        cls, dados: dict, modulo: str
    ) -> tuple[dict, list[str]]:
        """Valida tipos e estrutura do JSON retornado"""
        erros = []

        if not isinstance(dados, dict):
            erros.append("Resposta não é um objeto JSON válido")
            return {}, erros

        # Verificar campos obrigatórios por módulo
        campos_obrigatorios = {
            "orcamentos": ["confianca"],
            "clientes": ["nome", "confianca"],
            "financeiro": ["tipo", "valor", "confianca"],
            "comercial": ["qualificacao", "confianca"],
        }

        obrigatorios = campos_obrigatorios.get(modulo, ["confianca"])
        for campo in obrigatorios:
            if campo not in dados:
                erros.append(f"Campo obrigatório ausente: {campo}")
                dados[campo] = None

        # Garantir confianca é float válido
        try:
            confianca = float(dados.get("confianca", 0.5))
            dados["confianca"] = max(0.0, min(1.0, confianca))
        except (ValueError, TypeError):
            dados["confianca"] = 0.5
            erros.append("Confiança inválida, usando padrão 0.5")

        return dados, erros

    @classmethod
    def camada_3_validar_dominio(
        cls, dados: dict, modulo: str
    ) -> tuple[dict, list[str]]:
        """Valida regras de negócio e valores realistas"""
        erros = []
        limites = cls.LIMITES.get(modulo, {})

        if modulo == "orcamentos":
            # Validar valor
            try:
                valor = float(dados.get("valor", 0))
                if valor < limites.get("valor_min", 0):
                    erros.append(f"Valor negativo ({valor}), corrigido para 0")
                    dados["valor"] = 0.0
                    dados["confianca"] = min(dados.get("confianca", 0.5), 0.3)
                elif valor > limites.get("valor_max", 999999):
                    erros.append(f"Valor suspeito ({valor}), corrigido para 0")
                    dados["valor"] = 0.0
                    dados["confianca"] = 0.1
            except (ValueError, TypeError):
                dados["valor"] = 0.0

            # Validar nome do cliente
            nome = str(dados.get("cliente_nome", ""))
            if nome:
                if len(nome) < limites.get("nome_min_chars", 2):
                    erros.append(f"Nome muito curto: '{nome}'")
                    dados["cliente_nome"] = "A definir"
                    dados["confianca"] = min(dados.get("confianca", 0.5), 0.4)
                elif any(c in nome for c in "{}[]<>|\\/0123456789"):
                    erros.append(f"Nome contém caracteres inválidos: '{nome}'")
                    dados["cliente_nome"] = "A definir"
                    dados["confianca"] = min(dados.get("confianca", 0.5), 0.3)

        elif modulo == "clientes":
            # Validar nome
            nome = str(dados.get("nome", ""))
            if nome:
                invalid_chars = limites.get("caracteres_invalidos_nome", set())
                if any(c in nome for c in invalid_chars):
                    erros.append(f"Nome contém caracteres inválidos")
                    dados["nome"] = None
                    dados["confianca"] = 0.1

            # Validar telefone
            telefone = str(dados.get("telefone", ""))
            if telefone:
                digitos = re.sub(r"\D", "", telefone)
                min_dig = limites.get("telefone_min_digits", 10)
                max_dig = limites.get("telefone_max_digits", 13)
                if len(digitos) < min_dig or len(digitos) > max_dig:
                    erros.append(f"Telefone inválido ({len(digitos)} dígitos)")
                    dados["telefone"] = None

        elif modulo == "financeiro":
            # Validar valor
            try:
                valor = abs(float(dados.get("valor", 0)))
                if valor > limites.get("valor_max", 999999):
                    erros.append(f"Valor financeiro suspeito: {valor}")
                    dados["valor"] = 0.0
                    dados["confianca"] = 0.1
            except (ValueError, TypeError):
                dados["valor"] = 0.0

            # Validar categoria
            tipo = dados.get("tipo", "").lower()
            categoria = dados.get("categoria", "")
            categorias_validas = limites.get("categorias_validas", {})
            if tipo in categorias_validas:
                if categoria not in categorias_validas[tipo]:
                    erros.append(f"Categoria '{categoria}' não reconhecida para {tipo}")
                    dados["confianca"] = min(dados.get("confianca", 0.5), 0.4)

        elif modulo == "financeiro_analise":
            # Validar KPI principal
            kpi = dados.get("kpi_principal", {})
            if kpi:
                try:
                    valor_kpi = float(kpi.get("valor", 0))
                    if valor_kpi < limites.get(
                        "valor_min", 0
                    ) or valor_kpi > limites.get("valor_max", 9999999):
                        erros.append(f"KPI com valor fora do range: {valor_kpi}")
                        dados["confianca"] = min(dados.get("confianca", 0.5), 0.4)
                except (ValueError, TypeError):
                    erros.append("KPI principal com valor inválido")
                    dados["confianca"] = min(dados.get("confianca", 0.5), 0.3)

            # Validar tamanho das listas
            insights = dados.get("insights", [])
            recomendacoes = dados.get("recomendacoes", [])
            if len(insights) > limites.get("insights_max", 5):
                dados["insights"] = insights[: limites.get("insights_max", 5)]
                erros.append("Insights limitados ao máximo permitido")
            if len(recomendacoes) > limites.get("recomendacoes_max", 4):
                dados["recomendacoes"] = recomendacoes[
                    : limites.get("recomendacoes_max", 4)
                ]
                erros.append("Recomendações limitadas ao máximo permitido")

        elif modulo == "conversao_analise":
            # Validar taxa de conversão
            try:
                taxa = float(dados.get("taxa_conversao", 0))
                if taxa < limites.get("taxa_conversao_min", 0) or taxa > limites.get(
                    "taxa_conversao_max", 1
                ):
                    erros.append(f"Taxa de conversão inválida: {taxa}")
                    dados["taxa_conversao"] = max(0.0, min(1.0, taxa))
                    dados["confianca"] = min(dados.get("confianca", 0.5), 0.3)
            except (ValueError, TypeError):
                dados["taxa_conversao"] = 0.0

            # Validar contadores
            enviados = dados.get("orcamentos_enviados", 0)
            aprovados = dados.get("orcamentos_aprovados", 0)
            if aprovados > enviados:
                erros.append("Aprovados maior que enviados - corrigindo")
                dados["orcamentos_aprovados"] = enviados
                dados["confianca"] = min(dados.get("confianca", 0.5), 0.2)

            if enviados < limites.get("orcamentos_min_para_analise", 5):
                erros.append("Dados insuficientes para análise confiável")
                dados["confianca"] = min(dados.get("confianca", 0.5), 0.3)

        elif modulo == "negocio_sugestoes":
            # Validar tamanho dos campos de texto
            campos_texto = ["impacto_estimado", "acao_imediata", "metrica_sucesso"]
            limites_caracteres = {
                "impacto_estimado": limites.get("impacto_max_caracteres", 50),
                "acao_imediata": limites.get("acao_max_caracteres", 100),
                "metrica_sucesso": limites.get("metrica_max_caracteres", 80),
            }

            for campo in campos_texto:
                texto = dados.get(campo, "")
                if texto and len(texto) > limites_caracteres[campo]:
                    dados[campo] = texto[: limites_caracteres[campo]] + "..."
                    erros.append(f"Campo {campo} truncado por excesso de caracteres")

            # Validar tipo de sugestão
            tipos_validos = ["preco", "cliente", "operacao", "marketing"]
            if dados.get("tipo_sugestao") not in tipos_validos:
                erros.append(f"Tipo de sugestão inválido: {dados.get('tipo_sugestao')}")
                dados["confianca"] = min(dados.get("confianca", 0.5), 0.4)

        return dados, erros

    @classmethod
    def camada_4_verificar_consistencia(
        cls, dados: dict, modulo: str, db: Session = None
    ) -> tuple[dict, list[str]]:
        """Verifica consistência com dados existentes no sistema"""
        erros = []

        # Se confianca muito baixa, marcar para revisão
        if dados.get("confianca", 0) < 0.4:
            erros.append("Baixa confiança na interpretação - revisão recomendada")

        # Verificar dados completos vs confiança
        campos_preenchidos = sum(
            1
            for v in dados.values()
            if v is not None and v != 0 and v != "" and v != "A definir"
        )
        campos_totais = len([k for k in dados.keys() if k != "confianca"])

        if campos_preenchidos == 0 and dados.get("confianca", 0) > 0.5:
            erros.append("Inconsistência: nenhum dado extraído mas confiança alta")
            dados["confianca"] = 0.1

        return dados, erros


# ── Fallback Manual (Regex) ────────────────────────────────────────────────


class FallbackManual:
    """Fallback usando regex quando IA falha"""

    @staticmethod
    def extrair_orcamento(mensagem: str) -> dict:
        """Extrai dados de orçamento usando padrões regex"""
        resultado = {
            "cliente_nome": None,
            "servico": None,
            "valor": 0.0,
            "desconto": 0.0,
            "desconto_tipo": "percentual",
            "observacoes": None,
            "confianca": 0.3,
        }

        # Extrair valor monetário — inclui "por N" (ex: "cartão por 15")
        padroes_valor = [
            r"R\$\s*(\d+[.,]?\d*)",
            r"(\d+[.,]\d+)\s*reais?",
            r"(\d+)\s*reais?",
            r"por\s+(\d+[.,]?\d*)",
            r"(\d+)\s*mil",
        ]
        for padrao in padroes_valor:
            match = re.search(padrao, mensagem, re.IGNORECASE)
            if match:
                valor_str = match.group(1).replace(",", ".")
                try:
                    resultado["valor"] = float(valor_str)
                    if "mil" in mensagem.lower():
                        resultado["valor"] *= 1000
                    break
                except ValueError:
                    pass

        # Extrair serviços — primeiro lista predefinida, depois genérico
        servicos_conhecidos = [
            "pintura",
            "reforma",
            "elétrica",
            "hidráulica",
            "gesso",
            "piso",
            "azulejo",
            "telhado",
        ]
        for servico in servicos_conhecidos:
            if servico in mensagem.lower():
                resultado["servico"] = servico
                break

        # Serviço genérico: "de um cartão", "de instalação", etc.
        if not resultado["servico"]:
            match_de = re.search(
                r"\bde\s+(?:um\s+|uma\s+|uns\s+|umas\s+)?"
                r"([\w\sáéíóúâêîôûãõàèìòùäëïöüç]{2,40}?)"
                r"(?:\s+por\b|\s+r\$|\s+\d+\s*reais|\s+para\b|$)",
                mensagem, re.IGNORECASE
            )
            if match_de:
                servico_generico = match_de.group(1).strip()
                if servico_generico and servico_generico.lower() not in ("um", "uma", "uns", "umas"):
                    resultado["servico"] = servico_generico

        # Extrair nome — aceita letras minúsculas e acentuadas
        _NOME_PAT = r"[A-Za-záéíóúâêîôûãõàèìòùäëïöüçÁÉÍÓÚÂÊÎÔÛÃÕÀÈÌÒÙÄËÏÖÜÇ]+"
        padroes_nome = [
            rf"para\s+({_NOME_PAT}(?:\s+{_NOME_PAT})?)",
            rf"cliente\s+({_NOME_PAT}(?:\s+{_NOME_PAT})?)",
            rf"\bdo\s+({_NOME_PAT}(?:\s+{_NOME_PAT})?)",
        ]
        for padrao in padroes_nome:
            match = re.search(padrao, mensagem, re.IGNORECASE)
            if match:
                nome = match.group(1).strip()
                # Evita capturar preposições soltas como nome
                if len(nome) >= 2 and nome.lower() not in ("um", "uma", "uns", "umas", "para"):
                    resultado["cliente_nome"] = nome.title()
                    break


        return resultado

    @staticmethod
    def extrair_comando(mensagem: str, contexto_operacional: Optional[dict] = None) -> dict:
        """Extrai comando de operador usando padrões"""
        resultado = {"acao": "DESCONHECIDO", "orcamento_id": None}

        # Identificar ação
        acoes = {
            r"\b(ver|mostrar?|exibir|abrir|acessar|carregar|detalhes)\b": "VER",
            r"\b(aprovar?|aceitar)\b": "APROVAR",
            r"\b(recusar?|rejeitar|negar)\b": "RECUSAR",
            r"\b(enviar?|mandar|envia)\b.*\be[-\s]?mail\b": "ENVIAR_EMAIL",
            r"\b(enviar?|mandar|envia)\b": "ENVIAR",
            r"\b(duplicar?|copiar?|clonar?|clone)\b": "DUPLICAR",
            r"\b(criar?|novo|adicionar?)\b": "CRIAR",
            r"\b(ajuda|help|\?)\b": "AJUDA",
        }

        for padrao, acao in acoes.items():
            if re.search(padrao, mensagem, re.IGNORECASE):
                resultado["acao"] = acao
                break

        # Extrair ID do orçamento — prioriza padrão explícito (O-N, ORC-N, "orçamento N")
        # antes de cair no primeiro número da frase (evita capturar "5" de "5%")
        match = re.search(
            r"(?:[A-Za-z]+-|orçamento\s*|orc\s*)(\d+)", mensagem, re.IGNORECASE
        )
        if match:
            resultado["orcamento_id"] = int(match.group(1))
        else:
            nums = re.findall(r"\d+", mensagem)
            if nums:
                resultado["orcamento_id"] = int(nums[-1])

        if resultado["orcamento_id"] is None and isinstance(contexto_operacional, dict):
            ctx_orc_id = contexto_operacional.get("orcamento_id_ativo")
            if isinstance(ctx_orc_id, int) and ctx_orc_id > 0:
                resultado["orcamento_id"] = ctx_orc_id

        # Se nenhuma ação foi encontrada mas foi passado um ID num formato curto (ex: "orçamento 138"), assume VER
        if resultado["acao"] == "DESCONHECIDO" and resultado["orcamento_id"] is not None:
            if len(mensagem.split()) <= 4:
                resultado["acao"] = "VER"

        return resultado


# ── COTTE AI Hub Principal ──────────────────────────────────────────────────


class CotteAIHub:
    """
    Hub centralizado de IA do COTTE

    Uso:
        hub = CotteAIHub()
        resultado = await hub.processar("orcamentos", "pintura 800 para João")
    """

    def __init__(self):
        self.cache = ai_cache
        self.anti_delirium = AntiDeliriumSystem()
        self.fallback = FallbackManual()

    def _construir_mensagem_com_contexto(
        self, modulo: str, mensagem: str, contexto: Optional[dict] = None
    ) -> str:
        """Constrói mensagem incluindo dados de contexto quando disponíveis"""
        # Começa com a mensagem original
        msg_completa = mensagem

        # Para módulos de análise, incluir dados do contexto na mensagem
        if (
            modulo in ("financeiro_analise", "conversao_analise", "negocio_sugestoes")
            and contexto
        ):
            dados_str = json.dumps(contexto, ensure_ascii=False)

            if modulo == "financeiro_analise":
                msg_completa = f"{mensagem}\n\nDADOS FINANCEIROS:\n{dados_str}"
            elif modulo == "conversao_analise":
                msg_completa = f"{mensagem}\n\nDADOS DE ORÇAMENTOS:\n{dados_str}"
            elif modulo == "negocio_sugestoes":
                msg_completa = f"{mensagem}\n\nDADOS DO NEGÓCIO:\n{dados_str}"

        return msg_completa

    async def processar(
        self,
        modulo: Literal[
            "orcamentos",
            "clientes",
            "financeiro",
            "comercial",
            "operador",
            "conversacao",
        ],
        mensagem: str,
        contexto: Optional[dict] = None,
        db: Optional[Session] = None,
        usar_cache: bool = True,
        confianca_minima: float = 0.5,
    ) -> AIResponse:
        """
        Processa uma mensagem através do pipeline completo de IA

        Args:
            modulo: Módulo do sistema (orcamentos, clientes, etc.)
            mensagem: Texto a ser processado
            contexto: Dados adicionais para contextualização
            db: Sessão do banco para verificações de consistência
            usar_cache: Se deve usar cache
            confianca_minima: Limite mínimo de confiança aceitável

        Returns:
            AIResponse padronizada com validação completa
        """

        # ── CAMADA 1: Sanitização ───────────────────────────────────────────
        mensagem_limpa, erros_sanitizacao = (
            self.anti_delirium.camada_1_sanitizar_entrada(mensagem, modulo)
        )

        if not mensagem_limpa:
            return AIResponse(
                sucesso=False,
                dados=None,
                confianca=0.0,
                erros=erros_sanitizacao + ["Mensagem inválida após sanitização"],
                fallback_utilizado=False,
                cache_hit=False,
                modulo_origem=modulo,
            )

        # ── Verificar Cache ─────────────────────────────────────────────────
        empresa_id_ctx = None
        if isinstance(contexto, dict):
            empresa_id_ctx = contexto.get("empresa_id")

        if usar_cache:
            cached = self.cache.get(modulo, mensagem_limpa, empresa_id=empresa_id_ctx)
            if cached:
                return cached

        # ── Chamada à IA ──────────────────────────────────────────────────────
        input_tokens = 0
        output_tokens = 0
        try:
            from app.services.ia_service import ia_service

            # Usar PromptLoader para obter configuração atualizada
            config = _prompt_loader.get_dict(modulo)

            # Construir mensagem com contexto (se disponível)
            mensagem_completa = self._construir_mensagem_com_contexto(
                modulo, mensagem_limpa, contexto
            )

            response = await ia_service.chat(
                messages=[
                    {"role": "system", "content": config["system"]},
                    {"role": "user", "content": mensagem_completa},
                ],
                temperature=float(config.get("temperature", 0.1) or 0.1),
                max_tokens=int(config.get("max_tokens", 150) or 150),
            )

            usage = response.get("usage", {}) if isinstance(response, dict) else {}
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)

            raw = _extract_text_content_from_ia_response(response)

            # NOVO: Extrair JSON robusto com AIJSONExtractor (Etapa 1)
            dados_brutos = AIJSONExtractor.extract(raw)

            if dados_brutos is None:
                raise json.JSONDecodeError(
                    "Não foi possível extrair JSON válido", raw, 0
                )

            fallback_usado = False
            erros_ia = []

        except (json.JSONDecodeError, Exception) as e:
            # IA falhou - usar fallback manual
            logger.warning(f"[AI Hub] Falha na IA para {modulo}: {e}")

            if modulo == "orcamentos":
                dados_brutos = self.fallback.extrair_orcamento(mensagem_limpa)
            elif modulo == "operador":
                dados_brutos = self.fallback.extrair_comando(mensagem_limpa)
            else:
                dados_brutos = {
                    "erro": "Não foi possível interpretar",
                    "confianca": 0.1,
                }

            fallback_usado = True
            erros_ia = [f"IA falhou, usando fallback: {str(e)[:100]}"]

        # ── CAMADA 2: Validação de Schema ────────────────────────────────────
        dados_validados, erros_schema = self.anti_delirium.camada_2_validar_schema(
            dados_brutos, modulo
        )

        # ── CAMADA 3: Validação de Domínio ────────────────────────────────────
        dados_validados, erros_dominio = self.anti_delirium.camada_3_validar_dominio(
            dados_validados, modulo
        )

        # ── CAMADA 4: Verificação de Consistência ────────────────────────────
        if db:
            dados_validados, erros_consistencia = (
                self.anti_delirium.camada_4_verificar_consistencia(
                    dados_validados, modulo, db
                )
            )
        else:
            erros_consistencia = []

        # ── Consolidar Resultado ──────────────────────────────────────────────
        todos_erros = (
            erros_sanitizacao
            + erros_ia
            + erros_schema
            + erros_dominio
            + erros_consistencia
        )
        confianca_final = dados_validados.get("confianca", 0.5)

        # Determinar sucesso
        sucesso = confianca_final >= confianca_minima and not any(
            e.startswith("Inconsistência") or e.startswith("IA falhou")
            for e in todos_erros
        )

        # Mapear tipo de resposta por módulo
        mapa_tipos = {
            "orcamentos": "orcamento_rascunho",
            "clientes": "cliente_extraido",
            "financeiro": "financeiro_categorizado",
            "comercial": "lead_qualificado",
            "operador": "comando_operador",
            "conversacao": "conversa",
            "financeiro_analise": "analise_financeira",
            "conversao_analise": "analise_conversao",
            "negocio_sugestoes": "sugestao_negocio",
        }

        resposta_texto = _texto_exibicao_para_modulo(modulo, dados_validados)
        if not (resposta_texto or "").strip():
            resposta_texto = None

        resultado = AIResponse(
            sucesso=sucesso,
            dados=dados_validados,
            resposta=resposta_texto,
            tipo_resposta=mapa_tipos.get(modulo, "geral"),
            acao_sugerida=dados_validados.get("acao") if modulo == "operador" else None,
            confianca=confianca_final,
            erros=todos_erros if todos_erros else [],
            fallback_utilizado=fallback_usado,
            cache_hit=False,
            modulo_origem=modulo,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        # ── Salvar no Cache ─────────────────────────────────────────────────
        if usar_cache and sucesso and confianca_final >= 0.7:
            self.cache.set(modulo, mensagem_limpa, resultado, empresa_id=empresa_id_ctx)

        # Log do processamento
        logger.info(
            f"[AI Hub] {modulo}: confianca={confianca_final:.2f}, "
            f"sucesso={sucesso}, fallback={fallback_usado}, erros={len(todos_erros)}"
        )


        return resultado

    async def conversar(
        self,
        mensagem: str,
        dados_empresa: Optional[dict] = None,
        contexto_conversa: Optional[list] = None,
    ) -> str:
        """
        Gera resposta de conversação amigável

        Args:
            mensagem: Mensagem do usuário
            dados_empresa: Dados da empresa para personalização
            contexto_conversa: Histórico recente da conversa

        Returns:
            Texto da resposta
        """
        empresa_nome = dados_empresa.get("nome", "COTTE") if dados_empresa else "COTTE"

        system_prompt = f"""Você é o assistente virtual da {empresa_nome}.
Responda de forma amigável, profissional e breve (máximo 2-3 frases).
Seja prestativo e direto nas respostas.
Se não souber algo, seja honesto e sugere falar com um atendente humano."""

        messages = [{"role": "user", "content": mensagem}]

        if contexto_conversa:
            messages = contexto_conversa + messages

        try:
            from app.services.ia_service import ia_service

            response = await ia_service.chat(
                messages=[{"role": "system", "content": system_prompt}, *messages],
                temperature=0.3,
                max_tokens=600,
            )
            return _extract_text_content_from_ia_response(response)
        except Exception as e:
            logger.error(f"[AI Hub] Erro na conversação: {e}")
            return f"Desculpe, tive um problema para processar sua mensagem. Como posso ajudar?"


# ── Instância Global ─────────────────────────────────────────────────────────

ai_hub = CotteAIHub()


# ── Assistente Unificado ──────────────────────────────────────────────────────

SYSTEM_PROMPT_ASSISTENTE = """Você é o assistente virtual do sistema COTTE.

SOBRE O COTTE:
Sistema de gestão para prestadores de serviço (pintores, reformadores, eletricistas, etc.). Módulos: Orçamentos, Clientes, Financeiro (caixa/receber/pagar), Catálogo, Comercial (CRM/leads/campanhas), Documentos, WhatsApp (bot automático), Agendamentos, Relatórios, Configurações e Assistente IA.

DADOS QUE VOCÊ TEM ACESSO (bloco [DADOS DO SISTEMA]):
- Contexto temporal: data e hora atuais
- Empresa e usuário: nome da empresa e do operador logado
- Financeiro: saldo do caixa, receitas e despesas do mês atual E do mês anterior com variação percentual
- Orçamentos: últimos 10 com status + lista de pendentes que precisam de ação (rascunho/enviado) com dias de espera
- Clientes: total cadastrados e os mais recentes
- Leads: funil comercial com contagem por estágio

INSTRUÇÕES:
1. Para perguntas sobre dados do negócio (saldo, orçamentos, clientes, faturamento), use APENAS os dados do bloco [DADOS DO SISTEMA]. Nunca invente números.
2. Para perguntas sobre como o sistema funciona ou se uma funcionalidade existe ("tem como X?", "como faço Y?", "é possível Z?"), use APENAS o bloco [DOCUMENTAÇÃO DO SISTEMA] quando disponível.
3. Se um dado não estiver em [DADOS DO SISTEMA], diga que não tem essa informação.
4. Responda em português brasileiro.
5. Seja conciso: máximo 4 frases para respostas simples, até 8 para análises detalhadas.
6. Quando houver orçamentos pendentes há muitos dias, destaque proativamente.
7. Quando houver variação % disponível, use-a para contextualizar desempenho.
8. Para saudações ou perguntas fora do escopo, responda brevemente e ofereça ajuda.
9. Quando o bloco [DOCUMENTAÇÃO DO SISTEMA] estiver disponível, reescreva com suas palavras em 2ª pessoa ("você"), seja objetivo, máximo 4 frases. Cite apenas os passos essenciais. Não invente funcionalidades.
10. Se o usuário perguntar "tem como X?" ou "é possível Y?" ou "consigo fazer Z?": procure na [DOCUMENTAÇÃO DO SISTEMA]. Se encontrou, responda SIM e explique como em até 4 frases. Se NÃO encontrou na documentação, responda honestamente que essa funcionalidade não está disponível no sistema atual — nunca invente.

FORMATO DE RESPOSTA OBRIGATÓRIO (JSON):
{"resposta": "texto da resposta para o usuário", "tipo": "financeiro|orcamentos|clientes|leads|agendamentos|ajuda|geral", "dados": null, "sugestoes": ["até 3 perguntas de acompanhamento relevantes"]}

REGRA CRÍTICA: Retorne APENAS o JSON acima. Sem markdown, sem blocos de código, sem texto fora do JSON."""


async def criar_orcamento_ia(
    mensagem: str, db: Session, empresa_id: int, usuario_id: int
) -> AIResponse:
    """
    Extrai dados de orçamento da mensagem, busca o cliente pelo nome
    e retorna uma prévia para confirmação do usuário.
    """
    from app.models.models import Cliente, Servico
    from app.services.ai_tools.orcamento_tools import (
        _resolver_cliente,
        CriarOrcamentoInput,
    )

    # 1. Extrair dados via módulo "orcamentos"
    # confianca_minima=0.3 aceita nomes sem maiúsculas, serviços genéricos e "por N"
    resultado = await ai_hub.processar("orcamentos", mensagem, confianca_minima=0.3)
    dados_raw = resultado.dados or {}
    # Rejeita apenas se não extraiu absolutamente nenhuma informação útil
    if not dados_raw or (
        not dados_raw.get("servico")
        and not dados_raw.get("valor")
        and not dados_raw.get("cliente_nome")
    ):
        return AIResponse(
            sucesso=False,
            resposta="Não entendi os dados do orçamento. Tente: 'Orçamento de pintura para João Silva, R$ 800'",
            tipo_resposta="erro",
            confianca=0.0,
            modulo_origem="criar_orcamento",
        )

    dados = dados_raw
    cliente_nome = (dados.get("cliente_nome") or "").strip()

    # 2. Resolver cliente usando a lógica centralizada
    cliente_match = None
    clientes_sugeridos = []
    _cliente_auto_criado = False
    erro_ambiguo = None

    if cliente_nome and cliente_nome.lower() != "a definir":

        class _FakeInput:
            cliente_id = None
            pass

        fake_input = _FakeInput()
        fake_input.cliente_nome = cliente_nome

        try:
            c, auto_criado, err = _resolver_cliente(
                fake_input, db, type("U", (), {"empresa_id": empresa_id})()
            )
            if err:
                if err.get("code") == "ambiguous_cliente":
                    erro_ambiguo = err
                    clientes_sugeridos = err.get("candidatos", [])
                else:
                    return AIResponse(
                        sucesso=False,
                        resposta=err.get("error", "Erro ao resolver cliente"),
                        tipo_resposta="erro",
                        confianca=0.0,
                        modulo_origem="criar_orcamento",
                    )
            else:
                cliente_match = c
                _cliente_auto_criado = auto_criado
        except Exception as e:
            logger.warning(f"Erro ao resolver cliente em criar_orcamento_ia: {e}")

    servico_preview = (dados.get("servico") or "").strip()
    materiais_novos_preview: list[dict[str, Any]] = []
    if servico_preview:
        encontrou_servico = (
            db.query(Servico)
            .filter(
                Servico.empresa_id == empresa_id,
                Servico.nome.ilike(f"%{servico_preview}%"),
                Servico.ativo.is_(True),
            )
            .first()
        )
        if not encontrou_servico:
            materiais_novos_preview.append(
                {
                    "descricao": servico_preview,
                    "valor_unit": float(dados.get("valor") or 0),
                }
            )
        elif not dados.get("valor") and encontrou_servico.preco_padrao:
            # Usar preço do catálogo quando nenhum valor foi informado
            dados["valor"] = float(encontrou_servico.preco_padrao)

    # 3. Montar preview
    preview = {
        "cliente_nome": cliente_match.nome
        if cliente_match
        else (cliente_nome or "A definir"),
        "cliente_id": cliente_match.id if cliente_match else None,
        "cliente_encontrado": cliente_match is not None and not erro_ambiguo,
        "cliente_auto_criado": _cliente_auto_criado,
        "clientes_sugeridos": clientes_sugeridos,
        "cliente_ambiguo": erro_ambiguo is not None,
        "servico": servico_preview,
        "valor": float(dados.get("valor") or 0),
        "desconto": float(dados.get("desconto") or 0),
        "desconto_tipo": dados.get("desconto_tipo") or "percentual",
        "observacoes": dados.get("observacoes"),
        "confianca": float(dados.get("confianca") or 0.5),
        "empresa_id": empresa_id,
        "usuario_id": usuario_id,
        "materiais_novos": materiais_novos_preview,
    }

    # 3b. Se nenhum valor foi informado, sugerir itens do catálogo antes de criar o orçamento
    if not preview["valor"] and not erro_ambiguo and preview["servico"]:
        from app.services.ai_catalog_suggester import (
            buscar_sugestoes_catalogo,
            formatar_resposta_sugestao,
        )

        sugestoes = buscar_sugestoes_catalogo(db, empresa_id, preview["servico"])
        if sugestoes:
            contexto_orc = {
                "cliente_nome": preview["cliente_nome"],
                "cliente_id": preview["cliente_id"],
                "servico": preview["servico"],
            }
            r = formatar_resposta_sugestao(sugestoes, preview["servico"], contexto_orc)
            return AIResponse(
                sucesso=r["sucesso"],
                resposta=r["resposta"],
                tipo_resposta=r["tipo_resposta"],
                dados=r["dados"],
                confianca=r["confianca"],
                modulo_origem=r["modulo_origem"],
            )
        # Sem catálogo e sem valor: pedir o valor antes de criar o preview
        cliente_ref = preview["cliente_nome"] or "o cliente"
        servico_ref = preview["servico"]
        return AIResponse(
            sucesso=False,
            resposta=(
                f"Qual o valor do orçamento de **{servico_ref}** para **{cliente_ref}**? "
                f"Informe o valor e envie novamente. Exemplo: "
                f"'orçamento de {servico_ref} para {cliente_ref}, R$ 150'"
            ),
            tipo_resposta="solicitar_valor",
            confianca=0.5,
            modulo_origem="criar_orcamento",
        )

    if erro_ambiguo:
        resposta = f"Encontrei vários clientes com o nome '{cliente_nome}'. Selecione um abaixo:"
    elif cliente_match and _cliente_auto_criado:
        resposta = f"Cliente '{cliente_match.nome}' cadastrado automaticamente. Revise o orçamento abaixo e confirme."
    elif cliente_match:
        resposta = f"Encontrei o cliente {cliente_match.nome}. Revise o orçamento abaixo e confirme."
    else:
        resposta = (
            f"Cliente '{cliente_nome}' não está cadastrado. O orçamento será criado sem cliente vinculado."
            if cliente_nome and cliente_nome.lower() != "a definir"
            else "Revise o orçamento abaixo e confirme."
        )

    return AIResponse(
        sucesso=True,
        resposta=resposta,
        tipo_resposta="orcamento_preview",
        dados=preview,
        confianca=float(dados.get("confianca") or 0.5),
        modulo_origem="criar_orcamento",
    )


async def faturamento_ia(
    db: Session, 
    empresa_id: int, 
    mes: Optional[int] = None, 
    ano: Optional[int] = None
) -> AIResponse:
    """Retorna faturamento bruto (soma de aprovados) para um mês/ano específico."""
    agora = datetime.now(_TZ_BR)
    target_mes = mes or agora.month
    target_ano = ano or agora.year

    stmt = select(
        func.sum(Orcamento.total),
        func.count(Orcamento.id)
    ).where(
        Orcamento.empresa_id == empresa_id,
        Orcamento.status == StatusOrcamento.APROVADO,
        extract("month", Orcamento.aprovado_em) == target_mes,
        extract("year", Orcamento.aprovado_em) == target_ano
    )
    
    res = db.execute(stmt).first()
    total = float(res[0] or 0)
    qtd = int(res[1] or 0)
    ticket = total / qtd if qtd > 0 else 0

    def fmt(v):
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    meses = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    label_periodo = f"{meses[target_mes]} de {target_ano}" if target_mes <= 12 else "este mês"

    resposta = (
        f"📊 Faturamento em {label_periodo}: *{fmt(total)}*\n"
        f"Aprovados: {qtd} orçamento(s) | Ticket médio: {fmt(ticket)}\n"
        f"(Total de orçamentos aprovados no período)"
    )

    return AIResponse(
        sucesso=True,
        resposta=resposta,
        tipo_resposta="faturamento",
        dados={
            "faturamento": total,
            "qtd_aprovados": qtd,
            "ticket_medio": ticket,
            "periodo": label_periodo
        },
        confianca=0.99,
        modulo_origem="financeiro_faturamento"
    )


async def contas_receber_ia(db: Session, empresa_id: int) -> AIResponse:
    """Retorna total a receber (valores em aberto de orçamentos aprovados)."""
    stmt = select(
        func.sum(Orcamento.total),
        func.count(Orcamento.id)
    ).where(
        Orcamento.empresa_id == empresa_id,
        Orcamento.status == StatusOrcamento.APROVADO
    )
    
    res = db.execute(stmt).first()
    total_aberto = float(res[0] or 0)
    qtd = int(res[1] or 0)

    # Vencidos (mais de 7 dias)
    sete_dias_atras = datetime.now(_TZ_BR) - timedelta(days=7)
    stmt_vencidos = select(func.sum(Orcamento.total), func.count(Orcamento.id)).where(
        Orcamento.empresa_id == empresa_id,
        Orcamento.status == StatusOrcamento.APROVADO,
        Orcamento.aprovado_em < sete_dias_atras
    )
    res_vencidos = db.execute(stmt_vencidos).first()
    total_vencido = float(res_vencidos[0] or 0)
    qtd_vencidos = int(res_vencidos[1] or 0)

    def fmt(v):
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    if total_vencido > 0:
        resposta = (
            f"📋 A receber: *{fmt(total_aberto)}*\n"
            f"Vencidos (7+ dias): {fmt(total_vencido)} ({qtd_vencidos} orçamento(s))\n"
            f"Total: {qtd} aprovação(ões) em aberto"
        )
    else:
        resposta = f"📋 A receber: *{fmt(total_aberto)}*\n{qtd} aprovação(ões) em aberto — nenhum vencido ainda"

    return AIResponse(
        sucesso=True,
        resposta=resposta,
        tipo_resposta="contas_receber",
        dados={
            "total_aberto": total_aberto,
            "total_vencido": total_vencido,
            "qtd": qtd,
        },
        confianca=0.98,
        modulo_origem="financeiro_contas_receber",
    )


async def contas_pagar_ia(db: Session, empresa_id: int) -> AIResponse:
    """Retorna total a pagar (parcelas/contas a pagar em aberto)."""
    stmt = select(
        func.sum(ContaFinanceira.valor),
        func.count(ContaFinanceira.id)
    ).where(
        ContaFinanceira.empresa_id == empresa_id,
        ContaFinanceira.tipo == "pagar",
        ContaFinanceira.status.notin_(["pago", "cancelado"])
    )
    
    res = db.execute(stmt).first()
    total_pagar = float(res[0] or 0)
    qtd = int(res[1] or 0)

    def fmt(v):
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    if qtd == 0:
        resposta = "✅ Nenhuma conta a pagar no momento."
    else:
        resposta = f"📤 A pagar: *{fmt(total_pagar)}*\n{qtd} conta(s) em aberto"

    return AIResponse(
        sucesso=True,
        resposta=resposta,
        tipo_resposta="contas_pagar",
        dados={"total_pagar": total_pagar, "qtd": qtd},
        confianca=0.98,
        modulo_origem="financeiro_contas_pagar",
    )


async def executar_comando_operador_ia(
    mensagem: str,
    db: Session,
    empresa_id: int,
    usuario_id: int,
) -> AIResponse:
    """
    Executa comandos de operador via chat do assistente.
    Reutiliza interpretar_comando_operador (ia_service) + lógica de comando_bot (orcamentos.py).
    """
    from app.models.models import Orcamento, StatusOrcamento, HistoricoEdicao
    from app.services.ia_service import interpretar_comando_operador
    from app.services import financeiro_service
    from app.services.quote_notification_service import (
        ensure_quote_approval_metadata,
        handle_quote_status_changed,
    )
    import sqlalchemy as _sa

    cmd = await interpretar_comando_operador(mensagem)
    acao = (cmd.get("acao") or "DESCONHECIDO").upper()
    orc_id = cmd.get("orcamento_id")

    # ── AJUDA ──
    if acao == "AJUDA":
        return AIResponse(
            sucesso=True,
            resposta="Comandos disponíveis: 'ver 5' · 'aprovar 5' · 'recusar 5' · 'enviar orçamento 5' · 'desconto 10% no 5' · 'adicionar item limpeza 80 no 5' · 'remover item 2 do 5'",
            tipo_resposta="operador_resultado",
            confianca=1.0,
            modulo_origem="operador",
        )

    # ── Ações que precisam de orcamento_id ──
    if (
        acao
        in ("APROVAR", "RECUSAR", "ENVIAR", "VER", "DESCONTO", "ADICIONAR", "REMOVER")
        and not orc_id
    ):
        return AIResponse(
            sucesso=False,
            resposta=f"Qual o número do orçamento? Ex: '{acao.lower()} 5'",
            tipo_resposta="operador_resultado",
            confianca=0.5,
            modulo_origem="operador",
        )

    orc = None
    if orc_id:
        # Prioriza match por número (ORC-71-26) pois é o que o usuário vê
        orc = (
            db.query(Orcamento)
            .filter(
                Orcamento.empresa_id == empresa_id,
                Orcamento.numero.like(f"ORC-{orc_id}-%"),
            )
            .first()
        )
        if not orc:
            # Fallback: busca por id de linha
            try:
                orc = (
                    db.query(Orcamento)
                    .filter(
                        Orcamento.empresa_id == empresa_id,
                        Orcamento.id == int(orc_id),
                    )
                    .first()
                )
            except (ValueError, TypeError):
                pass
        if not orc:
            return AIResponse(
                sucesso=False,
                resposta=f"Orçamento #{orc_id} não encontrado.",
                tipo_resposta="operador_resultado",
                confianca=0.9,
                modulo_origem="operador",
            )

    # ── VER ──
    if acao == "VER":
        return AIResponse(
            sucesso=True,
            resposta=f"Orçamento {orc.numero} — {orc.cliente.nome if orc.cliente else '?'} — R$ {orc.total:.2f} — {orc.status.value}",
            tipo_resposta="orcamento_card_unificado",
            dados={
                "id": orc.id,
                "numero": orc.numero,
                "cliente_nome": orc.cliente.nome if orc.cliente else "—",
                "cliente_id": orc.cliente_id,
                "total": float(orc.total or 0),
                "desconto": float(orc.desconto or 0),
                "desconto_tipo": orc.desconto_tipo or "percentual",
                "status": orc.status.value if orc.status else "",
                "forma_pagamento": orc.forma_pagamento.value
                if hasattr(orc.forma_pagamento, "value")
                else (orc.forma_pagamento or ""),
                "validade_dias": orc.validade_dias or 0,
                "observacoes": orc.observacoes or "",
                "link_publico": orc.link_publico or "",
                "tem_telefone": bool(orc.cliente and orc.cliente.telefone),
                "tem_email": bool(orc.cliente and orc.cliente.email),
                "itens": [
                    {
                        "descricao": it.descricao,
                        "quantidade": float(it.quantidade or 0),
                        "valor_unit": float(it.valor_unit or 0),
                        "total": float(it.total or 0),
                    }
                    for it in orc.itens
                ],
            },
            confianca=1.0,
            modulo_origem="operador",
        )

    # ── APROVAR ──
    if acao == "APROVAR":
        if orc.status == StatusOrcamento.APROVADO:
            return AIResponse(
                sucesso=True,
                resposta=f"Orçamento {orc.numero} já está aprovado.",
                tipo_resposta="operador_resultado",
                confianca=1.0,
                modulo_origem="operador",
            )
        old_status = orc.status
        orc.status = StatusOrcamento.APROVADO
        ensure_quote_approval_metadata(orc, source="ia")
        from app.utils.orcamento_utils import renomear_numero_aprovado

        renomear_numero_aprovado(orc)
        db.add(
            HistoricoEdicao(
                orcamento_id=orc.id,
                editado_por_id=usuario_id,
                descricao="Aprovado pelo assistente IA.",
            )
        )
        financeiro_service.criar_contas_receber_aprovacao(orc, empresa_id, db)
        try:
            from app.services.agendamento_auto_service import (
                processar_agendamento_apos_aprovacao,
            )

            processar_agendamento_apos_aprovacao(
                db, orc, canal="ia", usuario_id=usuario_id
            )
        except Exception:
            logger.exception(
                "Falha ao processar agendamento pós-aprovação (IA, orcamento_id=%s)",
                orc.id,
            )
        db.commit()
        db.refresh(orc)
        await handle_quote_status_changed(
            db=db,
            quote=orc,
            old_status=old_status,
            new_status=orc.status,
            source="assistente_ia",
        )
        return AIResponse(
            sucesso=True,
            resposta=f"Orçamento {orc.numero} aprovado com sucesso!",
            tipo_resposta="operador_resultado",
            dados={"acao": "APROVADO", "numero": orc.numero, "id": orc.id},
            confianca=1.0,
            modulo_origem="operador",
        )

    # ── RECUSAR ──
    if acao == "RECUSAR":
        if orc.status == StatusOrcamento.RECUSADO:
            return AIResponse(
                sucesso=True,
                resposta=f"Orçamento {orc.numero} já está recusado.",
                tipo_resposta="operador_resultado",
                confianca=1.0,
                modulo_origem="operador",
            )
        orc.status = StatusOrcamento.RECUSADO
        db.add(
            HistoricoEdicao(
                orcamento_id=orc.id,
                editado_por_id=usuario_id,
                descricao="Recusado pelo assistente IA.",
            )
        )
        db.commit()
        return AIResponse(
            sucesso=True,
            resposta=f"Orçamento {orc.numero} marcado como recusado.",
            tipo_resposta="operador_resultado",
            dados={"acao": "RECUSADO", "numero": orc.numero, "id": orc.id},
            confianca=1.0,
            modulo_origem="operador",
        )

    # ── ENVIAR (WhatsApp) ──
    if acao == "ENVIAR":
        if not orc.cliente or not orc.cliente.telefone:
            cliente_nome = orc.cliente.nome if orc.cliente else "cliente"
            return AIResponse(
                sucesso=False,
                resposta=f"Cliente {cliente_nome} não tem telefone cadastrado.",
                tipo_resposta="operador_resultado",
                confianca=1.0,
                modulo_origem="operador",
            )
        try:
            from app.services.whatsapp_service import enviar_orcamento_completo
            from app.utils.pdf_utils import (
                get_orcamento_dict_for_pdf,
                get_empresa_dict_for_pdf,
            )
            from app.services.pdf_service import gerar_pdf_orcamento

            orc_dict = get_orcamento_dict_for_pdf(orc, db)
            empresa_dict = get_empresa_dict_for_pdf(orc.empresa)

            # Campos legados/específicos esperados pela mensagem de WA
            orc_dict["cliente_nome"] = orc.cliente.nome
            orc_dict["empresa_nome"] = orc.empresa.nome

            pdf_bytes = gerar_pdf_orcamento(orc_dict, empresa_dict)
            await enviar_orcamento_completo(
                orc.cliente.telefone, orc_dict, pdf_bytes or b"", orc.empresa
            )
            return AIResponse(
                sucesso=True,
                resposta=f"Orçamento {orc.numero} enviado via WhatsApp para {orc.cliente.nome}!",
                tipo_resposta="operador_resultado",
                dados={"acao": "ENVIADO", "numero": orc.numero, "id": orc.id},
                confianca=1.0,
                modulo_origem="operador",
            )
        except Exception as e:
            logger.error(f"[executar_comando_operador_ia] Erro ao enviar WA: {e}")
            return AIResponse(
                sucesso=False,
                resposta=f"Não foi possível enviar o orçamento: {str(e)[:120]}",
                tipo_resposta="operador_resultado",
                confianca=0.0,
                erros=[str(e)],
                modulo_origem="operador",
            )

    # ── DESCONTO ──
    if acao == "DESCONTO":
        valor = float(cmd.get("valor") or 0)
        tipo = "fixo" if cmd.get("desconto_tipo") == "fixo" else "percentual"
        subtotal = sum(i.total for i in orc.itens)
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
        db.commit()
        sufixo = "%" if tipo == "percentual" else " R$"
        msg = f"Desconto de {valor:.0f}{sufixo} aplicado ao {orc.numero}. Novo total: R$ {novo_total:.2f}"
        return AIResponse(
            sucesso=True,
            resposta=msg,
            tipo_resposta="operador_resultado",
            dados={
                "acao": "DESCONTO",
                "numero": orc.numero,
                "total": novo_total,
                "id": orc.id,
            },
            confianca=1.0,
            modulo_origem="operador",
        )

    # ── ADICIONAR ──
    if acao == "ADICIONAR":
        from app.models.models import ItemOrcamento

        descricao = str(cmd.get("descricao") or "Item")
        valor_item = float(cmd.get("valor") or 0)
        if valor_item <= 0:
            return AIResponse(
                sucesso=False,
                resposta="Informe o valor do item. Ex: 'adicionar limpeza 80 no 5'",
                tipo_resposta="operador_resultado",
                confianca=0.5,
                modulo_origem="operador",
            )
        db.add(
            ItemOrcamento(
                orcamento_id=orc.id,
                descricao=descricao,
                quantidade=1,
                valor_unit=valor_item,
                total=valor_item,
            )
        )
        db.flush()
        db.refresh(orc)
        subtotal = sum(i.total for i in orc.itens)
        from app.utils.desconto import aplicar_desconto

        orc.total = aplicar_desconto(
            subtotal, orc.desconto or 0, orc.desconto_tipo or "percentual"
        )
        db.commit()
        return AIResponse(
            sucesso=True,
            resposta=f"Item '{descricao}' adicionado ao {orc.numero}. Total: R$ {orc.total:.2f}",
            tipo_resposta="operador_resultado",
            dados={
                "acao": "ADICIONADO",
                "numero": orc.numero,
                "total": float(orc.total),
                "id": orc.id,
            },
            confianca=1.0,
            modulo_origem="operador",
        )

    # ── REMOVER ──
    if acao == "REMOVER":
        itens = list(orc.itens)
        num_item = int(cmd.get("num_item") or 0)
        if num_item < 1 or num_item > len(itens):
            return AIResponse(
                sucesso=False,
                resposta=f"Item {num_item} inválido. Use 'ver {orc_id}' para listar os itens.",
                tipo_resposta="operador_resultado",
                confianca=0.8,
                modulo_origem="operador",
            )
        if len(itens) == 1:
            return AIResponse(
                sucesso=False,
                resposta="Não é possível remover o único item do orçamento.",
                tipo_resposta="operador_resultado",
                confianca=1.0,
                modulo_origem="operador",
            )
        desc_removido = itens[num_item - 1].descricao
        db.delete(itens[num_item - 1])
        db.flush()
        db.refresh(orc)
        subtotal = sum(i.total for i in orc.itens)
        from app.utils.desconto import aplicar_desconto

        orc.total = aplicar_desconto(
            subtotal, orc.desconto or 0, orc.desconto_tipo or "percentual"
        )
        db.commit()
        return AIResponse(
            sucesso=True,
            resposta=f"Item '{desc_removido}' removido de {orc.numero}. Total: R$ {orc.total:.2f}",
            tipo_resposta="operador_resultado",
            dados={
                "acao": "REMOVIDO",
                "numero": orc.numero,
                "total": float(orc.total),
                "id": orc.id,
            },
            confianca=1.0,
            modulo_origem="operador",
        )

    return AIResponse(
        sucesso=False,
        resposta=f"Comando '{acao}' não reconhecido. Digite 'ajuda' para ver os comandos disponíveis.",
        tipo_resposta="operador_resultado",
        confianca=0.3,
        modulo_origem="operador",
    )


_INTENCOES_FINANCEIRAS = {
    "SALDO_RAPIDO",
    "FATURAMENTO",
    "CONTAS_RECEBER",
    "CONTAS_PAGAR",
    "DASHBOARD",
    "PREVISAO",
    "INADIMPLENCIA",
    "ANALISE",
}


async def assistente_unificado(
    mensagem: str,
    sessao_id: str,
    db: Session,
    empresa_id: int,
    usuario_id: int = 0,
    permissoes: dict | None = None,
    is_gestor: bool = False,
    current_user: Usuario = None, # Adicionado current_user como parâmetro
) -> AIResponse:
    """
    Ponto de entrada único para o chat do assistente COTTE.

    Fluxo:
    1. Busca histórico da sessão
    2. Classifica a intenção da mensagem
    3. Busca dados do banco baseado na intenção
    4. Chama o gateway LiteLLM com contexto completo + histórico
    5. Persiste o turno na sessão
    6. Retorna AIResponse estruturado
    """
    from app.services.cotte_context_builder import SessionStore, ContextBuilder

    # 1. Histórico da sessão (últimas 6 mensagens)
    historico = SessionStore.get_or_create(sessao_id)

    # 2. Classificar intenção (regex determinístico)
    try:
        classificacao = await detectar_intencao_assistente_async(mensagem)
        intencao = classificacao.intencao.value
    except Exception:
        intencao = "CONVERSACAO"

    # Bloquear intenções financeiras para quem não tem permissão de financeiro
    _perms = permissoes or {}
    _nivel_fin = _perms.get("financeiro")
    _tem_financeiro = is_gestor or bool(_nivel_fin)
    if intencao in _INTENCOES_FINANCEIRAS and not _tem_financeiro:
        return AIResponse(
            sucesso=False,
            resposta="Você não tem acesso ao módulo financeiro. Fale com o gestor da sua conta para solicitar permissão.",
            tipo_resposta="sem_permissao",
            dados={},
            confianca=1.0,
            modulo_origem="assistente",
        )

    # Roteamento especial: criação de orçamento (não passa pelo prompt completo do assistente)
    if intencao == "CRIAR_ORCAMENTO":
        return await criar_orcamento_ia(
            mensagem=mensagem, db=db, empresa_id=empresa_id, usuario_id=usuario_id
        )

    # NOVO: Roteamento determinístico para relatórios e listagens de orçamentos
    if intencao == "GERAR_RELATORIO" and "orçament" in mensagem.lower():
        from app.services.ai_tools.orcamento_tools import _gerar_relatorio_orcamentos, GerarRelatorioOrcamentosInput, _resolver_status_orcamento_listar

        status_match = re.search(r"\b(pendentes?|enviados?|aprovados?|recusados?|rascunho)\b", mensagem.lower())
        status_str = status_match.group(0) if status_match else None
        
        status_value = None
        if status_str:
            try:
                status_enum = _resolver_status_orcamento_listar(status_str)
                status_value = status_enum.value
            except (KeyError, ValueError):
                status_value = None

        # Simula a chamada da tool diretamente
        inp = GerarRelatorioOrcamentosInput(status=status_value)
        dados = await _gerar_relatorio_orcamentos(inp, db=db, current_user=current_user)
        
        # Adapta a resposta para o formato AIResponse
        return AIResponse(
            sucesso=True,
            resposta="Aqui está o relatório de orçamentos que você pediu:",
            tipo_resposta="relatorio_dinamico",
            dados={
                "_meta_frontend_data": dados.get("_meta_frontend_data"),
                "is_report": True,
                "report_type": "orcamentos",
            },
            confianca=0.99,
            modulo_origem="assistente_determinista",
        )

    if intencao == "LISTAR_ORCAMENTOS":
        from app.services.ai_tools.orcamento_tools import _listar_orcamentos, ListarOrcamentosInput, _resolver_status_orcamento_listar
        
        status_match = re.search(r"pendentes|enviados|aprovados|recusados|rascunho", mensagem.lower())
        status_str = status_match.group(0) if status_match else None

        try:
            status_enum = _resolver_status_orcamento_listar(status_str) if status_str else None
            status_value = status_enum.value if status_enum else None
        except (KeyError, ValueError):
            status_value = None # Fallback to default if status is invalid

        inp = ListarOrcamentosInput(status=status_value)
        dados = await _listar_orcamentos(inp, db=db, current_user=current_user)

        return AIResponse(
            sucesso=True,
            resposta="Aqui estão os orçamentos encontrados:",
            tipo_resposta="lista_orcamentos",
            dados={
                "_meta_frontend_data": dados.get("_meta_frontend_data"),
                "is_list": True
            },
            confianca=0.99,
            modulo_origem="assistente_determinista",
        )

    if intencao == "LISTAR_CLIENTES":
        from app.services.ai_tools.cliente_tools import _listar_clientes, ListarClientesInput
        inp = ListarClientesInput(limit=20)
        dados = await _listar_clientes(inp, db=db, current_user=current_user)
        return AIResponse(
            sucesso=True,
            resposta="Aqui estão os clientes encontrados:",
            tipo_resposta="clientes_lista",
            dados=dados,
            confianca=0.99,
            modulo_origem="assistente_determinista",
        )

    # Roteamento especial: saldo rápido determinístico (evita interpretação do LLM)
    if intencao == "SALDO_RAPIDO":
        from app.services.ai_intention_classifier import saldo_rapido_ia

        return await saldo_rapido_ia(db=db, empresa_id=empresa_id)

    # Roteamento especial: onboarding guiado (sem LLM — puramente data-driven)
    if intencao == "ONBOARDING":
        from app.services.onboarding_service import (
            get_onboarding_status,
            formatar_resposta_onboarding,
        )

        status = get_onboarding_status(db=db, empresa_id=empresa_id)
        resposta = formatar_resposta_onboarding(status)
        return _v2_attach_operational_context_to_response(
            sessao_id=sessao_id,
            db=db,
            current_user=current_user,
            response=AIResponse(
                sucesso=True,
                resposta=resposta,
                tipo_resposta="onboarding",
                dados=status,
                confianca=1.0,
                modulo_origem="onboarding",
            ),
        )

    # Roteamento especial: comandos de operador (aprovar, recusar, enviar, ver, desconto...)
    if intencao == "OPERADOR":
        return await executar_comando_operador_ia(
            mensagem=mensagem,
            db=db,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
        )

    # Se conversa genérica + setup incompleto → IA responde normalmente mas adiciona dica sutil
    # REMOVIDO: bloco punitivo que bloqueava qualquer conversa abaixo de 60% onboarding
    # Agora: IA responde a qualquer pergunta, onboarding é apenas sugerido se relevante.

    # 2b. Extrair hints estruturados da mensagem via regex (pré-LLM)
    from app.services.text_preprocessor import parse_message_hints, build_hint_injection

    _hints = parse_message_hints(mensagem)
    _hint_str = build_hint_injection(_hints)

    # 3. Buscar contexto de dados relevante
    contexto = await ContextBuilder.build(
        intencao, db, empresa_id, usuario_id=usuario_id, mensagem=mensagem
    )

    # 4. Montar conteúdo da mensagem do usuário (com dados injetados)
    agora = datetime.now(_TZ_BR)
    cabecalho = f"Hoje: {agora.strftime('%A, %d/%m/%Y')} às {agora.strftime('%H:%M')}"
    # Contexto de ajuda usa bloco separado [DOCUMENTAÇÃO DO SISTEMA]
    doc_sistema = contexto.pop("documentacao_sistema", None) if contexto else None
    _hint_prefix = f"{_hint_str}\n\n" if _hint_str else ""
    if contexto:
        user_content = (
            f"{_hint_prefix}{mensagem}\n\n[DADOS DO SISTEMA]\n{cabecalho}\n"
            f"{json.dumps(contexto, ensure_ascii=False, default=str)}"
        )
    else:
        user_content = f"{_hint_prefix}{mensagem}\n\n[DADOS DO SISTEMA]\n{cabecalho}"
    if doc_sistema:
        user_content += f"\n\n[DOCUMENTAÇÃO DO SISTEMA]\n{doc_sistema}"

    messages = historico + [{"role": "user", "content": user_content}]

    # 5. Chamar o gateway LiteLLM
    try:
        from app.services.ia_service import ia_service

        # Adicionado para buscar a skill do usuário
        skill = db.query(CopilotoUserSkill).filter(CopilotoUserSkill.usuario_id == current_user.id).first()
        if skill:
            SYSTEM_PROMPT_ASSISTENTE_TURBO = SYSTEM_PROMPT_ASSISTENTE + f"\n\nINSTRUÇÕES ADICIONAIS DO USUÁRIO:\n{skill.skill_text}"
        else:
            SYSTEM_PROMPT_ASSISTENTE_TURBO = SYSTEM_PROMPT_ASSISTENTE

        response = await ia_service.chat(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_ASSISTENTE_TURBO},
                *messages,
            ],
            temperature=0.3,
            max_tokens=800,
        )
        raw = _extract_text_content_from_ia_response(response)

        # Tentar parsear JSON da resposta
        dados_resposta = AIJSONExtractor.extract(raw)
        if not dados_resposta:
            # Fallback: encapsular texto plain como resposta
            dados_resposta = {
                "resposta": raw[:800],
                "tipo": "geral",
                "dados": None,
                "sugestoes": [],
            }

        resposta_texto = dados_resposta.get("resposta", raw[:800])
        tipo = dados_resposta.get("tipo", intencao.lower())
        sugestoes_originais = dados_resposta.get("sugestoes", [])

        # Filtrar sugestões já vistas para evitar repetição
        sugestoes_novas = SessionStore.filter_new_suggestions(
            sessao_id,
            sugestoes_originais,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
        )
        if sugestoes_novas:
            SessionStore.add_seen_suggestions(
                sessao_id,
                sugestoes_novas,
                empresa_id=empresa_id,
                usuario_id=usuario_id,
            )

        # 6. Persistir turno (mensagem limpa, sem o bloco de dados)
        SessionStore.append(
            sessao_id, "user", mensagem, empresa_id=empresa_id, usuario_id=usuario_id
        )
        SessionStore.append(
            sessao_id,
            "assistant",
            resposta_texto,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
        )

        return AIResponse(
            sucesso=True,
            resposta=resposta_texto,
            tipo_resposta=tipo,
            dados=dados_resposta.get("dados"),
            acao_sugerida=json.dumps(sugestoes_novas, ensure_ascii=False)
            if sugestoes_novas
            else None,
            confianca=0.9,
            modulo_origem="assistente_unificado",
        )

    except Exception as e:
        logger.error(f"[assistente_unificado] Erro ao chamar LiteLLM: {e}")
        return AIResponse(
            sucesso=False,
            resposta="Não consegui processar sua mensagem. Tente novamente.",
            tipo_resposta="erro",
            confianca=0.0,
            erros=[str(e)],
            modulo_origem="assistente_unificado",
        )


def _v2_normalize_bootstrap_message(mensagem: str) -> str:
    texto = re.sub(r"\s+", " ", (mensagem or "").strip().lower())
    if not texto:
        return ""
    mapa = str.maketrans(
        {
            "ã": "a",
            "õ": "o",
            "ç": "c",
            "á": "a",
            "é": "e",
            "í": "i",
            "ó": "o",
            "ú": "u",
            "â": "a",
            "ê": "e",
            "ô": "o",
            "à": "a",
        }
    )
    return texto.translate(mapa).strip(" .!?")


def _v2_is_onboarding_bootstrap_message(mensagem: str) -> bool:
    # O frontend envia esse gatilho oculto ao abrir o assistente quando o
    # onboarding ainda está pendente. Não deve montar prompt nem chamar LLM.
    return _v2_normalize_bootstrap_message(mensagem) in {"comecar", "vamos comecar"}


def _v2_build_onboarding_fastpath_payload(
    db: Session, empresa_id: int
) -> tuple[str, dict]:
    from app.services.onboarding_service import (
        formatar_resposta_onboarding,
        get_onboarding_status,
    )

    status = get_onboarding_status(db=db, empresa_id=empresa_id)
    resposta = formatar_resposta_onboarding(status)
    return resposta, status


_V2_HELP_REQUEST_RE = re.compile(
    r"\b(como|tem como|da pra|dá pra|e possivel|é possível|consigo|onde fica|funciona|passo a passo|tutorial)\b",
    flags=re.IGNORECASE,
)
_V2_MINIMAL_INTENTS = {
    "CONVERSACAO",
    "OPERADOR",
    "CRIAR_ORCAMENTO",
    "SALDO_RAPIDO",
    "AGENDAMENTO_CRIAR",
    "AGENDAMENTO_LISTAR",
    "AGENDAMENTO_STATUS",
    "AGENDAMENTO_CANCELAR",
    "CONVERSAO",
    "FATURAMENTO",
    "CONTAS_RECEBER",
    "CONTAS_PAGAR",
    "PREVISAO",
    "ANALISE",
    "NEGOCIO",
    "GERAR_RELATORIO",
    "LISTAR_ORCAMENTOS",
    "INADIMPLENCIA",
}

_V2_TOOLSET_FINANCEIRO = {
    "obter_saldo_caixa",
    "listar_movimentacoes_financeiras",
    "listar_despesas",
    "criar_movimentacao_financeira",
    "registrar_pagamento_recebivel",
    "criar_despesa",
    "marcar_despesa_paga",
    "criar_parcelamento",
}
_V2_TOOLSET_ORCAMENTOS = {
    "listar_orcamentos",
    "obter_orcamento",
    "criar_orcamento",
    "duplicar_orcamento",
    "editar_orcamento",
    "editar_item_orcamento",
    "aprovar_orcamento",
    "recusar_orcamento",
    "enviar_orcamento_whatsapp",
    "enviar_orcamento_email",
    "anexar_documento_orcamento",
}
_V2_TOOLSET_CLIENTES = {
    "listar_clientes",
    "criar_cliente",
    "editar_cliente",
    "excluir_cliente",
}
_V2_TOOLSET_AGENDAMENTOS = {
    "listar_agendamentos",
    "criar_agendamento",
    "cancelar_agendamento",
    "remarcar_agendamento",
}
_V2_TOOLSET_CATALOGO = {"listar_materiais", "cadastrar_material"}
_V2_TOOLSET_CORE_READONLY = {
    "obter_saldo_caixa",
    "listar_orcamentos",
    "obter_orcamento",
    "listar_clientes",
    "listar_movimentacoes_financeiras",
    "listar_despesas",
    "listar_agendamentos",
    "listar_materiais",
}


def _v2_message_likely_requires_tools(mensagem: str) -> bool:
    msg = _v2_normalize_bootstrap_message(mensagem)
    if not msg:
        return False
    tokens = (
        "saldo",
        "caixa",
        "receita",
        "despesa",
        "financeiro",
        "faturamento",
        "orcamento",
        "orçamento",
        "cliente",
        "clientes",
        "agendamento",
        "agenda",
        "material",
        "catalogo",
        "catálogo",
        "listar",
        "mostrar",
        "ver",
        "criar",
        "editar",
        "excluir",
        "aprovar",
        "recusar",
        "enviar",
        "whatsapp",
        "email",
        "quanto",
        "quais",
        "quem",
        "alterar",
        "arredondar",
        "mudar",
        "modificar",
        "valor",
        "atualizar",
    )
    return any(t in msg for t in tokens)


def _v2_selected_tool_names_for_message(
    *,
    mensagem: str,
    prompt_strategy: str,
    resolved_engine: str,
) -> tuple[set[str] | None, str]:
    if resolved_engine != DEFAULT_ENGINE:
        return None, "engine_default"

    normalized = _v2_normalize_bootstrap_message(mensagem)
    intent = _v2_detect_deterministic_intent(mensagem)

    if intent == "GERAR_RELATORIO":
        return {"gerar_relatorio_dinamico"}, "relatorio_scoped"

    if intent in {"FATURAMENTO", "CONVERSAO", "ANALISE", "NEGOCIO", "PREVISAO"}:
        return {"gerar_relatorio_dinamico", "listar_orcamentos", "gerar_relatorio_vendas", "gerar_relatorio_ranking_clientes", "gerar_relatorio_contas_a_receber"}, "analise_scoped"

    if intent in {"CONTAS_RECEBER", "CONTAS_PAGAR"}:
        return {
            "gerar_relatorio_dinamico",
            "listar_movimentacoes_financeiras",
            "listar_despesas",
            "gerar_relatorio_contas_a_receber",
        }, "contas_scoped"

    if intent == "INADIMPLENCIA":
        return {"gerar_relatorio_dinamico", "listar_clientes", "gerar_relatorio_contas_a_receber"}, "inadimplencia_scoped"

    # Identifica se é do domínio financeiro ou inadimplência
    is_financeiro = any(
        k in normalized
        for k in (
            "saldo",
            "caixa",
            "financeiro",
            "receita",
            "despesa",
            "faturamento",
            "inadimpl",
            "devendo",
            "vencid",
        )
    )

    # A) Scoped tools também para `standard`
    # Libera perfil reduzido para financeiro mesmo fora do minimal
    if prompt_strategy != "minimal" and not is_financeiro:
        return None, "full"

    if intent == "CONVERSACAO" and not _v2_message_likely_requires_tools(mensagem):
        return set(), "minimal_conversation_no_tools"

    if is_financeiro:
        # Base bem mais enxuta para financeiro (evita carregar schemas inteiros)
        selected = {
            "obter_saldo_caixa",
            "listar_movimentacoes_financeiras",
            "listar_despesas",
            "listar_clientes",
        }
        # Inclui orçamentos apenas se houver menção explícita
        if any(
            k in normalized
            for k in (
                "orcamento",
                "orçamento",
                "venda",
                "aprovar",
                "pendente",
                "status",
            )
        ):
            selected |= {"listar_orcamentos"}
    else:
        selected = set(_V2_TOOLSET_CORE_READONLY)

    if any(
        k in normalized
        for k in ("orcamento", "orçamento", "aprovar", "recusar", "enviar")
    ):
        selected |= _V2_TOOLSET_ORCAMENTOS
    if any(
        k in normalized
        for k in ("saldo", "caixa", "financeiro", "receita", "despesa", "faturamento")
    ):
        selected |= _V2_TOOLSET_FINANCEIRO
    if "cliente" in normalized:
        selected |= _V2_TOOLSET_CLIENTES
    if "agenda" in normalized or "agendamento" in normalized:
        selected |= _V2_TOOLSET_AGENDAMENTOS
    if "material" in normalized or "catalogo" in normalized or "catálogo" in normalized:
        selected |= _V2_TOOLSET_CATALOGO
    if intent == "OPERADOR":
        selected |= (
            _V2_TOOLSET_ORCAMENTOS
            | _V2_TOOLSET_CLIENTES
            | _V2_TOOLSET_FINANCEIRO
            | _V2_TOOLSET_AGENDAMENTOS
            | _V2_TOOLSET_CATALOGO
        )

    return selected, f"{prompt_strategy}_intent_scoped"


def _v2_filter_tools_payload_by_name(
    tools_payload: list[dict[str, Any]],
    allowed_names: set[str] | None,
) -> list[dict[str, Any]]:
    if allowed_names is None:
        return list(tools_payload)
    return [
        item
        for item in tools_payload
        if ((item.get("function") or {}).get("name") or "") in allowed_names
    ]


def _v2_select_tools_payload(
    *,
    mensagem: str,
    prompt_strategy: str,
    resolved_engine: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool, str]:
    full_payload = tools_payload_for_engine(resolved_engine)
    allowed_names, profile = _v2_selected_tool_names_for_message(
        mensagem=mensagem,
        prompt_strategy=prompt_strategy,
        resolved_engine=resolved_engine,
    )
    selected = _v2_filter_tools_payload_by_name(full_payload, allowed_names)
    reduced = allowed_names is not None and len(selected) < len(full_payload)

    # Fallback preventivo: se a heurística reduziu demais em mensagem claramente operacional,
    # reabre para o catálogo completo antes de chamar o LLM.
    if reduced and not selected and _v2_message_likely_requires_tools(mensagem):
        return full_payload, full_payload, False, "fallback_preemptive_full"
    return selected, full_payload, reduced, profile


def _v2_should_retry_with_full_tools(
    *,
    mensagem: str,
    candidate_text: str,
    reduced_tools_active: bool,
) -> bool:
    if not reduced_tools_active:
        return False
    if not _v2_message_likely_requires_tools(mensagem):
        return False
    normalized = _v2_normalize_bootstrap_message(candidate_text)
    retry_markers = (
        "nao consegui",
        "não consegui",
        "nao foi possivel",
        "não foi possível",
        "nao ha ferramenta",
        "não há ferramenta",
        "sem ferramenta",
        "nao posso",
        "não posso",
    )
    if not normalized:
        return True
    return any(m in normalized for m in retry_markers)


def _v2_history_window_size(*, prompt_strategy: str, mensagem: str) -> int:
    if prompt_strategy != "minimal":
        return 12
    words = len((mensagem or "").split())
    intent = _v2_detect_deterministic_intent(mensagem)
    if (
        intent == "CONVERSACAO"
        and words <= 6
        and not _v2_message_likely_requires_tools(mensagem)
    ):
        return 1
    if words <= 12:
        return 2
    return 4


def _v2_detect_deterministic_intent(mensagem: str) -> str:
    try:
        return str(detectar_intencao_assistente(mensagem) or "CONVERSACAO").upper()
    except Exception:
        return "CONVERSACAO"


def _v2_is_saldo_rapido_message(mensagem: str) -> bool:
    return _v2_detect_deterministic_intent(mensagem) == "SALDO_RAPIDO"


def _v2_is_orcamento_fastpath_message(mensagem: str) -> bool:
    return _v2_detect_deterministic_intent(mensagem) == "CRIAR_ORCAMENTO"


def _v2_is_listar_orcamentos_fastpath_message(mensagem: str) -> bool:
    return _v2_detect_deterministic_intent(mensagem) == "LISTAR_ORCAMENTOS"


def _v2_is_listar_clientes_fastpath_message(mensagem: str) -> bool:
    return _v2_detect_deterministic_intent(mensagem) == "LISTAR_CLIENTES"


_RE_FOLLOWUP_DESCONTO_PCT = re.compile(r"(\d+(?:[.,]\d+)?)\s*%", re.IGNORECASE)
_RE_FOLLOWUP_ORCAMENTO_VALOR = re.compile(
    r"\b(qual\s+o\s+valor|quanto\s+ficou|valor\s+do\s+or[çc]amento|me\s+mostra\s+o\s+or[çc]amento|esse\s+or[çc]amento)\b",
    re.IGNORECASE,
)
_RE_FOLLOWUP_ORCAMENTO_CONTATO = re.compile(
    r"\b(follow[\s-]?up|proximo\s+contato|pr[óo]ximo\s+contato|entrar\s+em\s+contato|retomar)\b",
    re.IGNORECASE,
)
# Verbos de edição: se presentes, a mensagem é EDITAR, não uma consulta de valor
_RE_EDIT_VERBS = re.compile(
    r"\b(alterar?|mudar?|arredondar?|editar?|modificar?|atualizar?|trocar?|corrigir?|ajustar?)\b",
    re.IGNORECASE,
)

_RE_SHORT_AFFIRMATIVE = re.compile(
    r"^(sim|s|ok|okay|claro|pode|pode sim|com certeza|confirmo|isso|isso mesmo|pode ser)$",
    re.IGNORECASE,
)


def _v2_resolve_followup_confirmation_message(
    *, mensagem: str, contexto_operacional: Optional[dict]
) -> Optional[str]:
    text = (mensagem or "").strip()
    if not text or not _RE_SHORT_AFFIRMATIVE.match(text):
        return None
    if not isinstance(contexto_operacional, dict):
        return None

    followup = contexto_operacional.get("followup_pendente")
    if not isinstance(followup, dict):
        return None
    if str(followup.get("tipo") or "").strip().lower() == "listar_orcamentos_status":
        return "listar orçamentos em aberto com sugestão de follow-up"
    return None


def _v2_extract_pending_followup_from_assistant_text(text: str) -> Optional[dict]:
    normalized = (text or "").strip().lower()
    if not normalized:
        return None
    if "deseja que eu" in normalized and "orçament" in normalized and "contato" in normalized:
        return {
            "tipo": "listar_orcamentos_status",
            "mensagem": (text or "").strip(),
        }
    return None


def _v2_is_orcamento_context_followup_message(mensagem: str) -> bool:
    text = (mensagem or "").strip().lower()
    if not text:
        return False
    # Verbos de edição → não tratar como consulta de valor; deixa passar para OPERADOR/LLM
    if _RE_EDIT_VERBS.search(text):
        return False
    if _RE_FOLLOWUP_ORCAMENTO_VALOR.search(text):
        return True
    if _RE_FOLLOWUP_ORCAMENTO_CONTATO.search(text):
        return True
    if _RE_FOLLOWUP_DESCONTO_PCT.search(text) and (
        "desconto" in text or "der" in text or "aplica" in text or "aplicar" in text
    ):
        return True
    return False


def _coerce_positive_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        if normalized.isdigit():
            parsed = int(normalized)
            return parsed if parsed > 0 else None
    return None


async def _v2_build_orcamento_context_followup_response(
    *,
    mensagem: str,
    sessao_id: str,
    db: Session,
    current_user: Any,
    request_id: Optional[str],
) -> Optional[AIResponse]:
    from app.services.tool_executor import execute as tool_execute

    contexto_operacional = _v2_get_operational_context(
        sessao_id=sessao_id,
        db=db,
        current_user=current_user,
    )
    raw_orcamento_id = contexto_operacional.get("orcamento_id_ativo") if isinstance(contexto_operacional, dict) else None
    orcamento_id = _coerce_positive_int(raw_orcamento_id)

    msg = (mensagem or "").strip().lower()
    pct_match = _RE_FOLLOWUP_DESCONTO_PCT.search(msg)
    if orcamento_id is None:
        preview = contexto_operacional.get("orcamento_preview_ativo") if isinstance(contexto_operacional, dict) else None
        if not isinstance(preview, dict) or not _RE_FOLLOWUP_ORCAMENTO_VALOR.search(msg):
            return None
        valor = preview.get("valor")
        try:
            valor_float = float(valor or 0)
        except (TypeError, ValueError):
            valor_float = 0.0
        if valor_float <= 0:
            return None
        valor_fmt = f"R$ {valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        cliente_ref = preview.get("cliente_nome") or contexto_operacional.get("cliente_nome_ativo") or "o cliente"
        servico_ref = preview.get("servico") or "serviço"
        return AIResponse(
            sucesso=True,
            resposta=f"O valor da prévia do orçamento de {servico_ref} para {cliente_ref} é {valor_fmt}.",
            tipo_resposta="orcamento_preview",
            confianca=0.98,
            modulo_origem="assistente_v2_contexto",
            dados={**preview, "valor_fmt": valor_fmt, "input_tokens": 0, "output_tokens": 0},
        )

    if pct_match and ("desconto" in msg or "der" in msg or "aplica" in msg or "aplicar" in msg):
        mensagem_simulada = f"simular desconto de {pct_match.group(1)}% no {orcamento_id}"
        return await _v2_build_simular_desconto_response(
            mensagem=mensagem_simulada,
            db=db,
            current_user=current_user,
            request_id=request_id,
        )

    if not (
        _RE_FOLLOWUP_ORCAMENTO_VALOR.search(msg)
        or _RE_FOLLOWUP_ORCAMENTO_CONTATO.search(msg)
    ):
        return None

    tc_dict = {
        "id": "fast_context_orcamento_valor",
        "type": "function",
        "function": {
            "name": "obter_orcamento",
            "arguments": json.dumps({"id": orcamento_id}),
        },
    }
    result = await tool_execute(
        tc_dict,
        db=db,
        current_user=current_user,
        sessao_id=sessao_id,
        request_id=request_id,
    )
    if result.status != "ok" or not result.data:
        return None

    if _RE_FOLLOWUP_ORCAMENTO_CONTATO.search(msg):
        data_orc = result.data or {}
        status_orc = str(data_orc.get("status") or "").strip().upper()
        cliente = ((data_orc.get("cliente") or {}).get("nome") if isinstance(data_orc.get("cliente"), dict) else None) or "o cliente"
        numero = data_orc.get("numero") or f"O-{orcamento_id}"
        criado_em = data_orc.get("criado_em")
        dias_desde_criacao = None
        if isinstance(criado_em, str) and criado_em.strip():
            try:
                criado_dt = datetime.fromisoformat(criado_em.replace("Z", "+00:00"))
                dias_desde_criacao = max((datetime.now(timezone.utc) - criado_dt).days, 0)
            except Exception:
                dias_desde_criacao = None

        if status_orc in {"APROVADO", "RECUSADO", "CANCELADO"}:
            resposta = (
                f"O orçamento {numero} está com status {status_orc.lower()}. "
                "Não há follow-up comercial pendente para este orçamento."
            )
        else:
            if dias_desde_criacao is None:
                janela = "hoje"
            elif dias_desde_criacao <= 1:
                janela = "amanhã"
            elif dias_desde_criacao <= 3:
                janela = "hoje"
            else:
                janela = "o quanto antes (preferencialmente hoje)"
            resposta = (
                f"Para {cliente}, no orçamento {numero}, o próximo contato recomendado é {janela}."
            )

        return AIResponse(
            sucesso=True,
            resposta=resposta,
            tipo_resposta="operador_resultado",
            confianca=0.98,
            modulo_origem="assistente_v2_contexto",
            tool_trace=[{"tool": "obter_orcamento", "status": "ok", "latencia_ms": result.latencia_ms}],
            dados={
                **data_orc,
                "acao": "FOLLOWUP_RECOMENDADO",
                "followup_recomendado": True,
                "input_tokens": 0,
                "output_tokens": 0,
            },
        )

    return AIResponse(
        sucesso=True,
        resposta="",
        tipo_resposta="operador_resultado",
        confianca=0.98,
        modulo_origem="assistente_v2_contexto",
        tool_trace=[{"tool": "obter_orcamento", "status": "ok", "latencia_ms": result.latencia_ms}],
        dados={"acao": "VER", **(result.data or {}), "input_tokens": 0, "output_tokens": 0},
    )


async def _v2_build_listar_clientes_fastpath_response(
    *,
    mensagem: str,
    db: Session,
    current_user: Any,
) -> AIResponse | None:
    from app.services.ai_tools.cliente_tools import _listar_clientes, ListarClientesInput
    import re

    # Extrair filtros (busca, limit, cursor)
    busca_match = re.search(r'buscar? "([^"]+)"', mensagem)
    busca_val = busca_match.group(1) if busca_match else None

    cursor_match = re.search(r'cursor "([^"]+)"', mensagem)
    cursor_val = cursor_match.group(1) if cursor_match else None

    limite_match = re.search(r'limit(?:e)? (\d+)', mensagem.lower())
    limite_val = int(limite_match.group(1)) if limite_match else 20

    inp = ListarClientesInput(
        busca=busca_val,
        cursor=cursor_val,
        limit=limite_val,
    )
    result = await _listar_clientes(inp, db=db, current_user=current_user)

    clientes = result.get("clientes", [])
    total = result.get("total", 0)

    if not clientes:
        if cursor_val:
            resposta = "Não há mais clientes para exibir."
        else:
            resposta = "Não encontrei nenhum cliente cadastrado."
    else:
        if cursor_val:
            resposta = f"Carreguei mais {len(clientes)} cliente(s)."
        else:
            resposta = f"Encontrei {len(clientes)} cliente(s)."
        
        if result.get("has_more"):
            resposta += " (Há mais resultados disponíveis)"

    return AIResponse(
        sucesso=True,
        resposta=resposta,
        tipo_resposta="clientes_lista",
        dados=result,
        confianca=1.0,
        modulo_origem="assistente_v2_fastpath",
    )


async def _v2_build_listar_orcamentos_fastpath_response(
    *,
    mensagem: str,
    db: Session,
    current_user: Any,
) -> AIResponse | None:
    from app.services.ai_tools.orcamento_tools import (
        _listar_orcamentos,
        ListarOrcamentosInput,
        _resolver_status_orcamento_listar,
        _gerar_relatorio_orcamentos,
        GerarRelatorioOrcamentosInput,
    )
    from datetime import date
    import re
    import logging
    logger = logging.getLogger(__name__)

    status_match = re.search(
        r"pendentes?|enviados?|aprovados?|recusados?|rascunhos?", mensagem.lower()
    )
    status_str = status_match.group(0) if status_match else None

    # Extrair filtros adicionais da mensagem gerada pelo botão "Carregar mais"
    # Ex: Liste mais orçamentos com cursor "...", dias 30, limite 10. Status pendente. Cliente 123.
    cursor_match = re.search(r'cursor "([^"]+)"', mensagem)
    cursor_val = cursor_match.group(1) if cursor_match else None

    dias_match = re.search(r'dias (\d+)', mensagem.lower())
    dias_val = int(dias_match.group(1)) if dias_match else 30

    limite_match = re.search(r'limit(?:e)? (\d+)', mensagem.lower())
    limite_val = int(limite_match.group(1)) if limite_match else 10
    
    cliente_id_val = None
    cliente_match = re.search(r'(?:cliente|id|código|codigo)\s*(\d+)', mensagem.lower())
    if cliente_match:
        cliente_id_val = int(cliente_match.group(1))
    else:
        # Se não achou ID explícito, tenta achar o nome do cliente na frase
        # ex: "orçamentos da ana julia", "lista orçamentos aprovados ana julia"
        nome_match = re.search(
            r'(?:or[çc]amentos?)\s+'
            r'(?:(?:pendentes?|enviados?|aprovados?|recusados?|rascunhos?|status\s+\w+)\s+)?'
            r'(?:(?:da|do|de|para|cliente)\s+)?'
            r'([\wÀ-ÿ ]+?)'
            r'(?:\s+(?:nos?|últimos?|hoje|ontem|dias|id|código|limit|status|aprovado)|$)',
            mensagem.lower()
        )
        if nome_match:
            nome_busca = nome_match.group(1).strip()
            # Não buscar se bateu apenas em palavra reservada acidentalmente
            if nome_busca and nome_busca not in ['pendentes', 'enviados', 'aprovados', 'recusados', 'rascunhos', 'pendente', 'enviado', 'aprovado', 'recusado', 'rascunho']:
                from app.models.models import Cliente
                # Faz uma busca leve (ilike) pelo nome
                cliente_db = db.query(Cliente.id).filter(
                    Cliente.empresa_id == getattr(current_user, "empresa_id", 0),
                    Cliente.nome.ilike(f"%{nome_busca}%")
                ).first()
                if cliente_db:
                    cliente_id_val = cliente_db[0]

    try:
        aprovado_de_match = re.search(r'aprovado_em_de ([\d-]+)', mensagem.lower())
        aprovado_de_val = date.fromisoformat(aprovado_de_match.group(1)) if aprovado_de_match else None
    except ValueError:
        aprovado_de_val = None

    try:
        aprovado_ate_match = re.search(r'aprovado_em_ate ([\d-]+)', mensagem.lower())
        aprovado_ate_val = date.fromisoformat(aprovado_ate_match.group(1)) if aprovado_ate_match else None
    except ValueError:
        aprovado_ate_val = None

    # Substituir status se for extraído pelo comando explicitamente (ex: "Status pendente")
    status_cmd_match = re.search(r'status (\w+)', mensagem.lower())
    if status_cmd_match and not status_str:
        status_str = status_cmd_match.group(1)

    try:
        status_enum = (
            _resolver_status_orcamento_listar(status_str) if status_str else None
        )
        status_value = status_enum.value if status_enum else None
    except (KeyError, ValueError):
        status_value = None

    try:
        # 1. Busca os dados paginados para a visualização em tela
        inp_lista = ListarOrcamentosInput(
            status=status_value, 
            limit=limite_val,
            dias=dias_val,
            cursor=cursor_val,
            cliente_id=cliente_id_val,
            aprovado_em_de=aprovado_de_val,
            aprovado_em_ate=aprovado_ate_val
        )
        res_lista = await _listar_orcamentos(inp_lista, db=db, current_user=current_user)
        
        # 2. Busca a lista completa para o modo de impressão (até 1000 itens)
        inp_relatorio = GerarRelatorioOrcamentosInput(
            status=status_value,
            dias=dias_val,
            cliente_id=cliente_id_val,
            aprovado_em_de=aprovado_de_val,
            aprovado_em_ate=aprovado_ate_val
        )
        res_relatorio = await _gerar_relatorio_orcamentos(inp_relatorio, db=db, current_user=current_user)
    except Exception as e:
        logger.error(f"Erro no fastpath de listar orçamentos: {e}")
        return None

    if not isinstance(res_lista, dict) or res_lista.get("error"):
        logger.error(f"res_lista com erro: {res_lista.get('error')}")
        return None

    total = res_lista.get("total", 0)
    status_label = status_str or "encontrado(s)"
    resumo = f"Encontrei {total} orçamento(s) {status_label}."

    # Extrai a lista de orçamentos para a tabela paginada
    orcamentos_list_ui = res_lista.get("_meta_frontend_data", {}).get("orcamentos", [])
    
    # Extrai a lista completa de orçamentos para impressão
    orcamentos_list_impressao = res_relatorio.get("_meta_frontend_data", {}).get("orcamentos", [])

    return AIResponse(
        sucesso=True,
        resposta=resumo,
        tipo_resposta="lista_orcamentos",
        confianca=0.99,
        modulo_origem="assistente_v2",
        tool_trace=[{"tool": "listar_orcamentos", "status": "ok", "latencia_ms": 0}],
        dados={
            "_meta_frontend_data": res_lista.get("_meta_frontend_data"),
            "orcamentos": orcamentos_list_ui,
            "orcamentos_impressao": orcamentos_list_impressao,
            "total": total,
            "itens_retornados": res_lista.get("itens_retornados", len(orcamentos_list_ui)),
            "limit": res_lista.get("limit", 10),
            "has_more": res_lista.get("has_more", False),
            "next_cursor": res_lista.get("next_cursor"),
            "filtros": res_lista.get("filtros", {}),
            "totais_por_status": res_lista.get("totais_por_status", {}),
            "is_list": True,
            "input_tokens": 0,
            "output_tokens": 0,
            "intent_detectada": "LISTAR_ORCAMENTOS"
        },
    )
def _v2_is_operador_fastpath_message(mensagem: str) -> bool:
    """True se OPERADOR com ação + ID de orçamento claramente parseáveis (0 tokens LLM)."""
    if _v2_detect_deterministic_intent(mensagem) != "OPERADOR":
        return False
    cmd = FallbackManual.extrair_comando(mensagem)
    return cmd.get("acao") in {"APROVAR", "RECUSAR", "VER", "ENVIAR", "ENVIAR_EMAIL", "DUPLICAR"}


async def _v2_build_operador_fastpath_response(
    *,
    mensagem: str,
    db: Session,
    current_user: Any,
    sessao_id: str,
    request_id: Optional[str],
) -> Optional[AIResponse]:
    """Executa ação de orçamento (VER/APROVAR/RECUSAR/ENVIAR) sem chamar o LLM.

    Retorna None se a ação falhar — o chamador deve cair no fluxo LLM normal.
    """
    from app.services.tool_executor import execute as tool_execute

    contexto_operacional = _v2_get_operational_context(
        sessao_id=sessao_id,
        db=db,
        current_user=current_user,
    )
    cmd = FallbackManual.extrair_comando(mensagem, contexto_operacional)
    acao = cmd.get("acao")
    orcamento_id = cmd.get("orcamento_id")
    if not orcamento_id:
        return None

    tool_map: dict[str, tuple[str, dict]] = {
        "VER":      ("obter_orcamento",          {"id": orcamento_id}),
        "APROVAR":  ("aprovar_orcamento",         {"orcamento_id": orcamento_id}),
        "RECUSAR":  ("recusar_orcamento",         {"orcamento_id": orcamento_id}),
        "ENVIAR":       ("enviar_orcamento_whatsapp", {"orcamento_id": orcamento_id}),
        "ENVIAR_EMAIL": ("enviar_orcamento_email",    {"orcamento_id": orcamento_id}),
        "DUPLICAR":     ("duplicar_orcamento",        {"orcamento_id": orcamento_id}),
    }
    tool_entry = tool_map.get(acao)
    if not tool_entry:
        return None

    tool_name, tool_args = tool_entry
    tc_dict = {
        "id": f"fast_op_{acao.lower()}",
        "type": "function",
        "function": {"name": tool_name, "arguments": json.dumps(tool_args)},
    }
    result = await tool_execute(
        tc_dict,
        db=db,
        current_user=current_user,
        sessao_id=sessao_id,
        request_id=request_id,
    )

    if result.status == "pending":
        pending_action = result.pending_action or {}
        return AIResponse(
            sucesso=True,
            resposta="",
            tipo_resposta="operador_action",
            confianca=0.95,
            modulo_origem="assistente_v2",
            pending_action=pending_action,
            tool_trace=[{
                "tool": tool_name,
                "status": "pending",
                "latencia_ms": result.latencia_ms,
            }],
            dados={
                **(pending_action.get("args") or {}),
                **(pending_action.get("extras") or {}),
                "input_tokens": 0,
                "output_tokens": 0,
            },
        )

    if result.status == "ok":
        data = result.data or {}
        return AIResponse(
            sucesso=True,
            resposta="",
            tipo_resposta="operador_resultado",
            confianca=0.95,
            modulo_origem="assistente_v2",
            tool_trace=[{
                "tool": tool_name,
                "status": "ok",
                "latencia_ms": result.latencia_ms,
            }],
            dados={"acao": acao, **data, "input_tokens": 0, "output_tokens": 0},
        )

    # erro ou forbidden: cai no LLM para mensagem de erro contextual
    return None


_RE_SIMULAR_DESCONTO = re.compile(
    r'simular\s+desconto\s+de\s+(\d+(?:[.,]\d+)?)\s*%\s+(?:n[oa]?\s+)?([A-Za-z]+-?\d+|\d+)',
    re.IGNORECASE,
)


def _v2_is_simular_desconto_message(mensagem: str) -> bool:
    return bool(_RE_SIMULAR_DESCONTO.search(mensagem))


async def _v2_build_simular_desconto_response(
    *,
    mensagem: str,
    db: Session,
    current_user: Any,
    request_id: Optional[str],
) -> Optional[AIResponse]:
    """Simula desconto percentual em orçamento sem chamar o LLM (0 tokens)."""
    from app.services.tool_executor import execute as tool_execute
    from decimal import Decimal

    m = _RE_SIMULAR_DESCONTO.search(mensagem)
    if not m:
        return None

    pct_raw = m.group(1).replace(",", ".")
    orc_ref = m.group(2)
    try:
        pct = float(pct_raw)
    except ValueError:
        return None

    # Resolve número do orçamento para ID
    id_match = re.search(r'\d+', orc_ref)
    if not id_match:
        return None
    orcamento_id = int(id_match.group())

    tc_dict = {
        "id": f"fast_sim_desc",
        "type": "function",
        "function": {"name": "obter_orcamento", "arguments": json.dumps({"id": orcamento_id})},
    }
    result = await tool_execute(tc_dict, db=db, current_user=current_user, sessao_id="", request_id=request_id)
    if result.status != "ok" or not result.data:
        return None

    orc = result.data
    total_orig = float(orc.get("total") or 0)
    desconto_atual = float(orc.get("desconto") or 0)
    total_com_desc = round(total_orig * (1 - pct / 100), 2)
    economia = round(total_orig - total_com_desc, 2)

    def fmt_brl(v: float) -> str:
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    return AIResponse(
        sucesso=True,
        resposta="",
        tipo_resposta="orcamento_simulacao",
        confianca=0.99,
        modulo_origem="assistente_v2",
        dados={
            "acao": "SIMULAR_DESCONTO",
            "id": orc.get("id"),
            "numero": orc.get("numero"),
            "cliente": orc.get("cliente"),
            "total_original": total_orig,
            "total_original_fmt": fmt_brl(total_orig),
            "desconto_pct": pct,
            "economia": economia,
            "economia_fmt": fmt_brl(economia),
            "total_com_desconto": total_com_desc,
            "total_com_desconto_fmt": fmt_brl(total_com_desc),
            "input_tokens": 0,
            "output_tokens": 0,
        },
        tool_trace=[{"tool": "obter_orcamento", "status": "ok", "latencia_ms": 0}],
    )


async def _v2_build_saldo_fastpath_response(db: Session, empresa_id: int) -> AIResponse:
    from app.services.ai_intention_classifier import saldo_rapido_ia

    return await saldo_rapido_ia(db=db, empresa_id=empresa_id)


async def _v2_build_orcamento_fastpath_response(
    *,
    mensagem: str,
    db: Session,
    empresa_id: int,
    usuario_id: int,
) -> AIResponse:
    return await criar_orcamento_ia(
        mensagem=mensagem,
        db=db,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
    )


_V2_RELATORIO_INTENTS = {"GERAR_RELATORIO", "FATURAMENTO", "CONVERSAO", "DASHBOARD", "INADIMPLENCIA", "ANALISE", "PREVISAO"}

_V2_DOMINIO_KEYWORDS = {
    "inadimplencia": ("inadimpl", "devendo", "atrasado", "vencid", "atraso"),
    "servicos": ("serviç", "servic", "mais vendid", "top serviç", "top servic"),
    "agendamentos": ("agendamento", "agenda"),
    "clientes": ("ranking de cliente", "melhores clientes", "top cliente", "inativo"),
    "orcamentos": ("orcament", "orçament", "conversão", "conversao", "faturamento", "ticket", "pendente", "aprovado"),
    "financeiro": ("fluxo de caixa", "financeir", "contas a receber", "contas a pagar", "receita", "despesa", "dashboard", "caixa", "resumo"),
    "inadimplencia": ("inadimplente", "devedor", "atraso", "devendo"),
}

_V2_PERIODO_RE = re.compile(
    r"(?:ultim[oa]s?|nos?|últim[oa]s?)\s*(\d{1,3})\s*(dia|dias|semana|semanas|mes|meses|mês|ano|anos)",
    re.IGNORECASE,
)


def _v2_parse_relatorio_params(mensagem: str, intent_str: str | None = None) -> tuple[str, int, str | None, str | None]:
    msg = _v2_normalize_bootstrap_message(mensagem) or ""
    msg_low = msg.lower()

    # domínio
    dominio = "orcamentos"
    if intent_str == "INADIMPLENCIA":
        dominio = "inadimplencia"
    else:
        for dom, kws in _V2_DOMINIO_KEYWORDS.items():
            if any(k in msg_low for k in kws):
                dominio = dom
                break

    # período
    periodo_dias = 30
    if "hoje" in msg_low:
        periodo_dias = 1
    elif "semana" in msg_low and "semanas" not in msg_low:
        periodo_dias = 7
    elif "trimestre" in msg_low:
        periodo_dias = 90
    elif "ano" in msg_low:
        periodo_dias = 365
    elif "mês atual" in msg_low or "mes atual" in msg_low or "este mês" in msg_low or "este mes" in msg_low:
        # Dias desde o início do mês atual
        periodo_dias = (datetime.now(_TZ_BR).day)
    elif "mês" in msg_low or "mes" in msg_low:
        periodo_dias = 30
    m = _V2_PERIODO_RE.search(msg_low)
    if m:
        n = int(m.group(1))
        unidade = m.group(2)
        if "semana" in unidade:
            periodo_dias = n * 7
        elif "mes" in unidade or "mês" in unidade or "meses" in unidade:
            periodo_dias = n * 30
        elif "ano" in unidade:
            periodo_dias = n * 365
        else:
            periodo_dias = n
    periodo_dias = max(1, min(periodo_dias, 365))

    # agrupamento
    agrupamento: str | None = None
    if any(k in msg_low for k in ("por cliente", "ranking de cliente", "top cliente", "ranking", "quem mais comprou", "maior comprador", "maiores clientes")):
        agrupamento = "cliente"
    elif any(k in msg_low for k in ("evolução", "evolucao", "por mês", "por mes", "por dia", "ao longo do tempo", "tendência", "historico", "histórico")):
        agrupamento = "tempo"
    elif any(k in msg_low for k in ("faixa de atraso", "por faixa", "idade da d", "tempo de atraso")):
        agrupamento = "faixa_atraso"
    elif any(k in msg_low for k in ("por vendedor", "por colaborador", "performance do vendedor", "comissão", "comissao", "comissões")):
        agrupamento = "vendedor"
    elif any(k in msg_low for k in ("por serviço", "por servico")):
        agrupamento = "servico"
    elif "por status" in msg_low:
        agrupamento = "status"
    elif "por categoria" in msg_low:
        agrupamento = "categoria"

    # métrica explícita
    metrica: str | None = None
    if "taxa de conversão" in msg_low or "taxa de conversao" in msg_low or "conversão" in msg_low:
        metrica = "taxa_conversao"
    elif "ticket médio" in msg_low or "ticket medio" in msg_low:
        metrica = "ticket_medio"
    elif "faturamento" in msg_low:
        metrica = "faturamento"
    elif "inativo" in msg_low:
        metrica = "inativos"
        dominio = "clientes"
    elif "despesa" in msg_low:
        metrica = "despesas"
        dominio = "financeiro"
    elif "quantidade" in msg_low or "mais vendid" in msg_low:
        metrica = "quantidade"
    elif "taxa de cancelamento" in msg_low or "cancelamento" in msg_low:
        metrica = "taxa_cancelamento"
    elif "total em aberto" in msg_low or "em aberto" in msg_low:
        metrica = "total_aberto"

    return dominio, periodo_dias, agrupamento, metrica


def _v2_format_relatorio_resumo(
    dominio: str,
    metricas: dict,
    periodo_label: str,
    rows: list,
    titulo: str = "",
) -> str:
    def _money(v):
        try:
            n = float(v or 0)
        except (TypeError, ValueError):
            return "R$ 0,00"
        return f"R$ {n:_.2f}".replace("_", "X").replace(".", ",").replace("X", ".")

    if dominio == "orcamentos":
        total = int(metricas.get("total_orcamentos") or metricas.get("total") or 0)
        aprovados = int(metricas.get("total_aprovados") or metricas.get("aprovados") or 0)
        taxa = metricas.get("taxa_conversao_pct") or metricas.get("taxa_conversao") or 0
        fat = metricas.get("total_faturado") or metricas.get("faturamento") or 0
        ticket = metricas.get("ticket_medio") or 0

        title_line = f"{titulo} — {periodo_label}." if titulo else f"Relatório de orçamentos — {periodo_label}."
        linhas = [title_line]
        
        titulo_low = title_line.lower()
        if "faturamento" in titulo_low:
            linhas.append(f"💰 Faturamento total: {_money(fat)}.")
            linhas.append(f"Aprovados: {aprovados} de {total} orçamentos | Ticket médio: {_money(ticket)}.")
        elif "convers" in titulo_low:
            linhas.append(f"📊 Taxa de conversão: {taxa}%.")
            linhas.append(f"Total: {total} orçamentos | Aprovados: {aprovados}.")
            linhas.append(f"Faturamento gerado: {_money(fat)} | Ticket médio: {_money(ticket)}.")
        else:
            linhas.append(f"Total: {total} | Aprovados: {aprovados} | Taxa de conversão: {taxa}%.")
            linhas.append(f"Faturamento: {_money(fat)} | Ticket médio: {_money(ticket)}.")

        return "\n".join(linhas)

    if dominio == "clientes":
        total_clientes = len(rows or [])
        return f"Ranking de clientes — {periodo_label}. {total_clientes} clientes no topo."

    if dominio == "financeiro":
        entradas = metricas.get("entradas") or metricas.get("total_entradas") or 0
        saidas = metricas.get("saidas") or metricas.get("total_saidas") or 0
        saldo = metricas.get("saldo") or (float(entradas or 0) - float(saidas or 0))
        return (
            f"Financeiro — {periodo_label}. "
            f"Entradas: {_money(entradas)} | Saídas: {_money(saidas)} | Saldo: {_money(saldo)}."
        )

    if dominio == "inadimplencia":
        total = int(metricas.get("total_clientes") or len(rows or []))
        valor = metricas.get("total_devido") or 0
        return f"Inadimplência — {total} clientes devendo {_money(valor)} ({periodo_label})."

    return f"Relatório de {dominio} — {periodo_label}. {len(rows or [])} itens."


async def _v2_parse_relatorio_params_semantico(mensagem: str, default_dominio: str, default_periodo: int) -> tuple[str, int, str | None, str | None]:
    """Usa LLM para extrair parâmetros de relatório quando o Regex falha em encontrar um agrupamento."""
    import os
    import json
    from litellm import acompletion
    from app.services.ia_service import logger
    
    try:
        model = os.getenv("AI_TECHNICAL_MODEL") or os.getenv("AI_MODEL") or "openrouter/google/gemini-2.5-flash"
        if os.getenv("AI_PROVIDER") == "openrouter" and not model.startswith("openrouter/"):
            model = f"openrouter/{model}"
            
        prompt = (
            f"Você é um extrator de parâmetros JSON. Analise a mensagem: '{mensagem}'\n"
            "Retorne APENAS um JSON válido com as seguintes chaves:\n"
            "- agrupamento (string): pode ser 'cliente' (para rankings, maiores, melhores, quem comprou mais), 'vendedor', 'servico', 'tempo', 'status', 'categoria' ou null se não houver.\n"
            "- metrica (string): 'taxa_conversao', 'ticket_medio', 'faturamento' ou null.\n"
            "Exemplo: {\"agrupamento\": \"cliente\", \"metrica\": null}\n"
            "Retorne apenas o JSON, sem markdown."
        )
        
        resp = await acompletion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=30
        )
        
        txt = resp.choices[0].message.content.strip()
        if txt.startswith("```json"): txt = txt[7:]
        if txt.startswith("```"): txt = txt[3:]
        if txt.endswith("```"): txt = txt[:-3]
        
        dados = json.loads(txt.strip())
        agrupamento = dados.get("agrupamento")
        metrica = dados.get("metrica")
        
        if agrupamento in ["null", "None", "", "none"]: agrupamento = None
        if metrica in ["null", "None", "", "none"]: metrica = None
        
        return default_dominio, default_periodo, agrupamento, metrica
    except Exception as e:
        logger.error(f"[Semantic Extract] Falhou: {e}")
        return default_dominio, default_periodo, None, None

async def _v2_build_relatorio_fastpath_response(
    *,
    mensagem: str,
    db: Session,
    current_user: Any,
    intent_str: str | None = None,
) -> AIResponse | None:
    from app.services.ai_tools.relatorio_tools import (
        GerarRelatorioDinamicoInput,
        _handler_gerar_relatorio_dinamico,
    )

    # 1. Tenta extrair por Regex
    dominio, periodo_dias, agrupamento, metrica = _v2_parse_relatorio_params(mensagem, intent_str=intent_str)
    
    # 2. Extrator Semântico se o Regex não achou agrupamento mas sabemos que é um relatório
    if not agrupamento:
        dominio, periodo_dias, agrupamento, metrica = await _v2_parse_relatorio_params_semantico(mensagem, dominio, periodo_dias)

    try:
        inp = GerarRelatorioDinamicoInput(
            dominio=dominio,
            periodo_dias=periodo_dias,
            agrupamento=agrupamento,
            metrica=metrica,
        )
        rel_data = await _handler_gerar_relatorio_dinamico(
            inp, db=db, current_user=current_user
        )
    except Exception as e:
        logger.error(f"Erro no fastpath de gerar relatório: {e}")
        return None

    if not isinstance(rel_data, dict) or rel_data.get("error"):
        logger.error(f"rel_data com erro: {rel_data.get('error') if isinstance(rel_data, dict) else 'not a dict'}")
        return None

    rows = list(rel_data.get("rows") or [])
    metricas_resumo = rel_data.get("metricas_resumo") or {}
    chart_spec = rel_data.get("chart_spec")
    titulo = rel_data.get("titulo") or "Relatório"
    subtitulo = rel_data.get("subtitulo") or ""
    periodo_label = rel_data.get("periodo_label") or f"Últimos {periodo_dias} dias"
    insights = list(rel_data.get("insights_base") or [])

    resumo = _v2_format_relatorio_resumo(dominio, metricas_resumo, periodo_label, rows, titulo=titulo)

    dados: dict[str, Any] = {
        "rows": rows,
        "titulo": titulo,
        "subtitulo": subtitulo,
        "periodo_label": periodo_label,
        "metricas_resumo": metricas_resumo,
        "insights_base": insights,
        "dominio": dominio,
        "grafico": chart_spec,
        "input_tokens": 0,
        "output_tokens": 0,
    }

    return AIResponse(
        sucesso=True,
        resposta=resumo,
        tipo_resposta="relatorio_dinamico",
        confianca=0.95,
        modulo_origem="assistente_v2",
        tool_trace=[{"tool": "gerar_relatorio_dinamico", "status": "ok", "latencia_ms": 0}],
        dados=dados,
    )


def _v2_is_relatorio_fastpath_message(mensagem: str) -> bool:
    return _v2_detect_deterministic_intent(mensagem) in _V2_RELATORIO_INTENTS


def _v2_apply_prompt_caching(messages: list[dict]) -> list[dict]:
    """Aplica Anthropic prompt caching no primeiro system message.

    Transforma `content: str` em `content: [{type: text, text, cache_control}]`.
    Só atua se o provider/model ativo for Anthropic/Claude — outros ignoram.
    """
    try:
        from app.services.ia_service import ia_service
        if not ia_service.supports_prompt_caching():
            return messages
    except Exception:
        return messages

    if not messages:
        return messages

    patched: list[dict] = []
    cached_once = False
    for msg in messages:
        if (
            not cached_once
            and isinstance(msg, dict)
            and msg.get("role") == "system"
            and isinstance(msg.get("content"), str)
            and len(msg["content"]) > 1024
        ):
            patched.append({
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": msg["content"],
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            })
            cached_once = True
        else:
            patched.append(msg)
    return patched


def _v2_prompt_strategy(mensagem: str, resolved_engine: str) -> str:
    if resolved_engine == ENGINE_INTERNAL_COPILOT:
        return "technical"

    deterministic_intent = _v2_detect_deterministic_intent(mensagem)
    normalized = _v2_normalize_bootstrap_message(mensagem)
    word_count = len((mensagem or "").split())

    if deterministic_intent in {"AJUDA_SISTEMA", "ONBOARDING"}:
        return "full_kb"
    if normalized and _V2_HELP_REQUEST_RE.search(normalized):
        return "full_kb"
    if deterministic_intent in _V2_MINIMAL_INTENTS and word_count <= 18:
        return "minimal"
    return "standard"


def _v2_build_system_prompt(
    *,
    mensagem: str,
    resolved_engine: str,
    now: str,
) -> tuple[str, str]:
    prompt_strategy = _v2_prompt_strategy(mensagem, resolved_engine)
    kb_snippet = _v2_load_kb_snippet() if prompt_strategy == "full_kb" else ""

    if resolved_engine == ENGINE_INTERNAL_COPILOT:
        system_prompt = f"{_V2_TECHNICAL_COPILOT_PROMPT}\n\nData/hora atual: {now}."
    else:
        base_prompt = (
            _V2_MINIMAL_SYSTEM_PROMPT
            if prompt_strategy == "minimal"
            else _V2_SYSTEM_PROMPT
        )
        system_prompt = f"{base_prompt}\n\nData/hora atual: {now}."
        system_prompt += _v2_prompt_listar_orcamentos_datas_br()

    system_prompt += "\n\n" + build_engine_guardrails(resolved_engine)
    if resolved_engine == ENGINE_INTERNAL_COPILOT:
        system_prompt += (
            "\n- Este canal e interno: nao responda operacoes de negocio de clientes, exceto consultas internas autorizadas para superadmin usando tools de leitura."
            "\n- Nao reutilize contexto de assistente operacional."
        )
    if kb_snippet:
        system_prompt += (
            "\n\n## Manual funcional do sistema (fonte de verdade para 'como fazer')\n"
            f"{kb_snippet}"
        )

    return system_prompt, prompt_strategy


def _v2_build_runtime_meta(
    *,
    prompt_strategy: str,
    resolved_engine: str,
    model_override: str | None = None,
) -> dict[str, Any]:
    effective_model = model_override or settings.AI_MODEL
    return {
        "prompt_strategy": prompt_strategy,
        "llm_gateway": "litellm",
        "llm_provider": settings.AI_PROVIDER,
        "llm_model": effective_model,
        "engine": resolved_engine,
    }


def _v2_persist_fastpath_response(
    *,
    sessao_id: str,
    db: Session,
    current_user: Any,
    resposta: str,
) -> None:
    from app.services.cotte_context_builder import SessionStore

    empresa_id = getattr(current_user, "empresa_id", 0)
    usuario_id = getattr(current_user, "id", 0)
    SessionStore.ensure_sessao_db(
        sessao_id=sessao_id,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        db=db,
    )
    if resposta:
        SessionStore.append_db(
            sessao_id,
            "assistant",
            resposta,
            db,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
        )


def _v2_update_operational_context_from_payload(
    *,
    sessao_id: str,
    db: Session,
    current_user: Any,
    payload: Optional[dict],
    engine: str = DEFAULT_ENGINE,
    intent: str = "CONVERSACAO",
) -> dict:
    from app.services.cotte_context_builder import SessionStore

    empresa_id = getattr(current_user, "empresa_id", 0)
    usuario_id = getattr(current_user, "id", 0)
    data = payload if isinstance(payload, dict) else {}
    patch: dict[str, Any] = {
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
        "rota_primaria": engine,
        "tipo_resposta_esperada": intent,
        "subagente_primario": engine if engine != DEFAULT_ENGINE else "assistente_v2",
        "objetivo_ativo": intent,
        "tipo_fluxo_ativo": engine,
    }

    if data.get("orcamento_id") or data.get("id"):
        patch["orcamento_id_ativo"] = data.get("orcamento_id") or data.get("id")
    if data.get("orcamento_numero") or data.get("numero"):
        patch["orcamento_numero_ativo"] = data.get("orcamento_numero") or data.get("numero")
    if data.get("cliente_id"):
        patch["cliente_id_ativo"] = data.get("cliente_id")
    if data.get("cliente_nome"):
        patch["cliente_nome_ativo"] = data.get("cliente_nome")
    if data.get("documento_id"):
        patch["documento_id_ativo"] = data.get("documento_id")
    if data.get("documento_titulo"):
        patch["documento_titulo_ativo"] = data.get("documento_titulo")
    if data.get("periodo"):
        patch["periodo_financeiro_ativo"] = data.get("periodo")
    if data.get("_tipo_resposta") == "orcamento_preview" and data.get("valor") and data.get("servico"):
        patch["orcamento_preview_ativo"] = {
            "cliente_nome": data.get("cliente_nome"),
            "cliente_id": data.get("cliente_id"),
            "servico": data.get("servico"),
            "valor": data.get("valor"),
            "desconto": data.get("desconto"),
            "desconto_tipo": data.get("desconto_tipo"),
            "observacoes": data.get("observacoes"),
        }
    if "followup_pendente" in data:
        patch["followup_pendente"] = data.get("followup_pendente")

    return SessionStore.set_operational_context(
        sessao_id,
        patch,
        db=db,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
    )


def _v2_get_operational_context(*, sessao_id: str, db: Session, current_user: Any) -> dict:
    from app.services.cotte_context_builder import SessionStore

    return SessionStore.get_operational_context(
        sessao_id,
        db=db,
        empresa_id=getattr(current_user, "empresa_id", 0),
        usuario_id=getattr(current_user, "id", 0),
    )


def _v2_attach_operational_context_to_response(
    *,
    sessao_id: str,
    db: Session,
    current_user: Any,
    response: AIResponse,
    engine: str = DEFAULT_ENGINE,
    intent: str = "CONVERSACAO",
) -> AIResponse:
    dados = dict(response.dados or {})
    ctx = _v2_update_operational_context_from_payload(
        sessao_id=sessao_id,
        db=db,
        current_user=current_user,
        payload={**dados, "_tipo_resposta": response.tipo_resposta},
        engine=engine,
        intent=intent,
    )

    dados["contexto_operacional"] = ctx
    try:
        from app.services.insight_engine import InsightEngine

        empresa_id_val = getattr(current_user, "empresa_id", 0)
        snapshot = {"orcamentos": [], "financeiro": {}}
        try:
            import asyncio
            if asyncio.iscoroutinefunction(InsightEngine.build_snapshot):
                import inspect
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    pass
                else:
                    snapshot = loop.run_until_complete(
                        InsightEngine.build_snapshot(db, empresa_id_val)
                    )
            else:
                snapshot = InsightEngine.build_snapshot(db, empresa_id_val)
        except Exception:
            snapshot = {"orcamentos": [], "financeiro": {}}

        insights = InsightEngine().build_for_empresa(
            empresa_id=empresa_id_val,
            contexto={
                "sessao_id": sessao_id,
                "usuario_id": getattr(current_user, "id", 0),
                "contexto_operacional": ctx,
            },
            snapshot=snapshot,
        )
        proativos = insights if isinstance(insights, list) else []
        existentes = dados.get("insights")
        dados["insights"] = ([*existentes, *proativos] if isinstance(existentes, list) else proativos)
    except Exception as exc:
        logger.warning("Falha ao gerar insights proativos no assistente v2: %s", exc)
    response.dados = dados
    return response


async def assistente_unificado_v2(
    *,
    mensagem: str,
    sessao_id: str,
    db: Session,
    current_user: Any,
    engine: str = DEFAULT_ENGINE,
    request_id: Optional[str] = None,
    confirmation_token: Optional[str] = None,
    override_args: Optional[dict] = None,
) -> AIResponse:
    """Wrapper para o fluxo V2 (não-stream)."""
    # Para o fluxo não-stream, podemos simplesmente consumir o gerador do core
    # e retornar apenas o evento is_final como AIResponse.
    
    final_resp = None
    async for event_str in assistente_v2_stream_core(
        mensagem=mensagem,
        sessao_id=sessao_id,
        db=db,
        current_user=current_user,
        engine=engine,
        request_id=request_id,
        confirmation_token=confirmation_token,
        override_args=override_args,
    ):
        if not event_str.startswith("data: "):
            continue
        try:
            data = json.loads(event_str[6:])
            if data.get("is_final"):
                meta = data.get("metadata") or {}
                # Reconstruir AIResponse a partir do metadata do evento final
                final_resp = AIResponse(
                    sucesso=True,
                    resposta=meta.get("final_text") or "",
                    tipo_resposta=meta.get("tipo_resposta"),
                    confianca=meta.get("confianca", 0.9),
                    modulo_origem=meta.get("modulo_origem", "assistente_v2"),
                    pending_action=meta.get("pending_action"),
                    tool_trace=meta.get("tool_trace"),
                    input_tokens=meta.get("input_tokens", 0),
                    output_tokens=meta.get("output_tokens", 0),
                    metrics=meta.get("metrics"),
                    dados=meta.get("dados"),
                    chart_data=meta.get("chart_data"),
                    table_data=meta.get("table_data"),
                    actions=meta.get("actions"),
                    form_schema=meta.get("form_schema"),
                    contexto_operacional=meta.get("contexto_operacional"),
                )
            elif data.get("error"):
                return AIResponse(
                    sucesso=False,
                    resposta=data.get("error"),
                    tipo_resposta="erro",
                    confianca=0.0,
                    modulo_origem="assistente_v2",
                    erros=[data.get("error")]
                )
        except Exception:
            continue
            
    if final_resp:
        return final_resp
        
    return AIResponse(
        sucesso=False,
        resposta="Não foi possível obter uma resposta do assistente.",
        tipo_resposta="erro",
        confianca=0.0,
        modulo_origem="assistente_v2",
    )


async def assistente_v2_stream_core(
    *,
    mensagem: str,
    sessao_id: str,
    db,
    current_user,
    engine: str = DEFAULT_ENGINE,
    request_id: str | None = None,
    confirmation_token: str | None = None,
    override_args: dict | None = None,
):
    """Núcleo do Tool Use v2 adaptado para SSE.

    Eventos emitidos (cada um como linha `data: <json>\\n\\n`):
    - {"phase": "thinking"}                      — antes do 1º LLM
    - {"phase": "tool_running", "tool": "X"}     — ao executar tool X
    - {"chunk": "texto..."}                      — token a token
    - {"is_final": true, "final_text": "...", "metadata": {...}}  — fim da resposta
    - {"error": "msg"}                           — erro grave
    """
    import asyncio
    from app.services.assistant_preferences_service import AssistantPreferencesService
    from app.services.cotte_context_builder import SessionStore, SemanticMemoryStore
    from app.services.ia_service import ia_service
    from app.services.tool_executor import execute as tool_execute

    try:
        from app.services.tool_executor import execute_pending
    except ImportError:
        execute_pending = None

    contexto_operacional = _v2_get_operational_context(
        sessao_id=sessao_id,
        db=db,
        current_user=current_user,
    )
    mensagem_resolvida = _v2_resolve_followup_confirmation_message(
        mensagem=mensagem,
        contexto_operacional=contexto_operacional,
    )
    if mensagem_resolvida:
        mensagem = mensagem_resolvida

    from app.services.ai_intention_classifier import detectar_intencao_assistente_async
    try:
        classificacao = await detectar_intencao_assistente_async(mensagem)
        intent_str = classificacao.intencao.value
    except Exception:
        intent_str = "CONVERSACAO"


    def _enc(d):
        return f"data: {json.dumps(d, ensure_ascii=False, default=str)}\n\n"

    def _to_semantic_chart(grafico: dict | None) -> dict | None:
        if not isinstance(grafico, dict):
            return None
        dados = grafico.get("dados") or {}
        if not isinstance(dados, dict):
            return None
        return {
            "type": grafico.get("tipo") or "bar",
            "labels": list(dados.get("labels") or []),
            "datasets": list(dados.get("datasets") or []),
        }

    def _build_semantic_contract(
        *,
        summary: str,
        table: list[dict] | None = None,
        chart: dict | None = None,
        printable: dict | None = None,
        metadata_extra: dict | None = None,
    ) -> dict:
        return {
            "summary": summary or "",
            "table": list(table or []),
            "chart": chart,
            "printable": printable,
            "metadata": metadata_extra or {},
        }

    async def _emit_fastpath_ai_response(ai_response: AIResponse):
        final_text = _derive_ai_response_display_text(ai_response)
        _v2_persist_fastpath_response(
            sessao_id=sessao_id,
            db=db,
            current_user=current_user,
            resposta=final_text,
        )
        dados_out = dict(ai_response.dados or {})
        contexto_operacional = _v2_update_operational_context_from_payload(
            sessao_id=sessao_id,
            db=db,
            current_user=current_user,
            payload={**dados_out, "_tipo_resposta": ai_response.tipo_resposta},
            engine=engine,
            intent=intent_str,
        )
        dados_out["contexto_operacional"] = contexto_operacional
        grafico_meta = dados_out.get("grafico")

        if ai_response.tipo_resposta == "relatorio_dinamico" and "semantic_contract" not in dados_out:
            dados_out["semantic_contract"] = _build_semantic_contract(
                summary=final_text,
                table=list(dados_out.get("rows") or []),
                chart=_to_semantic_chart(grafico_meta),
                printable={
                    "title": dados_out.get("titulo", "Relatório"),
                    "summary": final_text,
                    "rows": list(dados_out.get("rows") or []),
                    "force_printable": True,
                    "theme": {"variant": "professional", "accent_color": "#0f766e"},
                },
                metadata_extra={
                    "capability": "GenerateAnalyticsReport",
                    "domain": dados_out.get("dominio", "analytics"),
                    "period_days": (dados_out.get("metricas_resumo") or {}).get("periodo_dias"),
                    "tipo_resposta_inferida": "relatorio_dinamico",
                },
            )

        yield _enc({"phase": "thinking"})
        if final_text:
            yield _enc({"chunk": final_text})
        yield _enc(
            {
                "is_final": True,
                "final_text": final_text,
                "metadata": {
                    "final_text": final_text,
                    "tipo": ai_response.tipo_resposta or "geral",
                    "dados": dados_out,
                    "grafico": grafico_meta,
                    "pending_action": ai_response.pending_action,
                    "tool_trace": ai_response.tool_trace,
                    "input_tokens": 0,
                    "output_tokens": 0,
                },
            }
        )

    resolved_engine = resolve_engine(engine)
    engine_policy = get_engine_policy(resolved_engine)
    intent_detectada = _v2_detect_deterministic_intent(mensagem)

    if _v2_is_onboarding_bootstrap_message(mensagem):
        resposta, status = _v2_build_onboarding_fastpath_payload(
            db=db,
            empresa_id=getattr(current_user, "empresa_id", 0),
        )
        _v2_persist_fastpath_response(
            sessao_id=sessao_id,
            db=db,
            current_user=current_user,
            resposta=resposta,
        )
        yield _enc({"phase": "thinking"})
        yield _enc({"chunk": resposta})
        yield _enc(
            {
                "is_final": True,
                "final_text": resposta,
                "metadata": {
                    "final_text": resposta,
                    "tipo": "onboarding",
                    "dados": status,
                    "input_tokens": 0,
                    "output_tokens": 0,
                },
            }
        )
        return

    if intent_str == "SALDO_RAPIDO":
        resposta = await _v2_build_saldo_fastpath_response(
            db=db,
            empresa_id=getattr(current_user, "empresa_id", 0),
        )
        async for event in _emit_fastpath_ai_response(resposta):
            yield event
        return

    if intent_str == "FATURAMENTO":
        # Check if it is a simple request for "this month" or similar
        # If it has complex grouping, fallback to dynamic report
        msg_low = mensagem.lower()
        if not any(k in msg_low for k in ("por cliente", "por vendedor", "por serviço", "por status", "ranking")):
            resposta = await faturamento_ia(db=db, empresa_id=getattr(current_user, "empresa_id", 0))
            async for event in _emit_fastpath_ai_response(resposta):
                yield event
            return

    if intent_str == "CONTAS_RECEBER":
        resposta = await contas_receber_ia(db=db, empresa_id=getattr(current_user, "empresa_id", 0))
        async for event in _emit_fastpath_ai_response(resposta):
            yield event
        return

    if intent_str == "CONTAS_PAGAR":
        resposta = await contas_pagar_ia(db=db, empresa_id=getattr(current_user, "empresa_id", 0))
        async for event in _emit_fastpath_ai_response(resposta):
            yield event
        return

    if intent_str == "CRIAR_ORCAMENTO":
        resposta = await _v2_build_orcamento_fastpath_response(
            mensagem=mensagem,
            db=db,
            empresa_id=getattr(current_user, "empresa_id", 0),
            usuario_id=getattr(current_user, "id", 0),
        )
        async for event in _emit_fastpath_ai_response(resposta):
            yield event
        return

    if intent_str in _V2_RELATORIO_INTENTS:
        resposta_rel = await _v2_build_relatorio_fastpath_response(
            mensagem=mensagem,
            db=db,
            current_user=current_user,
            intent_str=intent_str,
        )
        if resposta_rel is not None:
            async for event in _emit_fastpath_ai_response(resposta_rel):
                yield event
            return

    if _v2_is_orcamento_context_followup_message(mensagem):
        resposta_ctx_orc = await _v2_build_orcamento_context_followup_response(
            mensagem=mensagem,
            sessao_id=sessao_id,
            db=db,
            current_user=current_user,
            request_id=request_id,
        )
        if resposta_ctx_orc is not None:
            async for event in _emit_fastpath_ai_response(resposta_ctx_orc):
                yield event
            return
        # Fast path reconheceu consulta de orçamento mas não há contexto ativo.
        # Força OPERADOR para o LLM usar ferramentas de orçamento em vez de cair
        # no fluxo CONVERSACAO que inclui obter_saldo_caixa e retornaria o caixa.
        if intent_str == "CONVERSACAO":
            intent_str = "OPERADOR"

    if intent_str == "LISTAR_ORCAMENTOS":
        resposta_lista = await _v2_build_listar_orcamentos_fastpath_response(
            mensagem=mensagem,
            db=db,
            current_user=current_user,
        )
        if resposta_lista is not None:
            async for event in _emit_fastpath_ai_response(resposta_lista):
                yield event
            return

    if intent_str == "LISTAR_CLIENTES":
        resposta_lista = await _v2_build_listar_clientes_fastpath_response(
            mensagem=mensagem,
            db=db,
            current_user=current_user,
        )
        if resposta_lista is not None:
            async for event in _emit_fastpath_ai_response(resposta_lista):
                yield event
            return

    if _v2_is_excel_chart_request(mensagem):
        final_text = (
            "Hoje eu não gero arquivo Excel diretamente pelo chat. "
            "Consigo te entregar os dados e o gráfico financeiro aqui no assistente, "
            "e você exporta para planilha com segurança."
        )
        SessionStore.append_db(
            sessao_id,
            "assistant",
            final_text,
            db,
            empresa_id=getattr(current_user, "empresa_id", 0),
            usuario_id=getattr(current_user, "id", 0),
        )
        yield _enc({"phase": "thinking"})
        yield _enc({"chunk": final_text})
        yield _enc(
            {
                "is_final": True,
                "final_text": final_text,
                "metadata": {
                    "final_text": final_text,
                    "dados": {
                        "capability": "excel_nao_suportado",
                        "semantic_contract": _build_semantic_contract(
                            summary=final_text,
                            metadata_extra={"capability": "excel_nao_suportado"},
                        ),
                    },
                    "tipo": "geral",
                },
            }
        )
        return

    if _v2_is_financial_chart_request(mensagem):
        from app.services.tool_executor import execute as _tool_exec

        dias = _v2_extract_days_window(mensagem)
        yield _enc({"phase": "thinking"})
        yield _enc(
            {"phase": "tool_running", "tool": "listar_movimentacoes_financeiras"}
        )
        tc_mov = {
            "id": "chart_movs",
            "type": "function",
            "function": {
                "name": "listar_movimentacoes_financeiras",
                "arguments": json.dumps(
                    {"dias": dias, "limit": 100}, ensure_ascii=False
                ),
            },
        }
        res_mov = await _tool_exec(
            tc_mov,
            db=db,
            current_user=current_user,
            sessao_id=sessao_id,
            confirmation_token=None,
        )
        yield _enc({"phase": "tool_running", "tool": "obter_saldo_caixa"})
        tc_saldo = {
            "id": "chart_saldo",
            "type": "function",
            "function": {"name": "obter_saldo_caixa", "arguments": "{}"},
        }
        res_saldo = await _tool_exec(
            tc_saldo,
            db=db,
            current_user=current_user,
            sessao_id=sessao_id,
            confirmation_token=None,
        )

        movs = (
            (res_mov.data or {}).get("movimentacoes", [])
            if res_mov.status == "ok"
            else []
        )
        grafico = _v2_build_financial_chart_payload(movs)
        saldo_atual = (
            (res_saldo.data or {}).get("saldo_atual")
            if res_saldo.status == "ok"
            else None
        )
        qtd = len(movs)
        if grafico:
            final_text = (
                f"Aqui está o gráfico financeiro dos últimos {dias} dias "
                f"(com {qtd} movimentações)."
            )
            if saldo_atual is not None:
                final_text += f" Saldo atual: R$ {float(saldo_atual):,.2f}."
        else:
            final_text = f"Não encontrei movimentações suficientes para montar o gráfico dos últimos {dias} dias."
        SessionStore.append_db(
            sessao_id,
            "assistant",
            final_text,
            db,
            empresa_id=getattr(current_user, "empresa_id", 0),
            usuario_id=getattr(current_user, "id", 0),
        )
        yield _enc({"chunk": final_text})
        yield _enc(
            {
                "is_final": True,
                "final_text": final_text,
                "metadata": {
                    "final_text": final_text,
                    "tipo": "financeiro",
                    "dados": {
                        "dias": dias,
                        "movimentacoes_total": qtd,
                        "saldo_atual": saldo_atual,
                        "semantic_contract": _build_semantic_contract(
                            summary=final_text,
                            table=[
                                {
                                    "data": mov.get("data"),
                                    "descricao": mov.get("descricao"),
                                    "tipo": mov.get("tipo"),
                                    "valor": mov.get("valor"),
                                }
                                for mov in list(movs or [])[:100]
                                if isinstance(mov, dict)
                            ],
                            chart=_to_semantic_chart(grafico),
                            printable={
                                "title": f"Resumo financeiro ({dias} dias)",
                                "summary": final_text,
                            },
                            metadata_extra={
                                "capability": "GenerateAnalyticsReport",
                                "domain": "analytics",
                                "period_days": dias,
                            },
                        ),
                    },
                    "grafico": grafico,
                    "tool_trace": [
                        {
                            "tool": "listar_movimentacoes_financeiras",
                            "status": res_mov.status,
                            "latencia_ms": res_mov.latencia_ms,
                        },
                        {
                            "tool": "obter_saldo_caixa",
                            "status": res_saldo.status,
                            "latencia_ms": res_saldo.latencia_ms,
                        },
                    ],
                },
            }
        )
        return

    # ── Fast-path: confirmação de ação pendente ────────────────────────────
    if confirmation_token and execute_pending:
        yield _enc({"phase": "thinking"})
        try:
            result = await execute_pending(
                confirmation_token,
                db=db,
                current_user=current_user,
                sessao_id=sessao_id,
                request_id=request_id,
                override_args=override_args or {},
                engine=engine,
            )
        except Exception as exc:
            logger.exception("[stream_v2] Erro no fast-path de confirmação")
            yield _enc({"error": str(exc)})
            return

        orc_data = result.data or {} if hasattr(result, "data") else {}
        status = result.status if hasattr(result, "status") else "ok"
        if status == "ok" and orc_data.get("numero"):
            _tool_exec = getattr(result, "tool_name", None)
            if _tool_exec == "editar_orcamento":
                final_text = "✅ Orçamento atualizado com sucesso."
                tipo_resp = "orcamento_atualizado"
            elif _tool_exec == "aprovar_orcamento":
                final_text = "✅ Orçamento aprovado com sucesso."
                tipo_resp = "orcamento_aprovado"
            elif _tool_exec == "recusar_orcamento":
                final_text = "✅ Orçamento recusado com sucesso."
                tipo_resp = "orcamento_recusado"
            else:
                final_text = "✅ Ação concluída com sucesso."
                tipo_resp = "orcamento_criado"
            sugs = [
                f"Ver {orc_data['numero']}",
                f"Enviar {orc_data['numero']} por WhatsApp",
            ]
            resp_dados = orc_data
        elif status == "forbidden":
            final_text = "❌ Sem permissão para esta ação."
            tipo_resp = None
            sugs = []
            resp_dados = {}
        else:
            final_text = (
                f"❌ Não foi possível concluir: {getattr(result, 'error', status)}"
            )
            tipo_resp = None
            sugs = []
            resp_dados = {}

        tool_trace_fpath = [{"tool": "(confirmação)", "status": status}]
        for word in final_text.split(" "):
            yield _enc({"chunk": word + " "})
        SessionStore.append_db(
            sessao_id,
            "assistant",
            final_text,
            db,
            empresa_id=getattr(current_user, "empresa_id", 0),
            usuario_id=getattr(current_user, "id", 0),
        )
        yield _enc(
            {
                "is_final": True,
                "final_text": final_text,
                "metadata": {
                    "final_text": final_text,
                    "tipo": tipo_resp,
                    "dados": {
                        **resp_dados,
                        "semantic_contract": _build_semantic_contract(
                            summary=final_text,
                            table=[resp_dados]
                            if isinstance(resp_dados, dict) and resp_dados
                            else [],
                            printable={
                                "title": "Resultado de ação confirmada",
                                "summary": final_text,
                            },
                            metadata_extra={
                                "capability": "PrepareQuotePackage",
                                "domain": "quote_ops",
                            },
                        ),
                    },
                    "tool_trace": tool_trace_fpath,
                    "sugestoes": sugs,
                    "pending_action": None,
                },
            }
        )
        return

    # ── Fast-path: simular desconto (0 tokens LLM) ───────────────────────────
    if not confirmation_token and _v2_is_simular_desconto_message(mensagem):
        resposta_sim = await _v2_build_simular_desconto_response(
            mensagem=mensagem,
            db=db,
            current_user=current_user,
            request_id=request_id,
        )
        if resposta_sim is not None:
            async for event in _emit_fastpath_ai_response(resposta_sim):
                yield event
            return

    # ── Fast-path: operador (aprovar/recusar/ver/enviar com ID explícito) ────
    if not confirmation_token and _v2_is_operador_fastpath_message(mensagem):
        resposta_op = await _v2_build_operador_fastpath_response(
            mensagem=mensagem,
            db=db,
            current_user=current_user,
            sessao_id=sessao_id,
            request_id=request_id,
        )
        if resposta_op is not None:
            if resposta_op.pending_action:
                tool_name_op = (resposta_op.pending_action or {}).get("tool", "?")
                yield _enc({"phase": "thinking"})
                yield _enc({"phase": "tool_running", "tool": tool_name_op})
                yield _enc({
                    "is_final": True,
                    "final_text": "",
                    "metadata": {
                        "final_text": "",
                        "tipo": "operador_action",
                        "dados": resposta_op.dados or {},
                        "tool_trace": resposta_op.tool_trace or [],
                        "sugestoes": [],
                        "pending_action": resposta_op.pending_action,
                        "input_tokens": 0,
                        "output_tokens": 0,
                    },
                })
            else:
                async for event in _emit_fastpath_ai_response(resposta_op):
                    yield event
            return

    # ── Fluxo normal: loop Tool Use v2 ────────────────────────────────────
    yield _enc({"phase": "thinking"})

    agora = datetime.now(_TZ_BR).strftime("%Y-%m-%d %H:%M")
    empresa_id = getattr(current_user, "empresa_id", 0)
    usuario_id = getattr(current_user, "id", 0)

    SessionStore.ensure_sessao_db(
        sessao_id=sessao_id,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        db=db,
    )
    history = SessionStore.get_or_create(
        sessao_id,
        db=db,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
    )
    SessionStore.append_db(
        sessao_id,
        "user",
        mensagem,
        db,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
    )

    system_prompt, prompt_strategy = _v2_build_system_prompt(
        mensagem=mensagem,
        resolved_engine=resolved_engine,
        now=agora,
    )
    allow_context_enrichment = prompt_strategy != "minimal"

    semantic_ctx = {}
    rag_ctx = {}
    adaptive_ctx = {}
    if engine_policy.allow_business_context and allow_context_enrichment:
        semantic_ctx = SemanticMemoryStore.build_context(
            db=db,
            empresa_id=getattr(current_user, "empresa_id", 0),
            mensagem=mensagem,
            usuario_id=getattr(current_user, "id", 0),
        )
        adaptive_ctx = AssistantPreferencesService.get_context_for_prompt(
            db=db,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            mensagem=mensagem,
        )
    if engine_policy.allow_tenant_rag and allow_context_enrichment:
        try:
            from app.services.rag import TenantRAGService

            rag_ctx = TenantRAGService.build_prompt_context(
                db=db,
                empresa_id=empresa_id,
                query=mensagem,
                top_k=4,
            )
        except Exception:
            rag_ctx = {}
    code_ctx = {}
    if (
        resolved_engine == ENGINE_INTERNAL_COPILOT
        and is_code_rag_enabled()
        and allow_context_enrichment
    ):
        try:
            from app.services.code_rag_service import build_code_context

            code_ctx = build_code_context(query=mensagem, top_k=4)
        except Exception:
            code_ctx = {}
    runtime_meta = _v2_build_runtime_meta(
        prompt_strategy=prompt_strategy,
        resolved_engine=resolved_engine,
        model_override=(
            settings.AI_TECHNICAL_MODEL
            if resolved_engine == ENGINE_INTERNAL_COPILOT
            else None
        ),
    )
    adaptive_meta = {
        **runtime_meta,
        "intent_detectada": intent_detectada,
        "visualizacao_recomendada": adaptive_ctx.get("preferencia_visualizacao_usuario")
        or {},
        "playbook_setor": adaptive_ctx.get("playbook_setor") or {},
    }

    if adaptive_ctx:
        _modulos = adaptive_ctx.get("modulos_ativos") or {}
        _nomes_modulos = {
            "clientes": "Clientes",
            "financeiro": "Financeiro",
            "catalogo": "Catálogo de Serviços",
            "orcamentos": "Orçamentos",
        }
        _linhas_modulos = [
            f"- {label}: {'habilitado' if _modulos.get(key, True) else 'DESABILITADO pelo usuário'}"
            for key, label in _nomes_modulos.items()
        ]
        system_prompt += (
            "\n\n## Módulos com acesso autorizado pelo usuário\n"
            + "\n".join(_linhas_modulos)
            + "\nRespeite estritamente: não busque, exiba nem infira dados de módulos DESABILITADOS."
        )

    messages: list[dict] = [
        {
            "role": "system",
            "content": system_prompt,
        },
    ]
    if semantic_ctx:
        messages.append(
            {
                "role": "system",
                "content": (
                    "## Memória semântica da empresa (use para reduzir repetição e aumentar precisão)\n"
                    + json.dumps(semantic_ctx, ensure_ascii=False, default=str)
                ),
            }
        )
    if rag_ctx and rag_ctx.get("context"):
        messages.append(
            {
                "role": "system",
                "content": (
                    "## Contexto RAG por tenant (usar somente como apoio factual)\n"
                    f"Fontes: {', '.join(rag_ctx.get('sources') or [])}\n\n"
                    + (rag_ctx.get("context") or "")
                ),
            }
        )
    if code_ctx and code_ctx.get("context"):
        messages.append(
            {
                "role": "system",
                "content": (
                    "## Code RAG técnico interno (usar apenas para suporte técnico interno)\n"
                    f"Fontes: {', '.join(code_ctx.get('sources') or [])}\n\n"
                    + (code_ctx.get("context") or "")
                ),
            }
        )
    _instrucoes_empresa = (adaptive_ctx or {}).get("instrucoes_empresa", "")
    if _instrucoes_empresa:
        messages.append(
            {
                "role": "system",
                "content": (
                    "## GUARDRAILS OBRIGATÓRIOS DA EMPRESA (aplicar em TODA resposta, sem exceção)\n"
                    + _instrucoes_empresa
                ),
            }
        )
    if adaptive_ctx:
        messages.append(
            {
                "role": "system",
                "content": (
                    "## Preferências adaptativas da empresa/usuário (aplicar por contexto)\n"
                    + json.dumps(adaptive_ctx, ensure_ascii=False, default=str)
                ),
            }
        )
    history_window = _v2_history_window_size(
        prompt_strategy=prompt_strategy,
        mensagem=mensagem,
    )
    for h in (history or [])[-history_window:]:
        role = h.get("role") if isinstance(h, dict) else getattr(h, "role", None)
        content = (
            h.get("content") if isinstance(h, dict) else getattr(h, "content", None)
        )
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": mensagem})
    logger.info(
        "[stream_v2] engine=%s prompt_strategy=%s system_chars=%s history=%s",
        resolved_engine,
        prompt_strategy,
        len(system_prompt),
        history_window,
    )

    tools_payload, full_tools_payload, reduced_tools_active, tool_profile = (
        _v2_select_tools_payload(
            mensagem=mensagem,
            prompt_strategy=prompt_strategy,
            resolved_engine=resolved_engine,
        )
    )
    adaptive_meta["tool_profile"] = tool_profile
    adaptive_meta["tool_count"] = len(tools_payload)
    adaptive_meta["tool_count_full"] = len(full_tools_payload)
    flow_started_perf = time.perf_counter()
    tool_trace: list[dict] = []

    pending_action: Optional[dict] = None
    total_in = 0
    total_out = 0
    final_text: Optional[str] = None
    final_tipo_resposta: Optional[str] = None
    final_interactive_payload: Optional[dict] = None
    expanded_tools_once = False

    modelo_injetado = (
        settings.AI_TECHNICAL_MODEL
        if resolved_engine == ENGINE_INTERNAL_COPILOT
        else None
    )

    for _iter in range(_V2_MAX_ITER):
        # Proteção: budget máximo de tokens
        if total_in > 15000:
            logger.warning("[v2_core] Token budget excedido (total_in=%s).", total_in)
            yield _enc({
                "error": "A consulta exigiu volume de dados além do limite seguro. Seja mais específico.",
                "phase": "error"
            })
            return

        try:
            resp = await ia_service.chat(
                messages=_v2_apply_prompt_caching(messages),
                tools=tools_payload,
                temperature=0.3,
                max_tokens=1024,
                model_override=modelo_injetado,
            )
        except Exception as e:
            logger.exception("Falha na chamada ia_service.chat (v2)")
            yield _enc({
                "error": f"Erro ao consultar assistente: {e}",
                "phase": "error"
            })
            return

        usage = (
            resp.get("usage", {})
            if isinstance(resp, dict)
            else getattr(resp, "usage", {}) or {}
        )
        try:
            total_in += int(usage.get("prompt_tokens", 0) or 0)
            total_out += int(usage.get("completion_tokens", 0) or 0)
        except Exception:
            pass

        choices = (
            resp.get("choices")
            if isinstance(resp, dict)
            else getattr(resp, "choices", None)
        )
        if not choices:
            break
        choice = choices[0]
        msg = (
            choice.get("message")
            if isinstance(choice, dict)
            else getattr(choice, "message", None)
        )
        finish = (
            choice.get("finish_reason")
            if isinstance(choice, dict)
            else getattr(choice, "finish_reason", None)
        )

        # Extrair tool_calls
        tool_calls = None
        if msg is not None:
            tool_calls = (
                msg.get("tool_calls")
                if isinstance(msg, dict)
                else getattr(msg, "tool_calls", None)
            )
        if not tool_calls and not expanded_tools_once:
            candidate_text = (
                msg.get("content")
                if isinstance(msg, dict)
                else getattr(msg, "content", None)
            ) or ""
            if _v2_should_retry_with_full_tools(
                mensagem=mensagem,
                candidate_text=candidate_text,
                reduced_tools_active=reduced_tools_active,
            ):
                expanded_tools_once = True

                if total_in > 10000:
                    logger.warning(
                        "[v2_core] Blocking retry with full tools due to token budget (total_in=%s)",
                        total_in,
                    )
                else:
                    try:
                        resp_retry = await ia_service.chat(
                            messages=_v2_apply_prompt_caching(messages),
                            tools=full_tools_payload,
                            temperature=0.3,
                            max_tokens=1024,
                            model_override=modelo_injetado,
                        )
                        usage_retry = (
                            resp_retry.get("usage", {})
                            if isinstance(resp_retry, dict)
                            else getattr(resp_retry, "usage", {}) or {}
                        )
                        total_in += int(usage_retry.get("prompt_tokens", 0) or 0)
                        total_out += int(usage_retry.get("completion_tokens", 0) or 0)
                        choices_retry = (
                            resp_retry.get("choices")
                            if isinstance(resp_retry, dict)
                            else getattr(resp_retry, "choices", None)
                        )
                        if choices_retry:
                            choice = choices_retry[0]
                            msg = (
                                choice.get("message")
                                if isinstance(choice, dict)
                                else getattr(choice, "message", None)
                            )
                            finish = (
                                choice.get("finish_reason")
                                if isinstance(choice, dict)
                                else getattr(choice, "finish_reason", None)
                            )
                            tool_calls = (
                                msg.get("tool_calls")
                                if isinstance(msg, dict)
                                else getattr(msg, "tool_calls", None)
                            )
                            tools_payload = full_tools_payload
                            reduced_tools_active = False
                            adaptive_meta["tool_profile"] = "fallback_expanded_full"
                            adaptive_meta["tool_count"] = len(tools_payload)
                    except Exception:
                        logger.exception(
                            "Falha ao aplicar fallback para tools completas (v2)"
                        )

        if tool_calls:
            # Anexa o assistant turn com tool_calls (preservando ids)
            assistant_msg = {
                "role": "assistant",
                "content": (
                    msg.get("content")
                    if isinstance(msg, dict)
                    else getattr(msg, "content", None)
                )
                or "",
                "tool_calls": [
                    {
                        "id": (
                            tc.get("id")
                            if isinstance(tc, dict)
                            else getattr(tc, "id", None)
                        ),
                        "type": "function",
                        "function": {
                            "name": (
                                (
                                    tc.get("function", {})
                                    if isinstance(tc, dict)
                                    else getattr(tc, "function", None)
                                ).get("name")
                                if isinstance(tc, dict)
                                else getattr(
                                    getattr(tc, "function", None), "name", None
                                )
                            ),
                            "arguments": (
                                (
                                    tc.get("function", {})
                                    if isinstance(tc, dict)
                                    else getattr(tc, "function", None)
                                ).get("arguments")
                                if isinstance(tc, dict)
                                else getattr(
                                    getattr(tc, "function", None), "arguments", None
                                )
                            ),
                        },
                    }
                    for tc in tool_calls
                ],
            }
            messages.append(assistant_msg)

            for tc in tool_calls:
                tc_dict = (
                    tc
                    if isinstance(tc, dict)
                    else {
                        "id": getattr(tc, "id", None),
                        "function": {
                            "name": getattr(
                                getattr(tc, "function", None), "name", None
                            ),
                            "arguments": getattr(
                                getattr(tc, "function", None), "arguments", None
                            ),
                        },
                    }
                )
                result = await tool_execute(
                    tc_dict,
                    db=db,
                    current_user=current_user,
                    sessao_id=sessao_id,
                    request_id=request_id,
                    confirmation_token=confirmation_token,
                    engine=resolved_engine,
                )
                result = await _autopaginate_tool_result(
                    mensagem=mensagem,
                    tc=tc_dict,
                    result=result,
                    tool_execute=tool_execute,
                    db=db,
                    current_user=current_user,
                    sessao_id=sessao_id,
                    request_id=request_id,
                    confirmation_token=confirmation_token,
                    engine=resolved_engine,
                )
                t_status = result.status
                t_code = result.code
                t_error = result.error
                tool_trace.append(
                    {
                        "tool": (tc_dict.get("function") or {}).get("name"),
                        "status": t_status,
                        "latencia_ms": result.latencia_ms,
                        "code": t_code,
                        "reason": _tool_trace_reason(
                            status=t_status,
                            code=t_code,
                            error=t_error,
                        ),
                    }
                )
                payload = result.to_llm_payload()
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc_dict.get("id"),
                        "content": json.dumps(payload, ensure_ascii=False, default=str),
                    }
                )
                if result.status == "pending":
                    pending_action = result.pending_action
                    if isinstance(pending_action, dict) and not pending_action.get("extras"):
                        try:
                            from app.services.ai_tools.destructive_preview import (
                                build_destructive_extras,
                            )

                            pending_action["extras"] = await build_destructive_extras(
                                (pending_action.get("tool") or ""),
                                pending_action.get("args") or {},
                                db=db,
                                current_user=current_user,
                            )
                        except Exception:
                            logger.debug(
                                "Falha ao recomputar extras da ação pendente tool=%s",
                                pending_action.get("tool"),
                                exc_info=True,
                            )

            if pending_action:
                final_text = ""
                break
            # Próxima iteração: LLM verá os tool results
            continue

        # Sem tool_calls → resposta final
        raw_final_text = (
            msg.get("content")
            if isinstance(msg, dict)
            else getattr(msg, "content", None)
        ) or ""
        interactive_payload = _extract_interactive_ai_payload(raw_final_text)
        if interactive_payload:
            final_interactive_payload = interactive_payload
            final_tipo_resposta = interactive_payload.get("tipo") or final_tipo_resposta
            final_text = (
                interactive_payload.get("resposta")
                or interactive_payload.get("message")
                or interactive_payload.get("summary")
                or interactive_payload.get("resumo")
                or raw_final_text
            )
        else:
            final_text = raw_final_text
        if finish and finish != "stop" and finish != "tool_calls":
            logger.info("v2 finish_reason inesperado: %s", finish)
        break
    else:
        final_text = "Limite de iterações de ferramentas atingido. Refine a pergunta."

    if final_text:
        # Persiste resposta do assistente no banco
        SessionStore.append_db(
            sessao_id,
            "assistant",
            final_text,
            db,
            empresa_id=getattr(current_user, "empresa_id", 0),
            usuario_id=getattr(current_user, "id", 0),
        )

    if pending_action:
        dados_out = {
            **(pending_action.get("args") or {}),
            **(pending_action.get("extras") or {}),
            "input_tokens": total_in,
            "output_tokens": total_out,
            **adaptive_meta,
        }
    else:
        dados_out = {
            "input_tokens": total_in,
            "output_tokens": total_out,
            **adaptive_meta,
        }

    if isinstance(final_interactive_payload, dict):
        llm_dados = final_interactive_payload.get("dados")
        if isinstance(llm_dados, dict):
            dados_out = {**llm_dados, **dados_out}

    followup_pendente = _v2_extract_pending_followup_from_assistant_text(final_text or "")

    # Atualiza contexto operacional
    ctx = _v2_update_operational_context_from_payload(
        sessao_id=sessao_id,
        db=db,
        current_user=current_user,
        payload={**dados_out, "_tipo_resposta": final_tipo_resposta},
        engine=resolved_engine,
        intent=intent_label,
    )

    if final_text:
        yield _enc({"chunk": final_text})

    yield _enc(
        {
            "is_final": True,
            "final_text": final_text or "",
            "metadata": {
                "final_text": final_text or "",
                "tipo_resposta": final_tipo_resposta,
                "confianca": 0.9 if final_text else 0.4,
                "modulo_origem": "assistente_v2",
                "pending_action": pending_action,
                "tool_trace": tool_trace or None,
                "input_tokens": total_in,
                "output_tokens": total_out,
                "metrics": {
                    "tokens_in": total_in,
                    "tokens_out": total_out,
                    "iterations": _iter + 1,
                    "engine": resolved_engine,
                    "has_pending": bool(pending_action),
                    "tool_calls": len(tool_trace) if tool_trace else 0,
                    "total_duration_ms": int((time.perf_counter() - flow_started_perf) * 1000),
                    "steps_with_error": sum(1 for step in tool_trace if str(step.get("status")).lower() in {"erro", "error"})
                },
                "dados": {
                    **dados_out,
                    "followup_pendente": followup_pendente,
                    "contexto_operacional": ctx,
                },
                "contexto_operacional": ctx,
                "chart_data": (final_interactive_payload or {}).get("chart_data") if final_interactive_payload else None,
                "table_data": (final_interactive_payload or {}).get("table_data") if final_interactive_payload else None,
                "actions": (final_interactive_payload or {}).get("actions") if final_interactive_payload else None,
                "form_schema": (final_interactive_payload or {}).get("form_schema") if final_interactive_payload else None,
            },
        }
    )
    return
