---
title: Audit
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Audit
tags:
  - documentacao
  - frontend
prioridade: media
status: documentado
---
# Auditoria de Funcionalidades — configuracoes.html

> Data: 2026-03-16
> Status: [ ] Pendente | [x] OK | [!] Bug encontrado

---

## Navegação Lateral

| # | Elemento | Comportamento esperado | Status | Observação |
|---|----------|----------------------|--------|------------|
| N1 | Click em "Empresa" | Exibe `#sec-empresa`, nav item fica `.active` | [ ] | |
| N2 | Click em "Orçamentos" | Exibe `#sec-orcamentos` | [ ] | |
| N3 | Click em "Formas de Pagamento" | Exibe `#sec-formas-pagamento` | [ ] | |
| N4 | Click em "Aparência" | Exibe `#sec-aparencia` | [ ] | |
| N5 | Click em "Comunicação" | Exibe `#sec-comunicacao` | [ ] | |
| N6 | Click em "Integrações" | Exibe `#sec-integracoes` | [ ] | |
| N7 | Click em "Plano e Assinatura" | Exibe `#sec-plano` | [ ] | |
| N8 | Click em "Segurança" | Exibe `#sec-seguranca` | [ ] | |
| N9 | URL hash `#orcamentos` | Navega direto para a seção correta ao carregar | [ ] | |

---

## 1. Seção: Empresa

### 1.1 Logo da Empresa

| # | Elemento | Comportamento esperado | Status | Observação |
|---|----------|----------------------|--------|------------|
| E1 | `#logo-placeholder` | Visível quando não há logo | [ ] | |
| E2 | Click em `#btn-upload-logo` | Abre seletor de arquivo | [ ] | |
| E3 | Upload de imagem válida (.png/.jpg/.webp) | POST `/empresa/logo` → preview aparece | [ ] | |
| E4 | Upload de arquivo inválido | Mostra erro / não faz upload | [ ] | |
| E5 | `#btn-remover-logo` | Visível só quando há logo | [ ] | |
| E6 | Click em `#btn-remover-logo` | DELETE `/empresa/logo` → placeholder volta | [ ] | |

### 1.2 Dados da Empresa

| # | Elemento | Comportamento esperado | Status | Observação |
|---|----------|----------------------|--------|------------|
| E7 | Carregamento inicial | `GET /empresa/` preenche todos os campos | [ ] | |
| E8 | `#emp-nome` | Aceita texto, reflete no preview | [ ] | |
| E9 | `#emp-telefone` | Campo livre, reflete no preview | [ ] | |
| E10 | `#emp-email` | Campo email, reflete no preview | [ ] | |
| E11 | `#emp-cor` + `#emp-cor-hex` | Sincronizam entre si; cor reflete no preview | [ ] | |
| E12 | `#btn-salvar-empresa` | PATCH `/empresa/` com sucesso → notif verde | [ ] | |
| E13 | Preview do cabeçalho | Atualiza em tempo real ao digitar | [ ] | |

---

## 2. Seção: Orçamentos

| # | Elemento | Comportamento esperado | Status | Observação |
|---|----------|----------------------|--------|------------|
| O1 | `#emp-validade` (1-365) | Carregado da API, aceita número no range | [ ] | |
| O2 | `#emp-desconto-max` (0-100) | Carregado da API, aceita número no range | [ ] | |
| O3 | `#btn-salvar-orc` | PATCH `/empresa/` → notif verde | [ ] | |
| O4 | `#emp-lembrete` | Carregado da API | [ ] | |
| O5 | `#emp-lembrete-texto` | Carregado da API | [ ] | |
| O6 | `#btn-salvar-lembrete` | PATCH `/empresa/` com lembrete → notif verde | [ ] | |
| O7 | Chips de variáveis | Exibidos corretamente (`{cliente_nome}` etc.) | [ ] | |

---

## 3. Seção: Formas de Pagamento

### 3.1 Bancos e PIX

| # | Elemento | Comportamento esperado | Status | Observação |
|---|----------|----------------------|--------|------------|
| F1 | Carregamento inicial | `GET /empresa/pix/bancos` preenche lista | [ ] | |
| F2 | Estado vazio `#bancos-pix-vazio` | Visível quando não há bancos cadastrados | [ ] | |
| F3 | Botão "Novo banco/PIX" | Abre `#modal-banco-pix` com campos vazios | [ ] | |
| F4 | Campos do modal banco | Nome obrigatório, tipo de chave, etc. | [ ] | |
| F5 | Salvar banco novo | POST `/empresa/pix/bancos` → modal fecha, lista atualiza | [ ] | |
| F6 | Click em banco existente | Abre modal com dados preenchidos | [ ] | |
| F7 | Salvar banco editado | PATCH `/empresa/pix/bancos/{id}` → lista atualiza | [ ] | |
| F8 | Excluir banco | DELETE → banco some da lista | [ ] | |

### 3.2 Formas de Pagamento

| # | Elemento | Comportamento esperado | Status | Observação |
|---|----------|----------------------|--------|------------|
| F9 | Carregamento inicial | `GET /financeiro/formas-pagamento` preenche lista | [ ] | |
| F10 | Botão "Nova forma" | Abre `#modal-forma-pagamento` com campos vazios | [ ] | |
| F11 | Checkbox "Exigir entrada" | Mostra/oculta `#forma-campos-entrada` | [ ] | |
| F12 | `#forma-pct-entrada` | Calcula saldo automaticamente (100 - entrada) | [ ] | |
| F13 | Entrada + Saldo > 100% | Mostra `#forma-erro-percentual` | [ ] | |
| F14 | `#forma-preview` | Preview em linguagem natural atualiza ao interagir | [ ] | |
| F15 | Salvar forma nova | POST → modal fecha, lista atualiza | [ ] | |
| F16 | Editar forma existente | Modal abre com dados preenchidos | [ ] | |
| F17 | Toggle ativo/inativo | PATCH `{"ativo": bool}` → estado visual atualiza | [ ] | |
| F18 | Definir como padrão | POST `/{id}/padrao` → badge "padrão" aparece | [ ] | |

