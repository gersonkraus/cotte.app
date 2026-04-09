import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_CHAVE_NUMEROS = "numeros_monitoramento"
_CHAVE_TRIAL_DIAS = "dias_trial_padrao"
_JSON_LEGADO = Path("static/config/admin_settings.json")


def _migrar_json_se_necessario(db: Session) -> None:
    """Na primeira execução, importa dados do JSON legado para o banco."""
    from app.models.models import ConfigGlobal
    existente = db.get(ConfigGlobal, _CHAVE_NUMEROS)
    if existente is not None:
        return
    numeros: List[str] = []
    try:
        if _JSON_LEGADO.exists():
            data = json.loads(_JSON_LEGADO.read_text(encoding="utf-8"))
            numeros = data.get(_CHAVE_NUMEROS, [])
    except (json.JSONDecodeError, OSError):
        pass
    db.add(ConfigGlobal(chave=_CHAVE_NUMEROS, valor=json.dumps(numeros)))
    db.add(ConfigGlobal(chave=_CHAVE_TRIAL_DIAS, valor=json.dumps(14))) # 14 padrao
    db.commit()


def get_admin_config(db: Session) -> Dict[str, Any]:
    from app.models.models import ConfigGlobal
    _migrar_json_se_necessario(db)
    
    # Busca numeros
    row_num = db.get(ConfigGlobal, _CHAVE_NUMEROS)
    try:
        numeros = json.loads(row_num.valor) if row_num and row_num.valor else []
    except json.JSONDecodeError:
        numeros = []

    # Busca trial days
    row_trial = db.get(ConfigGlobal, _CHAVE_TRIAL_DIAS)
    try:
        dias_trial = int(json.loads(row_trial.valor)) if row_trial and row_trial.valor else 14
    except (json.JSONDecodeError, ValueError):
        dias_trial = 14

    return {
        _CHAVE_NUMEROS: numeros,
        _CHAVE_TRIAL_DIAS: dias_trial
    }


def save_admin_config(cfg: Dict[str, Any], db: Session) -> Dict[str, Any]:
    from app.models.models import ConfigGlobal
    
    # Numeros
    numeros = cfg.get(_CHAVE_NUMEROS, [])
    row_num = db.get(ConfigGlobal, _CHAVE_NUMEROS)
    if row_num:
        row_num.valor = json.dumps(numeros)
    else:
        db.add(ConfigGlobal(chave=_CHAVE_NUMEROS, valor=json.dumps(numeros)))

    # Trial days
    dias_trial = cfg.get(_CHAVE_TRIAL_DIAS, 14)
    row_trial = db.get(ConfigGlobal, _CHAVE_TRIAL_DIAS)
    if row_trial:
        row_trial.valor = json.dumps(dias_trial)
    else:
        db.add(ConfigGlobal(chave=_CHAVE_TRIAL_DIAS, valor=json.dumps(dias_trial)))

    db.commit()
    return {
        _CHAVE_NUMEROS: numeros,
        _CHAVE_TRIAL_DIAS: dias_trial
    }
