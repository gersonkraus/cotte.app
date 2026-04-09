---
title: Audit Permissoes
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Audit Permissoes
tags:
  - documentacao
prioridade: alta
status: documentado
---
# Relatório de Segurança — Sistema de Permissões COTTE

**Data:** 2026-03-23
**Gerado por:** Análise estática completa do código-fonte

---

## BLOCO 1 — Resumo Executivo

**Nível geral de segurança: Bom com falhas pontuais importantes**

O sistema possui uma arquitetura de autorização bem estruturada com JWT, permissões granulares por recurso/ação, isolamento de tenant nas queries e middleware contra ataques comuns. A maioria das rotas críticas está corretamente protegida.

**Riscos mais graves em ordem de prioridade:**

1. **`/admin/test` sem proteção alguma** — exposição pública da rota admin
2. **`/empresa/usuarios` sem validação de perfil** — qualquer operador pode gerenciar usuários
3. **IP real não extraído corretamente no rate limiting global** — proteção pode ser ineficaz em produção (Railway usa proxy)
4. **Entropia de `link_publico` precisa verificação** — acesso público a orçamentos via token
5. **Zero testes de isolamento de tenant** — risco não testado de cross-tenant access

---

## BLOCO 2 — Como o Sistema de Permissão Funciona Hoje

### Autenticação

**`sistema/app/core/auth.py` (linhas 34–87)**

- **JWT HS256** com payload `{sub: usuario_id, v: token_versao, exp: ...}`
- `token_versao` implementa **sessão única** — novo login invalida tokens anteriores
- Validação de empresa ativa e assinatura não expirada a cada request
- Função: `get_usuario_atual()`

### Autorização

**`sistema/app/core/auth.py` (linhas 98–152)**

Função `exigir_permissao(recurso, acao)` com hierarquia:
1. `is_superadmin` → acesso total a tudo
2. `is_gestor` → acesso total à própria empresa
3. `permissoes` JSON → `{"orcamentos": "escrita", "financeiro": "leitura"}`
4. Fallback legado: `perm_catalogo=True` → equivale a `"admin"` no catálogo

**Níveis de ação:** `leitura (1)` < `meus (1.5)` < `escrita (2)` < `admin (3)`

**Recursos conhecidos:** `catalogo`, `financeiro`, `clientes`, `orcamentos`, `equipe`, `configuracoes`

### Tenant Isolation

Implementado nas queries SQL de cada endpoint. Padrão correto:
```python
# orcamentos.py:997
.filter(Orcamento.empresa_id == usuario.empresa_id)
```
O `empresa_id` **nunca** vem do corpo da requisição — sempre de `usuario.empresa_id`.

### Middleware

**`sistema/app/core/security_middleware.py`** — camadas:
- Bloqueio de paths suspeitos (WordPress, phpMyAdmin, `.env`, `.git`)
- Rate limiting por IP com bloqueio de 5 min
- Bloqueio de user agents de scanners (SQLMap, Nikto, etc.)

### Arquivos críticos do sistema de permissão

| Arquivo | Função |
|---|---|
| `sistema/app/core/auth.py` | `get_usuario_atual`, `exigir_permissao`, `get_superadmin` |
| `sistema/app/models/models.py` (l.267–298) | Model `Usuario` com campos de permissão |
| `sistema/app/core/security_middleware.py` | Middleware global |
| `sistema/app/routers/admin.py` | Rotas de superadmin |
| `sistema/app/routers/empresa.py` | Gestão de usuários/empresa |
| `tests/test_permissions.py` | Testes existentes |

---

## BLOCO 3 — Falhas Encontradas

---

### FALHA 1 — Endpoint `/admin/test` sem proteção

**Severidade:** Média (reconhecimento)
**Onde:** `sistema/app/routers/admin.py`, linhas 39–41

```python
@router.get("/test")
def admin_test():
    return {"message": "Admin router is working"}
```

**Por que é problema:** Confirma publicamente que a rota `/admin` existe e responde. Facilita reconhecimento para atacantes.

**Cenário real:** Scanner automático confirma `/admin/test` → tenta força bruta em `/admin/login`, `/admin/dashboard`, etc.

**Como corrigir:** Deletar a rota. Não há motivo para existir em produção.

---

### FALHA 2 — `/empresa/usuarios` sem validação de perfil de autorização

**Severidade:** Alta
**Onde:** `sistema/app/routers/empresa.py`, rotas de gerenciamento de usuários

