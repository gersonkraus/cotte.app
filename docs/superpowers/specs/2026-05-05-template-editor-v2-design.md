# Template Editor V2 — Paste de Imagem + Preview ao Vivo

**Data:** 2026-05-05
**Status:** Design validado, aguardando implementação
**Escopo:** Modal de template (tenant-comercial), Etapa 2 (Composição)

---

## Objetivo

Permitir que o usuário cole imagens diretamente (Ctrl+V, drag & drop) no editor de templates e veja um preview ao vivo simulando WhatsApp/Email, com UI moderna e autoexplicativa.

---

## Escopo

### O que muda
1. Etapa 2 ganha layout em 2 colunas: Editor (60%) | Preview (40%)
2. Input de arquivo de anexo é substituído por zona visual de drop/paste de imagens
3. Painel de preview ao vivo simulando WhatsApp (bolha verde) ou Email
4. Contador de caracteres mostra estimativa de mensagens WhatsApp

### O que NÃO muda
- Wizard de 2 etapas (Tipo → Mensagem) permanece igual
- Etapa 1 (seleção de tipo) permanece igual
- Backend de upload de anexos (`POST /api/v1/tenant/comercial/templates/upload-anexo`)
- API de preview com lead real (`POST /api/v1/tenant/comercial/templates/{id}/preview`)
- Variáveis interativas (badges clicáveis)
- Campos: nome, canal pills, assunto, conteúdo textarea
- Resto do modal (header, footer, stepper, botões Cancelar/Salvar/Voltar)

---

## Arquivos afetados

| Arquivo | Tipo de mudança |
|---|---|
| `sistema/cotte-frontend/tenant-comercial.html` | Reestruturar HTML da Etapa 2 (linhas ~790-834) |
| `sistema/cotte-frontend/js/tenant-TemplatesManager.js` | Nova lógica: paste/drop, preview ao vivo, gerenciamento de múltiplas imagens |
| `sistema/cotte-frontend/css/tenant-comercial.css` | Novas classes: zona de imagens, preview panel, simulação WhatsApp/Email |

---

## Componentes do Design

### 1. Zona de Imagens (Drop/Paste Zone)

Substitui o `<input type="file" id="tpl-anexo">` atual por uma zona visual.

**Estados visuais:**
- **Vazia:** Área com borda tracejada, ícone 📁, texto "Solte imagens aqui ou Ctrl+V"
- **Com imagens:** Grid de thumbnails (120x120px) com nome do arquivo e botão ✕ para remover
- **Drag over:** Borda muda para cor accent, fundo levemente colorido
- **Último card:** Sempre um card "+" para adicionar mais (clique ou drop)

**Restrições:**
- Tipos aceitos: PNG, JPG, WEBP, PDF
- Tamanho máximo: 15 MB por arquivo
- WhatsApp (canal = whatsapp): **máximo 1 imagem**
- Email (canal = email, ambos): **múltiplas imagens** (limite prático: 10)

**Interações:**
- Ctrl+V em qualquer lugar do modal: se clipboard contiver imagem, adiciona à zona
- Drag & drop na zona: adiciona arquivos
- Clique no card "+": abre file picker nativo
- Clique no ✕: remove imagem (confirmação visual, sem dialog)
- Ao trocar canal para WhatsApp e houver >1 imagem: mantém só a primeira, avisa o usuário

**Dados:**
- Cada imagem vira um objeto: `{ file: File, previewUrl: string, nome: string, tamanho: number }`
- Upload acontece no momento de salvar (via `_uploadSelectedAnexo` existente, adaptado para múltiplos)

### 2. Preview ao Vivo

Painel direito que atualiza em tempo real (debounce 300ms via `input` + `change`).

