# Design: Templates de Mensagem para Briefing do Comercial

**Data:** 2026-04-29
**Status:** Aprovado para implementação

## Objetivo

Permitir pré-cadastrar templates de mensagem que podem ser usados no briefing diário do comercial, como alternativa aos rascunhos gerados pela IA.

## Contexto

O briefing diário gera rascunhos de mensagem dinamicamente via IA para cada lead. O usuário deseja:
1. Pré-cadastrar templates personalizados
2. Escolher no momento do briefing entre usar template ou rascunho da IA

## Solução

Reutilizar o sistema de templates existente (`TenantCommercialTemplate`), estendendo-o com novas variáveis e integrando-o na UI do briefing.

## Alterações

### 1. Backend: Estender preview de template

**Arquivo:** `app/routers/tenant/comercial_templates.py`

Adicionar novas variáveis ao endpoint de preview:

| Variável | Fonte | Exemplo |
|----------|-------|---------|
| `{dias_sem_contato}` | Calculado do lead | 5 |
| `{score}` | `lead.score` | quente |
| `{etapa}` | `lead.status_pipeline` | proposta_enviada |
| `{valor}` | `lead.valor_proposto` | R$ 500 |
| `{plano}` | `lead.plano_interesse` | Pro |

**Implementação:**
- Calcular dias desde último contato
- Formatar valor como moeda
- Traduzir etapa para label legível

### 2. Frontend: Integrar templates no briefing

**Arquivo:** `cotte-frontend/js/tenant-comercial-briefing.js`

**Adicionar ao card:**
- Botão "📋 Template" após "✓ Enviar agora"
- Função `selecionarTemplate(leadId)` que abre dropdown
- Preview do template selecionado
- Opção de usar o template ou cancelar

**Nova função:**
```javascript
selecionarTemplate: async function(leadId, tipoAcao) {
  // 1. Buscar templates do tipo followup filtrados por canal
  // 2. Exibir dropdown
  // 3. Ao selecionar, chamar preview endpoint
  // 4. Exibir preview com opção de usar ou cancelar
  // 5. Se usar, substituir rascunho pelo template preenchido
}
```

### 3. Frontend: Atualizar gerenciador de templates

**Arquivo:** `cotte-frontend/js/tenant-TemplatesManager.js`

Adicionar helper de variáveis disponíveis para briefing:
- Atualizar lista de variáveis no modal de template
- Documentar variáveis específicas do briefing

### 4. HTML: Atualizar modal de template

**Arquivo:** `cotte-frontend/tenant-comercial.html`

Atualizar seção de variáveis no modal de template para incluir:
- `{dias_sem_contato}`
- `{score}`
- `{etapa}`
- `{valor}`
- `{plano}`

## Fluxo de Uso

```
1. Usuário acessa aba "Hoje" no comercial
2. Briefing carrega com rascunhos gerados pela IA
3. Em cada card, usuário pode:
   a) Usar rascunho da IA diretamente
   b) Clicar "📋 Template" → selecionar → preview → usar
4. Após selecionar template, o texto substitui o rascunho
5. Usuário pode editar antes de enviar
6. Clica "✓ Enviar agora" para enviar
```

## Critérios de Aceitação

1. [ ] Botão "📋 Template" aparece em cada card do briefing
2. [ ] Dropdown mostra templates do tipo followup filtrados por canal
3. [ ] Preview mostra template com variáveis preenchidas
4. [ ] Usuário pode usar template ou cancelar
5. [ ] Template usado substitui rascunho da IA
6. [ ] Variáveis do briefing funcionam corretamente
7. [ ] Modal de template mostra novas variáveis

## Riscos

- **Baixo:** Mudanças são aditivas, não quebram funcionalidade existente
- **Mitigação:** Testar manualmente o fluxo completo

## Testes

1. Criar template followup com variáveis do briefing
2. Abrir briefing e clicar em "📋 Template"
3. Selecionar template e verificar preview
4. Usar template e verificar substituição do rascunho
5. Editar e enviar mensagem
