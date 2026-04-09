---
title: Prompt Permissoes Escalaveis
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Prompt Permissoes Escalaveis
tags:
  - documentacao
prioridade: alta
status: documentado
---
# Prompt para Claude Code — Unificação do Sistema de Permissões (Escalável)

## Contexto do Projeto

Este é o COTTE — um sistema de orçamentos (CRM/ERP leve) para empresas de serviço. O backend é **FastAPI + SQLAlchemy + PostgreSQL** com Alembic para migrations. O frontend é **HTML/CSS/JS vanilla** (sem framework) servido como arquivos estáticos na pasta `cotte-frontend/`. O sistema de auth está em `app/core/auth.py`.

Antes de começar, **leia toda a estrutura do projeto** para entender os padrões existentes:
- `app/models/models.py` — modelos SQLAlchemy (inclui `Usuario`, `Empresa`, `Plano`, `ModuloSistema`, tabela associativa `plano_modulo`)
- `app/schemas/schemas.py` — schemas Pydantic
- `app/core/auth.py` — autenticação e permissões (`get_usuario_atual`, `exigir_permissao`)
- `app/services/plano_service.py` — PLANO_CONFIG hardcoded, funções como `ia_automatica_habilitada()`, `relatorios_habilitados()`, `whatsapp_proprio_habilitado()`
- `app/routers/` — todos os routers existentes
- `app/main.py` — registro de routers e startup
- `cotte-frontend/admin-planos.html` — tela de admin que já exibe módulos
- `alembic/` — configuração de migrations

Siga os padrões de código, nomenclatura e estilo já existentes no projeto.

---

## Objetivo

Unificar o sistema de permissões em 3 níveis escaláveis:

1. **Nível empresa (plano)** — o plano da empresa define quais módulos estão disponíveis
2. **Nível empresa (papel/role)** — cada empresa cria papéis com permissões granulares
3. **Nível usuário** — cada usuário recebe um papel que define o que pode fazer

A meta é: quando um novo módulo for criado no futuro (ex: CRM, Estoque), basta o admin cadastrar o módulo, associar ao plano, e o gestor da empresa configurar quais papéis têm acesso — **zero código novo**.

---

## Situação Atual (o que já existe)

O sistema tem dois mecanismos paralelos que não se conversam:

1. `plano_service.py` com `PLANO_CONFIG` — hardcoded, verifica features por plano (string "trial/starter/pro/business")
2. `exigir_permissao(recurso, acao)` — lê JSON do campo `usuario.permissoes`, verifica por usuário
3. `modulos_sistema` (tabela) + `plano_modulo` (associativa) — existe no banco mas só é usada visualmente no `admin-planos.html`

A empresa tem dois campos de plano:
- `empresa.plano` (string "trial/starter/pro") — legado, usado pelo `plano_service.py`
- `empresa.plano_id` (FK para tabela `Plano`) — novo sistema, existe mas não é usado para controle de acesso

---

## Arquitetura Alvo (3 níveis)

```
modulos_sistema ──[many-to-many]── planos
                                      │
                                  empresa.plano_id  ← empresa usa qual plano
                                      │
                              exigir_modulo("slug")  ← nível 1: empresa tem o módulo?
                                      │
                                   papeis  ← nível 2: papel da empresa
                                      │
                         papel.permissoes = ["modulo:acao", ...]
                                      │
                              usuario.papel_id  ← nível 3: usuário tem o papel
                                      │
                         exigir_permissao("modulo", "acao")  ← verifica no papel
```

### Fluxo de verificação em cada endpoint:
1. `exigir_modulo("financeiro")` → o plano da empresa inclui o módulo "financeiro"?
2. `exigir_permissao("financeiro", "escrita")` → o papel do usuário inclui "financeiro:escrita"?

