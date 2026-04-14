"""Serviço de rollout controlado da IA V2 por empresa (Sprint 9)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.models import ConfigGlobal

ROLLOUT_CONFIG_KEY = "ai_rollout_v2_plan"
ROLLOUT_PHASES = {"disabled", "pilot", "ga"}
ENGINE_KEYS = ("operational", "analytics", "documental", "internal_copilot")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_plan() -> dict[str, Any]:
    return {
        "default_phase": "disabled",
        "companies": {},
        "updated_at": _utc_now_iso(),
    }


def _normalize_phase(value: str | None) -> str:
    phase = (value or "disabled").strip().lower()
    if phase not in ROLLOUT_PHASES:
        return "disabled"
    return phase


def _normalize_engines(value: list[str] | None) -> list[str]:
    if not isinstance(value, list):
        return []
    valid = []
    seen = set()
    for item in value:
        key = str(item or "").strip().lower()
        if key in ENGINE_KEYS and key not in seen:
            valid.append(key)
            seen.add(key)
    return valid


def _normalize_companies(raw_companies: Any) -> dict[str, Any]:
    if not isinstance(raw_companies, dict):
        return {}
    out: dict[str, Any] = {}
    for empresa_key, cfg in raw_companies.items():
        try:
            empresa_id = int(str(empresa_key).strip())
        except (TypeError, ValueError):
            continue
        if empresa_id <= 0:
            continue
        cfg_dict = cfg if isinstance(cfg, dict) else {}
        out[str(empresa_id)] = {
            "phase": _normalize_phase(cfg_dict.get("phase")),
            "enabled_engines": _normalize_engines(cfg_dict.get("enabled_engines")),
            "notes": str(cfg_dict.get("notes") or "").strip()[:500] or None,
            "updated_at": str(cfg_dict.get("updated_at") or _utc_now_iso()),
            "updated_by": cfg_dict.get("updated_by"),
        }
    return out


def normalize_rollout_plan(raw: Any) -> dict[str, Any]:
    src = raw if isinstance(raw, dict) else {}
    return {
        "default_phase": _normalize_phase(src.get("default_phase")),
        "companies": _normalize_companies(src.get("companies")),
        "updated_at": str(src.get("updated_at") or _utc_now_iso()),
    }


def get_rollout_plan(db: Session) -> dict[str, Any]:
    row = db.get(ConfigGlobal, ROLLOUT_CONFIG_KEY)
    if not row or not row.valor:
        return _default_plan()
    try:
        payload = json.loads(row.valor)
    except (TypeError, json.JSONDecodeError):
        return _default_plan()
    return normalize_rollout_plan(payload)


def save_rollout_plan(db: Session, plan: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_rollout_plan(plan)
    row = db.get(ConfigGlobal, ROLLOUT_CONFIG_KEY)
    payload_str = json.dumps(normalized, ensure_ascii=False)
    if row:
        row.valor = payload_str
    else:
        db.add(ConfigGlobal(chave=ROLLOUT_CONFIG_KEY, valor=payload_str))
    db.commit()
    return normalized


def build_rollout_plan_from_payload(
    *,
    default_phase: str,
    companies: list[dict[str, Any]],
    updated_by: int | None,
) -> dict[str, Any]:
    normalized_default = _normalize_phase(default_phase)
    companies_map: dict[str, Any] = {}
    for item in companies:
        empresa_id = int(item["empresa_id"])
        companies_map[str(empresa_id)] = {
            "phase": _normalize_phase(item.get("phase")),
            "enabled_engines": _normalize_engines(item.get("enabled_engines")),
            "notes": str(item.get("notes") or "").strip()[:500] or None,
            "updated_at": _utc_now_iso(),
            "updated_by": updated_by,
        }
    return {
        "default_phase": normalized_default,
        "companies": companies_map,
        "updated_at": _utc_now_iso(),
    }


def get_rollout_for_empresa(db: Session, empresa_id: int) -> dict[str, Any]:
    plan = get_rollout_plan(db)
    empresa_cfg = (plan.get("companies") or {}).get(str(int(empresa_id))) or {}
    phase = _normalize_phase(empresa_cfg.get("phase") or plan.get("default_phase"))
    engines = _normalize_engines(empresa_cfg.get("enabled_engines"))
    if not engines and phase == "ga":
        engines = list(ENGINE_KEYS)
    return {
        "phase": phase,
        "enabled_engines": engines,
        "source": "company" if empresa_cfg else "default",
        "plan_updated_at": plan.get("updated_at"),
        "company_updated_at": empresa_cfg.get("updated_at"),
        "company_updated_by": empresa_cfg.get("updated_by"),
        "notes": empresa_cfg.get("notes"),
    }
