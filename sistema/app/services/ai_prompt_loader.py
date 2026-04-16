"""
PromptLoader - COTTE AI Hub
Etapa 3: Externalização de Prompts para arquivos YAML/JSON

Este módulo permite mover os prompts hardcoded para arquivos externos,
facilitando manutenção, A/B testing e internacionalização.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from functools import lru_cache
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class PromptConfig:
    """Configuração de um prompt específico"""
    system: str
    max_tokens: int = 150
    model: str = "default"
    temperature: float = 0.1
    top_p: float = 0.9
    version: str = "1.0"
    description: Optional[str] = None
    tags: list = field(default_factory=list)


class AIPromptLoader:
    """
    Carregador de prompts externos para o COTTE AI Hub.
    
    Suporta:
    - Arquivos JSON (.json)
    - Arquivos YAML (.yaml, .yml)
    - Hot-reload em desenvolvimento
    - Cache em memória para performance
    - Fallback para prompts embutidos
    
    Estrutura esperada do arquivo:
    {
        "orcamentos": {
            "system": "Você é o assistente...",
            "max_tokens": 150,
            "model": "default",
            "version": "1.0"
        },
        ...
    }
    """
    
    # Prompts padrão (fallback se arquivos externos não existirem)
    DEFAULT_PROMPTS: Dict[str, PromptConfig] = {
        "orcamentos": PromptConfig(
            system="""Você é o assistente de orçamentos do COTTE. Extraia dados de orçamento de mensagens em linguagem natural.

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
            max_tokens=150,
            model="default",
            version="1.0"
        ),
        
        "clientes": PromptConfig(
            system="""Você é o assistente de cadastro de clientes do COTTE. Extraia informações de contato e identificação.

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
            max_tokens=200,
            model="default",
            version="1.0"
        ),
        
        "financeiro": PromptConfig(
            system="""Você é o assistente financeiro do COTTE. Categorize transações e identifique padrões.

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
            max_tokens=150,
            model="default",
            version="1.0"
        ),
        
        "comercial": PromptConfig(
            system="""Você é o assistente comercial do COTTE. Qualifique leads e sugira abordagens.

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
            max_tokens=180,
            model="default",
            version="1.0"
        ),
        
        "operador": PromptConfig(
            system="""Você interpreta comandos de operadores do sistema COTTE.

REGRAS OBRIGATÓRIAS:
1. Identifique a ação principal com precisão
2. Extraia IDs de orçamento quando presentes
3. Retorne APENAS JSON válido

FORMATO DE SAÍDA:
{"acao":"VER ou DESCONTO ou ADICIONAR ou REMOVER ou ENVIAR ou CRIAR ou APROVAR ou RECUSAR ou AJUDA ou DESCONHECIDO","orcamento_id":null,"valor":null,"desconto_tipo":"percentual","descricao":null,"num_item":null}

EXEMPLOS DE COMANDOS:
- "ver 5" → acao: VER, orcamento_id: 5
- "10% no 3" → acao: DESCONTO, orcamento_id: 3, valor: 10, desconto_tipo: percentual
- "adiciona filtro 80 no 3" → acao: ADICIONAR, orcamento_id: 3, descricao: "filtro", valor: 80
- "remove item 2 do 5" → acao: REMOVER, orcamento_id: 5, num_item: 2
- "aprovar 5" → acao: APROVAR, orcamento_id: 5
- "ajuda" → acao: AJUDA""",
            max_tokens=100,
            model="default",
            version="1.0"
        ),
        
        "conversacao": PromptConfig(
            system="""Você é o assistente virtual do COTTE. Responda de forma amigável e profissional.

REGRAS:
1. Seja breve e direto (máximo 2-3 frases)
2. Use tom profissional mas caloroso
3. Sempre ofereça ajuda concreta quando possível
4. Se não souber, seja honesto e sugere falar com um humano""",
            max_tokens=120,
            model="default",
            version="1.0"
        ),
        
        "financeiro_analise": PromptConfig(
            system="""Você é o assistente financeiro do COTTE. Você DEVE retornar APENAS JSON válido.

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
            max_tokens=600,
            model="default",
            version="1.0"
        ),
        
        "conversao_analise": PromptConfig(
            system="""Você é o analista de conversão do COTTE. Analise taxas de sucesso de orçamentos.

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
            max_tokens=250,
            model="default",
            version="1.0"
        ),
        
        "negocio_sugestoes": PromptConfig(
            system="""Você é o consultor de negócios do COTTE. Forneça sugestões estratégicas baseadas em dados.

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
            max_tokens=200,
            model="default",
            version="1.0"
        ),
        
        "intencao_classificador": PromptConfig(
            system="""Você é um classificador de intenções do sistema COTTE.

Sua tarefa é classificar a mensagem do usuário em uma das categorias abaixo.

CATEGORIAS DISPONÍVEIS:
- SALDO_RAPIDO: Perguntas curtas sobre saldo/caixa (ex: "qual o saldo?", "caixa")
- DASHBOARD: Visão geral financeira (ex: "como estão as finanças?", "dashboard")
- PREVISAO: Projeções futuras (ex: "previsão de caixa", "quanto vou receber")
- INADIMPLENCIA: Clientes devendo (ex: "quem está devendo?", "inadimplentes")
- ANALISE: Análise financeira detalhada (ex: "analisar receitas", "detalhamento")
- CONVERSAO: Métricas de vendas (ex: "ticket médio", "taxa de conversão")
- NEGOCIO: Sugestões estratégicas (ex: "como aumentar vendas?", "sugestões")
- CONVERSACAO: Perguntas gerais ou não relacionadas (ex: "oi", "ajuda")

REGRAS:
1. Retorne APENAS o nome da categoria em MAIÚSCULAS
2. Seja conservador - quando em dúvida, use CONVERSACAO
3. Responda apenas com a categoria, sem explicações

FORMATO DE SAÍDA:
{"intencao":"NOME_DA_CATEGORIA","confianca":0.0}

EXEMPLOS:
- "qual meu saldo?" → {"intencao":"SALDO_RAPIDO","confianca":0.95}
- "como posso melhorar minhas vendas?" → {"intencao":"NEGOCIO","confianca":0.88}
- "previsão financeira" → {"intencao":"PREVISAO","confianca":0.92}""",
            max_tokens=50,
            model="default",
            temperature=0.0,
            version="1.0"
        )
    }
    
    def __init__(self, prompts_dir: Optional[str] = None):
        """
        Inicializa o PromptLoader.
        
        Args:
            prompts_dir: Diretório contendo os arquivos de prompt.
                        Se None, usa prompts embutidos.
        """
        self._prompts: Dict[str, PromptConfig] = {}
        self._prompts_dir = prompts_dir
        self._loaded = False
        self._lock = asyncio.Lock()
    
    async def load(self, force_reload: bool = False) -> Dict[str, PromptConfig]:
        """
        Carrega prompts de forma assíncrona.
        
        Args:
            force_reload: Se True, recarrega mesmo se já carregado
        
        Returns:
            Dict com todos os prompts carregados
        """
        async with self._lock:
            if self._loaded and not force_reload:
                return self._prompts
            
            if self._prompts_dir and os.path.exists(self._prompts_dir):
                await self._load_from_directory(self._prompts_dir)
            
            # Mesclar com defaults (defaults têm menor prioridade)
            for key, config in self.DEFAULT_PROMPTS.items():
                if key not in self._prompts:
                    self._prompts[key] = config
            
            self._loaded = True
            logger.info(f"[PromptLoader] {len(self._prompts)} prompts carregados")
            return self._prompts
    
    async def _load_from_directory(self, directory: str):
        """Carrega prompts de arquivos no diretório"""
        path = Path(directory)
        
        # Carrega JSON
        for json_file in path.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, config_dict in data.items():
                        self._prompts[key] = PromptConfig(**config_dict)
                logger.info(f"[PromptLoader] Carregado: {json_file.name}")
            except Exception as e:
                logger.error(f"[PromptLoader] Erro ao carregar {json_file}: {e}")
        
        # Carrega YAML se disponível
        try:
            import yaml
            for yaml_file in list(path.glob("*.yaml")) + list(path.glob("*.yml")):
                try:
                    with open(yaml_file, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                        for key, config_dict in data.items():
                            self._prompts[key] = PromptConfig(**config_dict)
                    logger.info(f"[PromptLoader] Carregado: {yaml_file.name}")
                except Exception as e:
                    logger.error(f"[PromptLoader] Erro ao carregar {yaml_file}: {e}")
        except ImportError:
            logger.debug("[PromptLoader] PyYAML não instalado, ignorando arquivos YAML")
    
    def get(self, modulo: str) -> Optional[PromptConfig]:
        """
        Retorna configuração de um prompt específico.
        
        Args:
            modulo: Nome do módulo (ex: "orcamentos", "financeiro")
        
        Returns:
            PromptConfig ou None se não encontrado
        """
        # Se ainda não carregou, retorna default
        if not self._loaded:
            return self.DEFAULT_PROMPTS.get(modulo)
        return self._prompts.get(modulo)
    
    def get_dict(self, modulo: str) -> Dict[str, Any]:
        """
        Retorna prompt como dicionário (compatibilidade com código existente).
        
        Returns:
            Dict com keys: system, max_tokens, model
        """
        config = self.get(modulo)
        if config:
            return {
                "system": config.system,
                "max_tokens": config.max_tokens,
                "model": config.model
            }
        # Fallback para conversação
        return {
            "system": self.DEFAULT_PROMPTS["conversacao"].system,
            "max_tokens": 120,
            "model": "default"
        }
    
    def list_modulos(self) -> list:
        """Retorna lista de módulos disponíveis"""
        if not self._loaded:
            return list(self.DEFAULT_PROMPTS.keys())
        return list(self._prompts.keys())
    
    def reload(self) -> asyncio.Future:
        """Força recarregamento dos prompts"""
        return asyncio.create_task(self.load(force_reload=True))


# Instância global (singleton)
_prompt_loader_instance: Optional[AIPromptLoader] = None


def get_prompt_loader(prompts_dir: Optional[str] = None) -> AIPromptLoader:
    """
    Retorna instância singleton do PromptLoader.
    
    Args:
        prompts_dir: Diretório de prompts (usado apenas na primeira chamada)
    
    Returns:
        AIPromptLoader instance
    """
    global _prompt_loader_instance
    if _prompt_loader_instance is None:
        _prompt_loader_instance = AIPromptLoader(prompts_dir)
    return _prompt_loader_instance


# Funções de conveniência
async def load_prompts(prompts_dir: Optional[str] = None) -> Dict[str, PromptConfig]:
    """Carrega todos os prompts de forma assíncrona"""
    loader = get_prompt_loader(prompts_dir)
    return await loader.load()


def get_prompt(modulo: str) -> Dict[str, Any]:
    """
    Retorna configuração de prompt (síncrono).
    Usa defaults se ainda não carregou.
    """
    loader = get_prompt_loader()
    return loader.get_dict(modulo)