### Como adicionar nova permissão futuramente:
1. Admin cria módulo no `admin-planos.html` (ex: "CRM" com slug `crm`, ações: leitura/escrita/exclusao/admin)
2. Admin associa o módulo ao plano
3. Gestor da empresa configura no painel quais papéis têm acesso ao CRM
4. Dev adiciona `exigir_modulo("crm")` + `exigir_permissao("crm", "escrita")` no endpoint
5. Zero hardcoding novo.

---

## PARTE 1 — Modelo de Dados

### 1.1 Atualizar tabela `modulos_sistema`

Verificar o modelo `ModuloSistema` existente em `app/models/models.py`. Adicionar campo `acoes` se não existir:

```python
# No modelo ModuloSistema existente, adicionar:
acoes = Column(JSON, default=["leitura", "escrita", "exclusao", "admin"])
# Lista de ações que este módulo suporta
# Cada módulo pode ter ações diferentes
# Ex: módulo "configuracoes" pode ter apenas ["leitura", "admin"]
```

As ações padrão são:
- `leitura` — visualizar dados do módulo
- `escrita` — criar/editar dados
- `exclusao` — deletar dados
- `admin` — configurações avançadas do módulo

### 1.2 Novo modelo `Papel` (Role)

Criar o modelo `Papel` em `app/models/models.py`:

```python
class Papel(Base):
    __tablename__ = "papeis"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    nome = Column(String(100), nullable=False)          # ex: "Gestor", "Vendedor", "Financeiro"
    slug = Column(String(50), nullable=False)            # ex: "gestor", "vendedor", "financeiro"
    descricao = Column(String(500), nullable=True)       # descrição do papel
    permissoes = Column(JSON, default=[])                # lista de strings "modulo:acao"
    is_default = Column(Boolean, default=False)          # se é o papel padrão para novos usuários
    is_sistema = Column(Boolean, default=False)          # se foi criado pelo seed (não pode ser excluído)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    empresa = relationship("Empresa", back_populates="papeis")
    usuarios = relationship("Usuario", back_populates="papel")

    # Constraint: slug único por empresa
    __table_args__ = (
        UniqueConstraint('empresa_id', 'slug', name='uq_papel_empresa_slug'),
    )
```

### 1.3 Atualizar modelo `Usuario`

Adicionar campo `papel_id` ao modelo `Usuario`:

```python
# Adicionar ao modelo Usuario existente:
papel_id = Column(Integer, ForeignKey("papeis.id"), nullable=True)  # nullable para migração gradual
papel = relationship("Papel", back_populates="usuarios")
```

**IMPORTANTE:** O campo é `nullable=True` para não quebrar usuários existentes. Na migração, associar usuários gestores/dono ao papel "Gestor" automaticamente.

### 1.4 Atualizar modelo `Empresa`

Adicionar a relationship inversa:

```python
# Adicionar ao modelo Empresa existente:
papeis = relationship("Papel", back_populates="empresa", order_by="Papel.nome")
```

### 1.5 Migration Alembic

Criar UMA migration que faz tudo em ordem:

1. Adicionar coluna `acoes` (JSON) na tabela `modulos_sistema` (se não existir)
2. Criar tabela `papeis`
3. Adicionar coluna `papel_id` (FK, nullable) na tabela `usuarios`

**NÃO alterar migrations antigas. Criar nova migration.**

---

## PARTE 2 — Seed de Módulos, Planos e Papéis

### 2.1 Criar `app/services/seed_modulos.py`

Função `seed_modulos_e_planos_padrao(db)` que:

**A) Upsert dos 11 módulos por slug (idempotente):**

