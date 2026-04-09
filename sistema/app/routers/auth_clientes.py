from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from typing import List
from datetime import datetime, timezone, timedelta
import io
import csv
import logging
import random
import string
import secrets
import hashlib
from app.core.database import get_db
from app.core.auth import (
    hash_senha,
    verificar_senha,
    criar_token,
    get_usuario_atual,
    garantir_acesso_empresa_nao_expirado,
)
from app.core.config import settings
from app.services.email_service import (
    enviar_email_boas_vindas,
    enviar_email_reset_senha,
)
from app.services.rate_limit_service import reset_password_rate_limiter
from app.models.models import (
    Usuario,
    Empresa,
    Cliente,
    CommercialLead,
    CommercialLeadSource,
    LeadScore,
    InteressePlano,
)
from app.schemas.schemas import (
    LoginRequest,
    TokenOut,
    UsuarioCreate,
    UsuarioOut,
    ClienteCreate,
    ClienteOut,
    ClienteUpdate,
    RegistroPublico,
    EsqueciSenhaRequest,
    RedefinirSenhaRequest,
)

# ── AUTH ───────────────────────────────────────────────────────────────────
auth_router = APIRouter(prefix="/auth", tags=["Autenticação"])


def _hash_token_reset(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _agora_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


def _normalizar_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        # Primeiro IP da cadeia (cliente original)
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _validar_rate_limit_reset(request: Request, email: str) -> None:
    ip = _normalizar_ip(request)
    rl = reset_password_rate_limiter.check_reset_limit(ip=ip, email=email)
    if not rl.allowed:
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas de recuperação. Aguarde alguns minutos e tente novamente.",
        )


