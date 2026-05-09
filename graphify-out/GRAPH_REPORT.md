# Graph Report - .  (2026-05-09)

## Corpus Check
- 548 files · ~626,479 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 7646 nodes · 29814 edges · 419 communities detected
- Extraction: 39% EXTRACTED · 61% INFERRED · 0% AMBIGUOUS · INFERRED: 18067 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `Usuario` - 731 edges
2. `Empresa` - 587 edges
3. `StatusOrcamento` - 584 edges
4. `Orcamento` - 582 edges
5. `Cliente` - 379 edges
6. `ModoAgendamentoOrcamento` - 288 edges
7. `LeadScore` - 269 edges
8. `TipoInteracao` - 269 edges
9. `CanalInteracao` - 269 edges
10. `StatusPipeline` - 265 edges

## Surprising Connections (you probably didn't know these)
- `Repositório base com operações CRUD síncronas e cache.` --uses--> `TenantScopedMixin`  [INFERRED]
  sistema/app/repositories/base.py → sistema/app/models/tenant.py
- `Busca um registro por ID.` --uses--> `TenantScopedMixin`  [INFERRED]
  sistema/app/repositories/base.py → sistema/app/models/tenant.py
- `Busca múltiplos registros com paginação e filtros.` --uses--> `TenantScopedMixin`  [INFERRED]
  sistema/app/repositories/base.py → sistema/app/models/tenant.py
- `Cria um novo registro.` --uses--> `TenantScopedMixin`  [INFERRED]
  sistema/app/repositories/base.py → sistema/app/models/tenant.py
