// ── CLIENTES ─────────────────────────────────────────────────────────────

let todosClientes = [];

async function carregarClientes(busca = '') {
  const tbody = document.getElementById('clientes-tbody');
  tbody.innerHTML = `<tr><td colspan="6"><div class="loading"><div class="spinner"></div> Carregando...</div></td></tr>`;

  try {
    const endpoint = busca ? `/clientes/?nome=${encodeURIComponent(busca)}` : '/clientes/';
    todosClientes = await api.get(endpoint);
    renderizarClientes(todosClientes);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><div class="icon">⚠️</div><div class="title">Erro ao carregar</div><div class="desc">${escapeHtml(err?.message || '')}</div></div></td></tr>`;
  }
}

function renderizarClientes(clientes) {
  const tbody = document.getElementById('clientes-tbody');

  renderizarClientesCards(clientes);

  if (!clientes.length) {
    tbody.innerHTML = `<tr><td colspan="6">
      <div class="empty-state">
        <div class="icon">👥</div>
        <div class="title">Nenhum cliente ainda</div>
        <div class="desc">Clique em "Novo Cliente" para cadastrar o primeiro.</div>
      </div>
    </td></tr>`;
    return;
  }

  tbody.innerHTML = clientes.map(c => {
    const endExibir = _enderecoResumido(c);
    const docExibir = c.tipo_pessoa === 'PJ'
      ? escapeHtml(c.cnpj || '—')
      : escapeHtml(c.cpf  || '—');
    return `
    <tr>
      <td>
        <div class="client-cell">
          <div class="client-avatar" style="background:${corAvatar(c.nome)}">${iniciaisDe(c.nome)}</div>
          <div>
            <div class="client-name">${escapeHtml(c.nome || '')}</div>
            <div class="client-service">${escapeHtml(c.email || '—')}</div>
          </div>
        </div>
      </td>
      <td class="col-hide-mobile" style="color:var(--muted);font-size:12px">
        ${c.tipo_pessoa === 'PJ' ? '<span style="font-size:10px;background:var(--green-dim);color:var(--green);padding:2px 6px;border-radius:6px;margin-right:4px">PJ</span>' : ''}
        ${docExibir}
      </td>
      <td class="col-hide-mobile" style="color:var(--muted)">${escapeHtml(c.telefone || '—')}</td>
      <td class="col-hide-mobile" style="color:var(--muted);font-size:12px">${endExibir}</td>
      <td class="col-hide-mobile" style="color:var(--muted);font-size:12px">${formatarData(c.criado_em)}</td>
      <td>
        <button class="action-btn" onclick="abrirModalEditar(${c.id})">✏️ Editar</button>
        <button class="action-btn send" onclick="novoOrcamentoCliente(${c.id}, '${String(c.nome || '').replace(/\\/g, '\\\\').replace(/\r/g, ' ').replace(/\n/g, ' ').replace(/'/g, "\\'")}')">📋 Orçamento</button>
      </td>
    </tr>`;
  }).join('');
}

/** Monta string de endereço legível para a tabela */
function _enderecoResumido(c) {
  if (c.logradouro) {
    const partes = [c.logradouro, c.numero, c.complemento].filter(Boolean).map(v => escapeHtml(v));
    const linha1 = partes.join(', ');
    const linha2 = [c.bairro, c.cidade, c.estado].filter(Boolean).map(v => escapeHtml(v)).join(' — ');
    return [linha1, linha2].filter(Boolean).join('<br>');
  }
  return escapeHtml(c.endereco || '—');
}

// ── MODAL NOVO/EDITAR CLIENTE ─────────────────────────────────────────────

let clienteEditandoId = null;

function abrirModalNovoCliente() {
  clienteEditandoId = null;
  document.getElementById('modal-cliente-title').textContent = '👤 Novo Cliente';
  document.getElementById('btn-salvar-cliente').textContent  = 'Salvar Cliente';
  limparFormCliente();
  selecionarTipoPessoa('PF');
  document.getElementById('modal-cliente').classList.add('open');
}

function abrirModalEditar(clienteId) {
  const cliente = todosClientes.find(c => c.id === clienteId);
  if (!cliente) return;
  clienteEditandoId = cliente.id;
  document.getElementById('modal-cliente-title').textContent = '✏️ Editar Cliente';
  document.getElementById('btn-salvar-cliente').textContent  = 'Atualizar Cliente';

  document.getElementById('cli-nome').value       = cliente.nome        || '';
  document.getElementById('cli-telefone').value   = cliente.telefone    || '';
  document.getElementById('cli-email').value      = cliente.email       || '';
  document.getElementById('cli-obs').value        = cliente.observacoes || '';

  // Endereço estruturado
  document.getElementById('cli-cep').value        = cliente.cep         || '';
  document.getElementById('cli-logradouro').value = cliente.logradouro  || '';
  document.getElementById('cli-numero').value     = cliente.numero      || '';
  document.getElementById('cli-complemento').value= cliente.complemento || '';
  document.getElementById('cli-bairro').value     = cliente.bairro      || '';
  document.getElementById('cli-cidade').value     = cliente.cidade      || '';
  document.getElementById('cli-estado').value     = cliente.estado      || '';

  // Campos fiscais
  const tipo = cliente.tipo_pessoa || 'PF';
  selecionarTipoPessoa(tipo);
  document.getElementById('cli-cpf').value          = cliente.cpf                 || '';
  document.getElementById('cli-cnpj').value         = cliente.cnpj                || '';
  document.getElementById('cli-razao-social').value = cliente.razao_social        || '';
  document.getElementById('cli-nome-fantasia').value= cliente.nome_fantasia       || '';
  document.getElementById('cli-ie').value           = cliente.inscricao_estadual  || '';
  document.getElementById('cli-im').value           = cliente.inscricao_municipal || '';

  _setCepStatus('');
  document.getElementById('modal-cliente').classList.add('open');
}

function fecharModalCliente() {
  document.getElementById('modal-cliente').classList.remove('open');
}

const _CAMPOS_CLIENTE = [
  'cli-nome','cli-telefone','cli-email','cli-obs',
  'cli-cep','cli-logradouro','cli-numero','cli-complemento',
  'cli-bairro','cli-cidade',
  'cli-cpf','cli-cnpj','cli-razao-social','cli-nome-fantasia','cli-ie','cli-im',
];

function limparFormCliente() {
  _CAMPOS_CLIENTE.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  const estado = document.getElementById('cli-estado');
  if (estado) estado.value = '';
  _setCepStatus('');
  _setCnpjStatus('');
  // Fechar seção de dados fiscais
  const secao = document.getElementById('secao-dados-fiscais');
  const icon  = document.getElementById('icon-fiscal');
  if (secao) secao.style.display = 'none';
  if (icon)  icon.textContent = '▶';
}

// ── DADOS FISCAIS COLAPSÁVEL ─────────────────────────────────────────────

function toggleDadosFiscais() {
  const el   = document.getElementById('secao-dados-fiscais');
  const icon = document.getElementById('icon-fiscal');
  const aberto = el.style.display !== 'none';
  el.style.display  = aberto ? 'none' : 'block';
  icon.textContent  = aberto ? '▶' : '▼';
}

// ── TIPO DE PESSOA ────────────────────────────────────────────────────────

function selecionarTipoPessoa(tipo) {
  document.getElementById('cli-tipo-pessoa').value = tipo;

  const btnPF = document.getElementById('btn-pf');
  const btnPJ = document.getElementById('btn-pj');
  const camposPF = document.getElementById('campos-pf');
  const camposPJ = document.getElementById('campos-pj');
  const labelNome = document.getElementById('label-cli-nome');

  if (tipo === 'PJ') {
    // Estilo Ativo PJ
    btnPJ.style.background = 'var(--green)';
    btnPJ.style.color = 'white';
    // Estilo Inativo PF
    btnPF.style.background = 'transparent';
    btnPF.style.color = 'var(--muted)';
    
    camposPF.style.display = 'none';
    camposPJ.style.display = 'block';
    if (labelNome) labelNome.textContent = 'Nome Fantasia *';
  } else {
    // Estilo Ativo PF
    btnPF.style.background = 'var(--green)';
    btnPF.style.color = 'white';
    // Estilo Inativo PJ
    btnPJ.style.background = 'transparent';
    btnPJ.style.color = 'var(--muted)';

    camposPF.style.display = 'block';
    camposPJ.style.display = 'none';
    if (labelNome) labelNome.textContent = 'Nome completo *';
  }
}

// ── MÁSCARAS ──────────────────────────────────────────────────────────────

/** Aplica máscara 00000-000 enquanto digita */
function mascararCep(input) {
  let v = input.value.replace(/\D/g, '').slice(0, 8);
  if (v.length > 5) v = v.slice(0, 5) + '-' + v.slice(5);
  input.value = v;
  _setCepStatus('');

  // Auto-busca ao completar os 9 chars (com traço)
  if (input.value.length === 9) buscarCep();
}

/** Aplica máscara 000.000.000-00 */
function mascararCpf(input) {
  let v = input.value.replace(/\D/g, '').slice(0, 11);
  if (v.length > 9) v = v.slice(0,3) + '.' + v.slice(3,6) + '.' + v.slice(6,9) + '-' + v.slice(9);
  else if (v.length > 6) v = v.slice(0,3) + '.' + v.slice(3,6) + '.' + v.slice(6);
  else if (v.length > 3) v = v.slice(0,3) + '.' + v.slice(3);
  input.value = v;
}

/** Aplica máscara 00.000.000/0000-00 e auto-busca ao completar */
function mascararCnpj(input) {
  const digits = input.value.replace(/\D/g, '').slice(0, 14);
  let v = digits;
  if (v.length > 12) v = v.slice(0,2) + '.' + v.slice(2,5) + '.' + v.slice(5,8) + '/' + v.slice(8,12) + '-' + v.slice(12);
  else if (v.length > 8) v = v.slice(0,2) + '.' + v.slice(2,5) + '.' + v.slice(5,8) + '/' + v.slice(8);
  else if (v.length > 5) v = v.slice(0,2) + '.' + v.slice(2,5) + '.' + v.slice(5);
  else if (v.length > 2) v = v.slice(0,2) + '.' + v.slice(2);
  input.value = v;
  _setCnpjStatus('');
  if (digits.length === 14) buscarCnpj();
}

// ── CNPJ AUTO-PREENCHIMENTO ───────────────────────────────────────────────

function _setCnpjStatus(msg, tipo = '') {
  const el = document.getElementById('cnpj-status');
  if (!el) return;
  el.textContent = msg;
  el.style.color = tipo === 'erro' ? '#ef4444'
                 : tipo === 'ok'   ? 'var(--green)'
                 : 'var(--muted)';
}

async function buscarCnpj() {
  const cnpj = document.getElementById('cli-cnpj').value.replace(/\D/g, '');
  if (cnpj.length !== 14) {
    _setCnpjStatus('Digite um CNPJ com 14 dígitos', 'erro');
    return;
  }

  const btn = document.getElementById('btn-buscar-cnpj');
  if (btn) { btn.textContent = '⏳'; btn.disabled = true; }
  _setCnpjStatus('Buscando...', '');

  try {
    const resp = await fetch(`https://brasilapi.com.br/api/cnpj/v1/${cnpj}`);
    if (!resp.ok) {
      _setCnpjStatus('CNPJ não encontrado', 'erro');
      return;
    }
    const d = await resp.json();

    // Razão Social e Nome Fantasia
    if (d.razao_social) document.getElementById('cli-razao-social').value = d.razao_social;
    if (d.nome_fantasia) {
      document.getElementById('cli-nome-fantasia').value = d.nome_fantasia;
      // Preenche o campo nome principal se estiver vazio
      const nomeEl = document.getElementById('cli-nome');
      if (!nomeEl.value.trim()) nomeEl.value = d.nome_fantasia || d.razao_social || '';
    } else if (d.razao_social) {
      const nomeEl = document.getElementById('cli-nome');
      if (!nomeEl.value.trim()) nomeEl.value = d.razao_social;
    }

    // Endereço
    if (d.logradouro)  document.getElementById('cli-logradouro').value  = d.logradouro;
    if (d.numero)      document.getElementById('cli-numero').value      = d.numero;
    if (d.complemento) document.getElementById('cli-complemento').value = d.complemento;
    if (d.bairro)      document.getElementById('cli-bairro').value      = d.bairro;
    if (d.municipio)   document.getElementById('cli-cidade').value      = d.municipio;
    if (d.uf)          document.getElementById('cli-estado').value      = d.uf;
    if (d.cep)         document.getElementById('cli-cep').value         = d.cep.replace(/^(\d{5})(\d{3})$/, '$1-$2');

    // E-mail (se estiver vazio)
    if (d.email) {
      const emailEl = document.getElementById('cli-email');
      if (!emailEl.value.trim()) emailEl.value = d.email;
    }

    _setCnpjStatus('✅ Dados preenchidos!', 'ok');

  } catch {
    _setCnpjStatus('Erro ao consultar CNPJ', 'erro');
  } finally {
    if (btn) { btn.textContent = '🔍'; btn.disabled = false; }
  }
}

