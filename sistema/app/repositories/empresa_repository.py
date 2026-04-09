"""
Repositório para operações com empresas.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, func, and_, or_
import logging

from app.models.models import Empresa, Usuario, Orcamento
from app.schemas.schemas import EmpresaUpdate, EmpresaAdminCreate
from app.repositories.base import RepositoryBase

logger = logging.getLogger(__name__)


class EmpresaRepository(RepositoryBase[Empresa, EmpresaAdminCreate, EmpresaUpdate]):
    """Repositório especializado para empresas."""
    
    def __init__(self):
        super().__init__(Empresa)
    
    async def get_by_telefone_operador(
        self,
        db: AsyncSession,
        telefone_operador: str
    ) -> Optional[Empresa]:
        """
        Busca empresa por telefone do operador (WhatsApp).
        
        Args:
            db: Sessão assíncrona do banco
            telefone_operador: Número do WhatsApp do operador
            
        Returns:
            Empresa encontrada ou None
        """
        try:
            stmt = select(Empresa).where(
                Empresa.telefone_operador == telefone_operador,
                Empresa.ativo == True
            )
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Erro ao buscar empresa por telefone operador {telefone_operador}: {e}")
            raise
    
    async def get_estatisticas(
        self,
        db: AsyncSession,
        empresa_id: int
    ) -> Dict[str, Any]:
        """
        Obtém estatísticas de uma empresa.
        
        Args:
            db: Sessão assíncrona do banco
            empresa_id: ID da empresa
            
        Returns:
            Dicionário com estatísticas
        """
        try:
            # Contagem de usuários ativos
            stmt_usuarios = select(func.count(Usuario.id)).where(
                Usuario.empresa_id == empresa_id,
                Usuario.ativo == True
            )
            result_usuarios = await db.execute(stmt_usuarios)
            total_usuarios = result_usuarios.scalar() or 0
            
            # Contagem de clientes
            from app.repositories.cliente_repository import ClienteRepository
            cliente_repo = ClienteRepository()
            estatisticas_clientes = await cliente_repo.get_estatisticas(db, empresa_id)
            
            # Contagem de orçamentos
            stmt_orcamentos = select(func.count(Orcamento.id)).where(
                Orcamento.empresa_id == empresa_id
            )
            result_orcamentos = await db.execute(stmt_orcamentos)
            total_orcamentos = result_orcamentos.scalar() or 0
            
            # Orçamentos por status
            stmt_orcamentos_status = select(
                Orcamento.status,
                func.count(Orcamento.id).label("quantidade")
            ).where(
                Orcamento.empresa_id == empresa_id
            ).group_by(Orcamento.status)
            
            result_status = await db.execute(stmt_orcamentos_status)
            orcamentos_por_status = {
                row.status: row.quantidade 
                for row in result_status.all()
            }
            
            return {
                "total_usuarios": total_usuarios,
                "clientes": estatisticas_clientes,
                "total_orcamentos": total_orcamentos,
                "orcamentos_por_status": orcamentos_por_status
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Erro ao obter estatísticas da empresa {empresa_id}: {e}")
            raise
    
    async def get_configuracoes(
        self,
        db: AsyncSession,
        empresa_id: int
    ) -> Dict[str, Any]:
        """
        Obtém configurações de uma empresa.
        
        Args:
            db: Sessão assíncrona do banco
            empresa_id: ID da empresa
            
        Returns:
            Dicionário com configurações
        """
        try:
            empresa = await self.get(db, empresa_id)
            
            if not empresa:
                return {}
            
            return {
                "validade_padrao_dias": empresa.validade_padrao_dias,
                "desconto_max_percent": empresa.desconto_max_percent,
                "lembrete_dias": empresa.lembrete_dias,
                "lembrete_texto": empresa.lembrete_texto,
                "notif_email_aprovado": empresa.notif_email_aprovado,
                "notif_email_expirado": empresa.notif_email_expirado,
                "anexar_pdf_email": empresa.anexar_pdf_email,
                "assinatura_email": empresa.assinatura_email,
                "msg_boas_vindas": empresa.msg_boas_vindas,
                "boas_vindas_ativo": empresa.boas_vindas_ativo,
                "limite_orcamentos_custom": empresa.limite_orcamentos_custom
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Erro ao obter configurações da empresa {empresa_id}: {e}")
            raise
    
    async def update_configuracoes(
        self,
        db: AsyncSession,
        empresa_id: int,
        configuracoes: Dict[str, Any]
    ) -> Empresa:
        """
        Atualiza configurações de uma empresa.
        
        Args:
            db: Sessão assíncrona do banco
            empresa_id: ID da empresa
            configuracoes: Dicionário com configurações a atualizar
            
        Returns:
            Empresa atualizada
        """
        try:
            empresa = await self.get(db, empresa_id)
            
            if not empresa:
                raise ValueError(f"Empresa com ID {empresa_id} não encontrada")
            
            # Campos permitidos para atualização
            campos_permitidos = {
                "validade_padrao_dias",
                "desconto_max_percent", 
                "lembrete_dias",
                "lembrete_texto",
                "notif_email_aprovado",
                "notif_email_expirado",
                "anexar_pdf_email",
                "assinatura_email",
                "msg_boas_vindas",
                "boas_vindas_ativo",
                "limite_orcamentos_custom"
            }
            
            # Atualiza campos
            for campo, valor in configuracoes.items():
                if campo in campos_permitidos and hasattr(empresa, campo):
                    setattr(empresa, campo, valor)
            
            await db.commit()
            await db.refresh(empresa)
            
            logger.info(f"Configurações da empresa {empresa_id} atualizadas")
            
            return empresa
            
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Erro ao atualizar configurações da empresa {empresa_id}: {e}")
            raise
    
    async def listar_empresas_ativas(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[Empresa]:
        """
        Lista empresas ativas.
        
        Args:
            db: Sessão assíncrona do banco
            skip: Número de registros para pular
            limit: Número máximo de registros
            
        Returns:
            Lista de empresas ativas
        """
        try:
            stmt = select(Empresa).where(
                Empresa.ativo == True
            ).order_by(Empresa.nome).offset(skip).limit(limit)
            
            result = await db.execute(stmt)
            return result.scalars().all()
            
        except SQLAlchemyError as e:
            logger.error(f"Erro ao listar empresas ativas: {e}")
            raise