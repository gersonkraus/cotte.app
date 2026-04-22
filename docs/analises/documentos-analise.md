# Análise do Módulo de Documentos — COTTE
**Data:** 2026-04-21  
**Objetivo:** Preparação para comercialização (semana que vem)  
**Arquivos analisados:**
- `sistema/app/routers/documentos.py`
- `sistema/app/services/documentos_service.py`
- `sistema/app/services/documentos_html_service.py`
- `sistema/app/schemas/schemas.py` (seção DocumentoEmpresa*)
- `sistema/app/models/models.py` (model DocumentoEmpresa)
- `sistema/cotte-frontend/documentos.html`
- `sistema/cotte-frontend/js/documentos.js`

---

## Resumo Executivo

O módulo possui **4 bugs críticos** que bloqueiam o uso correto em produção — o mais grave é a omissão de campos essenciais no schema de saída (`DocumentoEmpresaOut`), que faz o botão de download sempre aparecer desabilitado para todos os documentos. O backend de integração com orçamentos está completo (`orcamentos.py`), mas a UI do frontend de orçamentos precisa ser verificada. Os serviços de geração de slug e nome de download têm regex quebrado.

---

## 1. BUGS CRÍTICOS

### BUG-01 — `DocumentoEmpresaOut` ausente campos essenciais (CRÍTICO)

**Arquivo:** `sistema/app/schemas/schemas.py:347-365`

`DocumentoEmpresaOut` está faltando os campos:
- `permite_download: bool` — **frontend usa `d.permite_download` para mostrar/ocultar botão de download. Como o campo não vem na resposta, `d.permite_download` é sempre `undefined` (falsy), fazendo o botão de download aparecer desabilitado para TODOS os documentos.**
- `visivel_no_portal: bool` — não retornado, nunca refletido no frontend
- `criado_em: datetime` — frontend usa `d.atualizado_em || d.criado_em` para exibir data; sem os dois, sempre exibe `'—'`
- `atualizado_em: Optional[datetime]` — idem acima; lista não exibe datas

O schema atual:
```python
class DocumentoEmpresaOut(BaseModel):
    id: int
    empresa_id: int
    criado_por_id: Optional[int] = None
    nome: str
    slug: Optional[str] = None
    tipo: TipoDocumentoEmpresa
    descricao: Optional[str] = None
    arquivo_nome_original: Optional[str] = None
    mime_type: Optional[str] = None
    tamanho_bytes: Optional[int] = None
    tipo_conteudo: TipoConteudoDocumento
    conteudo_html: Optional[str] = None
    variaveis_suportadas: Optional[list] = None
    versao: Optional[str] = None
    status: StatusDocumentoEmpresa
    class Config:
        from_attributes = True
```

**Correção:**
```python
class DocumentoEmpresaOut(BaseModel):
    id: int
    empresa_id: int
    criado_por_id: Optional[int] = None
    nome: str
    slug: Optional[str] = None
    tipo: TipoDocumentoEmpresa
    descricao: Optional[str] = None
    arquivo_nome_original: Optional[str] = None
    mime_type: Optional[str] = None
    tamanho_bytes: Optional[int] = None
    tipo_conteudo: TipoConteudoDocumento
    conteudo_html: Optional[str] = None
    variaveis_suportadas: Optional[list] = None
    versao: Optional[str] = None
    status: StatusDocumentoEmpresa
    permite_download: bool = True        # FALTAVA
    visivel_no_portal: bool = True       # FALTAVA
    criado_em: Optional[datetime] = None # FALTAVA
    atualizado_em: Optional[datetime] = None  # FALTAVA
    class Config:
        from_attributes = True
```

**Impacto colateral:** O endpoint `GET /orcamentos/{id}/documentos/disponiveis` em `orcamentos.py:731` também usa `DocumentoEmpresaOut`, então a UI de vínculo de documentos em orçamentos sofre o mesmo problema.

---

### BUG-02 — Regex quebrada em `gerar_slug_documento` (CRÍTICO)

