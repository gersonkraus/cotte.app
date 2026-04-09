from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import os, logging

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.core.auth import hash_senha, get_superadmin
from app.services.audit_service import registrar_auditoria
from app.core.config import settings
from app.models.models import (
    Usuario,
    Empresa,
    Orcamento,
    Cliente,
    DocumentoEmpresa,
    Servico,
    Broadcast,
)
from app.schemas.schemas import (
    EmpresaAdminCreate,
    EmpresaAdminOut,
    EmpresaUpdate,
    UsuarioAdminCreate,
    UsuarioAdminOut,
    UsuarioEmpresaUpdate,
    SuperAdminSetup,
    AssinaturaUpdate,
    BroadcastCreate,
    BroadcastOut,
)
from app.services.plano_service import checar_limite_usuarios
from app.services.pricing_config import get_pricing_config, save_pricing_config
from app.services.admin_config import get_admin_config, save_admin_config
from app.services.plan_defaults_config import get_plan_defaults, save_plan_defaults
from app.services.r2_service import r2_service
from app.services.template_segmento_service import (
    admin_listar_templates,
    admin_criar_template,
    admin_atualizar_template,
    admin_deletar_template,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


EXTENSOES_LOGO = {".png", ".jpg", ".jpeg", ".webp"}


def _to_out(e: Empresa) -> EmpresaAdminOut:
    """Converte ORM Empresa → EmpresaAdminOut (inclui campos de assinatura)."""
    return EmpresaAdminOut(
        id=e.id,
        nome=e.nome,
        email=e.email,
        telefone=e.telefone,
        telefone_operador=e.telefone_operador,
        logo_url=e.logo_url,
        cor_primaria=e.cor_primaria,
        ativo=e.ativo,
        criado_em=e.criado_em,
        total_orcamentos=len(e.orcamentos),
        total_clientes=len(e.clientes),
        total_usuarios=len([u for u in e.usuarios if not u.is_superadmin]),
        total_mensagens_ia=int(e.total_mensagens_ia or 0),
        ultima_atividade_em=e.ultima_atividade_em,
        plano_id=e.plano_id,
        plano=e.plano or "trial",
        assinatura_valida_ate=e.assinatura_valida_ate,
        trial_ate=e.trial_ate,
        limite_orcamentos_custom=e.limite_orcamentos_custom,
        limite_usuarios_custom=e.limite_usuarios_custom,
        desativar_ia=e.desativar_ia,
        desativar_lembretes=e.desativar_lembretes,
        desativar_relatorios=e.desativar_relatorios,
        cupom_kiwify=e.cupom_kiwify,
    )


def _to_out_with_counts(
    e: Empresa, total_orcamentos: int, total_clientes: int, total_usuarios: int
) -> EmpresaAdminOut:
    return EmpresaAdminOut(
        id=e.id,
        nome=e.nome,
        email=e.email,
        telefone=e.telefone,
        telefone_operador=e.telefone_operador,
        logo_url=e.logo_url,
        cor_primaria=e.cor_primaria,
        ativo=e.ativo,
        criado_em=e.criado_em,
        total_orcamentos=int(total_orcamentos or 0),
        total_clientes=int(total_clientes or 0),
        total_usuarios=int(total_usuarios or 0),
        total_mensagens_ia=int(e.total_mensagens_ia or 0),
        ultima_atividade_em=e.ultima_atividade_em,
        plano_id=e.plano_id,
        plano=e.plano or "trial",
        assinatura_valida_ate=e.assinatura_valida_ate,
        trial_ate=e.trial_ate,
        limite_orcamentos_custom=e.limite_orcamentos_custom,
        limite_usuarios_custom=e.limite_usuarios_custom,
        desativar_ia=e.desativar_ia,
        desativar_lembretes=e.desativar_lembretes,
        desativar_relatorios=e.desativar_relatorios,
        cupom_kiwify=e.cupom_kiwify,
    )


# ── SETUP INICIAL ──────────────────────────────────────────────────────────


@router.post(
    "/setup", status_code=201, summary="Cria o primeiro superadmin (use uma vez)"
)
def setup_superadmin(dados: SuperAdminSetup, db: Session = Depends(get_db)):
    """Endpoint de uso único para criar o superadmin. Protegido por setup_key."""
    if dados.setup_key != settings.ADMIN_SETUP_KEY:
        raise HTTPException(status_code=403, detail="Chave de setup inválida")

    if db.query(Usuario).filter(Usuario.is_superadmin == True).first():
        raise HTTPException(status_code=400, detail="Superadmin já existe")

    # Cria empresa-raiz para o superadmin
    empresa = Empresa(nome="COTTE — Admin", ativo=True)
    db.add(empresa)
    db.flush()

    usuario = Usuario(
        empresa_id=empresa.id,
        nome=dados.nome,
        email=dados.email,
        senha_hash=hash_senha(dados.senha),
        is_superadmin=True,
        ativo=True,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return {"status": "ok", "usuario_id": usuario.id, "empresa_id": empresa.id}


# ── DASHBOARD ─────────────────────────────────────────────────────────────


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), current_user=Depends(get_superadmin)):
    """Retorna estatísticas gerais do painel admin."""
    # Log para depuração
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"Superadmin acessando dashboard: usuario_id={current_user.id}")

    total_empresas = db.query(Empresa).filter(Empresa.ativo == True).count()
    total_usuarios = (
        db.query(Usuario)
        .filter(Usuario.ativo == True, Usuario.is_superadmin == False)
        .count()
    )
    total_orcamentos = db.query(func.count(Orcamento.id)).scalar() or 0
    total_clientes = db.query(func.count(Cliente.id)).scalar() or 0

    # Soma total de mensagens IA de todas as empresas
    try:
        total_ia = db.query(func.sum(Empresa.total_mensagens_ia)).scalar() or 0
    except Exception as e:
        logger.warning(f"Erro ao somar mensagens IA (coluna pode faltar): {e}")
        total_ia = 0

    logger.info(
        f"Dashboard stats: empresas={total_empresas}, usuarios={total_usuarios}, orcamentos={total_orcamentos}, clientes={total_clientes}, ia={total_ia}"
    )

    return {
        "total_empresas": total_empresas,
        "total_usuarios": total_usuarios,
        "total_orcamentos": total_orcamentos,
        "total_clientes": total_clientes,
        "total_ia": int(total_ia or 0),
    }


