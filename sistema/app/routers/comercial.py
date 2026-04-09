"""
Router principal do módulo comercial — Stub de compatibilidade.

Os endpoints foram divididos em módulos especializados:
- comercial_leads.py      → CRUD de leads, dashboard, importações, envio em lote
- comercial_pipeline.py   → Pipeline stages e atualização de status
- comercial_interacoes.py → Interações, WhatsApp/e-mail, lembretes, templates
- comercial_config.py     → Segmentos, origens e configurações

Este arquivo mantém o router para compatibilidade com importações existentes.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/comercial", tags=["Comercial"])


@router.get("/health")
def health_check():
    """Health check do módulo comercial."""
    return {"status": "ok", "module": "comercial"}
