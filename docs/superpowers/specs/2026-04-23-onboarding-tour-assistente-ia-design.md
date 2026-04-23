# Spec: Onboarding guiado no primeiro acesso ao Assistente IA

**Data:** 2026-04-23
**Status:** Aprovado

---

## Contexto

Novas empresas chegam ao assistente IA sem nenhuma referência de como usá-lo. O abandono por falta de clareza é alto — o usuário abre a página, vê o campo de texto e não sabe o que digitar. Este onboarding reduz essa fricção com um tour de 3 passos exibido apenas na primeira visita, antes de qualquer interação.

---

## Comportamento

- **Quem vê:** empresas com `total_mensagens_ia == 0` (nunca enviaram uma mensagem ao assistente)
- **Onde aparece:** no lugar do welcome card existente (`#assistente-welcome`), na área central da página
- **Pode pular:** sim — botão "Pular" visível em qualquer passo
- **Desaparece automaticamente:** após a primeira mensagem enviada, `total_mensagens_ia` passa a ser > 0, e na próxima visita o tour não é mais exibido

---

## Backend

**Arquivo:** `sistema/app/routers/ai_hub.py`
**Endpoint:** `GET /ai/assistente/capabilities`

Adicionar o campo `mostrar_tour_onboarding` ao response existente:

```python
caps["mostrar_tour_onboarding"] = (
    (current_user.empresa.total_mensagens_ia or 0) == 0
)
```

- Nenhuma migration de banco necessária — `total_mensagens_ia` já existe em `Empresa`
- O campo retorna `true` enquanto a empresa nunca enviou mensagem; passa a `false` após a primeira

---

## Frontend

**Arquivos:**
- `sistema/cotte-frontend/assistente-ia.html` — componente do tour
- `sistema/cotte-frontend/css/assistente-ia.css` — estilos do tour

### Inicialização

Após `CapabilityFlagsService.preload()` completar:

```javascript
if (CapabilityFlagsService.isEnabledSync('mostrar_tour_onboarding')) {
    renderTour();
} else {
    renderWelcomeCard(); // comportamento atual, sem mudança
}
```

### Slides do tour

| Passo | Ícone | Título | Descrição | Exemplo |
|-------|-------|--------|-----------|---------|
| 1 | 🤖 | O que o Assistente IA faz | Gerenciar clientes, criar orçamentos, analisar financeiro e responder dúvidas do seu negócio — tudo por chat. | "Quais orçamentos estão pendentes hoje?" |
| 2 | 📋 | Como pedir um orçamento | Descreva o cliente e o serviço. O assistente busca o catálogo e monta o orçamento pronto para enviar. | "Crie um orçamento para João — instalação elétrica residencial" |
| 3 | 📊 | Como pedir relatório financeiro | Peça saldos, receitas, despesas ou análises do caixa. O assistente acessa os dados em tempo real. | "Quanto entrou esse mês e qual meu saldo atual?" |

### Layout do tour

```
┌─────────────────────────────────────────────┐
│  Passo 1 de 3                      [Pular]  │
│                                             │
│              🤖                             │
│   O que o Assistente IA faz                 │
│   Gerenciar clientes, criar orçamentos,     │
│   analisar financeiro e responder dúvidas   │
│   do seu negócio — tudo por chat.           │
│                                             │
│   Experimente:                              │
│   "Quais orçamentos estão pendentes hoje?"  │
│                                             │
│   ●  ○  ○                    [Próximo →]   │
└─────────────────────────────────────────────┘
```

- **Indicadores de passo:** pontos clicáveis (● ○ ○)
- **Navegação:** botões Anterior / Próximo; no último passo, "Próximo" vira "Concluir"
- **Pular:** sempre visível no canto superior direito

### CSS

Reutiliza variáveis e animações já definidas em `assistente-ia.css`. Nenhum arquivo CSS novo. Adicionar bloco `/* === Tour de Onboarding === */` no mesmo arquivo.

### Transição ao concluir/pular

```javascript
function finalizarTour() {
    document.getElementById('assistente-tour')?.remove();
    // Exibir o welcome card existente: o elemento #assistente-welcome
    // (ou equivalente na estrutura atual do DOM) que estava oculto durante o tour
    document.getElementById('assistente-welcome')?.classList.remove('hidden');
}
```

A partir daí o fluxo é idêntico ao atual — `sendMessage()` chama `dismissWelcome()` e inicia o chat. O implementador deve confirmar o seletor correto do welcome card inspecionando `assistente-ia.html` linhas 418-443.

---

## Tratamento de erros

- Se `/ai/assistente/capabilities` falhar (rede, 403, timeout): `mostrar_tour_onboarding` não estará disponível → `isEnabledSync` retorna `false` por padrão → welcome card normal é exibido. O tour nunca bloqueia o usuário.

---

## Arquivos modificados

| Arquivo | Mudança |
|---------|---------|
| `sistema/app/routers/ai_hub.py` | +1 linha no endpoint `GET /ai/assistente/capabilities` |
| `sistema/cotte-frontend/assistente-ia.html` | Componente `#assistente-tour` + lógica JS de inicialização/navegação |
| `sistema/cotte-frontend/css/assistente-ia.css` | Estilos do tour (bloco novo no arquivo existente) |

---

## Verificação end-to-end

1. Resetar `total_mensagens_ia = 0` em uma empresa de teste
2. Abrir `assistente-ia.html` → tour aparece no lugar do welcome card
3. Navegar pelos 3 slides — verificar indicadores de ponto, botões Anterior/Próximo
4. Clicar "Pular" no passo 1 → tour desaparece, welcome card aparece
5. Concluir o tour no passo 3 → mesmo resultado
6. Enviar uma mensagem → `total_mensagens_ia` incrementa para 1
7. Recarregar a página → welcome card normal, sem tour
8. Testar com empresa que já tem mensagens → nunca exibe o tour
9. Simular falha no endpoint capabilities → welcome card aparece normalmente
