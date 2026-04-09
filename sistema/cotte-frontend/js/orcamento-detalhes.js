// Detalhes de orçamento em modal reutilizável (dashboard + listagem) — v11

const _PAG_LABELS = { pix: 'PIX', a_vista: 'À vista', '2x': '2x sem juros', '3x': '3x sem juros', '4x': '4x sem juros' };

// ── Modal Principal ────────────────────────────────────────────────────────────

async function abrirDetalhesOrcamento(id) {
  let orc = null;
  try {
    const completo = await api.get('/orcamentos/' + id);
    if (typeof orcamentosCache !== 'undefined' && Array.isArray(orcamentosCache)) {
      const idx = orcamentosCache.findIndex(o => o.id === id);
      if (idx >= 0) orcamentosCache[idx] = completo;
      else orcamentosCache.push(completo);
    }
    orc = completo;
  } catch (e) {
    console.warn('Falha ao carregar detalhe completo do orçamento', e);
    return;
  }
  if (!orc) return;

  const bodyEl = document.getElementById('detalhes-body');
  const footerEl = document.getElementById('detalhes-footer');
  const titleEl = document.getElementById('detalhes-titulo');
  const modalEl = document.getElementById('modal-detalhes');
  if (!bodyEl || !footerEl || !titleEl || !modalEl) return;

  titleEl.textContent = '📋 ' + (orc.numero || ('#' + orc.id));

  // Itens
  const itensHtml = (orc.itens || []).map(item => `
    <tr>
      <td style="padding:8px 0;border-bottom:1px solid var(--border);font-size:13px">${escapeHtml(item.descricao || '')}</td>
      <td style="padding:8px 0;border-bottom:1px solid var(--border);font-size:13px;text-align:center;color:var(--muted)">${escapeHtml(String(item.quantidade ?? ''))}x</td>
      <td style="padding:8px 0;border-bottom:1px solid var(--border);font-size:13px;text-align:right;color:var(--muted)">${formatarMoeda(item.valor_unit)}</td>
      <td style="padding:8px 0;border-bottom:1px solid var(--border);font-size:13px;text-align:right;font-weight:600">${formatarMoeda((item.quantidade || 0) * (item.valor_unit || 0))}</td>
    </tr>`).join('');

  // Desconto
  let descontoHtml = '';
  if (orc.desconto > 0) {
    const subtotal = (orc.itens || []).reduce((s, i) => s + i.quantidade * i.valor_unit, 0);
    const descValor = orc.desconto_tipo === 'percentual'
      ? subtotal * (orc.desconto / 100)
      : orc.desconto;
    const label = orc.desconto_tipo === 'percentual'
      ? `Desconto (${orc.desconto}%)`
      : 'Desconto';
    descontoHtml = `
      <div style="display:flex;justify-content:space-between;font-size:13px;color:var(--muted);margin-bottom:4px">
        <span>Subtotal</span><span>${formatarMoeda(subtotal)}</span>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:13px;color:var(--red);margin-bottom:8px">
        <span>${label}</span><span>− ${formatarMoeda(descValor)}</span>
      </div>`;
  }

  // Cards de info
  const cards = [
    { label: 'Cliente',   value: `<strong>${escapeHtml(orc.cliente?.nome || '')}</strong>` },
    { label: 'Status',    value: `<span class="status-badge ${safeClass(orc.status)}">${escapeHtml(orc.status || '')}</span>` },
    { label: 'Criado em', value: formatarData(orc.criado_em) },
    { label: 'Validade',  value: escapeHtml(`${orc.validade_dias} dias`) },
    { label: 'Pagamento', value: escapeHtml(_PAG_LABELS[orc.forma_pagamento] || orc.forma_pagamento || '') },
    { label: 'Número',    value: `<code style="font-size:12px;color:var(--muted)">${escapeHtml(orc.numero || '')}</code>` },
    ...(orc.lembrete_enviado_em ? [{ label: '🔔 Lembrete enviado', value: formatarData(orc.lembrete_enviado_em) }] : []),
  ].map(c => `
    <div style="background:var(--surface2);border:1px solid var(--border);border-radius:10px;padding:12px 14px">
      <div style="font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:5px;font-weight:600">${c.label}</div>
      <div style="font-size:14px">${c.value}</div>
    </div>`).join('');

  bodyEl.innerHTML = `
    <div style="padding-top:20px">
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:20px">
        ${cards}
      </div>
      <div style="margin-bottom:16px">
        <div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:10px;font-weight:600">Itens do orçamento</div>
        <table style="width:100%;border-collapse:collapse">
          <thead>
            <tr style="font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em">
              <th style="text-align:left;padding-bottom:6px;border-bottom:1px solid var(--border)">Descrição</th>
              <th style="text-align:center;padding-bottom:6px;border-bottom:1px solid var(--border)">Qtd</th>
              <th style="text-align:right;padding-bottom:6px;border-bottom:1px solid var(--border)">Unit.</th>
              <th style="text-align:right;padding-bottom:6px;border-bottom:1px solid var(--border)">Total</th>
            </tr>
          </thead>
          <tbody>${itensHtml}</tbody>
        </table>
      </div>
      <div style="background:var(--surface2);border:1px solid var(--border);border-radius:10px;padding:14px 16px;margin-bottom:${orc.observacoes ? '14px' : '20px'}">
        ${descontoHtml}
        <div style="display:flex;justify-content:space-between;font-weight:700;font-size:16px">
          <span>Total</span>
          <span style="color:var(--green)">${formatarMoeda(orc.total)}</span>
        </div>
      </div>
      ${orc.observacoes ? `
      <div style="background:var(--surface2);border:1px solid var(--border);border-radius:10px;padding:12px 14px;margin-bottom:14px">
        <div style="font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px;font-weight:600">Observações</div>
        <div style="font-size:13px;color:var(--muted);line-height:1.6">${escapeHtmlWithBreaks(orc.observacoes)}</div>
      </div>` : ''}
      <div id="detalhes-documentos-section" style="margin-bottom:14px"></div>
      ${orc.status === 'aprovado' ? `
      <div id="pagamentos-section" style="border:1px solid rgba(0,229,160,0.3);border-radius:10px;padding:14px 16px;margin-bottom:20px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
          <div style="font-size:10px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.07em">💰 Pagamentos</div>
          <button id="btn-novo-pagamento" class="btn btn-primary" style="font-size:12px;padding:6px 12px">+ Novo Pagamento</button>
        </div>
        <div id="pagamentos-contas"></div>
        <div id="pagamentos-progresso"></div>
        <div id="pagamentos-historico"></div>
        <div id="pagamentos-form-area"></div>
      </div>` : ''}
    </div>`;

  // Footer de ações
  const num = (orc.numero || '').replace(/'/g, "\\'");
  const temTimeline = typeof abrirTimeline === 'function';
  const temEditar = typeof abrirModalEditarOrcamento === 'function';
  const temWhats = typeof enviarWhatsapp === 'function';
  const temEmail = typeof enviarEmail === 'function';
  const temDuplicar = typeof duplicarOrcamento === 'function';

  let footerHtml = `
    <button class="btn btn-ghost" onclick="fecharDetalhes()" style="margin-right:auto">Fechar</button>`;
  if (temTimeline) {
    footerHtml += `
    <button class="btn btn-ghost" onclick="fecharDetalhes();abrirTimeline(${orc.id},'${num}')" title="Linha do tempo">🕐 Timeline</button>`;
  }
  if (temEditar) {
    footerHtml += `
    <button class="btn btn-ghost" onclick="fecharDetalhes();abrirModalEditarOrcamento(${orc.id})" title="Editar">✏️ Editar</button>`;
  }
  footerHtml += `
    <button class="btn btn-ghost" onclick="window.open('orcamento-view.html?id=${orc.id}','_blank')" title="Ver PDF">📄 PDF</button>`;
  if (temDuplicar) {
    footerHtml += `
    <button class="btn btn-ghost" onclick="fecharDetalhes();duplicarOrcamento(${orc.id})" title="Duplicar orçamento">📋 Duplicar</button>`;
  }
  if (['rascunho', 'enviado'].includes(orc.status) && typeof aprovarOrcamento === 'function') {
    footerHtml += `
    <button class="btn btn-primary" onclick="fecharDetalhes();aprovarOrcamento(${orc.id},'${num}')" title="Aprovar orçamento">✅ Aprovar</button>`;
  }
  if (orc.status === 'aprovado' && typeof atualizarStatusOrcamento === 'function') {
    footerHtml += `
    <button class="btn btn-ghost" style="color:#ef4444" onclick="confirmarDesaprovar(${orc.id},'${num}')" title="Desaprovar orçamento (reverter para rascunho)">↩ Desaprovar</button>`;
  }
  // Botão Agendar (só para aprovados)
  if (orc.status === 'aprovado') {
    footerHtml += `<button class="btn btn-primary" onclick="fecharDetalhes();abrirModalAgendamentoRapido(${orc.id},'${num}','${(orc.cliente_nome || '').replace(/'/g, "\\'")}')" title="Agendar serviço">📅 Agendar</button>`;
  }
  if (typeof abrirModalDocsOrcamento === 'function') {
    footerHtml += `
    <button class="btn btn-ghost" onclick="fecharDetalhes();abrirModalDocsOrcamento(${orc.id})" title="Documentos do orçamento">📎 Docs</button>`;
  }
  if (temWhats) {
    footerHtml += `
    <button class="btn ${['rascunho','enviado'].includes(orc.status) ? 'btn-ghost' : 'btn-primary'}" onclick="fecharDetalhes();enviarWhatsapp(${orc.id})" title="Enviar via WhatsApp">📲 WhatsApp</button>`;
  }
  if (temEmail) {
    footerHtml += `
    <button class="btn btn-ghost" onclick="fecharDetalhes();enviarEmail(${orc.id})" title="Enviar por e-mail">📧 E-mail</button>`;
  }

  footerEl.innerHTML = footerHtml;
  modalEl.classList.add('open');

  // Carregar documentos vinculados
  _carregarDocumentosDetalhes(orc.id);

  // Renderizar progresso, contas e histórico imediatamente
  if (orc.status === 'aprovado') {
    _carregarContasOrcamento(orc.id);
    _renderizarProgressoPagamentos(orc);
    _renderizarHistoricoPagamentos(orc);

    // Botão "+ Novo Pagamento" — toggle do formulário
    document.getElementById('btn-novo-pagamento')?.addEventListener('click', () => {
      const area = document.getElementById('pagamentos-form-area');
      if (!area) return;
      if (area.innerHTML.trim() !== '') {
        area.innerHTML = '';
        document.getElementById('btn-novo-pagamento').textContent = '+ Novo Pagamento';
        return;
      }
      _abrirFormaPagamento(orc);
    });
  }
}

function fecharDetalhes() {
  const modalEl = document.getElementById('modal-detalhes');
  if (modalEl) modalEl.classList.remove('open');
}

// ── Barra de Progresso ────────────────────────────────────────────────────────

function _renderizarProgressoPagamentos(orc) {
  const el = document.getElementById('pagamentos-progresso');
  if (!el) return;
  const pagamentos = orc.pagamentos_financeiros || [];
  const pago = pagamentos.filter(p => p.status === 'confirmado').reduce((s, p) => s + parseFloat(p.valor), 0);
  const total = parseFloat(orc.total || 0);
  const saldo = Math.max(total - pago, 0);
  const pct = total > 0 ? Math.min(Math.round((pago / total) * 100), 100) : 0;

  if (pagamentos.length === 0 && pago === 0) { el.innerHTML = ''; return; }

  const saldoFmt = typeof formatarMoeda === 'function' ? formatarMoeda(saldo) : 'R$ ' + saldo.toFixed(2);
  const pagoFmt  = typeof formatarMoeda === 'function' ? formatarMoeda(pago)  : 'R$ ' + pago.toFixed(2);
  const totFmt   = typeof formatarMoeda === 'function' ? formatarMoeda(total) : 'R$ ' + total.toFixed(2);

  el.innerHTML = `
    <div style="margin-bottom:12px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px">
        <span style="font-size:12px;color:var(--muted)">${pagoFmt} de ${totFmt} · ${pct}% pago</span>
        <span style="font-size:12px;font-weight:700;color:${saldo > 0 ? '#ea580c' : '#10b981'}">
          ${saldo > 0 ? 'Saldo: ' + saldoFmt : '✅ Quitado'}
        </span>
      </div>
      <div style="height:7px;background:var(--surface2);border-radius:4px;overflow:hidden">
        <div style="height:100%;width:${pct}%;background:#00e5a0;border-radius:4px;transition:width .5s ease"></div>
      </div>
    </div>`;
}

// ── Histórico de Pagamentos ────────────────────────────────────────────────────

function _renderizarHistoricoPagamentos(orc) {
  const el = document.getElementById('pagamentos-historico');
  if (!el) return;
  const pagamentos = orc.pagamentos_financeiros || [];
  if (pagamentos.length === 0) { el.innerHTML = ''; return; }

  const tipoLabel = { sinal: 'Sinal', parcela: 'Parcela', quitacao: 'Quitação' };
  const tipoIcon  = { sinal: '🟡', parcela: '🔵', quitacao: '🟢' };

  el.innerHTML = `
    <div style="border-top:1px solid var(--border);padding-top:10px;margin-bottom:10px">
      ${pagamentos.map(p => {
        const label = tipoLabel[p.tipo] || p.tipo || '';
        const icon  = p.status === 'confirmado' ? (tipoIcon[p.tipo] || '💰') : '○';
        const forma = escapeHtml(p.forma_pagamento_nome || 'N/A');
        const data  = p.data_pagamento
          ? p.data_pagamento.slice(0, 10).split('-').reverse().join('/')
          : '';
        const vFmt  = typeof formatarMoeda === 'function' ? formatarMoeda(p.valor) : 'R$ ' + parseFloat(p.valor).toFixed(2);
        const opaco = p.status !== 'confirmado' ? 'opacity:.5;' : '';
        return `
          <div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04);${opaco}">
            <span style="font-size:15px;flex-shrink:0">${icon}</span>
            <div style="flex:1;min-width:0">
              <span style="font-size:13px;font-weight:600;color:var(--text)">${escapeHtml(label)} — ${vFmt}</span>
              <span style="font-size:11px;color:var(--muted);margin-left:6px">${forma} · ${data}</span>
            </div>
            ${p.status === 'estornado' ? '<span style="font-size:10px;padding:2px 7px;border-radius:5px;background:rgba(239,68,68,.15);color:#ef4444">estornado</span>' : ''}
            <div style="position:relative;flex-shrink:0">
              <button class="btn-pag-menu" data-pag-id="${p.id}"
                style="background:none;border:none;color:var(--muted);cursor:pointer;font-size:18px;padding:2px 6px;line-height:1">⋯</button>
              <div class="pag-menu-dropdown" style="display:none;position:absolute;right:0;top:100%;background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:4px 0;min-width:148px;z-index:20;box-shadow:0 4px 16px rgba(0,0,0,.35)">
                ${p.comprovante_url ? `<button class="btn-pag-comprovante" data-url="${escapeHtml(p.comprovante_url)}" style="display:block;width:100%;text-align:left;padding:9px 14px;font-size:12px;background:none;border:none;color:var(--text);cursor:pointer">📎 Ver comprovante</button>` : ''}
                ${p.status === 'confirmado' ? `<button class="btn-pag-estornar" data-pag-id="${p.id}" data-valor="${escapeHtml(vFmt)}" style="display:block;width:100%;text-align:left;padding:9px 14px;font-size:12px;background:none;border:none;color:#ef4444;cursor:pointer">↩ Estornar</button>` : ''}
              </div>
            </div>
          </div>`;
      }).join('')}
    </div>`;

  // Toggle de mini-menu
  el.querySelectorAll('.btn-pag-menu').forEach(btn => {
    btn.addEventListener('click', e => {
      e.stopPropagation();
      const dd = btn.nextElementSibling;
      el.querySelectorAll('.pag-menu-dropdown').forEach(d => { if (d !== dd) d.style.display = 'none'; });
      dd.style.display = dd.style.display === 'none' ? '' : 'none';
    });
  });

  // Fechar menus ao clicar fora
  document.addEventListener('click', () => {
    el.querySelectorAll('.pag-menu-dropdown').forEach(d => d.style.display = 'none');
  }, { once: false, capture: false });

  // Ver comprovante
  el.querySelectorAll('.btn-pag-comprovante').forEach(btn => {
    btn.addEventListener('click', () => window.open(btn.dataset.url, '_blank'));
  });

  // Estornar
  el.querySelectorAll('.btn-pag-estornar').forEach(btn => {
    btn.addEventListener('click', async () => {
      const pagId = btn.dataset.pagId;
      const valorFmt = btn.dataset.valor;
      if (!confirm(`Estornar pagamento de ${valorFmt}? Esta ação não pode ser desfeita.`)) return;
      btn.textContent = 'Estornando...';
      btn.disabled = true;
      try {
        await Financeiro.estornarPagamento(pagId, 'Estorno manual pelo operador');
        if (typeof showToast === 'function') showToast('Pagamento estornado.', 'success');
        await _atualizarCacheOrcamento(orc.id);
        const orcAtualizado = (typeof orcamentosCache !== 'undefined' && Array.isArray(orcamentosCache))
          ? orcamentosCache.find(o => o.id === orc.id) : null;
        if (orcAtualizado) {
          _renderizarProgressoPagamentos(orcAtualizado);
          _renderizarHistoricoPagamentos(orcAtualizado);
        }
      } catch (e) {
        if (typeof showToast === 'function') showToast('Erro ao estornar: ' + e.message, 'error');
        btn.disabled = false;
        btn.textContent = '↩ Estornar';
      }
    });
  });
}

