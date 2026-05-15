# Portfolio Templates de Capa — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar galeria de 4 templates HTML/CSS de capa no modal "Gerar Portfólio" do COTTE, com tagline sugerida por IA, persistência no banco e renderização server-side no PDF/HTML.

**Architecture:** Dois novos campos em `empresas` (`capa_template_id`, `capa_slogan`) persistidos via endpoints em `/empresa`. O gerador de portfólio (Jinja2 + WeasyPrint) renderiza o template como HTML/CSS puro usando `empresa.cor_primaria` inline. Upload manual e template são mutuamente exclusivos — selecionar um limpa o outro via chamada do frontend.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic (backend), Vanilla JS (frontend), Jinja2 + WeasyPrint (gerador), PostgreSQL.

**Spec:** `docs/superpowers/specs/2026-05-15-portfolio-templates-banner-design.md`

---

## Mapa de Arquivos

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `sistema/app/models/models.py` | Modificar | Adicionar 2 campos à classe `Empresa` |
| `sistema/alembic/versions/z037_add_capa_template_empresas.py` | Criar | Migration Alembic |
| `sistema/app/schemas/schemas.py` | Modificar | `EmpresaOut` + novo `CapaTemplateRequest` |
| `sistema/app/routers/empresa.py` | Modificar | 2 novos endpoints + limpar template no upload |
| `sistema/app/routers/catalogo.py` | Modificar | `_empresa_para_portfolio_dict` + endpoint `sugerir-slogan-ia` |
| `sistema/app/templates/portfolio.html` | Modificar | CSS + 4 blocos de template Jinja2 |
| `sistema/cotte-frontend/catalogo.html` | Modificar | HTML da galeria + funções JS |

---

## Task 1: Model + Migration

**Files:**
- Modify: `sistema/app/models/models.py` (~linha 200)
- Create: `sistema/alembic/versions/z037_add_capa_template_empresas.py`

- [ ] **1.1 Adicionar campos ao model Empresa**

Em `sistema/app/models/models.py`, após a linha `capa_portfolio_url = Column(String(500), nullable=True)`:

```python
capa_template_id = Column(String(30), nullable=True)   # slug: corporativo|clean|impacto|premium
capa_slogan = Column(String(120), nullable=True)        # tagline editada pelo usuário
```

- [ ] **1.2 Gerar migration**

No diretório `sistema/`:
```bash
cd sistema && alembic revision --autogenerate -m "add capa_template_id capa_slogan to empresas"
```

Renomear o arquivo gerado para `z037_add_capa_template_empresas.py` (para manter ordem alfabética com os outros).

- [ ] **1.3 Aplicar migration**

```bash
cd sistema && alembic upgrade head
```

Resultado esperado: `Running upgrade ... -> <rev_id>` sem erros.

- [ ] **1.4 Commit**

```bash
git add sistema/app/models/models.py sistema/alembic/versions/z037_*.py
git commit -m "feat(db): add capa_template_id and capa_slogan to empresas"
```

---

## Task 2: Schemas Pydantic

**Files:**
- Modify: `sistema/app/schemas/schemas.py` (linhas ~961–987 para EmpresaOut; após linha 2327 para novo schema)

- [ ] **2.1 Adicionar campos ao EmpresaOut**

Em `sistema/app/schemas/schemas.py`, dentro de `class EmpresaOut(BaseModel)`, após `capa_portfolio_url: Optional[str] = None` (linha 968):

```python
capa_template_id: Optional[str] = None
capa_slogan: Optional[str] = None
```

- [ ] **2.2 Adicionar CapaTemplateRequest**

Após a classe `PortfolioLinkOut` (após linha 2327):

```python
class CapaTemplateRequest(BaseModel):
    template_id: str
    slogan: str = ""

class SloganIARequest(BaseModel):
    segmento: Optional[str] = None
```

- [ ] **2.3 Commit**

```bash
git add sistema/app/schemas/schemas.py
git commit -m "feat(schema): add capa_template_id, capa_slogan to EmpresaOut; add CapaTemplateRequest"
```

---

## Task 3: Endpoints em /empresa

**Files:**
- Modify: `sistema/app/routers/empresa.py` (após linha 372 — endpoint DELETE /capa-portfolio)

- [ ] **3.1 Importar CapaTemplateRequest**

No topo de `sistema/app/routers/empresa.py`, na linha de imports de schemas, adicionar `CapaTemplateRequest`:

```python
from app.schemas.schemas import (
    ...
    CapaTemplateRequest,
    ...
)
```

- [ ] **3.2 Adicionar POST /capa-template**

Após o endpoint `DELETE /capa-portfolio` (linha ~372):