# ── EMPRESAS ──────────────────────────────────────────────────────────────


@router.get("/empresas", response_model=List[EmpresaAdminOut])
def listar_empresas(
    db: Session = Depends(get_db), current_user=Depends(get_superadmin)
):
    """Lista todas as empresas com contagem de orçamentos, clientes e usuários."""
    # Log para depuração
    import logging

    logger = logging.getLogger(__name__)
    logger.info(
        f"Superadmin acessando listar_empresas: usuario_id={current_user.id}, email={current_user.email}"
    )

    orc_sq = (
        db.query(
            Orcamento.empresa_id.label("empresa_id"),
            func.count(Orcamento.id).label("total_orcamentos"),
        )
        .group_by(Orcamento.empresa_id)
        .subquery()
    )

    cli_sq = (
        db.query(
            Cliente.empresa_id.label("empresa_id"),
            func.count(Cliente.id).label("total_clientes"),
        )
        .group_by(Cliente.empresa_id)
        .subquery()
    )

    usr_sq = (
        db.query(
            Usuario.empresa_id.label("empresa_id"),
            func.count(Usuario.id).label("total_usuarios"),
        )
        .filter(Usuario.is_superadmin == False)
        .group_by(Usuario.empresa_id)
        .subquery()
    )

    rows = (
        db.query(
            Empresa,
            orc_sq.c.total_orcamentos,
            cli_sq.c.total_clientes,
            usr_sq.c.total_usuarios,
        )
        .outerjoin(orc_sq, Empresa.id == orc_sq.c.empresa_id)
        .outerjoin(cli_sq, Empresa.id == cli_sq.c.empresa_id)
        .outerjoin(usr_sq, Empresa.id == usr_sq.c.empresa_id)
        .order_by(Empresa.criado_em.desc())
        .all()
    )

    logger.info(f"Total de empresas encontradas: {len(rows)}")
    return [_to_out_with_counts(e, o, c, u) for (e, o, c, u) in rows]


