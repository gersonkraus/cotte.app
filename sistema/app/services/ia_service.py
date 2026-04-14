# sistema/app/services/ia_service.py
"""
IA Service - LiteLLM + GPT-4o-mini (Tool Use nativo)
100% compatível com todas as funcionalidades já implementadas no sistema COTTE
"""

import json
import logging
import re
import unicodedata
from typing import List, Dict, Any, Optional

try:
    from litellm import acompletion, completion
except ModuleNotFoundError:  # pragma: no cover - fallback para ambiente de teste/local sem dependência opcional
    async def acompletion(*args, **kwargs):
        raise RuntimeError("litellm não está instalado no ambiente atual")

    def completion(*args, **kwargs):
        raise RuntimeError("litellm não está instalado no ambiente atual")

from app.core.config import settings
from app.schemas.schemas import IAInterpretacaoOut

logger = logging.getLogger(__name__)


class IAService:
    def __init__(self):
        self.provider = settings.AI_PROVIDER or "openai"
        self.model = settings.AI_MODEL or "gpt-4o-mini"
        self.api_key = settings.AI_API_KEY
        logger.info(f"🚀 IA Service iniciado → {self.provider} / {self.model} (Tool Use ativado)")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.3,
        max_tokens: int = 4000,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """Chat unificado com suporte completo a Tool Use / Function Calling"""
        try:
            response = await acompletion(
                model=self.model,
                messages=messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=self.api_key,
                stream=stream,
            )

            usage = response.get("usage", {})
            input_t = usage.get("prompt_tokens", 0)
            output_t = usage.get("completion_tokens", 0)
            cost = self._calculate_cost(input_t, output_t)

            logger.info(
                f"IA → {self.model} | Tokens: {input_t} in / {output_t} out | "
                f"Custo ≈ ${cost:.5f}"
            )
            return response

        except Exception as e:
            logger.error(f"Erro na chamada IA: {e}", exc_info=True)
            raise

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ):
        """Streaming real de tokens (sem tool calling).

        Retorna um async generator que produz strings de texto incrementais.
        Usar apenas na fase de resposta final em texto livre — tool calls devem
        usar `chat()` normal.
        """
        try:
            response = await acompletion(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=self.api_key,
                stream=True,
            )
            async for chunk in response:
                delta = None
                try:
                    choices = getattr(chunk, "choices", None) or chunk.get("choices")
                    if choices:
                        msg = getattr(choices[0], "delta", None) or choices[0].get("delta")
                        if msg:
                            delta = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else None)
                except Exception:
                    pass
                if delta:
                    yield delta
        except Exception as e:
            logger.error(f"Erro no chat_stream: {e}", exc_info=True)
            raise

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        if "gpt-4o-mini" in self.model:
            return (input_tokens * 0.00000015) + (output_tokens * 0.00000060)
        return (input_tokens + output_tokens) * 0.000002

    def chat_sync(self, messages: List[Dict], tools=None, **kwargs):
        return completion(
            model=self.model,
            messages=messages,
            tools=tools,
            api_key=self.api_key,
            **kwargs
        )


# Instância única usada em todo o sistema
ia_service = IAService()