```python
@router.post("/capa-template", response_model=EmpresaOut)
def salvar_capa_template(
    req: CapaTemplateRequest,
    usuario: Usuario = Depends(exigir_permissao("configuracoes", "escrita")),
    db: Session = Depends(get_db),
):
    """Salva o template de capa escolhido e a tagline editada."""
    SLUGS_VALIDOS = {"corporativo", "clean", "impacto", "premium"}
    if req.template_id not in SLUGS_VALIDOS:
        raise HTTPException(status_code=422, detail=f"template_id inválido: {req.template_id}")
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    empresa.capa_template_id = req.template_id
    empresa.capa_slogan = (req.slogan or "").strip()[:120]
    db.commit()
    db.refresh(empresa)
    return empresa


@router.delete("/capa-template", response_model=EmpresaOut)
def remover_capa_template(
    usuario: Usuario = Depends(exigir_permissao("configuracoes", "escrita")),
    db: Session = Depends(get_db),
):
    """Remove o template de capa ativo."""
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    empresa.capa_template_id = None
    empresa.capa_slogan = None
    db.commit()
    db.refresh(empresa)
    return empresa
```

- [ ] **3.3 Limpar template quando imagem é enviada**

No endpoint `POST /capa-portfolio` (linha ~328), após salvar `file_url` e antes de `db.commit()`:

```python
empresa.capa_portfolio_url = file_url
empresa.capa_template_id = None   # upload substitui template
empresa.capa_slogan = None
db.commit()
```

- [ ] **3.4 Commit**

```bash
git add sistema/app/routers/empresa.py
git commit -m "feat(empresa): add POST/DELETE /capa-template endpoints"
```

---

## Task 4: Endpoint sugerir-slogan-ia + _empresa_para_portfolio_dict

**Files:**
- Modify: `sistema/app/routers/catalogo.py`

- [ ] **4.1 Importar SloganIARequest**

No topo de `sistema/app/routers/catalogo.py`, na linha de imports de schemas:

```python
from app.schemas.schemas import (
    ...
    SloganIARequest,
    ...
)
```

- [ ] **4.2 Atualizar _empresa_para_portfolio_dict**

Em `sistema/app/routers/catalogo.py`, função `_empresa_para_portfolio_dict` (linha ~700), adicionar ao dict retornado:

```python
def _empresa_para_portfolio_dict(empresa: Empresa) -> dict:
    endereco_partes = [
        (empresa.endereco_logradouro or "").strip(),
        (empresa.endereco_numero or "").strip(),
        (empresa.endereco_bairro or "").strip(),
        (empresa.endereco_cidade or "").strip(),
        (empresa.endereco_uf or "").strip(),
    ]
    endereco = ", ".join([p for p in endereco_partes if p])
    return {
        "nome": empresa.nome,
        "logo_url": empresa.logo_url,
        "capa_portfolio_url": getattr(empresa, "capa_portfolio_url", None),
        "capa_template_id": getattr(empresa, "capa_template_id", None),
        "capa_slogan": getattr(empresa, "capa_slogan", None) or "",
        "cor_primaria": getattr(empresa, "cor_primaria", None) or "#00e5a0",
        "telefone": empresa.telefone,
        "email": empresa.email,
        "descricao_publica_empresa": empresa.descricao_publica_empresa,
        "endereco_apresentacao": endereco or None,
    }
```

- [ ] **4.3 Adicionar endpoint sugerir-slogan-ia**

Após o endpoint `sugerir_descricao_ia` (linha ~899):

```python
@router.post("/portfolio/sugerir-slogan-ia")
def sugerir_slogan_ia(
    req: SloganIARequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_permissao("catalogo", "leitura")),
):
    """Gera uma tagline curta (1 linha, máx 80 chars) para o banner de capa."""
    empresa = usuario.empresa
    segmento = (req.segmento or "").strip() or "não informado"
    nome = empresa.nome or "Empresa"
    descricao = (empresa.descricao_publica_empresa or "").strip()

    prompt = (
        "Crie uma tagline comercial curta para o banner de capa de um portfólio de produtos. "
        f"Empresa: {nome}. Segmento: {segmento}. "
        f"{'Descrição: ' + descricao + '. ' if descricao else ''}"
        "Regras: máximo 80 caracteres, português do Brasil, sem emoji, "
        "sem aspas, sem ponto final obrigatório, tom profissional e direto. "
        "Retorne APENAS a tagline, sem explicações."
    )

    try:
        resp = ia_service.chat_sync(messages=[{"role": "user", "content": prompt}])
        slogan = (resp.get("content", "") if isinstance(resp, dict) else "").strip()
        slogan = slogan.strip('"\'').strip()[:80]
    except Exception:
        slogan = ""

    if not slogan:
        slogan = f"{nome} — qualidade e confiança."

    return {"slogan": slogan}
```

- [ ] **4.4 Commit**

```bash
git add sistema/app/routers/catalogo.py
git commit -m "feat(catalogo): add sugerir-slogan-ia endpoint; expose capa_template in portfolio dict"
```

---

## Task 5: Template Jinja2 — portfolio.html

**Files:**
- Modify: `sistema/app/templates/portfolio.html` (linhas ~126–145 CSS; linhas ~492–496 HTML)

- [ ] **5.1 Adicionar CSS dos templates de banner**

Em `sistema/app/templates/portfolio.html`, após o bloco `.cover-banner img { @media print ... }` (após linha ~145), adicionar:

