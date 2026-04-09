---
title: Auditoria Tecnica
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Auditoria Tecnica
tags:
  - documentacao
prioridade: alta
status: documentado
---
# AUDITORIA TÉCNICA COMPLETA — SISTEMA COTTE

**Data:** 26/03/2026
**Escopo:** Backend (18 routers, 37 services, models, schemas) + Frontend (15 páginas HTML, 9 JS, 1 CSS)
**Stack:** Python/FastAPI + SQLAlchemy + PostgreSQL | HTML/CSS/JS Vanilla | Railway

---

## SUMÁRIO

1. [Resumo Executivo](#1-resumo-executivo)
2. [Análise do Frontend](#2-análise-do-frontend)
3. [Análise do Backend](#3-análise-do-backend)
4. [Inconsistências entre Frontend e Backend](#4-inconsistências-entre-frontend-e-backend)
5. [Top 10 Problemas Críticos](#5-top-10-problemas-críticos)
6. [Listas Consolidadas](#6-listas-consolidadas)
7. [Plano de Ação Priorizado](#7-plano-de-ação-priorizado)
8. [Roadmap Técnico Sugerido](#8-roadmap-técnico-sugerido)

---

## 1. RESUMO EXECUTIVO

O sistema COTTE possui **funcionalidade real mas arquitetura frágil**. O fluxo principal de orçamentos funciona em cenários ideais, mas apresenta **falhas críticas em concorrência, tratamento de erros e consistência de dados**. O frontend tem **bugs ativos em produção** que impedem funcionalidades core (busca de clientes, upload de logo, geração PIX). O backend sofre de **violação massiva de separação de responsabilidades** com routers de 2000+ linhas contendo lógica de negócio.

### Métricas Gerais

| Métrica | Valor |
|---------|-------|
| Routers | 18 |
| Endpoints HTTP | ~150+ |
| Services | 37 |
| Maior router | comercial.py (~2200 linhas) |
| Maior service | financeiro_service.py (1731 linhas) |
| Funções helper duplicadas | 12+ |
| Bugs críticos ativos | 8 |
| Inconsistências front/back | 12 |
| Código morto identificado | 1 arquivo (app.js) |
| `except Exception` genéricos | 15+ |
| `onclick` inline (violando AGENTS.md) | 30+ |

### Bugs Ativos em Produção (Corrigir Hoje)

1. **Busca de clientes** — parâmetro `?busca=` ignorado pelo backend (retorna todos)
2. **Upload de logo** — falta `/api/v1` na URL (retorna 404)
3. **Geração PIX** — `fetch()` sem `/api/v1` (retorna 404)
4. **CSS inválido** — `body { pb-24; }` em `orcamento-publico.html`
5. **Botão "+ Novo Lead"** — sem `onclick`, não faz nada

---

## 2. ANÁLISE DO FRONTEND

### 2.1 Problemas de Arquitetura

| # | Problema | Onde ocorre | Impacto | Prioridade |
|---|----------|-------------|---------|------------|
| F1 | **Modal de orçamento duplicado 2x** (120+ linhas HTML cada) | `index.html:463-597`, `orcamentos.html:512-639` | Manutenção impossível — mudança exige atualizar 2 arquivos | Alta |
| F2 | **`app.js` é código morto** — imports de módulos inexistentes (`ApiService.js`, `CacheService.js`) | `js/app.js` | Confusão, nenhum efeito prático mas indica abandono | Alta |
| F3 | **`comercial.js` com 2352 linhas monolíticas** | `js/comercial.js` | Impossível de manter, leads + pipeline + templates + import + config tudo junto | Crítica |
| F4 | **Funções utilitárias redefinidas 5+ vezes** (`formatarMoeda`, `escapeHtml`, `formatarData`) | `api.js`, `orcamento-view.html`, `orcamento-publico.html`, `comercial.js`, `orcamento-detalhes.js`, `relatorios.html` | Formatação inconsistente entre telas | Alta |
| F5 | **Inline scripts de 600+ linhas** em 8 páginas | `index.html`, `orcamentos.html`, `orcamento-publico.html`, `configuracoes.html`, `financeiro.html`, `catalogo.html`, `admin.html`, `login.html` | Código não reutilizável, não testável | Alta |
| F6 | **Inline styles de 150+ a 940 linhas** | `index.html`, `orcamentos.html`, `configuracoes.html`, `financeiro.html`, `login.html` | Conflitos CSS, manutenção impossível | Alta |
| F7 | **3 sistemas CSS conflitantes**: `style.css` + Tailwind CDN + CSS inline por página | `orcamento-publico.html` (Tailwind), `login.html` (CSS próprio), `orcamento-view.html` (CSS próprio) | Visual inconsistente, bugs de layout | Crítica |
| F8 | **`configuracoes.js` com 8 funções de salvar** que fazem `api.patch('/empresa/', ...)` com campos diferentes | `js/configuracoes.js` | Pulverização de responsabilidade | Média |

### 2.2 Problemas de Experiência e Fluxo

| # | Problema | Onde ocorre | Impacto | Prioridade |
|---|----------|-------------|---------|------------|
| F9 | **Botão "+ Novo Lead" sem `onclick`** — não abre modal | `comercial.html:23` | Feature completamente quebrada | Crítica |
| F10 | **Modal footer com `display:none !important`** no dashboard — botão "Criar Orçamento" escondido | `index.html:592` | Usuário não vê como criar pelo dashboard | Alta |
| F11 | **Sem estados de erro/timeout** na maioria das telas | Dashboard, orçamentos, clientes, financeiro, comercial | Spinner infinito se API falhar | Alta |
| F12 | **`confirm()` nativo do browser** para excluir categoria | `catalogo.html:700` | UX não profissional | Média |
| F13 | **Função `carregarComSeguranca()` com `while` loop** aguardando `Permissoes` | `catalogo.html:328-346` | Pode travar por 2s se permissões falharem | Média |
| F14 | **Filtros de orçamento incompletos** — só rascunho/enviado/aprovado | `orcamentos.html:472` | `em_execucao` e `aguardando_pagamento` ficam invisíveis | Alta |
| F15 | **Tela de cadastro duplicada**: `cadastro.html` + `login.html#cadastro` com implementações diferentes | `cadastro.html`, `login.html` | Confusão para o usuário | Média |

### 2.3 Problemas Visuais e de Consistência

| # | Problema | Onde ocorre | Impacto | Prioridade |
|---|----------|-------------|---------|------------|
| F16 | **CSS inválido `body { pb-24; }`** — falta `padding-bottom:` | `orcamento-publico.html:110` | Bug visual na página pública | Crítica |
| F17 | **Modais com estruturas diferentes** — `.open`, `.classList.add`, `display:flex`, `display:block` | Múltiplas páginas | Comportamento imprevisível | Alta |
| F18 | **Sistema de notificações duplicado**: `showNotif()` vs `showToast()` | `api.js` vs `comercial.js` | Experiência inconsistente | Média |
| F19 | **`login.html` redefine `.btn`, `.btn-primary`** incompatíveis com `style.css` | `login.html` | Visual quebrado no login | Alta |
| F20 | **`orcamento-view.html` sem sidebar** — experiência inconsistente | `orcamento-view.html` | Usuário perde navegação | Média |
| F21 | **Helvetica Neue em `orcamento-view.html`** vs DM Sans no resto do sistema | `orcamento-view.html` | Identidade visual quebrada | Baixa |

### 2.4 Problemas de Segurança no Frontend

| # | Problema | Onde ocorre | Impacto | Prioridade |
|---|----------|-------------|---------|------------|
| F22 | **XSS via JSON em `onclick`** | `clientes.js:58` — `onclick="abrirModalEditar(${JSON.stringify(c).replace(/"/g, '&quot;')})"` | Vulnerabilidade de segurança | Crítica |
| F23 | **`console.log` com dados sensíveis em produção** (corpos de requisição, respostas) | `api.js:33,58,83` | Exposição de tokens e dados | Alta |
| F24 | **`onclick` inline em vez de `addEventListener`** (30+ ocorrências) | Múltiplas páginas | Viola o próprio AGENTS.md, dificulta CSP | Média |

### 2.5 Problemas de Integração com Backend

| # | Problema | Onde ocorre | Impacto | Prioridade |
|---|----------|-------------|---------|------------|
| F25 | **`fetch()` sem prefixo `/api/v1`** — geração PIX retorna 404 | `orcamento-detalhes.js:453,723` | QR Code PIX quebrado | Crítica |
| F26 | **Busca de clientes usa `?busca=` mas backend espera `?nome=`** | `clientes.js:10` vs `clientes.py:33` | Busca não filtra nada — retorna todos | Crítica |
| F27 | **Upload logo usa URL sem `/api/v1`** — retorna 404 | `configuracoes.js:557` | Upload de logo quebrado | Crítica |
| F28 | **PUT usado para atualização parcial** — campos vazios limpam dados | `clientes.js:397` — envia `''` para campos não preenchidos | Dados de clientes podem ser apagados | Alta |
| F29 | **`_PAG_LABELS` incompleto** — falta `'4x'` | `orcamento-detalhes.js:3` | Exibe "4x" em vez de "4x sem juros" | Média |
| F30 | **`err.response?.data?.detail`** — padrão Axios inexistente no wrapper fetch | `orcamento-detalhes.js:801` | Funciona por fallback mas código incorreto | Baixa |

---

## 3. ANÁLISE DO BACKEND

### 3.1 Problemas Estruturais

| # | Problema | Arquivo(s) | Impacto | Prioridade |
|---|----------|------------|---------|------------|
| B1 | **`comando_bot` com 550+ linhas** — interpretação de linguagem natural + criação + aprovação + recusa + envio + análise financeira | `routers/orcamentos.py:407-964` | Impossível de manter/testar | Crítica |
| B2 | **`comercial.py` com 2200+ linhas e 43 endpoints** — deveria ser 4 routers | `routers/comercial.py` | Manutenção impossível | Crítica |
| B3 | **`whatsapp.py` com 1400+ linhas de lógica interna** — 100+ funções privadas que deveriam ser services | `routers/whatsapp.py` | Lógica de negócio no router | Crítica |
| B4 | **Funções helper duplicadas entre routers** (`_brl_fmt`, `_listar_itens_txt`, `_encontrar_servico_catalogo`, `_normalizar_texto`) | `orcamentos.py` + `whatsapp.py` | Mudança exige atualizar 2 arquivos | Alta |
| B5 | **Export CSV duplicado 4 vezes** (mesmo padrão `io.StringIO` + `csv.writer` + `StreamingResponse`) | `orcamentos.py`, `financeiro.py` (2x), `clientes.py` | Código duplicado | Alta |
| B6 | **`financeiro_service.py` com 1731 linhas** — deveria ser 5 services | `services/financeiro_service.py` | Monólito inmanutenível | Alta |
| B7 | **`email_service.py` com 1053 linhas** — templates HTML inline | `services/email_service.py` | Templates misturados com lógica | Alta |
| B8 | **`relatorios.py` com 184 linhas de agregação no router** | `routers/relatorios.py:15-199` | Lógica de negócio no router | Alta |
| B9 | **`auth_clientes.py` registro_publico com 130 linhas** — criação de empresa + usuário + lead + WhatsApp + email tudo no handler | `routers/auth_clientes.py:118-248` | Lógica de negócio no router | Alta |
| B10 | **11 funções auxiliares no router `webhooks.py`** — parser/validator deveria ser service | `routers/webhooks.py` | Acoplamento | Média |
| B11 | **Mix de patterns de autenticação** — alguns endpoints usam `get_superadmin`, outros `exigir_permissao` | `routers/comercial.py` | Inconsistência de segurança | Alta |
| B12 | **`response_model=List[dict]`** em vez de schema Pydantic | `routers/notificacoes.py:12` | Sem validação de resposta | Média |

### 3.2 Problemas de Lógica de Negócio

| # | Problema | Arquivo(s) | Impacto | Prioridade |
|---|----------|------------|---------|------------|
| B13 | **Orçamento pode ser editado APÓS aprovação** — sem verificação de status | `routers/orcamentos.py` (PUT endpoint) | Inconsistência jurídica — cliente aprovou valores que foram alterados | Crítica |
| B14 | **Contas financeiras falham silenciosamente após aceite** — `except Exception` engole erro | `routers/publico.py:481-487` | Orçamento aprovado mas sem parcelas criadas | Crítica |
| B15 | **Status ENVIADO marcado ANTES de confirmar envio WhatsApp** | `routers/orcamentos.py` | Se WhatsApp falhar, orçamento fica "enviado" mas cliente não recebeu | Crítica |
| B16 | **Race condition na visualização pública** — notificações duplicadas | `routers/publico.py:129-155` | Dois clientes abrindo simultaneamente geram dados duplicados | Alta |
| B17 | **Sem idempotência no envio** — operador pode clicar 2x e enviar 2 WhatsApps | `routers/orcamentos.py` | Mensagens duplicadas | Alta |
| B18 | **Edição após aprovação não invalida aceite anterior** | `routers/orcamentos.py` | PDF desatualizado, aceite inválido | Crítica |
| B19 | **Validação de itens vazios ausente** — orçamento com `total=0` aceito | `routers/orcamentos.py:138` | Orçamentos inválidos | Alta |
| B20 | **`recusar_orcamento` sem `with_for_update=True`** — apenas `aceitar` tem lock | `routers/publico.py` | Race condition na recusa | Média |
| B21 | **Função `_calcular_score` no router** — lógica de scoring deveria ser service | `routers/comercial.py:137-167` | Acoplamento | Média |
| B22 | **Auto-aplicação de PIX duplicada** — mesma lógica em `ver_orcamento_publico` e `aceitar_orcamento` | `routers/publico.py:171-188` e `463-479` | Código duplicado | Média |

### 3.3 Problemas de Modelagem e Persistência

| # | Problema | Arquivo(s) | Impacto | Prioridade |
|---|----------|------------|---------|------------|
| B23 | **`Usuario.empresa_id` nullable** — permite usuários sem empresa | `models/models.py` | Risco de dados inconsistentes, queries quebradas | Alta |
| B24 | **Sem índices compostos** — `(empresa_id, status)`, `(empresa_id, cliente_id)`, etc. | `models/models.py` | Performance degrade com crescimento | Alta |
| B25 | **`Orcamento.desconto` sem validação de limite** — aceita valores negativos | `models/models.py` + `schemas/schemas.py` | Cálculos financeiros errados | Crítica |
| B26 | **`BancoPIXEmpresa` permite múltiplos `padrao_pix=True`** — sem constraint | `models/models.py` | Integridade de dados | Alta |
| B27 | **FK sem `ondelete`** — `Orcamento.criado_por_id`, `ItemOrcamento.servico_id`, `Usuario.empresa_id` | `models/models.py` | Dados órfãos ao deletar | Alta |
| B28 | **`ContaFinanceira.valor_pago` pode ultrapassar `valor`** | `models/models.py` | Valores inconsistentes | Alta |
| B29 | **`PipelineStage` global sem `empresa_id`** — multi-tenant quebrado | `models/models.py` | Dados de empresas se misturam | Crítica |
| B30 | **`Campaign.empresa_id` tem index mas não FK** | `models/models.py` | Sem integridade referencial | Alta |
| B31 | **`PagamentoFinanceiro` sem `estornado_em`** | `models/models.py` | Sem rastreabilidade de estornos | Média |
| B32 | **`Orcamento` sem `expirado_em`** — há lógica de expiração mas campo não existe | `models/models.py` | Dados de expiração não persistidos | Média |
| B33 | **Schemas sem validação `ge=0`** em `desconto`, `quantidade`, `valor_unit` | `schemas/schemas.py` | Valores negativos aceitos | Alta |
| B34 | **`OrcamentoCreate.itens` sem `min_length`** — aceita lista vazia | `schemas/schemas.py` | Orçamento sem itens | Alta |

### 3.4 Problemas de Integração

| # | Problema | Arquivo(s) | Impacto | Prioridade |
|---|----------|------------|---------|------------|
| B35 | **`campaign_service.py` completamente quebrado** — referencia `WhatsAppService` e `EmailService` que não existem | `services/campaign_service.py:20-21` | `NameError` em runtime, campanhas 100% inoperantes | Crítica |
| B36 | **PDF perde acentos e cedilhas** — função `_ascii()` destrói caracteres especiais | `services/pdf_service.py:28-30` | PDFs profissionais com "Orcamento" em vez de "Orçamento" | Crítica |
| B37 | **WhatsApp sem retry** — falhas transitórias causam perda de mensagens | `services/whatsapp_*.py` | Mensagens de orçamento perdidas | Alta |
| B38 | **`enviar_orcamento_completo()` sempre retorna `True`** — ignora falhas de envio | `services/whatsapp_evolution.py:179-230` | Erro mascarado | Alta |
| B39 | **Webhook WhatsApp sem deduplicação** — mensagens duplicadas processadas múltiplas vezes | `routers/whatsapp.py` | Respostas duplicadas para o cliente | Alta |
| B40 | **Webhook WhatsApp não trata míria** — imagem/áudio silenciosamente ignorados | `routers/whatsapp.py` | Clientes que enviam imagem são ignorados | Alta |
| B41 | **Email SMTP síncrono bloqueia event loop** — `smtplib.SMTP()` em contexto asyncio | `services/email_service.py` | Degrada performance do servidor | Alta |
| B42 | **Senha enviada por email em texto plano** | `services/email_service.py:810` | Vulnerabilidade de segurança | Alta |
| B43 | **`@lru_cache` em `get_provider()`** — se config mudar, provider antigo fica cached | `services/whatsapp_service.py:25` | Configuração não atualiza sem restart | Média |
| B44 | **Webhook Kiwify usa SHA1** para validação de signature | `routers/webhooks.py:159` | SHA1 obsoleto para HMAC | Média |
| B45 | **Fallback para "pro" no mapeamento de plano Kiwify** — se nome não bater, dá acesso premium | `routers/webhooks.py:56` | Acesso indevido a funcionalidades | Alta |
| B46 | **`datetime.utcnow()` deprecated** — usado em `financeiro_service.py` | `services/financeiro_service.py:183` | Deprecation warning, pode quebrar em Python futuro | Baixa |

### 3.5 Problemas de Manutenção e Escalabilidade

| # | Problema | Arquivo(s) | Impacto | Prioridade |
|---|----------|------------|---------|------------|
| B47 | **Imports lazy dentro de handlers** — acoplamento oculto | `routers/orcamentos.py:754`, `routers/publico.py` | Difícil de rastrear dependências | Média |
| B48 | **`print()` em vez de `logging`** em produção | `routers/whatsapp.py:395` | Sem controle de nível de log | Média |
| B49 | **`SessionLocal()` manual** sem try/except robusto | `routers/whatsapp.py:233` | Sessão pode vazar | Alta |
| B50 | **`except Exception` genéricos** — 15+ ocorrências | Múltiplos arquivos | Erros reais escondidos | Alta |
| B51 | **Funções chamando `service._enriquecer_out()`** — quebra encapsulamento | `routers/agendamentos.py:94,130,415` | Acoplamento a implementação interna | Média |
| B52 | **`_to_out` e `_to_out_with_counts` 90% idênticos** | `routers/admin.py:52-110` | Código duplicado | Média |
| B53 | **Delete em cascata manual no router** | `routers/admin.py:435-437` | Lógica de banco no router | Média |
| B54 | **Sem testes unitários para routers** — apenas `tests/test_helpers.py` | `tests/` | Mudanças sem garantia | Alta |
| B55 | **Risco de IDOR** — alguns endpoints não filtram `empresa_id` | `routers/comercial.py:394,640`, `routers/whatsapp.py:1047` | Acesso a dados de outras empresas | Crítica |
| B56 | **Carregamento de TODOS os orçamentos em memória** | `routers/relatorios.py:46` — `query.all()` | OOM em empresas com muitos orçamentos | Alta |

---

## 4. INCONSISTÊNCIAS ENTRE FRONTEND E BACKEND

| # | Inconsistência | Camada errada | Comportamento correto | Prioridade |
|---|----------------|---------------|----------------------|------------|
| C1 | **`fetch()` sem `/api/v1`** em geração PIX e cache de orçamento | Frontend | Usar `api.post()` ou adicionar prefixo | Crítica |
| C2 | **Parâmetro `?busca=` vs `?nome=`** — busca de clientes não filtra | Ambas | Backend aceitar `busca` genérico OU frontend usar `nome` | Crítica |
| C3 | **Upload logo sem `/api/v1`** | Frontend | Adicionar prefixo na URL | Crítica |
| C4 | **Status `em_execucao`/`aguardando_pagamento` sem UI** | Frontend | Adicionar filtros e botões de transição | Alta |
| C5 | **PUT para atualização parcial de cliente** — campos vazios limpam dados | Frontend | Limpar campos vazios antes de enviar | Alta |
| C6 | **`_PAG_LABELS` incompleto** — falta `'4x'` | Frontend | Adicionar label para 4x | Média |
| C7 | **Permissão `admin` para deletar PIX mas botão exibido para `escrita`** | Frontend | Esconder botão sem permissão `admin` | Média |
| C8 | **`endereco` composto + campos individuais enviados juntos** — duplicação | Frontend | Enviar apenas campos individuais | Média |
| C9 | **Slug auto-gerado pode conflitar com seed padrão** | Frontend | Validar unicidade antes de enviar | Média |
| C10 | **Atualização pos-desaprovar pode falhar** — `carregar()` pode não existir | Frontend | Usar evento customizado | Baixa |

---

## 5. TOP 10 PROBLEMAS MAIS CRÍTICOS

| # | Problema | Tipo | Impacto direto |
|---|----------|------|----------------|
| **1** | **`campaign_service.py` quebrado** — `NameError` em runtime | Backend | Campanhas 100% inoperantes |
| **2** | **PDF perde acentos/cedilhas** — `_ascii()` destrói caracteres | Backend | PDFs profissionais com caracteres corrompidos |
| **3** | **Orçamento editável após aprovação** — sem verificação de status | Backend | Inconsistência jurídica, cliente aprovou valores alterados |
| **4** | **Contas financeiras falham silenciosamente** após aceite | Backend | Orçamento aprovado sem parcelas |
| **5** | **Busca de clientes quebrada** — `?busca=` vs `?nome=` | Front/Back | Busca retorna todos os clientes |
| **6** | **Upload de logo quebrado** — falta `/api/v1` | Frontend | Upload de logo retorna 404 |
| **7** | **Geração PIX quebrada** — falta `/api/v1` em `fetch()` | Frontend | QR Code PIX não funciona |
| **8** | **Status ENVIADO antes de confirmar envio** | Backend | Orçamento "enviado" mas cliente não recebeu |
| **9** | **XSS via JSON em onclick** | Frontend | Vulnerabilidade de segurança |
| **10** | **Risco de IDOR** — endpoints sem filtro de `empresa_id` | Backend | Acesso a dados de outras empresas |

---

## 6. LISTAS CONSOLIDADAS

### 6.1 Bugs e Falhas Lógicas

1. `campaign_service.py` — classes inexistentes (`WhatsAppService`, `EmailService`)
2. PDF — `_ascii()` corrompe caracteres especiais
3. Edição de orçamento após aprovação não bloqueada
4. Contas financeiras com exceção engolida no aceite
5. Status ENVIADO marcado antes de envio real
6. Busca clientes — parâmetro divergente (`busca` vs `nome`)
7. Upload logo — falta prefixo `/api/v1`
8. Geração PIX — `fetch()` sem `/api/v1`
9. XSS em `clientes.js` — JSON em `onclick`
10. Race condition na visualização pública
11. `enviar_orcamento_completo()` sempre retorna `True`
12. Webhook WhatsApp sem deduplicação
13. `datetime.utcnow()` deprecated
14. CSS inválido `body { pb-24; }` em `orcamento-publico.html`
15. Botão "+ Novo Lead" sem `onclick`
16. `window._apiBase` indefinido em `orcamento-view.html`

### 6.2 Processos Inacabados

1. **Campanhas** — service quebrado, router existe mas não funciona
2. **Status `em_execucao`/`aguardando_pagamento`** — backend tem transições, frontend não tem UI
3. **Expiração automática de orçamentos** — status existe mas sem job/cron
4. **Tratamento de míria no WhatsApp** — webhook ignora imagem/áudio
5. **Bounce de email** — sem webhook de bounce do Brevo
6. **Idempotência no webhook Kiwify** — eventos duplicados podem alterar estado
7. **Dashboard de relatórios** — router monolítico, sem service separado
8. **Sistema de agendamentos** — usa funções privadas do service
9. **Modulos/papéis** — seed roda no startup mas sem UI completa de gestão
10. **Onboarding** — existe service mas fluxo público incompleto

### 6.3 Problemas de Arquitetura

1. Routers com lógica de negócio (orcamentos, whatsapp, comercial, financeiro, auth, relatorios)
2. Services monolíticos (financeiro 1731L, email 1053L)
3. Funções helper duplicadas entre routers
4. Export CSV duplicado 4x
5. Sem separação clara entre domínio, aplicação e integração
6. `app.js` código morto com imports inexistentes
7. Modal de orçamento duplicado em 2 páginas HTML
8. Funções utilitárias redefinidas 5+ vezes no frontend
9. Inline scripts/styles massivos em 8+ páginas
10. 3 sistemas CSS conflitantes

### 6.4 Melhorias de Modelagem

1. `Usuario.empresa_id` → NOT NULL
2. Adicionar índices compostos para queries comuns
3. `Orcamento.desconto` → validação `ge=0` no schema
4. `BancoPIXEmpresa` → constraint de unicidade de `padrao_pix`
5. FK com `ondelete` correto em todas as tabelas
6. `PipelineStage` → adicionar `empresa_id` para multi-tenant
7. `Campaign.empresa_id` → FK em vez de apenas index
8. Adicionar `estornado_em` em `PagamentoFinanceiro`
9. Adicionar `expirado_em` em `Orcamento`
10. Schemas → validar `quantidade > 0`, `valor_unit >= 0`, `itens` com `min_length=1`

### 6.5 Melhorias de Escalabilidade e Manutenção

1. Extrair `comando_bot` para `bot_command_service.py`
2. Mover funções `_processar_*` de `whatsapp.py` para `whatsapp_bot_service.py`
3. Dividir `comercial.py` em 4 routers (leads, pipeline, interações, config)
4. Criar `csv_utils.py` centralizado
5. Dividir `financeiro_service.py` em 5 services
6. Extrair templates de email para arquivos HTML
7. Criar `utils.js` centralizado no frontend
8. Externalizar inline scripts/styles de todas as páginas
9. Quebrar `comercial.js` em módulos
10. Implementar testes unitários para services críticos
11. Substituir `except Exception` genéricos por exceções específicas
12. Substituir `print()` por `logging`
13. Configurar retry no WhatsApp
14. Configurar timeout no boto3 (R2)
15. Trocar FPDF por fpdf2 com suporte a Unicode

---

## 7. PLANO DE AÇÃO PRIORIZADO

### 7.1 Corrigir Imediatamente (Hoje)

| Ação | Arquivo(s) | Esforço |
|------|-----------|---------|
| Corrigir busca clientes (`?busca=` → `?nome=` ou adicionar param genérico) | `clientes.js:10` ou `clientes.py` | 5 min |
| Corrigir upload logo (adicionar `/api/v1`) | `configuracoes.js:557` | 5 min |
| Corrigir geração PIX (`fetch()` → `api.post()`) | `orcamento-detalhes.js:453,723` | 15 min |
| Corrigir CSS inválido `body { pb-24; }` | `orcamento-publico.html:110` | 2 min |
| Adicionar `onclick` no botão "+ Novo Lead" | `comercial.html:23` | 5 min |

### 7.2 Corrigir Nesta Sprint

| Ação | Arquivo(s) | Esforço |
|------|-----------|---------|
| Bloquear edição de orçamento após aprovação | `routers/orcamentos.py` (PUT endpoint) | 30 min |
| Remover `except Exception` que engole falha de contas financeiras | `routers/publico.py:481-487` | 15 min |
| Marcar ENVIADO apenas após confirmação de envio | `routers/orcamentos.py` | 1 hora |
| Corrigir `campaign_service.py` — classes inexistentes | `services/campaign_service.py` | 2 horas |
| Corrigir PDF — usar fpdf2 com fonte Unicode | `services/pdf_service.py` | 3 horas |
| Corrigir PUT para PATCH ou limpar campos vazios | `clientes.js:397` | 30 min |
| Adicionar `_PAG_LABELS['4x']` | `orcamento-detalhes.js:3` | 2 min |
| Verificar permissão antes de exibir botão de excluir PIX | `configuracoes.js` | 15 min |
| Adicionar validação de itens vazios no schema | `schemas/schemas.py` | 15 min |
| Adicionar validação `ge=0` em desconto/quantidade/valor | `schemas/schemas.py` | 15 min |

### 7.3 Refatorar em Seguida (Próximo Ciclo)

| Ação | Esforço |
|------|---------|
| Extrair `comando_bot` de `orcamentos.py` para service | 1 dia |
| Mover lógica de `whatsapp.py` para `whatsapp_bot_service.py` | 1 dia |
| Dividir `comercial.py` em 4 routers | 2 dias |
| Criar `utils.js` centralizado e eliminar duplicatas do frontend | 1 dia |
| Externalizar inline scripts/styles das 8 páginas maiores | 2 dias |
| Padronizar sistema de modais (uma estrutura, uma classe de abertura) | 1 dia |
| Criar `csv_utils.py` e eliminar 4 duplicatas de export CSV | 2 horas |
| Adicionar índices compostos no banco | 2 horas |
| Adicionar retry no WhatsApp | 3 horas |
| Implementar deduplicação no webhook WhatsApp | 2 horas |

### 7.4 Melhorar Depois (Backlog)

| Ação | Esforço |
|------|---------|
| Dividir `financeiro_service.py` em 5 services | 2 dias |
| Extrair templates de email para arquivos HTML | 1 dia |
| Quebrar `comercial.js` em módulos (leads, pipeline, templates, import) | 2 dias |
| Implementar testes unitários para services críticos | 3 dias |
| Adicionar webhook de bounce para email (Brevo) | 1 dia |
| Implementar idempotência no webhook Kiwify | 3 horas |
| Trocar SHA1 por SHA256 na validação Kiwify | 15 min |
| Adicionar `expirado_em` em `Orcamento` + job de expiração automática | 1 dia |
| Adicionar `estornado_em` em `PagamentoFinanceiro` | 1 hora |
| Implementar filtros de status `em_execucao`/`aguardando_pagamento` no frontend | 2 horas |
| Configurar timeout no boto3 (R2) | 15 min |
| Substituir `datetime.utcnow()` por `datetime.now(timezone.utc)` | 30 min |

---

## 8. ROADMAP TÉCNICO SUGERIDO

### Fase 1 — Estabilização (Semana 1)
Corrigir os 5 bugs ativos em produção (busca, upload logo, PIX, CSS, botão lead). Corrigir edição pós-aprovação e contas financeiras silenciosas.

### Fase 2 — Correção Estrutural (Semanas 2-3)
Extrair lógica dos routers principais (orcamentos, whatsapp, comercial). Corrigir campaign_service, PDF com Unicode, status ENVIADO. Adicionar validações nos schemas.

### Fase 3 — Padronização (Semanas 4-5)
Centralizar utilitários (utils.js, csv_utils.py). Padronizar modais e CSS. Externalizar inline scripts/styles. Adicionar índices no banco.

### Fase 4 — Melhoria de UX (Semanas 6-7)
Estados de loading/erro em todas as telas. Filtros de status completos. Notificações padronizadas. Sistema de agendamentos completo.

### Fase 5 — Preparação para Escala (Semanas 8+)
Testes unitários. Divisão de services monolíticos. Retry/fallback em integrações. Monitoramento. Preparação multi-tenant robusta.

---

*Análise baseada no código lido em 26/03/2026. Problemas marcados como "críticos" representam risco real de perda de dados, inconsistência jurídica ou funcionalidade quebrada em produção.*
