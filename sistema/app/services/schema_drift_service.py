from __future__ import annotations

from typing import Any

from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeMeta
from sqlalchemy.orm import Session


CRITICAL_SCHEMA_COLUMNS: list[tuple[str, str]] = [
    ("empresas", "assistente_instrucoes"),
]


def analyze_schema_drift(engine: Engine, metadata: DeclarativeMeta) -> dict[str, Any]:
    """
    Compara colunas/tabelas do metadata SQLAlchemy com o schema atual do banco.
    Retorna divergências para uso em endpoint admin e preflight.
    """
    inspector = inspect(engine)
    db_tables = set(inspector.get_table_names())

    missing_tables: list[str] = []
    missing_columns: list[dict[str, Any]] = []
    extra_columns: list[dict[str, Any]] = []

    for table_name, table in metadata.tables.items():
        if table_name not in db_tables:
            missing_tables.append(table_name)
            continue

        db_column_names = {col["name"] for col in inspector.get_columns(table_name)}
        model_column_names = {col.name for col in table.columns}

        cols_missing_in_db = sorted(model_column_names - db_column_names)
        cols_extra_in_db = sorted(db_column_names - model_column_names)

        if cols_missing_in_db:
            missing_columns.append(
                {
                    "table": table_name,
                    "columns": cols_missing_in_db,
                }
            )
        if cols_extra_in_db:
            extra_columns.append(
                {
                    "table": table_name,
                    "columns": cols_extra_in_db,
                }
            )

    return {
        "ok": not (missing_tables or missing_columns),
        "missing_tables": sorted(missing_tables),
        "missing_columns": missing_columns,
        "extra_columns": extra_columns,
    }


def check_critical_schema_drift(
    engine: Engine, metadata: DeclarativeMeta
) -> dict[str, Any]:
    """
    Verifica apenas divergências críticas conhecidas para bloquear startup cedo,
    com mensagem guiada de correção.
    """
    drift = analyze_schema_drift(engine, metadata)
    missing_map: dict[str, set[str]] = {
        item["table"]: set(item["columns"]) for item in drift["missing_columns"]
    }

    critical_missing: list[str] = []
    for table_name, column_name in CRITICAL_SCHEMA_COLUMNS:
        if column_name in missing_map.get(table_name, set()):
            critical_missing.append(f"{table_name}.{column_name}")

    return {
        "ok": len(critical_missing) == 0,
        "critical_missing": sorted(critical_missing),
        "drift": drift,
    }


def safe_analyze_schema_drift(engine: Engine, metadata: DeclarativeMeta) -> dict[str, Any]:
    """
    Wrapper resiliente para endpoint admin: nunca lança erro não tratado.
    """
    try:
        return {
            "success": True,
            "result": analyze_schema_drift(engine, metadata),
        }
    except SQLAlchemyError as exc:
        return {
            "success": False,
            "error": f"Erro SQLAlchemy ao inspecionar schema: {exc}",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "success": False,
            "error": f"Erro inesperado ao inspecionar schema: {exc}",
        }


def save_schema_drift_snapshot(
    db: Session,
    drift: dict[str, Any],
    *,
    source: str = "manual_admin",
    app_version: str | None = None,
    environment: str | None = None,
) -> Any:
    """
    Persiste um snapshot da análise de drift para histórico operacional.
    """
    from app.models.models import SchemaDriftSnapshot

    snapshot = SchemaDriftSnapshot(
        app_version=app_version,
        environment=environment,
        source=source,
        status_ok=bool(drift.get("ok", False)),
        missing_tables_json=drift.get("missing_tables", []),
        missing_columns_json=drift.get("missing_columns", []),
        extra_columns_json=drift.get("extra_columns", []),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def list_schema_drift_snapshots(db: Session, *, limit: int = 20, offset: int = 0) -> list[Any]:
    """
    Lista snapshots mais recentes (paginação simples).
    """
    from app.models.models import SchemaDriftSnapshot

    safe_limit = max(1, min(limit, 100))
    safe_offset = max(0, offset)
    return (
        db.query(SchemaDriftSnapshot)
        .order_by(SchemaDriftSnapshot.criado_em.desc(), SchemaDriftSnapshot.id.desc())
        .offset(safe_offset)
        .limit(safe_limit)
        .all()
    )


def get_schema_drift_snapshot(db: Session, snapshot_id: int) -> Any | None:
    """
    Retorna um snapshot específico por ID.
    """
    from app.models.models import SchemaDriftSnapshot

    return db.query(SchemaDriftSnapshot).filter(SchemaDriftSnapshot.id == snapshot_id).first()


def compare_schema_drift_snapshots(base_snapshot: Any, target_snapshot: Any) -> dict[str, Any]:
    """
    Compara dois snapshots e destaca mudanças nas divergências.
    """
    def _norm_tables(s: Any) -> set[str]:
        return set(s or [])

    def _norm_columns(s: Any) -> set[tuple[str, str]]:
        items = set()
        for row in s or []:
            table = row.get("table")
            for col in row.get("columns", []):
                items.add((table, col))
        return items

    base_missing_tables = _norm_tables(base_snapshot.missing_tables_json)
    target_missing_tables = _norm_tables(target_snapshot.missing_tables_json)
    base_missing_columns = _norm_columns(base_snapshot.missing_columns_json)
    target_missing_columns = _norm_columns(target_snapshot.missing_columns_json)

    def _fmt_cols(cols: set[tuple[str, str]]) -> list[str]:
        return sorted([f"{table}.{col}" for table, col in cols])

    return {
        "base_snapshot_id": base_snapshot.id,
        "target_snapshot_id": target_snapshot.id,
        "new_missing_tables": sorted(target_missing_tables - base_missing_tables),
        "resolved_tables": sorted(base_missing_tables - target_missing_tables),
        "new_missing_columns": _fmt_cols(target_missing_columns - base_missing_columns),
        "resolved_columns": _fmt_cols(base_missing_columns - target_missing_columns),
    }


def generate_auto_fix_preview(drift: dict[str, Any]) -> dict[str, Any]:
    """
    Gera preview de correção (dry-run), sem executar SQL.
    """
    suggestions: list[dict[str, Any]] = []
    for missing in drift.get("missing_tables", []):
        suggestions.append(
            {
                "type": "missing_table",
                "target": missing,
                "action": "create_table_via_migration",
                "risk": "alto",
                "sql_preview": f"-- criar tabela {missing} via Alembic migration",
            }
        )

    for item in drift.get("missing_columns", []):
        table = item.get("table")
        for col in item.get("columns", []):
            suggestions.append(
                {
                    "type": "missing_column",
                    "target": f"{table}.{col}",
                    "action": "add_column_via_migration",
                    "risk": "medio",
                    "sql_preview": f"ALTER TABLE {table} ADD COLUMN {col} <tipo_model>;",
                }
            )

    return {
        "dry_run": True,
        "executed": False,
        "detected_issues": {
            "missing_tables": drift.get("missing_tables", []),
            "missing_columns": drift.get("missing_columns", []),
            "extra_columns": drift.get("extra_columns", []),
        },
        "suggestions": suggestions,
        "next_step": "Revisar sugestões e aplicar migration apropriada com alembic upgrade head.",
    }
