async def _v2_build_listar_orcamentos_fastpath_response(
    *,
    mensagem: str,
    db: Session,
    current_user: Any,
) -> AIResponse | None:
    from app.services.ai_tools.orcamento_tools import (
        _listar_orcamentos,
        ListarOrcamentosInput,
        _resolver_status_orcamento_listar,
        _gerar_relatorio_orcamentos,
        GerarRelatorioOrcamentosInput,
    )
    from datetime import date
    import re
    import logging
    logger = logging.getLogger(__name__)

    status_match = re.search(
        r"pendentes|enviados|aprovados|recusados|rascunho", mensagem.lower()
    )
    status_str = status_match.group(0) if status_match else None

    # Extrair filtros adicionais da mensagem gerada pelo botão "Carregar mais"
    # Ex: Liste mais orçamentos com cursor "...", dias 30, limite 10. Status pendente. Cliente 123.
    cursor_match = re.search(r'cursor "([^"]+)"', mensagem)
    cursor_val = cursor_match.group(1) if cursor_match else None

    dias_match = re.search(r'dias (\d+)', mensagem.lower())
    dias_val = int(dias_match.group(1)) if dias_match else 30

    limite_match = re.search(r'limit(?:e)? (\d+)', mensagem.lower())
    limite_val = int(limite_match.group(1)) if limite_match else 10
    
    cliente_match = re.search(r'cliente (\d+)', mensagem.lower())
    cliente_id_val = int(cliente_match.group(1)) if cliente_match else None

    try:
        aprovado_de_match = re.search(r'aprovado_em_de ([\d-]+)', mensagem.lower())
        aprovado_de_val = date.fromisoformat(aprovado_de_match.group(1)) if aprovado_de_match else None
    except ValueError:
        aprovado_de_val = None

    try:
        aprovado_ate_match = re.search(r'aprovado_em_ate ([\d-]+)', mensagem.lower())
        aprovado_ate_val = date.fromisoformat(aprovado_ate_match.group(1)) if aprovado_ate_match else None
    except ValueError:
        aprovado_ate_val = None

    # Substituir status se for extraído pelo comando explicitamente (ex: "Status pendente")
    status_cmd_match = re.search(r'status (\w+)', mensagem.lower())
    if status_cmd_match and not status_str:
        status_str = status_cmd_match.group(1)

    try:
        status_enum = (
            _resolver_status_orcamento_listar(status_str) if status_str else None
        )
        status_value = status_enum.value if status_enum else None
    except (KeyError, ValueError):
        status_value = None

    try:
        # 1. Busca os dados paginados para a visualização em tela
        inp_lista = ListarOrcamentosInput(
            status=status_value, 
            limit=limite_val,
            dias=dias_val,
            cursor=cursor_val,
            cliente_id=cliente_id_val,
            aprovado_em_de=aprovado_de_val,
            aprovado_em_ate=aprovado_ate_val
        )
        res_lista = await _listar_orcamentos(inp_lista, db=db, current_user=current_user)
        
        # 2. Busca a lista completa para o modo de impressão (até 1000 itens)
        inp_relatorio = GerarRelatorioOrcamentosInput(
            status=status_value,
            dias=dias_val,
            cliente_id=cliente_id_val,
            aprovado_em_de=aprovado_de_val,
            aprovado_em_ate=aprovado_ate_val
        )
        res_relatorio = await _gerar_relatorio_orcamentos(inp_relatorio, db=db, current_user=current_user)
    except Exception as e:
        logger.error(f"Erro no fastpath de listar orçamentos: {e}")
        return None

    if not isinstance(res_lista, dict) or res_lista.get("error"):
        logger.error(f"res_lista com erro: {res_lista.get('error')}")
        return None

    total = res_lista.get("total", 0)
    status_label = status_str or "encontrado(s)"
    resumo = f"Encontrei {total} orçamento(s) {status_label}."

    # Extrai a lista de orçamentos para a tabela paginada
    orcamentos_list_ui = res_lista.get("_meta_frontend_data", {}).get("orcamentos", [])
    
    # Extrai a lista completa de orçamentos para impressão
    orcamentos_list_impressao = res_relatorio.get("_meta_frontend_data", {}).get("orcamentos", [])

    return AIResponse(
        sucesso=True,
        resposta=resumo,
        tipo_resposta="lista_orcamentos",
        confianca=0.99,
        modulo_origem="assistente_v2",
        tool_trace=[{"tool": "listar_orcamentos", "status": "ok", "latencia_ms": 0}],
        dados={
            "_meta_frontend_data": res_lista.get("_meta_frontend_data"),
            "orcamentos": orcamentos_list_ui,
            "orcamentos_impressao": orcamentos_list_impressao,
            "total": total,
            "itens_retornados": res_lista.get("itens_retornados", len(orcamentos_list_ui)),
            "limit": res_lista.get("limit", 10),
            "has_more": res_lista.get("has_more", False),
            "next_cursor": res_lista.get("next_cursor"),
            "filtros": res_lista.get("filtros", {}),
            "totais_por_status": res_lista.get("totais_por_status", {}),
            "is_list": True,
            "input_tokens": 0,
            "output_tokens": 0,
            "intent_detectada": "LISTAR_ORCAMENTOS"
        },
    )
