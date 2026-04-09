"""
COTTE AI Hub - Sistema centralizado de IA com validação robusta anti-delírios
Refatoração Senior 2025: Performance, Modularidade e Robustez

Melhorias implementadas:
1. Extração de JSON robusta com Regex (ai_json_extractor)
2. Queries agregadas SQLAlchemy func.sum (anti-bloqueio)
3. Prompts externalizados (ai_prompt_loader)
4. Classificador de intenção híbrido Regex+Haiku (ai_intention_classifier)
"""

import json
import re
import hashlib
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Any, Literal

_TZ_BR = ZoneInfo("America/Sao_Paulo")
from functools import wraps
from decimal import Decimal

import anthropic
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from sqlalchemy.future import select
from pydantic import BaseModel, Field, validator

from app.core.config import settings

# Importar novos módulos refatorados
from app.services.ai_json_extractor import AIJSONExtractor
from app.services.ai_prompt_loader import get_prompt_loader, load_prompts
from app.services.ai_intention_classifier import (
    get_intention_classifier,
    IntencaoUsuario,
    detectar_intencao_assistente,
    detectar_intencao_assistente_async,
)

logger = logging.getLogger(__name__)

# ── Configuração dos Modelos ───────────────────────────────────────────────

class _LazyAnthropicClient:
    """Wrapper lazy: instancia o client Anthropic só no primeiro uso real.

    Mantém compatibilidade com chamadas legadas a `client.messages.create(...)` sem
    explodir no import quando ANTHROPIC_API_KEY não está configurada (caso atual:
    o sistema migrou para LiteLLM/OpenAI via `ia_service`). Se uma rota legada
    realmente chamar Anthropic sem a chave, o erro será claro e local.
    """

    _real = None

    def _build(self):
        import os
        key = os.getenv("ANTHROPIC_API_KEY") or getattr(settings, "ANTHROPIC_API_KEY", None)
        if not key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY não configurada — esta rota legada ainda usa "
                "anthropic.Anthropic. Migre para ia_service ou defina a variável."
            )
        self._real = anthropic.Anthropic(api_key=key)
        return self._real

    def __getattr__(self, item):
        return getattr(self._real or self._build(), item)


client = _LazyAnthropicClient()

SONNET = "claude-sonnet-4-20250514"
HAIKU = "claude-haiku-4-5-20251001"

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


# ── Cache Inteligente ──────────────────────────────────────────────────────


