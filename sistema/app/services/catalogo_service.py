"""Service para lógica de negócio do catálogo de serviços/produtos."""

from sqlalchemy.orm import Session

from app.models.models import Servico, CategoriaCatalogo


# ── CATEGORIAS PADRÃO ─────────────────────────────────────────────────────────

CATEGORIAS_PADRAO = [
    "Serviços",
    "Materiais",
    "Mão de obra",
    "Transporte",
]


def _seed_categorias_padrao(empresa_id: int, db: Session) -> None:
    """Cria categorias padrão para empresa recém-criada (idempotente)."""
    existentes = (
        db.query(CategoriaCatalogo)
        .filter(CategoriaCatalogo.empresa_id == empresa_id)
        .count()
    )
    if existentes > 0:
        return
    for nome in CATEGORIAS_PADRAO:
        db.add(CategoriaCatalogo(empresa_id=empresa_id, nome=nome))
    db.flush()


# ── SERVIÇOS DE DEMONSTRAÇÃO ─────────────────────────────────────────────────

SERVICOS_DEMONSTRACAO = [
    dict(
        nome="Cliente Teste",
        descricao="Serviço de exemplo para demonstração do sistema.",
        preco_padrao=0,
        unidade="un",
    ),
    dict(
        nome="Material Teste",
        descricao="Material de exemplo para demonstração do sistema.",
        preco_padrao=0,
        unidade="un",
    ),
]


def _seed_servicos_demonstracao(empresa_id: int, db: Session) -> None:
    """Cria serviços de demonstração para empresa recém-criada (idempotente)."""
    existentes = db.query(Servico).filter(Servico.empresa_id == empresa_id).count()
    if existentes > 0:
        return
    for dados in SERVICOS_DEMONSTRACAO:
        db.add(Servico(empresa_id=empresa_id, ativo=True, **dados))
    db.flush()


def seed_catalogo_padrao(empresa_id: int, db: Session) -> None:
    """Executa todos os seeds padrão do catálogo para uma empresa."""
    _seed_categorias_padrao(empresa_id, db)
    _seed_servicos_demonstracao(empresa_id, db)
