from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

# ── MÓDULOS ──────────────────────────────────────────────────────────────────


class ModuloBase(BaseModel):
    nome: str = Field(..., description="Nome do módulo (ex: Financeiro)")
    slug: str = Field(..., description="Slug identificador (ex: financeiro)")
    descricao: Optional[str] = None
    ativo: bool = True


class ModuloCreate(ModuloBase):
    pass


class ModuloUpdate(BaseModel):
    nome: Optional[str] = None
    slug: Optional[str] = None
    descricao: Optional[str] = None
    ativo: Optional[bool] = None


class ModuloOut(ModuloBase):
    id: int

    class Config:
        from_attributes = True


# ── PLANOS ───────────────────────────────────────────────────────────────────


class PlanoBase(BaseModel):
    nome: str
    descricao: Optional[str] = None
    limite_usuarios: int = 1
    limite_orcamentos: int = 50
    total_mensagem_ia: int = 100
    total_mensagem_whatsapp: int = 500
    preco_mensal: Decimal = Decimal("0.0")
    ativo: bool = True


class PlanoCreate(PlanoBase):
    modulos_ids: List[int] = []


class PlanoUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    limite_usuarios: Optional[int] = None
    limite_orcamentos: Optional[int] = None
    total_mensagem_ia: Optional[int] = None
    total_mensagem_whatsapp: Optional[int] = None
    preco_mensal: Optional[Decimal] = None
    ativo: Optional[bool] = None
    modulos_ids: Optional[List[int]] = None


class PlanoOut(PlanoBase):
    id: int
    criado_em: datetime
    modulos: List[ModuloOut] = []

    class Config:
        from_attributes = True
