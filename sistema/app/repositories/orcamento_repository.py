from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, func, and_
import logging

from app.models.models import Orcamento, StatusOrcamento
from app.schemas.schemas import OrcamentoCreate, OrcamentoUpdate
from app.repositories.base import RepositoryBase

logger = logging.getLogger(__name__)


class OrcamentoRepository(RepositoryBase[Orcamento, OrcamentoCreate, OrcamentoUpdate]):
    """Repositório especializado para orçamentos."""
    
    def __init__(self):
        super().__init__(Orcamento)
    
    def get_with_details(
        self, 
        db: Session, 
        orcamento_id: int,
        empresa_id: Optional[int] = None
    ) -> Optional[Orcamento]:
        """Busca um orçamento com todos os relacionamentos carregados."""
        try:
            stmt = select(Orcamento).options(
                joinedload(Orcamento.cliente),
                joinedload(Orcamento.criado_por),
                joinedload(Orcamento.itens),
                joinedload(Orcamento.empresa)
            ).where(Orcamento.id == orcamento_id)
            
            if empresa_id:
                stmt = stmt.where(Orcamento.empresa_id == empresa_id)
            
            result = db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Erro ao buscar orçamento {orcamento_id} com detalhes: {e}")
            raise
    
    def get_by_numero(
        self, 
        db: Session, 
        numero: str,
        empresa_id: Optional[int] = None
    ) -> Optional[Orcamento]:
        """Busca um orçamento pelo número."""
        try:
            stmt = select(Orcamento).where(Orcamento.numero == numero)
            if empresa_id:
                stmt = stmt.where(Orcamento.empresa_id == empresa_id)
            
            result = db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Erro ao buscar orçamento por número {numero}: {e}")
            raise
    
    def get_by_cliente(
        self,
        db: Session,
        cliente_id: int,
        empresa_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Orcamento]:
        """Busca orçamentos de um cliente específico."""
        try:
            stmt = select(Orcamento).where(Orcamento.cliente_id == cliente_id)
            if empresa_id:
                stmt = stmt.where(Orcamento.empresa_id == empresa_id)
            
            stmt = stmt.order_by(Orcamento.criado_em.desc()).offset(skip).limit(limit)
            result = db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Erro ao buscar orçamentos do cliente {cliente_id}: {e}")
            raise
    
    def get_by_status(
        self,
        db: Session,
        status: StatusOrcamento,
        empresa_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Orcamento]:
        """Busca orçamentos por status."""
        try:
            stmt = select(Orcamento).where(Orcamento.status == status)
            if empresa_id:
                stmt = stmt.where(Orcamento.empresa_id == empresa_id)
            
            stmt = stmt.order_by(Orcamento.criado_em.desc()).offset(skip).limit(limit)
            result = db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Erro ao buscar orçamentos com status {status}: {e}")
            raise
    
    def get_expirados(
        self,
        db: Session,
        empresa_id: Optional[int] = None
    ) -> List[Orcamento]:
        """Busca orçamentos expirados."""
        try:
            from sqlalchemy import text
            from datetime import timedelta
            
            stmt = select(Orcamento).where(
                and_(
                    Orcamento.status == StatusOrcamento.ENVIADO,
                    func.date(Orcamento.criado_em) + Orcamento.validade_dias < func.current_date()
                )
            )
            if empresa_id:
                stmt = stmt.where(Orcamento.empresa_id == empresa_id)
            
            result = db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Erro ao buscar orçamentos expirados: {e}")
            raise
    
    def update_status(
        self,
        db: Session,
        orcamento_id: int,
        novo_status: StatusOrcamento,
        empresa_id: Optional[int] = None
    ) -> Optional[Orcamento]:
        """Atualiza o status de um orçamento."""
        try:
            stmt = select(Orcamento).where(Orcamento.id == orcamento_id)
            if empresa_id:
                stmt = stmt.where(Orcamento.empresa_id == empresa_id)
            
            result = db.execute(stmt)
            orcamento = result.scalar_one_or_none()
            if not orcamento:
                return None
            
            orcamento.status = novo_status
            orcamento.atualizado_em = datetime.now()
            
            db.commit()
            db.refresh(orcamento)
            return orcamento
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Erro ao atualizar status do orçamento {orcamento_id}: {e}")
            raise
    
    def gerar_numero_unico(
        self,
        db: Session,
        empresa_id: int
    ) -> str:
        """Gera um número único de orçamento."""
        try:
            ano = datetime.now().year
            ano_curto = str(ano)[-2:]
            
            from sqlalchemy import cast, Integer
            from sqlalchemy.sql import func as sql_func
            
            stmt = select(
                sql_func.max(
                    cast(
                        sql_func.split_part(
                            sql_func.split_part(Orcamento.numero, "-", 2),
                            "-", 1
                        ),
                        Integer
                    )
                )
            ).where(
                and_(
                    Orcamento.empresa_id == empresa_id,
                    Orcamento.numero.like(f"ORC-%-{ano_curto}")
                )
            )
            
            result = db.execute(stmt)
            max_seq = result.scalar()
            proximo = (max_seq or 0) + 1
            return f"ORC-{proximo}-{ano_curto}"
        except SQLAlchemyError as e:
            logger.error(f"Erro ao gerar número único de orçamento: {e}")
            raise
    
    def get_estatisticas(
        self,
        db: Session,
        empresa_id: int,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Obtém estatísticas de orçamentos."""
        try:
            filtros = [Orcamento.empresa_id == empresa_id]
            if data_inicio:
                filtros.append(Orcamento.criado_em >= data_inicio)
            if data_fim:
                filtros.append(Orcamento.criado_em <= data_fim)
            
            stmt_total = select(func.count(Orcamento.id)).where(and_(*filtros))
            result_total = db.execute(stmt_total)
            total = result_total.scalar() or 0
            
            estatisticas = {"total": total, "por_status": {}}
            for status in StatusOrcamento:
                stmt_status = select(func.count(Orcamento.id)).where(
                    and_(*filtros, Orcamento.status == status)
                )
                result_status = db.execute(stmt_status)
                count = result_status.scalar() or 0
                estatisticas["por_status"][status.value] = count
            
            stmt_valor = select(func.sum(Orcamento.total)).where(
                and_(*filtros, Orcamento.status == StatusOrcamento.APROVADO)
            )
            result_valor = db.execute(stmt_valor)
            valor_total = result_valor.scalar() or 0
            estatisticas["valor_total_aprovado"] = valor_total
            
            return estatisticas
        except SQLAlchemyError as e:
            logger.error(f"Erro ao obter estatísticas de orçamentos: {e}")
            raise