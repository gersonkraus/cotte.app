"""
Seed idempotente: popula módulos, planos padrão e papéis por empresa.
Pode rodar N vezes sem duplicar dados.
"""

from sqlalchemy.orm import Session

from app.models.models import Empresa, ModuloSistema, Papel, Plano, PlanoModulo, Usuario

# ── Módulos canônicos do sistema ────────────────────────────────────────────

MODULOS_SEED = [
    {
        "nome": "Orçamentos",
        "slug": "orcamentos",
        "descricao": "Criação e gerenciamento de orçamentos",
        "acoes": ["leitura", "escrita", "exclusao", "admin"],
    },
    {
        "nome": "Clientes",
        "slug": "clientes",
        "descricao": "Cadastro e gestão de clientes",
        "acoes": ["leitura", "escrita", "exclusao", "admin"],
    },
    {
        "nome": "Catálogo",
        "slug": "catalogo",
        "descricao": "Serviços e categorias",
        "acoes": ["leitura", "escrita", "exclusao", "admin"],
    },
    {
        "nome": "Documentos",
        "slug": "documentos",
        "descricao": "Documentos da empresa",
        "acoes": ["leitura", "escrita", "exclusao"],
    },
    {
        "nome": "Relatórios",
        "slug": "relatorios",
        "descricao": "Relatórios e análises",
        "acoes": ["leitura", "admin"],
    },
    {
        "nome": "Financeiro",
        "slug": "financeiro",
        "descricao": "Caixa, contas a receber e a pagar",
        "acoes": ["leitura", "escrita", "exclusao", "admin"],
    },
    {
        "nome": "IA Hub",
        "slug": "ia",
        "descricao": "Assistente de inteligência artificial",
        "acoes": ["leitura", "escrita", "admin"],
    },
    {
        "nome": "Equipe",
        "slug": "equipe",
        "descricao": "Gerenciamento de usuários e papéis",
        "acoes": ["leitura", "escrita", "exclusao", "admin"],
    },
    {
        "nome": "Configurações",
        "slug": "configuracoes",
        "descricao": "Configurações da empresa",
        "acoes": ["leitura", "admin"],
    },
    {
        "nome": "WhatsApp Próprio",
        "slug": "whatsapp_proprio",
        "descricao": "Conectar número WhatsApp da empresa",
        "acoes": ["leitura", "escrita", "admin"],
    },
    {
        "nome": "Lembretes",
        "slug": "lembretes",
        "descricao": "Lembretes automáticos para clientes",
        "acoes": ["leitura", "escrita", "exclusao"],
    },
    {
        "nome": "Agendamentos",
        "slug": "agendamentos",
        "descricao": "Agendamento de entregas e serviços",
        "acoes": ["leitura", "escrita", "exclusao", "admin"],
    },
]

# Módulos por plano (slugs)
PLANOS_SEED = {
    "trial": [
        "orcamentos", "clientes", "catalogo", "documentos", "configuracoes",
    ],
    "starter": [
        "orcamentos", "clientes", "catalogo", "documentos", "configuracoes",
        "relatorios", "financeiro", "equipe", "lembretes",
        "agendamentos",
    ],
    "pro": [
        "orcamentos", "clientes", "catalogo", "documentos", "configuracoes",
        "relatorios", "financeiro", "equipe", "lembretes",
        "ia", "whatsapp_proprio",
        "agendamentos",
    ],
    "business": [
        "orcamentos", "clientes", "catalogo", "documentos", "configuracoes",
        "relatorios", "financeiro", "equipe", "lembretes",
        "ia", "whatsapp_proprio",
        "agendamentos",
    ],
}

# Papéis padrão base (permissões definidas mais abaixo no seed)
PAPEIS_PADRAO_BASE = [
    {
        "nome": "Gestor",
        "slug": "gestor",
        "descricao": "Acesso total ao sistema",
        "is_default": False,
        "is_sistema": True,
        "permissoes": [],  # preenchido dinamicamente com módulos do plano
    },
    {
        "nome": "Vendedor",
        "slug": "vendedor",
        "descricao": "Acesso a orçamentos, clientes e catálogo",
        "is_default": True,
        "is_sistema": True,
        "permissoes": [
            "orcamentos:leitura", "orcamentos:escrita",
            "clientes:leitura", "clientes:escrita",
            "catalogo:leitura",
            "documentos:leitura",
            "agendamentos:leitura", "agendamentos:escrita",
        ],
    },
    {
        "nome": "Financeiro",
        "slug": "financeiro",
        "descricao": "Acesso ao módulo financeiro e relatórios",
        "is_default": False,
        "is_sistema": True,
        "permissoes": [
            "financeiro:leitura", "financeiro:escrita", "financeiro:admin",
            "relatorios:leitura",
            "clientes:leitura",
            "orcamentos:leitura",
            "agendamentos:leitura",
        ],
    },
]


def _upsert_modulos(db: Session) -> dict[str, ModuloSistema]:
    """Cria ou atualiza os módulos canônicos. Retorna dict slug → ModuloSistema."""
    result = {}
    for dados in MODULOS_SEED:
        modulo = db.query(ModuloSistema).filter(ModuloSistema.slug == dados["slug"]).first()
        if modulo is None:
            modulo = ModuloSistema(
                nome=dados["nome"],
                slug=dados["slug"],
                descricao=dados["descricao"],
                acoes=dados["acoes"],
                ativo=True,
            )
            db.add(modulo)
        else:
            # Atualiza campos que podem ter mudado
            modulo.nome = dados["nome"]
            modulo.acoes = dados["acoes"]
            if modulo.descricao is None:
                modulo.descricao = dados["descricao"]
        result[dados["slug"]] = modulo
    db.flush()
    return result


