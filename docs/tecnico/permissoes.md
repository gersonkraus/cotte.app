---
title: Permissoes
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Mapa Técnico - Permissões e Acesso (COTTE)
tags:
  - tecnico
  - seguranca
  - permissoes
  - backend
prioridade: alta
status: documentado
---

# Mapa Técnico: Permissões e Acesso (COTTE)

## 1. Entrada do Fluxo

O fluxo tem **3 pontos de entrada** distintos:

### A) Login (aquisição de token)
- **Frontend:** `sistema/cotte-frontend/login.html:1128` — função `fazerLogin()`
- **Backend:** `POST /api/v1/auth/login` → `sistema/app/routers/auth_clientes.py:257`

### B) Validação de token (toda requisição autenticada)
- **Backend:** `sistema/app/core/auth.py:34` — função `get_usuario_atual()` (dependência FastAPI)

### C) Verificação de permissão granular (cada endpoint protegido)
- **Backend:** `sistema/app/core/auth.py:102` — função `exigir_permissao(recurso, acao)` (dependência FastAPI)

### D) Proteção de UI (frontend)
- **Frontend:** `sistema/cotte-frontend/js/api.js:501` — objeto `window.Permissoes`

---

## 2. Caminho Completo dos Arquivos

### Backend

| Arquivo | Função/Responsabilidade |
|---------|------------------------|
| `sistema/app/models/models.py:329-358` | `Usuario` — campos `is_superadmin`, `is_gestor`, `permissoes` (JSON), `token_versao` |
| `sistema/app/schemas/schemas.py:859-861` | `TokenOut` — resposta do login |
| `sistema/app/schemas/schemas.py:890-900` | `UsuarioOut` — inclui `permissoes: dict` |
| `sistema/app/schemas/schemas.py:971-982` | `UsuarioEmpresaUpdate` — campo `permissoes: Optional[dict]` |
| `sistema/app/core/auth.py:1-173` | Toda lógica de autenticação e autorização |
| `sistema/app/routers/auth_clientes.py:46-364` | Login, registro, /me, reset senha |
| `sistema/app/routers/admin.py:40-840` | CRUD empresas/usários (superadmin) |
| `sistema/app/routers/empresa.py:32-695` | CRUD usuários da empresa, configs |
| `sistema/app/routers/orcamentos.py` | 25 endpoints com `exigir_permissao` |
| `sistema/app/routers/financeiro.py` | 50+ endpoints com `exigir_permissao` |
| `sistema/app/routers/catalogo.py` | 15 endpoints com `exigir_permissao` |
| `sistema/app/routers/clientes.py` | 9 endpoints com `exigir_permissao` |
| `sistema/app/routers/documentos.py` | 7 endpoints com `exigir_permissao` |
| `sistema/app/routers/comercial_import.py` | 4 endpoints com `exigir_permissao("comercial")` |
| `sistema/app/routers/comercial_templates.py` | 6 endpoints com `exigir_permissao("comercial")` |
| `sistema/app/routers/comercial_campaigns.py` | 8 endpoints com `exigir_permissao("comercial")` |
| `sistema/app/routers/ai_hub.py` | 23 endpoints com `exigir_permissao("ia")` |
| `sistema/app/routers/relatorios.py` | 1 endpoint com `exigir_permissao("relatorios")` |

### Frontend

| Arquivo | Função/Responsabilidade |
|---------|------------------------|
| `sistema/cotte-frontend/js/api.js:85-142` | Intercepta 401, `requireAuth()`, `logout()`, `salvarSessao()` |
| `sistema/cotte-frontend/js/api.js:495-530` | `window.Permissoes.pode()` e `protegerUI()` |
| `sistema/cotte-frontend/js/layout.js:284-303` | Remove itens de menu baseado em `Permissoes.pode()` |
| `sistema/cotte-frontend/login.html:1128-1172` | `fazerLogin()` — chama POST /auth/login, depois GET /auth/me |

---

## 3. Sequência de Chamadas

### Fluxo A — Login

