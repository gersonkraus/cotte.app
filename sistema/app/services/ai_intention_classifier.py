"""
Classificador de Intenção Híbrido - COTTE AI Hub
Etapa 4: Classificador de Intenção com Regex

Este módulo implementa um classificador leve que:
1. Usa Regex para comandos simples e determinísticos (performance)
2. Evita fallback em LLM no roteamento para manter custo previsível

Padrão Strategy: Prioriza velocidade e custo zero no roteamento.
"""

import re
import logging
from decimal import Decimal
from typing import Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Importações para type hints (evitar circular imports)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.services.cotte_ai_hub import AIResponse


class IntencaoUsuario(Enum):
    """Categorias de intenção do usuário"""
    SALDO_RAPIDO = "SALDO_RAPIDO"
    FATURAMENTO = "FATURAMENTO"
    CONTAS_RECEBER = "CONTAS_RECEBER"
    CONTAS_PAGAR = "CONTAS_PAGAR"
    DASHBOARD = "DASHBOARD"
    PREVISAO = "PREVISAO"
    INADIMPLENCIA = "INADIMPLENCIA"
    ANALISE = "ANALISE"
    CONVERSAO = "CONVERSAO"
    NEGOCIO = "NEGOCIO"
    CRIAR_ORCAMENTO = "CRIAR_ORCAMENTO"
    OPERADOR = "OPERADOR"
    ONBOARDING = "ONBOARDING"
    AJUDA_SISTEMA = "AJUDA_SISTEMA"  # Dúvidas sobre como usar o sistema
    CONVERSACAO = "CONVERSACAO"  # Fallback
    AGENDAMENTO_CRIAR = "AGENDAMENTO_CRIAR"
    AGENDAMENTO_LISTAR = "AGENDAMENTO_LISTAR"
    AGENDAMENTO_STATUS = "AGENDAMENTO_STATUS"
    AGENDAMENTO_CANCELAR = "AGENDAMENTO_CANCELAR"
    
    @classmethod
    def from_string(cls, value: str) -> "IntencaoUsuario":
        """Converte string para enum, retornando CONVERSACAO se inválido"""
        try:
            return cls(value.upper())
        except ValueError:
            return cls.CONVERSACAO


@dataclass
class ClassificacaoResult:
    """Resultado da classificação de intenção"""
    intencao: IntencaoUsuario
    confianca: float
    metodo: str  # "regex" ou "fallback"
    tempo_ms: Optional[float] = None
    raw_response: Optional[str] = None


