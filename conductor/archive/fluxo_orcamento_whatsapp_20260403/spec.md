---
title: Spec
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Spec
tags:
  - tecnico
prioridade: media
status: documentado
---
# Especificação da Track: Fluxo Ponta-a-Ponta de Geração de Orçamentos via WhatsApp com IA

## Descrição
Esta track tem como objetivo implementar, revisar e assegurar o funcionamento da jornada central do COTTE: a capacidade do vendedor interagir com a IA para rascunhar o orçamento, a geração do documento em formato PDF estilizado, e o disparo da comunicação com o cliente pelo WhatsApp.

## Objetivos
1. **Integração IA (Claude):** Validar a extração de intenções e a formatação adequada de dados do orçamento a partir da interação via WhatsApp.
2. **Geração de PDF (WeasyPrint):** Implementar e refinar o template do PDF gerado pelo sistema para garantir o estilo "Clássico Corporativo, Moderno e Minimalista".
3. **Disparo no WhatsApp:** Garantir que o endpoint de mensageria da Z-API/Evolution API funcione de forma síncrona/assíncrona sem falhas, disparando os Alertas Intrusivos caso necessário antes do envio.

## Escopo e Limites
- O foco desta sprint é exclusivamente no backend (FastAPI), integrações e feedback síncrono.
- Não abordaremos outras automações fora da geração de orçamento e disparo.