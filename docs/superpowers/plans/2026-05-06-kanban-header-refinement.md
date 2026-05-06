# Kanban Header Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add emojis to Kanban column headers, reduce vertical height, and improve alignment.

**Architecture:** Modify JavaScript template generation to wrap emojis in a specific class and update CSS to reduce padding and center items.

**Tech Stack:** JavaScript, CSS.

---

### Task 1: Update CSS for Compact Headers and Emoji Styling

**Files:**
- Modify: `sistema/cotte-frontend/css/tenant-comercial-precision.css`

- [ ] **Step 1: Reduce padding and align items in .k-head**
    Modify lines 563-570.
    ```css
    .k-head {
      padding: var(--space-2) var(--space-5); /* Reduzido de space-4 para space-2 (8px) */
      display: flex;
      justify-content: space-between;
      align-items: center; /* Alterado de flex-start para center */
      gap: var(--space-2);
      border-bottom: 1.5px solid var(--color-outline-subtle);
    }
    ```

- [ ] **Step 2: Add styles for k-title-emoji**
    Add after `.k-head` block.
    ```css
    .k-title-emoji {
      font-size: 1.15rem;
      margin-right: 8px;
      display: inline-flex;
      align-items: center;
      line-height: 1;
    }
    ```

- [ ] **Step 3: Commit CSS changes**
    ```bash
    git add sistema/cotte-frontend/css/tenant-comercial-precision.css
    git commit -m "style: compact kanban headers and add emoji styling"
    ```

### Task 2: Update JavaScript Template for Headers

**Files:**
- Modify: `sistema/cotte-frontend/js/tenant-comercial-pipeline.js`

- [ ] **Step 1: Wrap emoji in span and update inline styles**
    Modify line 51.
    ```javascript
    // Old:
    // '<div class="k-head-left" style="min-width:0;flex:1"><div class="k-title" style="line-height:1.25;word-break:break-word">' + (s.emoji || '') + ' ' + esc(s.label) + '</div>' +
    
    // New:
    '<div class="k-head-left" style="min-width:0;flex:1;flex-direction:row;align-items:center"><span class="k-title-emoji">' + (s.emoji || '') + '</span><div class="k-title" style="line-height:1.25;word-break:break-word">' + esc(s.label) + '</div>' +
    ```

- [ ] **Step 2: Commit JS changes**
    ```bash
    git add sistema/cotte-frontend/js/tenant-comercial-pipeline.js
    git commit -m "feat: wrap kanban header emojis in span and adjust layout"
    ```

### Task 3: Final Verification

- [ ] **Step 1: Verify visual alignment**
    Manual check (if browser available) or verify code consistency.
    Expected: Headers have 8px vertical padding, emojis are centered vertically with labels.
