let documentosCache = [];
let documentoEditandoId = null;

const _DOC_TIPOS_LABEL = {
  certificado_garantia: 'Certificado de garantia',
  contrato: 'Contrato',
  termo: 'Termo',
  documento_tecnico: 'Documento técnico',
  anexo: 'Anexo',
  outro: 'Outro',
};

const _DOC_STATUS_LABEL = {
  ativo: 'Ativo',
  inativo: 'Inativo',
  arquivado: 'Arquivado',
};

function _statusPill(status) {
  const s = (status || '').toLowerCase();
  const map = {
    ativo:    { bg: 'rgba(16,185,129,0.12)', fg: '#10b981', br: 'rgba(16,185,129,0.25)' },
    inativo:  { bg: 'rgba(107,114,128,0.12)', fg: '#6b7280', br: 'rgba(107,114,128,0.25)' },
    arquivado:{ bg: 'rgba(249,115,22,0.12)', fg: '#f97316', br: 'rgba(249,115,22,0.25)' },
  };
  const c = map[s] || map.inativo;
  return `<span style="display:inline-flex;align-items:center;padding:3px 10px;border-radius:999px;border:1px solid ${c.br};background:${c.bg};color:${c.fg};font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:.05em">${escapeHtml(_DOC_STATUS_LABEL[s] || status || '—')}</span>`;
}

const _DOC_TIPOS_COLOR = {
  certificado_garantia: { bg:'rgba(99,102,241,.1)', fg:'#6366f1', br:'rgba(99,102,241,.25)' },
  contrato:             { bg:'rgba(59,130,246,.1)', fg:'#3b82f6', br:'rgba(59,130,246,.25)' },
  termo:                { bg:'rgba(245,158,11,.1)', fg:'#f59e0b', br:'rgba(245,158,11,.25)' },
  documento_tecnico:    { bg:'rgba(16,185,129,.1)', fg:'#10b981', br:'rgba(16,185,129,.25)' },
  anexo:                { bg:'rgba(139,92,246,.1)', fg:'#8b5cf6', br:'rgba(139,92,246,.25)' },
  outro:                { bg:'rgba(107,114,128,.1)', fg:'#6b7280', br:'rgba(107,114,128,.25)' },
};

function _tipoBadge(tipo) {
  const t = (tipo || 'outro');
  const c = _DOC_TIPOS_COLOR[t] || _DOC_TIPOS_COLOR.outro;
  const label = escapeHtml(_DOC_TIPOS_LABEL[t] || tipo || '—');
  return `<span style="display:inline-flex;align-items:center;padding:3px 9px;border-radius:999px;border:1px solid ${c.br};background:${c.bg};color:${c.fg};font-size:11px;font-weight:600;white-space:nowrap">${label}</span>`;
}


async function carregarDocumentos() {
  const tbody = document.getElementById('docs-tbody');
  tbody.innerHTML = `<tr><td colspan="6"><div class="loading"><div class="spinner"></div> Carregando...</div></td></tr>`;

  try {
    const q = (document.getElementById('docs-busca')?.value || '').trim();
    const tipo = (document.getElementById('docs-tipo')?.value || '').trim();
    const status = (document.getElementById('docs-status')?.value || '').trim();
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    if (tipo) params.set('tipo', tipo);
    if (status) params.set('status_filtro', status);
    params.set('incluir_arquivados', 'true');

    documentosCache = await api.get('/documentos/?' + params.toString());
    renderizarDocumentos(documentosCache || []);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><div class="icon">⚠️</div><div class="title">Erro ao carregar</div><div class="desc">${escapeHtml(err?.message || '')}</div></div></td></tr>`;
  }
}

function aplicarFiltrosDocumentos() {
  carregarDocumentos();
}

function renderizarDocumentos(lista) {
  const tbody = document.getElementById('docs-tbody');
  const countEl = document.getElementById('docs-count');

  if (!lista.length) {
    tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><div class="icon">📎</div><div class="title">Nenhum documento</div><div class="desc">Clique em "Novo documento" para cadastrar o primeiro.</div></div></td></tr>`;
    if (countEl) countEl.textContent = '';
    return;
  }

  if (countEl) countEl.textContent = `${lista.length} documento${lista.length !== 1 ? 's' : ''}`;

  tbody.innerHTML = lista.map(d => {
    const nome = escapeHtml(d.nome || '—');
    const versao = escapeHtml(d.versao || '—');
    const atualizado = d.atualizado_em || d.criado_em;

    const toggleLabel = (d.status === 'ativo') ? 'Inativar' : 'Ativar';
    const toggleIcon  = (d.status === 'ativo') ? '⏸' : '▶';
    const toggleNext  = (d.status === 'ativo') ? 'inativo' : 'ativo';

    const ib = (icon, fn, title, extra = '') =>
      `<button class="icon-btn${extra}" onclick="${fn}" title="${title}">${icon}</button>`;

    const actions = `
      <div style="display:flex;gap:4px;align-items:center">
        ${ib('👁', `abrirDocumento(${d.id})`, 'Abrir')}
        ${d.permite_download
          ? ib('⬇', `baixarDocumento(${d.id})`, 'Baixar')
          : `<button class="icon-btn" title="Download desabilitado" disabled>⬇</button>`}
        ${ib('✏️', `abrirModalEditarDocumento(${d.id})`, 'Editar')}
        ${ib(toggleIcon, `atualizarStatusDocumento(${d.id}, '${toggleNext}')`, toggleLabel)}
        ${ib('🗑', `excluirDocumento(${d.id})`, 'Excluir', ' danger')}
      </div>`;

    return `
      <tr>
        <td style="font-weight:600">${nome}</td>
        <td class="col-hide-mobile">${_tipoBadge(d.tipo)}</td>
        <td class="col-hide-mobile" style="color:var(--muted);font-size:13px">${versao}</td>
        <td class="col-hide-mobile">${_statusPill(d.status)}</td>
        <td class="col-hide-mobile" style="color:var(--muted);font-size:12px">${atualizado ? formatarData(atualizado) : '—'}</td>
        <td class="col-hide-mobile">${actions}</td>
      </tr>
      <tr class="action-row">
        <td colspan="6" style="padding:4px 12px 12px">
          <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:6px">
            ${_tipoBadge(d.tipo)}
            ${_statusPill(d.status)}
            ${versao !== '—' ? `<span style="font-size:11px;color:var(--muted)">v${versao}</span>` : ''}
            ${atualizado ? `<span style="font-size:11px;color:var(--muted)">${formatarData(atualizado)}</span>` : ''}
          </div>
          <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">
            ${ib("👁", `abrirDocumento(${d.id})`, "Abrir")}
            ${d.permite_download
              ? ib("⬇", `baixarDocumento(${d.id})`, "Baixar")
              : ""}
            ${ib("✏️", `abrirModalEditarDocumento(${d.id})`, "Editar")}
            ${ib(toggleIcon, `atualizarStatusDocumento(${d.id}, '${toggleNext}')`, toggleLabel)}
            ${ib("🗑", `excluirDocumento(${d.id})`, "Excluir", " danger")}
          </div>
        </td>
      </tr>`;
  }).join('');
}

