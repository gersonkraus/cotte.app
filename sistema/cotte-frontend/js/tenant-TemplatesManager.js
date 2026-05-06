const MODAL_TITLES = {
  NEW_TEMPLATE: 'Novo Template',
  EDIT_TEMPLATE: 'Editar Template'
};

const TIPOS_TPL_CONFIG = [
  {
    tipo: 'mensagem_inicial',
    emoji: '👋',
    label: 'Mensagem Inicial',
    desc: 'Para se apresentar a um novo contato pela primeira vez',
    canal: 'whatsapp',
    canalLabel: '📱 WhatsApp',
    canalOptions: ['whatsapp', 'ambos']
  },
  {
    tipo: 'followup',
    emoji: '🔁',
    label: 'Follow-up',
    desc: 'Para retomar contato com quem não respondeu ainda',
    canal: 'whatsapp',
    canalLabel: '📱 WhatsApp',
    canalOptions: ['whatsapp', 'email', 'ambos']
  },
  {
    tipo: 'proposta_comercial',
    emoji: '💼',
    label: 'Proposta Comercial',
    desc: 'Para enviar uma oferta com valor e prazo ao cliente',
    canal: 'ambos',
    canalLabel: '📱📧 WhatsApp ou E-mail',
    canalOptions: ['whatsapp', 'email', 'ambos']
  },
  {
    tipo: 'email_comercial',
    emoji: '📧',
    label: 'E-mail Comercial',
    desc: 'Para comunicações formais e envio de documentos',
    canal: 'email',
    canalLabel: '📧 E-mail',
    canalOptions: ['email']
  }
];

const EXEMPLOS_TPL = {
  mensagem_inicial: {
    whatsapp: 'Olá {nome}, tudo bem? 😊\n\nAqui é da equipe da {empresa}.\n\nVi que {empresa_lead} pode se interessar pelo que oferecemos. Posso te contar mais em 2 minutinhos?',
    ambos: 'Olá {nome}, tudo bem? 😊\n\nAqui é da equipe da {empresa}. Gostaria de apresentar nossa solução para {empresa_lead}.\n\nPosso te contar mais detalhes?'
  },
  followup: {
    whatsapp: 'Oi {nome}! 👋\n\nPassando para ver se teve chance de pensar na nossa conversa.\n\nFica à vontade para me chamar se tiver dúvidas 😊',
    email: 'Olá {nome},\n\nPassando para dar continuidade à nossa conversa sobre {empresa_lead}.\n\nCaso tenha surgido alguma dúvida, estou à disposição!\n\nAbraços,',
    ambos: 'Oi {nome}! Passando para verificar se surgiu alguma dúvida. Pode me chamar quando quiser! 😊'
  },
  proposta_comercial: {
    whatsapp: 'Olá {nome}! 🤝\n\nPreparei uma proposta especial para {empresa_lead}:\n\n💰 Investimento: R$ {valor}\n📅 Validade: 7 dias\n\nPosso te enviar todos os detalhes?',
    email: 'Prezado(a) {nome},\n\nSeguem os detalhes da proposta comercial para {empresa_lead}:\n\n• Investimento: R$ {valor}\n• Validade: 7 dias\n\nEstou à disposição para esclarecer qualquer dúvida.\n\nAtenciosamente,',
    ambos: 'Olá {nome}! Preparei uma proposta para {empresa_lead} no valor de R$ {valor}. Posso te enviar os detalhes completos?'
  },
  email_comercial: {
    email: 'Prezado(a) {nome},\n\nEspero que esteja bem.\n\nGostaria de apresentar nossa solução e acredito que pode ser muito benéfica para {empresa_lead}.\n\nTeria disponibilidade para uma conversa de 15 minutos?\n\nAtenciosamente,'
  }
};

const SUGESTAO_NOMES_TPL = {
  mensagem_inicial: 'Apresentação Inicial',
  followup: 'Follow-up',
  proposta_comercial: 'Proposta Comercial',
  email_comercial: 'E-mail Comercial'
};