class SimpleCache:
    """Cache TTL simples para reduzir chamadas à API"""

    def __init__(self, ttl_seconds: int = 300):
        self._cache = {}
        self._ttl = ttl_seconds

    def _generate_key(self, modulo: str, mensagem: str) -> str:
        """Gera chave única baseada no conteúdo"""
        content = f"{modulo}:{mensagem.lower().strip()}"
        return hashlib.md5(content.encode()).hexdigest()

    def get(self, modulo: str, mensagem: str) -> Optional[AIResponse]:
        key = self._generate_key(modulo, mensagem)
        if key in self._cache:
            entry = self._cache[key]
            if datetime.now() < entry["expires_at"]:
                entry["data"].cache_hit = True
                return entry["data"]
            del self._cache[key]
        return None

    def set(self, modulo: str, mensagem: str, response: AIResponse):
        key = self._generate_key(modulo, mensagem)
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
        "model": SONNET,
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
        "model": SONNET,
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
        "model": HAIKU,
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
        "model": HAIKU,
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
        "model": HAIKU,
    },
    "conversacao": {
        "system": """Você é o assistente virtual do COTTE. Responda de forma amigável e profissional.

REGRAS:
1. Seja breve e direto (máximo 2-3 frases)
2. Use tom profissional mas caloroso
3. Sempre ofereça ajuda concreta quando possível
4. Se não souber, seja honesto e sugere falar com um humano""",
        "max_tokens": 120,
        "model": HAIKU,
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
        "model": SONNET,
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
        "model": SONNET,
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
        "model": SONNET,
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

        # Extrair valor monetário
        padroes_valor = [
            r"R?\$?\s*(\d+[.,]?\d*)",
            r"(\d+)\s*reais?",
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

        # Extrair serviços comuns
        servicos = [
            "pintura",
            "reforma",
            "elétrica",
            "hidráulica",
            "gesso",
            "piso",
            "azulejo",
            "telhado",
        ]
        for servico in servicos:
            if servico in mensagem.lower():
                resultado["servico"] = servico
                break

        # Extrair nome (após "para", "cliente", etc.)
        padroes_nome = [
            r"para\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            r"cliente\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            r"do\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        ]
        for padrao in padroes_nome:
            match = re.search(padrao, mensagem)
            if match:
                resultado["cliente_nome"] = match.group(1)
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
        match = re.search(r"(?:O-|ORC-|orçamento\s*|orc\s*)(\d+)", mensagem, re.IGNORECASE)
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
        if usar_cache:
            cached = self.cache.get(modulo, mensagem_limpa)
            if cached:
                return cached

        # ── Chamada à IA ──────────────────────────────────────────────────────
        try:
            # Usar PromptLoader para obter configuração atualizada
            config = _prompt_loader.get_dict(modulo)

            # Construir mensagem com contexto (se disponível)
            mensagem_completa = self._construir_mensagem_com_contexto(
                modulo, mensagem_limpa, contexto
            )

            response = client.messages.create(
                model=config["model"],
                max_tokens=config["max_tokens"],
                system=config["system"],
                messages=[{"role": "user", "content": mensagem_completa}],
            )

            raw = response.content[0].text.strip()

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

        resultado = AIResponse(
            sucesso=sucesso,
            dados=dados_validados,
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
            self.cache.set(modulo, mensagem_limpa, resultado)

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
            response = client.messages.create(
                model=HAIKU, max_tokens=600, system=system_prompt, messages=messages
            )
            return response.content[0].text.strip()
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
    from app.models.models import Cliente

    # 1. Extrair dados via módulo "orcamentos"
    resultado = await ai_hub.processar("orcamentos", mensagem)
    if not resultado.sucesso or not resultado.dados:
        return AIResponse(
            sucesso=False,
            resposta="Não entendi os dados do orçamento. Tente: 'Orçamento de pintura para João Silva, R$ 800'",
            tipo_resposta="erro",
            confianca=0.0,
            modulo_origem="criar_orcamento",
        )

    dados = resultado.dados
    cliente_nome = (dados.get("cliente_nome") or "").strip()

    # 2. Buscar cliente no banco
    cliente_match = None
    clientes_sugeridos = []
    _cliente_auto_criado = False

    if cliente_nome and cliente_nome.lower() != "a definir":
        # 1) Busca exata (ilike)
        cliente_match = (
            db.query(Cliente)
            .filter(
                Cliente.empresa_id == empresa_id,
                Cliente.nome.ilike(cliente_nome),
            )
            .first()
        )
        # 2) Busca ampla (contém)
        if not cliente_match:
            cliente_match = (
                db.query(Cliente)
                .filter(
                    Cliente.empresa_id == empresa_id,
                    Cliente.nome.ilike(f"%{cliente_nome}%"),
                )
                .first()
            )
        # 3) Não encontrou nenhum — cadastrar automaticamente
        if not cliente_match:
            from app.schemas.schemas import ClienteCreate
            from app.services.cliente_service import ClienteService
            from app.models.models import Usuario as _Usuario

            _usuario_fake = db.query(_Usuario).filter(_Usuario.empresa_id == empresa_id).first()
            if _usuario_fake:
                novo_cliente = ClienteService(db).criar_cliente(
                    ClienteCreate(nome=cliente_nome.strip()), _usuario_fake
                )
                db.flush()
                cliente_match = novo_cliente
                _cliente_auto_criado = True


    # 3. Montar preview
    preview = {
        "cliente_nome": cliente_match.nome if cliente_match else (cliente_nome or "A definir"),
        "cliente_id": cliente_match.id if cliente_match else None,
        "cliente_encontrado": cliente_match is not None,
        "cliente_auto_criado": _cliente_auto_criado,
        "clientes_sugeridos": [],
        "servico": dados.get("servico") or "",
        "valor": float(dados.get("valor") or 0),
        "desconto": float(dados.get("desconto") or 0),
        "desconto_tipo": dados.get("desconto_tipo") or "percentual",
        "observacoes": dados.get("observacoes"),
        "confianca": float(dados.get("confianca") or 0.5),
        "empresa_id": empresa_id,
        "usuario_id": usuario_id,
    }

    if cliente_match and _cliente_auto_criado:
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
    from app.services.quote_notification_service import handle_quote_status_changed
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
        itens_txt = (
            "\n".join(
                f"  {i + 1}. {it.descricao} — R$ {it.total:.2f}"
                for i, it in enumerate(orc.itens)
            )
            if orc.itens
            else "  (sem itens)"
        )
        desc_txt = ""
        if orc.desconto and orc.desconto > 0:
            sufixo = "%" if orc.desconto_tipo == "percentual" else " R$"
            desc_txt = f" · Desconto: {orc.desconto:.0f}{sufixo}"
        return AIResponse(
            sucesso=True,
            resposta=f"Orçamento {orc.numero} — {orc.cliente.nome if orc.cliente else '?'} — R$ {orc.total:.2f} — {orc.status.value}",
            tipo_resposta="operador_resultado",
            dados={
                "acao": "VER",
                "numero": orc.numero,
                "cliente": orc.cliente.nome if orc.cliente else "—",
                "total": float(orc.total or 0),
                "status": orc.status.value,
                "id": orc.id,
                "itens": [
                    {"descricao": it.descricao, "total": float(it.total)}
                    for it in orc.itens
                ],
                "forma_pagamento": orc.forma_pagamento.value
                if orc.forma_pagamento
                else "",
                "validade_dias": orc.validade_dias or 0,
                "observacoes": orc.observacoes or "",
                "link_publico": orc.link_publico or "",
                "tem_telefone": bool(orc.cliente and orc.cliente.telefone),
                "tem_email": bool(orc.cliente and orc.cliente.email),
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
            from app.utils.pdf_utils import get_orcamento_dict_for_pdf, get_empresa_dict_for_pdf
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
    "SALDO_RAPIDO", "FATURAMENTO", "CONTAS_RECEBER", "CONTAS_PAGAR",
    "DASHBOARD", "PREVISAO", "INADIMPLENCIA", "ANALISE",
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
    4. Chama Claude Sonnet com contexto completo + histórico
    5. Persiste o turno na sessão
    6. Retorna AIResponse estruturado
    """
    from app.services.cotte_context_builder import SessionStore, ContextBuilder

    # 1. Histórico da sessão (últimas 6 mensagens)
    historico = SessionStore.get_or_create(sessao_id)

    # 2. Classificar intenção (regex + Haiku como fallback)
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

    # Roteamento especial: criação de orçamento (não passa pelo Claude genérico)
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

    # 3. Buscar contexto de dados relevante
    contexto = await ContextBuilder.build(
        intencao, db, empresa_id, usuario_id=usuario_id, mensagem=mensagem
    )

    # 4. Montar conteúdo da mensagem do usuário (com dados injetados)
    agora = datetime.now(_TZ_BR)
    cabecalho = f"Hoje: {agora.strftime('%A, %d/%m/%Y')} às {agora.strftime('%H:%M')}"
    # Contexto de ajuda usa bloco separado [DOCUMENTAÇÃO DO SISTEMA]
    doc_sistema = contexto.pop("documentacao_sistema", None) if contexto else None
    if contexto:
        user_content = (
            f"{mensagem}\n\n[DADOS DO SISTEMA]\n{cabecalho}\n"
            f"{json.dumps(contexto, ensure_ascii=False, default=str)}"
        )
    else:
        user_content = f"{mensagem}\n\n[DADOS DO SISTEMA]\n{cabecalho}"
    if doc_sistema:
        user_content += f"\n\n[DOCUMENTAÇÃO DO SISTEMA]\n{doc_sistema}"

    messages = historico + [{"role": "user", "content": user_content}]

    # 5. Chamar Claude Sonnet
    try:
        response = client.messages.create(
            model=SONNET,
            max_tokens=800,
            system=SYSTEM_PROMPT_ASSISTENTE,
            messages=messages,
        )
        raw = response.content[0].text.strip()

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
            sessao_id, sugestoes_originais
        )
        if sugestoes_novas:
            SessionStore.add_seen_suggestions(sessao_id, sugestoes_novas)

        # 6. Persistir turno (mensagem limpa, sem o bloco de dados)
        SessionStore.append(sessao_id, "user", mensagem)
        SessionStore.append(sessao_id, "assistant", resposta_texto)

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
        logger.error(f"[assistente_unificado] Erro ao chamar Claude: {e}")
        return AIResponse(
            sucesso=False,
            resposta="Não consegui processar sua mensagem. Tente novamente.",
            tipo_resposta="erro",
            confianca=0.0,
            erros=[str(e)],
            modulo_origem="assistente_unificado",
        )


async def assistente_unificado_stream(
    mensagem: str,
    sessao_id: str,
    db: Session,
    empresa_id: int,
    usuario_id: int = 0,
    permissoes: dict | None = None,
    is_gestor: bool = False,
):
    from app.models.models import AIChatSessao, AIChatMensagem
    from app.services.cotte_context_builder import ContextBuilder
    from app.services.ai_intention_classifier import detectar_intencao_assistente_async
    import json
    import os

    # 1. Obter Sessao e Histórico no DB
    sessao = db.query(AIChatSessao).filter(AIChatSessao.id == sessao_id).first()
    if not sessao:
        sessao = AIChatSessao(id=sessao_id, empresa_id=empresa_id, usuario_id=usuario_id)
        db.add(sessao)
        db.commit()
    
    historico_mensagens = db.query(AIChatMensagem).filter(AIChatMensagem.sessao_id == sessao_id).order_by(AIChatMensagem.criado_em.asc()).all()
    # Pega ultimas 10 msgs para evitar sobrecarga de contexto
    historico = [{"role": msg.role, "content": msg.content} for msg in historico_mensagens][-10:]

    msg_user = AIChatMensagem(sessao_id=sessao_id, role="user", content=mensagem)
    db.add(msg_user)
    db.commit()

    # 2. Interpretação + ContextBuilder
    try:
        classificacao = await detectar_intencao_assistente_async(mensagem)
        intencao = classificacao.intencao.value
    except Exception:
        intencao = "CONVERSACAO"

    # Bloqueio de finanças
    _perms = permissoes or {}
    _nivel_fin = _perms.get("financeiro")
    _tem_financeiro = is_gestor or bool(_nivel_fin)
    if intencao in _INTENCOES_FINANCEIRAS and not _tem_financeiro:
        yield f"data: {json.dumps({'chunk': 'Você não tem acesso ao módulo financeiro. Fale com o gestor da sua conta.', 'is_final': True})}\n\n"
        return

    # Roteamento especial
    fast_response = None
    if intencao == "CRIAR_ORCAMENTO":
        fast_response = await criar_orcamento_ia(mensagem=mensagem, db=db, empresa_id=empresa_id, usuario_id=usuario_id)
    elif intencao == "SALDO_RAPIDO":
        from app.services.ai_intention_classifier import saldo_rapido_ia
        fast_response = await saldo_rapido_ia(db=db, empresa_id=empresa_id)
    elif intencao == "OPERADOR":
        fast_response = await executar_comando_operador_ia(mensagem=mensagem, db=db, empresa_id=empresa_id, usuario_id=usuario_id)
    elif intencao == "ONBOARDING":
        from app.services.onboarding_service import get_onboarding_status, formatar_resposta_onboarding
        status = get_onboarding_status(db=db, empresa_id=empresa_id)
        fast_response = AIResponse(sucesso=True, resposta=formatar_resposta_onboarding(status), tipo_resposta="onboarding", dados=status, confianca=1.0, modulo_origem="onboarding")
    elif intencao == "CONVERSACAO":
        # Onboarding não bloqueia mais o assistente — IA responde normalmente
        pass

    if fast_response:
        import asyncio
        msg_ast = AIChatMensagem(sessao_id=sessao_id, role="assistant", content=fast_response.resposta)
        db.add(msg_ast)
        db.commit()
        
        texto_parts = fast_response.resposta.split(' ')
        for word in texto_parts:
            yield f"data: {json.dumps({'chunk': word + ' '})}\n\n"
            await asyncio.sleep(0.01)
            
        sugs = []
        if getattr(fast_response, "acao_sugerida", None):
            try:
                sugs = json.loads(fast_response.acao_sugerida)
            except:
                pass
                
        metadata = {
            "tipo": fast_response.tipo_resposta,
            "dados": fast_response.dados,
            "sugestoes": sugs
        }
        yield f"data: {json.dumps({'is_final': True, 'metadata': metadata})}\n\n"
        return

    contexto = await ContextBuilder.build(
        intencao, db, empresa_id, usuario_id=usuario_id, mensagem=mensagem
    )

    agora = datetime.now(_TZ_BR)
    cabecalho = f"Hoje: {agora.strftime('%A, %d/%m/%Y')} às {agora.strftime('%H:%M')}"
    
    doc_sistema = contexto.pop("documentacao_sistema", None) if contexto else None
    
    user_content = f"{mensagem}\n\n[DADOS DO SISTEMA]\n{cabecalho}"
    if contexto:
        user_content += f"\n{json.dumps(contexto, ensure_ascii=False, default=str)}"
    if doc_sistema:
        user_content += f"\n\n[DOCUMENTAÇÃO DO SISTEMA]\n{doc_sistema}"

    messages = historico + [{"role": "user", "content": user_content}]

    # Modifica o system prompt em tempo de execução para forçar Markdown e separador
    prompt = SYSTEM_PROMPT_ASSISTENTE.replace(
        "FORMATO DE RESPOSTA OBRIGATÓRIO (JSON):",
        "INSTRUÇÃO IMPORTANTE: RETORNE SUA MENSAGEM PRINCIPAL EM **MARKDOWN FORMATADO**. USE TABELAS MARKDOWN OBRIGATORIAMENTE PARA LISTAS LONGAS OU ARRAYS DE DADOS.\n\nNo final da sua resposta, CASO detecte intenção de analises financeiras/conversão, OU você tiver <sugestoes>, inclua o marcador exato '---JSON_CONFIG---' e em seguida UM JSON VÁLIDO contendo as métricas de grafico e ou sugestoes.\n\nEXEMPLO DA SUA SAÍDA:\nAqui está o resultado...\n| Col A | Col B |\n| --- | --- |\n| 1 | 2 |\n\n---JSON_CONFIG---\n{\"tipo\": \"financeiro\", \"grafico\": {\"tipo\": \"bar\", \"dados\": {\"labels\":[\"A\"], \"datasets\":[{\"label\":\"Vendas\", \"data\":[50]}]}}, \"sugestoes\": [\"O que mais deseja fazer?\"]}\n\nFORMATO DE RESPOSTA OBRIGATÓRIO:"
    ).replace(
        "{\"resposta\": \"texto da resposta para o usuário\", \"tipo\": \"financeiro|orcamentos|clientes|leads|agendamentos|ajuda|geral\", \"dados\": null, \"sugestoes\": [\"até 3 perguntas de acompanhamento relevantes\"]}",
        "O Texto Markdown!"
    )

    import anthropic
    key = os.getenv("ANTHROPIC_API_KEY") or getattr(settings, "ANTHROPIC_API_KEY", None)
    async_client = anthropic.AsyncAnthropic(api_key=key)

    try:
        stream = await async_client.messages.create(
            model=SONNET,
            max_tokens=2500,
            system=prompt,
            messages=messages,
            stream=True
        )

        full_content = ""
        split_marker = "---JSON_CONFIG---"
        is_metadata_phase = False

        async for event in stream:
            if event.type == "content_block_delta":
                chunk = event.delta.text
                full_content += chunk
                
                if split_marker in full_content:
                    if not is_metadata_phase:
                        is_metadata_phase = True
                else:
                    # Yield text chunks avoiding partial split_marker matches locally
                    # For safety we just let frontend append chunk
                    # Small visual glitch if it types '-' then hides is acceptable or we process in parts
                    # We will just yield it since partial markers are rare and fast
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                    
        # Conclusão do stream
        parts = full_content.split(split_marker)
        resposta_markdown = parts[0].strip()
        
        metadata = {}
        if len(parts) > 1:
            try:
                metadata = json.loads(parts[1].strip())
            except Exception as j_err:
                logger.error(f"[stream] Erro parse JSON block: {j_err} -> {parts[1]}")

        # Persistir a mensagem base limpa no DB
        msg_ast = AIChatMensagem(sessao_id=sessao_id, role="assistant", content=resposta_markdown)
        db.add(msg_ast)
        db.commit()

        yield f"data: {json.dumps({'is_final': True, 'metadata': metadata})}\n\n"

    except Exception as e:
        logger.error(f"[stream] Exception: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


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
    mensagem: str, dados_orcamentos: Optional[dict] = None, db: Optional[Session] = None
) -> AIResponse:
    """
    Analisa taxas de conversão de orçamentos

    Args:
        mensagem: Pergunta ou comando do usuário
        dados_orcamentos: Dados de orçamentos para análise
        db: Sessão do banco para buscar dados se não fornecidos
    """
    # Se não tiver dados, buscar do banco
    if not dados_orcamentos and db:
        # TODO: Implementar busca de dados de orçamentos do banco
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
    mensagem: str, dados_empresa: Optional[dict] = None, db: Optional[Session] = None
) -> AIResponse:
    """
    Gera sugestões estratégicas para o negócio

    Args:
        mensagem: Pergunta ou área de interesse
        dados_empresa: Dados da empresa para análise
        db: Sessão do banco para buscar dados se não fornecidos
    """
    # Se não tiver dados, buscar do banco
    if not dados_empresa and db:
        # TODO: Implementar busca de dados da empresa do banco
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
    return await analisar_conversao_ia(mensagem, db=db)


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
    return await analisar_conversao_ia(mensagem, db=db)


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
    return await gerar_sugestoes_negocio_ia(mensagem, db=db)


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

_V2_SYSTEM_PROMPT = (
    "Você é o **Assistente COTTE**, um parceiro inteligente de gestão para pequenas empresas. "
    "Responda sempre em português, de forma direta e amigável. Máximo de 3 parágrafos. "
    "\n\n"
    "## Como funcionar:  \n"
    "Use as ferramentas (tools) disponíveis para buscar informações reais antes de responder. "
    "NUNCA invente números, nomes ou valores — sempre obtenha via tool. "
    "\n\n"
    "## Regras críticas:  \n"
    "1. **Criar/excluir**: chame a tool DIRETAMENTE — o sistema mostrará um card de confirmação. "
    "NÃO pergunte 'deseja prosseguir?' previamente. \n"
    "2. **IDs por conta própria**: para excluir/editar por NOME, chame `listar_clientes(busca=\"nome\")` "
    "primeiro para obter o ID real. NUNCA chute IDs ou use posições de listas anteriores. \n"
    "3. **Sem tool correspondente**: diga claramente que não há ferramenta para isso — "
    "NÃO chame outra tool no lugar. \n"
    "4. **Criar orçamentos**: chame `criar_orcamento` DIRETAMENTE com `cliente_nome` e o item. "
    "NÃO busque o cliente antes, o backend resolve automaticamente. \n"
    "5. **Sem loop**: NUNCA repita a mesma tool call mais de uma vez. Se a resposta não vier "
    "como esperado, explique o que tem e a limitação. \n"
    "6. **Erros de identidade**: se não encontrar um recurso pelo nome/ID exato informado, "
    "EXPLIQUE o motivo e sugira alternativas (ex: 'Não encontrei O-103 — os recentes são X e Y'). "
    "NUNCA diga 'Comando DESCONHECIDO' ou retorne um erro técnico cru. \n"
    "7. **Inteligente mas humilde**: se não tiver certeza, pergunte ao usuário uma "
    "coisa de cada vez, sem listas de perguntas. "
)

_V2_MAX_ITER = 5


async def assistente_unificado_v2(
    *,
    mensagem: str,
    sessao_id: str,
    db: Session,
    current_user: Any,  # Usuario; importado lazy para evitar ciclo
    confirmation_token: Optional[str] = None,
    override_args: Optional[dict] = None,
) -> AIResponse:
    """Loop de Tool Use sobre `ia_service.chat` (LiteLLM/OpenAI format).

    Mantém histórico via `SessionStore`. Limite de 5 iterações.
    """
    from app.services.ai_tools import openai_tools_payload
    from app.services.cotte_context_builder import SessionStore
    from app.services.ia_service import ia_service
    from app.services.tool_executor import execute as tool_execute
    from app.services.tool_executor import execute_pending

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
                override_args=override_args,
            )
            if result.status == "ok":
                orc_data = result.data or {}
                if orc_data.get("numero"):
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
                final_text = f"❌ Não consegui concluir a ação: {result.error or result.status}"
                tipo_resp = None
                acao_sug = None
                resp_dados = {"input_tokens": 0, "output_tokens": 0}
            tool_trace_out = [{
                "tool": "(confirmação)",
                "status": result.status,
                "latencia_ms": result.latencia_ms,
                "data": result.data,
                "error": result.error,
            }]
        except Exception as e:
            import logging as _lg
            _lg.getLogger(__name__).exception("Falha no fast-path de confirmação")
            try:
                db.rollback()
            except Exception:
                pass
            final_text = f"❌ Erro ao processar a confirmação: {e}"
            tool_trace_out = [{"tool": "(confirmação)", "status": "erro", "error": str(e)}]
            tipo_resp = None
            acao_sug = None
            resp_dados = {"input_tokens": 0, "output_tokens": 0}

        SessionStore.append(sessao_id, "assistant", final_text)
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

    messages: list[dict] = [
        {"role": "system", "content": f"{_V2_SYSTEM_PROMPT}\n\nData/hora atual: {now}."},
    ]
    # SessionStore historiza apenas role+content (sem tool_calls). Mantemos como hint.
    for h in history[-12:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": mensagem})

    # Persiste mensagem do usuário no banco
    SessionStore.append_db(sessao_id, "user", mensagem, db)

    tools_payload = openai_tools_payload()
    tool_trace: list[dict] = []
    pending_action: Optional[dict] = None
    total_in = 0
    total_out = 0
    final_text: Optional[str] = None

    for _iter in range(_V2_MAX_ITER):
        try:
            resp = await ia_service.chat(
                messages=messages,
                tools=tools_payload,
                temperature=0.3,
                max_tokens=1024,
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

        usage = resp.get("usage", {}) if isinstance(resp, dict) else getattr(resp, "usage", {}) or {}
        try:
            total_in += int(usage.get("prompt_tokens", 0) or 0)
            total_out += int(usage.get("completion_tokens", 0) or 0)
        except Exception:
            pass

        choices = resp.get("choices") if isinstance(resp, dict) else getattr(resp, "choices", None)
        if not choices:
            break
        choice = choices[0]
        msg = choice.get("message") if isinstance(choice, dict) else getattr(choice, "message", None)
        finish = choice.get("finish_reason") if isinstance(choice, dict) else getattr(choice, "finish_reason", None)

        # Extrair tool_calls
        tool_calls = None
        if msg is not None:
            tool_calls = (
                msg.get("tool_calls") if isinstance(msg, dict) else getattr(msg, "tool_calls", None)
            )

        if tool_calls:
            # Anexa o assistant turn com tool_calls (preservando ids)
            assistant_msg = {
                "role": "assistant",
                "content": (msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)) or "",
                "tool_calls": [
                    {
                        "id": (tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)),
                        "type": "function",
                        "function": {
                            "name": (
                                (tc.get("function", {}) if isinstance(tc, dict) else getattr(tc, "function", None)).get("name")
                                if isinstance(tc, dict) else getattr(getattr(tc, "function", None), "name", None)
                            ),
                            "arguments": (
                                (tc.get("function", {}) if isinstance(tc, dict) else getattr(tc, "function", None)).get("arguments")
                                if isinstance(tc, dict) else getattr(getattr(tc, "function", None), "arguments", None)
                            ),
                        },
                    }
                    for tc in tool_calls
                ],
            }
            messages.append(assistant_msg)

            for tc in tool_calls:
                tc_dict = tc if isinstance(tc, dict) else {
                    "id": getattr(tc, "id", None),
                    "function": {
                        "name": getattr(getattr(tc, "function", None), "name", None),
                        "arguments": getattr(getattr(tc, "function", None), "arguments", None),
                    },
                }
                result = await tool_execute(
                    tc_dict,
                    db=db,
                    current_user=current_user,
                    sessao_id=sessao_id,
                    confirmation_token=confirmation_token,
                )
                tool_trace.append({
                    "tool": (tc_dict.get("function") or {}).get("name"),
                    "status": result.status,
                    "latencia_ms": result.latencia_ms,
                })
                payload = result.to_llm_payload()
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_dict.get("id"),
                    "content": json.dumps(payload, ensure_ascii=False, default=str),
                })
                if result.status == "pending":
                    pending_action = result.pending_action

            if pending_action:
                final_text = (
                    "Para concluir a ação, preciso da sua confirmação. "
                    "Confira os detalhes e clique em confirmar."
                )
                break
            # Próxima iteração: LLM verá os tool results
            continue

        # Sem tool_calls → resposta final
        final_text = (msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)) or ""
        if finish and finish != "stop" and finish != "tool_calls":
            logger.info("v2 finish_reason inesperado: %s", finish)
        break
    else:
        final_text = "Limite de iterações de ferramentas atingido. Refine a pergunta."

    if final_text:
        # Persiste resposta do assistente no banco
        SessionStore.append_db(sessao_id, "assistant", final_text, db)

    return AIResponse(
        sucesso=True,
        resposta=final_text or "",
        confianca=0.9 if final_text else 0.4,
        modulo_origem="assistente_v2",
        pending_action=pending_action,
        tool_trace=tool_trace or None,
        dados={"input_tokens": total_in, "output_tokens": total_out},
    )

