# Design Spec: Templates de Capa para Portfólio

**Data:** 2026-05-15  
**Status:** Aprovado  
**Contexto:** O COTTE serve múltiplas empresas (distribuidoras, varejo, indústria) que geram portfólios de produtos para apresentar a clientes. O upload manual de imagem de capa já existe; este feature adiciona uma galeria de 4 templates HTML/CSS pré-desenhados com IA para empresas que não têm imagem própria.

---

## Escopo

- Galeria de 4 templates de banner inline na seção "2. Imagem de capa" do modal "Gerar Portfólio" (`catalogo.html`)
- IA sugere tagline (1 linha) usando dados da empresa; usuário pode editar
- Seleção persiste no banco (`capa_template_id` + `capa_slogan`)
- Upload manual e template são **mutuamente exclusivos** — selecionar um limpa o outro
- Portfólio gerado (HTML + PDF via WeasyPrint) renderiza o template como HTML/CSS puro

---

## Banco de Dados

**Tabela `empresas` — 2 novos campos:**

| Campo | Tipo | Default | Descrição |
|---|---|---|---|
| `capa_template_id` | `String(30)`, nullable | `None` | Slug do template ativo: `corporativo`, `clean`, `impacto`, `premium` |
| `capa_slogan` | `String(120)`, nullable | `None` | Tagline editada pelo usuário |

**Migration:** `alembic revision --autogenerate -m "add capa_template_id capa_slogan to empresas"`

---

## Backend

### Novos endpoints em `/empresa`

**`POST /empresa/capa-template`**  
- Body: `{ template_id: str, slogan: str }`  
- Salva `capa_template_id` e `capa_slogan` na empresa  
- **Não** apaga `capa_portfolio_url` — o frontend chama `DELETE /empresa/capa-portfolio` primeiro **somente se** `empresa.capa_portfolio_url != null`  
- Permissão: `configuracoes.escrita`  
- Retorna: `EmpresaOut`

**`DELETE /empresa/capa-template`**  
- Zera `capa_template_id` e `capa_slogan`  
- Permissão: `configuracoes.escrita`  
- Retorna: `EmpresaOut`

### Novo endpoint em `/catalogo/portfolio`

**`POST /catalogo/portfolio/sugerir-slogan-ia`**  
- Body: `{ segmento?: str }`  
- Usa `ia_service.chat_sync` com prompt: nome + descrição + segmento da empresa  
- Retorna: `{ slogan: str }` — 1 frase, máx 80 chars, português, sem emoji  
- Fallback se IA falhar: `"{empresa.nome} — qualidade e confiança."` 
- Permissão: `catalogo.leitura`

### Mudanças em arquivos existentes

**`app/routers/empresa.py`** — adicionar os 2 endpoints acima.

**`app/routers/catalogo.py` — `_empresa_para_portfolio_dict`**  
Adicionar ao dict retornado:
```python
"capa_template_id": empresa.capa_template_id,
"capa_slogan": empresa.capa_slogan or "",
```

**`app/schemas/empresa.py` (ou onde estiver `EmpresaOut`)**  
Adicionar:
```python
capa_template_id: Optional[str] = None
capa_slogan: Optional[str] = None
```

---

## Templates de Banner (HTML/CSS)

4 designs, todos usando variáveis já existentes no CSS do portfólio (`var(--accent)`, `var(--accent-soft)`) e as variáveis do contexto Jinja2 (`empresa.nome`, `empresa.capa_slogan`, `empresa.logo_url`).

| Slug | Estilo | Descrição |
|---|---|---|
| `corporativo` | Fundo dark + cor primária | Inicial da empresa, nome, cidade, tagline em accent |
| `clean` | Fundo branco + barra lateral | Logo circular, badges de diferenciais |
| `impacto` | Gradiente monocromático da cor | Nome grande, tagline, sem divisores |
| `premium` | Fundo muito escuro + textura | Iniciais separadas, tipografia espaçada |