const BANNER_DESCRICAO_TPL = {
  mensagem_inicial: 'Primeiro contato — para se apresentar a novos leads',
  followup: 'Retomada de contato — para leads que não responderam',
  proposta_comercial: 'Proposta — para enviar oferta com valor ao cliente',
  email_comercial: 'E-mail formal — para comunicações e documentos'
};

let _tplTipoAtual = null;

class TemplatesManager {
  static async carregarTemplates() {
    try {
      var tpls = await api.get('/tenant/comercial/templates');
      var tbody = document.getElementById('templates-tbody');
      if (!tbody) return;

      if (!tpls.length) {
        tbody.innerHTML = '<tr><td colspan="5"><div class="empty"><p>Nenhum template</p></div></td></tr>';
        TemplatesManager.renderTemplatesMobile([]);
        return;
      }

      var canalEmoji = { whatsapp: '📱', email: '📧', sms: '💬', ambos: '📱📧' };
      tbody.innerHTML = tpls.map(function(t) {
        var preview = (t.conteudo || '').replace(/\n/g, ' ').slice(0, 80) + ((t.conteudo || '').length > 80 ? '…' : '');
        const cfg = TIPOS_TPL_CONFIG.find(c => c.tipo === t.tipo);
        const tipoLabel = cfg ? (cfg.emoji + ' ' + cfg.label) : t.tipo;
        const canalLabel = t.canal === 'ambos' ? '📱📧 Ambos' : ((canalEmoji[t.canal] || '') + ' ' + (t.canal === 'whatsapp' ? 'WhatsApp' : 'E-mail'));
        const anexoBadge = t.anexo_nome_original ? '<span style="display:inline-flex;margin-left:6px;padding:2px 6px;border:1px solid var(--border);border-radius:999px;font-size:10px;color:var(--muted)">Com anexo</span>' : '';

        return '<tr>' +
          '<td><strong>' + (typeof esc === 'function' ? esc(t.nome) : t.nome) + '</strong>' + anexoBadge + '<div style="font-size:11px;color:var(--muted);margin-top:2px">' + (typeof esc === 'function' ? esc(preview) : preview) + '</div></td>' +
          '<td>' + tipoLabel + '</td>' +
          '<td>' + canalLabel + '</td>' +
          '<td><span class="badge-active ' + (t.ativo ? 'on' : 'off') + '">' + (t.ativo ? 'Ativo' : 'Inativo') + '</span></td>' +
          '<td><button class="btn btn-sm btn-ghost btn-edit-tpl" data-id="' + t.id + '">✏️</button> <button class="btn btn-sm btn-ghost btn-del-tpl" data-id="' + t.id + '">🗑️</button></td>' +
          '</tr>';
      }).join('');

      tbody.querySelectorAll('.btn-edit-tpl').forEach(function(btn) {
        btn.addEventListener('click', function() { TemplatesManager.editarTemplate(parseInt(this.dataset.id)); });
      });
      tbody.querySelectorAll('.btn-del-tpl').forEach(function(btn) {
        btn.addEventListener('click', function() { TemplatesManager.excluirTemplate(parseInt(this.dataset.id)); });
      });

      TemplatesManager.renderTemplatesMobile(tpls);
    } catch(e) {
      if (typeof showToast !== 'undefined') showToast('Erro ao carregar templates', 'error');
    }
  }