```python
MODULOS_SEED = [
    {"nome": "Orçamentos",       "slug": "orcamentos",       "acoes": ["leitura", "escrita", "exclusao", "admin"]},
    {"nome": "Clientes",         "slug": "clientes",         "acoes": ["leitura", "escrita", "exclusao", "admin"]},
    {"nome": "Catálogo",         "slug": "catalogo",          "acoes": ["leitura", "escrita", "exclusao", "admin"]},
    {"nome": "Documentos",       "slug": "documentos",        "acoes": ["leitura", "escrita", "exclusao"]},
    {"nome": "Relatórios",       "slug": "relatorios",        "acoes": ["leitura", "admin"]},
    {"nome": "Financeiro",       "slug": "financeiro",        "acoes": ["leitura", "escrita", "exclusao", "admin"]},
    {"nome": "IA Hub",           "slug": "ia",                "acoes": ["leitura", "escrita", "admin"]},
    {"nome": "Equipe",           "slug": "equipe",            "acoes": ["leitura", "escrita", "exclusao", "admin"]},
    {"nome": "Configurações",    "slug": "configuracoes",     "acoes": ["leitura", "admin"]},
    {"nome": "WhatsApp Próprio", "slug": "whatsapp_proprio",  "acoes": ["leitura", "escrita", "admin"]},
    {"nome": "Lembretes",        "slug": "lembretes",         "acoes": ["leitura", "escrita", "exclusao"]},
]
```

**B) Upsert dos 4 planos padrão com associação de módulos:**

```python
PLANOS_SEED = {
    "trial":    ["orcamentos", "clientes", "catalogo", "documentos", "configuracoes"],
    "starter":  ["orcamentos", "clientes", "catalogo", "documentos", "configuracoes", "relatorios", "financeiro", "equipe", "lembretes"],
    "pro":      ["orcamentos", "clientes", "catalogo", "documentos", "configuracoes", "relatorios", "financeiro", "equipe", "lembretes", "ia", "whatsapp_proprio"],
    "business": ["orcamentos", "clientes", "catalogo", "documentos", "configuracoes", "relatorios", "financeiro", "equipe", "lembretes", "ia", "whatsapp_proprio"],
}
```

**C) Seed de papéis padrão para CADA empresa existente:**

Para cada empresa que ainda NÃO tem papéis, criar os 3 papéis base:

```python
PAPEIS_PADRAO = [
    {
        "nome": "Gestor",
        "slug": "gestor",
        "descricao": "Acesso total ao sistema",
        "is_default": False,
        "is_sistema": True,
        "permissoes": []  # TODAS as permissões — será preenchido dinamicamente com base nos módulos do plano
    },
    {
        "nome": "Vendedor",
        "slug": "vendedor",
        "descricao": "Acesso a orçamentos, clientes e catálogo",
        "is_default": True,  # papel padrão para novos usuários
        "is_sistema": True,
        "permissoes": [
            "orcamentos:leitura", "orcamentos:escrita",
            "clientes:leitura", "clientes:escrita",
            "catalogo:leitura",
            "documentos:leitura",
        ]
    },
    {
        "nome": "Financeiro",
        "slug": "financeiro",
        "descricao": "Acesso ao módulo financeiro e relatórios",
        "is_sistema": True,
        "permissoes": [
            "financeiro:leitura", "financeiro:escrita", "financeiro:admin",
            "relatorios:leitura",
            "clientes:leitura",
            "orcamentos:leitura",
        ]
    },
]
```

**Lógica para o papel "Gestor":** gerar dinamicamente `["modulo:acao"]` para TODOS os módulos que o plano da empresa inclui, com TODAS as ações de cada módulo. Assim o gestor sempre tem acesso total ao que o plano permite.

**D) Associar usuários existentes ao papel correto:**

Após criar os papéis de cada empresa:
- Usuários que são dono/gestor da empresa → associar ao papel "Gestor"
- Demais usuários → associar ao papel "Vendedor" (is_default=True)
- Superadmins → não precisam de papel (bypass total)

**E) A função deve ser totalmente idempotente** — pode rodar N vezes sem duplicar dados. Usar upsert por slug.

### 2.2 Chamar seed no startup

Em `app/main.py`, no evento startup:

```python
@app.on_event("startup")
def startup():
    db = next(get_db())
    try:
        seed_modulos_e_planos_padrao(db)
    finally:
        db.close()
```

---

