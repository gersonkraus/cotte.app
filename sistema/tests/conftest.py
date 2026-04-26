"""
Fixtures compartilhadas para todos os testes do COTTE.

Estratégia:
- Banco SQLite em arquivo (sem PostgreSQL necessário)
- Serviços externos mockados: WhatsApp, Claude AI, PDF
- Fábricas de objetos para criar Empresa, Usuario, Cliente, Orcamento
"""

import os
import secrets
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, joinedload, sessionmaker

# ── Variáveis de ambiente ANTES de qualquer import do app ──────────────────
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_cotte.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-only-for-tests")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("WHATSAPP_PROVIDER", "zapi")
os.environ.setdefault("ADMIN_SETUP_KEY", "test-admin-setup-key-only-for-tests")
os.environ.setdefault("ZAPI_CLIENT_TOKEN", "test-zapi-client-token")
os.environ.setdefault("EVOLUTION_API_KEY", "test-evolution-api-key")
os.environ.setdefault("API_V1_STR", "/api/v1")

from tests.asgi_client import SyncASGIClient

from app.core.database import Base, get_db
from app.models.models import (
    Cliente,
    Empresa,
    ItemOrcamento,
    ModuloSistema,
    Orcamento,
    Plano,
    PlanoModulo,
    StatusOrcamento,
    Usuario,
)

# ── Engines SQLite para testes ──────────────────────────────────────────────
SQLITE_URL = "sqlite+aiosqlite:///./test_cotte.db"
async_engine_test = create_async_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
)
TestingAsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=async_engine_test,
    class_=AsyncSession,
)

sync_engine_test = create_engine(
    "sqlite:///./test_cotte.db",
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine_test,
)


def override_get_db():
    """Dependency sync para uso com TestClient."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


async def override_get_async_db():
    """Dependency async para uso com AsyncClient."""
    async with TestingAsyncSessionLocal() as session:
        yield session


# ── Patches de serviços externos (aplicados em toda a sessão de testes) ─────
PATCHES = [
    patch("app.services.whatsapp_bot_service.enviar_mensagem_texto", new_callable=AsyncMock),
    patch("app.services.whatsapp_bot_service.enviar_orcamento_completo", new_callable=AsyncMock),
    patch("app.services.whatsapp_bot_service.interpretar_mensagem", new_callable=AsyncMock),
    patch("app.services.whatsapp_bot_service.interpretar_comando_operador", new_callable=AsyncMock),
    patch("app.services.whatsapp_bot_service.gerar_resposta_bot", new_callable=AsyncMock),
    patch("app.services.whatsapp_bot_service.gerar_pdf_orcamento", return_value=b"%PDF-fake"),
    patch("app.services.whatsapp_bot_service.handle_quote_status_changed", new_callable=AsyncMock),
    patch("app.routers.publico.notificar_operador_visualizacao", new_callable=AsyncMock),
    patch("app.routers.publico.notificar_operador_recusa", new_callable=AsyncMock),
    patch("app.routers.publico.handle_quote_status_changed", new_callable=AsyncMock),
    patch("app.routers.publico.enviar_mensagem_texto", new_callable=AsyncMock),
    patch("app.routers.publico.email_habilitado", return_value=False),
    patch("app.routers.publico.enviar_email_confirmacao_aceite", return_value=True),
    patch("app.services.plano_service.ia_automatica_habilitada", return_value=True),
    patch("app.services.plano_service.checar_limite_orcamentos", return_value=None),
]


@pytest_asyncio.fixture(scope="session")
async def setup_database():
    """Cria as tabelas uma vez por sessão de testes."""
    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await async_engine_test.dispose()


@pytest_asyncio.fixture
async def clean_tables(setup_database):
    """Limpa todas as tabelas entre os testes para isolamento."""
    import asyncio

    yield
    async with TestingAsyncSessionLocal() as db_session:
        async with db_session.begin():
            for table in reversed(Base.metadata.sorted_tables):
                await db_session.execute(table.delete())
    await asyncio.sleep(0)


@pytest.fixture(scope="session")
def mock_services():
    """Ativa todos os patches de serviços externos na sessão inteira."""
    started = [p.start() for p in PATCHES]
    yield started
    for p in PATCHES:
        p.stop()


@pytest.fixture
def http_client(mock_services, setup_database, clean_tables):
    """Cliente síncrono para testes ASGI."""
    from app.main import app as main_app

    main_app.dependency_overrides[get_db] = override_get_db
    yield SyncASGIClient(main_app, raise_app_exceptions=False)
    main_app.dependency_overrides.clear()


@pytest.fixture
def db(setup_database):
    """Sessão de banco síncrona para uso com TestClient."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest_asyncio.fixture
async def db_session(setup_database) -> AsyncSession:
    """Sessão assíncrona por teste."""
    async with TestingAsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def empresa_id(db_session: AsyncSession) -> int:
    """ID da empresa de teste criada por teste."""
    emp = Empresa(
        nome="Empresa Teste Financeiro",
        telefone_operador="5511999990001",
        ativo=True,
        plano="pro",
    )
    db_session.add(emp)
    await db_session.commit()
    await db_session.refresh(emp)
    return emp.id


