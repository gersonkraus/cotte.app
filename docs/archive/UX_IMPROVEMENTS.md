---
title: Ux Improvements
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Ux Improvements
tags:
  - documentacao
  - frontend
prioridade: media
status: documentado
---
# Melhorias de UX — Frontend COTTE

## Itens Implementados

### 1. ✅ Cards alternativos para tabela mobile
- Tabela é substituída por cards empilhados em telas < 640px
- Cards mostram todas as informações (número, cliente, valor, status, data, ações)
- Botão "⋯" abre menu dropdown com todas as ações

### 2. ✅ Contagem nos filter-chips
- Chips de status mostram quantidade de orçamentos (ex: "Enviados (5)")
- Atualiza dinamicamente após filtros

### 3. ✅ Estados de erro descritivos
- Mensagens de erro contextuais com sugestões de ação
- Estados: sem conexão, sessão expirada, limite atingido, erro genérico

### 4. ✅ Menu dropdown de ações mobile
- Botão "⋯" em cada card mobile abre popover com ações
- Área de toque ≥ 44px
- Fecha ao clicar fora

### 5. ✅ Sticky footer no modal de orçamento
- Total fixo no rodapé do modal durante scroll
- Sempre visível ao preencher itens

### 6. ✅ Paginação melhorada
- Indicador "Página X de Y"
- Botões anterior/próximo
- Seletor de itens por página