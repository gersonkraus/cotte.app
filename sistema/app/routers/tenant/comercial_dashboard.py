from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import exigir_modulo, exigir_permissao
from app.core.database import get_db
from app.models.models import TenantCommercialLead, TenantPipelineEtapa, Usuario


router = APIRouter(
    prefix="/dashboard",
    tags=["Tenant Comercial Dashboard"],
    dependencies=[Depends(exigir_modulo("comercial"))],
)


@router.get("")
def get_dashboard(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("comercial", "leitura")),
):
    leads = (
        db.query(TenantCommercialLead)
        .filter(
            TenantCommercialLead.empresa_id == usuario.empresa_id,
            TenantCommercialLead.ativo.is_(True),
        )
        .all()
    )
    etapas = {
        etapa.id: etapa.nome
        for etapa in db.query(TenantPipelineEtapa)
        .filter(TenantPipelineEtapa.empresa_id == usuario.empresa_id)
        .all()
    }

    hoje = date.today()
    leads_por_etapa: dict[str, int] = {}
    leads_novos_hoje = 0
    recentes = []

    for lead in leads:
        nome_etapa = etapas.get(lead.etapa_pipeline_id, "Sem etapa")
        leads_por_etapa[nome_etapa] = leads_por_etapa.get(nome_etapa, 0) + 1
        if lead.criado_em and lead.criado_em.date() == hoje:
            leads_novos_hoje += 1

    for lead in sorted(leads, key=lambda item: item.id, reverse=True)[:5]:
        recentes.append(
            {
                "id": lead.id,
                "nome": lead.nome,
                "email": lead.email,
                "telefone": lead.telefone,
                "etapa_pipeline_id": lead.etapa_pipeline_id,
            }
        )

    return {
        "total_leads": len(leads),
        "leads_por_etapa": leads_por_etapa,
        "leads_novos_hoje": leads_novos_hoje,
        "leads_recentes": recentes,
    }
