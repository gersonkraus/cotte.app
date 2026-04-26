import inspect
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import exigir_modulo, exigir_permissao
from app.core.database import get_db
from app.models.models import TenantCommercialLead, TenantProposta, Usuario
from app.services.email_service import send_email_simples
from app.services.whatsapp_service import enviar_mensagem_texto


class PropostaCreate(BaseModel):
    lead_id: int
    titulo: str
    descricao: Optional[str] = None
    valor_total: Optional[Decimal] = None


class PropostaResponse(PropostaCreate):
    id: int
    empresa_id: int
    status: str
    enviada_em: Optional[datetime] = None
    criado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


class PropostaListResponse(BaseModel):
    items: list[PropostaResponse]
    total: int


class PropostaEnvioRequest(BaseModel):
    canal: str


router = APIRouter(
    prefix="/propostas",
    tags=["Tenant Comercial Propostas"],
    dependencies=[Depends(exigir_modulo("comercial"))],
)


def _buscar_proposta(db: Session, empresa_id: int, proposta_id: int) -> TenantProposta:
    proposta = (
        db.query(TenantProposta)
        .filter(
            TenantProposta.id == proposta_id,
            TenantProposta.empresa_id == empresa_id,
        )
        .first()
    )
    if proposta is None:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")
    return proposta


@router.post("/", response_model=PropostaResponse, status_code=status.HTTP_201_CREATED)
def create_proposta(
    payload: PropostaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    lead = (
        db.query(TenantCommercialLead)
        .filter(
            TenantCommercialLead.id == payload.lead_id,
            TenantCommercialLead.empresa_id == usuario.empresa_id,
            TenantCommercialLead.ativo.is_(True),
        )
        .first()
    )
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    proposta = TenantProposta(
        empresa_id=usuario.empresa_id,
        lead_id=payload.lead_id,
        titulo=payload.titulo,
        descricao=payload.descricao,
        valor_total=payload.valor_total,
        status="rascunho",
        criado_em=datetime.now(timezone.utc),
    )
    db.add(proposta)
    db.commit()
    db.refresh(proposta)
    return proposta


@router.get("/", response_model=PropostaListResponse)
def list_propostas(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    query = db.query(TenantProposta).filter(TenantProposta.empresa_id == usuario.empresa_id)
    return {
        "items": query.order_by(TenantProposta.id.desc()).all(),
        "total": query.count(),
    }


@router.get("/{proposta_id}", response_model=PropostaResponse)
def get_proposta(
    proposta_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    return _buscar_proposta(db, usuario.empresa_id, proposta_id)


@router.post("/{proposta_id}/enviar")
async def enviar_proposta(
    proposta_id: int,
    payload: PropostaEnvioRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "escrita")),
):
    proposta = _buscar_proposta(db, usuario.empresa_id, proposta_id)
    lead = (
        db.query(TenantCommercialLead)
        .filter(
            TenantCommercialLead.id == proposta.lead_id,
            TenantCommercialLead.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    canal = payload.canal.lower()
    if canal not in {"whatsapp", "email", "ambos"}:
        raise HTTPException(status_code=400, detail="Canal inválido")

    mensagem = f"Proposta: {proposta.titulo}"
    if canal in {"whatsapp", "ambos"} and lead.telefone:
        resultado = enviar_mensagem_texto(lead.telefone, mensagem)
        if inspect.isawaitable(resultado):
            await resultado
    if canal in {"email", "ambos"} and lead.email:
        send_email_simples(
            destinatario=lead.email,
            assunto=proposta.titulo,
            mensagem=proposta.descricao or mensagem,
        )

    proposta.status = "enviada"
    proposta.enviada_em = datetime.now(timezone.utc)
    db.commit()
    db.refresh(proposta)
    return {"ok": True, "status": proposta.status, "proposta_id": proposta.id}