```python
@router.get("/empresa/usuarios")
def listar_usuarios(usuario = Depends(get_usuario_atual), ...):

@router.post("/empresa/usuarios")
def criar_usuario(usuario = Depends(get_usuario_atual), ...):

@router.patch("/empresa/usuarios/{id}")
def editar_usuario(usuario = Depends(get_usuario_atual), ...):
```

**Por que é problema:** Usa apenas `get_usuario_atual` (autenticação), não `exigir_permissao("equipe", "admin")`. Qualquer operador autenticado, mesmo sem permissão `equipe`, pode listar, criar e editar usuários da empresa.

**Cenário real:** Operador sem `equipe` na sua permissão acessa `GET /empresa/usuarios` e vê todos os funcionários com seus perfis. Pior: `POST /empresa/usuarios` com escalação de privilégios — cria novo usuário gestor.

**Como corrigir:**
```python
# Listar: exigir_permissao("equipe", "leitura")
# Criar/editar: exigir_permissao("equipe", "admin")
```

---

### FALHA 3 — Rate limiting do middleware não extrai IP real em produção

**Severidade:** Alta
**Onde:** `sistema/app/core/security_middleware.py`, linha ~61

```python
client_ip = request.client.host if request.client else "unknown"
```

**Por que é problema:** No Railway, `request.client.host` retorna o IP do load balancer interno, não o IP real do cliente. Todos os usuários compartilham o mesmo IP → rate limit não funciona, ou bloqueia todos ao mesmo tempo.

**Cenário real:** Atacante faz brute force de login sem ser bloqueado porque o rate limit nunca atinge o limite individual. Ou um único usuário legítimo dispara o limite e bloqueia toda a instância.

**Como corrigir:**
```python
def _get_real_ip(request: Request) -> str:
    for header in ["cf-connecting-ip", "x-real-ip", "x-forwarded-for"]:
        val = request.headers.get(header)
        if val:
            return val.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
```

**Nota:** `auth_clientes.py` já faz isso corretamente para o reset de senha (usa `x-forwarded-for`). O middleware central não faz.

---

### FALHA 4 — `link_publico` — entropia precisa de verificação

**Severidade:** Crítica (se fraco) / Baixa (se usando `secrets`)
**Onde:** `sistema/app/models/models.py` (campo) + onde é gerado em `orcamentos.py`

**Por que é problema:** O `link_publico` é o único mecanismo de controle de acesso para visualização, aprovação e recusa de orçamentos por clientes. Se for um UUID v4 ou `secrets.token_urlsafe(32)`, é seguro. Se for sequencial, hash curto ou baseado em ID, é enumerável.

**Cenário real:** Atacante itera `link_publico` e acessa orçamentos de todos os clientes da plataforma, vendo valores, dados de clientes, podendo aprovar/recusar.

**Como verificar:** Buscar onde `link_publico =` é atribuído em `orcamentos.py` e confirmar que usa `secrets.token_urlsafe(32)` ou equivalente com >= 128 bits de entropia.

---

### FALHA 5 — Nível `meus` implementado apenas em clientes, não em orçamentos

**Severidade:** Média
**Onde:** `sistema/app/routers/clientes.py` (l.44–49) vs ausência em `orcamentos.py`

**Por que é problema:** A permissão `meus` existe para clientes (operador vê apenas seus clientes), mas orçamentos não implementam o mesmo filtro. Operador com `orcamentos: meus` provavelmente vê todos os orçamentos.

**Cenário real:** Operador deveria ver apenas orçamentos que ele criou, mas vê todos da empresa.

**Status:** Hipótese — verificar se `orcamentos.py` faz o filtro de `criado_por` quando a permissão for `meus`.

---

### FALHA 6 — Empresa pode alterar próprios dados sem restrição de perfil

**Severidade:** Média
**Onde:** `sistema/app/routers/empresa.py`

```python
@router.patch("/empresa/")
def atualizar_empresa(usuario = Depends(get_usuario_atual), ...):
```

**Por que é problema:** Qualquer usuário autenticado pode editar os dados da empresa (nome, CNPJ, configurações). Deveria exigir pelo menos `is_gestor` ou `exigir_permissao("configuracoes", "escrita")`.

**Cenário real:** Operador muda o nome da empresa ou CNPJ nos dados cadastrais.

---

### FALHA 7 — Fallback `perm_catalogo` eleva para `admin` silenciosamente

**Severidade:** Baixa (por design, mas não documentado como risco)
**Onde:** `sistema/app/core/auth.py` (linhas 120–122)

