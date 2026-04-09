"""
Serviço para processamento de documentos HTML com substituição de variáveis.

Este módulo fornece funcionalidades para:
1. Extrair variáveis de templates HTML
2. Substituir variáveis por valores dinâmicos
3. Validar e processar conteúdo HTML
"""

import re
import json
from typing import Dict, List, Optional, Any
from datetime import datetime


def extrair_variaveis_html(html_content: str) -> List[str]:
    """
    Extrai todas as variáveis do formato {nome_variavel} de um conteúdo HTML.
    
    Args:
        html_content: Conteúdo HTML a ser analisado
        
    Returns:
        Lista de nomes de variáveis únicas encontradas
    """
    if not html_content:
        return []
    
    # Padrão para encontrar variáveis no formato {nome_variavel}
    # Suporta letras, números, underscores e hífens dentro das chaves
    padrao = r'\{([a-zA-Z0-9_\-]+)\}'
    
    # Encontrar todas as correspondências
    matches = re.findall(padrao, html_content)
    
    # Remover duplicatas mantendo a ordem
    variaveis_unicas = []
    for var in matches:
        if var not in variaveis_unicas:
            variaveis_unicas.append(var)
    
    return variaveis_unicas


def substituir_variaveis_html(
    html_content: str, 
    valores: Dict[str, Any],
    manter_variaveis_nao_encontradas: bool = False
) -> str:
    """
    Substitui variáveis no formato {nome_variavel} por valores fornecidos.
    
    Args:
        html_content: Conteúdo HTML com variáveis
        valores: Dicionário com valores para substituição
        manter_variaveis_nao_encontradas: Se True, mantém variáveis não encontradas no formato original
        
    Returns:
        Conteúdo HTML com variáveis substituídas
    """
    if not html_content:
        return ""
    
    # Função de substituição
    def substituir(match):
        var_name = match.group(1)
        if var_name in valores:
            valor = valores[var_name]
            # Converter para string se não for
            if not isinstance(valor, str):
                valor = str(valor)
            return valor
        elif manter_variaveis_nao_encontradas:
            # Manter a variável no formato original
            return match.group(0)
        else:
            # Remover a variável (substituir por string vazia)
            return ""
    
    # Padrão para encontrar variáveis
    padrao = r'\{([a-zA-Z0-9_\-]+)\}'
    
    # Realizar substituição
    resultado = re.sub(padrao, substituir, html_content)
    
    return resultado


