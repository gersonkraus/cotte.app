from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlalchemy.future import select

from app.models.models import Empresa, Orcamento, Usuario

# Importação tardia para evitar dependência circular
def _get_plan_defaults():
    from app.services.plan_defaults_config import get_plan_defaults
    return get_plan_defaults()


# Configuração central de planos.
# Os nomes devem bater com Empresa.plano (trial/starter/pro/business).
PLANO_CONFIG: Dict[str, Dict[str, Any]] = {
    "trial": {
        "nome_exibicao": "Avaliação",
        "limite_orcamentos_total": 50,
        "limite_usuarios": 1,
        "ia_automatica": False,
        "lembretes_automaticos": False,
        "relatorios": False,
        "whatsapp_proprio": False,
    },
    "starter": {
        "nome_exibicao": "Starter",
        "limite_orcamentos_total": 200,
        "limite_usuarios": 3,
        "ia_automatica": False,
        "lembretes_automaticos": True,
        "relatorios": True,
        "whatsapp_proprio": False,
    },
    "pro": {
        "nome_exibicao": "Pro",
        "limite_orcamentos_total": 1000,
        "limite_usuarios": 10,
        "ia_automatica": True,
        "lembretes_automaticos": True,
        "relatorios": True,
        "whatsapp_proprio": True,
    },
    "business": {
        "nome_exibicao": "Business",
        "limite_orcamentos_total": None,  # ilimitado
        "limite_usuarios": None,
        "ia_automatica": True,
        "lembretes_automaticos": True,
        "relatorios": True,
        "whatsapp_proprio": True,
    },
}


def _config_for_empresa(empresa: Empresa) -> Dict[str, Any]:
    plano = (empresa.plano or "trial").lower()
    base = PLANO_CONFIG.get(plano, PLANO_CONFIG["pro"]).copy()
    # Sobrescrever limites com os padrões editáveis pelo Admin (plan_defaults.json)
    defaults = _get_plan_defaults()
    if plano in defaults:
        if "limite_orcamentos" in defaults[plano]:
            base["limite_orcamentos_total"] = defaults[plano]["limite_orcamentos"]
        if "limite_usuarios" in defaults[plano]:
            base["limite_usuarios"] = defaults[plano]["limite_usuarios"]
    return base


def checar_limite_orcamentos(db: Session, empresa: Empresa) -> None:
    """Lança HTTP 402 se a empresa já atingiu o limite de orçamentos do plano."""
    cfg = _config_for_empresa(empresa)
    # Override por empresa, se configurado
    if empresa.limite_orcamentos_custom is not None:
        limite = empresa.limite_orcamentos_custom
    else:
        limite = cfg.get("limite_orcamentos_total")
    if not limite:
        return

    usados = db.query(func.count(Orcamento.id)).filter(
        Orcamento.empresa_id == empresa.id
    ).scalar() or 0

    if usados >= limite:
        raise HTTPException(
            status_code=402,
            detail=f"Seu plano ({cfg['nome_exibicao']}) permite até {limite} orçamentos. "
                   f"Faça upgrade para criar mais orçamentos.",
        )


def checar_limite_usuarios(db: Session, empresa: Empresa) -> None:
    """Lança HTTP 402 se a empresa já atingiu o limite de usuários do plano."""
    cfg = _config_for_empresa(empresa)
    if empresa.limite_usuarios_custom is not None:
        limite = empresa.limite_usuarios_custom
    else:
        limite = cfg.get("limite_usuarios")
    if not limite:
        return

    usados = db.query(func.count(Usuario.id)).filter(
        Usuario.empresa_id == empresa.id,
        Usuario.is_superadmin == False,
    ).scalar() or 0

    if usados >= limite:
        raise HTTPException(
            status_code=402,
            detail=f"Seu plano ({cfg['nome_exibicao']}) permite até {limite} usuários. "
                   f"Faça upgrade para adicionar mais usuários à equipe.",
        )