class IntentionClassifier:
    """
    Classificador de intenção baseado em Regex.
    
    ARQUITETURA:
    ┌─────────────────────────────────────────────────────────────┐
    │                    MENSAGEM DO USUÁRIO                      │
    └──────────────────────┬──────────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │    ETAPA 1: REGEX       │  ← Velocidade O(1)
              │  (Heurísticas Rápidas)  │
              └────────────┬────────────┘
                           │ Match?
           Sim ┌───────────┴───────────┐ Não
               ▼                       ▼
    ┌─────────────────────┐  ┌─────────────────────┐
    │  Retorna Intenção   │  │      FALLBACK       │  ← Segurança
    │  (confiança alta)   │  │  CONVERSACAO        │    Custo zero
    └─────────────────────┘  │      Custo)         │
                             └──────────┬──────────┘
                                        │
                             ┌──────────▼──────────┐
                             │  Retorna Intenção   │
                             │  (confiança baixa)  │
                             └─────────────────────┘
    
    REGRAS DE NEGÓCIO:
    - Regex: 0ms latência, cobre 80% dos casos comuns
    - Fallback: CONVERSACAO para casos não reconhecidos
    """

    # ─────────────────────────────────────────────────────────────────
    # PADRÕES REGEX POR INTENÇÃO
    # ─────────────────────────────────────────────────────────────────
    
    # A) SALDO RÁPIDO - Comandos curtos e diretos
    SALDO_EXATO = {
        'caixa', 'saldo', 'meu caixa', 'meu saldo', 'saldo atual',
        'caixa atual', 'saldo de hoje', 'caixa de hoje', 'saldo hoje',
        'caixa hoje', 'valor em caixa', 'saldo do caixa', 'saldo caixa',
        'quanto tenho', 'quanto tenho em caixa', 'quanto tenho disponivel',
        'quanto eu tenho', 'disponivel', 'meu disponivel'
    }
    
    SALDO_PREFIXOS = [
        r'^saldo\b',
        r'^meu saldo',
        r'^caixa\b',
        r'^meu caixa',
        r'^quanto tenho',
        r'^valor em caixa',
        r'^saldo atual',
        r'^caixa atual',
        r'\bsaldo do caixa\b',
        r'\bqual\s+(?:o\s+)?saldo\b',
        r'\bqual\s+(?:e|é)\s+o\s+saldo\b',
        r'\bquanto\s+(?:tenho|ha|há)\s+(?:em\s+)?caixa\b',
    ]
    
    # B) FATURAMENTO
    FATURAMENTO_KEYWORDS = [
        r'faturamento',
        r'quanto fatura',
        r'faturamos',
        r'total faturado',
        r'receita total',
        r'total de vendas',
        r'quanto vendemos',
        r'^vendas\b',
    ]

    # B2) CONTAS A RECEBER
    CONTAS_RECEBER_KEYWORDS = [
        r'a receber',
        r'pra receber',
        r'tenho pra receber',
        r'tenho a receber',
        r'quanto tenho a receber',
        r'contas a receber',
        r'valor a receber',
    ]

    # B3) CONTAS A PAGAR
    CONTAS_PAGAR_KEYWORDS = [
        r'a pagar',
        r'pra pagar',
        r'tenho pra pagar',
        r'tenho a pagar',
        r'contas a pagar',
        r'quanto tenho a pagar',
        r'valor a pagar',
        r'parcelas',
    ]

    # C) PREVISÃO / FLUXO
    PREVISAO_KEYWORDS = [
        r'previs[ãa]o',
        r'proje[cç][ãa]o',
        r'fluxo de caixa',
        r'^fluxo\b',
        r'quanto vou',
        r'pr[oó]ximos\s+\d*\s*dias',
        r'pr[oó]ximas\s+\d*\s*semanas?',
        r'futuro',
        r'vou receber',
        r'vou pagar',
        r'previs[ãa]o de caixa',
        r'caixa dos pr[oó]ximos',
        r'previs[ãa]o financeira',
        r'caixa futuro',
        r'saldo futuro'
    ]
    
    # D) INADIMPLÊNCIA
    INADIMPLENCIA_KEYWORDS = [
        r'devendo',
        r'inadimplente',
        r'atraso',
        r'atrasado',
        r'vencidas',
        r'contas vencidas',
        r'recebimentos atrasados',
        r'quem deve',
        r'quem est[áa] devendo',
        r'clientes devendo',
        r'lista de devedores',
        r'contas em atraso',
        r'pend[êe]ncias',
        r'pendente'
    ]
    
    # B) DASHBOARD / VISÃO GERAL
    DASHBOARD_KEYWORDS = [
        r'dashboard',
        r'vis[ãa]o geral',
        r'panorama',
        r'resumo financeiro',
        r'situa[çc][ãa]o financeira',
        r'como est[ãa]o as finan[çc]as',
        r'como est[áa] meu',
        r'resumo completo',
        r'an[áa]lise financeira',
        r'relat[óo]rio financeiro',
        r'extrato',
        r'demonstrativo',
        r'balan[çc]o'
    ]
    
    # E) ANÁLISE DETALHADA
    ANALISE_KEYWORDS = [
        r'an[áa]lise\s+detalhada',
        r'detalhes?\s+financeiros?',
        r'aprofundado',
        r'estudo\s+financeiro',
        r'avalia[çc][ãa]o',
        r'relat[óo]rio detalhado',
        r'explica[çc][ãa]o',
        r'insights?\s+financeiros?',
        r'tend[êe]ncias?',
        r'comparativo',
        r'evolu[çc][ãa]o'
    ]
    
    # F) CONVERSÃO
    CONVERSAO_KEYWORDS = [
        r'convers[ãa]o',
        r'taxa de aprova[çc][ãa]o',
        r'ticket m[ée]dio',
        r'aprovados',
        r'recusados',
        r'servi[çc]o mais vendido',
        r'mais vendido',
        r'ranking\s+de\s+vendas'
    ]
    
    # G) NEGÓCIO
    NEGOCIO_KEYWORDS = [
        r'sugest[ãa]o',
        r'sugest[õo]es',
        r'aumentar vendas',
        r'melhorar\s+(neg[óo]cio|vendas)',
        r'crescer',
        r'estrat[ée]gia',
        r'pre[çc]os?\s+(muito\s+)?(baixos?|altos?)',
        r'revisar\s+tabela\s+de\s+pre[çc]os?',
        r'lucrativo',
        r'rent[áa]vel',
        r'melhor\s+cliente'
    ]

    # H) CRIAR ORÇAMENTO
    CRIAR_ORCAMENTO_KEYWORDS = [
        r'\bcriar?\s+or[çc]amento\b',
        r'\bnovo\s+or[çc]amento\b',
        r'\bor[çc]amento\s+(de|para|do|da)\b',
        r'\bor[çc]ar\b',
        r'\bfazer\s+or[çc]amento\b',
        r'\bmontar\s+or[çc]amento\b',
        r'\bor[çc]amento\s+.*?r\$',
        r'\bor[çc]amento\s+.*?\d+\s*(reais|mil)\b',
        r'\bnovo\s+orc\b',
        r'\bcriar?\s+orc\b',
    ]

    # I) OPERADOR — comandos de execução em orçamentos existentes
    OPERADOR_KEYWORDS = [
        r'\baprovar?\b',
        r'\brecusar?\b',
        r'\benviar?\s+(or[çc]amento|orc|\d)',
        r'\bmand(a|ar)\s+(or[çc]amento|orc)\b',
        r'\bver\s+(or[çc]amento|orc|\d)',
        r'\bmostrar?\s+(or[çc]amento|orc)\b',
        r'\bdetalhes?\s+(do\s+)?(or[çc]amento|orc)\b',
        r'\bdesconto\s+(de\s+)?\d',
        r'\b\d+\s*%\s*(no|do|n[ao])\s+\d+\b',
        r'\badicionar?\s+item\b',
        r'\bremover?\s+item\b',
        r'\bremove\s+item\b',
        r'\badiciona\s+',
    ]

    # J) ONBOARDING — configuração inicial / primeiro uso
    ONBOARDING_KEYWORDS = [
        r'\bonboarding\b',
        r'como come[çc]o',
        r'por onde come[çc]o',
        r'n[ãa]o sei (por onde|como) come[çc]ar',
        r'pr[óo]ximo passo',
        r'o que (devo|preciso) fazer',
        r'ajuda.*configurar',
        r'configurar.*sistema',
        r'primeiro or[çc]amento',
        r'\bchecklist\b',
        r'como (usar|utilizar) o (sistema|cotte)',
        r'me ajuda a (come[çc]ar|configurar|usar)',
        r'n[ãa]o sei usar',
        r'como funciona',
        r'primeiros? passos?',
        r'guia\b',
        r'configurar empresa',
    ]

    ONBOARDING_EXATO = {
        'ajuda', 'comecar', 'configurar', 'setup', 'inicio',
        'onboarding', 'guia', 'tutorial',
    }

    # K) AJUDA_SISTEMA — dúvidas sobre como usar funcionalidades do sistema
    AJUDA_SISTEMA_KEYWORDS = [
        r'como\s+(crio?|criar?|fa[çc]o|fazer|mont[ao]|montar|envio?|enviar|conect[ao]|conectar|uso?|usar|vejo?|ver|ativio?|ativar|acesso?|acessar|cancel[ao]|cancelar)\b',
        r'como\s+(funciona|funcionar)\b',
        r'como\s+(registro?|registrar|importo?|importar|exporto?|exportar|duplico?|duplicar|parcel[ao]|parcelar|aprovo?|aprovar)\b',
        r'o\s+que\s+[ée]\s+(o|a|um|uma)?\s*(or[çc]amento|cliente|cat[áa]logo|pipeline|lead|financeiro|caixa|whatsapp|bot|documento)',
        r'para\s+que\s+serve\b',
        r'como\s+fa[çc]o\s+para\b',
        r'como\s+posso\b',
        r'onde\s+(fico?|acho?|encontro?|vejo?)\b',
        r'n[ãa]o\s+(sei|consigo|encontro?)\s+(como|onde)',
        r'passo\s+a\s+passo',
        r'instru[çc][õo]es?\b',
        r'tutorial\b',
        r'(tem|h[áa])\s+como\s+',
        r'[ée]\s+poss[íi]vel\s+(criar|enviar|fazer|duplicar|importar)',
        r'como\s+conecto?\b',
        r'como\s+link[ao]\b',
        r'como\s+cadastr[ao]\b',
        r'como\s+add\b',
    ]

    # L) AGENDAMENTOS
    AGENDAMENTO_CRIAR_KEYWORDS = [
        r'\bagendar\b',
        r'\bquero\s+agendar\b',
        r'\bagendamento\s+(novo|criar)\b',
        r'\b(agendar|agenda)\s+(visita|entrega|serviço|servico)\b',
    ]
    AGENDAMENTO_LISTAR_KEYWORDS = [
        r'\bagendamentos?\s+(de\s+)?hoje\b',
        r'\bagenda\s+(do\s+dia|de\s+hoje)\b',
        r'\bmeus?\s+agendamentos?\b',
        r'\bagendamentos?\s+(da\s+)?semana\b',
    ]
    AGENDAMENTO_STATUS_KEYWORDS = [
        r'\bagendamento\s+\w*\d+\b',
        r'\bagd[-\s]?\d+\b',
        r'\bstatus\s+(do\s+)?agendamento\b',
    ]
    AGENDAMENTO_CANCELAR_KEYWORDS = [
        r'\bcancelar?\s+agendamento\b',
        r'\bcancelar?\s+agd\b',
    ]

    def __init__(self):
        self._regex_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> dict:
        """Compila padrões regex para performance"""
        return {
            IntencaoUsuario.SALDO_RAPIDO: [re.compile(p, re.IGNORECASE) for p in self.SALDO_PREFIXOS],
            IntencaoUsuario.FATURAMENTO: [re.compile(p, re.IGNORECASE) for p in self.FATURAMENTO_KEYWORDS],
            IntencaoUsuario.CONTAS_RECEBER: [re.compile(p, re.IGNORECASE) for p in self.CONTAS_RECEBER_KEYWORDS],
            IntencaoUsuario.CONTAS_PAGAR: [re.compile(p, re.IGNORECASE) for p in self.CONTAS_PAGAR_KEYWORDS],
            IntencaoUsuario.PREVISAO: [re.compile(p, re.IGNORECASE) for p in self.PREVISAO_KEYWORDS],
            IntencaoUsuario.INADIMPLENCIA: [re.compile(p, re.IGNORECASE) for p in self.INADIMPLENCIA_KEYWORDS],
            IntencaoUsuario.DASHBOARD: [re.compile(p, re.IGNORECASE) for p in self.DASHBOARD_KEYWORDS],
            IntencaoUsuario.ANALISE: [re.compile(p, re.IGNORECASE) for p in self.ANALISE_KEYWORDS],
            IntencaoUsuario.CONVERSAO: [re.compile(p, re.IGNORECASE) for p in self.CONVERSAO_KEYWORDS],
            IntencaoUsuario.NEGOCIO: [re.compile(p, re.IGNORECASE) for p in self.NEGOCIO_KEYWORDS],
            IntencaoUsuario.CRIAR_ORCAMENTO: [re.compile(p, re.IGNORECASE) for p in self.CRIAR_ORCAMENTO_KEYWORDS],
            IntencaoUsuario.OPERADOR: [re.compile(p, re.IGNORECASE) for p in self.OPERADOR_KEYWORDS],
            IntencaoUsuario.ONBOARDING: [re.compile(p, re.IGNORECASE) for p in self.ONBOARDING_KEYWORDS],
            IntencaoUsuario.AJUDA_SISTEMA: [re.compile(p, re.IGNORECASE) for p in self.AJUDA_SISTEMA_KEYWORDS],
            IntencaoUsuario.AGENDAMENTO_CRIAR: [re.compile(p, re.IGNORECASE) for p in self.AGENDAMENTO_CRIAR_KEYWORDS],
            IntencaoUsuario.AGENDAMENTO_LISTAR: [re.compile(p, re.IGNORECASE) for p in self.AGENDAMENTO_LISTAR_KEYWORDS],
            IntencaoUsuario.AGENDAMENTO_STATUS: [re.compile(p, re.IGNORECASE) for p in self.AGENDAMENTO_STATUS_KEYWORDS],
            IntencaoUsuario.AGENDAMENTO_CANCELAR: [re.compile(p, re.IGNORECASE) for p in self.AGENDAMENTO_CANCELAR_KEYWORDS],
        }
    
    # ═════════════════════════════════════════════════════════════════
    # MÉTODO PRINCIPAL: CLASSIFICAR
    # ═════════════════════════════════════════════════════════════════

    async def classificar(self, mensagem: str, usar_haiku: bool = True) -> ClassificacaoResult:
        """
        Classifica a intenção do usuário usando apenas Regex.

        Args:
            mensagem: Texto da mensagem do usuário
            usar_haiku: Mantido apenas por compatibilidade. Não é mais usado.
        
        Returns:
            ClassificacaoResult com intenção e metadados
        """
        import time
        start_time = time.time()
        
        if not mensagem or not mensagem.strip():
            return ClassificacaoResult(
                intencao=IntencaoUsuario.CONVERSACAO,
                confianca=0.0,
                metodo="fallback",
                tempo_ms=0
            )
        
        # ── ETAPA 1: REGEX (Heurísticas Rápidas) ─────────────────────
        intencao_regex = self._classificar_regex(mensagem)
        
        if intencao_regex != IntencaoUsuario.CONVERSACAO:
            tempo_ms = (time.time() - start_time) * 1000
            logger.debug(f"[IntentionClassifier] Regex match: {intencao_regex.value} ({tempo_ms:.1f}ms)")
            return ClassificacaoResult(
                intencao=intencao_regex,
                confianca=0.85,  # Alta confiança para regex
                metodo="regex",
                tempo_ms=tempo_ms
            )
        
        # ── FALLBACK ─────────────────────────────────────────────────
        tempo_ms = (time.time() - start_time) * 1000
        return ClassificacaoResult(
            intencao=IntencaoUsuario.CONVERSACAO,
            confianca=0.5,
            metodo="fallback",
            tempo_ms=tempo_ms
        )
    
    def _classificar_regex(self, mensagem: str) -> IntencaoUsuario:
        """
        Classifica usando regex - O(1) latência.
        Retorna CONVERSACAO se nenhum padrão match.
        """
        # Normalização
        mensagem_lower = mensagem.lower().strip()
        mensagem_lower = re.sub(r'\s+', ' ', mensagem_lower)
        
        # Remove acentos para matching mais flexível
        mensagem_normalized = self._normalize_text(mensagem_lower)
        
        # A) SALDO RÁPIDO - Match exato primeiro
        if mensagem_lower in self.SALDO_EXATO:
            # Exclui se contém palavras que indicam outras intenções
            if re.search(r'receber|a receber|pra receber', mensagem_lower):
                pass  # não é saldo, continua
            elif re.search(r'pagar|a pagar|pra pagar', mensagem_lower):
                pass
            elif re.search(r'faturamento|vendas|total de vendas', mensagem_lower):
                pass
            else:
                return IntencaoUsuario.SALDO_RAPIDO

        # Verifica se começa com prefixo de saldo
        for pattern in self._regex_patterns[IntencaoUsuario.SALDO_RAPIDO]:
            if pattern.search(mensagem_lower):
                # Verifica se NÃO contém palavras que indicariam outra intenção
                if re.search(r'receber|a receber|pra receber', mensagem_lower):
                    pass  # é contas a receber, não saldo
                elif re.search(r'pagar|a pagar|pra pagar', mensagem_lower):
                    pass  # é contas a pagar
                elif re.search(r'faturamento|vendas|total de vendas', mensagem_lower):
                    pass  # é faturamento
                elif re.search(r'an[áa]lise|dashboard|panorama|resumo\s+completo|vis[ãa]o\s+geral|situa[çc][ãa]o|como\s+est[áa]|previs[ãa]o|proje[çc][ãa]o|detalhado|completo.extenso|insights', mensagem_lower):
                    pass  # é análise complexa
                else:
                    return IntencaoUsuario.SALDO_RAPIDO

        # B) FATURAMENTO
        for pattern in self._regex_patterns[IntencaoUsuario.FATURAMENTO]:
            if pattern.search(mensagem_normalized):
                return IntencaoUsuario.FATURAMENTO

        # B2) CONTAS A RECEBER
        for pattern in self._regex_patterns[IntencaoUsuario.CONTAS_RECEBER]:
            if pattern.search(mensagem_normalized):
                return IntencaoUsuario.CONTAS_RECEBER

        # B3) CONTAS A PAGAR
        for pattern in self._regex_patterns[IntencaoUsuario.CONTAS_PAGAR]:
            if pattern.search(mensagem_normalized):
                return IntencaoUsuario.CONTAS_PAGAR

        # C) PREVISÃO
        for pattern in self._regex_patterns[IntencaoUsuario.PREVISAO]:
            if pattern.search(mensagem_normalized):
                return IntencaoUsuario.PREVISAO

        # D) INADIMPLÊNCIA
        for pattern in self._regex_patterns[IntencaoUsuario.INADIMPLENCIA]:
            if pattern.search(mensagem_normalized):
                # Orçamento(s) pendente(s) = pipeline comercial (rascunho/enviado), não cobrança
                if re.search(r"\bor[çc]amentos?\b", mensagem_lower) and re.search(
                    r"\bpendentes?\b", mensagem_lower
                ):
                    continue
                return IntencaoUsuario.INADIMPLENCIA

        # E) DASHBOARD
        for pattern in self._regex_patterns[IntencaoUsuario.DASHBOARD]:
            if pattern.search(mensagem_normalized):
                return IntencaoUsuario.DASHBOARD
        
        # E) ANÁLISE
        for pattern in self._regex_patterns[IntencaoUsuario.ANALISE]:
            if pattern.search(mensagem_normalized):
                return IntencaoUsuario.ANALISE
        
        # F) CONVERSÃO
        for pattern in self._regex_patterns[IntencaoUsuario.CONVERSAO]:
            if pattern.search(mensagem_normalized):
                return IntencaoUsuario.CONVERSAO
        
        # G) NEGÓCIO
        for pattern in self._regex_patterns[IntencaoUsuario.NEGOCIO]:
            if pattern.search(mensagem_normalized):
                return IntencaoUsuario.NEGOCIO

        # I) OPERADOR — executar ação em orçamento existente (antes de CRIAR para evitar conflito)
        for pattern in self._regex_patterns[IntencaoUsuario.OPERADOR]:
            if pattern.search(mensagem_lower):
                return IntencaoUsuario.OPERADOR

        # H) CRIAR ORÇAMENTO
        for pattern in self._regex_patterns[IntencaoUsuario.CRIAR_ORCAMENTO]:
            if pattern.search(mensagem_lower):
                return IntencaoUsuario.CRIAR_ORCAMENTO

        # J) ONBOARDING — configuração inicial / primeiros passos (match exato + regex)
        if mensagem_normalized in self.ONBOARDING_EXATO:
            return IntencaoUsuario.ONBOARDING
        for pattern in self._regex_patterns[IntencaoUsuario.ONBOARDING]:
            if pattern.search(mensagem_normalized):
                return IntencaoUsuario.ONBOARDING

        # K) AJUDA_SISTEMA — dúvidas sobre como usar funcionalidades
        for pattern in self._regex_patterns[IntencaoUsuario.AJUDA_SISTEMA]:
            if pattern.search(mensagem_normalized):
                return IntencaoUsuario.AJUDA_SISTEMA

        # L) AGENDAMENTOS — cancelar primeiro (mais específico), depois criar, listar, status
        for pattern in self._regex_patterns[IntencaoUsuario.AGENDAMENTO_CANCELAR]:
            if pattern.search(mensagem_lower):
                return IntencaoUsuario.AGENDAMENTO_CANCELAR
        for pattern in self._regex_patterns[IntencaoUsuario.AGENDAMENTO_CRIAR]:
            if pattern.search(mensagem_lower):
                return IntencaoUsuario.AGENDAMENTO_CRIAR
        for pattern in self._regex_patterns[IntencaoUsuario.AGENDAMENTO_LISTAR]:
            if pattern.search(mensagem_lower):
                return IntencaoUsuario.AGENDAMENTO_LISTAR
        for pattern in self._regex_patterns[IntencaoUsuario.AGENDAMENTO_STATUS]:
            if pattern.search(mensagem_lower):
                return IntencaoUsuario.AGENDAMENTO_STATUS

        # M) FUZZY MATCHING para mensagens curtas com erros de digitação
        if len(mensagem_lower) < 4:
            import difflib
            whitelist = {
                "caixa": IntencaoUsuario.SALDO_RAPIDO,
                "saldo": IntencaoUsuario.SALDO_RAPIDO,
                "ver": IntencaoUsuario.OPERADOR,
                "aprovar": IntencaoUsuario.OPERADOR,
                "recusar": IntencaoUsuario.OPERADOR,
                "enviar": IntencaoUsuario.OPERADOR,
                "ajuda": IntencaoUsuario.CONVERSACAO,
                "oi": IntencaoUsuario.CONVERSACAO,
                " Thiago".strip(): IntencaoUsuario.CONVERSACAO,
            }
            # Usa ratio estrito para evitar falsos positivos
            close = difflib.get_close_matches(mensagem_lower, whitelist.keys(), n=1, cutoff=0.75)
            if close:
                intent = whitelist[close[0]]
                if intent in (IntencaoUsuario.SALDO_RAPIDO, IntencaoUsuario.OPERADOR):
                    return intent

        return IntencaoUsuario.CONVERSACAO
    
    def _normalize_text(self, text: str) -> str:
        """Normaliza texto para matching (remove acentos comuns)"""
        replacements = {
            'ã': 'a', 'õ': 'o', 'ç': 'c',
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'â': 'a', 'ê': 'e', 'ô': 'o',
            'à': 'a', 'è': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u'
        }
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        return text
    
    # ═════════════════════════════════════════════════════════════════
    # MÉTODOS DE CONVENIÊNCIA
    # ═════════════════════════════════════════════════════════════════
    
    def classificar_sync(self, mensagem: str) -> IntencaoUsuario:
        """
        Versão síncrona - usa apenas Regex.
        Útil para contextos onde async não é possível.
        """
        return self._classificar_regex(mensagem)
    
    async def classificar_batch(self, mensagens: list) -> list:
        """
        Classifica múltiplas mensagens em batch usando apenas regex.
        """
        resultados = []
        for msg in mensagens:
            resultado = await self.classificar(msg, usar_haiku=False)
            resultados.append(resultado)
        return resultados


