/**
 * agendamentos.js — Módulo de Agendamentos COTTE
 * Estilo Google Agenda com FullCalendar 6
 */

let calendar = null;
let clientesCache = [];
let responsaveisCache = [];
let orcamentosCache = [];
let filtrosStatus = new Set(['pendente', 'confirmado', 'em_andamento', 'concluido', 'reagendado', 'aguardando_escolha']);
let filtroTexto = '';
let filtroTipo = '';
let filtroResponsavel = '';
let contagemStatus = {};

// Cores por status - Google Calendar style
const STATUS_COLORS = {
  pendente:       { bg: '#fef7e0', border: '#fbbc04', text: '#b06000', label: 'Pendente' },
  confirmado:     { bg: '#e6f4ea', border: '#34a853', text: '#137333', label: 'Confirmado' },
  em_andamento:   { bg: '#e8f0fe', border: '#1a73e8', text: '#1967d2', label: 'Em Andamento' },
  concluido:      { bg: '#f1f3f4', border: '#5f6368', text: '#3c4043', label: 'Concluído' },
  reagendado:     { bg: '#f3e8fd', border: '#a142f4', text: '#7c4dff', label: 'Reagendado' },
  cancelado:      { bg: '#fce8e6', border: '#ea4335', text: '#c5221f', label: 'Cancelado' },
  nao_compareceu: { bg: '#fce8e6', border: '#ea4335', text: '#c5221f', label: 'Não Compareceu' },
  aguardando_escolha: { bg: '#fff3e0', border: '#ff9800', text: '#e65100', label: 'Aguardando Escolha' },
};

const TIPO_LABELS = {
  servico: 'Serviço',
  entrega: 'Entrega',
  instalacao: 'Instalação',
  manutencao: 'Manutenção',
  visita_tecnica: 'Visita Técnica',
  outro: 'Outro',
};

// ══════════════════════════════════════════════════════════════════════════════
// INICIALIZAÇÃO
// ══════════════════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', async () => {
  const token = localStorage.getItem('cotte_token');
  if (!token) { window.location.href = 'login.html'; return; }

  inicializarLayout('agendamentos');

  await Promise.all([
    carregarClientes(),
    carregarResponsaveis(),
    carregarOrcamentos(),
  ]);

  atualizarLabelStatus();
  inicializarCalendario();
  carregarDashboard();
  atualizarBadgePreFila();

  const pfb = document.getElementById('pre-fila-busca');
  if (pfb) {
    let _pfDebounce;
    pfb.addEventListener('input', () => {
      clearTimeout(_pfDebounce);
      _pfDebounce = setTimeout(() => carregarPreAgendamentoFila(), 350);
    });
    pfb.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { clearTimeout(_pfDebounce); carregarPreAgendamentoFila(); }
    });
  }

  // Detectar parâmetros URL para abertura automática do modal
  _processarUrlParams();
});

// ══════════════════════════════════════════════════════════════════════════════
// FULLCALENDAR
// ══════════════════════════════════════════════════════════════════════════════

function inicializarCalendario() {
  const el = document.getElementById('calendar');
  calendar = new FullCalendar.Calendar(el, {
    locale: 'pt-br',
    initialView: 'dayGridMonth',
    headerToolbar: false,
    allDaySlot: false,
    slotMinTime: '06:00:00',
    slotMaxTime: '22:00:00',
    slotDuration: '00:30:00',
    slotLabelFormat: { hour: '2-digit', minute: '2-digit', hour12: false },
    expandRows: true,
    nowIndicator: true,
    dayMaxEvents: 4,
    navLinks: true,
    selectable: true,
    selectMirror: true,
    unselectAuto: true,
    eventOverlap: false,
    slotEventOverlap: false,
    stickyHeaderDates: true,

    events: carregarEventos,
    eventClick: aoClicarEvento,
    select: aoSelecionarSlot,
    datesSet: aoMudarDatas,
    eventContent: renderizarEvento,
  });

  calendar.render();
  atualizarTitulo();
}

// ══════════════════════════════════════════════════════════════════════════════
// CARREGAMENTO DE DADOS
// ══════════════════════════════════════════════════════════════════════════════

async function carregarEventos(info, successCallback, failureCallback) {
  try {
    const params = new URLSearchParams({
      data_de: info.startStr,
      data_ate: info.endStr,
      per_page: 200,
    });
    if (filtroTipo) params.set('tipo', filtroTipo);
    if (filtroResponsavel) params.set('responsavel_id', filtroResponsavel);

    const data = await apiRequest('GET', `/agendamentos/?${params}`);

    // Contar status de TODOS os eventos (antes de filtrar) para os chips
    const todosEventos = (data || []).map(ag => ({
      extendedProps: { status: ag.status }
    }));
    atualizarContagemStatus(todosEventos);

    // Aplicar filtros de status e texto
    const eventos = (data || [])
      .filter(ag => filtrosStatus.has(ag.status))
      .filter(ag => !filtroTexto || (ag.cliente_nome || '').toLowerCase().includes(filtroTexto))
      .map(ag => {
        const sc = STATUS_COLORS[ag.status] || STATUS_COLORS.pendente;
        const inicio = ag.data_agendada || ag.primeira_opcao_data_hora;
        const durMin = ag.duracao_estimada_min || 60;
        let fim = ag.data_fim;
        if (!fim && inicio) {
          fim = new Date(new Date(inicio).getTime() + durMin * 60000).toISOString();
        }
        return {
          id: ag.id,
          title: ag.cliente_nome || 'Cliente',
          start: inicio,
          end: fim,
          backgroundColor: sc.bg,
          borderColor: sc.border,
          textColor: sc.text,
          extendedProps: { ...ag },
        };
      })
      .filter(ev => ev.start);

    successCallback(eventos);
  } catch (err) {
    console.error('Erro ao carregar eventos:', err);
    failureCallback(err);
  }
}

async function carregarClientes() {
  try {
    clientesCache = await apiRequest('GET', '/clientes/?per_page=200') || [];
    const select = document.getElementById('form-cliente');
    clientesCache.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = c.nome;
      select.appendChild(opt);
    });
  } catch (e) { console.error('Erro ao carregar clientes:', e); }
}

async function carregarResponsaveis() {
  try {
    responsaveisCache = await apiRequest('GET', '/agendamentos/responsaveis') || [];
    const selects = [
      document.getElementById('form-responsavel'),
      document.getElementById('agd-filtro-responsavel'),
      document.getElementById('bloq-responsavel'),
    ];
    responsaveisCache.forEach(r => {
      selects.forEach(sel => {
        if (!sel) return;
        const opt = document.createElement('option');
        opt.value = r.id;
        opt.textContent = r.nome;
        sel.appendChild(opt);
      });
    });
  } catch (e) { console.error('Erro ao carregar responsáveis:', e); }
}

async function carregarOrcamentos() {
  try {
    const data = await apiRequest('GET', '/orcamentos/?status=aprovado&per_page=100');
    orcamentosCache = data?.itens || data || [];
    const select = document.getElementById('form-orcamento');
    orcamentosCache.forEach(o => {
      const opt = document.createElement('option');
      opt.value = o.id;
      opt.textContent = `${o.numero} — ${o.cliente_nome || 'Cliente'}`;
      select.appendChild(opt);
    });
  } catch (e) { console.error('Erro ao carregar orçamentos:', e); }
}

async function carregarDashboard() {
  try {
    const dash = await apiRequest('GET', '/agendamentos/dashboard');
    if (dash) {
      document.getElementById('dash-hoje').textContent = dash.total_hoje || 0;
      document.getElementById('dash-pendentes').textContent = dash.pendentes_confirmacao || 0;
      document.getElementById('dash-confirmados').textContent = dash.confirmados_hoje || 0;
      document.getElementById('dash-andamento').textContent = dash.em_andamento || 0;
      document.getElementById('dash-proximos').textContent = dash.proximos_7_dias || 0;
    }
  } catch (e) { console.error('Erro ao carregar dashboard:', e); }
}

// ══════════════════════════════════════════════════════════════════════════════
// RENDERIZAÇÃO DE EVENTOS
// ══════════════════════════════════════════════════════════════════════════════

