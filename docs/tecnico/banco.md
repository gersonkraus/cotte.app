---
title: Banco
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: MAPA TÉCNICO - Banco de Dados (SaaS COTTE)
tags:
  - tecnico
  - banco
  - database
  - arquitetura
prioridade: alta
status: documentado
---

# MAPA TÉCNICO: Estrutura de Modelagem do Banco de Dados (SaaS COTTE)

> Gerado em: 2026-03-23
> Escopo: Mapeamento completo da arquitetura de banco de dados, multi-tenancy e fluxo SaaS

---

## 1. PONTO DE PARTIDA — Definição do Schema

O banco é definido em **duas camadas** que devem estar sincronizadas:

| Camada | Arquivo | Função |
|--------|---------|--------|
| **Models SQLAlchemy** | `sistema/app/models/models.py` (1524 linhas) | Define todas as 33 tabelas, enums, relationships |
| **Base declarativa** | `sistema/app/core/database.py:23` | `Base = declarative_base()` — único ponto de origem do metadata |
| **Schemas Pydantic** | `sistema/app/schemas/schemas.py` (1527 linhas) | Validação de entrada/saída HTTP |
| **Schemas Financeiro** | `sistema/app/schemas/financeiro.py` (599 linhas) | Schemas específicos do módulo financeiro |
| **Schemas Planos** | `sistema/app/schemas/plano.py` (70 linhas) | Schemas do módulo de planos |
| **Migrations** | `sistema/alembic/versions/` (~55 arquivos) | Histórico incremental de alterações |
| **env.py Alembic** | `sistema/alembic/env.py:11` | `from app.models import models` — carrega todos os models no metadata |

---

## 2. CAMINHO COMPLETO DOS ARQUIVOS

### Camada de Persistência

```
sistema/app/core/database.py          → Engine síncrono, SessionLocal, Base, get_db()
sistema/app/core/config.py            → Settings (DATABASE_URL, SECRET_KEY, etc.)
sistema/app/models/models.py          → TODOS os 33 models (tabela única)
sistema/app/models/__init__.py        → VAZIO (não re-exporta nada)
sistema/alembic/env.py                → Carrega metadata dos models para autogenerate
sistema/alembic/versions/001_initial_schema.py → Baseline: create_all(Base.metadata)
```

### Camada de Validação (Schemas)

```
sistema/app/schemas/schemas.py        → Schemas gerais (Clientes, Orçamentos, Usuários, Comercial, Admin)
sistema/app/schemas/financeiro.py     → Schemas financeiros (Contas, Pagamentos, Fluxo de Caixa)
sistema/app/schemas/plano.py          → Schemas de Módulos e Planos
sistema/app/schemas/notifications.py  → Schemas de notificações
```

### Camada de Negócio (Services)

```
sistema/app/services/subscription_service.py  → Lógica de planos, limites, módulos
sistema/app/services/financeiro_service.py    → Lógica financeira
sistema/app/services/plano_service.py         → CRUD de planos
sistema/app/services/catalogo_service.py      → Catálogo de serviços
sistema/app/services/cliente_service.py       → CRUD clientes
sistema/app/services/documentos_service.py    → Documentos da empresa
sistema/app/services/audit_service.py         → Audit logs
```

### Camada de Entrada HTTP (Routers)

```
sistema/app/routers/orcamentos.py     → CRUD orçamentos
sistema/app/routers/clientes.py       → CRUD clientes
sistema/app/routers/financeiro.py     → Módulo financeiro
sistema/app/routers/empresa.py        → Configurações da empresa
sistema/app/routers/admin.py          → Admin (superadmin)
sistema/app/routers/admin_planos.py   → Gestão de planos/módulos
sistema/app/routers/catalogo.py       → Catálogo de serviços
sistema/app/routers/documentos.py     → Documentos da empresa
sistema/app/routers/comercial.py      → CRM comercial
sistema/app/routers/whatsapp.py       → WhatsApp
sistema/app/routers/publico.py        → Página pública do orçamento
sistema/app/routers/auth_clientes.py  → Autenticação
sistema/app/routers/ai_hub.py         → Assistente IA
sistema/app/routers/webhooks.py       → Webhooks (Kiwify, etc.)
```

