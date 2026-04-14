from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.tenant_context import enable_superadmin_bypass, set_tenant_context
from app.models.models import Empresa, Plano, Usuario

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_senha(senha: str) -> str:
    # bcrypt limita a 72 bytes; truncar evita ValueError
    b = senha.encode("utf-8")
    if len(b) > 72:
        senha = b[:72].decode("utf-8", errors="ignore") or senha[:24]
    return pwd_context.hash(senha)


def verificar_senha(senha: str, hash: str) -> bool:
    return pwd_context.verify(senha, hash)


def criar_token(data: dict) -> str:
    payload = data.copy()
    expira = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload.update({"exp": expira})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _normalizar_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def limite_acesso_empresa(empresa: Empresa) -> Optional[datetime]:
    """
    Data até a qual o acesso à API é considerado válido, unificando trial e assinatura.

    Usa o máximo entre trial_ate e assinatura_valida_ate quando ambos existem
    (ex.: trial encerrado mas assinatura ativa). Se nenhum estiver definido,
    retorna None (compatível com bases legadas sem teto).
    """
    limites: list[datetime] = []
    if empresa.trial_ate is not None:
        limites.append(_normalizar_utc(empresa.trial_ate))
    if empresa.assinatura_valida_ate is not None:
        limites.append(_normalizar_utc(empresa.assinatura_valida_ate))
    if not limites:
        return None
    return max(limites)


def garantir_acesso_empresa_nao_expirado(empresa: Empresa) -> None:
    """Lança 402 se o período unificado (trial e/ou assinatura) exceder a graça de 3 dias."""
    limite = limite_acesso_empresa(empresa)
    if limite is None:
        return
    agora = datetime.now(timezone.utc)
    graca = timedelta(days=3)
    if limite + graca < agora:
        raise HTTPException(
            status_code=402,
            detail="Assinatura expirada. Renove seu plano para continuar.",
        )


def _presenca_esta_desatualizada(
    ultima: Optional[datetime], agora: datetime, intervalo: timedelta
) -> bool:
    """True se não há marca anterior ou se já passou o intervalo desde a última gravação."""
    if ultima is None:
        return True
    return agora - _normalizar_utc(ultima) >= intervalo


