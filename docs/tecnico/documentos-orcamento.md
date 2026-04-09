---
title: Documentos Orcamento
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Mapa Tecnico Documentos Orcamento Publico
tags:
  - tecnico
  - mapa
  - tecnico
prioridade: media
status: documentado
---
# Mapa Técnico: Documentos + Orçamento Público

> Gerado em: 2026-03-23
> Contexto: rastreamento ponta a ponta da funcionalidade de documentos vinculados a orçamentos e do portal público do cliente.

---

## 1. Entrada do fluxo

**Dois fluxos independentes que se cruzam no portal público:**

**Fluxo A — Biblioteca de Documentos da Empresa**
- Entrada: operador acessa `documentos.html` (CRUD de templates PDF/HTML da empresa)

**Fluxo B — Orçamento Público (link do cliente)**
- Entrada: cliente abre `https://app.cotte.com.br/o/{link_publico}`
  - Renderização: `orcamento-publico.html` (SPA estática)
  - API: `GET /o/{link_publico}` → `publico.py`

---

## 2. Caminho completo dos arquivos

```
Biblioteca de Documentos (Fluxo A):
  cotte-frontend/documentos.html
  cotte-frontend/js/documentos.js
      └─→ routers/documentos.py
              └─→ services/documentos_service.py
                      └─→ services/r2_service.py  (upload Cloudflare R2)
              └─→ models/models.py :: DocumentoEmpresa

Vínculo Documento ↔ Orçamento:
  cotte-frontend/orcamento-view.html
  cotte-frontend/js/orcamento-detalhes.js  (_carregarDocumentosDetalhes)
      └─→ routers/orcamentos.py  (rotas /{orcamento_id}/documentos/*)
              └─→ models/models.py :: OrcamentoDocumento

Portal Público (Fluxo B):
  cotte-frontend/orcamento-publico.html  (JS inline)
      └─→ routers/publico.py
              ├─→ GET  /{link}                              → ver_orcamento_publico
              ├─→ GET  /{link}/pdf                          → download_pdf_orcamento
              ├─→ GET  /{link}/documentos/{id}              → baixar_documento_publico
              ├─→ POST /{link}/documentos/{id}/ler          → marcar_documento_lido
              ├─→ POST /{link}/aceitar                      → aceitar_orcamento
              ├─→ POST /{link}/recusar                      → recusar_orcamento
              └─→ POST /{link}/ajuste                       → solicitar_ajuste
              └─→ services/documentos_service.py :: resolver_arquivo_path, montar_nome_download
              └─→ services/r2_service.py (redirect R2)
              └─→ services/pdf_service.py :: gerar_pdf_orcamento
```

---

## 3. Sequência de chamadas

### Fluxo A — Upload de documento na biblioteca

```
1. Frontend → POST /documentos/  (multipart/form-data)
   routers/documentos.py :: criar_documento()
     ├─ validação tipo_conteudo (PDF ou HTML)
     ├─ PDF → documentos_service.salvar_upload_documento()
     │           ├─ valida ext (.pdf), mime, tamanho (máx 15 MB)
     │           └─ r2_service.upload_file() → retorna URL https://...
     ├─ HTML → sem arquivo físico, salva conteudo_html no DB
     ├─ gerar_slug_documento(nome) → slug único por empresa
     └─ INSERT DocumentoEmpresa → tabela documentos_empresa
```

### Sub-fluxo — Vincular documento a orçamento

```
2. Frontend → POST /orcamentos/{id}/documentos
   routers/orcamentos.py :: vincular_documento_ao_orcamento()
     ├─ busca Orcamento (empresa_id = usuario.empresa_id)
     ├─ busca DocumentoEmpresa (valida pertencimento)
     ├─ verifica unicidade (UNIQUE orcamento_id + documento_id)
     ├─ calcula max(ordem) + 1
     └─ INSERT OrcamentoDocumento
         ├─ copia snapshot: documento_nome, tipo, versao, arquivo_path
         ├─ flags: exibir_no_portal, enviar_por_email, enviar_por_whatsapp, obrigatorio
         └─ arquivo_path = NULL se HTML (coluna nullable após q001)
```

### Fluxo B — Cliente abre o link público