```
login.html:fazerLogin()
  → POST /api/v1/auth/login {email, senha}
    → auth_clientes.py:login()
      → verificar_senha(senha, hash)    [app/core/auth.py:23]
      → usuario.token_versao += 1       [invalida tokens anteriores]
      → criar_token({"sub": id, "empresa_id": eid, "v": versao})  [app/core/auth.py:27]
      → return {access_token}
  → GET /api/v1/auth/me  (com Bearer token)
    → get_usuario_atual()               [app/core/auth.py:34]
      → jwt.decode(token) → payload.sub = usuario_id
      → db.query(Usuario).filter(id==usuario_id, ativo==True)
      → verifica token_versao (sessão única)
      → verifica empresa.ativo
      → verifica assinatura_valida_ate + 3 dias de graça
      → atualiza ultima_atividade_em
      → return Usuario
  → salvarSessao(token, usuario)         [localStorage]
```

### Fluxo B — Requisição autenticada com permissão

```
Frontend: api.get('/orcamentos/123')
  → Authorization: Bearer <token>
    → FastAPI Dependency Chain:
      exigir_permissao("orcamentos", "leitura")  [auth.py:102]
        → get_usuario_atual()                    [auth.py:34]
          → jwt.decode → query usuario → valida token_versao → valida empresa
        → if is_superadmin: return (bypass total)
        → if is_gestor: return (bypass total)
        → perms = usuario.permissoes or {}
        → user_acao = perms.get("orcamentos")
        → if !user_acao && recurso in ["equipe","configuracoes"]: 403
        → if !user_acao: 403
        → niveis = {leitura:1, meus:1.5, escrita:2, admin:3}
        → if niveis[user_acao] < niveis[acao]: 403
        → return usuario
    → endpoint handler(usuario=usuario_autorizado)
```

### Fluxo C — Frontend protege UI

```
layout.js:inicializarLayout(pageKey)
  → requireAuth() → redirect se sem token
  → Permissoes.pode("orcamentos") → hide nav item se false
  → Permissoes.pode("financeiro") → hide nav item se false
  → ... (8 recursos verificados)
  → if is_superadmin: mostra links admin
```

### Fluxo D — Gestor altera permissões de um usuário

```
empresa.html → PATCH /api/v1/empresa/usuarios/{id} {permissoes: {...}}
  → empresa.py:atualizar_usuario_empresa()
    → exigir_permissao("equipe", "escrita")
    → verifica usuario.is_gestor (só gestor pode alterar permissoes/ativo)
    → setattr(alvo, "permissoes", novo_dict)
    → db.commit()
    → registrar_auditoria("usuario_permissao_alterada")
```

---

## 4. Estruturas de Dados Envolvidas

### JWT Payload

```json
{"sub": "<usuario_id>", "empresa_id": 42, "v": 5, "exp": 1711234567}
```

### Usuario.permissoes (JSON column no banco)

```json
{
  "orcamentos": "escrita",
  "clientes": "escrita",
  "catalogo": "leitura",
  "documentos": "leitura",
  "relatorios": "leitura",
  "ia": "leitura"
}
```

### Níveis hierárquicos

```
leitura (1) < meus (1.5) < escrita (2) < admin (3)
```

- `leitura` — apenas visualização
- `meus` — nível intermediário (definido mas não implementado em filtros)
- `escrita` — criação e edição
- `admin` — exclusão e operações críticas

### Recursos conhecidos

| Recurso | Onde é usado |
|---------|-------------|
| `orcamentos` | `routers/orcamentos.py` |
| `financeiro` | `routers/financeiro.py` |
| `clientes` | `routers/clientes.py` |
| `catalogo` | `routers/catalogo.py` |
| `documentos` | `routers/documentos.py` |
| `relatorios` | `routers/relatorios.py` |
| `ia` | `routers/ai_hub.py` |
| `equipe` | `routers/empresa.py` |
| `configuracoes` | `routers/empresa.py` |
| `comercial` | `routers/comercial_*.py` |

### Permissões padrão ao criar usuário pela empresa

**Arquivo:** `sistema/app/routers/empresa.py:224-231`

```python
permissoes = {
    "orcamentos": "escrita",
    "clientes": "escrita",
    "catalogo": "leitura",
    "documentos": "leitura",
    "relatorios": "leitura",
    "ia": "leitura",
}
```