@auth_router.post("/registrar", response_model=UsuarioOut, status_code=201)
def registrar(dados: UsuarioCreate, db: Session = Depends(get_db)):
    """Registra uma nova empresa e o usuário gestor fundador."""
    if db.query(Usuario).filter(func.lower(Usuario.email) == dados.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    from app.services.admin_config import get_admin_config

    cfg_admin = get_admin_config(db)
    dias_trial = cfg_admin.get("dias_trial_padrao", 14)
    agora = datetime.now(timezone.utc)

    try:
        empresa = Empresa(
            nome=dados.empresa_nome,
            plano="trial",
            trial_ate=agora + timedelta(days=dias_trial),
            ativo=True,
        )
        db.add(empresa)
        db.flush()

        usuario = Usuario(
            empresa_id=empresa.id,
            nome=dados.nome,
            email=dados.email,
            senha_hash=hash_senha(dados.senha),
            is_gestor=True,  # fundador da empresa é gestor
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        # Retorno explícito para evitar falha de serialização do ORM em produção
        return UsuarioOut(
            id=usuario.id,
            nome=usuario.nome,
            email=usuario.email,
            empresa_id=usuario.empresa_id,
            is_superadmin=usuario.is_superadmin or False,
            is_gestor=usuario.is_gestor or False,
        )
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="E-mail já cadastrado ou dados inválidos."
        )
    except Exception as e:
        db.rollback()
        logging.exception("Erro ao registrar usuário: %s", e)
        raise HTTPException(
            status_code=500, detail="Erro ao criar conta. Tente novamente."
        )


@auth_router.post("/registro-publico", status_code=201)
async def registro_publico(dados: RegistroPublico, db: Session = Depends(get_db)):
    """Cadastro self-service: cria empresa em trial (14 dias) e envia credenciais por WhatsApp e e-mail."""
    if db.query(Usuario).filter(func.lower(Usuario.email) == dados.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    # Senha legível: 4 letras maiúsculas + 4 dígitos (ex: BXKP4821)
    senha = "".join(random.choices(string.ascii_uppercase, k=4)) + "".join(
        random.choices(string.digits, k=4)
    )

    from app.services.admin_config import get_admin_config

    cfg_admin = get_admin_config(db)
    dias_trial = cfg_admin.get("dias_trial_padrao", 14)

    try:
        agora = datetime.now(timezone.utc)
        empresa = Empresa(
            nome=dados.empresa_nome,
            telefone=dados.telefone,
            plano="trial",
            trial_ate=agora + timedelta(days=dias_trial),
            ativo=True,
        )
        db.add(empresa)
        db.flush()

        usuario = Usuario(
            empresa_id=empresa.id,
            nome=dados.nome,
            email=dados.email,
            senha_hash=hash_senha(senha),
            ativo=True,
            is_gestor=True,  # fundador da empresa é gestor
        )
        db.add(usuario)
        db.commit()

        # Cria CommercialLead para o time comercial acompanhar o novo trial
        try:
            agora_str = agora.strftime("%d/%m/%Y %H:%M")
            origem = (
                db.query(CommercialLeadSource)
                .filter(func.lower(CommercialLeadSource.nome) == "landing page")
                .first()
            )
            if not origem:
                origem = CommercialLeadSource(nome="Landing Page")
                db.add(origem)
                db.flush()
            lead = CommercialLead(
                nome_responsavel=dados.nome,
                nome_empresa=dados.empresa_nome,
                whatsapp=dados.telefone,
                email=dados.email,
                origem_lead_id=origem.id,
                empresa_id=empresa.id,
                status_pipeline="novo",
                lead_score=LeadScore.QUENTE,
                interesse_plano=InteressePlano.TRIAL,
                observacoes=f"Cadastro via landing page em {agora_str}",
                conta_criada_em=agora,
            )
            db.add(lead)
            db.commit()
        except Exception as e:
            db.rollback()
            logging.warning(
                "Falha ao criar CommercialLead para %s: %s", dados.empresa_nome, e
            )

        # Envia credenciais por WhatsApp
        try:
            from app.services.whatsapp_service import enviar_mensagem_texto

            primeiro = dados.nome.strip().split()[0]
            link = f"{settings.APP_URL}/app/index.html"
            msg = (
                f"🎉 *Bem-vindo ao COTTE, {primeiro}!*\n\n"
                f"Sua conta foi criada com sucesso.\n\n"
                f"📧 *E-mail:* {dados.email}\n"
                f"🔑 *Senha:* `{senha}`\n\n"
                f"🔗 *Acesse agora:*\n{link}\n\n"
                f"⏰ Seu trial gratuito é válido por *{dias_trial} dias*.\n\n"
                f"Qualquer dúvida é só chamar! — Equipe COTTE"
            )
            await enviar_mensagem_texto(dados.telefone, msg)
        except Exception as e:
            logging.warning("Falha ao enviar WhatsApp para %s: %s", dados.telefone, e)

        # Envia notificação de monitoramento para administradores
        try:
            from app.services.admin_config import get_admin_config
            from app.services.whatsapp_service import enviar_mensagem_texto

            cfg = get_admin_config(db)
            numeros_monitoramento = cfg.get("numeros_monitoramento", [])

            if numeros_monitoramento:
                msg_admin = (
                    f"🚨 *Novo Cadastro no COTTE*\n\n"
                    f"🏢 *Empresa:* {dados.empresa_nome}\n"
                    f"👤 *Responsável:* {dados.nome}\n"
                    f"📧 *E-mail:* {dados.email}\n"
                    f"📱 *WhatsApp:* {dados.telefone}"
                )
                for num in numeros_monitoramento:
                    num = str(num).strip()
                    if num:
                        await enviar_mensagem_texto(num, msg_admin)
        except Exception as e:
            logging.warning("Falha ao notificar admin no WhatsApp: %s", e)

        # Envia e-mail de boas-vindas (silencioso se SMTP/Brevo não configurado)
        enviar_email_boas_vindas(dados.email, dados.nome, senha)

        return {
            "ok": True,
            "mensagem": "Conta criada! Verifique seu WhatsApp com as credenciais de acesso.",
        }

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.")
    except Exception as e:
        db.rollback()
        logging.exception("Erro ao criar conta pública: %s", e)
        raise HTTPException(
            status_code=500, detail="Erro ao criar conta. Tente novamente."
        )


@auth_router.get("/config-publica")
def get_config_publica(db: Session = Depends(get_db)):
    """Retorna configurações públicas do sistema, úteis para telas de login ou landing pages antes do login."""
    from app.services.admin_config import get_admin_config

    cfg = get_admin_config(db)
    return {"dias_trial_padrao": cfg.get("dias_trial_padrao", 14)}


@auth_router.post("/login", response_model=TokenOut)
def login(dados: LoginRequest, db: Session = Depends(get_db)):
    """Autentica o usuário e retorna um token JWT de acesso."""
    usuario = db.query(Usuario).filter(func.lower(Usuario.email) == dados.email).first()
    if not usuario or not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")

    # Bloqueia login se o usuário estiver inativo
    if not usuario.ativo:
        raise HTTPException(
            status_code=403,
            detail="Usuário inativo. Entre em contato com o administrador.",
        )

    # Bloqueia login se a empresa estiver inativa (exceto superadmin)
    if not usuario.is_superadmin and usuario.empresa:
        if not usuario.empresa.ativo:
            raise HTTPException(
                status_code=403,
                detail="Empresa inativa. Entre em contato com o suporte.",
            )
        garantir_acesso_empresa_nao_expirado(usuario.empresa)

    # Invalida todos os logins anteriores: só este token será aceito a partir de agora
    usuario.token_versao = (usuario.token_versao or 0) + 1
    db.commit()
    db.refresh(usuario)

    token = criar_token(
        {
            "sub": str(usuario.id),
            "empresa_id": usuario.empresa_id,
            "v": usuario.token_versao,
        }
    )
    return {"access_token": token}


@auth_router.post("/esqueci-senha")
def esqueci_senha(
    dados: EsqueciSenhaRequest, request: Request, db: Session = Depends(get_db)
):
    """
    Inicia recuperação de senha por token temporário.
    Sempre retorna sucesso para não expor se o e-mail existe.
    """
    _validar_rate_limit_reset(request, dados.email)

    usuario = (
        db.query(Usuario)
        .filter(func.lower(Usuario.email) == dados.email, Usuario.ativo == True)
        .first()
    )
    if usuario:
        token_plano = secrets.token_urlsafe(32)
        usuario.reset_senha_token_hash = _hash_token_reset(token_plano)
        usuario.reset_senha_expira_em = datetime.now(timezone.utc) + timedelta(
            minutes=30
        )
        db.commit()

        link_reset = f"{settings.APP_URL.rstrip('/')}/app/redefinir-senha.html?token={token_plano}"
        try:
            enviar_email_reset_senha(usuario.email, usuario.nome, link_reset)
        except Exception as e:
            logging.warning(
                "Falha ao disparar e-mail de reset para %s: %s", usuario.email, e
            )

    return {
        "ok": True,
        "mensagem": "Se o e-mail estiver cadastrado, você receberá um link de redefinição em instantes.",
    }


@auth_router.post("/redefinir-senha")
def redefinir_senha(dados: RedefinirSenhaRequest, db: Session = Depends(get_db)):
    """Redefine a senha do usuário a partir de um token de recuperação."""
    token_hash = _hash_token_reset(dados.token)
    usuario = (
        db.query(Usuario)
        .filter(Usuario.reset_senha_token_hash == token_hash, Usuario.ativo == True)
        .first()
    )

    if not usuario or not usuario.reset_senha_expira_em:
        raise HTTPException(status_code=400, detail="Link inválido ou expirado.")

    if usuario.reset_senha_expira_em < datetime.now(timezone.utc):
        usuario.reset_senha_token_hash = None
        usuario.reset_senha_expira_em = None
        db.commit()
        raise HTTPException(status_code=400, detail="Link inválido ou expirado.")

    usuario.senha_hash = hash_senha(dados.nova_senha)
    usuario.reset_senha_token_hash = None
    usuario.reset_senha_expira_em = None
    usuario.token_versao = (
        usuario.token_versao or 0
    ) + 1  # invalida sessões anteriores
    db.commit()

    return {
        "ok": True,
        "mensagem": "Senha redefinida com sucesso. Faça login com a nova senha.",
    }


@auth_router.get("/me", response_model=UsuarioOut)
def me(usuario: Usuario = Depends(get_usuario_atual)):
    """Retorna os dados do usuário autenticado."""
    return usuario


# ── CLIENTES ───────────────────────────────────────────────────────────────
# Os endpoints de clientes foram movidos para app/routers/clientes.py
