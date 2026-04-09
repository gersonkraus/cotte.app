from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

from fastapi import HTTPException

from app.models.models import Cliente, Usuario
from app.schemas.schemas import ClienteCreate, ClienteUpdate
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.orcamento_repository import OrcamentoRepository
from app.core.exceptions import ClienteNotFoundException, ClienteDuplicadoException

logger = logging.getLogger(__name__)


class ClienteService:
    """Serviço para operações com clientes."""

    def __init__(self, db: Session):
        self.db = db
        self.cliente_repo = ClienteRepository()
        self.orcamento_repo = OrcamentoRepository()

    def criar_cliente(self, dados: ClienteCreate, usuario: Usuario) -> Cliente:
        """Cria um novo cliente com validações de negócio."""
        try:
            # Verifica se já existe cliente com mesmo telefone na mesma empresa
            if dados.telefone:
                cliente_existente = self.cliente_repo.get_by_telefone(
                    self.db, dados.telefone, usuario.empresa_id
                )
                if cliente_existente:
                    raise ClienteDuplicadoException(
                        f"Cliente com telefone {dados.telefone} já existe"
                    )

            # Verifica se já existe cliente com mesmo email na mesma empresa
            if dados.email:
                cliente_existente = self.cliente_repo.get_by_email(
                    self.db, dados.email, usuario.empresa_id
                )
                if cliente_existente:
                    raise ClienteDuplicadoException(
                        f"Cliente com email {dados.email} já existe"
                    )

            # Adiciona empresa_id e criado_por_id aos dados
            dados_dict = dados.dict()
            dados_dict["empresa_id"] = usuario.empresa_id
            dados_dict["criado_por_id"] = usuario.id

            # Cria o cliente
            cliente = self.cliente_repo.create(self.db, dados_dict)
            logger.info(f"Cliente criado: ID {cliente.id}, Nome: {cliente.nome}")
            return cliente

        except ClienteDuplicadoException:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Erro ao criar cliente: {e}", exc_info=True)
            raise

    def obter_cliente(self, cliente_id: int, usuario: Usuario) -> Cliente:
        """Obtém um cliente específico com verificação de permissão."""
        try:
            cliente = self.cliente_repo.get(self.db, cliente_id)
            if not cliente or cliente.empresa_id != usuario.empresa_id:
                raise ClienteNotFoundException(cliente_id)
            return cliente
        except ClienteNotFoundException:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Erro ao obter cliente {cliente_id}: {e}", exc_info=True)
            raise

    def listar_clientes(
        self,
        usuario: Usuario,
        skip: int = 0,
        limit: int = 100,
        nome: Optional[str] = None,
        telefone: Optional[str] = None,
        email: Optional[str] = None,
        apenas_meus: bool = False,
    ) -> List[Cliente]:
        """Lista clientes com filtros e paginação."""
        try:
            filters = {"empresa_id": usuario.empresa_id}

            # Filtra por dono do registro se solicitado (requer coluna criado_por_id no banco)
            if apenas_meus:
                filters["criado_por_id"] = usuario.id

            if nome:
                return self.cliente_repo.buscar_por_nome(
                    self.db,
                    nome,
                    usuario.empresa_id,
                    skip,
                    limit,
                    criado_por_id=usuario.id if apenas_meus else None,
                )
            if telefone:
                cliente = self.cliente_repo.get_by_telefone(
                    self.db, telefone, usuario.empresa_id
                )
                if cliente and apenas_meus and cliente.criado_por_id != usuario.id:
                    return []
                return [cliente] if cliente else []
            if email:
                cliente = self.cliente_repo.get_by_email(
                    self.db, email, usuario.empresa_id
                )
                if cliente and apenas_meus and cliente.criado_por_id != usuario.id:
                    return []
                return [cliente] if cliente else []

            return self.cliente_repo.get_multi(
                self.db, skip=skip, limit=limit, filters=filters
            )
        except SQLAlchemyError as e:
            logger.error(f"Erro ao listar clientes: {e}", exc_info=True)
            raise

    def atualizar_cliente(
        self, cliente_id: int, dados: ClienteUpdate, usuario: Usuario
    ) -> Cliente:
        """Atualiza um cliente existente."""
        try:
            cliente = self.obter_cliente(cliente_id, usuario)
            if dados.telefone is not None and dados.telefone != cliente.telefone:
                cliente_existente = self.cliente_repo.get_by_telefone(
                    self.db, dados.telefone, usuario.empresa_id
                )
                if cliente_existente and cliente_existente.id != cliente_id:
                    raise ClienteDuplicadoException(
                        f"Telefone {dados.telefone} já existe"
                    )

            if dados.email is not None and dados.email != cliente.email:
                cliente_existente = self.cliente_repo.get_by_email(
                    self.db, dados.email, usuario.empresa_id
                )
                if cliente_existente and cliente_existente.id != cliente_id:
                    raise ClienteDuplicadoException(f"Email {dados.email} já existe")

            return self.cliente_repo.update(self.db, cliente, dados)
        except (ClienteNotFoundException, ClienteDuplicadoException):
            raise
        except SQLAlchemyError as e:
            logger.error(f"Erro ao atualizar cliente {cliente_id}: {e}", exc_info=True)
            raise

    def excluir_cliente(self, cliente_id: int, usuario: Usuario) -> bool:
        """Exclui um cliente."""
        try:
            cliente = self.obter_cliente(cliente_id, usuario)

            orcamentos = self.orcamento_repo.get_by_cliente(
                self.db, cliente_id, empresa_id=usuario.empresa_id
            )
            if orcamentos:
                raise HTTPException(
                    status_code=400,
                    detail="Cliente possui orçamentos que precisam ser removidos antes",
                )

            return self.cliente_repo.delete(self.db, cliente_id)
        except ClienteNotFoundException:
            raise
        except HTTPException:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Erro ao excluir cliente {cliente_id}: {e}", exc_info=True)
            raise

    def obter_estatisticas(self, usuario: Usuario) -> Dict[str, Any]:
        """Obtém estatísticas de clientes."""
        return self.cliente_repo.get_estatisticas(self.db, usuario.empresa_id)

    def buscar_ou_criar_cliente(
        self, telefone: str, nome: str, usuario: Usuario, email: Optional[str] = None
    ) -> Cliente:
        """Busca cliente por telefone ou cria um novo se não existir."""
        try:
            cliente = self.cliente_repo.get_by_telefone(
                self.db, telefone, usuario.empresa_id
            )
            if cliente:
                return cliente

            dados = ClienteCreate(nome=nome, telefone=telefone, email=email)
            return self.criar_cliente(dados, usuario)
        except SQLAlchemyError as e:
            logger.error(f"Erro em buscar_ou_criar_cliente: {e}", exc_info=True)
            raise
