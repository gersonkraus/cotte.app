---
title: Modal Planos Readme
tags:
  - roadmap
prioridade: alta
status: planejado
---
---
title: Modal Planos Readme
tags:
  - roadmap
  - frontend
prioridade: alta
status: planejado
---
# Modal de Seleção de Planos - Implementação Completa

## 📋 Resumo

Implementado modal overlay que aparece automaticamente no dashboard quando o trial de 14 dias expira e não há assinatura ativa.

## 🎯 Funcionalidades Implementadas

### 1. **Detecção Automática de Trial Expirado**
- Verifica `trial_ate` e `assinatura_valida_ate` via endpoint `/empresa/uso`
- Exibe modal apenas quando trial expirou E não há assinatura ativa
- Não exibe para superadmins

### 2. **Modal com 3 Planos**

#### **Starter - R$ 89,90/mês**
- Link: https://pay.kiwify.com.br/mlUv9Ox
- Até 200 orçamentos/mês
- 3 usuários
- Envio por WhatsApp
- Lembretes automáticos
- Relatórios básicos

#### **Pro - R$ 129/mês (RECOMENDADO)**
- Link: https://pay.kiwify.com.br/GEEDagv
- Até 1.000 orçamentos/mês
- 10 usuários
- IA automática (LiteLLM)
- Lembretes automáticos
- Relatórios avançados
- WhatsApp próprio
- Badge "Recomendado" destacado

#### **Business - R$ 189/mês**
- Link: https://pay.kiwify.com.br/pA85TDN
- Orçamentos ilimitados
- Usuários ilimitados
- Tudo do Pro
- Suporte prioritário
- Onboarding personalizado

### 3. **Design e UX**
- Modal overlay com backdrop blur
- Não pode ser fechado (força escolha de plano)
- Animações suaves de entrada (fadeIn + slideUp)
- Responsivo (mobile-first)
- Compatível com dark mode
- Acessibilidade (ARIA attributes)

## 📁 Arquivos Modificados

### `index.html`
- Adicionado HTML do modal antes do `</body>`
- Estrutura com 3 cards de planos
- Atributos de acessibilidade (`role="dialog"`, `aria-modal="true"`)

### `css/style.css`
- Estilos do modal overlay e backdrop
- Cards de planos com hover effects
- Badge "Recomendado" no plano Pro
- Responsividade mobile (< 768px)
- Animações CSS (@keyframes fadeIn, slideUp)

### `js/api.js`
- Função `verificarTrialExpirado(uso)` - detecta trial expirado
- Função `exibirModalPlanos()` - exibe o modal
- Integração com `_preencherUsoPlano()` existente

## 🧪 Como Testar

### Teste 1: Trial Expirado (Modal deve aparecer)
```sql
-- No banco de dados, definir trial_ate no passado
UPDATE empresas 
SET trial_ate = '2026-01-01 00:00:00+00', 
    assinatura_valida_ate = NULL,
    plano = 'trial'
WHERE id = <ID_DA_EMPRESA>;
```

### Teste 2: Assinatura Ativa (Modal NÃO deve aparecer)
```sql
-- Assinatura válida até o futuro
UPDATE empresas 
SET assinatura_valida_ate = '2026-12-31 23:59:59+00',
    plano = 'pro'
WHERE id = <ID_DA_EMPRESA>;
```

### Teste 3: Superadmin (Modal NÃO deve aparecer)
- Login como superadmin
- Modal não deve aparecer mesmo com trial expirado

### Teste 4: Responsividade
- Abrir dashboard em tela desktop (cards lado a lado)
- Abrir em mobile (cards empilhados verticalmente)
- Verificar scroll no modal se necessário

### Teste 5: Dark Mode
- Alternar tema para dark mode
- Verificar contraste e cores do modal

### Teste 6: Fluxo Completo
1. Trial expira → modal aparece
2. Clicar em um plano → abre Kiwify em nova aba
3. Completar pagamento no Kiwify
4. Webhook ativa assinatura automaticamente
5. Retornar ao dashboard → modal não aparece mais

## 🔄 Integração com Sistema Existente

### Webhook Kiwify
O sistema já possui webhook configurado em `/webhooks/kiwify` que:
- Recebe notificação de pagamento
- Atualiza `assinatura_valida_ate` e `plano` da empresa
- Ativa a empresa automaticamente

### Endpoint de Uso
O modal utiliza o endpoint existente:
```
GET /empresa/uso
```

Retorna:
```json
{
  "plano": "trial",
  "trial_ate": "2026-03-01T00:00:00Z",
  "assinatura_valida_ate": null,
  "orcamentos_usados": 10,
  "orcamentos_limite": 50,
  "usuarios_usados": 1,
  "usuarios_limite": 1
}
```

## 🎨 Customização

### Alterar Preços
Editar em `index.html`:
```html
<span class="preco-valor">R$ 89,90</span>
```

### Alterar Links Kiwify
Editar em `index.html`:
```html
<a href="https://pay.kiwify.com.br/mlUv9Ox" target="_blank">
```

### Alterar Mensagem
Editar em `index.html`:
```html
<h2 id="modal-planos-titulo">Seu período de teste acabou...</h2>
```

### Alterar Cores
Editar em `css/style.css`:
```css
.plano-card.plano-destaque {
  border-color: var(--accent); /* Cor do destaque */
}
```

## 🐛 Troubleshooting

### Modal não aparece
1. Verificar console do navegador (F12)
2. Confirmar que `trial_ate` está no passado
3. Confirmar que `assinatura_valida_ate` é null ou passado
4. Verificar se usuário não é superadmin

### Modal aparece mas não deveria
1. Verificar dados no banco: `SELECT trial_ate, assinatura_valida_ate, plano FROM empresas WHERE id = X;`
2. Verificar timezone do servidor vs cliente

### Estilos quebrados
1. Limpar cache do navegador (Ctrl+Shift+R)
2. Verificar se `css/style.css` foi atualizado
3. Verificar console para erros de CSS

## ✅ Checklist de Validação

- [x] Modal HTML adicionado ao index.html
- [x] Estilos CSS completos e responsivos
- [x] Lógica JavaScript de detecção implementada
- [x] Atributos de acessibilidade (ARIA)
- [x] Compatibilidade dark mode
- [x] Links Kiwify corretos
- [x] Preços corretos (Starter R$ 89,90, Pro R$ 129, Business R$ 189)
- [x] Badge "Recomendado" no plano Pro
- [x] Não bloqueia superadmins
- [x] Integração com webhook existente

## 📝 Notas Técnicas

- **Z-index do modal:** 9999 (garante que fica sobre tudo)
- **Backdrop blur:** 8px (efeito glassmorphism)
- **Animação de entrada:** 0.3s fadeIn + 0.4s slideUp
- **Breakpoint mobile:** 768px
- **Não pode fechar:** Sem botão X ou clique fora (design intencional)

## 🚀 Próximos Passos (Opcional)

1. Adicionar analytics para tracking de conversão
2. A/B test de mensagens e preços
3. Adicionar FAQ ou chat de suporte no modal
4. Implementar desconto especial para upgrade rápido
5. Adicionar depoimentos de clientes no modal
