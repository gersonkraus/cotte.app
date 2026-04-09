"""Máquina de estados de orçamento — transições compartilhadas entre API e bot."""

from app.models.models import StatusOrcamento

# RASCUNHO → ENVIADO | ENVIADO → APROVADO | RECUSADO | EXPIRADO. Estados finais não permitem transição
# (exceto reaberturas definidas abaixo).
_TRANSICOES_PERMITIDAS: dict[StatusOrcamento, set[StatusOrcamento]] = {
    StatusOrcamento.RASCUNHO: {StatusOrcamento.ENVIADO},
    StatusOrcamento.ENVIADO: {
        StatusOrcamento.APROVADO,
        StatusOrcamento.RECUSADO,
        StatusOrcamento.EXPIRADO,
    },
    StatusOrcamento.APROVADO: {
        StatusOrcamento.ENVIADO,
        StatusOrcamento.RASCUNHO,
        StatusOrcamento.EM_EXECUCAO,
        StatusOrcamento.CONCLUIDO,  # pagamento 100% sem agendamento
    },
    StatusOrcamento.EM_EXECUCAO: {
        StatusOrcamento.APROVADO,
        StatusOrcamento.AGUARDANDO_PAGAMENTO,
        StatusOrcamento.CONCLUIDO,  # agendamento concluído + pagamento 100%
    },
    StatusOrcamento.AGUARDANDO_PAGAMENTO: {
        StatusOrcamento.EM_EXECUCAO,
        StatusOrcamento.CONCLUIDO,  # pagamento 100% recebido
    },
    StatusOrcamento.RECUSADO: {
        StatusOrcamento.RASCUNHO,
        StatusOrcamento.ENVIADO,
    },
    StatusOrcamento.EXPIRADO: {StatusOrcamento.RASCUNHO, StatusOrcamento.ENVIADO},
}


def transicao_permitida(de: StatusOrcamento, para: StatusOrcamento) -> bool:
    """Retorna True se a transição de status for permitida pela máquina de estados (idempotente se de == para)."""
    if de == para:
        return True
    return para in _TRANSICOES_PERMITIDAS.get(de, set())


def texto_transicao_negada(
    old_status: StatusOrcamento,
    novo_status: StatusOrcamento,
    *,
    para_bot: bool = False,
) -> str:
    """Mensagem quando a transição não é permitida (HTTP ou bot WhatsApp/dashboard)."""
    if para_bot:
        return (
            f"❌ Não é possível alterar de «{old_status.value}» para «{novo_status.value}» por aqui. "
            "As mesmas regras do painel se aplicam (ex.: aprovar/recusar só a partir de **Enviado**). "
            "Use o painel para estados avançados ou reabrir orçamentos."
        )
    return (
        f"Transição de status não permitida: de '{old_status.value}' para '{novo_status.value}'. "
        "Transições válidas: Rascunho → Enviado; Enviado → Aprovado, Recusado ou Expirado. "
        "Estados finais não podem ser alterados."
    )
