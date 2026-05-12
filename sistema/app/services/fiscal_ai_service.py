"""
fiscal_ai_service.py

Sugere dados fiscais (NCM, CFOP, CSOSN, origem, unidade) para produtos
usando IA, com defaults inteligentes para Simples Nacional como fallback.
"""

import logging
from typing import Optional

from app.services.ia_service import IAService
from app.services.ai_json_extractor import AIJSONExtractor

logger = logging.getLogger(__name__)

# Defaults Simples Nacional
_DEFAULTS = {
    "ncm": None,
    "cfop": "5102",
    "csosn": "400",
    "origem": 0,
    "unidade": "UN",
    "confianca": "baixa",
}

_PROMPT_SISTEMA = """Você é um especialista em classificação fiscal brasileira.
Dado o nome/descrição de um produto, retorne um JSON com os dados fiscais para NF-e no Simples Nacional.

Responda SOMENTE com JSON, sem explicações:
{
  "ncm": "XXXXXXXX",  // código NCM com 8 dígitos, ou null se não souber
  "cfop": "XXXX",     // 4 dígitos, default 5102 (venda interna)
  "csosn": "XXX",     // 3-4 chars, default 400 (tributado Simples)
  "origem": 0,        // 0=nacional, 1=importado
  "unidade": "XX",    // UN, PC, KG, MT, CX, etc.
  "confianca": "alta" // alta|media|baixa
}

Exemplos de NCM comuns:
- Papel A4, caderno → 4820.10.00
- Caneta, lápis → 9608.10.00
- Tinta, verniz → 3208.10.00
- Cabo elétrico → 8544.42.00
- Parafuso, prego → 7317.00.90
- Tinta spray → 3212.10.00
- Serra, alicate → 8203.10.00
- Cimento → 2523.21.00
- Tijolo → 6901.00.00
- Tubo PVC → 3917.21.10
"""


async def sugerir_dados_fiscais(
    descricao: str,
    categoria: Optional[str] = None,
    preco: Optional[float] = None,
) -> dict:
    """
    Sugere NCM, CFOP, CSOSN, origem e unidade para um produto.
    Retorna defaults para Simples Nacional em caso de falha da IA.
    """
    texto_produto = descricao.strip()
    if categoria:
        texto_produto += f" (categoria: {categoria})"
    if preco:
        texto_produto += f" (preço aprox: R$ {preco:.2f})"

    try:
        ia = IAService()
        response = await ia.chat(
            messages=[
                {"role": "system", "content": _PROMPT_SISTEMA},
                {"role": "user", "content": f"Produto: {texto_produto}"},
            ],
            temperature=0.1,
            max_tokens=300,
        )

        content = response["choices"][0]["message"]["content"]
        dados = AIJSONExtractor.extract(content)

        result = {**_DEFAULTS}
        if isinstance(dados, dict):
            for campo in ("ncm", "cfop", "csosn", "origem", "unidade", "confianca"):
                if dados.get(campo) is not None:
                    result[campo] = dados[campo]

        # normaliza NCM: remove pontos/traços, rejeita se < 8 dígitos
        if result.get("ncm"):
            ncm_clean = str(result["ncm"]).replace(".", "").replace("-", "").strip()
            result["ncm"] = ncm_clean if len(ncm_clean) >= 8 else None

        return result

    except Exception as e:
        logger.warning(f"fiscal_ai_service: erro ao sugerir dados para '{descricao}': {e}")
        return {**_DEFAULTS}