Nota: `financeiro`, `equipe`, `configuracoes` e `comercial` **não são incluídos** por padrão, ficando bloqueados.

---

## 5. Regras de Negócio Encontradas

| Regra | Local | Descrição |
|-------|-------|-----------|
| Superadmin bypass total | `auth.py:112-113` | `is_superadmin=True` ignora toda verificação de permissão |
| Gestor bypass total | `auth.py:116-117` | `is_gestor=True` ignora verificação granular |
| Sessão única | `auth.py:60-62`, `auth_clientes.py:278-279` | `token_versao` incrementado a cada login; tokens antigos invalidados |
| Empresa inativa bloqueia login | `auth_clientes.py:270-276` | Exceto superadmin |
| Assinatura expirada | `auth.py:71-81` | Bloqueia acesso após 3 dias de tolerância (402 Payment Required) |
| Recursos restritos | `auth.py:125-129` | `equipe` e `configuracoes` bloqueados por padrão para usuários sem permissão explícita |
| Gestor pode alterar permissões | `empresa.py:273-279` | Somente `is_gestor` pode alterar `permissoes` e `ativo` de outros usuários |
| Usuário não pode inativar a si mesmo | `empresa.py:280-283` | Validação no router |
| Primeiro usuário é gestor | `auth_clientes.py:90`, `admin.py:269` | Fundador da empresa e primeiro usuário criado pelo admin são gestores |
| Ownership por empresa (tenant) | `auth.py:155-173` | `verificar_ownership()` existe mas **não é usado nos routers atuais** |
| is_gestor só via superadmin | `empresa.py:272` | `payload.pop("is_gestor", None)` remove do update pela empresa |

---

## 6. Problemas de Arquitetura

### 6.1 — `verificar_ownership()` existe mas NÃO é usado

**Arquivo:** `sistema/app/core/auth.py:155-173`

A função `verificar_ownership(obj, usuario)` foi criada para garantir isolamento de tenant (empresa não acessa dados de outra), mas **nenhum router a chama**. O isolamento de empresa depende apenas de que os endpoints filtram por `usuario.empresa_id` manualmente. Se alguém esquecer o filtro, não há proteção automática.

### 6.2 — Permissões granulares ignoradas para gestores e superadmins

**Arquivo:** `sistema/app/core/auth.py:112-117`

`is_gestor=True` dá bypass total. Não existe forma de um gestor ter permissões parciais. Se uma empresa quiser um "gestor de vendas" (sem acesso a financeiro), o modelo atual não suporta.

### 6.3 — Duplicação: validação de login em dois lugares

**Arquivo 1:** `sistema/app/routers/auth_clientes.py:263-276` (verifica `usuario.ativo` e `empresa.ativo`)
**Arquivo 2:** `sistema/app/core/auth.py:52-69` (verifica `usuario.ativo` e `empresa.ativo` no `get_usuario_atual`)

A mesma validação de "empresa inativa" e "assinatura expirada" existe em dois pontos. Se alguém alterar apenas um, cria inconsistência.

### 6.4 — `db.commit()` em `get_usuario_atual()` a cada request

**Arquivo:** `sistema/app/core/auth.py:83-90`

Toda requisição autenticada faz um `db.commit()` para atualizar `ultima_atividade_em`. Isso:
- Gera escrita no banco em cada leitura
- Pode causar conflitos em transações
- Não está protegido por try/except (se falhar, quebra a requisição)

### 6.5 — Frontend: permissões no localStorage são auto-declaradas

**Arquivo:** `sistema/cotte-frontend/js/api.js:122-126`, `sistema/cotte-frontend/login.html:1150-1152`

O objeto `usuario` (incluindo `permissoes`) fica em `localStorage`. Se o gestor alterar permissões de um usuário, o frontend desse usuário continuará com permissões antigas até que:
- Faça logout/login novamente, OU
- `atualizarUsuarioLocal()` seja chamado (`api.js:487-492`)

Não há mecanismo automático de invalidação de cache de permissões.

### 6.6 — Testes inexistentes para o módulo de permissões

**Diretório:** `sistema/tests/`

