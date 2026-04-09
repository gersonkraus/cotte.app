---
title: Financeiro
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Mapa Tecico Financeiro
tags:
  - tecnico
  - mapa
  - tecnico
prioridade: media
status: documentado
---
# MAPA TÉCNICO — Módulo Financeiro COTTE

> Análise ponta a ponta realizada em 2026-03-23.
> Rastreamento via QMD + leitura de código-fonte real.

---

## 1. Entrada do Fluxo (Pontos de Acesso)

O módulo financeiro é acessado por **4 caminhos de entrada**:

| # | Origem | Arquivo | Gatilho |
|---|--------|---------|---------|
| 1 | **Frontend direto** | `cotte-frontend/financeiro.html` | Usuário clica em abas (Contas, Despesas, Pagamentos, Fluxo de Caixa, Caixa, Categorias) |
| 2 | **Aprovação de orçamento** | `app/routers/orcamentos.py:477` | Orçamento aprovado → `financeiro_service.criar_contas_receber_aprovacao()` |
| 3 | **Webhook público** | `app/routers/publico.py:357` | Pagamento via link público → `fin_svc.criar_contas_receber_aprovacao()` |
| 4 | **WhatsApp** | `app/routers/whatsapp.py:767` | Confirmação de pagamento via WhatsApp → `financeiro_service.aplicar_regra_no_orcamento()` |

---

## 2. Caminho Completo dos Arquivos

### Backend

```
sistema/
├── app/
│   ├── routers/
│   │   ├── financeiro.py          ← Router principal (1091 linhas, prefix="/financeiro")
│   │   ├── orcamentos.py          ← Chama financeiro_service em 5 pontos
│   │   ├── publico.py             ← Chama financeiro_service em 1 ponto (aprovação)
│   │   └── whatsapp.py            ← Chama financeiro_service em 1 ponto
│   ├── services/
│   │   └── financeiro_service.py  ← Service principal (1660 linhas, TODA a lógica)
│   ├── repositories/
│   │   └── categoria_financeira_repository.py  ← Único repository do módulo
│   ├── models/
│   │   └── models.py              ← 8 modelos financeiros (linhas 1086–1386)
│   ├── schemas/
│   │   └── financeiro.py          ← 30+ schemas Pydantic (599 linhas)
│   └── services/
│       ├── cotte_ai_hub.py        ← IA financeira (analisar_financeiro_ia, dashboard_financeiro_ia)
│       └── pix_service.py         ← Geração de payload/QRCode PIX
```

### Frontend

```
sistema/cotte-frontend/
├── financeiro.html                 ← Tela principal (3520 linhas, 6 abas)
├── js/
│   ├── api-financeiro.js           ← Módulo JS centralizado (221 linhas)
│   └── api.js                      ← Wrapper HTTP genérico
```

---

## 3. Sequência de Chamadas

### FLUXO PRINCIPAL — Registro de Pagamento

```
1. Frontend: financeiro.html
   └─ Financeiro.registrarPagamento(dados) [api-financeiro.js:38]
      └─ POST /financeiro/pagamentos

2. Router: financeiro.py:197 (registrar_pagamento)
   └─ svc.registrar_pagamento(empresa_id, dados, usuario, db) [service.py:354]
      ├─ _obter_ou_criar_conta_orcamento(orc, empresa_id, dados, db) [service.py:408]
      │  └─ Cria ContaFinanceira se não existe (tipo=RECEBER)
      ├─ Cria PagamentoFinanceiro (status=CONFIRMADO)
      ├─ _recalcular_status_conta(conta) [service.py:141]
      │  └─ Atualiza StatusConta: PENDENTE → PARCIAL → PAGO
      ├─ Se tipo=SINAL:
      │  └─ _criar_conta_saldo_se_necessario() [service.py:439]
      │     └─ Cria ContaFinanceira do saldo devedor
      └─ _atualizar_status_orcamento(orc) [service.py:166]
         └─ Seta orc.pagamento_recebido_em se todas contas pagas

3. Router: financeiro.py:210
   └─ registrar_auditoria() (log de auditoria)

4. Response: PagamentoOut enriquecido (_enrich_pagamento)
```

### FLUXO APROVAÇÃO DE ORÇAMENTO

```
1. Router: orcamentos.py:477
   └─ financeiro_service.criar_contas_receber_aprovacao(orc, empresa_id, db) [service.py:913]
      ├─ Verifica idempotência (contas_receber_geradas_em)
      ├─ Lê regra de pagamento do orçamento
      ├─ Se pct_entrada > 0: cria ContaFinanceira (tipo_lancamento="entrada")
      ├─ Se pct_saldo > 0: cria N parcelas (tipo_lancamento="saldo")
      ├─ Sem regra: cria ContaFinanceira integral
      └─ Seta orc.contas_receber_geradas_em
```