function abrirModalNovoDocumento() {
  documentoEditandoId = null;
  document.getElementById('modal-doc-title').textContent = '📎 Novo documento';
  document.getElementById('btn-salvar-doc').textContent = 'Salvar';
  document.getElementById('doc-arquivo-obrigatorio').style.display = '';
  document.getElementById('btn-trocar-arquivo').style.display = 'none';
  document.getElementById('doc-arquivo-info').textContent = '';
  _limparFormDocumento();
  document.getElementById('modal-documento').classList.add('open');
}

function abrirModalEditarDocumento(docId) {
  const doc = documentosCache.find(d => d.id === docId);
  if (!doc) return;
  documentoEditandoId = doc.id;
  document.getElementById('modal-doc-title').textContent = '✏️ Editar documento';
  document.getElementById('btn-salvar-doc').textContent = 'Salvar alterações';

  // Configurar tipo de conteúdo
  const tipoConteudo = doc.tipo_conteudo || 'pdf';
  document.getElementById('doc-tipo-conteudo').value = tipoConteudo;
  
  // Configurar campos comuns
  document.getElementById('doc-nome').value = doc.nome || '';
  document.getElementById('doc-tipo').value = doc.tipo || 'outro';
  document.getElementById('doc-versao').value = doc.versao || '';
  document.getElementById('doc-status').value = doc.status || 'ativo';
  document.getElementById('doc-descricao').value = doc.descricao || '';
  document.getElementById('doc-permite-download').checked = !!doc.permite_download;
  document.getElementById('doc-visivel-portal').checked = !!doc.visivel_no_portal;

  // Configurar campos específicos baseados no tipo de conteúdo
  if (tipoConteudo === 'pdf') {
    document.getElementById('doc-arquivo-obrigatorio').style.display = 'none';
    document.getElementById('btn-trocar-arquivo').style.display = '';
    document.getElementById('doc-arquivo-info').textContent = doc.arquivo_nome_original ? `Arquivo atual: ${doc.arquivo_nome_original}` : 'Arquivo atual: —';
    const input = document.getElementById('doc-arquivo');
    if (input) input.value = '';
  } else {
    // Documento HTML
    document.getElementById('doc-arquivo-obrigatorio').style.display = 'none';
    document.getElementById('btn-trocar-arquivo').style.display = 'none';
    document.getElementById('doc-arquivo-info').textContent = 'Documento HTML (editor de texto rico)';
    
    // Carregar conteúdo HTML no editor
    if (doc.conteudo_html) {
      definirConteudoHtmlEditor(doc.conteudo_html);
    }
    
    // Configurar variáveis suportadas
    if (doc.variaveis_suportadas && Array.isArray(doc.variaveis_suportadas)) {
      document.getElementById('doc-variaveis-suportadas').value = JSON.stringify(doc.variaveis_suportadas);
    }
  }

  // Alternar visualização baseada no tipo de conteúdo
  alternarTipoConteudoDocumento();
  
  // Abrir modal
  document.getElementById('modal-documento').classList.add('open');
}

function trocarArquivoDocumento() {
  const input = document.getElementById('doc-arquivo');
  if (input) input.click();
}

function fecharModalDocumento() {
  document.getElementById('modal-documento').classList.remove('open');
}

function _limparFormDocumento() {
  document.getElementById('doc-nome').value = '';
  document.getElementById('doc-tipo').value = 'certificado_garantia';
  document.getElementById('doc-versao').value = '';
  document.getElementById('doc-status').value = 'ativo';
  document.getElementById('doc-descricao').value = '';
  document.getElementById('doc-permite-download').checked = true;
  document.getElementById('doc-visivel-portal').checked = true;
  const input = document.getElementById('doc-arquivo');
  if (input) input.value = '';
}

