// ═══════════════════════════════════════════════════════════════════════════════
// COTTE — Comercial Core
// State global, utilitários compartilhados, inicialização e navegação por tabs
// ═══════════════════════════════════════════════════════════════════════════════

// ═══════════════════════════════════════════════════════════════════════════════
// STATE (acessível por todos os módulos)
// ═══════════════════════════════════════════════════════════════════════════════
let leadAtualId = null;
let leadsPage = 1;
let leadsOrderBy = 'criado_em';
let leadsOrderDir = 'desc';
/** Quando definido, GET /comercial/leads inclui origem_lead_id (ex.: clique em Empresas em trial). */
let leadsFilterOrigemId = null;
/** Filtro alinhado ao bloco "O que fazer hoje" / KPI Follow-ups (próximo contato vencido ou para agora). */
let leadsFilterFollowUpHoje = false;
/** Filtro para leads vinculados a empresas em trial ativo. */
let leadsFilterEmpresaTrial = false;
let _fromDashboard = false;
let debounceTimer = null;
let segmentosCache = [];
let origensCache = [];
let templatesCache = [];
let importacaoLoteAtual = null;
let kanbanShowClosed = false;

let pipelineStages = [];
let STATUS_LABELS = {novo:'Novo',contato_iniciado:'Contato',proposta_enviada:'Proposta',negociacao:'Negociação',fechado_ganho:'Ganho',fechado_perdido:'Perdido'};
let STATUS_COLORS = {novo:'#94a3b8',contato_iniciado:'#3b82f6',proposta_enviada:'#f59e0b',negociacao:'#06b6d4',fechado_ganho:'#10b981',fechado_perdido:'#ef4444'};

const TIPO_TPL_LABELS = {mensagem_inicial:'Msg Inicial',followup:'Follow-up',proposta_comercial:'Proposta',email_comercial:'E-mail'};
const CANAL_TPL_LABELS = {whatsapp:'WhatsApp',email:'E-mail',ambos:'Ambos'};

// ═══════════════════════════════════════════════════════════════════════════════
// UTILS (acessível por todos os módulos)
// ═══════════════════════════════════════════════════════════════════════════════
function fecharModal(id) {
  var overlay = document.getElementById(id);
  if (!overlay) return;
  var modal = overlay.querySelector('.modal');
  if (modal && window.innerWidth <= 640) {
    modal.classList.add('closing');
    setTimeout(function() {
      overlay.classList.remove('open');
      modal.classList.remove('closing');
    }, 250);
  } else {
    overlay.classList.remove('open');
  }
}

