# Templates de Mensagem para Briefing - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrar templates de mensagem no briefing do comercial, permitindo escolher entre rascunho IA e templates pré-cadastrados.

**Architecture:** Estender o endpoint de preview de templates existente com novas variáveis do briefing, adicionar UI de seleção de template no card do briefing, e atualizar helper de variáveis no modal de templates.

**Tech Stack:** FastAPI, SQLAlchemy, JavaScript vanilla, HTML/CSS

---

## File Structure

| Arquivo | Responsabilidade |
|---------|------------------|
| `app/routers/tenant/comercial_templates.py` | Estender preview com novas variáveis |
| `app/routers/tenant/comercial_leads.py` | Adicionar helper de dias sem contato |
| `cotte-frontend/js/tenant-comercial-briefing.js` | UI de seleção de template |
| `cotte-frontend/tenant-comercial.html` | Atualizar helper de variáveis no modal |

---

### Task 1: Estender endpoint de preview com novas variáveis

**Files:**
- Modify: `app/routers/tenant/comercial_templates.py:123-165`

- [ ] **Step 1: Adicionar cálculo de dias_sem_contato**

Modificar o endpoint `preview_template` para calcular dias desde último contato:

```python
from datetime import datetime, timezone

# Após obter o lead, calcular dias_sem_contato
dias_sem_contato = 0
if lead.ultimo_contato:
    try:
        ultimo = lead.ultimo_contato
        if ultimo.tzinfo is None:
            ultimo = ultimo.replace(tzinfo=timezone.utc)
        agora = datetime.now(timezone.utc)
        dias_sem_contato = (agora - ultimo).days
    except Exception:
        pass
```

- [ ] **Step 2: Adicionar substituição das novas variáveis**

Após as substituições existentes, adicionar:

```python
# Variáveis do briefing
conteudo = conteudo.replace("{dias_sem_contato}", str(dias_sem_contato))
conteudo = conteudo.replace("{score}", (lead.score or "frio").lower())
conteudo = conteudo.replace("{etapa}", (lead.status_pipeline or "").replace("_", " ").title())
conteudo = conteudo.replace("{plano}", lead.plano_interesse or "")

# Valor formatado
valor_str = ""
if lead.valor_proposto:
    valor_str = f"R$ {lead.valor_proposto:,.0f}".replace(",", ".")
conteudo = conteudo.replace("{valor}", valor_str)

# Também no assunto se existir
if assunto:
    assunto = assunto.replace("{dias_sem_contato}", str(dias_sem_contato))
    assunto = assunto.replace("{score}", (lead.score or "frio").lower())
    assunto = assunto.replace("{etapa}", (lead.status_pipeline or "").replace("_", " ").title())
    assunto = assunto.replace("{plano}", lead.plano_interesse or "")
    assunto = assunto.replace("{valor}", valor_str)
```

- [ ] **Step 3: Atualizar return para incluir variáveis calculadas**

```python
return TemplatePreview(
    assunto=assunto, 
    conteudo=conteudo,
    dias_sem_contato=dias_sem_contato,
    score=lead.score,
    etapa=lead.status_pipeline,
    valor=lead.valor_proposto,
    plano=lead.plano_interesse
)
```

- [ ] **Step 4: Atualizar schema TemplatePreview**

Modificar `app/schemas/schemas.py` para adicionar campos ao TemplatePreview:

```python
class TemplatePreview(BaseModel):
    assunto: Optional[str] = None
    conteudo: str
    dias_sem_contato: Optional[int] = None
    score: Optional[str] = None
    etapa: Optional[str] = None
    valor: Optional[float] = None
    plano: Optional[str] = None
```

- [ ] **Step 5: Testar endpoint manualmente**

```bash
# Reiniciar servidor e testar via curl ou Postman
curl -X POST "http://localhost:8000/api/v1/tenant/comercial/templates/1/preview?lead_id=1" \
  -H "Authorization: Bearer <token>"
```

- [ ] **Step 6: Commit**

```bash
git add app/routers/tenant/comercial_templates.py app/schemas/schemas.py
git commit -m "feat(comercial): estende preview de template com variáveis do briefing"
```

---

### Task 2: Adicionar endpoint para listar templates por tipo

**Files:**
- Modify: `app/routers/tenant/comercial_templates.py:39-52`

- [ ] **Step 1: Adicionar parâmetro de filtro por tipo**

Modificar o endpoint `list_templates`:

```python
@router.get("/", response_model=List[TemplateOut])
async def list_templates(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(exigir_permissao("comercial", "leitura")),
    ativo: Optional[bool] = Query(None),
    tipo: Optional[str] = Query(None),  # Novo parâmetro
    canal: Optional[str] = Query(None),  # Novo parâmetro
):
    q = db.query(TenantCommercialTemplate).filter(
        TenantCommercialTemplate.empresa_id == current_user.empresa_id
    )
    if ativo is None:
        q = q.filter(TenantCommercialTemplate.ativo.is_(True))
    else:
        q = q.filter(TenantCommercialTemplate.ativo == ativo)
    
    # Filtros novos
    if tipo:
        q = q.filter(TenantCommercialTemplate.tipo == tipo)
    if canal:
        q = q.filter(TenantCommercialTemplate.canal.in_([canal, "ambos"]))
    
    return q.order_by(TenantCommercialTemplate.id.desc()).all()
```