async function salvarDocumento() {
  const nome = document.getElementById('doc-nome').value.trim();
  const btn = document.getElementById('btn-salvar-doc');
  if (!nome) {
    showNotif('⚠️', 'Informe o nome', 'O nome do documento é obrigatório', 'error');
    return;
  }

  const tipo = document.getElementById('doc-tipo').value;
  const versao = document.getElementById('doc-versao').value.trim();
  const status = document.getElementById('doc-status').value;
  const descricao = document.getElementById('doc-descricao').value.trim();
  const permiteDownload = document.getElementById('doc-permite-download').checked;
  const visivelPortal = document.getElementById('doc-visivel-portal').checked;
  const tipoConteudo = document.getElementById('doc-tipo-conteudo').value;
  const arquivoInput = document.getElementById('doc-arquivo');
  const arquivo = arquivoInput?.files?.[0] || null;
  const variaveisSuportadas = document.getElementById('doc-variaveis-suportadas').value;

  // Obter conteúdo HTML do editor se for documento HTML
  let conteudoHtml = '';
  if (tipoConteudo === 'html' && quillEditor) {
    conteudoHtml = quillEditor.root.innerHTML;
    if (!conteudoHtml || conteudoHtml === '<p><br></p>' || conteudoHtml === '<p></p>') {
      showNotif('⚠️', 'Conteúdo vazio', 'Digite o conteúdo do documento HTML', 'error');
      return;
    }
  }

  setLoading(btn, true);
  try {
    if (!documentoEditandoId) {
      // Validações baseadas no tipo de conteúdo
      if (tipoConteudo === 'pdf' && !arquivo) {
        showNotif('⚠️', 'Envie o PDF', 'Selecione um arquivo PDF para cadastrar o documento', 'error');
        return;
      }
      
      if (tipoConteudo === 'html' && !conteudoHtml) {
        showNotif('⚠️', 'Conteúdo vazio', 'Digite o conteúdo do documento HTML', 'error');
        return;
      }

      const formData = new FormData();
      formData.append('nome', nome);
      formData.append('tipo', tipo);
      formData.append('versao', versao);
      formData.append('status_doc', status);
      formData.append('descricao', descricao);
      formData.append('permite_download', permiteDownload ? 'true' : 'false');
      formData.append('visivel_no_portal', visivelPortal ? 'true' : 'false');
      formData.append('tipo_conteudo', tipoConteudo);
      
      // Adicionar campos específicos do tipo de conteúdo
      if (tipoConteudo === 'pdf' && arquivo) {
        formData.append('arquivo', arquivo);
      } else if (tipoConteudo === 'html') {
        formData.append('conteudo_html', conteudoHtml);
        if (variaveisSuportadas) {
          formData.append('variaveis_suportadas', variaveisSuportadas);
        }
      }

      await _apiUpload('POST', '/documentos/', formData);
      fecharModalDocumento();
      showNotif('✅', 'Documento criado', 'Pronto para vincular em orçamentos');
    } else {
      // Atualização de documento existente
      const dadosAtualizacao = {
        nome,
        tipo,
        versao,
        status,
        descricao,
        permite_download: permiteDownload,
        visivel_no_portal: visivelPortal,
        tipo_conteudo: tipoConteudo,
      };
      
      // Adicionar campos específicos se for documento HTML
      if (tipoConteudo === 'html') {
        dadosAtualizacao.conteudo_html = conteudoHtml;
        if (variaveisSuportadas) {
          dadosAtualizacao.variaveis_suportadas = JSON.parse(variaveisSuportadas);
        }
      }
      
      await api.put(`/documentos/${documentoEditandoId}`, dadosAtualizacao);

      // Se for PDF e houver novo arquivo, fazer upload
      if (tipoConteudo === 'pdf' && arquivo) {
        const fd = new FormData();
        fd.append('arquivo', arquivo);
        await _apiUpload('PUT', `/documentos/${documentoEditandoId}/arquivo`, fd);
      }

      fecharModalDocumento();
      showNotif('✅', 'Documento atualizado', '');
    }
    await carregarDocumentos();
  } catch (err) {
    showNotif('❌', 'Erro', err.message, 'error');
  } finally {
    setLoading(btn, false, documentoEditandoId ? 'Salvar alterações' : 'Salvar');
  }
}

async function atualizarStatusDocumento(id, statusNovo) {
  try {
    await api.put(`/documentos/${id}`, { status: statusNovo });
    await carregarDocumentos();
    showNotif('✅', 'Status atualizado', '');
  } catch (err) {
    showNotif('❌', 'Erro', err.message, 'error');
  }
}

async function excluirDocumento(id) {
  const ok = confirm('Excluir este documento? Isso arquiva o documento e mantém histórico nos orçamentos já enviados.');
  if (!ok) return;
  try {
    await api.delete(`/documentos/${id}`);
    await carregarDocumentos();
    showNotif('✅', 'Documento excluído', '');
  } catch (err) {
    showNotif('❌', 'Erro', err.message, 'error');
  }
}

async function abrirDocumento(id) {
  try {
    const blob = await _apiDownloadBlob(`/documentos/${id}/arquivo`);
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  } catch (err) {
    showNotif('❌', 'Erro ao abrir', err.message, 'error');
  }
}