**Arquivo:** `sistema/app/services/documentos_service.py:19-25`

```python
def gerar_slug_documento(nome: str) -> str:
    s = (nome or "").strip().lower()
    s = re.sub(r"[^a-z0-9\\s-]", "", s)   # ❌ \\s em raw string = literal \s (não whitespace)
    s = re.sub(r"\\s+", "-", s)            # ❌ nunca substitui espaços por hífens
    s = re.sub(r"-{2,}", "-", s)
    s = s.strip("-")
    return s or "documento"
```

Em raw string `r"..."`, `\\s` é a sequência literal `\s` (dois chars), não o metacaracter de whitespace. O efeito real:
- Primeiro regex: remove tudo que não é `[a-z0-9\s-]` literalmente — espaços SÃO removidos (não estão na lista)
- Segundo regex: `\\s+` nunca casa com espaços; tenta casar com `\s` literal

Resultado: `"Mão de obra"` → `"modeobra"` (palavras coladas, sem hífen).

**Correção:**
```python
def gerar_slug_documento(nome: str) -> str:
    s = (nome or "").strip().lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)   # \s = whitespace
    s = re.sub(r"\s+", "-", s)            # substitui espaços por hífens
    s = re.sub(r"-{2,}", "-", s)
    s = s.strip("-")
    return s or "documento"
```

---

### BUG-03 — Regex quebrada em `montar_nome_download` (CRÍTICO)

**Arquivo:** `sistema/app/services/documentos_service.py:101-113`

```python
def montar_nome_download(nome_base, versao, ext=".pdf"):
    base = re.sub(r"[\\r\\n\\t]", " ", base)  # ❌ literal \r\n\t, não control chars
    base = re.sub(r"\\s+", " ", base).strip()  # ❌ não substitui espaços múltiplos
```

