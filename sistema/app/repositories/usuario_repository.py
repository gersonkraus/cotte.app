"""
Repositório para operações com usuários.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, func, and_, or_, func
import logging

from app.models.models import Usuario
from app.schemas.schemas import UsuarioCreate, UsuarioEmpresaUpdate
from app.repositories.base import RepositoryBase

logger = logging.getLogger(__name__)


class UsuarioRepository(RepositoryBase[Usuario, UsuarioCreate, UsuarioEmpresaUpdate]):
    """Repositório especializado para usuários."""
    
    def __init__(self):
        super().__init__(Usuario)
    
    async def get_by_email(
        self,
        db: AsyncSession,
        email: str
    ) -> Optional[Usuario]:
        """
        Busca usuário por email.
        
        Args:
            db: Sessão assíncrona do banco
            email: Endereço de email
            
        Returns:
            Usuário encontrado ou None
        """
        try:
            stmt = select(Usuario).where(
                func.lower(Usuario.email) == email,
                Usuario.ativo == True
            )
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Erro ao buscar usuário por email {email}: {e}")
            raise
    
    async def get_by_empresa(
        self,
        db: AsyncSession,
        empresa_id: int,
        skip: int = 0,
        limit: int = 100,
        apenas_ativos: bool = True
    ) -> List[Usuario]:
        """
        Lista usuários de uma empresa.
        
        Args:
            db: Sessão assíncrona do banco
            empresa_id: ID da empresa
            skip: Número de registros para pular
            limit: Número máximo de registros
            apenas_ativos: Filtra apenas usuários ativos
            
        Returns:
            Lista de usuários da empresa
        """
        try:
            stmt = select(Usuario).where(Usuario.empresa_id == empresa_id)
            
            if apenas_ativos:
                stmt = stmt.where(Usuario.ativo == True)
            
            stmt = stmt.order_by(Usuario.nome).offset(skip).limit(limit)
            result = await db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Erro ao listar usuários da empresa {empresa_id}: {e}")
            raise
    
    async def get_administradores_empresa(
        self,
        db: AsyncSession,
        empresa_id: int
    ) -> List[Usuario]:
        """
        Obtém administradores de uma empresa.
        
        Args:
            db: Sessão assíncrona do banco
            empresa_id: ID da empresa
            
        Returns:
            Lista de usuários administradores
        """
        try:
            stmt = select(Usuario).where(
                Usuario.empresa_id == empresa_id,
                Usuario.ativo == True,
                Usuario.is_admin == True
            ).order_by(Usuario.nome)
            
            result = await db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Erro ao obter administradores da empresa {empresa_id}: {e}")
            raise
    
    async def verificar_email_existente(
        self,
        db: AsyncSession,
        email: str,
        excluir_usuario_id: Optional[int] = None
    ) -> bool:
        """
        Verifica se email já está em uso por outro usuário.
        
        Args:
            db: Sessão assíncrona do banco
            email: Email a verificar
            excluir_usuario_id: ID do usuário a excluir da verificação (para atualização)
            
        Returns:
            True se email já está em uso, False caso contrário
        """
        try:
            stmt = select(Usuario).where(func.lower(Usuario.email) == email)
            
            if excluir_usuario_id:
                stmt = stmt.where(Usuario.id != excluir_usuario_id)
            
            result = await db.execute(stmt)
            usuario = result.scalar_one_or_none()
            
            return usuario is not None
            
        except SQLAlchemyError as e:
            logger.error(f"Erro ao verificar email {email}: {e}")
            raise
    
    async def atualizar_senha(
        self,
        db: AsyncSession,
        usuario_id: int,
        nova_senha_hash: str
    ) -> bool:
        """
        Atualiza a senha de um usuário.
        
        Args:
            db: Sessão assíncrona do banco
            usuario_id: ID do usuário
            nova_senha_hash: Hash da nova senha
            
        Returns:
            True se atualizado com sucesso
        """
        try:
            usuario = await self.get(db, usuario_id)
            
            if not usuario:
                return False
            
            usuario.senha_hash = nova_senha_hash
            await db.commit()
            
            logger.info(f"Senha do usuário {usuario_id} atualizada")
            return True
            
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Erro ao atualizar senha do usuário {usuario_id}: {e}")
            raise
    
    async def get_estatisticas(
        self,
        db: AsyncSession,
        empresa_id: int
    ) -> Dict[str, Any]:
        """
        Obtém estatísticas de usuários de uma empresa.
        
        Args:
            db: Sessão assíncrona do banco
            empresa_id: ID da empresa
            
        Returns:
            Dicionário com estatísticas
        """
        try:
            # Contagem total
            stmt_total = select(func.count(Usuario.id)).where(
                Usuario.empresa_id == empresa_id
            )
            result_total = await db.execute(stmt_total)
            total = result_total.scalar() or 0
            
            # Contagem ativos
            stmt_ativos = select(func.count(Usuario.id)).where(
                and_(
                    Usuario.empresa_id == empresa_id,
                    Usuario.ativo == True
                )
            )
            result_ativos = await db.execute(stmt_ativos)
            ativos = result_ativos.scalar() or 0
            
            # Contagem administradores
            stmt_admins = select(func.count(Usuario.id)).where(
                and_(
                    Usuario.empresa_id == empresa_id,
                    Usuario.ativo == True,
                    Usuario.is_admin == True
                )
            )
            result_admins = await db.execute(stmt_admins)
            admins = result_admins.scalar() or 0
            
            # Último acesso
            stmt_ultimo_acesso = select(
                func.max(Usuario.ultimo_acesso_em)
            ).where(
                Usuario.empresa_id == empresa_id,
                Usuario.ativo == True
            )
            result_ultimo_acesso = await db.execute(stmt_ultimo_acesso)
            ultimo_acesso = result_ultimo_acesso.scalar()
            
            return {
                "total": total,
                "ativos": ativos,
                "inativos": total - ativos,
                "administradores": admins,
                "usuarios_comuns": ativos - admins,
                "ultimo_acesso": ultimo_acesso.isoformat() if ultimo_acesso else None
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Erro ao obter estatísticas de usuários da empresa {empresa_id}: {e}")
            raise
    
    async def atualizar_ultimo_acesso(
        self,
        db: AsyncSession,
        usuario_id: int
    ) -> bool:
        """
        Atualiza a data do último acesso do usuário.
        
        Args:
            db: Sessão assíncrona do banco
            usuario_id: ID do usuário
            
        Returns:
            True se atualizado com sucesso
        """
        try:
            from sqlalchemy.sql import func
            
            stmt = select(Usuario).where(Usuario.id == usuario_id)
            result = await db.execute(stmt)
            usuario = result.scalar_one_or_none()
            
            if not usuario:
                return False
            
            usuario.ultimo_acesso_em = func.now()
            await db.commit()
            
            return True
            
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Erro ao atualizar último acesso do usuário {usuario_id}: {e}")
            raise
    
    async def buscar_por_nome(
        self,
        db: AsyncSession,
        nome: str,
        empresa_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Usuario]:
        """
        Busca usuários por nome (busca parcial).
        
        Args:
            db: Sessão assíncrona do banco
            nome: Nome ou parte do nome
            empresa_id: ID da empresa (opcional)
            skip: Número de registros para pular
            limit: Número máximo de registros
            
        Returns:
            Lista de usuários
        """
        try:
            stmt = select(Usuario).where(
                Usuario.nome.ilike(f"%{nome}%"),
                Usuario.ativo == True
            )
            
            if empresa_id:
                stmt = stmt.where(Usuario.empresa_id == empresa_id)
            
            stmt = stmt.order_by(Usuario.nome).offset(skip).limit(limit)
            result = await db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Erro ao buscar usuários por nome {nome}: {e}")
            raise