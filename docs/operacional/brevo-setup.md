---
title: Brevo Setup
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Brevo Setup
tags:
  - documentacao
prioridade: alta
status: documentado
---
# 📧 Setup Brevo para Envio de Emails

O Brevo (ou SMTP configurado) é usado no COTTE para:
- **Envio do orçamento ao cliente** (e-mail com link da proposta e opcionalmente PDF em anexo)
- **Recuperação de senha**
- **E-mail de boas-vindas** (se implementado)

Não é usado para notificações internas de "orçamento aprovado" ou "orçamento expirado" — essas foram descontinuadas por e-mail; a notificação de aprovação é enviada por WhatsApp ao responsável.

---

## 🚀 Passo 1: Criar Conta Brevo

1. Acesse [https://brevo.com](https://brevo.com)
2. Clique em **Sign Up** (ou crie conta com Google/GitHub)
3. Confirme seu email

## 🔑 Passo 2: Gerar Credenciais SMTP

1. Após logar, vá em **Settings** → **SMTP & API**
2. Clique em **SMTP** na aba esquerda
3. Clique em **Create SMTP User** (ou use credencial padrão se já existir)
4. Você verá:
   - **SMTP Host**: `smtp-relay.brevo.com`
   - **SMTP Port**: `587`
   - **SMTP User**: seu email ou chave gerada
   - **SMTP Password**: senha ou chave gerada

## 🌐 Passo 3: Configurar Domínio (Importante!)

Para não cair em SPAM, configure **SPF** e **DKIM**:

1. Em **Settings** → **Domains** → clique no seu domínio
2. Siga as instruções para adicionar registros DNS:

   **SPF:**
   ```
   v=spf1 include:relay.brevo.com ~all
   ```

   **DKIM:** Brevo fornece valores específicos — copie exatamente

3. Aguarde ~15 min para DNS propagar

## 📝 Passo 4: Atualizar `.env`

Abra o arquivo `.env` e atualize:

```bash
# ── E-mail (SMTP) ─────────────────────────────────────────
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USER=seu-email@seudominio.com
SMTP_PASS=sua-chave-smtp-brevo-aqui
SMTP_FROM=Sua Empresa <noreply@seudominio.com>
```

**Onde encontrar:**
- `SMTP_USER`: seu email cadastrado no Brevo OU login SMTP gerado
- `SMTP_PASS`: senha SMTP gerada em **Settings → SMTP & API**
- `SMTP_FROM`: use seu domínio próprio (não gmail.com)

## ✅ Passo 5: Testar

1. Crie um orçamento no dashboard
2. Clique em **Enviar por Email** (ícone 📧)
3. Verifique se a resposta é: **"E-mail será enviado em breve"**
4. Aguarde ~10 segundos
5. Confira o email na caixa de entrada do cliente

## 📊 Monitorar Envios

No dashboard, você pode ver:
- **Status**: Se foi enviado/erro
- **Tentativas**: Quantas tentativas foram feitas
- **Data**: Quando foi enviado

## 💡 Dicas

- **Limite Gratuito**: 300 emails/dia (9.000/mês)
- **Teste primeiro**: Envie para seu próprio email
- **Domínio próprio**: Essencial para não cair em SPAM
- **SPF + DKIM**: Aumenta deliverability em 99%+

## 🚨 Problemas Comuns

### E-mail cai em SPAM
- Falta SPF/DKIM (veja Passo 3)
- Usando email genérico (Gmail, Hotmail) — use domínio próprio

### Erro: "SMTP não configurado"
- Verifique `.env`: `SMTP_HOST` e `SMTP_USER` não podem estar vazios
- Reinicie a aplicação após atualizar `.env`

### Erro: "Falha ao conectar SMTP"
- Verifique `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`
- Certifique-se que Brevo gerou as credenciais corretas

## 📞 Próximos Passos (Opcional)

- **Automação**: Configure lembretes automáticos em **Empresa → Configurações**
- **Webhooks**: Brevo pode enviar callbacks quando email é aberto/clicado
- **Templates**: Crie templates customizados no Brevo (você pode usá-los depois)

---

**Dúvidas?** Acesse a documentação: [brevo.com/docs](https://brevo.com/docs)
