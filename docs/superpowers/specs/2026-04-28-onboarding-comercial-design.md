# Onboarding Checklist — Módulo Comercial

## Objetivo

Guiar novos usuários do módulo Comercial pelos 5 passos obrigatórios de configuração inicial, com explicação do que é cada item e atalho direto para a aba correta.

## Comportamento de exibição

- **Aparece** na primeira visita ao módulo E enquanto houver passos incompletos.
- **Detecta primeira visita** via `localStorage` (`cotte_comercial_onboarding_seen`).
- **Detecta conclusão** verificando os caches já carregados pelo core + 1 chamada leve para leads.
- **Ocultar por agora**: botão que seta flag de sessão (`sessionStorage`) — some até recarregar, mas volta na próxima visita se ainda houver pendências.
- **Some definitivamente** quando todos os 5 passos estiverem completos; remove a flag do localStorage.

## Passos do checklist

| # | Título | Explicação | Detecção de conclusão | Botão → |
|---|--------|-----------|----------------------|---------|
| 1 | Criar um Segmento | Classifica seus leads por área de atuação (ex: Tecnologia, Varejo) | `segmentosCache.length > 0` | Aba Cadastros |
| 2 | Criar uma Origem | Indica de onde o lead veio (ex: Instagram, Indicação) | `origensCache.length > 0` | Aba Cadastros |
| 3 | Criar Etapas do Pipeline | As fases do seu processo de vendas (ex: Contato → Proposta → Fechado). Necessário para o Kanban funcionar | `pipelineStages.length > 0` | Aba Cadastros |
| 4 | Criar um Template de Mensagem | Mensagens pré-escritas com variáveis como {nome} e {empresa}, para WhatsApp ou e-mail | `templatesCache.length > 0` | Aba Templates |
| 5 | Adicionar seu primeiro Lead | Contatos que você quer converter em clientes. **Dica extra**: tem uma lista? Use a Importação em lote | `GET /tenant/comercial/leads?limit=1` → `total > 0` | Aba Leads (+ dica de Importação) |

## Visual

- **Localização**: topo do `#briefing-container`, na aba "Hoje"
- **Tema**: usa variáveis CSS do projeto (`--surface`, `--text`, `--border`, `--accent`, `--muted`) — adapta automaticamente ao modo claro/escuro
- **Estados dos passos**:
  - ✓ Concluído: fundo verde suave, texto com line-through
  - → Próximo (primeiro incompleto): fundo âmbar, botão "Ir →" ativo
  - Pendente: opacidade reduzida, botão desabilitado visualmente mas clicável
- **Barra de progresso**: `X/5` com preenchimento proporcional

## Arquitetura

- **Arquivo novo**: `sistema/cotte-frontend/js/tenant-comercial-onboarding.js`
- **Carregado no HTML**: após `tenant-comercial-core.js`, antes do `tenant-comercial.js`
- **Ativação**: chamado em `carregarCadastrosCache()` (após caches prontos) via `OnboardingComercial.init()`
- **Navegação**: `OnboardingComercial` usa a função global de troca de tab já existente no core

## Detecção de estado

```js
// Dados já disponíveis pós-carregarCadastrosCache():
segmentosCache.length > 0   // passo 1
origensCache.length > 0     // passo 2
pipelineStages.length > 0   // passo 3
templatesCache.length > 0   // passo 4

// Chamada leve adicional:
GET /tenant/comercial/leads?limit=1  // passo 5 — total > 0
```

## O que NÃO está no escopo

- Wizard interativo de criação dentro do onboarding (abre a aba, não o modal)
- Personalização dos passos por empresa
- Analytics de conclusão do onboarding
