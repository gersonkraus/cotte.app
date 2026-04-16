---
title: 2026 04 15 124454 Poss Vel Usar O Litellm Para Poder Definir
tags:
  - documentacao
prioridade: media
status: documentado
---
# Plano: Arquitetura de Gateway LLM com LiteLLM Proxy

## Objetivo
Desacoplar a escolha e configuração dos modelos de Inteligência Artificial do código-fonte do sistema COTTE, utilizando o **LiteLLM Proxy Server** como um gateway unificado. Isso permitirá configurar modelos diferentes (ex: um mais rápido/barato para os clientes e um mais inteligente para o Copiloto Técnico) dinamicamente, sem precisar alterar código ou reiniciar o backend.

## Contexto Atual / Diagnóstico
- Atualmente, o sistema usa o **SDK Python do LiteLLM** dentro de `sistema/app/services/ia_service.py`.
- O modelo e provedor (`AI_PROVIDER` e `AI_MODEL`) são lidos do arquivo `.env` da aplicação principal e aplicados globalmente. Se você quiser trocar de modelo, precisa mudar o `.env` do backend e reiniciar a aplicação.
- Para rotear chamadas do Assistente Operacional para o `gpt-4o-mini` e as do Copiloto Técnico para o `claude-3.5-sonnet`, precisaríamos encher o código backend com chaves de API da OpenAI e da Anthropic.

## Abordagem Proposta
Sim, **é perfeitamente possível e é a melhor prática atual de mercado (arquitetura de AI Gateway)**. 
A ideia é subir o **LiteLLM Proxy Server** (uma aplicação à parte, rodando em sua própria porta/container). 

Nesse cenário:
1. O LiteLLM Proxy gerencia todas as suas chaves de API (OpenAI, Anthropic, Google, etc.).
2. No LiteLLM Proxy, você cria **Alias/Virtual Models**. Por exemplo:
   - `modelo-operacional` -> aponta para `openai/gpt-4o-mini`
   - `modelo-tecnico` -> aponta para `anthropic/claude-3-5-sonnet`
3. O seu sistema COTTE (`ia_service.py`) passa a conversar **apenas** com o LiteLLM Proxy usando uma única chave de acesso interna.
4. O código no COTTE apenas diz: "Ei, LiteLLM, mande essa mensagem para o `modelo-tecnico`". O Proxy faz o roteamento transparente.

## Plano Passo a Passo

### 1. Configurar e Subir o LiteLLM Proxy
- Criar um arquivo `litellm_config.yaml` na raiz da infraestrutura definindo o roteamento:
  ```yaml
  model_list:
    - model_name: modelo-operacional
      litellm_params:
        model: openai/gpt-4o-mini
        api_key: os.environ/OPENAI_API_KEY
    - model_name: modelo-tecnico
      litellm_params:
        model: anthropic/claude-3-5-sonnet-20241022
        api_key: os.environ/ANTHROPIC_API_KEY
  ```
- Subir o Proxy (via Docker, tmux, ou serviço systemd), escutando, por exemplo, na porta 4000.

### 2. Atualizar o Backend do COTTE (Variáveis de Ambiente)
- Modificar o `.env` do backend para apontar para o proxy:
  ```env
  AI_PROVIDER=openai # O proxy usa o padrão OpenAI
  AI_API_BASE=http://localhost:4000/v1
  AI_API_KEY=chave-interna-do-litellm
  ```

### 3. Modificar o `ia_service.py` para Suportar o Gateway
- Atualizar a classe `IAService` para aceitar um `model_override` ou ler as requisições baseadas no destino, e utilizar o `api_base` injetado pelo `.env`.

### 4. Modificar o Orquestrador (`cotte_ai_hub.py`)
- Na hora de chamar o `ia_service.chat()`, identificar de onde vem a requisição.
- Se `resolved_engine == ENGINE_INTERNAL_COPILOT`:
  Passar argumento instruindo o uso do `modelo-tecnico`.
- Caso contrário:
  Instruir o uso do `modelo-operacional`.

## Arquivos Provavelmente Modificados
- Novo arquivo: `litellm_config.yaml` (ou na infraestrutura Docker)
- `.env` e `sistema/app/core/config.py`
- `sistema/app/services/ia_service.py`
- `sistema/app/services/cotte_ai_hub.py`

## Testes / Validação
1. **Teste de Gateway:** Fazer curl localmente para `http://localhost:4000/v1/chat/completions` chamando o `modelo-tecnico` e validar se a Anthropic responde.
2. **Teste Operacional:** No assistente do cliente (assistente-ia.html), confirmar se a resposta mantém a latência e o custo baixos (passando pelo GPT-4o-mini no proxy).
3. **Teste do Copiloto:** Acessar o `copiloto-tecnico.html`, fazer uma pergunta de código e validar via logs do LiteLLM Proxy se a requisição foi roteada corretamente para o modelo premium.

## Riscos, Tradeoffs e Questões em Aberto
- **Vantagens:** Observabilidade centralizada (o LiteLLM Proxy tem uma UI que mostra os custos separados por modelo/usuário), proteção de chaves de API, e facilidade absurda para trocar modelos (se sair o GPT-5 amanhã, você só altera o YAML do Proxy, não precisa encostar no código do COTTE nem fazer deploy).
- **Tradeoff:** Adiciona um novo componente à sua infraestrutura (o LiteLLM Proxy Server precisará estar rodando continuamente ao lado do backend do COTTE). Se ele cair, as IAs param. É necessário garantir que ele suba automaticamente com o sistema (ex: docker-compose ou systemd).