# Novo Classificador Híbrido & Auto-Healing Tests

## O Problema Original
Antes, o assistente usava um roteamento puramente baseado em Expressões Regulares (Regex) para determinar qual ferramenta chamar. Se o usuário pedisse *"Crie um ranking do valor total comprado"*, a regex exigia exatamente a palavra "ranking de cliente". Ao falhar, o sistema ativava o "Fallback de Conversação" (sem acesso ao banco de dados), resultando em respostas genéricas em texto puro em vez de gráficos reais.

## A Solução: Arquitetura Híbrida (Regex + LLM Semântico)
Implementamos uma arquitetura de funil (Funnel Routing) em `ai_intention_classifier.py` e `cotte_ai_hub.py`:
1. **Camada 1 (Zero-Cost / Regex):** Tenta casar a intenção com padrões estritos (ex: *"qual meu saldo"*). Retorna em 0ms e custo zero.
2. **Camada 2 (Semantic Routing - Novidade!):** Se o Regex falhar (ou seja, achar que é um bate-papo qualquer), a frase é enviada a um LLM ultrarrápido (`google/gemini-2.5-flash` via OpenRouter). O LLM é instruído a classificar a semântica da frase e devolver apenas o Enum correto (ex: `GERAR_RELATORIO`). 
3. **Extrator JSON Dinâmico:** Se a intenção for confirmada como relatório mas faltarem parâmetros de agrupamento (ex: "cliente", "tempo"), uma nova função (`_v2_parse_relatorio_params_semantico`) extrai esses parâmetros via JSON usando a inteligência do LLM.

## Testes de Mutação (Auto-Healing Test Suite)
Em `sistema/tests/test_ai_intention_classifier.py`, criamos:
1. **Testes de Regressão Estáticos:** Garantem que as regex originais continuam funcionando.
2. **Testes de Mutação (Auto-Healing):** Uma *fixture* que usa o LLM para gerar variações coloquiais, com gírias ou erros de digitação (ex: *"Bora vê os clientes que mais gastaram"*), e testa se o Classificador Híbrido consegue roteá-las corretamente.
   - **Importante:** Esse teste só roda se a variável `RUN_AI_MUTATION_TESTS=true` estiver ativada, economizando tempo e custos de API no desenvolvimento local. Ideal para rodar em esteiras de CI (GitHub Actions).

## Como Configurar e Testar
Nenhuma variável nova é necessária no seu `.env` além das que já gerenciam o LLM:
```env
AI_PROVIDER=openrouter
AI_API_KEY="sk-or-..."
AI_TECHNICAL_MODEL=google/gemini-2.5-flash
```

Para rodar o teste de mutação manualmente e ver a mágica do LLM estressando o seu próprio classificador:
```bash
export AI_API_KEY="sua_chave"
RUN_AI_MUTATION_TESTS=true pytest sistema/tests/test_ai_intention_classifier.py -v
```
