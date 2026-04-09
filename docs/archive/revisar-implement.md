---
title: Revisar Implement
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Revisar Implement
tags:
  - tecnico
prioridade: media
status: documentado
---
# Revisão de Implementações Recentes

## 🔐 Fluxo OTP de Aceite (Feature Principal)

### Backend
| Onde | O quê |
|---|---|
| `app/services/otp_service.py` | **NOVO** - Classe `OTPService` com `gerar_codigo()` e `validar_codigo()` (Redis ou fallback memória) |
| `app/services/email_service.py` | **Nova função** `enviar_otp_aceite()` - envia código por e-mail |
| `app/routers/publico.py` | **Novo endpoint** `POST /{link_publico}/aceitar/solicitar-otp` |
| `app/routers/publico.py` | `aceitar_orcamento()` agora valida OTP antes de aceitar |
| `app/routers/publico.py` | **Nova função** `_exige_otp()` - regra flexível (campo no orçamento OU config da empresa + valor mínimo) |

### Modelos/Schemas (4 campos novos)
- **Empresa:** `exigir_otp_aceite`, `otp_valor_minimo`
- **Orcamento:** `aceite_confirmado_otp`, `exigir_otp`

### Frontend
- `orcamento-publico.html` - Modal de aceite em **2 passos** (selecionar canal → inserir código)
- `orcamentos.html` / `index.html` - Checkbox "Exigir OTP" no formulário
- `js/configuracoes.js` - Campo `otp_valor_minimo` nas configurações

---

## ✅ Validações Novas (Schemas)
- **`validar_prefixo`** - prefixo de numeração: `^[A-Z0-9]{1,8}$`, auto-uppercase
- **`validar_desconto`** - range `0-100`

---

## 🔧 Refactors
- `configuracoes.html` → JS extraído para `js/configuracoes.js`
- `catalogo.html` - Removido botão "Modelos", adicionado select de categoria destino

---

## 📄 PDF
- `pdf_service.gerar_pdf_orcamento()` agora renderiza bloco de **Aceite Digital** com badge "VERIFICADO VIA OTP"

---

## 🧪 Testes existentes
- `tests/test_empresa_schema.py` - 20 testes para validators de prefixo e desconto

---

## Prioridades de Teste

1. **Fluxo OTP completo**: solicitar código → receber → validar → aceitar orçamento
2. **Regra `_exige_otp()`**: quando OTP é exigido vs quando não é (campo orçamento, config empresa, valor mínimo)
3. **Rate limiting** do endpoint de solicitação de OTP
4. **Fallback Redis → memória** quando Redis não está disponível
5. **PDF com aceite**: verificar badge OTP aparece no PDF quando `aceite_confirmado_otp=True`
6. **Validators de schema**: prefixo e desconto (já tem 20 testes unitários)
