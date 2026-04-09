from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import re

from app.core.database import get_db
from app.core.auth import get_usuario_atual
from app.models.models import Empresa, ModuloSistema, Papel, Plano, Usuario
from app.schemas.schemas import (
    AtribuirPapelRequest,
    ModuloComAcoes,
    PapelCreate,
    PapelOut,
    PapelUpdate,
)

router = APIRouter(prefix="/papeis", tags=["Papéis"])


def _slugify(text: str) -> str:
    """Gera slug a partir do nome."""
    slug = text.lower().strip()
    slug = re.sub(r"[àáâãä]", "a", slug)
    slug = re.sub(r"[èéêë]", "e", slug)
    slug = re.sub(r"[ìíîï]", "i", slug)
    slug = re.sub(r"[òóôõö]", "o", slug)
    slug = re.sub(r"[ùúûü]", "u", slug)
    slug = re.sub(r"[ç]", "c", slug)
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug


def _exigir_gestor(usuario: Usuario = Depends(get_usuario_atual)) -> Usuario:
    """Exige que o usuário seja gestor ou superadmin."""
    if not usuario.is_superadmin and not usuario.is_gestor:
        raise HTTPException(status_code=403, detail="Apenas gestores podem gerenciar papéis.")
    return usuario


def _modulos_do_plano(empresa: Empresa, db: Session) -> list[ModuloSistema]:
    """Retorna módulos disponíveis para a empresa (via plano_id ou todos se não tiver plano)."""
    if empresa.plano_id:
        plano = db.query(Plano).filter(Plano.id == empresa.plano_id).first()
        if plano:
            return plano.modulos
    # Sem plano_id: retorna todos os módulos ativos
    return db.query(ModuloSistema).filter(ModuloSistema.ativo == True).all()