// ── CEP ───────────────────────────────────────────────────────────────────

function _setCepStatus(msg, tipo = '') {
  const el = document.getElementById('cep-status');
  if (!el) return;
  el.textContent = msg;
  el.style.color = tipo === 'erro' ? '#ef4444'
                 : tipo === 'ok'   ? 'var(--green)'
                 : 'var(--muted)';
}

async function buscarCep() {
  const cepInput = document.getElementById('cli-cep');
  const cep = cepInput.value.replace(/\D/g, '');

  if (cep.length !== 8) {
    _setCepStatus('Digite um CEP com 8 dígitos', 'erro');
    return;
  }

  const btn = document.getElementById('btn-buscar-cep');
  btn.textContent = '⏳';
  btn.disabled = true;
  _setCepStatus('Buscando...', '');

  try {
    const resp = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
    const data = await resp.json();

    if (data.erro) {
      _setCepStatus('CEP não encontrado', 'erro');
      return;
    }

    // Preenche os campos automaticamente
    document.getElementById('cli-logradouro').value  = data.logradouro  || '';
    document.getElementById('cli-bairro').value      = data.bairro      || '';
    document.getElementById('cli-cidade').value      = data.localidade  || '';
    document.getElementById('cli-estado').value      = data.uf          || '';
    document.getElementById('cli-complemento').value = data.complemento || '';

    _setCepStatus('✅ Endereço preenchido!', 'ok');

    // Foca no campo Número para o usuário completar
    setTimeout(() => document.getElementById('cli-numero').focus(), 100);

  } catch {
    _setCepStatus('Erro ao consultar CEP', 'erro');
  } finally {
    btn.textContent = '🔍';
    btn.disabled = false;
  }
}

