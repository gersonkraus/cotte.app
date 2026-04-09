from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db as get_core_db
from app.services.cliente_service import ClienteService
from app.repositories.cliente_repository import ClienteRepository


def get_db() -> Generator[Session, None, None]:
    """
    Obtém uma sessão síncrona do banco de dados.
    
    Yields:
        Sessão síncrona do SQLAlchemy
    """
    yield from get_core_db()


def get_cliente_repository() -> ClienteRepository:
    """
    Obtém uma instância do repositório de clientes.
    
    Returns:
        Instância de ClienteRepository
    """
    return ClienteRepository()


def get_cliente_service(db: Session = Depends(get_db)) -> ClienteService:
    """
    Obtém uma instância do serviço de clientes.
    
    Args:
        db: Sessão do banco (injetada via Depends)
        
    Returns:
        Instância de ClienteService
    """
    return ClienteService(db)