function renderizarEvento(eventInfo) {
  const ag = eventInfo.event.extendedProps;
  const status = ag.status || 'pendente';
  const sc = STATUS_COLORS[status] || STATUS_COLORS.pendente;

  if (eventInfo.view.type === 'dayGridMonth') {
    const hasOrc = ag.orcamento_numero;
    return {
      html: `<div style="display:flex;align-items:center;gap:4px;padding:1px 3px;font-size:11px;overflow:hidden;">
        <span style="width:6px;height:6px;border-radius:50%;background:${sc.border};flex-shrink:0"></span>
        ${hasOrc ? '<span style="flex-shrink:0;font-size:10px" title="Orçamento ' + ag.orcamento_numero + '">📋</span>' : ''}
        <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${ag.cliente_nome || '—'}</span>
      </div>`
    };
  }

  const hasOrc = ag.orcamento_numero;
  return {
    html: `<div style="display:flex;flex-direction:column;height:100%;padding:3px 5px;background:${sc.bg};border-left:3px solid ${sc.border};overflow:hidden;">
      <div style="display:flex;align-items:center;gap:3px">
        ${hasOrc ? '<span style="font-size:9px;flex-shrink:0" title="Orçamento ' + ag.orcamento_numero + '">📋</span>' : ''}
        <div style="font-weight:500;font-size:11px;color:${sc.text};overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${ag.cliente_nome || '—'}</div>
      </div>
      <div style="font-size:10px;opacity:0.8;color:${sc.text}">${TIPO_LABELS[ag.tipo] || ''}</div>
    </div>`
  };
}

// ══════════════════════════════════════════════════════════════════════════════
// INTERAÇÃO
// ══════════════════════════════════════════════════════════════════════════════

function _statusActions(ag) {
  const id = ag.id;
  const s = ag.status;
  const sep   = `<div class="agd-pop-sep"></div>`;
  const editar = `<button class="agd-popover-btn ghost" onclick="abrirModalEditar(${id})">✏️ Editar agendamento</button>`;

  const map = {
    pendente: [
      `<button class="agd-popover-btn blue"   onclick="acaoRapida(${id},'confirmado')">✓ Confirmar agendamento</button>`,
      `<button class="agd-popover-btn danger"  onclick="acaoRapida(${id},'cancelado')">✕ Cancelar</button>`,
      sep, editar,
    ],
    confirmado: [
      `<button class="agd-popover-btn blue"   onclick="acaoRapida(${id},'em_andamento')">▶ Iniciar atendimento</button>`,
      `<button class="agd-popover-btn"        onclick="abrirModalReagendar(${id})">↺ Reagendar</button>`,
      `<button class="agd-popover-btn danger"  onclick="acaoRapida(${id},'cancelado')">✕ Cancelar</button>`,
      sep, editar,
    ],
    em_andamento: [
      `<button class="agd-popover-btn primary" onclick="acaoRapida(${id},'concluido')">✓ Concluir atendimento</button>`,
      `<button class="agd-popover-btn danger"  onclick="acaoRapida(${id},'nao_compareceu')">✗ Cliente não compareceu</button>`,
      sep, editar,
    ],
    reagendado: [
      `<button class="agd-popover-btn blue"   onclick="acaoRapida(${id},'confirmado')">✓ Confirmar novo horário</button>`,
      `<button class="agd-popover-btn danger"  onclick="acaoRapida(${id},'cancelado')">✕ Cancelar</button>`,
      sep, editar,
    ],
    concluido:      [editar],
    cancelado:      [editar],
    nao_compareceu: [editar],
  };
  return map[s] || [editar];
}

function aoClicarEvento(info) {
  const ag = info.event.extendedProps;
  const el = info.el;
  const popover = document.getElementById('agd-popover');
  const sc = STATUS_COLORS[ag.status] || STATUS_COLORS.pendente;

  document.getElementById('pop-status').textContent = sc.label;
  document.getElementById('pop-status').style.background = sc.bg;
  document.getElementById('pop-status').style.color = sc.text;
  document.getElementById('pop-titulo').textContent = ag.cliente_nome || 'Sem nome';

  const dataExibir = ag.data_agendada || ag.primeira_opcao_data_hora;
  const sufixoData = ag.status === 'aguardando_escolha' && !ag.data_agendada && ag.primeira_opcao_data_hora
    ? ' <span style="opacity:0.75;font-size:11px">(1ª opção — cliente ainda escolhe)</span>'
    : '';
  let html = `
    <div class="agd-popover-row">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
      ${formatarData(dataExibir, true)}${sufixoData}
    </div>
    <div class="agd-popover-row">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
      ${ag.responsavel_nome || '—'}
    </div>
  `;
  if (ag.endereco) {
    html += `<div class="agd-popover-row"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>${ag.endereco}</div>`;
  }
  if (ag.orcamento_numero) {
    html += `<div class="agd-popover-row" style="cursor:pointer" onclick="window.open('orcamento-view.html?id=${ag.orcamento_id}','_blank')" title="Ver orçamento">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
      📋 ${ag.orcamento_numero} <span style="opacity:0.6;font-size:11px">— Ver orçamento →</span>
    </div>`;
  }

  document.getElementById('pop-body').innerHTML = html;

  document.getElementById('pop-actions').innerHTML = _statusActions(ag).join('');

  const rect = el.getBoundingClientRect();
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const margin = 10;
  const gap = 10;

  popover.classList.add('open');

  // Mede tamanho real após abrir para posicionar sem overflow
  const popRect = popover.getBoundingClientRect();
  const popWidth = popRect.width || 320;
  const popHeight = popRect.height || 220;

  // Preferência: direita do evento; fallback: esquerda; último recurso: clamp
  let left = rect.right + gap;
  if (left + popWidth + margin > viewportWidth) {
    left = rect.left - popWidth - gap;
  }
  left = Math.max(margin, Math.min(left, viewportWidth - popWidth - margin));

  // Alinha pelo topo do evento, limitando ao viewport para não vazar embaixo/cima
  let top = rect.top;
  top = Math.max(margin, Math.min(top, viewportHeight - popHeight - margin));

  popover.style.left = `${Math.round(left)}px`;
  popover.style.top = `${Math.round(top)}px`;
  setTimeout(() => {
    const fechar = (e) => {
      if (!popover.contains(e.target)) {
        popover.classList.remove('open');
        document.removeEventListener('mousedown', fechar);
      }
    };
    document.addEventListener('mousedown', fechar);
  }, 10);
}

// formatarData() — centralizada em js/utils.js (utils.js carregado via api.js → utils.js)

function aoSelecionarSlot(info) {
  abrirModalCriar(info.start);
}

async function buscarSlotsDisponiveis() {
  const dataVal = document.getElementById('form-data')?.value;
  const section = document.getElementById('slots-section');
  const lista = document.getElementById('slots-lista');
  if (!section || !lista) return;
  if (!dataVal) { section.style.display = 'none'; return; }

  const date = dataVal.split('T')[0];
  const respId = document.getElementById('form-responsavel')?.value;
  section.style.display = 'block';
  lista.innerHTML = '<span style="font-size:12px;color:var(--agd-muted)">Buscando horários…</span>';
  try {
    const params = new URLSearchParams({ data: date });
    if (respId) params.set('responsavel_id', respId);
    const slots = await apiRequest('GET', `/agendamentos/disponiveis?${params}`);
    if (!slots?.length) {
      lista.innerHTML = '<span style="font-size:12px;color:var(--agd-muted)">Nenhum horário disponível neste dia.</span>';
      return;
    }
    lista.innerHTML = slots.map(s =>
      `<button type="button" class="slot-chip" onclick="selecionarSlot('${s.inicio}','${s.fim}',this)">
        ${new Date(s.inicio).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'})}
      </button>`
    ).join('');
  } catch (e) {
    lista.innerHTML = '<span style="font-size:12px;color:var(--agd-muted)">Erro ao buscar horários.</span>';
  }
}

