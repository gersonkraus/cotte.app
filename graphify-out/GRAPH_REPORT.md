# Graph Report - .  (2026-04-11)

## Corpus Check
- Large corpus: 734 files · ~1,053,332 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder, or use --no-semantic to run AST-only.

## Summary
- 5994 nodes · 24676 edges · 356 communities detected
- Extraction: 36% EXTRACTED · 64% INFERRED · 0% AMBIGUOUS · INFERRED: 15831 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `Usuario` - 568 edges
2. `StatusOrcamento` - 538 edges
3. `Orcamento` - 491 edges
4. `Empresa` - 454 edges
5. `Cliente` - 394 edges
6. `ModoAgendamentoOrcamento` - 314 edges
7. `StatusPipeline` - 256 edges
8. `StatusDocumentoEmpresa` - 248 edges
9. `LeadScore` - 242 edges
10. `TipoConteudoDocumento` - 240 edges

## Surprising Connections (you probably didn't know these)
- `IA Assistant E2E Tests` --references--> `IA Assistant Knowledge Base`  [INFERRED]
  tests/e2e/assistente-ia-desktop.spec.js → sistema/app/services/prompts/knowledge_base.md
- `AI Tool: criar_orcamento` --implements--> `Orcamento`  [EXTRACTED]
  sistema/app/services/ai_tools/orcamento_tools.py → /home/gk/Projeto-izi/sistema/app/models/models.py
- `Máquina de estados de orçamento — transições compartilhadas entre API e bot.` --uses--> `StatusOrcamento`  [INFERRED]
  /home/gk/Projeto-izi/sistema/app/utils/orcamento_status.py → /home/gk/Projeto-izi/sistema/app/models/models.py
- `Retorna True se a transição de status for permitida pela máquina de estados (ide` --uses--> `StatusOrcamento`  [INFERRED]
  /home/gk/Projeto-izi/sistema/app/utils/orcamento_status.py → /home/gk/Projeto-izi/sistema/app/models/models.py
- `Mensagem quando a transição não é permitida (HTTP ou bot WhatsApp/dashboard).` --uses--> `StatusOrcamento`  [INFERRED]
  /home/gk/Projeto-izi/sistema/app/utils/orcamento_status.py → /home/gk/Projeto-izi/sistema/app/models/models.py

## Hyperedges (group relationships)
- **AI Agent Orchestration Flow** — cotte_ai_hub_ai_hub, ia_service_ia_service, tool_executor_execute, orcamento_tools_criar [EXTRACTED 0.95]
- **Multi-tenant WhatsApp Architecture** — whatsapp_service_factory, models_empresa, whatsapp_evolution [EXTRACTED 1.00]
- **Módulo Comercial CRM** — routers_comercial_leads, comercial_pipeline, comercial_interacoes, comercial_config [EXTRACTED 1.00]
- **Módulo Financeiro** — routers_financeiro, schemas_financeiro, financeiro_service [EXTRACTED 1.00]
- **Core Business Entities Evolution** — table_orcamentos, table_commercial_leads, module_financeiro, module_agendamentos [INFERRED 0.90]
- **Empresa Configuration Features** — feature_pix_payment, feature_whatsapp_notifications, ai_assistant_features, rbac_system [INFERRED 0.95]
- **Frontend Service Infrastructure** — api_service_js, cache_service_js, sw_js [INFERRED 0.90]
- **AI Assistant Frontend Components** — assistente_ia_js, assistente_ia_render_js, assistente_ia_actions_js [EXTRACTED 1.00]
- **MCP Server Ecosystem** — mcp_server_everything, mcp_server_filesystem, mcp_server_memory, mcp_server_git [EXTRACTED 1.00]
- **E2E Testing Suite** — e2e_tests_assistente_ia, e2e_tests_orcamentos [EXTRACTED 1.00]

## Communities

### Community 0 - "Automatic Appointment Service"
Cohesion: 0.02
Nodes (604): criar_agendamento_automatico(), _gerar_opcoes_automaticas(), liberar_pre_agendamento_lote(), listar_pre_agendamento_fila(), processar_agendamento_apos_aprovacao(), Serviço de criação automática de agendamento ao aprovar orçamento., Cria automaticamente um agendamento com opções de data quando um     orçamento c, Registra canal/data de aprovação e cria agendamento automático ou enfileira (+596 more)

### Community 1 - "Admin & Company Management API"
Cohesion: 0.03
Nodes (549): atualizar_assinatura(), atualizar_template_admin(), atualizar_usuario_admin(), criar_broadcast(), criar_empresa(), criar_template_admin(), criar_usuario_empresa(), dashboard() (+541 more)

### Community 2 - "Tailwind CSS Infrastructure"
Cohesion: 0.01
Nodes (510): _a(), aa(), ac(), add(), addToError(), Ae(), after(), Ah() (+502 more)

### Community 3 - "AI Transcription & Audio Services"
Cohesion: 0.01
Nodes (234): get_admin_config(), _migrar_json_se_necessario(), Na primeira execução, importa dados do JSON legado para o banco., _baixar_audio_evolution(), mensagem_voz_nao_configurada(), [INOVAÇÃO] Transcrição de áudio para o canal WhatsApp do operador.  Fluxo: 1. Ba, Mensagem amigável quando a transcrição não está disponível., Baixa e transcreve um áudio do WhatsApp.      Args:         message_data: dict c (+226 more)

### Community 4 - "Financial Categories & Repository"
Cohesion: 0.06
Nodes (276): Retorna o backend atual: 'redis' ou 'memory'., CategoriaFinanceiraRepository, atualizar_categoria(), atualizar_conta(), atualizar_despesa(), buscar_clientes(), buscar_orcamentos(), cancelar_conta() (+268 more)

### Community 5 - "Appointment Schemas & Data Models"
Cohesion: 0.05
Nodes (226): AgendamentoCalendario, AgendamentoComOpcoes, AgendamentoCreate, AgendamentoCreateComOpcoes, AgendamentoDashboard, AgendamentoOpcaoCreate, AgendamentoOpcaoOut, AgendamentoOut (+218 more)

