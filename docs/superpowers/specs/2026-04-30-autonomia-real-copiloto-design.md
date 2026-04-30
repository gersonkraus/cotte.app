## Objetivo

Definir a arquitetura do novo copiloto com autonomia real para interpretar perguntas, gerar consultas, executar leitura no banco de dados restrita ao `empresa_id` do usuário e montar respostas úteis, sem depender de catálogo de tools exposto ao modelo.

## Contexto atual

O fluxo atual do copiloto interno ainda passa pelo `assistente_unificado_v2` e pelo loop de `tool_calls`, inclusive para consultas SQL. Isso impede classificar o comportamento atual como autonomia real. O objetivo desta proposta é substituir esse modelo por um runtime próprio do copiloto, com planner, guardrails e executor internos.

## Escopo

### Incluído

- interpretação da pergunta do operador
- planejamento interno da consulta
- geração híbrida de consulta: intenção estruturada primeiro, fallback controlado para SQL
- execução de leituras de banco restritas ao `empresa_id` do usuário
- composição da resposta final em linguagem natural com suporte a tabela/resumo
- suporte futuro a `INSERT`, `UPDATE` e `DELETE` apenas com confirmação explícita
- auditoria completa de pergunta, plano, SQL final, bloqueios e métricas

### Excluído neste desenho inicial

- execução automática de escrita
- comandos `ALTER`, `DROP`, CTEs mutáveis e múltiplas statements
- acesso fora do escopo do `empresa_id`
- dependência de catálogo de tools como interface principal do modelo

## Objetivos funcionais

O novo copiloto deve:

1. interpretar a pergunta do operador
2. identificar intenção, entidades, período, agregações e formato de resposta esperado
3. montar um plano de consulta interno
4. gerar SQL apenas quando necessário e sempre sob validação do backend
5. executar a consulta de forma segura
6. responder com base no resultado real retornado
7. bloquear ou degradar o fluxo quando não conseguir provar segurança

## Objetivos não funcionais

- segurança por backend, não por prompt
- isolamento obrigatório por `empresa_id`
- observabilidade completa
- rollout incremental e reversível
- baixo risco de regressão no frontend atual
- capacidade de suportar perguntas abertas de leitura

## Abordagens consideradas

### 1. SQL direto pelo LLM

O modelo gera SQL diretamente e o backend só valida e executa.

**Prós**
- implementação mais rápida
- maior flexibilidade inicial

**Contras**
- maior risco de deriva
- validação mais frágil
- dificuldade maior de garantir isolamento por `empresa_id`

### 2. Intenção estruturada apenas

O modelo gera apenas uma AST/intenção e o backend compila tudo para SQL.

**Prós**
- previsibilidade alta
- segurança forte

**Contras**
- baixa cobertura inicial para perguntas abertas
- rigidez excessiva para o escopo desejado

### 3. Híbrido controlado

O modelo tenta primeiro um plano estruturado e, quando necessário, usa fallback para SQL controlado e validado.

**Prós**
- melhor equilíbrio entre cobertura e segurança
- atende perguntas abertas melhor
- reduz dependência de tool calling

**Contras**
- exige validador/compilador robusto
- requer observabilidade mais cuidadosa

### Abordagem escolhida

Adotar a abordagem **híbrida controlada**.

## Arquitetura proposta

O novo runtime do copiloto será composto por cinco estágios principais.

### 1. Interpretador

Responsável por analisar a pergunta e extrair:

- intenção principal
- entidades de domínio mencionadas
- período/filtros implícitos ou explícitos
- tipo de agregação desejada
- formato esperado de resposta
- ambiguidades relevantes

Saída esperada: um objeto normalizado de intenção.

### 2. Planner híbrido

Recebe a intenção normalizada e tenta gerar um plano estruturado contendo:

- tabelas candidatas
- colunas candidatas
- filtros
- joins previstos
- agregações
- ordenação
- limite sugerido

Se o plano estruturado for insuficiente, o planner gera um SQL candidato controlado para ser revisado pelo backend.

Saída esperada:

- `structured_plan`, quando possível
- `sql_candidate`, quando necessário
- racional interno resumido para debug/auditoria

### 3. Validador/compilador

Camada crítica de segurança e governança.

Responsabilidades:

- compilar `structured_plan` para SQL quando possível
- validar `sql_candidate` quando houver fallback
- permitir `SELECT` dentro dos guardrails
- exigir confirmação explícita para `INSERT`, `UPDATE` e `DELETE`
- bloquear sempre `ALTER`, `DROP`, CTEs mutáveis e múltiplas statements
- impor `LIMIT` máximo e timeout
- validar allowlist de tabelas, colunas, joins e funções
- provar isolamento por `empresa_id`
- reescrever a consulta de forma conservadora quando possível
- bloquear a execução quando segurança não puder ser provada

### 4. Executor interno único

Executa apenas a consulta já validada, sem expor nome de tool ao modelo.

Responsabilidades:

- executar a query final
- devolver colunas, linhas e metadados
- registrar latência
- informar volume retornado
- propagar sinais de risco ou degradação

### 5. Compositor de resposta

Transforma o resultado bruto em resposta útil ao operador.

Responsabilidades:

