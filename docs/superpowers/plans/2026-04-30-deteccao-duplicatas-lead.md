# Detecção de Duplicatas em Tempo Real — Lead Form

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ao digitar WhatsApp ou e-mail no formulário de lead, verificar via debounce (500ms) se já existe um lead com esse contato e mostrar um card inline com opção de "Atualizar este lead" (transforma o form em modo edição) ou "Ignorar".

**Architecture:** Novo endpoint `GET /comercial/leads/check-duplicata?whatsapp=X&email=Y` no backend; no frontend, listeners nos inputs disparam debounce que chama a API e renderiza/oculta um card `#lead-duplicata-card` diretamente abaixo dos campos de contato. Clicar "Atualizar este lead" chama `_aplicarLeadExistente(lead)` para popular o form inline sem fechar o modal.

**Tech Stack:** FastAPI + SQLAlchemy (backend), Vanilla JS + HTML5 (frontend), CSS custom variables já existentes no projeto.

---

## Arquivos Afetados

| Arquivo | Ação |
|---|---|
| `sistema/app/routers/comercial_leads.py` | Adicionar endpoint `GET /leads/check-duplicata` (antes da linha do CRUD comment ~207) |
| `sistema/cotte-frontend/comercial.html` | Adicionar `#lead-duplicata-card` no modal; bump versão JS `?v=5` e CSS `?v=7` |
| `sistema/cotte-frontend/css/comercial.css` | Adicionar estilos do card duplicata no final do arquivo |
| `sistema/cotte-frontend/js/comercial-leads.js` | Adicionar debounce, funções de check/render/hide, `_aplicarLeadExistente()`, event listeners |

---

## Task 1: Endpoint Backend `GET /leads/check-duplicata`

**Files:**
- Modify: `sistema/app/routers/comercial_leads.py` — inserir antes do comentário `# ═══ CRUD LEADS` (linha ~207)

- [ ] **Step 1: Abrir o arquivo e localizar o ponto de inserção**

```bash
grep -n "CRUD LEADS" sistema/app/routers/comercial_leads.py
```

Resultado esperado: linha ~207

- [ ] **Step 2: Inserir o endpoint check-duplicata**

Inserir o bloco abaixo **imediatamente antes** do comentário `# ═══ CRUD LEADS`:

```python
@router.get("/leads/check-duplicata")
def check_duplicata_lead(
    whatsapp: Optional[str] = None,
    email: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(get_superadmin),
):
    """Verifica se existe lead com o WhatsApp ou e-mail informado. Retorna o lead ou null."""
    if not whatsapp and not email:
        return None

    filters = []
    if whatsapp:
        wa_norm = re.sub(r"\D", "", whatsapp)
        filters.append(func.regexp_replace(CommercialLead.whatsapp, r"\D", "", "g") == wa_norm)
    if email:
        filters.append(func.lower(CommercialLead.email) == email.lower().strip())

    lead = (
        db.query(CommercialLead)
        .options(
            joinedload(CommercialLead.segmento_rel),
            joinedload(CommercialLead.origem_rel),
        )
        .filter(CommercialLead.ativo == True, or_(*filters))
        .first()
    )

    return _lead_to_out(lead) if lead else None
```

> **Nota:** `re`, `func`, `or_`, `joinedload`, `CommercialLead`, `_lead_to_out`, `get_superadmin`, `Optional`, `Depends`, `get_db` já estão importados no arquivo.

- [ ] **Step 3: Verificar sintaxe Python**

```bash
cd /home/gk/Projeto-izi/sistema && python -c "import ast; ast.parse(open('app/routers/comercial_leads.py').read()); print('OK')"
```

Resultado esperado: `OK`

- [ ] **Step 4: Testar o endpoint manualmente (com servidor rodando)**

```bash
curl -s "http://localhost:8000/comercial/leads/check-duplicata?whatsapp=48991234567" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Resultado esperado: JSON do lead existente ou `null`

- [ ] **Step 5: Commit**

```bash
git add sistema/app/routers/comercial_leads.py
git commit -m "feat(comercial): endpoint GET /leads/check-duplicata para detecção de duplicatas"
```

---

## Task 2: CSS — Estilos do Card Duplicata

**Files:**
- Modify: `sistema/cotte-frontend/css/comercial.css` — adicionar ao final do arquivo

- [ ] **Step 1: Adicionar estilos ao final de `comercial.css`**

```css
/* ── Detecção de Duplicata ────────────────────────────────────── */
#lead-duplicata-card {
  border: 1.5px solid var(--warning, #f59e0b);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,.08);
  padding: 10px 12px;
  margin-top: 6px;
  animation: fadeInDown .18s ease;
}

