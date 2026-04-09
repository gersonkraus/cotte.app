---
title: Fluxo Do Sistema
tags:
  - tecnico
prioridade: alta
status: documentado
---
---
title: Fluxo do Sistema — COTTE
tags:
  - fluxo
  - arquitetura
  - tecnico
prioridade: alta
status: documentado
---

# Fluxo do Sistema — COTTE

## Fluxo principal

1. Usuário cria um orçamento (manual no dashboard ou por mensagem no WhatsApp).
2. O orçamento contém itens, valores, observações e validade.
3. O sistema gera:
   - PDF automático
   - link público da proposta
4. O usuário envia o orçamento ao cliente:
   - por e-mail (Brevo)
   - por WhatsApp (Evolution API ou Z-API)
   - compartilhando o link
5. O cliente visualiza a proposta (link público ou PDF).
6. O cliente pode:
   - aprovar (digitalmente pelo link ou respondendo no WhatsApp)
   - recusar
   - baixar o PDF
7. O sistema atualiza o status da proposta e dispara notificações conforme configurado.

## Notificações internas (para o atendente/empresa)

- **Orçamento aprovado:** o sistema envia uma mensagem por WhatsApp ao responsável pelo orçamento (criador do orçamento ou gestor da empresa). O envio é idempotente: não repete para a mesma aprovação. E-mail interno de aprovado não é mais utilizado.
- **Orçamento expirado:** o status é atualizado para expirado automaticamente (ao listar orçamentos ou por job). Nenhuma notificação interna (e-mail ou WhatsApp) é enviada para o evento de expiração.

## E-mails ao cliente

- Envio do orçamento ao cliente por e-mail (com link da proposta e opcionalmente PDF em anexo) continua sendo feito pelo Brevo/SMTP configurado na empresa.
- Recuperação de senha e outros e-mails transacionais também utilizam o mesmo serviço de e-mail.
