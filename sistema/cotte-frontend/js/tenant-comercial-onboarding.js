(function() {
  'use strict';

  var STORAGE_KEY = 'cotte_comercial_onboarding_seen';
  var SESSION_KEY  = 'cotte_comercial_onboarding_hidden';

  var PASSOS = [
    {
      id: 'segmento',
      titulo: 'Criar um Segmento',
      descricao: 'Classifica seus leads por área de atuação (ex: Tecnologia, Varejo, Saúde)',
      tab: 'cadastros',
      check: function() { return segmentosCache.length > 0; }
    },
    {
      id: 'origem',
      titulo: 'Criar uma Origem',
      descricao: 'Indica de onde o lead veio (ex: Instagram, Indicação, Google)',
      tab: 'cadastros',
      check: function() { return origensCache.length > 0; }
    },
    {
      id: 'pipeline',
      titulo: 'Criar Etapas do Pipeline',
      descricao: 'As fases do seu processo de vendas: ex. Contato → Proposta → Fechado. Necessário para o Kanban.',
      tab: 'cadastros',
      check: function() { return pipelineStages.length > 0; }
    },
    {
      id: 'template',
      titulo: 'Criar um Template de Mensagem',
      descricao: 'Mensagens pré-escritas com variáveis como {nome} e {empresa}, para WhatsApp ou e-mail',
      tab: 'templates',
      check: function() { return templatesCache.length > 0; }
    },
    {
      id: 'lead',
      titulo: 'Adicionar seu primeiro Lead',
      descricao: 'Contatos que você quer converter em clientes',
      dica: '💡 Tem uma lista? Use a Importação em lote',
      tabDica: 'importacao',
      tab: 'leads',
      check: function() { return OnboardingComercial._temLead; }
    }
  ];

  var OnboardingComercial = {
    _temLead: false,

    init: async function() {
      if (sessionStorage.getItem(SESSION_KEY)) return;

      try {
        var res = await api.get('/tenant/comercial/leads?limit=1&per_page=1');
        this._temLead = (res && typeof res.total === 'number')
          ? res.total > 0
          : (Array.isArray(res) && res.length > 0);
      } catch(e) {
        this._temLead = false;
      }

      var status = this._getStatus();
      var todosCompletos = status.every(function(s) { return s.completo; });

      if (todosCompletos) {
        localStorage.removeItem(STORAGE_KEY);
        return;
      }

      localStorage.setItem(STORAGE_KEY, '1');
      this._render(status);
    },

    _getStatus: function() {
      return PASSOS.map(function(p) {
        return { passo: p, completo: p.check() };
      });
    },

    _render: function(status) {
      var container = document.getElementById('briefing-container');
      if (!container) return;

      var total      = status.length;
      var concluidos = status.filter(function(s) { return s.completo; }).length;
      var pct        = Math.round((concluidos / total) * 100);
      var proximoIdx = status.findIndex(function(s) { return !s.completo; });

      var passosHTML = status.map(function(s, i) {
        var p = s.passo;

        if (s.completo) {
          return '<div class="ob-passo ob-passo--ok">' +
            '<div class="ob-num ob-num--ok">✓</div>' +
            '<div class="ob-info">' +
              '<div class="ob-titulo ob-titulo--ok">' + p.titulo + '</div>' +
              '<div class="ob-desc ob-desc--ok">Concluído · ' + p.descricao + '</div>' +
            '</div>' +
          '</div>';
        }

        var isProximo = (i === proximoIdx);
        var dicaHTML  = '';
        if (p.dica) {
          dicaHTML = '<button type="button" class="ob-dica"' +
            ' onclick="OnboardingComercial._irPara(\'' + p.tabDica + '\')">' +
            p.dica + '</button>';
        }

        return '<div class="ob-passo ' + (isProximo ? 'ob-passo--ativo' : 'ob-passo--pendente') + '">' +
          '<div class="ob-num ' + (isProximo ? 'ob-num--ativo' : 'ob-num--pendente') + '">' + (i + 1) + '</div>' +
          '<div class="ob-info">' +
            '<div class="ob-titulo">' + p.titulo + '</div>' +
            '<div class="ob-desc">' + p.descricao + '</div>' +
            dicaHTML +
          '</div>' +
          '<button type="button" class="ob-btn' + (isProximo ? ' ob-btn--ativo' : '') + '"' +
            ' onclick="OnboardingComercial._irPara(\'' + p.tab + '\')">' +
            (isProximo ? 'Ir →' : 'Ir') +
          '</button>' +
        '</div>';
      }).join('');

      var html =
        '<div class="ob-bloco" id="ob-bloco">' +
          '<div class="ob-header">' +
            '<div>' +
              '<div class="ob-titulo-principal">🚀 Configure o Comercial</div>' +
              '<div class="ob-subtitulo">Complete os passos abaixo para começar a usar o CRM</div>' +
            '</div>' +
            '<div>' +
              '<div class="ob-progresso-label">Progresso</div>' +
              '<div class="ob-progresso-valor">' + concluidos +
                '<span class="ob-progresso-total">/' + total + '</span>' +
              '</div>' +
            '</div>' +
          '</div>' +
          '<div class="ob-barra-wrap"><div class="ob-barra" style="width:' + pct + '%"></div></div>' +
          '<div class="ob-passos">' + passosHTML + '</div>' +
          '<div class="ob-footer">' +
            '<span class="ob-footer-hint">Este guia some automaticamente quando tudo estiver pronto</span>' +
            '<button type="button" class="ob-ocultar" onclick="OnboardingComercial._ocultar()">Ocultar por agora</button>' +
          '</div>' +
        '</div>';

      container.insertAdjacentHTML('afterbegin', html);
    },

    _irPara: function(tab) {
      switchTab(tab);
    },

    _ocultar: function() {
      sessionStorage.setItem(SESSION_KEY, '1');
      var bloco = document.getElementById('ob-bloco');
      if (bloco) bloco.remove();
    }
  };

  window.OnboardingComercial = OnboardingComercial;
})();
