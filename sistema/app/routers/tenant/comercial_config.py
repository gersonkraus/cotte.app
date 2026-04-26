from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import exigir_modulo, exigir_permissao
from app.core.database import get_db
from app.models.models import TenantConfig, Usuario


class ConfigItemCreate(BaseModel):
    nome: str


class ConfigItemResponse(BaseModel):
    id: int
    empresa_id: int
    tipo: str
    nome: str
    ativo: bool

    class Config:
        from_attributes = True


router = APIRouter(
    prefix="/config",
    tags=["Tenant Comercial Config"],
    dependencies=[Depends(exigir_modulo("comercial"))],
)


def _listar_por_tipo(db: Session, empresa_id: int, tipo: str):
    return (
        db.query(TenantConfig)
        .filter(
            TenantConfig.empresa_id == empresa_id,
            TenantConfig.tipo == tipo,
            TenantConfig.ativo.is_(True),
        )
        .order_by(TenantConfig.nome.asc())
        .all()
    )


@router.get("/segmentos", response_model=list[ConfigItemResponse])
def list_segmentos(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    return _listar_por_tipo(db, usuario.empresa_id, "segmento")


@router.post("/segmentos", response_model=ConfigItemResponse, status_code=status.HTTP_201_CREATED)
def create_segmento(
    payload: ConfigItemCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "admin")),
):
    item = TenantConfig(
        empresa_id=usuario.empresa_id,
        tipo="segmento",
        nome=payload.nome,
        ativo=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/origens", response_model=list[ConfigItemResponse])
def list_origens(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    return _listar_por_tipo(db, usuario.empresa_id, "origem")


@router.post("/origens", response_model=ConfigItemResponse, status_code=status.HTTP_201_CREATED)
def create_origem(
    payload: ConfigItemCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "admin")),
):
    item = TenantConfig(
        empresa_id=usuario.empresa_id,
        tipo="origem",
        nome=payload.nome,
        ativo=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