function selecionarSlot(inicio, fim, btn) {
  const d = new Date(inicio);
  const pad = n => String(n).padStart(2, '0');
  document.getElementById('form-data').value =
    `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  const durMin = Math.round((new Date(fim) - d) / 60000);
  if (durMin > 0) document.getElementById('form-duracao').value = durMin;
  document.querySelectorAll('.slot-chip').forEach(c => c.classList.remove('selected'));
  btn.classList.add('selected');
}

function filtrarEventos() {
  filtroTexto = (document.getElementById('agd-busca')?.value || '').toLowerCase().trim();
  filtroTipo = document.getElementById('agd-filtro-tipo')?.value || '';
  filtroResponsavel = document.getElementById('agd-filtro-responsavel')?.value || '';
  if (calendar) calendar.refetchEvents();
}

function filtrarPorCliente() { filtrarEventos(); }

function aoMudarDatas() {
  atualizarTitulo();
}

// ══════════════════════════════════════════════════════════════════════════════
// MODAL
// ══════════════════════════════════════════════════════════════════════════════

function abrirModalCriar(dataInicial) {
  fecharPopover();
  document.getElementById('modal-title').textContent = 'Novo Agendamento';
  document.getElementById('btn-salvar').textContent = 'Criar';
  document.getElementById('btn-cancelar-ag').style.display = 'none';
  document.getElementById('form-status-actions').style.display = 'none';
  document.getElementById('historico-section').style.display = 'none';
  document.getElementById('criar-via-orcamento').style.display = 'none';
  document.getElementById('slots-section').style.display = 'none';
  document.getElementById('form-id').value = '';

  document.getElementById('form-cliente').value = '';
  document.getElementById('form-orcamento').value = '';
  document.getElementById('form-tipo').value = 'servico';
  document.getElementById('form-responsavel').value = '';
  document.getElementById('form-duracao').value = 60;
  document.getElementById('form-endereco').value = '';
  document.getElementById('form-obs').value = '';

  if (dataInicial) {
    document.getElementById('form-data').value = toLocalDatetime(new Date(dataInicial));
  } else {
    const now = new Date();
    now.setMinutes(Math.ceil(now.getMinutes() / 30) * 30, 0, 0);
    now.setDate(now.getDate() + 1);
    document.getElementById('form-data').value = toLocalDatetime(now);
  }

  document.getElementById('modal-overlay').classList.add('open');
}

async function abrirModalEditar(agendamentoId) {
  fecharPopover();
  try {
    const ag = await apiRequest('GET', `/agendamentos/${agendamentoId}`);
    if (!ag) { toast('Agendamento não encontrado'); return; }

    document.getElementById('modal-title').textContent = `Agendamento ${ag.numero || ''}`;
    document.getElementById('btn-salvar').textContent = 'Salvar';
    document.getElementById('form-id').value = ag.id;

    document.getElementById('form-cliente').value = ag.cliente_id || '';
    document.getElementById('form-orcamento').value = ag.orcamento_id || '';
    document.getElementById('form-tipo').value = ag.tipo || 'servico';
    document.getElementById('form-responsavel').value = ag.responsavel_id || '';
    document.getElementById('form-data').value = toLocalDatetime(new Date(ag.data_agendada));
    document.getElementById('form-duracao').value = ag.duracao_estimada_min || 60;
    document.getElementById('form-endereco').value = ag.endereco || '';
    document.getElementById('form-obs').value = ag.observacoes || '';

    document.getElementById('form-status-actions').style.display = 'block';
    document.getElementById('form-status-atual').textContent = STATUS_COLORS[ag.status]?.label || ag.status;

    const podeC = ['pendente', 'confirmado', 'em_andamento'].includes(ag.status);
    document.getElementById('btn-cancelar-ag').style.display = podeC ? 'block' : 'none';

    document.getElementById('modal-overlay').classList.add('open');
    carregarHistorico(agendamentoId);
  } catch (e) {
    toast('Erro ao carregar agendamento');
  }
}

function fecharModal() {
  document.getElementById('modal-overlay').classList.remove('open');
}

function fecharModalFora(e) {
  if (e.target === e.currentTarget) fecharModal();
}

async function salvarAgendamento(e) {
  e.preventDefault();
  const id = document.getElementById('form-id').value;
  const clienteId = parseInt(document.getElementById('form-cliente').value);
  const orcamentoId = document.getElementById('form-orcamento').value;
  const tipo = document.getElementById('form-tipo').value;
  const responsavelId = document.getElementById('form-responsavel').value;
  const dataAgendada = document.getElementById('form-data').value;
  const duracao = parseInt(document.getElementById('form-duracao').value) || 60;
  const endereco = document.getElementById('form-endereco').value;
  const obs = document.getElementById('form-obs').value;

  if (!clienteId || !dataAgendada) {
    toast('Preencha os campos obrigatórios');
    return;
  }

  const payload = {
    cliente_id: clienteId,
    tipo: tipo,
    data_agendada: new Date(dataAgendada).toISOString(),
    duracao_estimada_min: duracao,
  };
  if (orcamentoId) payload.orcamento_id = parseInt(orcamentoId);
  if (responsavelId) payload.responsavel_id = parseInt(responsavelId);
  if (endereco) payload.endereco = endereco;
  if (obs) payload.observacoes = obs;

  try {
    const btn = document.getElementById('btn-salvar');
    btn.disabled = true;
    btn.textContent = 'Salvando…';

    if (id) {
      await apiRequest('PUT', `/agendamentos/${id}`, payload);
      toast('Agendamento atualizado!');
    } else {
      await apiRequest('POST', '/agendamentos/', payload);
      toast('Agendamento criado!');
    }

    fecharModal();
    calendar.refetchEvents();
    carregarDashboard();
  } catch (err) {
    toast(err?.detail || err?.message || 'Erro ao salvar');
  } finally {
    const btn = document.getElementById('btn-salvar');
    btn.disabled = false;
    btn.textContent = id ? 'Salvar' : 'Criar';
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// AÇÕES RÁPIDAS
// ══════════════════════════════════════════════════════════════════════════════

async function acaoRapida(id, novoStatus) {
  fecharPopover();
  try {
    await apiRequest('PATCH', `/agendamentos/${id}/status`, { status: novoStatus });
    toast(`Status: ${STATUS_COLORS[novoStatus]?.label || novoStatus}`);
    calendar.refetchEvents();
    carregarDashboard();
  } catch (err) {
    toast(err?.detail || 'Erro ao atualizar status');
  }
}

async function cancelarAgendamento() {
  const id = document.getElementById('form-id').value;
  if (!id) return;
  if (!confirm('Cancelar este agendamento?')) return;

  try {
    await apiRequest('PATCH', `/agendamentos/${id}/status`, { status: 'cancelado' });
    toast('Agendamento cancelado');
    fecharModal();
    calendar.refetchEvents();
    carregarDashboard();
  } catch (err) {
    toast(err?.detail || 'Erro ao cancelar');
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// REAGENDAMENTO
// ══════════════════════════════════════════════════════════════════════════════

function abrirModalReagendar(id) {
  fecharPopover();
  const agId = id || document.getElementById('form-id').value;
  if (!agId) return;
  document.getElementById('reagendar-id').value = agId;
  document.getElementById('reagendar-motivo').value = '';
  // pré-preenche com a data atual do agendamento se vier do modal de edição
  const dataAtual = document.getElementById('form-data')?.value || '';
  document.getElementById('reagendar-data').value = dataAtual;
  document.getElementById('modal-reagendar').classList.add('open');
}

function fecharModalReagendar() {
  document.getElementById('modal-reagendar').classList.remove('open');
}

async function confirmarReagendar() {
  const id = document.getElementById('reagendar-id').value;
  const novaData = document.getElementById('reagendar-data').value;
  if (!novaData) { toast('Informe a nova data e hora'); return; }

  const btn = document.getElementById('btn-confirmar-reagendar');
  btn.disabled = true;
  btn.textContent = 'Salvando…';
  try {
    await apiRequest('PATCH', `/agendamentos/${id}/reagendar`, {
      nova_data: new Date(novaData).toISOString(),
      motivo: document.getElementById('reagendar-motivo').value || undefined,
    });
    toast('Reagendado com sucesso');
    fecharModalReagendar();
    fecharModal();
    calendar.refetchEvents();
    carregarDashboard();
  } catch (err) {
    toast(err?.detail || err?.message || 'Erro ao reagendar');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Confirmar';
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// HISTÓRICO
// ══════════════════════════════════════════════════════════════════════════════

async function carregarHistorico(agId) {
  const section = document.getElementById('historico-section');
  const lista = document.getElementById('historico-lista');
  if (!section || !lista) return;
  section.style.display = 'block';
  lista.innerHTML = '<div style="font-size:12px;color:var(--agd-muted)">Carregando…</div>';
  try {
    const hist = await apiRequest('GET', `/agendamentos/${agId}/historico`);
    if (!hist || !hist.length) {
      lista.innerHTML = '<div style="font-size:12px;color:var(--agd-muted)">Sem registros.</div>';
      return;
    }
    lista.innerHTML = hist.map(h => {
      const sc = STATUS_COLORS[h.status_novo] || {};
      const de = h.status_anterior ? `<span style="opacity:.6">${STATUS_COLORS[h.status_anterior]?.label || h.status_anterior}</span> → ` : '';
      const data = h.criado_em ? new Date(h.criado_em).toLocaleString('pt-BR', {day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}) : '';
      return `<div style="display:flex;gap:8px;align-items:flex-start;font-size:12px">
        <span style="width:6px;height:6px;border-radius:50%;background:${sc.border||'#ccc'};flex-shrink:0;margin-top:4px"></span>
        <div>
          <span>${de}<strong style="color:${sc.text||'inherit'}">${sc.label || h.status_novo}</strong></span>
          ${h.editado_por_nome ? `<span style="color:var(--agd-muted)"> · ${h.editado_por_nome}</span>` : ''}
          ${h.descricao ? `<div style="color:var(--agd-muted);margin-top:2px">${h.descricao}</div>` : ''}
          <div style="color:var(--agd-muted)">${data}</div>
        </div>
      </div>`;
    }).join('');
  } catch (e) {
    lista.innerHTML = '<div style="font-size:12px;color:var(--agd-muted)">Erro ao carregar histórico.</div>';
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// NAVEGAÇÃO
// ══════════════════════════════════════════════════════════════════════════════

function navegarCal(dir) {
  if (dir < 0) calendar.prev();
  else calendar.next();
  atualizarTitulo();
}

function irHoje() {
  calendar.today();
  atualizarTitulo();
}

function mudarView(viewName) {
  const calEl = document.getElementById('calendar');
  const hojeEl = document.getElementById('agd-view-hoje');

  if (viewName === 'hoje') {
    calEl.style.display = 'none';
    hojeEl.style.display = 'block';
    carregarViewHoje();
  } else {
    calEl.style.display = '';
    hojeEl.style.display = 'none';
    calendar.changeView(viewName);
    atualizarTitulo();
  }
  document.querySelectorAll('.agd-view-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.view === viewName);
  });
}

async function carregarViewHoje() {
  const lista = document.getElementById('hoje-lista');
  if (!lista) return;
  lista.innerHTML = '<div style="font-size:13px;color:var(--agd-muted)">Carregando…</div>';
  try {
    const data = await apiRequest('GET', '/agendamentos/hoje');
    const items = Array.isArray(data) ? data : (data?.itens || []);
    const hoje = new Date().toLocaleDateString('pt-BR', {weekday:'long',day:'2-digit',month:'long'});
    document.getElementById('hoje-titulo').textContent = `Hoje — ${hoje}`;
    if (!items.length) {
      lista.innerHTML = '<div style="text-align:center;padding:32px 0;color:var(--agd-muted);font-size:13px">Nenhum agendamento para hoje.</div>';
      return;
    }
    lista.innerHTML = items.map(ag => {
      const sc = STATUS_COLORS[ag.status] || STATUS_COLORS.pendente;
      const hora = ag.data_agendada ? new Date(ag.data_agendada).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'}) : '—';
      const dur = ag.duracao_estimada_min ? `${ag.duracao_estimada_min}min` : '';
      const tipo = TIPO_LABELS[ag.tipo] || ag.tipo || '';
      return `<div class="hoje-card" onclick="abrirModalEditar(${ag.id})" style="border-left:3px solid ${sc.border}">
        <div class="hoje-hora">
          <span class="hoje-hora-num" style="color:${sc.text}">${hora}</span>
          ${dur ? `<span class="hoje-hora-dur">${dur}</span>` : ''}
        </div>
        <div class="hoje-info">
          <div class="hoje-nome">${ag.cliente_nome || '—'}</div>
          <div class="hoje-meta">${[tipo, ag.responsavel_nome].filter(Boolean).join(' · ')}</div>
        </div>
        <span style="display:inline-flex;align-items:center;padding:2px 9px;border-radius:999px;border:1px solid ${sc.border};background:${sc.bg};color:${sc.text};font-size:10px;font-weight:700;text-transform:uppercase;white-space:nowrap">${sc.label}</span>
      </div>`;
    }).join('');
  } catch (e) {
    lista.innerHTML = '<div style="font-size:13px;color:var(--agd-muted)">Erro ao carregar agendamentos de hoje.</div>';
  }
}

function atualizarTitulo() {
  const d = calendar.getDate();
  const meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
  const view = calendar.view.type;

  let titulo;
  if (view === 'dayGridMonth') {
    titulo = `${meses[d.getMonth()]} ${d.getFullYear()}`;
  } else if (view === 'timeGridWeek') {
    const ini = new Date(calendar.view.activeStart);
    const fim = new Date(calendar.view.activeEnd);
    fim.setDate(fim.getDate() - 1);
    if (ini.getMonth() === fim.getMonth()) {
      titulo = `${ini.getDate()} – ${fim.getDate()} ${meses[ini.getMonth()]}`;
    } else {
      titulo = `${ini.getDate()} ${meses[ini.getMonth()]} – ${fim.getDate()} ${meses[fim.getMonth()]}`;
    }
  } else {
    titulo = `${d.getDate()} ${meses[d.getMonth()]}`;
  }

  document.getElementById('agd-title').textContent = titulo;
}

// ══════════════════════════════════════════════════════════════════════════════
// FILTROS DE STATUS (CHIPS)
// ══════════════════════════════════════════════════════════════════════════════

function renderizarFiltrosStatus() {
  const container = document.getElementById('agd-status-chips');
  if (!container) return;
  container.innerHTML = '';

  const statusOrdem = ['pendente', 'aguardando_escolha', 'confirmado', 'em_andamento', 'concluido', 'reagendado', 'cancelado'];
  statusOrdem.forEach(status => {
    const sc = STATUS_COLORS[status];
    const isActive = filtrosStatus.has(status);
    const count = contagemStatus[status] || 0;

    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = `agd-status-chip${isActive ? ' active' : ''}`;
    chip.style.cssText = isActive
      ? `background:${sc.border};border-color:${sc.border};`
      : '';
    chip.innerHTML = `<span class="chip-dot" style="background:${sc.border}"></span>${sc.label}<span class="chip-count">${count}</span>`;
    chip.onclick = () => {
      if (isActive) {
        filtrosStatus.delete(status);
      } else {
        filtrosStatus.add(status);
      }
      renderizarFiltrosStatus();
      filtrarEventos();
    };
    container.appendChild(chip);
  });
}

function atualizarLabelStatus() {
  // Agora os chips substituem o label, mas mantemos para compatibilidade
  renderizarFiltrosStatus();
}

function selecionarTodosStatus() {
  const todos = ['pendente', 'aguardando_escolha', 'confirmado', 'em_andamento', 'concluido', 'reagendado', 'cancelado'];
  filtrosStatus.clear();
  todos.forEach(s => filtrosStatus.add(s));
  renderizarFiltrosStatus();
  filtrarEventos();
}

function limparTodosStatus() {
  filtrosStatus.clear();
  renderizarFiltrosStatus();
  filtrarEventos();
}

function atualizarContagemStatus(eventos) {
  contagemStatus = {};
  const statusOrdem = ['pendente', 'aguardando_escolha', 'confirmado', 'em_andamento', 'concluido', 'reagendado', 'cancelado'];
  statusOrdem.forEach(s => contagemStatus[s] = 0);

  (eventos || []).forEach(ev => {
    const st = ev.extendedProps?.status;
    if (st && contagemStatus[st] !== undefined) {
      contagemStatus[st]++;
    }
  });

  renderizarFiltrosStatus();
}

// ══════════════════════════════════════════════════════════════════════════════
// MODAL DASH
// ══════════════════════════════════════════════════════════════════════════════

const DASH_CONFIG = {
  hoje:       { titulo: 'Agendamentos de hoje',     params: () => { const d = new Date().toISOString().slice(0,10); return { data_de: d, data_ate: d, per_page: 100 }; } },
  pendentes:  { titulo: 'Pendentes de confirmação', params: () => ({ status: 'pendente', per_page: 100 }) },
  confirmados:{ titulo: 'Confirmados hoje',         params: () => { const d = new Date().toISOString().slice(0,10); return { status: 'confirmado', data_de: d, data_ate: d, per_page: 100 }; } },
  andamento:  { titulo: 'Em andamento',             params: () => ({ status: 'em_andamento', per_page: 100 }) },
  proximos:   { titulo: 'Próximos 7 dias',          params: () => { const d = new Date(); const fim = new Date(d); fim.setDate(fim.getDate() + 7); return { data_de: d.toISOString().slice(0,10), data_ate: fim.toISOString().slice(0,10), per_page: 100 }; } },
};

async function abrirModalDash(tipo) {
  const cfg = DASH_CONFIG[tipo];
  if (!cfg) return;

  document.getElementById('modal-dash-titulo').textContent = cfg.titulo;
  document.getElementById('modal-dash-body').innerHTML = '<div class="agd-dash-empty">Carregando…</div>';
  document.getElementById('modal-dash').style.display = 'flex';

  try {
    const params = new URLSearchParams(cfg.params());
    const lista = await apiRequest('GET', `/agendamentos/?${params}`);
    renderizarModalDash(lista || []);
  } catch (e) {
    document.getElementById('modal-dash-body').innerHTML = '<div class="agd-dash-empty">Erro ao carregar agendamentos.</div>';
  }
}

function renderizarModalDash(lista) {
  const body = document.getElementById('modal-dash-body');
  if (!lista.length) {
    body.innerHTML = '<div class="agd-dash-empty">Nenhum agendamento encontrado.</div>';
    return;
  }

  body.innerHTML = lista.map(ag => {
    const sc = STATUS_COLORS[ag.status] || STATUS_COLORS.pendente;
    const data = ag.data_agendada ? new Date(ag.data_agendada).toLocaleString('pt-BR', { day:'2-digit', month:'2-digit', hour:'2-digit', minute:'2-digit' }) : '—';
    const tipo = TIPO_LABELS[ag.tipo] || ag.tipo || '';
    return `
      <div class="agd-dash-card" onclick="fecharModalDash();abrirModalEditar(${ag.id})" style="cursor:pointer">
        <span class="agd-dash-card-dot" style="background:${sc.border}"></span>
        <div class="agd-dash-card-info">
          <div class="agd-dash-card-nome">${ag.cliente_nome || '—'}</div>
          <div class="agd-dash-card-meta">${data}${tipo ? ' · ' + tipo : ''}${ag.responsavel_nome ? ' · ' + ag.responsavel_nome : ''}</div>
        </div>
        <span class="agd-dash-card-status" style="background:${sc.bg};color:${sc.text}">${sc.label}</span>
      </div>`;
  }).join('');
}

function fecharModalDash() {
  document.getElementById('modal-dash').style.display = 'none';
}

function fecharPopover() {
  document.getElementById('agd-popover').classList.remove('open');
}

// ══════════════════════════════════════════════════════════════════════════════
// CONFIGURAÇÕES DA AGENDA
// ══════════════════════════════════════════════════════════════════════════════

function abrirModalConfig() {
  document.getElementById('modal-config').classList.add('open');
  mudarAbaConfig('empresa');
  carregarConfig();
}

function fecharModalConfig() {
  document.getElementById('modal-config').classList.remove('open');
}

function mudarAbaConfig(aba) {
  ['empresa', 'bloqueios'].forEach(a => {
    document.getElementById(`tab-${a}`)?.classList.toggle('active', a === aba);
    document.getElementById(`aba-${a}`).style.display = a === aba ? 'block' : 'none';
  });
  if (aba === 'bloqueios') carregarBloqueios();
}

function toggleDiaConfig(btn) {
  btn.classList.toggle('on');
}

async function carregarConfig() {
  try {
    const cfg = await apiRequest('GET', '/agendamentos/config/empresa');
    if (!cfg) return;
    document.getElementById('cfg-horario-inicio').value = cfg.horario_inicio || '08:00';
    document.getElementById('cfg-horario-fim').value = cfg.horario_fim || '18:00';
    document.getElementById('cfg-duracao').value = cfg.duracao_padrao_min || 60;
    document.getElementById('cfg-intervalo').value = cfg.intervalo_minimo_min || 30;
    document.getElementById('cfg-antecedencia').value = cfg.antecedencia_minima_horas || 24;
    const chk = document.getElementById('cfg-requer-confirmacao');
    chk.checked = cfg.requer_confirmacao !== false;
    document.getElementById('cfg-confirmacao-label').textContent = chk.checked ? 'Sim' : 'Não';
    const chkCliente = document.getElementById('cfg-permite-cliente');
    if (chkCliente) chkCliente.checked = cfg.permite_agendamento_cliente === true;
    const msgConf = document.getElementById('cfg-msg-confirmacao');
    if (msgConf) msgConf.value = cfg.mensagem_confirmacao || '';
    const msgReag = document.getElementById('cfg-msg-reagendamento');
    if (msgReag) msgReag.value = cfg.mensagem_reagendamento || '';
    const diasAtivos = cfg.dias_trabalho || [0, 1, 2, 3, 4];
    document.querySelectorAll('.agd-dia-btn').forEach(btn => {
      btn.classList.toggle('on', diasAtivos.includes(parseInt(btn.dataset.dia)));
    });
  } catch (e) { console.error('Erro ao carregar config:', e); }
}

async function salvarConfig() {
  const btn = document.getElementById('btn-salvar-config');
  btn.disabled = true; btn.textContent = 'Salvando…';
  const dias = [];
  document.querySelectorAll('.agd-dia-btn.on').forEach(b => dias.push(parseInt(b.dataset.dia)));
  const payload = {
    horario_inicio: document.getElementById('cfg-horario-inicio').value,
    horario_fim: document.getElementById('cfg-horario-fim').value,
    dias_trabalho: dias,
    duracao_padrao_min: parseInt(document.getElementById('cfg-duracao').value),
    intervalo_minimo_min: parseInt(document.getElementById('cfg-intervalo').value),
    antecedencia_minima_horas: parseInt(document.getElementById('cfg-antecedencia').value),
    requer_confirmacao: document.getElementById('cfg-requer-confirmacao').checked,
    permite_agendamento_cliente: document.getElementById('cfg-permite-cliente')?.checked || false,
    mensagem_confirmacao: document.getElementById('cfg-msg-confirmacao')?.value || null,
    mensagem_reagendamento: document.getElementById('cfg-msg-reagendamento')?.value || null,
  };
  try {
    await apiRequest('PUT', '/agendamentos/config/empresa', payload);
    toast('Configurações salvas!');
    fecharModalConfig();
  } catch (err) {
    toast(err?.detail || 'Erro ao salvar configurações');
  } finally {
    btn.disabled = false; btn.textContent = 'Salvar configurações';
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// BLOQUEIOS DE HORÁRIO
// ══════════════════════════════════════════════════════════════════════════════

async function carregarBloqueios() {
  const lista = document.getElementById('lista-bloqueios');
  if (!lista) return;
  lista.innerHTML = '<div style="font-size:13px;color:var(--agd-muted)">Carregando…</div>';
  try {
    const data = await apiRequest('GET', '/agendamentos/bloqueados');
    const items = data || [];
    if (!items.length) {
      lista.innerHTML = '<div style="font-size:13px;color:var(--agd-muted)">Nenhum bloqueio cadastrado.</div>';
      return;
    }
    lista.innerHTML = items.map(b => {
      const de = new Date(b.data_inicio).toLocaleString('pt-BR', {day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'});
      const ate = new Date(b.data_fim).toLocaleString('pt-BR', {day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'});
      const quem = b.usuario_nome || 'Empresa toda';
      return `<div class="agd-bloqueio-item">
        <div class="agd-bloqueio-info">
          <div class="agd-bloqueio-titulo">${b.motivo || 'Bloqueio'}</div>
          <div class="agd-bloqueio-meta">${de} → ${ate} · ${quem}</div>
        </div>
        <button class="agd-modal-close" onclick="deletarBloqueio(${b.id})" title="Remover">×</button>
      </div>`;
    }).join('');
  } catch (e) {
    lista.innerHTML = '<div style="font-size:13px;color:var(--agd-muted)">Erro ao carregar bloqueios.</div>';
  }
}

async function adicionarBloqueio() {
  const inicio = document.getElementById('bloq-inicio').value;
  const fim = document.getElementById('bloq-fim').value;
  if (!inicio || !fim) { toast('Informe data de início e fim'); return; }
  if (new Date(inicio) >= new Date(fim)) { toast('Data fim deve ser após o início'); return; }
  const btn = document.getElementById('btn-add-bloqueio');
  btn.disabled = true; btn.textContent = 'Adicionando…';
  const payload = {
    data_inicio: new Date(inicio).toISOString(),
    data_fim: new Date(fim).toISOString(),
    recorrente: false,
  };
  const motivo = document.getElementById('bloq-motivo').value;
  if (motivo) payload.motivo = motivo;
  const responsavelId = document.getElementById('bloq-responsavel').value;
  if (responsavelId) payload.usuario_id = parseInt(responsavelId);
  try {
    await apiRequest('POST', '/agendamentos/bloquear-slot', payload);
    document.getElementById('bloq-inicio').value = '';
    document.getElementById('bloq-fim').value = '';
    document.getElementById('bloq-motivo').value = '';
    document.getElementById('bloq-responsavel').value = '';
    toast('Bloqueio adicionado!');
    carregarBloqueios();
  } catch (err) {
    toast(err?.detail || 'Erro ao adicionar bloqueio');
  } finally {
    btn.disabled = false; btn.textContent = '＋ Adicionar bloqueio';
  }
}

async function deletarBloqueio(id) {
  if (!confirm('Remover este bloqueio?')) return;
  try {
    await apiRequest('DELETE', `/agendamentos/bloquear-slot/${id}`);
    toast('Bloqueio removido');
    carregarBloqueios();
  } catch (err) { toast(err?.detail || 'Erro ao remover'); }
}

// ══════════════════════════════════════════════════════════════════════════════
// CRIAR VIA ORÇAMENTO
// ══════════════════════════════════════════════════════════════════════════════

function toggleCriarViaOrcamento() {
  const id = document.getElementById('form-orcamento').value;
  const div = document.getElementById('criar-via-orcamento');
  div.style.display = id ? 'flex' : 'none';

  // Preencher endereço automaticamente ao selecionar orçamento
  if (id && orcamentosCache.length) {
    const orc = orcamentosCache.find(o => String(o.id) === String(id));
    if (orc && orc.cliente_endereco) {
      document.getElementById('form-endereco').value = orc.cliente_endereco;
    }
    // Se não tem endereço no orçamento, tentar do cliente
    if (orc && !orc.cliente_endereco && orc.cliente_id && clientesCache.length) {
      const cliente = clientesCache.find(c => c.id === orc.cliente_id);
      if (cliente && cliente.endereco) {
        document.getElementById('form-endereco').value = cliente.endereco;
      }
    }
  }
}

async function criarViaOrcamento() {
  const orcId = document.getElementById('form-orcamento').value;
  const data = document.getElementById('form-data').value;
  if (!orcId) return;
  if (!data) { toast('Informe a data e hora antes de continuar'); return; }
  const btn = document.querySelector('#criar-via-orcamento .agd-btn');
  if (btn) { btn.disabled = true; btn.textContent = 'Criando…'; }
  const payload = { data_agendada: new Date(data).toISOString(), duracao_estimada_min: parseInt(document.getElementById('form-duracao').value) || 60 };
  const resp = document.getElementById('form-responsavel').value;
  if (resp) payload.responsavel_id = parseInt(resp);
  const obs = document.getElementById('form-obs').value;
  if (obs) payload.observacoes = obs;
  try {
    await apiRequest('POST', `/agendamentos/criar-do-orcamento/${orcId}`, payload);
    toast('Agendamento criado via orçamento!');
    fecharModal();
    calendar.refetchEvents();
    carregarDashboard();
  } catch (err) {
    toast(err?.detail || err?.message || 'Erro ao criar via orçamento');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '📋 Criar via orçamento'; }
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// HELPERS
// ══════════════════════════════════════════════════════════════════════════════

// Processar parâmetros URL — chamado na inicialização
function _processarUrlParams() {
  const params = new URLSearchParams(window.location.search);
  if (params.get('novo') !== 'true') return;

  const orcamentoId = params.get('orcamento_id');
  const clienteNome = params.get('cliente');

  // Limpar URL para não re-abrir ao recarregar
  window.history.replaceState({}, '', 'agendamentos.html');

  // Aguardar um pouco para o calendário renderizar
  setTimeout(() => {
    abrirModalCriar();

    // Pré-selecionar orçamento se veio da tela de orçamentos
    if (orcamentoId) {
      const selectOrc = document.getElementById('form-orcamento');
      if (selectOrc) {
        selectOrc.value = orcamentoId;
        toggleCriarViaOrcamento(); // Preenche endereço e mostra botão
      }
    }

    // Pré-selecionar cliente se veio da tela de orçamentos
    if (clienteNome) {
      const selectCliente = document.getElementById('form-cliente');
      if (selectCliente && clientesCache.length) {
        const cliente = clientesCache.find(
          c => c.nome.toLowerCase() === decodeURIComponent(clienteNome).toLowerCase()
        );
        if (cliente) {
          selectCliente.value = cliente.id;
        }
      }
    }
  }, 300);
}

function toast(msg) {
  const el = document.getElementById('agd-toast');
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 3000);
}

function toLocalDatetime(date) {
  const pad = n => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

// ══════════════════════════════════════════════════════════════════════════════
// PRÉ-AGENDAMENTO (fila pós-aprovação)
// ══════════════════════════════════════════════════════════════════════════════

function _toggleCalendarUI(show) {
  // Classe helper para esconder elementos (inclusive os com !important no media query)
  const cls = 'agd-hidden-prefila';
  ['.agd-toolbar-left', '.agd-dash', '.agd-view-btns', '.agd-mobile-views',
   '.agd-filters-bar'].forEach((sel) => {
    const el = document.querySelector(sel);
    if (el) el.classList.toggle(cls, !show);
  });
  // Topbar: esconde actions (chips, botão Novo Agendamento) no modo pré-fila
  const topActions = document.getElementById('agd-topbar-actions');
  if (topActions) topActions.classList.toggle(cls, !show);
  // Atualiza título/subtítulo da topbar
  const title = document.getElementById('agd-page-title');
  const sub = document.getElementById('agd-page-sub');
  if (title) title.textContent = show ? 'Agendamentos' : 'Pré-agendamento';
  if (sub) sub.textContent = show ? 'Gerencie sua agenda' : 'Libere orçamentos aprovados para agendamento';
}

function mostrarPainelAgenda() {
  document.getElementById('btn-modo-agenda')?.classList.add('active');
  document.getElementById('btn-modo-prefila')?.classList.remove('active');
  _toggleCalendarUI(true);
  const wrap = document.getElementById('agd-cal-wrap');
  const panel = document.getElementById('agd-pre-fila-panel');
  if (wrap) wrap.style.display = '';
  if (panel) panel.style.display = 'none';

  // Após esconder o wrap com display:none, o FullCalendar fica com dimensão 0;
  // ao voltar é obrigatório updateSize(). Também restaura calendário vs. lista "Hoje".
  const activeBtn = document.querySelector('.agd-view-btn.active');
  const viewName = activeBtn?.dataset?.view || 'timeGridWeek';
  const calEl = document.getElementById('calendar');
  const hojeEl = document.getElementById('agd-view-hoje');
  if (viewName === 'hoje') {
    if (calEl) calEl.style.display = 'none';
    if (hojeEl) hojeEl.style.display = 'block';
    carregarViewHoje();
  } else {
    if (calEl) calEl.style.display = '';
    if (hojeEl) hojeEl.style.display = 'none';
    requestAnimationFrame(() => {
      if (calendar) {
        calendar.updateSize();
      }
    });
  }
}

function mostrarPainelPreFila() {
  document.getElementById('btn-modo-prefila')?.classList.add('active');
  document.getElementById('btn-modo-agenda')?.classList.remove('active');
  _toggleCalendarUI(false);
  const wrap = document.getElementById('agd-cal-wrap');
  const panel = document.getElementById('agd-pre-fila-panel');
  if (wrap) wrap.style.display = 'none';
  if (panel) panel.style.display = 'block';
  carregarPreAgendamentoFila();
}

function atualizarBadgeContagemPreFila(n) {
  const badge = document.getElementById('pre-fila-count');
  if (!badge) return;
  badge.textContent = String(n);
  badge.style.display = n > 0 ? 'inline-block' : 'none';
}

async function atualizarBadgePreFila() {
  const badge = document.getElementById('pre-fila-count');
  if (!badge) return;
  try {
    const rows = await apiRequest('GET', '/agendamentos/pre-agendamento/fila');
    const n = Array.isArray(rows) ? rows.length : 0;
    atualizarBadgeContagemPreFila(n);
  } catch (_) {
    badge.style.display = 'none';
  }
}

function _canalLabel(c) {
  const m = { publico: 'Público', whatsapp: 'WhatsApp', manual: 'Painel', ia: 'IA' };
  return m[c] || c || '—';
}

// ── Canal filter chips ──────────────────────────────────────────────────────
let _activeCanalFilter = '';

// Botão "Todos" — sempre limpa o filtro e exibe tudo
function resetCanalFilter(btn) {
  document.querySelectorAll('.pf-canal-chip').forEach((c) => c.classList.remove('active'));
  btn.classList.add('active');
  _activeCanalFilter = '';
  carregarPreAgendamentoFila();
}

function toggleCanalFilter(btn) {
  const canal = btn.dataset.canal;
  const wasActive = btn.classList.contains('active');
  document.querySelectorAll('.pf-canal-chip').forEach((c) => c.classList.remove('active'));
  if (wasActive) {
    // Desativar canal específico → volta para "Todos"
    const todosBtn = document.querySelector('.pf-canal-chip[data-canal="todos"]');
    if (todosBtn) todosBtn.classList.add('active');
    _activeCanalFilter = '';
  } else {
    btn.classList.add('active');
    _activeCanalFilter = canal;
  }
  carregarPreAgendamentoFila();
}

function _atualizarContagensCanal(rows) {
  const counts = {};
  (rows || []).forEach((r) => {
    const c = r.aprovado_canal || 'unknown';
    counts[c] = (counts[c] || 0) + 1;
  });
  document.querySelectorAll('[data-count-canal]').forEach((el) => {
    const c = el.dataset.countCanal;
    const n = counts[c] || 0;
    el.textContent = n > 0 ? n : '';
  });
}

function refreshPreFila() {
  const btn = document.getElementById('pf-refresh-btn');
  if (btn) {
    btn.classList.add('pf-spinning');
    setTimeout(() => btn.classList.remove('pf-spinning'), 600);
  }
  carregarPreAgendamentoFila();
}

function _renderPayProgress(r) {
  const pct = typeof r.percentual_pago === 'number' ? Math.min(r.percentual_pago, 100) : 0;
  const total = r.total || 0;
  const pago = total * pct / 100;
  const pagoFmt  = pago.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  const totalFmt = total > 0 ? total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) : '—';
  const barCls    = pct >= 100 ? 'pf-100' : pct > 0 ? 'pf-partial' : 'pf-zero';
  const statusTxt = pct >= 100 ? 'Quitado' : pct > 0 ? 'Parcial' : 'Pendente';
  const statusCls = pct >= 100 ? 'pf-status-ok' : pct > 0 ? 'pf-status-partial' : 'pf-status-blocked';
  return { pct, pagoFmt, totalFmt, barCls, statusTxt, statusCls };
}

function _preFilaSkeleton() {
  return `<div class="pf-skeleton">${Array.from({length: 4}, () => `
    <div class="pf-skeleton-row">
      <div class="pf-sk pf-sk-circle"></div>
      <div class="pf-sk-block">
        <div class="pf-sk pf-sk-line s-l"></div>
        <div class="pf-sk pf-sk-line s-m"></div>
        <div class="pf-sk pf-sk-line s-s"></div>
      </div>
      <div class="pf-sk pf-sk-bar"></div>
      <div class="pf-sk pf-sk-btn"></div>
    </div>`).join('')}</div>`;
}

function _preFilaEmpty() {
  return `<div class="pf-empty">
    <svg class="pf-empty-icon" width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
      <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
      <path d="M9 14l2 2 4-4" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    <p class="pf-empty-title">Fila vazia</p>
    <p class="pf-empty-hint">Orçamentos aprovados com liberação pendente aparecerão aqui.</p>
  </div>`;
}

function atualizarBatchBar() {
  const checked = document.querySelectorAll('.pre-fila-cb:checked');
  const bar = document.getElementById('pf-batch-bar');
  const countEl = document.getElementById('pf-batch-count');
  if (!bar) return;
  const n = checked.length;
  if (n > 0) {
    bar.style.display = 'flex';
    if (countEl) countEl.textContent = `${n} selecionado${n > 1 ? 's' : ''}`;
  } else {
    bar.style.display = 'none';
  }
}

function desmarcarTodosPreFila() {
  document.querySelectorAll('.pre-fila-cb:checked').forEach((cb) => { cb.checked = false; });
  const all = document.getElementById('pre-fila-check-all');
  if (all) all.checked = false;
  atualizarBatchBar();
}

function _bindPreFilaCheckboxes(host) {
  const all = document.getElementById('pre-fila-check-all');
  if (all) {
    all.addEventListener('change', () => {
      host.querySelectorAll('.pre-fila-cb:not([disabled])').forEach((cb) => { cb.checked = all.checked; });
      atualizarBatchBar();
    });
  }
  host.querySelectorAll('.pre-fila-cb').forEach((cb) => {
    cb.addEventListener('change', atualizarBatchBar);
  });
  atualizarBatchBar();
}

async function carregarPreAgendamentoFila() {
  const host = document.getElementById('pre-fila-lista');
  if (!host) return;
  host.innerHTML = _preFilaSkeleton();
  const canal = _activeCanalFilter;
  const busca = (document.getElementById('pre-fila-busca') || {}).value || '';
  const params = new URLSearchParams();
  if (canal) params.set('canal', canal);
  if (busca.trim()) params.set('busca', busca.trim());
  // Reset batch bar ao recarregar
  const bar = document.getElementById('pf-batch-bar');
  if (bar) bar.style.display = 'none';
  try {
    // Sempre busca todos para alimentar contadores, filtra no cliente se canal ativo
    const allRows = await apiRequest('GET', `/agendamentos/pre-agendamento/fila?${busca.trim() ? 'busca=' + encodeURIComponent(busca.trim()) : ''}`);
    _atualizarContagensCanal(allRows);
    const rows = canal ? (allRows || []).filter((r) => r.aprovado_canal === canal) : allRows;
    // Badge do toggle sempre reflete total geral (sem filtro canal)
    atualizarBadgeContagemPreFila(Array.isArray(allRows) ? allRows.length : 0);
    if (!rows || !rows.length) {
      host.innerHTML = _preFilaEmpty();
      return;
    }

    // ── tabela desktop ──────────────────────────────────────────────────────
    let tableHtml = `<div class="pf-table-view pf-table-wrap">
      <table class="pf-table">
        <thead><tr>
          <th style="width:36px"><input type="checkbox" id="pre-fila-check-all" title="Selecionar todos"></th>
          <th>Cliente</th>
          <th>Pagamento</th>
          <th>Total</th>
          <th>Canal</th>
          <th>Aprovado</th>
          <th>Mensagem</th>
          <th class="pf-col-action"></th>
        </tr></thead>
        <tbody>`;
    rows.forEach((r) => {
      const nome     = (r.cliente_nome || '').replace(/</g, '&lt;') || '—';
      const avatar   = `<div class="pf-avatar" style="background:${corAvatar(r.cliente_nome || '')}">${iniciaisDe(r.cliente_nome || '')}</div>`;
      const orcLink  = `<a class="pf-orc-link" href="orcamento-view.html?id=${r.orcamento_id}" target="_blank" rel="noopener">${r.numero || '#' + r.orcamento_id}</a>`;
      const dt       = r.aprovado_em ? new Date(r.aprovado_em).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—';
      const canalCls = 'pf-canal-' + (r.aprovado_canal || 'manual');
      const msg      = (r.aceite_mensagem || '').replace(/</g, '&lt;').slice(0, 70);
      const msgTitle = (r.aceite_mensagem || '').replace(/"/g, '&quot;');
      const dis      = r.pagamento_ok_para_liberar ? '' : ' disabled title="Pagamento 100% exigido pela empresa"';
      const { pct, pagoFmt, totalFmt, barCls, statusTxt, statusCls } = _renderPayProgress(r);
      const totalVal = r.total != null ? r.total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) : '—';
      tableHtml += `<tr>
        <td><input type="checkbox" class="pre-fila-cb" value="${r.orcamento_id}"${dis}></td>
        <td>
          <div class="pf-cell-cliente">
            ${avatar}
            <div class="pf-cliente-info">
              <div class="pf-cliente-nome" title="${nome}">${nome}</div>
              ${orcLink}
            </div>
          </div>
        </td>
        <td>
          <div class="pf-pay-progress">
            <div class="pf-pay-label">
              <span class="pf-pay-label-text">${r.total ? pagoFmt + ' de ' + totalFmt + ' · ' + pct.toFixed(0) + '%' : '—'}</span>
              <span class="pf-pay-status ${statusCls}">${statusTxt}</span>
            </div>
            <div class="pf-pay-bar-wrap"><div class="pf-pay-bar ${barCls}" style="width:${pct}%"></div></div>
          </div>
        </td>
        <td><span class="pf-total-val">${totalVal}</span></td>
        <td><span class="pf-canal-badge ${canalCls}">${_canalLabel(r.aprovado_canal)}</span></td>
        <td class="pf-date-cell">${dt}</td>
        <td class="pf-msg-cell" title="${msgTitle}">${msg || '—'}</td>
        <td class="pf-col-action"><button type="button" class="pf-btn-liberar" data-orc-id="${r.orcamento_id}" onclick="liberarUmPreAgendamento(${r.orcamento_id})"${dis}>Liberar</button></td>
      </tr>`;
    });
    tableHtml += '</tbody></table></div>';

    // ── cards mobile ────────────────────────────────────────────────────────
    let cardsHtml = '<div class="pf-card-view">';
    rows.forEach((r) => {
      const nome     = (r.cliente_nome || '').replace(/</g, '&lt;') || '—';
      const avatar   = `<div class="pf-avatar" style="background:${corAvatar(r.cliente_nome || '')}">${iniciaisDe(r.cliente_nome || '')}</div>`;
      const dt       = r.aprovado_em ? new Date(r.aprovado_em).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—';
      const canalCls = 'pf-canal-' + (r.aprovado_canal || 'manual');
      const dis      = r.pagamento_ok_para_liberar ? '' : ' disabled title="Pagamento 100% exigido pela empresa"';
      const { pct, pagoFmt, totalFmt, barCls, statusTxt, statusCls } = _renderPayProgress(r);
      const totalVal = r.total != null ? r.total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) : '—';
      const msgRaw   = (r.aceite_mensagem || '').replace(/</g, '&lt;');
      const msgBlock = msgRaw ? `<details class="pf-card-msg-details"><summary>Mensagem pública</summary><p>${msgRaw}</p></details>` : '';
      cardsHtml += `<div class="pf-card">
        <div class="pf-card-header">
          <input type="checkbox" class="pre-fila-cb pf-card-cb" value="${r.orcamento_id}"${dis}>
          <div class="pf-card-identity">
            ${avatar}
            <div class="pf-card-info">
              <div class="pf-card-nome" title="${nome}">${nome}</div>
              <a class="pf-card-orc-link" href="orcamento-view.html?id=${r.orcamento_id}" target="_blank" rel="noopener">${r.numero || '#' + r.orcamento_id}</a>
            </div>
          </div>
          <span class="pf-canal-badge ${canalCls}">${_canalLabel(r.aprovado_canal)}</span>
        </div>
        <div class="pf-card-section">
          <div class="pf-card-total-big">${totalVal}</div>
        </div>
        <div class="pf-card-pay-section">
          <div class="pf-pay-progress">
            <div class="pf-pay-label">
              <span class="pf-pay-label-text">${r.total ? pagoFmt + ' de ' + totalFmt + ' · ' + pct.toFixed(0) + '%' : '—'}</span>
              <span class="pf-pay-status ${statusCls}">${statusTxt}</span>
            </div>
            <div class="pf-pay-bar-wrap"><div class="pf-pay-bar ${barCls}" style="width:${pct}%"></div></div>
          </div>
        </div>
        ${msgBlock}
        <div class="pf-card-footer">
          <span class="pf-card-date">${dt}</span>
          <button type="button" class="pf-btn-liberar pf-btn-liberar-full" data-orc-id="${r.orcamento_id}" onclick="liberarUmPreAgendamento(${r.orcamento_id})"${dis}>Liberar</button>
        </div>
      </div>`;
    });
    cardsHtml += '</div>';

    host.innerHTML = tableHtml + cardsHtml;
    _bindPreFilaCheckboxes(host);
  } catch (e) {
    host.innerHTML = `<div style="color:#c5221f;padding:16px">Erro ao carregar fila: ${(e && e.message) || e}</div>`;
  }
}

async function liberarPreAgendamentoSelecionados() {
  // dedup: tabela e cards têm checkboxes com mesmo value — usar Set para evitar duplicatas
  const ids = [...new Set(Array.from(document.querySelectorAll('.pre-fila-cb:checked')).map((cb) => parseInt(cb.value, 10)))];
  if (!ids.length) {
    toast('Selecione ao menos um orçamento.');
    return;
  }
  const btnBatch = document.querySelector('#pf-batch-bar .btn-primary');
  if (btnBatch) setLoading(btnBatch, true);
  const obs = (document.getElementById('pre-fila-obs') || {}).value || '';
  try {
    const res = await apiRequest('POST', '/agendamentos/pre-agendamento/liberar', {
      orcamento_ids: ids,
      observacao: obs.trim() || null,
    });
    const ok = (res.resultados || []).filter((x) => x.ok).length;
    const bad = (res.resultados || []).filter((x) => !x.ok);
    toast(`Liberados: ${ok}. Falhas: ${bad.length}.`);
    if (bad.length) console.warn(bad);
    carregarPreAgendamentoFila();
    if (calendar) calendar.refetchEvents();
  } catch (e) {
    toast('Erro ao liberar: ' + ((e && e.message) || e));
    if (btnBatch) setLoading(btnBatch, false, 'Liberar selecionados');
  }
}

async function liberarUmPreAgendamento(orcamentoId) {
  const btn = document.querySelector(`.pf-btn-liberar[data-orc-id="${orcamentoId}"]`);
  if (btn) setLoading(btn, true);
  const obs = (document.getElementById('pre-fila-obs') || {}).value || '';
  try {
    const res = await apiRequest('POST', '/agendamentos/pre-agendamento/liberar', {
      orcamento_ids: [orcamentoId],
      observacao: obs.trim() || null,
    });
    const r = (res.resultados || [])[0];
    if (r && r.ok) toast('Opções de agendamento geradas.');
    else toast((r && r.detalhe) || 'Falha ao liberar.');
    carregarPreAgendamentoFila();
    if (calendar) calendar.refetchEvents();
  } catch (e) {
    toast('Erro: ' + ((e && e.message) || e));
    if (btn) setLoading(btn, false, 'Liberar');
  }
}
