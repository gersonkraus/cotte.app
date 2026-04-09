from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, func as _func
from typing import List
import os, shutil, uuid, logging

from app.core.database import get_db
from app.core.auth import get_usuario_atual, hash_senha, exigir_permissao
from app.services.audit_service import registrar_auditoria
from app.models.models import Usuario, Empresa, BancoPIXEmpresa, Orcamento, Notificacao
from app.schemas.schemas import (
    EmpresaOut,
    EmpresaSidebarOut,
    EmpresaUpdate,
    EmpresaUsoOut,
    UsuarioAdminCreate,
    UsuarioAdminOut,
    UsuarioEmpresaUpdate,
    WhatsAppStatusOut,
    BancoPIXOut,
    BancoPIXCreate,
    BancoPIXUpdate,
)
from app.services.plano_service import (
    checar_limite_usuarios,
    whatsapp_proprio_habilitado,
    exigir_whatsapp_proprio,
    _config_for_empresa,
)
from app.core.config import settings
from app.services.r2_service import r2_service

router = APIRouter(prefix="/empresa", tags=["Empresa"])

logger = logging.getLogger(__name__)

LOGO_DIR = "static/logos"
os.makedirs(LOGO_DIR, exist_ok=True)

EXTENSOES_PERMITIDAS = {".png", ".jpg", ".jpeg", ".webp"}


def _erro_instancia_inexistente(error_text: str | None) -> bool:
    txt = (error_text or "").lower()
    return (
        "not found" in txt
        or "instance not found" in txt
        or "instance does not exist" in txt
        or "no instance" in txt
        or '"status":404' in txt
    )