// ── Formulário de Novo Pagamento ──────────────────────────────────────────────

async function _abrirFormaPagamento(orc) {
  const area = document.getElementById('pagamentos-form-area');
  if (!area) return;

  const btnNovo = document.getElementById('btn-novo-pagamento');
  if (btnNovo) btnNovo.textContent = '✕ Cancelar';

  area.innerHTML = `<div style="font-size:12px;color:var(--muted);padding:8px 0">Carregando formas de pagamento...</div>`;

  let formas = [];
  try {
    formas = await Financeiro.listarFormasPagamento();
  } catch (e) {
    area.innerHTML = `<div style="color:var(--red);font-size:12px;padding:8px 0">Erro ao carregar formas de pagamento.</div>`;
    if (btnNovo) btnNovo.textContent = '+ Novo Pagamento';
    return;
  }

  // Calcula saldo devedor
  const pagamentos = orc.pagamentos_financeiros || [];
  const pago = pagamentos.filter(p => p.status === 'confirmado').reduce((s, p) => s + parseFloat(p.valor), 0);
  const total = parseFloat(orc.total || 0);
  const saldo = Math.max(total - pago, 0);
  const temPagAnt = pagamentos.filter(p => p.status === 'confirmado').length > 0;

  const cardsHtml = formas.map(f => `
    <button class="btn-forma-pag" data-forma-id="${f.id}" data-forma-pix="${f.gera_pix_qrcode ? '1' : '0'}"
      role="radio" aria-pressed="false" tabindex="0"
      style="display:flex;flex-direction:column;align-items:center;padding:10px 8px;border:2px solid var(--border);
             border-radius:10px;background:var(--surface2);cursor:pointer;gap:4px;transition:border-color .15s,background .15s;position:relative;outline:none">
      <span style="font-size:22px;line-height:1.2">${f.icone || '💳'}</span>
      <span style="font-weight:600;font-size:11px;color:var(--text);text-align:center;line-height:1.3">${escapeHtml(f.nome)}</span>
      <span class="forma-check" aria-hidden="true"
        style="display:none;position:absolute;top:4px;right:4px;width:16px;height:16px;border-radius:50%;background:#10b981;color:white;font-size:9px;line-height:16px;text-align:center;font-weight:700">✓</span>
    </button>`).join('');

  area.innerHTML = `
    <div style="border-top:1px solid var(--border);padding-top:14px;margin-top:4px">
      <div style="font-size:10px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.07em;margin-bottom:8px">Forma de pagamento</div>
      <div id="formas-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(80px,1fr));gap:8px;margin-bottom:14px">
        ${cardsHtml}
      </div>
      <div id="pag-detalhes" style="display:none">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:8px">
          <div>
            <label for="pag-tipo" style="font-size:10px;color:var(--muted);font-weight:600;display:block;margin-bottom:4px">TIPO</label>
            <select id="pag-tipo" style="width:100%;padding:9px 10px;border:1px solid var(--border);border-radius:8px;background:var(--surface);color:var(--text);font-size:13px">
              <option value="sinal">Sinal / Entrada</option>
              <option value="parcela">Parcela</option>
              <option value="quitacao">Quitação</option>
            </select>
          </div>
          <div>
            <label for="pag-valor" style="font-size:10px;color:var(--muted);font-weight:600;display:block;margin-bottom:4px">VALOR (R$)</label>
            <input id="pag-valor" type="number" min="0.01" step="0.01" placeholder="0,00"
              value="${saldo.toFixed(2)}"
              style="width:100%;padding:9px 10px;border:1px solid var(--border);border-radius:8px;background:var(--surface);color:var(--text);font-size:13px;box-sizing:border-box">
          </div>
        </div>
        <div style="display:flex;gap:6px;margin-bottom:10px">
          <button class="btn-atalho-valor" data-pct="30" tabindex="0"
            style="flex:1;padding:6px 4px;font-size:11px;border:1px solid var(--border);border-radius:6px;background:var(--surface2);color:var(--muted);cursor:pointer">30%</button>
          <button class="btn-atalho-valor" data-pct="50" tabindex="0"
            style="flex:1;padding:6px 4px;font-size:11px;border:1px solid var(--border);border-radius:6px;background:var(--surface2);color:var(--muted);cursor:pointer">50%</button>
          <button class="btn-atalho-valor" data-pct="100" tabindex="0"
            style="flex:1;padding:6px 4px;font-size:11px;border:1px solid var(--border);border-radius:6px;background:var(--surface2);color:var(--muted);cursor:pointer">Saldo total</button>
        </div>
        <div style="margin-bottom:10px">
          <label for="pag-obs" style="font-size:10px;color:var(--muted);font-weight:600;display:block;margin-bottom:4px">OBSERVAÇÃO (opcional)</label>
          <input id="pag-obs" type="text" maxlength="200" placeholder="..."
            style="width:100%;padding:9px 10px;border:1px solid var(--border);border-radius:8px;background:var(--surface);color:var(--text);font-size:13px;box-sizing:border-box">
        </div>
        <div id="pag-pix-area" style="display:none;margin-bottom:10px">
          <div style="background:var(--surface2);border-radius:10px;padding:14px;min-height:60px">
            <div id="pag-qr-loading" style="font-size:12px;color:var(--muted);text-align:center">Gerando QR Code...</div>
            <div id="pag-qr-resultado"></div>
          </div>
        </div>
        <div id="pag-validacao" style="display:none;margin-bottom:10px;padding:8px 12px;border-radius:8px;background:rgba(251,191,36,.1);border:1px solid rgba(251,191,36,.4);font-size:12px;color:#f59e0b"></div>
        <button id="btn-confirmar-pag" class="btn btn-primary" style="width:100%;font-size:14px;padding:11px;font-weight:700;transition:opacity .2s">
          💾 Confirmar e Registrar Pagamento
        </button>
      </div>
    </div>`;

  // ── Responsividade (< 360px → 2 colunas) ────────────────────────────────
  const mq = window.matchMedia('(max-width: 360px)');
  const ajustarGrid = q => {
    const grid = document.getElementById('formas-grid');
    if (grid) grid.style.gridTemplateColumns = q.matches ? '1fr 1fr' : 'repeat(auto-fill,minmax(80px,1fr))';
  };
  ajustarGrid(mq);
  if (mq.addEventListener) mq.addEventListener('change', ajustarGrid);

  // ── Estado interno ───────────────────────────────────────────────────────
  let formaIdSelecionada = null;
  let ehPix = false;
  let qrTimer = null;

  // ── Auto-inferência do tipo ──────────────────────────────────────────────
  function autoInferirTipo() {
    const valor = parseFloat(document.getElementById('pag-valor')?.value) || 0;
    const sel = document.getElementById('pag-tipo');
    if (!sel) return;
    if (!temPagAnt) {
      sel.value = 'sinal';
    } else if (saldo > 0 && Math.abs(valor - saldo) < 0.01) {
      sel.value = 'quitacao';
    } else {
      sel.value = 'parcela';
    }
  }

  // ── Validação valor vs saldo ─────────────────────────────────────────────
  function validarValor() {
    const valor = parseFloat(document.getElementById('pag-valor')?.value) || 0;
    const aviso = document.getElementById('pag-validacao');
    const btn   = document.getElementById('btn-confirmar-pag');
    const saldoFmt = typeof formatarMoeda === 'function' ? formatarMoeda(saldo) : 'R$ ' + saldo.toFixed(2);
    if (valor <= 0) {
      if (aviso) aviso.style.display = 'none';
      if (btn) { btn.disabled = true; btn.style.opacity = '.45'; }
    } else if (valor > saldo + 0.01 && saldo > 0) {
      if (aviso) { aviso.textContent = `Valor excede o saldo restante de ${saldoFmt}`; aviso.style.display = ''; }
      if (btn) { btn.disabled = true; btn.style.opacity = '.45'; }
    } else {
      if (aviso) aviso.style.display = 'none';
      if (btn) { btn.disabled = false; btn.style.opacity = '1'; }
    }
  }

  // ── QR PIX com debounce 500ms ────────────────────────────────────────────
  function gerarQRDebounce() {
    clearTimeout(qrTimer);
    const loading  = document.getElementById('pag-qr-loading');
    const resultado = document.getElementById('pag-qr-resultado');
    if (loading)   { loading.textContent = 'Gerando QR Code...'; loading.style.color = 'var(--muted)'; loading.style.display = ''; }
    if (resultado) resultado.innerHTML = '';

    qrTimer = setTimeout(async () => {
      const valor = parseFloat(document.getElementById('pag-valor')?.value);
      if (!valor || valor <= 0) {
        if (loading) loading.style.display = 'none';
        return;
      }
      try {
        const { qrcode, payload } = await api.post('/orcamentos/' + orc.id + '/pix/gerar', { valor });
        const valorFmt = typeof formatarMoeda === 'function' ? formatarMoeda(valor) : 'R$ ' + valor.toFixed(2);
        if (loading)   loading.style.display = 'none';
        if (resultado) {
          resultado.innerHTML = `
            <div style="display:flex;gap:12px;align-items:center">
              <img src="data:image/png;base64,${qrcode}"
                style="width:100px;height:100px;border-radius:8px;border:2px solid rgba(6,182,212,0.3);background:white;flex-shrink:0">
              <div style="flex:1;min-width:0">
                <div style="font-size:18px;font-weight:700;color:var(--green);margin-bottom:8px">${valorFmt}</div>
                <button id="btn-copiar-pix" class="btn btn-ghost" style="width:100%;font-size:11px">📋 Copiar código PIX</button>
              </div>
            </div>`;
          document.getElementById('btn-copiar-pix')?.addEventListener('click', () => {
            navigator.clipboard.writeText(payload || '').then(() => {
              const c = document.getElementById('btn-copiar-pix');
              if (c) { c.textContent = '✅ Copiado!'; setTimeout(() => { c.textContent = '📋 Copiar código PIX'; }, 2000); }
              if (typeof showToast === 'function') showToast('Código PIX copiado!', 'success');
            });
          });
        }
      } catch (e) {
        if (loading) { loading.textContent = 'Erro ao gerar QR. Verifique a chave PIX em Configurações.'; loading.style.color = 'var(--red)'; loading.style.display = ''; }
        if (resultado) resultado.innerHTML = '';
      }
    }, 500);
  }

  // ── Listeners: cards de forma ────────────────────────────────────────────
  area.querySelectorAll('.btn-forma-pag').forEach(btn => {
    const selecionar = () => {
      area.querySelectorAll('.btn-forma-pag').forEach(b => {
        b.style.borderColor = 'var(--border)';
        b.style.background  = 'var(--surface2)';
        b.setAttribute('aria-pressed', 'false');
        const chk = b.querySelector('.forma-check');
        if (chk) chk.style.display = 'none';
      });
      btn.style.borderColor = 'var(--cor, #06b6d4)';
      btn.style.background  = 'rgba(6,182,212,0.08)';
      btn.setAttribute('aria-pressed', 'true');
      const chk = btn.querySelector('.forma-check');
      if (chk) chk.style.display = '';

      formaIdSelecionada = parseInt(btn.dataset.formaId);
      ehPix = btn.dataset.formaPix === '1';
      document.getElementById('pag-detalhes').style.display = '';
      document.getElementById('pag-pix-area').style.display = ehPix ? '' : 'none';
      autoInferirTipo();
      validarValor();
      if (ehPix) gerarQRDebounce();
    };
    btn.addEventListener('click', selecionar);
    btn.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selecionar(); } });
  });

  // ── Listeners: campo de valor ────────────────────────────────────────────
  document.getElementById('pag-valor')?.addEventListener('input', () => {
    autoInferirTipo();
    validarValor();
    if (ehPix) gerarQRDebounce();
  });

  // ── Listeners: atalhos de valor ──────────────────────────────────────────
  area.querySelectorAll('.btn-atalho-valor').forEach(btn => {
    btn.addEventListener('click', () => {
      const pct = parseInt(btn.dataset.pct);
      const valor = pct === 100 ? saldo : parseFloat((saldo * pct / 100).toFixed(2));
      const input = document.getElementById('pag-valor');
      if (input) input.value = valor.toFixed(2);
      autoInferirTipo();
      validarValor();
      if (ehPix) gerarQRDebounce();
    });
  });

  // Validação inicial (valor pré-preenchido)
  autoInferirTipo();
  validarValor();

  // ── Confirmar pagamento ──────────────────────────────────────────────────
  document.getElementById('btn-confirmar-pag')?.addEventListener('click', async () => {
    if (!formaIdSelecionada) {
      if (typeof showToast === 'function') showToast('Selecione a forma de pagamento', 'error');
      return;
    }
    const valor = parseFloat(document.getElementById('pag-valor')?.value);
    if (!valor || valor <= 0) {
      if (typeof showToast === 'function') showToast('Informe um valor válido', 'error');
      return;
    }
    if (saldo > 0 && valor > saldo + 0.01) {
      if (typeof showToast === 'function') showToast('Valor excede o saldo restante', 'error');
      return;
    }
    const tipo = document.getElementById('pag-tipo')?.value || 'quitacao';
    const observacao = document.getElementById('pag-obs')?.value?.trim() || undefined;
    const btn = document.getElementById('btn-confirmar-pag');
    if (btn) { btn.disabled = true; btn.textContent = 'Registrando...'; btn.style.opacity = '.7'; }

    // Timeout de 15 segundos
    const timeoutId = setTimeout(() => {
      if (btn) { btn.disabled = false; btn.textContent = '💾 Confirmar e Registrar Pagamento'; btn.style.opacity = '1'; }
      if (typeof showToast === 'function') showToast('Falha na conexão, tente novamente', 'error');
    }, 15000);

    const hoje = new Date().toISOString().slice(0, 10);
    try {
      await Financeiro.registrarPagamento({
        orcamento_id: orc.id,
        valor,
        tipo,
        forma_pagamento_id: formaIdSelecionada,
        data_pagamento: hoje,
        observacao,
      });
      clearTimeout(timeoutId);
      if (typeof showToast === 'function') showToast('✅ Pagamento registrado com sucesso!', 'success');

      // Fecha formulário
      area.innerHTML = '';
      if (btnNovo) btnNovo.textContent = '+ Novo Pagamento';

      // Atualiza cache e re-renderiza
      await _atualizarCacheOrcamento(orc.id);
      const orcAtualizado = (typeof orcamentosCache !== 'undefined' && Array.isArray(orcamentosCache))
        ? orcamentosCache.find(o => o.id === orc.id) : null;
      if (orcAtualizado) {
        _renderizarProgressoPagamentos(orcAtualizado);
        _renderizarHistoricoPagamentos(orcAtualizado);
        // Atualiza objeto local para próximos cliques no mesmo modal
        Object.assign(orc, orcAtualizado);
      }
      // Recarrega status das contas geradas na aprovação
      await _carregarContasOrcamento(orc.id);
    } catch (e) {
      clearTimeout(timeoutId);
      if (typeof showToast === 'function') showToast('Erro: ' + e.message, 'error');
      if (btn) { btn.disabled = false; btn.textContent = '💾 Confirmar e Registrar Pagamento'; btn.style.opacity = '1'; }
    }
  });
}