```css
/* ── Templates de capa HTML/CSS ── */
.cover-template {
    width: 100%;
    height: 180px;
    display: flex;
    align-items: center;
    overflow: hidden;
    position: relative;
}

/* Corporativo */
.cover-template-corporativo {
    background: linear-gradient(135deg, #0f172a 55%, #1e3a5f 100%);
    padding: 0 32px;
    gap: 18px;
}
.cover-template-corporativo .ct-initial {
    width: 48px; height: 48px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 900; font-size: 22px; color: #0f172a;
    flex-shrink: 0;
}
.cover-template-corporativo .ct-nome {
    color: #fff; font-weight: 700; font-size: 18px; margin-bottom: 4px;
}
.cover-template-corporativo .ct-slogan {
    font-size: 13px; font-style: italic;
}
.cover-template-corporativo .ct-label {
    color: rgba(255,255,255,0.35); font-size: 10px;
    letter-spacing: 2px; text-transform: uppercase;
}

/* Clean */
.cover-template-clean {
    background: #ffffff;
    border-left: 8px solid;
    padding: 0 28px;
    gap: 18px;
}
.cover-template-clean .ct-circle {
    width: 52px; height: 52px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 22px; color: #fff;
    flex-shrink: 0;
}
.cover-template-clean .ct-nome {
    color: #0f172a; font-weight: 700; font-size: 18px; margin-bottom: 4px;
}
.cover-template-clean .ct-slogan { color: #475569; font-size: 13px; }
.cover-template-clean .ct-badges {
    display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap;
}
.cover-template-clean .ct-badge {
    font-size: 11px; font-weight: 600; padding: 3px 10px;
    border-radius: 20px;
}

/* Impacto */
.cover-template-impacto {
    padding: 0 36px;
    position: relative; overflow: hidden;
}
.cover-template-impacto::before {
    content: ''; position: absolute;
    right: -30px; bottom: -30px;
    width: 160px; height: 160px;
    border-radius: 50%; background: rgba(255,255,255,0.08);
}
.cover-template-impacto .ct-nome {
    color: #fff; font-weight: 900; font-size: 24px;
    letter-spacing: -0.5px; margin-bottom: 8px;
    text-shadow: 0 2px 8px rgba(0,0,0,0.25);
}
.cover-template-impacto .ct-slogan {
    color: rgba(255,255,255,0.88); font-size: 13px;
}
.cover-template-impacto .ct-line {
    width: 50px; height: 3px; border-radius: 2px;
    background: rgba(255,255,255,0.5); margin-top: 14px;
}

/* Premium */
.cover-template-premium {
    background: #1c1917; padding: 0 32px; gap: 0;
}
.cover-template-premium::before {
    content: '';
    position: absolute; inset: 0;
    background: repeating-linear-gradient(
        45deg,
        rgba(255,255,255,0.015) 0px, rgba(255,255,255,0.015) 1px,
        transparent 1px, transparent 12px
    );
}
.cover-template-premium .ct-divider {
    padding-right: 24px; margin-right: 24px;
    border-right: 1px solid; display: flex; flex-direction: column;
    align-items: center; justify-content: center; position: relative; z-index: 1;
}
.cover-template-premium .ct-initials {
    font-size: 28px; font-weight: 900; letter-spacing: -1px; line-height: 1;
}
.cover-template-premium .ct-since {
    font-size: 9px; letter-spacing: 3px; text-transform: uppercase;
    opacity: 0.4; color: #fff; margin-top: 4px;
}
.cover-template-premium .ct-info { position: relative; z-index: 1; }
.cover-template-premium .ct-label {
    font-size: 9px; letter-spacing: 3px; text-transform: uppercase;
    color: rgba(255,255,255,0.35); margin-bottom: 6px;
}
.cover-template-premium .ct-nome {
    color: #fff; font-weight: 700; font-size: 16px; letter-spacing: 0.5px;
}
.cover-template-premium .ct-slogan { font-size: 12px; font-style: italic; margin-top: 4px; }
```

- [ ] **5.2 Substituir bloco capa_portfolio_url no HTML do template**

Em `sistema/app/templates/portfolio.html`, substituir as linhas 492–496:

**Remover:**
```jinja2
{% if empresa.capa_portfolio_url %}
<div class="cover-banner" aria-hidden="true">
    <img src="{{ empresa.capa_portfolio_url }}" alt="">
</div>
{% endif %}
```

