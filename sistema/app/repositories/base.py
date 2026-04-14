from typing import TypeVar, Type, Generic, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status
import logging
import time
import hashlib
import json

from app.core.database import Base
from app.core.tenant_context import get_scoped_empresa_id, tenant_bypass_enabled
from app.models.tenant import TenantScopedMixin

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

logger = logging.getLogger(__name__)


class RepositoryBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Repositório base com operações CRUD síncronas e cache."""
    
    def __init__(self, model: Type[ModelType]):
        self.model = model
        self._cache_enabled = True
        self._cache_ttl = 300  # 5 minutos em segundos
        self._cache = {}
    
    def get(self, db: Session, id: int) -> Optional[ModelType]:
        """Busca um registro por ID."""
        try:
            stmt = select(self.model).where(self.model.id == id)
            result = db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Erro ao buscar {self.model.__name__} com ID {id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao buscar {self.model.__name__}"
            )
    
    def get_multi(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """Busca múltiplos registros com paginação e filtros."""
        try:
            stmt = select(self.model)
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        stmt = stmt.where(getattr(self.model, field) == value)
            
            stmt = stmt.offset(skip).limit(limit)
            result = db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Erro ao buscar múltiplos {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao buscar {self.model.__name__}"
            )

    def create(self, db: Session, obj_in: CreateSchemaType) -> ModelType:
        """Cria um novo registro."""
        try:
            obj_in_data = obj_in.model_dump() if hasattr(obj_in, 'model_dump') else dict(obj_in)
            db_obj = self.model(**obj_in_data)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Erro ao criar {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao criar {self.model.__name__}"
            )
    
    def update(
        self, 
        db: Session, 
        db_obj: ModelType, 
        obj_in: UpdateSchemaType
    ) -> ModelType:
        """Atualiza um registro existente."""
        try:
            update_data = obj_in.model_dump(exclude_unset=True) if hasattr(obj_in, 'model_dump') else dict(obj_in)
            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Erro ao atualizar {self.model.__name__} ID {db_obj.id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao atualizar {self.model.__name__}"
            )
    
    def delete(self, db: Session, id: int) -> bool:
        """Remove um registro por ID."""
        try:
            stmt = delete(self.model).where(self.model.id == id)
            if (
                issubclass(self.model, TenantScopedMixin)
                and not tenant_bypass_enabled(db)
            ):
                empresa_id = get_scoped_empresa_id(db)
                if empresa_id is not None:
                    stmt = stmt.where(self.model.empresa_id == empresa_id)
            result = db.execute(stmt)
            db.commit()
            return result.rowcount > 0
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Erro ao remover {self.model.__name__} ID {id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao remover {self.model.__name__}"
            )
    
    def exists(self, db: Session, id: int) -> bool:
        """Verifica se um registro existe pelo ID."""
        obj = self.get(db, id)
        return obj is not None
    
    def get_by_field(
        self, 
        db: Session, 
        field: str, 
        value: Any
    ) -> Optional[ModelType]:
        """Busca um registro por um campo específico."""
        try:
            if not hasattr(self.model, field):
                raise ValueError(f"Campo {field} não existe em {self.model.__name__}")
            stmt = select(self.model).where(getattr(self.model, field) == value)
            result = db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Erro ao buscar {self.model.__name__} por {field}={value}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao buscar {self.model.__name__}"
            )
