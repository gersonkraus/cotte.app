from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from datetime import datetime

from app.api.deps import get_db, get_cliente_service
from app.core.auth import get_usuario_atual, exigir_permissao
from app.models.models import Usuario, Cliente
from app.schemas.schemas import ClienteCreate, ClienteUpdate, ClienteOut
from app.services.cliente_service import ClienteService
from app.utils.csv_utils import gerar_csv_response
from app.core.exceptions import (
    ClienteNotFoundException,
    ClienteDuplicadoException,
    EmpresaNotFoundException,
)

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.post("/", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
def criar_cliente(
    dados: ClienteCreate,
    usuario: Usuario = Depends(exigir_permissao("clientes", "escrita")),
    cliente_service: ClienteService = Depends(get_cliente_service),
):
    """Cria um novo cliente."""
    return cliente_service.criar_cliente(dados, usuario)


@router.get("/", response_model=List[ClienteOut])
def listar_clientes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    nome: Optional[str] = Query(None),
    telefone: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    usuario: Usuario = Depends(exigir_permissao("clientes", "leitura")),
    cliente_service: ClienteService = Depends(get_cliente_service),
):
    """Lista clientes com filtros e paginação."""
    perms = usuario.permissoes or {}
    perm_cli = perms.get("clientes", "leitura")

    apenas_meus = (
        perm_cli == "meus" and not usuario.is_gestor and not usuario.is_superadmin
    )

    return cliente_service.listar_clientes(
        usuario=usuario,
        skip=skip,
        limit=limit,
        nome=nome,
        telefone=telefone,
        email=email,
        apenas_meus=apenas_meus,
    )


@router.get("/exportar/csv")
def exportar_clientes_csv(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("clientes", "leitura")),
):
    """Exporta clientes da empresa em CSV."""
    clientes = (
        db.query(Cliente)
        .filter(Cliente.empresa_id == usuario.empresa_id)
        .order_by(Cliente.nome)
        .all()
    )

    header = [
        "Tipo",
        "Nome",
        "CPF",
        "CNPJ",
        "Razão Social",
        "Telefone",
        "E-mail",
        "Cidade",
        "Estado",
        "Criado em",
    ]
    rows = []
    for c in clientes:
        data_str = c.criado_em.strftime("%d/%m/%Y") if c.criado_em else ""
        rows.append([
            c.tipo_pessoa or "PF",
            c.nome or "",
            c.cpf or "",
            c.cnpj or "",
            c.razao_social or "",
            c.telefone or "",
            c.email or "",
            c.cidade or "",
            c.estado or "",
            data_str,
        ])
    return gerar_csv_response(header, rows, "clientes")


@router.get("/estatisticas/resumo")
def obter_estatisticas_clientes(
    usuario: Usuario = Depends(exigir_permissao("clientes", "leitura")),
    cliente_service: ClienteService = Depends(get_cliente_service),
):
    """Obtém estatísticas de clientes."""
    return cliente_service.obter_estatisticas(usuario)


@router.get("/buscar/telefone/{telefone}", response_model=Optional[ClienteOut])
def buscar_cliente_por_telefone(
    telefone: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("clientes", "leitura")),
):
    """Busca cliente por telefone."""
    from app.repositories.cliente_repository import ClienteRepository

    cliente_repo = ClienteRepository()
    cliente = cliente_repo.get_by_telefone(db, telefone, usuario.empresa_id)
    if not cliente:
        raise ClienteNotFoundException(f"telefone={telefone}")
    return cliente


@router.post("/buscar-ou-criar/", response_model=ClienteOut)
def buscar_ou_criar_cliente(
    telefone: str = Query(...),
    nome: str = Query(...),
    email: Optional[str] = Query(None),
    usuario: Usuario = Depends(exigir_permissao("clientes", "escrita")),
    cliente_service: ClienteService = Depends(get_cliente_service),
):
    """Busca ou cria cliente pelo telefone."""
    return cliente_service.buscar_ou_criar_cliente(
        telefone=telefone, nome=nome, usuario=usuario, email=email
    )


@router.get("/{cliente_id}", response_model=ClienteOut)
def obter_cliente(
    cliente_id: int,
    usuario: Usuario = Depends(exigir_permissao("clientes", "leitura")),
    cliente_service: ClienteService = Depends(get_cliente_service),
):
    """Obtém um cliente específico."""
    return cliente_service.obter_cliente(cliente_id, usuario)


@router.put("/{cliente_id}", response_model=ClienteOut)
def atualizar_cliente(
    cliente_id: int,
    dados: ClienteUpdate,
    usuario: Usuario = Depends(exigir_permissao("clientes", "escrita")),
    cliente_service: ClienteService = Depends(get_cliente_service),
):
    """Atualiza um cliente existente."""
    return cliente_service.atualizar_cliente(cliente_id, dados, usuario)


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_cliente(
    cliente_id: int,
    usuario: Usuario = Depends(exigir_permissao("clientes", "admin")),
    cliente_service: ClienteService = Depends(get_cliente_service),
):
    """Exclui um cliente."""
    cliente_service.excluir_cliente(cliente_id, usuario)
    return None