```
3. Browser → GET /o/{link_publico}
   publico.py :: ver_orcamento_publico()
     ├─ _get_orcamento_publico(link, db)
     │   └─ Query Orcamento + joinedload(itens, servico, empresa, documentos)
     ├─ registra visualizacoes++, visualizado_em (primeira vez)
     ├─ INSERT Notificacao tipo="visualizado"
     ├─ notificar_operador_visualizacao (WhatsApp, se toggle ativo)
     ├─ fallback: auto-aplica PIX da empresa
     ├─ monta OrcamentoPublicoOut
     │   └─ out.documentos = [d for d in orc.documentos if d.exibir_no_portal]
     └─ retorna JSON incluindo documentos (apenas exibir_no_portal=True)

4. Browser → GET /o/{link_publico}/documentos/{orcamento_documento_id}
   publico.py :: baixar_documento_publico()
     ├─ valida orc.link_publico == link (segurança)
     ├─ valida vinc.exibir_no_portal (acesso público permitido)
     ├─ verifica vinc.permite_download (se ?download=1)
     ├─ Se arquivo_path vazio/nulo e documento_id presente:
     │   └─ busca DocumentoEmpresa, se HTML → retorna HTMLResponse(conteudo_html)
     ├─ resolver_arquivo_path(vinc.arquivo_path)
     │   ├─ URL R2 → RedirectResponse 302
     │   └─ path local legado → FileResponse
     └─ headers Content-Disposition: inline ou attachment
```

### Cliente marca "Li e aceito" em documento obrigatório

```
5. Browser → POST /o/{link_publico}/documentos/{id}/ler
   publico.py :: marcar_documento_lido()
     ├─ valida link e pertencimento ao orçamento
     ├─ valida exibir_no_portal == True
     ├─ SET visualizado_em = now() (se ainda nulo)
     ├─ SET aceito_em = now()
     └─ retorna {"ok": True}
```

### Cliente aceita o orçamento

```
6. Browser → POST /o/{link_publico}/aceitar  {nome, mensagem?}
   publico.py :: aceitar_orcamento()
     ├─ _check_rate_limit (IP:action:link)
     ├─ _get_orcamento_publico(for_update=True) → WITH FOR UPDATE (lock PostgreSQL)
     ├─ _status_bloqueia_acao() → idempotência
     ├─ SET status=APROVADO, aceite_nome, aceite_mensagem, aceite_em
     ├─ renomear_numero_aprovado(orc, empresa) (utils/orcamento_utils.py)
     ├─ auto-aplicar PIX da empresa (pix_chave, pix_payload, pix_qrcode)
     ├─ fin_svc.criar_contas_receber_aprovacao() (savepoint — não quebra aceite)
     ├─ INSERT Notificacao tipo="aprovado"
     ├─ INSERT HistoricoEdicao (com IP do cliente)
     ├─ handle_quote_status_changed() (quote_notification_service.py)
     ├─ enviar_mensagem_texto() → WhatsApp cliente
     └─ background_task: enviar_email_confirmacao_aceite() (Brevo)
```

---

## 4. Estruturas de dados envolvidas

### `DocumentoEmpresa` (tabela `documentos_empresa`) — template da empresa
```
id, empresa_id, nome, slug (UNIQUE/empresa), tipo, descricao
tipo_conteudo: pdf | html
arquivo_path (URL R2 ou path legado, nullable), arquivo_nome_original, mime_type, tamanho_bytes
conteudo_html, variaveis_suportadas (JSON)
versao, status (ativo|inativo|arquivado), permite_download, visivel_no_portal
deletado_em (soft delete)
```

### `OrcamentoDocumento` (tabela `orcamento_documentos`) — vínculo + snapshot
```
id, orcamento_id (CASCADE), documento_id (SET NULL)
ordem, exibir_no_portal, enviar_por_email, enviar_por_whatsapp, obrigatorio
--- snapshot (copiado no momento da vinculação) ---
documento_nome, documento_tipo, documento_versao
arquivo_path (nullable após q001), arquivo_nome_original, mime_type, tamanho_bytes, permite_download
--- rastreamento ---
visualizado_em   → preenchido na primeira abertura via /ler
aceito_em        → preenchido ao marcar "Li e aceito" via /ler
```

### Schemas expostos ao cliente (portal público)
- `OrcamentoDocumentoPublicoOut` — expõe: `id, documento_nome, documento_tipo, documento_versao, permite_download`
- `OrcamentoPublicoOut.documentos` → lista filtrada por `exibir_no_portal=True`

---

## 5. Regras de negócio e UX

