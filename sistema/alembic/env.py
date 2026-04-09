# Alembic env.py — usa DATABASE_URL do app e MetaData dos models
from logging.config import fileConfig

from sqlalchemy import pool
from alembic import context

from app.core.config import settings
from app.core.database import Base

# Importar todos os models para que Base.metadata contenha as tabelas (autogenerate)
from app.models import models  # noqa: F401

config = context.config
target_metadata = Base.metadata

# URL do banco a partir do app (Railway envia postgres://; SQLAlchemy precisa postgresql://)
database_url = settings.DATABASE_URL
if database_url.startswith("postgres://"):
    database_url = "postgresql://" + database_url[10:]
config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_offline() -> None:
    """Executa migrations em modo offline (gera SQL sem conectar)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Executa migrations em modo online (conecta ao banco)."""
    from sqlalchemy import create_engine
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