**Inserir:**
```jinja2
{% if empresa.capa_template_id %}
<div class="cover-banner cover-template cover-template-{{ empresa.capa_template_id }}" aria-hidden="true"
     {% if empresa.capa_template_id == 'impacto' %}
     style="background:linear-gradient(120deg,{{ empresa.cor_primaria }},{{ empresa.cor_primaria }}99)"
     {% elif empresa.capa_template_id == 'clean' %}
     style="border-left-color:{{ empresa.cor_primaria }}"
     {% endif %}>
  {% set inicial = empresa.nome[0] | upper %}
  {% set cor = empresa.cor_primaria or '#00e5a0' %}

  {% if empresa.capa_template_id == 'corporativo' %}
    <div class="ct-initial" style="background:{{ cor }}">{{ inicial }}</div>
    <div>
      <div class="ct-nome">{{ empresa.nome }}</div>
      <div class="ct-slogan" style="color:{{ cor }}">{{ empresa.capa_slogan }}</div>
      {% if empresa.endereco_apresentacao %}
      <div class="ct-label" style="margin-top:8px">{{ empresa.endereco_apresentacao }}</div>
      {% endif %}
    </div>
    <div style="margin-left:auto;text-align:right;opacity:0.35">
      <div style="color:#fff;font-size:9px;letter-spacing:2px;text-transform:uppercase">Portfólio</div>
    </div>

  {% elif empresa.capa_template_id == 'clean' %}
    <div class="ct-circle" style="background:{{ cor }}">{{ inicial }}</div>
    <div>
      <div class="ct-nome">{{ empresa.nome }}</div>
      <div class="ct-slogan">{{ empresa.capa_slogan }}</div>
      <div class="ct-badges">
        <span class="ct-badge" style="background:{{ cor }}22;color:{{ cor }}">✓ Qualidade</span>
        <span class="ct-badge" style="background:{{ cor }}22;color:{{ cor }}">✓ Agilidade</span>
        <span class="ct-badge" style="background:{{ cor }}22;color:{{ cor }}">✓ Confiança</span>
      </div>
    </div>

  {% elif empresa.capa_template_id == 'impacto' %}
    <div>
      <div class="ct-nome">{{ empresa.nome }}</div>
      <div class="ct-slogan">{{ empresa.capa_slogan }}</div>
      <div class="ct-line"></div>
    </div>

  {% elif empresa.capa_template_id == 'premium' %}
    <div class="ct-divider" style="border-right-color:{{ cor }}">
      <div class="ct-initials" style="color:{{ cor }}">
        {{ empresa.nome[:2] | upper }}
      </div>
    </div>
    <div class="ct-info">
      <div class="ct-label">Portfólio de Produtos</div>
      <div class="ct-nome">{{ empresa.nome }}</div>
      <div class="ct-slogan" style="color:{{ cor }}">{{ empresa.capa_slogan }}</div>
    </div>
  {% endif %}
</div>

{% elif empresa.capa_portfolio_url %}
<div class="cover-banner" aria-hidden="true">
    <img src="{{ empresa.capa_portfolio_url }}" alt="">
</div>
{% endif %}
```

- [ ] **5.3 Commit**

```bash
git add sistema/app/templates/portfolio.html
git commit -m "feat(template): render 4 HTML/CSS banner templates in portfolio PDF/HTML"
```

---

## Task 6: Frontend — HTML da galeria em catalogo.html

**Files:**
- Modify: `sistema/cotte-frontend/catalogo.html` — seção "2. Imagem de capa (opcional)"

A seção atual termina com `<div id="portfolio-capa-status" ...></div>`.

- [ ] **6.1 Adicionar estrutura da galeria**

Após `<div id="portfolio-capa-status" ...></div>`, antes do `</div>` que fecha a `.portfolio-section`:

```html
      <!-- Divider upload / templates -->
      <div id="portfolio-capa-divider" style="display:flex;align-items:center;gap:8px;margin:10px 0">
        <div style="flex:1;height:1px;background:var(--border)"></div>
        <span style="font-size:11px;color:var(--muted)">ou escolha um template</span>
        <div style="flex:1;height:1px;background:var(--border)"></div>
      </div>

      <!-- Grid 2×2 dos templates (renderizado por JS) -->
      <div id="portfolio-templates-gallery" style="display:grid;grid-template-columns:1fr 1fr;gap:8px"></div>

      <!-- Seção template ativo (oculta por padrão) -->
      <div id="portfolio-template-ativo" style="display:none;margin-top:10px">
        <div id="portfolio-template-preview" style="border-radius:8px;overflow:hidden;margin-bottom:8px;border:1.5px solid var(--success, #22c55e)"></div>
        <div style="margin-bottom:8px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
            <span style="font-size:12px;color:var(--muted)">Tagline</span>
            <button type="button" id="btn-sugerir-slogan-ia" onclick="sugerirSloganIA()"
                    style="background:none;border:none;color:var(--primary,#818cf8);font-size:11px;cursor:pointer;padding:0">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:3px;vertical-align:middle"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
              Sugerir com IA
            </button>
          </div>
          <input type="text" id="portfolio-template-slogan" maxlength="120"
                 placeholder="Uma frase sobre a empresa..."
                 oninput="atualizarPreviewTemplateLive()"
                 style="width:100%;padding:8px 10px;background:var(--surface2);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:13px">
        </div>
        <div style="display:flex;gap:6px">
          <button type="button" onclick="trocarTemplateGaleria()"
                  style="flex:1;padding:6px 10px;background:var(--surface2);border:1px solid var(--border);border-radius:6px;font-size:12px;color:var(--muted);cursor:pointer">
            Trocar template
          </button>
          <button type="button" id="btn-salvar-template" onclick="salvarTemplate()"
                  style="flex:1;padding:6px 10px;background:var(--primary,#4f46e5);border:none;border-radius:6px;font-size:12px;color:#fff;font-weight:600;cursor:pointer">
            Salvar
          </button>
          <button type="button" onclick="removerTemplate()" title="Remover template"
                  style="padding:6px 10px;background:var(--surface2);border:1px solid var(--border);border-radius:6px;font-size:12px;color:var(--danger,#ef4444);cursor:pointer">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
      </div>

      <!-- Upload como alternativa (visível apenas quando template ativo) -->
      <div id="portfolio-upload-alt" style="display:none;margin-top:8px">
        <div onclick="document.getElementById('portfolio-input-capa').click()"
             style="border:1px dashed var(--border);border-radius:6px;padding:8px;text-align:center;font-size:11px;color:var(--muted);cursor:pointer;transition:border-color .15s">
          Ou enviar imagem própria (substitui o template)
        </div>
      </div>
```

