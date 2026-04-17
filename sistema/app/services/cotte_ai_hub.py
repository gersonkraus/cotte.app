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
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Optional, Any, Literal

_TZ_BR = ZoneInfo("America/Sao_Paulo")
from functools import wraps
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from sqlalchemy.future import select
from pydantic import BaseModel, Field, validator

from app.core.config import settings

# Importar novos módulos refatorados
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

    class Config:
        json_schema_extra = {
            "example": {
                "sucesso": True,
                "dados": {"cliente_nome": "João", "valor": 500.0},
                "confianca": 0.92,
                "modulo_origem": "orcamentos",
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
    def extrair_comando(mensagem: str) -> dict:
        """Extrai comando de operador usando padrões"""
        resultado = {"acao": "DESCONHECIDO", "orcamento_id": None}

        # Identificar ação
        acoes = {
            r"\b(ver|mostrar?|exibir)\b": "VER",
            r"\b(aprovar?|aceitar)\b": "APROVAR",
            r"\b(recusar?|rejeitar|negar)\b": "RECUSAR",
            r"\b(enviar?|mandar|envia)\b": "ENVIAR",
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
            r"(?:O-|ORC-|orçamento\s*|orc\s*)(\d+)", mensagem, re.IGNORECASE
        )
        if match:
            resultado["orcamento_id"] = int(match.group(1))
        else:
            nums = re.findall(r"\d+", mensagem)
            if nums:
                resultado["orcamento_id"] = int(nums[-1])

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

        sugestoes = await buscar_sugestoes_catalogo(db, empresa_id, preview["servico"])
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
        return AIResponse(
            sucesso=True,
            resposta=resposta,
            tipo_resposta="onboarding",
            dados=status,
            confianca=1.0,
            modulo_origem="onboarding",
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

        response = await ia_service.chat(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_ASSISTENTE},
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


def _v2_is_dashboard_financeiro_message(mensagem: str) -> bool:
    return _v2_detect_deterministic_intent(mensagem) == "DASHBOARD"


def _v2_is_clientes_devendo_message(mensagem: str) -> bool:
    return _v2_detect_deterministic_intent(mensagem) == "INADIMPLENCIA"


def _v2_is_orcamento_fastpath_message(mensagem: str) -> bool:
    return _v2_detect_deterministic_intent(mensagem) == "CRIAR_ORCAMENTO"


def _v2_is_operador_fastpath_message(mensagem: str) -> bool:
    """True se OPERADOR com ação + ID de orçamento claramente parseáveis (0 tokens LLM)."""
    if _v2_detect_deterministic_intent(mensagem) != "OPERADOR":
        return False
    cmd = FallbackManual.extrair_comando(mensagem)
    return (
        cmd.get("acao") in {"APROVAR", "RECUSAR", "VER", "ENVIAR"}
        and cmd.get("orcamento_id") is not None
    )


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

    cmd = FallbackManual.extrair_comando(mensagem)
    acao = cmd.get("acao")
    orcamento_id = cmd.get("orcamento_id")
    if not orcamento_id:
        return None

    tool_map: dict[str, tuple[str, dict]] = {
        "VER":     ("obter_orcamento",          {"orcamento_id": orcamento_id}),
        "APROVAR": ("aprovar_orcamento",         {"orcamento_id": orcamento_id}),
        "RECUSAR": ("recusar_orcamento",         {"orcamento_id": orcamento_id}),
        "ENVIAR":  ("enviar_orcamento_whatsapp", {"orcamento_id": orcamento_id}),
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
        return AIResponse(
            sucesso=True,
            resposta="",
            tipo_resposta="operador_action",
            confianca=0.95,
            modulo_origem="assistente_v2",
            pending_action=result.pending_action,
            tool_trace=[{
                "tool": tool_name,
                "status": "pending",
                "latencia_ms": result.latencia_ms,
            }],
            dados={"input_tokens": 0, "output_tokens": 0},
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


async def _v2_build_saldo_fastpath_response(db: Session, empresa_id: int) -> AIResponse:
    from app.services.ai_intention_classifier import saldo_rapido_ia

    return await saldo_rapido_ia(db=db, empresa_id=empresa_id)


async def _v2_build_dashboard_fastpath_response(
    db: Session, empresa_id: int
) -> AIResponse:
    return await dashboard_financeiro_ia(db=db, empresa_id=empresa_id)


async def _v2_build_inadimplencia_fastpath_response(
    db: Session, empresa_id: int
) -> AIResponse:
    return await clientes_devendo_ia(db=db, empresa_id=empresa_id)


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
            "\n- Este canal e interno: nao responda operacoes de negocio de clientes."
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
                    "dados": ai_response.dados or {},
                    "pending_action": ai_response.pending_action,
                    "tool_trace": ai_response.tool_trace,
                    "input_tokens": 0,
                    "output_tokens": 0,
                },
            }
        )

    resolved_engine = resolve_engine(engine)
    engine_policy = get_engine_policy(resolved_engine)

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

    if _v2_is_saldo_rapido_message(mensagem):
        resposta = await _v2_build_saldo_fastpath_response(
            db=db,
            empresa_id=getattr(current_user, "empresa_id", 0),
        )
        async for event in _emit_fastpath_ai_response(resposta):
            yield event
        return

    if _v2_is_dashboard_financeiro_message(mensagem):
        resposta = await _v2_build_dashboard_fastpath_response(
            db=db,
            empresa_id=getattr(current_user, "empresa_id", 0),
        )
        async for event in _emit_fastpath_ai_response(resposta):
            yield event
        return

    if _v2_is_clientes_devendo_message(mensagem):
        resposta = await _v2_build_inadimplencia_fastpath_response(
            db=db,
            empresa_id=getattr(current_user, "empresa_id", 0),
        )
        async for event in _emit_fastpath_ai_response(resposta):
            yield event
        return

    if _v2_is_orcamento_fastpath_message(mensagem):
        resposta = await _v2_build_orcamento_fastpath_response(
            mensagem=mensagem,
            db=db,
            empresa_id=getattr(current_user, "empresa_id", 0),
            usuario_id=getattr(current_user, "id", 0),
        )
        async for event in _emit_fastpath_ai_response(resposta):
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

    if _v2_is_customer_revenue_ranking_unavailable_request(mensagem):
        final_text = _v2_customer_revenue_ranking_unavailable_response()
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
                        "capability": "ranking_clientes_indisponivel",
                        "semantic_contract": _build_semantic_contract(
                            summary=final_text,
                            metadata_extra={
                                "capability": "ranking_clientes_indisponivel"
                            },
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
    tool_trace: list[dict] = []
    pending_action: dict | None = None
    grafico_data: dict | None = None
    resp_dados: dict = {**adaptive_meta}
    tipo_resp: str | None = None
    sugs: list = []
    final_text: str = ""

    modelo_injetado = (
        settings.AI_TECHNICAL_MODEL
        if resolved_engine == ENGINE_INTERNAL_COPILOT
        else None
    )

    total_in = 0
    total_out = 0
    expanded_tools_once = False

    _metrics = {
        "tokens_prompt_pre_tools": 0,
        "tokens_tool_loop": 0,
        "tokens_retry_full_tools": 0,
        "tokens_final_stream": 0,
        "iterations_count": 0,
        "tools_payload_size": len(tools_payload),
    }

    for _iter in range(_V2_MAX_ITER):
        _metrics["iterations_count"] += 1
        # Proteção: budget máximo de tokens para evitar loops caros repetitivos
        if total_in > 15000:
            logger.warning(
                "[stream_v2] Token budget excedido (total_in=%s). Abortando loop.",
                total_in,
            )
            yield _enc(
                {
                    "error": "O assistente precisou de muitas informações para processar. Tente ser mais específico."
                }
            )
            return

        try:
            resp = await ia_service.chat(
                messages=messages,
                tools=tools_payload,
                temperature=0.3,
                max_tokens=1024,
                model_override=modelo_injetado,
            )
        except Exception as exc:
            logger.exception(
                "[stream_v2] Falha na chamada ia_service.chat iter=%s", _iter
            )
            yield _enc({"error": f"Erro ao consultar assistente: {exc}"})
            return

        _usage = (
            resp.get("usage", {})
            if isinstance(resp, dict)
            else getattr(resp, "usage", {}) or {}
        )
        try:
            _pt = int(_usage.get("prompt_tokens", 0) or 0)
            _ct = int(_usage.get("completion_tokens", 0) or 0)
            total_in += _pt
            total_out += _ct
            if _iter == 0:
                _metrics["tokens_prompt_pre_tools"] += _pt
            else:
                _metrics["tokens_tool_loop"] += _pt
        except Exception:
            pass

        # Normalizar resposta (dict ou objeto LiteLLM)
        choices = (
            resp.get("choices")
            if isinstance(resp, dict)
            else getattr(resp, "choices", None)
        )
        if not choices:
            break
        choice = choices[0]
        msg_obj = (
            choice.get("message")
            if isinstance(choice, dict)
            else getattr(choice, "message", None)
        )
        if msg_obj is None:
            break

        def _get(obj, *keys):
            for k in keys:
                if isinstance(obj, dict):
                    obj = obj.get(k)
                else:
                    obj = getattr(obj, k, None)
                if obj is None:
                    return None
            return obj

        tool_calls = _get(msg_obj, "tool_calls")
        if not tool_calls and not expanded_tools_once:
            candidate_text = _get(msg_obj, "content") or ""
            if _v2_should_retry_with_full_tools(
                mensagem=mensagem,
                candidate_text=candidate_text,
                reduced_tools_active=reduced_tools_active,
            ):
                expanded_tools_once = True

                if total_in > 10000:
                    logger.warning(
                        "[stream_v2] Blocking retry with full tools due to token budget (total_in=%s)",
                        total_in,
                    )
                else:
                    try:
                        resp_retry = await ia_service.chat(
                            messages=messages,
                            tools=full_tools_payload,
                            temperature=0.3,
                            max_tokens=1024,
                            model_override=modelo_injetado,
                        )
                        _usage_retry = (
                            resp_retry.get("usage", {})
                            if isinstance(resp_retry, dict)
                            else getattr(resp_retry, "usage", {}) or {}
                        )
                        _pt_retry = int(_usage_retry.get("prompt_tokens", 0) or 0)
                        _ct_retry = int(_usage_retry.get("completion_tokens", 0) or 0)
                        total_in += _pt_retry
                        total_out += _ct_retry
                        _metrics["tokens_retry_full_tools"] += _pt_retry
                        choices_retry = (
                            resp_retry.get("choices")
                            if isinstance(resp_retry, dict)
                            else getattr(resp_retry, "choices", None)
                        )
                        if choices_retry:
                            choice = choices_retry[0]
                            msg_obj = (
                                choice.get("message")
                                if isinstance(choice, dict)
                                else getattr(choice, "message", None)
                            )
                            tool_calls = _get(msg_obj, "tool_calls")
                            tools_payload = full_tools_payload
                            reduced_tools_active = False
                            adaptive_meta["tool_profile"] = "fallback_expanded_full"
                            adaptive_meta["tool_count"] = len(tools_payload)
                    except Exception:
                        logger.exception(
                            "[stream_v2] Falha ao aplicar fallback para tools completas"
                        )

        if tool_calls:
            # Adicionar turno do assistente com tool_calls ao histórico de messages
            assistant_turn: dict = {
                "role": "assistant",
                "content": _get(msg_obj, "content") or "",
            }
            tc_serialized = []
            for tc in tool_calls:
                fn = _get(tc, "function")
                tc_serialized.append(
                    {
                        "id": _get(tc, "id"),
                        "type": "function",
                        "function": {
                            "name": _get(fn, "name")
                            if isinstance(fn, dict)
                            else getattr(fn, "name", None),
                            "arguments": (
                                _get(fn, "arguments")
                                if isinstance(fn, dict)
                                else getattr(fn, "arguments", None)
                            ),
                        },
                    }
                )
            assistant_turn["tool_calls"] = tc_serialized
            messages.append(assistant_turn)

            for tc in tc_serialized:
                tool_name = (tc.get("function") or {}).get("name") or "?"
                yield _enc({"phase": "tool_running", "tool": tool_name})

                result = await tool_execute(
                    tc,
                    db=db,
                    current_user=current_user,
                    sessao_id=sessao_id,
                    request_id=request_id,
                    confirmation_token=None,
                    engine=engine,
                )
                result = await _autopaginate_tool_result(
                    mensagem=mensagem,
                    tc=tc,
                    result=result,
                    tool_execute=tool_execute,
                    db=db,
                    current_user=current_user,
                    sessao_id=sessao_id,
                    request_id=request_id,
                    confirmation_token=None,
                    engine=engine,
                )
                t_status = result.status if hasattr(result, "status") else "ok"
                t_latencia = result.latencia_ms if hasattr(result, "latencia_ms") else 0
                t_code = result.code if hasattr(result, "code") else None
                t_error = result.error if hasattr(result, "error") else None
                tool_trace.append(
                    {
                        "tool": tool_name,
                        "status": t_status,
                        "latencia_ms": t_latencia,
                        "code": t_code,
                        "reason": _tool_trace_reason(
                            status=t_status,
                            code=t_code,
                            error=t_error,
                        ),
                        "data": result.data if hasattr(result, "data") else None,
                    }
                )

                if t_status == "pending":
                    pending_action = (
                        result.pending_action
                        if hasattr(result, "pending_action")
                        else None
                    )
                    if pending_action:
                        extras = pending_action.get("extras") or {}
                        args = pending_action.get("args") or {}
                        # Mescla: args tem cliente_nome/itens (campos que operador_wpp_service lê)
                        resp_dados = {**args, **extras}

                payload = (
                    result.to_llm_payload()
                    if hasattr(result, "to_llm_payload")
                    else {"error": "executor sem payload"}
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.get("id"),
                        "content": json.dumps(payload, ensure_ascii=False, default=str),
                    }
                )

            if pending_action:
                final_text = ""
                break
            continue

        # Sem tool_calls → fase de resposta em texto — streaming real
        final_text = ""
        try:
            async for token in ia_service.chat_stream(
                messages=list(messages),
                temperature=0.3,
                max_tokens=1024,
                model_override=modelo_injetado,
            ):
                final_text += token
                yield _enc({"chunk": token})
        except Exception as exc:
            # Fallback: usar texto já retornado pelo chat() desta iteração
            candidate = _get(msg_obj, "content") or ""
            if candidate:
                final_text = candidate
                for word in candidate.split(" "):
                    yield _enc({"chunk": word + " "})
                    await asyncio.sleep(0.006)
            else:
                final_text = "Não consegui gerar a resposta. Tente novamente."
                yield _enc({"chunk": final_text})
        break
    else:
        final_text = "Limite de iterações atingido. Refine sua pergunta."
        yield _enc({"chunk": final_text})

    # Inferir tipo da resposta pelo trace de tools executadas
    if tool_trace and not pending_action:
        tools_ok = [t["tool"] for t in tool_trace if t.get("status") == "ok"]
        if any(t in tools_ok for t in ("criar_orcamento", "duplicar_orcamento")):
            tipo_resp = "orcamento_criado"
            if not sugs:
                sugs = [
                    "Ver o orçamento criado",
                    "Enviar por WhatsApp",
                    "Aprovar agora",
                ]
        elif any(
            t in tools_ok
            for t in (
                "aprovar_orcamento",
                "recusar_orcamento",
                "enviar_orcamento_whatsapp",
                "enviar_orcamento_email",
            )
        ):
            tipo_resp = "operador_resultado"
        elif any(
            t in tools_ok
            for t in (
                "obter_saldo_caixa",
                "listar_movimentacoes_financeiras",
                "listar_despesas",
            )
        ):
            tipo_resp = "financeiro"
            mov_tool = next(
                (
                    t
                    for t in tool_trace
                    if t.get("tool") == "listar_movimentacoes_financeiras"
                ),
                None,
            )
            if mov_tool and isinstance(mov_tool.get("data"), dict):
                movs = mov_tool["data"].get("movimentacoes", [])
                grafico_data = _v2_build_financial_chart_payload(movs)

    if not isinstance(final_text, str) or not final_text.strip():
        if pending_action:
            final_text = ""
        else:
            final_text = "Não consegui montar a resposta completa agora. Tente novamente em alguns segundos."

    if final_text.strip():
        SessionStore.append_db(
            sessao_id,
            "assistant",
            final_text,
            db,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
        )

    # Persiste resumo de tokens da sessão no ToolCallLog para observabilidade
    if (total_in > 0 or total_out > 0) and db is not None:
        try:
            from app.models.models import ToolCallLog as _ToolCallLog

            _token_row = _ToolCallLog(
                empresa_id=int(empresa_id) if empresa_id else None,
                usuario_id=int(usuario_id) if usuario_id else None,
                sessao_id=str(sessao_id) if sessao_id else None,
                tool="llm_turn",
                args_json={
                    "_meta": {
                        **runtime_meta,
                    }
                },
                resultado_json=None,
                status="ok",
                input_tokens=int(total_in),
                output_tokens=int(total_out),
            )
            db.add(_token_row)
            db.commit()
        except Exception:
            pass  # não bloqueia a resposta se falhar

    yield _enc(
        {
            "is_final": True,
            "final_text": final_text,
            "metadata": {
                "final_text": final_text,
                "tipo": tipo_resp,
                "dados": {
                    **adaptive_meta,
                    **resp_dados,
                    "semantic_contract": _build_semantic_contract(
                        summary=final_text,
                        table=(
                            (
                                resp_dados.get("rows")
                                if isinstance(resp_dados, dict)
                                else None
                            )
                            or []
                        ),
                        chart=_to_semantic_chart(grafico_data),
                        printable={
                            "title": "Resumo do assistente",
                            "summary": final_text,
                        },
                        metadata_extra={
                            "capability": "GenerateAnalyticsReport"
                            if tipo_resp == "financeiro"
                            else "UnknownCapability",
                            "domain": "analytics"
                            if tipo_resp == "financeiro"
                            else "unknown",
                            "tipo_resposta_inferida": tipo_resp,
                        },
                    ),
                },
                "grafico": grafico_data,
                "pending_action": pending_action,
                "tool_trace": tool_trace or None,
                "sugestoes": sugs or None,
                "input_tokens": total_in,
                "output_tokens": total_out,
            },
        }
    )


async def assistente_unificado_stream(
    mensagem: str,
    sessao_id: str,
    db,
    current_user,
    engine: str = DEFAULT_ENGINE,
    request_id: str | None = None,
    confirmation_token: str | None = None,
    override_args: dict | None = None,
):
    """Ponto de entrada SSE — delega para assistente_v2_stream_core (Tool Use v2).

    Mantém compatibilidade de URL com o frontend. O router deve passar
    `current_user` (objeto User completo) e os tokens de confirmação.
    """
    import asyncio

    try:
        async for event in assistente_v2_stream_core(
            mensagem=mensagem,
            sessao_id=sessao_id,
            db=db,
            current_user=current_user,
            engine=engine,
            request_id=request_id,
            confirmation_token=confirmation_token,
            override_args=override_args,
        ):
            yield event
    except asyncio.TimeoutError:
        yield f"data: {json.dumps({'error': 'Tempo limite atingido. Tente novamente.'})}\n\n"
    except Exception as exc:
        logger.exception("[assistente_unificado_stream] Erro inesperado")
        yield f"data: {json.dumps({'error': str(exc)})}\n\n"


# ── Funções de Compatibilidade (manter backward compatibility) ────────────────


async def interpretar_mensagem_hub(
    mensagem: str, db: Optional[Session] = None
) -> AIResponse:
    """Wrapper compatível com interpretar_mensagem antiga"""
    return await ai_hub.processar("orcamentos", mensagem, db=db)


async def interpretar_comando_operador_hub(mensagem: str) -> AIResponse:
    """Wrapper compatível com interpretar_comando_operador antiga"""
    return await ai_hub.processar("operador", mensagem)


async def gerar_resposta_bot_hub(mensagem: str, dados_empresa: dict) -> str:
    """Wrapper compatível com gerar_resposta_bot antiga"""
    return await ai_hub.conversar(mensagem, dados_empresa)


async def processar_cliente_ia(
    mensagem: str, db: Optional[Session] = None
) -> AIResponse:
    """Processa cadastro de cliente por IA"""
    return await ai_hub.processar("clientes", mensagem, db=db)


async def processar_financeiro_ia(
    mensagem: str, db: Optional[Session] = None
) -> AIResponse:
    """Processa transação financeira por IA"""
    return await ai_hub.processar("financeiro", mensagem, db=db)


async def processar_comercial_ia(
    mensagem: str, db: Optional[Session] = None
) -> AIResponse:
    """Processa qualificação de lead por IA"""
    return await ai_hub.processar("comercial", mensagem, db=db)


async def analisar_financeiro_ia(
    mensagem: str,
    dados_financeiros: Optional[dict] = None,
    db: Optional[Session] = None,
    empresa_id: Optional[int] = None,
) -> AIResponse:
    """
    Analisa dados financeiros e fornece insights

    Args:
        mensagem: Pergunta ou comando do usuário
        dados_financeiros: Dados financeiros para análise (receitas, despesas, etc.)
        db: Sessão do banco para buscar dados se não fornecidos
        empresa_id: ID da empresa (obrigatório para buscar dados reais)
    """
    # Se não tiver dados, buscar do banco
    if not dados_financeiros and db and empresa_id:
        dados_financeiros = await _buscar_dados_financeiros(db, empresa_id)
    elif not dados_financeiros:
        dados_financeiros = {
            "receitas": [],
            "despesas": [],
            "periodo": "sem_dados",
            "saldo": 0,
        }
        if not empresa_id:
            logger.warning(
                "[AI Hub] empresa_id não fornecido para analisar_financeiro_ia"
            )

    # Montar contexto para a IA
    contexto = {"dados_financeiros": dados_financeiros, "pergunta": mensagem}

    return await ai_hub.processar(
        "financeiro_analise", mensagem, contexto=contexto, db=db
    )


async def _buscar_dados_financeiros(
    db: Session, empresa_id: Optional[int] = None
) -> dict:
    """
    Busca dados financeiros reais do banco de dados.

    VERSÃO OTIMIZADA (Etapa 2: Anti-Bloqueio):
    - Usa func.sum() para agregações no banco (não em Python)
    - Elimina loops Python para somar valores
    - Converte Decimal para float no resultado final

    Returns:
        dict com receitas, despesas, saldo e métricas financeiras
    """
    from datetime import datetime, timedelta
    from app.models.models import ContaFinanceira, SaldoCaixaConfig
    from app.services import financeiro_service

    if not empresa_id:
        logger.warning(
            "[AI Hub] empresa_id não fornecido para buscar dados financeiros"
        )
        return {"receitas": [], "despesas": [], "periodo": "ultimo_mes", "saldo": 0}

    hoje = datetime.now().date()
    inicio_mes = hoje.replace(day=1)

    # ═════════════════════════════════════════════════════════════════
    # ETAPA 2: QUERIES AGREGADAS (Anti-Bloqueio)
    # Elimina loops Python - deixa o banco fazer os cálculos
    # ═════════════════════════════════════════════════════════════════

    # Buscar saldo inicial configurado
    saldo_config = (
        db.query(SaldoCaixaConfig)
        .filter(SaldoCaixaConfig.empresa_id == empresa_id)
        .first()
    )

    # Converte Decimal para float para compatibilidade Pydantic/JSON
    saldo_inicial = float(saldo_config.saldo_inicial) if saldo_config else 0.0

    # AGREGADO: Soma de receitas usando func.sum() no banco
    # COALESCE trata NULL como 0
    total_receitas_result = (
        db.query(
            func.coalesce(
                func.sum(
                    func.coalesce(ContaFinanceira.valor_pago, ContaFinanceira.valor, 0)
                ),
                0,
            ).label("total")
        )
        .filter(
            and_(
                ContaFinanceira.empresa_id == empresa_id,
                ContaFinanceira.tipo == "receber",
                ContaFinanceira.excluido_em.is_(None),
                ContaFinanceira.cancelado_em.is_(None),
                ContaFinanceira.data_vencimento >= inicio_mes,
                ContaFinanceira.data_vencimento <= hoje,
            )
        )
        .scalar()
    )

    # AGREGADO: Soma de despesas usando func.sum() no banco
    total_despesas_result = (
        db.query(
            func.coalesce(
                func.sum(
                    func.coalesce(ContaFinanceira.valor_pago, ContaFinanceira.valor, 0)
                ),
                0,
            ).label("total")
        )
        .filter(
            and_(
                ContaFinanceira.empresa_id == empresa_id,
                ContaFinanceira.tipo == "pagar",
                ContaFinanceira.excluido_em.is_(None),
                ContaFinanceira.cancelado_em.is_(None),
                ContaFinanceira.data_vencimento >= inicio_mes,
                ContaFinanceira.data_vencimento <= hoje,
            )
        )
        .scalar()
    )

    # Converte Decimal para float para compatibilidade JSON/Pydantic
    total_receitas = float(total_receitas_result) if total_receitas_result else 0.0
    total_despesas = float(total_despesas_result) if total_despesas_result else 0.0

    # Saldo atual alinhado com o KPI "Saldo em Caixa" do dashboard financeiro.
    saldo_caixa = float(financeiro_service.calcular_saldo_caixa_kpi(empresa_id, db))

    # Buscar detalhes das receitas (limitado para não sobrecarregar)
    receitas_mes = (
        db.query(ContaFinanceira)
        .filter(
            and_(
                ContaFinanceira.empresa_id == empresa_id,
                ContaFinanceira.tipo == "receber",
                ContaFinanceira.excluido_em.is_(None),
                ContaFinanceira.cancelado_em.is_(None),
                ContaFinanceira.data_vencimento >= inicio_mes,
                ContaFinanceira.data_vencimento <= hoje,
            )
        )
        .limit(100)
        .all()
    )

    # Buscar detalhes das despesas (limitado)
    despesas_mes = (
        db.query(ContaFinanceira)
        .filter(
            and_(
                ContaFinanceira.empresa_id == empresa_id,
                ContaFinanceira.tipo == "pagar",
                ContaFinanceira.excluido_em.is_(None),
                ContaFinanceira.cancelado_em.is_(None),
                ContaFinanceira.data_vencimento >= inicio_mes,
                ContaFinanceira.data_vencimento <= hoje,
            )
        )
        .limit(100)
        .all()
    )

    # Formatar receitas para JSON (converter Decimal para float)
    receitas_formatted = [
        {
            "descricao": r.descricao,
            "valor": float(r.valor_pago or r.valor or 0),
            "status": r.status,
            "data_vencimento": str(r.data_vencimento) if r.data_vencimento else None,
            "categoria": r.categoria or "Serviço",
        }
        for r in receitas_mes
    ]

    # Formatar despesas para JSON
    despesas_formatted = [
        {
            "descricao": d.descricao,
            "valor": float(d.valor_pago or d.valor or 0),
            "status": d.status,
            "data_vencimento": str(d.data_vencimento) if d.data_vencimento else None,
            "categoria": d.categoria or "Despesa",
        }
        for d in despesas_mes
    ]

    logger.info(
        f"[AI Hub] Dados financeiros calculados: "
        f"receitas={total_receitas:.2f}, despesas={total_despesas:.2f}, "
        f"saldo={saldo_caixa:.2f}"
    )

    return {
        "receitas": receitas_formatted,
        "despesas": despesas_formatted,
        "periodo": "mes_atual",
        "data_inicio": str(inicio_mes),
        "data_fim": str(hoje),
        "saldo": {
            "inicial": saldo_inicial,
            "receitas": total_receitas,
            "despesas": total_despesas,
            "atual": saldo_caixa,
            "definicao": "Mesmo valor do KPI 'Saldo em Caixa' do Financeiro: pagamentos confirmados acumulados menos despesas pagas confirmadas, mais saldo inicial configurado.",
        },
        "totais": {
            "receitas": total_receitas,
            "despesas": total_despesas,
            "resultado": total_receitas - total_despesas,
        },
    }


async def analisar_conversao_ia(
    mensagem: str,
    dados_orcamentos: Optional[dict] = None,
    db: Optional[Session] = None,
    empresa_id: Optional[int] = None,
) -> AIResponse:
    """
    Analisa taxas de conversão de orçamentos

    Args:
        mensagem: Pergunta ou comando do usuário
        dados_orcamentos: Dados de orçamentos para análise
        db: Sessão do banco para buscar dados se não fornecidos
        empresa_id: ID da empresa para filtrar dados
    """
    # Se não tiver dados, buscar do banco
    if not dados_orcamentos and db and empresa_id:
        from app.models.models import Orcamento, StatusOrcamento

        inicio = datetime.now(ZoneInfo("America/Sao_Paulo")) - timedelta(days=30)
        total = (
            db.query(func.count(Orcamento.id))
            .filter(Orcamento.empresa_id == empresa_id, Orcamento.criado_em >= inicio)
            .scalar()
            or 0
        )
        aprovados = (
            db.query(func.count(Orcamento.id))
            .filter(
                Orcamento.empresa_id == empresa_id,
                Orcamento.status == StatusOrcamento.APROVADO,
                Orcamento.criado_em >= inicio,
            )
            .scalar()
            or 0
        )
        recusados = (
            db.query(func.count(Orcamento.id))
            .filter(
                Orcamento.empresa_id == empresa_id,
                Orcamento.status == StatusOrcamento.RECUSADO,
                Orcamento.criado_em >= inicio,
            )
            .scalar()
            or 0
        )
        dados_orcamentos = {
            "enviados": total,
            "aprovados": aprovados,
            "recusados": recusados,
            "servicos": [],
            "periodo": "ultimo_mes",
        }
    elif not dados_orcamentos:
        dados_orcamentos = {
            "enviados": 0,
            "aprovados": 0,
            "recusados": 0,
            "servicos": [],
            "periodo": "ultimo_mes",
        }

    contexto = {"dados_orcamentos": dados_orcamentos, "pergunta": mensagem}

    return await ai_hub.processar(
        "conversao_analise", mensagem, contexto=contexto, db=db
    )


async def gerar_sugestoes_negocio_ia(
    mensagem: str,
    dados_empresa: Optional[dict] = None,
    db: Optional[Session] = None,
    empresa_id: Optional[int] = None,
) -> AIResponse:
    """
    Gera sugestões estratégicas para o negócio

    Args:
        mensagem: Pergunta ou área de interesse
        dados_empresa: Dados da empresa para análise
        db: Sessão do banco para buscar dados se não fornecidos
        empresa_id: ID da empresa para filtrar dados
    """
    # Se não tiver dados, buscar do banco
    if not dados_empresa and db and empresa_id:
        from app.models.models import Orcamento, StatusOrcamento, Cliente

        inicio = datetime.now(ZoneInfo("America/Sao_Paulo")) - timedelta(days=30)
        orcs = (
            db.query(Orcamento.id, Orcamento.numero, Orcamento.total, Orcamento.status)
            .filter(Orcamento.empresa_id == empresa_id, Orcamento.criado_em >= inicio)
            .limit(20)
            .all()
        )
        clientes = (
            db.query(Cliente.id, Cliente.nome)
            .filter(Cliente.empresa_id == empresa_id)
            .limit(20)
            .all()
        )
        dados_empresa = {
            "orcamentos": [
                {
                    "id": o.id,
                    "numero": o.numero,
                    "total": float(o.total or 0),
                    "status": str(o.status),
                }
                for o in orcs
            ],
            "clientes": [{"id": c.id, "nome": c.nome} for c in clientes],
            "servicos": [],
            "financeiro": {},
        }
    elif not dados_empresa:
        dados_empresa = {
            "orcamentos": [],
            "clientes": [],
            "servicos": [],
            "financeiro": {},
        }

    contexto = {"dados_empresa": dados_empresa, "pergunta": mensagem}

    return await ai_hub.processar(
        "negocio_sugestoes", mensagem, contexto=contexto, db=db
    )


# ── Funções Especializadas para Comandos Comuns ─────────────────────────────────


async def dashboard_financeiro_ia(
    db: Optional[Session] = None, empresa_id: Optional[int] = None
) -> AIResponse:
    """
    Gera dashboard financeiro completo com IA

    Responde a comandos como:
    - "Como estão as finanças?"
    - "Me mostre o resumo financeiro"
    - "Dashboard financeiro"
    """
    mensagem = "Gerar dashboard financeiro completo com KPIs principais e insights"
    return await analisar_financeiro_ia(mensagem, db=db, empresa_id=empresa_id)


async def clientes_devendo_ia(
    db: Optional[Session] = None, empresa_id: Optional[int] = None
) -> AIResponse:
    """
    Lista clientes com contas em atraso

    Responde a comandos como:
    - "Quais clientes estão devendo?"
    - "Lista de inadimplentes"
    - "Clientes em atraso"
    """
    mensagem = "Listar clientes com contas em atraso e valores devidos"
    return await analisar_financeiro_ia(mensagem, db=db, empresa_id=empresa_id)


async def ticket_medio_ia(
    db: Optional[Session] = None, empresa_id: Optional[int] = None
) -> AIResponse:
    """
    Calcula e analisa ticket médio

    Responde a comandos como:
    - "Qual meu ticket médio?"
    - "Valor médio dos orçamentos"
    - "Ticket médio de vendas"
    """
    mensagem = "Calcular ticket médio de orçamentos aprovados e analisar tendências"
    return await analisar_conversao_ia(mensagem, db=db, empresa_id=empresa_id)


async def servico_mais_vendido_ia(
    db: Optional[Session] = None, empresa_id: Optional[int] = None
) -> AIResponse:
    """
    Identifica serviço mais vendido/procurado

    Responde a comandos como:
    - "Qual serviço mais vendido?"
    - "Serviço mais procurado"
    - "Ranking de serviços"
    """
    mensagem = "Identificar serviço mais vendido e analisar sua performance"
    return await analisar_conversao_ia(mensagem, db=db, empresa_id=empresa_id)


async def previsao_caixa_ia(
    db: Optional[Session] = None, empresa_id: Optional[int] = None
) -> AIResponse:
    """
    Gera previsão de fluxo de caixa

    Responde a comandos como:
    - "Previsão de caixa para próximos 30 dias"
    - "Quanto vou receber/pagar"
    - "Projeção financeira"
    """
    mensagem = (
        "Gerar previsão de fluxo de caixa para próximos 30 dias com receitas e despesas"
    )
    return await analisar_financeiro_ia(mensagem, db=db, empresa_id=empresa_id)


async def cliente_mais_lucrativo_ia(
    db: Optional[Session] = None, empresa_id: Optional[int] = None
) -> AIResponse:
    """
    Identifica cliente mais lucrativo

    Responde a comandos como:
    - "Qual cliente mais lucrativo?"
    - "Melhor cliente em receita"
    - "Top clientes"
    """
    mensagem = "Identificar cliente mais lucrativo e analisar seu histórico"
    return await gerar_sugestoes_negocio_ia(mensagem, db=db, empresa_id=empresa_id)


async def faturamento_ia(
    db: Optional[Session] = None, empresa_id: Optional[int] = None
) -> AIResponse:
    """
    Retorna faturamento do mês atual (soma de orçamentos aprovados).
    Diferencia de SALDO: faturamento = bruto aprovado; saldo = líquido em caixa.
    """
    try:
        from app.models.models import Orcamento, StatusOrcamento
        from datetime import datetime

        if not db or not empresa_id:
            return AIResponse(
                sucesso=False,
                resposta="Não foi possível identificar a empresa.",
                tipo_resposta="erro",
                confianca=0.0,
            )

        mes = datetime.now().month
        ano = datetime.now().year

        orcamentos_aprovados = (
            db.query(Orcamento)
            .filter(
                Orcamento.empresa_id == empresa_id,
                Orcamento.status == StatusOrcamento.APROVADO,
            )
            .all()
        )

        total_faturado = sum(float(o.total or 0) for o in orcamentos_aprovados)
        qtd = len(orcamentos_aprovados)
        ticket_medio = total_faturado / qtd if qtd > 0 else 0

        from app.core.config import settings

        simbolo = "R$"
        total_fmt = (
            f"{simbolo} {total_faturado:,.2f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )
        ticket_fmt = (
            f"{simbolo} {ticket_medio:,.2f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

        resposta = (
            f"📊 Faturamento este mês: *{total_fmt}*\n"
            f"Aprovados: {qtd} orçamento(s) | Ticket médio: {ticket_fmt}\n"
            f"(Orçamentos aprovados — independiente do pagamento)"
        )
        return AIResponse(
            sucesso=True,
            resposta=resposta,
            tipo_resposta="faturamento",
            dados={
                "faturamento": total_faturado,
                "qtd_aprovados": qtd,
                "ticket_medio": ticket_medio,
            },
            confianca=0.95,
            modulo_origem="financeiro_faturamento",
        )
    except Exception as e:
        logger.error(f"[faturamento_ia] Erro: {e}")
        return AIResponse(
            sucesso=False,
            resposta="Não foi possível consultar o faturamento.",
            tipo_resposta="erro",
            confianca=0.0,
            erros=[str(e)],
            modulo_origem="financeiro_faturamento",
        )


async def contas_receber_ia(
    db: Optional[Session] = None, empresa_id: Optional[int] = None
) -> AIResponse:
    """
    Retorna total a receber (valores em aberto de orçamentos aprovados).
    Diferencia de SALDO: é o que ainda NÃO entrou no caixa.
    """
    try:
        from app.models.models import Orcamento, StatusOrcamento
        from datetime import datetime, timezone

        if not db or not empresa_id:
            return AIResponse(
                sucesso=False,
                resposta="Não foi possível identificar a empresa.",
                tipo_resposta="erro",
                confianca=0.0,
            )

        orcamentos = (
            db.query(Orcamento)
            .filter(
                Orcamento.empresa_id == empresa_id,
                Orcamento.status == StatusOrcamento.APROVADO,
            )
            .all()
        )

        total_aberto = sum(float(o.total or 0) for o in orcamentos)
        qtd = len(orcamentos)

        # Vencidos: aprovados há mais de 7 dias
        agora = datetime.now(timezone.utc)
        vencidos = [
            o
            for o in orcamentos
            if o.aprovado_em
            and (agora - o.aprovado_em.replace(tzinfo=timezone.utc)).days > 7
        ]
        total_vencido = sum(float(o.total or 0) for o in vencidos)

        from app.core.config import settings

        simbolo = "R$"
        aberto_fmt = (
            f"{simbolo} {total_aberto:,.2f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )
        vencido_fmt = (
            f"{simbolo} {total_vencido:,.2f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

        if total_vencido > 0:
            resposta = f"📋 A receber: *{aberto_fmt}*\nVencidos (7+ dias): {vencido_fmt} ({len(vencidos)} orçamento(s))\nTotal: {qtd} aprovação(ões) em aberto"
        else:
            resposta = f"📋 A receber: *{aberto_fmt}*\n{qtd} aprovação(ões) em aberto — nenhum vencido ainda"

        return AIResponse(
            sucesso=True,
            resposta=resposta,
            tipo_resposta="contas_receber",
            dados={
                "total_aberto": total_aberto,
                "total_vencido": total_vencido,
                "qtd": qtd,
            },
            confianca=0.95,
            modulo_origem="financeiro_contas_receber",
        )
    except Exception as e:
        logger.error(f"[contas_receber_ia] Erro: {e}")
        return AIResponse(
            sucesso=False,
            resposta="Não foi possível consultar contas a receber.",
            tipo_resposta="erro",
            confianca=0.0,
            erros=[str(e)],
            modulo_origem="financeiro_contas_receber",
        )


async def contas_pagar_ia(
    db: Optional[Session] = None, empresa_id: Optional[int] = None
) -> AIResponse:
    """
    Retorna total a pagar (parcelas/contas a pagar cadastradas).
    """
    try:
        from app.models.models import ContaFinanceira
        from datetime import datetime

        if not db or not empresa_id:
            return AIResponse(
                sucesso=False,
                resposta="Não foi possível identificar a empresa.",
                tipo_resposta="erro",
                confianca=0.0,
            )

        contas = (
            db.query(ContaFinanceira)
            .filter(
                ContaFinanceira.empresa_id == empresa_id,
                ContaFinanceira.tipo == "pagar",
                ContaFinanceira.status != "pago",
                ContaFinanceira.status != "cancelado",
            )
            .all()
        )

        total_pagar = sum(float(c.valor or 0) for c in contas)
        qtd = len(contas)

        from app.core.config import settings

        simbolo = "R$"
        pagar_fmt = (
            f"{simbolo} {total_pagar:,.2f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

        resposta = f"📤 A pagar: *{pagar_fmt}*\n{qtd} conta(s) em aberto"
        if qtd == 0:
            resposta = "✅ Nenhuma conta a pagar no momento."

        return AIResponse(
            sucesso=True,
            resposta=resposta,
            tipo_resposta="contas_pagar",
            dados={"total_pagar": total_pagar, "qtd": qtd},
            confianca=0.95,
            modulo_origem="financeiro_contas_pagar",
        )
    except Exception as e:
        logger.error(f"[contas_pagar_ia] Erro: {e}")
        return AIResponse(
            sucesso=False,
            resposta="Não foi possível consultar contas a pagar.",
            tipo_resposta="erro",
            confianca=0.0,
            erros=[str(e)],
            modulo_origem="financeiro_contas_pagar",
        )


async def sugestao_precos_ia(
    servico: Optional[str] = None,
    db: Optional[Session] = None,
    empresa_id: Optional[int] = None,
) -> AIResponse:
    """
    Sugere ajustes de preços

    Responde a comandos como:
    - "Sugerir aumento de preços para pintura"
    - "Revisar tabela de preços"
    - "Precos muito baixos?"
    """
    mensagem = f"Sugerir ajustes de preços{f' para {servico}' if servico else ''} baseado em mercado e custos"
    return await gerar_sugestoes_negocio_ia(mensagem, db=db)


# ═══════════════════════════════════════════════════════════════════════════════
# NOTAS DE REFATORAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════
"""
Funções detectar_intencao_assistente e saldo_rapido_ia foram movidas para:
- app/services/ai_intention_classifier.py

Importe-as diretamente:
    from app.services.ai_intention_classifier import detectar_intencao_assistente
    from app.services.ai_intention_classifier import saldo_rapido_ia
"""


# ═══════════════════════════════════════════════════════════════════════════════
# Assistente Unificado v2 — Tool Use nativo (Fase 1)
# ═══════════════════════════════════════════════════════════════════════════════


def _v2_prompt_listar_orcamentos_datas_br() -> str:
    """Datas civis BR + exemplo de intervalo (reduz erro de parâmetro no LLM)."""
    hoje = datetime.now(_TZ_BR).date()
    ontem = hoje - timedelta(days=1)
    return (
        "\n\n## listar_orcamentos — datas (America/Sao_Paulo)\n"
        f"- Hoje: `{hoje.isoformat()}` | Ontem: `{ontem.isoformat()}`\n"
        f"- Só ontem: `aprovado_em_de` e `aprovado_em_ate` = `{ontem.isoformat()}`.\n"
        f'- Ontem **e** hoje (uma chamada): `aprovado_em_de="{ontem.isoformat()}"`, '
        f'`aprovado_em_ate="{hoje.isoformat()}"` (status APROVADO ou omita).\n'
        "- Para listar **todos** os itens de um intervalo curto no card (até o teto do sistema), "
        'use `limit=50` ou peça "lista completa" / "todos os orçamentos" na mensagem.\n'
        "- Não dispare várias `listar_orcamentos` em paralelo para dias vizinhos — "
        "use um único intervalo.\n"
    )


_V2_SYSTEM_PROMPT = (
    "Você é o **Assistente COTTE**, um parceiro inteligente de gestão para pequenas empresas, "
    "um **Assistente Operacional Universal**. Responda sempre em português, de forma direta e amigável. Máximo de 3 parágrafos. "
    "\n\n"
    "## Como funcionar:  \n"
    "Use as ferramentas (tools) disponíveis para buscar informações reais e cruzamentos analíticos. "
    "Se precisar de relatórios personalizados, agrupamentos por categoria, tabelas, rankings "
    "ou cálculos complexos do financeiro/comercial, **FAÇA queries SQL** ativamente usando a tool 'executar_sql_analitico'. "
    "NUNCA invente números, nomes ou valores — sempre obtenha via tool. "
    "\n\n"
    "## Regras críticas:  \n"
    "1. **Criar/excluir**: chame a tool DIRETAMENTE — o sistema mostrará um card de confirmação. "
    "NÃO pergunte 'deseja prosseguir?' previamente. \n"
    '2. **IDs por conta própria**: para excluir/editar por NOME, chame `listar_clientes(busca="nome")` '
    "primeiro para obter o ID real. NUNCA chute IDs ou use posições de listas anteriores. \n"
    "3. **Sem tool correspondente**: diga claramente que não há ferramenta para isso — "
    "NÃO chame outra tool no lugar. \n"
    "4. **Criar orçamentos**: chame `criar_orcamento` DIRETAMENTE com `cliente_nome` e o item. "
    "NÃO busque o cliente antes, o backend resolve automaticamente. "
    "PARSING DE PREÇO: extraia `valor_unit` do texto natural — 'pacote de prego por 36' → "
    "descricao='pacote de prego', valor_unit=36. Preposições 'por', 'a', 'de', 'R$' indicam preço. "
    "NUNCA coloque o preço dentro da descricao — sempre como campo `valor_unit` separado. \n"
    "5. **Sem loop**: NUNCA repita a mesma tool call mais de uma vez. Se a resposta não vier "
    "como esperado, explique o que tem e a limitação. \n"
    "6. **Erros de identidade**: se não encontrar um recurso pelo nome/ID exato informado, "
    "EXPLIQUE o motivo e sugira alternativas (ex: 'Não encontrei O-103 — os recentes são X e Y'). "
    "NUNCA diga 'Comando DESCONHECIDO' ou retorne um erro técnico cru. \n"
    "7. **Inteligente mas humilde**: se não tiver certeza, pergunte ao usuário uma "
    "coisa de cada vez, sem listas de perguntas. \n"
    "8. **`listar_orcamentos` e datas**: o parâmetro `dias` filtra pela **data de criação** "
    '(criado_em). Para **aprovação** (ex.: "aprovados ontem", "ontem e hoje"), use '
    "`aprovado_em_de` e `aprovado_em_ate` em YYYY-MM-DD (intervalo inclusivo; **um dia** = "
    'mesma data nas duas chaves). `status="APROVADO"` ou omita. Ver bloco fixo de datas '
    "no system prompt. \n"
    "9. **`listar_orcamentos` e paginação**: o JSON da tool traz `total` (quantos batem com o filtro), "
    "`itens_retornados` (ou o tamanho de `orcamentos`), `has_more` e `limit`. Se `total` for maior "
    "que a quantidade listada ou `has_more` for true, diga na resposta quantos existem no total e "
    'quantos foram mostrados (ex.: "Há 16 no período; abaixo os 10 mais recentes"); mencione '
    "o botão Carregar mais no card, se existir. Não dê a entender que a tabela é a lista completa "
    "quando houver paginação. \n"
)

_V2_MINIMAL_SYSTEM_PROMPT = (
    "Você é o Assistente COTTE. Responda sempre em português, com objetividade e no máximo 3 parágrafos. "
    "Use as tools disponíveis para buscar dados reais e nunca invente números, nomes ou valores. "
    "Para criar, editar ou excluir, chame a tool diretamente; o sistema cuida da confirmação quando necessário. "
    "Ao criar orçamento, extraia `cliente_nome`, item e `valor_unit` do texto natural e não misture preço na descrição. "
    "Se não existir ferramenta para a tarefa, diga isso claramente."
)

_V2_TECHNICAL_COPILOT_PROMPT = (
    "Você é o **Copiloto Técnico Interno** do sistema. "
    "Você é focado em engenharia de software e suporte técnico para o superadmin. "
    "Seu papel é auxiliar no entendimento da arquitetura, debug de código, boas práticas e manutenção. "
    "IMPORTANTE: Você tem acesso de leitura ao repositório! Use as ferramentas (tools) `ler_arquivo_repositorio`, "
    "`buscar_codigo_repositorio` e `analisar_estrutura_html` para inspecionar ativamente arquivos como HTML, JS, CSS e Python quando o usuário relatar um bug. "
    "Nunca diga que não tem acesso a arquivos. Se não encontrar algo, use a busca para localizar. "
    "Retorne suas análises e correções com blocos de código markdown (```html, ```js, etc)."
)

_V2_MAX_ITER = 5
_V2_KB_SNIPPET_CACHE: Optional[str] = None


def _v2_load_kb_snippet(max_chars: int = 1800) -> str:
    """Carrega um trecho compacto da KB funcional para orientar o v2."""
    global _V2_KB_SNIPPET_CACHE
    if _V2_KB_SNIPPET_CACHE is not None:
        return _V2_KB_SNIPPET_CACHE

    kb_path = os.path.join(
        os.path.dirname(__file__),
        "prompts",
        "knowledge_base.md",
    )
    try:
        with open(kb_path, "r", encoding="utf-8") as f:
            raw = f.read()
        # Remove frontmatter e compacta quebras excessivas
        raw = re.sub(r"^---[\s\S]*?---\s*", "", raw, count=1)
        raw = re.sub(r"\n{3,}", "\n\n", raw).strip()
        if len(raw) > max_chars:
            raw = raw[:max_chars].rsplit("\n", 1)[0].strip() + "\n\n[KB truncada]"
        _V2_KB_SNIPPET_CACHE = raw
    except Exception as e:
        logger.warning("[assistente_v2] Falha ao carregar knowledge_base.md: %s", e)
        _V2_KB_SNIPPET_CACHE = ""
    return _V2_KB_SNIPPET_CACHE


def _v2_is_excel_chart_request(mensagem: str) -> bool:
    msg = (mensagem or "").lower()
    if not msg:
        return False
    has_excel = any(
        k in msg for k in ("excel", "planilha", "xlsx", "arquivo xls", "arquivo excel")
    )
    has_chart = any(k in msg for k in ("gráfico", "grafico", "chart"))
    has_financial_scope = any(
        k in msg
        for k in ("financeiro", "finanças", "financas", "caixa", "receita", "despesa")
    )
    return has_excel and has_chart and has_financial_scope


def _v2_is_financial_chart_request(mensagem: str) -> bool:
    msg = (mensagem or "").lower()
    if not msg:
        return False
    has_chart = any(k in msg for k in ("gráfico", "grafico", "chart"))
    has_financial_scope = any(
        k in msg
        for k in (
            "financeiro",
            "finanças",
            "financas",
            "caixa",
            "receita",
            "despesa",
            "movimenta",
            "fluxo",
        )
    )
    return has_chart and has_financial_scope


def _v2_is_customer_revenue_ranking_unavailable_request(mensagem: str) -> bool:
    msg = (mensagem or "").lower()
    if not msg:
        return False
    has_client_scope = "cliente" in msg or "clientes" in msg
    has_revenue_scope = any(
        token in msg
        for token in (
            "faturamento",
            "ticket medio",
            "ticket médio",
            "mês anterior",
            "mes anterior",
        )
    )
    has_ranking_scope = "ranking" in msg and "10" in msg
    has_current_month_scope = "mês atual" in msg or "mes atual" in msg
    return (
        has_client_scope
        and has_revenue_scope
        and has_ranking_scope
        and has_current_month_scope
    )


def _v2_customer_revenue_ranking_unavailable_response() -> str:
    return (
        "Atualmente, não há uma ferramenta disponível para gerar um ranking dos clientes "
        "com maior faturamento diretamente. Para isso, você precisaria acessar os dados "
        "de faturamento e calcular o ticket médio e a variação em relação ao mês anterior manualmente.\n\n"
        "Se precisar de ajuda para encontrar esses dados ou orientações sobre como realizar "
        "esses cálculos, estou aqui para ajudar!"
    )


def _v2_extract_days_window(mensagem: str, default_days: int = 30) -> int:
    m = re.search(r"(\d{1,3})\s*dias?", (mensagem or "").lower())
    if not m:
        return default_days
    dias = int(m.group(1))
    return max(1, min(dias, 365))


def _v2_build_financial_chart_payload(movimentacoes: list[dict]) -> dict | None:
    if not movimentacoes:
        return None

    buckets: dict[str, dict[str, float]] = {}
    for mov in movimentacoes:
        data_raw = str(mov.get("data") or "")[:10]
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", data_raw):
            continue
        tipo = str(mov.get("tipo") or "").lower()
        valor = float(mov.get("valor") or 0.0)
        if data_raw not in buckets:
            buckets[data_raw] = {"entrada": 0.0, "saida": 0.0}
        if tipo == "entrada":
            buckets[data_raw]["entrada"] += valor
        elif tipo == "saida":
            buckets[data_raw]["saida"] += valor

    if not buckets:
        return None

    labels = sorted(buckets.keys())
    entradas = [round(buckets[d]["entrada"], 2) for d in labels]
    saidas = [round(buckets[d]["saida"], 2) for d in labels]
    return {
        "tipo": "line",
        "dados": {
            "labels": labels,
            "datasets": [
                {
                    "label": "Entradas",
                    "data": entradas,
                    "borderColor": "#22c55e",
                    "backgroundColor": "rgba(34,197,94,0.18)",
                    "tension": 0.25,
                    "fill": False,
                },
                {
                    "label": "Saídas",
                    "data": saidas,
                    "borderColor": "#ef4444",
                    "backgroundColor": "rgba(239,68,68,0.18)",
                    "tension": 0.25,
                    "fill": False,
                },
            ],
        },
    }


def _tool_trace_reason(
    *,
    status: str | None,
    code: str | None,
    error: str | None,
) -> str | None:
    """Retorna um motivo curto e estável para renderização no trace."""
    if status == "ok":
        return None
    if status == "pending":
        return "requires_confirmation"
    code_norm = str(code or "").strip().lower()
    err_norm = str(error or "").strip().lower()
    if code_norm:
        if code_norm == "exception":
            if "sqlalche.me/e/20/f405" in err_norm or (
                "group by" in err_norm and "order by" in err_norm
            ):
                return "group_by_order_by_conflict"
        return code_norm
    if "sqlalche.me/e/20/f405" in err_norm or (
        "group by" in err_norm and "order by" in err_norm
    ):
        return "group_by_order_by_conflict"
    if status:
        return str(status).strip().lower()
    return "unknown_error"


def _wants_all_orcamentos(mensagem: str) -> bool:
    txt = str(mensagem or "").lower()
    # "orçamentos" (ç) não contém o substring "orcament"; cobrir PT-BR e ASCII.
    if "orcament" not in txt and "orçament" not in txt:
        return False
    if bool(re.search(r"\b(todos|todas|tudo|completo|inteiro)\b", txt)):
        return True
    if "lista completa" in txt or "sem limite" in txt or "sem limites" in txt:
        return True
    if re.search(r"\btodos os or[cç]amentos\b", txt):
        return True
    return False


def _wants_all_clientes(mensagem: str) -> bool:
    txt = str(mensagem or "").lower()
    if "cliente" not in txt:
        return False
    if bool(re.search(r"\b(todos|todas|tudo|completo|inteiro)\b", txt)):
        return True
    if "lista completa" in txt or "sem limite" in txt or "sem limites" in txt:
        return True
    if re.search(r"\btodos os clientes\b", txt):
        return True
    return False


def _tool_call_args(tc: dict[str, Any]) -> dict[str, Any]:
    fn = tc.get("function") or {}
    raw = fn.get("arguments")
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return {}
        try:
            parsed = json.loads(s)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


async def _autopaginate_listar_orcamentos(
    *,
    mensagem: str,
    tc: dict[str, Any],
    result: Any,
    tool_execute: Any,
    db: Session,
    current_user: Any,
    sessao_id: str,
    request_id: Optional[str],
    confirmation_token: Optional[str],
    engine: str = DEFAULT_ENGINE,
) -> Any:
    tool_name = ((tc.get("function") or {}).get("name") or "").strip()
    if tool_name != "listar_orcamentos":
        return result
    if not _wants_all_orcamentos(mensagem):
        return result
    if not result or getattr(result, "status", None) != "ok":
        return result
    data = getattr(result, "data", None)
    if not isinstance(data, dict):
        return result
    if not data.get("has_more") or not data.get("next_cursor"):
        return result

    args_base = _tool_call_args(tc)
    if not args_base:
        return result

    itens = list(data.get("orcamentos") or [])
    cursor = data.get("next_cursor")
    max_items = 50
    max_paginas = 6
    paginas = 0
    lat_extra = 0

    while cursor and paginas < max_paginas and len(itens) < max_items:
        prox_args = dict(args_base)
        prox_args["cursor"] = cursor
        if "limit" not in prox_args:
            prox_args["limit"] = data.get("limit") or 10

        tc_prox = {
            "id": tc.get("id"),
            "type": "function",
            "function": {
                "name": "listar_orcamentos",
                "arguments": json.dumps(prox_args, ensure_ascii=False),
            },
        }
        prox_result = await tool_execute(
            tc_prox,
            db=db,
            current_user=current_user,
            sessao_id=sessao_id,
            request_id=request_id,
            confirmation_token=confirmation_token,
            engine=engine,
        )
        lat_extra += int(getattr(prox_result, "latencia_ms", 0) or 0)
        if getattr(prox_result, "status", None) != "ok":
            break
        prox_data = getattr(prox_result, "data", None)
        if not isinstance(prox_data, dict):
            break

        itens.extend(list(prox_data.get("orcamentos") or []))
        cursor = prox_data.get("next_cursor")
        data["has_more"] = bool(prox_data.get("has_more"))
        data["next_cursor"] = cursor
        paginas += 1
        if not prox_data.get("has_more"):
            break

    if paginas > 0:
        data["orcamentos"] = itens[:max_items]
        data["itens_retornados"] = len(data["orcamentos"])
        data["auto_paginated"] = True
        data["auto_paginated_paginas"] = paginas
        result.data = data
        result.latencia_ms = int(getattr(result, "latencia_ms", 0) or 0) + lat_extra
    return result


async def _autopaginate_listar_clientes(
    *,
    mensagem: str,
    tc: dict[str, Any],
    result: Any,
    tool_execute: Any,
    db: Session,
    current_user: Any,
    sessao_id: str,
    request_id: Optional[str],
    confirmation_token: Optional[str],
    engine: str = DEFAULT_ENGINE,
) -> Any:
    tool_name = ((tc.get("function") or {}).get("name") or "").strip()
    if tool_name != "listar_clientes":
        return result
    if not _wants_all_clientes(mensagem):
        return result
    if not result or getattr(result, "status", None) != "ok":
        return result

    data = getattr(result, "data", None)
    if not isinstance(data, dict):
        return result
    clientes = list(data.get("clientes") or [])

    args_base = _tool_call_args(tc)
    limit_atual_raw = args_base.get("limit")
    try:
        limit_atual = int(limit_atual_raw) if limit_atual_raw is not None else len(clientes)
    except Exception:
        limit_atual = len(clientes)

    # Quando o usuário pede "todos", o LLM deve receber a lista completa retornada,
    # sem preview de 10 linhas no payload da role=tool.
    data["_llm_disable_preview"] = True
    result.data = data

    if limit_atual >= 50:
        return result

    prox_args = dict(args_base)
    prox_args["limit"] = 50
    tc_prox = {
        "id": tc.get("id"),
        "type": "function",
        "function": {
            "name": "listar_clientes",
            "arguments": json.dumps(prox_args, ensure_ascii=False),
        },
    }
    prox_result = await tool_execute(
        tc_prox,
        db=db,
        current_user=current_user,
        sessao_id=sessao_id,
        request_id=request_id,
        confirmation_token=confirmation_token,
        engine=engine,
    )
    if getattr(prox_result, "status", None) != "ok":
        return result
    prox_data = getattr(prox_result, "data", None)
    if not isinstance(prox_data, dict):
        return result

    prox_data["_llm_disable_preview"] = True
    prox_data["auto_paginated"] = True
    prox_data["auto_paginated_paginas"] = 1
    result.data = prox_data
    result.latencia_ms = int(getattr(result, "latencia_ms", 0) or 0) + int(
        getattr(prox_result, "latencia_ms", 0) or 0
    )
    return result


async def _autopaginate_tool_result(
    *,
    mensagem: str,
    tc: dict[str, Any],
    result: Any,
    tool_execute: Any,
    db: Session,
    current_user: Any,
    sessao_id: str,
    request_id: Optional[str],
    confirmation_token: Optional[str],
    engine: str = DEFAULT_ENGINE,
) -> Any:
    result = await _autopaginate_listar_orcamentos(
        mensagem=mensagem,
        tc=tc,
        result=result,
        tool_execute=tool_execute,
        db=db,
        current_user=current_user,
        sessao_id=sessao_id,
        request_id=request_id,
        confirmation_token=confirmation_token,
        engine=engine,
    )
    result = await _autopaginate_listar_clientes(
        mensagem=mensagem,
        tc=tc,
        result=result,
        tool_execute=tool_execute,
        db=db,
        current_user=current_user,
        sessao_id=sessao_id,
        request_id=request_id,
        confirmation_token=confirmation_token,
        engine=engine,
    )
    return result


async def assistente_unificado_v2(
    *,
    mensagem: str,
    sessao_id: str,
    db: Session,
    current_user: Any,  # Usuario; importado lazy para evitar ciclo
    engine: str = DEFAULT_ENGINE,
    request_id: Optional[str] = None,
    confirmation_token: Optional[str] = None,
    override_args: Optional[dict] = None,
) -> AIResponse:
    """Wrapper de orquestração (LangGraph opcional com fallback legado)."""
    from app.services.assistant_langgraph import langgraph_enabled, run_assistant_graph
    from app.services.assistant_autonomy import (
        semantic_autonomy_enabled,
        try_handle_semantic_autonomy,
    )

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
        return AIResponse(
            sucesso=True,
            resposta=resposta,
            tipo_resposta="onboarding",
            dados=status,
            confianca=1.0,
            modulo_origem="onboarding",
        )

    if _v2_is_saldo_rapido_message(mensagem):
        resposta = await _v2_build_saldo_fastpath_response(
            db=db,
            empresa_id=getattr(current_user, "empresa_id", 0),
        )
        _v2_persist_fastpath_response(
            sessao_id=sessao_id,
            db=db,
            current_user=current_user,
            resposta=resposta.resposta or "",
        )
        return resposta

    if _v2_is_dashboard_financeiro_message(mensagem):
        resposta = await _v2_build_dashboard_fastpath_response(
            db=db,
            empresa_id=getattr(current_user, "empresa_id", 0),
        )
        _v2_persist_fastpath_response(
            sessao_id=sessao_id,
            db=db,
            current_user=current_user,
            resposta=resposta.resposta or "",
        )
        return resposta

    if _v2_is_clientes_devendo_message(mensagem):
        resposta = await _v2_build_inadimplencia_fastpath_response(
            db=db,
            empresa_id=getattr(current_user, "empresa_id", 0),
        )
        _v2_persist_fastpath_response(
            sessao_id=sessao_id,
            db=db,
            current_user=current_user,
            resposta=resposta.resposta or "",
        )
        return resposta

    if _v2_is_orcamento_fastpath_message(mensagem):
        resposta = await _v2_build_orcamento_fastpath_response(
            mensagem=mensagem,
            db=db,
            empresa_id=getattr(current_user, "empresa_id", 0),
            usuario_id=getattr(current_user, "id", 0),
        )
        _v2_persist_fastpath_response(
            sessao_id=sessao_id,
            db=db,
            current_user=current_user,
            resposta=resposta.resposta or "",
        )
        return resposta

    # OPERADOR fast-path: aprovar/recusar/ver/enviar com ID explícito → 0 tokens LLM
    if _v2_is_operador_fastpath_message(mensagem):
        resposta_op = await _v2_build_operador_fastpath_response(
            mensagem=mensagem,
            db=db,
            current_user=current_user,
            sessao_id=sessao_id,
            request_id=request_id,
        )
        if resposta_op is not None:
            _v2_persist_fastpath_response(
                sessao_id=sessao_id,
                db=db,
                current_user=current_user,
                resposta=resposta_op.resposta or "",
            )
            return resposta_op

    if (
        semantic_autonomy_enabled()
        and resolve_engine(engine) != ENGINE_INTERNAL_COPILOT
    ):
        try:
            semantic_payload = await try_handle_semantic_autonomy(
                mensagem=mensagem,
                sessao_id=sessao_id,
                db=db,
                current_user=current_user,
                engine=engine,
                request_id=request_id,
                confirmation_token=confirmation_token,
                override_args=override_args,
            )
            if isinstance(semantic_payload, dict) and semantic_payload:
                return AIResponse(**semantic_payload)
        except Exception as exc:
            logger.warning(
                "Falha no runtime semântico, fallback para fluxo legado: %s", exc
            )

    payload = {
        "mensagem": mensagem,
        "sessao_id": sessao_id,
        "db": db,
        "current_user": current_user,
        "engine": engine,
        "request_id": request_id,
        "confirmation_token": confirmation_token,
        "override_args": override_args,
    }
    if not langgraph_enabled():
        return await _assistente_unificado_v2_legacy(**payload)

    async def _legacy_runner(state: dict[str, Any]) -> AIResponse:
        return await _assistente_unificado_v2_legacy(**state)

    return await run_assistant_graph(payload=payload, legacy_runner=_legacy_runner)


async def _assistente_unificado_v2_legacy(
    *,
    mensagem: str,
    sessao_id: str,
    db: Session,
    current_user: Any,  # Usuario; importado lazy para evitar ciclo
    engine: str = DEFAULT_ENGINE,
    request_id: Optional[str] = None,
    confirmation_token: Optional[str] = None,
    override_args: Optional[dict] = None,
) -> AIResponse:
    """Loop de Tool Use sobre `ia_service.chat` (LiteLLM/OpenAI format).

    Mantém histórico via `SessionStore`. Limite de 5 iterações.
    """
    from app.services.assistant_preferences_service import AssistantPreferencesService
    from app.services.cotte_context_builder import SessionStore, SemanticMemoryStore
    from app.services.ia_service import ia_service
    from app.services.tool_executor import execute as tool_execute
    from app.services.tool_executor import execute_pending

    resolved_engine = resolve_engine(engine)
    engine_policy = get_engine_policy(resolved_engine)

    if _v2_is_excel_chart_request(mensagem):
        resposta_excel = (
            "Hoje eu não gero arquivo Excel diretamente pelo chat. "
            "Consigo te entregar os dados e o gráfico financeiro aqui no assistente, "
            "e você exporta para planilha com segurança."
        )
        SessionStore.append_db(
            sessao_id,
            "assistant",
            resposta_excel,
            db,
            empresa_id=getattr(current_user, "empresa_id", 0),
            usuario_id=getattr(current_user, "id", 0),
        )
        return AIResponse(
            sucesso=True,
            resposta=resposta_excel,
            confianca=0.98,
            modulo_origem="assistente_v2",
            dados={"capability": "excel_nao_suportado"},
        )

    if _v2_is_customer_revenue_ranking_unavailable_request(mensagem):
        resposta = _v2_customer_revenue_ranking_unavailable_response()
        SessionStore.append_db(
            sessao_id,
            "assistant",
            resposta,
            db,
            empresa_id=getattr(current_user, "empresa_id", 0),
            usuario_id=getattr(current_user, "id", 0),
        )
        return AIResponse(
            sucesso=True,
            resposta=resposta,
            confianca=0.98,
            modulo_origem="assistente_v2",
            dados={"capability": "ranking_clientes_indisponivel"},
        )

    if _v2_is_financial_chart_request(mensagem):
        dias = _v2_extract_days_window(mensagem)
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
        tc_saldo = {
            "id": "chart_saldo",
            "type": "function",
            "function": {"name": "obter_saldo_caixa", "arguments": "{}"},
        }
        res_mov = await tool_execute(
            tc_mov,
            db=db,
            current_user=current_user,
            sessao_id=sessao_id,
            request_id=request_id,
            engine=resolved_engine,
        )
        res_saldo = await tool_execute(
            tc_saldo,
            db=db,
            current_user=current_user,
            sessao_id=sessao_id,
            request_id=request_id,
            engine=resolved_engine,
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
        return AIResponse(
            sucesso=True,
            resposta=final_text,
            confianca=0.95 if grafico else 0.8,
            modulo_origem="assistente_v2",
            tipo_resposta="financeiro",
            tool_trace=[
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
            dados={
                "dias": dias,
                "movimentacoes_total": qtd,
                "saldo_atual": saldo_atual,
                "grafico": grafico,
            },
        )

    # ── Fast-path: confirmação de ação destrutiva ────────────────────────
    # Quando o usuário clica "Confirmar" no card, o frontend reenvia a
    # mensagem original + confirmation_token. Não passamos pelo LLM —
    # executamos exatamente a ação que foi proposta (args travados no token).
    if confirmation_token:
        try:
            result = await execute_pending(
                confirmation_token,
                db=db,
                current_user=current_user,
                sessao_id=sessao_id,
                request_id=request_id,
                override_args=override_args,
                engine=resolved_engine,
            )
            if result.status == "ok":
                orc_data = result.data or {}
                if orc_data.get("numero"):
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
                        final_text = "✅ Orçamento criado com sucesso."
                        tipo_resp = "orcamento_criado"
                    num = orc_data.get("numero", "")
                    acao_sug = f'["Duplicar {num}"]'
                    resp_dados = orc_data
                else:
                    final_text = "✅ Ação concluída com sucesso."
                    tipo_resp = None
                    acao_sug = None
                    resp_dados = {"input_tokens": 0, "output_tokens": 0}
            elif result.status == "forbidden":
                final_text = f"❌ Sem permissão: {result.error}"
                tipo_resp = None
                acao_sug = None
                resp_dados = {"input_tokens": 0, "output_tokens": 0}
            else:
                final_text = (
                    f"❌ Não consegui concluir a ação: {result.error or result.status}"
                )
                tipo_resp = None
                acao_sug = None
                resp_dados = {"input_tokens": 0, "output_tokens": 0}
            tool_trace_out = [
                {
                    "tool": "(confirmação)",
                    "status": result.status,
                    "latencia_ms": result.latencia_ms,
                    "data": result.data,
                    "error": result.error,
                }
            ]
        except Exception as e:
            import logging as _lg

            _lg.getLogger(__name__).exception("Falha no fast-path de confirmação")
            try:
                db.rollback()
            except Exception:
                pass
            final_text = f"❌ Erro ao processar a confirmação: {e}"
            tool_trace_out = [
                {"tool": "(confirmação)", "status": "erro", "error": str(e)}
            ]
            tipo_resp = None
            acao_sug = None
            resp_dados = {"input_tokens": 0, "output_tokens": 0}

        SessionStore.append(
            sessao_id,
            "assistant",
            final_text,
            empresa_id=getattr(current_user, "empresa_id", 0),
            usuario_id=getattr(current_user, "id", 0),
        )
        return AIResponse(
            sucesso=True,
            resposta=final_text,
            tipo_resposta=tipo_resp,
            acao_sugerida=acao_sug,
            confianca=0.95,
            modulo_origem="assistente_v2",
            pending_action=None,
            tool_trace=tool_trace_out,
            dados=resp_dados,
        )

    now = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%d %H:%M")
    # Recupera histórico com recovery automático do banco pós-reinício
    history = SessionStore.get_or_create(
        sessao_id,
        db=db,
        empresa_id=getattr(current_user, "empresa_id", 0),
        usuario_id=getattr(current_user, "id", 0),
    )
    # Garante que a sessão existe no banco para habilitar persistência
    SessionStore.ensure_sessao_db(
        sessao_id=sessao_id,
        empresa_id=getattr(current_user, "empresa_id", 0),
        usuario_id=getattr(current_user, "id", 0),
        db=db,
    )

    system_prompt, prompt_strategy = _v2_build_system_prompt(
        mensagem=mensagem,
        resolved_engine=resolved_engine,
        now=now,
    )
    allow_context_enrichment = prompt_strategy != "minimal"

    semantic_ctx = {}
    rag_ctx = {}
    adaptive_ctx = {}
    code_ctx = {}
    if engine_policy.allow_business_context and allow_context_enrichment:
        semantic_ctx = SemanticMemoryStore.build_context(
            db=db,
            empresa_id=getattr(current_user, "empresa_id", 0),
            mensagem=mensagem,
            usuario_id=getattr(current_user, "id", 0),
        )
        adaptive_ctx = AssistantPreferencesService.get_context_for_prompt(
            db=db,
            empresa_id=getattr(current_user, "empresa_id", 0),
            usuario_id=getattr(current_user, "id", 0),
            mensagem=mensagem,
        )
    if engine_policy.allow_tenant_rag and allow_context_enrichment:
        try:
            from app.services.rag import TenantRAGService

            rag_ctx = TenantRAGService.build_prompt_context(
                db=db,
                empresa_id=getattr(current_user, "empresa_id", 0),
                query=mensagem,
                top_k=4,
            )
        except Exception:
            rag_ctx = {}
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
        "visualizacao_recomendada": adaptive_ctx.get("preferencia_visualizacao_usuario")
        or {},
        "playbook_setor": adaptive_ctx.get("playbook_setor") or {},
    }

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
    # SessionStore historiza apenas role+content (sem tool_calls). Mantemos como hint.
    history_window = _v2_history_window_size(
        prompt_strategy=prompt_strategy,
        mensagem=mensagem,
    )
    for h in history[-history_window:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": mensagem})
    logger.info(
        "[assistente_v2] engine=%s prompt_strategy=%s system_chars=%s history=%s",
        resolved_engine,
        prompt_strategy,
        len(system_prompt),
        history_window,
    )

    # Persiste mensagem do usuário no banco
    SessionStore.append_db(
        sessao_id,
        "user",
        mensagem,
        db,
        empresa_id=getattr(current_user, "empresa_id", 0),
        usuario_id=getattr(current_user, "id", 0),
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
    tool_trace: list[dict] = []
    pending_action: Optional[dict] = None
    total_in = 0
    total_out = 0
    final_text: Optional[str] = None
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
            return AIResponse(
                sucesso=False,
                resposta="A consulta exigiu volume de dados além do limite seguro. Seja mais específico.",
                tipo_resposta="erro",
                confianca=0.0,
                modulo_origem="assistente_v2",
            )

        try:
            resp = await ia_service.chat(
                messages=messages,
                tools=tools_payload,
                temperature=0.3,
                max_tokens=1024,
                model_override=modelo_injetado,
            )
        except Exception as e:
            logger.exception("Falha na chamada ia_service.chat (v2)")
            return AIResponse(
                sucesso=False,
                resposta=f"Erro ao consultar assistente: {e}",
                confianca=0.0,
                modulo_origem="assistente_v2",
                erros=[str(e)],
            )

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
                            messages=messages,
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

            if pending_action:
                final_text = ""
                break
            # Próxima iteração: LLM verá os tool results
            continue

        # Sem tool_calls → resposta final
        final_text = (
            msg.get("content")
            if isinstance(msg, dict)
            else getattr(msg, "content", None)
        ) or ""
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

    return AIResponse(
        sucesso=True,
        resposta=final_text or "",
        confianca=0.9 if final_text else 0.4,
        modulo_origem="assistente_v2",
        pending_action=pending_action,
        tool_trace=tool_trace or None,
        dados=dados_out,
    )
