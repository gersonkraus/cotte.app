from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.auth import get_superadmin
from app.models.models import Plano, ModuloSistema, PlanoModulo, Empresa
from app.schemas.plano import (
    PlanoCreate,
    PlanoUpdate,
    PlanoOut,
    ModuloCreate,
    ModuloUpdate,
    ModuloOut,
)
from app.services.seed_modulos import MODULOS_SEED

router = APIRouter(prefix="/admin/pacotes", tags=["Admin - Pacotes"])

# ── MÓDULOS ──────────────────────────────────────────────────────────────────


@router.get("/modulos", response_model=List[ModuloOut])
def listar_modulos(db: Session = Depends(get_db), _=Depends(get_superadmin)):
    """Lista todos os módulos do sistema. Auto-seeda módulos canônicos se tabela vazia."""
    modulos = db.query(ModuloSistema).all()
    if not modulos:
        # Seed automático: cria os módulos canônicos do sistema
        for dados in MODULOS_SEED:
            db.add(ModuloSistema(
                nome=dados["nome"],
                slug=dados["slug"],
                descricao=dados["descricao"],
                acoes=dados["acoes"],
                ativo=True,
            ))
        db.commit()
        modulos = db.query(ModuloSistema).all()
    return modulos


@router.post("/modulos", response_model=ModuloOut, status_code=201)
def criar_modulo(
    dados: ModuloCreate, db: Session = Depends(get_db), _=Depends(get_superadmin)
):
    """Cria um novo módulo do sistema."""
    if db.query(ModuloSistema).filter(ModuloSistema.slug == dados.slug).first():
        raise HTTPException(status_code=400, detail="Slug de módulo já existe")

    modulo = ModuloSistema(**dados.model_dump())
    db.add(modulo)
    db.commit()
    db.refresh(modulo)
    return modulo


@router.put("/modulos/{modulo_id}", response_model=ModuloOut)
def atualizar_modulo(
    modulo_id: int,
    dados: ModuloUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Atualiza um módulo do sistema."""
    modulo = db.query(ModuloSistema).filter(ModuloSistema.id == modulo_id).first()
    if not modulo:
        raise HTTPException(status_code=404, detail="Módulo não encontrado")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(modulo, campo, valor)

    db.commit()
    db.refresh(modulo)
    return modulo


# ── PLANOS / PACOTES ────────────────────────────────────────────────────────


@router.get("/", response_model=List[PlanoOut])
def listar_planos(db: Session = Depends(get_db), _=Depends(get_superadmin)):
    """Lista todos os planos/pacotes disponíveis."""
    return db.query(Plano).all()


@router.post("/", response_model=PlanoOut, status_code=201)
def criar_plano(
    dados: PlanoCreate, db: Session = Depends(get_db), _=Depends(get_superadmin)
):
    """Cria um novo plano/pacote com módulos associados."""
    modulos_ids = dados.modulos_ids
    payload = dados.model_dump(exclude={"modulos_ids"})

    plano = Plano(**payload)
    db.add(plano)
    db.flush()

    if modulos_ids:
        for mid in modulos_ids:
            pm = PlanoModulo(plano_id=plano.id, modulo_id=mid)
            db.add(pm)

    db.commit()
    db.refresh(plano)
    return plano


@router.put("/{plano_id}", response_model=PlanoOut)
def atualizar_plano(
    plano_id: int,
    dados: PlanoUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Atualiza um plano/pacote e seus módulos associados."""
    plano = db.query(Plano).filter(Plano.id == plano_id).first()
    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    modulos_ids = dados.modulos_ids
    payload = dados.model_dump(exclude_unset=True, exclude={"modulos_ids"})

    for campo, valor in payload.items():
        setattr(plano, campo, valor)

    if modulos_ids is not None:
        # Limpa modulos atuais
        db.query(PlanoModulo).filter(PlanoModulo.plano_id == plano_id).delete()
        # Adiciona novos
        for mid in modulos_ids:
            pm = PlanoModulo(plano_id=plano.id, modulo_id=mid)
            db.add(pm)

    db.commit()
    db.refresh(plano)
    return plano


@router.delete("/{plano_id}", status_code=204)
def deletar_plano(
    plano_id: int, db: Session = Depends(get_db), _=Depends(get_superadmin)
):
    """Exclui um plano/pacote se não estiver vinculado a empresas."""
    plano = db.query(Plano).filter(Plano.id == plano_id).first()
    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    if db.query(Empresa).filter(Empresa.plano_id == plano_id).first():
        raise HTTPException(
            status_code=400,
            detail="Não é possível excluir um plano vinculado a empresas",
        )

    db.delete(plano)
    db.commit()
