/**
 * ux-improvements.js - Melhorias de UX centralizadas
 * Versão corrigida 06/04/2026 - Classic Vanilla JS (sem export)
 */

var UXImprovements = (function() {
  function initGlobalListeners() {
      window.addEventListener('api-error', function(e) {
          showError(e.detail);
      });
  }

  function setButtonLoading(btn, isLoading) {
      if (!btn) return;
      var originalText = btn.getAttribute('data-original-text') || btn.innerHTML;

      if (isLoading) {
          btn.setAttribute('data-original-text', originalText);
          btn.disabled = true;
          btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Carregando...';
      } else {
          btn.disabled = false;
          btn.innerHTML = originalText;
      }
  }

  function showToast(message, type = 'info') {
      var container = document.getElementById('toast-container');
      if (!container) {
          container = document.createElement('div');
          container.id = 'toast-container';
          container.style.cssText = 'position:fixed;top:20px;right:20px;z-index:9999;';
          document.body.appendChild(container);
      }

      var toast = document.createElement('div');
      toast.className = 'toast align-items-center text-white bg-' + type + ' border-0 show';
      toast.innerHTML = `
          <div class="d-flex">
              <div class="toast-body">${message}</div>
              <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
          </div>`;
      container.appendChild(toast);

      setTimeout(function() {
          if (toast) toast.remove();
      }, 4000);
  }

  function showSuccess(message) { showToast(message, 'success'); }
  function showError(message) { showToast(message, 'danger'); }

  function pollUntilReady(url, maxSeconds = 30) {
      return new Promise(function(resolve, reject) {
          var start = Date.now();
          var interval = setInterval(function() {
              if (Date.now() - start > maxSeconds * 1000) {
                  clearInterval(interval);
                  reject(new Error('Tempo esgotado ao gerar PDF'));
                  return;
              }
              if (typeof ApiService !== 'undefined') {
                ApiService.get(url)
                    .then(function(res) {
                        if (res.data && res.data.pdf_url) {
                            clearInterval(interval);
                            resolve(res.data.pdf_url);
                        }
                    })
                    .catch(function() {});
              }
          }, 800);
      });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 1. CARDS MOBILE PARA TABELAS
  // ══════════════════════════════════════════════════════════════════════════

  function renderizarCardsMobile(orcamentos) {
    const container = document.querySelector('.mobile-cards-list');
    if (!container) return;

    if (!orcamentos.length) {
      container.innerHTML = '<div class="empty-state"><div class="icon">📋</div><div class="title">Nenhum orçamento encontrado</div></div>';
      return;
    }

    container.innerHTML = orcamentos.map(o => {
      const nome = o.cliente?.nome || '—';
      const iniciais = nome.split(' ').map(w => w[0]).join('').substring(0, 2).toUpperCase();
      const cor = typeof window.corAvatar === 'function' ? window.corAvatar(nome) : 'linear-gradient(135deg,#06b6d4,#3b82f6)';
      const numEsc = (o.numero || '').replace(/'/g, "\\'");
      const stColors = { rascunho: '#94a3b8', enviado: '#3b82f6', aprovado: '#16a34a', recusado: '#ef4444', expirado: '#f59e0b' };
      const stColor = stColors[o.status] || 'var(--muted)';
      const dataFmt = o.criado_em ? new Date(o.criado_em).toLocaleDateString('pt-BR') : '—';

      return '<div class="mobile-card" data-id="' + o.id + '" onclick="abrirDetalhesOrcamento(' + o.id + ')" style="cursor:pointer">'
        + '<div class="mobile-card-header">'
        + '<div class="mobile-card-client">'
        + '<div class="mobile-card-avatar" style="background:' + cor + '">' + iniciais + '</div>'
        + '<div class="mobile-card-info">'
        + '<div class="mobile-card-name">' + (typeof escapeHtml === 'function' ? escapeHtml(nome) : nome) + '</div>'
        + '<div class="mobile-card-numero">' + (typeof escapeHtml === 'function' ? escapeHtml(o.numero || '') : (o.numero || '')) + '</div>'
        + '</div></div>'
        + '<button class="mobile-card-actions-btn" onclick="abrirDropdownAcoes(event,' + o.id + ',\'' + numEsc + '\',\'' + o.status + '\')">⋯</button>'
        + '</div>'
        + '<div class="mobile-card-body">'
        + '<div class="mobile-card-valor">' + (typeof formatarMoeda === 'function' ? formatarMoeda(o.total || 0) : 'R$ ' + (o.total || 0).toFixed(2)) + '</div>'
        + '<div class="mobile-card-meta">'
        + '<span class="status-badge" style="background:' + stColor + '20;color:' + stColor + '">' + (typeof escapeHtml === 'function' ? escapeHtml(o.status || '') : (o.status || '')) + '</span>'
        + '<span class="mobile-card-data">' + dataFmt + '</span>'
        + '</div></div></div>';
    }).join('');
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 2. MENU DROPDOWN DE AÇÕES MOBILE
  // ══════════════════════════════════════════════════════════════════════════

  let _dropdownAberto = null;

  function abrirDropdownAcoes(event, id, numero, status) {
    event.stopPropagation();
    fecharDropdownAcoes();

    const rect = event.currentTarget.getBoundingClientRect();
    const podeAprovar = ['rascunho', 'enviado'].includes(status);

    const dropdown = document.createElement('div');
    dropdown.className = 'actions-dropdown open';
    dropdown.id = 'actions-dropdown-mobile';

    let top = rect.bottom + 6;
    let left = Math.max(8, rect.left - 160);
    if (top + 300 > window.innerHeight) {
      top = rect.top - 6;
      dropdown.style.transform = 'translateY(-100%)';
    }
    dropdown.style.top = top + 'px';
    dropdown.style.left = left + 'px';

    dropdown.innerHTML = '<button class="actions-dropdown-item" onclick="fecharDropdownAcoes();abrirTimeline(' + id + ',\'' + numero + '\')"><span class="action-icon">🕐</span> Linha do tempo</button>'
      + '<button class="actions-dropdown-item" onclick="fecharDropdownAcoes();abrirDetalhesOrcamento(' + id + ')"><span class="action-icon">📋</span> Detalhes</button>'
      + '<button class="actions-dropdown-item" onclick="fecharDropdownAcoes();window.open(\'orcamento-view.html?id=' + id + '\',\'_blank\')"><span class="action-icon">📄</span> Ver PDF</button>'
      + '<button class="actions-dropdown-item" onclick="fecharDropdownAcoes();abrirModalEditarOrcamento(' + id + ')"><span class="action-icon">✏️</span> Editar</button>'
      + '<div class="actions-dropdown-divider"></div>'
      + '<button class="actions-dropdown-item" onclick="fecharDropdownAcoes();enviarWhatsapp(' + id + ')"><span class="action-icon">📲</span> Enviar WhatsApp</button>'
      + '<button class="actions-dropdown-item" onclick="fecharDropdownAcoes();enviarEmail(' + id + ')"><span class="action-icon">📧</span> Enviar e-mail</button>'
      + (podeAprovar ? '<div class="actions-dropdown-divider"></div><button class="actions-dropdown-item" onclick="fecharDropdownAcoes();aprovarOrcamento(' + id + ',\'' + numero + '\')"><span class="action-icon">✅</span> Aprovar</button>' : '');

    document.body.appendChild(dropdown);
    _dropdownAberto = dropdown;
    setTimeout(function() { document.addEventListener('click', fecharDropdownAcoes); }, 50);
  }

  function fecharDropdownAcoes() {
    var dd = document.getElementById('actions-dropdown-mobile');
    if (dd) dd.remove();
    _dropdownAberto = null;
    document.removeEventListener('click', fecharDropdownAcoes);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 3. CONTAGEM NOS FILTER-CHIPS
  // ══════════════════════════════════════════════════════════════════════════

  function atualizarContagemFiltros(orcamentos) {
    var contagens = { '': orcamentos.length, rascunho: 0, enviado: 0, aprovado: 0, recusado: 0, expirado: 0, vencendo: 0 };
    var agora = new Date();
    var em3dias = new Date(agora.getTime() + 3 * 86400000);

    orcamentos.forEach(function(o) {
      if (contagens[o.status] !== undefined) contagens[o.status]++;
      if (o.status === 'enviado' && o.validade_ate) {
        var venc = new Date(o.validade_ate);
        if (venc >= agora && venc <= em3dias) contagens['vencendo']++;
      }
    });

    document.querySelectorAll('.table-filters .filter-chip').forEach(function(chip) {
      var onclick = chip.getAttribute('onclick') || '';
      var match = onclick.match(/setStatus\(this,\s*'([^']*)'\)/);
      if (!match) return;
      var status = match[1];
      var existing = chip.querySelector('.filter-chip-count');
      if (existing) existing.remove();
      if (contagens[status] !== undefined) {
        var badge = document.createElement('span');
        badge.className = 'filter-chip-count';
        badge.textContent = contagens[status];
        chip.appendChild(badge);
      }
    });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 4. ESTADOS DE ERRO DESCRITIVOS
  // ══════════════════════════════════════════════════════════════════════════

  function mostrarEstadoErro(container, tipo, mensagemCustom) {
    if (!container) return;
    var configs = {
      conexao: { icon: '📡', title: 'Sem conexão com o servidor', desc: 'Não foi possível conectar ao servidor COTTE. Verifique sua conexão com a internet.', sugestao: 'O servidor pode estar em manutenção. Tente novamente em alguns minutos.', actions: '<button class="btn btn-primary" onclick="location.reload()">🔄 Tentar novamente</button>' },
      sessao: { icon: '🔐', title: 'Sessão expirada', desc: 'Sua sessão expirou por segurança. Faça login novamente para continuar.', sugestao: 'Isso acontece após um período de inatividade.', actions: '<button class="btn btn-primary" onclick="window.location.href=\'login.html\'">🔑 Fazer login</button>' },
      limite: { icon: '📊', title: 'Limite do plano atingido', desc: 'Você atingiu o limite de orçamentos do seu plano atual.', sugestao: 'Faça upgrade para continuar criando orçamentos sem limites.', actions: '<button class="btn btn-primary" onclick="window.location.href=\'configuracoes.html#plano\'">⬆️ Fazer upgrade</button>' },
      generico: { icon: '⚠️', title: 'Algo deu errado', desc: mensagemCustom || 'Ocorreu um erro inesperado. Tente novamente.', sugestao: 'Se o problema persistir, entre em contato com o suporte.', actions: '<button class="btn btn-ghost" onclick="location.reload()">🔄 Recarregar</button>' }
    };
    var cfg = configs[tipo] || configs.generico;
    container.innerHTML = '<div class="error-state"><div class="error-state-icon">' + cfg.icon + '</div><div class="error-state-title">' + cfg.title + '</div><div class="error-state-desc">' + cfg.desc + '</div><div class="error-state-actions">' + cfg.actions + '</div><div class="error-state-sugestao">' + cfg.sugestao + '</div></div>';
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 6. PAGINAÇÃO MELHORADA
  // ══════════════════════════════════════════════════════════════════════════

  function renderizarPaginacao(container, opts) {
    if (!container) return;
    var pag = opts.paginaAtual, total = opts.totalPaginas, itens = opts.totalItens, porPg = opts.porPagina;
    var inicio = ((pag - 1) * porPg) + 1;
    var fim = Math.min(pag * porPg, itens);
    var botoes = '';
    botoes += '<button class="pagination-btn" ' + (pag <= 1 ? 'disabled' : '') + ' onclick="irParaPagina(' + (pag - 1) + ')">‹</button>';

    var maxB = 5, iniR = Math.max(1, pag - Math.floor(maxB / 2)), fimR = Math.min(total, iniR + maxB - 1);
    if (fimR - iniR < maxB - 1) iniR = Math.max(1, fimR - maxB + 1);

    if (iniR > 1) { botoes += '<button class="pagination-btn" onclick="irParaPagina(1)">1</button>'; if (iniR > 2) botoes += '<span class="pagination-ellipsis">…</span>'; }
    for (var i = iniR; i <= fimR; i++) botoes += '<button class="pagination-btn ' + (i === pag ? 'active' : '') + '" onclick="irParaPagina(' + i + ')">' + i + '</button>';
    if (fimR < total) { if (fimR < total - 1) botoes += '<span class="pagination-ellipsis">…</span>'; botoes += '<button class="pagination-btn" onclick="irParaPagina(' + total + ')">' + total + '</button>'; }
    botoes += '<button class="pagination-btn" ' + (pag >= total ? 'disabled' : '') + ' onclick="irParaPagina(' + (pag + 1) + ')">›</button>';

    container.innerHTML = '<div class="pagination-info">Mostrando ' + inicio + '–' + fim + ' de ' + itens + '</div><div class="pagination-controls">' + botoes + '</div><div class="pagination-per-page"><span>Por página:</span><select onchange="alterarPorPagina(parseInt(this.value))"><option value="10" ' + (porPg === 10 ? 'selected' : '') + '>10</option><option value="15" ' + (porPg === 15 ? 'selected' : '') + '>15</option><option value="25" ' + (porPg === 25 ? 'selected' : '') + '>25</option><option value="50" ' + (porPg === 50 ? 'selected' : '') + '>50</option></select></div>';
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 7. ALERTAS INTRUSIVOS E LOADING OVERLAY
  // ══════════════════════════════════════════════════════════════════════════

  function mostrarLoading(mensagem = 'Processando...') {
    fecharLoading();
    const overlay = document.createElement('div');
    overlay.id = 'cotte-loading-overlay';
    overlay.style = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);z-index:9999;display:flex;flex-direction:column;align-items:center;justify-content:center;color:white;backdrop-filter:blur(4px);transition:opacity 0.3s';
    overlay.innerHTML = `
      <div class="loading-spinner" style="width:50px;height:50px;border:4px solid rgba(255,255,255,0.1);border-top-color:var(--accent);border-radius:50%;animation:spin 1s linear infinite;margin-bottom:20px"></div>
      <div style="font-weight:600;font-size:16px;letter-spacing:0.05em">${mensagem}</div>
      <style>@keyframes spin { to { transform: rotate(360deg); } }</style>
    `;
    document.body.appendChild(overlay);
  }

  function fecharLoading() {
    const el = document.getElementById('cotte-loading-overlay');
    if (el) el.remove();
  }

  /**
   * Mostra um alerta intrusivo com Double Opt-in
   */
  function confirmarAcaoCritica(titulo, mensagem, acaoLabel = 'Confirmar', corBtn = 'var(--accent)') {
    return new Promise((resolve) => {
      const modalId = 'modal-confirmacao-critica';
      const existing = document.getElementById(modalId);
      if (existing) existing.remove();

      const modal = document.createElement('div');
      modal.id = modalId;
      modal.className = 'modal-overlay open';
      modal.style = 'z-index:10000';
      modal.innerHTML = `
        <div class="modal" style="max-width:400px;text-align:center;padding:30px">
          <div style="font-size:40px;margin-bottom:15px">⚠️</div>
          <h3 style="margin-bottom:10px;font-size:20px">${titulo}</h3>
          <p style="color:var(--muted);font-size:14px;margin-bottom:25px;line-height:1.5">${mensagem}</p>

          <div style="background:var(--surface2);padding:15px;border-radius:10px;margin-bottom:25px;border:1px solid var(--border)">
            <label style="display:flex;align-items:center;gap:10px;cursor:pointer;user-select:none;text-align:left">
              <input type="checkbox" id="confirm-check" style="width:18px;height:18px;accent-color:${corBtn}">
              <span style="font-size:13px;font-weight:500">Estou ciente e desejo prosseguir</span>
            </label>
          </div>

          <div style="display:flex;gap:12px">
            <button class="btn btn-ghost" style="flex:1" id="confirm-cancel">Cancelar</button>
            <button class="btn" style="flex:1;background:${corBtn};color:white;opacity:0.5;cursor:not-allowed" id="confirm-proceed" disabled>${acaoLabel}</button>
          </div>
        </div>
      `;

      document.body.appendChild(modal);

      const check = modal.querySelector('#confirm-check');
      const btn = modal.querySelector('#confirm-proceed');
      const cancel = modal.querySelector('#confirm-cancel');

      check.onchange = () => {
        btn.disabled = !check.checked;
        btn.style.opacity = check.checked ? '1' : '0.5';
        btn.style.cursor = check.checked ? 'pointer' : 'not-allowed';
      };

      btn.onclick = () => {
        modal.remove();
        resolve(true);
      };

      cancel.onclick = () => {
        modal.remove();
        resolve(false);
      };
    });
  }

  return {
      init: function() {
          initGlobalListeners();
          console.log('%c✅ UX Improvements carregado com sucesso', 'color: #00ff88; font-weight: bold');
      },
      setButtonLoading: setButtonLoading,
      showSuccess: showSuccess,
      showError: showError,
      pollUntilReady: pollUntilReady,
      renderizarCardsMobile: renderizarCardsMobile,
      abrirDropdownAcoes: abrirDropdownAcoes,
      fecharDropdownAcoes: fecharDropdownAcoes,
      atualizarContagemFiltros: atualizarContagemFiltros,
      mostrarEstadoErro: mostrarEstadoErro,
      renderizarPaginacao: renderizarPaginacao,
      mostrarLoading: mostrarLoading,
      fecharLoading: fecharLoading,
      confirmarAcaoCritica: confirmarAcaoCritica
  };
})();

// Torna global para compatibilidade com orcamentos.html e outros
window.UXImprovements = UXImprovements;
window.renderizarCardsMobile = UXImprovements.renderizarCardsMobile;
window.abrirDropdownAcoes = UXImprovements.abrirDropdownAcoes;
window.fecharDropdownAcoes = UXImprovements.fecharDropdownAcoes;
window.atualizarContagemFiltros = UXImprovements.atualizarContagemFiltros;
window.mostrarEstadoErro = UXImprovements.mostrarEstadoErro;
window.renderizarPaginacao = UXImprovements.renderizarPaginacao;
window.mostrarLoading = UXImprovements.mostrarLoading;
window.fecharLoading = UXImprovements.fecharLoading;
window.confirmarAcaoCritica = UXImprovements.confirmarAcaoCritica;
window.setButtonLoading = UXImprovements.setButtonLoading;
window.showSuccess = UXImprovements.showSuccess;
window.showError = UXImprovements.showError;
window.inicializarStickyFooterModal = function() { /* Vazio conforme backup */ };

// Inicializa automaticamente
UXImprovements.init();
