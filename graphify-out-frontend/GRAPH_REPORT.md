---
title: Graph Report
tags:
  - documentacao
  - frontend
prioridade: media
status: documentado
---
# Graph Report - sistema/cotte-frontend  (2026-04-11)

## Corpus Check
- 52 files · ~100,258 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1493 nodes · 3180 edges · 72 communities detected
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 1 edges (avg confidence: 0.7)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `push()` - 62 edges
2. `map()` - 59 edges
3. `add()` - 44 edges
4. `has()` - 39 edges
5. `replace()` - 39 edges
6. `get()` - 33 edges
7. `insert()` - 26 edges
8. `ComercialCampanhas` - 25 edges
9. `OrcamentosTable` - 25 edges
10. `decl()` - 22 edges

## Surprising Connections (you probably didn't know these)
- `sendMessage (AI chat)` --references--> `ChatVirtualizer`  [INFERRED]
  sistema/cotte-frontend/js/assistente-ia.js → sistema/cotte-frontend/js/chat-virtualization.js
- `sendMessage (AI chat)` --calls--> `addMessage`  [EXTRACTED]
  sistema/cotte-frontend/js/assistente-ia.js → sistema/cotte-frontend/js/assistente-ia-input.js
- `confirmarAcaoIA / cancelarAcaoIA` --calls--> `sendMessage (AI chat)`  [EXTRACTED]
  sistema/cotte-frontend/js/assistente-ia-actions.js → sistema/cotte-frontend/js/assistente-ia.js
- `Speech Recognition (Voice Input)` --calls--> `sendMessage (AI chat)`  [EXTRACTED]
  sistema/cotte-frontend/js/assistente-ia-input.js → sistema/cotte-frontend/js/assistente-ia.js
- `carregarClientes` --calls--> `escapeHtml`  [EXTRACTED]
  sistema/cotte-frontend/js/clientes.js → sistema/cotte-frontend/js/utils.js

## Communities

### Community 0 - "Tailwind CSS Engine"
Cohesion: 0.02
Nodes (90): aa(), ac(), Ak(), applyVariantOffset(), bd(), bk(), blueGray(), bo() (+82 more)

### Community 1 - "Comercial Module Core"
Cohesion: 0.04
Nodes (103): abrirConfirmacaoReenvioProposta(), abrirContatosImportados(), abrirDetalhe(), abrirImportacaoLeads(), abrirModalCampanha(), abrirModalEmail(), abrirModalLead(), abrirModalLembrete() (+95 more)

### Community 2 - "Configuracoes & Preview"
Cohesion: 0.04
Nodes (59): abrirPreviewTemplatePublico(), atualizarBtnTema(), atualizarPreview(), atualizarPreviewForma(), atualizarPreviewNumero(), atualizarVisualizacaoTema(), _buildMockOrcamentoPublico(), _buildStaticPreviewExtras() (+51 more)

### Community 3 - "Agendamentos Module"
Cohesion: 0.05
Nodes (61): abrirModalConfig(), abrirModalCriar(), abrirModalDash(), abrirModalEditar(), abrirModalReagendar(), acaoRapida(), adicionarBloqueio(), aoClicarEvento() (+53 more)

### Community 4 - "JS Utility Functions"
Cohesion: 0.06
Nodes (51): Bh(), br(), breakpoints(), c(), checkForWarning(), d2(), Dv(), ei() (+43 more)

### Community 5 - "Async & Sync Helpers"
Cohesion: 0.06
Nodes (51): async(), ax(), catch(), Cl(), $d(), disabled(), disabledDecl(), disabledValue() (+43 more)

### Community 6 - "CSS PostCSS Processor"
Cohesion: 0.07
Nodes (39): after(), append(), BC(), before(), cloneAfter(), Co(), dy(), FC() (+31 more)

### Community 7 - "CSS Parser & AST"
Cohesion: 0.08
Nodes (39): An(), ao(), atrule(), checkMissedSemicolon(), colon(), comment(), decl(), doubleColon() (+31 more)