async def checar_limite_orcamentos_async(db: AsyncSession, empresa: Empresa) -> None:
    """Versão assíncrona de checar_limite_orcamentos."""
    cfg = _config_for_empresa(empresa)
    # Override por empresa, se configurado
    if empresa.limite_orcamentos_custom is not None:
        limite = empresa.limite_orcamentos_custom
    else:
        limite = cfg.get("limite_orcamentos_total")
    if not limite:
        return

    stmt = select(func.count(Orcamento.id)).where(Orcamento.empresa_id == empresa.id)
    result = await db.execute(stmt)
    usados = result.scalar() or 0

    if usados >= limite:
        raise HTTPException(
            status_code=402,
            detail=f"Seu plano ({cfg['nome_exibicao']}) permite até {limite} orçamentos. "
                   f"Faça upgrade para criar mais orçamentos.",
        )


def ia_automatica_habilitada(empresa: Empresa) -> bool:
    """Retorna True se a IA automática estiver liberada para o plano da empresa."""
    if empresa.desativar_ia:
        return False

    # Novo sistema: verifica via plano_id
    if empresa.plano_id and empresa.pacote:
        tem_modulo = any(m.slug == "ia" for m in empresa.pacote.modulos)
        if not tem_modulo:
            return False
    else:
        # Fallback legado
        cfg = _config_for_empresa(empresa)
        if not cfg.get("ia_automatica", False):
            return False

    if empresa.assinatura_valida_ate:
        agora = datetime.now(timezone.utc)
        if empresa.assinatura_valida_ate < agora:
            return False

    if empresa.ativo is False:
        return False

    return True


def exigir_ia_dashboard(empresa: Empresa) -> None:
    """Usada em endpoints de IA do dashboard; lança 403 se o plano não permitir."""
    if not ia_automatica_habilitada(empresa):
        raise HTTPException(
            status_code=403,
            detail="Seu plano atual não inclui automações de IA. "
                   "Acesse o painel de assinatura para fazer upgrade.",
        )


def lembretes_automaticos_habilitados(empresa: Empresa) -> bool:
    if empresa.desativar_lembretes:
        return False

    # Novo sistema
    if empresa.plano_id and empresa.pacote:
        tem_modulo = any(m.slug == "lembretes" for m in empresa.pacote.modulos)
        if not tem_modulo:
            return False
    else:
        cfg = _config_for_empresa(empresa)
        if not cfg.get("lembretes_automaticos", False):
            return False

    if empresa.lembrete_dias is None:
        return False
    if empresa.ativo is False:
        return False
    return True


def relatorios_habilitados(empresa: Empresa) -> bool:
    if empresa.desativar_relatorios:
        return False

    # Novo sistema
    if empresa.plano_id and empresa.pacote:
        tem_modulo = any(m.slug == "relatorios" for m in empresa.pacote.modulos)
        if not tem_modulo:
            return False
    else:
        cfg = _config_for_empresa(empresa)
        if not cfg.get("relatorios", False):
            return False

    if empresa.ativo is False:
        return False
    return True


def exigir_relatorios(empresa: Empresa) -> None:
    if not relatorios_habilitados(empresa):
        raise HTTPException(
            status_code=403,
            detail="Relatórios não estão disponíveis no seu plano atual.",
        )


def whatsapp_proprio_habilitado(empresa: Empresa) -> bool:
    """Retorna True se o plano da empresa permite usar número WhatsApp próprio."""
    # Novo sistema
    if empresa.plano_id and empresa.pacote:
        tem_modulo = any(m.slug == "whatsapp_proprio" for m in empresa.pacote.modulos)
        if not tem_modulo:
            return False
    else:
        cfg = _config_for_empresa(empresa)
        if not cfg.get("whatsapp_proprio", False):
            return False

    if empresa.ativo is False:
        return False
    if empresa.assinatura_valida_ate:
        agora = datetime.now(timezone.utc)
        if empresa.assinatura_valida_ate < agora:
            return False
    return True


def exigir_whatsapp_proprio(empresa: Empresa) -> None:
    """Lança 403 se o plano da empresa não incluir WhatsApp próprio."""
    if not whatsapp_proprio_habilitado(empresa):
        raise HTTPException(
            status_code=403,
            detail="WhatsApp próprio está disponível nos planos Pro e Business. "
                   "Faça upgrade para conectar o número da sua empresa.",
        )