- [ ] **6.2 Adicionar CSS de hover nos cards da galeria**

Dentro do `<style>` do `catalogo.html` (ou em bloco inline antes do `</head>`):

```css
.portfolio-template-card {
  border: 1.5px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: border-color .15s, transform .15s;
}
.portfolio-template-card:hover {
  border-color: var(--primary, #4f46e5);
  transform: translateY(-1px);
}
.portfolio-template-card.is-active {
  border-color: var(--success, #22c55e);
}
.portfolio-template-card-label {
  padding: 4px 8px;
  background: var(--surface2);
  font-size: 11px;
  color: var(--muted);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.portfolio-template-card.is-active .portfolio-template-card-label {
  color: var(--success, #22c55e);
}
```

- [ ] **6.3 Commit**

```bash
git add sistema/cotte-frontend/catalogo.html
git commit -m "feat(catalogo): add gallery HTML structure and CSS to portfolio modal cover section"
```

---

## Task 7: Frontend — Funções JS em catalogo.html

**Files:**
- Modify: `sistema/cotte-frontend/catalogo.html` — bloco `<script>` interno

Adicionar as funções abaixo no `<script>` do `catalogo.html`, próximo das funções existentes de capa (`uploadCapaPortfolioModal`, `removerCapaPortfolioModal`, etc.).

- [ ] **7.1 Variável de estado do template selecionado**

No topo do bloco `<script>` (junto com outras variáveis globais como `portfolioEmpresaCache`):

```javascript
let portfolioTemplateSelecionado = null; // { id, jaPersistido }
```

- [ ] **7.2 Função _renderTemplateMiniHTML (helper interno)**

```javascript
function _renderTemplateMiniHTML(templateId, nome, slogan, cor) {
  const ini = (nome || 'E')[0].toUpperCase();
  const ini2 = (nome || 'EM').substring(0, 2).toUpperCase();
  const cor2 = cor || '#00e5a0';

  if (templateId === 'corporativo') {
    return `
      <div style="background:linear-gradient(135deg,#0f172a 55%,#1e3a5f);height:64px;display:flex;align-items:center;padding:0 12px;gap:10px;overflow:hidden">
        <div style="width:28px;height:28px;border-radius:5px;background:${cor2};display:flex;align-items:center;justify-content:center;font-weight:900;font-size:13px;color:#0f172a;flex-shrink:0">${ini}</div>
        <div style="min-width:0">
          <div style="color:#fff;font-size:11px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${nome}</div>
          <div style="color:${cor2};font-size:9px;font-style:italic;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${slogan || 'Tagline aparece aqui'}</div>
        </div>
      </div>`;
  }
  if (templateId === 'clean') {
    return `
      <div style="background:#fff;height:64px;display:flex;align-items:stretch;overflow:hidden">
        <div style="width:5px;background:${cor2};flex-shrink:0"></div>
        <div style="padding:8px 10px;display:flex;align-items:center;gap:8px">
          <div style="width:28px;height:28px;border-radius:50%;background:${cor2};display:flex;align-items:center;justify-content:center;font-weight:800;font-size:12px;color:#fff;flex-shrink:0">${ini}</div>
          <div style="min-width:0">
            <div style="color:#0f172a;font-size:11px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${nome}</div>
            <div style="color:#64748b;font-size:9px;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${slogan || 'Tagline aparece aqui'}</div>
          </div>
        </div>
      </div>`;
  }
  if (templateId === 'impacto') {
    return `
      <div style="background:linear-gradient(120deg,${cor2},${cor2}99);height:64px;display:flex;align-items:center;padding:0 12px;overflow:hidden;position:relative">
        <div style="position:absolute;right:-10px;bottom:-10px;width:60px;height:60px;border-radius:50%;background:rgba(255,255,255,0.1)"></div>
        <div style="min-width:0">
          <div style="color:#fff;font-weight:900;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${nome}</div>
          <div style="color:rgba(255,255,255,0.85);font-size:9px;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${slogan || 'Tagline aparece aqui'}</div>
        </div>
      </div>`;
  }
  if (templateId === 'premium') {
    return `
      <div style="background:#1c1917;height:64px;display:flex;align-items:center;padding:0 10px;gap:0;overflow:hidden">
        <div style="border-right:1px solid ${cor2};padding-right:10px;margin-right:10px;flex-shrink:0">
          <div style="color:${cor2};font-size:14px;font-weight:900;letter-spacing:-1px">${ini2}</div>
        </div>
        <div style="min-width:0">
          <div style="color:#fff;font-size:11px;font-weight:700;letter-spacing:0.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${nome}</div>
          <div style="color:${cor2};font-size:9px;font-style:italic;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${slogan || 'Tagline aparece aqui'}</div>
        </div>
      </div>`;
  }
  return '';
}
```

- [ ] **7.3 Função _renderTemplatePreviewGrande (helper interno)**

