## Objetivo

Definir a menor expansão segura do runtime autônomo do `copiloto-interno` para melhorar diagnóstico real e cobrir filtros gerenciais frequentes sem depender exclusivamente do planner LLM.

## Contexto atual

O runtime autônomo já envia um histórico resumido ao planner SQL via `historico`, mas esse contexto não aparece no `trace/debug` retornado ao frontend. Isso dificulta validar, em produção, qual contexto realmente influenciou o planejamento.

Além disso, a heurística atual de interpretação já cobre alguns sinônimos operacionais, mas ainda não resolve de forma determinística pedidos recorrentes com:

- meses nominais, como `abril`
- períodos civis, como `hoje`, `ontem` e `este mês`
- filtros de status frequentes, como `aprovadas`, `recusadas` e `rascunho`

## Escopo

### Incluído

- expor no `trace` um preview curto do histórico resumido enviado ao planner
- expor métricas simples do histórico usado no planejamento
- reconhecer filtros civis frequentes em linguagem natural
- reconhecer filtros gerenciais frequentes por status de orçamento
- aplicar regra explícita de campo de data por status no fallback SQL hardcoded
- adicionar testes de regressão para trace, interpretação e SQL gerado

### Excluído

- histórico completo no payload de debug
- interpretação aberta de períodos arbitrários como `último trimestre` ou `entre 10 e 18 de abril`
- NLP avançado ou parser externo de datas
- mudanças de contrato no frontend além do consumo passivo do `trace`

## Premissas confirmadas

### Campo de data por status

- `aprovado` usa `aprovado_em`
- `recusado` usa `criado_em`
- `rascunho` usa `criado_em`
- `não aprovado` usa `criado_em`

### Exposição de histórico no debug

O `trace` deve mostrar apenas um preview curto do histórico, não o histórico completo.

## Abordagens consideradas

### 1. Heurística mínima no runtime

Expandir o runtime atual com helpers locais para status, período e preview de histórico.

**Prós**

- menor diff
- menor risco de regressão
- mantém o comportamento determinístico para casos frequentes

**Contras**

- cobertura semântica ainda limitada a regras explícitas

### 2. Parser dedicado de filtros

Extrair um parser pequeno para produzir um objeto normalizado de filtros antes do planner.

**Prós**

- melhora organização para expansões futuras
- deixa a montagem do fallback SQL mais previsível

**Contras**

- aumenta a superfície de código agora
- adiciona estrutura antes de haver necessidade comprovada maior

### 3. Dependência maior do planner LLM

Deixar o runtime apenas identificar um intent genérico e delegar períodos/status ao planner.

**Prós**

- flexibilidade maior para linguagem natural

**Contras**

- previsibilidade menor
- pior diagnóstico quando o planner falha
- cobertura dependente de flag e modelo

### Abordagem escolhida

Adotar a abordagem **1**, com um toque mínimo da abordagem **2**: helpers locais e pequenos, mas sem criar novo módulo ou abstração ampla.

## Desenho proposto

### 1. Enriquecimento do `trace` no passo `plan`

O step `plan` do `trace` deve passar a incluir:

- `history_preview`: texto truncado com poucas linhas e limite fixo de caracteres
- `history_messages`: quantidade de mensagens consideradas no resumo
- `history_truncated`: indicador booleano para informar truncamento

Objetivo:

- permitir diagnóstico real do contexto enviado ao planner
- evitar payload excessivo
- evitar exposição desnecessária de histórico completo no frontend

### 2. Normalização explícita de filtros gerenciais

O runtime deve reconhecer, no mínimo:

- meses nominais: `janeiro` a `dezembro`
- períodos civis rápidos: `hoje`, `ontem`, `este mês`
- status: `aprovado`, `aprovada`, `aprovados`, `aprovadas`, `recusado`, `recusada`, `recusados`, `recusadas`, `rascunho`, `rascunhos`, `não aprovado`, `não aprovada`, `não aprovados`, `não aprovadas`

Essa normalização deve alimentar tanto a interpretação quanto a montagem do fallback SQL.

### 3. Regra de data por status

Quando houver filtro temporal explícito, o fallback SQL deve escolher a coluna de data assim:

- consultas de aprovados: `aprovado_em`
- consultas de recusados: `criado_em`
- consultas de rascunho: `criado_em`
- consultas de não aprovados: `criado_em`

Se não houver status explícito compatível, o comportamento atual pode permanecer conservador.

### 4. Fallback SQL mínimo para casos frequentes

Sem substituir o planner LLM, o runtime deve conseguir gerar SQL hardcoded para consultas frequentes como:

- `orçamentos aprovados em abril`
- `orçamentos aprovados este mês`
- `orçamentos recusados ontem`
- `orçamentos em rascunho este mês`
- `propostas não aprovadas em abril`

O SQL deve continuar simples, com filtros por status e intervalo civil, deixando casos mais abertos para o planner quando necessário.

### 5. Estratégia de datas civis

O parser deve produzir intervalos fechados por dia civil com base no timezone de negócio já usado no sistema.

Regras mínimas:

- `hoje`: início e fim do dia atual
- `ontem`: início e fim do dia anterior
- `este mês`: primeiro dia do mês atual até `agora`
- `abril`: primeiro e último dia de abril do ano corrente por padrão

Se o sistema já tiver utilitário confiável para datas civis, ele deve ser reutilizado. Se não houver, criar helper local mínimo no runtime.

## Estrutura sugerida de implementação

Manter a mudança concentrada em `sistema/app/services/internal_copilot_autonomy_runtime.py`.

Helpers locais esperados:

- `_build_history_preview(...)`
- `_extract_status_filter(...)`
- `_extract_civil_period(...)`
- `_resolve_date_column_for_status(...)`
- `_append_status_and_period_filters(...)`

Os nomes podem variar, mas a responsabilidade deve continuar local e legível.

## Regras de resposta e compatibilidade

- não mudar a estrutura principal do payload
- manter `semantic_contract` compatível
- tratar novos campos de `trace` como aditivos e opcionais
- preservar o planner LLM como tentativa prioritária quando habilitado
- usar fallback hardcoded apenas para melhorar cobertura determinística

## Testes necessários

### Trace/debug

- deve expor `history_preview` no step `plan`
- deve marcar `history_truncated=True` quando o preview for cortado
- deve informar a quantidade de mensagens consideradas

### Interpretação

- reconhecer `abril`
- reconhecer `este mês`
- reconhecer `ontem`
- reconhecer `aprovadas`
- reconhecer `recusadas`
- reconhecer `rascunho`

### SQL fallback

- usar `aprovado_em` para aprovados com filtro temporal
- usar `criado_em` para recusados com filtro temporal
- usar `criado_em` para rascunho com filtro temporal
- aplicar `status <> 'APROVADO'` para não aprovados

## Riscos conhecidos

- `abril` sem ano explícito assume o ano corrente e pode divergir da intenção em virada de ano
- `não aprovadas` é uma categoria operacional conveniente, mas semanticamente ampla; a regra inicial continuará conservadora
- consultas muito abertas continuarão dependendo do planner LLM para melhor cobertura

## Validação

Antes de concluir a implementação:

1. rodar os testes de runtime autônomo relacionados
2. confirmar no output real que o `trace` inclui o preview curto
3. confirmar por teste que a coluna de data muda conforme o status
4. confirmar que não houve quebra do payload legado com `semantic_contract`

## Resultado esperado

Após essa expansão, o copiloto deve ficar mais auditável e mais confiável para perguntas gerenciais recorrentes, especialmente consultas de orçamentos por status e período civil simples, sem aumentar muito a complexidade do runtime.