  static renderTemplatesMobile(tpls) {
    var container = document.getElementById('templates-cards-mobile');
    if (!container) return;
    if (!tpls.length) { container.innerHTML = '<div style="text-align:center;padding:24px;color:var(--muted)">Nenhum template</div>'; return; }
    var canalEmoji = { whatsapp: '📱', email: '📧', sms: '💬', ambos: '📱📧' };
    container.innerHTML = tpls.map(function(t) {
      var preview = (t.conteudo || '').replace(/\n/g, ' ').slice(0, 60) + ((t.conteudo || '').length > 60 ? '…' : '');
      const cfg = TIPOS_TPL_CONFIG.find(c => c.tipo === t.tipo);
      const tipoLabel = cfg ? (cfg.emoji + ' ' + cfg.label) : t.tipo;
      const canalLabel = t.canal === 'ambos' ? '📱📧 Ambos' : ((canalEmoji[t.canal] || '') + ' ' + (t.canal === 'whatsapp' ? 'WhatsApp' : 'E-mail'));
      const anexoInfo = t.anexo_nome_original ? '<div style="font-size:11px;color:var(--muted);margin-top:4px">📎 Com anexo</div>' : '';

      return '<div class="crud-mobile-card">' +
        '<div class="crud-mobile-card-header">' +
          '<div class="crud-mobile-card-title">' + (typeof esc === 'function' ? esc(t.nome) : t.nome) + '</div>' +
          '<span class="badge-active ' + (t.ativo ? 'on' : 'off') + '">' + (t.ativo ? 'Ativo' : 'Inativo') + '</span>' +
        '</div>' +
        '<div class="crud-mobile-card-body">' +
          '<div>' + canalLabel + ' | ' + tipoLabel + '</div>' +
          anexoInfo +
          '<div style="font-size:11px;color:var(--muted)">' + (typeof esc === 'function' ? esc(preview) : preview) + '</div>' +
        '</div>' +
        '<div class="crud-mobile-card-actions">' +
          '<button class="btn btn-sm btn-ghost" onclick="TemplatesManager.editarTemplate(' + t.id + ')">✏️ Editar</button>' +
          '<button class="btn btn-sm btn-ghost" onclick="TemplatesManager.excluirTemplate(' + t.id + ')" style="color:var(--red)">🗑️ Excluir</button>' +
        '</div></div>';
    }).join('');
  }

  static abrirModalTemplate() {
    document.getElementById('tpl-id').value = '';
    document.getElementById('modal-tpl-title').textContent = MODAL_TITLES.NEW_TEMPLATE;
    document.getElementById('tpl-nome').value = '';
    document.getElementById('tpl-tipo').value = '';
    document.getElementById('tpl-canal').value = 'whatsapp';
    document.getElementById('tpl-assunto').value = '';
    document.getElementById('tpl-conteudo').value = '';
    _tplTipoAtual = null;
    TemplatesManager._resetAnexoState();
    TemplatesManager._mostrarEtapa(1);
    document.getElementById('modal-template').classList.add('open');
  }

  static async editarTemplate(id) {
    try {
      var t = await api.get('/tenant/comercial/templates/' + id);
      document.getElementById('tpl-id').value = t.id;
      document.getElementById('modal-tpl-title').textContent = MODAL_TITLES.EDIT_TEMPLATE;
      document.getElementById('tpl-nome').value = t.nome;
      document.getElementById('tpl-tipo').value = t.tipo;
      document.getElementById('tpl-canal').value = t.canal;
      document.getElementById('tpl-assunto').value = t.assunto || '';
      document.getElementById('tpl-conteudo').value = t.conteudo;
      _tplTipoAtual = t.tipo;
      TemplatesManager._resetAnexoState();
      TemplatesManager._setAnexoMetadata({
        arquivo_path: t.anexo_arquivo_path || t.anexo_url || '',
        arquivo_nome_original: t.anexo_nome_original || '',
        mime_type: t.anexo_mime_type || '',
        tamanho_bytes: t.anexo_tamanho_bytes || ''
      });
      const cfg = TIPOS_TPL_CONFIG.find(c => c.tipo === t.tipo);
      TemplatesManager._mostrarEtapa(2);
      TemplatesManager._updateContextBanner(t.tipo, t.canal);
      if (cfg) TemplatesManager._renderCanalPills(cfg, t.canal);
      TemplatesManager._toggleAssunto(t.canal);
      TemplatesManager._updateCharCounter();
      document.getElementById('modal-template').classList.add('open');
    } catch(e) {
      if (typeof showToast !== 'undefined') showToast('Erro', 'error');
    }
  }

