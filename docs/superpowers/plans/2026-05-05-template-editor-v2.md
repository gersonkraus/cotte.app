# Template Editor V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the template editor into a modern, split-layout interface with image paste support and live preview.

**Architecture:** 
- Split layout: Editor on the left, Preview on the right.
- Visual Image Zone: Replaces file input, supports paste/drop.
- Live Preview: Real-time substitution of variables (`{nome}`, etc.) using sample data.
- Stable Integration: Map the new UI state back to the existing backend single-attachment structure (for now).

**Tech Stack:** Vanilla JS, CSS (existing project styles), FastAPI backend.

---

### Task 1: CSS - New UI Layout & Styles

**Files:**
- Modify: `/home/gk/Projeto-izi/sistema/cotte-frontend/css/tenant-comercial.css`

- [ ] **Step 1: Add Split Layout Classes**

```css
/* Template V2 Split Layout */
.tpl-v2-container {
    display: flex;
    gap: 24px;
    height: 100%;
    min-height: 450px;
}

.tpl-v2-editor {
    flex: 1.2;
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.tpl-v2-preview-panel {
    flex: 0.8;
    background: #f8fafc;
    border-radius: 12px;
    padding: 20px;
    border: 1px solid #e2e8f0;
    display: flex;
    flex-direction: column;
    position: sticky;
    top: 0;
}

/* Image Paste Zone */
.tpl-image-zone {
    border: 2px dashed #cbd5e1;
    border-radius: 12px;
    padding: 16px;
    text-align: center;
    background: #fff;
    cursor: pointer;
    transition: all 0.2s;
    position: relative;
    min-height: 80px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #64748b;
}

.tpl-image-zone:hover, .tpl-image-zone.dragover {
    border-color: var(--accent);
    background: #f0fdf4;
    color: var(--accent);
}

.tpl-image-preview-container {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
    width: 100%;
}

.tpl-image-thumb {
    width: 60px;
    height: 60px;
    border-radius: 6px;
    object-fit: cover;
    border: 1px solid #e2e8f0;
    position: relative;
}

.tpl-image-thumb-remove {
    position: absolute;
    top: -6px;
    right: -6px;
    background: var(--red);
    color: white;
    border-radius: 50%;
    width: 18px;
    height: 18px;
    font-size: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    border: 2px solid white;
}

/* Live Preview Content */
.tpl-live-preview-window {
    background: white;
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    font-size: 14px;
    line-height: 1.5;
    flex: 1;
    overflow-y: auto;
    border: 1px solid #e2e8f0;
}

.tpl-preview-header {
    font-weight: 600;
    font-size: 12px;
    color: #64748b;
    text-transform: uppercase;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
}

.tpl-preview-image {
    width: 100%;
    max-height: 200px;
    object-fit: contain;
    border-radius: 6px;
    margin-bottom: 12px;
    background: #f1f5f9;
}
```

- [ ] **Step 2: Run verification**
Check if CSS is valid (manually or via basic grep for syntax errors if needed).

- [ ] **Step 3: Commit**

```bash
git add sistema/cotte-frontend/css/tenant-comercial.css
git commit -m "style: add styles for template editor v2"
```

---

### Task 2: HTML - Modal Restructure

**Files:**
- Modify: `/home/gk/Projeto-izi/sistema/cotte-frontend/tenant-comercial.html`

- [ ] **Step 1: Replace tpl-step-2 content with Split Layout**

Change lines 790-834 approximately.

