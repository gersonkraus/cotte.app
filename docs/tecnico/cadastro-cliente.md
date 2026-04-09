---
title: Cadastro Cliente
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Mapa Técnico - Cadastro de Clientes (COTTE)
tags:
  - tecnico
  - frontend
  - clientes
  - mapa
prioridade: media
status: documentado
---

# Mapa Técnico — Cadastro de Clientes (COTTE)

Data: 2026-03-23
Autor: Análise arquitetônica automatizada

---

## 1. Entrada do Fluxo

**URL base:** `POST /api/v1/clientes/`

### Fluxo Principal (CRUD via painel)
- Acesso via `clientes.html` → `js/clientes.js` → `api.post('/clientes/', payload)`

### Fluxos Alternativos
- **Fluxo 2 — WhatsApp (IA):** Router `orcamentos.py` cria clientes inline no contexto de orçamento por IA (linhas ~300-310 e ~845-856), **sem passar pelo ClienteService**
- **Fluxo 3 — Buscar ou Criar:** Endpoint `POST /clientes/buscar-ou-criar/` usa `ClienteService.buscar_ou_criar_cliente()`
- **Fluxo 4 — CSV Export:** Endpoint `GET /clientes/exportar/csv` faz query direta ao DB (sem service)

---

## 2. Caminho Completo dos Arquivos

### Frontend
```
sistema/cotte-frontend/clientes.html        ← Página HTML (tabela + modal)
sistema/cotte-frontend/js/clientes.js        ← Lógica JS (render, CRUD, máscaras, CEP/CNPJ)
sistema/cotte-frontend/js/api.js             ← Cliente HTTP (token, requisições, auth)
```

### Backend
```
sistema/app/main.py                          ← Monta routers (linha 140: clientes_router → /api/v1)
sistema/app/routers/clientes.py              ← 8 endpoints (CRUD + CSV + stats + buscar-ou-criar)
sistema/app/routers/auth_clientes.py         ← Registro público de usuários (não de clientes do painel)
sistema/app/api/deps.py                      ← Injeção de dependência: get_cliente_service()
sistema/app/core/auth.py                     ← exigir_permissao() — RBAC granular
sistema/app/core/exceptions.py               ← ClienteNotFoundException, ClienteDuplicadoException
sistema/app/services/cliente_service.py      ← Lógica de negócio (7 métodos)
sistema/app/repositories/cliente_repository.py ← Acesso a dados (4 métodos especializados)
sistema/app/repositories/base.py             ← RepositoryBase (CRUD genérico com cache)
sistema/app/models/models.py:385             ← Model Cliente (26 colunas)
sistema/app/schemas/schemas.py:17-76         ← ClienteBase, ClienteCreate, ClienteUpdate, ClienteOut
sistema/app/routers/orcamentos.py            ← Cria clientes inline (FLUXO ALTERNATIVO)
```

### Migrations
```
sistema/alembic/versions/o001_add_campos_fiscais_cliente.py
sistema/alembic/versions/p002_add_criado_por_id_clientes.py
```

---

## 3. Sequência de Chamadas (Fluxo Principal — Criar Cliente)