  static async salvarTemplate() {
    var nome = document.getElementById('tpl-nome').value;
    var conteudo = document.getElementById('tpl-conteudo').value;
    if (!nome || !conteudo) {
      if (typeof showToast !== 'undefined') showToast('Preencha nome e conteúdo', 'error');
      return;
    }
    var data = {
      nome: nome,
      tipo: document.getElementById('tpl-tipo').value,
      canal: document.getElementById('tpl-canal').value,
      assunto: document.getElementById('tpl-assunto').value || null,
      conteudo: conteudo
    };
    var id = document.getElementById('tpl-id').value;
    try {
      var uploadMeta = await TemplatesManager._uploadSelectedAnexo();
      if (uploadMeta) {
        TemplatesManager._setAnexoMetadata(uploadMeta);
      }
      var anexoMeta = TemplatesManager._getAnexoMetadata();
      if (anexoMeta.anexo_nome_original) {
        data.anexo_arquivo_path = anexoMeta.anexo_arquivo_path;
        data.anexo_nome_original = anexoMeta.anexo_nome_original;
        data.anexo_mime_type = anexoMeta.anexo_mime_type;
        data.anexo_tamanho_bytes = anexoMeta.anexo_tamanho_bytes;
      }
      if (id && document.getElementById('tpl-anexo-remover').value === '1') {
        data.remover_anexo = true;
      }
      if (id) {
        await api.put('/tenant/comercial/templates/' + id, data);
        if (typeof showToast !== 'undefined') showToast('Template atualizado!', 'success');
      } else {
        await api.post('/tenant/comercial/templates', data);
        if (typeof showToast !== 'undefined') showToast('Template criado!', 'success');
      }
      if (typeof fecharModal !== 'undefined') fecharModal('modal-template');
      TemplatesManager.carregarTemplates();
      if (typeof carregarCadastrosCache !== 'undefined') await carregarCadastrosCache();
    } catch(e) {
      if (typeof showToast !== 'undefined') showToast(e.message || 'Erro', 'error');
    }
  }

  static async excluirTemplate(id) {
    if (!confirm('Excluir template?')) return;
    try {
      await api.delete('/tenant/comercial/templates/' + id);
      if (typeof showToast !== 'undefined') showToast('Template excluído!', 'success');
      TemplatesManager.carregarTemplates();
    } catch(e) {
      if (typeof showToast !== 'undefined') showToast('Erro', 'error');
    }
  }

  static _mostrarEtapa(n) {
    const step1 = document.getElementById('tpl-step-1');
    const step2 = document.getElementById('tpl-step-2');
    const footer1 = document.getElementById('tpl-footer-step1');
    const footer2 = document.getElementById('tpl-footer-step2');
    const sc1 = document.getElementById('tpl-sc-1');
    const sc2 = document.getElementById('tpl-sc-2');
    const sl = document.getElementById('tpl-sl-12');
    if (n === 1) {
      step1.style.display = '';
      step2.style.display = 'none';
      footer1.style.display = '';
      footer2.style.display = 'none';
      sc1.classList.add('active');
      sc1.classList.remove('done');
      sc2.classList.remove('active', 'done');
      if (sl) sl.classList.remove('done');
      TemplatesManager._renderTypeCards();
    } else {
      step1.style.display = 'none';
      step2.style.display = '';
      footer1.style.display = 'none';
      footer2.style.display = 'flex';
      sc1.classList.remove('active');
      sc1.classList.add('done');
      sc2.classList.add('active');
      if (sl) sl.classList.add('done');
    }
  }