- `Atualiza um registro existente.` --uses--> `TenantScopedMixin`  [INFERRED]
  sistema/app/repositories/base.py → sistema/app/models/tenant.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (561): CancelarAgendamentoInput, CriarAgendamentoInput, ListarAgendamentosInput, Tools de agendamento: listar, criar, cancelar, remarcar., RemarcarAgendamentoInput, buscar_sugestoes_catalogo(), formatar_resposta_sugestao(), ai_catalog_suggester.py  Busca itens do catálogo similares ao serviço detectado (+553 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (541): Deleta um template custom., Gera plano de correção sugerido sem executar SQL/migrations., Converte ORM Empresa → EmpresaAdminOut (inclui campos de assinatura)., Endpoint de uso único para criar o superadmin. Protegido por setup_key., Retorna estatísticas gerais do painel admin., Lista todas as empresas com contagem de orçamentos, clientes e usuários., Cria uma nova empresa com seu primeiro usuário gestor., Edita os dados de uma empresa existente. (+533 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (510): _a(), aa(), ac(), add(), addToError(), Ae(), after(), Ah() (+502 more)

### Community 3 - "Community 3"
Cohesion: 0.01
Nodes (295): get_admin_config(), _migrar_json_se_necessario(), notificar_admins_novo_cadastro(), Na primeira execução, importa dados do JSON legado para o banco., Envia WhatsApp para todos os números de monitoramento configurados., build_ai_health_summary(), build_token_chart_data(), _engine_health() (+287 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (285): Converte string para enum, retornando CONVERSACAO se inválido, _build_redis_client(), cached(), CacheManager, generate_cache_key(), get_cached_config(), invalidate_cache_for_model(), Sistema de cache para repositórios e serviços. Implementa cache com Redis (fallb (+277 more)

### Community 5 - "Community 5"
Cohesion: 0.01
Nodes (223): Remove um registro por ID., Verifica se um registro existe pelo ID., Busca um registro por um campo específico., Repositório base com operações CRUD síncronas e cache., Busca um registro por ID., Busca múltiplos registros com paginação e filtros., Cria um novo registro., Atualiza um registro existente. (+215 more)

### Community 6 - "Community 6"
Cohesion: 0.05
Nodes (241): AgendamentoCalendario, AgendamentoComOpcoes, AgendamentoCreate, AgendamentoCreateComOpcoes, AgendamentoDashboard, AgendamentoOpcaoCreate, AgendamentoOpcaoOut, AgendamentoOut (+233 more)

### Community 7 - "Community 7"
Cohesion: 0.02
Nodes (88): BaseHTTPMiddleware, BaseSettings, _compute_version(), Config, get_pricing_public(), Usa o hash curto do último commit git como versão. Fallback: 'dev'., Retorna configuração pública de preços/limites para a landing., Envia um e-mail de teste para o endereço informado.     Use para validar SMTP (B (+80 more)

### Community 8 - "Community 8"
Cohesion: 0.04
Nodes (111): abrirConfirmacaoReenvioProposta(), abrirContatosImportados(), abrirDetalhe(), abrirImportacaoLeads(), abrirModalCampanha(), abrirModalEmail(), abrirModalLead(), abrirModalLembrete() (+103 more)

### Community 9 - "Community 9"
Cohesion: 0.03
Nodes (43): _agora_ts(), IaInterpretarRateLimiter, _now(), PublicEndpointRateLimiter, RateLimitResult, Rate limit para endpoints públicos sem autenticação (aceitar/recusar/ajuste)., Rate limit para o webhook WhatsApp (POST /whatsapp/webhook).     Limite mais gen, Rate limit para recuperação de senha.     Prioriza Redis (quando configurado) e (+35 more)

### Community 10 - "Community 10"
Cohesion: 0.03
Nodes (54): ABC, SendResult, _FakeDB, _FakeQuery, _make_quote(), test_ensure_quote_approval_metadata_preenche_campos_ausentes(), test_ensure_quote_approval_metadata_respeita_campos_existentes(), test_handle_quote_status_changed_expirado_sem_disparo() (+46 more)

### Community 11 - "Community 11"
Cohesion: 0.04
Nodes (103): abrirConfirmacaoReenvioProposta(), abrirContatosImportados(), abrirDetalhe(), abrirImportacaoLeads(), abrirModalCampanha(), abrirModalEmail(), abrirModalLead(), abrirModalLembrete() (+95 more)

### Community 12 - "Community 12"
Cohesion: 0.03
Nodes (73): abrirPreviewTemplatePublico(), atualizarBtnTema(), atualizarPreview(), atualizarPreviewForma(), atualizarPreviewNumero(), atualizarVisualizacaoTema(), _buildMockOrcamentoPublico(), _buildStaticPreviewExtras() (+65 more)

### Community 13 - "Community 13"
Cohesion: 0.07
Nodes (70): _append_financeiro_inadimplencia_texto(), assistente_unificado(), assistente_unificado_stream(), assistente_unificado_v2(), assistente_v2_stream_core(), camada_1_sanitizar_entrada(), camada_2_validar_schema(), camada_3_validar_dominio() (+62 more)

### Community 14 - "Community 14"
Cohesion: 0.05
Nodes (63): _analytics_sql_commission_report(), _analytics_sql_financial_categories(), _analytics_sql_from_plan(), _analytics_sql_month_comparison(), _analytics_sql_overdue_receivables(), _analytics_sql_quote_categories(), _analytics_sql_seller_ranking(), _analytics_sql_seller_sales_detail() (+55 more)

### Community 15 - "Community 15"
Cohesion: 0.07
Nodes (66): AgentExecutionContext, _artifact_matches_route(), _build_context(), BusinessDataAgent, BusinessDataAgentOutput, _contains_any(), ConversationContinuityAgent, ConversationContinuityAgentOutput (+58 more)

### Community 16 - "Community 16"
Cohesion: 0.06
Nodes (48): AnalisarHtmlInput, BuscarCodigoInput, handler_analisar_estrutura_html(), handler_buscar_codigo_repositorio(), handler_ler_arquivo_repositorio(), LerArquivoInput, LinterHTML, Busca um termo no repositório usando grep/rg. (+40 more)

### Community 17 - "Community 17"
Cohesion: 0.05
Nodes (43): ClassificacaoResult, detectar_intencao_assistente(), detectar_intencao_assistente_async(), get_intention_classifier(), IntencaoUsuario, IntentionClassifier, Classificador de Intenção Híbrido - COTTE AI Hub Etapa 4: Classificador de Inten, Categorias de intenção do usuário (+35 more)

### Community 18 - "Community 18"
Cohesion: 0.08
Nodes (43): applyAdaptiveMessagePlaceholder(), _applyOperationalContextFromMeta(), _base64ToUint8Array(), _bindEvents(), _buildAssistenteContext(), _buildSemanticPrintableHtml(), captureAssistenteResponseContext(), _clearAssistenteOperationalContext() (+35 more)

### Community 19 - "Community 19"
Cohesion: 0.06
Nodes (39): _allow_mock_tools(), _run(), _run_stream(), test_derive_display_text_fallback_dados_financeiro_analise(), test_intencao_orcamentos_pendentes_nao_dispara_inadimplencia(), test_loop_com_tool_call_e_resposta_final(), test_loop_limite_iteracoes(), test_loop_pending_action_interrompe() (+31 more)

### Community 20 - "Community 20"
Cohesion: 0.06
Nodes (15): admin_client(), make_lead(), make_origem(), make_segmento(), make_template(), nonadmin_client(), _superadmin_user(), test_enviar_email() (+7 more)

### Community 21 - "Community 21"
Cohesion: 0.09
Nodes (38): abrirDetalhe(), abrirModalEnviarProposta(), abrirModalLead(), adicionarObservacao(), alterarScore(), alterarStatusLead(), arquivarLead(), atualizarBannerFollowUpLeads() (+30 more)

### Community 22 - "Community 22"
Cohesion: 0.11
Nodes (35): buildAssistenteErrorCard(), buildAssistentePromptQuery(), canManageAssistentePrompts(), clearAssistentePromptEditor(), deleteAssistentePromptLibraryItem(), escapeHtml(), fillAssistentePromptEditor(), getAssistentePromptById() (+27 more)

### Community 23 - "Community 23"
Cohesion: 0.1
Nodes (40): brevo_api_habilitado(), email_habilitado(), enviar_email_boas_vindas(), enviar_email_confirmacao_aceite(), enviar_email_reset_senha(), enviar_email_teste(), enviar_orcamento_por_email(), enviar_otp_aceite() (+32 more)

### Community 24 - "Community 24"
Cohesion: 0.06
Nodes (37): atualizar_assinatura(), atualizar_template_admin(), atualizar_usuario_admin(), criar_broadcast(), criar_empresa(), criar_template_admin(), criar_usuario_empresa(), dashboard() (+29 more)

### Community 25 - "Community 25"
Cohesion: 0.09
Nodes (23): adicionarBlocoCustomizado(), adicionarVariavelProposta(), atualizarCampoBloco(), atualizarConfigBloco(), atualizarOrdemBlocos(), atualizarVariavelProposta(), carregarPropostasPublicas(), configurarDragAndDropBlocos() (+15 more)

### Community 26 - "Community 26"
Cohesion: 0.06
Nodes (7): _headers_for(), test_assistente_prompt_library_crud_contract(), test_assistente_prompt_library_rejects_non_manager_changes(), test_assistente_prompt_library_scoped_by_empresa(), test_get_insights_retorna_lista(), test_post_insights_feedback_aceita_payload(), test_post_insights_feedback_rejeita_payload_sem_sessao_id()

### Community 27 - "Community 27"
Cohesion: 0.1
Nodes (36): exigir_permissao_mock(), MockObjeto, MockUsuario, Permissão 'meus' deve satisfazer exigência de 'leitura'., Permissão 'meus' não deve satisfazer exigência de 'escrita'., Permissão 'escrita' deve satisfazer exigência de 'leitura'., Permissão 'admin' deve satisfazer todos os níveis., Mock local de verificar_ownership (mesma lógica de auth.py). (+28 more)

### Community 28 - "Community 28"
Cohesion: 0.11
Nodes (29): apiRequest(), baixarExportar(), buildAbsoluteAppUrl(), buildApiRequestUrl(), buildPublicAssetUrl(), carregarSidebar(), coerceFetchUrlIfMixedContent(), exibirModalPlanos() (+21 more)

### Community 29 - "Community 29"
Cohesion: 0.08
Nodes (9): Testes das funções auxiliares puras (sem banco, sem HTTP).  Cobre: - _calcular_t, Valida que o formato segue ORC-{seq}-{ano2d}., Importa a função diretamente para testar sem HTTP., TestCalcularTotal, TestClientePorTelefone, TestDigitosTelefone, TestEmpresaPorOperador, TestFormatoNumeroOrcamento (+1 more)

### Community 30 - "Community 30"
Cohesion: 0.12
Nodes (35): _accumulateSessionTokens(), addDownloadButtons(), addMessage(), bootstrapCapabilities(), buildTechnicalFallbackReply(), copilotoExportTraceJson(), downloadCSV(), downloadJSON() (+27 more)

### Community 31 - "Community 31"
Cohesion: 0.13
Nodes (35): add_seen_suggestions(), append(), append_db(), build(), build_context(), _build_dynamic_profile(), _cache_get(), _cache_key() (+27 more)

### Community 32 - "Community 32"
Cohesion: 0.17
Nodes (35): _adicionar_item_orcamento(), _aprovar_orcamento_via_bot(), _brl_fmt(), _buscar_orcamento(), _calcular_total(), _cliente_por_telefone(), _confirmar_aceite_pendente(), _criar_orcamento_via_bot() (+27 more)

### Community 33 - "Community 33"
Cohesion: 0.11
Nodes (23): acompletion(), analisar_leads(), _apply_google_to_gemini_alias(), _briefing_fallback(), completion(), _explicit_route_prefixes(), gerar_briefing_lead(), gerar_resposta_bot() (+15 more)

### Community 34 - "Community 34"
Cohesion: 0.1
Nodes (30): abrirDocumento(), abrirModalEditarDocumento(), abrirModalNovoDocumento(), abrirPreviewDocumento(), alternarTipoConteudoDocumento(), _apiDownloadBlob(), _apiUpload(), aplicarFiltrosDocumentos() (+22 more)

### Community 35 - "Community 35"
Cohesion: 0.11
Nodes (30): CopilotIntent, CopilotSafetyDecision, CopilotStructuredPlan, _ask_llm_textual_fallback(), _build_history_preview(), _build_orcamentos_status_query(), _build_plan(), _build_response_payload() (+22 more)

### Community 36 - "Community 36"
Cohesion: 0.12
Nodes (20): adicionarBlocoCustomizado(), adicionarVariavelProposta(), atualizarCampoBloco(), atualizarConfigBloco(), atualizarOrdemBlocos(), atualizarVariavelProposta(), carregarPropostasPublicas(), configurarDragAndDropBlocos() (+12 more)

### Community 37 - "Community 37"
Cohesion: 0.1
Nodes (8): ComercialTemplates, create_template(), delete_template(), _limpar_anexo_template(), list_templates(), preview_template(), update_template(), _validar_metadados_anexo_template()

### Community 38 - "Community 38"
Cohesion: 0.07
Nodes (0): 

### Community 39 - "Community 39"
Cohesion: 0.07
Nodes (14): limpar_cache_kb(), Testes de regressão: conhecimento de funcionalidades do assistente IA.  Valida q, Scoring deve limitar a 3 seções no máximo., Mensagem sem keywords não deve retornar seções., Verifica que a knowledge_base.md é carregada corretamente., Segunda chamada deve retornar o mesmo objeto (cache)., Verifica que o _INTENT_MAP tem os mapeamentos corretos., Garante que o cache da KB seja recarregado a cada teste. (+6 more)

### Community 40 - "Community 40"
Cohesion: 0.15
Nodes (1): TemplatesManager

### Community 41 - "Community 41"
Cohesion: 0.11
Nodes (1): ComercialCampanhas

### Community 42 - "Community 42"
Cohesion: 0.19
Nodes (28): _agora(), _atualizar_sessao(), _brl(), _buscar_orc_cliente(), _buscar_sessao_ativa(), _criar_sessao(), decodificar_row_id(), _encerrar_sessao() (+20 more)

### Community 43 - "Community 43"
Cohesion: 0.12
Nodes (11): ComercialImport, delete_import(), execute_import(), get_import_leads(), list_imports(), list_segments(), list_sources(), _parse_colar() (+3 more)

### Community 44 - "Community 44"
Cohesion: 0.07
Nodes (3): Testes unitários para app/utils/whatsapp_sanitizer.py (SEC-05).  Cobre edge-case, TestSanitizarMensagem, TestSanitizarTelefone

### Community 45 - "Community 45"
Cohesion: 0.1
Nodes (18): AIPromptLoader, get_prompt(), get_prompt_loader(), load_prompts(), PromptConfig, PromptLoader - COTTE AI Hub Etapa 3: Externalização de Prompts para arquivos YAM, Configuração de um prompt específico, Inicializa o PromptLoader.                  Args:             prompts_dir: Diret (+10 more)

### Community 46 - "Community 46"
Cohesion: 0.13
Nodes (1): OrcamentosTable

### Community 47 - "Community 47"
Cohesion: 0.23
Nodes (23): atualizar_modulo(), atualizar_plano(), criar_modulo(), criar_plano(), deletar_plano(), listar_modulos(), listar_planos(), Atualiza um plano/pacote e seus módulos associados. (+15 more)

### Community 48 - "Community 48"
Cohesion: 0.08
Nodes (4): Testes para os validators de EmpresaUpdate. Cobre: numero_prefixo, numero_prefix, TestDescontoMaxPercent, TestNumeroPrefixo, TestSemValidadores

### Community 49 - "Community 49"
Cohesion: 0.15
Nodes (16): applySlashCommand(), _closePrefSheet(), _focusFirstPrefField(), _getAssistentePrefCard(), _getPrefBackdrop(), _getPrefFocusableElements(), hideSlashCommands(), initSlashCommands() (+8 more)

### Community 50 - "Community 50"
Cohesion: 0.17
Nodes (20): adicionarBlocoCustom(), adicionarVariavel(), atualizarOrdem(), carregarProposta(), cloneBlocos(), cloneVars(), configurarDragDrop(), esc() (+12 more)

### Community 51 - "Community 51"
Cohesion: 0.23
Nodes (20): _args_hash(), _cache_get(), _cache_prune(), _cache_put(), _check_rate_limit(), _consume_token(), execute(), execute_pending() (+12 more)

### Community 52 - "Community 52"
Cohesion: 0.17
Nodes (21): esperar_token(), log(), main(), Script de Testes para Envio de WhatsApp no Comercial  Uso:     cd sistema     .., Testa listagem de leads., Testa detalhes de um lead., Testa envio de WhatsApp individual., Testa CRUD de templates. (+13 more)

### Community 53 - "Community 53"
Cohesion: 0.15
Nodes (16): carregarOrigens(), carregarPipelineStagesUI(), carregarSegmentos(), editarOrigem(), editarPipelineStage(), editarSegmento(), excluirPipelineStage(), renderEtapasMobile() (+8 more)

### Community 54 - "Community 54"
Cohesion: 0.19
Nodes (20): applyInsightAction(), bindInsightEvents(), buildInsightCard(), createInsightsBlock(), escapeHtml(), fetchAndRender(), getDefaultTarget(), getDomainLabel() (+12 more)

### Community 55 - "Community 55"
Cohesion: 0.13
Nodes (18): carregarPipeline(), create_pipeline_stage(), create_pipeline_stage_compat(), delete_etapa(), delete_pipeline_stage(), delete_pipeline_stage_compat(), dropCard(), _etapa_to_stage_out() (+10 more)

### Community 56 - "Community 56"
Cohesion: 0.15
Nodes (16): carregarOrigens(), carregarPipelineStagesUI(), carregarSegmentos(), editarOrigem(), editarPipelineStage(), editarSegmento(), excluirPipelineStage(), renderEtapasMobile() (+8 more)

### Community 57 - "Community 57"
Cohesion: 0.23
Nodes (15): _make_user(), _PingInput, Testes do tool_executor (Tool Use v2)., _run(), _tc(), test_destrutiva_com_token_executa(), test_destrutiva_sem_token_emite_pending(), test_execute_pending_idempotencia_envio_com_tokens_duplicados() (+7 more)

### Community 58 - "Community 58"
Cohesion: 0.2
Nodes (19): _build_quote_approved_message(), _buscar_usuario_ativo(), _context(), ensure_quote_approval_metadata(), _format_brl(), _format_datetime_br(), handle_quote_status_changed(), handle_quote_unapproved() (+11 more)

### Community 59 - "Community 59"
Cohesion: 0.15
Nodes (18): _brl(), _enriquecer_orcamento(), gerar_pdf_fpdf2(), gerar_pdf_orcamento(), gerar_pdf_weasyprint(), _hex_to_rgb(), _normalizar_logo_url(), Ajusta o logo_url para ser um caminho local absoluto ou relativo ao template_dir (+10 more)

### Community 60 - "Community 60"
Cohesion: 0.13
Nodes (6): _FakeDB, _FakeQuery, test_assistente_unificado_roteia_saldo_rapido_sem_llm(), test_buscar_dados_financeiros_alinha_saldo_com_kpi(), test_calcular_resumo_usa_fonte_unica_saldo(), test_saldo_rapido_ia_usa_mesmo_valor_do_kpi()

### Community 61 - "Community 61"
Cohesion: 0.12
Nodes (6): escapeHtml(), escapeHtmlWithBreaks(), formatarData(), formatarDataRelativa(), formatarMoeda(), formatarMoedaCompacta()

### Community 62 - "Community 62"
Cohesion: 0.16
Nodes (1): ComercialTemplates

### Community 63 - "Community 63"
Cohesion: 0.17
Nodes (1): CacheService

### Community 64 - "Community 64"
Cohesion: 0.17
Nodes (19): apply_changes(), build_frontmatter(), detect_category(), detect_priority(), detect_status(), extract_frontmatter(), has_required_properties(), main() (+11 more)

### Community 65 - "Community 65"
Cohesion: 0.19
Nodes (15): InternalFlowAuditRecord, InternalFlowMetrics, InternalResultEnvelope, InternalTechnicalFlowPayload, InternalTraceStep, LiveArtifact, Contratos internos tipados do copiloto tecnico., _serialize_value() (+7 more)

### Community 66 - "Community 66"
Cohesion: 0.2
Nodes (1): ComercialImport

### Community 67 - "Community 67"
Cohesion: 0.17
Nodes (1): RightPanel

### Community 68 - "Community 68"
Cohesion: 0.2
Nodes (1): ChartsGrid

### Community 69 - "Community 69"
Cohesion: 0.22
Nodes (17): _run(), test_aprovar_orcamento_preenche_aprovado_em(), test_cadastrar_material_gera_id(), test_criar_parcelamento_pagar(), test_despesa_ciclo_completo(), test_duplicar_orcamento_cria_rascunho_novo(), test_duplicar_orcamento_not_found(), test_editar_cliente_atualiza_campos() (+9 more)

### Community 70 - "Community 70"
Cohesion: 0.26
Nodes (17): bindEvents(), buildQuery(), carregarResumo(), carregarTokenStats(), configureAutoRefresh(), engineColor(), formatMs(), formatTokens() (+9 more)

### Community 71 - "Community 71"
Cohesion: 0.2
Nodes (14): formatAIResponse(), renderAnaliseTexto(), renderCatalogoSugestao(), renderListaClientes(), renderListaOrcamentos(), renderOnboarding(), renderOperadorResultado(), renderOrcamentoCardUnificado() (+6 more)

### Community 72 - "Community 72"
Cohesion: 0.16
Nodes (16): clear_tenant_context(), _context_template(), enable_superadmin_bypass(), get_scoped_empresa_id(), get_tenant_context(), is_impersonation_active(), Contexto de tenant por sessão SQLAlchemy., Retorna o contexto tenant associado à sessão. (+8 more)

### Community 73 - "Community 73"
Cohesion: 0.26
Nodes (16): aceitar_orcamento(), baixar_documento_publico(), _check_rate_limit(), download_pdf_orcamento(), escolher_opcao_agendamento(), _exige_otp(), gerar_pix_publico(), _get_orcamento_publico() (+8 more)

### Community 74 - "Community 74"
Cohesion: 0.18
Nodes (13): add_observacao(), concluir_lembrete(), create_lembrete(), _lead(), list_interactions(), list_lembretes(), list_templates(), preview_template() (+5 more)

### Community 75 - "Community 75"
Cohesion: 0.19
Nodes (12): _atualizarBadge(), _carregarCache(), _carregarEExibir(), _contar(), _esc(), _etapaLabel(), _fetchBriefing(), _renderBriefing() (+4 more)

### Community 76 - "Community 76"
Cohesion: 0.2
Nodes (14): applySmartList(), bindEvents(), clearSelection(), constructor(), filterLeadsAPI(), init(), loadCampanhas(), loadLeads() (+6 more)

### Community 77 - "Community 77"
Cohesion: 0.18
Nodes (1): StatsRow

### Community 78 - "Community 78"
Cohesion: 0.2
Nodes (15): criar_api_key(), criar_ou_obter_projeto(), _get_org_client(), _get_org_token(), onboarding_completo(), nfe_org_service.py — Gerenciamento de projetos Notaas via Organization API.  Usa, Faz upload do certificado A1 (.pfx/.p12) para o projeto.      Retorna o payload, Cria uma API key de projeto e salva em empresa.notaas_api_key.      Retorna a ch (+7 more)

### Community 79 - "Community 79"
Cohesion: 0.17
Nodes (15): add_error_responses(), add_examples_to_schemas(), create_api_documentation(), enhance_openapi_schema(), enhance_schemas_descriptions(), generate_model_documentation(), get_model_example(), Utilitários para documentação automática OpenAPI. Melhora a documentação gerada (+7 more)

### Community 80 - "Community 80"
Cohesion: 0.28
Nodes (15): _detectar_plano(), _extrair_cupom(), _extrair_data(), _extrair_email(), _extrair_evento(), _extrair_nome_plano(), _extrair_signature(), _extrair_token() (+7 more)

### Community 81 - "Community 81"
Cohesion: 0.13
Nodes (2): _frontend_integracoes_url(), oauth_callback()

### Community 82 - "Community 82"
Cohesion: 0.24
Nodes (15): _build_decision(), test_logical_agent_runner_builds_analytics_internal_plan_with_artifact_reuse(), test_logical_agent_runner_builds_hybrid_plan_with_data_and_technical_intents(), test_logical_agent_runner_builds_technical_plan_with_code_context_only(), test_logical_agent_runner_does_not_reuse_active_artifact_when_continuity_is_disabled(), test_logical_agent_runner_does_not_reuse_report_artifact_in_incompatible_follow_up_route(), test_logical_agent_runner_prepares_new_analytics_report_when_continuity_is_disabled(), test_logical_agent_runner_preserves_chart_visualization_intent_for_analytics_prompt() (+7 more)

### Community 83 - "Community 83"
Cohesion: 0.17
Nodes (8): abrirDropdownAcoes(), fecharDropdownAcoes(), fecharLoading(), initGlobalListeners(), mostrarLoading(), showError(), showSuccess(), showToast()

### Community 84 - "Community 84"
Cohesion: 0.2
Nodes (11): applyUxMode(), bindSimplifiedNavigationMenus(), bindTabEvents(), carregarCadastrosCache(), esc(), fecharModal(), initBottomSheets(), isAdvancedModeEnabled() (+3 more)

### Community 85 - "Community 85"
Cohesion: 0.28
Nodes (14): build_engine_guardrails(), EnginePolicy, _env_flag(), get_engine_policy(), is_code_rag_enabled(), is_engine_available_for_user(), is_internal_copilot_autonomy_enabled(), is_internal_copilot_enabled() (+6 more)

### Community 86 - "Community 86"
Cohesion: 0.18
Nodes (9): enviar_menu_interativo(), _extrair_bearer_token(), _processar_audio_operador(), _processar_lista_interativa(), _tratar_connection_update(), _validar_autenticacao_webhook(), _webhook_evolution(), webhook_whatsapp() (+1 more)

### Community 87 - "Community 87"
Cohesion: 0.21
Nodes (6): buildAssistenteDebugIntentMeta(), cloneIntent(), findAssistenteIntentByLabel(), findAssistenteIntentByResponseType(), matchAssistenteIntent(), normalizeAssistenteResponseType()

### Community 88 - "Community 88"
Cohesion: 0.15
Nodes (4): formatarData(), formatarDataRelativa(), formatarMoeda(), formatarMoedaCompacta()

### Community 89 - "Community 89"
Cohesion: 0.3
Nodes (13): build_code_context(), _extract_snippet(), _fingerprint(), _index_enabled(), _index_file_path(), _iter_candidate_files(), _load_index(), _match_score() (+5 more)

### Community 90 - "Community 90"
Cohesion: 0.23
Nodes (13): criar_preview_html(), extrair_variaveis_html(), gerar_valores_padrao(), processar_documento_html_com_variaveis(), Serviço para processamento de documentos HTML com substituição de variáveis.  Es, Gera valores padrão para variáveis com base em nomes comuns.          Args:, Extrai todas as variáveis do formato {nome_variavel} de um conteúdo HTML., Processa um documento HTML com variáveis, realizando validação e substituição. (+5 more)

### Community 91 - "Community 91"
Cohesion: 0.3
Nodes (13): build_semantic_report_filename(), _build_table_html(), _coerce_rows(), _coerce_theme(), _format_currency(), _format_value(), _period_label(), Renderização de relatórios semânticos em HTML/PDF para o assistente. (+5 more)

### Community 92 - "Community 92"
Cohesion: 0.25
Nodes (13): add_leads_to_campaign(), _calcular_eta(), cancelar_campaign(), create_campaign(), delete_campaign(), disparo_campaign(), _executar_disparo_background(), get_campaign() (+5 more)

### Community 93 - "Community 93"
Cohesion: 0.14
Nodes (0): 

### Community 94 - "Community 94"
Cohesion: 0.14
Nodes (13): Testes para validação cross-tenant do SQL analítico., SQL sem :empresa_id é permitido quando allow_cross_tenant=True., SQL perigoso é bloqueado mesmo com allow_cross_tenant=True., Fontes não permitidas são bloqueadas mesmo com allow_cross_tenant., SQL com :empresa_id passa na validação padrão., UNION é bloqueado independentemente de cross_tenant., SQL sem :empresa_id deve falhar por padrão., test_validate_analytics_sql_allows_no_tenant_scope_when_cross_tenant() (+5 more)

### Community 95 - "Community 95"
Cohesion: 0.29
Nodes (12): _base_playbook_por_setor(), build_playbook_setor(), get_context_for_prompt(), get_modulos_ativos(), inferir_dominio(), _normalizar_dominio(), _normalizar_formato(), obter_preferencia_visualizacao() (+4 more)

### Community 96 - "Community 96"
Cohesion: 0.41
Nodes (12): _acao_adicionar_item(), _acao_aprovar(), _acao_criar(), _acao_desconto(), _acao_enviar(), _acao_recusar(), _acao_remover_item(), _acao_ver() (+4 more)

### Community 97 - "Community 97"
Cohesion: 0.18
Nodes (6): R2Service, Deleta um arquivo do R2 a partir da URL pública.          Args:             file, Serviço para gerenciar uploads no Cloudflare R2 (compatível S3)., Retorna a URL pública de um arquivo.          Args:             key: Chave do ar, Gera URL temporária (presigned) para acesso a arquivo privado.          Args:, Faz upload de um arquivo para o R2.          Args:             file_obj: Objeto

### Community 98 - "Community 98"
Cohesion: 0.29
Nodes (12): checar_limite_orcamentos(), checar_limite_orcamentos_async(), checar_limite_usuarios(), _config_for_empresa(), exigir_ia_dashboard(), exigir_relatorios(), exigir_whatsapp_proprio(), _get_plan_defaults() (+4 more)

### Community 99 - "Community 99"
Cohesion: 0.21
Nodes (5): _FakeDb, _FakeMappings, _FakeResult, test_executar_sql_analitico_aplica_parametros_tenant_e_limit(), test_executar_sql_analitico_falha_sem_empresa()

### Community 100 - "Community 100"
Cohesion: 0.21
Nodes (7): bindTabEvents(), carregarCadastrosCache(), esc(), fecharModal(), initBottomSheets(), reconstruirStatusMaps(), switchTab()

### Community 101 - "Community 101"
Cohesion: 0.41
Nodes (11): build_rollout_plan_from_payload(), _default_plan(), get_rollout_for_empresa(), get_rollout_plan(), _normalize_companies(), _normalize_engines(), _normalize_phase(), normalize_rollout_plan() (+3 more)

### Community 102 - "Community 102"
Cohesion: 0.23
Nodes (11): _crc16(), _emv_field(), gerar_payload_pix(), gerar_qrcode_pix(), Serviço para geração de QR codes PIX no padrão EMV BRCode (Bacen).  O payload se, Gera QR Code PIX válido (padrão EMV BRCode) e retorna como base64 PNG.      Args, Formata um campo EMV TLV: ID (2 chars) + Length (2 chars) + Value., Remove acentos e caracteres não-ASCII; retorna uppercase sem pontuação. (+3 more)

### Community 103 - "Community 103"
Cohesion: 0.2
Nodes (9): addMessage(), monitor_ai_agent(), monitor_ai_stats(), monitor_ai_status(), Endpoint para o agente do Monitor AI.     Apenas superadmins podem acessar., Endpoint para retornar o status rápido do sistema para a sidebar do Monitor AI., Agregação de consumo de tokens por engine e por dia.     Usado pelo dashboard de, scrollToBottom() (+1 more)

### Community 104 - "Community 104"
Cohesion: 0.23
Nodes (10): esqueci_senha(), get_config_publica(), _hash_token_reset(), login(), me(), _normalizar_ip(), redefinir_senha(), registrar() (+2 more)

### Community 105 - "Community 105"
Cohesion: 0.17
Nodes (0): 

### Community 106 - "Community 106"
Cohesion: 0.3
Nodes (1): ChatVirtualizer

### Community 107 - "Community 107"
Cohesion: 0.26
Nodes (8): abrirDetalhesOrcamento(), _carregarContasOrcamento(), _carregarDocumentosDetalhes(), confirmarDesaprovar(), fecharDetalhes(), _renderizarHistoricoPagamentos(), _renderizarProgressoPagamentos(), sincronizarDocumento()

### Community 108 - "Community 108"
Cohesion: 0.32
Nodes (11): abrirModalEmail(), abrirModalWhatsApp(), aplicarTemplate(), assignMensagensGlobals(), enviarEmail(), enviarWhatsApp(), parseTemplateSelection(), populateTplSelect() (+3 more)

### Community 109 - "Community 109"
Cohesion: 0.31
Nodes (7): create_prompt(), list_prompts(), normalizar_categoria(), Serviço de biblioteca de prompts salvos por empresa., register_usage(), _serialize(), update_prompt()

### Community 110 - "Community 110"
Cohesion: 0.22
Nodes (10): enviar_lista_selecao(), enviar_poll_confirmacao(), _fmt_phone(), Camada de interações interativas para o canal WhatsApp do operador. Abstrai Poll, Converte markdown rico para formato compatível com WhatsApp., Envia enquete nativa do WhatsApp para confirmação.     Mais estável que sendButt, Envia menu de lista (sendList) — para selecionar clientes, serviços etc., Fallback universal: texto formatado com opções numeradas. (+2 more)

### Community 111 - "Community 111"
Cohesion: 0.35
Nodes (10): _detectar_resposta_poll(), _enviar_resposta(), _limpar_pending_wpp(), _mensagem_confirmacao_whatsapp(), processar_operador_wpp(), Monta texto da enquete com contexto operacional (cliente, orçamento, alterações), _recuperar_pending_wpp(), _salvar_pending_wpp() (+2 more)

### Community 112 - "Community 112"
Cohesion: 0.22
Nodes (6): cancelar_nota_fiscal(), configurar_notaas(), emitir_nota_fiscal(), _get_empresa_com_nfe(), receber_webhook_notaas(), status_notaas()

### Community 113 - "Community 113"
Cohesion: 0.2
Nodes (5): create_origem(), get_config(), list_origens(), update_config(), update_origem()

### Community 114 - "Community 114"
Cohesion: 0.18
Nodes (3): Testes: webhook Kiwify → bloqueio/ativação de empresa + check 402 em auth.  Cená, Desenvolvimento: token vazio não bloqueia; ENVIRONMENT fora de produção., sem_kiwify_token()

### Community 115 - "Community 115"
Cohesion: 0.18
Nodes (0): 

### Community 116 - "Community 116"
Cohesion: 0.18
Nodes (1): Testes da normalização de modelos LiteLLM (AI_MODEL / overrides independentes do

### Community 117 - "Community 117"
Cohesion: 0.29
Nodes (9): _build_flow_metrics(), _build_step_trace(), get_documental_catalog(), _listar_documentos_empresa(), _pending_confirmation_payload(), Serviços da Sprint 5: engine documental., Fluxo composto documental: consultar orçamento -> montar dossiê -> anexar opcion, Retorna catálogo explícito da superfície documental. (+1 more)

### Community 118 - "Community 118"
Cohesion: 0.27
Nodes (4): OTPService, Serviço para gerenciar códigos OTP (One-Time Password) para aceite de orçamentos, Gera um código de 6 dígitos, salva e retorna., Valida se o código informado é o correto e não expirou. Remove após validar.

### Community 119 - "Community 119"
Cohesion: 0.2
Nodes (8): code_rag_tool(), get_sql_toolkit(), log_reader_tool(), Retorna o toolkit SQL configurado com o LLM., Lê os arquivos de log do sistema para análise.     Útil para diagnosticar proble, Retorna colunas, tipos e relações de uma tabela requisitada usando SQLAlchemy In, Pesquisa e recupera trechos de código do projeto com base em uma query.     Útil, schema_inspector_tool()

### Community 120 - "Community 120"
Cohesion: 0.24
Nodes (9): _baixar_audio_evolution(), mensagem_voz_nao_configurada(), [INOVAÇÃO] Transcrição de áudio para o canal WhatsApp do operador.  Fluxo: 1. Ba, Mensagem amigável quando a transcrição não está disponível., Baixa e transcreve um áudio do WhatsApp.      Args:         message_data: dict c, Baixa o áudio da Evolution API e retorna os bytes., Envia áudio para a API Whisper (OpenAI) e retorna a transcrição., transcrever_audio_wpp() (+1 more)

### Community 121 - "Community 121"
Cohesion: 0.44
Nodes (9): _build_flow_metrics(), _build_step_trace(), _gerar_pdf_orcamento_runtime(), get_operational_catalog(), _load_orcamento_for_pdf(), _pending_confirmation_payload(), run_agendamento_operational_flow(), run_financeiro_operational_flow() (+1 more)

### Community 122 - "Community 122"
Cohesion: 0.31
Nodes (8): _build_flow_metrics(), _build_step_trace(), Serviços da Sprint 6: engine analítica e SQL Agent seguro., Fluxo SQL Agent analítico (read-only, behind flag)., Fluxo analítico MVP: consultar superfície read-only -> registrar resultado., run_analytics_flow(), run_analytics_sql_query_flow(), _scope_to_tool_args()

### Community 123 - "Community 123"
Cohesion: 0.24
Nodes (9): get_allowed_tables_for_guard(), get_schema_context_for_llm(), get_table_hints(), Contexto de schema do banco para o LLM SQL Planner., Retorna contexto de schema para injeção no prompt do LLM., Mapeamento de termos de negócio para tabelas., Resolve um termo de negócio para o nome da tabela., Retorna mapping de tabelas permitidas para o SQL guard.     Todas as tabelas com (+1 more)

### Community 124 - "Community 124"
Cohesion: 0.49
Nodes (9): _build_request(), _reset_db(), test_delete_lead_nao_remove_lead_global_e_remove_apenas_lead_da_empresa(), test_excluir_conta_soft_gera_auditoria_com_request_id(), test_excluir_movimentacao_caixa_gera_auditoria_e_respeita_empresa(), test_marcar_todas_lidas_nao_afeta_outra_empresa_e_gera_auditoria(), test_registrar_auditoria_persiste_request_id_e_detalhes(), test_remover_documento_do_orcamento_gera_auditoria() (+1 more)

### Community 125 - "Community 125"
Cohesion: 0.29
Nodes (1): TemplatesManager

### Community 126 - "Community 126"
Cohesion: 0.31
Nodes (6): createGlobalOverlay(), getNovoOrcamentoContent(), getNovoOrcamentoFooter(), init(), registerModals(), setupGlobalEvents()

### Community 127 - "Community 127"
Cohesion: 0.42
Nodes (8): _allowed_sources(), _balanced_parentheses(), _build_complexity(), Guardrails de segurança para SQL Agent analítico (read-only)., _risk_score(), SqlValidationResult, _strip_literals_and_comments(), validate_analytics_sql()

### Community 128 - "Community 128"
Cohesion: 0.36
Nodes (8): _extensao_do_nome(), obter_bytes_anexo(), _r2_esta_disponivel(), Obtém os bytes de um anexo, seja ele um caminho local ou uma URL (R2)., _resolver_mime(), _salvar_local(), salvar_upload_template_anexo(), validar_template_anexo_path()

### Community 129 - "Community 129"
Cohesion: 0.36
Nodes (8): create_agent_executor(), get_llm(), _import_langchain(), process_monitor_query(), Importa dependências opcionais do Monitor AI.      Mantém os imports lazy para n, Configura e retorna o LLM apontando para o OpenRouter., Cria e configura o Agent (LangGraph) com as tools necessárias e o prompt do Supe, Processa a query do usuário através do agente LangGraph e retorna o resultado.

### Community 130 - "Community 130"
Cohesion: 0.22
Nodes (8): contagem_nao_lidas(), listar_notificacoes(), marcar_como_lida(), marcar_todas_lidas(), Lista notificações da empresa do usuário., Retorna o número de notificações não lidas., Marca uma notificação como lida., Marca todas as notificações da empresa como lidas.

### Community 131 - "Community 131"
Cohesion: 0.22
Nodes (0): 

### Community 132 - "Community 132"
Cohesion: 0.42
Nodes (8): _build_decision(), test_data_executor_calls_semantic_runtime_with_analytics_engine_and_table_hint(), test_data_executor_does_not_prefix_hybrid_request(), test_data_executor_returns_none_on_runtime_exception(), test_data_executor_returns_none_when_runtime_returns_handled_false(), test_data_executor_safely_extracts_malformed_contract_fields(), test_data_executor_skips_when_run_has_no_business_data(), test_data_executor_uses_active_objective_for_short_analytics_follow_up()

### Community 133 - "Community 133"
Cohesion: 0.22
Nodes (0): 

### Community 134 - "Community 134"
Cohesion: 0.22
Nodes (0): 

### Community 135 - "Community 135"
Cohesion: 0.22
Nodes (2): test_orcamento_create_sem_agendamento_modo_valida(), TestResolverAgendamentoModoCriacao

### Community 136 - "Community 136"
Cohesion: 0.31
Nodes (3): _assistenteMetricsEnabled(), confirmarOrcamento(), _scheduleOrcamentoConfirmPaintMeasure()

### Community 137 - "Community 137"
Cohesion: 0.29
Nodes (4): _extensao_do_nome(), Retorna a URL do arquivo.     Para arquivos no R2, retorna a URL diretamente., resolver_arquivo_path(), salvar_upload_documento()

### Community 138 - "Community 138"
Cohesion: 0.25
Nodes (7): aplicar_desconto(), erro_validacao_desconto(), Validação e cálculo de desconto em orçamentos (NEG-05)., Limite de desconto efetivo: primeiro do usuário, depois da empresa, depois 100., Retorna mensagem de erro se o desconto for inválido; None se válido.     - Perce, Retorna o total após aplicar o desconto (usa Decimal para precisão monetária)., resolver_max_percent_desconto()

### Community 139 - "Community 139"
Cohesion: 0.32
Nodes (6): _coluna_existe(), _fk_existe(), add categoria_id to servicos  Revision ID: 20260323_categoria_id_servicos Revise, Verifica se uma coluna já existe na tabela., Verifica se uma foreign key já existe., upgrade()

### Community 140 - "Community 140"
Cohesion: 0.25
Nodes (0): 

### Community 141 - "Community 141"
Cohesion: 0.25
Nodes (1): Heurísticas do assistente para listagens com autopaginação.

### Community 142 - "Community 142"
Cohesion: 0.39
Nodes (7): check_sensitive_file(), log_alert(), main(), Retorna alerta se o arquivo é sensível., Registra alertas em ~/.claude/parry_alerts.log., Retorna lista de alertas encontrados no texto., scan_text()

### Community 143 - "Community 143"
Cohesion: 0.43
Nodes (7): abrirModalReenvioOrcamento(), bindReenvioModalHandlers(), cotteConfirmarReenvioSeNecessario(), fecharModalReenvioOrcamento(), mensagemFallback(), onKeydownReenvio(), precisaConfirmarReenvioOrcamento()

### Community 144 - "Community 144"
Cohesion: 0.39
Nodes (4): carregarPipeline(), dropCard(), kanbanCard(), renderKanban()

### Community 145 - "Community 145"
Cohesion: 0.43
Nodes (6): carregarDashboard(), carregarNovosClientes(), irParaLeadsComFiltro(), renderActionList(), renderMetrics(), renderRecentList()

### Community 146 - "Community 146"
Cohesion: 0.32
Nodes (1): TooltipManager

### Community 147 - "Community 147"
Cohesion: 0.62
Nodes (6): checar_limite_ia(), checar_limite_orcamentos(), checar_limite_usuarios(), checar_limite_whatsapp(), get_plano_empresa(), verificar_modulo()

### Community 148 - "Community 148"
Cohesion: 0.33
Nodes (6): build_hint_injection(), parse_message_hints(), ParsedHints, text_preprocessor.py  Parser de linguagem natural leve (regex) que extrai hints, Extrai hints estruturados da mensagem via regex. Não modifica a mensagem., Retorna bloco de texto para injetar no contexto antes de [DADOS DO SISTEMA].

### Community 149 - "Community 149"
Cohesion: 0.43
Nodes (6): _extract_json_from_response(), llm_sql_planner_enabled(), LLMSqlPlan, Planejador opcional de SQL via LLM para modo híbrido., Extrai JSON da resposta do LLM, tolerando markdown code blocks., try_generate_sql_from_llm()

### Community 150 - "Community 150"
Cohesion: 0.57
Nodes (6): _column_exists(), downgrade(), _index_exists(), feat: sistema de papeis RBAC (acoes nos modulos + tabela papeis + papel_id em us, _table_exists(), upgrade()

### Community 151 - "Community 151"
Cohesion: 0.29
Nodes (1): Testes da máquina de estados compartilhada (API + bot).

### Community 152 - "Community 152"
Cohesion: 0.29
Nodes (0): 

### Community 153 - "Community 153"
Cohesion: 0.29
Nodes (0): 

### Community 154 - "Community 154"
Cohesion: 0.29
Nodes (0): 

### Community 155 - "Community 155"
Cohesion: 0.48
Nodes (5): _orc_aprovado_com_parcelas(), test_idempotencia_retorna_mesmo_pagamento(), test_parcela_numero_forca_conta_correta(), test_registrar_pagamento_rejeita_valor_acima_saldo_parcela(), test_registrar_pagamento_respeita_ordem_parcelas()

### Community 156 - "Community 156"
Cohesion: 0.48
Nodes (6): _coletar_candidatos(), executar_backfill(), main(), _parse_args(), Backfill de aprovado_em para orçamentos já APROVADO com data nula.  Uso:     pyt, _resumir_origem()

### Community 157 - "Community 157"
Cohesion: 0.48
Nodes (5): carregarDashboard(), irParaLeadsComFiltro(), renderActionList(), renderMetrics(), renderRecentList()

### Community 158 - "Community 158"
Cohesion: 0.33
Nodes (2): _brl(), formatPendingArgs()

### Community 159 - "Community 159"
Cohesion: 0.38
Nodes (3): abrirModalEmail(), abrirModalWhatsApp(), populateTplSelect()

### Community 160 - "Community 160"
Cohesion: 0.33
Nodes (5): ensure_scoped_empresa_id(), Guard rails utilitários para escopo de tenant no assistente., Retorna um contexto seguro para multi-tenant.      Regras:     - Nunca confia em, Valida presença de empresa_id para operações scoping-sensitive., sanitize_context_with_tenant()

### Community 161 - "Community 161"
Cohesion: 0.33
Nodes (5): get_plan_defaults(), Configuração de limites padrão por plano (trial, starter, pro, business). Persis, Lê plan_defaults.json ou retorna os valores padrão., Salva plan_defaults.json.     Espera chaves trial, starter, pro, business com li, save_plan_defaults()

### Community 162 - "Community 162"
Cohesion: 0.4
Nodes (5): _env_enabled(), langgraph_enabled(), Orquestração opcional via LangGraph para o assistente v2., Executa a orquestração por LangGraph quando disponível.      Fallback:     - se, run_assistant_graph()

### Community 163 - "Community 163"
Cohesion: 0.33
Nodes (3): DimensionDefinition, MetricDefinition, Catálogo semântico de métricas e dimensões do assistente.

### Community 164 - "Community 164"
Cohesion: 0.33
Nodes (5): Sanitização de inputs não-confiáveis recebidos pelo webhook do WhatsApp.  SEC-05, Extrai apenas dígitos do telefone e valida o comprimento.     Retorna a string d, Remove bytes nulos e caracteres de controle (exceto \\t, \\n, \\r),     normaliz, sanitizar_mensagem(), sanitizar_telefone()

### Community 165 - "Community 165"
Cohesion: 0.33
Nodes (5): Máquina de estados de orçamento — transições compartilhadas entre API e bot., Retorna True se a transição de status for permitida pela máquina de estados (ide, Mensagem quando a transição não é permitida (HTTP ou bot WhatsApp/dashboard)., texto_transicao_negada(), transicao_permitida()

### Community 166 - "Community 166"
Cohesion: 0.33
Nodes (5): downgrade(), add_commercial_fk_tables  Revision ID: 9e5c2d29991b Revises: 5f2d3c4b1a9e Create, Adiciona colunas ativo, segmento_id e origem_lead_id ao commercial_leads.     Ta, Remove as colunas adicionadas (tabelas não são dropadas pois pertencem a outra m, upgrade()

### Community 167 - "Community 167"
Cohesion: 0.4
Nodes (4): _coluna_existe(), Add document tracking fields to orcamento_documentos  Revision ID: 20260323_doc_, Verifica se uma coluna já existe na tabela., upgrade()

### Community 168 - "Community 168"
Cohesion: 0.33
Nodes (5): downgrade(), add_status_envio_commercial_leads  Adiciona coluna status_envio à tabela commerc, Adiciona coluna status_envio se não existir., Remove coluna status_envio., upgrade()

### Community 169 - "Community 169"
Cohesion: 0.33
Nodes (5): downgrade(), Add commercial leads and interactions tables  Revision ID: 002_add_comercial_tab, Cria tabelas commercial_leads e commercial_interactions., Remove tabelas commercial_interactions e commercial_leads., upgrade()

### Community 170 - "Community 170"
Cohesion: 0.4
Nodes (4): _coluna_existe(), add preco_custo to servicos  Revision ID: 20260323_preco_custo Revises: 20260323, Verifica se uma coluna já existe na tabela., upgrade()

### Community 171 - "Community 171"
Cohesion: 0.67
Nodes (5): downgrade(), _index_exists(), add_mercadolivre_domain_tables  Revision ID: ml002_add_mercadolivre_domain_table, _table_exists(), upgrade()

### Community 172 - "Community 172"
Cohesion: 0.4
Nodes (4): column_exists(), add campaigns tables  Revision ID: b66af2e00a10 Revises: f4ef69a06e14 Create Dat, Verifica se uma coluna existe na tabela., upgrade()

### Community 173 - "Community 173"
Cohesion: 0.33
Nodes (5): downgrade(), Initial schema (baseline) — create_all a partir dos models atuais.  Banco já exi, Cria todas as tabelas a partir de Base.metadata (models atuais)., Remove todas as tabelas (ordem inversa de dependências)., upgrade()

### Community 174 - "Community 174"
Cohesion: 0.67
Nodes (5): downgrade(), _index_exists(), add_mercadolivre_integration_tables  Revision ID: ml001_add_mercadolivre_integra, _table_exists(), upgrade()

### Community 175 - "Community 175"
Cohesion: 0.33
Nodes (5): downgrade(), fix_status_envio_column  Corrige referência à coluna status_envio que não existe, Remove referência à coluna status_envio que não existe., Recria a referência problemática (não recomendado)., upgrade()

### Community 176 - "Community 176"
Cohesion: 0.33
Nodes (5): downgrade(), Add commercial segments, lead sources, templates, reminders, config tables and e, Remove tabelas e colunas adicionadas., Cria tabelas auxiliares e estende commercial_leads., upgrade()

### Community 177 - "Community 177"
Cohesion: 0.33
Nodes (5): downgrade(), fix_missing_commercial_leads_columns_again  Corrige problemas de integridade no, Remove correções (não recomendado em produção)., Corrige tabelas e colunas do módulo comercial., upgrade()

### Community 178 - "Community 178"
Cohesion: 0.33
Nodes (0): 

### Community 179 - "Community 179"
Cohesion: 0.53
Nodes (4): _fake_send_capture(), test_envio_email_com_anexo_quando_config_ativa(), test_envio_email_config_ativa_sem_pdf_envia_sem_anexo(), test_envio_email_sem_anexo_por_padrao()

### Community 180 - "Community 180"
Cohesion: 0.33
Nodes (0): 

### Community 181 - "Community 181"
Cohesion: 0.4
Nodes (2): _create_superadmin_token(), test_rollout_plan_superadmin_update_and_read()

### Community 182 - "Community 182"
Cohesion: 0.53
Nodes (4): _auth_headers(), test_cliente_por_id_de_outra_empresa_retorna_404(), test_clientes_lista_nao_vaza_registros_de_outra_empresa(), test_criar_cliente_permanece_na_empresa_do_usuario_autenticado()

### Community 183 - "Community 183"
Cohesion: 0.47
Nodes (3): _headers_for(), test_copiloto_interno_shadow_mode_keeps_legacy_response(), test_copiloto_interno_uses_autonomy_runtime_when_enabled()

### Community 184 - "Community 184"
Cohesion: 0.47
Nodes (5): main(), Testa se o comando 'ajuda' é interpretado corretamente., Testa se as novas ações são reconhecidas., test_ajuda(), test_novas_acoes()

### Community 185 - "Community 185"
Cohesion: 0.4
Nodes (2): carregarLembretes(), salvarLembrete()

### Community 186 - "Community 186"
Cohesion: 0.4
Nodes (2): _fallbackPayload(), fetchCapabilities()

### Community 187 - "Community 187"
Cohesion: 0.4
Nodes (4): get_pricing_config(), Lê o pricing.json ou retorna defaults., Salva o pricing.json (merge com defaults) e retorna o resultado., save_pricing_config()

### Community 188 - "Community 188"
Cohesion: 0.6
Nodes (4): downgrade(), _has_column(), add full address fields to tenant commercial leads  Adiciona campos de endereço, upgrade()

### Community 189 - "Community 189"
Cohesion: 0.4
Nodes (3): merge heads  Revision ID: 20260323_merge_heads Revises: 20260323_preco_custo, z_, Merge das duas heads - não faz nada, apenas une as branches, upgrade()

### Community 190 - "Community 190"
Cohesion: 0.6
Nodes (4): downgrade(), _has_column(), add address fields to commercial_leads  Adiciona campos de endereço completo ao, upgrade()

### Community 191 - "Community 191"
Cohesion: 0.7
Nodes (4): _execution_ok(), test_response_contract_contains_standard_metadata_and_printable(), test_to_ai_response_payload_embeds_semantic_contract(), test_to_ai_response_payload_keeps_pending_action()

### Community 192 - "Community 192"
Cohesion: 0.4
Nodes (0): 

### Community 193 - "Community 193"
Cohesion: 0.4
Nodes (1): Throttle de presença (ultima_atividade_em) em get_usuario_atual.

### Community 194 - "Community 194"
Cohesion: 0.6
Nodes (4): _auth_headers(), test_permite_quando_tem_documentos_leitura(), test_requer_documentos_leitura_alem_de_orcamentos_leitura(), TestOrcamentosDocumentosDisponiveisPermissao

### Community 195 - "Community 195"
Cohesion: 0.7
Nodes (4): _make_superadmin(), test_schema_drift_auto_fix_preview_dry_run(), test_schema_drift_endpoint_preserva_contrato(), test_schema_drift_snapshots_list_detail_compare()

### Community 196 - "Community 196"
Cohesion: 0.4
Nodes (0): 

### Community 197 - "Community 197"
Cohesion: 0.4
Nodes (0): 

### Community 198 - "Community 198"
Cohesion: 0.4
Nodes (0): 

### Community 199 - "Community 199"
Cohesion: 0.7
Nodes (4): _checkVersion(), _createBanner(), _init(), _showBanner()

### Community 200 - "Community 200"
Cohesion: 0.4
Nodes (0): 

### Community 201 - "Community 201"
Cohesion: 0.5
Nodes (1): Geração de insights estruturados para relatórios semânticos.

### Community 202 - "Community 202"
Cohesion: 0.5
Nodes (1): Chunking simples para contexto RAG.

### Community 203 - "Community 203"
Cohesion: 0.5
Nodes (3): gerar_csv_response(), Utilitários centralizados para geração de CSV.  Elimina duplicação do padrão io., Gera StreamingResponse CSV com delimitador ponto-e-vírgula.      Args:         h

### Community 204 - "Community 204"
Cohesion: 0.5
Nodes (1): add modulos_ativos to assistente_preferencias_usuario  Revision ID: z022_assiste

### Community 205 - "Community 205"
Cohesion: 0.5
Nodes (1): add missing FK indexes for performance  Revision ID: z003_add_missing_fk_indexes

### Community 206 - "Community 206"
Cohesion: 0.5
Nodes (1): add missing columns after stamp  Revision ID: e60f737b701c Revises: 001_initial

### Community 207 - "Community 207"
Cohesion: 0.5
Nodes (1): feat: adiciona valor_sinal_pix ao orcamento  Revision ID: e5b94f17c814 Revises:

### Community 208 - "Community 208"
Cohesion: 0.5
Nodes (1): feat: adicionar tabela bancos_pix_empresa  Revision ID: 9f0c_add_bancos_pix_empr

### Community 209 - "Community 209"
Cohesion: 0.5
Nodes (1): merge all heads  Revision ID: z020_merge_all_heads Revises: r002_fix_status_orca

### Community 210 - "Community 210"
Cohesion: 0.5
Nodes (1): fix trigger: adiciona cast ::statusconta nas strings do CASE  Revision ID: i002

### Community 211 - "Community 211"
Cohesion: 0.5
Nodes (1): add_conteudo_html_tipo_conteudo_to_documentos_empresa  Revision ID: b0bac86d4955

### Community 212 - "Community 212"
Cohesion: 0.5
Nodes (1): Pre-agendamento: fila, canal de aprovação, liberação manual.  Revision ID: z018_

### Community 213 - "Community 213"
Cohesion: 0.5
Nodes (1): fix: remove unique constraint global em orcamentos.numero e cria index por empre

### Community 214 - "Community 214"
Cohesion: 0.5
Nodes (1): merge: unifica todos os heads antes do agendamento_modo  Revision ID: w001_merge

### Community 215 - "Community 215"
Cohesion: 0.5
Nodes (1): perf: adiciona índices em empresa_id e compostos para queries multi-tenant  Revi

### Community 216 - "Community 216"
Cohesion: 0.5
Nodes (1): feat: configuracoes flexiveis de otp  Revision ID: a60e82cc379b Revises: 1913bf7

### Community 217 - "Community 217"
Cohesion: 0.5
Nodes (1): Garante módulo comercial (tenant) e vínculo em planos pagos.  Revision ID: tc003

### Community 218 - "Community 218"
Cohesion: 0.5
Nodes (1): fix missing lead_score column for legacy commercial_leads schemas  Migration def

### Community 219 - "Community 219"
Cohesion: 0.5
Nodes (1): tool_call_log  Revision ID: tc001_tool_call_log Revises: e9021f88a7c2 Create Dat

### Community 220 - "Community 220"
Cohesion: 0.5
Nodes (1): add_agendamento_opcoes  Revision ID: 9efd81e17334 Revises: a90994237bcc Create D

### Community 221 - "Community 221"
Cohesion: 0.5
Nodes (1): Cria tabela config_global para configurações persistentes da plataforma.  Revisi

### Community 222 - "Community 222"
Cohesion: 0.5
Nodes (1): add_telefone_operador_to_usuario  Adiciona campo telefone_operador na tabela usu

### Community 223 - "Community 223"
Cohesion: 0.5
Nodes (1): feat: documentos da empresa  Revision ID: b8c1d2e3f4a5 Revises: a07fa98d3427 Cre

### Community 224 - "Community 224"
Cohesion: 0.5
Nodes (1): add tenant comercial tables  Revision ID: tc002_add_tenant_comercial_tables Revi

### Community 225 - "Community 225"
Cohesion: 0.5
Nodes (1): Cria tabela feedback_assistente para avaliações do assistente IA.  Revision ID:

### Community 226 - "Community 226"
Cohesion: 0.5
Nodes (1): feat: adicionar PIX aos orcamentos  Revision ID: 2dc96d88fe32 Revises: a9b8c7d6e

### Community 227 - "Community 227"
Cohesion: 0.5
Nodes (1): add_nfe_fields_empresa_and_notas_fiscais_table  Revision ID: 80f4e3e65822 Revise

### Community 228 - "Community 228"
Cohesion: 0.5
Nodes (1): fix: permite superadmin sem empresa vinculada (empresa_id nullable em usuarios)

### Community 229 - "Community 229"
Cohesion: 0.5
Nodes (1): feat: regras de pagamento — campos em formas, snapshot no orçamento, tipo_lancam

### Community 230 - "Community 230"
Cohesion: 0.5
Nodes (1): merge legacy and current propostas publicas revisions  Revision ID: z024_merge_8

### Community 231 - "Community 231"
Cohesion: 0.5
Nodes (1): Add agendamento_escolha_obrigatoria to empresas.  Revision ID: z016_agendamento_

### Community 232 - "Community 232"
Cohesion: 0.5
Nodes (1): forma_pagamento: adiciona campo exibir_no_whatsapp  Revision ID: z027_forma_paga

### Community 233 - "Community 233"
Cohesion: 0.5
Nodes (1): add_criado_por_id_clientes  Revision ID: p002_add_criado_por_id_clientes Revises

### Community 234 - "Community 234"
Cohesion: 0.5
Nodes (1): add tipo to historico_edicoes  Revision ID: 8aa701096665 Revises: 4f007c9fa25f C

### Community 235 - "Community 235"
Cohesion: 0.5
Nodes (1): feat: pagamentos — empresa_id, chave de idempotência e índice único  Revision ID

### Community 236 - "Community 236"
Cohesion: 0.5
Nodes (1): fix: orcamento_documentos.arquivo_path nullable para documentos HTML  Revision I

### Community 237 - "Community 237"
Cohesion: 0.5
Nodes (1): add performance indices orcamentos_empresa_criado and notificacoes_empresa_lida

### Community 238 - "Community 238"
Cohesion: 0.5
Nodes (1): add_cupom_kiwify_to_empresa  Revision ID: 25a618cb66f6 Revises: i001 Create Date

### Community 239 - "Community 239"
Cohesion: 0.5
Nodes (1): Popula permissoes padrão para operadores que não têm as chaves básicas.  Garante

### Community 240 - "Community 240"
Cohesion: 0.5
Nodes (1): merge commercial and empresas heads  Revision ID: 5f2d3c4b1a9e Revises: 003_add_

### Community 241 - "Community 241"
Cohesion: 0.5
Nodes (1): Amplia alembic_version.version_num para VARCHAR(255).  O PostgreSQL padrão do Al

### Community 242 - "Community 242"
Cohesion: 0.5
Nodes (1): merge heads after contexto_operacional  Revision ID: e1b4a9d3c2f0 Revises: 899e5

### Community 243 - "Community 243"
Cohesion: 0.5
Nodes (1): pipeline_stages: cria tabela e migra status_pipeline para VARCHAR  Revision ID:

### Community 244 - "Community 244"
Cohesion: 0.5
Nodes (1): fix: corrige valores do enum statusorcamento para maiusculo  Revision ID: r002_f

### Community 245 - "Community 245"
Cohesion: 0.5
Nodes (1): feat: unique constraint parcial para padrao_pix por empresa  Garante que apenas

### Community 246 - "Community 246"
Cohesion: 0.5
Nodes (1): normalize_emails_lowercase  Revision ID: b53c78511b78 Revises: o001_add_campos_f

### Community 247 - "Community 247"
Cohesion: 0.5
Nodes (1): unify_tool_call_logs_schema  Revision ID: 4f007c9fa25f Revises: b71dff552e45 Cre

### Community 248 - "Community 248"
Cohesion: 0.5
Nodes (1): Adiciona tabela categorias_catalogo e colunas categoria_id/preco_custo em servic

### Community 249 - "Community 249"
Cohesion: 0.5
Nodes (1): add_status_aguardando_escolha  Revision ID: 2420bef5d6a4 Revises: 9efd81e17334 C

### Community 250 - "Community 250"
Cohesion: 0.5
Nodes (1): fix trigger: conta_financeira_id -> conta_id em pagamentos_financeiros  Revision

### Community 251 - "Community 251"
Cohesion: 0.5
Nodes (1): add_notif_whats_visualizacao_to_empresas  Revision ID: ac64aef565f2 Revises: e60

### Community 252 - "Community 252"
Cohesion: 0.5
Nodes (1): alter_arquivo_path_nullable_for_html_documents  Revision ID: 9d6276e279b2 Revise

### Community 253 - "Community 253"
Cohesion: 0.5
Nodes (1): merge z003 FK indexes head with z003 merge head  Revision ID: z004_merge_z003_he

### Community 254 - "Community 254"
Cohesion: 0.5
Nodes (1): remove_orcamentos_agendamento_fk  Revision ID: a90994237bcc Revises: 407429405c0

### Community 255 - "Community 255"
Cohesion: 0.5
Nodes (1): agendamento_opcoes.escolhida; remove agendamentos.opcao_escolhida_id (quebra cic

### Community 256 - "Community 256"
Cohesion: 0.5
Nodes (1): Add enviar_pdf_whatsapp to empresa  Revision ID: b4255a56f865 Revises: 9d9578b69

### Community 257 - "Community 257"
Cohesion: 0.5
Nodes (1): feat: adiciona pix_payload ao orcamento (EMV BRCode)  Revision ID: 8f19ab3f4b99

### Community 258 - "Community 258"
Cohesion: 0.5
Nodes (1): add_permissoes_column_usuario  Revision ID: p001_add_permissoes_column_usuario R

### Community 259 - "Community 259"
Cohesion: 0.5
Nodes (1): feat: adicionar campos de OTP para aceite público  Revision ID: 1913bf78d9a7 Rev

### Community 260 - "Community 260"
Cohesion: 0.5
Nodes (1): add_missing_empresa_columns  Revision ID: p003_add_missing_empresa_columns Revis

### Community 261 - "Community 261"
Cohesion: 0.5
Nodes (1): fix_antecedencia_minima_horas_default  Revision ID: ag001_fix_antecedencia Revis

### Community 262 - "Community 262"
Cohesion: 0.5
Nodes (1): Add template_publico to empresas  Revision ID: z012_template_publico Revises: 60

### Community 263 - "Community 263"
Cohesion: 0.5
Nodes (1): Criar tabelas ai_chat_sessoes e ai_chat_mensagens para persistência de sessões d

### Community 264 - "Community 264"
Cohesion: 0.5
Nodes (1): add schema drift snapshots  Revision ID: c6121d569572 Revises: 3344d22be19b Crea

### Community 265 - "Community 265"
Cohesion: 0.5
Nodes (1): tenant comercial: segmentos, templates, campanhas, import, propostas enviadas te

### Community 266 - "Community 266"
Cohesion: 0.5
Nodes (1): feat: adiciona status em_execucao e aguardando_pagamento ao StatusOrcamento  Rev

### Community 267 - "Community 267"
Cohesion: 0.5
Nodes (1): feat: número de orçamento personalizável por empresa  Adiciona: - Empresa: numer

### Community 268 - "Community 268"
Cohesion: 0.5
Nodes (1): feat: módulo financeiro — formas de pagamento, contas e pagamentos  Revision ID:

### Community 269 - "Community 269"
Cohesion: 0.5
Nodes (1): feat: adiciona assinatura_email a empresa  Revision ID: a07fa98d3427 Revises: 8f

### Community 270 - "Community 270"
Cohesion: 0.5
Nodes (1): feat: add planes and modules system  Revision ID: e11faf9b0ad1 Revises: z010_con

### Community 271 - "Community 271"
Cohesion: 0.5
Nodes (1): Adiciona SUBSTITUIDA ao enum statusproposta (reenvio forçado)  Revision ID: e902

### Community 272 - "Community 272"
Cohesion: 0.5
Nodes (1): fix: preencher_tipo_categorias_nulas  Revision ID: f985249b1289 Revises: j001 Cr

### Community 273 - "Community 273"
Cohesion: 0.5
Nodes (1): Fase 1 e 2 - Melhorias Financeiro  Revision ID: j001 Revises: i002 Create Date:

### Community 274 - "Community 274"
Cohesion: 0.5
Nodes (1): refactor_monetary_to_numeric_and_sync  Revision ID: 1548e7057e6c Revises: z005_s

### Community 275 - "Community 275"
Cohesion: 0.5
Nodes (1): add assistente prompts empresa  Revision ID: d4a8fbb2a901 Revises: c6121d569572

### Community 276 - "Community 276"
Cohesion: 0.5
Nodes (1): add_agendamentos_module  Revision ID: 407429405c03 Revises: s002_superadmin_empr

### Community 277 - "Community 277"
Cohesion: 0.5
Nodes (1): add endereco to tenant commercial leads  Revision ID: tc006_add_endereco_tenant

### Community 278 - "Community 278"
Cohesion: 0.5
Nodes (1): merge p and e heads  Merge migration to resolve multiple heads: e11faf9b0ad1 and

### Community 279 - "Community 279"
Cohesion: 0.5
Nodes (1): feat: adicionar pix padrao a empresa  Revision ID: 8b8efeace516 Revises: 2dc96d8

### Community 280 - "Community 280"
Cohesion: 0.5
Nodes (1): Adiciona tabela de logs de chamadas de tools para telemetria  Revision ID: b71df

### Community 281 - "Community 281"
Cohesion: 0.5
Nodes (1): add_sessao_whatsapp  Revision ID: aa51e0f91548 Revises: tc008_add_anexo_to_tenan

### Community 282 - "Community 282"
Cohesion: 0.5
Nodes (1): add_notaas_project_id_to_empresas  Revision ID: 0659a14bdfbe Revises: 80f4e3e658

### Community 283 - "Community 283"
Cohesion: 0.5
Nodes (1): add assistente_instrucoes to empresa  Revision ID: 3344d22be19b Revises: z021_ai

### Community 284 - "Community 284"
Cohesion: 0.5
Nodes (1): merge tc004 and tc005 heads  Revision ID: 899e50f244c5 Revises: tc004_tenant_com

### Community 285 - "Community 285"
Cohesion: 0.5
Nodes (1): merge tc006 endereco tenant and z025 address fields  Revision ID: z026_merge_tc0

### Community 286 - "Community 286"
Cohesion: 0.5
Nodes (1): feat: automação de status de orçamento — colunas empresa  Revision ID: z015_auto

### Community 287 - "Community 287"
Cohesion: 0.5
Nodes (1): Cria tabela audit_logs e remove coluna perm_catalogo de usuarios.  Antes de remo

### Community 288 - "Community 288"
Cohesion: 0.5
Nodes (1): trigger recalcular valor_pago em contas_financeiras  Revision ID: h001 Revises:

### Community 289 - "Community 289"
Cohesion: 0.5
Nodes (1): merge z002 obrigatorio branch with pipeline/html arquivo_path head  Revision ID:

### Community 290 - "Community 290"
Cohesion: 0.5
Nodes (1): add obrigatorio to orcamento_documentos  Revision ID: z002_obrigatorio_doc (curt

### Community 291 - "Community 291"
Cohesion: 0.5
Nodes (1): Add utilizar_agendamento_automatico to empresas.  Revision ID: z017_utilizar_age

### Community 292 - "Community 292"
Cohesion: 0.5
Nodes (1): Adiciona UniqueConstraint (empresa_id, nome) em servicos.  Revision ID: z022_uni

### Community 293 - "Community 293"
Cohesion: 0.5
Nodes (1): merge all heads  Merge migration para resolver os multiplos heads criados por br

### Community 294 - "Community 294"
Cohesion: 0.5
Nodes (1): Add agendamento_modo_padrao to empresas.  Reutiliza o enum PostgreSQL modoagenda

### Community 295 - "Community 295"
Cohesion: 0.5
Nodes (1): financeiro: parcelamento real, despesas, historico cobrancas, config financeira

### Community 296 - "Community 296"
Cohesion: 0.5
Nodes (1): add empresa_id to commercial_leads  Revision ID: e6ac99cf785c Revises: r001_add_

### Community 297 - "Community 297"
Cohesion: 0.5
Nodes (1): Adiciona status_pipeline em commercial_leads se ausente (legado / DB parcial).

### Community 298 - "Community 298"
Cohesion: 0.5
Nodes (1): merge 1548e7057e6c (monetary refactor) with m001 (feedback_assistente)  Revision

### Community 299 - "Community 299"
Cohesion: 0.5
Nodes (1): Adicionar models PropostaPublica, PropostaEnviada e PropostaVisualizacao  Revisi

### Community 300 - "Community 300"
Cohesion: 0.5
Nodes (1): Merge z006_audit_logs_remove_perm_catalogo e p003_add_missing_empresa_columns.

### Community 301 - "Community 301"
Cohesion: 0.5
Nodes (1): legacy alias for propostas publicas revision  Revision ID: 8237a0c4e1d0 Revises:

### Community 302 - "Community 302"
Cohesion: 0.5
Nodes (1): fix_commercial_leads_fk_columns  Revision ID: d60f6d62a957 Revises: 9e5c2d29991b

### Community 303 - "Community 303"
Cohesion: 0.5
Nodes (1): Add template_orcamento to empresa  Revision ID: 9d9578b69335 Revises: z018_pre_a

### Community 304 - "Community 304"
Cohesion: 0.5
Nodes (1): Set template_publico default to classico.  Revision ID: z013_template_publico_de

### Community 305 - "Community 305"
Cohesion: 0.5
Nodes (1): add contexto_operacional to ai_chat_sessoes  Revision ID: c8f2d1a9b401 Revises:

### Community 306 - "Community 306"
Cohesion: 0.5
Nodes (1): add copiloto_user_skill  Revision ID: 6f8002896a1d Revises: z022_unique_servico

### Community 307 - "Community 307"
Cohesion: 0.5
Nodes (1): add aceite_pendente_em to orcamentos  Revision ID: g001 Revises: 9f0c_add_bancos

### Community 308 - "Community 308"
Cohesion: 0.5
Nodes (1): add campos fiscais ao cliente (tipo_pessoa, cpf, cnpj, razao_social, etc)  Revis

### Community 309 - "Community 309"
Cohesion: 0.5
Nodes (1): Add unique partial index to categoria_financeira  Revision ID: f4ef69a06e14 Revi

### Community 310 - "Community 310"
Cohesion: 0.5
Nodes (1): Add status_envio to CommercialLead  Revision ID: b633b63e31e4 Revises: b66af2e00

### Community 311 - "Community 311"
Cohesion: 0.5
Nodes (1): Adiciona responsavel_id em tenant_commercial_leads se ausente.  Cenário: tabela

### Community 312 - "Community 312"
Cohesion: 0.5
Nodes (1): backfill_notif_whats_visualizacao_default  Revision ID: 00b953ce3024 Revises: ac

### Community 313 - "Community 313"
Cohesion: 0.5
Nodes (1): add anexo fields to tenant templates  Revision ID: tc008_add_anexo_to_tenant_tem

### Community 314 - "Community 314"
Cohesion: 0.5
Nodes (1): fix: add missing columns to orcamento_documentos  Revision ID: ba10b6a06e17 Revi

### Community 315 - "Community 315"
Cohesion: 0.5
Nodes (1): add SISTEMA to canalinteracao enum  Revision ID: fix_sistema_enum Revises: e1b4a

### Community 316 - "Community 316"
Cohesion: 0.5
Nodes (1): feat: agendamento_modo em orcamentos e usa_agendamento em config_agendamento  Ad

### Community 317 - "Community 317"
Cohesion: 0.83
Nodes (3): test_criar_documento_html(), test_fluxo_completo(), test_listar_documentos_html()

### Community 318 - "Community 318"
Cohesion: 0.5
Nodes (0): 

### Community 319 - "Community 319"
Cohesion: 0.5
Nodes (0): 

### Community 320 - "Community 320"
Cohesion: 0.5
Nodes (0): 

### Community 321 - "Community 321"
Cohesion: 0.5
Nodes (0): 

### Community 322 - "Community 322"
Cohesion: 0.5
Nodes (0): 

### Community 323 - "Community 323"
Cohesion: 0.83
Nodes (3): _appendClientesToExistingTable(), _appendOrcamentosToExistingTable(), processAIResponse()

### Community 324 - "Community 324"
Cohesion: 0.67
Nodes (2): carregarLembretes(), salvarLembrete()

### Community 325 - "Community 325"
Cohesion: 0.67
Nodes (2): createElement(), loadModule()

### Community 326 - "Community 326"
Cohesion: 0.67
Nodes (1): Sugestões de ações seguras baseadas no contrato semântico.

### Community 327 - "Community 327"
Cohesion: 0.67
Nodes (1): Roteamento de intenção em domínios semânticos.

### Community 328 - "Community 328"
Cohesion: 0.67
Nodes (2): parse_csv_to_leads(), Parse CSV base64 para lista de leads.

### Community 329 - "Community 329"
Cohesion: 0.67
Nodes (2): normalize_phone_number(), Normaliza para dígitos com DDI 55 (ex: 5548999887766).

### Community 330 - "Community 330"
Cohesion: 0.67
Nodes (0): 

### Community 331 - "Community 331"
Cohesion: 0.67
Nodes (2): Check if categorias endpoint is in OpenAPI spec, test_openapi_spec()

### Community 332 - "Community 332"
Cohesion: 0.67
Nodes (1): Agendamento automático respeita utilizar_agendamento_automatico da empresa.

### Community 333 - "Community 333"
Cohesion: 0.67
Nodes (0): 

### Community 334 - "Community 334"
Cohesion: 0.67
Nodes (0): 

### Community 335 - "Community 335"
Cohesion: 0.67
Nodes (0): 

### Community 336 - "Community 336"
Cohesion: 0.67
Nodes (0): 

### Community 337 - "Community 337"
Cohesion: 0.67
Nodes (2): check_endpoint(), Check if /financeiro/categorias endpoint exists

### Community 338 - "Community 338"
Cohesion: 0.67
Nodes (2): Test the /financeiro/categorias endpoint, test_categorias_endpoint()

### Community 339 - "Community 339"
Cohesion: 0.67
Nodes (0): 

### Community 340 - "Community 340"
Cohesion: 0.67
Nodes (0): 

### Community 341 - "Community 341"
Cohesion: 0.67
Nodes (0): 

### Community 342 - "Community 342"
Cohesion: 0.67
Nodes (1): GET /empresa/resumo-sidebar — payload agregado para a sidebar (1 round-trip).

### Community 343 - "Community 343"
Cohesion: 0.67
Nodes (1): Migração: adiciona campos individuais de endereço na tabela 'clientes'.  Execute

### Community 344 - "Community 344"
Cohesion: 1.0
Nodes (2): inicializarLayout(), _renderSetupStrip()

### Community 345 - "Community 345"
Cohesion: 0.67
Nodes (0): 

### Community 346 - "Community 346"
Cohesion: 1.0
Nodes (2): criarAgendamentoDeTeste(), criarUsuarioDeTeste()

### Community 347 - "Community 347"
Cohesion: 0.67
Nodes (0): 

### Community 348 - "Community 348"
Cohesion: 1.0
Nodes (0): 

### Community 349 - "Community 349"
Cohesion: 1.0
Nodes (0): 

### Community 350 - "Community 350"
Cohesion: 1.0
Nodes (0): 

### Community 351 - "Community 351"
Cohesion: 1.0
Nodes (0): 

### Community 352 - "Community 352"
Cohesion: 1.0
Nodes (0): 

### Community 353 - "Community 353"
Cohesion: 1.0
Nodes (0): 

### Community 354 - "Community 354"
Cohesion: 1.0
Nodes (0): 

### Community 355 - "Community 355"
Cohesion: 1.0
Nodes (0): 

### Community 356 - "Community 356"
Cohesion: 1.0
Nodes (0): 

### Community 357 - "Community 357"
Cohesion: 1.0
Nodes (0): 

### Community 358 - "Community 358"
Cohesion: 1.0
Nodes (0): 

### Community 359 - "Community 359"
Cohesion: 1.0
Nodes (0): 

### Community 360 - "Community 360"
Cohesion: 1.0
Nodes (0): 

### Community 361 - "Community 361"
Cohesion: 1.0
Nodes (0): 

### Community 362 - "Community 362"
Cohesion: 1.0
Nodes (0): 

### Community 363 - "Community 363"
Cohesion: 1.0
Nodes (0): 

### Community 364 - "Community 364"
Cohesion: 1.0
Nodes (0): 

### Community 365 - "Community 365"
Cohesion: 1.0
Nodes (0): 

### Community 366 - "Community 366"
Cohesion: 1.0
Nodes (0): 

### Community 367 - "Community 367"
Cohesion: 1.0
Nodes (0): 

### Community 368 - "Community 368"
Cohesion: 1.0
Nodes (0): 

### Community 369 - "Community 369"
Cohesion: 1.0
Nodes (0): 

### Community 370 - "Community 370"
Cohesion: 1.0
Nodes (0): 

### Community 371 - "Community 371"
Cohesion: 1.0
Nodes (0): 

### Community 372 - "Community 372"
Cohesion: 1.0
Nodes (0): 

### Community 373 - "Community 373"
Cohesion: 1.0
Nodes (0): 

### Community 374 - "Community 374"
Cohesion: 1.0
Nodes (0): 

### Community 375 - "Community 375"
Cohesion: 1.0
Nodes (0): 

### Community 376 - "Community 376"
Cohesion: 1.0
Nodes (0): 

### Community 377 - "Community 377"
Cohesion: 1.0
Nodes (0): 

### Community 378 - "Community 378"
Cohesion: 1.0
Nodes (1): Extrai JSON válido de texto da IA.                  Args:             text: Text

### Community 379 - "Community 379"
Cohesion: 1.0
Nodes (1): Tenta uma estratégia específica de extração

### Community 380 - "Community 380"
Cohesion: 1.0
Nodes (1): Extrai JSON de codeblocks markdown ```json ... ```

### Community 381 - "Community 381"
Cohesion: 1.0
Nodes (1): Extrai JSON usando regex com balanceamento de chaves.         Encontra o primeir

### Community 382 - "Community 382"
Cohesion: 1.0
Nodes (1): Extrai JSON localizando o primeiro '{' e o último '}'.         Útil quando a IA

### Community 383 - "Community 383"
Cohesion: 1.0
Nodes (1): Estratégia greedy - pega tudo entre o primeiro { e último }

### Community 384 - "Community 384"
Cohesion: 1.0
Nodes (1): Extrai JSON e retorna metadados sobre o processo.                  Returns:

### Community 385 - "Community 385"
Cohesion: 1.0
Nodes (1): Retorna o status de conexão da instância (deve incluir chave 'connected': bool).

### Community 386 - "Community 386"
Cohesion: 1.0
Nodes (1): Retorna o QR Code para conectar o WhatsApp (chave 'qrcode' em base64).

### Community 387 - "Community 387"
Cohesion: 1.0
Nodes (1): Desconecta a instância. Retorna True em caso de sucesso.

### Community 388 - "Community 388"
Cohesion: 1.0
Nodes (1): Envia texto simples. Retorna True em caso de sucesso.

### Community 389 - "Community 389"
Cohesion: 1.0
Nodes (1): Envia um arquivo PDF como anexo. Retorna True em caso de sucesso.

### Community 390 - "Community 390"
Cohesion: 1.0
Nodes (1): Envia uma imagem com legenda opcional. Retorna True em caso de sucesso.

### Community 391 - "Community 391"
Cohesion: 1.0
Nodes (1): Envia o orçamento ao cliente (link clicável + PDF).         O dict 'orcamento' c

### Community 392 - "Community 392"
Cohesion: 1.0
Nodes (1): Notifica o operador quando o cliente abre o orçamento pela primeira vez.

### Community 393 - "Community 393"
Cohesion: 1.0
Nodes (1): Notifica o operador quando o cliente aceita o orçamento.

### Community 394 - "Community 394"
Cohesion: 1.0
Nodes (1): Notifica o operador quando o cliente recusa o orçamento.

### Community 395 - "Community 395"
Cohesion: 1.0
Nodes (1): Envia lembrete automático ao cliente sobre orçamento pendente.

### Community 396 - "Community 396"
Cohesion: 1.0
Nodes (1): Garante DDI 55 nos dígitos: 5548999887766

### Community 397 - "Community 397"
Cohesion: 1.0
Nodes (1): Calcula a data de validade a partir de hoje + dias, retorna no formato DD/MM/AAA

### Community 398 - "Community 398"
Cohesion: 1.0
Nodes (1): Assets do frontend não devem consumir o contador: um carregamento de página

### Community 399 - "Community 399"
Cohesion: 1.0
Nodes (0): 

### Community 400 - "Community 400"
Cohesion: 1.0
Nodes (0): 

### Community 401 - "Community 401"
Cohesion: 1.0
Nodes (0): 

### Community 402 - "Community 402"
Cohesion: 1.0
Nodes (0): 

### Community 403 - "Community 403"
Cohesion: 1.0
Nodes (0): 

### Community 404 - "Community 404"
Cohesion: 1.0
Nodes (0): 

### Community 405 - "Community 405"
Cohesion: 1.0
Nodes (0): 

### Community 406 - "Community 406"
Cohesion: 1.0
Nodes (0): 

### Community 407 - "Community 407"
Cohesion: 1.0
Nodes (0): 

### Community 408 - "Community 408"
Cohesion: 1.0
Nodes (0): 

### Community 409 - "Community 409"
Cohesion: 1.0
Nodes (0): 

### Community 410 - "Community 410"
Cohesion: 1.0
Nodes (0): 

### Community 411 - "Community 411"
Cohesion: 1.0
Nodes (0): 

### Community 412 - "Community 412"
Cohesion: 1.0
Nodes (0): 

### Community 413 - "Community 413"
Cohesion: 1.0
Nodes (0): 

### Community 414 - "Community 414"
Cohesion: 1.0
Nodes (0): 

### Community 415 - "Community 415"
Cohesion: 1.0
Nodes (0): 

### Community 416 - "Community 416"
Cohesion: 1.0
Nodes (0): 

### Community 417 - "Community 417"
Cohesion: 1.0
Nodes (0): 

### Community 418 - "Community 418"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **456 isolated node(s):** `LiveArtifact`, `SessionWorkingMemory`, `URL da imagem do serviço vinculado (catálogo), para exibir no orçamento.`, `Infraestrutura base para entidades tenant-scoped.`, `Marca models cujo escopo principal é `empresa_id`.` (+451 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 348`** (2 nodes): `cotte_ai_hub_patch.py`, `_v2_selected_tool_names_for_message()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 349`** (2 nodes): `test.js`, `escapeHtml()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 350`** (2 nodes): `compress_test.py`, `to_llm_payload()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 351`** (2 nodes): `test_payload.js`, `_politicaAgendamentoSelectParaPayload()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 352`** (2 nodes): `fix_fn.py`, `_v2_build_listar_orcamentos_fastpath_response()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 353`** (2 nodes): `check_status_envio.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 354`** (2 nodes): `test_tool_executor_engine_policy.py`, `test_execute_blocks_tool_not_allowed_by_engine()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 355`** (2 nodes): `check_commercial_data.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 356`** (2 nodes): `test_orcamento_core_service.py`, `test_criar_orcamento_core_aceita_item_com_valor_zero()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 357`** (2 nodes): `test_assistant_autonomy_integration.py`, `test_assistente_unificado_v2_prefers_semantic_runtime()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 358`** (2 nodes): `check_db.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 359`** (2 nodes): `test_financeiro_tools_contas_bug.py`, `test_gerar_relatorio_contas_a_receber()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 360`** (2 nodes): `test_render_pdf.py`, `test_render()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 361`** (2 nodes): `assistente-ia-payloads.js`, `buildConfirmarOrcamentoPayload()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 362`** (2 nodes): `template-moderno.js`, `renderizarTemplateModerno()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 363`** (2 nodes): `agendamentos-modal.spec.js`, `loginComToken()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 364`** (2 nodes): `configuracoes.spec.js`, `loginComToken()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 365`** (2 nodes): `financeiro.spec.js`, `loginComToken()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 366`** (2 nodes): `orcamentos.spec.js`, `loginComToken()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 367`** (2 nodes): `explain_performance_orcamentos_sidebar_catalogo.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 368`** (1 nodes): `patch_comercial.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 369`** (1 nodes): `patch_executor.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 370`** (1 nodes): `playwright.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 371`** (1 nodes): `rewrite_render.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 372`** (1 nodes): `patch_cotte_ai_hub.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 373`** (1 nodes): `patch.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 374`** (1 nodes): `patch_recusar.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 375`** (1 nodes): `patch_render_types.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 376`** (1 nodes): `patch_logging.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 377`** (1 nodes): `query.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 378`** (1 nodes): `Extrai JSON válido de texto da IA.                  Args:             text: Text`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 379`** (1 nodes): `Tenta uma estratégia específica de extração`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 380`** (1 nodes): `Extrai JSON de codeblocks markdown ```json ... ````
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 381`** (1 nodes): `Extrai JSON usando regex com balanceamento de chaves.         Encontra o primeir`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 382`** (1 nodes): `Extrai JSON localizando o primeiro '{' e o último '}'.         Útil quando a IA`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 383`** (1 nodes): `Estratégia greedy - pega tudo entre o primeiro { e último }`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 384`** (1 nodes): `Extrai JSON e retorna metadados sobre o processo.                  Returns:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 385`** (1 nodes): `Retorna o status de conexão da instância (deve incluir chave 'connected': bool).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 386`** (1 nodes): `Retorna o QR Code para conectar o WhatsApp (chave 'qrcode' em base64).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 387`** (1 nodes): `Desconecta a instância. Retorna True em caso de sucesso.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 388`** (1 nodes): `Envia texto simples. Retorna True em caso de sucesso.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 389`** (1 nodes): `Envia um arquivo PDF como anexo. Retorna True em caso de sucesso.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 390`** (1 nodes): `Envia uma imagem com legenda opcional. Retorna True em caso de sucesso.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 391`** (1 nodes): `Envia o orçamento ao cliente (link clicável + PDF).         O dict 'orcamento' c`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 392`** (1 nodes): `Notifica o operador quando o cliente abre o orçamento pela primeira vez.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 393`** (1 nodes): `Notifica o operador quando o cliente aceita o orçamento.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 394`** (1 nodes): `Notifica o operador quando o cliente recusa o orçamento.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 395`** (1 nodes): `Envia lembrete automático ao cliente sobre orçamento pendente.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 396`** (1 nodes): `Garante DDI 55 nos dígitos: 5548999887766`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 397`** (1 nodes): `Calcula a data de validade a partir de hoje + dias, retorna no formato DD/MM/AAA`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 398`** (1 nodes): `Assets do frontend não devem consumir o contador: um carregamento de página`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 399`** (1 nodes): `direct_test.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 400`** (1 nodes): `test_write.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 401`** (1 nodes): `simple_test.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 402`** (1 nodes): `debug_test.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 403`** (1 nodes): `sw.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 404`** (1 nodes): `generate_icon.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 405`** (1 nodes): `tenant-comercial-onboarding.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 406`** (1 nodes): `nfe.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 407`** (1 nodes): `api-financeiro.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 408`** (1 nodes): `modal-orcamento.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 409`** (1 nodes): `assistente-render-types-fallback.test.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 410`** (1 nodes): `assistente-render-pending-action.test.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 411`** (1 nodes): `assistente-intents.test.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 412`** (1 nodes): `assistente-ia-html-fallback.test.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 413`** (1 nodes): `tenant-comercial-pipeline-script-order.test.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 414`** (1 nodes): `assistente-orcamento-confirmar-payload.test.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 415`** (1 nodes): `test-ai-response.spec.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 416`** (1 nodes): `assistente-ia-desktop.spec.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 417`** (1 nodes): `assistente-ia-mobile.spec.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 418`** (1 nodes): `assistente-ia-embed.spec.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Usuario` connect `Community 0` to `Community 1`, `Community 65`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 130`, `Community 103`, `Community 193`, `Community 51`, `Community 20`, `Community 117`, `Community 122`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Why does `Empresa` connect `Community 0` to `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 10`, `Community 78`, `Community 47`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Why does `StatusOrcamento` connect `Community 1` to `Community 0`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 165`, `Community 9`, `Community 151`, `Community 156`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Are the 729 inferred relationships involving `Usuario` (e.g. with `EmpresaRepository` and `Repositório para operações com empresas.`) actually correct?**
  _`Usuario` has 729 INFERRED edges - model-reasoned connections that need verification._
- **Are the 585 inferred relationships involving `Empresa` (e.g. with `Monta a lista de origens CORS a partir do .env.` and `Garante que erros 500 retornem JSON; não sobrescreve HTTPException (400, 401, 40`) actually correct?**
  _`Empresa` has 585 INFERRED edges - model-reasoned connections that need verification._
- **Are the 582 inferred relationships involving `StatusOrcamento` (e.g. with `OrcamentoRepository` and `Repositório especializado para orçamentos.`) actually correct?**
  _`StatusOrcamento` has 582 INFERRED edges - model-reasoned connections that need verification._
- **Are the 579 inferred relationships involving `Orcamento` (e.g. with `OrcamentoRepository` and `Repositório especializado para orçamentos.`) actually correct?**
  _`Orcamento` has 579 INFERRED edges - model-reasoned connections that need verification._