```python
if not user_acao and recurso == "catalogo" and usuario.perm_catalogo:
    user_acao = "admin"
```

**Por que é problema:** Um operador com `perm_catalogo=True` (campo legado) tem nível `admin` no catálogo, podendo excluir itens, mesmo que a intenção fosse apenas `escrita`.

**Como corrigir:** Mapear `perm_catalogo=True` para `"escrita"`, não `"admin"`. Ou migrar todos para o novo sistema e remover o fallback.

---

### FALHA 8 — Ausência de auditoria em ações sensíveis

**Severidade:** Média
**Onde:** Todos os routers

**Por que é problema:** Ações como criar usuário, alterar permissões, aprovar orçamentos, impersonate e movimentações financeiras não geram log de auditoria rastreável.

**Cenário real:** Operador aprova orçamento indevidamente ou gerencia usuários — impossível rastrear quem fez o quê e quando.

---

## BLOCO 4 — Inconsistências e Dívidas Técnicas

**1. Padrão de proteção inconsistente no router `/empresa`**
Routers de `orcamentos`, `financeiro`, `clientes` e `catalogo` usam `exigir_permissao()`. O router `/empresa` usa apenas `get_usuario_atual()` sem verificação de papel. Inconsistência perigosa e difícil de auditar.

**2. Regra `apenas_meus` implementada em clientes mas ausente em orçamentos**
Duplicação de lógica prevista mas não executada. Isso vai gerar confusão quando alguém tentar configurar `orcamentos: meus` para um operador.

**3. `perm_catalogo` é campo legado mas ainda ativo**
Dois sistemas de permissão coexistindo (coluna booleana + JSON). Aumenta superfície de ataque e dificulta auditoria.

**4. Zero testes de isolamento de tenant**
`tests/test_permissions.py` testa apenas a lógica de `exigir_permissao()` em memória. Não testa se as queries realmente filtram por `empresa_id`. Um bug de `empresa_id` nos filtros não seria detectado.

**5. Middleware de segurança e `auth_clientes.py` tratam IP de formas diferentes**
`auth_clientes.py` usa `x-forwarded-for`. O middleware central usa `request.client.host`. Inconsistência que pode gerar comportamentos diferentes dependendo do tipo de ataque.

**6. `exigir_permissao` não tem default seguro para recursos não mapeados**
Se um novo recurso for criado e não adicionado à lista de `recursos_restritos`, o comportamento de fallback é negar acesso mas com mensagem genérica. Poderia ser mais explícito.

---

## BLOCO 5 — Melhorias Recomendadas

### Melhorias rápidas de alto impacto

| Ação | Arquivo | Impacto |
|---|---|---|
| Deletar `/admin/test` | `admin.py:39` | Remove reconhecimento |
| Adicionar `exigir_permissao("equipe", "admin")` em `/empresa/usuarios` | `empresa.py` | Bloqueia escalação |
| Adicionar `exigir_permissao("configuracoes", "escrita")` em `PATCH /empresa/` | `empresa.py` | Protege dados da empresa |
| Corrigir extração de IP real no `SecurityMiddleware` | `security_middleware.py:61` | Rate limit funciona em prod |

### Melhorias estruturais

**Centralizar policy de tenant isolation:**
Criar uma função `verificar_ownership(obj, usuario)` que encapsula a validação de ownership. Hoje cada endpoint faz `.filter(X.empresa_id == usuario.empresa_id)` manualmente — se um dev esquecer, não há proteção.

```python
def verificar_ownership(obj, usuario: Usuario) -> None:
    if usuario.is_superadmin:
        return
    if hasattr(obj, 'empresa_id') and obj.empresa_id != usuario.empresa_id:
        raise HTTPException(403, "Acesso negado")
```

**Migrar e remover `perm_catalogo`:**
Criar migration que popula `permissoes["catalogo"] = "escrita"` para todos os usuários com `perm_catalogo=True`, depois remover o campo e o fallback.

**Padronizar proteção no router `/empresa`:**
Usar `exigir_permissao` em vez de `get_usuario_atual` nos endpoints sensíveis de empresa.

### Arquitetura ideal de autorização

```
Request
  └── SecurityMiddleware (IP real, rate limit, bot detection)
       └── JWT validation (get_usuario_atual)
            └── Role check (exigir_permissao / get_superadmin)
                 └── Tenant check (empresa_id nos filtros SQL)
                      └── Ownership check (verificar_ownership)
                           └── Business logic
```

### Checklist para novas rotas

