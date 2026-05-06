# Design Spec: Kanban Header Refinement

## Objective
Refine the visual appearance of the Kanban column headers in the Commercial Pipeline to fix alignment issues, add visual markers (emojis), and improve vertical space efficiency.

## Context
The Kanban headers were previously showing misaligned text and excessive height. The user requested adding emojis next to the text and reducing the overall header height.

## Proposed Changes

### 1. Frontend Logic (JavaScript)
- **File:** `sistema/cotte-frontend/js/tenant-comercial-pipeline.js`
- **Change:** 
    - Wrap the column emoji in a `<span>` with class `k-title-emoji`.
    - Change the inline style of `.k-head` to `align-items: center` (instead of `flex-start`).
    - Remove `overflow-wrap: anywhere` from the inline style of `.k-title` and replace with `word-break: break-word` (for consistency with CSS).

### 2. Styling (CSS)
- **File:** `sistema/cotte-frontend/css/tenant-comercial-precision.css`
- **Changes:**
    - `.k-head`: Reduce vertical padding to `var(--space-2)` (8px). Keep horizontal padding as `var(--space-5)`.
    - `.k-head`: Set `align-items: center`.
    - `.k-title-emoji`: 
        - `font-size: 1.15rem`
        - `margin-right: 8px`
        - `display: inline-flex`
        - `align-items: center`
    - `.k-title`: Ensure it stays `block` or `inline-block` to wrap properly next to the emoji.

## Success Criteria
- [ ] Kanban column headers are noticeably shorter.
- [ ] Emojis are aligned horizontally with the column title.
- [ ] There is a clear 8px padding above and below the title text/emoji.
- [ ] Column titles do not touch the left edge of the column container.

## Rollback Plan
Revert changes to `tenant-comercial-pipeline.js` and `tenant-comercial-precision.css`.