# Instância global
_classifier_instance: Optional[IntentionClassifier] = None


def get_intention_classifier() -> IntentionClassifier:
    """Retorna instância singleton do classificador"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = IntentionClassifier()
    return _classifier_instance


# ═════════════════════════════════════════════════════════════════════
# FUNÇÕES DE COMPATIBILIDADE (substituem detectar_intencao_assistente)
# ═════════════════════════════════════════════════════════════════════

def detectar_intencao_assistente(mensagem: str) -> str:
    """
    Função compatível com a API anterior.
    Retorna string da intenção (ex: "SALDO_RAPIDO").
    """
    classifier = get_intention_classifier()
    intencao = classifier.classificar_sync(mensagem)
    return intencao.value


async def detectar_intencao_assistente_async(
    mensagem: str,
    usar_haiku: bool = True
) -> ClassificacaoResult:
    """
    Versão assíncrona compatível.
    Retorna ClassificacaoResult usando apenas regex local.
    """
    classifier = get_intention_classifier()
    return await classifier.classificar(mensagem, usar_haiku=usar_haiku)


# ═════════════════════════════════════════════════════════════════════
# FUNÇÃO SALDO RÁPIDO (movida de cotte_ai_hub.py)
# ═════════════════════════════════════════════════════════════════════

async def saldo_rapido_ia(
    db: Optional[Any] = None,
    empresa_id: Optional[int] = None
) -> Any:
    """
    Retorna saldo atual de forma rápida e objetiva.
    NÃO usa IA - apenas busca dados e formata resposta simples.
    
    Args:
        db: Sessão do banco de dados
        empresa_id: ID da empresa
        
    Returns:
        AIResponse com resposta curta do saldo atual
    """
    # Importar AIResponse aqui para evitar circular imports
    try:
        from app.services.cotte_ai_hub import AIResponse
    except ImportError:
        # Se não conseguir importar, criar uma classe simples compatível
        class AIResponse:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
    
    # Importar modelos aqui para evitar circular imports
    try:
        from app.models.models import SaldoCaixaConfig
        from app.services import financeiro_service
    except ImportError:
        # Fallback se modelos não disponíveis
        return AIResponse(
            sucesso=False,
            resposta="Erro interno: modelos não disponíveis",
            tipo_resposta="erro",
            confianca=0.0,
            erros=["ImportError: modelos"],
            modulo_origem="financeiro_saldo"
        )
    
    if not db or not empresa_id:
        return AIResponse(
            sucesso=False,
            resposta="Não foi possível consultar o saldo. Empresa não identificada.",
            tipo_resposta="erro",
            confianca=0.0,
            erros=["empresa_id ou db não fornecido"],
            modulo_origem="financeiro_saldo"
        )
    
    try:
        # Buscar saldo inicial configurado
        saldo_config = db.query(SaldoCaixaConfig).filter(
            SaldoCaixaConfig.empresa_id == empresa_id
        ).first()
        saldo_inicial = saldo_config.saldo_inicial if saldo_config else Decimal("0")
        
        # Calcular saldo real usando a nova regra operacional
        saldo_atual = financeiro_service.calcular_saldo_caixa_kpi(empresa_id, db)
        
        # Formatar resposta BRL (1.250,00)
        saldo_formatado = f"R$ {saldo_atual:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        # Resposta curta e direta conforme o operacional solicitado
        resposta = f"Seu caixa atual é {saldo_formatado}.\n"
        resposta += "Esse valor considera apenas entradas recebidas e saídas já pagas."
        
        return AIResponse(
            sucesso=True,
            resposta=resposta,
            tipo_resposta="saldo_caixa",
            dados={
                "tipo": "saldo_caixa",
                "saldo_atual": float(saldo_atual),
                "saldo_inicial": float(saldo_inicial),
                "definicao": "Caixa operacional: Entradas reais - Saídas reais + Saldo Inicial."
            },
            confianca=0.98,
            modulo_origem="financeiro_saldo"
        )
        
    except Exception as e:
        logger.error(f"[saldo_rapido_ia] Erro ao consultar saldo: {e}")
        return AIResponse(
            sucesso=False,
            resposta="Não foi possível consultar o saldo no momento. Tente novamente.",
            tipo_resposta="erro",
            confianca=0.0,
            erros=[str(e)],
            modulo_origem="financeiro_saldo"
        )


# Mapeamento de intenções para funções do hub
INTENCAO_TO_FUNC = {
    IntencaoUsuario.SALDO_RAPIDO: "saldo_rapido_ia",
    IntencaoUsuario.FATURAMENTO: "faturamento_ia",
    IntencaoUsuario.CONTAS_RECEBER: "contas_receber_ia",
    IntencaoUsuario.CONTAS_PAGAR: "contas_pagar_ia",
    IntencaoUsuario.DASHBOARD: "dashboard_financeiro_ia",
    IntencaoUsuario.PREVISAO: "previsao_caixa_ia",
    IntencaoUsuario.INADIMPLENCIA: "clientes_devendo_ia",
    IntencaoUsuario.ANALISE: "analisar_financeiro_ia",
    IntencaoUsuario.CONVERSAO: "analisar_conversao_ia",
    IntencaoUsuario.NEGOCIO: "gerar_sugestoes_negocio_ia",
    IntencaoUsuario.CONVERSACAO: "processar_conversacao",
}