### Community 8 - "API Client Layer"
Cohesion: 0.11
Nodes (29): apiRequest(), baixarExportar(), buildAbsoluteAppUrl(), buildApiRequestUrl(), buildPublicAssetUrl(), carregarSidebar(), coerceFetchUrlIfMixedContent(), exibirModalPlanos() (+21 more)

### Community 9 - "String Processing Utils"
Cohesion: 0.07
Nodes (37): addToError(), Ae(), convertDirection(), Eh(), fixAngle(), fixDirection(), fixRadial(), G2() (+29 more)

### Community 10 - "Data Structures & Maps"
Cohesion: 0.1
Nodes (36): ca(), cs(), DC(), delete(), _deleteIfExpired(), _emitEvictions(), _entriesAscending(), entriesDescending() (+28 more)

### Community 11 - "Assistente IA Shell"
Cohesion: 0.12
Nodes (26): applyAdaptiveMessagePlaceholder(), _buildAssistenteContext(), captureAssistenteResponseContext(), _extractAssistenteCommand(), _extractAssistenteEntityFromResponse(), _extractAssistenteEntityFromText(), getAdaptiveMessagePlaceholder(), handleAssistenteChatScroll() (+18 more)

### Community 12 - "CSS Rule Processing"
Cohesion: 0.09
Nodes (33): beforeAfter(), block(), body(), calcBefore(), check(), cleanBrackets(), cleaner(), comma() (+25 more)

### Community 13 - "JSON & Stringify Utils"
Cohesion: 0.09
Nodes (31): Ah(), B(), c2(), clean(), cloneDiv(), colorStops(), content(), convert() (+23 more)

### Community 14 - "Propostas Publicas"
Cohesion: 0.12
Nodes (20): adicionarBlocoCustomizado(), adicionarVariavelProposta(), atualizarCampoBloco(), atualizarConfigBloco(), atualizarOrdemBlocos(), atualizarVariavelProposta(), carregarPropostasPublicas(), configurarDragAndDropBlocos() (+12 more)

### Community 15 - "Leads Management"
Cohesion: 0.14
Nodes (27): abrirDetalhe(), abrirModalEnviarProposta(), abrirModalLead(), adicionarObservacao(), alterarScore(), alterarStatusLead(), arquivarLead(), atualizarBannerFollowUpLeads() (+19 more)

### Community 16 - "Collection Helpers"
Cohesion: 0.09
Nodes (29): add(), already(), au(), cleanFromUnprefixed(), cleanOtherPrefixes(), clear(), cloneBefore(), findProp() (+21 more)

### Community 17 - "Clone & Transform"
Cohesion: 0.12
Nodes (28): _a(), applyParallelOffset(), as(), assign(), clone(), da(), ex(), F_() (+20 more)

### Community 18 - "Documentos Module"
Cohesion: 0.14
Nodes (23): abrirDocumento(), abrirModalEditarDocumento(), abrirModalNovoDocumento(), abrirPreviewDocumento(), alternarTipoConteudoDocumento(), _apiDownloadBlob(), _apiUpload(), aplicarFiltrosDocumentos() (+15 more)

### Community 19 - "Comercial Campanhas"
Cohesion: 0.13
Nodes (1): ComercialCampanhas

### Community 20 - "Orcamentos Table"
Cohesion: 0.13
Nodes (1): OrcamentosTable

### Community 21 - "DOM Insert Helpers"
Cohesion: 0.11
Nodes (23): arbitraryProperty(), cm(), contain3d(), cr(), De(), dr(), i(), il() (+15 more)

### Community 22 - "Proposta Builder"
Cohesion: 0.17
Nodes (20): adicionarBlocoCustom(), adicionarVariavel(), atualizarOrdem(), carregarProposta(), cloneBlocos(), cloneVars(), configurarDragDrop(), esc() (+12 more)

