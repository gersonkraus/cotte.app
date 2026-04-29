(function () {
  'use strict';

  const MODULE_LABEL = '[AssistenteInsights]';
  const DEFAULT_LIMIT = 5;

  function warn(message, err) {
    if (typeof console !== 'undefined' && console.warn) {
      console.warn(MODULE_LABEL, message, err || '');
    }
  }

  function getHttpClient() {
    const client = window.ApiService || window.api;
    if (!client || typeof client.get !== 'function' || typeof client.post !== 'function') return null;
    return client;
  }

  function escapeHtml(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function normalizeInsight(raw) {
    if (!raw || typeof raw !== 'object') return null;
    const title = String(raw.titulo || '').trim();
    const description = String(raw.descricao || '').trim();
    const action = String(raw.acao || '').trim();
    if (!title && !description && !action) return null;
    return {
      id: raw.id != null ? String(raw.id) : '',
      prioridade: String(raw.prioridade || 'media').toLowerCase(),
      dominio: String(raw.dominio || 'gestao').toLowerCase(),
      titulo: title || 'Sugestão operacional',
      descricao: description,
      acao: action,
      contexto: raw.contexto || null,
      expira_em: raw.expira_em || null,
    };
  }

  function normalizeInsights(items) {
    if (!Array.isArray(items)) return [];
    const seen = new Set();
    return items
      .map(normalizeInsight)
      .filter(Boolean)
      .filter((item) => {
        const key = item.id || `${item.titulo}:${item.acao}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });
  }

  function getInsightsFromResponse(response) {
    if (!response || typeof response !== 'object') return [];
    const dados = response.dados && typeof response.dados === 'object' ? response.dados : null;
    if (dados && Array.isArray(dados.insights)) return normalizeInsights(dados.insights);
    if (Array.isArray(response.insights)) return normalizeInsights(response.insights);
    return [];
  }

  function getInsightsFromApiPayload(payload) {
    if (Array.isArray(payload)) return normalizeInsights(payload);
    if (Array.isArray(payload?.insights)) return normalizeInsights(payload.insights);
    if (Array.isArray(payload?.data?.insights)) return normalizeInsights(payload.data.insights);
    if (Array.isArray(payload?.dados?.insights)) return normalizeInsights(payload.dados.insights);
    return [];
  }

  function getPriorityLabel(priority) {
    const labels = { alta: 'Alta', media: 'Média', baixa: 'Baixa' };
    return labels[priority] || 'Média';
  }

  function getDomainLabel(domain) {
    const labels = {
      financeiro: 'Financeiro',
      clientes: 'Clientes',
      orcamentos: 'Orçamentos',
      crm: 'CRM',
      agenda: 'Agenda',
      gestao: 'Gestão',
    };
    return labels[domain] || domain.replace(/_/g, ' ');
  }

  function getSessionId() {
    try {
      if (typeof window.getAssistenteSessaoId === 'function') return window.getAssistenteSessaoId() || null;
    } catch (_) { /* ignore */ }
    return window.assistenteSessaoId || null;
  }

  async function sendFeedback(insight, action) {
    const client = getHttpClient();
    const sessaoId = getSessionId();
    if (!client || !insight || !insight.id || !sessaoId) {
      if (!sessaoId) warn('sessao_id ausente, feedback não enviado.', null);
      return;
    }
    try {
      await client.post('/ai/insights/feedback', {
        insight_id: insight.id,
        acao: action,
        sessao_id: sessaoId,
      }, { bypassAutoLogout: true });
    } catch (err) {
      warn('Falha ao enviar feedback de insight.', err);
    }
  }

  function setInputValue(text) {
    const input = document.getElementById('messageInput');
    if (!input) return false;
    input.value = text;
    if (typeof window.resizeMessageInput === 'function') window.resizeMessageInput();
    input.focus();
    return true;
  }

  function applyInsightAction(insight) {
    const action = String(insight?.acao || '').trim();
    if (!action) return;
    if (setInputValue(action)) {
      sendFeedback(insight, 'executou');
    }
  }

  function buildInsightCard(insight, index) {
    const hasAction = !!insight.acao;
    const priority = escapeHtml(getPriorityLabel(insight.prioridade));
    const domain = escapeHtml(getDomainLabel(insight.dominio));
    const actionLabel = window.innerWidth <= 640 ? 'Usar' : 'Usar ação';
    return `
      <article class="assistente-insight-card" data-insight-index="${index}">
        <div class="assistente-insight-card__top">
          <span class="assistente-insight-chip assistente-insight-chip--${escapeHtml(insight.prioridade)}">${priority}</span>
          <span class="assistente-insight-domain">${domain}</span>
          <button type="button" class="assistente-insight-dismiss" data-insight-dismiss="${index}" aria-label="Dispensar sugestão">Dispensar</button>
        </div>
        <h3 class="assistente-insight-title">${escapeHtml(insight.titulo)}</h3>
        ${insight.descricao ? `<p class="assistente-insight-desc">${escapeHtml(insight.descricao)}</p>` : ''}
        ${hasAction ? `<button type="button" class="assistente-insight-action" data-insight-action="${index}">${actionLabel}</button>` : ''}
      </article>
    `;
  }

  function bindInsightEvents(root, insights) {
    root.querySelectorAll('[data-insight-action]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const idx = Number(btn.getAttribute('data-insight-action'));
        applyInsightAction(insights[idx]);
      });
    });
    root.querySelectorAll('[data-insight-dismiss]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const idx = Number(btn.getAttribute('data-insight-dismiss'));
        const card = btn.closest ? btn.closest('.assistente-insight-card') : null;
        if (card) card.remove();
        sendFeedback(insights[idx], 'dispensou');
      });
    });
  }

  function createInsightsBlock(insights, options) {
    const block = document.createElement('section');
    block.className = `assistente-insights assistente-insights--${options.placement || 'response'}`;
    block.setAttribute('aria-label', 'Sugestões proativas do assistente');
    block.innerHTML = `
      <div class="assistente-insights__header">
        <span class="assistente-insights__eyebrow">Sugestões proativas</span>
        <span class="assistente-insights__count">${insights.length}</span>
      </div>
      <div class="assistente-insights__grid">
        ${insights.map(buildInsightCard).join('')}
      </div>
    `;
    bindInsightEvents(block, insights);
    return block;
  }

  function getDefaultTarget(options) {
    if (options?.target) return options.target;
    if (options?.messageEl) return options.messageEl.querySelector('.message-bubble') || options.messageEl;
    if (options?.placement === 'welcome') {
      return document.querySelector('#welcomeState .welcome-msg') || document.getElementById('chatMessages');
    }
    return document.getElementById('chatMessages');
  }

  function render(items, options = {}) {
    try {
      const insights = normalizeInsights(items).slice(0, Number(options.limit || DEFAULT_LIMIT));
      const target = getDefaultTarget(options);
      if (!target || !insights.length) return null;
      const existing = options.replace !== false ? target.querySelector?.('.assistente-insights') : null;
      if (existing) existing.remove();
      const block = createInsightsBlock(insights, options);
      target.appendChild(block);
      if (typeof window.scrollChatToBottom === 'function' && options.placement !== 'welcome') {
        window.scrollChatToBottom({ behavior: 'auto' });
      }
      return block;
    } catch (err) {
      warn('Falha ao renderizar insights.', err);
      return null;
    }
  }

  function renderFromResponse(response, options = {}) {
    const insights = getInsightsFromResponse(response);
    if (!insights.length) return null;
    return render(insights, { ...options, placement: options.placement || 'response' });
  }

  async function fetchAndRender(options = {}) {
    const client = getHttpClient();
    if (!client) return null;
    try {
      const limit = Number(options.limit || DEFAULT_LIMIT);
      const payload = await client.get(`/ai/insights?limit=${encodeURIComponent(limit)}`, { bypassAutoLogout: true });
      const insights = getInsightsFromApiPayload(payload);
      return render(insights, { ...options, limit, placement: options.placement || 'welcome' });
    } catch (err) {
      warn('Falha ao buscar insights.', err);
      return null;
    }
  }

  function init(options = {}) {
    return fetchAndRender({ limit: DEFAULT_LIMIT, placement: 'welcome', ...options });
  }

  window.AssistenteInsights = {
    init,
    render,
    renderFromResponse,
    sendFeedback,
    applyInsightAction,
    _normalizeInsights: normalizeInsights,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => init());
  } else {
    setTimeout(() => init(), 0);
  }
})();