async function baixarDocumento(id) {
  try {
    const blob = await _apiDownloadBlob(`/documentos/${id}/arquivo?download=1`);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `documento-${id}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    showNotif('❌', 'Erro ao baixar', err.message, 'error');
  }
}

async function _apiUpload(method, endpoint, formData) {
  const token = getToken();
  const res = await fetch(API_URL + API_PREFIX + endpoint, {
    method,
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData,
  });
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch (_) { data = null; }
  if (res.status === 401) {
    logout();
    throw new Error('Sessão expirada. Faça login novamente.');
  }
  if (!res.ok) {
    throw new Error((data && data.detail) ? (typeof data.detail === 'string' ? data.detail : 'Erro no upload') : 'Erro no upload');
  }
  return data;
}

async function _apiDownloadBlob(endpoint) {
  const token = getToken();
  const res = await fetch(API_URL + API_PREFIX + endpoint, { headers: { 'Authorization': `Bearer ${token}` } });
  if (res.status === 401) {
    logout();
    throw new Error('Sessão expirada. Faça login novamente.');
  }
  if (!res.ok) {
    let data = null;
    try { data = await res.json(); } catch (_) { data = null; }
    throw new Error((data && data.detail) ? data.detail : 'Erro ao baixar arquivo');
  }
  return await res.blob();
}

// ============================================
// FUNÇÕES PARA EDITOR HTML E VARIÁVEIS
// ============================================

let quillEditor = null;

/**
 * Inicializa o editor Quill.js
 */
function inicializarEditorQuill() {
  if (quillEditor) {
    return; // Já inicializado
  }
  
  // Verificar se o container do editor existe
  const container = document.getElementById('editor-container');
  if (!container) {
    console.warn('Container do editor não encontrado');
    return;
  }
  
  // Carregar Quill.js dinamicamente se não estiver disponível
  if (typeof Quill === 'undefined') {
    console.warn('Quill.js não carregado. Carregando...');
    const script = document.createElement('script');
    script.src = 'https://cdn.quilljs.com/1.3.7/quill.js';
    script.onload = () => {
      criarEditorQuill();
    };
    document.head.appendChild(script);
  } else {
    criarEditorQuill();
  }
}

function criarEditorQuill() {
  const container = document.getElementById('editor-container');
  if (!container) return;
  
  // Limpar conteúdo anterior
  container.innerHTML = '';
  
  // Configurar toolbar personalizada com botão de variáveis
  const toolbarOptions = [
    ['bold', 'italic', 'underline', 'strike'],        // formatação básica
    [{ 'list': 'ordered'}, { 'list': 'bullet' }],     // listas
    [{ 'header': [1, 2, 3, false] }],                 // cabeçalhos
    [{ 'align': [] }],                                // alinhamento
    ['link', 'image'],                                // mídia
    ['clean'],                                        // limpar formatação
    ['variable']                                      // botão personalizado para variáveis
  ];
  
  // Criar o editor
  quillEditor = new Quill(container, {
    theme: 'snow',
    modules: {
      toolbar: {
        container: toolbarOptions,
        handlers: {
          'variable': function() {
            inserirVariavelNoEditor();
          }
        }
      }
    },
    placeholder: 'Digite o conteúdo do documento... Use {nome_variavel} para variáveis dinâmicas.',
  });
  
  // Adicionar ícone SVG personalizado para o botão de variáveis
  const variableButton = container.querySelector('.ql-variable');
  if (variableButton) {
    // Criar SVG para o ícone de variável
    const svgIcon = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" stroke-width="2"/>
        <path d="M8 8H16V16H8V8Z" fill="currentColor"/>
        <path d="M10 10H14V14H10V10Z" fill="white"/>
      </svg>
    `;
    variableButton.innerHTML = svgIcon;
    variableButton.title = 'Inserir variável (Ctrl+Shift+V)';
    variableButton.style.cssText = `
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 4px;
      border-radius: 4px;
      transition: background-color 0.2s;
    `;
    
    // Adicionar efeito hover
    variableButton.onmouseenter = () => {
      variableButton.style.backgroundColor = 'var(--surface2)';
    };
    variableButton.onmouseleave = () => {
      variableButton.style.backgroundColor = '';
    };
  }
  
  // Adicionar atalho de teclado Ctrl+Shift+V para inserir variável
  quillEditor.root.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.shiftKey && e.key === 'V') {
      e.preventDefault();
      inserirVariavelNoEditor();
    }
  });
  
  // Atualizar variáveis detectadas quando o conteúdo muda
  quillEditor.on('text-change', () => {
    atualizarVariaveisDetectadas();
  });
  
  // Monitorar mudanças no conteúdo para detectar variáveis
  quillEditor.on('text-change', function() {
    atualizarVariaveisDetectadas();
  });
}

/**
 * Alterna entre os modos PDF e HTML no formulário
 */
function alternarTipoConteudoDocumento() {
  const tipoConteudo = document.getElementById('doc-tipo-conteudo').value;
  const secaoPdf = document.getElementById('secao-pdf');
  const secaoHtml = document.getElementById('secao-html');
  const arquivoObrigatorio = document.getElementById('doc-arquivo-obrigatorio');
  const htmlObrigatorio = document.getElementById('doc-html-obrigatorio');
  const btnPreview = document.getElementById('btn-preview-doc');
  
  if (tipoConteudo === 'pdf') {
    secaoPdf.style.display = 'flex';
    secaoHtml.style.display = 'none';
    arquivoObrigatorio.style.display = 'inline';
    htmlObrigatorio.style.display = 'none';
    
    // Ocultar botão de preview para PDF
    if (btnPreview) {
      btnPreview.style.display = 'none';
    }
    
    // Inicializar o editor se ainda não foi inicializado (para quando alternar para HTML depois)
    if (!quillEditor) {
      inicializarEditorQuill();
    }
  } else {
    secaoPdf.style.display = 'none';
    secaoHtml.style.display = 'flex';
    arquivoObrigatorio.style.display = 'none';
    htmlObrigatorio.style.display = 'inline';
    
    // Mostrar botão de preview para HTML
    if (btnPreview) {
      btnPreview.style.display = 'flex';
    }
    
    // Inicializar o editor se necessário
    inicializarEditorQuill();
  }
}

/**
 * Extrai variáveis do conteúdo do editor
 */
function extrairVariaveisDoConteudo(conteudo) {
  if (!conteudo) return [];
  
  // Padrão para encontrar variáveis no formato {nome_variavel}
  const padrao = /\{([a-zA-Z0-9_\-]+)\}/g;
  const matches = [];
  let match;
  
  while ((match = padrao.exec(conteudo)) !== null) {
    if (!matches.includes(match[1])) {
      matches.push(match[1]);
    }
  }
  
  return matches;
}

/**
 * Atualiza a exibição de variáveis detectadas
 */
