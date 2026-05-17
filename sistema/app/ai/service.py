# sistema/app/services/ia_service.py
"""
IA Service - LiteLLM (Tool Use nativo)
100% compatível com todas as funcionalidades já implementadas no sistema COTTE
"""

import json
import logging
import os
import re
import unicodedata
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

try:
    from litellm import acompletion, completion
    import litellm
    if os.getenv("LITELLM_DEBUG", "").lower() in ("1", "true", "debug"):
        litellm.set_verbose = True
        logger.info("[LiteLLM] Debug mode enabled via LITELLM_DEBUG=1")
except (
    ModuleNotFoundError
):  # pragma: no cover - fallback para ambiente de teste/local sem dependência opcional

    async def acompletion(*args, **kwargs):
        raise RuntimeError("litellm não está instalado no ambiente atual")

    def completion(*args, **kwargs):
        raise RuntimeError("litellm não está instalado no ambiente atual")


from app.core.config import settings
from app.schemas.schemas import IAInterpretacaoOut

# Primeiro segmento do model já define o roteamento no LiteLLM — não reescrever.
# Lista conservadora + extensível via env (ver _explicit_route_prefixes).
_LITELLM_EXPLICIT_ROUTE_PREFIXES: frozenset[str] = frozenset(
    {
        "openrouter",
        "azure",
        "bedrock",
        "ollama",
        "anthropic",
        "gemini",
        "openai",
        "groq",
        "mistral",
        "cohere",
        "vertex_ai",
        "vertex_ai_beta",
        "deepseek",
        "fireworks_ai",
        "together_ai",
        "xai",
        "perplexity",
        "nvidia_nim",
        "sagemaker",
        "watsonx",
        "huggingface",
        "replicate",
        "vllm",
        "hosted_vllm",
        "databricks",
        "moonshot",
        "ai21",
        "clarifai",
        "nlp_cloud",
        "aleph_alpha",
        "anyscale",
        "cloudflare",
        "custom_openai",
        "text-completion-openai",
    }
)


def _explicit_route_prefixes() -> frozenset[str]:
    extra = (os.getenv("AI_LITELLM_ROUTE_PREFIXES") or "").strip()
    if not extra:
        return _LITELLM_EXPLICIT_ROUTE_PREFIXES
    parts = {p.strip().lower() for p in extra.split(",") if p.strip()}
    return _LITELLM_EXPLICIT_ROUTE_PREFIXES | parts


def _is_explicit_litellm_route(model: str, prefixes: frozenset[str]) -> bool:
    if "/" not in model:
        return False
    head = model.split("/", 1)[0].strip().lower()
    return head in prefixes


def _apply_google_to_gemini_alias(model: str) -> str:
    if model.startswith("google/"):
        return f"gemini/{model[len('google/') :]}"
    return model


def normalize_litellm_model(
    model: str,
    *,
    provider: str,
    raw: bool = False,
    fallback_model: str = "gpt-4o-mini",
) -> str:
    """Converte AI_MODEL / override em string aceita pelo LiteLLM (testável sem instanciar serviço).

    ``fallback_model`` vem tipicamente de ``Settings.AI_MODEL_FALLBACK`` quando ``model`` está vazio
    ou é o placeholder ``default``.
    """
    model = (model or "").strip()
    prov = (provider or "openai").strip().lower()

    if not model or model.lower() == "default":
        if model and model.lower() == "default":
            logger.warning(
                'AI_MODEL com valor literal "default" é inválido para o LiteLLM; '
                "usando AI_MODEL_FALLBACK (%s). Defina um id de modelo real no .env.",
                fallback_model,
            )
        model = (fallback_model or "").strip() or "gpt-4o-mini"

    if raw:
        return _apply_google_to_gemini_alias(model)

    # Com AI_PROVIDER=openrouter, "anthropic/..." (API nativa) vira rota OpenRouter no LiteLLM,
    # usando só OPENROUTER_API_KEY. Quem quiser API Anthropic direta: AI_PROVIDER=anthropic.
    if (
        prov == "openrouter"
        and model.startswith("anthropic/")
        and not model.startswith("openrouter/")
    ):
        model = f"openrouter/{model}"

    prefixes = _explicit_route_prefixes()
    if _is_explicit_litellm_route(model, prefixes):
        return _apply_google_to_gemini_alias(model)

    if prov == "openrouter":
        if model.startswith("openrouter/"):
            return model
        if "/" in model:
            return f"openrouter/{model}"
        return f"openrouter/openai/{model}"

    if model.startswith("google/"):
        model = f"gemini/{model[len('google/') :]}"

    if prov == "openai":
        if model.startswith("openrouter/openai/"):
            return model.replace("openrouter/openai/", "", 1)
        if model.startswith("openai/"):
            return model.replace("openai/", "", 1)
        return model

    if prov == "anthropic":
        if model.startswith("openrouter/anthropic/"):
            return model.replace("openrouter/anthropic/", "", 1)
        if model.startswith("anthropic/"):
            return model.replace("anthropic/", "", 1)
        return model

    if prov in ("google", "gemini"):
        if model.startswith("gemini/"):
            return model
        return f"gemini/{model}" if "/" not in model else model

    return _apply_google_to_gemini_alias(model)


