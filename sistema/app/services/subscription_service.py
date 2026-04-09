from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.models import Empresa, Orcamento, Usuario, Plano, ModuloSistema


class SubscriptionService:
    @staticmethod
    def get_plano_empresa(db: Session, empresa: Empresa) -> Plano:
        """Busca o plano vinculado ou o plano default se não houver."""
        if empresa.plano_id:
            return empresa.pacote

        # Fallback para compatibilidade: busca plano pelo nome string (legacy)
        plano_legacy = (
            db.query(Plano)
            .filter(func.lower(Plano.nome) == (empresa.plano or "trial").lower())
            .first()
        )
        return plano_legacy

    @staticmethod
    def verificar_modulo(db: Session, empresa: Empresa, modulo_slug: str) -> bool:
        """Verifica se a empresa tem acesso a um módulo específico."""
        plano = SubscriptionService.get_plano_empresa(db, empresa)
        if not plano or not plano.ativo:
            return False

        # Se empresa estiver desativada ou vencida
        if not empresa.ativo:
            return False
        if (
            empresa.assinatura_valida_ate
            and empresa.assinatura_valida_ate < datetime.now(timezone.utc)
        ):
            return False

        return any(m.slug == modulo_slug and m.ativo for m in plano.modulos)

    @staticmethod
    def checar_limite_orcamentos(db: Session, empresa: Empresa):
        plano = SubscriptionService.get_plano_empresa(db, empresa)

        # Override individual sempre tem prioridade
        limite = empresa.limite_orcamentos_custom
        if limite is None and plano:
            limite = plano.limite_orcamentos

        if limite is None:  # Ilimitado
            return

        usados = (
            db.query(func.count(Orcamento.id))
            .filter(Orcamento.empresa_id == empresa.id)
            .scalar()
            or 0
        )
        if usados >= limite:
            raise HTTPException(
                status_code=402,
                detail=f"Limite de orçamentos atingido ({limite}). Faça upgrade do seu plano.",
            )

    @staticmethod
    def checar_limite_usuarios(db: Session, empresa: Empresa):
        plano = SubscriptionService.get_plano_empresa(db, empresa)

        limite = empresa.limite_usuarios_custom
        if limite is None and plano:
            limite = plano.limite_usuarios

        if limite is None:
            return

        usados = (
            db.query(func.count(Usuario.id))
            .filter(Usuario.empresa_id == empresa.id, Usuario.is_superadmin == False)
            .scalar()
            or 0
        )

        if usados >= limite:
            raise HTTPException(
                status_code=402,
                detail=f"Limite de usuários atingido ({limite}). Faça upgrade do seu plano.",
            )

    @staticmethod
    def checar_limite_ia(db: Session, empresa: Empresa):
        if not SubscriptionService.verificar_modulo(db, empresa, "ia"):
            raise HTTPException(
                status_code=403, detail="Seu plano não inclui o Assistente IA."
            )

        plano = SubscriptionService.get_plano_empresa(db, empresa)
        limite = plano.total_mensagem_ia if plano else 100

        if empresa.total_mensagens_ia >= limite:
            raise HTTPException(
                status_code=402, detail="Limite de mensagens IA do mês atingido."
            )

    @staticmethod
    def checar_limite_whatsapp(db: Session, empresa: Empresa):
        if not SubscriptionService.verificar_modulo(db, empresa, "whatsapp"):
            raise HTTPException(
                status_code=403, detail="Seu plano não inclui WhatsApp Próprio."
            )

        plano = SubscriptionService.get_plano_empresa(db, empresa)
        limite = plano.total_mensagem_whatsapp if plano else 500

        if (empresa.total_mensagens_whatsapp or 0) >= limite:
            raise HTTPException(
                status_code=402, detail="Limite de mensagens WhatsApp do mês atingido."
            )
