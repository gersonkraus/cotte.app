# sistema/app/services/ia_service.py
"""
Proxy para o novo módulo app.ai.service.
Mantido para retrocompatibilidade.
"""

from app.ai.service import (
    ia_service,
    IAService,
    normalize_litellm_model,
    sanitizar_mensagem,
    interpretar_mensagem,
    interpretar_comando_operador,
    gerar_resposta_bot,
    interpretar_tabela_catalogo,
    analisar_leads,
    gerar_briefing_lead,
    _briefing_fallback,
    logger
)
