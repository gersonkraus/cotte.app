---
title: 2026 04 15 105149 Estou Logado No Painel Superadmin E Copiloto Tec
tags:
  - documentacao
prioridade: media
status: documentado
---
# Plano: Correção de Conflito de Autonomia Semântica no Copiloto Técnico

## Objetivo
Corrigir o erro de bloqueio de política ("fluxo semântico foi degradado por política no momento") no `copiloto-tecnico.html` ao fazer perguntas técnicas que contêm palavras-chave de negócio (ex: "orçamento", "agendamentos").

## Contexto Atual / Suposições
Quando o administrador logado como superadmin pergunta ao Copiloto Técnico algo como *"analise o motivo do modal de edição de orçamento não esta salvando os agendamentos"*, o sistema de Autonomia Semântica (Semantic Autonomy) intercepta a mensagem.
- O `intent_router` classifica erroneamente a pergunta como uma intenção de negócios (capability transacional/documental), devido às palavras "orçamento" e "agendamento".
- O `policy_engine` percebe que a intenção exige o `ENGINE_OPERATIONAL`, mas o contexto atual é o `ENGINE_INTERNAL_COPILOT`.
- Como mecanismo de defesa, a política bloqueia a execução, devolvendo a mensagem de erro que você presenciou, e impede o LLM de usar as ferramentas técnicas (`ler_arquivo_repositorio`, etc.) para inspecionar o código do modal de fato.

## Abordagem Proposta
O fluxo de Autonomia Semântica (`semantic_autonomy`) foi desenhado para as personas operacionais e analíticas de negócios. O Copiloto Técnico Interno deve atuar como um agente técnico direto, utilizando o fluxo legado/padrão que dá liberdade ao LLM para usar as ferramentas de engenharia de software sem as amarras das políticas de negócios.

A solução é fazer um "bypass" formal da Autonomia Semântica toda vez que a requisição for direcionada ao Copiloto Técnico.

## Plano Passo a Passo

### 1. Atualização do Orquestrador (`cotte_ai_hub.py`)
- Localizar a função `assistente_unificado_v2`, que é o ponto de entrada principal do assistente.
- Modificar a condição que delega o fluxo para a Autonomia Semântica:
  **De:**
  ```python
  if semantic_autonomy_enabled():
  ```
  **Para:**
  ```python
  if semantic_autonomy_enabled() and resolve_engine(engine) != ENGINE_INTERNAL_COPILOT:
  ```
- Isso garante que qualquer chamada originada do painel do `copiloto-tecnico.html` pule imediatamente a camada de intent/policy de negócios e vá direto para a montagem de contexto técnico (Code RAG) e tool loop livre.

## Arquivos que sofrerão alteração
- `sistema/app/services/cotte_ai_hub.py`

## Testes / Validação
1. **Teste Funcional (Manual):**
   - No painel superadmin, acessar `copiloto-tecnico.html`.
   - Enviar a mensagem exata: *"analise o motivo do modal de edição de orcamento não esta salvando os agendamentos"*.
   - **Resultado Esperado:** O erro sobre o "fluxo semântico" desaparecerá. A IA reconhecerá o pedido técnico e usará a ferramenta `buscar_codigo_repositorio` ou `ler_arquivo_repositorio` para procurar os arquivos frontend relacionados a "orçamento" e "agendamento", respondendo com uma análise técnica do código.

## Riscos, Tradeoffs e Questões em Aberto
- **Tradeoff:** O Copiloto Técnico não conseguirá consultar os "insights estruturados" gerados pela Autonomia Semântica (ex: gráficos de caixa, tickets processados semanticamente).
- **Justificativa:** Esse tradeoff é aceitável e desejado, já que a finalidade desta ferramenta específica é puramente engenharia de software, inspeção do repositório, debug e manutenção (que operam num nível de abstração diferente das transações de negócios dos clientes).
