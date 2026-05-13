/**
 * nfe.js — Emissão de NF-e/NFC-e/NFS-e a partir de orçamentos.
 * Usa api.get / api.post do padrão COTTE (js/api.js).
 */
const NFeService = (() => {
  let _orcamentoId = null;
  let _preparadoOk = false;
  /** HTML completo (Document) da última prévia DANFE/NFS-e para impressão. */
  let _ultimoHtmlPreviaImpressao = '';

  function _esc(s) {
    if (s == null || s === '') return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function _fmtBRL(n) {
    const x = Number(n);
    if (Number.isNaN(x)) return '—';
    try {
      return x.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    } catch (_) {
      return String(n);
    }
  }

  function _fmtCNPJExibicao(raw) {
    const d = String(raw || '').replace(/\D/g, '');
    if (d.length !== 14) return _esc(raw || '—');
    return _esc(d.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5'));
  }

  function _linhasEndereco(end) {
    if (!end || typeof end !== 'object') return '—';
    const p1 = [end.logradouro, end.numero, end.complemento].filter(Boolean).join(', ');
    const p2 = [end.bairro, end.cidade, end.uf].filter(Boolean).join(' — ');
    const p3 = end.cep ? `CEP ${end.cep}` : '';
    const p4 = end.codigoMunicipio ? `Mun. IBGE: ${end.codigoMunicipio}` : '';
    return [p1, p2, [p3, p4].filter(Boolean).join(' · ')].filter((x) => x && String(x).trim()).join('\n') || '—';
  }

  function _somarValorItensNfe(items) {
    if (!Array.isArray(items)) return 0;
    return items.reduce((acc, it) => acc + (Number(it.valorTotal) || 0), 0);
  }

  function _cssPreviaDanfe() {
    return ''
      + '.nfe-sim-root{font-family:Arial,Helvetica,sans-serif;font-size:11px;color:#111;max-width:210mm;margin:0 auto;background:#fff}'
      + '.nfe-sim-banner{background:#1a365d;color:#fff;padding:10px 12px;text-align:center;font-weight:700;font-size:11px;letter-spacing:.06em}'
      + '.nfe-sim-subbanner{background:#e2e8f0;color:#1a202c;padding:6px 10px;text-align:center;font-size:10px;font-weight:600}'
      + '.nfe-sim-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px}'
      + '.nfe-sim-box{border:1px solid #000;padding:8px;min-height:72px}'
      + '.nfe-sim-box h4{margin:0 0 4px;font-size:9px;font-weight:700;text-transform:uppercase;border-bottom:1px solid #000;padding-bottom:2px}'
      + '.nfe-sim-box p{margin:2px 0;font-size:10px;line-height:1.35;white-space:pre-wrap}'
      + '.nfe-sim-ident{text-align:right;font-size:10px}'
      + '.nfe-sim-ident .big{font-size:18px;font-weight:800;margin:4px 0}'
      + '.nfe-sim-chave{font-family:monospace;font-size:9px;letter-spacing:.12em;word-break:break-all;text-align:center;border:1px dashed #64748b;padding:6px;margin-top:6px;color:#334155}'
      + '.nfe-sim-table{width:100%;border-collapse:collapse;margin-top:8px;font-size:9px}'
      + '.nfe-sim-table th,.nfe-sim-table td{border:1px solid #000;padding:4px 5px}'
      + '.nfe-sim-table th{background:#f1f5f9;text-align:left}'
      + '.nfe-sim-table td.num{text-align:right}'
      + '.nfe-sim-table td.ctr{text-align:center}'
      + '.nfe-sim-tot{margin-top:8px;display:flex;justify-content:flex-end}'
      + '.nfe-sim-tot-inner{border:1px solid #000;padding:8px 12px;min-width:200px;font-size:11px;font-weight:700}'
      + '.nfe-sim-foot{margin-top:10px;padding-top:6px;border-top:1px solid #94a3b8;font-size:9px;color:#475569;text-align:center}'
      + '@media print{.nfe-sim-banner{-webkit-print-color-adjust:exact;print-color-adjust:exact}}';
  }

  function _htmlPreviaDanfeNfe(emit, p, serieForm) {
    const modelo = Number(p.modelo) === 65 ? '65' : '55';
    const docTipo = modelo === '65' ? 'NFC-e' : 'NF-e';
    const dest = p.dest || {};
    const end = dest.endereco || {};
    const items = Array.isArray(p.items) ? p.items : [];
    const pags = Array.isArray(p.pagamentos) ? p.pagamentos : [];
    const totalItens = _somarValorItensNfe(items);
    const totalPag = pags.length ? Number(pags[0].valor) || totalItens : totalItens;
    const hoje = new Date().toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
    const chaveSim = '0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000';
    const em = emit.endereco || {};

    let rows = '';
    items.forEach((it, idx) => {
      rows += '<tr>'
        + `<td class="ctr">${idx + 1}</td>`
        + `<td>${_esc(it.descricao || '—')}</td>`
        + `<td class="ctr">${_esc(it.ncm || '')}</td>`
        + `<td class="ctr">${_esc(it.cfop || '')}</td>`
        + `<td class="ctr">${_esc(String(it.unidade || 'UN'))}</td>`
        + `<td class="num">${_esc(String(it.quantidade != null ? it.quantidade : ''))}</td>`
        + `<td class="num">${_fmtBRL(it.valorUnitario)}</td>`
        + `<td class="num">${_fmtBRL(it.valorTotal)}</td>`
        + `<td class="ctr">${_esc(it.csosn || '')}</td>`
        + '</tr>';
    });

    return ''
      + '<div class="nfe-sim-root">'
      + '<div class="nfe-sim-banner">PRÉVIA LOCAL — SEM VALOR FISCAL — NÃO É DOCUMENTO ELETRÔNICO</div>'
      + '<div class="nfe-sim-subbanner">DANFE simplificado (simulação COTTE) · Dados do cadastro e do orçamento · sem envio para a Focus/SEFAZ</div>'
      + '<div class="nfe-sim-grid">'
      + '<div class="nfe-sim-box"><h4>Emitente</h4>'
      + `<p><strong>${_esc(emit.razao_social || '—')}</strong></p>`
      + `<p>CNPJ: ${_fmtCNPJExibicao(emit.cnpj)}</p>`
      + `<p>IE: ${_esc(emit.inscricao_estadual || '—')}${emit.inscricao_municipal ? ' · IM: ' + _esc(emit.inscricao_municipal) : ''}</p>`
      + (emit.crt_descricao ? `<p>${_esc(emit.crt_descricao)}</p>` : '')
      + `<p>${_esc(_linhasEndereco(em))}</p>`
      + '</div>'
      + '<div class="nfe-sim-box nfe-sim-ident"><h4 style="text-align:left">Documento (simulado)</h4>'
      + `<div>${_esc(docTipo)} · MODELO ${_esc(modelo)}</div>`
      + `<div class="big">SÉRIE ${_esc(serieForm)} · Nº ---</div>`
      + `<div><strong>Natureza:</strong> ${_esc(p.naturezaOperacao || '—')}</div>`
      + `<div><strong>Data emissão (simulada):</strong> ${_esc(hoje)}</div>`
      + `<div><strong>Ref. orçamento:</strong> ${_esc(emit.referencia_orcamento || '—')}</div>`
      + `<div class="nfe-sim-chave">CHAVE DE ACESSO (SIMULADA — 44 zeros)\n${chaveSim}</div>`
      + '</div></div>'
      + '<div class="nfe-sim-box" style="margin-top:8px"><h4>Destinatário / Remetente</h4>'
      + `<p><strong>${_esc(dest.nome || '—')}</strong></p>`
      + `<p>${dest.cnpj ? 'CNPJ: ' + _fmtCNPJExibicao(dest.cnpj) : (dest.cpf ? 'CPF: ' + _esc(dest.cpf) : '')}</p>`
      + `<p>IE: ${_esc(dest.ie || '—')}</p>`
      + `<p>${_esc(_linhasEndereco(end))}</p>`
      + (dest.email ? `<p>E-mail: ${_esc(dest.email)}</p>` : '')
      + '</div>'
      + '<table class="nfe-sim-table"><thead><tr>'
      + '<th class="ctr">#</th><th>Descrição</th><th class="ctr">NCM</th><th class="ctr">CFOP</th>'
      + '<th class="ctr">UN</th><th class="ctr">Qtd</th><th class="num">V.Unit</th><th class="num">V.Total</th><th class="ctr">CSOSN</th>'
      + '</tr></thead><tbody>' + (rows || '<tr><td colspan="9" style="text-align:center">Sem itens</td></tr>') + '</tbody></table>'
      + '<div class="nfe-sim-tot"><div class="nfe-sim-tot-inner">'
      + `Valor total dos produtos: ${_fmtBRL(totalItens)}<br>`
      + (pags.length ? `Pagamento (tipo ${ _esc(String(pags[0].tipoPagamento)) }): ${_fmtBRL(totalPag)}` : '')
      + '</div></div>'
      + '<div class="nfe-sim-foot">Esta página foi gerada apenas para conferência interna. A NF-e válida depende da autorização da SEFAZ após emissão pela Focus NFe.</div>'
      + '</div>';
  }

  function _htmlPreviaNfseSimulada(emit, p) {
    const tom = p.tomador || {};
    const srv = p.servico || {};
    const val = p.valores || {};
    const em = emit.endereco || {};
    const docTom = tom.cnpj ? `CNPJ ${_fmtCNPJExibicao(tom.cnpj)}` : (tom.cpf ? `CPF ${_esc(tom.cpf)}` : '');
    return ''
      + '<div class="nfe-sim-root">'
      + '<div class="nfe-sim-banner">PRÉVIA LOCAL — NFS-e (SIMULADA) — SEM VALOR FISCAL</div>'
      + '<div class="nfe-sim-subbanner">Prestador conforme cadastro COTTE / Focus NFe · Tomador e serviço conforme orçamento</div>'
      + '<div class="nfe-sim-grid">'
      + '<div class="nfe-sim-box"><h4>Prestador (emitente — cadastro)</h4>'
      + `<p><strong>${_esc(emit.razao_social || '—')}</strong></p>`
      + `<p>CNPJ: ${_fmtCNPJExibicao(emit.cnpj)}</p>`
      + `<p>IM: ${_esc(emit.inscricao_municipal || '—')}</p>`
      + `<p>${_esc(_linhasEndereco(em))}</p>`
      + '</div>'
      + '<div class="nfe-sim-box"><h4>Serviço / Valores</h4>'
      + `<p><strong>LC116:</strong> ${_esc(srv.codigo || '—')}</p>`
      + `<p><strong>Descrição:</strong> ${_esc(srv.descricao || '—')}</p>`
      + `<p><strong>Total:</strong> ${_fmtBRL(val.total)} · <strong>Alíquota ISS:</strong> ${_esc(String(val.aliquotaIss != null ? val.aliquotaIss : '—'))}%</p>`
      + `<p><strong>Competência:</strong> ${_esc(p.competencia || '—')} · <strong>Ref.:</strong> ${_esc(p.referencia || emit.referencia_orcamento || '—')}</p>`
      + '</div></div>'
      + '<div class="nfe-sim-box" style="margin-top:8px"><h4>Tomador</h4>'
      + `<p><strong>${_esc(tom.nome || '—')}</strong> ${docTom ? '· ' + docTom : ''}</p>`
      + (tom.email ? `<p>E-mail: ${_esc(tom.email)}</p>` : '')
      + (tom.endereco ? `<p>${_esc(_linhasEndereco(tom.endereco))}</p>` : '')
      + '</div>'
      + '<div class="nfe-sim-foot">NFS-e válida somente após transmissão e autorização pela prefeitura via Focus NFe.</div>'
      + '</div>';
  }

  function _documentoImpressaoHtml(innerBody) {
    const css = _cssPreviaDanfe();
    return '<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><title>Prévia fiscal (simulada)</title>'
      + `<style>${css}@page{size:A4;margin:12mm}</style></head><body>${innerBody}</body></html>`;
  }

  function _painelEnvolvendoPrevia(innerBody) {
    return `<div style="max-height:420px;overflow:auto;border:1px solid #cbd5e1;border-radius:8px;background:#fff;padding:10px"><style>${_cssPreviaDanfe()}</style>${innerBody}</div>`;
  }

  function _renderDanfeSimulado(emitente, payload, tipo, serieForm) {
    const host = document.getElementById('nfe-danfe-host');
    const btnP = document.getElementById('btn-nfe-previa-print');
    _ultimoHtmlPreviaImpressao = '';
    if (!host) return;
    host.innerHTML = '';
    if (!emitente || !payload) {
      if (btnP) btnP.disabled = true;
      return;
    }
    let inner = '';
    if (tipo === 'nfse') {
      inner = _htmlPreviaNfseSimulada(emitente, payload);
    } else {
      inner = _htmlPreviaDanfeNfe(emitente, payload, serieForm);
    }
    host.innerHTML = _painelEnvolvendoPrevia(inner);
    _ultimoHtmlPreviaImpressao = _documentoImpressaoHtml(inner);
    if (btnP) btnP.disabled = false;
  }

  function imprimirPreviaDanfe() {
    if (!_ultimoHtmlPreviaImpressao) {
      alert('Faça «Verificar e pré-visualizar» antes, sem bloqueios, para gerar a prévia.');
      return;
    }
    const w = window.open('', '_blank');
    if (!w) {
      alert('Permita pop-ups para imprimir a prévia.');
      return;
    }
    w.document.open();
    w.document.write(_ultimoHtmlPreviaImpressao);
    w.document.close();
    setTimeout(function () {
      try {
        w.focus();
        w.print();
      } catch (_) {}
    }, 300);
  }

  function _corpoPreparar() {
    const tipo = document.getElementById('nfe-tipo')?.value || 'nfe';
    const natureza = (document.getElementById('nfe-natureza')?.value || '').trim();
    const serie = (document.getElementById('nfe-serie')?.value || '').trim();
    const codigoServico = (document.getElementById('nfe-codigo-servico')?.value || '').trim();
    const aliquotaIss = document.getElementById('nfe-aliquota-iss')?.value;
    const body = { orcamento_id: _orcamentoId, tipo };
    if (natureza) body.natureza_operacao = natureza;
    if (serie) body.serie = serie;
    if (tipo === 'nfse') {
      if (codigoServico) body.codigo_servico_lc116 = codigoServico;
      if (aliquotaIss !== '' && aliquotaIss != null && !Number.isNaN(Number(aliquotaIss))) {
        body.aliquota_iss = Number(aliquotaIss);
      }
    }
    return body;
  }

  function _limparPainelPrevia() {
    const wrap = document.getElementById('nfe-preview-wrap');
    const body = document.getElementById('nfe-preview-body');
    const pre = document.getElementById('nfe-preview-json-pre');
    const det = document.getElementById('nfe-preview-json-details');
    const host = document.getElementById('nfe-danfe-host');
    const btnP = document.getElementById('btn-nfe-previa-print');
    if (wrap) wrap.style.display = 'none';
    if (body) body.innerHTML = '';
    if (pre) pre.textContent = '';
    if (det) det.open = false;
    if (host) host.innerHTML = '';
    if (btnP) btnP.disabled = true;
    _ultimoHtmlPreviaImpressao = '';
  }

  function _renderPayloadPreview(resultado) {
    const wrap = document.getElementById('nfe-preview-wrap');
    const body = document.getElementById('nfe-preview-body');
    const pre = document.getElementById('nfe-preview-json-pre');
    if (!wrap || !body || !pre) return;

    const tipo = document.getElementById('nfe-tipo')?.value || 'nfe';
    const serieForm = (document.getElementById('nfe-serie')?.value || '1').trim() || '1';
    const natForm = (document.getElementById('nfe-natureza')?.value || '').trim();

    if (!resultado || !resultado.payload_preview) {
      wrap.style.display = 'block';
      body.innerHTML =
        '<p style="color:var(--muted,#666);margin:0">Quando não houver bloqueios, aparece aqui o resumo do que será enviado à Focus NFe. '
        + 'Corrija os alertas em vermelho (se houver) e use <strong>Verificar e pré-visualizar</strong> de novo.</p>';
      pre.textContent = '';
      const host = document.getElementById('nfe-danfe-host');
      if (host) host.innerHTML = '';
      const btnP = document.getElementById('btn-nfe-previa-print');
      if (btnP) btnP.disabled = true;
      _ultimoHtmlPreviaImpressao = '';
      return;
    }

    const p = resultado.payload_preview;
    wrap.style.display = 'block';
    pre.textContent = JSON.stringify(p, null, 2);

    let html = '';

    if (tipo === 'nfse') {
      const tom = p.tomador || {};
      const srv = p.servico || {};
      const val = p.valores || {};
      const doc = tom.cnpj ? `CNPJ ${_esc(tom.cnpj)}` : (tom.cpf ? `CPF ${_esc(tom.cpf)}` : 'Documento não informado');
      html += '<p style="margin:0 0 8px"><strong>Tomador:</strong> ' + _esc(tom.nome || '—') + ' · ' + doc + '</p>';
      if (tom.email) html += '<p style="margin:0 0 8px"><strong>E-mail:</strong> ' + _esc(tom.email) + '</p>';
      html += '<p style="margin:0 0 8px"><strong>Serviço (LC116):</strong> ' + _esc(srv.codigo || '—') + '</p>';
      html += '<p style="margin:0 0 8px"><strong>Descrição:</strong> ' + _esc(srv.descricao || '—') + '</p>';
      html += '<p style="margin:0 0 8px"><strong>Total:</strong> ' + _fmtBRL(val.total)
        + ' · <strong>Alíquota ISS:</strong> ' + _esc(String(val.aliquotaIss != null ? val.aliquotaIss : '—'))
        + '% · <strong>Competência:</strong> ' + _esc(p.competencia || '—')
        + ' · <strong>Referência:</strong> ' + _esc(p.referencia || '—') + '</p>';
    } else {
      html += '<p style="margin:0 0 6px;font-size:0.78rem;color:var(--muted,#666)">Formulário: natureza <strong>'
        + _esc(natForm || '—') + '</strong> · série <strong>' + _esc(serieForm) + '</strong></p>';
      html += '<p style="margin:0 0 8px"><strong>Natureza da operação (envio):</strong> ' + _esc(p.naturezaOperacao || '—') + '</p>';
      html += '<p style="margin:0 0 8px"><strong>Modelo:</strong> ' + _esc(String(p.modelo || '—'))
        + ' (' + (Number(p.modelo) === 65 ? 'NFC-e' : 'NF-e') + ')</p>';

      const d = p.dest || {};
      const end = d.endereco || {};
      const doc = d.cnpj ? `CNPJ ${_esc(d.cnpj)}` : (d.cpf ? `CPF ${_esc(d.cpf)}` : '');
      html += '<p style="margin:0 0 4px"><strong>Destinatário:</strong> ' + _esc(d.nome || '—') + (doc ? ' · ' + doc : '') + '</p>';
      html += '<p style="margin:0 0 10px;font-size:0.78rem;color:var(--muted,#666)">'
        + _esc([end.logradouro, end.numero, end.bairro].filter(Boolean).join(', '))
        + ' — ' + _esc(end.cidade || '') + '/' + _esc(end.uf || '')
        + (end.codigoMunicipio != null ? ' · IBGE: ' + _esc(String(end.codigoMunicipio)) : '')
        + '</p>';

      const items = Array.isArray(p.items) ? p.items : [];
      if (items.length) {
        html += '<table style="width:100%;border-collapse:collapse;font-size:0.78rem;margin:8px 0"><thead><tr>'
          + '<th style="text-align:left;border-bottom:1px solid var(--border,#ddd);padding:4px 6px">Item</th>'
          + '<th style="text-align:right;border-bottom:1px solid var(--border,#ddd);padding:4px 6px">Qtd</th>'
          + '<th style="text-align:right;border-bottom:1px solid var(--border,#ddd);padding:4px 6px">Total</th>'
          + '<th style="text-align:center;border-bottom:1px solid var(--border,#ddd);padding:4px 6px">NCM</th>'
          + '<th style="text-align:center;border-bottom:1px solid var(--border,#ddd);padding:4px 6px">CFOP</th>'
          + '</tr></thead><tbody>';
        items.forEach((it) => {
          html += '<tr><td style="padding:6px;border-bottom:1px solid var(--border,#eee)">' + _esc(it.descricao || '—') + '</td>'
            + '<td style="text-align:right;padding:6px;border-bottom:1px solid var(--border,#eee)">' + _esc(String(it.quantidade != null ? it.quantidade : '—')) + '</td>'
            + '<td style="text-align:right;padding:6px;border-bottom:1px solid var(--border,#eee)">' + _fmtBRL(it.valorTotal) + '</td>'
            + '<td style="text-align:center;padding:6px;border-bottom:1px solid var(--border,#eee)">' + _esc(it.ncm || '—') + '</td>'
            + '<td style="text-align:center;padding:6px;border-bottom:1px solid var(--border,#eee)">' + _esc(it.cfop || '—') + '</td></tr>';
        });
        html += '</tbody></table>';
      }

      const pags = Array.isArray(p.pagamentos) ? p.pagamentos : [];
      if (pags.length) {
        html += '<p style="margin:6px 0 0"><strong>Pagamento:</strong> tipo ' + _esc(String(pags[0].tipoPagamento || '—'))
          + ' · ' + _fmtBRL(pags[0].valor) + '</p>';
      }
    }

    body.innerHTML = html;
    _renderDanfeSimulado(resultado.emitente_preview, p, tipo, serieForm);
  }

  function abrirModal(orcamentoId) {
    _orcamentoId = orcamentoId;
    const modal = document.getElementById('modal-nfe');
    if (!modal) return;
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
    carregarNotasExistentes(orcamentoId);
  }

  function fecharModal() {
    const modal = document.getElementById('modal-nfe');
    if (modal) {
      modal.classList.remove('open');
      modal.setAttribute('aria-hidden', 'true');
    }
    const statusMsg = document.getElementById('nfe-status-msg');
    if (statusMsg) statusMsg.textContent = '';
    _orcamentoId = null;
    _preparadoOk = false;
    const btnEmitir = document.getElementById('btn-emitir-nfe');
    if (btnEmitir) btnEmitir.disabled = true;
    const areaPrep = document.getElementById('nfe-prep-resultado');
    if (areaPrep) areaPrep.innerHTML = '';
    _limparPainelPrevia();
  }

  async function carregarNotasExistentes(orcamentoId) {
    const lista = document.getElementById('nfe-lista-notas');
    if (!lista) return;
    lista.innerHTML = '<p style="color:var(--text-muted,#888)">Carregando...</p>';

    let notas = [];
    try {
      const resp = await api.get(`/notas-fiscais/orcamento/${orcamentoId}`);
      notas = Array.isArray(resp) ? resp : (resp?.data || []);
    } catch (_) {
      notas = [];
    }

    if (!notas.length) {
      lista.innerHTML = '<p style="color:var(--text-muted,#888)">Nenhuma nota emitida para este orçamento.</p>';
      return;
    }
    lista.innerHTML = notas.map(n => `
      <div class="nfe-item" style="display:flex;align-items:center;gap:0.5rem;padding:0.5rem 0;border-bottom:1px solid var(--border,#eee)">
        <span style="font-weight:600;text-transform:uppercase;font-size:0.8rem">${n.tipo}</span>
        <span>${n.numero ? `N\xba ${n.numero} \xb7 S\xe9rie ${n.serie}` : '—'}</span>
        <span class="badge badge-${_badgeClass(n.status)}" style="margin-left:auto">${n.status}</span>
        ${n.danfe_url ? `<a href="${n.danfe_url}" target="_blank" class="btn btn-ghost btn-sm">DANFE</a>` : ''}
        ${n.xml_url ? `<a href="${n.xml_url}" target="_blank" class="btn btn-ghost btn-sm">XML</a>` : ''}
        ${n.status === 'emitida' ? `<button class="btn btn-ghost btn-sm" onclick="NFeService._cancelar(${n.id})">Cancelar</button>` : ''}
        ${n.status === 'erro' ? `<span style="font-size:0.75rem;color:var(--danger,red)">Erro: ${n.erro_mensagem || n.erro_codigo || ''}</span>` : ''}
      </div>
    `).join('');
  }

  async function emitir() {
    const tipo = document.getElementById('nfe-tipo')?.value;
    const natureza = document.getElementById('nfe-natureza')?.value || 'Venda de Serviços';
    const serie = document.getElementById('nfe-serie')?.value || '1';
    const codigoServico = document.getElementById('nfe-codigo-servico')?.value;
    const aliquotaIss = document.getElementById('nfe-aliquota-iss')?.value;
    const btn = document.getElementById('btn-emitir-nfe');
    const statusMsg = document.getElementById('nfe-status-msg');

    if (!_preparadoOk) {
      if (statusMsg) statusMsg.textContent = 'Use «Verificar e pré-visualizar» primeiro e corrija bloqueios, se houver.';
      return;
    }

    if (btn) { btn.disabled = true; btn.textContent = 'Emitindo...'; }
    if (statusMsg) statusMsg.textContent = 'Enviando para a SEFAZ, aguarde...';

    const payload = {
      orcamento_id: _orcamentoId,
      tipo,
      natureza_operacao: natureza,
      serie,
      ...(codigoServico ? { codigo_servico_lc116: codigoServico } : {}),
      ...(aliquotaIss ? { aliquota_iss: parseFloat(aliquotaIss) } : {}),
    };

    let resp = null;
    try {
      resp = await api.post('/notas-fiscais/emitir', payload);
    } catch (e) {
      if (btn) { btn.disabled = false; btn.textContent = '✅ Confirmar e Emitir'; }
      if (statusMsg) statusMsg.textContent = `Erro: ${e.message || 'Falha na emissão'}`;
      return;
    }

    if (btn) { btn.disabled = false; btn.textContent = '✅ Confirmar e Emitir'; }

    if (resp && resp.id) {
      if (statusMsg) statusMsg.textContent = 'Processando... aguardando SEFAZ.';
      _aguardarStatus(resp.id);
    } else {
      if (statusMsg) statusMsg.textContent = 'Erro: resposta inesperada do servidor';
    }
  }

  const NFE_STATUS_POLL_MAX = 45;
  const NFE_STATUS_INTERVAL_MS = 3000;

  async function _aguardarStatus(notaId, tentativas = 0) {
    const statusMsg = document.getElementById('nfe-status-msg');
    if (tentativas > NFE_STATUS_POLL_MAX) {
      try {
        await api.post(`/notas-fiscais/${notaId}/sincronizar-focus`, {});
        const resp = await api.get(`/notas-fiscais/${notaId}`);
        const notaSync = resp?.data || resp;
        if (notaSync && notaSync.status === 'emitida') {
          if (statusMsg) {
            statusMsg.textContent = `✓ NF emitida com sucesso! N\xfamero: ${notaSync.numero || '—'}`;
          }
          if (_orcamentoId) carregarNotasExistentes(_orcamentoId);
          return;
        }
        if (notaSync && notaSync.status === 'erro') {
          const msg = notaSync.erro_mensagem || notaSync.erro_codigo || 'desconhecido';
          if (statusMsg) statusMsg.textContent = `Erro: ${msg}`;
          if (_orcamentoId) carregarNotasExistentes(_orcamentoId);
          _mostrarBotaoAnalise(notaId);
          return;
        }
      } catch (_) {
        /* mantém mensagem genérica abaixo */
      }
      if (statusMsg) {
        statusMsg.textContent =
          'Tempo do modal esgotado. Se a Focus já mostra autorizado, atualize a lista de notas ou configure o webhook (URL pública POST …/api/v1/notas-fiscais/webhook/focus com Basic Auth = seu token).';
      }
      if (_orcamentoId) carregarNotasExistentes(_orcamentoId);
      return;
    }
    await new Promise(r => setTimeout(r, NFE_STATUS_INTERVAL_MS));

    let nota = null;
    try {
      const resp = await api.get(`/notas-fiscais/${notaId}`);
      nota = resp?.data || resp;
    } catch (_) {
      nota = null;
    }
    if (!nota) {
      if (statusMsg) statusMsg.textContent = `Processando... (sem resposta ${tentativas + 1}/${NFE_STATUS_POLL_MAX})`;
      return _aguardarStatus(notaId, tentativas + 1);
    }

    if (nota.status === 'emitida') {
      if (statusMsg) statusMsg.textContent = `✓ NF emitida com sucesso! N\xfamero: ${nota.numero || '—'}`;
      if (_orcamentoId) carregarNotasExistentes(_orcamentoId);
    } else if (nota.status === 'erro') {
      const msg = nota.erro_mensagem || nota.erro_codigo || 'desconhecido';
      const msgStr = String(msg);
      const ehAuthFocus =
        nota.erro_codigo === 'AUTH_ERROR' ||
        (msgStr.includes('HTTP 401') && msgStr.includes('Focus'));
      const prefix = ehAuthFocus
        ? 'Erro de autenticação na Focus (ainda não chegou à SEFAZ): '
        : 'Erro SEFAZ: ';
      if (statusMsg) statusMsg.textContent = prefix + msg;
      if (_orcamentoId) carregarNotasExistentes(_orcamentoId);
      _mostrarBotaoAnalise(notaId);
    } else {
      if (statusMsg) statusMsg.textContent = `Processando... (${tentativas + 1}/${NFE_STATUS_POLL_MAX})`;
      _aguardarStatus(notaId, tentativas + 1);
    }
  }

  function _mostrarBotaoAnalise(notaId) {
    const areaPrep = document.getElementById('nfe-prep-resultado');
    if (!areaPrep) return;
    areaPrep.innerHTML = `
      <div style="margin-top:8px">
        <button id="btn-analisar-erro-nfe" class="btn btn-sm btn-warning" style="width:100%">
          Analisar Erro e Ver O Que Corrigir
        </button>
        <div id="nfe-analise-resultado" style="margin-top:8px"></div>
      </div>`;
    document.getElementById('btn-analisar-erro-nfe').onclick = async function() {
      const btn = this;
      btn.disabled = true;
      btn.textContent = 'Analisando...';
      const area = document.getElementById('nfe-analise-resultado');
      try {
        const analise = await api.post(`/notas-fiscais/${notaId}/analisar-erro`, {});
        const sugestoes = analise.sugestoes || [];
        if (!sugestoes.length) {
          if (area) area.innerHTML = '<p style="font-size:12px;color:var(--text-muted,#888)">Nenhuma sugestão automática disponível.</p>';
        } else {
          if (area) area.innerHTML = sugestoes.map(s =>
            `<div style="margin-bottom:8px;padding:8px 10px;background:rgba(255,200,0,0.07);border-left:3px solid #f59e0b;border-radius:4px;font-size:12px">
              <div style="color:#f59e0b;font-weight:600;margin-bottom:2px">${s.campo}</div>
              <div>${s.acao}</div>
            </div>`
          ).join('');
        }
        btn.textContent = 'Atualizar Análise';
        btn.disabled = false;
      } catch(e) {
        btn.disabled = false;
        btn.textContent = 'Analisar Erro e Ver O Que Corrigir';
        if (area) area.innerHTML = `<p style="font-size:12px;color:#ef4444">Erro ao analisar: ${e.message || 'tente novamente'}</p>`;
      }
    };
  }

  async function _cancelar(notaId) {
    const motivo = prompt('Motivo do cancelamento (mín. 15 caracteres):');
    if (!motivo || motivo.length < 15) {
      alert('Motivo deve ter pelo menos 15 caracteres.');
      return;
    }
    try {
      await api.post(`/notas-fiscais/${notaId}/cancelar`, { motivo });
      if (_orcamentoId) carregarNotasExistentes(_orcamentoId);
    } catch (e) {
      alert(e.message || 'Erro ao cancelar nota');
    }
  }

  async function _preparar() {
    const btnVerificar = document.getElementById('btn-verificar-nfe');
    const btnEmitir = document.getElementById('btn-emitir-nfe');
    const areaPrep = document.getElementById('nfe-prep-resultado');
    if (!_orcamentoId) return;

    if (btnVerificar) { btnVerificar.disabled = true; btnVerificar.textContent = 'Verificando...'; }
    _preparadoOk = false;
    if (btnEmitir) btnEmitir.disabled = true;
    if (areaPrep) areaPrep.innerHTML = '';
    _limparPainelPrevia();

    try {
      const resultado = await api.post('/notas-fiscais/preparar', _corpoPreparar());

      _preparadoOk = resultado.pronto === true;
      if (btnEmitir) btnEmitir.disabled = !_preparadoOk;

      let html = '';

      if (resultado.bloqueios && resultado.bloqueios.length) {
        html += resultado.bloqueios.map(b =>
          `<div style="color:#ef4444;font-size:12px;padding:4px 0">❌ ${_esc(b)}</div>`
        ).join('');
      }
      if (resultado.avisos && resultado.avisos.length) {
        html += resultado.avisos.map(a =>
          `<div style="color:#f59e0b;font-size:12px;padding:4px 0">⚠️ ${_esc(a)}</div>`
        ).join('');
      }
      if (_preparadoOk && !html) {
        html = `<div style="color:#00e5a0;font-size:12px;font-weight:600">✅ ${resultado.resumo || 'Pronto para emitir'}</div>`;
      } else if (_preparadoOk) {
        html = `<div style="color:#00e5a0;font-size:12px;font-weight:600;margin-bottom:4px">✅ ${resultado.resumo}</div>` + html;
      }

      if (areaPrep) areaPrep.innerHTML = html;
      _renderPayloadPreview(resultado);
    } catch (e) {
      _preparadoOk = false;
      if (btnEmitir) btnEmitir.disabled = true;
      if (areaPrep) areaPrep.innerHTML = `<div style="color:#ef4444;font-size:12px">❌ Erro ao verificar: ${e.message || 'Tente novamente'}</div>`;
      _limparPainelPrevia();
    } finally {
      if (btnVerificar) { btnVerificar.disabled = false; btnVerificar.textContent = '🔍 Verificar e pré-visualizar'; }
    }
  }

  function _toggleCamposNfse() {
    const tipo = document.getElementById('nfe-tipo')?.value;
    const campos = document.getElementById('campos-nfse');
    const natureza = document.getElementById('nfe-natureza');
    if (!campos) return;
    if (tipo === 'nfse') {
      campos.style.display = 'flex';
      if (natureza && natureza.value === 'Venda de Mercadorias') natureza.value = 'Prestação de Serviços';
    } else {
      campos.style.display = 'none';
      if (natureza && natureza.value === 'Prestação de Serviços') natureza.value = 'Venda de Mercadorias';
    }
    // Resetar verificação ao mudar tipo
    _preparadoOk = false;
    const btnEmitir = document.getElementById('btn-emitir-nfe');
    if (btnEmitir) btnEmitir.disabled = true;
    const areaPrep = document.getElementById('nfe-prep-resultado');
    if (areaPrep) areaPrep.innerHTML = '';
    _limparPainelPrevia();
  }

  function _badgeClass(status) {
    const map = { emitida: 'success', erro: 'danger', cancelada: 'warning', processando: 'info', pendente: 'secondary' };
    return map[status] || 'secondary';
  }

  return { abrirModal, fecharModal, emitir, _cancelar, verificar: _preparar, _toggleCamposNfse, imprimirPreviaDanfe };
})();

// Expõe no escopo global para uso em onclick= attributes
window.NFeService = NFeService;
