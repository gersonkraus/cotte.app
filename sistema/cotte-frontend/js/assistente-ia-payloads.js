/**
 * Payloads puros do assistente (contrato com POST /api/v1/ai/orcamento/confirmar).
 * Usado em produção e nos testes Node (tests/unit).
 */

function buildConfirmarOrcamentoPayload(dados, clienteId) {
  return {
    cliente_id: clienteId,
    cliente_nome: dados.cliente_nome || 'A definir',
    servico: dados.servico || 'Serviço',
    valor: dados.valor || 0,
    desconto: dados.desconto || 0,
    desconto_tipo: dados.desconto_tipo || 'percentual',
    observacoes: dados.observacoes || null,
  };
}

if (typeof window !== 'undefined') {
  window.buildConfirmarOrcamentoPayload = buildConfirmarOrcamentoPayload;
}
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { buildConfirmarOrcamentoPayload };
}