class IAService:
    def __init__(self):
        self.provider = (settings.AI_PROVIDER or "openai").strip().lower()
        self.model = (settings.AI_MODEL or settings.AI_MODEL_FALLBACK).strip()
        self.litellm_model = self._normalize_model_for_provider(
            model=self.model,
            provider=self.provider,
        )
        self.api_key = self._resolve_api_key_for_litellm_model(self.litellm_model)
        
        # 1. Configuração de Cache (Redução de Custo)
        self._setup_cache()
        
        # 2. Configurações Globais LiteLLM
        try:
            # Drop logs silenciosos para focar no que importa
            litellm.drop_params = True 
            # Timeout global de 45s para evitar travamento total
            litellm.request_timeout = 45 
        except Exception:
            pass

        logger.info(
            "🚀 IA Service iniciado → %s / %s (modelo LiteLLM: %s, Cache: %s)",
            self.provider,
            self.model,
            self.litellm_model,
            "Redis" if settings.REDIS_URL else "In-memory",
        )

    def _setup_cache(self):
        """Configura o cache global do LiteLLM (Redis em prod, In-memory em dev)."""
        try:
            from litellm.caching import Cache
            if settings.REDIS_URL:
                # O LiteLLM espera host, port, password ou URL direta dependendo da versão
                # Usamos a URL direta que é o padrão da Railway
                litellm.cache = Cache(type="redis", url=settings.REDIS_URL)
                logger.info("[LiteLLM] Cache Redis ativado")
            else:
                litellm.cache = Cache(type="local")
                logger.info("[LiteLLM] Cache local (In-memory) ativado")
        except Exception as e:
            logger.warning(f"[LiteLLM] Falha ao configurar cache: {e}")

    def supports_prompt_caching(self) -> bool:
        """Retorna True se o modelo/provider ativo suporta Anthropic prompt caching."""
        model = (self.litellm_model or "").lower()
        provider = (self.provider or "").lower()
        if "claude" in model or "anthropic" in model:
            return True
        if provider == "anthropic":
            return True
        return False

    def _resolve_api_key_for_litellm_model(self, litellm_model: str) -> Optional[str]:
        """Escolhe a chave compatível com o model resolvido (LiteLLM roteia pelo prefixo)."""
        if settings.AI_API_KEY:
            return settings.AI_API_KEY

        m = (litellm_model or "").strip().lower()
        if m.startswith("openrouter/"):
            return os.getenv("OPENROUTER_API_KEY")

        # Rota nativa Anthropic (ex.: AI_PROVIDER=anthropic). Com openrouter/… não cai aqui.
        if m.startswith("anthropic/"):
            return os.getenv("ANTHROPIC_API_KEY")

        if m.startswith("gemini/") or m.startswith("google/"):
            return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

        if m.startswith("azure/"):
            return os.getenv("AZURE_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")

        if m.startswith("vertex_ai") or m.startswith("vertex_ai_beta"):
            return os.getenv("VERTEXAI_API_KEY")

        # OpenAI direto (prefixo openai/ ou modelo curto com AI_PROVIDER=openai)
        if m.startswith("openai/"):
            return os.getenv("OPENAI_API_KEY")
        if self.provider == "openai" and "/" not in m:
            return os.getenv("OPENAI_API_KEY")

        provider_key_map = {
            "openrouter": "OPENROUTER_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "gemini": "GEMINI_API_KEY",
        }
        env_name = provider_key_map.get(self.provider)
        if env_name:
            return os.getenv(env_name)
        return None

    def _normalize_model_for_provider(self, model: str, provider: str) -> str:
        """Delega para :func:`normalize_litellm_model` usando flags do settings."""
        return normalize_litellm_model(
            model,
            provider=provider,
            raw=bool(getattr(settings, "AI_LITELLM_RAW", False)),
            fallback_model=getattr(settings, "AI_MODEL_FALLBACK", "gpt-4o-mini"),
        )

    def _litellm_kwargs(
        self, *, model_override: Optional[str] = None, stream: bool = False
    ) -> dict:
        modelo_base = model_override if model_override else self.model
        modelo_final = self._normalize_model_for_provider(
            model=modelo_base,
            provider=self.provider,
        )
        api_key = self._resolve_api_key_for_litellm_model(modelo_final)
        
        # 3. Resiliência: Lista de Fallbacks
        # Se o modelo principal falhar, o LiteLLM tenta o fallback configurado
        fallback_m = self._normalize_model_for_provider(
            model=settings.AI_MODEL_FALLBACK,
            provider="openrouter" # Fallback geralmente via OpenRouter por ser agnóstico
        )
        
        kwargs: dict[str, Any] = {
            "model": modelo_final,
            "stream": stream,
            "caching": True, # Ativa cache por padrão
            "fallbacks": [fallback_m] if fallback_m != modelo_final else None
        }
        if api_key:
            kwargs["api_key"] = api_key
        return kwargs

    def describe_runtime(self, *, model_override: Optional[str] = None) -> dict[str, Any]:
        litellm_kwargs = self._litellm_kwargs(
            model_override=model_override,
            stream=False,
        )
        return {
            "gateway": "litellm",
            "provider": self.provider,
            "configured_model": model_override if model_override else self.model,
            "litellm_model": litellm_kwargs["model"],
            "api_key_configured": bool(litellm_kwargs.get("api_key")),
            "cache_type": "redis" if settings.REDIS_URL else "local"
        }

    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.3,
        max_tokens: int = 4000,
        stream: bool = False,
        model_override: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Chat unificado com suporte completo a Tool Use / Function Calling"""
        try:
            litellm_kwargs = self._litellm_kwargs(
                model_override=model_override,
                stream=stream,
            )
            modelo_final = litellm_kwargs["model"]
            response = await acompletion(
                messages=messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
                **litellm_kwargs,
                **kwargs,
            )

            # 4. Monitoramento de Lucratividade: Cálculo de Custo Real
            usage = response.get("usage", {})
            input_t = usage.get("prompt_tokens", 0)
            output_t = usage.get("completion_tokens", 0)
            
            try:
                # O LiteLLM calcula o custo exato baseado no modelo usado (incl. fallbacks)
                cost = litellm.completion_cost(completion_response=response)
            except Exception:
                cost = self._calculate_cost(input_t, output_t, modelo_final)

            # Extração de cache hit (LiteLLM expõe via hidden_params em algumas versões ou headers)
            cache_hit = False
            try:
                # Tenta várias formas que o LiteLLM pode expor o cache hit
                cache_hit = getattr(response, "hidden_params", {}).get("cache_hit", False)
                if not cache_hit:
                    # Algumas versões expõem via headers customizados no objeto original
                    headers = getattr(response, "_response_headers", {})
                    cache_hit = headers.get("x-litellm-cache-hit") == "True"
            except Exception:
                pass

            # Injeta metadados na resposta para telemetria e UI
            if isinstance(response, dict):
                response["_cost"] = cost
                response["_cache_hit"] = cache_hit

            logger.info(
                f"IA → {modelo_final} | Tokens: {input_t} in / {output_t} out | "
                f"Custo: ${cost:.6f} | Cache: {'SIM' if cache_hit else 'NÃO'}"
            )
            return response

        except Exception as e:
            logger.error(
                "Erro na chamada IA (provider=%s, model=%s): %s",
                self.provider,
                model_override if model_override else self.model,
                e,
                exc_info=True,
            )
            raise

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2048,
        model_override: Optional[str] = None,
        **kwargs,
    ):
        """Streaming real de tokens (sem tool calling).

        Retorna um async generator que produz strings de texto incrementais.
        Usar apenas na fase de resposta final em texto livre — tool calls devem
        usar `chat()` normal.
        """
        try:
            litellm_kwargs = self._litellm_kwargs(
                model_override=model_override,
                stream=True,
            )
            response = await acompletion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **litellm_kwargs,
                **kwargs,
            )
            async for chunk in response:
                delta = None
                try:
                    choices = getattr(chunk, "choices", None) or chunk.get("choices")
                    if choices:
                        msg = getattr(choices[0], "delta", None) or choices[0].get(
                            "delta"
                        )
                        if msg:
                            delta = getattr(msg, "content", None) or (
                                msg.get("content") if isinstance(msg, dict) else None
                            )
                except Exception:
                    pass
                if delta:
                    yield delta
        except Exception as e:
            logger.error(f"Erro no chat_stream: {e}", exc_info=True)
            raise

    def _calculate_cost(
        self, input_tokens: int, output_tokens: int, modelo_usado: Optional[str] = None
    ) -> float:
        model_to_check = (modelo_usado if modelo_usado else self.model or "").lower()
        fb = (getattr(settings, "AI_MODEL_FALLBACK", "") or "").strip().lower()
        fb_slug = fb.split("/")[-1] if fb else ""
        # Estimativa barata aproximada quando o modelo em uso corresponde ao fallback configurado.
        if fb_slug and fb_slug in model_to_check:
            return (input_tokens * 0.00000015) + (output_tokens * 0.00000060)
        return (input_tokens + output_tokens) * 0.000002

    async def chat_sync(
        self,
        messages: List[Dict],
        tools=None,
        model_override: Optional[str] = None,
        **kwargs,
    ):
        litellm_kwargs = self._litellm_kwargs(
            model_override=model_override,
            stream=bool(kwargs.get("stream", False)),
        )
        return completion(
            messages=messages,
            tools=tools,
            **litellm_kwargs,
            **kwargs,
        )

    async def get_embedding(self, text: str, model: str = "text-embedding-3-small") -> List[float]:
        """Gera embedding vetorial para um texto."""
        try:
            from litellm import aembedding

            # Garante prefixo se estiver usando openrouter
            if self.provider == "openrouter" and not model.startswith("openrouter/"):
                model = f"openrouter/{model}"

            response = await aembedding(
                model=model,
                input=[text],
                api_key=self.api_key
            )
            return response["data"][0]["embedding"]
        except Exception as e:
            logger.error(f"Erro ao gerar embedding: {e}")
            raise



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
        ch
        for ch in mensagem
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
- Padrões de ID aceitos: "ver 5","ver o 5","ver orc 5","ver orçamento 5","#5","id 5","orc 5", "O-103", "ORC-103", "0-131" — o número adjacente à palavra é o ID, extraia apenas os numerais ignorando prefixos como O- ou 0-, ex: "O-103" -> 103, "0-131" -> 131.
- "aprovar" sozinho ou "aprovar orçamento" (sem número) → orcamento_id=null (NUNCA criar; pedir o número)
- valor: ponto decimal | desconto_tipo:"percentual"(%) ou "fixo"(reais)
- Se o comando for de análise (finanças, conversão, negócio, caixa futuro), retorne acao correspondente e orcamento_id=null"""

