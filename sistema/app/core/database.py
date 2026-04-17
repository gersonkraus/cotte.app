from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session as SASession, sessionmaker, with_loader_criteria
from app.core.config import settings
from app.core.tenant_context import get_scoped_empresa_id, tenant_bypass_enabled
from app.models.tenant import TENANT_SCOPED_MODELS, TenantScopedMixin

# Railway e outros clouds às vezes enviam postgres://; SQLAlchemy precisa postgresql://
database_url = settings.DATABASE_URL
if database_url.startswith("postgres://"):
    database_url = "postgresql://" + database_url[10:]

# Engine síncrono (padronizado)
engine_kwargs = {
    "pool_pre_ping": True,  # testa conexão antes de usar (evita EOF/stale connections)
}
if not database_url.startswith("sqlite"):
    engine_kwargs.update(
        {
            "pool_recycle": 1800,  # recicla conexões após 30 min
            "pool_size": 5,
            "max_overflow": 10,
        }
    )
else:
    engine_kwargs.update({"connect_args": {"check_same_thread": False}})

engine = create_engine(database_url, **engine_kwargs)

# Session factories
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


@event.listens_for(SASession, "do_orm_execute")
def _apply_tenant_scope(execute_state):
    """Aplica filtro automático de tenant para entidades marcadas."""
    if not execute_state.is_select:
        return

    session = execute_state.session
    if tenant_bypass_enabled(session):
        return

    empresa_id = get_scoped_empresa_id(session)
    if empresa_id is None:
        return

    statement = execute_state.statement
    for model_cls in TENANT_SCOPED_MODELS:
        statement = statement.options(
            with_loader_criteria(
                model_cls,
                lambda cls: cls.empresa_id == empresa_id,
                include_aliases=True,
                track_closure_variables=True,
            )
        )
    execute_state.statement = statement


@event.listens_for(SASession, "before_flush")
def _autofill_tenant_on_create(session, flush_context, instances):
    """Preenche `empresa_id` automaticamente em novas entidades tenant-scoped."""
    if tenant_bypass_enabled(session):
        return

    empresa_id = get_scoped_empresa_id(session)
    if empresa_id is None:
        return

    for obj in session.new:
        if isinstance(obj, TenantScopedMixin) and getattr(obj, "empresa_id", None) in (
            None,
            0,
        ):
            obj.empresa_id = empresa_id


# Dependência síncrona usada nas rotas para obter sessão do banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.info.pop("_tenant_context", None)
        db.close()