```javascript
function _renderTemplatePreviewGrande(templateId, nome, slogan, cor) {
  const ini = (nome || 'E')[0].toUpperCase();
  const ini2 = (nome || 'EM').substring(0, 2).toUpperCase();
  const cor2 = cor || '#00e5a0';

  if (templateId === 'corporativo') {
    return `
      <div style="background:linear-gradient(135deg,#0f172a 55%,#1e3a5f);height:100px;display:flex;align-items:center;padding:0 20px;gap:14px;position:relative;overflow:hidden">
        <div style="position:absolute;right:-12px;top:-12px;width:100px;height:100px;border-radius:50%;background:rgba(255,255,255,0.06)"></div>
        <div style="width:40px;height:40px;border-radius:8px;background:${cor2};display:flex;align-items:center;justify-content:center;font-weight:900;font-size:18px;color:#0f172a;flex-shrink:0">${ini}</div>
        <div>
          <div style="color:#fff;font-size:15px;font-weight:700">${nome}</div>
          <div style="color:${cor2};font-size:11px;font-style:italic;margin-top:3px">${slogan || ''}</div>
        </div>
        <div style="margin-left:auto;text-align:right;opacity:0.3">
          <div style="color:#fff;font-size:9px;letter-spacing:2px;text-transform:uppercase">Portfólio</div>
        </div>
      </div>`;
  }
  if (templateId === 'clean') {
    return `
      <div style="background:#fff;height:100px;display:flex;align-items:stretch;overflow:hidden">
        <div style="width:6px;background:${cor2};flex-shrink:0"></div>
        <div style="padding:12px 16px;display:flex;align-items:center;gap:14px">
          <div style="width:44px;height:44px;border-radius:50%;background:${cor2};display:flex;align-items:center;justify-content:center;font-weight:800;font-size:18px;color:#fff;flex-shrink:0">${ini}</div>
          <div>
            <div style="color:#0f172a;font-size:15px;font-weight:700">${nome}</div>
            <div style="color:#64748b;font-size:11px;margin-top:3px">${slogan || ''}</div>
            <div style="display:flex;gap:8px;margin-top:8px">
              <span style="background:${cor2}22;color:${cor2};font-size:9px;font-weight:600;padding:2px 8px;border-radius:20px">✓ Qualidade</span>
              <span style="background:${cor2}22;color:${cor2};font-size:9px;font-weight:600;padding:2px 8px;border-radius:20px">✓ Agilidade</span>
            </div>
          </div>
        </div>
      </div>`;
  }
  if (templateId === 'impacto') {
    return `
      <div style="background:linear-gradient(120deg,${cor2},${cor2}99);height:100px;display:flex;align-items:center;padding:0 24px;overflow:hidden;position:relative">
        <div style="position:absolute;right:-20px;bottom:-20px;width:120px;height:120px;border-radius:50%;background:rgba(255,255,255,0.08)"></div>
        <div>
          <div style="color:#fff;font-weight:900;font-size:20px;letter-spacing:-0.5px;text-shadow:0 2px 6px rgba(0,0,0,0.2)">${nome}</div>
          <div style="color:rgba(255,255,255,0.88);font-size:12px;margin-top:5px">${slogan || ''}</div>
          <div style="width:40px;height:2px;border-radius:2px;background:rgba(255,255,255,0.45);margin-top:10px"></div>
        </div>
      </div>`;
  }
  if (templateId === 'premium') {
    return `
      <div style="background:#1c1917;height:100px;display:flex;align-items:center;padding:0 24px;gap:0;overflow:hidden;position:relative">
        <div style="position:absolute;inset:0;background:repeating-linear-gradient(45deg,rgba(255,255,255,0.015) 0px,rgba(255,255,255,0.015) 1px,transparent 1px,transparent 12px)"></div>
        <div style="border-right:1px solid ${cor2};padding-right:18px;margin-right:18px;text-align:center;flex-shrink:0;position:relative;z-index:1">
          <div style="color:${cor2};font-size:22px;font-weight:900;letter-spacing:-1px">${ini2}</div>
        </div>
        <div style="position:relative;z-index:1">
          <div style="color:rgba(255,255,255,0.35);font-size:9px;letter-spacing:3px;text-transform:uppercase;margin-bottom:5px">Portfólio</div>
          <div style="color:#fff;font-weight:700;font-size:14px;letter-spacing:0.5px">${nome}</div>
          <div style="color:${cor2};font-size:11px;font-style:italic;margin-top:3px">${slogan || ''}</div>
        </div>
      </div>`;
  }
  return '';
}
```

- [ ] **7.4 Função renderGaleriaTemplates**