SYSTEM_PROMPT_TABELA_CATALOGO = """Analisa tabela de produtos/serviços e extrai dados estruturados. Retorne APENAS JSON válido com array:
[{"nome":"Produto A","preco_padrao":100.5,"preco_custo":50.0,"unidade":"un","descricao":null,"categoria_sugerida":"Pintura"}]
Regras:
- Identifique automaticamente qual coluna é nome, preço, preço de custo, unidade, descrição (em qualquer ordem)
- nome: string obrigatório
- preco_padrao: número com ponto decimal; normalize "R$ 1.500,00", "1.500", "1500.00" → 1500.0
- preco_custo: extrair o valor numérico (com ponto) de colunas relativas a custo (ex: "custo", "preço custo", "pcusto", "valor custo"); normalize da mesma forma que preco_padrao; caso não exista, retornar null
- unidade: string com unidades comuns "un", "m²", "m", "hr", "kg", "lt", "srv"; se não identificado, use contexto (recomende "un" para produtos, "srv" para serviços)
- descricao: string ou null
- categoria_sugerida: sugira UMA categoria curta e genérica com base no nome e descrição do produto (ex: "Pintura", "Elétrica", "Hidráulica", "Acabamento", "Estrutura", "Limpeza", "Ferramentas"). Use null apenas se for impossível inferir.
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
            {"role": "user", "content": sanitizar_mensagem(mensagem)},
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
                {"role": "user", "content": sanitizar_mensagem(mensagem)},
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
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_TABELA_CATALOGO},
                {"role": "user", "content": f"Analise a tabela abaixo:\n\n{texto}"}
            ],
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


_BRIEFING_SYSTEM_PROMPT = """Você é um assistente comercial. Analise o contexto de um lead e decida a prioridade e próxima ação.

