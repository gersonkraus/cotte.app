const assert = require('assert');
// Fake DOM
global.document = {
  getElementById: (id) => {
    const map = {
      'emp-utilizar-agendamento-auto': { value: 'false' },
      'emp-agendamento-somente-pos-liberacao': { value: 'true' },
      'emp-politica-agendamento-orc': { value: 'PADRAO_SIM' }
    };
    return map[id] || { value: '' };
  }
};
function _politicaAgendamentoSelectParaPayload(valorSelect) {
  const v = (valorSelect || '').toString().trim().toUpperCase();
  switch (v) {
    case 'PADRAO_SIM':
      return { agendamento_escolha_obrigatoria: false, agendamento_modo_padrao: 'OPCIONAL' };
    case 'EXIGE_ESCOLHA':
      return { agendamento_escolha_obrigatoria: true, agendamento_modo_padrao: 'NAO_USA' };
    case 'PADRAO_OBRIGATORIO':
      return { agendamento_escolha_obrigatoria: false, agendamento_modo_padrao: 'OBRIGATORIO' };
    case 'PADRAO_NAO':
    default:
      return { agendamento_escolha_obrigatoria: false, agendamento_modo_padrao: 'NAO_USA' };
  }
}
const payload = {
  ..._politicaAgendamentoSelectParaPayload(
    document.getElementById('emp-politica-agendamento-orc')?.value
  ),
  utilizar_agendamento_automatico:
    document.getElementById('emp-utilizar-agendamento-auto')?.value === 'true',
  agendamento_opcoes_somente_apos_liberacao:
    document.getElementById('emp-agendamento-somente-pos-liberacao')?.value === 'true',
};
console.log(payload);