#lead-duplicata-card .dup-label {
  font-size: 11px;
  color: #d97706;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .5px;
  margin-bottom: 6px;
}

#lead-duplicata-card .dup-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

#lead-duplicata-card .dup-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #e0e7ff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  color: #4f46e5;
  font-size: 13px;
  flex-shrink: 0;
}

#lead-duplicata-card .dup-nome {
  font-weight: 600;
  font-size: 13px;
}

#lead-duplicata-card .dup-meta {
  font-size: 11px;
  color: #666;
  margin-top: 1px;
}

#lead-duplicata-card .dup-status {
  font-weight: 600;
  color: #059669;
}

#lead-duplicata-card .dup-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

#lead-duplicata-card .btn-dup-atualizar {
  flex: 1;
  padding: 5px 0;
  background: var(--primary, #4f46e5);
  color: #fff;
  border: none;
  border-radius: 5px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity .15s;
}

#lead-duplicata-card .btn-dup-atualizar:hover { opacity: .85; }

#lead-duplicata-card .btn-dup-ignorar {
  padding: 5px 10px;
  background: #f3f4f6;
  color: #374151;
  border: none;
  border-radius: 5px;
  font-size: 11px;
  cursor: pointer;
}

#lead-duplicata-card .btn-dup-ignorar:hover { background: #e5e7eb; }

.lead-field-checking {
  position: relative;
}