### Community 23 - "Comercial Cadastros"
Cohesion: 0.15
Nodes (16): carregarOrigens(), carregarPipelineStagesUI(), carregarSegmentos(), editarOrigem(), editarPipelineStage(), editarSegmento(), excluirPipelineStage(), renderEtapasMobile() (+8 more)

### Community 24 - "Clientes Module"
Cohesion: 0.17
Nodes (15): abrirModalEditar(), abrirModalNovoCliente(), buscarCep(), buscarCnpj(), carregarClientes(), fecharModalCliente(), limparFormCliente(), mascararCep() (+7 more)

### Community 25 - "Comercial Templates"
Cohesion: 0.15
Nodes (1): ComercialTemplates

### Community 26 - "HTML Escape Utils"
Cohesion: 0.12
Nodes (6): escapeHtml(), escapeHtmlWithBreaks(), formatarData(), formatarDataRelativa(), formatarMoeda(), formatarMoedaCompacta()

### Community 27 - "Cache Service"
Cohesion: 0.17
Nodes (1): CacheService

### Community 28 - "Assistente IA Input"
Cohesion: 0.19
Nodes (14): applySlashCommand(), _closePrefSheet(), _focusFirstPrefField(), _getAssistentePrefCard(), _getPrefBackdrop(), _getPrefFocusableElements(), hideSlashCommands(), initSlashCommands() (+6 more)

### Community 29 - "Comercial Import"
Cohesion: 0.2
Nodes (1): ComercialImport

### Community 30 - "Dashboard Right Panel"
Cohesion: 0.17
Nodes (1): RightPanel

### Community 31 - "Dashboard Charts"
Cohesion: 0.2
Nodes (1): ChartsGrid

### Community 32 - "Assistente IA Main"
Cohesion: 0.21
Nodes (10): escapeHtml(), hasHttpClient(), loadAssistentePreferences(), renderAssistentePreferencesCard(), saveAssistentePreferences(), sendMessage(), showAssistentePrefNotice(), syncAssistenteGearSavedBadge() (+2 more)

### Community 33 - "Dashboard Stats Row"
Cohesion: 0.18
Nodes (1): StatsRow

### Community 34 - "UX Improvements"
Cohesion: 0.17
Nodes (8): abrirDropdownAcoes(), fecharDropdownAcoes(), fecharLoading(), initGlobalListeners(), mostrarLoading(), showError(), showSuccess(), showToast()

### Community 35 - "Date & Format Utils"
Cohesion: 0.15
Nodes (4): formatarData(), formatarDataRelativa(), formatarMoeda(), formatarMoedaCompacta()

### Community 36 - "AI Chat Flow"
Cohesion: 0.14
Nodes (15): confirmarAcaoIA / cancelarAcaoIA, confirmarOrcamento, enviarPorWhatsapp, httpClient (ApiService|api fallback), Assistente Preferences (load/save), sendMessage (AI chat), Slash Commands Menu, SSE Stream Endpoint /ai/assistente/stream (+7 more)

### Community 37 - "Comercial Mensagens"
Cohesion: 0.23
Nodes (8): abrirModalEmail(), abrirModalWhatsApp(), carregarTemplates(), editarTemplate(), excluirTemplate(), populateTplSelect(), renderTemplatesMobile(), salvarTemplate()

### Community 38 - "Array Helpers"
Cohesion: 0.23
Nodes (12): Bf(), en(), every(), Ff(), jf(), jr(), ke(), Nf() (+4 more)

### Community 39 - "Chat Virtualizer"
Cohesion: 0.3
Nodes (1): ChatVirtualizer

### Community 40 - "Orcamento Detalhes"
Cohesion: 0.26
Nodes (8): abrirDetalhesOrcamento(), _carregarContasOrcamento(), _carregarDocumentosDetalhes(), confirmarDesaprovar(), fecharDetalhes(), _renderizarHistoricoPagamentos(), _renderizarProgressoPagamentos(), sincronizarDocumento()