## PARTE 3 — Auth: exigir_modulo() e exigir_permissao() atualizado

### 3.1 Criar `exigir_modulo()` em `app/core/auth.py`

```python
def exigir_modulo(slug: str):
    """
    Dependency do FastAPI que verifica se o plano da empresa inclui o módulo.

    - Superadmin: passa sempre
    - Demais: verifica empresa.plano_id → plano.modulos
    - Fallback: se plano_id is None, verifica PLANO_CONFIG[empresa.plano] (legado)
    """
    def dependency(
        current_user: Usuario = Depends(get_usuario_atual),
        db: Session = Depends(get_db)
    ) -> Usuario:
        if current_user.is_superadmin:
            return current_user

        empresa = current_user.empresa

        # Novo sistema: verifica via plano_id
        if empresa.plano_id:
            plano = db.query(Plano).filter(Plano.id == empresa.plano_id).first()
            if plano:
                slugs_disponiveis = [m.slug for m in plano.modulos]
                if slug not in slugs_disponiveis:
                    raise HTTPException(
                        status_code=403,
                        detail=f"O módulo '{slug}' não está disponível no plano '{plano.nome}' da sua empresa."
                    )
            else:
                raise HTTPException(status_code=403, detail="Plano da empresa não encontrado.")
        else:
            # Fallback legado: PLANO_CONFIG
            _verificar_modulo_legado(slug, empresa)

        return current_user

    return dependency


def _verificar_modulo_legado(slug: str, empresa):
    """
    Fallback para empresas que ainda usam empresa.plano (string).
    Mapeia slugs para features do PLANO_CONFIG.
    """
    from app.services.plano_service import PLANO_CONFIG

    plano_str = empresa.plano or "trial"
    config = PLANO_CONFIG.get(plano_str, PLANO_CONFIG["trial"])

    # Mapeamento slug → feature do PLANO_CONFIG
    SLUG_TO_FEATURE = {
        "ia": "ia_automatica",
        "relatorios": "relatorios",
        "whatsapp_proprio": "whatsapp_proprio",
        "equipe": "max_usuarios",  # se max_usuarios > 1
        "financeiro": "relatorios",  # financeiro segue mesma regra de relatórios no legado
        "lembretes": "relatorios",
    }

    feature = SLUG_TO_FEATURE.get(slug)
    if feature:
        valor = config.get(feature, False)
        if valor is False or valor == 0:
            raise HTTPException(
                status_code=403,
                detail=f"O módulo '{slug}' não está disponível no seu plano atual."
            )
    # Módulos que não estão no mapeamento são considerados disponíveis em todos os planos (ex: orcamentos, clientes)
```

### 3.2 Atualizar `exigir_permissao()` em `app/core/auth.py`

A função `exigir_permissao` já existe. **Atualizar** para buscar permissões do papel do usuário, com fallback para o JSON legado:

```python
def exigir_permissao(recurso: str, acao: str):
    """
    Dependency do FastAPI que verifica se o usuário tem permissão granular.

    Ordem de verificação:
    1. Superadmin → passa sempre
    2. Dono/gestor da empresa → passa sempre (verificar como está implementado)
    3. Se usuario.papel_id existe → verifica papel.permissoes
    4. Fallback: se papel_id is None → verifica usuario.permissoes (JSON legado)
    """
    def dependency(
        current_user: Usuario = Depends(get_usuario_atual),
        db: Session = Depends(get_db)
    ) -> Usuario:
        if current_user.is_superadmin:
            return current_user

        # Verificar se é dono/gestor — manter lógica existente
        # (ler o código atual para ver como isso é feito)

        permissao_necessaria = f"{recurso}:{acao}"

        # Novo sistema: verifica via papel
        if current_user.papel_id and current_user.papel:
            if permissao_necessaria in (current_user.papel.permissoes or []):
                return current_user
            raise HTTPException(
                status_code=403,
                detail=f"Você não tem permissão para '{acao}' em '{recurso}'. Fale com o gestor da empresa."
            )

        # Fallback legado: JSON no usuario.permissoes
        # MANTER A LÓGICA EXISTENTE AQUI — apenas adicionar o bloco acima antes
        # Copiar o código atual que já funciona

        raise HTTPException(status_code=403, detail="Permissão negada.")

    return dependency
```