```
1. clientes.html
   └─ onclick="abrirModalNovoCliente()" → abre modal
   └─ onclick="salvarCliente()" → monta payload e chama api.post('/clientes/', payload)

2. clientes.js :: salvarCliente()
   └─ Coleta 18+ campos do DOM (nome, telefone, email, endereço estruturado, fiscais)
   └─ Compõe `endereco` resumido a partir dos campos estruturados
   └─ api.post('/clientes/', payload)

3. api.js :: apiRequest('POST', '/clientes/', payload)
   └─ Adiciona header Authorization: Bearer {token}
   └─ POST → http://host:8000/api/v1/clientes/

4. main.py :: include_routers()
   └─ app.include_router(clientes_router, prefix="/api/v1")

5. routers/clientes.py :: criar_cliente()
   └─ Depends(exigir_permissao("clientes", "escrita"))  ← RBAC
   └─ Depends(get_cliente_service)                      ← DI
   └─ cliente_service.criar_cliente(dados, usuario)

6. deps.py :: get_cliente_service(db)
   └─ return ClienteService(db)

7. services/cliente_service.py :: criar_cliente(dados, usuario)
   ├─ Verifica duplicata por telefone → cliente_repo.get_by_telefone()
   ├─ Verifica duplicata por email → cliente_repo.get_by_email()
   ├─ Injeta empresa_id e criado_por_id nos dados
   └─ cliente_repo.create(db, dados_dict)

8. repositories/cliente_repository.py :: (herda de RepositoryBase)
   └─ RepositoryBase.create() → SQLAlchemy INSERT → commit → refresh

9. Response: ClienteOut (Pydantic serializa)
   └─ Retorna 201 + JSON do cliente criado
```

---

## 4. Estruturas de Dados Envolvidas

### Model SQLAlchemy (`models.py:385`)

```python
class Cliente(Base):
    id, empresa_id, criado_por_id, nome, telefone, email,
    endereco (compat), cep, logradouro, numero, complemento, bairro, cidade, estado,
    observacoes, criado_em,
    tipo_pessoa, cpf, cnpj, razao_social, nome_fantasia,
    inscricao_estadual, inscricao_municipal
    # Relationships: empresa, criado_por, orcamentos
```

### Schemas Pydantic (`schemas.py`)

- **ClienteBase:** 18 campos (nome obrigatório, resto opcional)
- **ClienteCreate(ClienteBase):** sem campos extras
- **ClienteUpdate(BaseModel):** todos os 18 campos opcionais
- **ClienteOut(ClienteBase):** + id, empresa_id, criado_em

### Payload JS (frontend → backend)

```json
{
  "nome": "string",
  "telefone": "string",
  "email": "string",
  "endereco": "string (composto)",
  "cep": "string",
  "logradouro": "string",
  "numero": "string",
  "complemento": "string",
  "bairro": "string",
  "cidade": "string",
  "estado": "string",
  "observacoes": "string",
  "tipo_pessoa": "PF|PJ",
  "cpf": "string",
  "cnpj": "string",
  "razao_social": "string",
  "nome_fantasia": "string",
  "inscricao_estadual": "string",
  "inscricao_municipal": "string"
}
```

---

## 5. Regras de Negócio Encontradas

| Regra | Onde | Detalhe |
|-------|------|---------|
| **Isolamento multi-tenancy** | Service + Repository | Filtra sempre por `empresa_id` |
| **Duplicata por telefone** | Service:24-31 | Verifica antes de criar; levanta `ClienteDuplicadoException` |
| **Duplicata por email** | Service:34-41 | Verifica antes de criar; levanta `ClienteDuplicadoException` |
| **Duplicata em update** | Service:127-141 | Verifica telefone e email alterados contra existentes |
| **Filtro "apenas meus"** | Router:44-48 | `perm_cli == "meus"` filtra por `criado_por_id` |
| **RBAC granular** | `exigir_permissao()` | Níveis: leitura(1) < meus(1.5) < escrita(2) < admin(3) |
| **Exclusão restrita** | Router:178 | Exige permissão `admin` para DELETE |
| **Atribuição automática** | Service:45-46 | Seta `empresa_id` e `criado_por_id` do usuário logado |

---

## 6. Problemas de Arquitetura

### 🔴 CRÍTICO — Criação de cliente bypassa o Service
- **Onde:** `sistema/app/routers/orcamentos.py:309` e `:855`
- **Problema:** O router de orçamentos cria clientes diretamente via `Cliente(empresa_id=..., nome=...)` + `db.add(cliente)`, sem passar pelo `ClienteService`. Isso ignora:
  - Verificação de duplicata por telefone/email
  - Log de auditoria (`logger.info`)
  - Atribuição de `criado_por_id`
