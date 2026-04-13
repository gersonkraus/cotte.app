const MODAL_TITLES = {
  NEW_TEMPLATE: 'Novo Template',
  EDIT_TEMPLATE: 'Editar Template'
};

class TemplatesManager {
  static async carregarTemplates() {
    try {
      var tpls = await api.get('/comercial/templates');
      var tbody = document.getElementById('templates-tbody');
      if (!tbody) return; // Prevent error if element doesn't exist
      
      if (!tpls.length) { 
        tbody.innerHTML = '<tr><td colspan="5"><div class="empty"><p>Nenhum template</p></div></td></tr>'; 
        TemplatesManager.renderTemplatesMobile([]); 
        return; 
      }
      
      var canalEmoji = { whatsapp:'📱', email:'📧', sms:'💬' };
      tbody.innerHTML = tpls.map(function(t) {
        var preview = (t.conteudo || '').replace(/\n/g, ' ').slice(0, 80) + ((t.conteudo || '').length > 80 ? '…' : '');
        
        // Handling variables that might not exist globally if not initialized yet
        const tipoLabel = typeof TIPO_TPL_LABELS !== 'undefined' && TIPO_TPL_LABELS[t.tipo] ? TIPO_TPL_LABELS[t.tipo] : t.tipo;
        const canalLabel = typeof CANAL_TPL_LABELS !== 'undefined' && CANAL_TPL_LABELS[t.canal] ? CANAL_TPL_LABELS[t.canal] : t.canal;
        
        return '<tr>' +
          '<td><strong>' + (typeof esc === 'function' ? esc(t.nome) : t.nome) + '</strong><div style="font-size:11px;color:var(--muted);margin-top:2px">' + (typeof esc === 'function' ? esc(preview) : preview) + '</div></td>' +
          '<td>' + tipoLabel + '</td>' +
          '<td>' + (canalEmoji[t.canal] || '') + ' ' + canalLabel + '</td>' +
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
    var canalEmoji = { whatsapp:'📱', email:'📧', sms:'💬' };
    container.innerHTML = tpls.map(function(t) {
      var preview = (t.conteudo || '').replace(/\n/g, ' ').slice(0, 60) + ((t.conteudo || '').length > 60 ? '…' : '');
      
      const tipoLabel = typeof TIPO_TPL_LABELS !== 'undefined' && TIPO_TPL_LABELS[t.tipo] ? TIPO_TPL_LABELS[t.tipo] : t.tipo;
      const canalLabel = typeof CANAL_TPL_LABELS !== 'undefined' && CANAL_TPL_LABELS[t.canal] ? CANAL_TPL_LABELS[t.canal] : t.canal;
      
      return '<div class="crud-mobile-card">' +
        '<div class="crud-mobile-card-header">' +
          '<div class="crud-mobile-card-title">' + (typeof esc === 'function' ? esc(t.nome) : t.nome) + '</div>' +
          '<span class="badge-active ' + (t.ativo ? 'on' : 'off') + '">' + (t.ativo ? 'Ativo' : 'Inativo') + '</span>' +
        '</div>' +
        '<div class="crud-mobile-card-body">' +
          '<div>' + (canalEmoji[t.canal] || '') + ' ' + canalLabel + ' | ' + tipoLabel + '</div>' +
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
    document.getElementById('tpl-tipo').value = 'mensagem_inicial';
    document.getElementById('tpl-canal').value = 'whatsapp';
    document.getElementById('tpl-assunto').value = '';
    document.getElementById('tpl-conteudo').value = '';
    document.getElementById('modal-template').classList.add('open');
  }

  static async editarTemplate(id) {
    try {
      var t = await api.get('/comercial/templates/' + id);
      document.getElementById('tpl-id').value = t.id;
      document.getElementById('modal-tpl-title').textContent = MODAL_TITLES.EDIT_TEMPLATE;
      document.getElementById('tpl-nome').value = t.nome;
      document.getElementById('tpl-tipo').value = t.tipo;
      document.getElementById('tpl-canal').value = t.canal;
      document.getElementById('tpl-assunto').value = t.assunto || '';
      document.getElementById('tpl-conteudo').value = t.conteudo;
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
      if (id) { 
        await api.patch('/comercial/templates/' + id, data); 
        if (typeof showToast !== 'undefined') showToast('Template atualizado!', 'success'); 
      } else { 
        await api.post('/comercial/templates', data); 
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
      await api.delete('/comercial/templates/' + id); 
      if (typeof showToast !== 'undefined') showToast('Template excluído!', 'success'); 
      TemplatesManager.carregarTemplates(); 
    } catch(e) { 
      if (typeof showToast !== 'undefined') showToast('Erro', 'error'); 
    }
  }
  static initVariablesEvents() {
    document.querySelectorAll('.btn-var-badge').forEach(btn => {
      btn.addEventListener('mousedown', (e) => {
        // Evita que o textarea perca o foco antes do clique, preservando a seleção do cursor
        e.preventDefault(); 
      });
      btn.addEventListener('click', (e) => {
        const varText = e.target.getAttribute('data-var');
        TemplatesManager.injetarVariavel(varText);
      });
    });
  }

  static injetarVariavel(variavelText) {
    const textarea = document.getElementById('tpl-conteudo');
    if (!textarea) return;

    // Foca caso não esteja focado
    textarea.focus();

    const startPos = textarea.selectionStart || 0;
    const endPos = textarea.selectionEnd || 0;
    const textBefore = textarea.value.substring(0, startPos);
    const textAfter = textarea.value.substring(endPos, textarea.value.length);

    textarea.value = textBefore + variavelText + textAfter;

    // Retorna o cursor para logo após a variável inserida
    const newPos = startPos + variavelText.length;
    textarea.setSelectionRange(newPos, newPos);
  }
}

// Inicializar eventos de variáveis assim que o DOM carregar
document.addEventListener('DOMContentLoaded', () => {
  TemplatesManager.initVariablesEvents();
});

// Para manter compatibilidade com botões que chamam as funções globais no HTML (ex. onclick="abrirModalTemplate()"):
window.carregarTemplates = TemplatesManager.carregarTemplates;
window.abrirModalTemplate = TemplatesManager.abrirModalTemplate;
window.editarTemplate = TemplatesManager.editarTemplate;
window.salvarTemplate = TemplatesManager.salvarTemplate;
window.excluirTemplate = TemplatesManager.excluirTemplate;
window.renderTemplatesMobile = TemplatesManager.renderTemplatesMobile;
