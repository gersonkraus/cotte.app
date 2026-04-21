# Análise — Criação de Orçamento (Assistente IA) e Checks em Configurações

> **Contexto**: Este documento consolida (1) como o frontend do **Assistente IA** cria um novo orçamento e (2) quais informações a tela **Configurações** carrega/valida e que impactam a criação/formatação de orçamentos.

## 1) Fluxo: como o Assistente IA cria um novo orçamento

### 1.1 Arquivos principais (frontend)

- `sistema/cotte-frontend/assistente-ia.html` — UI do chat e inclusão dos scripts.
- `sistema/cotte-frontend/js/assistente-ia.js` — envio da mensagem e streaming das respostas.
- `sistema/cotte-frontend/js/assistente-ia-intents.js` — definição da intenção **novo_orcamento** e requisitos mínimos.
- `sistema/cotte-frontend/js/assistente-ia-render.js` + `sistema/cotte-frontend/js/assistente-ia-render-types.js` — renderização de cards (preview/criado).
- `sistema/cotte-frontend/js/assistente-ia-actions.js` — ação de **confirmar/criar orçamento**.

### 1.2 Passo-a-passo (end-to-end)

1. Usuário digita e envia uma mensagem no chat (`assistente-ia.html`).
2. O frontend inicia o streaming do assistente (em `assistente-ia.js`) chamando o endpoint de IA do assistente (stream).
3. A IA identifica a intenção de **novo orçamento** (registrada em `assistente-ia-intents.js`) e devolve um **preview** (`orcamento_preview`) com dados mínimos (cliente/serviço/valor).
4. O frontend renderiza o card de preview (`assistente-ia-render*.js`).
5. Usuário clica em “Criar/Confirmar” (ou “Criar + mat.” para cadastrar itens novos). Isso chama `confirmarOrcamento(...)` em `assistente-ia-actions.js`.
6. `confirmarOrcamento(...)` monta o payload e chama o backend para efetivamente criar o orçamento.
7. Backend cria o orçamento e responde com `tipo_resposta = "orcamento_criado"` e dados do orçamento (id/número/total/etc).
8. Frontend renderiza o card de “orçamento criado” e disponibiliza ações subsequentes (ex.: envio/compartilhamento).

### 1.3 Endpoint final (criação efetiva)

- **Frontend** chama: `POST /ai/orcamento/confirmar` (resolvido via client para `/api/v1/...`)
- **Backend** expõe: `POST /api/v1/ai/orcamento/confirmar`

### 1.4 Payload (essência do que é enviado ao confirmar)

O payload montado no frontend (em `assistente-ia-actions.js`) inclui, tipicamente:

- `cliente_id` (opcional)
- `cliente_nome`
- `servico`
- `valor`
- `desconto` e `desconto_tipo` (com defaults)
- `observacoes` (opcional)
- `cadastrar_materiais_novos` (boolean; quando o usuário escolhe criar + cadastrar itens)

## 2) Backend: rotas, schemas e onde a criação acontece

### 2.1 Arquivos relevantes (backend)

- `sistema/app/routers/ai_hub.py` — rota `POST /api/v1/ai/orcamento/confirmar`.
- `sistema/app/services/ai_tools/orcamento_tools.py` — `CriarOrcamentoInput` e `_criar_orcamento` (criação real).
- (apoio) `sistema/app/schemas/schemas.py` — request/response schemas envolvidos.

### 2.2 Criação real no servidor

No backend, o fluxo de confirmação de orçamento via IA:

1. Recebe o request (`AIConfirmarOrcamentoRequest`).
2. Converte/monta um `CriarOrcamentoInput`.
3. Executa `_criar_orcamento(...)`, que:
   - resolve cliente (por id ou nome)
   - resolve itens e tenta associar ao catálogo
   - se `cadastrar_materiais_novos=true`, cadastra itens “novos” conforme regras existentes
   - persiste orçamento e itens
4. Retorna `AIResponse` com `tipo_resposta` apropriado (sucesso: `orcamento_criado`).

## 3) O que `configuracoes.html` verifica/checa para criação de orçamento

> Observação: aqui há (A) validações que bloqueiam salvar configuração e (B) configurações que são carregadas/salvas e impactam defaults/formatação de orçamentos.