| # | Regra | Onde |
|---|-------|------|
| R1 | Upload só aceita PDF (mime + extensão); máx 15 MB | `documentos_service.py:45–57` |
| R2 | Slug único por empresa (auto-gerado ou manual) | `documentos.py:115–128` |
| R3 | Snapshot copiado na vinculação — edições posteriores no template não afetam orçamentos já vinculados | `orcamentos.py:1247–1255` |
| R4 | Documento só aparece no portal se `exibir_no_portal=True` **no vínculo** (não no template) | `publico.py:189` |
| R5 | Download exige `permite_download=True` no vínculo; 403 caso contrário | `publico.py:239–240` |
| R6 | Documento obrigatório bloqueia o botão "Aceitar" no frontend até cliente marcar "Li e aceito" | `orcamento-publico.html:601–605` |
| R7 | Aceite com `FOR UPDATE` — previne double-accept concorrente no PostgreSQL | `publico.py:319` |
| R8 | Rate limit por IP para aceitar/recusar/ajuste | `publico.py:102–112` |
| R9 | `ondelete="SET NULL"` em `documento_id` — vínculo sobrevive se template for deletado | `models.py:552` |
| R10 | IP do cliente registrado no `HistoricoEdicao` ao aceitar | `publico.py:379–386` |
| UX1 | **Touch Targets:** Mínimo de 44x44px para botões e inputs interativos (Acessibilidade Mobile) | `css/style.css` |
| UX2 | **Sticky Footer:** Resumo de valores fixo no rodapé em visualização mobile | `orcamentos.html` |
| UX3 | **Atalhos de Teclado:** Ctrl+N (Novo), Ctrl+K (Busca), Esc (Fechar modais) | `orcamentos.html` |
| UX4 | **Performance:** Debounce de 300ms em campos de busca | `orcamentos.html` |
| UX5 | **Sincronização Manual:** Botão 🔄 nos detalhes do orçamento para atualizar snapshot | `orcamento-detalhes.js` |
| UX6 | **Acesso IA Mobile:** Botão flutuante 🤖 para abrir/fechar assistente no dashboard | `index.html` |

---

## 6. Qualidade e Testes

### Testes E2E (Playwright)
A funcionalidade de orçamentos e documentos é validada pela suíte em `tests/e2e/orcamentos.spec.js`, cobrindo:
- Visibilidade de elementos críticos (botão Novo Orçamento).
- Funcionamento dos atalhos de teclado.
- Comportamento do Sticky Footer em resoluções mobile.
- Persistência de estado de modais com a tecla `Esc`.

---

## 7. Problemas de arquitetura identificados

### ✅ P1 — `arquivo_path` nullable (CORRIGIDO em q001)
- `OrcamentoDocumento.arquivo_path` era `NOT NULL`, mas documentos HTML não têm arquivo físico.
- **Correção:** migration `q001_fix_arquivo_path_nullable` + `nullable=True` no model + remoção do `or ""` no router.

### ✅ P2 — Snapshot não reflete atualizações do template (CORRIGIDO)
- Implementado endpoint `POST /orcamentos/{id}/documentos/{vinc_id}/sincronizar`.
- Permite atualização manual do snapshot se o template for corrigido.

### ✅ P3 — Acoplamento assimétrico no acesso ao conteúdo HTML (CORRIGIDO)
- Conteúdo HTML agora é copiado para `OrcamentoDocumento.conteudo_html` no momento do vínculo.
- Portal público prioriza o snapshot do vínculo, garantindo integridade histórica.

### ✅ P5 — Aceite sem log de IP (CORRIGIDO)
- IP do cliente adicionado ao `HistoricoEdicao` no aceite público.

### ✅ P6 — `visualizado_em` e `aceito_em` sem endpoint (CORRIGIDO)
- Novo endpoint `POST /o/{link}/documentos/{id}/ler` persiste os campos.
- Frontend chama o endpoint ao marcar "Li e aceito".

---

## 7. Melhor ponto para alterar com segurança

| Objetivo | Ponto seguro |
|----------|-------------|
| Mudar metadados de exibição no portal | `PATCH /orcamentos/{id}/documentos/{vinc_id}` → `OrcamentoDocumentoUpdate` |
| Substituir arquivo de um template | `PUT /documentos/{id}/arquivo` — vínculos existentes **não** são atualizados |
| Adicionar campo novo ao portal público | `OrcamentoDocumentoPublicoOut` em `schemas.py:239` + filtro em `publico.py:189` |
| Implementar re-sync de snapshot | Novo endpoint `POST /orcamentos/{id}/documentos/{vinc_id}/sincronizar` |
| Corrigir P3 (HTML snapshot) | Copiar `conteudo_html` no momento da vinculação para `OrcamentoDocumento` |

---

## Histórico de alterações neste módulo

| Data | Migration | Descrição |
|------|-----------|-----------|
| 2026-03-20 | `9d6276e279b2` | `documentos_empresa.arquivo_path` → nullable (HTML) |
| 2026-03-23 | `20260323_doc_tracking` | Adiciona `visualizado_em` e `aceito_em` em `orcamento_documentos` |
| 2026-03-23 | `z002_add_obrigatorio_orcamento_documentos` | Campo `obrigatorio` no vínculo |
| 2026-03-23 | `q001_fix_arquivo_path_nullable` | `orcamento_documentos.arquivo_path` → nullable + endpoint `/ler` + IP no aceite |
| 2026-03-23 | `feat(ux)` | Implementação de Touch Targets, Sticky Footer, Atalhos e Testes E2E |
