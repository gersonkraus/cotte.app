from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.auth import exigir_modulo, exigir_permissao
from app.core.database import get_db
from app.models.models import StatusLembrete, TenantCommercialLead, TenantCommercialReminder, Usuario
from app.schemas.schemas import DashboardMetrics


router = APIRouter(
    prefix="/dashboard",
    tags=["Tenant Comercial Dashboard"],
    dependencies=[Depends(exigir_modulo("comercial"))],
)


@router.get("", response_model=DashboardMetrics)
def get_dashboard(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    eid = usuario.empresa_id
    agora = datetime.now(timezone.utc)
    inicio_dia = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)
    fim_dia = inicio_dia + timedelta(days=1)

    base = db.query(TenantCommercialLead).filter(
        TenantCommercialLead.empresa_id == eid,
        TenantCommercialLead.ativo.is_(True),
    )

    total = base.count()
    novos = base.filter(TenantCommercialLead.status_pipeline == "novo").count()
    propostas = base.filter(TenantCommercialLead.status_pipeline == "proposta_enviada").count()
    negociacoes = base.filter(TenantCommercialLead.status_pipeline == "negociacao").count()
    fechados_ganho = base.filter(TenantCommercialLead.status_pipeline == "fechado_ganho").count()
    fechados_perdido = base.filter(TenantCommercialLead.status_pipeline == "fechado_perdido").count()

    follow_ups_hoje = (
        base.filter(
            TenantCommercialLead.proximo_contato_em.isnot(None),
            TenantCommercialLead.proximo_contato_em <= agora,
            TenantCommercialLead.status_pipeline.notin_(["fechado_ganho", "fechado_perdido"]),
        ).count()
    )

    lembretes_pendentes = (
        db.query(func.count(TenantCommercialReminder.id))
        .filter(
            TenantCommercialReminder.empresa_id == eid,
            TenantCommercialReminder.status == StatusLembrete.PENDENTE,
        )
        .scalar()
        or 0
    )

    dias_sem = agora - timedelta(days=7)
    leads_sem_contato = (
        base.filter(
            or_(
                TenantCommercialLead.ultimo_contato_em.is_(None),
                TenantCommercialLead.ultimo_contato_em < dias_sem,
            ),
            TenantCommercialLead.criado_em < dias_sem,
            TenantCommercialLead.status_pipeline.notin_(["fechado_ganho", "fechado_perdido"]),
        ).count()
    )

    return DashboardMetrics(
        total_leads=total,
        novos=novos,
        propostas_enviadas=propostas,
        negociacoes=negociacoes,
        fechados_ganho=fechados_ganho,
        fechados_perdido=fechados_perdido,
        follow_ups_hoje=follow_ups_hoje,
        lembretes_pendentes=int(lembretes_pendentes),
        leads_sem_contato=leads_sem_contato,
        propostas_sem_retorno=0,
        empresas_em_trial=0,
    )
