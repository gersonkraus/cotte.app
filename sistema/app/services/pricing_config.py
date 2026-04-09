import json
import os
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

PRICING_PATH = Path("static/config/pricing.json")

PRICING_DEFAULT: Dict[str, Dict[str, Any]] = {
    "starter": {"preco": 49, "orcamentos": 200, "usuarios": 3},
    "pro": {"preco": 119, "orcamentos": 1000, "usuarios": 10},
    "business": {"preco": 299, "orcamentos": None, "usuarios": None},
}


def get_pricing_config() -> Dict[str, Dict[str, Any]]:
    """Lê o pricing.json ou retorna defaults."""
    try:
        if PRICING_PATH.exists():
            with PRICING_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {**PRICING_DEFAULT, **data}
    except (json.JSONDecodeError, OSError):
        logger.exception("Falha ao ler pricing.json")
    return PRICING_DEFAULT


def save_pricing_config(cfg: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Salva o pricing.json (merge com defaults) e retorna o resultado."""
    merged = {**PRICING_DEFAULT, **(cfg or {})}
    os.makedirs(PRICING_PATH.parent, exist_ok=True)
    with PRICING_PATH.open("w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    return merged
