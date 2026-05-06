# Template Editor V2 Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix modal size being too small and the image zone click interaction not working reliably.

**Architecture:** Increase CSS width for slide-over modals and decouple the hidden file input from the dynamic image zone in HTML/JS.

**Tech Stack:** CSS, HTML, Vanilla JavaScript.

---

### Task 1: UI Expansion & HTML Restructure

**Files:**
- Modify: `sistema/cotte-frontend/css/tenant-comercial.css`
- Modify: `sistema/cotte-frontend/tenant-comercial.html`

- [ ] **Step 1: Increase Modal Width in CSS**

Modify `sistema/cotte-frontend/css/tenant-comercial.css`:
```css
/* Localizar por volta da linha 632 */
.modal-overlay.modal-slide-over .modal {
  height: 100vh;
  max-height: 100vh;
  width: 850px; /* Alterado de 480px para 850px */
  max-width: 95%; /* Garantir que não quebre em telas muito pequenas */
  margin: 0;
  border-radius: 12px 0 0 12px;
  /* ... resto mantido ... */
}
```

- [ ] **Step 2: Move Hidden Input in HTML**

Modify `sistema/cotte-frontend/tenant-comercial.html`:
Move the `<input type="file" id="tpl-anexo">` outside the `#tpl-image-zone` div to prevent it from being removed when the zone's innerHTML is updated.

```html
<!-- Localizar por volta da linha 824 -->
<div class="form-group">
    <label>Imagem / Anexo</label>
    <!-- Mover o input para cá, fora da zona clicável dinâmica -->
    <input type="file" id="tpl-anexo" style="display:none" accept="image/*,application/pdf">
    
    <div id="tpl-image-zone" class="tpl-image-zone">
        <i class="fas fa-image" style="font-size: 24px; margin-bottom: 8px;"></i>
        <span>Arraste uma imagem ou <strong>Cole (Ctrl+V)</strong></span>
        <!-- REMOVER o input daqui de dentro -->
    </div>
    <div id="tpl-image-previews" class="tpl-image-preview-container"></div>
    <small class="text-muted">WhatsApp permite apenas 1 imagem.</small>
</div>
```

- [ ] **Step 3: Commit**

```bash
git add sistema/cotte-frontend/css/tenant-comercial.css sistema/cotte-frontend/tenant-comercial.html
git commit -m "style: aumentar largura do modal e isolar input de anexo"
```

---

### Task 2: JS Click Delegation Fix

**Files:**
- Modify: `sistema/cotte-frontend/js/tenant-TemplatesManager.js`

- [ ] **Step 1: Update Click Logic in _initV2Events**

Ensure the click on `#tpl-image-zone` correctly triggers the file input even if the zone's content changes.

Modify `sistema/cotte-frontend/js/tenant-TemplatesManager.js`:
```javascript
// Localizar por volta da linha 510
    zone.addEventListener('click', (e) => {
      // Impede propagação se necessário
      const input = document.getElementById('tpl-anexo');
      if (input) {
          console.log('Triggering file input click');
          input.click();
      }
    });
```

- [ ] **Step 2: Refine _renderImagePreview**

Ensure `_renderImagePreview` only updates the content and doesn't affect the input (which we moved outside in Task 1).

```javascript
// Localizar por volta da linha 590
    if (!file) {
      zone.innerHTML = `
        <i class="fas fa-image" style="font-size: 24px; margin-bottom: 8px;"></i>
        <span>Clique ou arraste uma imagem/PDF aqui ou <strong>Cole (Ctrl+V)</strong></span>
      `;
      if (previewImg) previewImg.innerHTML = '';
      return;
    }
```

- [ ] **Step 3: Verify and Commit**

```bash
git add sistema/cotte-frontend/js/tenant-TemplatesManager.js
git commit -m "fix: corrigir delegação de clique na zona de imagem"
```