### Camada de Autenticação/Autorização

```
sistema/app/core/auth.py              → JWT, hash senha, get_usuario_atual, get_superadmin, exigir_permissao, verificar_ownership
```

### Frontend (Vanilla JS)

```
sistema/cotte-frontend/js/api.js             → Cliente HTTP centralizado (apiRequest, getApiBaseUrl)
sistema/cotte-frontend/js/api-financeiro.js  → Cliente HTTP para módulo financeiro
sistema/cotte-frontend/index.html            → Dashboard principal
sistema/cotte-frontend/financeiro.html       → Módulo financeiro
sistema/cotte-frontend/orcamentos.html       → Lista de orçamentos
sistema/cotte-frontend/configuracoes.html    → Configurações da empresa
sistema/cotte-frontend/admin.html            → Painel superadmin
sistema/cotte-frontend/admin-planos.html     → Gestão de planos
```

---

## 3. SEQUÊNCIA DE CHAMADAS (Fluxo SaaS Multi-tenant)

```
┌─────────────────────────────────────────────────────────────────┐
│ FRONTEND (Vanilla JS)                                           │
│ cotte-frontend/js/api.js → apiRequest(method, endpoint, body)   │
│ └─ Header: Authorization: Bearer {token}                        │
│ └─ URL: {API_URL}/api/v1/{endpoint}                             │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP Request
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ FASTAPI APP (sistema/app/main.py)                               │
│ └─ app.include_router(router, prefix="/api/v1")                 │
│ └─ Middleware: CORS → LoggingMiddleware → SecurityMiddleware     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ ROUTER (ex: app/routers/orcamentos.py)                          │
│ └─ Depends(get_db) → Session SQLAlchemy                         │
│ └─ Depends(get_usuario_atual) → Usuario autenticado             │
│ └─ Depend opcional: exigir_permissao("recurso", "acao")         │
│ └─ Validação Pydantic via schemas de entrada                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ SERVICE (ex: app/services/subscription_service.py)              │
│ └─ Lógica de negócio, cálculos, regras de multi-tenancy         │
│ └─ Acessa db.query(Model) com filtro empresa_id                 │
│ └─ Chama verificar_ownership(obj, usuario)                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ DATABASE (PostgreSQL via SQLAlchemy síncrono)                   │
│ └─ engine = create_engine(DATABASE_URL)                         │
│ └─ pool_pre_ping=True, pool_recycle=1800, pool_size=5           │
│ └─ SessionLocal = sessionmaker(...)                             │
│ └─ get_db() → yield session → close()                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. ESTRUTURAS DE DADOS ENVOLVIDAS

### Entidade Central: `Empresa` (Model: `models.py:153`)

- **Tabela:** `empresas`
- **PK:** `id` (Integer)
- **FK para Plano:** `plano_id` → `planos.id`
- **Relationships:** `usuarios`, `clientes`, `orcamentos`, `servicos`, `notificacoes`, `documentos`, `bancos_pix`
- **Campos SaaS críticos:**
  - `plano_id` (FK) + `plano` (String legado) — dual system
  - `limite_orcamentos_custom`, `limite_usuarios_custom` — overrides
  - `desativar_ia`, `desativar_lembretes`, `desativar_relatorios` — feature flags
  - `total_mensagens_ia`, `total_mensagens_whatsapp` — usage counters
  - `assinatura_valida_ate`, `trial_ate` — subscription dates
  - `whatsapp_proprio_ativo`, `evolution_instance` — WhatsApp integration

### Sistema de Planos (Models: `models.py:28-74`)

| Model | Tabela | Função |
|-------|--------|--------|
| `ModuloSistema` | `modulos_sistema` | Módulos do sistema (slug, nome, ativo) |
| `Plano` | `planos` | Pacotes com limites e preço |
| `PlanoModulo` | `plano_modulos` | M2M join table entre Planos e Módulos |

### Multi-tenancy Pattern

Todas as tabelas de dados têm `empresa_id` (FK → `empresas.id`):

| Tabela | Campo FK |
|--------|----------|
| `usuarios` | `empresa_id` |
| `clientes` | `empresa_id` |
| `orcamentos` | `empresa_id` |
| `servicos` | `empresa_id` |
| `contas_financeiras` | `empresa_id` |
| `documentos_empresa` | `empresa_id` |
| `categorias_catalogo` | `empresa_id` |
| `notificacoes` | `empresa_id` |
| `audit_logs` | `empresa_id` |
| `formas_pagamento_config` | `empresa_id` |
| `movimentacoes_caixa` | `empresa_id` |
| `categorias_financeiras` | `empresa_id` |
| `saldo_caixa_configs` | `empresa_id` |
| `templates_notificacao` | `empresa_id` |
| `configuracoes_financeiras` | `empresa_id` |
| `bancos_pix_empresa` | `empresa_id` |
| `lead_importacoes` | `empresa_id` |
| `campaigns` | `empresa_id` |
| `feedback_assistente` | `empresa_id` |

### Sistema Financeiro (Models: `models.py:1087-1313`)

| Model | Tabela | Função |
|-------|--------|--------|
| `FormaPagamentoConfig` | `formas_pagamento_config` | Formas de pagamento por empresa |
| `ContaFinanceira` | `contas_financeiras` | Contas a pagar/receber com parcelamento |
| `PagamentoFinanceiro` | `pagamentos_financeiros` | Registros de pagamento |
| `MovimentacaoCaixa` | `movimentacoes_caixa` | Entradas/saídas manuais |
| `CategoriaFinanceira` | `categorias_financeiras` | Categorias customizáveis |
| `SaldoCaixaConfig` | `saldo_caixa_configs` | Saldo inicial por empresa |
| `TemplateNotificacao` | `templates_notificacao` | Templates de mensagem financeira |
| `HistoricoCobranca` | `historico_cobrancas` | Histórico de cobranças enviadas |
| `ConfiguracaoFinanceira` | `configuracoes_financeiras` | Configurações financeiras por empresa |

---

## 5. REGRAS DE NEGÓCIO ENCONTRADAS

| Regra | Localização | Descrição |
|-------|-------------|-----------|
| **Multi-tenancy** | `app/core/auth.py:155-173` `verificar_ownership()` | Todo objeto deve pertencer à empresa do usuário |
| **Sessão única** | `app/core/auth.py:59-62` | `token_versao` invalida tokens de logins anteriores |
| **Bloqueio por assinatura** | `app/core/auth.py:63-81` | Empresa inativa ou assinatura expirada +3d bloqueia acesso |
| **Sweep startup** | `app/main.py:204-233` | No boot, bloqueia empresas com assinatura vencida |
| **Limite de orçamentos** | `app/services/subscription_service.py:42-63` | Verifica limite do plano/override antes de criar |
| **Limite de usuários** | `app/services/subscription_service.py:66-87` | Verifica limite do plano/override |
| **Acesso a módulos** | `app/services/subscription_service.py:24-39` | Verifica se plano inclui módulo (slug-based) |
| **Permissões granulares** | `app/core/auth.py:102-152` | JSON `permissoes` no Usuario com níveis: leitura/meus/escrita/admin |
| **Herança de limites** | `subscription_service.py:45-48` | Override individual (`limite_orcamentos_custom`) tem prioridade sobre plano |
| **Fallback legado** | `subscription_service.py:15-21` | Se `plano_id` é null, busca plano pelo nome string |

---

## 6. PROBLEMAS DE ARQUITETURA IDENTIFICADOS

### CRÍTICO: Model Monolith

- **`models.py` tem 1524 linhas** com TODOS os 33 models em um único arquivo
- Dificulta navegação, merge de branches e manutenção
- Cada novo módulo adiciona mais dezenas de linhas ao mesmo arquivo

### CRÍTICO: Schema Monolith

- **`schemas.py` tem 1527 linhas** com todos os schemas (exceto financeiro e plano que foram separados)
- Separação inconsistente: financeiro e planos têm arquivos próprios, mas comercial, admin, etc. estão em schemas.py

### MÉDIO: Sistema Dual de Planos

- `Empresa` tem **dois campos** para plano: `plano_id` (FK) + `plano` (String legado)
- `subscription_service.py` faz fallback por nome se `plano_id` for null
- Risco de inconsistência se alguém alterar `plano` string sem atualizar `plano_id`

### MÉDIO: create_all no Startup

- `app/main.py:196-197` chama `Base.metadata.create_all(conn)` no startup
- Isso **conflita com Alembic** se houver divergência entre models e schema real
- Em produção, deve confiar apenas no Alembic

### MÉDIO: Engine Síncrono

- `database.py` usa `create_engine` síncrono (não async)
- FastAPI suporta async nativamente, mas o código usa `db.query()` síncrono
- Limita throughput em alta concorrência

### MÉDIO: Sem Repository Layer

- Services acessam `db.query()` diretamente
- Não há abstração de acesso a dados (repository pattern)
- Dificulta testes unitários e troca de ORM

### MÉDIO: Models __init__.py Vazio

- `app/models/__init__.py` está vazio
- Para que Alembic e o app funcionem, é necessário importar models explicitamente
- `alembic/env.py:11` e `app/main.py:194` fazem `from app.models import models`
- Se alguém esquecer de importar em novo módulo, tabelas não aparecem no autogenerate

### MÉDIO: Commits no Auth

- `app/core/auth.py:90` faz `db.commit()` dentro de `get_usuario_atual()`
- Atualiza `ultima_atividade_em` a cada request autenticado
- Cria acoplamento entre autenticação e escrita no banco
- Pode causar dirty writes se houver rollback posterior

### BAIXO: Cascade Delete em Empresa

- `Empresa` tem `cascade="all, delete-orphan"` em `usuarios`, `clientes`, `orcamentos`, `servicos`, `notificacoes`, `documentos`, `bancos_pix`
- Deletar uma empresa deleta TUDO em cascata
- Não há soft-delete na empresa (campo `ativo` existe mas não é usado como soft-delete)

### BAIXO: JSON para Permissões

- `Usuario.permissoes = Column(JSON, default={})`
- Sem schema de validação no banco
- Depende apenas da validação no service/router

---

## 7. MELHOR PONTO PARA ALTERAR COM SEGURANÇA

### Para adicionar novo módulo SaaS:

1. **Criar model** em arquivo separado (ex: `app/models/novo_modulo.py`)
2. **Criar schemas** em `app/schemas/novo_modulo.py`
3. **Criar service** em `app/services/novo_modulo_service.py`
4. **Criar router** em `app/routers/novo_modulo.py`
5. **Registrar router** em `app/main.py` na lista `routers`
6. **Importar model** em `app/models/__init__.py` e no `alembic/versions/`
7. **Criar migration** com `alembic revision --autogenerate`
8. **Adicionar módulo** na tabela `modulos_sistema` via seed ou admin
9. **Vincular módulo** ao plano desejado via `plano_modulos`

### Para alterar model existente:

1. **Nunca alterar migrations antigas** — criar nova migration
2. **Manter backward compatibility** — campos novos devem ser nullable ou ter default
3. **Atualizar schema Pydantic** correspondente (Create, Update, Out)
4. **Testar com Alembic autogenerate** antes de aplicar
5. **Verificar impacto no frontend** — se a API mudou contrato

### Para alterar regras de multi-tenancy:

1. **Ponto central:** `app/core/auth.py` → `verificar_ownership()`
2. **Ponto de limites:** `app/services/subscription_service.py`
3. **Ponto de permissões:** `app/core/auth.py` → `exigir_permissao()`

### Para alterar fluxo financeiro:

1. **Service:** `app/services/financeiro_service.py`
2. **Router:** `app/routers/financeiro.py`
3. **Schemas:** `app/schemas/financeiro.py`
4. **Models:** `FormaPagamentoConfig`, `ContaFinanceira`, `PagamentoFinanceiro` em `models.py`

---

## RESUMO VISUAL DA ARQUITETURA

```
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │   (Railway)     │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │  SQLAlchemy     │
                    │  Engine Sync    │
                    │  database.py    │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────┴───────┐ ┌───┴────────┐ ┌──┴───────────┐
     │  models.py     │ │ schemas.py │ │ alembic/     │
     │  (33 models)   │ │ (validação)│ │ migrations/  │
     └────────┬───────┘ └───┬────────┘ └──┬───────────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────┴────────┐
                    │   Services      │
                    │   (business     │
                    │    logic)       │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │   Routers       │
                    │   (HTTP entry)  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────┴───────┐ ┌───┴────────┐ ┌──┴───────────┐
     │  Auth/Middleware│ │ Schemas    │ │ Frontend     │
     │  (JWT, perms)  │ │ (Pydantic) │ │ (Vanilla JS) │
     └────────────────┘ └────────────┘ └──────────────┘
