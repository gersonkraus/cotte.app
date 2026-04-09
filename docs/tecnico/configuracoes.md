---
title: Configuracoes
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Mapa Técnico - Configurações (configuracoes.html)
tags:
  - tecnico
  - frontend
  - mapa
prioridade: media
status: documentado
---

# Mapa Técnico: configuracoes.html

> Rastreamento ponta a ponta da funcionalidade de Configurações do COTTE.
> Gerado em: 2026-03-23

---

## 1. Entrada do fluxo

O acesso se dá por navegação direta via sidebar (`layout.js:129`) ou por redirecionamento interno:

- `sistema/app/services/onboarding_service.py:31/89/94/288` — redireciona para `configuracoes.html` após onboarding
- `sistema/cotte-frontend/js/api.js:241` — redireciona quando limite do plano é atingido
- `sistema/cotte-frontend/js/ux-improvements.js:133` — botão de upgrade

A URL aceita hash para seção inicial: `configuracoes.html#empresa`, `#formas-pagamento`, `#integracoes`, `#plano`, `#cfg-financeiro` (HTML:3196-3200).

---

## 2. Caminho completo dos arquivos

### Frontend

| Arquivo | Função |
|---|---|
| `sistema/cotte-frontend/configuracoes.html` | Página principal — 3482 linhas, contém HTML + CSS + **todo JS inline** |
| `sistema/cotte-frontend/js/api.js` | `apiRequest()`, `api.get()`, `api.post()`, `api.patch()`, `api.delete()`, `getToken()`, `setLoading()`, `showNotif()` |
| `sistema/cotte-frontend/js/layout.js` | `inicializarLayout('configuracoes')` — sidebar, nav, permissão `configuracoes` |
| `sistema/cotte-frontend/js/api-financeiro.js` | Módulo `Financeiro` — **NÃO é carregado no configuracoes.html** (usa `apiRequest` diretamente) |

### Backend — Routers

| Arquivo | Prefixo | Endpoints usados |
|---|---|---|
| `sistema/app/routers/empresa.py` | `/empresa` | `GET /`, `PATCH /`, `POST /logo`, `DELETE /logo`, `GET /whatsapp/status`, `POST /whatsapp/conectar`, `GET /whatsapp/qrcode`, `DELETE /whatsapp/desconectar`, `GET /pix/bancos`, `POST /pix/bancos`, `PATCH /pix/bancos/:id`, `DELETE /pix/bancos/:id` |
| `sistema/app/routers/financeiro.py` | `/financeiro` | `GET /configuracoes`, `PATCH /configuracoes`, `GET /formas-pagamento`, `POST /formas-pagamento`, `PATCH /formas-pagamento/:id`, `POST /formas-pagamento/:id/padrao` |

Todos montados com prefixo `/api/v1` em `sistema/app/main.py:136-158`.

### Backend — Services

| Arquivo | Funções chamadas |
|---|---|
| `sistema/app/services/financeiro_service.py` | `obter_ou_criar_configuracao()` (linha 1363), `atualizar_configuracao()` (linha 1372) |
| `sistema/app/services/plano_service.py` | `whatsapp_proprio_habilitado()`, `exigir_whatsapp_proprio()`, `_config_for_empresa()` |
| `sistema/app/services/whatsapp_evolution.py` | `EvolutionProvider` — criar instância, get_status, get_qrcode |
| `sistema/app/services/r2_service.py` | `r2_service.upload_file()`, `r2_service.delete_file()` |

### Backend — Models

| Arquivo | Model | Tabela |
|---|---|---|
| `sistema/app/models/models.py:153` | `Empresa` | `empresas` (~40 colunas) |
| `sistema/app/models/models.py:1293` | `ConfiguracaoFinanceira` | `configuracoes_financeiras` (7 colunas + id/timestamps) |
| `sistema/app/models/models.py` | `BancoPIXEmpresa` | bancos/PIX da empresa |
| `sistema/app/models/models.py` | `FormaPagamentoConfig` | formas de pagamento |

### Backend — Schemas

| Arquivo | Schema | Uso |
|---|---|---|
| `sistema/app/schemas/schemas.py:662` | `EmpresaUpdate` | PATCH `/empresa/` — 30 campos opcionais |
| `sistema/app/schemas/schemas.py:715` | `EmpresaOut` | Resposta GET/PATCH — 35 campos |
| `sistema/app/schemas/financeiro.py:364` | `ConfiguracaoFinanceiraOut` | GET `/financeiro/configuracoes` |
| `sistema/app/schemas/financeiro.py:379` | `ConfiguracaoFinanceiraUpdate` | PATCH `/financeiro/configuracoes` |

### Permissões

| Arquivo | Função |
|---|---|
| `sistema/app/core/auth.py:125` | `exigir_permissao("configuracoes", "escrita"|"leitura"|"admin")` |