```javascript
function renderGaleriaTemplates(empresa) {
  const container = document.getElementById('portfolio-templates-gallery');
  if (!container) return;
  const nome = empresa.nome || 'Empresa';
  const cor = empresa.cor_primaria || '#00e5a0';
  const ativo = empresa.capa_template_id || null;
  const templates = [
    { id: 'corporativo', label: 'Corporativo' },
    { id: 'clean',       label: 'Clean' },
    { id: 'impacto',     label: 'Impacto' },
    { id: 'premium',     label: 'Premium' },
  ];
  const sloganAtivo = empresa.capa_slogan || '';
  container.innerHTML = templates.map(t => {
    const isAtivo = ativo === t.id;
    const sloganArg = isAtivo ? sloganAtivo.replace(/'/g, "\\'") : '';
    return `
    <div class="portfolio-template-card${isAtivo ? ' is-active' : ''}"
         data-template-id="${t.id}"
         onclick="selecionarTemplate('${t.id}', '${sloganArg}', ${isAtivo})"
         style="cursor:pointer">
      ${_renderTemplateMiniHTML(t.id, nome, isAtivo ? sloganAtivo : '', cor)}
      <div class="portfolio-template-card-label">
        <span>${t.label}</span>
        ${isAtivo ? '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>' : ''}
      </div>
    </div>
  `}).join('');
}
```

- [ ] **7.5 Função selecionarTemplate**

```javascript
function selecionarTemplate(templateId, slogan, jaPersistido) {
  const empresa = portfolioEmpresaCache;
  const nome = empresa ? (empresa.nome || 'Empresa') : 'Empresa';
  const cor = empresa ? (empresa.cor_primaria || '#00e5a0') : '#00e5a0';

  // Marca card ativo
  document.querySelectorAll('.portfolio-template-card').forEach(el => {
    el.classList.toggle('is-active', el.dataset.templateId === templateId);
    const lbl = el.querySelector('.portfolio-template-card-label span');
    // rebuild label badge
  });

  portfolioTemplateSelecionado = { id: templateId, jaPersistido };

  // Preenche campo de tagline
  const inputSlogan = document.getElementById('portfolio-template-slogan');
  if (inputSlogan) inputSlogan.value = slogan || '';

  // Atualiza preview grande
  const preview = document.getElementById('portfolio-template-preview');
  if (preview) preview.innerHTML = _renderTemplatePreviewGrande(templateId, nome, slogan || '', cor);

  // Mostra seção template-ativo e esconde upload principal
  document.getElementById('portfolio-template-ativo').style.display = 'block';
  document.getElementById('portfolio-upload-alt').style.display = 'block';
  document.getElementById('portfolio-capa-preview-wrap').style.display = 'none';
  document.getElementById('portfolio-capa-status').style.display = 'none';
  const divider = document.getElementById('portfolio-capa-divider');
  if (divider) divider.style.display = 'none';
}
```

- [ ] **7.6 Função atualizarPreviewTemplateLive**

```javascript
function atualizarPreviewTemplateLive() {
  if (!portfolioTemplateSelecionado) return;
  const slogan = (document.getElementById('portfolio-template-slogan')?.value || '');
  const empresa = portfolioEmpresaCache;
  const nome = empresa ? (empresa.nome || 'Empresa') : 'Empresa';
  const cor = empresa ? (empresa.cor_primaria || '#00e5a0') : '#00e5a0';
  const preview = document.getElementById('portfolio-template-preview');
  if (preview) preview.innerHTML = _renderTemplatePreviewGrande(portfolioTemplateSelecionado.id, nome, slogan, cor);
}
```

- [ ] **7.7 Função trocarTemplateGaleria**

```javascript
function trocarTemplateGaleria() {
  document.getElementById('portfolio-template-ativo').style.display = 'none';
  document.getElementById('portfolio-upload-alt').style.display = 'none';
  document.getElementById('portfolio-capa-preview-wrap').style.display = 'flex';
  document.getElementById('portfolio-capa-status').style.display = 'block';
  const divider = document.getElementById('portfolio-capa-divider');
  if (divider) divider.style.display = 'flex';
  portfolioTemplateSelecionado = null;
  // Re-renderiza galeria sem card ativo destacado
  const empresaSemTemplate = Object.assign({}, portfolioEmpresaCache, { capa_template_id: null, capa_slogan: null });
  renderGaleriaTemplates(empresaSemTemplate);
}
```

- [ ] **7.8 Função sugerirSloganIA**

```javascript
async function sugerirSloganIA() {
  const btn = document.getElementById('btn-sugerir-slogan-ia');
  const oldText = btn ? btn.innerHTML : '';
  if (btn) { btn.disabled = true; btn.textContent = 'Gerando...'; }
  try {
    const segmento = document.getElementById('portfolio-segmento')?.value || '';
    const resp = await api.post('/catalogo/portfolio/sugerir-slogan-ia', { segmento });
    if (resp && resp.slogan) {
      const input = document.getElementById('portfolio-template-slogan');
      if (input) { input.value = resp.slogan; atualizarPreviewTemplateLive(); }
    }
  } catch (err) {
    showNotif('❌', 'Erro', err.message, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = oldText; }
  }
}
```

- [ ] **7.9 Função salvarTemplate**

