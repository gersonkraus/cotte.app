"""
Configuração de limites padrão por plano (trial, starter, pro, business).
Persistida em static/config/plan_defaults.json para edição pelo Admin
sem alterar código. O plano_service usa esses valores quando não há
override por empresa.
"""
import json
import os
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

PLAN_DEFAULTS_PATH = Path("static/config/plan_defaults.json")

# Valores padrão (fallback quando o arquivo não existe)
PLAN_DEFAULTS_FALLBACK: Dict[str, Dict[str, Any]] = {
    "trial": {"limite_orcamentos": 50, "limite_usuarios": 1},
    "starter": {"limite_orcamentos": 200, "limite_usuarios": 3},
    "pro": {"limite_orcamentos": 1000, "limite_usuarios": 10},
    "business": {"limite_orcamentos": None, "limite_usuarios": None},
}


def get_plan_defaults() -> Dict[str, Dict[str, Any]]:
    """Lê plan_defaults.json ou retorna os valores padrão."""
    try:
        if PLAN_DEFAULTS_PATH.exists():
            with PLAN_DEFAULTS_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    merged = {}
                    for plano in ("trial", "starter", "pro", "business"):
                        merged[plano] = {
                            **PLAN_DEFAULTS_FALLBACK.get(plano, {}),
                            **(data.get(plano) or {}),
                        }
                    return merged
    except Exception:
        logger.exception("Falha ao ler plan_defaults.json")
    return dict(PLAN_DEFAULTS_FALLBACK)


def save_plan_defaults(cfg: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Salva plan_defaults.json.
    Espera chaves trial, starter, pro, business com limite_orcamentos e limite_usuarios
    (number ou null para ilimitado).
    """
    merged = {}
    for plano in ("trial", "starter", "pro", "business"):
        base = PLAN_DEFAULTS_FALLBACK.get(plano, {})
        entrada = (cfg or {}).get(plano) or {}
        limite_orc = entrada.get("limite_orcamentos")
        limite_usr = entrada.get("limite_usuarios")
        if limite_orc is not None and limite_orc != "":
            try:
                limite_orc = int(limite_orc)
            except (TypeError, ValueError):
                limite_orc = base.get("limite_orcamentos")
        else:
            limite_orc = base.get("limite_orcamentos")
        if limite_usr is not None and limite_usr != "":
            try:
                limite_usr = int(limite_usr)
            except (TypeError, ValueError):
                limite_usr = base.get("limite_usuarios")
        else:
            limite_usr = base.get("limite_usuarios")
        merged[plano] = {"limite_orcamentos": limite_orc, "limite_usuarios": limite_usr}

    os.makedirs(PLAN_DEFAULTS_PATH.parent, exist_ok=True)
    with PLAN_DEFAULTS_PATH.open("w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    return merged
