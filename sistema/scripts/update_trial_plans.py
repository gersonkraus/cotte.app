"""
Sincroniza o plano de avaliação (trial) com PLANOS_SEED['trial'] no banco.

Útil após deploy sem reiniciar a API, ou para validar antes do próximo startup
(o seed em `main.py` já chama a mesma lógica).

Uso:
    cd sistema && python scripts/update_trial_plans.py
    cd sistema && python scripts/update_trial_plans.py --apply
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import func

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from app.core.database import SessionLocal  # noqa: E402
from app.models.models import Plano  # noqa: E402
from app.services.seed_modulos import PLANOS_SEED, seed_modulos_e_planos_padrao  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Alinha módulos do plano trial com o seed (idempotente com --apply)."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Executa o seed completo de módulos/planos/papéis (grava no banco).",
    )
    return parser.parse_args()


def _dry_run() -> int:
    db = SessionLocal()
    try:
        plano = db.query(Plano).filter(func.lower(Plano.nome) == "trial").first()
        if plano is None:
            print("Nenhum plano com nome 'trial' (ignorando maiúsculas) encontrado.")
            return 1
        existentes = {m.slug for m in plano.modulos}
        alvo = PLANOS_SEED.get("trial", [])
        faltando = [s for s in alvo if s not in existentes]
        print(f"Plano trial id={plano.id} nome={plano.nome!r}")
        print(f"Módulos desejados ({len(alvo)}): {', '.join(alvo)}")
        print(f"Módulos atuais ({len(existentes)}): {', '.join(sorted(existentes))}")
        if not faltando:
            print("Nada a acrescentar — já está alinhado ao seed.")
            return 0
        print(f"Seriam acrescentados ({len(faltando)}): {', '.join(faltando)}")
        print("Rode com --apply para gravar (usa seed_modulos_e_planos_padrao).")
        return 0
    finally:
        db.close()


def main() -> int:
    args = _parse_args()
    if not args.apply:
        return _dry_run()
    db = SessionLocal()
    try:
        seed_modulos_e_planos_padrao(db)
        print("Seed concluído (módulos, plano trial, papéis por empresa).")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