// ── SALVAR ────────────────────────────────────────────────────────────────

async function salvarCliente() {
  const nome     = document.getElementById('cli-nome').value.trim();
  const btn      = document.getElementById('btn-salvar-cliente');

  if (!nome) {
    document.getElementById('cli-nome').classList.add('input-error');
    return;
  }

  // Campos de endereço estruturado
  const cep         = document.getElementById('cli-cep').value.trim();
  const logradouro  = document.getElementById('cli-logradouro').value.trim();
  const numero      = document.getElementById('cli-numero').value.trim();
  const complemento = document.getElementById('cli-complemento').value.trim();
  const bairro      = document.getElementById('cli-bairro').value.trim();
  const cidade      = document.getElementById('cli-cidade').value.trim();
  const estado      = document.getElementById('cli-estado').value;

  // Compõe endereco resumido para compatibilidade com PDF e outros sistemas
  const partes = [logradouro, numero, complemento].filter(Boolean);
  const linha1 = partes.join(', ');
  const linha2 = [bairro, cidade, estado].filter(Boolean).join(' — ');
  const endereco = [linha1, linha2].filter(Boolean).join(', ');

  setLoading(btn, true);

  try {
    const payload = {
      nome,
      telefone:    document.getElementById('cli-telefone').value.trim(),
      email:       document.getElementById('cli-email').value.trim(),
      observacoes: document.getElementById('cli-obs').value.trim(),
      endereco,
      cep, logradouro, numero, complemento, bairro, cidade, estado,
      // Campos fiscais
      tipo_pessoa:         document.getElementById('cli-tipo-pessoa').value || 'PF',
      cpf:                 document.getElementById('cli-cpf').value.trim()           || null,
      cnpj:                document.getElementById('cli-cnpj').value.trim()          || null,
      razao_social:        document.getElementById('cli-razao-social').value.trim()  || null,
      nome_fantasia:       document.getElementById('cli-nome-fantasia').value.trim() || null,
      inscricao_estadual:  document.getElementById('cli-ie').value.trim()            || null,
      inscricao_municipal: document.getElementById('cli-im').value.trim()            || null,
    };

    if (clienteEditandoId) {
      await api.put(`/clientes/${clienteEditandoId}`, payload);
      showNotif('✅', 'Cliente atualizado!', nome);
    } else {
      await api.post('/clientes/', payload);
      showNotif('✅', 'Cliente cadastrado!', nome + ' adicionado com sucesso');
    }

    fecharModalCliente();
    await carregarClientes();

  } catch (err) {
    showNotif('❌', 'Erro', err.message, 'error');
  } finally {
    setLoading(btn, false);
  }
}