- **Impacto:** Dois caminhos diferentes para criar clientes com comportamentos divergentes.

### 🟡 MÉDIO — CSV export fora do Service
- **Onde:** `routers/clientes.py:62-115`
- **Problema:** O endpoint `/clientes/exportar/csv` faz query direta ao DB (`db.query(Cliente).filter(...)`) sem usar o `ClienteService`. Se a regra de multi-tenancy mudar, este endpoint não será atualizado automaticamente.

### 🟡 MÉDIO — Busca por telefone no router
- **Onde:** `routers/clientes.py:127-140`
- **Problema:** O endpoint `/clientes/buscar/telefone/{telefone}` instancia `ClienteRepository()` diretamente no router, bypassando o service. Quebra o padrão de camadas.

### 🟡 MÉDIO — Campo `endereco` composto vs estruturado
- **Onde:** Frontend `clientes.js:358-362` e Model `models.py:396-397`
- **Problema:** O frontend compõe o campo `endereco` (resumido) a partir dos campos estruturados, e envia ambos. O campo `endereco` no model é mantido "para compatibilidade". Há duplicação de dados com risco de inconsistência.

### 🟡 MÉDIO — Sem validação de formato de CPF/CNPJ
- **Onde:** `schemas.py:33-34`
- **Problema:** CPF e CNPJ são `Optional[str]` sem validação de formato ou dígito verificador. A máscara é aplicada apenas no frontend. Dados inválidos podem chegar ao banco via API direta.

### 🟡 MÉDIO — Sem validação de email
- **Onde:** `schemas.py:20`
- **Problema:** `email: Optional[str] = None` — não usa `EmailStr` do Pydantic para validar formato. O campo `EmailStr` está importado mas não utilizado para clientes.

### 🟡 MÉDIO — Comentário desatualizado no auth_clientes.py
- **Onde:** `routers/auth_clientes.py:367`
- **Problema:** Comentário diz "Os endpoints de clientes foram movidos para app/routers/clientes.py" mas o arquivo ainda importa schemas e models de cliente sem usá-los na maioria.

### 🟢 BAIXO — Cache inativo no RepositoryBase
- **Onde:** `repositories/base.py:25-27`
- **Problema:** `self._cache_enabled = True` mas o cache nunca é consultado nem populado. Código morto.

### 🟢 BAIXO — Falta testes unitários
- **Onde:** `sistema/tests/`
- **Problema:** Não há arquivo `test_cliente*` nos testes. A funcionalidade não tem cobertura automatizada.

---

## 7. Melhor Ponto para Alterar com Segurança

Para alterações na funcionalidade de clientes, a **ordem recomendada** é:

1. **`sistema/app/services/cliente_service.py`** — Ponto central e mais seguro para adicionar regras de negócio. Todas as validações e lógica estão aqui. Alterações neste arquivo afetam todos os fluxos que usam o service.

2. **`sistema/app/schemas/schemas.py:17-76`** — Para adicionar validações de formato (CPF, CNPJ, email, telefone). Alterações aqui são seguras porque o Pydantic valida antes de chegar ao service.

3. **`sistema/app/repositories/cliente_repository.py`** — Para novas queries ou índices. Baixo risco.

4. **`sistema/cotte-frontend/js/clientes.js`** — Para mudanças de UI. Não afeta backend.

5. **`sistema/app/routers/orcamentos.py:300-310 e 845-856`** — ⚠️ **CUIDADO**: Este é o ponto mais sensível. Qualquer alteração aqui deve garantir que a criação inline de clientes pelo orçamento use o mesmo fluxo (service) para manter consistência.

**Regra de ouro:** Nunca edite o router de clientes sem verificar o service. Nunca edite o service sem verificar o repository. Nunca altere o model sem criar migration.
