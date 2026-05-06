(function() {
  'use strict';

  var STORAGE_KEY = 'cotte_comercial_onboarding_seen';
  var SESSION_KEY  = 'cotte_comercial_onboarding_hidden';

  var PASSOS = [
    {
      id: 'lead',
      titulo: 'Cadastrar o primeiro contato',
      descricao: 'Adicione pelo menos um contato para começar o trabalho comercial.',
      tab: 'leads',
      check: function() { return OnboardingComercial._temLead; }
    },
    {
      id: 'pipeline',
      titulo: 'Organizar no funil',
      descricao: 'Abra um lead e mova para a etapa correta do funil de vendas.',
      tab: 'pipeline',
      check: function() { return OnboardingComercial._temLeadComStatus; }
    },
    {
      id: 'followup',
      titulo: 'Agendar próximo contato',
      descricao: 'Defina data/hora de retorno para não perder oportunidades.',
      tab: 'lembretes',
      check: function() { return OnboardingComercial._temLeadComProximoContato; }
    },
    {
      id: 'template',
      titulo: 'Preparar mensagem padrão',
      descricao: 'Crie um modelo simples para agilizar WhatsApp e e-mail.',
      tab: 'config',
      check: function() { return typeof templatesCache !== 'undefined' && templatesCache.length > 0; }
    },
    {
      id: 'importacao',
      titulo: 'Importar lista (opcional)',
      descricao: 'Se já tiver contatos prontos, use importação para ganhar tempo.',
      dica: 'Tem lista de WhatsApp ou CSV? Use importação guiada',
      tabDica: 'importacao',
      tab: 'importacao',
      check: function() { return OnboardingComercial._temLead || OnboardingComercial._temImportacao; }
    }
  ];

  var OnboardingComercial = {
    _temLead: false,
    _temLeadComStatus: false,
    _temLeadComProximoContato: false,
    _temImportacao: false,

    init: async function() {
      if (sessionStorage.getItem(SESSION_KEY)) return;

      try {
        var res = await api.get('/tenant/comercial/leads?per_page=20');
        var leads = Array.isArray(res && res.items) ? res.items : (Array.isArray(res) ? res : []);
        this._temLead = (res && typeof res.total === 'number') ? res.total > 0 : leads.length > 0;
        this._temLeadComStatus = leads.some(function(l) { return !!(l && l.status_pipeline && l.status_pipeline !== 'novo'); });
        this._temLeadComProximoContato = leads.some(function(l) { return !!(l && l.proximo_contato_em); });
        this._temImportacao = this._temLead && leads.length >= 3;
      } catch(e) {
        this._temLead = false;
        this._temLeadComStatus = false;
        this._temLeadComProximoContato = false;
        this._temImportacao = false;
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
      if (document.getElementById('ob-bloco')) return;
      var anchor = document.getElementById('briefing-container');
      if (!anchor) return;

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
              '<div class="ob-titulo-principal">🚀 Rotina guiada do Comercial</div>' +
              '<div class="ob-subtitulo">Siga os passos para operar o CRM com segurança no dia a dia</div>' +
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

      anchor.insertAdjacentHTML('beforebegin', html);
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
