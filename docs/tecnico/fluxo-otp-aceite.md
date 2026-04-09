---
title: Fluxo Otp Aceite
tags:
  - tecnico
prioridade: alta
status: documentado
---
---
title: Fluxo Otp Aceite Publico
tags:
  - tecnico
prioridade: alta
status: documentado
---
# Fluxo OTP para aceite no link público

**STATUS: IMPLEMENTADO (23/03/2026)**

Objetivo: confirmar a identidade do cliente (por WhatsApp ou e-mail) antes de registrar o aceite digital, reduzindo aceites fraudulentos por quem apenas tem o link.

---

## 1. Visão geral do fluxo

```
[Cliente abre link público] → [Clica "Aceitar"]
    → Se OTP obrigatório (empresa configurou):
        1. Modal: "Confirmar identidade"
           - Mostra canal que receberá o código (mascara: ***1234 ou e***@***.com)
           - Botão "Enviar código por WhatsApp" ou "Enviar código por e-mail" (conforme disponível)
        2. Backend: gera código 6 dígitos, guarda em cache (TTL 10 min), envia via WhatsApp ou e-mail
        3. Modal: campo "Código recebido" + nome completo + mensagem opcional + checkbox declaração
        4. Cliente informa código e confirma
        5. Backend: valida código → se ok, registra aceite (aceite_nome, aceite_em, aceite_confirmado_otp=true)
    → Se OTP não obrigatório:
        Fluxo atual (só nome + declaração)
```

---

## 2. Backend

### 2.1 Configuração por empresa

- **Modelo `Empresa`**: novo campo booleano `exigir_otp_aceite` (default `False` para não quebrar quem já usa).
- **Migration**: `ALTER TABLE empresas ADD COLUMN IF NOT EXISTS exigir_otp_aceite BOOLEAN DEFAULT FALSE;`
- **Schemas**: incluir em `EmpresaUpdate` e `EmpresaOut`.
- **Configurações (frontend)**: checkbox em "Aceite e conversão" — "Exigir confirmação por código (OTP) no aceite do link público".

### 2.2 Cache do código OTP

- Chave: `otp_aceite:{link_publico}` (um código ativo por link; ao solicitar novo, invalida o anterior).
- Valor: `{ "code": "123456", "expires_at": "ISO8601" }`.
- TTL: 10 minutos (configurável).
- Implementação: Redis se existir no projeto; senão cache em memória (ex.: dict com expiry, ou `cachetools.TTLCache`). Se múltiplas instâncias no Railway, Redis é necessário para não ter código em uma instância e validar em outra.