```html
<div id="tpl-step-2" style="display:none">
    <div class="tpl-v2-container">
        <!-- Coluna Esquerda: Editor -->
        <div class="tpl-v2-editor">
            <div class="form-group">
                <label>Nome do Template</label>
                <input type="text" id="tpl-nome" class="form-control" placeholder="Ex: Boas-vindas Soluções">
                <small id="tpl-sugestao-nome" class="tpl-sugestao-nome"></small>
            </div>

            <div class="form-group" id="tpl-assunto-group">
                <label>Assunto do E-mail</label>
                <input type="text" id="tpl-assunto" class="form-control" placeholder="Assunto que o cliente verá">
            </div>

            <div class="form-group">
                <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:8px">
                    <label style="margin:0">Mensagem</label>
                    <div id="tpl-char-counter" class="tpl-char-counter">0 caracteres</div>
                </div>
                <textarea id="tpl-conteudo" class="form-control" rows="8" placeholder="Digite sua mensagem..."></textarea>
                
                <div class="tpl-vars-interactive" style="margin-top: 10px;">
                    <button type="button" class="btn-var-badge" data-var="{nome_responsavel}">Nome</button>
                    <button type="button" class="btn-var-badge" data-var="{nome_empresa}">Empresa</button>
                    <button type="button" class="btn-var-badge" data-var="{whatsapp}">WhatsApp</button>
                    <button type="button" class="btn-var-badge" data-var="{dias_sem_contato}">Dias sem contato</button>
                    <button type="button" class="btn-var-badge" data-var="{valor}">Valor</button>
                    <button type="button" class="btn-var-badge" data-var="{etapa}">Etapa</button>
                </div>
            </div>

            <div class="form-group">
                <label>Imagem / Anexo</label>
                <div id="tpl-image-zone" class="tpl-image-zone">
                    <i class="fas fa-image" style="font-size: 24px; margin-bottom: 8px;"></i>
                    <span>Arraste uma imagem ou <strong>Cole (Ctrl+V)</strong></span>
                    <input type="file" id="tpl-anexo" style="display:none" accept="image/*,application/pdf">
                </div>
                <div id="tpl-image-previews" class="tpl-image-preview-container"></div>
                <small class="text-muted">WhatsApp permite apenas 1 imagem.</small>
            </div>
        </div>

        <!-- Coluna Direita: Preview -->
        <div class="tpl-v2-preview-panel">
            <div class="tpl-preview-header">
                <span>Visualização Real</span>
                <span id="tpl-preview-canal-label">WhatsApp</span>
            </div>
            <div class="tpl-live-preview-window">
                <img id="tpl-preview-img" class="tpl-preview-image" style="display:none">
                <div id="tpl-preview-text" style="white-space: pre-wrap;"></div>
            </div>
        </div>
    </div>
</div>
```

- [ ] **Step 2: Commit**

```bash
git add sistema/cotte-frontend/tenant-comercial.html
git commit -m "view: restructure template modal for v2 split layout"
```

---

### Task 3: JS - Core V2 Logic

**Files:**
- Modify: `/home/gk/Projeto-izi/sistema/cotte-frontend/js/tenant-TemplatesManager.js`

- [ ] **Step 1: Initialize Image Zone Events**

Add `_initV2Events` call in `init`.

```javascript
  static init() {
    TemplatesManager._initV2Events();
    // ... existing init ...
  }

  static _initV2Events() {
    const zone = document.getElementById('tpl-image-zone');
    if (!zone) return;

    zone.addEventListener('click', () => document.getElementById('tpl-anexo').click());
    
    zone.addEventListener('dragover', (e) => {
      e.preventDefault();
      zone.classList.add('dragover');
    });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
    zone.addEventListener('drop', (e) => {
      e.preventDefault();
      zone.classList.remove('dragover');
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        TemplatesManager._handleFileSelection(e.dataTransfer.files[0]);
      }
    });

    document.getElementById('tpl-conteudo').addEventListener('paste', (e) => {
      const items = (e.clipboardData || e.originalEvent.clipboardData).items;
      for (let index in items) {
        const item = items[index];
        if (item.kind === 'file') {
          const blob = item.getAsFile();
          TemplatesManager._handleFileSelection(blob);
        }
      }
    });

    document.getElementById('tpl-conteudo').addEventListener('input', TemplatesManager._updateLivePreview);
    document.getElementById('tpl-assunto').addEventListener('input', TemplatesManager._updateLivePreview);
    document.getElementById('tpl-anexo').addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        TemplatesManager._handleFileSelection(e.target.files[0]);
      }
    });
  }
```

- [ ] **Step 2: Handle File Selection & Preview**

