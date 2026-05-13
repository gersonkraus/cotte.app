import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.models import (
    TenantCommercialLead,
    TenantCommercialInteraction,
    TipoInteracao,
    CanalInteracao,
)
from app.utils.phone import normalize_phone_number
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

def _digitos_telefone(telefone: str) -> str:
    return "".join(filter(str.isdigit, telefone or ""))

def find_lead_by_phone(db: Session, empresa_id: int, telefone: str) -> TenantCommercialLead | None:
    """
    Busca um lead de tenant pelo telefone, considerando os últimos 8 dígitos
    para evitar problemas com 9º dígito ou DDI.
    """
    dig = _digitos_telefone(telefone)
    if len(dig) < 8:
        return None
    sufixo = dig[-8:]

    # Tenta busca exata primeiro (performance)
    lead = db.query(TenantCommercialLead).filter(
        TenantCommercialLead.empresa_id == empresa_id,
        TenantCommercialLead.telefone == telefone
    ).first()
    
    if lead:
        return lead

    # Busca por sufixo (mais lento, mas robusto)
    # No PostgreSQL usamos regexp_replace para limpar e comparar o sufixo
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        digits_expr = func.regexp_replace(TenantCommercialLead.telefone, r"[^0-9]", "", "g")
        suffix_expr = func.right(digits_expr, 8)
        return db.query(TenantCommercialLead).filter(
            TenantCommercialLead.empresa_id == empresa_id,
            TenantCommercialLead.telefone.isnot(None),
            TenantCommercialLead.telefone != "",
            suffix_expr == sufixo
        ).first()
    
    # Fallback para outros bancos (SQLite/testes)
    leads = db.query(TenantCommercialLead).filter(
        TenantCommercialLead.empresa_id == empresa_id,
        TenantCommercialLead.telefone.isnot(None)
    ).all()
    for l in leads:
        dig_l = _digitos_telefone(l.telefone)
        if len(dig_l) >= 8 and dig_l[-8:] == sufixo:
            return l
            
    return None

async def registrar_interacao_whatsapp(
    empresa_id: int,
    telefone: str,
    mensagem: str,
    direcao: str = "recebido",
    message_id: str | None = None,
    db: Session | None = None
) -> bool:
    """
    Registra uma mensagem de WhatsApp na timeline do lead se ele existir.
    Abre sua própria sessão de banco se 'db' não for fornecido (útil para BackgroundTasks).
    """
    if not empresa_id or not telefone or not mensagem:
        return False

    _db = db or SessionLocal()
    try:
        # 1. Deduplicação
        if message_id:
            existente = _db.query(TenantCommercialInteraction).filter(
                TenantCommercialInteraction.empresa_id == empresa_id,
                TenantCommercialInteraction.message_id == message_id
            ).first()
            if existente:
                logger.info("[TenantCommercialService] Mensagem ja registrada (deduplicacao): %s", message_id)
                return True # Já registrado

        # 2. Localizar Lead
        lead = find_lead_by_phone(_db, empresa_id, telefone)
        if not lead:
            logger.warning("[TenantCommercialService] Lead nao localizado para telefone %s na empresa %s", telefone, empresa_id)
            return False

        # 3. Registrar Interação
        interacao = TenantCommercialInteraction(
            empresa_id=empresa_id,
            lead_id=lead.id,
            tipo=TipoInteracao.WHATSAPP,
            canal=CanalInteracao.WHATSAPP,
            conteudo=mensagem,
            direcao=direcao,
            message_id=message_id,
            criado_em=datetime.now(timezone.utc)
        )
        _db.add(interacao)
        
        # Atualizar data de último contato no lead
        lead.ultimo_contato_em = datetime.now(timezone.utc)
        
        _db.commit()
        logger.info("[TenantCommercialService] Interacao WhatsApp registrada com sucesso: lead=%s direcao=%s", lead.id, direcao)
        return True

    except Exception as e:
        logger.error("[TenantCommercialService] Erro ao registrar interacao: %s", e)
        _db.rollback()
        return False

    finally:
        if db is None:
            _db.close()