`r"[\\r\\n\\t]"` casa com os caracteres literais `\`, `r`, `\`, `n`, `\`, `t` — nunca com `\r`, `\n`, `\t` reais. `r"\\s+"` não casa com espaços.

**Correção:**
```python
base = re.sub(r"[\r\n\t]", " ", base)
base = re.sub(r"\s+", " ", base).strip()
```

---

### BUG-04 — `abrirPreviewDocumento` chama função inexistente `mostrarNotificacao` (CRÍTICO)

**Arquivo:** `sistema/cotte-frontend/js/documentos.js:932-940`

```js
function abrirPreviewDocumento() {
  if (!quillEditor) {
    mostrarNotificacao('Erro', 'Editor não inicializado', 'error');  // ❌ não existe
    return;
  }
  const conteudoHtml = obterConteudoHtmlEditor();
  if (!conteudoHtml || conteudoHtml.trim() === '') {
    mostrarNotificacao('Aviso', 'O documento está vazio', 'warning');  // ❌ não existe
```

A função no sistema é `showNotif(icon, title, sub, type)`. `mostrarNotificacao` causa `ReferenceError` — o botão "Visualizar" quebra silenciosamente.

**Correção:**
```js
showNotif('⚠️', 'Editor não inicializado', '', 'error');
// ...
showNotif('⚠️', 'Documento vazio', 'Digite o conteúdo antes de visualizar', 'error');
```

---

### BUG-05 — Ordem errada: conteúdo HTML definido antes do editor ser inicializado (CRÍTICO)

**Arquivo:** `sistema/cotte-frontend/js/documentos.js:149-198`

Em `abrirModalEditarDocumento`, para documentos HTML:
```js
// linha 184 — ANTES do editor existir
if (doc.conteudo_html) {
  definirConteudoHtmlEditor(doc.conteudo_html);  // quillEditor pode ser null
}
// ...
// linha 194 — DEPOIS, inicializa o editor
alternarTipoConteudoDocumento();  // chama inicializarEditorQuill()
```

`definirConteudoHtmlEditor` na linha 184 encontra `quillEditor === null`, cai no `setTimeout` de 100ms. Mas `alternarTipoConteudoDocumento` só é chamado em seguida (linha 194), e cria o editor. Na maioria dos casos o `setTimeout` dispara ANTES do editor estar pronto, causando conteúdo vazio ao abrir documentos HTML para edição.

**Correção:** Inverter a ordem — chamar `alternarTipoConteudoDocumento()` ANTES de `definirConteudoHtmlEditor()`:
```js
// Configurar tipo de conteúdo e inicializar editor PRIMEIRO
document.getElementById('doc-tipo-conteudo').value = tipoConteudo;
alternarTipoConteudoDocumento();  // inicializa Quill

// Só depois carregar conteúdo
if (tipoConteudo === 'html' && doc.conteudo_html) {
  definirConteudoHtmlEditor(doc.conteudo_html);
}
```

---

## 2. BUGS DE ALTA PRIORIDADE

### BUG-06 — `_limparFormDocumento` definida duas vezes

**Arquivo:** `sistema/cotte-frontend/js/documentos.js:209-219` e `1346-1369`

A primeira definição (linhas 209-219) é dead code — a segunda (mais completa) sobrescreve por hoisting. Não causa bug em runtime (a versão mais completa vence), mas é confuso e arriscado para manutenção.

**Correção:** Remover a primeira definição (linhas 209-219). A segunda é a correta.

---

### BUG-07 — Upload aceita arquivos com 0 bytes

**Arquivo:** `sistema/app/services/documentos_service.py:53-58`

```python
if tamanho > MAX_DOCUMENTO_BYTES:
    raise HTTPException(...)
```

Não há verificação `tamanho == 0`. Um arquivo vazio passa pela validação, vai para o R2 e fica registrado no banco como válido.

**Correção:** Adicionar `if tamanho == 0: raise HTTPException(status_code=400, detail="Arquivo vazio")`.

---

### BUG-08 — `baixarDocumento` usa extensão `.pdf` hardcoded para todos os tipos

**Arquivo:** `sistema/cotte-frontend/js/documentos.js:366`

```js
a.download = `documento-${id}.pdf`;  // ❌ sempre .pdf, mesmo para HTML
```

Documentos HTML baixados têm extensão `.pdf` incorreta.

**Correção:**
```js
const doc = documentosCache.find(d => d.id === id);
const ext = doc?.tipo_conteudo === 'html' ? '.html' : '.pdf';
a.download = `documento-${id}${ext}`;
```

---

### BUG-09 — `sincronizar_documento_viculado` não sincroniza `conteudo_html` nem `variaveis_suportadas`

**Arquivo:** `sistema/app/routers/orcamentos.py` (função `sincronizar_documento_viculado`)

O endpoint de sincronização (`POST /orcamentos/{id}/documentos/{vid}/sincronizar`) atualiza apenas `documento_nome`, `documento_tipo`, `documento_versao` — não sincroniza `conteudo_html`, `variaveis_suportadas`, `arquivo_nome_original`, `mime_type`, `tamanho_bytes`. Documentos HTML com variáveis nunca ficam atualizados no vínculo.

---

### BUG-10 — Sem substituição de variáveis no endpoint público

**Arquivo:** `sistema/app/services/documentos_html_service.py` (serviço completo nunca invocado)

`documentos_html_service.py` tem toda a infraestrutura de substituição de variáveis (`processar_documento_html_com_variaveis`, `substituir_variaveis_html`), mas não há nenhum endpoint que chame essas funções. Quando um cliente acessa `GET /documentos/{id}/arquivo` de um documento HTML, recebe o conteúdo bruto com `{nome_cliente}`, `{valor_orcamento}` etc. visíveis. O serviço existe mas não está conectado.

---

### BUG-11 — Sem rate limit no endpoint de upload

**Arquivo:** `sistema/app/routers/documentos.py:58-154`

O endpoint `POST /documentos/` não tem proteção contra uploads massivos. Um usuário com permissão de escrita pode fazer centenas de uploads por minuto consumindo espaço no R2 e largura de banda.

---

### BUG-12 — Quill.js sem feedback visual de falha de carregamento

**Arquivo:** `sistema/cotte-frontend/js/documentos.js:432-442`

```js
if (typeof Quill === 'undefined') {
  const script = document.createElement('script');
  script.src = 'https://cdn.quilljs.com/1.3.7/quill.js';
  script.onload = () => { criarEditorQuill(); };
  document.head.appendChild(script);
  // ❌ sem script.onerror — falha silenciosa
}
```

Se o CDN do Quill falhar, o usuário vê o campo vazio sem explicação.

---

## 3. BUGS DE MÉDIA PRIORIDADE

### BUG-13 — Slug collision silenciosa

**Arquivo:** `sistema/app/routers/documentos.py:117-130`

Quando há conflito de slug, o sistema adiciona timestamp silenciosamente (`slug-20260421120000`) sem informar o usuário. O slug exibido no cadastro difere do slug final salvo.

---

### BUG-14 — `atualizar_documento` não valida mudança de `tipo_conteudo`

**Arquivo:** `sistema/app/routers/documentos.py:178-217`

Se um documento é alterado de PDF para HTML (ou vice-versa), o endpoint `PUT /{id}` simplesmente salva o novo `tipo_conteudo` sem limpar os campos do tipo anterior (`arquivo_path`, `arquivo_nome_original` ficam no banco para um doc HTML, `conteudo_html` fica para um doc PDF).

---

### BUG-15 — `DocumentoEmpresaOut` retorna `conteudo_html` completo na listagem

**Arquivo:** `sistema/app/routers/documentos.py:29-55` + schema

`GET /documentos/` retorna todos os documentos com o campo `conteudo_html` completo. Para documentos grandes, isso gera payloads enormes na listagem. `conteudo_html` deveria ser omitido na listagem e incluído apenas em `GET /{id}`.

---

### BUG-16 — Sem aviso ao fechar modal com conteúdo não salvo

**Arquivo:** `sistema/cotte-frontend/js/documentos.js`

Usuário que edita um documento HTML extenso e clica "Cancelar" ou fecha o modal perde o conteúdo sem aviso.

---

### BUG-17 — `abrirDocumento` usa blob para R2 (ineficiente)

**Arquivo:** `sistema/cotte-frontend/js/documentos.js:350-358`

Para PDFs no R2, o backend faz `RedirectResponse`. O `_apiDownloadBlob` do frontend segue o redirect, baixa o arquivo para a memória do browser e cria um `objectURL`. O correto seria abrir a URL diretamente. Para documentos grandes isso desperdiça memória.

---

### BUG-18 — `DocumentoEmpresaUpdate` permite mudar `tipo_conteudo` mas o backend não valida

Ver BUG-14. O schema aceita a mudança e o backend salva sem validação cruzada.

---

### BUG-19 — Falta índice em `documentos_empresa.status`

O filtro `WHERE status != 'arquivado'` e `WHERE status = ?` são queries frequentes mas a coluna `status` não tem índice (não visível no model). Para tabelas com muitos documentos, pode gerar full table scan.

---

### BUG-20 — `criado_em` sem valor inicial na model

**Arquivo:** `sistema/app/models/models.py:640`

```python
criado_em = Column(DateTime(timezone=True), server_default=func.now())
atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())
```

`atualizado_em` usa `onupdate=func.now()` (ORM-level). Funciona corretamente com SQLAlchemy ORM. Porém, se alguém usar SQL direto (migrations, admin) sem passar pelo ORM, `atualizado_em` não é atualizado automaticamente. Considerar `server_onupdate` para consistência no banco.

---

## 4. FALHAS DE INTEGRAÇÃO

### INT-01 — Frontend de orçamentos: verificar UI de vínculo de documentos

O backend em `orcamentos.py` tem os endpoints completos para gerenciar documentos vinculados a orçamentos:
- `GET /orcamentos/{id}/documentos` — listar vinculados
- `GET /orcamentos/{id}/documentos/disponiveis` — listar disponíveis
- `POST /orcamentos/{id}/documentos` — vincular
- `PUT /orcamentos/{id}/documentos/{vid}` — configurar vínculo
- `POST /orcamentos/{id}/documentos/ordem` — reordenar
- `POST /orcamentos/{id}/documentos/{vid}/sincronizar` — sincronizar

**Verificar se a UI de orçamentos (orcamentos.html/orcamentos.js) implementa a interface de vínculo de documentos.** Se não implementada, o valor do módulo de documentos é zero para o usuário final.

---

### INT-02 — Portal do cliente não serve documentos com variáveis substituídas

O `documentos_html_service.py` tem toda a lógica de substituição de variáveis, mas:
1. Não há rota pública/portal que substitua variáveis por dados reais do orçamento/cliente
2. `GET /documentos/{id}/arquivo` retorna sempre o template bruto
3. `OrcamentoDocumento` não armazena dados de substituição

---

### INT-03 — Permissões não verificadas no endpoint `/disponiveis`

**Arquivo:** `sistema/app/routers/orcamentos.py:731-760`

`listar_documentos_disponiveis` usa `exigir_permissao("orcamentos", "leitura")` mas não `("documentos", "leitura")`. Um usuário sem permissão de documentos ainda pode listar todos os documentos da empresa via rota de orçamentos.

---

## 5. FUNCIONALIDADES AUSENTES ESSENCIAIS

### FEAT-01 — Sem busca por conteúdo (somente por nome)

`GET /documentos/?q=` filtra apenas por `nome.ilike`. Não há busca no conteúdo HTML nem na descrição.

---

### FEAT-02 — Sem paginação na listagem de documentos

`listar_documentos` retorna TODOS os documentos sem `skip`/`limit`. Para empresas com muitos documentos, payload crescente.

---

### FEAT-03 — Sem histórico de versões de documentos

Não há versionamento: cada edição sobrescreve o documento. Não é possível reverter para versão anterior.

---

### FEAT-04 — Sem exportação/download em lote

Não há endpoint para baixar múltiplos documentos como ZIP.

---

## 6. PLANO DE AÇÃO MÍNIMO PARA COMERCIALIZAÇÃO

| # | Item | Severidade | Status |
|---|------|-----------|--------|
| 1 | Adicionar `permite_download`, `visivel_no_portal`, `criado_em`, `atualizado_em` em `DocumentoEmpresaOut` | CRÍTICO | ✅ |
| 2 | Corrigir regex em `gerar_slug_documento` (`\\s` → `\s`) | CRÍTICO | ✅ |
| 3 | Corrigir regex em `montar_nome_download` (`\\r\\n\\t` e `\\s+`) | CRÍTICO | ✅ |
| 4 | Corrigir `abrirPreviewDocumento`: `mostrarNotificacao` → `showNotif` | CRÍTICO | ✅ |
| 5 | Corrigir ordem de init do Quill em `abrirModalEditarDocumento` | CRÍTICO | ✅ |
| 6 | Remover definição duplicada de `_limparFormDocumento` (linhas 209-219) | ALTO | ✅ |
| 7 | Rejeitar upload de arquivo com 0 bytes | ALTO | ✅ |
| 8 | Corrigir extensão do arquivo HTML em `baixarDocumento` | ALTO | ✅ |
| 9 | Verificar e implementar UI de vínculo de documentos em orçamentos | ALTO | ✅ |
| 10 | Adicionar `onerror` no carregamento dinâmico do Quill.js | ALTO | ✅ |

---

## 7. Pendências Pós-Lançamento (Backlog)

- Substituição de variáveis em tempo real ao servir documentos HTML para clientes
- Paginação na listagem de documentos
- Busca por conteúdo/descrição
- Versionamento de documentos (histórico)
- Download em lote (ZIP)
- Índice em `documentos_empresa.status` para performance
- Endpoint público (portal) com variáveis já substituídas por dados do orçamento
- Notificação de slug alterado automaticamente (BUG-13)
- Validação cruzada ao mudar `tipo_conteudo` (BUG-14)
- Remover `conteudo_html` do response da listagem (BUG-15)