### 3.1 Arquivos principais (Configurações)

- `sistema/cotte-frontend/configuracoes.html`
- `sistema/cotte-frontend/js/configuracoes.js`
- `sistema/cotte-frontend/js/api.js` (wrapper de API e tratamento de erros)

### 3.2 Validações/bloqueios explícitos

- **Nome da empresa obrigatório** ao salvar dados da empresa (bloqueia o salvamento e mostra notificação).
- Bloqueios indiretos por backend (tratados no wrapper `api.js`) quando a empresa/plano está inativo (podem impedir operações de API).

### 3.3 Informações carregadas/salvas que impactam orçamentos novos

Em `configuracoes.js`, a tela faz **`GET /empresa/`** para carregar e **`PATCH /empresa/`** para salvar.

Campos que influenciam criação/formatação de orçamentos:

**Identidade/cabeçalho**
- Nome da empresa, telefone, email
- Cor primária (branding)

**Defaults aplicados em novos orçamentos**
- `validade_padrao_dias`
- `desconto_max_percent`

**Política de agendamento**
- política de agendamento em novos orçamentos
- usar agendamento automático
- opções de data só após liberação manual

**Numeração de orçamento**
- prefixo
- incluir ano
- prefixo após aprovação

**Template do orçamento**
- `template_orcamento` (com fallback para “classico” no carregamento)

## 4) Mapa rápido: quem checa o quê

| Parte | O que é checado/coletado | Onde | Endpoint |
|---|---|---|---|
| Assistente IA (chat) | intenção + dados mínimos para preview (cliente/serviço/valor) | `assistente-ia-*` | stream do assistente |
| Confirmar/criar orçamento | payload de confirmação (inclui `cadastrar_materiais_novos`) | `assistente-ia-actions.js` | `POST /api/v1/ai/orcamento/confirmar` |
| Defaults do orçamento | validade, descontos, agendamento | `configuracoes.html` + `configuracoes.js` | `GET/PATCH /empresa/` |
| Identidade/numeração/template | prefixo/ano/template | `configuracoes.html` + `configuracoes.js` | `PATCH /empresa/` |
| Bloqueio explícito | nome da empresa vazio (ao salvar config) | `configuracoes.js` | bloqueia `PATCH /empresa/` |

## 5) Como validar (manual)

1. **Configurações**
   - deixar **Nome da empresa** vazio e tentar salvar → deve bloquear.
   - salvar validade/prefixo/template → conferir no Network que chama `PATCH /empresa/`.
2. **Assistente IA**
   - pedir “criar orçamento …” → deve aparecer card `orcamento_preview`.
   - clicar confirmar → observar `POST /api/v1/ai/orcamento/confirmar` e resposta `orcamento_criado`.

## 6) Riscos restantes

- Config de empresa incompleta (ex.: nome/template) tende a degradar cabeçalho/identidade do orçamento; a tela de configurações já bloqueia salvar sem nome.
- Falhas por dados incompletos ao confirmar orçamento (cliente/serviço/valor) devem retornar erro do backend; é importante o frontend traduzir isso bem no card.

## 7) Sugestões (contextuais)

### 7.1 Melhorias essenciais (2)

1. Documentar o contrato do fluxo **preview → confirmar** (campos obrigatórios e defaults) para evitar divergência entre frontend e `AIConfirmarOrcamentoRequest`.
2. Adicionar validação no frontend antes de confirmar (não chamar `/ai/orcamento/confirmar` sem cliente/serviço/valor).

### 7.2 Ideias inovadoras (2)

1. Pré-checagem de configuração no card preview (ex.: alertar “Empresa sem nome/template/numeração” via `GET /empresa/`).
2. Mostrar no preview “itens encontrados no catálogo” vs “itens novos” antes do usuário clicar em “Criar + mat.”.

### 7.3 Melhorias de frontend de alto impacto (2)

1. Card de preview editável: permitir ajustar cliente/serviço/valor/validade/desconto no próprio card antes de confirmar.
2. Erro no próprio card: em falha do `POST /ai/orcamento/confirmar`, renderizar erro estruturado + ação “corrigir e reenviar”.
