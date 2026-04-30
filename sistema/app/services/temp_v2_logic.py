async def assistente_v2_stream_core(
    *,
    mensagem: str,
    sessao_id: str,
    db,
    current_user,
    engine: str = DEFAULT_ENGINE,
    request_id: str | None = None,
    confirmation_token: str | None = None,
    override_args: dict | None = None,
):
    """Núcleo do Tool Use v2 adaptado para SSE.

    Eventos emitidos (cada um como linha `data: <json>\\n\\n`):
    - {"phase": "thinking"}                      — antes do 1º LLM
    - {"phase": "tool_running", "tool": "X"}     — ao executar tool X
    - {"chunk": "texto..."}                      — token a token
    - {"is_final": true, "final_text": "...", "metadata": {...}}  — fim da resposta
    - {"error": "msg"}                           — erro grave
    """
    import asyncio
    from app.services.assistant_preferences_service import AssistantPreferencesService
    from app.services.cotte_context_builder import SessionStore, SemanticMemoryStore
    from app.services.ia_service import ia_service
    from app.services.tool_executor import execute as tool_execute

    try:
        from app.services.tool_executor import execute_pending
    except ImportError:
        execute_pending = None

    contexto_operacional = _v2_get_operational_context(
        sessao_id=sessao_id,
        db=db,
        current_user=current_user,
    )
    mensagem_resolvida = _v2_resolve_followup_confirmation_message(
        mensagem=mensagem,
        contexto_operacional=contexto_operacional,
    )
    if mensagem_resolvida:
        mensagem = mensagem_resolvida

    from app.services.ai_intention_classifier import detectar_intencao_assistente_async
    try:
        classificacao = await detectar_intencao_assistente_async(mensagem)
        intent_str = classificacao.intencao.value
    except Exception:
        intent_str = "CONVERSACAO"


    def _enc(d):
        return f"data: {json.dumps(d, ensure_ascii=False, default=str)}\n\n"

    def _to_semantic_chart(grafico: dict | None) -> dict | None:
        if not isinstance(grafico, dict):
            return None
        dados = grafico.get("dados") or {}
        if not isinstance(dados, dict):
            return None
        return {
            "type": grafico.get("tipo") or "bar",
            "labels": list(dados.get("labels") or []),
            "datasets": list(dados.get("datasets") or []),
        }

    def _build_semantic_contract(
        *,
        summary: str,
        table: list[dict] | None = None,
        chart: dict | None = None,
        printable: dict | None = None,
        metadata_extra: dict | None = None,
    ) -> dict:
        return {
            "summary": summary or "",
            "table": list(table or []),
            "chart": chart,
            "printable": printable,
            "metadata": metadata_extra or {},
        }

    async def _emit_fastpath_ai_response(ai_response: AIResponse):
        final_text = _derive_ai_response_display_text(ai_response)
        _v2_persist_fastpath_response(
            sessao_id=sessao_id,
            db=db,
            current_user=current_user,
            resposta=final_text,
        )
        dados_out = dict(ai_response.dados or {})
        contexto_operacional = _v2_update_operational_context_from_payload(
            sessao_id=sessao_id,
            db=db,
            current_user=current_user,
            payload={**dados_out, "_tipo_resposta": ai_response.tipo_resposta},
        )
        dados_out["contexto_operacional"] = contexto_operacional
        grafico_meta = dados_out.get("grafico")

        if ai_response.tipo_resposta == "relatorio_dinamico" and "semantic_contract" not in dados_out:
            dados_out["semantic_contract"] = _build_semantic_contract(
                summary=final_text,
                table=list(dados_out.get("rows") or []),
                chart=_to_semantic_chart(grafico_meta),
                printable={
                    "title": dados_out.get("titulo", "Relatório"),
                    "summary": final_text,
                    "rows": list(dados_out.get("rows") or []),
                    "force_printable": True,
                    "theme": {"variant": "professional", "accent_color": "#0f766e"},
                },
                metadata_extra={
                    "capability": "GenerateAnalyticsReport",
                    "domain": dados_out.get("dominio", "analytics"),
                    "period_days": (dados_out.get("metricas_resumo") or {}).get("periodo_dias"),
                    "tipo_resposta_inferida": "relatorio_dinamico",
                },
            )

        yield _enc({"phase": "thinking"})
        if final_text:
            yield _enc({"chunk": final_text})
        yield _enc(
            {
                "is_final": True,
                "final_text": final_text,
                "metadata": {
                    "final_text": final_text,
                    "tipo": ai_response.tipo_resposta or "geral",
                    "dados": dados_out,
                    "grafico": grafico_meta,
                    "pending_action": ai_response.pending_action,
                    "tool_trace": ai_response.tool_trace,
                    "input_tokens": 0,
                    "output_tokens": 0,
                },
            }
        )

    resolved_engine = resolve_engine(engine)
    engine_policy = get_engine_policy(resolved_engine)
    intent_detectada = _v2_detect_deterministic_intent(mensagem)

    if _v2_is_onboarding_bootstrap_message(mensagem):
        resposta, status = _v2_build_onboarding_fastpath_payload(
            db=db,
            empresa_id=getattr(current_user, "empresa_id", 0),
        )
        _v2_persist_fastpath_response(
            sessao_id=sessao_id,
            db=db,
            current_user=current_user,
            resposta=resposta,
        )
        yield _enc({"phase": "thinking"})
        yield _enc({"chunk": resposta})
        yield _enc(
            {
                "is_final": True,
                "final_text": resposta,
                "metadata": {
                    "final_text": resposta,
                    "tipo": "onboarding",
                    "dados": status,
                    "input_tokens": 0,
                    "output_tokens": 0,
                },
            }
        )
        return

    if intent_str == "SALDO_RAPIDO":
        resposta = await _v2_build_saldo_fastpath_response(
            db=db,
            empresa_id=getattr(current_user, "empresa_id", 0),
        )
        async for event in _emit_fastpath_ai_response(resposta):
            yield event
        return

    if intent_str == "CRIAR_ORCAMENTO":
        resposta = await _v2_build_orcamento_fastpath_response(
            mensagem=mensagem,
            db=db,
            empresa_id=getattr(current_user, "empresa_id", 0),
            usuario_id=getattr(current_user, "id", 0),
        )
        async for event in _emit_fastpath_ai_response(resposta):
            yield event
        return

    if intent_str in _V2_RELATORIO_INTENTS:
        resposta_rel = await _v2_build_relatorio_fastpath_response(
            mensagem=mensagem,
            db=db,
            current_user=current_user,
            intent_str=intent_str,
        )
        if resposta_rel is not None:
            async for event in _emit_fastpath_ai_response(resposta_rel):
                yield event
            return

    if _v2_is_orcamento_context_followup_message(mensagem):
        resposta_ctx_orc = await _v2_build_orcamento_context_followup_response(
            mensagem=mensagem,
            sessao_id=sessao_id,
            db=db,
            current_user=current_user,
            request_id=request_id,
        )
        if resposta_ctx_orc is not None:
            async for event in _emit_fastpath_ai_response(resposta_ctx_orc):
                yield event
            return
        # Fast path reconheceu consulta de orçamento mas não há contexto ativo.
        # Força OPERADOR para o LLM usar ferramentas de orçamento em vez de cair
        # no fluxo CONVERSACAO que inclui obter_saldo_caixa e retornaria o caixa.
        if intent_str == "CONVERSACAO":
            intent_str = "OPERADOR"

    if intent_str == "LISTAR_ORCAMENTOS":
        resposta_lista = await _v2_build_listar_orcamentos_fastpath_response(
            mensagem=mensagem,
            db=db,
            current_user=current_user,
        )
        if resposta_lista is not None:
            async for event in _emit_fastpath_ai_response(resposta_lista):
                yield event
            return

    if intent_str == "LISTAR_CLIENTES":
        resposta_lista = await _v2_build_listar_clientes_fastpath_response(
            mensagem=mensagem,
            db=db,
            current_user=current_user,
        )
        if resposta_lista is not None:
            async for event in _emit_fastpath_ai_response(resposta_lista):
                yield event
            return

    if _v2_is_excel_chart_request(mensagem):
        final_text = (
            "Hoje eu não gero arquivo Excel diretamente pelo chat. "
            "Consigo te entregar os dados e o gráfico financeiro aqui no assistente, "
            "e você exporta para planilha com segurança."
        )
        SessionStore.append_db(
            sessao_id,
            "assistant",
            final_text,
            db,
            empresa_id=getattr(current_user, "empresa_id", 0),
            usuario_id=getattr(current_user, "id", 0),
        )
        yield _enc({"phase": "thinking"})
        yield _enc({"chunk": final_text})
        yield _enc(
            {
                "is_final": True,
                "final_text": final_text,
                "metadata": {
                    "final_text": final_text,
                    "dados": {
                        "capability": "excel_nao_suportado",
                        "semantic_contract": _build_semantic_contract(
                            summary=final_text,
                            metadata_extra={"capability": "excel_nao_suportado"},
                        ),
                    },
                    "tipo": "geral",
                },
            }
        )
        return

    if _v2_is_financial_chart_request(mensagem):
        from app.services.tool_executor import execute as _tool_exec

        dias = _v2_extract_days_window(mensagem)
        yield _enc({"phase": "thinking"})
        yield _enc(
            {"phase": "tool_running", "tool": "listar_movimentacoes_financeiras"}
        )
        tc_mov = {
            "id": "chart_movs",
            "type": "function",
            "function": {
                "name": "listar_movimentacoes_financeiras",
                "arguments": json.dumps(
                    {"dias": dias, "limit": 100}, ensure_ascii=False
                ),
            },
        }
        res_mov = await _tool_exec(
            tc_mov,
            db=db,
            current_user=current_user,
            sessao_id=sessao_id,
            confirmation_token=None,
        )
        yield _enc({"phase": "tool_running", "tool": "obter_saldo_caixa"})
        tc_saldo = {
            "id": "chart_saldo",
            "type": "function",
            "function": {"name": "obter_saldo_caixa", "arguments": "{}"},
        }
        res_saldo = await _tool_exec(
            tc_saldo,
            db=db,
            current_user=current_user,
            sessao_id=sessao_id,
            confirmation_token=None,
        )

        movs = (
            (res_mov.data or {}).get("movimentacoes", [])
            if res_mov.status == "ok"
            else []
        )
        grafico = _v2_build_financial_chart_payload(movs)
        saldo_atual = (
            (res_saldo.data or {}).get("saldo_atual")
            if res_saldo.status == "ok"
            else None
        )
        qtd = len(movs)
        if grafico:
            final_text = (
                f"Aqui está o gráfico financeiro dos últimos {dias} dias "
                f"(com {qtd} movimentações)."
            )
            if saldo_atual is not None:
                final_text += f" Saldo atual: R$ {float(saldo_atual):,.2f}."
        else:
            final_text = f"Não encontrei movimentações suficientes para montar o gráfico dos últimos {dias} dias."
        SessionStore.append_db(
            sessao_id,
            "assistant",
            final_text,
            db,
            empresa_id=getattr(current_user, "empresa_id", 0),
            usuario_id=getattr(current_user, "id", 0),
        )
        yield _enc({"chunk": final_text})
        yield _enc(
            {
                "is_final": True,
                "final_text": final_text,
                "metadata": {
                    "final_text": final_text,
                    "tipo": "financeiro",
                    "dados": {
                        "dias": dias,
                        "movimentacoes_total": qtd,
                        "saldo_atual": saldo_atual,
                        "semantic_contract": _build_semantic_contract(
                            summary=final_text,
                            table=[
                                {
                                    "data": mov.get("data"),
                                    "descricao": mov.get("descricao"),
                                    "tipo": mov.get("tipo"),
                                    "valor": mov.get("valor"),
                                }
                                for mov in list(movs or [])[:100]
                                if isinstance(mov, dict)
                            ],
                            chart=_to_semantic_chart(grafico),
                            printable={
                                "title": f"Resumo financeiro ({dias} dias)",
                                "summary": final_text,
                            },
                            metadata_extra={
                                "capability": "GenerateAnalyticsReport",
                                "domain": "analytics",
                                "period_days": dias,
                            },
                        ),
                    },
                    "grafico": grafico,
                    "tool_trace": [
                        {
                            "tool": "listar_movimentacoes_financeiras",
                            "status": res_mov.status,
                            "latencia_ms": res_mov.latencia_ms,
                        },
                        {
                            "tool": "obter_saldo_caixa",
                            "status": res_saldo.status,
                            "latencia_ms": res_saldo.latencia_ms,
                        },
                    ],
                },
            }
        )
        return

    # ── Fast-path: confirmação de ação pendente ────────────────────────────
    if confirmation_token and execute_pending:
        yield _enc({"phase": "thinking"})
        try:
            result = await execute_pending(
                confirmation_token,
                db=db,
                current_user=current_user,
                sessao_id=sessao_id,
                request_id=request_id,
                override_args=override_args or {},
                engine=engine,
            )
        except Exception as exc:
            logger.exception("[stream_v2] Erro no fast-path de confirmação")
            yield _enc({"error": str(exc)})
            return

        orc_data = result.data or {} if hasattr(result, "data") else {}
        status = result.status if hasattr(result, "status") else "ok"
        if status == "ok" and orc_data.get("numero"):
            _tool_exec = getattr(result, "tool_name", None)
            if _tool_exec == "editar_orcamento":
                final_text = "✅ Orçamento atualizado com sucesso."
                tipo_resp = "orcamento_atualizado"
            elif _tool_exec == "aprovar_orcamento":
                final_text = "✅ Orçamento aprovado com sucesso."
                tipo_resp = "orcamento_aprovado"
            elif _tool_exec == "recusar_orcamento":
                final_text = "✅ Orçamento recusado com sucesso."
                tipo_resp = "orcamento_recusado"
            else:
                final_text = "✅ Ação concluída com sucesso."
                tipo_resp = "orcamento_criado"
            sugs = [
                f"Ver {orc_data['numero']}",
                f"Enviar {orc_data['numero']} por WhatsApp",
            ]
            resp_dados = orc_data
        elif status == "forbidden":
            final_text = "❌ Sem permissão para esta ação."
            tipo_resp = None
            sugs = []
            resp_dados = {}
        else:
            final_text = (
                f"❌ Não foi possível concluir: {getattr(result, 'error', status)}"
            )
            tipo_resp = None
            sugs = []
            resp_dados = {}

        tool_trace_fpath = [{"tool": "(confirmação)", "status": status}]
        for word in final_text.split(" "):
            yield _enc({"chunk": word + " "})
        SessionStore.append_db(
            sessao_id,
            "assistant",
            final_text,
            db,
            empresa_id=getattr(current_user, "empresa_id", 0),
            usuario_id=getattr(current_user, "id", 0),
        )
        yield _enc(
            {
                "is_final": True,
                "final_text": final_text,
                "metadata": {
                    "final_text": final_text,
                    "tipo": tipo_resp,
                    "dados": {
                        **resp_dados,
                        "semantic_contract": _build_semantic_contract(
                            summary=final_text,
                            table=[resp_dados]
                            if isinstance(resp_dados, dict) and resp_dados
                            else [],
                            printable={
                                "title": "Resultado de ação confirmada",
                                "summary": final_text,
                            },
                            metadata_extra={
                                "capability": "PrepareQuotePackage",
                                "domain": "quote_ops",
                            },
                        ),
                    },
                    "tool_trace": tool_trace_fpath,
                    "sugestoes": sugs,
                    "pending_action": None,
                },
            }
        )
        return

    # ── Fast-path: simular desconto (0 tokens LLM) ───────────────────────────
    if not confirmation_token and _v2_is_simular_desconto_message(mensagem):
        resposta_sim = await _v2_build_simular_desconto_response(
            mensagem=mensagem,
            db=db,
            current_user=current_user,
            request_id=request_id,
        )
        if resposta_sim is not None:
            async for event in _emit_fastpath_ai_response(resposta_sim):
                yield event
            return

    # ── Fast-path: operador (aprovar/recusar/ver/enviar com ID explícito) ────
    if not confirmation_token and _v2_is_operador_fastpath_message(mensagem):
        resposta_op = await _v2_build_operador_fastpath_response(
            mensagem=mensagem,
            db=db,
            current_user=current_user,
            sessao_id=sessao_id,
            request_id=request_id,
        )
        if resposta_op is not None:
            if resposta_op.pending_action:
                tool_name_op = (resposta_op.pending_action or {}).get("tool", "?")
                yield _enc({"phase": "thinking"})
                yield _enc({"phase": "tool_running", "tool": tool_name_op})
                yield _enc({
                    "is_final": True,
                    "final_text": "",
                    "metadata": {
                        "final_text": "",
                        "tipo": "operador_action",
                        "dados": resposta_op.dados or {},
                        "tool_trace": resposta_op.tool_trace or [],
                        "sugestoes": [],
                        "pending_action": resposta_op.pending_action,
                        "input_tokens": 0,
                        "output_tokens": 0,
                    },
                })
            else:
                async for event in _emit_fastpath_ai_response(resposta_op):
                    yield event
            return

    # ── Fluxo normal: loop Tool Use v2 ────────────────────────────────────
    yield _enc({"phase": "thinking"})

    agora = datetime.now(_TZ_BR).strftime("%Y-%m-%d %H:%M")
    empresa_id = getattr(current_user, "empresa_id", 0)
    usuario_id = getattr(current_user, "id", 0)

    SessionStore.ensure_sessao_db(
        sessao_id=sessao_id,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        db=db,
    )
    history = SessionStore.get_or_create(
        sessao_id,
        db=db,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
    )
    SessionStore.append_db(
        sessao_id,
        "user",
        mensagem,
        db,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
    )

    system_prompt, prompt_strategy = _v2_build_system_prompt(
        mensagem=mensagem,
        resolved_engine=resolved_engine,
        now=agora,
    )
    allow_context_enrichment = prompt_strategy != "minimal"

    semantic_ctx = {}
    rag_ctx = {}
    adaptive_ctx = {}
    if engine_policy.allow_business_context and allow_context_enrichment:
        semantic_ctx = SemanticMemoryStore.build_context(
            db=db,
            empresa_id=getattr(current_user, "empresa_id", 0),
            mensagem=mensagem,
            usuario_id=getattr(current_user, "id", 0),
        )
        adaptive_ctx = AssistantPreferencesService.get_context_for_prompt(
            db=db,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            mensagem=mensagem,
        )
    if engine_policy.allow_tenant_rag and allow_context_enrichment:
        try:
            from app.services.rag import TenantRAGService

            rag_ctx = TenantRAGService.build_prompt_context(
                db=db,
                empresa_id=empresa_id,
                query=mensagem,
                top_k=4,
            )
        except Exception:
            rag_ctx = {}
    code_ctx = {}
    if (
        resolved_engine == ENGINE_INTERNAL_COPILOT
        and is_code_rag_enabled()
        and allow_context_enrichment
    ):
        try:
            from app.services.code_rag_service import build_code_context

            code_ctx = build_code_context(query=mensagem, top_k=4)
        except Exception:
            code_ctx = {}
    runtime_meta = _v2_build_runtime_meta(
        prompt_strategy=prompt_strategy,
        resolved_engine=resolved_engine,
        model_override=(
            settings.AI_TECHNICAL_MODEL
            if resolved_engine == ENGINE_INTERNAL_COPILOT
            else None
        ),
    )
    adaptive_meta = {
        **runtime_meta,
        "intent_detectada": intent_detectada,
        "visualizacao_recomendada": adaptive_ctx.get("preferencia_visualizacao_usuario")
        or {},
        "playbook_setor": adaptive_ctx.get("playbook_setor") or {},
    }

    if adaptive_ctx:
        _modulos = adaptive_ctx.get("modulos_ativos") or {}
        _nomes_modulos = {
            "clientes": "Clientes",
            "financeiro": "Financeiro",
            "catalogo": "Catálogo de Serviços",
            "orcamentos": "Orçamentos",
        }
        _linhas_modulos = [
            f"- {label}: {'habilitado' if _modulos.get(key, True) else 'DESABILITADO pelo usuário'}"
            for key, label in _nomes_modulos.items()
        ]
        system_prompt += (
            "\n\n## Módulos com acesso autorizado pelo usuário\n"
            + "\n".join(_linhas_modulos)
            + "\nRespeite estritamente: não busque, exiba nem infira dados de módulos DESABILITADOS."
        )

    messages: list[dict] = [
        {
            "role": "system",
            "content": system_prompt,
        },
    ]
    if semantic_ctx:
        messages.append(
            {
                "role": "system",
                "content": (
                    "## Memória semântica da empresa (use para reduzir repetição e aumentar precisão)\n"
                    + json.dumps(semantic_ctx, ensure_ascii=False, default=str)
                ),
            }
        )
    if rag_ctx and rag_ctx.get("context"):
        messages.append(
            {
                "role": "system",
                "content": (
                    "## Contexto RAG por tenant (usar somente como apoio factual)\n"
                    f"Fontes: {', '.join(rag_ctx.get('sources') or [])}\n\n"
                    + (rag_ctx.get("context") or "")
                ),
            }
        )
    if code_ctx and code_ctx.get("context"):
        messages.append(
            {
                "role": "system",
                "content": (
                    "## Code RAG técnico interno (usar apenas para suporte técnico interno)\n"
                    f"Fontes: {', '.join(code_ctx.get('sources') or [])}\n\n"
                    + (code_ctx.get("context") or "")
                ),
            }
        )
    _instrucoes_empresa = (adaptive_ctx or {}).get("instrucoes_empresa", "")
    if _instrucoes_empresa:
        messages.append(
            {
                "role": "system",
                "content": (
                    "## GUARDRAILS OBRIGATÓRIOS DA EMPRESA (aplicar em TODA resposta, sem exceção)\n"
                    + _instrucoes_empresa
                ),
            }
        )
    if adaptive_ctx:
        messages.append(
            {
                "role": "system",
                "content": (
                    "## Preferências adaptativas da empresa/usuário (aplicar por contexto)\n"
                    + json.dumps(adaptive_ctx, ensure_ascii=False, default=str)
                ),
            }
        )
    history_window = _v2_history_window_size(
        prompt_strategy=prompt_strategy,
        mensagem=mensagem,
    )
    for h in (history or [])[-history_window:]:
        role = h.get("role") if isinstance(h, dict) else getattr(h, "role", None)
        content = (
            h.get("content") if isinstance(h, dict) else getattr(h, "content", None)
        )
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": mensagem})
    logger.info(
        "[stream_v2] engine=%s prompt_strategy=%s system_chars=%s history=%s",
        resolved_engine,
        prompt_strategy,
        len(system_prompt),
        history_window,
    )

    tools_payload, full_tools_payload, reduced_tools_active, tool_profile = (
        _v2_select_tools_payload(
            mensagem=mensagem,
            prompt_strategy=prompt_strategy,
            resolved_engine=resolved_engine,
        )
    )
    adaptive_meta["tool_profile"] = tool_profile
    adaptive_meta["tool_count"] = len(tools_payload)
    adaptive_meta["tool_count_full"] = len(full_tools_payload)
    flow_started_perf = time.perf_counter()
    tool_trace: list[dict] = []

    pending_action: Optional[dict] = None
    total_in = 0
    total_out = 0
    final_text: Optional[str] = None
    final_tipo_resposta: Optional[str] = None
    final_interactive_payload: Optional[dict] = None
    expanded_tools_once = False

    modelo_injetado = (
        settings.AI_TECHNICAL_MODEL
        if resolved_engine == ENGINE_INTERNAL_COPILOT
        else None
    )

    for _iter in range(_V2_MAX_ITER):
        # Proteção: budget máximo de tokens
        if total_in > 15000:
            logger.warning("[v2_core] Token budget excedido (total_in=%s).", total_in)
            return AIResponse(
                sucesso=False,
                resposta="A consulta exigiu volume de dados além do limite seguro. Seja mais específico.",
                tipo_resposta="erro",
                confianca=0.0,
                modulo_origem="assistente_v2",
            )

        try:
            resp = await ia_service.chat(
                messages=_v2_apply_prompt_caching(messages),
                tools=tools_payload,
                temperature=0.3,
                max_tokens=1024,
                model_override=modelo_injetado,
            )
        except Exception as e:
            logger.exception("Falha na chamada ia_service.chat (v2)")
            return AIResponse(
                sucesso=False,
                resposta=f"Erro ao consultar assistente: {e}",
                confianca=0.0,
                modulo_origem="assistente_v2",
                erros=[str(e)],
            )

        usage = (
            resp.get("usage", {})
            if isinstance(resp, dict)
            else getattr(resp, "usage", {}) or {}
        )
        try:
            total_in += int(usage.get("prompt_tokens", 0) or 0)
            total_out += int(usage.get("completion_tokens", 0) or 0)
        except Exception:
            pass

        choices = (
            resp.get("choices")
            if isinstance(resp, dict)
            else getattr(resp, "choices", None)
        )
        if not choices:
            break
        choice = choices[0]
        msg = (
            choice.get("message")
            if isinstance(choice, dict)
            else getattr(choice, "message", None)
        )
        finish = (
            choice.get("finish_reason")
            if isinstance(choice, dict)
            else getattr(choice, "finish_reason", None)
        )

        # Extrair tool_calls
        tool_calls = None
        if msg is not None:
            tool_calls = (
                msg.get("tool_calls")
                if isinstance(msg, dict)
                else getattr(msg, "tool_calls", None)
            )
        if not tool_calls and not expanded_tools_once:
            candidate_text = (
                msg.get("content")
                if isinstance(msg, dict)
                else getattr(msg, "content", None)
            ) or ""
            if _v2_should_retry_with_full_tools(
                mensagem=mensagem,
                candidate_text=candidate_text,
                reduced_tools_active=reduced_tools_active,
            ):
                expanded_tools_once = True

                if total_in > 10000:
                    logger.warning(
                        "[v2_core] Blocking retry with full tools due to token budget (total_in=%s)",
                        total_in,
                    )
                else:
                    try:
                        resp_retry = await ia_service.chat(
                            messages=_v2_apply_prompt_caching(messages),
                            tools=full_tools_payload,
                            temperature=0.3,
                            max_tokens=1024,
                            model_override=modelo_injetado,
                        )
                        usage_retry = (
                            resp_retry.get("usage", {})
                            if isinstance(resp_retry, dict)
                            else getattr(resp_retry, "usage", {}) or {}
                        )
                        total_in += int(usage_retry.get("prompt_tokens", 0) or 0)
                        total_out += int(usage_retry.get("completion_tokens", 0) or 0)
                        choices_retry = (
                            resp_retry.get("choices")
                            if isinstance(resp_retry, dict)
                            else getattr(resp_retry, "choices", None)
                        )
                        if choices_retry:
                            choice = choices_retry[0]
                            msg = (
                                choice.get("message")
                                if isinstance(choice, dict)
                                else getattr(choice, "message", None)
                            )
                            finish = (
                                choice.get("finish_reason")
                                if isinstance(choice, dict)
                                else getattr(choice, "finish_reason", None)
                            )
                            tool_calls = (
                                msg.get("tool_calls")
                                if isinstance(msg, dict)
                                else getattr(msg, "tool_calls", None)
                            )
                            tools_payload = full_tools_payload
                            reduced_tools_active = False
                            adaptive_meta["tool_profile"] = "fallback_expanded_full"
                            adaptive_meta["tool_count"] = len(tools_payload)
                    except Exception:
                        logger.exception(
                            "Falha ao aplicar fallback para tools completas (v2)"
                        )

        if tool_calls:
            # Anexa o assistant turn com tool_calls (preservando ids)
            assistant_msg = {
                "role": "assistant",
                "content": (
                    msg.get("content")
                    if isinstance(msg, dict)
                    else getattr(msg, "content", None)
                )
                or "",
                "tool_calls": [
                    {
                        "id": (
                            tc.get("id")
                            if isinstance(tc, dict)
                            else getattr(tc, "id", None)
                        ),
                        "type": "function",
                        "function": {
                            "name": (
                                (
                                    tc.get("function", {})
                                    if isinstance(tc, dict)
                                    else getattr(tc, "function", None)
                                ).get("name")
                                if isinstance(tc, dict)
                                else getattr(
                                    getattr(tc, "function", None), "name", None
                                )
                            ),
                            "arguments": (
                                (
                                    tc.get("function", {})
                                    if isinstance(tc, dict)
                                    else getattr(tc, "function", None)
                                ).get("arguments")
                                if isinstance(tc, dict)
                                else getattr(
                                    getattr(tc, "function", None), "arguments", None
                                )
                            ),
                        },
                    }
                    for tc in tool_calls
                ],
            }
            messages.append(assistant_msg)

            for tc in tool_calls:
                tc_dict = (
                    tc
                    if isinstance(tc, dict)
                    else {
                        "id": getattr(tc, "id", None),
                        "function": {
                            "name": getattr(
                                getattr(tc, "function", None), "name", None
                            ),
                            "arguments": getattr(
                                getattr(tc, "function", None), "arguments", None
                            ),
                        },
                    }
                )
                result = await tool_execute(
                    tc_dict,
                    db=db,
                    current_user=current_user,
                    sessao_id=sessao_id,
                    request_id=request_id,
                    confirmation_token=confirmation_token,
                    engine=resolved_engine,
                )
                result = await _autopaginate_tool_result(
                    mensagem=mensagem,
                    tc=tc_dict,
                    result=result,
                    tool_execute=tool_execute,
                    db=db,
                    current_user=current_user,
                    sessao_id=sessao_id,
                    request_id=request_id,
                    confirmation_token=confirmation_token,
                    engine=resolved_engine,
                )
                t_status = result.status
                t_code = result.code
                t_error = result.error
                tool_trace.append(
                    {
                        "tool": (tc_dict.get("function") or {}).get("name"),
                        "status": t_status,
                        "latencia_ms": result.latencia_ms,
                        "code": t_code,
                        "reason": _tool_trace_reason(
                            status=t_status,
                            code=t_code,
                            error=t_error,
                        ),
                    }
                )
                payload = result.to_llm_payload()
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc_dict.get("id"),
                        "content": json.dumps(payload, ensure_ascii=False, default=str),
                    }
                )
                if result.status == "pending":
                    pending_action = result.pending_action
                    if isinstance(pending_action, dict) and not pending_action.get("extras"):
                        try:
                            from app.services.ai_tools.destructive_preview import (
                                build_destructive_extras,
                            )

                            pending_action["extras"] = await build_destructive_extras(
                                (pending_action.get("tool") or ""),
                                pending_action.get("args") or {},
                                db=db,
                                current_user=current_user,
                            )
                        except Exception:
                            logger.debug(
                                "Falha ao recomputar extras da ação pendente tool=%s",
                                pending_action.get("tool"),
                                exc_info=True,
                            )

            if pending_action:
                final_text = ""
                break
            # Próxima iteração: LLM verá os tool results
            continue

        # Sem tool_calls → resposta final
        raw_final_text = (
            msg.get("content")
            if isinstance(msg, dict)
            else getattr(msg, "content", None)
        ) or ""
        interactive_payload = _extract_interactive_ai_payload(raw_final_text)
        if interactive_payload:
            final_interactive_payload = interactive_payload
            final_tipo_resposta = interactive_payload.get("tipo") or final_tipo_resposta
            final_text = (
                interactive_payload.get("resposta")
                or interactive_payload.get("message")
                or interactive_payload.get("summary")
                or interactive_payload.get("resumo")
                or raw_final_text
            )
        else:
            final_text = raw_final_text
        if finish and finish != "stop" and finish != "tool_calls":
            logger.info("v2 finish_reason inesperado: %s", finish)
        break
    else:
        final_text = "Limite de iterações de ferramentas atingido. Refine a pergunta."

    if final_text:
        # Persiste resposta do assistente no banco
        SessionStore.append_db(
            sessao_id,
            "assistant",
            final_text,
            db,
            empresa_id=getattr(current_user, "empresa_id", 0),
            usuario_id=getattr(current_user, "id", 0),
        )

    if pending_action:
        dados_out = {
            **(pending_action.get("args") or {}),
            **(pending_action.get("extras") or {}),
            "input_tokens": total_in,
            "output_tokens": total_out,
            **adaptive_meta,
        }
    else:
        dados_out = {
            "input_tokens": total_in,
            "output_tokens": total_out,
            **adaptive_meta,
        }

    if isinstance(final_interactive_payload, dict):
        llm_dados = final_interactive_payload.get("dados")
        if isinstance(llm_dados, dict):
            dados_out = {**llm_dados, **dados_out}

    followup_pendente = _v2_extract_pending_followup_from_assistant_text(final_text or "")

    return AIResponse(
        sucesso=True,
        resposta=final_text or "",
        tipo_resposta=final_tipo_resposta,
        confianca=0.9 if final_text else 0.4,
        modulo_origem="assistente_v2",
        pending_action=pending_action,
        tool_trace=tool_trace or None,
        input_tokens=total_in,
        output_tokens=total_out,
        metrics={
            "tokens_in": total_in,
            "tokens_out": total_out,
            "iterations": _iter + 1,
            "engine": resolved_engine,
            "has_pending": bool(pending_action),
            "tool_calls": len(tool_trace) if tool_trace else 0,
            "total_duration_ms": int((time.perf_counter() - flow_started_perf) * 1000),
            "steps_with_error": sum(1 for step in tool_trace if str(step.get("status")).lower() in {"erro", "error"})
        },
        dados={
            **dados_out,
            "followup_pendente": followup_pendente,
        },
        chart_data=(final_interactive_payload or {}).get("chart_data") if final_interactive_payload else None,
        table_data=(final_interactive_payload or {}).get("table_data") if final_interactive_payload else None,
        actions=(final_interactive_payload or {}).get("actions") if final_interactive_payload else None,
        form_schema=(final_interactive_payload or {}).get("form_schema") if final_interactive_payload else None,
    )