- [ ] **Step 2: Testar endpoint**

```bash
curl "http://localhost:8000/api/v1/tenant/comercial/templates?tipo=followup&canal=whatsapp" \
  -H "Authorization: Bearer <token>"
```

- [ ] **Step 3: Commit**

```bash
git add app/routers/tenant/comercial_templates.py
git commit -m "feat(comercial): adiciona filtros de tipo e canal na listagem de templates"
```

---

### Task 3: Adicionar UI de seleção de template no briefing

**Files:**
- Modify: `cotte-frontend/js/tenant-comercial-briefing.js`

- [ ] **Step 1: Adicionar estado para templates carregados**

Adicionar no início do módulo:

```javascript
var _templates = null;
var _templateSelecionado = {};
```

- [ ] **Step 2: Criar função para carregar templates**

```javascript
async function _carregarTemplates(tipo, canal) {
  if (_templates) return _templates;
  try {
    var params = '?tipo=' + tipo + '&canal=' + canal;
    var res = await window.ApiService.get('/tenant/comercial/templates' + params);
    _templates = res || [];
    return _templates;
  } catch (e) {
    console.error('[BriefingIA] Erro ao carregar templates:', e);
    return [];
  }
}
```

- [ ] **Step 3: Modificar _renderCard para adicionar botão de template**

Encontrar a linha que define `botoesHtml` (aprox. linha 129-134) e modificar:

```javascript
var botoesHtml = '';
if (!concluido) {
  if (item.tipo_acao === 'mover_etapa') {
    botoesHtml =
      '<button class="briefing-btn-enviar" onclick="BriefingIA.confirmarEtapa(' + item.lead_id + ',\'' + _esc(item.etapa_sugerida || '') + '\')">✓ Mover etapa</button>' +
      '<button class="briefing-btn-ver" onclick="BriefingIA.verLead(' + item.lead_id + ')">Ver lead</button>' +
      '<button class="briefing-btn-pular" onclick="BriefingIA.pular(' + item.lead_id + ')">✗ Pular</button>';
  } else {
    var canalFiltro = item.tipo_acao === 'mensagem_email' ? 'email' : 'whatsapp';
    botoesHtml =
      '<button class="briefing-btn-enviar" onclick="BriefingIA.enviar(' + item.lead_id + ',\'' + item.tipo_acao + '\')">✓ Enviar agora</button>' +
      '<button class="briefing-btn-template" onclick="BriefingIA.selecionarTemplate(' + item.lead_id + ',\'' + canalFiltro + '\')">📋 Template</button>' +
      '<button class="briefing-btn-editar" onclick="BriefingIA.editar(' + item.lead_id + ')">✎ Editar</button>' +
      '<button class="briefing-btn-pular" onclick="BriefingIA.pular(' + item.lead_id + ')">✗ Pular</button>';
  }
}
```

- [ ] **Step 4: Adicionar função selecionarTemplate à API pública**

```javascript
selecionarTemplate: async function(leadId, canal) {
  var card = document.getElementById('briefing-card-' + leadId);
  if (!card) return;

  // Carregar templates
  var templates = await _carregarTemplates('followup', canal);
  if (!templates.length) {
    alert('Nenhum template de follow-up cadastrado para ' + canal + '. Cadastre na aba Templates.');
    return;
  }

  // Criar dropdown
  var dropdownId = 'template-dropdown-' + leadId;
  var existing = document.getElementById(dropdownId);
  if (existing) { existing.remove(); return; }

  var dropdown = document.createElement('div');
  dropdown.id = dropdownId;
  dropdown.className = 'briefing-template-dropdown';
  dropdown.innerHTML = '<div class="briefing-template-list">' +
    templates.map(function(t) {
      return '<div class="briefing-template-item" data-id="' + t.id + '" onclick="BriefingIA.usarTemplate(' + leadId + ',' + t.id + ',\'' + canal + '\')">' +
        '<strong>' + _esc(t.nome) + '</strong>' +
        '<span style="display:block;font-size:11px;color:#64748b">' + _esc(t.conteudo.slice(0,60)) + '...</span>' +
      '</div>';
    }).join('') +
    '<div class="briefing-template-item" style="color:#94a3b8" onclick="this.parentElement.remove()">Cancelar</div>' +
  '</div>';

  // Posicionar após botão de template
  var btnTemplate = card.querySelector('.briefing-btn-template');
  if (btnTemplate) {
    btnTemplate.parentElement.style.position = 'relative';
    btnTemplate.parentElement.appendChild(dropdown);
  }
},

usarTemplate: async function(leadId, templateId, canal) {
  var card = document.getElementById('briefing-card-' + leadId);
  if (!card) return;

  try {
    // Chamar preview
    var preview = await window.ApiService.post('/tenant/comercial/templates/' + templateId + '/preview?lead_id=' + leadId, {});
    
    // Substituir rascunho
    var rascunhoEl = card.querySelector('#rascunho-' + leadId);
    if (rascunhoEl) {
      rascunhoEl.textContent = preview.conteudo;
    }

    // Remover dropdown
    var dropdown = document.getElementById('template-dropdown-' + leadId);
    if (dropdown) dropdown.remove();

  } catch (e) {
    alert('Erro ao carregar template. Tente novamente.');
    console.error('[BriefingIA.usarTemplate]', e);
  }
},
```