// ── Documentos Vinculados (Modal de Detalhes) ──────────────────────────────────

async function _carregarDocumentosDetalhes(orcId) {
  const el = document.getElementById('detalhes-documentos-section');
  if (!el) return;

  try {
    const docs = await api.get(`/orcamentos/${orcId}/documentos`);
    if (!docs || !docs.length) {
      el.innerHTML = '';
      return;
    }

    const icones = { pdf: '📄', html: '📝' };
    el.innerHTML = `
      <div style="background:var(--surface2);border:1px solid var(--border);border-radius:10px;padding:12px 14px">
        <div style="font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:10px;font-weight:600">📎 Documentos vinculados</div>
        <div style="display:flex;flex-direction:column;gap:8px">
          ${docs.map(d => {
            const icone = icones[d.documento_tipo] || '📄';
            const obrigBadge = d.obrigatorio
              ? '<span style="display:inline-flex;align-items:center;padding:2px 8px;border-radius:99px;font-size:10px;font-weight:700;background:rgba(245,158,11,.12);color:#f59e0b;margin-left:8px">Obrigatório</span>'
              : '';
            
            // Lógica de Sincronização e Versão
            // Nota: d.documento_versao é o snapshot, precisamos da versão atual do template se disponível
            // Por simplicidade nesta fase, vamos adicionar o botão de sincronizar sempre que houver um documento_id
            const syncBtn = d.documento_id 
              ? `<button onclick="sincronizarDocumento(${orcId}, ${d.id}, this)" 
                  title="Sincronizar com a versão mais recente do template"
                  style="background:none;border:none;cursor:pointer;font-size:14px;padding:4px;opacity:0.6;transition:opacity .2s"
                  onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.6'">🔄</button>`
              : '';

            const canais = [];
            if (d.exibir_no_portal) canais.push('🌐 Portal');
            if (d.enviar_por_email) canais.push('📧 E-mail');
            if (d.enviar_por_whatsapp) canais.push('📲 WhatsApp');
            const canaisHtml = canais.length
              ? `<span style="font-size:10px;color:var(--muted2);margin-left:4px">${canais.join(' · ')}</span>`
              : '';
            return `
              <div style="display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:8px;border:1px solid var(--border);background:var(--surface)">
                <span style="font-size:18px;flex-shrink:0">${icone}</span>
                <div style="flex:1;min-width:0">
                  <div style="font-size:13px;font-weight:600;color:var(--text)">${escapeHtml(d.documento_nome || 'Documento')}${obrigBadge}</div>
                  <div style="font-size:11px;color:var(--muted);margin-top:2px">${escapeHtml(d.documento_tipo || '')}${d.documento_versao ? ' · v' + d.documento_versao : ''}${canaisHtml}</div>
                </div>
                ${syncBtn}
                <a href="/o/${d.id}" target="_blank" rel="noopener"
                  style="display:inline-flex;align-items:center;padding:6px 12px;border-radius:8px;font-size:11px;font-weight:600;background:var(--accent-dim);color:var(--accent-dark);text-decoration:none;flex-shrink:0;transition:background .15s"
                  onmouseover="this.style.background='var(--accent)';this.style.color='#fff'"
                  onmouseout="this.style.background='var(--accent-dim)';this.style.color='var(--accent-dark)'">
                  Abrir
                </a>
              </div>`;
          }).join('')}
        </div>
        <div style="display:flex;align-items:center;gap:6px;margin-top:10px">
          <button onclick="fecharDetalhes();abrirModalDocsOrcamento(${orcId})"
            style="padding:6px 12px;border-radius:8px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-size:11px;font-weight:600;cursor:pointer;transition:border-color .15s"
            onmouseover="this.style.borderColor='var(--accent)'"
            onmouseout="this.style.borderColor='var(--border)'">
            ✏️ Gerenciar documentos
          </button>
        </div>
      </div>`;
  } catch (_) {
    el.innerHTML = '';
  }
}

// ── Contas a Receber do Orçamento ─────────────────────────────────────────────

const _CONTA_ST = {
  PENDENTE:  { bg: 'rgba(37,99,235,.1)',  color: '#2563eb', label: 'Pendente'  },
  PARCIAL:   { bg: 'rgba(234,88,12,.1)',  color: '#ea580c', label: 'Parcial'   },
  PAGO:      { bg: 'rgba(22,163,74,.1)',  color: '#16a34a', label: 'Pago'      },
  VENCIDO:   { bg: 'rgba(220,38,38,.1)',  color: '#dc2626', label: 'Vencido'   },
  CANCELADO: { bg: 'rgba(107,114,128,.1)',color: '#6b7280', label: 'Cancelado' },
};
const _CONTA_TIPO = { entrada: '🔑 Entrada', saldo: '💰 Saldo', integral: '📋 Integral' };

async function _carregarContasOrcamento(orcId) {
  const el = document.getElementById('pagamentos-contas');
  if (!el) return;
  if (typeof Financeiro === 'undefined' || typeof Financeiro.listarContas !== 'function') return;
  try {
    const contas = await Financeiro.listarContas({ orcamento_id: orcId, tipo: 'receber' });
    if (!contas || !contas.length) return;
    const st = _CONTA_ST;
    el.innerHTML = `
      <div style="margin-bottom:12px;border:1px solid var(--border);border-radius:8px;overflow:hidden">
        <div style="font-size:10px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.07em;padding:8px 12px;background:var(--surface2);border-bottom:1px solid var(--border)">
          Contas Geradas na Aprovação
        </div>
        ${contas.map(c => {
          const s  = st[(c.status || '').toUpperCase()] || st.PENDENTE;
          const tp = _CONTA_TIPO[c.tipo_lancamento] || escapeHtml(c.descricao || '');
          const vFmt = typeof formatarMoeda === 'function' ? formatarMoeda(c.valor) : 'R$' + parseFloat(c.valor).toFixed(2);
          const venc = c.data_vencimento ? c.data_vencimento.slice(0,10).split('-').reverse().join('/') : '—';
          const metodo = (c.metodo_previsto || '').toUpperCase().replace('_',' ');
          return `<div style="display:flex;align-items:center;gap:8px;padding:9px 12px;border-bottom:1px solid var(--border);font-size:12px">
            <span style="flex:0 0 auto;font-size:12px">${tp}</span>
            ${metodo ? `<span style="color:var(--muted);font-size:10px">${escapeHtml(metodo)}</span>` : ''}
            <span style="flex:1"></span>
            <span style="color:var(--muted);font-size:10px">vence ${venc}</span>
            <span style="font-weight:700">${vFmt}</span>
            <span style="padding:2px 8px;border-radius:99px;font-size:10px;font-weight:700;background:${s.bg};color:${s.color}">${s.label}</span>
          </div>`;
        }).join('')}
      </div>`;
  } catch (_) { /* silencioso */ }
}

// ── Helpers ────────────────────────────────────────────────────────────────────

// Recarrega o orçamento da API e atualiza o cache (sem reabrir o modal)
async function _atualizarCacheOrcamento(orcId) {
  try {
    const orcAtualizado = await api.get('/orcamentos/' + orcId);
    if (typeof orcamentosCache !== 'undefined' && Array.isArray(orcamentosCache)) {
      const idx = orcamentosCache.findIndex(o => o.id === orcId);
      if (idx >= 0) orcamentosCache[idx] = orcAtualizado;
    }
  } catch (_) { /* silencioso */ }
}

document.addEventListener('DOMContentLoaded', function() {
  const modalEl = document.getElementById('modal-detalhes');
  if (modalEl) {
    modalEl.addEventListener('click', function(e) {
      if (e.target === modalEl) fecharDetalhes();
    });
  }
});

/**
 * Sincroniza um documento vinculado com o template original (P2)
 */
async function sincronizarDocumento(orcId, vincId, btn) {
  if (btn.disabled) return;
  
  if (!confirm('Deseja atualizar este documento para a versão mais recente do template? O conteúdo atual será sobrescrito.')) {
    return;
  }

  btn.disabled = true;
  btn.style.animation = 'spin 1s linear infinite';
  
  if (!document.getElementById('style-spin')) {
    const style = document.createElement('style');
    style.id = 'style-spin';
    style.innerHTML = '@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }';
    document.head.appendChild(style);
  }

  try {
    await api.post(`/orcamentos/${orcId}/documentos/${vincId}/sincronizar`);
    if (typeof showNotif === 'function') showNotif('✅', 'Sincronizado', 'Snapshot do documento atualizado.');
    _carregarDocumentosDetalhes(orcId);
  } catch (e) {
    if (typeof showNotif === 'function') showNotif('❌', 'Erro', e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.style.animation = '';
  }
}

async function confirmarDesaprovar(id, numero) {
  if (!confirm(`Deseja desaprovar o orçamento ${numero || '#' + id}? \n\nIsso irá remover as contas a receber pendentes geradas automaticamente.`)) {
    return;
  }
  
  try {
    // Usamos api.patch que já está no api.js
    await api.patch(`/orcamentos/${id}/status?novo_status=rascunho`);
    
    if (typeof showNotif === 'function') {
      showNotif('↩', 'Orçamento desaprovado', 'Revertido para rascunho.');
    } else if (typeof showToast === 'function') {
      showToast('Orçamento revertido para rascunho.', 'success');
    }
    
    fecharDetalhes();
    
    // Recarregar a lista se a função estiver disponível
    if (typeof carregar === 'function') {
      await carregar();
    } else if (typeof carregarResumo === 'function') {
      // No dashboard chama carregarResumo
      await carregarResumo();
    } else {
      location.reload();
    }
  } catch (err) {
    const msg = err.response?.data?.detail || err.message;
    if (typeof showNotif === 'function') {
      showNotif('❌', 'Erro ao desaprovar', msg, 'error');
    } else {
      alert('Erro: ' + msg);
    }
  }
}

function atualizarStatusOrcamento() {
    // Apenas para garantir que o botão apareça (check typeof)
    return true;
}