### Community 41 - "Comercial Core"
Cohesion: 0.21
Nodes (5): bindTabEvents(), carregarCadastrosCache(), esc(), reconstruirStatusMaps(), switchTab()

### Community 42 - "Range & Constructor"
Cohesion: 0.24
Nodes (11): Ba(), constructor(), createTokenizer(), mapResolve(), positionBy(), positionInside(), Qk(), rangeBy() (+3 more)

### Community 43 - "AI Response Renderer"
Cohesion: 0.38
Nodes (9): formatAIResponse(), renderAnaliseTexto(), renderOnboarding(), renderOperadorResultado(), renderOrcamentoAtualizado(), renderOrcamentoCriado(), renderOrcamentoPreview(), renderSaldoRapido() (+1 more)

### Community 44 - "Dashboard Modals"
Cohesion: 0.31
Nodes (6): createGlobalOverlay(), getNovoOrcamentoContent(), getNovoOrcamentoFooter(), init(), registerModals(), setupGlobalEvents()

### Community 45 - "Orcamento Reenvio"
Cohesion: 0.43
Nodes (7): abrirModalReenvioOrcamento(), bindReenvioModalHandlers(), cotteConfirmarReenvioSeNecessario(), fecharModalReenvioOrcamento(), mensagemFallback(), onKeydownReenvio(), precisaConfirmarReenvioOrcamento()

### Community 46 - "Tooltip Manager"
Cohesion: 0.32
Nodes (1): TooltipManager

### Community 47 - "Assistente IA Actions"
Cohesion: 0.29
Nodes (0): 

### Community 48 - "Assistente Render Utils"
Cohesion: 0.33
Nodes (2): _brl(), formatPendingArgs()

### Community 49 - "Comercial Dashboard"
Cohesion: 0.52
Nodes (6): carregarDashboard(), carregarNovosClientes(), irParaLeadsComFiltro(), renderActionList(), renderMetrics(), renderRecentList()

### Community 50 - "Version Check"
Cohesion: 0.53
Nodes (5): Update Banner UI, _checkVersion(), _createBanner(), _init(), _showBanner()

### Community 51 - "Comercial Pipeline"
Cohesion: 0.6
Nodes (4): carregarPipeline(), dropCard(), kanbanCard(), renderKanban()

### Community 52 - "API Service"
Cohesion: 0.4
Nodes (0): 

### Community 53 - "Layout Init & Guards"
Cohesion: 0.4
Nodes (5): DOMContentLoaded (comercial init), inicializarLayout, Permissoes Menu Guard, Onboarding Setup Strip, Sidebar Navigation Component

### Community 54 - "Comercial Lembretes"
Cohesion: 0.67
Nodes (2): carregarLembretes(), salvarLembrete()

### Community 55 - "Layout Module"
Cohesion: 1.0
Nodes (2): inicializarLayout(), _renderSetupStrip()

### Community 56 - "Assistente Feedback"
Cohesion: 0.67
Nodes (0): 

### Community 57 - "Service Worker Cache"
Cohesion: 0.67
Nodes (3): Cache Strategies (NetworkFirst/StaleWhileRevalidate/CacheFirst), COTTE Service Worker, Workbox CDN Integration

### Community 58 - "Clientes Render"
Cohesion: 0.67
Nodes (3): renderizarClientes, corAvatar, iniciaisDe

### Community 59 - "AI Response Processor"
Cohesion: 1.0
Nodes (0): 

### Community 60 - "Template Moderno"
Cohesion: 1.0
Nodes (0): 

### Community 61 - "Clientes Load"
Cohesion: 1.0
Nodes (2): carregarClientes, escapeHtml

### Community 62 - "Comercial Global State"
Cohesion: 1.0
Nodes (2): Comercial Global State, switchTab (Comercial)

### Community 63 - "SW Entry Point"
Cohesion: 1.0
Nodes (0): 

### Community 64 - "Icon Generator"
Cohesion: 1.0
Nodes (0): 

### Community 65 - "Financeiro API"
Cohesion: 1.0
Nodes (0): 