function atualizarVariaveisDetectadas() {
  if (!quillEditor) return;
  
  const conteudo = quillEditor.root.innerHTML;
  const variaveis = extrairVariaveisDoConteudo(conteudo);
  const container = document.getElementById('variaveis-detectadas');
  
  if (!container) return;
  
  if (variaveis.length === 0) {
    container.innerHTML = '<span style="color:var(--muted)">Nenhuma variável detectada</span>';
    document.getElementById('doc-variaveis-suportadas').value = '';
  } else {
    container.innerHTML = `<strong>Variáveis detectadas (${variaveis.length}):</strong> ${variaveis.map(v => `<code>{${v}}</code>`).join(', ')}`;
    
    // Atualizar campo oculto com variáveis suportadas (formato JSON)
    document.getElementById('doc-variaveis-suportadas').value = JSON.stringify(variaveis);
  }
}

/**
 * Insere uma variável no editor
 */
function inserirVariavelNoEditor() {
  if (!quillEditor) return;
  
  // Lista de variáveis comuns organizadas por categoria
  const variaveisPorCategoria = [
    {
      categoria: 'Cliente',
      variaveis: [
        { nome: 'nome_cliente', descricao: 'Nome do cliente' },
        { nome: 'email_cliente', descricao: 'E-mail do cliente' },
        { nome: 'telefone_cliente', descricao: 'Telefone do cliente' },
        { nome: 'cpf_cliente', descricao: 'CPF do cliente' },
        { nome: 'cnpj_cliente', descricao: 'CNPJ do cliente' },
        { nome: 'endereco_cliente', descricao: 'Endereço do cliente' },
        { nome: 'cidade_cliente', descricao: 'Cidade do cliente' },
        { nome: 'estado_cliente', descricao: 'Estado do cliente' },
      ]
    },
    {
      categoria: 'Orçamento',
      variaveis: [
        { nome: 'valor_orcamento', descricao: 'Valor total do orçamento' },
        { nome: 'data_orcamento', descricao: 'Data do orçamento' },
        { nome: 'numero_orcamento', descricao: 'Número do orçamento' },
        { nome: 'descricao_servico', descricao: 'Descrição do serviço' },
        { nome: 'prazo_entrega', descricao: 'Prazo de entrega' },
        { nome: 'forma_pagamento', descricao: 'Forma de pagamento' },
        { nome: 'parcelas', descricao: 'Número de parcelas' },
        { nome: 'valor_parcela', descricao: 'Valor da parcela' },
      ]
    },
    {
      categoria: 'Empresa',
      variaveis: [
        { nome: 'nome_empresa', descricao: 'Nome da empresa' },
        { nome: 'telefone_empresa', descricao: 'Telefone da empresa' },
        { nome: 'email_empresa', descricao: 'E-mail da empresa' },
        { nome: 'site_empresa', descricao: 'Site da empresa' },
        { nome: 'endereco_empresa', descricao: 'Endereço da empresa' },
        { nome: 'cnpj_empresa', descricao: 'CNPJ da empresa' },
      ]
    },
    {
      categoria: 'Data/Hora',
      variaveis: [
        { nome: 'data_atual', descricao: 'Data atual (dd/mm/aaaa)' },
        { nome: 'hora_atual', descricao: 'Hora atual (hh:mm)' },
        { nome: 'data_vencimento', descricao: 'Data de vencimento' },
        { nome: 'data_assinatura', descricao: 'Data da assinatura' },
      ]
    },
    {
      categoria: 'Assinaturas',
      variaveis: [
        { nome: 'assinatura_cliente', descricao: 'Assinatura do cliente' },
        { nome: 'assinatura_responsavel', descricao: 'Assinatura do responsável' },
        { nome: 'nome_responsavel', descricao: 'Nome do responsável' },
        { nome: 'cargo_responsavel', descricao: 'Cargo do responsável' },
      ]
    }
  ];
  
  // Criar menu de seleção
  const menu = document.createElement('div');
  menu.id = 'variaveis-dropdown-menu';
  menu.style.cssText = `
    position: absolute;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.15);
    z-index: 10000;
    max-height: 400px;
    overflow-y: auto;
    padding: 0;
    min-width: 320px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  `;
  
  // Adicionar cabeçalho
  const header = document.createElement('div');
  header.style.cssText = `
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    background: var(--surface2);
    font-weight: 600;
    font-size: 14px;
    color: var(--text);
    display: flex;
    justify-content: space-between;
    align-items: center;
  `;
  header.innerHTML = `
    <span>Inserir variável</span>
    <small style="font-weight: normal; color: var(--muted); font-size: 12px;">Clique para inserir</small>
  `;
  menu.appendChild(header);
  
  // Adicionar categorias e variáveis
  variaveisPorCategoria.forEach(categoria => {
    // Cabeçalho da categoria
    const catHeader = document.createElement('div');
    catHeader.style.cssText = `
      padding: 8px 16px;
      background: var(--surface2);
      font-weight: 600;
      font-size: 12px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      border-top: 1px solid var(--border);
      border-bottom: 1px solid var(--border);
      margin-top: 8px;
    `;
    catHeader.textContent = categoria.categoria;
    menu.appendChild(catHeader);
    
    // Variáveis da categoria
    categoria.variaveis.forEach(variavel => {
      const option = document.createElement('div');
      option.style.cssText = `
        padding: 10px 16px;
        cursor: pointer;
        font-size: 14px;
        color: var(--text);
        transition: all 0.2s;
        border-bottom: 1px solid var(--border-light);
        display: flex;
        align-items: center;
        gap: 12px;
      `;
      
      // Ícone da variável
      const icon = document.createElement('div');
      icon.style.cssText = `
        width: 24px;
        height: 24px;
        border-radius: 4px;
        background: var(--primary-light);
        color: var(--primary);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        font-weight: 600;
      `;
      icon.textContent = '{ }';
      
      // Conteúdo da variável
      const content = document.createElement('div');
      content.style.cssText = `
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 2px;
      `;
      
      const varName = document.createElement('div');
      varName.style.cssText = `
        font-weight: 600;
        font-size: 13px;
        color: var(--text);
      `;
      varName.textContent = `{${variavel.nome}}`;
      
      const varDesc = document.createElement('div');
      varDesc.style.cssText = `
        font-size: 12px;
        color: var(--muted);
      `;
      varDesc.textContent = variavel.descricao;
      
      content.appendChild(varName);
      content.appendChild(varDesc);
      
      option.appendChild(icon);
      option.appendChild(content);
      
      // Efeitos de hover
      option.onmouseenter = () => {
        option.style.background = 'var(--surface2)';
        option.style.transform = 'translateX(2px)';
      };
      option.onmouseleave = () => {
        option.style.background = '';
        option.style.transform = '';
      };
      
      option.onclick = (e) => {
        e.stopPropagation();
        // Inserir variável no editor
        const range = quillEditor.getSelection();
        const index = range ? range.index : quillEditor.getLength();
        quillEditor.insertText(index, `{${variavel.nome}}`);
        quillEditor.focus();
        
        // Destacar a variável inserida brevemente
        quillEditor.setSelection(index, variavel.nome.length + 2);
        setTimeout(() => {
          quillEditor.setSelection(index + variavel.nome.length + 2, 0);
        }, 500);
        
        // Fechar menu
        document.body.removeChild(menu);
        document.removeEventListener('click', closeMenu);
      };
      
      menu.appendChild(option);
    });
  });
  
  // Adicionar rodapé com instruções
  const footer = document.createElement('div');
  footer.style.cssText = `
    padding: 8px 16px;
    border-top: 1px solid var(--border);
    background: var(--surface2);
    font-size: 11px;
    color: var(--muted);
    text-align: center;
  `;
  footer.textContent = 'As variáveis serão substituídas automaticamente ao usar o documento';
  menu.appendChild(footer);
  
  // Posicionar menu próximo ao botão de variáveis
  const variableButton = document.querySelector('.ql-variable');
  if (variableButton) {
    const rect = variableButton.getBoundingClientRect();
    const viewportHeight = window.innerHeight;
    
    // Verificar se há espaço abaixo do botão
    const spaceBelow = viewportHeight - rect.bottom;
    const menuHeight = 400; // altura aproximada do menu
    
    if (spaceBelow < menuHeight && rect.top > menuHeight) {
      // Colocar acima do botão se não houver espaço abaixo
      menu.style.top = (rect.top + window.scrollY - menuHeight - 5) + 'px';
    } else {
      // Colocar abaixo do botão
      menu.style.top = (rect.bottom + window.scrollY + 5) + 'px';
    }
    
    menu.style.left = (rect.left + window.scrollX) + 'px';
  } else {
    // Posição padrão (centro da tela)
    menu.style.top = '50%';
    menu.style.left = '50%';
    menu.style.transform = 'translate(-50%, -50%)';
  }
  
  // Fechar menu ao clicar fora
  const closeMenu = (e) => {
    if (!menu.contains(e.target) && e.target !== variableButton && !e.target.closest('.ql-variable')) {
      if (document.body.contains(menu)) {
        document.body.removeChild(menu);
      }
      document.removeEventListener('click', closeMenu);
    }
  };
  
  // Fechar ao pressionar ESC
  const closeOnEsc = (e) => {
    if (e.key === 'Escape') {
      if (document.body.contains(menu)) {
        document.body.removeChild(menu);
      }
      document.removeEventListener('keydown', closeOnEsc);
      document.removeEventListener('click', closeMenu);
    }
  };
  
  document.body.appendChild(menu);
  setTimeout(() => {
    document.addEventListener('click', closeMenu);
    document.addEventListener('keydown', closeOnEsc);
  }, 10);
  
  // Focar no menu para navegação por teclado
  setTimeout(() => {
    menu.focus();
  }, 50);
}