---

## 3. Sequência de chamadas (por seção)

### FLUXO A — Seção "Empresa" (dados + logo + cor)

```
[1] carregarEmpresa()                          [configuracoes.html:2484]
    └─ api.get('/empresa/')                    [api.js]
        └─ GET /api/v1/empresa/                [empresa.py:51]
            └─ db.query(Empresa).first()
            └─ Retorna EmpresaOut (35 campos)

[2] salvarEmpresa()                            [configuracoes.html:3104]
    └─ api.patch('/empresa/', { nome, telefone, email, cor_primaria,
        validade_padrao_dias, desconto_max_percent, lembrete_dias, lembrete_texto })
        └─ PATCH /api/v1/empresa/              [empresa.py:114]
            └─ dados: EmpresaUpdate
            └─ for campo, valor in dados.model_dump(exclude_none=True):
                   setattr(empresa, campo, valor)
            └─ db.commit()

[3] uploadLogo(input)                          [configuracoes.html:2944]
    └─ fetch(API_URL + '/empresa/logo', { method: POST, body: FormData })
        └─ POST /api/v1/empresa/logo           [empresa.py:132]
            └─ Valida extensão (.png/.jpg/.jpeg/.webp)
            └─ r2_service.upload_file()
            └─ empresa.logo_url = file_url

[4] removerLogo()                              [configuracoes.html:2972]
    └─ api.delete('/empresa/logo')
        └─ DELETE /api/v1/empresa/logo         [empresa.py:167]
            └─ r2_service.delete_file(empresa.logo_url)
```

### FLUXO B — Seção "Orçamentos" (numeração, lembrete)

```
[1] salvarEmpresa() — compartilhado com Fluxo A
    (envia validade_padrao_dias, desconto_max_percent, lembrete_dias, lembrete_texto)

[2] salvarNumeracao()                          [configuracoes.html:3083]
    └─ api.patch('/empresa/', { numero_prefixo, numero_incluir_ano, numero_prefixo_aprovado })
        └─ PATCH /api/v1/empresa/              [empresa.py:114]
```

### FLUXO C — Seção "Formas de Pagamento"

```
[1] carregarFormasPagamento()                  [configuracoes.html:3220]
    └─ apiRequest('GET', '/financeiro/formas-pagamento')
        └─ GET /api/v1/financeiro/formas-pagamento   [financeiro.py]
            └─ Retorna lista de FormaPagamentoConfig

[2] salvarForma()                              [configuracoes.html:3358]
    └─ apiRequest('POST' ou 'PATCH', '/financeiro/formas-pagamento[/:id]', payload)
        └─ POST/PATCH /api/v1/financeiro/formas-pagamento[/:id]

[3] setPadrao(id)                              [configuracoes.html:3404]
    └─ apiRequest('POST', `/financeiro/formas-pagamento/${id}/padrao`)

[4] toggleFormaAtivo(id, ativoAtual)           [configuracoes.html:3415]
    └─ apiRequest('PATCH', `/financeiro/formas-pagamento/${id}`, { ativo: !ativoAtual })
```

### FLUXO D — Seção "Financeiro" (configurações financeiras)

```
[1] carregarConfiguracaoFinanceira()            [configuracoes.html:3438]
    └─ apiRequest('GET', '/financeiro/configuracoes')
        └─ GET /api/v1/financeiro/configuracoes     [financeiro.py:758]
            └─ exigir_permissao("financeiro", "leitura")
            └─ svc.obter_ou_criar_configuracao(empresa_id, db)
            └─ Retorna ConfiguracaoFinanceiraOut

[2] salvarConfiguracaoFinanceira()              [configuracoes.html:3459]
    └─ apiRequest('PATCH', '/financeiro/configuracoes', { gerar_contas_ao_aprovar,
        dias_vencimento_padrao, automacoes_ativas, dias_lembrete_antes, dias_lembrete_apos })
        └─ PATCH /api/v1/financeiro/configuracoes   [financeiro.py:768]
            └─ exigir_permissao("financeiro", "escrita")
            └─ ConfiguracaoFinanceiraUpdate (validação Pydantic)
            └─ svc.atualizar_configuracao(empresa_id, dados.model_dump(exclude_unset=True), db)
```

### FLUXO E — Seção "Comunicação"

