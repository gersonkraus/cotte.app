# Observabilidade do Assistente IA: Roteamento e Telemetria

Este documento descreve as melhorias implementadas na Sprint atual para garantir a **estabilidade do roteamento de intenções** e preparar o terreno para a **telemetria de ferramentas**.

## 1. Testes de Regressão de Roteamento (Routing Regression)

O assistente COTTE possui múltiplas ferramentas (`tools`) com escopos que podem se sobrepor (ex: relatórios de faturamento vs. ferramentas específicas de contas a receber). Para evitar que o LLM escolha a ferramenta errada de forma imprevisível, implementamos testes de regressão automatizados para o `IntentionClassifier`.

### Como funciona
O arquivo `sistema/tests/test_ai_tool_routing.py` contém um conjunto de comandos padrão que os usuários enviam e mapeia cada um para a sua **intenção exata esperada**. 

Qualquer mudança no arquivo `ai_intention_classifier.py` deve passar por estes testes, garantindo que:
*   Comandos genéricos como `"faturamento"` chamem a ferramenta correta.
*   Conflitos entre `"listar orçamentos"` e `"relatório de orçamentos"` sejam mediados com precisão semântica.
*   Priorização entre domínios (como `INADIMPLENCIA` vs `CONTAS_RECEBER`) seja mantida.

### Como executar
```bash
cd sistema
pytest tests/test_ai_tool_routing.py
```
Se você adicionar uma nova intenção ou alterar um Regex, sempre execute os testes para garantir que não introduziu "falsos positivos" que afetem as demais rotas.

## 2. Telemetria de Ferramentas (Tool Call Logging)

Para evoluir o sistema baseando-nos em dados (e não apenas intuição), preparamos a estrutura para logging de todas as execuções de ferramentas do assistente.

### O Modelo de Dados (`ToolCallLog`)
A tabela proposta armazena o histórico do que os usuários tentam executar:
- `sessao_id`: Permite rastrear o fluxo dentro de uma mesma conversa.
- `tool`: Qual ferramenta foi efetivamente chamada.
- `args_json` e `user_input`: Quais parâmetros o LLM extraiu vs. o que o usuário realmente pediu.
- `status`: "ok", "error" ou falha de fallback.

### Como utilizar a Telemetria
Os dados coletados pelo `tool_executor.py` poderão ser utilizados em dashboards de Metabase ou SQL local para responder:
1.  **Quais ferramentas são usadas com mais frequência?** (Candidatas a otimização de performance).
2.  **Quais ferramentas quase nunca são chamadas?** (Candidatas a descontinuação e consolidação, como `gerar_relatorio_vendas` vs `gerar_relatorio_dinamico`).
3.  **Taxa de erro por ferramenta**: Se uma ferramenta tem alto indíce de `invalid_input`, seu _prompt_ ou os tipos do Pydantic precisam ser ajustados.

---
> **Próximos Passos (Ação para o Desenvolvedor)**: Aplicar a migration Alembic cuidadosamente no banco de staging para que o log `ToolCallLog` já modelado passe a registrar todas as requisições em background.
