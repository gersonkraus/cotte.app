"""
Extrator Robusto de JSON - COTTE AI Hub
Etapa 1: Robustez na Extração de JSON com Regex

Este módulo substitui a lógica frágil de split por expressões regulares
que localizam o primeiro '{' e o último '}' garantindo extração mesmo
quando a IA adiciona conversas antes ou depois do JSON.
"""

import json
import re
import logging
from typing import Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class JSONExtractionStrategy(Enum):
    """Estratégias de extração de JSON disponíveis"""
    REGEX_BALANCED = "regex_balanced"      # Regex com balanceamento de chaves
    REGEX_GREEDY = "regex_greedy"          # Regex greedy simples (fallback)
    MARKDOWN_CODEBLOCK = "markdown_block"  # Extrai de ```json ... ```
    FIRST_LAST_BRACE = "first_last_brace"  # Primeiro { e último }


class AIJSONExtractor:
    """
    Extrator robusto de JSON de respostas de IA.
    
    Problema: IAs como Claude às vezes adicionam texto explicativo antes
    ou depois do JSON, ou retornam markdown codeblocks.
    
    Solução: Múltiplas estratégias de extração com fallback inteligente.
    """
    
    # Regex para encontrar JSON com balanceamento de chaves
    # Captura o primeiro { e o último } correspondente
    _BALANCED_JSON_REGEX = re.compile(
        r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',
        re.DOTALL
    )
    
    # Regex para codeblocks markdown
    _CODEBLOCK_REGEX = re.compile(
        r'```(?:json)?\s*\n?(.*?)```',
        re.DOTALL | re.IGNORECASE
    )
    
    # Regex para primeiro { e último }
    _FIRST_LAST_BRACE_REGEX = re.compile(
        r'^(.*?)\{(.*)\}(.*?)$',
        re.DOTALL
    )
    
    @classmethod
    def extract(
        cls, 
        text: str, 
        strategy: JSONExtractionStrategy = JSONExtractionStrategy.REGEX_BALANCED,
        try_all_strategies: bool = True
    ) -> Optional[dict]:
        """
        Extrai JSON válido de texto da IA.
        
        Args:
            text: Texto retornado pela IA
            strategy: Estratégia principal de extração
            try_all_strategies: Se True, tenta todas as estratégias em ordem
        
        Returns:
            dict com dados extraídos ou None se falhar
        """
        if not text or not isinstance(text, str):
            logger.warning("[JSONExtractor] Texto vazio ou inválido")
            return None
        
        text = text.strip()
        
        # Se já é um JSON puro, retorna direto
        if text.startswith('{') and text.endswith('}'):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass  # Continua para estratégias de extração
        
        strategies = [
            JSONExtractionStrategy.MARKDOWN_CODEBLOCK,
            JSONExtractionStrategy.REGEX_BALANCED,
            JSONExtractionStrategy.FIRST_LAST_BRACE,
            JSONExtractionStrategy.REGEX_GREEDY,
        ]
        
        # Se não deve tentar todas, usa apenas a especificada
        if not try_all_strategies:
            strategies = [strategy]
        
        for strat in strategies:
            try:
                result = cls._try_strategy(text, strat)
                if result is not None:
                    logger.debug(f"[JSONExtractor] Sucesso com estratégia: {strat.value}")
                    return result
            except Exception as e:
                logger.debug(f"[JSONExtractor] Falha na estratégia {strat.value}: {e}")
                continue
        
        logger.warning(f"[JSONExtractor] Todas as estratégias falharam para texto: {text[:100]}...")
        return None
    
    @classmethod
    def _try_strategy(cls, text: str, strategy: JSONExtractionStrategy) -> Optional[dict]:
        """Tenta uma estratégia específica de extração"""
        
        if strategy == JSONExtractionStrategy.MARKDOWN_CODEBLOCK:
            return cls._extract_from_codeblock(text)
        
        elif strategy == JSONExtractionStrategy.REGEX_BALANCED:
            return cls._extract_balanced_json(text)
        
        elif strategy == JSONExtractionStrategy.FIRST_LAST_BRACE:
            return cls._extract_first_last_brace(text)
        
        elif strategy == JSONExtractionStrategy.REGEX_GREEDY:
            return cls._extract_greedy_json(text)
        
        return None
    
    @classmethod
    def _extract_from_codeblock(cls, text: str) -> Optional[dict]:
        """Extrai JSON de codeblocks markdown ```json ... ```"""
        match = cls._CODEBLOCK_REGEX.search(text)
        if match:
            json_str = match.group(1).strip()
            # Remove prefixo 'json' se existir
            if json_str.lower().startswith('json'):
                json_str = json_str[4:].strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        return None
    
    @classmethod
    def _extract_balanced_json(cls, text: str) -> Optional[dict]:
        """
        Extrai JSON usando regex com balanceamento de chaves.
        Encontra o primeiro '{' e o último '}' correspondente.
        """
        # Procura por objetos JSON válidos
        for match in cls._BALANCED_JSON_REGEX.finditer(text):
            json_str = match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                continue
        return None
    
    @classmethod
    def _extract_first_last_brace(cls, text: str) -> Optional[dict]:
        """
        Extrai JSON localizando o primeiro '{' e o último '}'.
        Útil quando a IA envolve o JSON em texto explicativo.
        """
        # Encontra o primeiro {
        first_brace = text.find('{')
        if first_brace == -1:
            return None
        
        # Encontra o último }
        last_brace = text.rfind('}')
        if last_brace == -1 or last_brace <= first_brace:
            return None
        
        # Extrai o conteúdo entre eles
        json_str = text[first_brace:last_brace + 1]
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None
    
    @classmethod
    def _extract_greedy_json(cls, text: str) -> Optional[dict]:
        """Estratégia greedy - pega tudo entre o primeiro { e último }"""
        match = cls._FIRST_LAST_BRACE_REGEX.search(text)
        if match:
            json_str = '{' + match.group(2) + '}'
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        return None
    
    @classmethod
    def extract_with_metadata(cls, text: str) -> dict:
        """
        Extrai JSON e retorna metadados sobre o processo.
        
        Returns:
            {
                "success": bool,
                "data": dict | None,
                "strategy_used": str | None,
                "original_length": int,
                "extracted_length": int,
                "error": str | None
            }
        """
        result = {
            "success": False,
            "data": None,
            "strategy_used": None,
            "original_length": len(text) if text else 0,
            "extracted_length": 0,
            "error": None
        }
        
        if not text:
            result["error"] = "Texto vazio"
            return result
        
        strategies = [
            JSONExtractionStrategy.MARKDOWN_CODEBLOCK,
            JSONExtractionStrategy.REGEX_BALANCED,
            JSONExtractionStrategy.FIRST_LAST_BRACE,
            JSONExtractionStrategy.REGEX_GREEDY,
        ]
        
        for strategy in strategies:
            try:
                data = cls._try_strategy(text, strategy)
                if data is not None:
                    result["success"] = True
                    result["data"] = data
                    result["strategy_used"] = strategy.value
                    result["extracted_length"] = len(json.dumps(data))
                    return result
            except Exception as e:
                continue
        
        result["error"] = "Todas as estratégias de extração falharam"
        return result


# Função de conveniência para backward compatibility
def extract_json_from_ai_response(text: str, default: Any = None) -> Any:
    """
    Função simplificada para extrair JSON de resposta da IA.
    
    Args:
        text: Texto da resposta da IA
        default: Valor padrão se extração falhar
    
    Returns:
        dict extraído ou valor default
    """
    result = AIJSONExtractor.extract(text)
    return result if result is not None else default


# Regex pre-compilados para uso direto (performance)
JSON_BLOCK_REGEX = re.compile(r'```(?:json)?\s*\n?(.*?)```', re.DOTALL | re.IGNORECASE)
BALANCED_BRACES_REGEX = re.compile(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', re.DOTALL)