- [ ] **Step 5: Adicionar CSS para dropdown**

Na função `_injectStyles`, adicionar:

```javascript
'.briefing-template-dropdown{position:absolute;top:100%;left:0;z-index:100;background:#fff;border:1px solid #e2e8f0;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,.15);min-width:250px;max-height:300px;overflow-y:auto;margin-top:4px}',
'.briefing-template-list{padding:8px 0}',
'.briefing-template-item{padding:10px 14px;cursor:pointer;border-bottom:1px solid #f1f5f9}',
'.briefing-template-item:last-child{border-bottom:none}',
'.briefing-template-item:hover{background:#f8fafc}',
'.briefing-template-item strong{display:block;font-size:13px;color:#1e293b}',
'.briefing-btn-template{background:#6366f1;color:#fff;border:none;border-radius:6px;padding:7px 12px;font-size:0.8rem;font-weight:500;cursor:pointer}',
'.briefing-btn-template:hover{background:#4f46e5}',
```

- [ ] **Step 6: Testar fluxo completo**

1. Criar template de followup via UI
2. Abrir briefing
3. Clicar em "📋 Template"
4. Selecionar template
5. Verificar substituição do rascunho

- [ ] **Step 7: Commit**

```bash
git add cotte-frontend/js/tenant-comercial-briefing.js
git commit -m "feat(briefing): adiciona seleção de templates no briefing"
```

---

### Task 4: Atualizar helper de variáveis no modal de template

**Files:**
- Modify: `cotte-frontend/tenant-comercial.html:719-731`

- [ ] **Step 1: Adicionar novas variáveis ao helper**

Localizar a seção de botões de variáveis e adicionar:

```html
<div class="tpl-vars-interactive">
  <span style="font-size:11px;color:var(--muted);display:block;margin-bottom:6px;">Inserir variável no cursor:</span>
  <div style="display:flex;gap:6px;flex-wrap:wrap;">
    <button type="button" class="btn-var-badge" data-var="{nome_responsavel}">nome</button>
    <button type="button" class="btn-var-badge" data-var="{nome_empresa}">empresa</button>
    <button type="button" class="btn-var-badge" data-var="{whatsapp}">whatsapp</button>
    <button type="button" class="btn-var-badge" data-var="{email}">email</button>
    <button type="button" class="btn-var-badge" data-var="{cidade}">cidade</button>
    <button type="button" class="btn-var-badge" data-var="{dias_sem_contato}">dias_sem_contato</button>
    <button type="button" class="btn-var-badge" data-var="{score}">score</button>
    <button type="button" class="btn-var-badge" data-var="{etapa}">etapa</button>
    <button type="button" class="btn-var-badge" data-var="{valor}">valor</button>
    <button type="button" class="btn-var-badge" data-var="{plano}">plano</button>
  </div>
  <p style="font-size:10px;color:var(--muted);margin-top:8px">
    <strong>Briefing:</strong> dias_sem_contato, score, etapa, valor, plano
  </p>
</div>
```

- [ ] **Step 2: Commit**

```bash
git add cotte-frontend/tenant-comercial.html
git commit -m "feat(templates): adiciona variáveis do briefing ao helper"
```

---

### Task 5: Validação final

- [ ] **Step 1: Testar fluxo completo**

1. Acessar aba Templates
2. Criar template tipo "Follow-up" com variáveis do briefing
3. Acessar aba "Hoje" (Briefing)
4. Em um card, clicar "📋 Template"
5. Selecionar template
6. Verificar preview com variáveis preenchidas
7. Editar se necessário
8. Enviar mensagem

- [ ] **Step 2: Verificar responsividade mobile**

Testar em tela pequena:
- Dropdown aparece corretamente
- Botões não quebram o layout
- Template preview é legível

- [ ] **Step 3: Commit final**

```bash
git add -A
git commit -m "feat(comercial): templates de mensagem para briefing (finalizado)"
```

---

## Checklist de Aceitação

- [ ] Endpoint de preview suporta variáveis do briefing
- [ ] Endpoint de listagem filtra por tipo e canal
- [ ] Botão "📋 Template" aparece nos cards do briefing
- [ ] Dropdown mostra templates relevantes
- [ ] Preview funciona com variáveis preenchidas
- [ ] Modal de template mostra novas variáveis
- [ ] Fluxo funciona em mobile