def _upsert_planos(db: Session, modulos_por_slug: dict[str, ModuloSistema]) -> dict[str, Plano]:
    """
    Cria os 4 planos padrão APENAS se a tabela estiver vazia.
    Se já existirem planos, não cria nem altera nenhum.
    Retorna dict nome → Plano com os planos existentes.
    """
    planos_existentes = db.query(Plano).all()

    # Se já há planos, não criar nada — retorna os existentes indexados por nome
    if planos_existentes:
        return {p.nome: p for p in planos_existentes}

    PLANO_CONFIGS = {
        "trial":    {"limite_usuarios": 1,    "limite_orcamentos": 50,   "preco_mensal": 0},
        "starter":  {"limite_usuarios": 3,    "limite_orcamentos": 200,  "preco_mensal": 0},
        "pro":      {"limite_usuarios": 10,   "limite_orcamentos": 1000, "preco_mensal": 0},
        "business": {"limite_usuarios": None, "limite_orcamentos": None, "preco_mensal": 0},
    }

    result = {}
    for slug_plano, slugs_modulos in PLANOS_SEED.items():
        cfg = PLANO_CONFIGS[slug_plano]
        plano = Plano(
            nome=slug_plano,
            descricao=f"Plano {slug_plano.capitalize()}",
            limite_usuarios=cfg["limite_usuarios"],
            limite_orcamentos=cfg["limite_orcamentos"] or 0,
            preco_mensal=cfg["preco_mensal"],
            ativo=True,
        )
        db.add(plano)
        db.flush()

        modulos_desejados = [modulos_por_slug[s] for s in slugs_modulos if s in modulos_por_slug]
        for m in modulos_desejados:
            plano.modulos.append(m)

        result[slug_plano] = plano

    db.flush()
    return result


def _gerar_permissoes_gestor(empresa: Empresa, modulos_por_slug: dict[str, ModuloSistema]) -> list[str]:
    """Gera todas as permissões para o papel Gestor com base no plano da empresa."""
    permissoes = []

    # Tenta via plano_id (novo sistema)
    if empresa.pacote and empresa.pacote.modulos:
        modulos = empresa.pacote.modulos
    else:
        # Fallback: usa todos os módulos do plano legado
        plano_str = empresa.plano or "trial"
        slugs = PLANOS_SEED.get(plano_str, PLANOS_SEED["trial"])
        modulos = [modulos_por_slug[s] for s in slugs if s in modulos_por_slug]

    for modulo in modulos:
        acoes = modulo.acoes or ["leitura", "escrita", "exclusao", "admin"]
        for acao in acoes:
            permissoes.append(f"{modulo.slug}:{acao}")

    return permissoes


def _upsert_papeis_empresa(
    db: Session,
    empresa: Empresa,
    modulos_por_slug: dict[str, ModuloSistema],
) -> dict[str, Papel]:
    """Cria os 3 papéis padrão para uma empresa, se não existirem. Retorna dict slug → Papel."""
    result = {}

    permissoes_gestor = _gerar_permissoes_gestor(empresa, modulos_por_slug)

    for dados in PAPEIS_PADRAO_BASE:
        slug = dados["slug"]
        papel = (
            db.query(Papel)
            .filter(Papel.empresa_id == empresa.id, Papel.slug == slug)
            .first()
        )
        if papel is None:
            permissoes = permissoes_gestor if slug == "gestor" else dados["permissoes"]
            papel = Papel(
                empresa_id=empresa.id,
                nome=dados["nome"],
                slug=slug,
                descricao=dados["descricao"],
                permissoes=permissoes,
                is_default=dados["is_default"],
                is_sistema=dados["is_sistema"],
                ativo=True,
            )
            db.add(papel)
        elif slug == "gestor":
            # Atualiza permissões do gestor se o plano mudou
            papel.permissoes = permissoes_gestor

        result[slug] = papel

    db.flush()
    return result


def _associar_usuarios_a_papeis(
    db: Session,
    empresa: Empresa,
    papeis: dict[str, Papel],
) -> None:
    """Associa usuários existentes sem papel ao papel correto."""
    papel_gestor = papeis.get("gestor")
    papel_vendedor = papeis.get("vendedor")

    for usuario in empresa.usuarios:
        if usuario.is_superadmin:
            continue  # superadmin não precisa de papel
        if usuario.papel_id is not None:
            continue  # já tem papel atribuído

        if usuario.is_gestor:
            usuario.papel_id = papel_gestor.id if papel_gestor else None
        else:
            usuario.papel_id = papel_vendedor.id if papel_vendedor else None


def seed_modulos_e_planos_padrao(db: Session) -> None:
    """
    Função principal de seed. Idempotente — pode rodar N vezes sem duplicar dados.

    O que faz:
    1. Upsert dos 11 módulos canônicos em modulos_sistema
    2. Upsert dos 4 planos padrão (trial/starter/pro/business) com módulos
    3. Para cada empresa: cria 3 papéis padrão (Gestor/Vendedor/Financeiro)
    4. Associa usuários existentes sem papel ao papel correto
    """
    try:
        modulos_por_slug = _upsert_modulos(db)
        _upsert_planos(db, modulos_por_slug)

        empresas = db.query(Empresa).filter(Empresa.ativo == True).all()
        for empresa in empresas:
            papeis = _upsert_papeis_empresa(db, empresa, modulos_por_slug)
            _associar_usuarios_a_papeis(db, empresa, papeis)

        db.commit()
    except Exception as e:
        db.rollback()
        # Log sem travar o startup
        import logging
        logging.getLogger(__name__).warning(f"[seed_modulos] Erro durante seed: {e}")