@pytest_asyncio.fixture
async def admin_token(db_session: AsyncSession, empresa_id: int) -> str:
    """Token JWT válido para testes que exigem autenticação admin."""
    import uuid

    from app.core.auth import criar_token

    user = Usuario(
        empresa_id=empresa_id,
        nome="Admin Teste",
        email=f"admin_test_{uuid.uuid4().hex[:8]}@teste.com",
        senha_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehash12",
        ativo=True,
        is_gestor=True,
        token_versao=1,
    )
    db_session.add(user)
    try:
        await db_session.commit()
    except Exception:
        await db_session.rollback()
        raise
    await db_session.refresh(user)

    return criar_token(data={"sub": str(user.id), "v": 1})


@pytest_asyncio.fixture
async def client(mock_services, setup_database):
    """AsyncClient para testes async com FastAPI."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app as main_app

    main_app.dependency_overrides[get_db] = override_get_async_db

    transport = ASGITransport(app=main_app, raise_app_exceptions=False)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as c:
        yield c

    main_app.dependency_overrides.clear()


# ── Fixtures de apoio ao módulo comercial tenant ────────────────────────────
@pytest.fixture
def seed_base_data(db: Session):
    """Cria plano com módulo comercial habilitado."""
    modulo = db.query(ModuloSistema).filter(ModuloSistema.slug == "comercial").first()
    if modulo is None:
        modulo = ModuloSistema(
            nome="Comercial",
            slug="comercial",
            descricao="CRM de leads, pipeline e propostas",
            acoes=["leitura", "escrita", "exclusao", "admin"],
        )
        db.add(modulo)
        db.flush()

    plano = Plano(
        nome="Plano Comercial Teste",
        preco_mensal=Decimal("99.90"),
        ativo=True,
    )
    db.add(plano)
    db.flush()

    db.add(PlanoModulo(plano_id=plano.id, modulo_id=modulo.id))
    db.commit()

    return (
        db.query(Plano)
        .options(joinedload(Plano.modulos))
        .filter(Plano.id == plano.id)
        .first()
    )


@pytest.fixture
def empresa_com_plano(db: Session, seed_base_data: Plano):
    """Cria empresa com plano que possui o módulo comercial."""
    empresa = Empresa(
        nome=f"Empresa Teste Comercial {seed_base_data.id}",
        telefone_operador="5511999990001",
        ativo=True,
        plano_id=seed_base_data.id,
    )
    db.add(empresa)
    db.commit()
    return (
        db.query(Empresa)
        .options(joinedload(Empresa.pacote).joinedload(Plano.modulos))
        .filter(Empresa.id == empresa.id)
        .first()
    )


# ── Fábricas de objetos de teste ────────────────────────────────────────────
def make_empresa(db, nome="Empresa Teste", telefone_operador="5511999990001", plano="pro"):
    emp = Empresa(nome=nome, telefone_operador=telefone_operador, plano=plano)
    db.add(emp)
    db.flush()
    return emp


def make_usuario(
    db,
    empresa,
    nome="Gestor Teste",
    email=None,
    is_gestor=True,
    permissoes=None,
):
    """Cria um usuário de teste com empresa e permissões."""
    email = email or f"gestor_{empresa.id}@teste.com"
    perm_data = {}
    if isinstance(permissoes, (list, set)):
        for p_str in permissoes:
            if ":" in p_str:
                recurso, acao = p_str.split(":", 1)
                perm_data[recurso] = acao
            else:
                perm_data[p_str] = "admin"
    elif isinstance(permissoes, dict):
        perm_data = permissoes

    u = Usuario(
        empresa_id=empresa.id,
        nome=nome,
        email=email,
        senha_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehash12",
        ativo=True,
        is_gestor=is_gestor,
        permissoes=perm_data or {},
    )
    db.add(u)
    db.flush()
    return u


def make_cliente(db, empresa, nome="Cliente Teste", telefone="5511988880001"):
    c = Cliente(empresa_id=empresa.id, nome=nome, telefone=telefone)
    db.add(c)
    db.flush()
    return c


def make_orcamento(
    db,
    empresa,
    cliente,
    usuario,
    status=StatusOrcamento.ENVIADO,
    total=500.0,
    link_publico=None,
    numero=None,
):
    link_publico = link_publico or secrets.token_urlsafe(12)
    numero = numero or "ORC-1-26"
    orc = Orcamento(
        empresa_id=empresa.id,
        cliente_id=cliente.id,
        criado_por_id=usuario.id,
        numero=numero,
        status=status,
        total=total,
        link_publico=link_publico,
        origem_whatsapp=False,
    )
    db.add(orc)
    db.flush()
    item = ItemOrcamento(
        orcamento_id=orc.id,
        descricao="Serviço teste",
        quantidade=1.0,
        valor_unit=total,
        total=total,
    )
    db.add(item)
    db.commit()
    db.refresh(orc)
    return orc