@router.post("/empresas", response_model=EmpresaAdminOut, status_code=201)
def criar_empresa(
    dados: EmpresaAdminCreate, db: Session = Depends(get_db), _=Depends(get_superadmin)
):
    """Cria uma nova empresa com seu primeiro usuário gestor."""
    if (
        db.query(Usuario)
        .filter(func.lower(Usuario.email) == dados.usuario_email)
        .first()
    ):
        raise HTTPException(status_code=400, detail="E-mail do usuário já cadastrado")

    empresa = Empresa(
        nome=dados.nome,
        email=dados.email,
        telefone=dados.telefone,
        telefone_operador=dados.telefone_operador,
        cor_primaria=dados.cor_primaria,
        ativo=True,
    )
    db.add(empresa)
    db.flush()

    usuario = Usuario(
        empresa_id=empresa.id,
        nome=dados.usuario_nome,
        email=dados.usuario_email,
        senha_hash=hash_senha(dados.usuario_senha),
        ativo=True,
        is_gestor=True,  # primeiro usuário da empresa criado pelo admin é gestor
    )
    db.add(usuario)
    db.commit()
    db.refresh(empresa)
    return _to_out(empresa)


@router.patch("/empresas/{empresa_id}", response_model=EmpresaAdminOut)
def editar_empresa(
    empresa_id: int,
    dados: EmpresaUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Edita os dados de uma empresa existente."""
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(empresa, campo, valor)
    db.commit()
    db.refresh(empresa)
    return _to_out(empresa)


@router.patch("/empresas/{empresa_id}/toggle-ativo")
def toggle_empresa_ativo(
    empresa_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Ativa ou desativa uma empresa."""
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    empresa.ativo = not empresa.ativo
    db.commit()
    return {"id": empresa.id, "ativo": empresa.ativo}


@router.post("/empresas/{empresa_id}/impersonate")
def impersonate_empresa(
    empresa_id: int,
    request: Request,
    db: Session = Depends(get_db),
    superadmin=Depends(get_superadmin),
):
    """
    Superadmin entra como empresa: autentica como um usuário ativo da empresa.
    Prioriza gestor ativo; se não houver, usa o primeiro usuário ativo.
    """
    from app.core.auth import criar_token

    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    # 1. Busca gestor ativo
    usuario = (
        db.query(Usuario)
        .filter(
            Usuario.empresa_id == empresa_id,
            Usuario.ativo == True,
            Usuario.is_gestor == True,
            Usuario.is_superadmin == False,
        )
        .order_by(Usuario.id.asc())
        .first()
    )

    # 2. Se não houver gestor, busca primeiro usuário ativo
    if not usuario:
        usuario = (
            db.query(Usuario)
            .filter(
                Usuario.empresa_id == empresa_id,
                Usuario.ativo == True,
                Usuario.is_superadmin == False,
            )
            .order_by(Usuario.id.asc())
            .first()
        )

    if not usuario:
        raise HTTPException(
            status_code=400, detail="Empresa não possui usuários ativos para simulação"
        )

    logger.warning(
        f"[IMPERSONATE] superadmin_id={superadmin.id} email={superadmin.email} "
        f"entrou como usuario_id={usuario.id} email={usuario.email} "
        f"empresa_id={empresa_id} empresa={empresa.nome}"
    )
    registrar_auditoria(
        db=db,
        usuario=superadmin,
        acao="admin_impersonate",
        recurso="empresa",
        recurso_id=str(empresa_id),
        detalhes={
            "empresa_nome": empresa.nome,
            "usuario_alvo_id": usuario.id,
            "usuario_alvo_email": usuario.email,
        },
        request=request,
    )

    token = criar_token(
        {
            "sub": str(usuario.id),
            "empresa_id": usuario.empresa_id,
            "v": usuario.token_versao,
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": {
            "id": usuario.id,
            "nome": usuario.nome,
            "email": usuario.email,
            "empresa_id": usuario.empresa_id,
            "empresa_nome": empresa.nome,
        },
    }


@router.delete("/empresas/{empresa_id}", status_code=204)
def deletar_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Remove uma empresa que não possui orçamentos."""
    from app.models.models import Cliente, ItemOrcamento, Orcamento

    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    if len(empresa.orcamentos) > 0:
        raise HTTPException(
            status_code=400,
            detail="Empresa possui orçamentos. Desative ao invés de excluir.",
        )

    # Remove logo do disco se existir
    if empresa.logo_url:
        caminho = empresa.logo_url.lstrip("/")
        if os.path.exists(caminho):
            os.remove(caminho)

    # Remove usuários e clientes antes de deletar a empresa
    db.query(Usuario).filter(Usuario.empresa_id == empresa_id).delete()
    db.query(Cliente).filter(Cliente.empresa_id == empresa_id).delete()
    db.delete(empresa)
    db.commit()


@router.post("/empresas/{empresa_id}/logo", response_model=EmpresaAdminOut)
async def upload_logo_empresa_admin(
    empresa_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Superadmin envia ou altera a logo de uma empresa."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in EXTENSOES_LOGO:
        raise HTTPException(
            status_code=400,
            detail=f"Formato não permitido. Use: {', '.join(EXTENSOES_LOGO)}",
        )

    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    if empresa.logo_url:
        r2_service.delete_file(empresa.logo_url)

    mime_type = file.content_type or "image/png"
    file_url = r2_service.upload_file(
        file_obj=file.file,
        empresa_id=empresa_id,
        tipo="logos",
        extensao=ext,
        content_type=mime_type,
    )

    empresa.logo_url = file_url
    db.commit()
    db.refresh(empresa)
    return _to_out(empresa)


@router.delete("/empresas/{empresa_id}/logo", response_model=EmpresaAdminOut)
def remover_logo_empresa_admin(
    empresa_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Superadmin remove a logo de uma empresa."""
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    if empresa.logo_url:
        r2_service.delete_file(empresa.logo_url)
        empresa.logo_url = None
        db.commit()
        db.refresh(empresa)
    return _to_out(empresa)


# ── ASSINATURA ─────────────────────────────────────────────────────────────


@router.patch("/empresas/{empresa_id}/assinatura")
def atualizar_assinatura(
    empresa_id: int,
    dados: AssinaturaUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Define plano, validade e ativa/desativa a empresa."""
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    if dados.plano is not None:
        empresa.plano = dados.plano

    if dados.plano_id is not None:
        empresa.plano_id = dados.plano_id

    empresa.assinatura_valida_ate = dados.assinatura_valida_ate
    if dados.ativo is not None:
        empresa.ativo = dados.ativo
    db.commit()
    return {
        "id": empresa.id,
        "plano": empresa.plano,
        "plano_id": empresa.plano_id,
        "assinatura_valida_ate": empresa.assinatura_valida_ate,
        "ativo": empresa.ativo,
    }


# ── USUÁRIOS POR EMPRESA ───────────────────────────────────────────────────


@router.get("/empresas/{empresa_id}/usuarios", response_model=List[UsuarioAdminOut])
def listar_usuarios_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Lista os usuários de uma empresa específica."""
    return (
        db.query(Usuario)
        .filter(
            Usuario.empresa_id == empresa_id,
            Usuario.is_superadmin == False,
        )
        .order_by(Usuario.nome)
        .all()
    )


@router.post(
    "/empresas/{empresa_id}/usuarios", response_model=UsuarioAdminOut, status_code=201
)
def criar_usuario_empresa(
    empresa_id: int,
    dados: UsuarioAdminCreate,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Cria um novo usuário vinculado a uma empresa."""
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    # Respeita limites do plano também na criação via painel admin
    checar_limite_usuarios(db, empresa)

    if db.query(Usuario).filter(func.lower(Usuario.email) == dados.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    usuario = Usuario(
        empresa_id=empresa_id,
        nome=dados.nome,
        email=dados.email,
        senha_hash=hash_senha(dados.senha),
        ativo=True,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.patch("/usuarios/{usuario_id}/toggle-ativo")
def toggle_usuario_ativo(
    usuario_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Ativa ou desativa um usuário."""
    usuario = (
        db.query(Usuario)
        .filter(Usuario.id == usuario_id, Usuario.is_superadmin == False)
        .first()
    )
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    usuario.ativo = not usuario.ativo
    db.commit()
    return {"id": usuario.id, "ativo": usuario.ativo}


@router.patch("/usuarios/{usuario_id}", response_model=UsuarioAdminOut)
def atualizar_usuario_admin(
    usuario_id: int,
    dados: UsuarioEmpresaUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Superadmin altera o cadastro de um usuário (nome, e-mail, senha)."""
    usuario = (
        db.query(Usuario)
        .filter(Usuario.id == usuario_id, Usuario.is_superadmin == False)
        .first()
    )
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    payload = dados.model_dump(exclude_unset=True)
    if "email" in payload and payload["email"]:
        outro = (
            db.query(Usuario)
            .filter(
                func.lower(Usuario.email) == payload["email"], Usuario.id != usuario_id
            )
            .first()
        )
        if outro:
            raise HTTPException(
                status_code=400, detail="E-mail já está em uso por outro usuário"
            )
    if "senha" in payload and payload["senha"]:
        payload["senha_hash"] = hash_senha(payload.pop("senha"))

    for campo, valor in payload.items():
        if campo != "senha_hash" and hasattr(usuario, campo):
            setattr(usuario, campo, valor)
    if "senha_hash" in payload:
        usuario.senha_hash = payload["senha_hash"]

    db.commit()
    db.refresh(usuario)
    return usuario


@router.delete("/usuarios/{usuario_id}", status_code=204)
def deletar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Remove um usuário não superadmin."""
    usuario = (
        db.query(Usuario)
        .filter(Usuario.id == usuario_id, Usuario.is_superadmin == False)
        .first()
    )
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    db.delete(usuario)
    db.commit()


# ── CONFIG: PLANOS / PRICING DA LANDING ───────────────────────────────────────


@router.get("/pricing")
def get_pricing_admin(_=Depends(get_superadmin)):
    """Retorna a configuração de preços/limites usada na landing."""
    return get_pricing_config()


@router.put("/pricing")
def update_pricing_admin(payload: dict, _=Depends(get_superadmin)):
    """
    Atualiza a configuração de planos/preços usada na landing.
    Espera um objeto com chaves starter/pro/business e campos:
    { preco: number, orcamentos: number|null, usuarios: number|null }.
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload inválido.")
    cfg = save_pricing_config(payload)
    return cfg


# ── LIMITES PADRÃO DOS PLANOS (backend) ─────────────────────────────────────


@router.get("/plan-defaults")
def get_plan_defaults_admin(_=Depends(get_superadmin)):
    """Retorna os limites padrão de orçamentos e usuários por plano (trial, starter, pro, business)."""
    return get_plan_defaults()


@router.put("/plan-defaults")
def update_plan_defaults_admin(payload: dict, _=Depends(get_superadmin)):
    """
    Atualiza os limites padrão de cada plano.
    Payload: { trial: { limite_orcamentos, limite_usuarios }, starter, pro, business }.
    Use null ou omita para ilimitado (ex.: business).
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload inválido.")
    return save_plan_defaults(payload)


# ── CONFIGURAÇÕES GLOBAIS DO ADMIN ──────────────────────────────────────────


@router.get("/config")
def get_config_admin(db: Session = Depends(get_db), _=Depends(get_superadmin)):
    """Retorna as configurações globais do admin (ex: números para monitoramento)."""
    return get_admin_config(db)


@router.put("/config")
def update_config_admin(
    payload: dict, db: Session = Depends(get_db), _=Depends(get_superadmin)
):
    """Atualiza as configurações globais do admin."""
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload inválido.")
    return save_admin_config(payload, db)


@router.post("/migrar-urls-r2")
def migrar_urls_r2(db: Session = Depends(get_db), _=Depends(get_superadmin)):
    """
    Migra URLs do R2 de storage interno para URL pública.
    Endpoint temporário para corrigir arquivos salvos antes da configuração de R2_PUBLIC_URL.
    """
    if not settings.R2_PUBLIC_URL:
        raise HTTPException(
            status_code=400,
            detail="R2_PUBLIC_URL não está configurada. Configure a variável de ambiente primeiro.",
        )

    public_url = settings.R2_PUBLIC_URL.rstrip("/")
    storage_pattern = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

    resultado = {
        "storage_pattern": storage_pattern,
        "public_url": public_url,
        "documentos": 0,
        "servicos": 0,
        "empresas": 0,
        "total": 0,
    }

    # Migrar documentos
    documentos = (
        db.query(DocumentoEmpresa)
        .filter(DocumentoEmpresa.arquivo_path.like(f"{storage_pattern}%"))
        .all()
    )

    for doc in documentos:
        doc.arquivo_path = doc.arquivo_path.replace(storage_pattern, public_url)

    resultado["documentos"] = len(documentos)

    # Migrar imagens de serviços
    servicos = (
        db.query(Servico).filter(Servico.imagem_url.like(f"{storage_pattern}%")).all()
    )

    for srv in servicos:
        srv.imagem_url = srv.imagem_url.replace(storage_pattern, public_url)

    resultado["servicos"] = len(servicos)

    # Migrar logos de empresas
    empresas = (
        db.query(Empresa).filter(Empresa.logo_url.like(f"{storage_pattern}%")).all()
    )

    for emp in empresas:
        emp.logo_url = emp.logo_url.replace(storage_pattern, public_url)

    resultado["empresas"] = len(empresas)
    resultado["total"] = (
        resultado["documentos"] + resultado["servicos"] + resultado["empresas"]
    )

    db.commit()

    return {
        "success": True,
        "message": f"Migração concluída! {resultado['total']} arquivos atualizados.",
        "detalhes": resultado,
    }


# ── BROADCASTS ──────────────────────────────────────────────────────────────


@router.get("/broadcasts", response_model=List[BroadcastOut])
def listar_broadcasts(db: Session = Depends(get_db), _=Depends(get_superadmin)):
    """Lista todos os broadcasts (ativos e inativos)."""
    return db.query(Broadcast).order_by(Broadcast.criado_em.desc()).all()


@router.post("/broadcasts", response_model=BroadcastOut, status_code=201)
def criar_broadcast(
    dados: BroadcastCreate,
    db: Session = Depends(get_db),
    superadmin=Depends(get_superadmin),
):
    """Cria um novo broadcast que será exibido no dashboard das empresas."""
    broadcast = Broadcast(
        mensagem=dados.mensagem,
        tipo=dados.tipo,
        ativo=True,
        criado_por_id=superadmin.id,
        expira_em=dados.expira_em,
    )
    db.add(broadcast)
    db.commit()
    db.refresh(broadcast)
    return broadcast


@router.delete("/broadcasts/{broadcast_id}", status_code=204)
def deletar_broadcast(
    broadcast_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Remove um broadcast."""
    broadcast = db.query(Broadcast).filter(Broadcast.id == broadcast_id).first()
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast não encontrado")
    db.delete(broadcast)
    db.commit()


@router.patch("/broadcasts/{broadcast_id}/toggle-ativo")
def toggle_broadcast_ativo(
    broadcast_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Ativa/desativa um broadcast."""
    broadcast = db.query(Broadcast).filter(Broadcast.id == broadcast_id).first()
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast não encontrado")
    broadcast.ativo = not broadcast.ativo
    db.commit()
    return {"id": broadcast.id, "ativo": broadcast.ativo}


# ── ADMIN: MODELOS DE CATÁLOGO ───────────────────────────────────────────────


@router.get("/catalogo/templates")
def listar_templates_admin(_=Depends(get_superadmin)):
    """Lista todos os templates de catálogo (padrão + custom)."""
    return admin_listar_templates()


@router.post("/catalogo/templates", status_code=201)
def criar_template_admin(payload: dict, _=Depends(get_superadmin)):
    """Cria um novo template custom."""
    slug = payload.get("slug", "").strip().lower().replace(" ", "-")
    if not slug or not payload.get("nome"):
        raise HTTPException(status_code=400, detail="slug e nome são obrigatórios")
    try:
        return admin_criar_template(slug, payload)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.put("/catalogo/templates/{slug}")
def atualizar_template_admin(slug: str, payload: dict, _=Depends(get_superadmin)):
    """Atualiza um template custom."""
    try:
        return admin_atualizar_template(slug, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/catalogo/templates/{slug}", status_code=204)
def deletar_template_admin(slug: str, _=Depends(get_superadmin)):
    """Deleta um template custom."""
    try:
        admin_deletar_template(slug)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