### Community 6 - "Core Configuration & Middlewares"
Cohesion: 0.02
Nodes (84): BaseHTTPMiddleware, BaseSettings, _compute_version(), Config, get_pricing_public(), Usa o hash curto do último commit git como versão. Fallback: 'dev'., Retorna configuração pública de preços/limites para a landing., Envia um e-mail de teste para o endereço informado.     Use para validar SMTP (B (+76 more)

### Community 7 - "Context7 SDK & Client Infrastructure"
Cohesion: 0.02
Nodes (55): Context7, Command, Context7 CLI, Context7Agent, Context7 SDK, formatLibraryAsText(), getTrustScoreLabel(), detectVendorSpecificAgents() (+47 more)

### Community 8 - "AI Hub & Assistant Orchestration"
Cohesion: 0.02
Nodes (66): ABC, COTTE AI Hub, IA Service (LiteLLM), COTTE FastAPI Application, SendResult, _acao_adicionar_item(), _acao_aprovar(), _acao_criar() (+58 more)

### Community 9 - "Commercial Dashboard & Modal Logic"
Cohesion: 0.04
Nodes (106): abrirConfirmacaoReenvioProposta(), abrirContatosImportados(), abrirDetalhe(), abrirImportacaoLeads(), abrirModalCampanha(), abrirModalEmail(), abrirModalLead(), abrirModalLembrete() (+98 more)

### Community 10 - "MCP Fetch & Server Testing"
Cohesion: 0.02
Nodes (53): Tests for the fetch MCP server., Tests for get_robots_txt_url function., Tests for fetch_url function., Test with a simple URL., Test with URL containing path., When no repository restriction is configured, any path should be allowed., When repo_path exactly matches allowed_repository, validation should pass., When repo_path is a subdirectory of allowed_repository, validation should pass. (+45 more)

### Community 11 - "Settings UI & Preferences"
Cohesion: 0.04
Nodes (59): abrirPreviewTemplatePublico(), atualizarBtnTema(), atualizarPreview(), atualizarPreviewForma(), atualizarPreviewNumero(), atualizarVisualizacaoTema(), _buildMockOrcamentoPublico(), _buildStaticPreviewExtras() (+51 more)

### Community 12 - "Robust JSON Extraction Strategy"
Cohesion: 0.03
Nodes (62): extract(), _extract_balanced_json(), _extract_first_last_brace(), _extract_from_codeblock(), _extract_greedy_json(), extract_json_from_ai_response(), extract_with_metadata(), JSONExtractionStrategy (+54 more)

### Community 13 - "Frontend API Client & Utils"
Cohesion: 0.06
Nodes (39): apiRequest(), baixarExportar(), buildAbsoluteAppUrl(), buildApiRequestUrl(), buildPublicAssetUrl(), carregarSidebar(), coerceFetchUrlIfMixedContent(), downloadSkill() (+31 more)

### Community 14 - "Lead Management & Sales Funnel"
Cohesion: 0.07
Nodes (46): abrirDetalhe(), abrirModalEnviarProposta(), abrirModalLead(), adicionarObservacao(), alterarScore(), alterarStatusLead(), analisar_importacao(), arquivar_lead() (+38 more)

### Community 15 - "Community 15"
Cohesion: 0.06
Nodes (15): admin_client(), make_lead(), make_origem(), make_segmento(), make_template(), nonadmin_client(), _superadmin_user(), test_enviar_email() (+7 more)

### Community 16 - "Community 16"
Cohesion: 0.13
Nodes (42): atualizar_modulo(), atualizar_plano(), criar_modulo(), criar_plano(), deletar_plano(), listar_modulos(), listar_planos(), Atualiza um plano/pacote e seus módulos associados. (+34 more)

### Community 17 - "Community 17"
Cohesion: 0.08
Nodes (40): Registro de eventos de webhook já processados (idempotência).      Garante que c, WebhookEvent, _brl(), _enriquecer_orcamento(), gerar_pdf_fpdf2(), gerar_pdf_orcamento(), gerar_pdf_weasyprint(), _hex_to_rgb() (+32 more)

### Community 18 - "Community 18"
Cohesion: 0.1
Nodes (39): brevo_api_habilitado(), email_habilitado(), enviar_email_boas_vindas(), enviar_email_confirmacao_aceite(), enviar_email_reset_senha(), enviar_email_teste(), enviar_orcamento_por_email(), enviar_otp_aceite() (+31 more)

### Community 19 - "Community 19"
Cohesion: 0.1
Nodes (36): exigir_permissao_mock(), MockObjeto, MockUsuario, Permissão 'meus' deve satisfazer exigência de 'leitura'., Permissão 'meus' não deve satisfazer exigência de 'escrita'., Permissão 'escrita' deve satisfazer exigência de 'leitura'., Permissão 'admin' deve satisfazer todos os níveis., Mock local de verificar_ownership (mesma lógica de auth.py). (+28 more)

### Community 20 - "Community 20"
Cohesion: 0.08
Nodes (9): Testes das funções auxiliares puras (sem banco, sem HTTP).  Cobre: - _calcular_t, Valida que o formato segue ORC-{seq}-{ano2d}., Importa a função diretamente para testar sem HTTP., TestCalcularTotal, TestClientePorTelefone, TestDigitosTelefone, TestEmpresaPorOperador, TestFormatoNumeroOrcamento (+1 more)

### Community 21 - "Community 21"
Cohesion: 0.08
Nodes (21): ensureConfigDir(), errorPage(), escapeHtml(), exigir_modulo(), exigir_permissao(), fetchWhoami(), garantir_acesso_empresa_nao_expirado(), get_usuario_atual() (+13 more)

### Community 22 - "Community 22"
Cohesion: 0.17
Nodes (35): _adicionar_item_orcamento(), _aprovar_orcamento_via_bot(), _brl_fmt(), _buscar_orcamento(), _calcular_total(), _cliente_por_telefone(), _confirmar_aceite_pendente(), _criar_orcamento_via_bot() (+27 more)

### Community 23 - "Community 23"
Cohesion: 0.12
Nodes (26): applyAdaptiveMessagePlaceholder(), _buildAssistenteContext(), captureAssistenteResponseContext(), _extractAssistenteCommand(), _extractAssistenteEntityFromResponse(), _extractAssistenteEntityFromText(), getAdaptiveMessagePlaceholder(), handleAssistenteChatScroll() (+18 more)

### Community 24 - "Community 24"
Cohesion: 0.1
Nodes (30): abrirDocumento(), abrirModalEditarDocumento(), abrirModalNovoDocumento(), abrirPreviewDocumento(), alternarTipoConteudoDocumento(), _apiDownloadBlob(), _apiUpload(), aplicarFiltrosDocumentos() (+22 more)

### Community 25 - "Community 25"
Cohesion: 0.12
Nodes (28): add_seen_suggestions(), append(), append_db(), build(), build_context(), _build_dynamic_profile(), _cache_get(), _cache_key() (+20 more)

### Community 26 - "Community 26"
Cohesion: 0.12
Nodes (20): adicionarBlocoCustomizado(), adicionarVariavelProposta(), atualizarCampoBloco(), atualizarConfigBloco(), atualizarOrdemBlocos(), atualizarVariavelProposta(), carregarPropostasPublicas(), configurarDragAndDropBlocos() (+12 more)

### Community 27 - "Community 27"
Cohesion: 0.12
Nodes (28): AI Tool: criar_orcamento, _args_hash(), _cache_get(), _cache_prune(), _cache_put(), _check_rate_limit(), _consume_token(), execute() (+20 more)

### Community 28 - "Community 28"
Cohesion: 0.07
Nodes (14): limpar_cache_kb(), Testes de regressão: conhecimento de funcionalidades do assistente IA.  Valida q, Scoring deve limitar a 3 seções no máximo., Mensagem sem keywords não deve retornar seções., Verifica que a knowledge_base.md é carregada corretamente., Segunda chamada deve retornar o mesmo objeto (cache)., Verifica que o _INTENT_MAP tem os mapeamentos corretos., Garante que o cache da KB seja recarregado a cada teste. (+6 more)

### Community 29 - "Community 29"
Cohesion: 0.09
Nodes (18): _build_redis_client(), cached(), CacheManager, generate_cache_key(), get_cached_config(), invalidate_cache_for_model(), Sistema de cache para repositórios e serviços. Implementa cache com Redis (fallb, Remove um item do cache. (+10 more)

### Community 30 - "Community 30"
Cohesion: 0.07
Nodes (3): Testes unitários para app/utils/whatsapp_sanitizer.py (SEC-05).  Cobre edge-case, TestSanitizarMensagem, TestSanitizarTelefone

### Community 31 - "Community 31"
Cohesion: 0.11
Nodes (6): ComercialTemplates, create_template(), delete_template(), list_templates(), preview_template(), update_template()

### Community 32 - "Community 32"
Cohesion: 0.1
Nodes (18): AIPromptLoader, get_prompt(), get_prompt_loader(), load_prompts(), PromptConfig, PromptLoader - COTTE AI Hub Etapa 3: Externalização de Prompts para arquivos YAM, Configuração de um prompt específico, Inicializa o PromptLoader.                  Args:             prompts_dir: Diret (+10 more)

### Community 33 - "Community 33"
Cohesion: 0.13
Nodes (1): ComercialCampanhas

### Community 34 - "Community 34"
Cohesion: 0.13
Nodes (1): OrcamentosTable

### Community 35 - "Community 35"
Cohesion: 0.13
Nodes (10): _agora_ts(), IaInterpretarRateLimiter, _now(), PublicEndpointRateLimiter, Rate limit para endpoints públicos sem autenticação (aceitar/recusar/ajuste)., Rate limit para o webhook WhatsApp (POST /whatsapp/webhook).     Limite mais gen, Rate limit para recuperação de senha.     Prioriza Redis (quando configurado) e, Rate limit para POST /whatsapp/interpretar (endpoint de teste sem autenticação). (+2 more)

### Community 36 - "Community 36"
Cohesion: 0.08
Nodes (4): Testes para os validators de EmpresaUpdate. Cobre: numero_prefixo, numero_prefix, TestDescontoMaxPercent, TestNumeroPrefixo, TestSemValidadores

### Community 37 - "Community 37"
Cohesion: 0.1
Nodes (8): escapeHtml(), escapeHtmlWithBreaks(), formatarData(), formatarDataRelativa(), formatarMoeda(), formatarMoedaCompacta(), formatSearchResult(), getSourceReputationLabel()

### Community 38 - "Community 38"
Cohesion: 0.17
Nodes (20): adicionarBlocoCustom(), adicionarVariavel(), atualizarOrdem(), carregarProposta(), cloneBlocos(), cloneVars(), configurarDragDrop(), esc() (+12 more)

### Community 39 - "Community 39"
Cohesion: 0.14
Nodes (14): Protocol, find_changed_packages(), gen_version(), generate_matrix(), generate_notes(), generate_version(), GitHashParamType, has_changes() (+6 more)

### Community 40 - "Community 40"
Cohesion: 0.17
Nodes (21): esperar_token(), log(), main(), Script de Testes para Envio de WhatsApp no Comercial  Uso:     cd sistema     .., Testa listagem de leads., Testa detalhes de um lead., Testa envio de WhatsApp individual., Testa CRUD de templates. (+13 more)

### Community 41 - "Community 41"
Cohesion: 0.15
Nodes (16): carregarOrigens(), carregarPipelineStagesUI(), carregarSegmentos(), editarOrigem(), editarPipelineStage(), editarSegmento(), excluirPipelineStage(), renderEtapasMobile() (+8 more)

### Community 42 - "Community 42"
Cohesion: 0.16
Nodes (19): admin_atualizar_template(), admin_criar_template(), admin_deletar_template(), admin_listar_templates(), importar_template_para_empresa(), _ler_custom(), listar_segmentos(), obter_template() (+11 more)

### Community 43 - "Community 43"
Cohesion: 0.17
Nodes (1): CacheService

### Community 44 - "Community 44"
Cohesion: 0.17
Nodes (19): apply_changes(), build_frontmatter(), detect_category(), detect_priority(), detect_status(), extract_frontmatter(), has_required_properties(), main() (+11 more)

### Community 45 - "Community 45"
Cohesion: 0.16
Nodes (18): Snapshot histórico das divergências entre models SQLAlchemy e banco., SchemaDriftSnapshot, analyze_schema_drift(), check_critical_schema_drift(), compare_schema_drift_snapshots(), generate_auto_fix_preview(), get_schema_drift_snapshot(), list_schema_drift_snapshots() (+10 more)

### Community 46 - "Community 46"
Cohesion: 0.19
Nodes (14): applySlashCommand(), _closePrefSheet(), _focusFirstPrefField(), _getAssistentePrefCard(), _getPrefBackdrop(), _getPrefFocusableElements(), hideSlashCommands(), initSlashCommands() (+6 more)

### Community 47 - "Community 47"
Cohesion: 0.17
Nodes (1): RightPanel

### Community 48 - "Community 48"
Cohesion: 0.2
Nodes (1): ChartsGrid

### Community 49 - "Community 49"
Cohesion: 0.14
Nodes (7): applyFileEdits(), createUnifiedDiff(), normalizeLineEndings(), resolveRelativePathAgainstAllowedDirectories(), SequentialThinkingServer, tailFile(), validatePath()

### Community 50 - "Community 50"
Cohesion: 0.23
Nodes (17): _build_quote_approved_message(), _buscar_usuario_ativo(), _context(), _format_brl(), _format_datetime_br(), handle_quote_status_changed(), handle_quote_unapproved(), has_quote_approval_notification_been_sent() (+9 more)

### Community 51 - "Community 51"
Cohesion: 0.22
Nodes (1): ComercialImport

### Community 52 - "Community 52"
Cohesion: 0.29
Nodes (13): _make_user(), _PingInput, Testes do tool_executor (Tool Use v2)., _run(), _tc(), test_destrutiva_com_token_executa(), test_destrutiva_sem_token_emite_pending(), test_forbidden() (+5 more)

### Community 53 - "Community 53"
Cohesion: 0.21
Nodes (10): escapeHtml(), hasHttpClient(), loadAssistentePreferences(), renderAssistentePreferencesCard(), saveAssistentePreferences(), sendMessage(), showAssistentePrefNotice(), syncAssistenteGearSavedBadge() (+2 more)

### Community 54 - "Community 54"
Cohesion: 0.18
Nodes (1): StatsRow

### Community 55 - "Community 55"
Cohesion: 0.17
Nodes (15): add_error_responses(), add_examples_to_schemas(), create_api_documentation(), enhance_openapi_schema(), enhance_schemas_descriptions(), generate_model_documentation(), get_model_example(), Utilitários para documentação automática OpenAPI. Melhora a documentação gerada (+7 more)

### Community 56 - "Community 56"
Cohesion: 0.17
Nodes (8): abrirDropdownAcoes(), fecharDropdownAcoes(), fecharLoading(), initGlobalListeners(), mostrarLoading(), showError(), showSuccess(), showToast()

### Community 57 - "Community 57"
Cohesion: 0.22
Nodes (9): analisar_leads(), gerar_resposta_bot(), IAService, interpretar_comando_operador(), interpretar_mensagem(), interpretar_tabela_catalogo(), Chat unificado com suporte completo a Tool Use / Function Calling, Streaming real de tokens (sem tool calling).          Retorna um async generator (+1 more)

### Community 58 - "Community 58"
Cohesion: 0.15
Nodes (4): formatarData(), formatarDataRelativa(), formatarMoeda(), formatarMoedaCompacta()

### Community 59 - "Community 59"
Cohesion: 0.23
Nodes (13): criar_preview_html(), extrair_variaveis_html(), gerar_valores_padrao(), processar_documento_html_com_variaveis(), Serviço para processamento de documentos HTML com substituição de variáveis.  Es, Gera valores padrão para variáveis com base em nomes comuns.          Args:, Extrai todas as variáveis do formato {nome_variavel} de um conteúdo HTML., Processa um documento HTML com variáveis, realizando validação e substituição. (+5 more)

### Community 60 - "Community 60"
Cohesion: 0.29
Nodes (12): checar_limite_orcamentos(), checar_limite_orcamentos_async(), checar_limite_usuarios(), _config_for_empresa(), exigir_ia_dashboard(), exigir_relatorios(), exigir_whatsapp_proprio(), _get_plan_defaults() (+4 more)

### Community 61 - "Community 61"
Cohesion: 0.29
Nodes (12): _run(), test_cadastrar_material_gera_id(), test_criar_parcelamento_pagar(), test_despesa_ciclo_completo(), test_duplicar_orcamento_cria_rascunho_novo(), test_duplicar_orcamento_not_found(), test_editar_cliente_atualiza_campos(), test_editar_cliente_sem_campos() (+4 more)

### Community 62 - "Community 62"
Cohesion: 0.23
Nodes (8): abrirModalEmail(), abrirModalWhatsApp(), carregarTemplates(), editarTemplate(), excluirTemplate(), populateTplSelect(), renderTemplatesMobile(), salvarTemplate()

### Community 63 - "Community 63"
Cohesion: 0.23
Nodes (11): _crc16(), _emv_field(), gerar_payload_pix(), gerar_qrcode_pix(), Serviço para geração de QR codes PIX no padrão EMV BRCode (Bacen).  O payload se, Gera QR Code PIX válido (padrão EMV BRCode) e retorna como base64 PNG.      Args, Formata um campo EMV TLV: ID (2 chars) + Length (2 chars) + Value., Remove acentos e caracteres não-ASCII; retorna uppercase sem pontuação. (+3 more)

### Community 64 - "Community 64"
Cohesion: 0.3
Nodes (1): ChatVirtualizer

### Community 65 - "Community 65"
Cohesion: 0.26
Nodes (8): abrirDetalhesOrcamento(), _carregarContasOrcamento(), _carregarDocumentosDetalhes(), confirmarDesaprovar(), fecharDetalhes(), _renderizarHistoricoPagamentos(), _renderizarProgressoPagamentos(), sincronizarDocumento()

### Community 66 - "Community 66"
Cohesion: 0.21
Nodes (5): bindTabEvents(), carregarCadastrosCache(), esc(), reconstruirStatusMaps(), switchTab()

### Community 67 - "Community 67"
Cohesion: 0.23
Nodes (10): carregarPipeline(), create_pipeline_stage(), delete_pipeline_stage(), dropCard(), kanbanCard(), list_pipeline_stages(), renderKanban(), reorder_pipeline_stages() (+2 more)

### Community 68 - "Community 68"
Cohesion: 0.35
Nodes (10): _detectar_resposta_poll(), _enviar_resposta(), _limpar_pending_wpp(), _mensagem_confirmacao_whatsapp(), processar_operador_wpp(), Monta texto da enquete com contexto operacional (cliente, orçamento, alterações), _recuperar_pending_wpp(), _salvar_pending_wpp() (+2 more)

### Community 69 - "Community 69"
Cohesion: 0.27
Nodes (8): atribuir_papel_a_usuario(), atualizar_papel(), criar_papel(), _exigir_gestor(), listar_modulos_disponiveis(), listar_papeis(), _modulos_do_plano(), _slugify()

### Community 70 - "Community 70"
Cohesion: 0.18
Nodes (3): Testes: webhook Kiwify → bloqueio/ativação de empresa + check 402 em auth.  Cená, Desenvolvimento: token vazio não bloqueia; ENVIRONMENT fora de produção., sem_kiwify_token()

### Community 71 - "Community 71"
Cohesion: 0.18
Nodes (0): 

### Community 72 - "Community 72"
Cohesion: 0.27
Nodes (4): installCommand(), logInstallSummary(), searchCommand(), suggestCommand()

### Community 73 - "Community 73"
Cohesion: 0.4
Nodes (9): downloadSkillFromGitHub(), fetchDefaultBranch(), fetchRepoTree(), getGitHubHeaders(), getGitHubToken(), getSkillFromGitHub(), listSkillsFromGitHub(), parseGitHubUrl() (+1 more)

### Community 74 - "Community 74"
Cohesion: 0.22
Nodes (2): fetchRule(), getRuleContent()

### Community 75 - "Community 75"
Cohesion: 0.2
Nodes (9): Script de teste para verificar o middleware de segurança. Testa se caminhos susp, Testa se caminhos do WordPress são bloqueados., Testa se caminhos normais continuam funcionando., Testa rate limiting (simulação básica)., Testa bloqueio de user agents maliciosos., test_malicious_user_agents(), test_normal_paths(), test_rate_limiting() (+1 more)

### Community 76 - "Community 76"
Cohesion: 0.38
Nodes (9): formatAIResponse(), renderAnaliseTexto(), renderOnboarding(), renderOperadorResultado(), renderOrcamentoAtualizado(), renderOrcamentoCriado(), renderOrcamentoPreview(), renderSaldoRapido() (+1 more)

### Community 77 - "Community 77"
Cohesion: 0.31
Nodes (6): createGlobalOverlay(), getNovoOrcamentoContent(), getNovoOrcamentoFooter(), init(), registerModals(), setupGlobalEvents()

### Community 78 - "Community 78"
Cohesion: 0.28
Nodes (4): appendTomlServer(), buildTomlServerBlock(), readJsonConfig(), stripJsonComments()

### Community 79 - "Community 79"
Cohesion: 0.22
Nodes (8): Testa a interpretação de um comando do operador para ver um orçamento., Testa o endpoint /ai/orcamento/interpretar., Testa o endpoint /ai/operador/comando., Testa a extração de dados de orçamento de uma mensagem em linguagem natural., test_interpretar_comando_operador_ver_orcamento(), test_interpretar_mensagem_sucesso(), test_route_comando_operador_sucesso(), test_route_interpretar_orcamento_sucesso()

### Community 80 - "Community 80"
Cohesion: 0.22
Nodes (2): test_orcamento_create_sem_agendamento_modo_valida(), TestResolverAgendamentoModoCriacao

### Community 81 - "Community 81"
Cohesion: 0.32
Nodes (7): Service para lógica de negócio do catálogo de serviços/produtos., Cria categorias padrão para empresa recém-criada (idempotente)., Cria serviços de demonstração para empresa recém-criada (idempotente)., Executa todos os seeds padrão do catálogo para uma empresa., seed_catalogo_padrao(), _seed_categorias_padrao(), _seed_servicos_demonstracao()

### Community 82 - "Community 82"
Cohesion: 0.25
Nodes (7): aplicar_desconto(), erro_validacao_desconto(), Validação e cálculo de desconto em orçamentos (NEG-05)., Limite de desconto efetivo: primeiro do usuário, depois da empresa, depois 100., Retorna mensagem de erro se o desconto for inválido; None se válido.     - Perce, Retorna o total após aplicar o desconto (usa Decimal para precisão monetária)., resolver_max_percent_desconto()

### Community 83 - "Community 83"
Cohesion: 0.32
Nodes (6): _coluna_existe(), _fk_existe(), add categoria_id to servicos  Revision ID: 20260323_categoria_id_servicos Revise, Verifica se uma coluna já existe na tabela., Verifica se uma foreign key já existe., upgrade()

### Community 84 - "Community 84"
Cohesion: 0.39
Nodes (7): check_sensitive_file(), log_alert(), main(), Retorna alerta se o arquivo é sensível., Registra alertas em ~/.claude/parry_alerts.log., Retorna lista de alertas encontrados no texto., scan_text()

### Community 85 - "Community 85"
Cohesion: 0.43
Nodes (7): abrirModalReenvioOrcamento(), bindReenvioModalHandlers(), cotteConfirmarReenvioSeNecessario(), fecharModalReenvioOrcamento(), mensagemFallback(), onKeydownReenvio(), precisaConfirmarReenvioOrcamento()

### Community 86 - "Community 86"
Cohesion: 0.32
Nodes (1): TooltipManager

### Community 87 - "Community 87"
Cohesion: 0.25
Nodes (8): Núcleo de Autenticação JWT, Configuração de Banco de Dados, Middleware de Segurança, Router Administrativo (Superadmin), Router Unificado de IA, Router de Acesso Público, Schemas Gerais (Cliente, Orçamento, Auth), Utilitários de PDF

### Community 88 - "Community 88"
Cohesion: 0.62
Nodes (6): checar_limite_ia(), checar_limite_orcamentos(), checar_limite_usuarios(), checar_limite_whatsapp(), get_plano_empresa(), verificar_modulo()

### Community 89 - "Community 89"
Cohesion: 0.57
Nodes (6): _column_exists(), downgrade(), _index_exists(), feat: sistema de papeis RBAC (acoes nos modulos + tabela papeis + papel_id em us, _table_exists(), upgrade()

### Community 90 - "Community 90"
Cohesion: 0.29
Nodes (1): Testes da máquina de estados compartilhada (API + bot).

### Community 91 - "Community 91"
Cohesion: 0.48
Nodes (5): _orc_aprovado_com_parcelas(), test_idempotencia_retorna_mesmo_pagamento(), test_parcela_numero_forca_conta_correta(), test_registrar_pagamento_rejeita_valor_acima_saldo_parcela(), test_registrar_pagamento_respeita_ordem_parcelas()

### Community 92 - "Community 92"
Cohesion: 0.29
Nodes (0): 

### Community 93 - "Community 93"
Cohesion: 0.33
Nodes (2): _brl(), formatPendingArgs()

### Community 94 - "Community 94"
Cohesion: 0.52
Nodes (6): carregarDashboard(), carregarNovosClientes(), irParaLeadsComFiltro(), renderActionList(), renderMetrics(), renderRecentList()

### Community 95 - "Community 95"
Cohesion: 0.4
Nodes (2): detectAgents(), pathExists()

### Community 96 - "Community 96"
Cohesion: 0.33
Nodes (5): Sanitização de inputs não-confiáveis recebidos pelo webhook do WhatsApp.  SEC-05, Extrai apenas dígitos do telefone e valida o comprimento.     Retorna a string d, Remove bytes nulos e caracteres de controle (exceto \\t, \\n, \\r),     normaliz, sanitizar_mensagem(), sanitizar_telefone()

### Community 97 - "Community 97"
Cohesion: 0.33
Nodes (5): Máquina de estados de orçamento — transições compartilhadas entre API e bot., Retorna True se a transição de status for permitida pela máquina de estados (ide, Mensagem quando a transição não é permitida (HTTP ou bot WhatsApp/dashboard)., texto_transicao_negada(), transicao_permitida()

### Community 98 - "Community 98"
Cohesion: 0.33
Nodes (5): downgrade(), add_commercial_fk_tables  Revision ID: 9e5c2d29991b Revises: 5f2d3c4b1a9e Create, Adiciona colunas ativo, segmento_id e origem_lead_id ao commercial_leads.     Ta, Remove as colunas adicionadas (tabelas não são dropadas pois pertencem a outra m, upgrade()

### Community 99 - "Community 99"
Cohesion: 0.4
Nodes (4): _coluna_existe(), Add document tracking fields to orcamento_documentos  Revision ID: 20260323_doc_, Verifica se uma coluna já existe na tabela., upgrade()

### Community 100 - "Community 100"
Cohesion: 0.33
Nodes (5): downgrade(), add_status_envio_commercial_leads  Adiciona coluna status_envio à tabela commerc, Adiciona coluna status_envio se não existir., Remove coluna status_envio., upgrade()

### Community 101 - "Community 101"
Cohesion: 0.33
Nodes (5): downgrade(), Add commercial leads and interactions tables  Revision ID: 002_add_comercial_tab, Cria tabelas commercial_leads e commercial_interactions., Remove tabelas commercial_interactions e commercial_leads., upgrade()

### Community 102 - "Community 102"
Cohesion: 0.4
Nodes (4): _coluna_existe(), add preco_custo to servicos  Revision ID: 20260323_preco_custo Revises: 20260323, Verifica se uma coluna já existe na tabela., upgrade()

### Community 103 - "Community 103"
Cohesion: 0.4
Nodes (4): column_exists(), add campaigns tables  Revision ID: b66af2e00a10 Revises: f4ef69a06e14 Create Dat, Verifica se uma coluna existe na tabela., upgrade()

### Community 104 - "Community 104"
Cohesion: 0.33
Nodes (5): downgrade(), Initial schema (baseline) — create_all a partir dos models atuais.  Banco já exi, Cria todas as tabelas a partir de Base.metadata (models atuais)., Remove todas as tabelas (ordem inversa de dependências)., upgrade()

### Community 105 - "Community 105"
Cohesion: 0.33
Nodes (5): downgrade(), fix_status_envio_column  Corrige referência à coluna status_envio que não existe, Remove referência à coluna status_envio que não existe., Recria a referência problemática (não recomendado)., upgrade()

### Community 106 - "Community 106"
Cohesion: 0.33
Nodes (5): downgrade(), Add commercial segments, lead sources, templates, reminders, config tables and e, Remove tabelas e colunas adicionadas., Cria tabelas auxiliares e estende commercial_leads., upgrade()

### Community 107 - "Community 107"
Cohesion: 0.33
Nodes (5): downgrade(), fix_missing_commercial_leads_columns_again  Corrige problemas de integridade no, Remove correções (não recomendado em produção)., Corrige tabelas e colunas do módulo comercial., upgrade()

### Community 108 - "Community 108"
Cohesion: 0.47
Nodes (5): main(), Testa se o comando 'ajuda' é interpretado corretamente., Testa se as novas ações são reconhecidas., test_ajuda(), test_novas_acoes()

### Community 109 - "Community 109"
Cohesion: 0.33
Nodes (6): Frontend API Service Layer, AI Assistant Tool Actions, AI Assistant Core Logic, AI Assistant UI Rendering, Frontend Cache Service, Commercial Pipeline UI

### Community 110 - "Community 110"
Cohesion: 0.8
Nodes (4): build_destructive_extras(), _mudancas_editar_item(), _mudancas_editar_orcamento(), _safe_float()

### Community 111 - "Community 111"
Cohesion: 0.4
Nodes (3): merge heads  Revision ID: 20260323_merge_heads Revises: 20260323_preco_custo, z_, Merge das duas heads - não faz nada, apenas une as branches, upgrade()

### Community 112 - "Community 112"
Cohesion: 0.4
Nodes (1): Throttle de presença (ultima_atividade_em) em get_usuario_atual.

### Community 113 - "Community 113"
Cohesion: 0.4
Nodes (1): Fila de pré-agendamento pós-aprovação (z018).

### Community 114 - "Community 114"
Cohesion: 0.7
Nodes (4): _make_superadmin(), test_schema_drift_auto_fix_preview_dry_run(), test_schema_drift_endpoint_preserva_contrato(), test_schema_drift_snapshots_list_detail_compare()

### Community 115 - "Community 115"
Cohesion: 0.7
Nodes (4): _checkVersion(), _createBanner(), _init(), _showBanner()

### Community 116 - "Community 116"
Cohesion: 0.4
Nodes (0): 

### Community 117 - "Community 117"
Cohesion: 0.5
Nodes (2): beginSimulatedResourceUpdates(), sendSimulatedResourceUpdates()

### Community 118 - "Community 118"
Cohesion: 0.6
Nodes (3): generateResearchReport(), getInterpretationsForTopic(), runResearchProcess()

### Community 119 - "Community 119"
Cohesion: 0.83
Nodes (3): encryptClientIp(), generateHeaders(), validateEncryptionKey()

### Community 120 - "Community 120"
Cohesion: 0.5
Nodes (3): gerar_csv_response(), Utilitários centralizados para geração de CSV.  Elimina duplicação do padrão io., Gera StreamingResponse CSV com delimitador ponto-e-vírgula.      Args:         h

### Community 121 - "Community 121"
Cohesion: 0.5
Nodes (1): add missing FK indexes for performance  Revision ID: z003_add_missing_fk_indexes

### Community 122 - "Community 122"
Cohesion: 0.5
Nodes (1): add missing columns after stamp  Revision ID: e60f737b701c Revises: 001_initial

### Community 123 - "Community 123"
Cohesion: 0.5
Nodes (1): feat: adiciona valor_sinal_pix ao orcamento  Revision ID: e5b94f17c814 Revises:

### Community 124 - "Community 124"
Cohesion: 0.5
Nodes (1): feat: adicionar tabela bancos_pix_empresa  Revision ID: 9f0c_add_bancos_pix_empr

### Community 125 - "Community 125"
Cohesion: 0.5
Nodes (1): merge all heads  Revision ID: z020_merge_all_heads Revises: r002_fix_status_orca

### Community 126 - "Community 126"
Cohesion: 0.5
Nodes (1): fix trigger: adiciona cast ::statusconta nas strings do CASE  Revision ID: i002

### Community 127 - "Community 127"
Cohesion: 0.5
Nodes (1): add_conteudo_html_tipo_conteudo_to_documentos_empresa  Revision ID: b0bac86d4955

### Community 128 - "Community 128"
Cohesion: 0.5
Nodes (1): Pre-agendamento: fila, canal de aprovação, liberação manual.  Revision ID: z018_

### Community 129 - "Community 129"
Cohesion: 0.5
Nodes (1): fix: remove unique constraint global em orcamentos.numero e cria index por empre

### Community 130 - "Community 130"
Cohesion: 0.5
Nodes (1): merge: unifica todos os heads antes do agendamento_modo  Revision ID: w001_merge

### Community 131 - "Community 131"
Cohesion: 0.5
Nodes (1): perf: adiciona índices em empresa_id e compostos para queries multi-tenant  Revi

### Community 132 - "Community 132"
Cohesion: 0.5
Nodes (1): feat: configuracoes flexiveis de otp  Revision ID: a60e82cc379b Revises: 1913bf7

### Community 133 - "Community 133"
Cohesion: 0.5
Nodes (1): fix missing lead_score column for legacy commercial_leads schemas  Migration def

### Community 134 - "Community 134"
Cohesion: 0.5
Nodes (1): tool_call_log  Revision ID: tc001_tool_call_log Revises: e9021f88a7c2 Create Dat

### Community 135 - "Community 135"
Cohesion: 0.5
Nodes (1): add_agendamento_opcoes  Revision ID: 9efd81e17334 Revises: a90994237bcc Create D

### Community 136 - "Community 136"
Cohesion: 0.5
Nodes (1): Cria tabela config_global para configurações persistentes da plataforma.  Revisi

### Community 137 - "Community 137"
Cohesion: 0.5
Nodes (1): add_telefone_operador_to_usuario  Adiciona campo telefone_operador na tabela usu

### Community 138 - "Community 138"
Cohesion: 0.5
Nodes (1): feat: documentos da empresa  Revision ID: b8c1d2e3f4a5 Revises: a07fa98d3427 Cre

### Community 139 - "Community 139"
Cohesion: 0.5
Nodes (1): Cria tabela feedback_assistente para avaliações do assistente IA.  Revision ID:

### Community 140 - "Community 140"
Cohesion: 0.5
Nodes (1): feat: adicionar PIX aos orcamentos  Revision ID: 2dc96d88fe32 Revises: a9b8c7d6e

### Community 141 - "Community 141"
Cohesion: 0.5
Nodes (1): fix: permite superadmin sem empresa vinculada (empresa_id nullable em usuarios)

### Community 142 - "Community 142"
Cohesion: 0.5
Nodes (1): feat: regras de pagamento — campos em formas, snapshot no orçamento, tipo_lancam

### Community 143 - "Community 143"
Cohesion: 0.5
Nodes (1): Add agendamento_escolha_obrigatoria to empresas.  Revision ID: z016_agendamento_

### Community 144 - "Community 144"
Cohesion: 0.5
Nodes (1): add_criado_por_id_clientes  Revision ID: p002_add_criado_por_id_clientes Revises

### Community 145 - "Community 145"
Cohesion: 0.5
Nodes (1): feat: pagamentos — empresa_id, chave de idempotência e índice único  Revision ID

### Community 146 - "Community 146"
Cohesion: 0.5
Nodes (1): fix: orcamento_documentos.arquivo_path nullable para documentos HTML  Revision I

### Community 147 - "Community 147"
Cohesion: 0.5
Nodes (1): add performance indices orcamentos_empresa_criado and notificacoes_empresa_lida

### Community 148 - "Community 148"
Cohesion: 0.5
Nodes (1): add_cupom_kiwify_to_empresa  Revision ID: 25a618cb66f6 Revises: i001 Create Date

### Community 149 - "Community 149"
Cohesion: 0.5
Nodes (1): Popula permissoes padrão para operadores que não têm as chaves básicas.  Garante

### Community 150 - "Community 150"
Cohesion: 0.5
Nodes (1): merge commercial and empresas heads  Revision ID: 5f2d3c4b1a9e Revises: 003_add_

### Community 151 - "Community 151"
Cohesion: 0.5
Nodes (1): Amplia alembic_version.version_num para VARCHAR(255).  O PostgreSQL padrão do Al

### Community 152 - "Community 152"
Cohesion: 0.5
Nodes (1): pipeline_stages: cria tabela e migra status_pipeline para VARCHAR  Revision ID:

### Community 153 - "Community 153"
Cohesion: 0.5
Nodes (1): fix: corrige valores do enum statusorcamento para maiusculo  Revision ID: r002_f

### Community 154 - "Community 154"
Cohesion: 0.5
Nodes (1): feat: unique constraint parcial para padrao_pix por empresa  Garante que apenas

### Community 155 - "Community 155"
Cohesion: 0.5
Nodes (1): normalize_emails_lowercase  Revision ID: b53c78511b78 Revises: o001_add_campos_f

### Community 156 - "Community 156"
Cohesion: 0.5
Nodes (1): Adiciona tabela categorias_catalogo e colunas categoria_id/preco_custo em servic

### Community 157 - "Community 157"
Cohesion: 0.5
Nodes (1): add_status_aguardando_escolha  Revision ID: 2420bef5d6a4 Revises: 9efd81e17334 C

### Community 158 - "Community 158"
Cohesion: 0.5
Nodes (1): fix trigger: conta_financeira_id -> conta_id em pagamentos_financeiros  Revision

### Community 159 - "Community 159"
Cohesion: 0.5
Nodes (1): add_notif_whats_visualizacao_to_empresas  Revision ID: ac64aef565f2 Revises: e60

### Community 160 - "Community 160"
Cohesion: 0.5
Nodes (1): alter_arquivo_path_nullable_for_html_documents  Revision ID: 9d6276e279b2 Revise

### Community 161 - "Community 161"
Cohesion: 0.5
Nodes (1): merge z003 FK indexes head with z003 merge head  Revision ID: z004_merge_z003_he

### Community 162 - "Community 162"
Cohesion: 0.5
Nodes (1): remove_orcamentos_agendamento_fk  Revision ID: a90994237bcc Revises: 407429405c0

### Community 163 - "Community 163"
Cohesion: 0.5
Nodes (1): Add enviar_pdf_whatsapp to empresa  Revision ID: b4255a56f865 Revises: 9d9578b69

### Community 164 - "Community 164"
Cohesion: 0.5
Nodes (1): feat: adiciona pix_payload ao orcamento (EMV BRCode)  Revision ID: 8f19ab3f4b99

### Community 165 - "Community 165"
Cohesion: 0.5
Nodes (1): add_permissoes_column_usuario  Revision ID: p001_add_permissoes_column_usuario R

### Community 166 - "Community 166"
Cohesion: 0.5
Nodes (1): feat: adicionar campos de OTP para aceite público  Revision ID: 1913bf78d9a7 Rev

### Community 167 - "Community 167"
Cohesion: 0.5
Nodes (1): add_missing_empresa_columns  Revision ID: p003_add_missing_empresa_columns Revis

### Community 168 - "Community 168"
Cohesion: 0.5
Nodes (1): fix_antecedencia_minima_horas_default  Revision ID: ag001_fix_antecedencia Revis

### Community 169 - "Community 169"
Cohesion: 0.5
Nodes (1): Add template_publico to empresas  Revision ID: z012_template_publico Revises: 60

### Community 170 - "Community 170"
Cohesion: 0.5
Nodes (1): Criar tabelas ai_chat_sessoes e ai_chat_mensagens para persistência de sessões d

### Community 171 - "Community 171"
Cohesion: 0.5
Nodes (1): add schema drift snapshots  Revision ID: c6121d569572 Revises: 3344d22be19b Crea

### Community 172 - "Community 172"
Cohesion: 0.5
Nodes (1): feat: adiciona status em_execucao e aguardando_pagamento ao StatusOrcamento  Rev

### Community 173 - "Community 173"
Cohesion: 0.5
Nodes (1): feat: número de orçamento personalizável por empresa  Adiciona: - Empresa: numer

### Community 174 - "Community 174"
Cohesion: 0.5
Nodes (1): feat: módulo financeiro — formas de pagamento, contas e pagamentos  Revision ID:

### Community 175 - "Community 175"
Cohesion: 0.5
Nodes (1): feat: adiciona assinatura_email a empresa  Revision ID: a07fa98d3427 Revises: 8f

### Community 176 - "Community 176"
Cohesion: 0.5
Nodes (1): feat: add planes and modules system  Revision ID: e11faf9b0ad1 Revises: z010_con

### Community 177 - "Community 177"
Cohesion: 0.5
Nodes (1): Adiciona SUBSTITUIDA ao enum statusproposta (reenvio forçado)  Revision ID: e902

### Community 178 - "Community 178"
Cohesion: 0.5
Nodes (1): fix: preencher_tipo_categorias_nulas  Revision ID: f985249b1289 Revises: j001 Cr

### Community 179 - "Community 179"
Cohesion: 0.5
Nodes (1): Fase 1 e 2 - Melhorias Financeiro  Revision ID: j001 Revises: i002 Create Date:

### Community 180 - "Community 180"
Cohesion: 0.5
Nodes (1): refactor_monetary_to_numeric_and_sync  Revision ID: 1548e7057e6c Revises: z005_s

### Community 181 - "Community 181"
Cohesion: 0.5
Nodes (1): add_agendamentos_module  Revision ID: 407429405c03 Revises: s002_superadmin_empr

### Community 182 - "Community 182"
Cohesion: 0.5
Nodes (1): merge p and e heads  Merge migration to resolve multiple heads: e11faf9b0ad1 and

### Community 183 - "Community 183"
Cohesion: 0.5
Nodes (1): feat: adicionar pix padrao a empresa  Revision ID: 8b8efeace516 Revises: 2dc96d8

### Community 184 - "Community 184"
Cohesion: 0.5
Nodes (1): add assistente_instrucoes to empresa  Revision ID: 3344d22be19b Revises: z021_ai

### Community 185 - "Community 185"
Cohesion: 0.5
Nodes (1): feat: automação de status de orçamento — colunas empresa  Revision ID: z015_auto

### Community 186 - "Community 186"
Cohesion: 0.5
Nodes (1): Cria tabela audit_logs e remove coluna perm_catalogo de usuarios.  Antes de remo

### Community 187 - "Community 187"
Cohesion: 0.5
Nodes (1): trigger recalcular valor_pago em contas_financeiras  Revision ID: h001 Revises:

### Community 188 - "Community 188"
Cohesion: 0.5
Nodes (1): merge z002 obrigatorio branch with pipeline/html arquivo_path head  Revision ID:

### Community 189 - "Community 189"
Cohesion: 0.5
Nodes (1): add obrigatorio to orcamento_documentos  Revision ID: z002_obrigatorio_doc (curt

### Community 190 - "Community 190"
Cohesion: 0.5
Nodes (1): Add utilizar_agendamento_automatico to empresas.  Revision ID: z017_utilizar_age

### Community 191 - "Community 191"
Cohesion: 0.5
Nodes (1): merge all heads  Merge migration para resolver os multiplos heads criados por br

### Community 192 - "Community 192"
Cohesion: 0.5
Nodes (1): Add agendamento_modo_padrao to empresas.  Reutiliza o enum PostgreSQL modoagenda

### Community 193 - "Community 193"
Cohesion: 0.5
Nodes (1): financeiro: parcelamento real, despesas, historico cobrancas, config financeira

### Community 194 - "Community 194"
Cohesion: 0.5
Nodes (1): add empresa_id to commercial_leads  Revision ID: e6ac99cf785c Revises: r001_add_

### Community 195 - "Community 195"
Cohesion: 0.5
Nodes (1): Adiciona status_pipeline em commercial_leads se ausente (legado / DB parcial).

### Community 196 - "Community 196"
Cohesion: 0.5
Nodes (1): merge 1548e7057e6c (monetary refactor) with m001 (feedback_assistente)  Revision

### Community 197 - "Community 197"
Cohesion: 0.5
Nodes (1): Adicionar models PropostaPublica, PropostaEnviada e PropostaVisualizacao  Revisi

### Community 198 - "Community 198"
Cohesion: 0.5
Nodes (1): Merge z006_audit_logs_remove_perm_catalogo e p003_add_missing_empresa_columns.

### Community 199 - "Community 199"
Cohesion: 0.5
Nodes (1): fix_commercial_leads_fk_columns  Revision ID: d60f6d62a957 Revises: 9e5c2d29991b

### Community 200 - "Community 200"
Cohesion: 0.5
Nodes (1): Add template_orcamento to empresa  Revision ID: 9d9578b69335 Revises: z018_pre_a

### Community 201 - "Community 201"
Cohesion: 0.5
Nodes (1): Set template_publico default to classico.  Revision ID: z013_template_publico_de

### Community 202 - "Community 202"
Cohesion: 0.5
Nodes (1): add aceite_pendente_em to orcamentos  Revision ID: g001 Revises: 9f0c_add_bancos

### Community 203 - "Community 203"
Cohesion: 0.5
Nodes (1): add campos fiscais ao cliente (tipo_pessoa, cpf, cnpj, razao_social, etc)  Revis

### Community 204 - "Community 204"
Cohesion: 0.5
Nodes (1): Add unique partial index to categoria_financeira  Revision ID: f4ef69a06e14 Revi

### Community 205 - "Community 205"
Cohesion: 0.5
Nodes (1): Add status_envio to CommercialLead  Revision ID: b633b63e31e4 Revises: b66af2e00

### Community 206 - "Community 206"
Cohesion: 0.5
Nodes (1): backfill_notif_whats_visualizacao_default  Revision ID: 00b953ce3024 Revises: ac

### Community 207 - "Community 207"
Cohesion: 0.5
Nodes (1): fix: add missing columns to orcamento_documentos  Revision ID: ba10b6a06e17 Revi

### Community 208 - "Community 208"
Cohesion: 0.5
Nodes (1): feat: agendamento_modo em orcamentos e usa_agendamento em config_agendamento  Ad

### Community 209 - "Community 209"
Cohesion: 0.83
Nodes (3): test_criar_documento_html(), test_fluxo_completo(), test_listar_documentos_html()

### Community 210 - "Community 210"
Cohesion: 0.67
Nodes (2): carregarLembretes(), salvarLembrete()

### Community 211 - "Community 211"
Cohesion: 0.83
Nodes (3): formatDirectoryError(), getValidRootDirectories(), parseRootUri()

### Community 212 - "Community 212"
Cohesion: 0.67
Nodes (2): convertToWindowsPath(), normalizePath()

### Community 213 - "Community 213"
Cohesion: 0.67
Nodes (2): getMimeType(), registerFileResources()

### Community 214 - "Community 214"
Cohesion: 0.5
Nodes (1): InMemoryEventStore

### Community 215 - "Community 215"
Cohesion: 0.5
Nodes (0): 

### Community 216 - "Community 216"
Cohesion: 0.5
Nodes (4): PIX Payment Integration, Agendamentos Module, Financeiro Module, Orcamentos Table

### Community 217 - "Community 217"
Cohesion: 0.67
Nodes (0): 

### Community 218 - "Community 218"
Cohesion: 0.67
Nodes (0): 

### Community 219 - "Community 219"
Cohesion: 0.67
Nodes (0): 

### Community 220 - "Community 220"
Cohesion: 0.67
Nodes (2): normalize_phone_number(), Normaliza para dígitos com DDI 55 (ex: 5548999887766).

### Community 221 - "Community 221"
Cohesion: 0.67
Nodes (2): Check if categorias endpoint is in OpenAPI spec, test_openapi_spec()

### Community 222 - "Community 222"
Cohesion: 0.67
Nodes (1): Agendamento automático respeita utilizar_agendamento_automatico da empresa.

### Community 223 - "Community 223"
Cohesion: 0.67
Nodes (2): check_endpoint(), Check if /financeiro/categorias endpoint exists

### Community 224 - "Community 224"
Cohesion: 0.67
Nodes (2): Test the /financeiro/categorias endpoint, test_categorias_endpoint()

### Community 225 - "Community 225"
Cohesion: 0.67
Nodes (0): 

### Community 226 - "Community 226"
Cohesion: 0.67
Nodes (1): GET /empresa/resumo-sidebar — payload agregado para a sidebar (1 round-trip).

### Community 227 - "Community 227"
Cohesion: 0.67
Nodes (1): Testes dos endpoints de Agendamentos — todos os 18 endpoints. Usa TestClient do

### Community 228 - "Community 228"
Cohesion: 0.67
Nodes (1): Migração: adiciona campos individuais de endereço na tabela 'clientes'.  Execute

### Community 229 - "Community 229"
Cohesion: 1.0
Nodes (2): inicializarLayout(), _renderSetupStrip()

### Community 230 - "Community 230"
Cohesion: 0.67
Nodes (0): 

### Community 231 - "Community 231"
Cohesion: 0.67
Nodes (0): 

### Community 232 - "Community 232"
Cohesion: 1.0
Nodes (2): checkSymlinkSupport(), getSymlinkSupport()

### Community 233 - "Community 233"
Cohesion: 0.67
Nodes (0): 

### Community 234 - "Community 234"
Cohesion: 0.67
Nodes (3): AI Assistant Configurations, Alembic Database Migrations, WhatsApp Notifications Logic

### Community 235 - "Community 235"
Cohesion: 0.67
Nodes (3): COTTE System Architecture, COTTE Product Roadmap, Rationale for Vanilla JS

### Community 236 - "Community 236"
Cohesion: 1.0
Nodes (0): 

### Community 237 - "Community 237"
Cohesion: 1.0
Nodes (0): 

### Community 238 - "Community 238"
Cohesion: 1.0
Nodes (0): 

### Community 239 - "Community 239"
Cohesion: 1.0
Nodes (0): 

### Community 240 - "Community 240"
Cohesion: 1.0
Nodes (0): 

### Community 241 - "Community 241"
Cohesion: 1.0
Nodes (0): 

### Community 242 - "Community 242"
Cohesion: 1.0
Nodes (0): 

### Community 243 - "Community 243"
Cohesion: 1.0
Nodes (0): 

### Community 244 - "Community 244"
Cohesion: 1.0
Nodes (0): 

### Community 245 - "Community 245"
Cohesion: 1.0
Nodes (0): 

### Community 246 - "Community 246"
Cohesion: 1.0
Nodes (0): 

### Community 247 - "Community 247"
Cohesion: 1.0
Nodes (0): 

### Community 248 - "Community 248"
Cohesion: 1.0
Nodes (0): 

### Community 249 - "Community 249"
Cohesion: 1.0
Nodes (0): 

### Community 250 - "Community 250"
Cohesion: 1.0
Nodes (0): 

### Community 251 - "Community 251"
Cohesion: 1.0
Nodes (0): 

### Community 252 - "Community 252"
Cohesion: 1.0
Nodes (0): 

### Community 253 - "Community 253"
Cohesion: 1.0
Nodes (0): 

### Community 254 - "Community 254"
Cohesion: 1.0
Nodes (0): 

### Community 255 - "Community 255"
Cohesion: 1.0
Nodes (0): 

### Community 256 - "Community 256"
Cohesion: 1.0
Nodes (0): 

### Community 257 - "Community 257"
Cohesion: 1.0
Nodes (0): 

### Community 258 - "Community 258"
Cohesion: 1.0
Nodes (0): 

### Community 259 - "Community 259"
Cohesion: 1.0
Nodes (0): 

### Community 260 - "Community 260"
Cohesion: 1.0
Nodes (0): 

### Community 261 - "Community 261"
Cohesion: 1.0
Nodes (0): 

### Community 262 - "Community 262"
Cohesion: 1.0
Nodes (0): 

### Community 263 - "Community 263"
Cohesion: 1.0
Nodes (0): 

### Community 264 - "Community 264"
Cohesion: 1.0
Nodes (0): 

### Community 265 - "Community 265"
Cohesion: 1.0
Nodes (0): 

### Community 266 - "Community 266"
Cohesion: 1.0
Nodes (0): 

### Community 267 - "Community 267"
Cohesion: 1.0
Nodes (0): 

### Community 268 - "Community 268"
Cohesion: 1.0
Nodes (0): 

### Community 269 - "Community 269"
Cohesion: 1.0
Nodes (0): 

### Community 270 - "Community 270"
Cohesion: 1.0
Nodes (0): 

### Community 271 - "Community 271"
Cohesion: 1.0
Nodes (0): 

### Community 272 - "Community 272"
Cohesion: 1.0
Nodes (0): 

### Community 273 - "Community 273"
Cohesion: 1.0
Nodes (0): 

### Community 274 - "Community 274"
Cohesion: 1.0
Nodes (0): 

### Community 275 - "Community 275"
Cohesion: 1.0
Nodes (0): 

### Community 276 - "Community 276"
Cohesion: 1.0
Nodes (0): 

### Community 277 - "Community 277"
Cohesion: 1.0
Nodes (0): 

### Community 278 - "Community 278"
Cohesion: 1.0
Nodes (0): 

### Community 279 - "Community 279"
Cohesion: 1.0
Nodes (0): 

### Community 280 - "Community 280"
Cohesion: 1.0
Nodes (0): 

### Community 281 - "Community 281"
Cohesion: 1.0
Nodes (2): Router Financeiro, Schemas Financeiros

### Community 282 - "Community 282"
Cohesion: 1.0
Nodes (2): Router de Relatórios, Máquina de Estados de Orçamento

### Community 283 - "Community 283"
Cohesion: 1.0
Nodes (2): Router de Agendamentos, Schemas de Agendamento

### Community 284 - "Community 284"
Cohesion: 1.0
Nodes (2): Proposal Builder Engine, Modern Proposal Template Logic

### Community 285 - "Community 285"
Cohesion: 1.0
Nodes (2): Everything MCP Server, Filesystem MCP Server

### Community 286 - "Community 286"
Cohesion: 1.0
Nodes (2): IA Assistant Knowledge Base, IA Assistant E2E Tests

### Community 287 - "Community 287"
Cohesion: 1.0
Nodes (2): COTTE Agents Operating Contract, Lore Commit Protocol

### Community 288 - "Community 288"
Cohesion: 1.0
Nodes (0): 

### Community 289 - "Community 289"
Cohesion: 1.0
Nodes (0): 

### Community 290 - "Community 290"
Cohesion: 1.0
Nodes (0): 

### Community 291 - "Community 291"
Cohesion: 1.0
Nodes (0): 

### Community 292 - "Community 292"
Cohesion: 1.0
Nodes (0): 

### Community 293 - "Community 293"
Cohesion: 1.0
Nodes (0): 

### Community 294 - "Community 294"
Cohesion: 1.0
Nodes (1): URL da imagem do serviço vinculado (catálogo), para exibir no orçamento.

### Community 295 - "Community 295"
Cohesion: 1.0
Nodes (1): Extrai JSON válido de texto da IA.                  Args:             text: Text

### Community 296 - "Community 296"
Cohesion: 1.0
Nodes (1): Tenta uma estratégia específica de extração

### Community 297 - "Community 297"
Cohesion: 1.0
Nodes (1): Extrai JSON de codeblocks markdown ```json ... ```

### Community 298 - "Community 298"
Cohesion: 1.0
Nodes (1): Extrai JSON usando regex com balanceamento de chaves.         Encontra o primeir

### Community 299 - "Community 299"
Cohesion: 1.0
Nodes (1): Extrai JSON localizando o primeiro '{' e o último '}'.         Útil quando a IA

### Community 300 - "Community 300"
Cohesion: 1.0
Nodes (1): Estratégia greedy - pega tudo entre o primeiro { e último }

### Community 301 - "Community 301"
Cohesion: 1.0
Nodes (1): Extrai JSON e retorna metadados sobre o processo.                  Returns:

### Community 302 - "Community 302"
Cohesion: 1.0
Nodes (1): Retorna o status de conexão da instância (deve incluir chave 'connected': bool).

### Community 303 - "Community 303"
Cohesion: 1.0
Nodes (1): Retorna o QR Code para conectar o WhatsApp (chave 'qrcode' em base64).

### Community 304 - "Community 304"
Cohesion: 1.0
Nodes (1): Desconecta a instância. Retorna True em caso de sucesso.

### Community 305 - "Community 305"
Cohesion: 1.0
Nodes (1): Envia texto simples. Retorna True em caso de sucesso.

### Community 306 - "Community 306"
Cohesion: 1.0
Nodes (1): Envia um arquivo PDF como anexo. Retorna True em caso de sucesso.

### Community 307 - "Community 307"
Cohesion: 1.0
Nodes (1): Envia o orçamento ao cliente (link clicável + PDF).         O dict 'orcamento' c

### Community 308 - "Community 308"
Cohesion: 1.0
Nodes (1): Notifica o operador quando o cliente abre o orçamento pela primeira vez.

### Community 309 - "Community 309"
Cohesion: 1.0
Nodes (1): Notifica o operador quando o cliente aceita o orçamento.

### Community 310 - "Community 310"
Cohesion: 1.0
Nodes (1): Notifica o operador quando o cliente recusa o orçamento.

### Community 311 - "Community 311"
Cohesion: 1.0
Nodes (1): Envia lembrete automático ao cliente sobre orçamento pendente.

### Community 312 - "Community 312"
Cohesion: 1.0
Nodes (1): Garante DDI 55 nos dígitos: 5548999887766

### Community 313 - "Community 313"
Cohesion: 1.0
Nodes (1): Calcula a data de validade a partir de hoje + dias, retorna no formato DD/MM/AAA

### Community 314 - "Community 314"
Cohesion: 1.0
Nodes (1): Assets do frontend não devem consumir o contador: um carregamento de página

### Community 315 - "Community 315"
Cohesion: 1.0
Nodes (0): 

### Community 316 - "Community 316"
Cohesion: 1.0
Nodes (0): 

### Community 317 - "Community 317"
Cohesion: 1.0
Nodes (0): 

### Community 318 - "Community 318"
Cohesion: 1.0
Nodes (0): 

### Community 319 - "Community 319"
Cohesion: 1.0
Nodes (0): 

### Community 320 - "Community 320"
Cohesion: 1.0
Nodes (0): 

### Community 321 - "Community 321"
Cohesion: 1.0
Nodes (0): 

### Community 322 - "Community 322"
Cohesion: 1.0
Nodes (0): 

### Community 323 - "Community 323"
Cohesion: 1.0
Nodes (0): 

### Community 324 - "Community 324"
Cohesion: 1.0
Nodes (0): 

### Community 325 - "Community 325"
Cohesion: 1.0
Nodes (0): 

### Community 326 - "Community 326"
Cohesion: 1.0
Nodes (0): 

### Community 327 - "Community 327"
Cohesion: 1.0
Nodes (0): 

### Community 328 - "Community 328"
Cohesion: 1.0
Nodes (0): 

### Community 329 - "Community 329"
Cohesion: 1.0
Nodes (0): 

### Community 330 - "Community 330"
Cohesion: 1.0
Nodes (0): 

### Community 331 - "Community 331"
Cohesion: 1.0
Nodes (0): 

### Community 332 - "Community 332"
Cohesion: 1.0
Nodes (1): Test that fetching is allowed when robots.txt returns 404.

### Community 333 - "Community 333"
Cohesion: 1.0
Nodes (1): Test that fetching is blocked when robots.txt returns 401.

### Community 334 - "Community 334"
Cohesion: 1.0
Nodes (1): Test that fetching is blocked when robots.txt returns 403.

### Community 335 - "Community 335"
Cohesion: 1.0
Nodes (1): Test that fetching is allowed when robots.txt allows all.

### Community 336 - "Community 336"
Cohesion: 1.0
Nodes (1): Test that fetching is blocked when robots.txt disallows all.

### Community 337 - "Community 337"
Cohesion: 1.0
Nodes (1): Test fetching an HTML page returns markdown content.

### Community 338 - "Community 338"
Cohesion: 1.0
Nodes (1): Test fetching an HTML page with raw=True returns original HTML.

### Community 339 - "Community 339"
Cohesion: 1.0
Nodes (1): Test fetching JSON content returns raw content.

### Community 340 - "Community 340"
Cohesion: 1.0
Nodes (1): Test that 404 response raises McpError.

### Community 341 - "Community 341"
Cohesion: 1.0
Nodes (1): Test that 500 response raises McpError.

### Community 342 - "Community 342"
Cohesion: 1.0
Nodes (1): Test that proxy URL is passed to client.

### Community 343 - "Community 343"
Cohesion: 1.0
Nodes (0): 

### Community 344 - "Community 344"
Cohesion: 1.0
Nodes (0): 

### Community 345 - "Community 345"
Cohesion: 1.0
Nodes (0): 

### Community 346 - "Community 346"
Cohesion: 1.0
Nodes (1): Schemas de Planos e Módulos

### Community 347 - "Community 347"
Cohesion: 1.0
Nodes (1): Sanitizador de WhatsApp

### Community 348 - "Community 348"
Cohesion: 1.0
Nodes (1): Router Comercial (Leads)

### Community 349 - "Community 349"
Cohesion: 1.0
Nodes (1): Gerenciador de Cache (Redis/Mem)

### Community 350 - "Community 350"
Cohesion: 1.0
Nodes (1): Commercial Leads Table

### Community 351 - "Community 351"
Cohesion: 1.0
Nodes (1): RBAC Roles and Permissions

### Community 352 - "Community 352"
Cohesion: 1.0
Nodes (1): Service Worker

### Community 353 - "Community 353"
Cohesion: 1.0
Nodes (1): Dashboard Right Panel

### Community 354 - "Community 354"
Cohesion: 1.0
Nodes (1): Quotations E2E Tests

### Community 355 - "Community 355"
Cohesion: 1.0
Nodes (1): Memory MCP Server

## Knowledge Gaps
- **518 isolated node(s):** `Repositório base com operações CRUD síncronas e cache.`, `Busca um registro por ID.`, `Busca múltiplos registros com paginação e filtros.`, `Cria um novo registro.`, `Atualiza um registro existente.` (+513 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 236`** (2 nodes): `tsup.config.ts`, `esbuildOptions()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 237`** (2 nodes): `auth-commands.test.ts`, `runCommand()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 238`** (2 nodes): `setup.test.ts`, `appendRule()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 239`** (2 nodes): `selectOrInput.ts`, `reorderOptions()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 240`** (2 nodes): `parse-input.ts`, `parseSkillInput()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 241`** (2 nodes): `tracking.ts`, `trackEvent()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 242`** (2 nodes): `database.py`, `get_db()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 243`** (2 nodes): `check_status_envio.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 244`** (2 nodes): `check_commercial_data.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 245`** (2 nodes): `check_db.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 246`** (2 nodes): `test_render_pdf.py`, `test_render()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 247`** (2 nodes): `assistente-ia-render.js`, `processAIResponse()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 248`** (2 nodes): `template-moderno.js`, `renderizarTemplateModerno()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 249`** (2 nodes): `configuracoes.spec.js`, `loginComToken()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 250`** (2 nodes): `financeiro.spec.js`, `loginComToken()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 251`** (2 nodes): `orcamentos.spec.js`, `loginComToken()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 252`** (2 nodes): `path-validation.ts`, `isPathWithinAllowedDirectories()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 253`** (2 nodes): `directory-tree.test.ts`, `buildTreeForTesting()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 254`** (2 nodes): `startup-validation.test.ts`, `spawnServer()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 255`** (2 nodes): `simple.ts`, `registerSimplePrompt()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 256`** (2 nodes): `resource.ts`, `registerEmbeddedResourcePrompt()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 257`** (2 nodes): `args.ts`, `registerArgumentsPrompt()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 258`** (2 nodes): `completions.ts`, `registerPromptWithCompletions()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 259`** (2 nodes): `prompts.test.ts`, `createMockServer()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 260`** (2 nodes): `registrations.test.ts`, `createMockServer()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 261`** (2 nodes): `tools.test.ts`, `createMockServer()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 262`** (2 nodes): `stdio.ts`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 263`** (2 nodes): `roots.ts`, `syncRoots()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 264`** (2 nodes): `trigger-sampling-request.ts`, `registerTriggerSamplingRequestTool()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 265`** (2 nodes): `get-tiny-image.ts`, `registerGetTinyImageTool()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 266`** (2 nodes): `trigger-long-running-operation.ts`, `registerTriggerLongRunningOperationTool()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 267`** (2 nodes): `toggle-simulated-logging.ts`, `registerToggleSimulatedLoggingTool()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 268`** (2 nodes): `trigger-elicitation-request.ts`, `registerTriggerElicitationRequestTool()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 269`** (2 nodes): `get-structured-content.ts`, `registerGetStructuredContentTool()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 270`** (2 nodes): `echo.ts`, `registerEchoTool()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 271`** (2 nodes): `trigger-elicitation-request-async.ts`, `registerTriggerElicitationRequestAsyncTool()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 272`** (2 nodes): `trigger-sampling-request-async.ts`, `registerTriggerSamplingRequestAsyncTool()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 273`** (2 nodes): `get-roots-list.ts`, `registerGetRootsListTool()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 274`** (2 nodes): `get-env.ts`, `registerGetEnvTool()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 275`** (2 nodes): `get-resource-reference.ts`, `registerGetResourceReferenceTool()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 276`** (2 nodes): `get-resource-links.ts`, `registerGetResourceLinksTool()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 277`** (2 nodes): `toggle-subscriber-updates.ts`, `registerToggleSubscriberUpdatesTool()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 278`** (2 nodes): `get-annotated-message.ts`, `registerGetAnnotatedMessageTool()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 279`** (2 nodes): `get-sum.ts`, `registerGetSumTool()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 280`** (2 nodes): `explain_performance_orcamentos_sidebar_catalogo.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 281`** (2 nodes): `Router Financeiro`, `Schemas Financeiros`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 282`** (2 nodes): `Router de Relatórios`, `Máquina de Estados de Orçamento`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 283`** (2 nodes): `Router de Agendamentos`, `Schemas de Agendamento`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 284`** (2 nodes): `Proposal Builder Engine`, `Modern Proposal Template Logic`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 285`** (2 nodes): `Everything MCP Server`, `Filesystem MCP Server`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 286`** (2 nodes): `IA Assistant Knowledge Base`, `IA Assistant E2E Tests`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 287`** (2 nodes): `COTTE Agents Operating Contract`, `Lore Commit Protocol`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 288`** (1 nodes): `patch_comercial.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 289`** (1 nodes): `playwright.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 290`** (1 nodes): `system.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 291`** (1 nodes): `constants.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 292`** (1 nodes): `logger.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 293`** (1 nodes): `query.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 294`** (1 nodes): `URL da imagem do serviço vinculado (catálogo), para exibir no orçamento.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 295`** (1 nodes): `Extrai JSON válido de texto da IA.                  Args:             text: Text`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 296`** (1 nodes): `Tenta uma estratégia específica de extração`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 297`** (1 nodes): `Extrai JSON de codeblocks markdown ```json ... ````
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 298`** (1 nodes): `Extrai JSON usando regex com balanceamento de chaves.         Encontra o primeir`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 299`** (1 nodes): `Extrai JSON localizando o primeiro '{' e o último '}'.         Útil quando a IA`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 300`** (1 nodes): `Estratégia greedy - pega tudo entre o primeiro { e último }`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 301`** (1 nodes): `Extrai JSON e retorna metadados sobre o processo.                  Returns:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 302`** (1 nodes): `Retorna o status de conexão da instância (deve incluir chave 'connected': bool).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 303`** (1 nodes): `Retorna o QR Code para conectar o WhatsApp (chave 'qrcode' em base64).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 304`** (1 nodes): `Desconecta a instância. Retorna True em caso de sucesso.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 305`** (1 nodes): `Envia texto simples. Retorna True em caso de sucesso.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 306`** (1 nodes): `Envia um arquivo PDF como anexo. Retorna True em caso de sucesso.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 307`** (1 nodes): `Envia o orçamento ao cliente (link clicável + PDF).         O dict 'orcamento' c`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 308`** (1 nodes): `Notifica o operador quando o cliente abre o orçamento pela primeira vez.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 309`** (1 nodes): `Notifica o operador quando o cliente aceita o orçamento.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 310`** (1 nodes): `Notifica o operador quando o cliente recusa o orçamento.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 311`** (1 nodes): `Envia lembrete automático ao cliente sobre orçamento pendente.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 312`** (1 nodes): `Garante DDI 55 nos dígitos: 5548999887766`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 313`** (1 nodes): `Calcula a data de validade a partir de hoje + dias, retorna no formato DD/MM/AAA`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 314`** (1 nodes): `Assets do frontend não devem consumir o contador: um carregamento de página`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 315`** (1 nodes): `direct_test.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 316`** (1 nodes): `test_write.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 317`** (1 nodes): `simple_test.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 318`** (1 nodes): `debug_test.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 319`** (1 nodes): `sw.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 320`** (1 nodes): `generate_icon.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 321`** (1 nodes): `api-financeiro.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 322`** (1 nodes): `modal-orcamento.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 323`** (1 nodes): `assistente-ia-desktop.spec.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 324`** (1 nodes): `assistente-ia-mobile.spec.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 325`** (1 nodes): `assistente-ia-embed.spec.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 326`** (1 nodes): `structured-content.test.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 327`** (1 nodes): `lib.test.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 328`** (1 nodes): `roots-utils.test.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 329`** (1 nodes): `path-utils.test.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 330`** (1 nodes): `file-path.test.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 331`** (1 nodes): `knowledge-graph.test.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 332`** (1 nodes): `Test that fetching is allowed when robots.txt returns 404.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 333`** (1 nodes): `Test that fetching is blocked when robots.txt returns 401.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 334`** (1 nodes): `Test that fetching is blocked when robots.txt returns 403.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 335`** (1 nodes): `Test that fetching is allowed when robots.txt allows all.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 336`** (1 nodes): `Test that fetching is blocked when robots.txt disallows all.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 337`** (1 nodes): `Test fetching an HTML page returns markdown content.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 338`** (1 nodes): `Test fetching an HTML page with raw=True returns original HTML.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 339`** (1 nodes): `Test fetching JSON content returns raw content.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 340`** (1 nodes): `Test that 404 response raises McpError.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 341`** (1 nodes): `Test that 500 response raises McpError.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 342`** (1 nodes): `Test that proxy URL is passed to client.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 343`** (1 nodes): `resources.test.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 344`** (1 nodes): `server.test.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 345`** (1 nodes): `sse.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 346`** (1 nodes): `Schemas de Planos e Módulos`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 347`** (1 nodes): `Sanitizador de WhatsApp`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 348`** (1 nodes): `Router Comercial (Leads)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 349`** (1 nodes): `Gerenciador de Cache (Redis/Mem)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 350`** (1 nodes): `Commercial Leads Table`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 351`** (1 nodes): `RBAC Roles and Permissions`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 352`** (1 nodes): `Service Worker`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 353`** (1 nodes): `Dashboard Right Panel`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 354`** (1 nodes): `Quotations E2E Tests`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 355`** (1 nodes): `Memory MCP Server`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Usuario` connect `Automatic Appointment Service` to `Admin & Company Management API`, `AI Transcription & Audio Services`, `Financial Categories & Repository`, `Appointment Schemas & Data Models`, `Community 15`, `Community 16`, `Community 17`, `Community 112`, `Community 27`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Why does `Empresa` connect `Automatic Appointment Service` to `Admin & Company Management API`, `AI Transcription & Audio Services`, `Financial Categories & Repository`, `Appointment Schemas & Data Models`, `Core Configuration & Middlewares`, `AI Hub & Assistant Orchestration`, `Community 16`, `Community 17`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Why does `StatusOrcamento` connect `Automatic Appointment Service` to `Admin & Company Management API`, `Community 97`, `AI Transcription & Audio Services`, `Financial Categories & Repository`, `Appointment Schemas & Data Models`, `Community 113`, `Community 90`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Are the 566 inferred relationships involving `Usuario` (e.g. with `EmpresaRepository` and `Repositório para operações com empresas.`) actually correct?**
  _`Usuario` has 566 INFERRED edges - model-reasoned connections that need verification._
- **Are the 536 inferred relationships involving `StatusOrcamento` (e.g. with `OrcamentoRepository` and `Repositório especializado para orçamentos.`) actually correct?**
  _`StatusOrcamento` has 536 INFERRED edges - model-reasoned connections that need verification._
- **Are the 488 inferred relationships involving `Orcamento` (e.g. with `OrcamentoRepository` and `Repositório especializado para orçamentos.`) actually correct?**
  _`Orcamento` has 488 INFERRED edges - model-reasoned connections that need verification._
- **Are the 452 inferred relationships involving `Empresa` (e.g. with `Monta a lista de origens CORS a partir do .env.` and `Garante que erros 500 retornem JSON; não sobrescreve HTTPException (400, 401, 40`) actually correct?**
  _`Empresa` has 452 INFERRED edges - model-reasoned connections that need verification._