**Dados de exemplo (fallback quando não há lead real):**
- `{nome}` → "João Silva"
- `{empresa}` → "Tech Ltda"
- `{cidade}` → "São Paulo"
- `{whatsapp}` → "(11) 99999-9999"
- `{email}` → "joao@tech.com.br"
- `{dias_sem_contato}` → "3"
- `{score}` → "Quente 🔴"
- `{etapa}` → "Proposta Enviada"
- `{valor}` → "R$ 5.000,00"

**Modo WhatsApp (canal = whatsapp ou ambos):**
```
┌─ Preview ──────────────────┐
│  📱 WhatsApp               │
│                            │
│  ┌──────────────────────┐  │
│  │ [texto renderizado]  │  │
│  │      12:30 ✓✓        │  │
│  └──────────────────────┘  │
│                            │
│  ┌── Anexos ────────────┐  │
│  │ ┌──────────────┐     │  │
│  │ │   🖼️ [nome]  │     │  │
│  │ │   [tamanho]  │     │  │
│  │ └──────────────┘     │  │
│  └──────────────────────┘  │
└────────────────────────────┘
```

**Modo Email (canal = email):**
```
┌─ Preview ──────────────────┐
│  📧 E-mail                 │
│                            │
│  De: [assinatura empresa]  │
│  Assunto: [assunto]        │
│                            │
│  ┌──────────────────────┐  │
│  │ [texto renderizado]  │  │
│  └──────────────────────┘  │
│                            │
│  📎 [arquivo-1] ([tam])    │
│  📎 [arquivo-2] ([tam])    │
└────────────────────────────┘
```

**Atualização:**
- Dispara em: `input` na textarea, `input` no assunto, `change` no canal pill, adição/remoção de imagem
- Debounce: 300ms
- Se texto vazio: mostra placeholder "Sua mensagem aparecerá aqui..."

### 3. Contador de Caracteres Melhorado

Atual: `0 caracteres` (texto simples à direita)

Novo:
- `245 / 1000 caracteres • ~1 mensagem` (WhatsApp)
- `245 caracteres` (Email, sem limite visual)
- Quando > 1000: texto e borda do contador ficam `#ef4444`
- Estimativa WhatsApp: 1 msg ≤ 1000, 2 msgs ≤ 2000, 3 msgs ≤ 3000...

---

## Estrutura HTML (Etapa 2)

```
<div id="tpl-step-2" style="display:none">
  <div class="tpl-editor-layout">          <!-- NOVO: wrapper 2 colunas -->

    <!-- Coluna Esquerda: Editor -->
    <div class="tpl-editor-col">
      <!-- [mantido] banner de contexto -->
      <!-- [mantido] nome, canal pills, assunto -->
      <!-- [mantido] textarea conteúdo -->
      <!-- [NOVO] contador melhorado -->
      <div class="tpl-char-counter" id="tpl-char-counter">0 / 1000 caracteres • ~1 mensagem</div>

      <!-- NOVO: Zona de Imagens -->
      <div class="tpl-image-zone" id="tpl-image-zone">
        <div class="tpl-image-grid" id="tpl-image-grid">
          <!-- thumbnails gerados via JS -->
        </div>
        <div class="tpl-image-drop-hint" id="tpl-image-drop-hint">
          📁 Solte imagens aqui ou Ctrl+V<br>
          <span>PNG, JPG, WEBP, PDF · até 15 MB</span>
        </div>
      </div>

      <!-- [mantido] badges de variáveis -->
    </div>

    <!-- Coluna Direita: Preview -->
    <div class="tpl-preview-col" id="tpl-preview-col">
      <div class="tpl-preview-header">
        <span id="tpl-preview-icon">📱</span>
        <span id="tpl-preview-label">WhatsApp</span>
      </div>
      <div class="tpl-preview-body" id="tpl-preview-body">
        <div class="tpl-preview-bubble" id="tpl-preview-bubble">
          Sua mensagem aparecerá aqui...
        </div>
        <div class="tpl-preview-attachments" id="tpl-preview-attachments"></div>
      </div>
    </div>

  </div>
</div>
```

