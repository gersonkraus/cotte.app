---
title: Pull Request Template
tags:
  - documentacao
prioridade: media
status: documentado
---
## Descrição

<!-- O que mudou e por quê (1–3 frases). -->

## Tipo de mudança

Marque **todos** que se aplicam e siga o checklist correspondente em [CONTRIBUTING.md](../CONTRIBUTING.md).

- [ ] **Correção de bug** — ver [Regras para debug](../CONTRIBUTING.md#regras-para-debug) e validação mínima no PR
- [ ] **Nova funcionalidade / melhoria** — ver [Antes de contribuir](../CONTRIBUTING.md#antes-de-contribuir) e [Regras para backend](../CONTRIBUTING.md#regras-para-backend) / [frontend](../CONTRIBUTING.md#regras-para-frontend)
- [ ] **Documentação apenas** — sem alteração de comportamento em runtime
- [ ] **Testes** — novos testes ou ajuste de cobertura (indicar `pytest` / Playwright / `npm run test:unit`)
- [ ] **Refatoração / cleanup** — ver [Regras para cleanup, refactor e simplificação](../CONTRIBUTING.md#regras-para-cleanup-refactor-e-simplificação)
- [ ] **Configuração / tooling** — ver [Regras para configuração](../CONTRIBUTING.md#regras-para-configuração)

## Checklist geral (CONTRIBUTING)

- [ ] Li [CONTRIBUTING.md](../CONTRIBUTING.md) e a mudança é a **menor correção segura** possível
- [ ] Mapeei impacto em backend/frontend/contrato de API (quando aplicável)
- [ ] Validei como indicado na descrição (testes manuais ou automatizados)
- [ ] Não incluo segredos, `.env`, chaves ou dados sensíveis
- [ ] Se alterei `docs/contribuicao.yaml`, rodei `npm run generate:contribuicao` e incluí `docs/contribuicao.md` atualizado
- [ ] Se alterei `AGENTS.md` ou `CONTRIBUTING.md` com títulos `##` de secções `critical` no YAML, confirmei com `npm run validate:contributing`

## Como validar

<!-- Passos concretos para o revisor (comandos, tela, endpoint). -->

## Riscos / notas

<!-- Opcional: regressões possíveis, follow-ups. -->