**IMPORTANTE:** Ler o código atual de `exigir_permissao()` antes de editar. Preservar toda a lógica existente como fallback. O novo código (verificação via papel) é adicionado ANTES do fallback, não substitui.

### 3.3 Uso nos endpoints (exemplo)

```python
@router.get("/financeiro/dashboard")
async def dashboard_financeiro(
    current_user: Usuario = Depends(exigir_modulo("financeiro")),
    _: Usuario = Depends(exigir_permissao("financeiro", "leitura")),
    db: Session = Depends(get_db)
):
    ...

@router.delete("/financeiro/contas/{id}")
async def deletar_conta(
    id: int,
    current_user: Usuario = Depends(exigir_modulo("financeiro")),
    _: Usuario = Depends(exigir_permissao("financeiro", "exclusao")),
    db: Session = Depends(get_db)
):
    ...
```

**NÃO aplicar `exigir_modulo` e `exigir_permissao` em rotas existentes nesta fase.** Apenas criar as functions. A aplicação em rotas será feita gradualmente depois.

---

## PARTE 4 — Atualizar plano_service.py (Fallback com plano_id)

No arquivo `app/services/plano_service.py`, atualizar as funções existentes para suportar o novo sistema:

### 4.1 `ia_automatica_habilitada(empresa, db)`

```python
def ia_automatica_habilitada(empresa, db=None):
    # Novo sistema: verifica via plano_id
    if empresa.plano_id and db:
        plano = db.query(Plano).filter(Plano.id == empresa.plano_id).first()
        if plano:
            return any(m.slug == "ia" for m in plano.modulos)
        return False

    # Fallback legado
    config = PLANO_CONFIG.get(empresa.plano or "trial", PLANO_CONFIG["trial"])
    return config.get("ia_automatica", False)
```

### 4.2 Aplicar o mesmo padrão para:

- `relatorios_habilitados()` → verifica slug `"relatorios"`
- `whatsapp_proprio_habilitado()` → verifica slug `"whatsapp_proprio"`
- Qualquer outra função similar

Manter o parâmetro `db` opcional para compatibilidade. Se `db` não for passado, cai no fallback legado.

---

## PARTE 5 — Schemas Pydantic

### 5.1 Schemas do Papel

Em `app/schemas/schemas.py`:

```python
class PapelBase(BaseModel):
    nome: str
    descricao: Optional[str] = None
    permissoes: List[str] = []  # ["modulo:acao", ...]
    is_default: bool = False

class PapelCreate(PapelBase):
    pass

class PapelUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    permissoes: Optional[List[str]] = None
    is_default: Optional[bool] = None
    ativo: Optional[bool] = None

class PapelOut(PapelBase):
    id: int
    slug: str
    is_sistema: bool
    ativo: bool
    empresa_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class PapelResumo(BaseModel):
    """Versão resumida para exibição em listas de usuários"""
    id: int
    nome: str
    slug: str

    class Config:
        from_attributes = True
```

### 5.2 Schemas auxiliares

```python
class ModuloComAcoes(BaseModel):
    """Para o frontend montar a tela de configuração de papéis"""
    id: int
    nome: str
    slug: str
    acoes: List[str]

    class Config:
        from_attributes = True

class AtribuirPapelRequest(BaseModel):
    """Para atribuir papel a um usuário"""
    papel_id: int
```

### 5.3 Atualizar UsuarioOut

Adicionar o campo `papel` ao schema de saída do usuário:

```python
# No UsuarioOut existente, adicionar:
papel: Optional[PapelResumo] = None
```

---

## PARTE 6 — Router de Papéis