---

## Funcionamento JavaScript

### Inicialização (`_iniciarEditorV2`)
- Chamado ao entrar na Etapa 2
- Configura listeners: `paste` no document, `dragover`/`drop` na zona de imagens
- Configura observer/debounce para preview ao vivo
- Renderiza imagens existentes (se edição)

### Paste de imagem (`_handlePaste`)
```javascript
_handlePaste(e) {
  const items = e.clipboardData?.items;
  if (!items) return;
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      e.preventDefault();
      const file = item.getAsFile();
      this._adicionarImagem(file);
    }
  }
}
```

### Adicionar/remover imagem (`_adicionarImagem`, `_removerImagem`)
- Valida tipo e tamanho
- Cria `previewUrl` via `URL.createObjectURL(file)`
- Se WhatsApp e já tem 1: substitui (com aviso)
- Atualiza grid de thumbnails
- Atualiza preview ao vivo
- Atualiza visibilidade do drop hint

### Preview ao vivo (`_atualizarPreview`)
- Lê conteúdo da textarea, assunto, canal atual
- Substitui variáveis por dados de exemplo
- Renderiza bolha WhatsApp ou email
- Renderiza thumbnails de anexos
- Troca ícone e label do preview ao mudar canal

### Upload múltiplo (`_fazerUploadAnexos`)
- Itera sobre `this._imagens` e faz upload sequencial via `POST .../upload-anexo`
- Coleta paths e metadados
- Retorna array de anexos para incluir no payload de salvar

---

## Backend: Adaptações necessárias

**Mínimas.** O sistema atual suporta 1 anexo por template. Para suportar múltiplos:

### Opção A (Recomendada): Manter 1 anexo, upload sequencial
- Manter a estrutura atual de 1 anexo por template
- Se o usuário adicionar múltiplas imagens para email, fazer upload de cada uma e armazenar paths em JSON no campo `anexo_arquivo_path` ou criar tabela separada
- Impacto: médio — precisa de migration ou JSON field

### Opção B: Anexo único, múltiplos uploads com concatenação
- Criar endpoint `POST .../upload-anexos` que aceita múltiplos arquivos
- Criar tabela `tenant_template_anexos` (template_id, arquivo_path, nome_original, mime_type, tamanho_bytes, ordem)
- Impacto: maior — migration + novo endpoint + schema

**Decisão:** Começar com Opção A (mínimo impacto), evoluir para B se necessário.

---

## Riscos

1. **Clipboard API:** Pode não funcionar em HTTP (só HTTPS ou localhost). Já estamos em localhost.
2. **Múltiplos anexos:** Backend atual suporta 1 anexo. Email com múltiplas imagens exigirá adaptação.
3. **Preview com dados falsos:** Pode gerar expectativa errada se o lead real tiver dados muito diferentes. Mitigação: botão "Usar lead real" opcional.
4. **Memória:** `URL.createObjectURL` para múltiplas imagens grandes. Mitigação: `revokeObjectURL` ao remover.

---

## Validação

- [ ] Ctrl+V de print screen cola imagem na zona
- [ ] Drag & drop de arquivo de imagem funciona
- [ ] Clique no card "+" abre file picker
- [ ] Remover imagem funciona (thumbnail some, preview atualiza)
- [ ] WhatsApp limita a 1 imagem
- [ ] Email aceita múltiplas imagens
- [ ] Preview ao vivo atualiza ao digitar (texto + variáveis substituídas)
- [ ] Preview ao vivo mostra thumbnails de anexos
- [ ] Trocar canal atualiza preview (WhatsApp ↔ Email)
- [ ] Contador de caracteres mostra estimativa WhatsApp
- [ ] Salvar template com imagens funciona
- [ ] Editar template com imagens existentes carrega corretamente
- [ ] Layout 2 colunas colapsa em mobile (< 900px)
