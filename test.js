const orcId = 172;
const orcNum = 'O-145';
const clienteNome = "Ana D'Julia";
function escapeHtml(s) { return s; }
const html = `<button type="button" class="orc-card-v2__icon-btn btn-calendar" onclick="abrirModalAgendamentoRapido(${orcId}, '${escapeHtml(orcNum)}', '${(clienteNome || '').replace(/'/g, "\\'")}')" title="Agendar">📅</button>`;
console.log(html);
