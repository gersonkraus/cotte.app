from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError
from app.models.models import CategoriaFinanceira
from app.core.exceptions import HTTPException

class CategoriaFinanceiraRepository:
    def __init__(self, db: Session):
        self.db = db

    def criar_categoria(self, categoria: CategoriaFinanceira) -> CategoriaFinanceira:
        # Verifica duplicidade antes de inserir (importante para SQLite que
        # não suporta partial unique indexes corretamente)
        existente = self._buscar_categoria_por_nome_tipo(
            categoria.empresa_id, categoria.nome, categoria.tipo
        )
        if existente:
            if existente.ativo:
                raise HTTPException(
                    status_code=400,
                    detail="Já existe uma categoria ativa com o mesmo nome e tipo."
                )
            # Reativa categoria inativa existente com os novos dados
            existente.ativo = True
            existente.cor = categoria.cor
            existente.icone = categoria.icone
            existente.ordem = categoria.ordem
            self.db.add(existente)
            self.db.flush()
            self.db.refresh(existente)
            return existente

        self.db.add(categoria)
        self.db.flush()
        self.db.refresh(categoria)
        return categoria

    def _buscar_categoria_por_nome_tipo(
        self, empresa_id: int, nome: str, tipo: str
    ) -> Optional[CategoriaFinanceira]:
        stmt = select(CategoriaFinanceira).filter(
            CategoriaFinanceira.empresa_id == empresa_id,
            CategoriaFinanceira.nome == nome,
            CategoriaFinanceira.tipo == tipo,
        )
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    def get_by_id(self, categoria_id: int, empresa_id: int) -> Optional[CategoriaFinanceira]:
        stmt = select(CategoriaFinanceira).filter_by(id=categoria_id, empresa_id=empresa_id)
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    def listar_categorias(self, empresa_id: int, tipo: Optional[str] = None, ativas: bool = True) -> List[CategoriaFinanceira]:
        stmt = select(CategoriaFinanceira).filter_by(empresa_id=empresa_id)
        if tipo:
            stmt = stmt.filter_by(tipo=tipo)
        if ativas:
            stmt = stmt.filter_by(ativo=True)
        stmt = stmt.order_by(CategoriaFinanceira.ordem, CategoriaFinanceira.nome)
        result = self.db.execute(stmt)
        return result.scalars().all()

    def verificar_duplicidade(self, empresa_id: int, nome: str, tipo: str, categoria_id: Optional[int] = None) -> Optional[CategoriaFinanceira]:
        # Verifica duplicidade considerando categorias ativas, mas excluindo a própria categoria se for uma atualização.
        stmt = select(CategoriaFinanceira).filter(
            CategoriaFinanceira.empresa_id == empresa_id,
            CategoriaFinanceira.nome == nome,
            CategoriaFinanceira.tipo == tipo,
            CategoriaFinanceira.ativo == True
        )
        if categoria_id:
            stmt = stmt.filter(CategoriaFinanceira.id != categoria_id)
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    def atualizar_categoria(self, categoria: CategoriaFinanceira, update_data: dict) -> CategoriaFinanceira:
        novo_nome = update_data.get("nome", categoria.nome)
        novo_tipo = update_data.get("tipo", categoria.tipo)

        # Verifica duplicidade antes de atualizar (importante para SQLite)
        duplicada = self.verificar_duplicidade(
            categoria.empresa_id, novo_nome, novo_tipo, categoria_id=categoria.id
        )
        if duplicada:
            raise HTTPException(
                status_code=400,
                detail="Já existe uma categoria ativa com o mesmo nome e tipo."
            )

        for key, value in update_data.items():
            setattr(categoria, key, value)
        self.db.flush()
        return categoria

    def soft_delete_categoria(self, categoria: CategoriaFinanceira) -> CategoriaFinanceira:
        categoria.ativo = False
        self.db.flush()
        self.db.refresh(categoria)
        return categoria