A busca por testes de `exigir_permissao` ou `permissoes` encontrou apenas 1 referência em `test_comercial.py:67`, e é um comentário. Não existem testes unitários cobrindo:
- Os diferentes níveis de permissão
- O bypass de superadmin/gestor
- O bloqueamento de recursos restritos
- A verificação de token_versao

### 6.7 — Recurso "comercial" não mapeado no frontend

**Backend:** `comercial_import.py`, `comercial_templates.py`, `comercial_campaigns.py` usam `exigir_permissao("comercial", ...)`
**Frontend:** `layout.js:284-295` NÃO verifica `pode("comercial")` — o item de menu comercial não é protegido por permissão no frontend.

### 6.8 — Nível "meus" definido mas não implementado

**Arquivo:** `sistema/app/core/auth.py:140`

O nível `"meus": 1.5` existe no mapa de níveis, mas nenhum endpoint filtra registros "apenas do próprio usuário" quando `user_acao == "meus"`. Apenas bloqueia escrita via comparação numérica.

---

## 7. Melhor Ponto para Alterar com Segurança

**`sistema/app/core/auth.py`** é o ponto único e mais seguro para alterações no sistema de permissões.

### Motivos:
1. Todas as 157+ rotas protegidas dependem de `exigir_permissao()` — mudanças aqui afetam tudo uniformemente
2. `get_usuario_atual()` é a dependência base — qualquer reforço de autenticação deve ser feito aqui
3. O modelo de dados (`permissoes` JSON column em `Usuario`) é flexível o suficiente para novos recursos sem migration
4. O frontend espelha a mesma lógica em `api.js:501-530` — alterações no backend devem ser refletidas lá

### Pontos secundários para alteração coordenada:
- `sistema/app/routers/empresa.py:248-331` — onde gestores editam permissões de usuários
- `sistema/cotte-frontend/js/api.js:495-530` — lógica espelhada de RBAC no frontend
- `sistema/cotte-frontend/js/layout.js:284-303` — proteção visual de itens de menu

---

## Resumo Visual do Fluxo

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                  │
│                                                                  │
│  login.html:fazerLogin()                                        │
│    → POST /auth/login → salva token no localStorage             │
│    → GET /auth/me → salva usuario (com permissoes) no LS        │
│                                                                  │
│  layout.js:inicializarLayout()                                  │
│    → requireAuth() → redirect se sem token                      │
│    → Permissoes.pode(recurso) → hide/mostra itens de menu       │
│                                                                  │
│  api.js:apiRequest()                                            │
│    → adiciona Authorization: Bearer token                       │
│    → se 401: logout() + redirect login.html                     │
│                                                                  │
│  api.js:window.Permissoes.pode(recurso, acao)                  │
│    → lê usuario do localStorage                                 │
│    → is_superadmin/is_gestor → true                             │
│    → compara niveis: {leitura:1, meus:1.5, escrita:2, admin:3} │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS + Bearer JWT
┌───────────────────────────▼─────────────────────────────────────┐
│                        BACKEND                                    │
│                                                                  │
│  get_usuario_atual()  [core/auth.py:34]                         │
│    → jwt.decode() → extrai usuario_id                           │
│    → query Usuario por id + ativo=True                          │
│    → valida token_versao (sessão única)                         │
│    → valida empresa.ativo                                       │
│    → valida assinatura_valida_ate + 3 dias graça               │
│    → atualiza ultima_atividade_em + commit                      │
│    → return Usuario                                             │
│                                                                  │
│  exigir_permissao(recurso, acao)  [core/auth.py:102]           │
│    → chama get_usuario_atual()                                  │
│    → if is_superadmin: return (bypass)                          │
│    → if is_gestor: return (bypass)                              │
│    → perms = usuario.permissoes (JSON)                          │
│    → user_acao = perms[recurso]                                 │
│    → if recurso in ["equipe","configuracoes"] sem permissao: 403│
│    → if !user_acao: 403                                         │
│    → if niveis[user_acao] < niveis[acao]: 403                   │
│    → return Usuario                                             │
│                                                                  │
│  verificar_ownership(obj, usuario)  [core/auth.py:155]          │
│    → NÃO CHAMADO por nenhum router                              │
│    → verificaria empresa_id do objeto vs usuario.empresa_id     │
└─────────────────────────────────────────────────────────────────┘
```