```

---

## ÍNDICE DE TABELAS DO BANCO (33 tabelas)

| # | Tabela | Model | Linha no models.py |
|---|--------|-------|-------------------|
| 1 | `modulos_sistema` | `ModuloSistema` | 28 |
| 2 | `planos` | `Plano` | 42 |
| 3 | `plano_modulos` | `PlanoModulo` | 67 |
| 4 | `empresas` | `Empresa` | 153 |
| 5 | `bancos_pix_empresa` | `BancoPIXEmpresa` | 290 |
| 6 | `usuarios` | `Usuario` | 326 |
| 7 | `audit_logs` | `AuditLog` | 361 |
| 8 | `clientes` | `Cliente` | 385 |
| 9 | `config_global` | `ConfigGlobal` | 425 |
| 10 | `categorias_catalogo` | `CategoriaCatalogo` | 435 |
| 11 | `servicos` | `Servico` | 448 |
| 12 | `documentos_empresa` | `DocumentoEmpresa` | 469 |
| 13 | `orcamento_documentos` | `OrcamentoDocumento` | 533 |
| 14 | `orcamentos` | `Orcamento` | 587 |
| 15 | `itens_orcamento` | `ItemOrcamento` | 730 |
| 16 | `historico_edicoes` | `HistoricoEdicao` | 759 |
| 17 | `notificacoes` | `Notificacao` | 779 |
| 18 | `log_email_orcamento` | `LogEmailOrcamento` | 800 |
| 19 | `pipeline_stages` | `PipelineStage` | 830 |
| 20 | `commercial_segments` | `CommercialSegment` | 925 |
| 21 | `commercial_lead_sources` | `CommercialLeadSource` | 939 |
| 22 | `commercial_templates` | `CommercialTemplate` | 956 |
| 23 | `commercial_reminders` | `CommercialReminder` | 975 |
| 24 | `commercial_config` | `CommercialConfig` | 998 |
| 25 | `commercial_leads` | `CommercialLead` | 1015 |
| 26 | `commercial_interactions` | `CommercialInteraction` | 1065 |
| 27 | `formas_pagamento_config` | `FormaPagamentoConfig` | 1087 |
| 28 | `contas_financeiras` | `ContaFinanceira` | 1134 |
| 29 | `pagamentos_financeiros` | `PagamentoFinanceiro` | 1200 |
| 30 | `templates_notificacao` | `TemplateNotificacao` | 1256 |
| 31 | `historico_cobrancas` | `HistoricoCobranca` | 1273 |
| 32 | `configuracoes_financeiras` | `ConfiguracaoFinanceira` | 1294 |
| 33 | `movimentacoes_caixa` | `MovimentacaoCaixa` | 1319 |
| 34 | `categorias_financeiras` | `CategoriaFinanceira` | 1342 |
| 35 | `saldo_caixa_configs` | `SaldoCaixaConfig` | 1373 |
| 36 | `lead_importacoes` | `LeadImportacao` | 1393 |
| 37 | `lead_importacao_itens` | `LeadImportacaoItem` | 1413 |
| 38 | `campaigns` | `Campaign` | 1442 |
| 39 | `campaign_leads` | `CampaignLead` | 1466 |
| 40 | `feedback_assistente` | `FeedbackAssistente` | 1490 |
| 41 | `broadcasts` | `Broadcast` | 1511 |