.lead-field-checking::after {
  content: '';
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  width: 14px;
  height: 14px;
  border: 2px solid #d1d5db;
  border-top-color: var(--primary, #4f46e5);
  border-radius: 50%;
  animation: spin .6s linear infinite;
}

@keyframes fadeInDown {
  from { opacity: 0; transform: translateY(-6px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

> **Nota:** `@keyframes spin` já existe no arquivo de CSS do projeto. `fadeInDown` é novo.

- [ ] **Step 2: Verificar se `@keyframes spin` já existe (para não duplicar)**

```bash
grep -n "keyframes spin" sistema/cotte-frontend/css/comercial.css
```

Se existir, remover o `@keyframes spin` do bloco acima antes de salvar.

- [ ] **Step 3: Commit**

```bash
git add sistema/cotte-frontend/css/comercial.css
git commit -m "feat(comercial): estilos CSS para card de duplicata inline"
```

---

## Task 3: HTML — Adicionar `#lead-duplicata-card` no Modal

**Files:**
- Modify: `sistema/cotte-frontend/comercial.html`

- [ ] **Step 1: Localizar os campos WhatsApp e email no modal**

```bash
grep -n "lead-whatsapp\|lead-email" sistema/cotte-frontend/comercial.html
```

Os dois inputs ficam próximos um do outro dentro de um `<div class="fr">` (flex-row).

- [ ] **Step 2: Adicionar o card duplicata após o grupo WhatsApp/email**

Localizar com `grep -n "lead-whatsapp\|lead-email" comercial.html` — os dois inputs ficam num mesmo `<div class="fr">`. Após o `</div>` que fecha esse `<div class="fr">`, inserir:

```html
<!-- Card de duplicata detectada -->
<div id="lead-duplicata-card" style="display:none" role="alert" aria-live="polite"></div>
```

- [ ] **Step 3: Bump de versão no cache-bust do JS e CSS**

Localizar e alterar no `<head>` da página:
- `comercial.css?v=6` → `comercial.css?v=7`
- `comercial-leads.js?v=4` → `comercial-leads.js?v=5`

- [ ] **Step 4: Verificar HTML bem-formado**

```bash
grep -A5 "lead-duplicata-card" sistema/cotte-frontend/comercial.html
```

Resultado esperado: div vazia com `style="display:none"` logo após o grupo WA/email.

- [ ] **Step 5: Commit**

```bash
git add sistema/cotte-frontend/comercial.html
git commit -m "feat(comercial): adiciona container #lead-duplicata-card no modal de lead"
```

---

## Task 4: JavaScript — Debounce + Check + Card + Transformação de Form

**Files:**
- Modify: `sistema/cotte-frontend/js/comercial-leads.js`

### 4a — Variáveis de controle e helper de normalização

- [ ] **Step 1: Adicionar variáveis e funções utilitárias após as variáveis globais existentes (topo do arquivo, após `var debounceTimer`)**

```javascript
// ── Detecção de duplicata ──────────────────────────────────────────
var _dupTimer = null;
var _dupIgnorada = false;  // true quando usuário clica "Ignorar"
var _dupLeadId = null;     // id do lead duplicado encontrado

function _normalizarTelefone(v) {
  return (v || '').replace(/\D/g, '');
}

function _inicialsDup(nome) {
  var parts = (nome || '').trim().split(' ');
  return (parts[0][0] || '') + (parts[1] ? parts[1][0] : '');
}
```

### 4b — Funções de renderização e ocultação do card

- [ ] **Step 2: Adicionar funções de card**

```javascript
function _mostrarCardDuplicata(lead) {
  var card = document.getElementById('lead-duplicata-card');
  if (!card) return;
  var initials = _inicialsDup(lead.nome_responsavel).toUpperCase();
  var status = lead.status_pipeline || '';
  card.innerHTML =
    '<div class="dup-label">⚠️ Lead já existe</div>' +
    '<div class="dup-info">' +
      '<div class="dup-avatar">' + initials + '</div>' +
      '<div>' +
        '<div class="dup-nome">' + (lead.nome_responsavel || '') + '</div>' +
        '<div class="dup-meta">' + (lead.nome_empresa || '') +
          ' · <span class="dup-status">● ' + status + '</span></div>' +
      '</div>' +
    '</div>' +
    '<div class="dup-actions">' +
      '<button class="btn-dup-atualizar" onclick="_usarLeadExistente(' + lead.id + ', this)">Atualizar este lead</button>' +
      '<button class="btn-dup-ignorar" onclick="_ignorarDuplicata()">Ignorar</button>' +
    '</div>';
  card.style.display = 'block';
}

function _ocultarCardDuplicata() {
  var card = document.getElementById('lead-duplicata-card');
  if (card) { card.style.display = 'none'; card.innerHTML = ''; }
}
```

### 4c — Ação "Atualizar este lead": transformar modal em modo edição

- [ ] **Step 3: Adicionar `_usarLeadExistente` e `_ignorarDuplicata`**

```javascript
async function _usarLeadExistente(leadId, btn) {
  btn.disabled = true;
  btn.textContent = 'Carregando...';
  try {
    var l = await api.get('/comercial/leads/' + leadId);
    leadAtualId = leadId;
    document.getElementById('modal-lead-title').textContent = 'Editando: ' + (l.nome_responsavel || 'Lead');
    document.getElementById('lead-id').value = l.id;
    document.getElementById('lead-nome-responsavel').value = l.nome_responsavel || '';
    document.getElementById('lead-nome-empresa').value = l.nome_empresa || '';
    document.getElementById('lead-whatsapp').value = l.whatsapp || '';
    document.getElementById('lead-email').value = l.email || '';
    document.getElementById('lead-cidade').value = l.cidade || '';
    document.getElementById('lead-segmento-id').value = l.segmento_id || '';
    document.getElementById('lead-origem-id').value = l.origem_lead_id || '';
    document.getElementById('lead-plano').value = l.interesse_plano || '';
    document.getElementById('lead-valor').value = l.valor_proposto || '';
    document.getElementById('lead-observacoes').value = l.observacoes || '';
    if (l.proximo_contato_em)
      document.getElementById('lead-proximo-contato').value = new Date(l.proximo_contato_em).toISOString().slice(0, 16);
    document.getElementById('lead-empresa-id').value = l.empresa_id || '';
    // Endereço
    document.getElementById('lead-cep').value = l.cep || '';
    document.getElementById('lead-logradouro').value = l.logradouro || '';
    document.getElementById('lead-numero').value = l.numero || '';
    document.getElementById('lead-complemento').value = l.complemento || '';
    document.getElementById('lead-bairro').value = l.bairro || '';
    document.getElementById('lead-uf').value = l.uf || '';
    if (l.cep || l.logradouro) document.getElementById('accordion-endereco').open = true;
    // Limpar seção de primeiro contato
    document.getElementById('lead-template-id').value = '';
    document.getElementById('lead-campanha-id').value = '';
    document.getElementById('lead-tpl-preview-area').style.display = 'none';
    document.getElementById('accordion-primeiro-contato').open = false;
    _ocultarCardDuplicata();
    _dupLeadId = leadId;
    showToast('Formulário carregado com dados do lead existente', 'info');
  } catch(e) {
    showToast('Erro ao carregar lead', 'error');
    btn.disabled = false;
    btn.textContent = 'Atualizar este lead';
  }
}

function _ignorarDuplicata() {
  _dupIgnorada = true;
  _ocultarCardDuplicata();
}
```

### 4d — Função de debounce + check principal

- [ ] **Step 4: Adicionar `_checkDuplicataLead`**

```javascript
async function _checkDuplicataLead(whatsapp, email) {
  var wa = _normalizarTelefone(whatsapp);
  var em = (email || '').trim();
  if (!wa && !em) { _ocultarCardDuplicata(); return; }
  if (_dupIgnorada) return;

  // mostrar spinner no wrapper do campo que disparou
  var params = new URLSearchParams();
  if (wa) params.set('whatsapp', wa);
  if (em) params.set('email', em);

  try {
    var lead = await api.get('/comercial/leads/check-duplicata?' + params.toString());
    if (lead && lead.id && (!leadAtualId || lead.id !== leadAtualId)) {
      _mostrarCardDuplicata(lead);
    } else {
      _ocultarCardDuplicata();
    }
  } catch(e) {
    // silenciar erros de rede no check (não bloquear o usuário)
    _ocultarCardDuplicata();
  }
}
```

> **Nota:** a condição `(!leadAtualId || lead.id !== leadAtualId)` evita mostrar o card quando estamos editando o próprio lead.

### 4e — Reset do estado ao abrir o modal

- [ ] **Step 5: Modificar `abrirModalLead()` para resetar estado de duplicata**

Localizar a função `abrirModalLead()` (~linha 771) e adicionar logo após `leadAtualId = null;`:

```javascript
_dupIgnorada = false;
_dupLeadId = null;
_ocultarCardDuplicata();
```

### 4f — Event listeners nos inputs

- [ ] **Step 6: Adicionar listeners dentro do bloco `DOMContentLoaded` existente (linha ~1080 de `comercial-leads.js`)**

Localizar `document.addEventListener('DOMContentLoaded', () => {` (~linha 1080) e adicionar ao final desse bloco, antes do `});` de fechamento:

```javascript
// Detecção de duplicata em tempo real
var _waInput = document.getElementById('lead-whatsapp');
var _emInput = document.getElementById('lead-email');

function _onContatoInput() {
  clearTimeout(_dupTimer);
  if (_dupIgnorada) return;
  _dupTimer = setTimeout(function() {
    _checkDuplicataLead(
      document.getElementById('lead-whatsapp').value,
      document.getElementById('lead-email').value
    );
  }, 500);
}

if (_waInput) _waInput.addEventListener('input', _onContatoInput);
if (_emInput) _emInput.addEventListener('input', _onContatoInput);
```

- [ ] **Step 7: Verificar sintaxe JS**

```bash
node --check sistema/cotte-frontend/js/comercial-leads.js && echo "OK"
```

Resultado esperado: `OK` (sem erros de sintaxe)

- [ ] **Step 8: Commit**

```bash
git add sistema/cotte-frontend/js/comercial-leads.js
git commit -m "feat(comercial): detecção de duplicatas em tempo real no formulário de lead"
```

---

## Task 5: Teste Manual End-to-End

- [ ] **Step 1: Abrir `comercial.html` no browser (ou servidor local)**

- [ ] **Step 2: Abrir modal "Novo Lead"**

- [ ] **Step 3: Digitar o WhatsApp de um lead existente no banco**

Esperar 500ms. Resultado esperado: card amarelo aparece com nome/empresa/status do lead.

- [ ] **Step 4: Clicar "Atualizar este lead"**

Resultado esperado: formulário se popula com dados do lead, título muda para `Editando: [Nome]`, card desaparece, toast info.

- [ ] **Step 5: Clicar "Ignorar" em vez de "Atualizar"**

Novo teste: digitar WA duplicado → clicar "Ignorar" → continuar digitando no mesmo campo → verificar que o card **não** reaparece.

- [ ] **Step 6: Testar com e-mail duplicado**

Digitar email de lead existente → verificar card aparece.

- [ ] **Step 7: Testar campo limpo**

Apagar o conteúdo do campo → verificar que o card desaparece e não ocorre chamada à API.

- [ ] **Step 8: Testar edição de lead existente (sem falso positivo)**

Abrir `editarLead(id)` → editar o WhatsApp do próprio lead → verificar que o card **não** aparece (condição `lead.id !== leadAtualId`).

---

## Verificação Final

```bash
# Sintaxe Python
cd sistema && python -c "import ast; ast.parse(open('app/routers/comercial_leads.py').read()); print('Python OK')"

# Sintaxe JS
node --check cotte-frontend/js/comercial-leads.js && echo "JS OK"
```