- responder diretamente à pergunta
- produzir resumo quando a pergunta for analítica
- anexar tabela quando houver ganho real
- explicar ambiguidades ou ausência de resultado
- sugerir refinamentos quando apropriado

## Regras de segurança

### 1. Leitura por padrão

- `SELECT` pode executar se passar em todas as validações

### 2. Escrita sob confirmação

- `INSERT`, `UPDATE` e `DELETE` nunca executam automaticamente
- o copiloto deve explicar a intenção da alteração
- a execução só pode ocorrer após confirmação explícita

### 3. Comandos sempre bloqueados

- `ALTER`
- `DROP`
- CTEs mutáveis
- múltiplas statements na mesma execução

### 4. Restrição obrigatória por empresa

Toda consulta precisa estar restrita ao `empresa_id` do usuário atual.

Regras:

- se a tabela tiver `empresa_id`, o filtro deve estar presente
- se a tabela não tiver `empresa_id` direto, o compilador deve provar o vínculo via join seguro
- se esse vínculo não puder ser provado, a consulta deve ser bloqueada

### 5. Allowlist estrutural

O backend deve controlar explicitamente:

- tabelas liberadas
- colunas liberadas
- joins permitidos
- funções permitidas
- agregações permitidas

### 6. Governança operacional

- `LIMIT` máximo obrigatório
- timeout curto por consulta
- paginação para resultados grandes
- bloqueio de consultas excessivas quando detectável

### 7. Fallback seguro

Quando a segurança não puder ser provada de primeira:

1. tentar reescrita conservadora
2. se ainda não for seguro, bloquear e pedir reformulação

## Fluxo de resposta

Após execução validada, o copiloto deve seguir este fluxo:

1. entender a pergunta
2. planejar a busca
3. executar a consulta
4. interpretar o resultado
5. montar a resposta final

### Regras de composição

- perguntas diretas: resposta curta com evidência mínima
- perguntas analíticas: resumo + tabela quando fizer sentido
- ambiguidades: explicar e sugerir refinamento
- ausência de resultado: informar claramente sem inventar
- resposta sempre baseada no resultado real, nunca em preenchimento probabilístico

### Payload final sugerido

- `answer`
- `summary`
- `table`
- `sql_preview` opcional para debug interno
- `safety`
- `needs_confirmation`
- `suggested_followups`

## Auditoria e observabilidade

Cada execução deve registrar:

- pergunta original
- intenção normalizada
- plano estruturado
- SQL candidato, quando existir
- SQL final executado
- decisão de segurança
- motivo de bloqueio, quando houver
- latência
- total de linhas retornadas
- necessidade de confirmação

O debug do frontend deve distinguir explicitamente:

- plano estruturado
- fallback SQL
- execução bloqueada
- resposta baseada em leitura real

## Rollout proposto

### Fase 1 — modo sombra

O fluxo atual continua respondendo ao usuário, enquanto o novo runtime roda em paralelo apenas para avaliação.

Objetivos:

- medir taxa de sucesso
- medir taxa de bloqueio
- avaliar cobertura do filtro por `empresa_id`
- comparar qualidade de respostas

### Fase 2 — read-only controlado

Ativar o novo runtime para consultas `SELECT`.

Condições:

- auditoria completa
- timeout, limits e paginação ativos
- fallback para bloqueio quando segurança não puder ser provada
- contingência no fluxo antigo se necessário

### Fase 3 — mutações com confirmação

Permitir `INSERT`, `UPDATE` e `DELETE` apenas com confirmação explícita, mantendo todos os bloqueios permanentes já definidos.

## Critérios de sucesso

- nenhuma consulta pode escapar do escopo de `empresa_id`
- nenhuma mutação pode executar sem confirmação explícita
- nenhum comando proibido pode executar
- perguntas abertas de leitura devem produzir respostas úteis
- toda execução deve ter trilha de auditoria completa

## Riscos principais

### 1. Falso positivo de segurança

O maior risco é uma consulta parecer válida mas sair do escopo da empresa.

Mitigação: a prova de escopo deve existir no backend e nunca depender do LLM.

### 2. Cobertura insuficiente do plano estruturado

Perguntas abertas podem cair cedo demais em fallback SQL.

Mitigação: evolução incremental da camada estruturada e observabilidade por tipo de falha.

### 3. Regressão de experiência

Bloqueios excessivos podem fazer o copiloto parecer menos útil no início.

Mitigação: rollout em modo sombra, mensagens claras de bloqueio e refinamento orientado.

## Decisões finais aprovadas

- autonomia real sem catálogo de tools exposto ao modelo
- runtime próprio do copiloto
- pipeline: interpretação → plano estruturado → fallback SQL controlado → validação → execução → resposta
- `SELECT` permitido quando validado
- `INSERT`, `UPDATE` e `DELETE` apenas com confirmação explícita
- `ALTER`, `DROP`, CTEs mutáveis e múltiplas statements sempre bloqueados
- qualquer acesso restrito ao `empresa_id` do usuário
- auditoria e rollout gradual obrigatórios

## Fora de escopo imediato para implementação inicial

- escrita automática
- suporte irrestrito a qualquer tabela sem modelagem mínima de allowlist
- remoção imediata do fluxo antigo antes do modo sombra
- otimizações avançadas de custo de consulta antes da validação básica de segurança