### Community 66 - "Modal Orcamento"
Cohesion: 1.0
Nodes (0): 

### Community 67 - "Moeda Formatter"
Cohesion: 1.0
Nodes (1): formatarMoeda

### Community 68 - "Data Formatter"
Cohesion: 1.0
Nodes (1): formatarData

### Community 69 - "Telefone Formatter"
Cohesion: 1.0
Nodes (1): formatarTelefone

### Community 70 - "IA Health Validator"
Cohesion: 1.0
Nodes (1): Assistente HealthCheck Validator

### Community 71 - "Email Sender"
Cohesion: 1.0
Nodes (1): enviarPorEmail

## Knowledge Gaps
- **25 isolated node(s):** `Workbox CDN Integration`, `Cache Strategies (NetworkFirst/StaleWhileRevalidate/CacheFirst)`, `formatarMoeda`, `formatarData`, `escapeHtml` (+20 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `AI Response Processor`** (2 nodes): `assistente-ia-render.js`, `processAIResponse()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Template Moderno`** (2 nodes): `template-moderno.js`, `renderizarTemplateModerno()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Clientes Load`** (2 nodes): `carregarClientes`, `escapeHtml`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Comercial Global State`** (2 nodes): `Comercial Global State`, `switchTab (Comercial)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `SW Entry Point`** (1 nodes): `sw.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Icon Generator`** (1 nodes): `generate_icon.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Financeiro API`** (1 nodes): `api-financeiro.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Modal Orcamento`** (1 nodes): `modal-orcamento.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Moeda Formatter`** (1 nodes): `formatarMoeda`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Data Formatter`** (1 nodes): `formatarData`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Telefone Formatter`** (1 nodes): `formatarTelefone`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `IA Health Validator`** (1 nodes): `Assistente HealthCheck Validator`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Email Sender`** (1 nodes): `enviarPorEmail`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `push()` connect `JSON & Stringify Utils` to `Tailwind CSS Engine`, `JS Utility Functions`, `Async & Sync Helpers`, `Array Helpers`, `CSS PostCSS Processor`, `CSS Parser & AST`, `String Processing Utils`, `Data Structures & Maps`, `CSS Rule Processing`, `Collection Helpers`, `Clone & Transform`, `DOM Insert Helpers`?**
  _High betweenness centrality (0.001) - this node is a cross-community bridge._
- **Why does `map()` connect `JS Utility Functions` to `Tailwind CSS Engine`, `Async & Sync Helpers`, `CSS PostCSS Processor`, `Array Helpers`, `CSS Parser & AST`, `String Processing Utils`, `Range & Constructor`, `Data Structures & Maps`, `CSS Rule Processing`, `JSON & Stringify Utils`, `Collection Helpers`, `Clone & Transform`, `DOM Insert Helpers`?**
  _High betweenness centrality (0.001) - this node is a cross-community bridge._
- **Why does `add()` connect `Collection Helpers` to `Tailwind CSS Engine`, `JS Utility Functions`, `Async & Sync Helpers`, `CSS PostCSS Processor`, `CSS Parser & AST`, `String Processing Utils`, `Data Structures & Maps`, `CSS Rule Processing`, `JSON & Stringify Utils`, `Clone & Transform`, `DOM Insert Helpers`?**
  _High betweenness centrality (0.000) - this node is a cross-community bridge._
- **What connects `Workbox CDN Integration`, `Cache Strategies (NetworkFirst/StaleWhileRevalidate/CacheFirst)`, `formatarMoeda` to the rest of the system?**
  _25 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Tailwind CSS Engine` be split into smaller, more focused modules?**
  _Cohesion score 0.02 - nodes in this community are weakly interconnected._
- **Should `Comercial Module Core` be split into smaller, more focused modules?**
  _Cohesion score 0.04 - nodes in this community are weakly interconnected._
- **Should `Configuracoes & Preview` be split into smaller, more focused modules?**
  _Cohesion score 0.04 - nodes in this community are weakly interconnected._