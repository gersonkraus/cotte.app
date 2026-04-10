import uuid

from app.models.models import Empresa, Usuario
from app.routers import admin as admin_router


def _make_superadmin(db):
    empresa = Empresa(nome="Empresa Admin Drift", ativo=True, plano="pro")
    db.add(empresa)
    db.flush()

    usuario = Usuario(
        empresa_id=empresa.id,
        nome="Superadmin Drift",
        email=f"superadmin.drift.{uuid.uuid4().hex[:8]}@teste.com",
        senha_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehash12",
        ativo=True,
        is_superadmin=True,
        token_versao=1,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def test_schema_drift_endpoint_preserva_contrato(db):
    superadmin = _make_superadmin(db)
    payload = admin_router.schema_drift(db=db, _=superadmin)
    assert payload["success"] is True
    assert "data" in payload
    assert "suggestion" in payload
    assert "snapshot_id" in payload
    assert "ok" in payload["data"]
    assert "missing_tables" in payload["data"]
    assert "missing_columns" in payload["data"]
    assert "extra_columns" in payload["data"]


def test_schema_drift_auto_fix_preview_dry_run(db):
    superadmin = _make_superadmin(db)
    payload = admin_router.schema_drift_auto_fix_preview(_=superadmin)
    assert payload["success"] is True
    assert payload["data"]["dry_run"] is True
    assert payload["data"]["executed"] is False
    assert "suggestions" in payload["data"]


def test_schema_drift_snapshots_list_detail_compare(db):
    superadmin = _make_superadmin(db)
    first = admin_router.schema_drift(db=db, _=superadmin)
    second = admin_router.schema_drift(db=db, _=superadmin)
    base_id = first["snapshot_id"]
    target_id = second["snapshot_id"]

    listed = admin_router.schema_drift_snapshots(db=db, _=superadmin)
    assert listed["success"] is True
    assert len(listed["data"]) >= 2

    detail = admin_router.schema_drift_snapshot_detail(
        snapshot_id=base_id, db=db, _=superadmin
    )
    assert detail["success"] is True
    assert detail["data"]["id"] == base_id

    compare = admin_router.schema_drift_snapshot_compare(
        base_id=base_id, target_id=target_id, db=db, _=superadmin
    )
    assert compare["success"] is True
    assert compare["data"]["base_snapshot_id"] == base_id
    assert compare["data"]["target_snapshot_id"] == target_id
