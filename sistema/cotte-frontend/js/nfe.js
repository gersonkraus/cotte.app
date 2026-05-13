/**
 * nfe.js — Emissão de NF-e/NFC-e/NFS-e a partir de orçamentos.
 * Usa api.get / api.post do padrão COTTE (js/api.js).
 */
const NFeService = (() => {
  let _orcamentoId = null;
  let _preparadoOk = false;
  /** Snapshot do GET /orcamentos/{id} (para montar itens_override). */
  let _orcSnapshot = null;
  /** True se o operador alterou NCM/CFOP/unidade/CSOSN/origem na tabela desta sessão. */
  let _fiscalItensDirty = false;
  /** Valores fiscais efetivos do último preparar (payload Focus `items`), por id do item do orçamento. */
  let _fiscalEfetivoPorItemId = {};

  function _limparFiscalEfetivoPreparar() {
    _fiscalEfetivoPorItemId = {};
  }

  /** Converte um elemento de `payload_preview.items` (Focus) para campos da tabela do modal. */
  function _payloadItemParaFiscalLinha(pItem) {
    if (!pItem || typeof pItem !== 'object') return null;
    let ncm = '';
    try {
      const n = parseInt(String(pItem.codigo_ncm ?? ''), 10);
      if (Number.isFinite(n) && n > 0) ncm = String(n).padStart(8, '0').slice(-8);
    } catch (_) { /* ignora */ }
    let cfop = '';
    try {
      const c = parseInt(String(pItem.cfop ?? ''), 10);
      if (Number.isFinite(c) && c > 0) cfop = String(c).padStart(4, '0').slice(-4);
    } catch (_) { /* ignora */ }
    const uniRaw = pItem.unidade_comercial || pItem.unidade_tributavel || 'UN';
    const uni = (String(uniRaw || 'UN').trim().toUpperCase().slice(0, 6) || 'UN');
    const st = pItem.icms_situacao_tributaria;
    const csosn = st != null && String(st).trim() !== ''
      ? String(st).replace(/\D/g, '').slice(0, 4)
      : '';
    let origem = '0';
    if (pItem.icms_origem != null && String(pItem.icms_origem).trim() !== '') {
      const o = parseInt(String(pItem.icms_origem), 10);
      if (!Number.isNaN(o)) origem = String(o);
    }
    return { ncm, cfop, unidade: uni, csosn, origem };
  }

  /** Preenche `_fiscalEfetivoPorItemId` a partir de `payload_preview` (mesma ordem dos itens do orçamento). */
  function _aplicarFiscalDoPayloadPreparar(payloadPreview) {
    const tipo = document.getElementById('nfe-tipo')?.value || 'nfe';
    if (tipo === 'nfse' || !_orcSnapshot?.itens?.length) {
      _limparFiscalEfetivoPreparar();
      return;
    }
    const rawItems = payloadPreview && payloadPreview.items;
    if (!Array.isArray(rawItems) || rawItems.length !== _orcSnapshot.itens.length) {
      _limparFiscalEfetivoPreparar();
      return;
    }
    const next = {};
    for (let i = 0; i < _orcSnapshot.itens.length; i++) {
      const it = _orcSnapshot.itens[i];
      if (it == null || it.id == null) continue;
      const line = _payloadItemParaFiscalLinha(rawItems[i]);
      if (line) next[String(it.id)] = line;
    }
    _fiscalEfetivoPorItemId = next;
    _fiscalItensDirty = false;
  }

  /** Valor sentinela da opção «Outro» no select (não é texto enviado à API). */
  const NATUREZA_OUTRO = '__outro__';

  /** Opções NF-e / NFC-e — textos curtos, alinhados ao uso típico e ao default em nfe_service (Venda de mercadorias). */
  const _OPCOES_NFE_NFCE = [
    { value: 'Venda de mercadorias', label: 'Venda de mercadorias' },
    { value: 'Venda de mercadorias adquiridas de terceiros', label: 'Venda de mercadorias adquiridas de terceiros' },
    { value: 'Remessa para demonstração', label: 'Remessa para demonstração' },
    { value: 'Devolução de mercadorias', label: 'Devolução de mercadorias' },
    { value: 'Remessa para conserto ou reparo', label: 'Remessa para conserto ou reparo' },
    { value: 'Industrialização efetuada por outra empresa', label: 'Industrialização efetuada por outra empresa' },
    { value: 'Retorno de mercadorias utilizada na industrialização', label: 'Retorno de mercadorias utilizada na industrialização' },
    { value: 'Bonificação', label: 'Bonificação' },
    { value: NATUREZA_OUTRO, label: 'Outro (especificar)' },
  ];

  const _OPCOES_NFSE = [
    { value: 'Prestação de serviços', label: 'Prestação de serviços' },
    { value: 'Locação de mão de obra', label: 'Locação de mão de obra' },
    { value: 'Locação de bens móveis', label: 'Locação de bens móveis' },
    { value: 'Treinamento e consultoria', label: 'Treinamento e consultoria' },
    { value: 'Intermediação de serviços', label: 'Intermediação de serviços' },
    { value: NATUREZA_OUTRO, label: 'Outro (especificar)' },
  ];

  const _DICA_POR_TIPO = {
    nfe: 'NF-e (55): materiais com NCM/CFOP e cliente com endereço e documento completos. Verificação usa o mesmo payload enviado à Focus.',
    nfce: 'NFC-e (65): consumidor final; em produção a SEFAZ exige CSC/token da NFC-e cadastrados na Focus para o ambiente correto.',
    nfse: 'NFS-e municipal: informe código LC116 e alíquota de ISS. Algumas prefeituras exigem dados extras fora desta tela.',
  };

  function _defaultNaturezaParaTipo(tipo) {
    const t = (tipo || 'nfe').toLowerCase();
    if (t === 'nfse') return 'Prestação de serviços';
    return 'Venda de mercadorias';
  }

  function _preencherSelectNatureza(tipo) {
    const sel = document.getElementById('nfe-natureza');
    if (!sel) return;
    const t = (tipo || 'nfe').toLowerCase();
    const opcoes = t === 'nfse' ? _OPCOES_NFSE : _OPCOES_NFE_NFCE;
    sel.replaceChildren();
    opcoes.forEach((o) => {
      const opt = document.createElement('option');
      opt.value = o.value;
      opt.textContent = o.label;
      sel.appendChild(opt);
    });
    sel.value = opcoes[0].value;
  }

  function _atualizarDicaTipo() {
    const el = document.getElementById('nfe-dica-tipo');
    const tipo = document.getElementById('nfe-tipo')?.value || 'nfe';
    if (el) el.textContent = _DICA_POR_TIPO[tipo] || '';
  }

  function _naturezaOperacaoResolvida() {
    const tipo = document.getElementById('nfe-tipo')?.value || 'nfe';
    const sel = document.getElementById('nfe-natureza');
    const outroEl = document.getElementById('nfe-natureza-outro');
    const v = (sel?.value || '').trim();
    if (v === NATUREZA_OUTRO) {
      const texto = (outroEl?.value || '').trim().slice(0, 120);
      return texto || _defaultNaturezaParaTipo(tipo);
    }
    return v.slice(0, 120) || _defaultNaturezaParaTipo(tipo);
  }

  function _onNaturezaSelectChange() {
    const wrap = document.getElementById('nfe-natureza-outro-wrap');
    const sel = document.getElementById('nfe-natureza');
    const outroEl = document.getElementById('nfe-natureza-outro');
    const isOutro = sel && sel.value === NATUREZA_OUTRO;
    if (wrap) wrap.style.display = isOutro ? 'block' : 'none';
    if (!isOutro && outroEl) outroEl.value = '';
    _invalidatePrep();
  }

  function _invalidatePrep() {
    _preparadoOk = false;
    const btnEmitir = document.getElementById('btn-emitir-nfe');
    if (btnEmitir) btnEmitir.disabled = true;
  }

  function _markFiscalItensDirty() {
    _fiscalItensDirty = true;
    _invalidatePrep();
  }

  function _renderTabelaFiscalItens() {
    const bloco = document.getElementById('nfe-bloco-itens-fiscal');
    const host = document.getElementById('nfe-itens-fiscais');
    const tipo = document.getElementById('nfe-tipo')?.value || 'nfe';
    if (!bloco || !host) return;
    if (tipo === 'nfse' || !_orcSnapshot || !Array.isArray(_orcSnapshot.itens) || !_orcSnapshot.itens.length) {
      bloco.style.display = 'none';
      host.innerHTML = '';
      return;
    }
    bloco.style.display = 'block';
    const itens = _orcSnapshot.itens;
    const rows = itens.map((it, idx) => {
      const s = it.servico || {};
      const fid = _fiscalEfetivoPorItemId[String(it.id)];
      const ncmPrep = fid && fid.ncm ? String(fid.ncm).replace(/\D/g, '').slice(0, 8) : '';
      const ncmCat = String(s.ncm || '').replace(/\D/g, '').slice(0, 8);
      const ncm = ncmPrep || ncmCat;
      const cfopPrep = fid && fid.cfop ? String(fid.cfop).replace(/\D/g, '').slice(0, 4) : '';
      const cfopCat = String(s.cfop || '').replace(/\D/g, '').slice(0, 4);
      const cfop = cfopPrep || cfopCat;
      const uniPrep = fid && fid.unidade ? String(fid.unidade).trim().toUpperCase().slice(0, 6) : '';
      const uniCat = String(s.unidade_fiscal || s.unidade || it.unidade || 'UN').slice(0, 6);
      const uni = uniPrep || uniCat || 'UN';
      let csosn = '';
      if (fid && fid.csosn != null && String(fid.csosn).trim() !== '') {
        csosn = String(fid.csosn).replace(/\D/g, '').slice(0, 4);
      } else if (s.csosn != null && String(s.csosn).trim() !== '') {
        csosn = String(s.csosn).replace(/\D/g, '').slice(0, 4);
      }
      let origem = '0';
      if (fid && fid.origem != null && String(fid.origem).trim() !== '') {
        origem = String(fid.origem);
      } else if (s.origem != null && s.origem !== '') {
        origem = String(s.origem);
      }
      return `<tr data-nfe-item-row data-item-id="${it.id}" style="font-size:12px">
        <td style="padding:6px;border-bottom:1px solid var(--border,#eee);max-width:200px;vertical-align:middle">${_esc((it.descricao || '—').slice(0, 100))}</td>
        <td style="padding:4px;border-bottom:1px solid var(--border,#eee);vertical-align:middle"><input class="nfe-in-ncm" type="text" inputmode="numeric" maxlength="8" value="${_esc(ncm)}" style="width:7rem" aria-label="NCM item ${idx + 1}" oninput="NFeService._markFiscalItensDirty()"></td>
        <td style="padding:4px;border-bottom:1px solid var(--border,#eee);vertical-align:middle"><input class="nfe-in-cfop" type="text" inputmode="numeric" maxlength="4" value="${_esc(cfop)}" style="width:4.2rem" aria-label="CFOP item ${idx + 1}" oninput="NFeService._markFiscalItensDirty()"></td>
        <td style="padding:4px;border-bottom:1px solid var(--border,#eee);vertical-align:middle"><input class="nfe-in-un" type="text" maxlength="6" value="${_esc(uni)}" style="width:3.5rem" aria-label="Unidade item ${idx + 1}" oninput="NFeService._markFiscalItensDirty()"></td>
        <td style="padding:4px;border-bottom:1px solid var(--border,#eee);vertical-align:middle"><input class="nfe-in-csosn" type="text" inputmode="numeric" maxlength="4" value="${_esc(csosn)}" style="width:3.5rem" placeholder="102" aria-label="CSOSN item ${idx + 1}" oninput="NFeService._markFiscalItensDirty()"></td>
        <td style="padding:4px;border-bottom:1px solid var(--border,#eee);vertical-align:middle"><input class="nfe-in-origem" type="number" min="0" max="8" step="1" value="${_esc(origem)}" style="width:3rem" aria-label="Origem item ${idx + 1}" oninput="NFeService._markFiscalItensDirty()"></td>
      </tr>`;
    }).join('');
    host.innerHTML = `<table style="width:100%;border-collapse:collapse;min-width:520px"><thead><tr>
      <th align="left" style="padding:6px;border-bottom:1px solid var(--border,#ddd);font-size:11px">Descrição</th>
      <th align="left" style="padding:6px;border-bottom:1px solid var(--border,#ddd);font-size:11px">NCM</th>
      <th align="left" style="padding:6px;border-bottom:1px solid var(--border,#ddd);font-size:11px">CFOP</th>
      <th align="left" style="padding:6px;border-bottom:1px solid var(--border,#ddd);font-size:11px">Un.</th>
      <th align="left" style="padding:6px;border-bottom:1px solid var(--border,#ddd);font-size:11px">CSOSN</th>
      <th align="left" style="padding:6px;border-bottom:1px solid var(--border,#ddd);font-size:11px">Orig.</th>
    </tr></thead><tbody>${rows}</tbody></table>`;
  }

  function _montarItensOverrideBody() {
    const tipo = document.getElementById('nfe-tipo')?.value || 'nfe';
    if (tipo === 'nfse' || !_orcSnapshot?.itens?.length) return undefined;
    const host = document.getElementById('nfe-itens-fiscais');
    if (!host) return undefined;
    const trs = host.querySelectorAll('tr[data-nfe-item-row]');
    if (trs.length !== _orcSnapshot.itens.length) return undefined;
    const out = [];
    for (let i = 0; i < _orcSnapshot.itens.length; i++) {
      const it = _orcSnapshot.itens[i];
      const tr = trs[i];
      if (!tr || String(it.id) !== tr.getAttribute('data-item-id')) return undefined;
      const ncmRaw = tr.querySelector('.nfe-in-ncm')?.value?.trim().replace(/\D/g, '').slice(0, 8);
      const cfopRaw = tr.querySelector('.nfe-in-cfop')?.value?.trim().replace(/\D/g, '').slice(0, 4);
      const un = (tr.querySelector('.nfe-in-un')?.value || 'UN').trim().slice(0, 6) || 'UN';
      const csRaw = tr.querySelector('.nfe-in-csosn')?.value?.trim().replace(/\D/g, '').slice(0, 4);
      const oRaw = tr.querySelector('.nfe-in-origem')?.value?.trim();
      let origem = null;
      if (oRaw !== '' && oRaw != null && !Number.isNaN(Number(oRaw))) origem = parseInt(oRaw, 10);
      const codigo_produto = it.servico && it.servico.id != null ? String(it.servico.id) : String(it.id);
      const qtd = Number(it.quantidade);
      const vu = Number(it.valor_unit);
      const tot = it.total != null ? Number(it.total) : (Number.isFinite(qtd) && Number.isFinite(vu) ? Math.round(qtd * vu * 100) / 100 : 0);
      out.push({
        descricao: it.descricao || 'Item',
        quantidade: qtd,
        valor_unit: vu,
        total: tot,
        ncm: ncmRaw || null,
        cfop: cfopRaw || null,
        unidade: un,
        csosn: csRaw || null,
        origem,
        codigo_produto,
      });
    }
    return out;
  }

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

  function _fmtDoc(raw) {
    const d = String(raw || '').replace(/\D/g, '');
    if (d.length === 14) return _fmtCNPJExibicao(d);
    if (d.length === 11) return _esc(d.replace(/^(\d{3})(\d{3})(\d{3})(\d{2})$/, '$1.$2.$3-$4'));
    return _esc(raw || '—');
  }

  function _linhasEndereco(end) {
    if (!end || typeof end !== 'object') return '—';
    const p1 = [end.logradouro, end.numero, end.complemento].filter(Boolean).join(', ');
    const p2 = [end.bairro, end.cidade, end.uf].filter(Boolean).join(' — ');
    const p3 = end.cep ? `CEP ${end.cep}` : '';
    const p4 = end.codigoMunicipio ? `Mun. IBGE: ${end.codigoMunicipio}` : '';
    return [p1, p2, [p3, p4].filter(Boolean).join(' · ')].filter((x) => x && String(x).trim()).join('\n') || '—';
  }

  function _corpoPreparar() {
    const tipo = document.getElementById('nfe-tipo')?.value || 'nfe';
    const natureza = _naturezaOperacaoResolvida();
    const serie = (document.getElementById('nfe-serie')?.value || '').trim();
    const codigoServico = (document.getElementById('nfe-codigo-servico')?.value || '').trim();
    const aliquotaIss = document.getElementById('nfe-aliquota-iss')?.value;
    const body = { orcamento_id: _orcamentoId, tipo, auto_fill: true };
    if (natureza) body.natureza_operacao = natureza;
    if (serie) body.serie = serie;
    if (tipo === 'nfse') {
      if (codigoServico) body.codigo_servico_lc116 = codigoServico;
      if (aliquotaIss !== '' && aliquotaIss != null && !Number.isNaN(Number(aliquotaIss))) {
        body.aliquota_iss = Number(aliquotaIss);
      }
    } else if (_fiscalItensDirty) {
      const ov = _montarItensOverrideBody();
      if (ov && ov.length) body.itens_override = ov;
    }
    return body;
  }

  function _renderContextoOrcamento(data, cfgFiscal) {
    const host = document.getElementById('nfe-contexto-orcamento');
    if (!host) return;
    if (!data) {
      host.innerHTML = '<p style="margin:0;color:var(--muted,#666);font-size:12px">Não foi possível carregar dados do orçamento.</p>';
      return;
    }
    const cli = data.cliente || {};
    const doc = cli.cnpj || cli.cpf || '';
    const itens = Array.isArray(data.itens) ? data.itens : [];
    const linhasItens = itens.length
      ? `<table style="width:100%;border-collapse:collapse;font-size:12px;margin-top:8px"><thead><tr>
          <th style="text-align:left;border-bottom:1px solid var(--border,#ddd);padding:4px">Material/Serviço</th>
          <th style="text-align:right;border-bottom:1px solid var(--border,#ddd);padding:4px">Qtd</th>
          <th style="text-align:right;border-bottom:1px solid var(--border,#ddd);padding:4px">V. unit.</th>
          <th style="text-align:right;border-bottom:1px solid var(--border,#ddd);padding:4px">Total</th>
        </tr></thead><tbody>
        ${itens.map((it) => `<tr>
          <td style="padding:4px;border-bottom:1px solid var(--border,#eee)">${_esc(it.descricao || '—')}</td>
          <td style="padding:4px;text-align:right;border-bottom:1px solid var(--border,#eee)">${_esc(String(it.quantidade ?? '—'))}</td>
          <td style="padding:4px;text-align:right;border-bottom:1px solid var(--border,#eee)">${_fmtBRL(it.valor_unit)}</td>
          <td style="padding:4px;text-align:right;border-bottom:1px solid var(--border,#eee)">${_fmtBRL(it.total)}</td>
        </tr>`).join('')}
      </tbody></table>`
      : '<p style="margin:6px 0 0;font-size:12px;color:var(--muted,#666)">Sem materiais/itens no orçamento.</p>';

    host.innerHTML = `
      <div style="font-size:12px;display:grid;grid-template-columns:1fr;gap:6px">
        <div><strong>Cliente:</strong> ${_esc(cli.nome || cli.razao_social || '—')}</div>
        <div><strong>CPF/CNPJ:</strong> ${_fmtDoc(doc)}</div>
        <div><strong>Endereço:</strong> ${_esc(_linhasEndereco(cli))}</div>
        <div><strong>Total orçamento:</strong> ${_fmtBRL(data.total)}</div>
        <div><strong>Emitente (fiscal):</strong> CNPJ ${_fmtDoc(cfgFiscal?.cnpj || '—')} · Ambiente ${_esc(cfgFiscal?.nfe_ambiente || '—')}</div>
      </div>
      ${linhasItens}
    `;
  }

  async function _carregarContextoOrcamento() {
    const host = document.getElementById('nfe-contexto-orcamento');
    if (host) host.innerHTML = '<p style="margin:0;color:var(--muted,#666);font-size:12px">Carregando dados fiscais e materiais...</p>';
    _limparFiscalEfetivoPreparar();
    try {
      const [orc, cfg] = await Promise.all([
        api.get(`/orcamentos/${_orcamentoId}`),
        api.get('/notas-fiscais/configuracao'),
      ]);
      const orcData = orc?.data || orc;
      _orcSnapshot = orcData;
      _fiscalItensDirty = false;
      _renderContextoOrcamento(orcData, cfg?.data || cfg);
      _renderTabelaFiscalItens();
    } catch (e) {
      _orcSnapshot = null;
      _limparFiscalEfetivoPreparar();
      if (host) host.innerHTML = `<p style="margin:0;color:#ef4444;font-size:12px">Erro ao carregar contexto: ${_esc(e?.message || 'tente novamente')}</p>`;
      _renderTabelaFiscalItens();
    }
  }

  async function abrirModal(orcamentoId) {
    _orcamentoId = orcamentoId;
    _orcSnapshot = null;
    _fiscalItensDirty = false;
    _limparFiscalEfetivoPreparar();
    const modal = document.getElementById('modal-nfe');
    if (!modal) return;
    const tipoSel = document.getElementById('nfe-tipo');
    if (tipoSel) tipoSel.value = 'nfe';
    const outroNat = document.getElementById('nfe-natureza-outro');
    if (outroNat) outroNat.value = '';
    _toggleCamposNfse();
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
    const areaPrep = document.getElementById('nfe-prep-resultado');
    if (areaPrep) areaPrep.innerHTML = '';
    await Promise.all([carregarNotasExistentes(orcamentoId), _carregarContextoOrcamento()]);
    await _preparar();
  }

  function fecharModal() {
    const modal = document.getElementById('modal-nfe');
    if (modal) {
      modal.classList.remove('open');
      modal.setAttribute('aria-hidden', 'true');
    }
    const statusMsg = document.getElementById('nfe-status-msg');
    if (statusMsg) statusMsg.textContent = '';
    const outroNat = document.getElementById('nfe-natureza-outro');
    if (outroNat) outroNat.value = '';
    const wrapOutro = document.getElementById('nfe-natureza-outro-wrap');
    if (wrapOutro) wrapOutro.style.display = 'none';
    _orcamentoId = null;
    _orcSnapshot = null;
    _fiscalItensDirty = false;
    _limparFiscalEfetivoPreparar();
    _preparadoOk = false;
    const fiHost = document.getElementById('nfe-itens-fiscais');
    if (fiHost) fiHost.innerHTML = '';
    const fiBloco = document.getElementById('nfe-bloco-itens-fiscal');
    if (fiBloco) fiBloco.style.display = 'none';
    const btnEmitir = document.getElementById('btn-emitir-nfe');
    if (btnEmitir) btnEmitir.disabled = true;
    const areaPrep = document.getElementById('nfe-prep-resultado');
    if (areaPrep) areaPrep.innerHTML = '';
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
    const natureza = _naturezaOperacaoResolvida();
    const serie = document.getElementById('nfe-serie')?.value || '1';
    const codigoServico = document.getElementById('nfe-codigo-servico')?.value;
    const aliquotaIss = document.getElementById('nfe-aliquota-iss')?.value;
    const btn = document.getElementById('btn-emitir-nfe');
    const statusMsg = document.getElementById('nfe-status-msg');

    if (!_preparadoOk) {
      if (statusMsg) statusMsg.textContent = 'Use «Verificar» primeiro e corrija bloqueios, se houver.';
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
    if (_fiscalItensDirty && tipo !== 'nfse') {
      const ov = _montarItensOverrideBody();
      if (ov && ov.length) payload.itens_override = ov;
    }

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

      const tipoAtual = document.getElementById('nfe-tipo')?.value || 'nfe';
      if (tipoAtual === 'nfe' || tipoAtual === 'nfce') {
        _aplicarFiscalDoPayloadPreparar(resultado.payload_preview);
        _renderTabelaFiscalItens();
      }
    } catch (e) {
      _preparadoOk = false;
      if (btnEmitir) btnEmitir.disabled = true;
      if (areaPrep) areaPrep.innerHTML = `<div style="color:#ef4444;font-size:12px">❌ Erro ao verificar: ${e.message || 'Tente novamente'}</div>`;
    } finally {
      if (btnVerificar) { btnVerificar.disabled = false; btnVerificar.textContent = '🔍 Verificar'; }
    }
  }

  function _toggleCamposNfse() {
    _limparFiscalEfetivoPreparar();
    const tipo = document.getElementById('nfe-tipo')?.value || 'nfe';
    const campos = document.getElementById('campos-nfse');
    if (!campos) return;
    campos.style.display = tipo === 'nfse' ? 'flex' : 'none';
    const outroNat = document.getElementById('nfe-natureza-outro');
    if (outroNat) outroNat.value = '';
    _preencherSelectNatureza(tipo);
    _atualizarDicaTipo();
    _onNaturezaSelectChange();
    _renderTabelaFiscalItens();
    _preparadoOk = false;
    const btnEmitir = document.getElementById('btn-emitir-nfe');
    if (btnEmitir) btnEmitir.disabled = true;
    const areaPrep = document.getElementById('nfe-prep-resultado');
    if (areaPrep) areaPrep.innerHTML = '';
  }

  function _badgeClass(status) {
    const map = { emitida: 'success', erro: 'danger', cancelada: 'warning', processando: 'info', pendente: 'secondary' };
    return map[status] || 'secondary';
  }

  return {
    abrirModal,
    fecharModal,
    emitir,
    _cancelar,
    verificar: _preparar,
    _toggleCamposNfse,
    _onNaturezaSelectChange,
    _invalidatePrep,
    _markFiscalItensDirty,
  };
})();

// Expõe no escopo global para uso em onclick= attributes
window.NFeService = NFeService;