/**
 * Obtém o conteúdo HTML do editor
 */
function obterConteudoHtmlEditor() {
  if (!quillEditor) return '';
  return quillEditor.root.innerHTML;
}

/**
 * Define o conteúdo HTML no editor
 */
function definirConteudoHtmlEditor(html) {
  if (!quillEditor) {
    // Tentar inicializar se não estiver inicializado
    inicializarEditorQuill();
    // Aguardar um pouco para o editor ser criado
    setTimeout(() => {
      if (quillEditor) {
        quillEditor.root.innerHTML = html || '';
        atualizarVariaveisDetectadas();
      }
    }, 100);
  } else {
    quillEditor.root.innerHTML = html || '';
    atualizarVariaveisDetectadas();
  }
}

/**
 * Abre uma janela de preview do documento HTML
 */
function abrirPreviewDocumento() {
  if (!quillEditor) {
    mostrarNotificacao('Erro', 'Editor não inicializado', 'error');
    return;
  }
  
  const conteudoHtml = obterConteudoHtmlEditor();
  if (!conteudoHtml || conteudoHtml.trim() === '') {
    mostrarNotificacao('Aviso', 'O documento está vazio', 'warning');
    return;
  }
  
  // Extrair variáveis do conteúdo
  const variaveis = extrairVariaveisDoConteudo(conteudoHtml);
  
  // Criar modal de preview
  const modalPreview = document.createElement('div');
  modalPreview.id = 'modal-preview-documento';
  modalPreview.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.7);
    z-index: 10000;
    display: flex;
    align-items: center;
    justify-content: center;
    animation: fadeIn 0.2s ease;
  `;
  
  const previewContent = document.createElement('div');
  previewContent.style.cssText = `
    background: var(--surface);
    border-radius: 12px;
    width: 90%;
    max-width: 900px;
    height: 90%;
    max-height: 800px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
  `;
  
  // Cabeçalho do preview
  const header = document.createElement('div');
  header.style.cssText = `
    padding: 16px 24px;
    border-bottom: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--surface2);
  `;
  
  const title = document.createElement('div');
  title.style.cssText = `
    font-weight: 600;
    font-size: 18px;
    color: var(--text);
    display: flex;
    align-items: center;
    gap: 10px;
  `;
  title.innerHTML = `
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 4.5C7 4.5 2.73 7.61 1 12C2.73 16.39 7 19.5 12 19.5C17 19.5 21.27 16.39 23 12C21.27 7.61 17 4.5 12 4.5ZM12 17C9.24 17 7 14.76 7 12C7 9.24 9.24 7 12 7C14.76 7 17 9.24 17 12C17 14.76 14.76 17 12 17ZM12 9C10.34 9 9 10.34 9 12C9 13.66 10.34 15 12 15C13.66 15 15 13.66 15 12C15 10.34 13.66 9 12 9Z" fill="currentColor"/>
    </svg>
    Preview do Documento
  `;
  
  const closeBtn = document.createElement('button');
  closeBtn.style.cssText = `
    background: none;
    border: none;
    color: var(--text);
    font-size: 24px;
    cursor: pointer;
    padding: 4px;
    border-radius: 4px;
    transition: background 0.2s;
  `;
  closeBtn.innerHTML = '&times;';
  closeBtn.onclick = () => {
    document.body.removeChild(modalPreview);
  };
  closeBtn.onmouseenter = () => {
    closeBtn.style.background = 'var(--surface3)';
  };
  closeBtn.onmouseleave = () => {
    closeBtn.style.background = '';
  };
  
  header.appendChild(title);
  header.appendChild(closeBtn);
  
  // Corpo do preview com abas
  const body = document.createElement('div');
  body.style.cssText = `
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  `;
  
  // Abas
  const tabs = document.createElement('div');
  tabs.style.cssText = `
    display: flex;
    border-bottom: 1px solid var(--border);
    background: var(--surface2);
  `;
  
  const tabPreview = document.createElement('button');
  tabPreview.style.cssText = `
    padding: 12px 24px;
    background: var(--surface);
    border: none;
    border-bottom: 2px solid var(--primary);
    color: var(--text);
    font-weight: 600;
    cursor: pointer;
    font-size: 14px;
  `;
  tabPreview.textContent = 'Visualização';
  
  const tabVariables = document.createElement('button');
  tabVariables.style.cssText = `
    padding: 12px 24px;
    background: var(--surface2);
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--muted);
    font-weight: 600;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.2s;
  `;
  tabVariables.textContent = `Variáveis (${variaveis.length})`;
  
  tabs.appendChild(tabPreview);
  tabs.appendChild(tabVariables);
  
  // Conteúdo das abas
  const tabContent = document.createElement('div');
  tabContent.style.cssText = `
    flex: 1;
    overflow: hidden;
    position: relative;
  `;
  
  // Conteúdo da aba de preview
  const previewTab = document.createElement('div');
  previewTab.id = 'preview-tab-content';
  previewTab.style.cssText = `
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    overflow: auto;
    padding: 24px;
    background: white;
  `;
  
  // Adicionar estilos básicos para o conteúdo HTML
  const styledContent = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <style>
        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          line-height: 1.6;
          color: #333;
          max-width: 800px;
          margin: 0 auto;
          padding: 20px;
        }
        h1, h2, h3 {
          color: #2c3e50;
          margin-top: 1.5em;
          margin-bottom: 0.5em;
        }
        p {
          margin-bottom: 1em;
        }
        ul, ol {
          margin-bottom: 1em;
          padding-left: 2em;
        }
        strong {
          font-weight: 600;
        }
        em {
          font-style: italic;
        }
        .variable {
          background: #fff3cd;
          border: 1px solid #ffeaa7;
          border-radius: 4px;
          padding: 2px 6px;
          font-family: monospace;
          color: #e17055;
          font-weight: 600;
        }
        .document-header {
          border-bottom: 2px solid #3498db;
          padding-bottom: 20px;
          margin-bottom: 30px;
        }
      </style>
    </head>
    <body>
      <div class="document-header">
        <h1>Preview do Documento</h1>
        <p style="color: #7f8c8d; font-size: 14px;">
          As variáveis aparecem destacadas em amarelo. Elas serão substituídas automaticamente ao usar o documento.
        </p>
      </div>
      ${conteudoHtml.replace(
        /\{([a-zA-Z0-9_\-]+)\}/g,
        '<span class="variable">{$1}</span>'
      )}
    </body>
    </html>
  `;
  
  previewTab.innerHTML = styledContent;
  
  // Conteúdo da aba de variáveis
  const variablesTab = document.createElement('div');
  variablesTab.id = 'variables-tab-content';
  variablesTab.style.cssText = `
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    overflow: auto;
    padding: 24px;
    background: var(--surface);
    display: none;
  `;
  
  if (variaveis.length === 0) {
    variablesTab.innerHTML = `
      <div style="text-align: center; padding: 40px 20px; color: var(--muted);">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-bottom: 16px;">
          <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" stroke-width="2"/>
          <path d="M8 8H16V16H8V8Z" fill="currentColor"/>
          <path d="M10 10H14V14H10V10Z" fill="var(--surface)"/>
        </svg>
        <h3 style="margin-bottom: 8px;">Nenhuma variável detectada</h3>
        <p>Use o botão "{ }" na toolbar para inserir variáveis no documento.</p>
      </div>
    `;
  } else {
    let variablesHtml = `
      <h3 style="margin-bottom: 20px; color: var(--text);">Variáveis detectadas (${variaveis.length})</h3>
      <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 16px;">
    `;
    
    variaveis.forEach(variavel => {
      variablesHtml += `
        <div style="background: var(--surface2); border-radius: 8px; padding: 16px; border: 1px solid var(--border);">
          <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
            <div style="width: 32px; height: 32px; border-radius: 6px; background: var(--primary-light); color: var(--primary); display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 14px;">
              { }
            </div>
            <div>
              <div style="font-weight: 600; color: var(--text); font-family: monospace; font-size: 15px;">{${variavel}}</div>
              <div style="font-size: 12px; color: var(--muted);">Variável dinâmica</div>
            </div>
          </div>
          <div style="font-size: 13px; color: var(--text); margin-top: 8px;">
            Esta variável será substituída por dados reais quando o documento for usado.
          </div>
        </div>
      `;
    });
    
    variablesHtml += `
      </div>
      <div style="margin-top: 24px; padding: 16px; background: var(--surface3); border-radius: 8px; border-left: 4px solid var(--primary);">
        <div style="font-weight: 600; color: var(--text); margin-bottom: 8px;">💡 Como usar variáveis</div>
        <div style="font-size: 13px; color: var(--text);">
          <p>As variáveis entre chaves serão automaticamente substituídas quando:</p>
          <ul style="margin-top: 8px; padding-left: 20px;">
            <li>O documento for anexado a um orçamento</li>
            <li>O cliente visualizar o documento no portal</li>
            <li>O documento for enviado por e-mail</li>
          </ul>
        </div>
      </div>
    `;
    
    variablesTab.innerHTML = variablesHtml;
  }
  
  tabContent.appendChild(previewTab);
  tabContent.appendChild(variablesTab);
  
  // Adicionar funcionalidade de troca de abas
  tabPreview.onclick = () => {
    tabPreview.style.background = 'var(--surface)';
    tabPreview.style.borderBottomColor = 'var(--primary)';
    tabPreview.style.color = 'var(--text)';
    
    tabVariables.style.background = 'var(--surface2)';
    tabVariables.style.borderBottomColor = 'transparent';
    tabVariables.style.color = 'var(--muted)';
    
    previewTab.style.display = 'block';
    variablesTab.style.display = 'none';
  };
  
  tabVariables.onclick = () => {
    tabVariables.style.background = 'var(--surface)';
    tabVariables.style.borderBottomColor = 'var(--primary)';
    tabVariables.style.color = 'var(--text)';
    
    tabPreview.style.background = 'var(--surface2)';
    tabPreview.style.borderBottomColor = 'transparent';
    tabPreview.style.color = 'var(--muted)';
    
    previewTab.style.display = 'none';
    variablesTab.style.display = 'block';
  };
  
  // Rodapé
  const footer = document.createElement('div');
  footer.style.cssText = `
    padding: 16px 24px;
    border-top: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--surface2);
  `;
  
  const info = document.createElement('div');
  info.style.cssText = `
    font-size: 13px;
    color: var(--muted);
  `;
  info.innerHTML = `
    <div style="display: flex; align-items: center; gap: 8px;">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z" stroke="currentColor" stroke-width="2"/>
        <path d="M12 16V12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <path d="M12 8H12.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
      Esta é uma visualização estática. As variáveis serão substituídas dinamicamente.
    </div>
  `;
  
  const closeButton = document.createElement('button');
  closeButton.style.cssText = `
    padding: 10px 20px;
    background: var(--primary);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
  `;
  closeButton.textContent = 'Fechar Preview';
  closeButton.onclick = () => {
    document.body.removeChild(modalPreview);
  };
  closeButton.onmouseenter = () => {
    closeButton.style.background = 'var(--primary-dark)';
  };
  closeButton.onmouseleave = () => {
    closeButton.style.background = 'var(--primary)';
  };
  
  footer.appendChild(info);
  footer.appendChild(closeButton);
  
  // Montar a estrutura
  body.appendChild(tabs);
  body.appendChild(tabContent);
  
  previewContent.appendChild(header);
  previewContent.appendChild(body);
  previewContent.appendChild(footer);
  
  modalPreview.appendChild(previewContent);
  document.body.appendChild(modalPreview);
  
  // Fechar com ESC
  const closeOnEsc = (e) => {
    if (e.key === 'Escape') {
      document.body.removeChild(modalPreview);
      document.removeEventListener('keydown', closeOnEsc);
    }
  };
  document.addEventListener('keydown', closeOnEsc);
  
  // Focar no botão de fechar
  setTimeout(() => {
    closeButton.focus();
  }, 100);
}

/**
 * Limpa o formulário do documento incluindo o editor
 */
function _limparFormDocumento() {
  documentoEditandoId = null;
  document.getElementById('modal-doc-title').textContent = '📎 Novo documento';
  document.getElementById('doc-nome').value = '';
  document.getElementById('doc-tipo').value = 'certificado_garantia';
  document.getElementById('doc-versao').value = '';
  document.getElementById('doc-status').value = 'ativo';
  document.getElementById('doc-descricao').value = '';
  document.getElementById('doc-permite-download').checked = true;
  document.getElementById('doc-visivel-portal').checked = true;
  document.getElementById('doc-tipo-conteudo').value = 'pdf';
  document.getElementById('doc-arquivo').value = '';
  document.getElementById('doc-arquivo-info').textContent = '';
  document.getElementById('btn-trocar-arquivo').style.display = 'none';
  document.getElementById('doc-variaveis-suportadas').value = '';
  
  // Limpar editor
  if (quillEditor) {
    quillEditor.root.innerHTML = '';
    atualizarVariaveisDetectadas();
  }
  
  // Resetar para modo PDF
  alternarTipoConteudoDocumento();
}