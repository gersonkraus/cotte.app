---
title: 2026 04 15 131211 Mas Se Usar A Openrouter Vou Poder Escolher
tags:
  - documentacao
prioridade: media
status: documentado
---
# Plano: Configuração Dinâmica de Modelos via OpenRouter

## Objetivo
Permitir que o administrador escolha e troque os modelos de Inteligência Artificial (tanto o modelo do assistente de clientes quanto o do copiloto técnico) a qualquer momento, utilizando o OpenRouter, **sem precisar alterar uma única linha de código-fonte**.

## Como o OpenRouter Viabiliza Isso
O sistema COTTE já usa a biblioteca `LiteLLM`. Essa biblioteca foi criada exatamente para normalizar todas as APIs (OpenAI, Google, Anthropic) no mesmo formato. 

Ao configurar sua conta no OpenRouter, você ganha acesso a **centenas** de modelos. Como eles já seguem o padrão da OpenAI/LiteLLM, a escolha do modelo passa a ser apenas uma *string* de texto configurada no seu painel de hospedagem (Railway, Render, VPS, ou arquivo `.env`).

## Abordagem Proposta: Variáveis de Ambiente Dedicadas
Faremos uma única alteração arquitetural final no código para criar dois "slots" de configuração independentes. A partir de então, você nunca mais precisará abrir o código para trocar a IA.

1. **`AI_MODEL`**: Define qual IA atende aos seus clientes finais (Assistente Operacional).
2. **`AI_TECHNICAL_MODEL`**: Define qual IA atende você, Superadmin (Copiloto Técnico).

## Plano Passo-a-Passo

### 1. Atualizar o `config.py` e `.env`
Adicionar o novo slot de configuração:
```python
# Em sistema/app/core/config.py
AI_PROVIDER: str = "openrouter"
AI_MODEL: str = "openai/gpt-4o-mini"
AI_TECHNICAL_MODEL: str = "anthropic/claude-3.5-sonnet"
AI_API_KEY: Optional[str] = None # Aqui vai a chave do OpenRouter
```

### 2. Preparar o `ia_service.py` para Trocas Dinâmicas
Modificar a função `chat` e `chat_stream` para aceitar um argumento de substituição (`model_override`):
```python
async def chat(self, messages, tools=None, temperature=0.3, max_tokens=4000, model_override=None):
    modelo_final = model_override if model_override else self.model
    # ...
    response = await acompletion(
        model=modelo_final,
        # ...
    )
```

### 3. Orquestrar a Separação no Hub (`cotte_ai_hub.py`)
No momento em que a mensagem chega no orquestrador `assistente_unificado_v2`, o código avalia qual é a Engine. 
- Se for `ENGINE_INTERNAL_COPILOT`, ele enviará o `settings.AI_TECHNICAL_MODEL` como override.
- Caso contrário, enviará o padrão.

## Como será a sua rotina no futuro (Sem Alterar Código)

Quando esse plano for implementado, o seu código estará blindado. 
Se amanhã for lançado o "GPT-5" e você quiser testá-lo no Copiloto Técnico, você fará apenas o seguinte:

1. Abrirá as configurações de Variáveis de Ambiente do seu servidor/hospedagem.
2. Trocará o valor de `AI_TECHNICAL_MODEL` de `anthropic/claude-3.5-sonnet` para `openai/gpt-5`.
3. Salvará e o servidor reiniciará automaticamente.
4. **Pronto.** O Copiloto Técnico agora roda no GPT-5. O assistente dos seus clientes continuará rodando seguro e barato no GPT-4o-mini.

## Arquivos que sofrerão alteração (Pela última vez)
- `sistema/app/core/config.py`
- `sistema/app/services/ia_service.py`
- `sistema/app/services/cotte_ai_hub.py`

## Testes / Validação
1. Configurar uma chave de teste do OpenRouter no `.env`.
2. Definir o `AI_MODEL` como `google/gemini-flash-1.5` e o `AI_TECHNICAL_MODEL` como `anthropic/claude-3-haiku`.
3. Entrar no chat operacional (cliente) e perguntar "Qual modelo de IA você é?". Validar se ele se comporta como Google.
4. Entrar no chat do Copiloto Técnico e perguntar "Qual modelo de IA você é?". Validar se ele responde como Anthropic.

## Conclusão
Sim, o OpenRouter (em conjunto com o LiteLLM já presente no seu sistema) é a chave de ouro para libertar você de ter que programar integrações com cada IA nova que sai no mercado. Após essa configuração de "Slots", a troca de IAs vira apenas uma troca de texto no painel do servidor.