### FLUXO CAIXA (Saldo Operacional)

```
1. Frontend: Financeiro.resumo() [api-financeiro.js:91]
   └─ GET /financeiro/resumo

2. Router: financeiro.py:412
   └─ svc.calcular_resumo(empresa_id, db) [service.py:585]
      ├─ _calcular_estatisticas_caixa() [service.py:51]
      │  ├─ Query: SUM PagamentoFinanceiro (entradas orçamentos)
      │  ├─ Query: SUM PagamentoFinanceiro (saídas contas pagar)
      │  ├─ Query: SUM MovimentacaoCaixa (entradas/saídas manuais)
      │  ├─ Query: SaldoCaixaConfig (saldo inicial)
      │  └─ saldo = entradas - saídas + saldo_inicial
      ├─ Query: total a receber, vencido, ticket médio
      ├─ _receita_ultimos_meses() [service.py:724] (GROUP BY ano/mês)
      ├─ _receita_por_meio() [service.py:772] (GROUP BY forma de pagamento)
      └─ _previsao(7), _previsao(30) (contas a vencer)
```

### FLUXO ESTORNO

```
Frontend: Financeiro.estornarPagamento(id, motivo) [api-financeiro.js:61]
   └─ POST /financeiro/pagamentos/{id}/estornar
      └─ svc.estornar_pagamento() [service.py:475]
         ├─ Valida empresa_id (pelo orçamento OU pela conta)
         ├─ Marca pagamento como ESTORNADO
         ├─ _recalcular_status_conta(conta)
         └─ Limpa orc.pagamento_recebido_em se necessário
```

---

## 4. Estruturas de Dados Envolvidas

### Models (SQLAlchemy)

| Model | Tabela | Arquivo | Linha |
|-------|--------|---------|-------|
| `FormaPagamentoConfig` | `formas_pagamento_config` | `models.py` | 1086 |
| `ContaFinanceira` | `contas_financeiras` | `models.py` | 1133 |
| `PagamentoFinanceiro` | `pagamentos_financeiros` | `models.py` | 1199 |
| `TemplateNotificacao` | `templates_notificacao` | `models.py` | 1255 |
| `HistoricoCobranca` | `historico_cobrancas` | `models.py` | 1272 |
| `ConfiguracaoFinanceira` | `configuracoes_financeiras` | `models.py` | 1293 |
| `MovimentacaoCaixa` | `movimentacoes_caixa` | `models.py` | 1318 |
| `CategoriaFinanceira` | `categorias_financeiras` | `models.py` | 1341 |
| `SaldoCaixaConfig` | `saldo_caixa_configs` | `models.py` | 1372 |

### Enums críticos

- `TipoConta`: `RECEBER`, `PAGAR`
- `StatusConta`: `PENDENTE`, `PARCIAL`, `PAGO`, `VENCIDO`, `CANCELADO`
- `TipoPagamento`: `QUITACAO`, `SINAL`, `PARCIAL`, `ADICIONAL`
- `StatusPagamentoFinanceiro`: `CONFIRMADO`, `ESTORNADO`
- `OrigemRegistro`: `SISTEMA`, `MANUAL`, `IA`, `WHATSAPP`

### Schemas Pydantic

| Schema | Uso | Linha |
|--------|-----|-------|
| `PagamentoCreate` | Input POST pagamentos | 106 |
| `PagamentoOut` | Output pagamentos | 119 |
| `ContaFinanceiraCreate` | Input POST contas | 154 |
| `ContaFinanceiraOut` | Output contas | 200 |
| `DespesaCreate` | Input POST despesas | 172 |
| `FinanceiroResumoOut` | Output dashboard | 271 |
| `FluxoCaixaOut` | Output fluxo de caixa | 331 |
| `ContaRapidoCreate` | Input conta rápida | 397 |
| `SaldoDetalhadoOut` | Output saldo detalhado | 431 |

---

## 5. Regras de Negócio Encontradas

| Regra | Local | Função |
|-------|-------|--------|
| **Idempotência de contas** | `service.py:924` | `contas_receber_geradas_em` impede duplicação na aprovação |
| **Auto-criação de conta** | `service.py:408` | `_obter_ou_criar_conta_orcamento` cria conta se não existe ao pagar |
| **Sinal gera saldo** | `service.py:439` | `_criar_conta_saldo_se_necessario` cria conta do saldo após sinal |
| **Recálculo de status** | `service.py:141` | `_recalcular_status_conta` ajusta PENDENTE→PARCIAL→PAGO |
| **Quitado em** | `service.py:166` | `_atualizar_status_orcamento` seta `pagamento_recebido_em` |
| **Seed lazy** | `service.py:200` | `_seed_formas_padrao` cria 6 formas padrão na primeira chamada |
| **Snapshot de regra** | `service.py:875` | `aplicar_regra_no_orcamento` copia regra para o orçamento |
| **Saldo detalhado** | `service.py:1466` | Exclui orçamentos/contas com `excluido_em` |
| **Cobrança WhatsApp** | `service.py:1175` | Template com placeholders + histórico |