### 6.1 Criar `app/routers/papeis.py`

```python
# Endpoints:

# GET /papeis
# Lista papéis da empresa do usuário logado
# Permissão: qualquer usuário autenticado (para exibir em selects)

# GET /papeis/{id}
# Detalhe de um papel
# Permissão: qualquer usuário autenticado

# POST /papeis
# Criar novo papel na empresa do usuário
# Permissão: gestor/dono da empresa
# Body: PapelCreate
# Lógica:
#   - Gerar slug a partir do nome (slugify)
#   - Validar que permissoes contêm apenas "modulo:acao" onde modulo existe e acao está nas acoes do módulo
#   - Validar que o módulo referenciado está no plano da empresa
#   - Salvar

# PUT /papeis/{id}
# Atualizar papel
# Permissão: gestor/dono da empresa
# Body: PapelUpdate
# Regra: papéis com is_sistema=True podem ter permissões editadas, mas não podem ser renomeados ou excluídos

# DELETE /papeis/{id}
# Desativar papel (soft delete via ativo=False)
# Permissão: gestor/dono da empresa
# Regra: não pode excluir papel com is_sistema=True
# Regra: não pode excluir papel que tem usuários ativos associados (retornar erro com lista de usuários)

# PUT /papeis/{id}/usuarios/{usuario_id}
# Atribuir papel a um usuário
# Permissão: gestor/dono da empresa
# Regra: o usuário deve pertencer à mesma empresa

# GET /papeis/modulos-disponiveis
# Retorna lista de módulos do plano da empresa com suas ações
# Usado pelo frontend para montar a tela de checkboxes
# Response: List[ModuloComAcoes]
```

### 6.2 Registrar router em `app/main.py`

```python
from app.routers import papeis
app.include_router(papeis.router, prefix="/papeis", tags=["Papéis"])
```

---

## PARTE 7 — Frontend: Tela de Gerenciamento de Papéis

### 7.1 Adicionar seção na tela de equipe existente

Verificar se existe `cotte-frontend/equipe.html` ou tela similar de gestão de equipe. Adicionar uma **aba ou seção "Papéis e Permissões"** nessa tela.

**Se não existir tela de equipe, criar `cotte-frontend/papeis.html`** e adicionar link no menu lateral.

### 7.2 Layout da tela

A tela deve ter:

**A) Lista de papéis** (lado esquerdo ou como cards):
- Nome do papel + badge "Sistema" se is_sistema=True
- Quantidade de usuários com este papel
- Botão editar / excluir (excluir desabilitado para papéis sistema)
- Botão "+ Novo Papel"

**B) Editor de permissões** (ao clicar em um papel):
- Modal ou painel lateral
- Título: "Permissões do papel: {nome}"
- Organizado por módulo:
  - Nome do módulo como header do grupo
  - Checkboxes para cada ação: ☐ Leitura ☐ Escrita ☐ Exclusão ☐ Admin
  - Toggle "Selecionar todas" por módulo
- Botão "Salvar"

**C) Fetch de dados:**
- `GET /papeis` → lista os papéis
- `GET /papeis/modulos-disponiveis` → lista módulos com ações para montar os checkboxes
- `PUT /papeis/{id}` → salvar permissões
- `POST /papeis` → criar novo papel

### 7.3 Estilo

Seguir exatamente o mesmo padrão visual das outras telas do COTTE (procurar em `cotte-frontend/` e copiar classes CSS, gradientes, cards, modais, etc.).

### 7.4 Atribuição de papel na tela de usuários

Na tela onde se gerencia membros da equipe (verificar qual é), adicionar um **select/dropdown de papel** ao lado de cada usuário. Ao mudar, chamar `PUT /papeis/{papel_id}/usuarios/{usuario_id}`.

---

## PARTE 8 — NÃO FAZER (escopo de manutenção futura)

Para manter esta implementação enxuta e segura, **NÃO faça nada abaixo agora**:

