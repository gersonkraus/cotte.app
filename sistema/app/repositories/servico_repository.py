"""
Repositório para operações com serviços (catálogo).
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, func, and_, or_
import logging

from app.models.models import Servico
from app.schemas.schemas import ServicoCreate, ServicoUpdate
from app.repositories.base import RepositoryBase

logger = logging.getLogger(__name__)


class ServicoRepository(RepositoryBase[Servico, ServicoCreate, ServicoUpdate]):
    """Repositório especializado para serviços (catálogo)."""
    
    def __init__(self):
        super().__init__(Servico)
    
    async def buscar_por_nome(
        self,
        db: AsyncSession,
        nome: str,
        empresa_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Servico]:
        """
        Busca serviços por nome (busca parcial).
        
        Args:
            db: Sessão assíncrona do banco
            nome: Nome ou parte do nome
            empresa_id: ID da empresa (para serviços da empresa)
            skip: Número de registros para pular
            limit: Número máximo de registros
            
        Returns:
            Lista de serviços
        """
        try:
            stmt = select(Servico).where(Servico.nome.ilike(f"%{nome}%"))
            
            if empresa_id:
                stmt = stmt.where(Servico.empresa_id == empresa_id)
            
            stmt = stmt.order_by(Servico.nome).offset(skip).limit(limit)
            result = await db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Erro ao buscar serviços por nome {nome}: {e}")
            raise
    
    async def listar_por_empresa(
        self,
        db: AsyncSession,
        empresa_id: int,
        skip: int = 0,
        limit: int = 100,
        apenas_ativos: bool = True
    ) -> List[Servico]:
        """
        Lista serviços de uma empresa específica.
        
        Args:
            db: Sessão assíncrona do banco
            empresa_id: ID da empresa
            skip: Número de registros para pular
            limit: Número máximo de registros
            apenas_ativos: Filtra apenas serviços ativos
            
        Returns:
            Lista de serviços da empresa
        """
        try:
            stmt = select(Servico).where(Servico.empresa_id == empresa_id)
            
            if apenas_ativos:
                stmt = stmt.where(Servico.ativo == True)
            
            stmt = stmt.order_by(Servico.nome).offset(skip).limit(limit)
            result = await db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Erro ao listar serviços da empresa {empresa_id}: {e}")
            raise
    
    async def get_servicos_populares(
        self,
        db: AsyncSession,
        empresa_id: int,
        limite: int = 10
    ) -> List[Servico]:
        """
        Obtém serviços mais populares (mais usados em orçamentos).
        
        Args:
            db: Sessão assíncrona do banco
            empresa_id: ID da empresa
            limite: Número máximo de serviços
            
        Returns:
            Lista de serviços populares
        """
        try:
            # Esta é uma query mais complexa que precisaria de JOIN com itens_orcamento
            # Por enquanto, retorna serviços ativos ordenados por nome
            stmt = select(Servico).where(
                Servico.empresa_id == empresa_id,
                Servico.ativo == True
            ).order_by(Servico.nome).limit(limite)
            
            result = await db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Erro ao obter serviços populares da empresa {empresa_id}: {e}")
            raise
    
    async def get_estatisticas(
        self,
        db: AsyncSession,
        empresa_id: int
    ) -> Dict[str, Any]:
        """
        Obtém estatísticas de serviços de uma empresa.
        
        Args:
            db: Sessão assíncrona do banco
            empresa_id: ID da empresa
            
        Returns:
            Dicionário com estatísticas
        """
        try:
            # Contagem total
            stmt_total = select(func.count(Servico.id)).where(
                Servico.empresa_id == empresa_id
            )
            result_total = await db.execute(stmt_total)
            total = result_total.scalar() or 0
            
            # Contagem ativos
            stmt_ativos = select(func.count(Servico.id)).where(
                and_(
                    Servico.empresa_id == empresa_id,
                    Servico.ativo == True
                )
            )
            result_ativos = await db.execute(stmt_ativos)
            ativos = result_ativos.scalar() or 0
            
            # Serviços com preço padrão
            stmt_com_preco = select(func.count(Servico.id)).where(
                and_(
                    Servico.empresa_id == empresa_id,
                    Servico.preco_padrao.isnot(None),
                    Servico.preco_padrao > 0
                )
            )
            result_com_preco = await db.execute(stmt_com_preco)
            com_preco = result_com_preco.scalar() or 0
            
            # Média de preços
            stmt_media_preco = select(func.avg(Servico.preco_padrao)).where(
                and_(
                    Servico.empresa_id == empresa_id,
                    Servico.preco_padrao.isnot(None),
                    Servico.preco_padrao > 0
                )
            )
            result_media_preco = await db.execute(stmt_media_preco)
            media_preco = result_media_preco.scalar() or 0
            
            return {
                "total": total,
                "ativos": ativos,
                "inativos": total - ativos,
                "com_preco_padrao": com_preco,
                "sem_preco_padrao": total - com_preco,
                "media_preco": float(media_preco) if media_preco else 0.0
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Erro ao obter estatísticas de serviços da empresa {empresa_id}: {e}")
            raise
    
    async def buscar_servico_similar(
        self,
        db: AsyncSession,
        nome: str,
        empresa_id: int,
        limite_similaridade: float = 0.7
    ) -> Optional[Servico]:
        """
        Busca serviço similar por nome usando similaridade de texto.
        Útil para evitar duplicação no catálogo.
        
        Args:
            db: Sessão assíncrona do banco
            nome: Nome do serviço a buscar
            empresa_id: ID da empresa
            limite_similaridade: Limite de similaridade (0.0 a 1.0)
            
        Returns:
            Servico similar ou None
        """
        try:
            # Busca serviços da mesma empresa
            stmt = select(Servico).where(
                Servico.empresa_id == empresa_id,
                Servico.ativo == True
            )
            result = await db.execute(stmt)
            servicos = result.scalars().all()
            
            # Implementação simples de similaridade (poderia usar fuzzywuzzy ou similar)
            nome_lower = nome.lower().strip()
            
            for servico in servicos:
                servico_nome_lower = servico.nome.lower().strip()
                
                # Verifica se é substring
                if nome_lower in servico_nome_lower or servico_nome_lower in nome_lower:
                    return servico
                
                # Verifica similaridade simples (compartilha palavras)
                nome_palavras = set(nome_lower.split())
                servico_palavras = set(servico_nome_lower.split())
                
                palavras_comuns = nome_palavras.intersection(servico_palavras)
                if palavras_comuns:
                    # Calcula similaridade básica
                    similaridade = len(palavras_comuns) / max(len(nome_palavras), len(servico_palavras))
                    if similaridade >= limite_similaridade:
                        return servico
            
            return None
            
        except SQLAlchemyError as e:
            logger.error(f"Erro ao buscar serviço similar para '{nome}': {e}")
            raise