def validar_variaveis_suportadas(
    html_content: str, 
    variaveis_suportadas: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Valida se todas as variáveis no conteúdo HTML estão na lista de variáveis suportadas.
    
    Args:
        html_content: Conteúdo HTML a ser validado
        variaveis_suportadas: Lista de variáveis suportadas (None para extrair do conteúdo)
        
    Returns:
        Dicionário com informações de validação:
        - 'valido': bool indicando se todas as variáveis são suportadas
        - 'variaveis_encontradas': lista de variáveis encontradas no conteúdo
        - 'variaveis_nao_suportadas': lista de variáveis não suportadas (se houver)
        - 'sugestao_variaveis_suportadas': lista sugerida de variáveis suportadas
    """
    # Extrair variáveis do conteúdo
    variaveis_encontradas = extrair_variaveis_html(html_content)
    
    resultado = {
        'valido': True,
        'variaveis_encontradas': variaveis_encontradas,
        'variaveis_nao_suportadas': [],
        'sugestao_variaveis_suportadas': variaveis_encontradas.copy()
    }
    
    # Se não há lista de variáveis suportadas, considerar todas como suportadas
    if variaveis_suportadas is None:
        return resultado
    
    # Verificar quais variáveis não estão na lista de suportadas
    for var in variaveis_encontradas:
        if var not in variaveis_suportadas:
            resultado['variaveis_nao_suportadas'].append(var)
            resultado['valido'] = False
    
    return resultado


def gerar_valores_padrao(variaveis: List[str]) -> Dict[str, str]:
    """
    Gera valores padrão para variáveis com base em nomes comuns.
    
    Args:
        variaveis: Lista de nomes de variáveis
        
    Returns:
        Dicionário com valores padrão para cada variável
    """
    valores_padrao = {}
    
    # Mapeamento de padrões de nomes para valores padrão
    padroes = {
        r'(?i)nome': 'João Silva',
        r'(?i)cliente': 'Cliente Exemplo',
        r'(?i)email': 'cliente@exemplo.com',
        r'(?i)telefone': '(11) 99999-9999',
        r'(?i)cpf': '123.456.789-00',
        r'(?i)cnpj': '12.345.678/0001-90',
        r'(?i)endereco': 'Rua Exemplo, 123 - Centro',
        r'(?i)cidade': 'São Paulo',
        r'(?i)estado': 'SP',
        r'(?i)cep': '01234-567',
        r'(?i)data': datetime.now().strftime('%d/%m/%Y'),
        r'(?i)hora': datetime.now().strftime('%H:%M'),
        r'(?i)valor': 'R$ 1.000,00',
        r'(?i)orcamento': 'ORC-2024-001',
        r'(?i)servico': 'Serviço Contratado',
        r'(?i)descricao': 'Descrição do serviço ou produto',
        r'(?i)empresa': 'Empresa Contratante',
        r'(?i)responsavel': 'Responsável pelo Contrato',
        r'(?i)assinatura': '________________________',
    }
    
    for var in variaveis:
        valor_encontrado = None
        for padrao_regex, valor in padroes.items():
            if re.search(padrao_regex, var):
                valor_encontrado = valor
                break
        
        if valor_encontrado:
            valores_padrao[var] = valor_encontrado
        else:
            # Valor genérico para variáveis não reconhecidas
            valores_padrao[var] = f"[{var.replace('_', ' ').title()}]"
    
    return valores_padrao


def processar_documento_html_com_variaveis(
    html_content: str,
    valores_variaveis: Optional[Dict[str, Any]] = None,
    variaveis_suportadas: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Processa um documento HTML com variáveis, realizando validação e substituição.
    
    Args:
        html_content: Conteúdo HTML do documento
        valores_variaveis: Valores para substituição (None para usar valores padrão)
        variaveis_suportadas: Lista de variáveis suportadas para validação
        
    Returns:
        Dicionário com resultados do processamento:
        - 'conteudo_processado': HTML com variáveis substituídas
        - 'variaveis_encontradas': lista de variáveis encontradas
        - 'variaveis_substituidas': lista de variáveis que foram substituídas
        - 'valores_utilizados': dicionário com valores utilizados
        - 'valido': bool indicando se o processamento foi bem-sucedido
        - 'erros': lista de mensagens de erro (se houver)
    """
    resultado = {
        'conteudo_processado': html_content,
        'variaveis_encontradas': [],
        'variaveis_substituidas': [],
        'valores_utilizados': {},
        'valido': True,
        'erros': []
    }
    
    # Extrair variáveis do conteúdo
    variaveis_encontradas = extrair_variaveis_html(html_content)
    resultado['variaveis_encontradas'] = variaveis_encontradas
    
    if not variaveis_encontradas:
        # Nenhuma variável encontrada, retornar conteúdo original
        return resultado
    
    # Validar variáveis se uma lista de suportadas foi fornecida
    if variaveis_suportadas is not None:
        validacao = validar_variaveis_suportadas(html_content, variaveis_suportadas)
        if not validacao['valido']:
            resultado['valido'] = False
            resultado['erros'].append(
                f"Variáveis não suportadas encontradas: {', '.join(validacao['variaveis_nao_suportadas'])}"
            )
            # Continuar processamento mesmo com variáveis não suportadas
    
    # Preparar valores para substituição
    if valores_variaveis is None:
        # Usar valores padrão baseados nos nomes das variáveis
        valores_variaveis = gerar_valores_padrao(variaveis_encontradas)
    
    # Filtrar apenas valores para variáveis encontradas
    valores_para_substituir = {}
    for var in variaveis_encontradas:
        if var in valores_variaveis:
            valores_para_substituir[var] = valores_variaveis[var]
            resultado['variaveis_substituidas'].append(var)
        else:
            # Variável encontrada mas sem valor fornecido
            resultado['erros'].append(f"Valor não fornecido para variável: {var}")
    
    resultado['valores_utilizados'] = valores_para_substituir.copy()
    
    # Realizar substituição (mantendo variáveis não encontradas)
    conteudo_processado = substituir_variaveis_html(
        html_content, 
        valores_para_substituir,
        manter_variaveis_nao_encontradas=True
    )
    
    resultado['conteudo_processado'] = conteudo_processado
    
    return resultado


def criar_preview_html(
    html_content: str,
    valores_variaveis: Optional[Dict[str, Any]] = None
) -> str:
    """
    Cria uma versão de preview do HTML com variáveis substituídas.
    
    Args:
        html_content: Conteúdo HTML original
        valores_variaveis: Valores para substituição
        
    Returns:
        HTML processado para preview
    """
    if not html_content:
        return ""
    
    # Extrair variáveis
    variaveis = extrair_variaveis_html(html_content)
    
    if not variaveis:
        return html_content
    
    # Usar valores fornecidos ou gerar valores padrão
    if valores_variaveis is None:
        valores_variaveis = gerar_valores_padrao(variaveis)
    
    # Substituir variáveis
    preview = substituir_variaveis_html(
        html_content, 
        valores_variaveis,
        manter_variaveis_nao_encontradas=False  # Remover variáveis não encontradas
    )
    
    return preview