Retorne APENAS JSON válido com esta estrutura:
{
  "prioridade": "urgente|hoje|esta_semana|ok",
  "tipo_acao": "mensagem_whatsapp|mensagem_email|mover_etapa|nenhuma",
  "rascunho": "texto da mensagem ou null",
  "motivo": "explicação em 1-2 frases",
  "etapa_sugerida": "slug_da_etapa ou null",
  "confianca": 0.0
}

Regras de prioridade:
- urgente: +5 dias sem contato em proposta_enviada; OU +3 dias com score quente; OU proximo_contato vencido (passado)
- hoje: proximo_contato = hoje (futuro ou passado no mesmo dia); OU +7 dias sem contato com score morno; OU cliente respondeu recentemente
- esta_semana: outros leads que precisam de atenção em breve
- ok: contato_realizado=true E contato recente (<2 dias) E sem lembrete hoje; OU lead frio em etapa inicial sem lembrete

ATENÇÃO: contato_realizado=false significa que o lead NUNCA foi contatado (apenas cadastrado). Nesse caso, dias_sem_contato conta desde o cadastro — NÃO use a regra "ok por contato recente". Se houver proximo_contato hoje ou vencido, use urgente/hoje mesmo que dias_sem_contato seja 0.

Regras de tipo_acao:
- mensagem_whatsapp: maioria dos follow-ups
- mensagem_email: se último contato foi por email
- mover_etapa: se cliente respondeu e etapa não reflete a realidade
- nenhuma: se prioridade é ok

