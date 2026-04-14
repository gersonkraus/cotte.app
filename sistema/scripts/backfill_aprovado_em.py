"""
Backfill de aprovado_em para orçamentos já APROVADO com data nula.

Uso:
    python scripts/backfill_aprovado_em.py --empresa-id 1
    python scripts/backfill_aprovado_em.py --empresa-id 1 --apply
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import and_

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from app.core.database import SessionLocal  # noqa: E402
from app.models.models import Orcamento, StatusOrcamento  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Preenche aprovado_em para orçamentos APROVADO sem data. "
            "Padrão é dry-run."
        )
    )
    parser.add_argument(
        "--empresa-id",
        type=int,
        action="append",
        help="ID da empresa (pode repetir). Se omitido, processa todas.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica alterações. Sem este flag roda apenas simulação.",
    )
    return parser.parse_args()


def _coletar_candidatos(db, empresa_ids: set[int] | None) -> list[Orcamento]:
    filtro_base = [
        Orcamento.status == StatusOrcamento.APROVADO,
        Orcamento.aprovado_em.is_(None),
    ]
    if empresa_ids:
        filtro_base.append(Orcamento.empresa_id.in_(empresa_ids))
    return (
        db.query(Orcamento)
        .filter(and_(*filtro_base))
        .order_by(Orcamento.empresa_id.asc(), Orcamento.id.asc())
        .all()
    )


def _resumir_origem(candidatos: list[Orcamento]) -> dict[str, int]:
    resumo = {"aceite_em": 0, "atualizado_em": 0, "criado_em": 0, "now": 0}
    agora = datetime.now(timezone.utc)
    for orc in candidatos:
        if getattr(orc, "aceite_em", None):
            resumo["aceite_em"] += 1
        elif getattr(orc, "atualizado_em", None):
            resumo["atualizado_em"] += 1
        elif getattr(orc, "criado_em", None):
            resumo["criado_em"] += 1
        else:
            # caso raro de dado legado sem timestamps
            resumo["now"] += 1
            orc.aprovado_em = agora
    return resumo


def executar_backfill(empresa_ids: set[int] | None, apply: bool) -> int:
    db = SessionLocal()
    try:
        candidatos = _coletar_candidatos(db, empresa_ids)
        total = len(candidatos)
        print(f"Orçamentos APROVADO sem aprovado_em: {total}")
        if total == 0:
            return 0

        resumo = _resumir_origem(candidatos)
        print(
            "Origem sugerida: "
            f"aceite_em={resumo['aceite_em']}, "
            f"atualizado_em={resumo['atualizado_em']}, "
            f"criado_em={resumo['criado_em']}, "
            f"now={resumo['now']}"
        )

        if not apply:
            print("Dry-run concluído. Use --apply para gravar.")
            return 0

        agora = datetime.now(timezone.utc)
        atualizados = 0
        for orc in candidatos:
            escolhido = (
                getattr(orc, "aceite_em", None)
                or getattr(orc, "atualizado_em", None)
                or getattr(orc, "criado_em", None)
                or agora
            )
            orc.aprovado_em = escolhido
            atualizados += 1
        db.commit()

        print(f"Backfill aplicado com sucesso. Registros atualizados: {atualizados}")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"Falha no backfill: {exc}")
        return 1
    finally:
        db.close()


def main() -> int:
    args = _parse_args()
    empresa_ids = set(args.empresa_id or [])
    if empresa_ids:
        print(f"Filtrando empresas: {sorted(empresa_ids)}")
    return executar_backfill(empresa_ids or None, apply=bool(args.apply))


if __name__ == "__main__":
    raise SystemExit(main())