# ── Código antigo preservado e migrado ─────────────────────────────────────
_MAX_MSG_LEN = 500
_INJECTION_PATTERNS = [
    r"ignore\s+(as\s+)?(instru[çc][õo]es?|regras?|anteriores?)",
    r"ignore\s+(all\s+)?previous\s+instructions?",
    r"(desconsidere?|esqueça|ignore)\s+(tudo|todas?\s+as?\s+instru[çc][õo]es?)",
    r"novo\s+prompt\s+(do\s+)?sistema",
    r"new\s+system\s+prompt",
    r"(aja|comporte.se|finja)\s+(como|que\s+voc[êe]\s+[eé])",
    r"(act|behave|pretend)\s+as",
    r"voc[êe]\s+agora\s+[eé]",
    r"you\s+are\s+now",
    r"\[SYSTEM\]|\[INST\]|<\|im_start\|>",
    r"(revelar?|mostrar?|imprimir?)\s+(suas?\s+)?(instru[çc][õo]es?|system\s+prompt|segredos?)",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def sanitizar_mensagem(mensagem: str) -> str:
    if not mensagem:
        return ""
    cleaned = "".join(
        ch for ch in mensagem
        if unicodedata.category(ch) not in ("Cc", "Cf") or ch in ("\n", "\t")
    )
    cleaned = cleaned[:_MAX_MSG_LEN]
    if _INJECTION_RE.search(cleaned):
        logger.warning("[parry] Prompt injection detectada: %r", cleaned[:80])
        return "[mensagem inválida]"
    return cleaned


# ── Prompts originais mantidos ─────────────────────────────────────────────
SYSTEM_PROMPT = """Extrai dados de orçamento de mensagem em linguagem natural. Retorne APENAS JSON válido:
{"cliente_nome":"...","servico":"...","valor":0.0,"desconto":0.0,"desconto_tipo":"percentual","observacoes":null,"confianca":0.95}
- valor: numérico com ponto decimal, BRUTO (antes do desconto). "setecentos","700,00","700 reais","700" → 700.0. Número puro isolado ou após nome de produto é o valor: "epson 899" → 899.0, "nike 299" → 299.0, "mesa 1500" → 1500.0
- desconto: número puro se percentual (10 para 10%); valor em reais se fixo (50 para R$50)
- desconto_tipo: "percentual" (mencionar % ou porcentagem) ou "fixo" (mencionar reais/R$)
- confianca: 0.0-1.0; reduza se faltar valor
- sem valor → 0.0 e confianca baixa; sem cliente → "A definir"; sem desconto → 0.0 e "percentual"
- observacoes: detalhes extras ou null"""

SYSTEM_PROMPT_OPERADOR = """Interpreta comando de operador de orçamentos. Retorne APENAS JSON válido:
{"acao":"VER|DESCONTO|ADICIONAR|REMOVER|ENVIAR|CRIAR|APROVAR|RECUSAR|AJUDA|ANALISE_FINANCEIRA|ANALISE_CONVERSAO|SUGESTOES_NEGOCIO|CAIXA_FUTURO|DESCONHECIDO","orcamento_id":null,"valor":null,"desconto_tipo":"percentual","descricao":null,"num_item":null}
VER / MOSTRAR:"ver 5","mostra 5","mostra o 5","me mostra o orc 3","ver orçamento 5","detalhes do 5" | DESCONTO:"10% no 5","50 reais no 3","desconto 15% no orcamento 2" | ADICIONAR:"adiciona filtro 80 no 3","coloca pintura 200 no orcamento 3" | REMOVER:"remove item 2 do 5","tira o item 1 do orçamento 3" | ENVIAR:"envia o 5","manda o 3","enviar orçamento 5","mandar orc 3","enviar O-103","enviar 103" | APROVAR:"aprovar 5","aprova o 3","aprovar orçamento 5","confirma 5" | RECUSAR:"recusar 5","recusa o 3","reprovar 2","rejeitar orcamento 5" | CRIAR:"pintura 800 para João","corte 150 pra maria" | AJUDA:"ajuda","help"
ANALISE_FINANCEIRA:"Como estão as finanças?","Analisar financeiro","Quanto faturamos?"
ANALISE_CONVERSAO:"Qual meu ticket médio?","Analisar conversão","Serviço mais vendido"
SUGESTOES_NEGOCIO:"Como aumentar vendas?","Quais clientes devendo?","Sugestões de negócio"
CAIXA_FUTURO:"caixa futuro","previsão de caixa","fluxo de caixa","quanto vou receber","projeção financeira"
- Padrões de ID aceitos: "ver 5","ver o 5","ver orc 5","ver orçamento 5","#5","id 5","orc 5", "O-103", "ORC-103" — o número adjacent à palavra é o ID, extraia apenas os numerais, ex: "O-103" -> 103.
- "aprovar" sozinho ou "aprovar orçamento" (sem número) → orcamento_id=null (NUNCA criar; pedir o número)
- valor: ponto decimal | desconto_tipo:"percentual"(%) ou "fixo"(reais)
- Se o comando for de análise (finanças, conversão, negócio, caixa futuro), retorne acao correspondente e orcamento_id=null"""

SYSTEM_PROMPT_TABELA_CATALOGO = """Analisa tabela de produtos/serviços e extrai dados estruturados. Retorne APENAS JSON válido com array:
[{"nome":"Produto A","preco_padrao":100.5,"unidade":"un","descricao":null}]
Regras:
- Identifique automaticamente qual coluna é nome, preço, unidade, descrição (em qualquer ordem)
- nome: string obrigatório
- preco_padrao: número com ponto decimal; normalize "R$ 1.500,00", "1.500", "1500.00" → 1500.0
- unidade: string com unidades comuns "un", "m²", "m", "hr", "kg", "lt", "srv"; se não identificado, use contexto (recomende "un" para produtos, "srv" para serviços)
- descricao: string ou null
- Ignore linhas vazias ou inválidas
- Se não conseguir extrair, retorne array vazio []"""

SYSTEM_PROMPT_LEADS = """Você é um extrator de leads de contato. Analise o texto e extraia todos os contatos identificáveis.

O texto pode estar em qualquer formato: lista simples, CSV (com vírgulas e campos entre aspas), tabela, WhatsApp exportado, etc.

Para cada contato extraia:
- nome_responsavel: nome da pessoa de contato quando houver; em listagens só com nome comercial, marca, nome fantasia ou serviço (ex: eletricista 24h), use esse nome aqui — nunca deixe vazio se existir um nome identificável na linha
- nome_empresa: razão social ou nome da empresa quando for distinto do contato; se a linha tiver um único nome (ex: "LA Serviços Elétricos"), pode repetir o mesmo valor em nome_responsavel e nome_empresa ou deixar um deles com o nome principal e o outro null
- whatsapp: apenas dígitos, mínimo 10 (ex: "21987654398"); null se não houver
- email: endereço de e-mail válido; null se não houver
- cidade: SOMENTE o nome da cidade (ex: "Curitiba", "São Paulo"). Se aparecer "Curitiba PR" extraia "Curitiba". Se o endereço contiver a cidade, extraia-a.
- segmento_nome: se mencionado, use um de: construção, tecnologia, saúde, educação, varejo, serviços, indústria, alimentício, financeiro, outros. Caso contrário null.
- origem_nome: se mencionado, use um de: indicação, site, redes sociais, evento, cold call, e-mail marketing, telefone, outros. Caso contrário null.
- observacoes: endereço completo (rua, número, bairro, CEP, estado), ou qualquer informação extra relevante. null se não houver.

Regras:
- whatsapp: extraia APENAS dígitos, sem espaços, parênteses ou hífens
- Se não houver whatsapp nem email, ignore o contato
- cidade: apenas o nome da cidade, nunca o endereço completo
- O endereço completo vai em observacoes
- Não invente dados
- Retorne SOMENTE JSON válido, sem markdown, sem explicações

Formato de saída:
{"items": [{"nome_responsavel":"...","nome_empresa":"...","whatsapp":"...","email":"...","cidade":"...","segmento_nome":"...","origem_nome":"...","observacoes":"..."}]}
"""


# ── Funções originais migradas para LiteLLM ───────────────────────────────
async def interpretar_mensagem(mensagem: str) -> IAInterpretacaoOut:
    response = await ia_service.chat(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": sanitizar_mensagem(mensagem)}
        ],
        temperature=0.0,
        max_tokens=150,
    )
    raw = response["choices"][0]["message"]["content"].strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return IAInterpretacaoOut(**json.loads(raw))