- ❌ NÃO aplicar `exigir_modulo()` ou `exigir_permissao()` em rotas existentes — isso será feito gradualmente depois
- ❌ NÃO remover o PLANO_CONFIG do plano_service.py — ele é o fallback
- ❌ NÃO remover o campo `usuario.permissoes` (JSON legado) — continua como fallback
- ❌ NÃO remover o campo `empresa.plano` (string legado) — continua como fallback
- ❌ NÃO alterar migrations antigas
- ❌ NÃO alterar contratos de API existentes
- ❌ NÃO alterar o admin-planos.html nesta fase

---

## Checklist de Execução

Execute na seguinte ordem:

1. [ ] Ler toda a estrutura do projeto e entender padrões existentes
2. [ ] Ler `app/models/models.py` — verificar campos exatos de `ModuloSistema`, `Plano`, `Usuario`, `Empresa`, tabela associativa `plano_modulo`
3. [ ] Ler `app/core/auth.py` — entender `get_usuario_atual`, `exigir_permissao`, lógica de superadmin/gestor
4. [ ] Ler `app/services/plano_service.py` — entender PLANO_CONFIG e funções existentes
5. [ ] Adicionar campo `acoes` (JSON) ao modelo `ModuloSistema` (se não existir)
6. [ ] Criar modelo `Papel` em `app/models/models.py`
7. [ ] Adicionar campo `papel_id` (FK, nullable) ao modelo `Usuario`
8. [ ] Adicionar relationships inversas (`empresa.papeis`, `usuario.papel`)
9. [ ] Criar migration Alembic e rodar
10. [ ] Criar `app/services/seed_modulos.py` com toda a lógica de seed idempotente
11. [ ] Chamar seed no startup do `app/main.py`
12. [ ] Criar `exigir_modulo()` em `app/core/auth.py`
13. [ ] Atualizar `exigir_permissao()` em `app/core/auth.py` — adicionar verificação via papel ANTES do fallback legado
14. [ ] Atualizar funções do `plano_service.py` com fallback via plano_id
15. [ ] Criar schemas Pydantic para Papel
16. [ ] Atualizar UsuarioOut com campo `papel`
17. [ ] Criar `app/routers/papeis.py` com todos os endpoints
18. [ ] Registrar router em `app/main.py`
19. [ ] Criar tela frontend de gerenciamento de papéis
20. [ ] Adicionar dropdown de papel na tela de gestão de equipe
21. [ ] Testar: reiniciar app → verificar seed (11 módulos, 4 planos, papéis por empresa)
22. [ ] Testar: criar papel customizado → associar a usuário → verificar permissões
23. [ ] Testar: empresa sem plano_id → fallback legado deve funcionar normalmente
24. [ ] Verificar que NENHUMA rota existente foi quebrada

**IMPORTANTE:** A cada etapa, testar se o código compila e não quebra nada existente. Manter compatibilidade total com os fluxos atuais.

---

## Verificação Final

1. Reiniciar app → tabela `modulos_sistema` deve ter 11 módulos com campo `acoes`
2. Tabela `planos` deve ter 4 planos com módulos corretos associados
3. Tabela `papeis` deve ter 3 papéis para cada empresa existente
4. Cada usuário existente deve ter `papel_id` preenchido (gestor ou vendedor)
5. `admin-planos.html` → modal "Gerenciar Módulos" continua funcionando normalmente
6. Criar empresa nova com plano_id=pro → deve criar os 3 papéis automaticamente
7. Testar `exigir_modulo("ia")`:
   - Empresa com plano pro → deve passar
   - Empresa com plano trial → deve retornar 403
8. Testar `exigir_permissao("financeiro", "escrita")`:
   - Usuário com papel "Gestor" → deve passar
   - Usuário com papel "Vendedor" → deve retornar 403
9. Testar fallback: empresa sem plano_id → deve usar PLANO_CONFIG normalmente
10. Testar fallback: usuário sem papel_id → deve usar JSON legado normalmente
