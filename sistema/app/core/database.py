from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Railway e outros clouds às vezes enviam postgres://; SQLAlchemy precisa postgresql://
database_url = settings.DATABASE_URL
if database_url.startswith("postgres://"):
    database_url = "postgresql://" + database_url[10:]

# Engine síncrono (padronizado)
engine = create_engine(
    database_url,
    pool_pre_ping=True,      # testa conexão antes de usar (evita EOF/stale connections)
    pool_recycle=1800,       # recicla conexões após 30 min
    pool_size=5,
    max_overflow=10,
)

# Session factories
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Dependência síncrona usada nas rotas para obter sessão do banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