---

## 6. Problemas de Arquitetura

### 🔴 Alto risco

1. **Service como God Object** (`financeiro_service.py` — 1660 linhas)
   - Contém TUDO: lógica de pagamento, cálculo de saldo, fluxo de caixa, categorias, templates, cobrança WhatsApp.
   - Único repository existente é `CategoriaFinanceiraRepository`. Todo o resto acessa DB diretamente no service.

2. **Inconsistência de cálculo de saldo**
   - `_calcular_estatisticas_caixa` (service.py:51) soma `PagamentoFinanceiro` de orçamentos E contas a receber.
   - `calcular_saldo_detalhado` (service.py:1466) usa lógica diferente (só pagamentos com `orcamento_id`).
   - `calcular_resumo` (service.py:585) tem terceira abordagem.
   - **3 funções diferentes calculam "saldo" com queries diferentes.**

3. **Validação inconsistente de empresa_id**
   - `estornar_pagamento` (service.py:481) faz validação manual de empresa_id pelo orçamento OU conta.
   - `registrar_pagamento` (service.py:354) só valida pelo orçamento.
   - `registrar_pagamento_conta_receber` (service.py:1127) não valida empresa_id explicitamente.

### 🟡 Médio risco

4. **Lógica de negócio no router**
   - `cancelar_conta` (router.py:906) faz query direta + update de status no router.
   - `excluir_conta_soft` (router.py:933) idem.
   - `registrar_entrada_caixa` (router.py:1019) cria `MovimentacaoCaixa` diretamente no router.
   - `definir_saldo_inicial` (router.py:970) manipula `SaldoCaixaConfig` no router.

5. **Duplicação de CSV export**
   - `exportar_contas_csv` (router.py:316) e `exportar_despesas_csv` (router.py:493) têm lógica de formatação quase idêntica no router.

6. **asyncio.run dentro de request síncrono**
   - `cobrar_via_whatsapp` (service.py:1236) usa `asyncio.run()` dentro de função síncrona. Pode causar erros se já houver loop rodando.

7. **Duplicação de campos em `categoria`**
   - `ContaFinanceira` tem `categoria` (String 100) E `categoria_slug` (String 50). Ambos são preenchidos no service com o mesmo valor (service.py:265, 1028).

### 🟢 Baixo risco

8. **Schema `FormaPagamentoConfigUpdateV2`** (schema.py:390) existe mas não é usado em nenhum endpoint.

9. **Função `listar_categorias_financeiras`** (service.py:1602) não é chamada — só `listar_categorias_sync` (service.py:1561) é usada.

---

## 7. Melhor Ponto para Alterar com Segurança

### Para adicionar nova funcionalidade no fluxo de pagamento:

```
ALTERAR:
1. financeiro_service.py  → adicionar lógica em função dedicada
2. schemas/financeiro.py  → adicionar schema de input/output
3. financeiro.py (router) → adicionar endpoint fino que delega ao service
4. api-financeiro.js      → adicionar wrapper JS
5. financeiro.html        → adicionar chamada no frontend
```

### Para alterar regra de cálculo de saldo:

```
ÚNICO ponto seguro: _calcular_estatisticas_caixa() [service.py:51]
   → É o "single source of truth" usado por calcular_saldo_caixa_kpi()
   → Alterar AQUI e garantir que calcular_resumo() e calcular_saldo_detalhado()
     usem a mesma fonte (ou chamem esta função).
```

### Para alterar regra de aprovação/criação de contas:

```
PONTO ÚNICO: criar_contas_receber_aprovacao() [service.py:913]
   → Chamada por: orcamentos.py:477, publico.py:357, cotte_ai_hub.py:1230
   → Idempotência garantida por: contas_receber_geradas_em
   → Seguro adicionar lógica aqui (nova parcela, nova regra, etc.)
```

---

## Referências rápidas

| O que | Onde |
|-------|------|
| Router financeiro | `sistema/app/routers/financeiro.py` |
| Service financeiro | `sistema/app/services/financeiro_service.py` |
| Schemas financeiro | `sistema/app/schemas/financeiro.py` |
| Models financeiros | `sistema/app/models/models.py` (linhas 1086–1386) |
| Repository categoria | `sistema/app/repositories/categoria_financeira_repository.py` |
| Frontend financeiro | `sistema/cotte-frontend/financeiro.html` |
| API JS financeiro | `sistema/cotte-frontend/js/api-financeiro.js` |
| IA financeira | `sistema/app/services/cotte_ai_hub.py` (funções `analisar_financeiro_ia`, `dashboard_financeiro_ia`) |