function novoOrcamentoCliente(clienteId, clienteNome) {
  window.location.href = `index.html?novo_orcamento=1&cliente_id=${clienteId}&cliente_nome=${encodeURIComponent(clienteNome)}`;
}

// ── BUSCA ─────────────────────────────────────────────────────────────────

let buscaTimeout;
function onBuscaCliente(valor) {
  clearTimeout(buscaTimeout);
  buscaTimeout = setTimeout(() => carregarClientes(valor), 350);
}

function renderizarClientesCards(clientes) {
  const container = document.getElementById('clientes-cards-mobile');
  if (!container) return;
  
  if (!clientes.length) {
    container.innerHTML = '';
    return;
  }

  container.innerHTML = clientes.map(c => {
    const docExibir = c.tipo_pessoa === 'PJ' ? (c.cnpj || '—') : (c.cpf || '—');
    const nomeEscapado = String(c.nome || '').replace(/'/g, "\\'");
    
    return `
    <div class="mobile-card" onclick="abrirModalEditar(${c.id})" style="cursor:pointer">
      <div class="mobile-card-header">
        <div class="mobile-card-client">
          <div class="mobile-card-avatar" style="background:${corAvatar(c.nome)}">${iniciaisDe(c.nome)}</div>
          <div class="mobile-card-info">
            <div class="mobile-card-name">${escapeHtml(c.nome || '')}</div>
            <div class="mobile-card-numero">${escapeHtml(c.email || '—')}</div>
          </div>
        </div>
      </div>
      <div class="mobile-card-body">
        <div style="display:flex;flex-direction:column;gap:4px;font-size:12px;color:var(--muted)">
          <div style="display:flex;justify-content:space-between">
            <span>${c.tipo_pessoa === 'PJ' ? 'CNPJ' : 'CPF'}:</span>
            <b style="color:var(--text)">${escapeHtml(docExibir)}</b>
          </div>
          <div style="display:flex;justify-content:space-between">
            <span>WhatsApp:</span>
            <b style="color:var(--text)">${escapeHtml(c.telefone || '—')}</b>
          </div>
        </div>
        <div style="margin-top:12px;display:flex;gap:8px">
          <button class="btn btn-primary" style="flex:1;font-size:11px;padding:8px" onclick="event.stopPropagation();novoOrcamentoCliente(${c.id}, '${nomeEscapado}')">📋 Orçamento</button>
        </div>
      </div>
    </div>`;
  }).join('');
}