@router.get("/modulos-disponiveis", response_model=List[ModuloComAcoes])
def listar_modulos_disponiveis(
    current_user: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    """Lista módulos do plano da empresa com suas ações — usado pelo frontend de papéis."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    modulos = _modulos_do_plano(empresa, db)
    return [
        ModuloComAcoes(
            id=m.id,
            nome=m.nome,
            slug=m.slug,
            acoes=m.acoes or ["leitura", "escrita", "exclusao", "admin"],
        )
        for m in modulos
    ]


@router.get("", response_model=List[PapelOut])
def listar_papeis(
    current_user: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    """Lista papéis da empresa do usuário logado."""
    papeis = (
        db.query(Papel)
        .filter(Papel.empresa_id == current_user.empresa_id, Papel.ativo == True)
        .order_by(Papel.nome)
        .all()
    )
    return papeis


@router.get("/{papel_id}", response_model=PapelOut)
def detalhe_papel(
    papel_id: int,
    current_user: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    papel = (
        db.query(Papel)
        .filter(Papel.id == papel_id, Papel.empresa_id == current_user.empresa_id)
        .first()
    )
    if not papel:
        raise HTTPException(status_code=404, detail="Papel não encontrado.")
    return papel


@router.post("", response_model=PapelOut, status_code=201)
def criar_papel(
    dados: PapelCreate,
    current_user: Usuario = Depends(_exigir_gestor),
    db: Session = Depends(get_db),
):
    slug = _slugify(dados.nome)

    # Validar slug único na empresa
    existente = (
        db.query(Papel)
        .filter(Papel.empresa_id == current_user.empresa_id, Papel.slug == slug)
        .first()
    )
    if existente:
        raise HTTPException(status_code=400, detail=f"Já existe um papel com o nome '{dados.nome}'.")

    # Validar permissões: apenas módulos disponíveis e ações existentes
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    modulos_disponiveis = {m.slug: (m.acoes or []) for m in _modulos_do_plano(empresa, db)}

    for perm in dados.permissoes:
        try:
            mod, acao = perm.split(":", 1)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Permissão inválida: '{perm}'. Use formato 'modulo:acao'.")
        if mod not in modulos_disponiveis:
            raise HTTPException(status_code=400, detail=f"Módulo '{mod}' não está disponível no plano da empresa.")
        if acao not in modulos_disponiveis[mod]:
            raise HTTPException(status_code=400, detail=f"Ação '{acao}' não é válida para o módulo '{mod}'.")

    # Se is_default=True, remover is_default dos outros papéis
    if dados.is_default:
        db.query(Papel).filter(
            Papel.empresa_id == current_user.empresa_id,
            Papel.is_default == True,
        ).update({"is_default": False})

    papel = Papel(
        empresa_id=current_user.empresa_id,
        nome=dados.nome,
        slug=slug,
        descricao=dados.descricao,
        permissoes=dados.permissoes,
        is_default=dados.is_default,
        is_sistema=False,
        ativo=True,
    )
    db.add(papel)
    db.commit()
    db.refresh(papel)
    return papel


@router.put("/{papel_id}", response_model=PapelOut)
def atualizar_papel(
    papel_id: int,
    dados: PapelUpdate,
    current_user: Usuario = Depends(_exigir_gestor),
    db: Session = Depends(get_db),
):
    papel = (
        db.query(Papel)
        .filter(Papel.id == papel_id, Papel.empresa_id == current_user.empresa_id)
        .first()
    )
    if not papel:
        raise HTTPException(status_code=404, detail="Papel não encontrado.")

    # Papéis sistema: pode editar permissões, mas não nome/slug
    if papel.is_sistema and dados.nome is not None and dados.nome != papel.nome:
        raise HTTPException(status_code=400, detail="Papéis do sistema não podem ser renomeados.")

    if dados.nome is not None and not papel.is_sistema:
        novo_slug = _slugify(dados.nome)
        if novo_slug != papel.slug:
            existente = (
                db.query(Papel)
                .filter(
                    Papel.empresa_id == current_user.empresa_id,
                    Papel.slug == novo_slug,
                    Papel.id != papel_id,
                )
                .first()
            )
            if existente:
                raise HTTPException(status_code=400, detail=f"Já existe um papel com o nome '{dados.nome}'.")
            papel.nome = dados.nome
            papel.slug = novo_slug

    if dados.permissoes is not None:
        empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
        modulos_disponiveis = {m.slug: (m.acoes or []) for m in _modulos_do_plano(empresa, db)}
        for perm in dados.permissoes:
            try:
                mod, acao = perm.split(":", 1)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Permissão inválida: '{perm}'.")
            if mod not in modulos_disponiveis:
                raise HTTPException(status_code=400, detail=f"Módulo '{mod}' não está disponível no plano.")
            if acao not in modulos_disponiveis[mod]:
                raise HTTPException(status_code=400, detail=f"Ação '{acao}' inválida para '{mod}'.")
        papel.permissoes = dados.permissoes

    if dados.descricao is not None:
        papel.descricao = dados.descricao

    if dados.is_default is not None:
        if dados.is_default:
            db.query(Papel).filter(
                Papel.empresa_id == current_user.empresa_id,
                Papel.is_default == True,
                Papel.id != papel_id,
            ).update({"is_default": False})
        papel.is_default = dados.is_default

    if dados.ativo is not None:
        papel.ativo = dados.ativo

    db.commit()
    db.refresh(papel)
    return papel


@router.delete("/{papel_id}", status_code=204)
def desativar_papel(
    papel_id: int,
    current_user: Usuario = Depends(_exigir_gestor),
    db: Session = Depends(get_db),
):
    papel = (
        db.query(Papel)
        .filter(Papel.id == papel_id, Papel.empresa_id == current_user.empresa_id)
        .first()
    )
    if not papel:
        raise HTTPException(status_code=404, detail="Papel não encontrado.")

    if papel.is_sistema:
        raise HTTPException(status_code=400, detail="Papéis do sistema não podem ser excluídos.")

    # Verificar se tem usuários ativos
    usuarios_com_papel = (
        db.query(Usuario)
        .filter(Usuario.papel_id == papel_id, Usuario.ativo == True)
        .all()
    )
    if usuarios_com_papel:
        nomes = ", ".join(u.nome for u in usuarios_com_papel[:5])
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível excluir: papel em uso por {len(usuarios_com_papel)} usuário(s): {nomes}.",
        )

    papel.ativo = False
    db.commit()


@router.put("/{papel_id}/usuarios/{usuario_id}", response_model=dict)
def atribuir_papel_a_usuario(
    papel_id: int,
    usuario_id: int,
    current_user: Usuario = Depends(_exigir_gestor),
    db: Session = Depends(get_db),
):
    """Atribui um papel a um usuário da mesma empresa."""
    papel = (
        db.query(Papel)
        .filter(Papel.id == papel_id, Papel.empresa_id == current_user.empresa_id)
        .first()
    )
    if not papel:
        raise HTTPException(status_code=404, detail="Papel não encontrado.")

    usuario = (
        db.query(Usuario)
        .filter(Usuario.id == usuario_id, Usuario.empresa_id == current_user.empresa_id)
        .first()
    )
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    usuario.papel_id = papel_id
    db.commit()
    return {"ok": True, "usuario_id": usuario_id, "papel_id": papel_id}