```
[1] salvarComunicacao()                        [configuracoes.html:3029]
    └─ api.patch('/empresa/', { descricao_publica_empresa, texto_assinatura_proposta,
        telefone_operador, mostrar_botao_whatsapp, texto_aviso_aceite,
        mensagem_confianca_proposta, mostrar_mensagem_confianca })

[2] salvarAssinaturaEmail()                    [configuracoes.html:3050]
    └─ api.patch('/empresa/', { assinatura_email })

[3] salvarBoasVindas()                         [configuracoes.html:2995]
    └─ api.patch('/empresa/', { boas_vindas_ativo, msg_boas_vindas })

[4] salvarNotifWhatsVisualizacao()             [configuracoes.html:3007]
    └─ api.patch('/empresa/', { notif_whats_visualizacao })

[5] salvarAnexoPdfEmail()                      [configuracoes.html:3018]
    └─ api.patch('/empresa/', { anexar_pdf_email })
```

Todos acima chamam o mesmo endpoint `PATCH /api/v1/empresa/` — diferem apenas nos campos enviados.

### FLUXO F — Seção "Integrações" (WhatsApp Próprio)

```
[1] carregarStatusWhatsapp()                   [configuracoes.html:2801]
    └─ api.get('/empresa/whatsapp/status')
        └─ GET /api/v1/empresa/whatsapp/status [empresa.py:337]

[2] wpConectar()                               [configuracoes.html:2869]
    └─ api.post('/empresa/whatsapp/conectar', {})
        └─ POST /api/v1/empresa/whatsapp/conectar [empresa.py:386]
            └─ EvolutionProvider.criar_instancia()
            └─ provider.get_qrcode()

[3] _iniciarPollingConexao() (a cada 4s)      [configuracoes.html:2854]
    └─ api.get('/empresa/whatsapp/status') — até st.conectado = true

[4] wpDesconectar()                            [configuracoes.html:2904]
    └─ api.delete('/empresa/whatsapp/desconectar')
```

---

## 4. Estruturas de dados envolvidas

### Empresa (model `empresas`) — ~40 colunas

Usadas na página:

```
nome, telefone, email, telefone_operador, logo_url, cor_primaria,
validade_padrao_dias, desconto_max_percent, lembrete_dias, lembrete_texto,
anexar_pdf_email, assinatura_email, msg_boas_vindas, boas_vindas_ativo,
descricao_publica_empresa, texto_assinatura_proposta, texto_aviso_aceite,
mensagem_confianca_proposta, mostrar_botao_whatsapp, mostrar_mensagem_confianca,
notif_whats_visualizacao, numero_prefixo, numero_incluir_ano, numero_prefixo_aprovado,
plano, assinatura_valida_ate, trial_ate, limite_orcamentos_custom,
limite_usuarios_custom, whatsapp_proprio_ativo, whatsapp_numero,
whatsapp_conectado, evolution_instance
```

### ConfiguracaoFinanceira (model `configuracoes_financeiras`) — 7 colunas

| Coluna | Tipo | Default |
|---|---|---|
| `id` | Integer PK | auto |
| `empresa_id` | Integer FK (unique) | — |
| `dias_vencimento_padrao` | Integer | 7 |
| `gerar_contas_ao_aprovar` | Boolean | True |
| `automacoes_ativas` | Boolean | False |
| `dias_lembrete_antes` | Integer | 2 |
| `dias_lembrete_apos` | Integer | 3 |
| `categorias_despesa` | Text (JSON) | None |
| `updated_at` | DateTime | now() |

### ConfiguracaoFinanceiraUpdate (Pydantic)

Validações:

| Campo | Constraint |
|---|---|
| `dias_vencimento_padrao` | `ge=0, le=365` |
| `dias_lembrete_antes` | `ge=0, le=30` |
| `dias_lembrete_apos` | `ge=0, le=30` |
| `gerar_contas_ao_aprovar` | `Optional[bool]` |
| `automacoes_ativas` | `Optional[bool]` |
| `categorias_despesa` | `Optional[str]` |

---

## 5. Regras de negócio encontradas

| Regra | Local | Descrição |
|---|---|---|
| Permissão por recurso | `auth.py:125`, `empresa.py:117/135/169/339/388` | `exigir_permissao("configuracoes", "escrita"|"leitura"|"admin")` |
| Validação de extensão de logo | `empresa.py:139` | Apenas `.png`, `.jpg`, `.jpeg`, `.webp` |
| Upload para R2 | `empresa.py:153` | Logo vai para Cloudflare R2 (não armazenamento local) |
| Auto-criação de ConfiguracaoFinanceira | `financeiro_service.py:1365-1368` | Se não existe registro, cria com defaults |
| Validação Pydantic | `financeiro.py:380-384` | Limites numéricos nos campos de configuração financeira |
| WhatsApp próprio só Pro/Business | `empresa.py:397` | `exigir_whatsapp_proprio(empresa)` antes de conectar |
| Numeração: prefixo apenas alfanumérico | `configuracoes.html:3112` | Regex JS: `.replace(/[^A-Z0-9]/g, '')` |
| Percentual entrada+saldo ≤ 100% | `configuracoes.html:3364` | Validação JS antes de salvar forma |
| Campo `nome` obrigatório na forma | `configuracoes.html:3360` | Validação JS inline |

