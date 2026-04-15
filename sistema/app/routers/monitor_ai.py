from fastapi import APIRouter, Depends, HTTPException, Body, Query
from typing import Dict, Any, List
import logging
from sqlalchemy.orm import Session

from app.core.auth import get_superadmin
from app.core.database import get_db
from app.models.models import Usuario
from app.services.monitor_ai_service import process_monitor_query
from app.services.ai_observability_service import build_token_chart_data

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/agent")
def monitor_ai_agent(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_superadmin),
) -> Dict[str, Any]:
    """
    Endpoint para o agente do Monitor AI.
    Apenas superadmins podem acessar.
    """
    query = payload.get("query")
    history = payload.get("history", [])

    if not query:
        raise HTTPException(status_code=400, detail="Query não informada.")

    try:
        result = process_monitor_query(query, history)
        return result
    except Exception as e:
        logger.error(f"Erro no endpoint Monitor AI: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
def monitor_ai_status(
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_superadmin)
) -> Dict[str, Any]:
    """
    Endpoint para retornar o status rápido do sistema para a sidebar do Monitor AI.
    Apenas superadmins podem acessar.
    """
    try:
        # Aqui você pode expandir as métricas lendo o banco de dados.
        # Exemplo estático ou buscas rápidas:

        return {
            "success": True,
            "status": {
                "erros_24h": 0,
                "jobs_pendentes": 0,
                "cpu_usage": "N/A",  # Poderia usar psutil
                "db_status": "Online",
            },
        }
    except Exception as e:
        logger.error(f"Erro ao buscar status no Monitor AI: {e}")
        return {"success": False, "status": {}}


@router.get("/stats")
def monitor_ai_stats(
    hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_superadmin),
) -> Dict[str, Any]:
    """
    Agregação de consumo de tokens por engine e por dia.
    Usado pelo dashboard de observabilidade IA.
    Apenas superadmins podem acessar.
    """
    try:
        data = build_token_chart_data(db=db, hours=hours, empresa_id=None)
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Erro ao gerar stats de tokens: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