```javascript
async function salvarTemplate() {
  if (!portfolioTemplateSelecionado) return;
  const btn = document.getElementById('btn-salvar-template');
  const slogan = (document.getElementById('portfolio-template-slogan')?.value || '').trim();
  setLoading(btn, true);
  try {
    // Limpa upload se existir
    if (portfolioEmpresaCache && portfolioEmpresaCache.capa_portfolio_url) {
      await api.delete('/empresa/capa-portfolio');
    }
    const data = await api.post('/empresa/capa-template', {
      template_id: portfolioTemplateSelecionado.id,
      slogan,
    });
    portfolioEmpresaCache = null; // força reload
    portfolioTemplateSelecionado = { ...portfolioTemplateSelecionado, jaPersistido: true };
    // Atualiza preview com slogan salvo
    const empresa = data;
    if (empresa && empresa.capa_template_id) {
      const preview = document.getElementById('portfolio-template-preview');
      if (preview) preview.innerHTML = _renderTemplatePreviewGrande(
        empresa.capa_template_id,
        empresa.nome || 'Empresa',
        empresa.capa_slogan || '',
        empresa.cor_primaria || '#00e5a0'
      );
    }
    showNotif('✅', 'Template salvo', 'Aparecerá no portfólio gerado.');
  } catch (err) {
    showNotif('❌', 'Erro', err.message, 'error');
  } finally {
    setLoading(btn, false, 'Salvar');
  }
}
```

- [ ] **7.10 Função removerTemplate**

```javascript
async function removerTemplate() {
  try {
    await api.delete('/empresa/capa-template');
    portfolioEmpresaCache = null;
    portfolioTemplateSelecionado = null;
    // Volta ao estado padrão
    ocultarCapaPortfolioModal();
    document.getElementById('portfolio-template-ativo').style.display = 'none';
    document.getElementById('portfolio-upload-alt').style.display = 'none';
    document.getElementById('portfolio-capa-preview-wrap').style.display = 'flex';
    document.getElementById('portfolio-capa-status').style.display = 'block';
    const divider = document.getElementById('portfolio-capa-divider');
    if (divider) divider.style.display = 'flex';
    // Re-renderiza galeria sem seleção ativa
    const empresa = await carregarDadosEmpresaPortfolio(true);
    renderGaleriaTemplates(empresa || { nome: '', cor_primaria: '#00e5a0' });
    showNotif('✅', 'Template removido', 'O portfólio usará layout padrão.');
  } catch (err) {
    showNotif('❌', 'Erro', err.message, 'error');
  }
}
```

- [ ] **7.11 Atualizar abrirModalPortfolio**

Substituir o bloco `.then((empresa) => { ... })` existente em `abrirModalPortfolio`:

```javascript
carregarDadosEmpresaPortfolio()
  .then((empresa) => {
    if (!document.getElementById('portfolio-descricao').value.trim() && empresa && empresa.descricao_publica_empresa) {
      document.getElementById('portfolio-descricao').value = empresa.descricao_publica_empresa.trim();
    }
    if (empresa && empresa.capa_template_id) {
      // Template ativo — renderiza galeria e seleciona
      renderGaleriaTemplates(empresa);
      selecionarTemplate(empresa.capa_template_id, empresa.capa_slogan || '', true);
    } else if (empresa && empresa.capa_portfolio_url) {
      // Imagem uploadada
      mostrarCapaPortfolioModal(empresa.capa_portfolio_url);
      renderGaleriaTemplates(empresa || { nome: '', cor_primaria: '#00e5a0' });
    } else {
      // Nenhuma capa
      ocultarCapaPortfolioModal();
      renderGaleriaTemplates(empresa || { nome: '', cor_primaria: '#00e5a0' });
    }
  })
  .catch(() => {
    renderPreviewEmpresaPortfolio(null);
    ocultarCapaPortfolioModal();
  });
```

- [ ] **7.12 Atualizar uploadCapaPortfolioModal para limpar template**

Na função `uploadCapaPortfolioModal`, após o upload bem-sucedido (`mostrarCapaPortfolioModal(data.capa_portfolio_url)`):

```javascript
// Limpa estado de template
portfolioTemplateSelecionado = null;
portfolioEmpresaCache = null;
document.getElementById('portfolio-template-ativo').style.display = 'none';
document.getElementById('portfolio-upload-alt').style.display = 'none';
document.getElementById('portfolio-capa-preview-wrap').style.display = 'flex';
const divider = document.getElementById('portfolio-capa-divider');
if (divider) divider.style.display = 'flex';
```

- [ ] **7.13 Commit**

```bash
git add sistema/cotte-frontend/catalogo.html
git commit -m "feat(catalogo): add portfolio banner template gallery with AI slogan suggestion"
```

---

## Verificação Final

- [ ] Abrir modal "Gerar Portfólio" sem nenhuma capa → galeria com 4 cards visível
- [ ] Clicar "Clean" → preview grande aparece com nome da empresa; campo tagline vazio
- [ ] Clicar "Sugerir com IA" → campo preenchido com 1 frase
- [ ] Editar tagline manualmente → preview atualiza em tempo real
- [ ] "Salvar" → notificação de sucesso; fechar e reabrir modal → "Clean" ainda selecionado
- [ ] "Baixar PDF" → PDF tem banner Clean no topo com o nome e tagline da empresa
- [ ] "Visualizar HTML" → mesmo banner no HTML
- [ ] Selecionar template quando havia imagem uploaded → imagem removida, template ativo
- [ ] Upload de imagem quando template ativo → template desmarcado, galeria volta ao padrão
- [ ] "✕" → template removido, galeria em estado padrão
- [ ] Testar todos os 4 templates no PDF com temas diferentes (classico, escuro, corporativo)
