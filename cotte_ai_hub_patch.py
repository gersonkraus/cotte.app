import re

def _v2_selected_tool_names_for_message(
    *,
    mensagem: str,
    prompt_strategy: str,
    resolved_engine: str,
) -> tuple[set[str] | None, str]:
    if resolved_engine != DEFAULT_ENGINE:
        return None, "engine_default"
        
    normalized = _v2_normalize_bootstrap_message(mensagem)
    intent = _v2_detect_deterministic_intent(mensagem)

    # Fast-paths e scoped tools para intents financeiras/inadimplência (mesmo no standard)
    is_financeiro = any(k in normalized for k in ("saldo", "caixa", "financeiro", "receita", "despesa", "faturamento", "inadimpl"))
    
    if prompt_strategy != "minimal" and not is_financeiro:
        return None, "full"

    if intent == "CONVERSACAO" and not _v2_message_likely_requires_tools(mensagem):
        return set(), "minimal_conversation_no_tools"

    # Base mais enxuta
    selected = set()
    
    if is_financeiro:
        selected |= {"obter_saldo_caixa", "listar_movimentacoes_financeiras", "listar_despesas", "listar_clientes"}
        # listar_orcamentos entra apenas se explicitamente falar sobre orçamentos/vendas
        if any(k in normalized for k in ("orcamento", "orçamento", "venda", "aprovar", "pendente")):
            selected |= {"listar_orcamentos"}
    else:
        selected |= _V2_TOOLSET_CORE_READONLY

    if any(k in normalized for k in ("orcamento", "orçamento", "aprovar", "recusar", "enviar")):
        selected |= _V2_TOOLSET_ORCAMENTOS
    if "cliente" in normalized:
        selected |= _V2_TOOLSET_CLIENTES
    if "agenda" in normalized or "agendamento" in normalized:
        selected |= _V2_TOOLSET_AGENDAMENTOS
    if "material" in normalized or "catalogo" in normalized or "catálogo" in normalized:
        selected |= _V2_TOOLSET_CATALOGO
        
    if intent == "OPERADOR":
        selected |= (
            _V2_TOOLSET_ORCAMENTOS
            | _V2_TOOLSET_CLIENTES
            | _V2_TOOLSET_FINANCEIRO
            | _V2_TOOLSET_AGENDAMENTOS
            | _V2_TOOLSET_CATALOGO
        )

    return selected, f"{prompt_strategy}_intent_scoped"