function esc(s) {
  if (!s) return '';
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function fmtMoeda(v) {
  return new Intl.NumberFormat('pt-BR', {minimumFractionDigits:2, maximumFractionDigits:2}).format(v);
}

function fmtData(d) {
  if (!d) return '\u2014';
  return new Date(d).toLocaleDateString('pt-BR');
}

function fmtDataHora(d) {
  if (!d) return '\u2014';
  return new Date(d).toLocaleString('pt-BR', {day:'2-digit', month:'2-digit', year:'2-digit', hour:'2-digit', minute:'2-digit'});
}

function showToast(msg, type) {
  type = type || 'success';
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast ' + type + ' show';
  t.setAttribute('role', 'alert');
  setTimeout(function() { t.classList.remove('show'); }, 3500);
}

/** Desabilita botão durante operação assíncrona */
function withBtnLoading(btn, fn) {
  if (!btn) return fn();
  var originalText = btn.textContent;
  btn.disabled = true;
  btn.classList.add('loading');
  btn.textContent = 'Processando...';
  var result = fn();
  if (result && typeof result.finally === 'function') {
    result.finally(function() {
      btn.disabled = false;
      btn.classList.remove('loading');
      btn.textContent = originalText;
    });
  } else {
    btn.disabled = false;
    btn.classList.remove('loading');
    btn.textContent = originalText;
  }
  return result;
}

function reconstruirStatusMaps() {
  STATUS_LABELS = {};
  STATUS_COLORS = {};
  pipelineStages.forEach(function(s) {
    STATUS_LABELS[s.slug] = s.label;
    STATUS_COLORS[s.slug] = s.cor;
  });
  var sel = document.getElementById('leads-filter-status');
  if (sel) {
    var val = sel.value;
    sel.innerHTML = '<option value="">Todos os status</option>' +
      pipelineStages.map(function(s) { return '<option value="' + esc(s.slug) + '">' + esc(s.label) + '</option>'; }).join('');
    sel.value = val;
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════════════════════════

function bindTabEvents() {
  document.querySelectorAll('.admin-tab[data-tab]').forEach(function(tab) {
    tab.addEventListener('click', function() {
      switchTab(this.dataset.tab);
    });
  });
}

function initBottomSheets() {
  document.querySelectorAll('.modal').forEach(function(modal) {
    if (!modal.querySelector('.modal-drag-handle')) {
      var handle = document.createElement('div');
      handle.className = 'modal-drag-handle';
      var startY = 0;
      handle.addEventListener('touchstart', function(e) {
        startY = e.touches[0].clientY;
      }, {passive: true});
      handle.addEventListener('touchend', function(e) {
        var endY = e.changedTouches[0].clientY;
        if (endY - startY > 30) {
          var overlay = modal.closest('.modal-overlay');
          if (overlay && overlay.id) fecharModal(overlay.id);
        }
      });
      handle.addEventListener('click', function() {
        var overlay = modal.closest('.modal-overlay');
        if (overlay && overlay.id) fecharModal(overlay.id);
      });
      modal.insertBefore(handle, modal.firstChild);
    }
  });
}

document.addEventListener('DOMContentLoaded', async function() {
  inicializarLayout('comercial');
  bindTabEvents();
  initBottomSheets();
  await carregarCadastrosCache();
  carregarDashboard();
});

async function carregarCadastrosCache() {
  try {
    var results = await Promise.all([
      api.get('/comercial/segmentos?ativo=true'),
      api.get('/comercial/origens?ativo=true'),
      api.get('/comercial/templates?ativo=true'),
      api.get('/comercial/pipeline-stages'),
    ]);
    segmentosCache = results[0] || [];
    origensCache = results[1] || [];
    templatesCache = results[2] || [];
    pipelineStages = results[3] || [];
    reconstruirStatusMaps();
  } catch(e) { console.warn('Erro ao carregar cadastros', e); }
}

// ═══════════════════════════════════════════════════════════════════════════════
// TABS
// ═══════════════════════════════════════════════════════════════════════════════
function switchTab(tab, skipLoad) {
  document.querySelectorAll('.admin-tab').forEach(function(t) {
    t.classList.toggle('active', t.dataset.tab === tab);
  });

  document.querySelectorAll('.tab-panel').forEach(function(p) {
    var active = p.id === 'tab-' + tab;
    p.classList.toggle('active', active);
    // Limpar inline style para deixar CSS (display:none/block) controlar
    p.style.display = '';
  });

  if (skipLoad) return;

  if (tab === 'dashboard') carregarDashboard();
  else if (tab === 'pipeline') carregarPipeline();
  else if (tab === 'leads') {
    if (!_fromDashboard) { leadsFilterEmpresaTrial = false; leadsFilterFollowUpHoje = false; leadsFilterOrigemId = null; }
    _fromDashboard = false;
    carregarLeadsTabela();
  }
  else if (tab === 'templates') carregarTemplates();
  else if (tab === 'propostas-publicas') carregarPropostasPublicas();
  else if (tab === 'campanhas') carregarCampanhas();
  else if (tab === 'lembretes') carregarLembretes();
  else if (tab === 'cadastros') { carregarSegmentos(); carregarOrigens(); carregarPipelineStagesUI(); }
  else if (tab === 'config') carregarConfig();
  else if (tab === 'importacao') carregarImportacao();
}
