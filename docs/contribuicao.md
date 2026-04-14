---
title: Contribuicao
tags:
  - tecnico
prioridade: media
status: documentado
---
<!-- Gerado por scripts/generate-contribuicao-doc.mjs — não editar manualmente -->
<!-- Fonte: docs/contribuicao.yaml -->

# Contribuição — índice

Este ficheiro é **gerado automaticamente** a partir de `docs/contribuicao.yaml`.
Para alterar textos ou ordem das entradas, edite o YAML e execute `npm run generate:contribuicao`.

Os guias completos permanecem em [`AGENTS.md`](../AGENTS.md) (agentes/automação) e
[`CONTRIBUTING.md`](../CONTRIBUTING.md) (contribuição humana e detalhes).

## Objetivo

**Resumo:** Propósito do repositório e prioridades (manter o sistema estável, mudanças pequenas e validáveis).

- [AGENTS.md — Objetivo do projeto](../AGENTS.md#objetivo-do-projeto)
- [CONTRIBUTING.md — Objetivo](../CONTRIBUTING.md#objetivo)

## Complemento de orientação

**Resumo:** Referência ao CONTRIBUTING e ao índice gerado; alinhamento entre guias.

- [AGENTS.md — Complemento de orientação](../AGENTS.md#complemento-de-orientação)

## Idioma

**Resumo:** Português do Brasil nas comunicações e documentação.

- [AGENTS.md — Idioma](../AGENTS.md#idioma)
- [CONTRIBUTING.md — Idioma e comunicação](../CONTRIBUTING.md#idioma-e-comunicação)

## Ordem de precedência

**Resumo:** Hierarquia em caso de conflito: segurança, regras do projeto, evidência, menor alteração, preferências.

- [AGENTS.md — Ordem de precedência](../AGENTS.md#ordem-de-precedência)
- [CONTRIBUTING.md — Ordem de precedência](../CONTRIBUTING.md#ordem-de-precedência)

## Postura de execução

**Resumo:** Executar até concluir quando seguro; pedir confirmação só com risco ou ambiguidade real.

- [AGENTS.md — Postura de execução](../AGENTS.md#postura-de-execução)

## Flags e telemetria (assistente IA)

**Resumo:** localStorage `cotte_assistente_metrics` = `1` ativa métricas de performance no assistente (ambiente local).

- [CONTRIBUTING.md — Flags e telemetria (assistente IA)](../CONTRIBUTING.md#flags-e-telemetria-assistente-ia)

## Regras para backend

**Resumo:** Preservar contratos de API, FastAPI, validações e impacto no frontend antes de mudar payloads.

- [AGENTS.md — Regras para backend](../AGENTS.md#regras-para-backend)
- [CONTRIBUTING.md — Regras para backend](../CONTRIBUTING.md#regras-para-backend)

## Regras para frontend

**Resumo:** Evitar regressões de layout, CSS global e DOM; preservar estados de loading/erro.

- [AGENTS.md — Regras para frontend](../AGENTS.md#regras-para-frontend)
- [CONTRIBUTING.md — Regras para frontend](../CONTRIBUTING.md#regras-para-frontend)

## Regras para debug

**Resumo:** Reproduzir, achar causa raiz, corrigir com mudança mínima e validar com evidência.

- [AGENTS.md — Regras para debug](../AGENTS.md#regras-para-debug)
- [CONTRIBUTING.md — Regras para debug](../CONTRIBUTING.md#regras-para-debug)

## Regras para configuração

**Resumo:** Não expor segredos; não alterar env sem necessidade; distinguir problema de config vs código.

- [AGENTS.md — Regras para configuração](../AGENTS.md#regras-para-configuração)
- [CONTRIBUTING.md — Regras para configuração](../CONTRIBUTING.md#regras-para-configuração)

## Limpeza e simplificação

**Resumo:** Plano curto, validar antes; preferir remoção e simplificação a novas abstrações desnecessárias.

- [AGENTS.md — Regras para limpeza e simplificação](../AGENTS.md#regras-para-limpeza-e-simplificação)
- [CONTRIBUTING.md — Regras para cleanup, refactor e simplificação](../CONTRIBUTING.md#regras-para-cleanup-refactor-e-simplificação)

## Regras para testes e validação

**Resumo:** Rodar testes e validação manual quando fizer sentido; não declarar sucesso sem evidência.

- [AGENTS.md — Regras para testes e validação](../AGENTS.md#regras-para-testes-e-validação)
- [CONTRIBUTING.md — Regras para testes e validação](../CONTRIBUTING.md#regras-para-testes-e-validação)

## Regras para deploy e commits

**Resumo:** Deploy automático via post-commit; apenas `git commit` e `git push` no repositório principal quando solicitado.

- [AGENTS.md — Regras para deploy e commits](../AGENTS.md#regras-para-deploy-e-commits)
- [CONTRIBUTING.md — Deploy e push](../CONTRIBUTING.md#deploy-e-push)

## O que evitar

**Resumo:** Refatoração ampla sem pedido, mudanças estéticas desnecessárias, alterar contratos sem mapear consumidores.

- [AGENTS.md — O que evitar](../AGENTS.md#o-que-evitar)
- [CONTRIBUTING.md — O que evitar](../CONTRIBUTING.md#o-que-evitar)

## Princípio final

**Resumo:** Segurança, evidência e menor impacto; preferir verificação a suposição.

- [AGENTS.md — Princípio final](../AGENTS.md#princípio-final)
- [CONTRIBUTING.md — Princípio final](../CONTRIBUTING.md#princípio-final)