def get_usuario_atual(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Usuario:
    erro = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        usuario_id: int = payload.get("sub")
        if usuario_id is None:
            raise erro
    except JWTError:
        raise erro

    usuario = (
        db.query(Usuario)
        .filter(Usuario.id == usuario_id, Usuario.ativo == True)
        .first()
    )
    if not usuario:
        raise erro
    # Sessão única: token só vale se a versão bater (login em outro lugar invalida este token)
    token_versao = payload.get("v")
    if token_versao is None or usuario.token_versao != token_versao:
        raise erro
    # Bloqueia acesso se a empresa estiver inativa (exceto superadmin)
    if not usuario.is_superadmin and usuario.empresa:
        if not usuario.empresa.ativo:
            raise HTTPException(
                status_code=403,
                detail="Empresa inativa. Entre em contato com o suporte.",
            )
        # Trial e assinatura: bloqueia se o limite efetivo (+ graça) foi ultrapassado
        garantir_acesso_empresa_nao_expirado(usuario.empresa)
    # Presença: throttle para não dar COMMIT em toda requisição (layout, polling, etc.)
    agora = datetime.now(timezone.utc)
    intervalo = timedelta(seconds=settings.ULTIMA_ATIVIDADE_COMMIT_INTERVAL_SECONDS)
    empresa = usuario.empresa
    ultima_empresa: Optional[datetime] = None
    if empresa:
        try:
            ultima_empresa = empresa.ultima_atividade_em
        except AttributeError:
            ultima_empresa = None
    precisa = _presenca_esta_desatualizada(
        usuario.ultima_atividade_em, agora, intervalo
    ) or (
        empresa is not None
        and ultima_empresa is not None
        and _presenca_esta_desatualizada(ultima_empresa, agora, intervalo)
    )
    # Primeira gravação da empresa (coluna null) alinha com o usuário
    if empresa is not None and ultima_empresa is None:
        precisa = True
    if precisa:
        usuario.ultima_atividade_em = agora
        if empresa:
            try:
                empresa.ultima_atividade_em = agora
            except AttributeError:
                pass
        db.commit()
    set_tenant_context(
        db,
        empresa_id=usuario.empresa_id,
        usuario_id=usuario.id,
        is_superadmin=usuario.is_superadmin,
    )
    return usuario


def get_superadmin(
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
) -> Usuario:
    if not usuario.is_superadmin:
        raise HTTPException(
            status_code=403, detail="Acesso restrito ao administrador do sistema"
        )
    enable_superadmin_bypass(db, usuario=usuario, reason="superadmin_dependency")
    return usuario


def exigir_modulo(slug: str):
    """
    Dependência que verifica se o plano da empresa inclui o módulo.

    - Superadmin: passa sempre
    - Demais: verifica empresa.plano_id → pacote.modulos (novo sistema)
    - Fallback: se plano_id is None, verifica PLANO_CONFIG[empresa.plano] (legado)
    """

    def dependency(
        current_user: Usuario = Depends(get_usuario_atual),
        db: Session = Depends(get_db),
    ) -> Usuario:
        if current_user.is_superadmin:
            return current_user

        empresa = current_user.empresa
        if empresa is None:
            raise HTTPException(status_code=403, detail="Empresa não encontrada.")

        if empresa.plano_id:
            plano = db.query(Plano).filter(Plano.id == empresa.plano_id).first()
            if plano:
                slugs_disponiveis = [m.slug for m in plano.modulos]
                if slug not in slugs_disponiveis:
                    raise HTTPException(
                        status_code=403,
                        detail=f"O módulo '{slug}' não está disponível no plano '{plano.nome}'.",
                    )
            else:
                raise HTTPException(status_code=403, detail="Plano da empresa não encontrado.")
        else:
            _verificar_modulo_legado(slug, empresa)

        return current_user

    return dependency


def _verificar_modulo_legado(slug: str, empresa) -> None:
    """
    Fallback para empresas sem plano_id.
    Mapeia slugs para features do PLANO_CONFIG.
    Módulos não mapeados são considerados disponíveis em todos os planos.
    """
    from app.services.plano_service import PLANO_CONFIG

    plano_str = empresa.plano or "trial"
    config = PLANO_CONFIG.get(plano_str, PLANO_CONFIG["trial"])

    SLUG_TO_FEATURE = {
        "ia": "ia_automatica",
        "relatorios": "relatorios",
        "whatsapp_proprio": "whatsapp_proprio",
        "lembretes": "lembretes_automaticos",
    }

    feature = SLUG_TO_FEATURE.get(slug)
    if feature:
        valor = config.get(feature, False)
        if valor is False:
            raise HTTPException(
                status_code=403,
                detail=f"O módulo '{slug}' não está disponível no seu plano atual.",
            )


def exigir_permissao(recurso: str, acao: str = "leitura"):
    """
    Dependência para validar permissões granulares.

    Ordem de verificação:
    1. Superadmin → passa sempre
    2. Gestor → passa sempre
    3. Novo: se usuario.papel_id → verifica papel.permissoes (lista "modulo:acao")
    4. Fallback legado: usuario.permissoes (dict JSON)

    Hierarquia de ações: admin(3) > escrita(2) > exclusao(2.5) > meus(1.5) > leitura(1)
    """

    niveis = {
        "leitura": 1,
        "meus": 1.5,
        "escrita": 2,
        "exclusao": 2.5,
        "admin": 3,
    }

    def validator(usuario: Usuario = Depends(get_usuario_atual)) -> Usuario:
        # 1. Superadmin sempre tem acesso
        if usuario.is_superadmin:
            return usuario

        # 2. Gestor tem acesso total à empresa
        if usuario.is_gestor:
            return usuario

        nivel_requerido = niveis.get(acao, 1)

        # 3. Novo sistema: verificação via papel (RBAC)
        if usuario.papel_id and usuario.papel:
            permissoes_papel = usuario.papel.permissoes or []
            for perm in permissoes_papel:
                try:
                    mod, acao_papel = perm.split(":", 1)
                except ValueError:
                    continue
                if mod == recurso and niveis.get(acao_papel, 0) >= nivel_requerido:
                    return usuario
            raise HTTPException(
                status_code=403,
                detail=f"Você não tem permissão para '{acao}' em '{recurso}'. Fale com o gestor.",
            )

        # 4. Fallback legado: JSON usuario.permissoes
        perms = usuario.permissoes or {}
        user_acao = perms.get(recurso)

        recursos_restritos = ["equipe", "configuracoes"]
        if not user_acao and recurso in recursos_restritos:
            raise HTTPException(
                status_code=403, detail=f"Acesso restrito ao recurso {recurso}"
            )

        if not user_acao:
            raise HTTPException(
                status_code=403,
                detail=f"Sem permissão para acessar '{recurso}'. Contate o gestor da conta.",
            )

        if niveis.get(user_acao, 0) < nivel_requerido:
            raise HTTPException(
                status_code=403,
                detail=f"Permissão insuficiente em {recurso} (necessário {acao})",
            )

        return usuario

    return validator


def verificar_ownership(obj, usuario: Usuario) -> None:
    """
    Garante que o objeto pertence à empresa do usuário autenticado.
    Superadmin ignora a verificação. Lança 403 se houver violação de tenant.

    Uso:
        verificar_ownership(orcamento, usuario)
        verificar_ownership(cliente, usuario)
    """
    if usuario.is_superadmin:
        return
    empresa_id_obj = getattr(obj, "empresa_id", None)
    if empresa_id_obj is None:
        return
    if empresa_id_obj != usuario.empresa_id:
        raise HTTPException(
            status_code=403,
            detail="Acesso negado: este recurso não pertence à sua empresa.",
        )