```
[ ] Usa Depends(get_usuario_atual) ou Depends(exigir_permissao())?
[ ] Se operação de escrita: usa exigir_permissao com "escrita" ou "admin"?
[ ] Todas as queries filtram por usuario.empresa_id?
[ ] IDs externos são buscados com filtro de empresa_id (não só pelo ID)?
[ ] empresa_id nunca vem do corpo da requisição?
[ ] Se público: usa token opaco com >= 128 bits de entropia?
[ ] Ações destrutivas (delete) verificam ownership explicitamente?
[ ] Ações administrativas usam get_superadmin?
[ ] Ações sensíveis geram evento de auditoria?
[ ] Erros de permissão retornam 403?
```

---

## BLOCO 6 — Plano de Correção Priorizado

### Fase 1 — Riscos críticos (fazer esta semana)

1. **Deletar `/admin/test`** — 5 min
2. **Proteger `/empresa/usuarios` com `exigir_permissao("equipe", "admin")`** — 30 min
3. **Proteger `PATCH /empresa/` com `exigir_permissao("configuracoes", "escrita")`** — 30 min
4. **Corrigir extração de IP real no `SecurityMiddleware`** — 1h
5. **Verificar entropia do `link_publico`** — 15 min (só leitura)

### Fase 2 — Inconsistências (próximas 2 semanas)

6. Implementar filtro `apenas_meus` também em orçamentos se permissão `meus` for configurável
7. Mapear `perm_catalogo` para `"escrita"` em vez de `"admin"` no fallback
8. Padronizar todos os endpoints de `/empresa` com `exigir_permissao`

### Fase 3 — Fortalecer arquitetura (próximo mês)

9. Criar helper `verificar_ownership(obj, usuario)` centralizado
10. Migration para remover `perm_catalogo` e migrar para JSON
11. Adicionar log de auditoria em ações sensíveis (criação de usuário, impersonate, aprovação, movimentações)

### Fase 4 — Auditoria e testes (contínuo)

12. Testes de tenant isolation: usuário da empresa A não acessa empresa B
13. Testes de privilege escalation: operador não consegue virar gestor
14. Testes de endpoints públicos: `link_publico` inválido retorna 404
15. Testes de rate limiting com mocks de IP de proxy

---

## Extras

### 10 verificações que todo endpoint deve seguir

```
1.  Autentica com get_usuario_atual ou exigir_permissao?
2.  Se operação de escrita: usa exigir_permissao com "escrita" ou "admin"?
3.  Todas as queries filtram por usuario.empresa_id?
4.  IDs externos são buscados com filtro de empresa_id (não só pelo ID)?
5.  empresa_id nunca vem do corpo da requisição?
6.  Se público: usa token opaco com >= 128 bits de entropia?
7.  Ações destrutivas (delete) verificam ownership explicitamente?
8.  Ações administrativas usam get_superadmin?
9.  Ações sensíveis geram evento de auditoria?
10. Erros de permissão retornam 403 (não 200 ou 404 para esconder info)?
```

### Matriz de permissão sugerida por perfil

| Recurso | Operador padrão | Operador escrita | Gestor | Superadmin |
|---|---|---|---|---|
| `orcamentos` | leitura | escrita | admin | admin |
| `financeiro` | — | leitura | admin | admin |
| `clientes` | meus | escrita | admin | admin |
| `catalogo` | leitura | escrita | admin | admin |
| `equipe` | — | — | admin | admin |
| `configuracoes` | — | — | escrita | admin |
| `relatorios` | — | leitura | admin | admin |

### Rotas mais sensíveis para testes manuais imediatos

```
1.  POST   /empresa/usuarios          → Operador consegue criar outro usuário?
2.  PATCH  /empresa/usuarios/{id}     → Operador consegue se tornar gestor?
3.  PATCH  /empresa/                  → Operador consegue editar dados da empresa?
4.  GET    /orcamentos/?empresa_id=2  → Parâmetro extra vaza dados de outra empresa?
5.  GET    /o/{link}/view             → Link curto/previsível é enumerável?
6.  POST   /o/{link}/aprovar          → Rejeitar link inválido retorna 404 ou 200?
7.  GET    /admin/test                → Deveria retornar 404, não 200
8.  POST   /admin/empresas/{id}/impersonate → Acessível sem is_superadmin?
9.  GET    /financeiro/resumo         → Operador sem permissão financeiro consegue?
10. POST   /auth/redefinir-senha      → Rate limit funciona com IPs diferentes?
```
