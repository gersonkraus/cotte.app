---
title: Plano Melhorias Proposta
tags:
  - roadmap
prioridade: media
status: documentado
---
---
title: Plano Melhorias Proposta
tags:
  - roadmap
prioridade: media
status: documentado
---
# Plano de Melhorias: Propostas Públicas Interativas

Este documento detalha o roteiro de implementação para as melhorias identificadas em 05/04/2026 para o módulo de **Propostas Públicas** do COTTE.

## 🎯 Objetivos
1. Aumentar a taxa de conversão das propostas enviadas.
2. Facilitar a vida do vendedor com geração de conteúdo via IA.
3. Fornecer dados de engajamento em tempo real (Analytics).

---

## 📅 Roteiro de Implementação (Amanhã)

### Fase 1: Novos Blocos de Conteúdo (Builder)
- [ ] **Bloco de Vídeo**: Adicionar campo `video_url` (suporte YouTube/Vimeo/Loom) no builder e renderizar `<iframe>` na proposta pública.
- [ ] **Bloco de FAQ**: Criar novo tipo de bloco com lista de `pergunta` e `resposta` (formato accordion).
- [ ] **Bloco de Prova Social**: Permitir upload/link de imagens de logotipos ou prints de depoimentos.

### Fase 2: Inteligência Artificial (Claude)
- [ ] **Botão "Gerar com IA"**: No editor de cada bloco, adicionar botão que dispara chamada para o `ia_service.py`.
- [ ] **Contexto do Lead**: Garantir que o prompt da IA receba o `nome_empresa`, `segmento` e `dores` do lead para gerar copy personalizado.
- [ ] **Refinamento de Pitch**: IA deve sugerir 3 opções de títulos impactantes para o bloco Hero.

### Fase 3: Analytics e Engajamento
- [ ] **Rastreio de Visualização**: Endpoint para registrar `visualizacao_id`, `data_hora` e `dispositivo`.
- [ ] **Tempo por Bloco**: Script JS na proposta pública que envia via `navigator.sendBeacon` o tempo de permanência em cada `ID` de bloco.
- [ ] **Notificação Real-time**: Disparar `whatsapp_service` para o vendedor quando a proposta for aberta pela primeira vez.

### Fase 4: Formalização e Fechamento
- [ ] **Assinatura Digital**: Componente Canvas simples no bloco de CTA para assinatura manual.
- [ ] **Geração de Comprovante**: Salvar a assinatura vinculada ao aceite da proposta no banco de dados.
- [ ] **Link de Pagamento (Pix)**: Campo no CTA para inserir chave Pix ou link de checkout externo.

---

## 🛠 Alterações Técnicas Necessárias

### Backend (`app/`)
- `models/comercial.py`: Adicionar campos de configuração nos blocos (JSONB).
- `services/ia_service.py`: Criar prompt template específico para "Copywriting de Propostas".
- `routers/comercial.py`: Novos endpoints de `/analytics/proposta`.

### Frontend (`cotte-frontend/`)
- `js/proposta-builder.js`: Lógica para os novos campos e botão de IA.
- `proposta-publica.html` (Verificar se existe ou se é renderizada dinamicamente): Atualizar CSS para os novos blocos.

---

## ✅ Definição de Pronto
- [ ] Proposta com vídeo renderiza corretamente.
- [ ] Vendedor recebe WhatsApp quando o link é clicado.
- [ ] IA gera texto condizente com o lead selecionado.
- [ ] Assinatura manual é salva e exibida no detalhe do lead.
