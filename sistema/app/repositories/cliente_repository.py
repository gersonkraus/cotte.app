from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, func, and_
import logging

from app.models.models import Cliente
from app.schemas.schemas import ClienteCreate, ClienteUpdate
from app.repositories.base import RepositoryBase

logger = logging.getLogger(__name__)


class ClienteRepository(RepositoryBase[Cliente, ClienteCreate, ClienteUpdate]):
    """Repositório especializado para clientes."""
    
    def __init__(self):
        super().__init__(Cliente)
    
    def get_by_telefone(
        self,
        db: Session,
        telefone: str,
        empresa_id: Optional[int] = None
    ) -> Optional[Cliente]:
        """Busca cliente por telefone."""
        try:
            stmt = select(Cliente).where(Cliente.telefone == telefone)
            if empresa_id:
                stmt = stmt.where(Cliente.empresa_id == empresa_id)
            
            result = db.execute(stmt)
            return result.scalars().first()
        except SQLAlchemyError as e:
            logger.error(f"Erro ao buscar cliente por telefone {telefone}: {e}")
            raise

    def get_by_email(
        self,
        db: Session,
        email: str,
        empresa_id: Optional[int] = None
    ) -> Optional[Cliente]:
        """Busca cliente por email."""
        try:
            stmt = select(Cliente).where(Cliente.email == email)
            if empresa_id:
                stmt = stmt.where(Cliente.empresa_id == empresa_id)

            result = db.execute(stmt)
            return result.scalars().first()
        except SQLAlchemyError as e:
            logger.error(f"Erro ao buscar cliente por email {email}: {e}")
            raise
    
    def buscar_por_nome(
        self,
        db: Session,
        nome: str,
        empresa_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
        criado_por_id: Optional[int] = None,
    ) -> List[Cliente]:
        """Busca clientes por nome (busca parcial)."""
        try:
            stmt = select(Cliente).where(Cliente.nome.ilike(f"%{nome}%"))
            if empresa_id:
                stmt = stmt.where(Cliente.empresa_id == empresa_id)
            if criado_por_id is not None:
                stmt = stmt.where(Cliente.criado_por_id == criado_por_id)

            stmt = stmt.order_by(Cliente.nome).offset(skip).limit(limit)
            result = db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Erro ao buscar clientes por nome {nome}: {e}")
            raise
    
    def get_estatisticas(
        self,
        db: Session,
        empresa_id: int
    ) -> Dict[str, Any]:
        """Obtém estatísticas de clientes para uma empresa."""
        try:
            # Contagem total
            stmt_total = select(func.count(Cliente.id)).where(
                Cliente.empresa_id == empresa_id
            )
            result_total = db.execute(stmt_total)
            total = result_total.scalar() or 0
            
            # Clientes com email
            stmt_com_email = select(func.count(Cliente.id)).where(
                and_(
                    Cliente.empresa_id == empresa_id,
                    Cliente.email.isnot(None)
                )
            )
            result_com_email = db.execute(stmt_com_email)
            com_email = result_com_email.scalar() or 0
            
            # Clientes com telefone
            stmt_com_telefone = select(func.count(Cliente.id)).where(
                and_(
                    Cliente.empresa_id == empresa_id,
                    Cliente.telefone.isnot(None)
                )
            )
            result_com_telefone = db.execute(stmt_com_telefone)
            com_telefone = result_com_telefone.scalar() or 0
            
            return {
                "total": total,
                "com_email": com_email,
                "com_telefone": com_telefone,
                "sem_contato": total - max(com_email, com_telefone)
            }
        except SQLAlchemyError as e:
            logger.error(f"Erro ao obter estatísticas de clientes: {e}")
            raise