**Lógica no `portfolio.html` (Jinja2):**
```jinja2
{% if empresa.capa_template_id %}
  <div class="cover-banner cover-template cover-template-{{ empresa.capa_template_id }}">
    {% if empresa.capa_template_id == "corporativo" %}
      {# bloco HTML/CSS corporativo #}
    {% elif empresa.capa_template_id == "clean" %}
      {# bloco HTML/CSS clean #}
    {% elif empresa.capa_template_id == "impacto" %}
      {# bloco HTML/CSS impacto #}
    {% elif empresa.capa_template_id == "premium" %}
      {# bloco HTML/CSS premium #}
    {% endif %}
  </div>
{% elif empresa.capa_portfolio_url %}
  <div class="cover-banner" aria-hidden="true">
    <img src="{{ empresa.capa_portfolio_url }}" alt="">
  </div>
{% endif %}
```

CSS dos templates usa `.cover-banner` existente + estilos inline nos blocos para evitar conflito.

---

## Frontend (`catalogo.html`)

### HTML — Seção "2. Imagem de capa (opcional)"

Estrutura final da seção (após as edições do dia 2026-05-15):

```
[ Zona de upload (existente) ]
─── ou escolha um template ───
[ Grid 2×2: 4 cards de template ]
[ Campo tagline + botão "Sugerir com IA" ]  ← visível só quando template selecionado
[ Botões: Trocar template | Salvar | ✕ ]    ← visível só quando template selecionado
```

Quando template está ativo:
- Grid colapsa para "▼ ver outros templates" (toggle)
- Preview grande do template aparece no lugar da zona de upload
- Upload fica como opção discreta no rodapé da seção

### Novas funções JS

| Função | Responsabilidade |
|---|---|
| `renderGaleriaTemplates(empresa)` | Renderiza os 4 cards com `cor_primaria` e `nome` da empresa; marca o card ativo se `capa_template_id` já estiver definido |
| `selecionarTemplate(templateId, slogan, jaPersistido)` | Destaca o card, exibe campo de tagline pré-preenchido e preview grande; `jaPersistido=true` indica que não precisa salvar ao fechar sem clicar "Salvar" |
| `sugerirSloganIA()` | Chama `POST /catalogo/portfolio/sugerir-slogan-ia`, preenche o input |
| `salvarTemplate()` | `DELETE /empresa/capa-portfolio` (se existir) → `POST /empresa/capa-template` |
| `removerTemplate()` | `DELETE /empresa/capa-template`, volta ao estado padrão |

### Atualização em `abrirModalPortfolio()`

Após `carregarDadosEmpresaPortfolio()` resolver:
```javascript
if (empresa.capa_template_id) {
  renderGaleriaTemplates(empresa);
  selecionarTemplate(empresa.capa_template_id, empresa.capa_slogan, /* persistido */ true);
} else if (empresa.capa_portfolio_url) {
  mostrarCapaPortfolioModal(empresa.capa_portfolio_url);
} else {
  ocultarCapaPortfolioModal();
  renderGaleriaTemplates(empresa);
}
```

### Cache

`portfolioEmpresaCache = null` após `salvarTemplate()` e `removerTemplate()` para forçar reload.

---

## Verificação

1. Abrir modal "Gerar Portfólio" sem nenhuma capa → galeria visível com 4 cards
2. Clicar "Corporativo" → preview grande aparece + campo de tagline vazio
3. Clicar "Sugerir com IA" → campo preenchido com 1 frase
4. Editar a tagline → preview grande atualiza o texto em tempo real (event `input` no campo, sem chamada de API)
5. "Salvar" → notificação de sucesso; fechar e reabrir modal → template ainda selecionado
6. "Baixar PDF" → PDF tem o banner do template escolhido no topo
7. "Visualizar HTML" → mesmo banner no HTML
8. Selecionar template quando havia imagem uploaded → imagem removida, template ativo
9. Upload de imagem quando havia template → template desmarcado, imagem ativa
10. "✕" → template removido, estado padrão restaurado