async def interpretar_comando_operador(mensagem: str) -> dict:
    try:
        response = await ia_service.chat(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_OPERADOR},
                {"role": "user", "content": sanitizar_mensagem(mensagem)}
            ],
            temperature=0.0,
            max_tokens=100,
        )
        raw = response["choices"][0]["message"]["content"].strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        logger.warning("[ia_operador] Falha ao interpretar comando: %s", e)
        return {"acao": "DESCONHECIDO"}


async def gerar_resposta_bot(mensagem: str, dados_empresa: dict) -> str:
    response = await ia_service.chat(
        messages=[{"role": "user", "content": sanitizar_mensagem(mensagem)}],
        temperature=0.7,
        max_tokens=120,
    )
    return response["choices"][0]["message"]["content"]


async def interpretar_tabela_catalogo(texto: str) -> list[dict]:
    try:
        response = await ia_service.chat(
            messages=[{"role": "user", "content": f"Analise a tabela abaixo:\n\n{texto}"}],
            temperature=0.0,
            max_tokens=2000,
        )
        raw = response["choices"][0]["message"]["content"].strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        return data
    except Exception as e:
        logger.warning("[ia_tabela] Falha ao interpretar tabela: %s", e)
        return []


async def analisar_leads(texto: str) -> dict:
    try:
        response = await ia_service.chat(
            messages=[{"role": "user", "content": texto[:8000]}],
            temperature=0.0,
            max_tokens=2000,
        )
        raw = response["choices"][0]["message"]["content"].strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        logger.warning("[ia_leads] Falha ao analisar leads: %s", e)
        return {"items": []}