Se tipo_acao for mensagem_whatsapp ou mensagem_email, redija rascunho em português informal, curto (2-3 frases), sem nome da empresa no fim.
Se confianca < 0.5, retorne prioridade "ok" e tipo_acao "nenhuma".
Nunca invente informações não presentes no contexto."""


def _briefing_fallback(ctx: dict) -> dict:
    """Fallback com regras locais quando a IA falha."""
    from datetime import datetime, timezone, date

    dias = ctx.get("dias_sem_contato", 0)
    score = (ctx.get("score") or "frio").lower()
    etapa = ctx.get("etapa", "")
    proximo_raw = ctx.get("proximo_contato_em")

    proximo_vencido = False
    proximo_hoje = False
    if proximo_raw:
        try:
            proximo_dt = datetime.fromisoformat(str(proximo_raw).replace("Z", "+00:00"))
            agora = datetime.now(timezone.utc)
            proximo_vencido = proximo_dt < agora
            proximo_hoje = proximo_dt.date() == agora.date()
        except Exception:
            pass

    if (dias >= 5 and etapa == "proposta_enviada") or (score == "quente" and dias >= 3) or proximo_vencido:
        prioridade = "urgente"
    elif proximo_hoje or (score == "morno" and dias >= 7):
        prioridade = "hoje"
    elif dias < 2 and not proximo_hoje and not proximo_vencido:
        prioridade = "ok"
    else:
        prioridade = "esta_semana"

    tipo_acao = "nenhuma" if prioridade == "ok" else "mensagem_whatsapp"
    return {
        "prioridade": prioridade,
        "tipo_acao": tipo_acao,
        "rascunho": None,
        "motivo": f"{dias} dias sem contato. Score: {score}.",
        "etapa_sugerida": None,
        "confianca": 0.6,
    }


async def gerar_briefing_lead(ctx: dict) -> dict:
    """Analisa um lead e retorna prioridade, ação sugerida e rascunho de mensagem."""
    user_content = json.dumps(ctx, ensure_ascii=False, default=str)
    try:
        response = await ia_service.chat(
            messages=[
                {"role": "system", "content": _BRIEFING_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.0,
            max_tokens=500,
        )
        raw = response["choices"][0]["message"]["content"].strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        resultado = json.loads(raw)
        prioridade = resultado.get("prioridade", "ok")
        if prioridade not in ("urgente", "hoje", "esta_semana", "ok"):
            prioridade = "ok"
        tipo_acao = resultado.get("tipo_acao", "nenhuma")
        if tipo_acao not in ("mensagem_whatsapp", "mensagem_email", "mover_etapa", "nenhuma"):
            tipo_acao = "nenhuma"
        return {
            "prioridade": prioridade,
            "tipo_acao": tipo_acao,
            "rascunho": resultado.get("rascunho"),
            "motivo": resultado.get("motivo", ""),
            "etapa_sugerida": resultado.get("etapa_sugerida"),
            "confianca": float(resultado.get("confianca", 0.7)),
        }
    except Exception as e:
        logger.warning("[ia_briefing] Falha ao analisar lead '%s': %s", ctx.get("nome"), e)
        return _briefing_fallback(ctx)
