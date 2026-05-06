from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, computed_field, field_serializer

from app.models.models import CanalTemplate, TipoTemplate


class TenantTemplateCreate(BaseModel):
    nome: str
    tipo: TipoTemplate
    canal: CanalTemplate
    assunto: Optional[str] = None
    conteudo: str
    anexo_arquivo_path: Optional[str] = None
    anexo_nome_original: Optional[str] = None
    anexo_mime_type: Optional[str] = None
    anexo_tamanho_bytes: Optional[int] = None


class TenantTemplateUpdate(BaseModel):
    nome: Optional[str] = None
    tipo: Optional[TipoTemplate] = None
    canal: Optional[CanalTemplate] = None
    assunto: Optional[str] = None
    conteudo: Optional[str] = None
    ativo: Optional[bool] = None
    anexo_arquivo_path: Optional[str] = None
    anexo_nome_original: Optional[str] = None
    anexo_mime_type: Optional[str] = None
    anexo_tamanho_bytes: Optional[int] = None
    remover_anexo: Optional[bool] = None


class TenantTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    tipo: TipoTemplate
    canal: CanalTemplate
    assunto: Optional[str] = None
    conteudo: str
    ativo: bool
    anexo_arquivo_path: Optional[str] = None
    anexo_nome_original: Optional[str] = None
    anexo_mime_type: Optional[str] = None
    anexo_tamanho_bytes: Optional[int] = None
    criado_em: datetime
    atualizado_em: Optional[datetime] = None

    @computed_field
    @property
    def anexo_url(self) -> Optional[str]:
        return self.anexo_arquivo_path

    @field_serializer("canal", "tipo")
    def serialize_enum(self, value):
        return value.value if hasattr(value, "value") else str(value)


class TemplatePreviewBody(BaseModel):
    lead_id: int


class TenantTemplatePreview(BaseModel):
    assunto: Optional[str] = None
    conteudo: str
    dias_sem_contato: int = 0
    score: Optional[str] = None
    etapa: Optional[str] = None
    valor: Optional[float] = None
    anexo_url: Optional[str] = None
    anexo_nome_original: Optional[str] = None
    anexo_mime_type: Optional[str] = None
    anexo_tamanho_bytes: Optional[int] = None