```javascript
  static _handleFileSelection(file) {
    if (!file.type.startsWith('image/') && file.type !== 'application/pdf') {
      if (typeof showToast !== 'undefined') showToast('Apenas imagens ou PDF', 'error');
      return;
    }
    
    // Update hidden input for legacy compatibility
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    document.getElementById('tpl-anexo').files = dataTransfer.files;

    TemplatesManager._renderImagePreview(file);
    TemplatesManager._updateLivePreview();
  }

  static _renderImagePreview(file) {
    const container = document.getElementById('tpl-image-previews');
    container.innerHTML = ''; // Single attachment for now
    
    const wrapper = document.createElement('div');
    wrapper.style.position = 'relative';
    
    const img = document.createElement('img');
    img.className = 'tpl-image-thumb';
    
    if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => img.src = e.target.result;
        reader.readAsDataURL(file);
    } else {
        img.src = '/img/icon-pdf.png'; // Assume icon exists
    }
    
    const remove = document.createElement('div');
    remove.className = 'tpl-image-thumb-remove';
    remove.innerHTML = '&times;';
    remove.onclick = (e) => {
        e.stopPropagation();
        TemplatesManager._removeAnexo();
        container.innerHTML = '';
        TemplatesManager._updateLivePreview();
    };
    
    wrapper.appendChild(img);
    wrapper.appendChild(remove);
    container.appendChild(wrapper);
  }
```

- [ ] **Step 3: Live Preview Substitution**

```javascript
  static _updateLivePreview() {
    const conteudo = document.getElementById('tpl-conteudo').value;
    const canal = document.getElementById('tpl-canal').value;
    const assunto = document.getElementById('tpl-assunto').value;
    const previewText = document.getElementById('tpl-preview-text');
    const previewImg = document.getElementById('tpl-preview-img');
    const canalLabel = document.getElementById('tpl-preview-canal-label');

    if (!previewText) return;

    canalLabel.textContent = canal === 'email' ? 'E-mail' : 'WhatsApp';

    // Sample data for substitution
    const samples = {
        '{nome_responsavel}': 'João Silva',
        '{nome_empresa}': 'Empresa Exemplo Ltda',
        '{whatsapp}': '(11) 98765-4321',
        '{email}': 'joao@cliente.com',
        '{dias_sem_contato}': '5',
        '{valor}': 'R$ 1.500,00',
        '{etapa}': 'Proposta Enviada'
    };

    let text = conteudo;
    Object.keys(samples).forEach(key => {
        text = text.replace(new RegExp(key.replace('{','\\{').replace('}','\\}'), 'g'), `<strong>${samples[key]}</strong>`);
    });

    if (canal === 'email' && assunto) {
        text = `<div style="padding-bottom:10px; border-bottom:1px solid #eee; margin-bottom:10px"><strong>Assunto:</strong> ${assunto}</div>` + text;
    }

    previewText.innerHTML = text;

    // Image preview in window
    const file = document.getElementById('tpl-anexo').files[0];
    if (file && file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImg.src = e.target.result;
            previewImg.style.display = 'block';
        };
        reader.readAsDataURL(file);
    } else {
        previewImg.style.display = 'none';
    }
    
    TemplatesManager._updateCharCounter();
  }
```

- [ ] **Step 4: Commit**

```bash
git add sistema/cotte-frontend/js/tenant-TemplatesManager.js
git commit -m "feat: implement image paste and live preview logic"
```

---

### Task 5: Integration & Cleanup

**Files:**
- Modify: `/home/gk/Projeto-izi/sistema/cotte-frontend/js/tenant-TemplatesManager.js`
- Modify: `/home/gk/Projeto-izi/sistema/cotte-frontend/js/TemplatesManager.js` (Legacy fix)

- [ ] **Step 1: Update salvarTemplate to use new UI state**

The existing `salvarTemplate` already uses `_uploadSelectedAnexo` which reads from `tpl-anexo`. Since we update `tpl-anexo.files` in `_handleFileSelection`, it should work automatically. 

Just need to ensure `_updateLivePreview` is called when editing.

```javascript
  // In editarTemplate(id), after filling fields:
  TemplatesManager._updateLivePreview();
```

- [ ] **Step 2: Fix 405 Method Not Allowed in Legacy Manager**

Modify `/home/gk/Projeto-izi/sistema/cotte-frontend/js/TemplatesManager.js` line 120 approx.

```javascript
// OLD
await api.patch('/comercial/templates/' + id, data);
// NEW
await api.put('/comercial/templates/' + id, data);
```

- [ ] **Step 3: Final Verification**
Test the modal opening, pasting an image, typing variables, and saving.

- [ ] **Step 4: Commit**

```bash
git add sistema/cotte-frontend/js/tenant-TemplatesManager.js sistema/cotte-frontend/js/TemplatesManager.js
git commit -m "fix: fix legacy 405 error and integrate v2 UI with save flow"
```