---

## 4. Seção: Aparência

| # | Elemento | Comportamento esperado | Status | Observação |
|---|----------|----------------------|--------|------------|
| A1 | `#tema-card-light` | Click define tema claro, `#tema-check-light` visível | [ ] | |
| A2 | `#tema-card-dark` | Click define tema escuro, `#tema-check-dark` visível | [ ] | |
| A3 | Persistência do tema | localStorage `cotte_tema` salvo; mantém ao recarregar | [ ] | |
| A4 | Info de branding | Link para seção "Empresa" funciona | [ ] | |

---

## 5. Seção: Comunicação

| # | Elemento | Comportamento esperado | Status | Observação |
|---|----------|----------------------|--------|------------|
| C1 | Carregamento | Campos preenchidos com dados da API | [ ] | |
| C2 | `#descricao-publica-empresa` | Aceita texto | [ ] | |
| C3 | `#texto-assinatura-proposta` | Aceita texto | [ ] | |
| C4 | `#assinatura-email` | Textarea aceita texto | [ ] | |
| C5 | Botão "Salvar assinatura" | PATCH `/empresa/` → notif verde | [ ] | |
| C6 | `#telefone-operador` | Campo aceita texto | [ ] | |
| C7 | `#mostrar-botao-whatsapp` | Checkbox funcional | [ ] | |
| C8 | `#texto-aviso-aceite` | Textarea aceita texto | [ ] | |
| C9 | `#mensagem-confianca-proposta` | Textarea aceita texto | [ ] | |
| C10 | `#mostrar-mensagem-confianca` | Checkbox funcional | [ ] | |
| C11 | `#btn-salvar-comunicacao` | PATCH `/empresa/` com todos os campos → notif verde | [ ] | |
| C12 | `#notif-whats-visualizacao` | Toggle salva imediatamente | [ ] | |
| C13 | `#anexar-pdf-email` | Toggle salva imediatamente | [ ] | |
| C14 | `#boas-vindas-ativo` | Toggle mostra/oculta campo de mensagem | [ ] | |
| C15 | `#msg-boas-vindas` | Textarea aceita texto | [ ] | |
| C16 | Botão salvar boas-vindas | PATCH `/empresa/` → notif verde | [ ] | |

---

## 6. Seção: Integrações

| # | Elemento | Comportamento esperado | Status | Observação |
|---|----------|----------------------|--------|------------|
| I1 | Carregamento inicial | GET `/empresa/whatsapp/status` define estado do card | [ ] | |
| I2 | Estado desconectado | `#wp-desconectado-state` visível, outros ocultos | [ ] | |
| I3 | Botão "Conectar" | POST `/empresa/whatsapp/conectar` → estado QR Code | [ ] | |
| I4 | Estado QR Code | `#wp-qrcode-state` visível com imagem QR | [ ] | |
| I5 | Polling de conexão | A cada 4s verifica status; ao conectar muda estado | [ ] | |
| I6 | Botão "Novo QR Code" | GET `/empresa/whatsapp/qrcode` → QR atualizado | [ ] | |
| I7 | Botão "Cancelar" | Para polling, volta para estado desconectado | [ ] | |
| I8 | Estado conectado | `#wp-conectado-state` com número exibido | [ ] | |
| I9 | Botão "Desconectar" | DELETE → volta para estado desconectado | [ ] | |
| I10 | Plano sem WhatsApp | `#wp-upgrade-state` visível com CTA de upgrade | [ ] | |

---

## 7. Seção: Plano e Assinatura

| # | Elemento | Comportamento esperado | Status | Observação |
|---|----------|----------------------|--------|------------|
| P1 | `#cfg-plano-badge` | Exibe nome do plano com cor correta | [ ] | |
| P2 | `#cfg-plano-validade` | Exibe data de validade ou "Ativo" | [ ] | |
| P3 | `#cfg-plano-orc` | Exibe limite de orçamentos ou "Ilimitado" | [ ] | |
| P4 | `#cfg-plano-usr` | Exibe limite de usuários ou "Ilimitado" | [ ] | |
| P5 | Cards de upgrade | Visíveis apenas para planos acima do atual | [ ] | |
| P6 | Links de upgrade | Apontam para URL de pagamento externo | [ ] | |
| P7 | `#cfg-multi-usr-status` | Exibe status de multi-usuários conforme plano | [ ] | |

---

## 8. Seção: Segurança

| # | Elemento | Comportamento esperado | Status | Observação |
|---|----------|----------------------|--------|------------|
| S1 | Card "Zona de Perigo" | Visível na seção | [ ] | |
| S2 | Botão "Sair / Logout" | Chama `logout()` → redireciona para login | [ ] | |

---

## Pontos Críticos para Testes Playwright

Prioridade alta (automatizar primeiro):

1. **Navegação** — N1 a N8: troca de seções
2. **Carregamento de dados** — E7, F1, F9: GET da API preenche campos
3. **Salvar empresa** — E12: PATCH com sucesso
4. **Modal banco PIX** — F3 a F8: CRUD completo
5. **Modal forma de pagamento** — F10 a F15: CRUD + validações
6. **Lógica de formas** — F11, F12, F13: entrada/saldo/erro
7. **Tema** — A1 a A3: toggle e persistência
8. **Logout** — S2: funciona e redireciona