@router.get("/", response_model=EmpresaOut)
def get_empresa(
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    """Retorna os dados da empresa do usuário logado."""
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return empresa


@router.get("/uso", response_model=EmpresaUsoOut)
def get_empresa_uso(
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    """Retorna o uso de recursos (orçamentos, usuários) da empresa."""
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    cfg = _config_for_empresa(empresa)

    lim_orc = (
        empresa.limite_orcamentos_custom
        if empresa.limite_orcamentos_custom is not None
        else cfg.get("limite_orcamentos_total")
    )
    lim_usr = (
        empresa.limite_usuarios_custom
        if empresa.limite_usuarios_custom is not None
        else cfg.get("limite_usuarios")
    )

    orc_usados = (
        db.query(_func.count(Orcamento.id))
        .filter(Orcamento.empresa_id == empresa.id)
        .scalar()
        or 0
    )

    usr_usados = (
        db.query(_func.count(Usuario.id))
        .filter(
            Usuario.empresa_id == empresa.id,
            Usuario.is_superadmin == False,
        )
        .scalar()
        or 0
    )

    return EmpresaUsoOut(
        plano=empresa.plano or "trial",
        nome_plano=cfg.get("nome_exibicao", empresa.plano or "trial"),
        orcamentos_usados=orc_usados,
        orcamentos_limite=lim_orc,
        usuarios_usados=usr_usados,
        usuarios_limite=lim_usr,
        assinatura_valida_ate=empresa.assinatura_valida_ate,
        trial_ate=empresa.trial_ate,
        ativo=empresa.ativo if empresa.ativo is not None else True,
    )


@router.get("/resumo-sidebar")
def get_resumo_sidebar(
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    """Retorna em uma única chamada os dados necessários para a sidebar: empresa, uso do plano e contagem de notificações."""
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    cfg = _config_for_empresa(empresa)

    lim_orc = (
        empresa.limite_orcamentos_custom
        if empresa.limite_orcamentos_custom is not None
        else cfg.get("limite_orcamentos_total")
    )
    lim_usr = (
        empresa.limite_usuarios_custom
        if empresa.limite_usuarios_custom is not None
        else cfg.get("limite_usuarios")
    )

    orc_usados = (
        db.query(_func.count(Orcamento.id))
        .filter(Orcamento.empresa_id == empresa.id)
        .scalar()
        or 0
    )
    usr_usados = (
        db.query(_func.count(Usuario.id))
        .filter(
            Usuario.empresa_id == empresa.id,
            Usuario.is_superadmin == False,
        )
        .scalar()
        or 0
    )
    notif_count = (
        db.query(_func.count(Notificacao.id))
        .filter(
            Notificacao.empresa_id == empresa.id,
            Notificacao.lida == False,
        )
        .scalar()
        or 0
    )

    return {
        "empresa": EmpresaSidebarOut.model_validate(empresa),
        "uso": EmpresaUsoOut(
            plano=empresa.plano or "trial",
            nome_plano=cfg.get("nome_exibicao", empresa.plano or "trial"),
            orcamentos_usados=orc_usados,
            orcamentos_limite=lim_orc,
            usuarios_usados=usr_usados,
            usuarios_limite=lim_usr,
            assinatura_valida_ate=empresa.assinatura_valida_ate,
            trial_ate=empresa.trial_ate,
            ativo=empresa.ativo if empresa.ativo is not None else True,
        ),
        "notificacoes_nao_lidas": notif_count,
    }


@router.patch("/", response_model=EmpresaOut)
def atualizar_empresa(
    dados: EmpresaUpdate,
    usuario: Usuario = Depends(exigir_permissao("configuracoes", "escrita")),
    db: Session = Depends(get_db),
):
    """Atualiza os dados da empresa do usuário logado."""
    try:
        empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
        if not empresa:
            logger.error(f"[DB] Empresa {usuario.empresa_id} não encontrada para o usuário {usuario.id}")
            raise HTTPException(status_code=404, detail="Empresa não encontrada")

        update_data = dados.model_dump(exclude_unset=True)
        logger.info(f"[DB] PATCH /empresa/ - Empresa {empresa.id}. Dados: {update_data}")

        for campo, valor in update_data.items():
            if hasattr(empresa, campo):
                logger.info(f"[DB] Campo '{campo}': {getattr(empresa, campo)} -> {valor}")
                setattr(empresa, campo, valor)
            else:
                logger.warning(f"[DB] Campo '{campo}' enviado no PATCH mas não existe no modelo Empresa.")

        db.add(empresa) # Força o objeto no tracking da sessão
        db.commit()
        db.refresh(empresa)
        
        # Verificação pós-commit
        valor_final = getattr(empresa, "enviar_pdf_whatsapp", "N/A")
        logger.info(f"[DB] Empresa {empresa.id} salva. Valor final de enviar_pdf_whatsapp no banco: {valor_final}")
        return empresa
    except Exception as e:
        db.rollback()
        import traceback
        err_msg = traceback.format_exc()
        logger.error(f"[DB] ERRO CRÍTICO ao atualizar empresa {usuario.empresa_id}:\n{err_msg}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erro interno no servidor ao salvar configurações: {str(e)}"
        )


@router.post("/logo", response_model=EmpresaOut)
async def upload_logo(
    file: UploadFile = File(...),
    usuario: Usuario = Depends(exigir_permissao("configuracoes", "escrita")),
    db: Session = Depends(get_db),
):
    """Faz upload da logo da empresa (PNG, JPG, JPEG ou WEBP)."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in EXTENSOES_PERMITIDAS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato não permitido. Use: {', '.join(EXTENSOES_PERMITIDAS)}",
        )

    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()

    # Remove logo anterior se existir
    if empresa.logo_url:
        r2_service.delete_file(empresa.logo_url)

    # Upload para R2
    mime_type = file.content_type or "image/png"
    file_url = r2_service.upload_file(
        file_obj=file.file,
        empresa_id=usuario.empresa_id,
        tipo="logos",
        extensao=ext,
        content_type=mime_type,
    )

    empresa.logo_url = file_url
    db.commit()
    db.refresh(empresa)
    return empresa


@router.delete("/logo", response_model=EmpresaOut)
def remover_logo(
    usuario: Usuario = Depends(exigir_permissao("configuracoes", "escrita")),
    db: Session = Depends(get_db),
):
    """Remove a logo da empresa."""
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    if empresa.logo_url:
        r2_service.delete_file(empresa.logo_url)
        empresa.logo_url = None
        db.commit()
        db.refresh(empresa)
    return empresa


# ── USUÁRIOS DA EMPRESA (a empresa cadastra mais usuários) ─────────────────


@router.get("/usuarios", response_model=List[UsuarioAdminOut])
def listar_usuarios_empresa(
    usuario: Usuario = Depends(exigir_permissao("equipe", "leitura")),
    db: Session = Depends(get_db),
):
    """Lista todos os usuários já cadastrados da empresa do usuário logado."""
    return (
        db.query(Usuario)
        .filter(
            Usuario.empresa_id == usuario.empresa_id,
        )
        .order_by(Usuario.nome)
        .all()
    )


@router.post("/usuarios", response_model=UsuarioAdminOut, status_code=201)
def criar_usuario_empresa(
    request: Request,
    dados: UsuarioAdminCreate,
    usuario: Usuario = Depends(exigir_permissao("equipe", "escrita")),
    db: Session = Depends(get_db),
):
    """A empresa adiciona um novo usuário (vendedor/atendente)."""
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    # Limite por plano: quantidade máxima de usuários
    checar_limite_usuarios(db, empresa)

    if db.query(Usuario).filter(func.lower(Usuario.email) == dados.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    novo = Usuario(
        empresa_id=usuario.empresa_id,
        nome=dados.nome,
        email=dados.email,
        senha_hash=hash_senha(dados.senha),
        ativo=True,
        permissoes={
            "orcamentos": "escrita",
            "clientes": "escrita",
            "catalogo": "leitura",
            "documentos": "leitura",
            "relatorios": "leitura",
            "ia": "leitura",
        },
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    registrar_auditoria(
        db=db,
        usuario=usuario,
        acao="usuario_criado",
        recurso="usuario",
        recurso_id=str(novo.id),
        detalhes={"email": novo.email, "nome": novo.nome},
        request=request,
    )
    return novo


@router.patch("/usuarios/{usuario_id}", response_model=UsuarioAdminOut)
def atualizar_usuario_empresa(
    usuario_id: int,
    request: Request,
    dados: UsuarioEmpresaUpdate,
    usuario: Usuario = Depends(exigir_permissao("equipe", "escrita")),
    db: Session = Depends(get_db),
):
    """A empresa altera o cadastro de um usuário da própria empresa."""
    alvo = (
        db.query(Usuario)
        .filter(
            Usuario.id == usuario_id,
            Usuario.empresa_id == usuario.empresa_id,
            Usuario.is_superadmin == False,
        )
        .first()
    )
    if not alvo:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    payload = dados.model_dump(exclude_unset=True)

    # Campos restritos ao gestor (is_gestor só pode ser alterado pelo superadmin via /admin)
    payload.pop("is_gestor", None)
    campos_gestor = {"ativo", "permissoes", "papel_id"}
    if campos_gestor.intersection(payload):
        if not usuario.is_gestor:
            raise HTTPException(
                status_code=403,
                detail="Somente o gestor da empresa pode alterar permissões de usuários.",
            )

    if "papel_id" in payload and payload["papel_id"] is not None:
        from app.models.models import Papel
        papel = db.query(Papel).filter(
            Papel.id == payload["papel_id"],
            Papel.empresa_id == usuario.empresa_id,
            Papel.ativo == True,
        ).first()
        if not papel:
            raise HTTPException(status_code=400, detail="Papel não encontrado.")
        if "ativo" in payload and usuario_id == usuario.id:
            raise HTTPException(
                status_code=400, detail="Você não pode inativar sua própria conta."
            )

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
    if (
        "desconto_max_percent" in payload
        and payload["desconto_max_percent"] is not None
    ):
        v = payload["desconto_max_percent"]
        if not (0 <= v <= 100):
            raise HTTPException(
                status_code=400, detail="Desconto máximo deve estar entre 0 e 100%."
            )
    if "telefone_operador" in payload and payload["telefone_operador"]:
        from app.utils.phone import normalize_phone_number
        normalizado = normalize_phone_number(payload["telefone_operador"])
        payload["telefone_operador"] = normalizado or payload["telefone_operador"]

    for campo, valor in payload.items():
        if campo != "senha_hash" and hasattr(alvo, campo):
            setattr(alvo, campo, valor)
    if "senha_hash" in payload:
        alvo.senha_hash = payload["senha_hash"]

    db.commit()
    db.refresh(alvo)
    acao = (
        "usuario_permissao_alterada"
        if "permissoes" in payload
        else "usuario_atualizado"
    )
    registrar_auditoria(
        db=db,
        usuario=usuario,
        acao=acao,
        recurso="usuario",
        recurso_id=str(alvo.id),
        detalhes={"campos": list(payload.keys()), "alvo_email": alvo.email},
        request=request,
    )
    return alvo


# ── WHATSAPP PRÓPRIO ────────────────────────────────────────────────────────


@router.get("/whatsapp/status", response_model=WhatsAppStatusOut)
async def whatsapp_status(
    usuario: Usuario = Depends(exigir_permissao("configuracoes", "leitura")),
    db: Session = Depends(get_db),
):
    """Retorna o status do WhatsApp próprio da empresa."""
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    habilitado = whatsapp_proprio_habilitado(empresa)

    qrcode_data = None
    if habilitado and empresa.whatsapp_proprio_ativo and empresa.evolution_instance:
        from app.services.whatsapp_evolution import EvolutionProvider

        provider = EvolutionProvider(instance=empresa.evolution_instance)

        # Sincroniza status real da Evolution (não depende só de webhook)
        status = await provider.get_status()
        if status.get("connected"):
            if not empresa.whatsapp_conectado:
                empresa.whatsapp_conectado = True
                db.commit()
        else:
            if empresa.whatsapp_conectado:
                empresa.whatsapp_conectado = False
                db.commit()

            # Se a instância foi apagada direto na Evolution, limpa estado local
            if _erro_instancia_inexistente(status.get("error")):
                empresa.evolution_instance = None
                empresa.whatsapp_proprio_ativo = False
                empresa.whatsapp_conectado = False
                empresa.whatsapp_numero = None
                db.commit()
            else:
                # Só tenta QR quando a instância existe, mas está desconectada
                qr = await provider.get_qrcode()
                if not qr.get("error"):
                    qrcode_data = qr.get("qrcode")

    return WhatsAppStatusOut(
        habilitado=habilitado,
        ativo=bool(empresa.whatsapp_proprio_ativo or False),
        conectado=bool(empresa.whatsapp_conectado or False),
        numero=empresa.whatsapp_numero,
        instance=empresa.evolution_instance,
        qrcode=qrcode_data,
    )


@router.post("/whatsapp/conectar", response_model=WhatsAppStatusOut)
async def whatsapp_conectar(
    usuario: Usuario = Depends(exigir_permissao("configuracoes", "escrita")),
    db: Session = Depends(get_db),
):
    """
    Inicia a conexão do WhatsApp próprio da empresa.
    Cria a instância na Evolution API (se ainda não existe) e retorna o QR Code.
    Requer plano Pro ou Business.
    """
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    exigir_whatsapp_proprio(empresa)

    from app.services.whatsapp_evolution import EvolutionProvider

    instance_name = empresa.evolution_instance or f"empresa-{empresa.id}"
    webhook_url = (
        f"{settings.APP_URL.rstrip('/')}/whatsapp/webhook?instance={instance_name}"
    )

    # Se já existe instância salva, valida se ainda existe na Evolution
    if empresa.evolution_instance:
        provider_existente = EvolutionProvider(instance=empresa.evolution_instance)
        status_existente = await provider_existente.get_status()
        if _erro_instancia_inexistente(status_existente.get("error")):
            empresa.evolution_instance = None
            empresa.whatsapp_proprio_ativo = False
            empresa.whatsapp_conectado = False
            empresa.whatsapp_numero = None
            db.commit()
            db.refresh(empresa)

    # Cria a instância quando não existir localmente (ou quando foi removida acima)
    if not empresa.evolution_instance:
        resultado = await EvolutionProvider.criar_instancia(instance_name, webhook_url)
        if not resultado.get("ok"):
            raise HTTPException(
                status_code=503,
                detail=f"Falha ao criar instância na Evolution API: {resultado.get('error', 'erro desconhecido')}",
            )
        empresa.evolution_instance = instance_name
        empresa.whatsapp_proprio_ativo = True
        empresa.whatsapp_conectado = False
        db.commit()
        db.refresh(empresa)

    # Busca o QR code para escanear
    provider = EvolutionProvider(instance=empresa.evolution_instance)
    qr = await provider.get_qrcode()
    if qr.get("error"):
        # Se a instância sumiu entre create/status e connect, limpa e pede nova tentativa
        if _erro_instancia_inexistente(qr.get("error")):
            empresa.evolution_instance = None
            empresa.whatsapp_proprio_ativo = False
            empresa.whatsapp_conectado = False
            empresa.whatsapp_numero = None
            db.commit()
        raise HTTPException(
            status_code=503, detail=f"Falha ao gerar QR Code: {qr.get('error')}"
        )

    status = await provider.get_status()
    conectado = bool(status.get("connected"))
    if conectado and not empresa.whatsapp_conectado:
        empresa.whatsapp_conectado = True
        db.commit()

    return WhatsAppStatusOut(
        habilitado=True,
        ativo=True,
        conectado=conectado,
        numero=empresa.whatsapp_numero,
        instance=empresa.evolution_instance,
        qrcode=qr.get("qrcode"),
    )


@router.get("/whatsapp/qrcode")
async def whatsapp_qrcode_refresh(
    usuario: Usuario = Depends(exigir_permissao("configuracoes", "escrita")),
    db: Session = Depends(get_db),
):
    """Atualiza e retorna um novo QR code (útil quando o anterior expirou)."""
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    exigir_whatsapp_proprio(empresa)

    if not empresa.evolution_instance:
        raise HTTPException(
            status_code=400, detail="Instância não configurada. Use /conectar primeiro."
        )

    from app.services.whatsapp_evolution import EvolutionProvider

    provider = EvolutionProvider(instance=empresa.evolution_instance)
    qr = await provider.get_qrcode()

    if "error" in qr:
        raise HTTPException(status_code=503, detail=qr["error"])

    return {"qrcode": qr.get("qrcode"), "instance": empresa.evolution_instance}


@router.delete("/whatsapp/desconectar")
async def whatsapp_desconectar(
    usuario: Usuario = Depends(exigir_permissao("configuracoes", "escrita")),
    db: Session = Depends(get_db),
):
    """
    Desconecta e remove o WhatsApp próprio da empresa.
    Deleta a instância na Evolution API e limpa os dados no banco.
    """
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()

    if not empresa.evolution_instance:
        raise HTTPException(
            status_code=400, detail="Nenhum WhatsApp próprio configurado."
        )

    from app.services.whatsapp_evolution import EvolutionProvider

    await EvolutionProvider.deletar_instancia(empresa.evolution_instance)

    empresa.evolution_instance = None
    empresa.whatsapp_proprio_ativo = False
    empresa.whatsapp_conectado = False
    empresa.whatsapp_numero = None
    db.commit()

    return {"status": "desconectado"}


# ── BANCOS / PIX DA EMPRESA ──────────────────────────────────────────────────


@router.get("/pix/bancos", response_model=list[BancoPIXOut])
def listar_bancos_pix(
    usuario: Usuario = Depends(exigir_permissao("configuracoes", "leitura")),
    db: Session = Depends(get_db),
):
    """Lista todos os bancos/contas com PIX cadastrados para a empresa."""
    bancos = (
        db.query(BancoPIXEmpresa)
        .filter(BancoPIXEmpresa.empresa_id == usuario.empresa_id)
        .order_by(BancoPIXEmpresa.id.asc())
        .all()
    )
    return bancos


@router.post("/pix/bancos", response_model=BancoPIXOut)
def criar_banco_pix(
    dados: BancoPIXCreate,
    usuario: Usuario = Depends(exigir_permissao("configuracoes", "escrita")),
    db: Session = Depends(get_db),
):
    """Cria um novo banco/conta com chave PIX para a empresa."""
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    banco = BancoPIXEmpresa(
        empresa_id=empresa.id,
        **dados.model_dump(),
    )

    # Se marcado como padrão, desmarca os demais e sincroniza com Empresa.pix_*_padrao
    if dados.padrao_pix and dados.pix_chave:
        (
            db.query(BancoPIXEmpresa)
            .filter(
                BancoPIXEmpresa.empresa_id == empresa.id,
                BancoPIXEmpresa.padrao_pix.is_(True),
            )
            .update({BancoPIXEmpresa.padrao_pix: False})
        )
        empresa.pix_chave_padrao = dados.pix_chave
        empresa.pix_tipo_padrao = dados.pix_tipo
        empresa.pix_titular_padrao = dados.pix_titular

    db.add(banco)
    db.commit()
    db.refresh(banco)
    return banco


@router.patch("/pix/bancos/{banco_id}", response_model=BancoPIXOut)
def atualizar_banco_pix(
    banco_id: int,
    dados: BancoPIXUpdate,
    usuario: Usuario = Depends(exigir_permissao("configuracoes", "escrita")),
    db: Session = Depends(get_db),
):
    """Atualiza dados de um banco/conta PIX da empresa."""
    banco = (
        db.query(BancoPIXEmpresa)
        .filter(
            BancoPIXEmpresa.id == banco_id,
            BancoPIXEmpresa.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not banco:
        raise HTTPException(status_code=404, detail="Banco PIX não encontrado")

    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    payload = dados.model_dump(exclude_unset=True)
    for campo, valor in payload.items():
        setattr(banco, campo, valor)

    # Se padrao_pix foi alterado, ajustar padrão e sincronizar com Empresa.pix_*_padrao
    if "padrao_pix" in payload:
        if payload["padrao_pix"]:
            (
                db.query(BancoPIXEmpresa)
                .filter(
                    BancoPIXEmpresa.empresa_id == empresa.id,
                    BancoPIXEmpresa.id != banco.id,
                )
                .update({BancoPIXEmpresa.padrao_pix: False})
            )
            if banco.pix_chave:
                empresa.pix_chave_padrao = banco.pix_chave
                empresa.pix_tipo_padrao = banco.pix_tipo
                empresa.pix_titular_padrao = banco.pix_titular
        else:
            # Desmarcando o padrão deste banco; se ele era o padrão atual, limpa campos da empresa
            if (
                empresa.pix_chave_padrao == banco.pix_chave
                and empresa.pix_tipo_padrao == banco.pix_tipo
            ):
                empresa.pix_chave_padrao = None
                empresa.pix_tipo_padrao = None
                empresa.pix_titular_padrao = None

    db.commit()
    db.refresh(banco)
    return banco


@router.delete("/pix/bancos/{banco_id}")
def deletar_banco_pix(
    banco_id: int,
    usuario: Usuario = Depends(exigir_permissao("configuracoes", "admin")),
    db: Session = Depends(get_db),
):
    """Remove um banco/conta PIX da empresa."""
    banco = (
        db.query(BancoPIXEmpresa)
        .filter(
            BancoPIXEmpresa.id == banco_id,
            BancoPIXEmpresa.empresa_id == usuario.empresa_id,
        )
        .first()
    )
    if not banco:
        raise HTTPException(status_code=404, detail="Banco PIX não encontrado")

    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()

    if empresa and banco.pix_chave:
        orcamentos_relacionados = (
            db.query(Orcamento)
            .filter(
                Orcamento.empresa_id == usuario.empresa_id,
                Orcamento.status.in_(
                    [
                        StatusOrcamento.RASCUNHO,
                        StatusOrcamento.ENVIADO,
                        StatusOrcamento.APROVADO,
                    ]
                ),
            )
            .filter(
                (Orcamento.pix_chave == banco.pix_chave)
                | (
                    (Orcamento.pix_chave.is_(None) | (Orcamento.pix_chave == ""))
                    & (empresa.pix_chave_padrao == banco.pix_chave)
                ),
            )
            .count()
        )

        if orcamentos_relacionados > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Chave PIX possui {orcamentos_relacionados} orçamento(s) ativo(s) vinculado(s). Remova ou altere os orçamentos antes de excluir a chave PIX.",
            )

    # Se este banco era o padrão atual, limpa na empresa
    if (
        empresa
        and banco.padrao_pix
        and empresa.pix_chave_padrao == banco.pix_chave
        and empresa.pix_tipo_padrao == banco.pix_tipo
    ):
        empresa.pix_chave_padrao = None
        empresa.pix_tipo_padrao = None
        empresa.pix_titular_padrao = None

    db.delete(banco)
    db.commit()
    return {"status": "ok"}


# ── BROADCASTS (mensagens do admin) ──────────────────────────────────────────


@router.get("/broadcasts")
def listar_broadcasts_ativos(
    db: Session = Depends(get_db), usuario=Depends(get_usuario_atual)
):
    """Retorna broadcasts ativos e não expirados para exibir no dashboard da empresa."""
    from app.models.models import Broadcast
    from datetime import datetime, timezone

    agora = datetime.now(timezone.utc)
    broadcasts = (
        db.query(Broadcast)
        .filter(
            Broadcast.ativo == True,
            (Broadcast.expira_em == None) | (Broadcast.expira_em > agora),
        )
        .order_by(Broadcast.criado_em.desc())
        .limit(10)
        .all()
    )
    return [
        {
            "id": b.id,
            "mensagem": b.mensagem,
            "tipo": b.tipo,
            "criado_em": b.criado_em.isoformat() if b.criado_em else None,
            "expira_em": b.expira_em.isoformat() if b.expira_em else None,
        }
        for b in broadcasts
    ]