---

## 6. Problemas de arquitetura

> **Status (2026-03-23):** 6.1, 6.4, 6.5, 6.7, 6.8, 6.9 — **corrigidos**. 6.2, 6.3, 6.6 — pendentes (baixo impacto operacional).

### 6.1 — ~~God page (3482 linhas)~~ ✅ CORRIGIDO

JS extraído para `sistema/cotte-frontend/js/configuracoes.js`. HTML reduzido de 3499 → 2422 linhas. Qualquer alteração de lógica JS agora vai no arquivo dedicado.

### 6.2 — Duplicação de endpoints PATCH

**5+ funções JS distintas** (`salvarEmpresa`, `salvarComunicacao`, `salvarBoasVindas`, `salvarNotifWhatsVisualizacao`, `salvarAnexoPdfEmail`, `salvarAssinaturaEmail`) chamam **o mesmo endpoint** `PATCH /empresa/`. Pendente — baixo impacto operacional.

### 6.3 — Dois domínios misturados na mesma página

Configurações da **empresa** e do **financeiro** compartilham o mesmo HTML. Pendente — baixo impacto operacional.

### 6.4 — ~~`api-financeiro.js` não é usado na página~~ ✅ CORRIGIDO

`api-financeiro.js?v=4` agora carregado. `carregarFormasPagamento()` usa `Financeiro.listarFormasPagamento()` com TTL de 5min. Mutations chamam `Financeiro.invalidarFormas()` antes de recarregar.

### 6.5 — ~~Validação JS sem espelho no backend~~ ✅ CORRIGIDO

`EmpresaUpdate` (`schemas.py`) agora valida:
- `numero_prefixo` / `numero_prefixo_aprovado`: apenas `[A-Z0-9]`, máx. 8 chars, auto-uppercase
- `desconto_max_percent`: range `0–100`

20 testes em `tests/test_empresa_schema.py` cobrem todos os casos.

### 6.6 — `ConfiguracaoFinanceira` vs `Empresa` — campos sobrepostos

`Empresa.lembrete_dias` (lembrete de orçamento) vs `ConfiguracaoFinanceira.dias_lembrete_*` (cobrança financeira). Nomes confusamente parecidos. Pendente — doc e nomes OK no código, confusão apenas na UI.

### 6.7 — ~~Polling sem cleanup~~ ✅ CORRIGIDO

`configuracoes.js` — `window.addEventListener('beforeunload', ...)` limpa `_wpQrTimer` ao navegar para outra página.

### 6.8 — ~~`salvarEmpresa` desabilita botões cruzados~~ ✅ CORRIGIDO

`salvarEmpresa(btnEl)` recebe o botão clicado como parâmetro e desabilita **apenas ele**. Onclicks atualizados para `onclick="salvarEmpresa(this)"`.

### 6.9 — ~~Fluxo de Formas de Pagamento inline~~ ✅ CORRIGIDO

Toda a lógica movida para `configuracoes.js`. Usa `Financeiro.listarFormasPagamento()` e `Financeiro.invalidarFormas()`.

---

## 7. Melhor ponto para alterar com segurança

**Para alterações em configurações da empresa** (nome, logo, cor, numeração, lembrete, comunicação):

- Edite `PATCH /empresa/` em `sistema/app/routers/empresa.py:114`
- Schema: `sistema/app/schemas/schemas.py:662` (`EmpresaUpdate`) — validators já definidos
- Frontend: `sistema/cotte-frontend/js/configuracoes.js` — funções `salvarEmpresa()`, `salvarComunicacao()`, etc.

**Para alterações em configurações financeiras** (vencimento, automações de cobrança):

- Edite `PATCH /financeiro/configuracoes` em `sistema/app/routers/financeiro.py:768`
- Service: `sistema/app/services/financeiro_service.py:1372`
- Schema: `sistema/app/schemas/financeiro.py:379` (`ConfiguracaoFinanceiraUpdate`)
- Frontend: `sistema/cotte-frontend/js/configuracoes.js` — função `salvarConfiguracaoFinanceira()`

**Para formas de pagamento:**

- Frontend: `sistema/cotte-frontend/js/configuracoes.js` — funções `salvarForma()`, `setPadrao()`, `toggleFormaAtivo()`
- Após mutations: chama `Financeiro.invalidarFormas()` para forçar reload do cache

**O ponto mais seguro para extensão** é o schema Pydantic (`EmpresaUpdate` ou `ConfiguracaoFinanceiraUpdate`). Para novos campos, adicione no HTML, no `configuracoes.js` e no schema — sempre com `@field_validator` quando há restrição de formato ou range.