  static _renderTypeCards() {
    const container = document.getElementById('tpl-type-cards');
    if (!container) return;
    container.innerHTML = TIPOS_TPL_CONFIG.map(cfg => `
      <div class="tpl-type-card" data-tipo="${cfg.tipo}" role="button" tabindex="0" aria-label="${cfg.label}">
        <div class="tpl-type-card-emoji">${cfg.emoji}</div>
        <div class="tpl-type-card-body">
          <div class="tpl-type-card-title">${cfg.label}</div>
          <div class="tpl-type-card-desc">${cfg.desc}</div>
        </div>
        <div class="tpl-type-card-canal">${cfg.canalLabel}</div>
      </div>
    `).join('');
    container.querySelectorAll('.tpl-type-card').forEach(card => {
      const handler = () => TemplatesManager._selecionarTipo(card.dataset.tipo);
      card.addEventListener('click', handler);
      card.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handler(); }
      });
    });
  }

  static _selecionarTipo(tipo) {
    const cfg = TIPOS_TPL_CONFIG.find(c => c.tipo === tipo);
    if (!cfg) return;
    _tplTipoAtual = tipo;
    document.getElementById('tpl-tipo').value = tipo;

    const canalPadrao = cfg.canal === 'ambos' ? 'ambos' : cfg.canal;
    document.getElementById('tpl-canal').value = canalPadrao;

    const sugestao = document.getElementById('tpl-sugestao-nome');
    if (sugestao) sugestao.textContent = 'Sugestão: ' + SUGESTAO_NOMES_TPL[tipo];

    const exemplos = EXEMPLOS_TPL[tipo] || {};
    document.getElementById('tpl-conteudo').value = exemplos[canalPadrao] || exemplos['whatsapp'] || exemplos['email'] || '';

    TemplatesManager._updateContextBanner(tipo, canalPadrao);
    TemplatesManager._renderCanalPills(cfg, canalPadrao);
    TemplatesManager._toggleAssunto(canalPadrao);
    TemplatesManager._updateCharCounter();
    TemplatesManager._mostrarEtapa(2);
  }

  static _voltarEtapa1() {
    _tplTipoAtual = null;
    document.getElementById('tpl-tipo').value = '';
    TemplatesManager._mostrarEtapa(1);
  }

  static _renderCanalPills(cfg, canalAtivo) {
    const container = document.getElementById('tpl-canal-pills');
    if (!container || !cfg) return;
    const CANAL_OPTIONS = [
      { value: 'whatsapp', label: '📱 WhatsApp' },
      { value: 'email', label: '📧 E-mail' },
      { value: 'ambos', label: '📱📧 Ambos' }
    ];
    const opcoes = CANAL_OPTIONS.filter(o => cfg.canalOptions.includes(o.value));
    if (opcoes.length <= 1) {
      container.innerHTML = `<span class="tpl-canal-pill active" style="cursor:default">${opcoes[0] ? opcoes[0].label : ''}</span>`;
      return;
    }
    container.innerHTML = opcoes.map(o => `
      <button type="button" class="tpl-canal-pill${o.value === canalAtivo ? ' active' : ''}" data-canal="${o.value}">${o.label}</button>
    `).join('');
    container.querySelectorAll('.tpl-canal-pill[data-canal]').forEach(pill => {
      pill.addEventListener('click', () => {
        container.querySelectorAll('.tpl-canal-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        const canal = pill.dataset.canal;
        document.getElementById('tpl-canal').value = canal;
        const tipo = _tplTipoAtual;
        const exemploAtual = document.getElementById('tpl-conteudo').value;
        const todosExemplos = Object.values(EXEMPLOS_TPL[tipo] || {});
        if (!exemploAtual || todosExemplos.includes(exemploAtual)) {
          const novo = (EXEMPLOS_TPL[tipo] || {})[canal] || exemploAtual;
          document.getElementById('tpl-conteudo').value = novo;
          TemplatesManager._updateCharCounter();
        }
        TemplatesManager._updateContextBanner(tipo, canal);
        TemplatesManager._toggleAssunto(canal);
      });
    });
  }

  static _updateContextBanner(tipo, canal) {
    const banner = document.getElementById('tpl-context-banner');
    if (!banner) return;
    const cfg = TIPOS_TPL_CONFIG.find(c => c.tipo === tipo);
    const desc = BANNER_DESCRICAO_TPL[tipo] || '';
    const canalStr = canal === 'whatsapp' ? '📱 WhatsApp' : canal === 'email' ? '📧 E-mail' : '📱📧 WhatsApp e E-mail';
    banner.innerHTML = `<span class="tpl-context-emoji">${cfg ? cfg.emoji : ''}</span> <span><strong>${cfg ? cfg.label : tipo}</strong> — ${desc} &nbsp;|&nbsp; ${canalStr}</span>`;
  }

  static _toggleAssunto(canal) {
    const group = document.getElementById('tpl-assunto-group');
    if (!group) return;
    group.style.display = (canal === 'email' || canal === 'ambos') ? '' : 'none';
  }

  static _updateCharCounter() {
    const textarea = document.getElementById('tpl-conteudo');
    const counter = document.getElementById('tpl-char-counter');
    if (!textarea || !counter) return;
    const len = textarea.value.length;
    counter.textContent = len + ' caracteres' + (len > 1000 ? ' — mensagem longa para WhatsApp' : '');
    counter.style.color = len > 1000 ? 'var(--red)' : 'var(--muted)';
  }

  static _formatFileSize(size) {
    var bytes = parseInt(size, 10);
    if (!bytes) return '';
    if (bytes >= 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1).replace(/\.0$/, '') + ' MB';
    if (bytes >= 1024) return Math.round(bytes / 1024) + ' KB';
    return bytes + ' bytes';
  }

  static _updateAnexoUI() {
    var info = document.getElementById('tpl-anexo-atual');
    var btnRemover = document.getElementById('btn-tpl-remover-anexo');
    var input = document.getElementById('tpl-anexo');
    if (!info || !btnRemover || !input) return;

    var nome = document.getElementById('tpl-anexo-nome').value;
    var path = document.getElementById('tpl-anexo-path').value;
    var tamanho = TemplatesManager._formatFileSize(document.getElementById('tpl-anexo-tamanho').value);
    var selecionado = input.files && input.files[0];

    if (selecionado) {
      info.textContent = 'Arquivo selecionado: ' + selecionado.name + (selecionado.size ? ' (' + TemplatesManager._formatFileSize(selecionado.size) + ')' : '') + '. Será enviado ao salvar.';
      btnRemover.style.display = '';
      return;
    }

    if (nome) {
      info.textContent = '';
      info.appendChild(document.createTextNode('Anexo atual: '));
      if (path) {
        var link = document.createElement('a');
        link.href = path;
        link.target = '_blank';
        link.rel = 'noopener';
        link.textContent = nome;
        info.appendChild(link);
      } else {
        info.appendChild(document.createTextNode(nome));
      }
      if (tamanho) {
        info.appendChild(document.createTextNode(' (' + tamanho + ')'));
      }
      btnRemover.style.display = '';
      return;
    }

    info.textContent = 'Nenhum anexo selecionado.';
    btnRemover.style.display = 'none';
  }

  static _setAnexoMetadata(meta) {
    document.getElementById('tpl-anexo-path').value = meta && meta.arquivo_path ? meta.arquivo_path : '';
    document.getElementById('tpl-anexo-nome').value = meta && meta.arquivo_nome_original ? meta.arquivo_nome_original : '';
    document.getElementById('tpl-anexo-mime').value = meta && meta.mime_type ? meta.mime_type : '';
    document.getElementById('tpl-anexo-tamanho').value = meta && meta.tamanho_bytes ? String(meta.tamanho_bytes) : '';
    document.getElementById('tpl-anexo-remover').value = '0';
    TemplatesManager._updateAnexoUI();
  }

  static _getAnexoMetadata() {
    return {
      anexo_arquivo_path: document.getElementById('tpl-anexo-path').value || null,
      anexo_nome_original: document.getElementById('tpl-anexo-nome').value || null,
      anexo_mime_type: document.getElementById('tpl-anexo-mime').value || null,
      anexo_tamanho_bytes: document.getElementById('tpl-anexo-tamanho').value ? parseInt(document.getElementById('tpl-anexo-tamanho').value, 10) : null
    };
  }

  static _resetAnexoState() {
    document.getElementById('tpl-anexo').value = '';
    document.getElementById('tpl-anexo-remover').value = '0';
    TemplatesManager._setAnexoMetadata(null);
  }

  static _removeAnexo() {
    document.getElementById('tpl-anexo').value = '';
    document.getElementById('tpl-anexo-path').value = '';
    document.getElementById('tpl-anexo-nome').value = '';
    document.getElementById('tpl-anexo-mime').value = '';
    document.getElementById('tpl-anexo-tamanho').value = '';
    document.getElementById('tpl-anexo-remover').value = '1';
    TemplatesManager._updateAnexoUI();
  }

  static async _uploadSelectedAnexo() {
    var input = document.getElementById('tpl-anexo');
    if (!input || !input.files || !input.files[0]) return null;

    var formData = new FormData();
    formData.append('file', input.files[0]);
    var response = await api.post('/tenant/comercial/templates/upload-anexo', formData);
    input.value = '';
    return response;
  }

  static _initV2Events() {
    const zone = document.getElementById('tpl-image-zone');
    if (!zone) return;

    zone.addEventListener('click', () => {
      const input = document.getElementById('tpl-anexo');
      if (input) input.click();
    });
    
    zone.addEventListener('dragover', (e) => {
      e.preventDefault();
      zone.classList.add('dragover');
    });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
    zone.addEventListener('drop', (e) => {
      e.preventDefault();
      zone.classList.remove('dragover');
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        TemplatesManager._handleFileSelection(e.dataTransfer.files[0]);
      }
    });

    const conteudo = document.getElementById('tpl-conteudo');
    if (conteudo) {
      conteudo.addEventListener('paste', (e) => {
        const items = (e.clipboardData || e.originalEvent.clipboardData).items;
        for (let index in items) {
          const item = items[index];
          if (item.kind === 'file') {
            const blob = item.getAsFile();
            TemplatesManager._handleFileSelection(blob);
          }
        }
      });
      conteudo.addEventListener('input', () => {
        TemplatesManager._updateCharCounter();
        TemplatesManager._updateLivePreview();
      });
    }

    const assunto = document.getElementById('tpl-assunto');
    if (assunto) {
      assunto.addEventListener('input', () => TemplatesManager._updateLivePreview());
    }

    const anexo = document.getElementById('tpl-anexo');
    if (anexo) {
      anexo.addEventListener('change', (e) => {
        document.getElementById('tpl-anexo-remover').value = '0';
        if (e.target.files && e.target.files[0]) {
          TemplatesManager._handleFileSelection(e.target.files[0]);
        }
        TemplatesManager._updateAnexoUI();
      });
    }
  }

  static _handleFileSelection(file) {
    // Task 4 will implement this fully
    console.log('File selected:', file);
  }

  static _updateLivePreview() {
    // Task 4 will implement this fully
    console.log('Updating live preview...');
  }

  static initVariablesEvents() {
    TemplatesManager._initV2Events();
    document.querySelectorAll('.btn-var-badge').forEach(btn => {
      btn.addEventListener('mousedown', e => e.preventDefault());
      btn.addEventListener('click', e => {
        TemplatesManager.injetarVariavel(e.target.getAttribute('data-var'));
      });
    });

    const btnVoltar = document.getElementById('btn-tpl-voltar');
    if (btnVoltar) btnVoltar.addEventListener('click', TemplatesManager._voltarEtapa1);

    const btnRemoverAnexo = document.getElementById('btn-tpl-remover-anexo');
    if (btnRemoverAnexo) btnRemoverAnexo.addEventListener('click', TemplatesManager._removeAnexo);
  }

  static injetarVariavel(variavelText) {
    const textarea = document.getElementById('tpl-conteudo');
    if (!textarea) return;
    textarea.focus();
    const startPos = textarea.selectionStart || 0;
    const endPos = textarea.selectionEnd || 0;
    const textBefore = textarea.value.substring(0, startPos);
    const textAfter = textarea.value.substring(endPos, textarea.value.length);
    textarea.value = textBefore + variavelText + textAfter;
    const newPos = startPos + variavelText.length;
    textarea.setSelectionRange(newPos, newPos);
    TemplatesManager._updateCharCounter();
  }
}

document.addEventListener('DOMContentLoaded', () => {
  TemplatesManager.initVariablesEvents();
});

window.carregarTemplates = TemplatesManager.carregarTemplates;
window.abrirModalTemplate = TemplatesManager.abrirModalTemplate;
window.editarTemplate = TemplatesManager.editarTemplate;
window.salvarTemplate = TemplatesManager.salvarTemplate;
window.excluirTemplate = TemplatesManager.excluirTemplate;
window.renderTemplatesMobile = TemplatesManager.renderTemplatesMobile;