### 2.3 Novos endpoints (API pública, prefixo `/o/`)

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/{link_publico}/aceitar/solicitar-otp` | Body: `{ "canal": "whatsapp" \| "email" }`. Verifica se orçamento está enviado e não aceito/recusado/expirado. Se cliente tem telefone (WhatsApp) ou e-mail, gera código, salva no cache, envia mensagem. Retorna `{ "enviado": true, "canal": "whatsapp", "expira_em_minutos": 10 }` ou 400 com mensagem (ex.: "Informe telefone ou e-mail do cliente no orçamento"). |
| `POST` | `/{link_publico}/aceitar` | **Alterado**: body pode incluir `codigo_otp` (opcional). Se empresa tem `exigir_otp_aceite=True`, exige `codigo_otp`; valida no cache; se ok, remove do cache e registra aceite (e marca `aceite_confirmado_otp=True` no orçamento, se quisermos esse campo). Se `exigir_otp_aceite=False`, fluxo atual (ignora código). |

### 2.4 Modelo Orcamento (opcional mas recomendado)

- `aceite_confirmado_otp` (Boolean, default False): True quando o aceite foi feito após validação de OTP. Útil para relatórios e para o operador saber se houve confirmação de identidade.

### 2.5 Envio do código

- **WhatsApp**: usar `enviar_mensagem_texto(telefone_cliente, "Seu código de confirmação para aceitar o orçamento ... é: *123456*. Válido por 10 minutos.", empresa=...)`. Telefone = orçamento.cliente.telefone (normalizado).
- **E-mail**: novo template em `email_service` (ex.: `enviar_otp_aceite(email, codigo, numero_orcamento, empresa_nome)`). E-mail = orçamento.cliente.email.
- Se o cliente não tiver telefone nem e-mail no cadastro, não é possível enviar OTP; retornar erro claro e sugerir à empresa cadastrar contato do cliente.

### 2.6 Rate limit

- Aplicar rate limit em `solicitar-otp` (ex.: mesmo limite do aceite por IP/link) para evitar abuso de envio de SMS/e-mail/WhatsApp.

---

## 3. Frontend (página pública)

### 3.1 Quando OTP é obrigatório

- Ao carregar o orçamento, a API deve indicar se exige OTP (ex.: campo `exigir_otp_aceite` no objeto empresa retornado em `GET /o/{link}`). Hoje o público retorna `OrcamentoPublicoOut` com `empresa: EmpresaPublicoOut` — adicionar `exigir_otp_aceite: bool` em `EmpresaPublicoOut`.

### 3.2 Modal em duas etapas

**Etapa 1 — Solicitar código**

- Título: "Confirmar identidade"
- Texto: "Para aceitar este orçamento, envie um código de confirmação para o seu contato cadastrado."
- Exibir de forma mascarada o canal disponível (ex.: "WhatsApp terminado em ***5678" ou "E-mail ***@gmail.com"), com base em dados que o backend pode retornar em um endpoint ou no próprio GET (ex.: `canal_otp_disponivel: { whatsapp: true, email: true }` e `canal_mascarado: "***5678"`). Ou o backend retorna só "enviado para o contato cadastrado" sem revelar o número/e-mail.
- Botão(ões): "Enviar código por WhatsApp" e/ou "Enviar código por e-mail".
- Ao clicar, chamar `POST /o/{link}/aceitar/solicitar-otp` com `{ "canal": "whatsapp" }` ou `"email"`. Em sucesso, passar para a etapa 2.

**Etapa 2 — Inserir código e confirmar**

- Campo: "Código recebido (6 dígitos)"
- Mantém: nome completo, mensagem opcional, checkbox de declaração.
- Botão: "Confirmar aceite".
- Ao confirmar, enviar `POST /o/{link}/aceitar` com `{ "nome": "...", "mensagem": "...", "codigo_otp": "123456" }`.

### 3.3 Quando OTP não é obrigatório

- Comportamento atual: um único modal com nome, mensagem e declaração, sem passo de código.

---

## 4. Casos de borda

- **Cliente sem telefone nem e-mail**: se empresa exige OTP, exibir mensagem: "Não foi possível enviar o código: o seu contato não está cadastrado. Entre em contato com a empresa para atualizar seu cadastro e tentar novamente."
- **Código expirado**: ao submeter aceite com código vencido, retornar 400 "Código expirado. Solicite um novo código."
- **Código inválido**: 400 "Código incorreto. Verifique e tente novamente."
- **Muitas tentativas de OTP**: rate limit em `solicitar-otp` (e opcionalmente em tentativas de validação no aceite).
- **Orçamento aceito/recusado/expirado entre solicitar OTP e confirmar**: ao chamar `aceitar` com código, o backend já valida status; retornar erro adequado.

---

## 5. Ordem sugerida de implementação

1. Migration + campo `exigir_otp_aceite` (Empresa) e `aceite_confirmado_otp` (Orcamento); expor em schemas e GET público.
2. Cache OTP (em memória ou Redis) + geração de código (6 dígitos, aleatório).
3. Endpoint `solicitar-otp`: gerar código, salvar no cache, enviar via WhatsApp e/ou e-mail (usar cliente do orçamento).
4. Endpoint `aceitar`: aceitar parâmetro opcional `codigo_otp`; se `exigir_otp_aceite` e código presente, validar no cache; se ok, registrar aceite e marcar `aceite_confirmado_otp=True`.
5. Frontend: detectar `exigir_otp_aceite`, mostrar fluxo em duas etapas (solicitar OTP → informar código + nome e confirmar).
6. Configurações: checkbox "Exigir confirmação por código (OTP) no aceite".

---

## 6. Referências no código atual

- Aceite: `sistema/app/routers/publico.py` — `aceitar_orcamento`, `AceiteRequest`.
- Página pública: `sistema/cotte-frontend/orcamento-publico.html` — modal de aceite, `confirmarAceite()`.
- Empresa (público): `sistema/app/schemas/schemas.py` — `EmpresaPublicoOut`.
- Envio WhatsApp: `app.services.whatsapp_service.enviar_mensagem_texto`.
- Envio e-mail: `app.services.email_service` (criar função para OTP).
