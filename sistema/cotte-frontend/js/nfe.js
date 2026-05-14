/**
 * nfe.js — Emissão de NF-e/NFC-e/NFS-e a partir de orçamentos.
 * Usa api.get / api.post do padrão COTTE (js/api.js).
 */
const NFeService = (() => {
  let _orcamentoId = null;
  let _preparadoOk = false;
  /** Última config fiscal (GET /notas-fiscais/configuracao) para ambiente no card de emitente. */
  let _lastCfgFiscal = null;
  /** Snapshot do GET /orcamentos/{id} (para montar itens_override). */
  let _orcSnapshot = null;
  /** True se o operador alterou NCM/CFOP/unidade/CSOSN/origem na tabela desta sessão. */
  let _fiscalItensDirty = false;
  /** Valores fiscais efetivos do último preparar (payload Focus `items`), por id do item do orçamento. */
  let _fiscalEfetivoPorItemId = {};
  /** Delegação de clique em «Ir ao campo» (checklist) — instalada uma vez. */
  let _nfeScrollDelegationInstalled = false;

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

  function _fiscalValoresLinha(it) {
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
    return { ncm, cfop, uni, csosn, origem };
  }

  /** Cartões por item (sem scroll horizontal); mesmos inputs/classes que _montarItensOverrideBody espera. */
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
    const fld = (lab, full, inner) =>
      `<div style="min-width:0"><label style="display:block;font-size:10px;color:var(--muted,#666);margin-bottom:2px" title="${_esc(full)}">${lab}</label>${inner}</div>`;
    const cards = itens.map((it, idx) => {
      const { ncm, cfop, uni, csosn, origem } = _fiscalValoresLinha(it);
      const desc = _esc((it.descricao || '—').slice(0, 140));
      return `<div data-nfe-item-row data-item-id="${it.id}" class="nfe-fiscal-item-card" style="border:1px solid var(--border,#e5e5e5);border-radius:8px;padding:10px 12px;margin-bottom:10px;background:var(--surface1,rgba(0,0,0,0.02))">
        <div style="font-size:12px;font-weight:600;margin-bottom:8px;line-height:1.35;color:var(--text)">${desc}</div>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(5.5rem,1fr));gap:8px 10px;align-items:end">
          ${fld('NCM', 'Nomenclatura Comum do Mercosul (8 dígitos)', `<input class="nfe-in-ncm" type="text" inputmode="numeric" maxlength="8" value="${_esc(ncm)}" style="width:100%;max-width:7.5rem;box-sizing:border-box;font-size:12px" aria-label="NCM item ${idx + 1}" oninput="NFeService._markFiscalItensDirty()">`)}
          ${fld('CFOP', 'Código fiscal de operações e prestações', `<input class="nfe-in-cfop" type="text" inputmode="numeric" maxlength="4" value="${_esc(cfop)}" style="width:100%;max-width:5rem;box-sizing:border-box;font-size:12px" aria-label="CFOP item ${idx + 1}" oninput="NFeService._markFiscalItensDirty()">`)}
          ${fld('Un.', 'Unidade comercial', `<input class="nfe-in-un" type="text" maxlength="6" value="${_esc(uni)}" style="width:100%;max-width:4rem;box-sizing:border-box;font-size:12px" aria-label="Unidade item ${idx + 1}" oninput="NFeService._markFiscalItensDirty()">`)}
          ${fld('CSOSN', 'Código de Situação da Operação — Simples Nacional', `<input class="nfe-in-csosn" type="text" inputmode="numeric" maxlength="4" value="${_esc(csosn)}" style="width:100%;max-width:4rem;box-sizing:border-box;font-size:12px" placeholder="102" aria-label="CSOSN item ${idx + 1}" oninput="NFeService._markFiscalItensDirty()">`)}
          ${fld('Origem', 'Origem da mercadoria (0–8)', `<input class="nfe-in-origem" type="number" min="0" max="8" step="1" value="${_esc(origem)}" style="width:100%;max-width:3.5rem;box-sizing:border-box;font-size:12px" aria-label="Origem da mercadoria item ${idx + 1}" oninput="NFeService._markFiscalItensDirty()">`)}
        </div>
      </div>`;
    }).join('');
    host.innerHTML = `<div class="nfe-fiscal-cards" style="max-width:100%">${cards}</div>`;
  }

  function _montarItensOverrideBody() {
    const tipo = document.getElementById('nfe-tipo')?.value || 'nfe';
    if (tipo === 'nfse' || !_orcSnapshot?.itens?.length) return undefined;
    const host = document.getElementById('nfe-itens-fiscais');
    if (!host) return undefined;
    const rows = host.querySelectorAll('[data-nfe-item-row]');
    if (rows.length !== _orcSnapshot.itens.length) return undefined;
    const out = [];
    for (let i = 0; i < _orcSnapshot.itens.length; i++) {
      const it = _orcSnapshot.itens[i];
      const row = rows[i];
      if (!row || String(it.id) !== row.getAttribute('data-item-id')) return undefined;
      const ncmRaw = row.querySelector('.nfe-in-ncm')?.value?.trim().replace(/\D/g, '').slice(0, 8);
      const cfopRaw = row.querySelector('.nfe-in-cfop')?.value?.trim().replace(/\D/g, '').slice(0, 4);
      const un = (row.querySelector('.nfe-in-un')?.value || 'UN').trim().slice(0, 6) || 'UN';
      const csRaw = row.querySelector('.nfe-in-csosn')?.value?.trim().replace(/\D/g, '').slice(0, 4);
      const oRaw = row.querySelector('.nfe-in-origem')?.value?.trim();
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

  function _tituloGrupoChecklist(grupo) {
    const g = String(grupo || 'outros').toLowerCase();
    const map = {
      geral: 'Cadastro e orçamento',
      nfe: 'Regras da NF-e / NFC-e',
      nfce: 'Regras da NF-e / NFC-e',
      nfse: 'Regras da NFS-e',
      outros: 'Demais verificações',
    };
    return map[g] || map.outros;
  }

  function _checklistChaveDataAttr(chave) {
    const s = String(chave == null ? '' : chave).trim();
    return /^[a-z0-9_]+$/i.test(s) ? s : '';
  }

  function _countChecklistFalhas(checklist) {
    if (!Array.isArray(checklist) || !checklist.length) return 0;
    return checklist.filter((raw) => raw && typeof raw === 'object' && raw.ok !== true).length;
  }

  /** Itens com `ok` verdadeiro — `<details>` compacto (não polui a vista principal). */
  function _renderChecklistValidadosDetails(checklist) {
    if (!Array.isArray(checklist) || !checklist.length) return '';
    const okItems = checklist.filter((raw) => raw && typeof raw === 'object' && raw.ok === true);
    if (!okItems.length) return '';
    const m = okItems.length;
    const rows = okItems
      .map((c) => {
        const g = _tituloGrupoChecklist(c.grupo);
        return `<li style="font-size:11px;line-height:1.35;margin:3px 0;color:var(--text);list-style:none;padding-left:0">
          <span style="color:#15803d;font-weight:600" aria-hidden="true">✓ </span>${_esc(c.titulo || '')}
          <span style="color:var(--muted,#888);font-size:10px"> · ${_esc(g)}</span>
        </li>`;
      })
      .join('');
    return `<details class="nfe-checklist-validados" style="margin-top:10px;border:1px solid var(--border,#e5e5e5);border-radius:8px;padding:8px 10px;background:var(--surface2,rgba(0,0,0,0.02))">
      <summary style="cursor:pointer;font-size:12px;font-weight:600;color:var(--text);user-select:none">Ver tudo que foi validado (${m})</summary>
      <ul style="margin:8px 0 0;padding:0">${rows}</ul>
    </details>`;
  }

  function scrollParaChecklistChave(chaveRaw) {
    const chave = String(chaveRaw || '').trim().toLowerCase();
    const modal = document.getElementById('modal-nfe');
    const fallbackBody = modal?.querySelector('.modal-body');

    function ir(el, focusEl) {
      if (!el) return false;
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      if (focusEl && typeof focusEl.focus === 'function') {
        try {
          focusEl.focus({ preventScroll: true });
        } catch (_) {
          focusEl.focus();
        }
      }
      return true;
    }

    if (chave === 'natureza_operacao' || chave === 'natureza') {
      const wrap = document.getElementById('nfe-natureza-outro-wrap');
      const outro = document.getElementById('nfe-natureza-outro');
      const sel = document.getElementById('nfe-natureza');
      if (wrap && wrap.style.display === 'block' && outro) return ir(outro, outro);
      return ir(sel, sel);
    }
    if (chave === 'nota_autorizada_equivalente') {
      const det = document.getElementById('nfe-detalhes-avancados');
      const ser = document.getElementById('nfe-serie');
      if (det) det.open = true;
      return ir(ser || det, ser || null);
    }
    if (chave === 'tipo_nota') {
      const el = document.getElementById('nfe-tipo');
      return ir(el, el);
    }

    const chavesItensNfe = new Set([
      'ncm',
      'cfop',
      'unidades',
      'quantidade_valor',
      'icms',
      'pis_cofins',
      'frete',
      'consumidor_final',
      'presenca_comprador',
    ]);
    if (chavesItensNfe.has(chave)) {
      const bloco = document.getElementById('nfe-bloco-itens-fiscal');
      const host = document.getElementById('nfe-itens-fiscais');
      const firstIn = host && host.querySelector('input.nfe-in-ncm');
      const alvo = bloco?.style.display !== 'none' && host ? host : bloco;
      return ir(alvo || bloco, firstIn || null);
    }

    if (chave === 'item_lista') {
      const el = document.getElementById('nfe-codigo-servico');
      return ir(el, el);
    }
    if (chave === 'aliquota_iss') {
      const el = document.getElementById('nfe-aliquota-iss');
      return ir(el, el);
    }
    if (chave === 'iss_retido') {
      const campos = document.getElementById('campos-nfse');
      return ir(campos, null);
    }

    const chavesContexto = new Set([
      'orcamento_aprovado',
      'cliente_documento',
      'cliente_endereco',
      'emitente_configurado',
      'token_focus',
      'ambiente',
      'referencia',
      'valor_total',
      'data_emissao',
      'prestador',
      'tomador',
      'municipio_prestacao',
      'valor_servico',
      'descricao_servico',
      'optante_sn',
    ]);
    if (chavesContexto.has(chave)) {
      const ctx = document.getElementById('nfe-contexto-orcamento');
      return ir(ctx, null);
    }

    if (fallbackBody) {
      fallbackBody.scrollIntoView({ behavior: 'smooth', block: 'start' });
      return true;
    }
    return false;
  }

  function _ensureNfeScrollDelegation() {
    if (_nfeScrollDelegationInstalled) return;
    _nfeScrollDelegationInstalled = true;
    document.addEventListener('click', (ev) => {
      const modal = document.getElementById('modal-nfe');
      if (!modal || !modal.classList.contains('open')) return;
      const btn = ev.target.closest('[data-nfe-scroll-chave]');
      if (!btn || !modal.contains(btn)) return;
      const ck = btn.getAttribute('data-nfe-scroll-chave');
      if (!ck) return;
      ev.preventDefault();
      const ok = scrollParaChecklistChave(ck);
      if (!ok) {
        try {
          alert('Campo não associado a um atalho neste modal. Corrija usando o título da pendência como guia.');
        } catch (_) { /* ignora */ }
      }
    });
  }

  /** Lista estruturada do backend (evita duplicar linhas idênticas aos bloqueios quando o checklist veio preenchido). */
  /** Só pendências (`ok` falso): itens aprovados não aparecem na UI. */
  function _renderChecklistHtml(checklist) {
    if (!Array.isArray(checklist) || !checklist.length) return '';
    const falhas = checklist.filter((raw) => raw && typeof raw === 'object' && raw.ok !== true);
    if (!falhas.length) return '';
    const n = falhas.length;
    const byGroup = {};
    falhas.forEach((raw) => {
      const g = String(raw.grupo || 'outros').toLowerCase();
      if (!byGroup[g]) byGroup[g] = [];
      byGroup[g].push(raw);
    });
    const order = ['geral', 'nfe', 'nfce', 'nfse', 'outros'];
    const keys = Object.keys(byGroup).sort(
      (a, b) => (order.includes(a) ? order.indexOf(a) : 99) - (order.includes(b) ? order.indexOf(b) : 99),
    );
    let html = '<div id="nfe-checklist-host" style="margin-top:10px;border:1px solid var(--border,#e5e5e5);border-radius:8px;padding:10px 12px;background:var(--surface2,rgba(0,0,0,0.02))">';
    html += `<p style="margin:0 0 8px;font-size:12px;font-weight:700">Pendências na verificação (${n})</p>`;
    keys.forEach((g) => {
      const items = byGroup[g];
      if (!items || !items.length) return;
      html += `<div style="margin-top:6px"><div style="font-size:11px;font-weight:600;color:var(--muted,#666);text-transform:uppercase;letter-spacing:0.02em;margin-bottom:6px">${_esc(_tituloGrupoChecklist(g))}</div>`;
      items.forEach((c) => {
        const det = (c.detalhe && String(c.detalhe).trim())
          ? `<div style="font-size:11px;color:var(--muted,#666);margin-top:3px">${_esc(String(c.detalhe))}</div>`
          : '';
        const ckAttr = _checklistChaveDataAttr(c.chave);
        const btnIr =
          ckAttr !== ''
            ? `<button type="button" class="btn btn-sm btn-ghost" style="flex-shrink:0;font-size:11px;padding:4px 8px;white-space:nowrap" data-nfe-scroll-chave="${_esc(ckAttr)}">Ir ao campo</button>`
            : '';
        html += `<div style="display:flex;align-items:flex-start;gap:8px;padding:6px 0;border-bottom:1px solid var(--border,#eee)">
          <span style="flex-shrink:0;font-size:10px;font-weight:700;padding:2px 7px;border-radius:4px;background:rgba(239,68,68,0.12);color:#b91c1c">Pendente</span>
          <div style="flex:1;min-width:0;font-size:12px;line-height:1.4"><div>${_esc(c.titulo || '')}</div>${det}</div>
          ${btnIr}
        </div>`;
      });
      html += '</div>';
    });
    html += '</div>';
    return html;
  }

  function _renderEmitentePreviewBloco(ep, cfgFiscal) {
    if (!ep || typeof ep !== 'object') return '';
    const amb = cfgFiscal && cfgFiscal.nfe_ambiente != null ? String(cfgFiscal.nfe_ambiente) : '';
    const raz = (ep.razao_social || '').trim() || '—';
    const cnpjFmt = _fmtDoc(ep.cnpj);
    const ie = (ep.inscricao_estadual || '').trim();
    const ref = (ep.referencia_orcamento || '').trim();
    const crt = (ep.crt_descricao || '').trim();
    return `<div id="nfe-emitente-preview" style="margin-bottom:10px;padding:10px 12px;border-radius:8px;border:1px solid var(--border,#e5e5e5);background:var(--surface1,rgba(0,0,0,0.03))">
      <p style="margin:0 0 6px;font-size:11px;font-weight:700;color:var(--muted,#666)">Emitente na prévia do envio</p>
      <div style="font-size:12px;line-height:1.45">
        <div><strong>${_esc(raz)}</strong></div>
        <div>CNPJ: ${cnpjFmt}${ie ? ` · IE: ${_esc(ie)}` : ''}</div>
        ${crt ? `<div>${_esc(crt)}</div>` : ''}
        ${ref ? `<div>Referência: ${_esc(ref)}</div>` : ''}
        ${amb ? `<div>Ambiente: ${_esc(amb)}</div>` : ''}
      </div>
    </div>`;
  }

  function _fmtDataListaNota(iso) {
    if (!iso) return '';
    try {
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return '';
      return d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
    } catch (_) {
      return '';
    }
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
      ? `<p style="margin:12px 0 6px;font-size:12px;font-weight:700;color:var(--text)">Itens do orçamento</p>
        <table style="width:100%;border-collapse:collapse;font-size:12px"><thead><tr>
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
      : '<p style="margin:12px 0 0;font-size:12px;color:var(--muted,#666)">Sem materiais/itens no orçamento.</p>';

    host.innerHTML = `
      <p style="margin:0 0 8px;font-size:12px;font-weight:700;color:var(--text)">Destinatário (cliente)</p>
      <div style="font-size:12px;display:grid;grid-template-columns:1fr;gap:6px">
        <div><strong>Nome:</strong> ${_esc(cli.nome || cli.razao_social || '—')}</div>
        <div><strong>CPF/CNPJ:</strong> ${_fmtDoc(doc)}</div>
        <div style="white-space:pre-line"><strong>Endereço:</strong> ${_esc(_linhasEndereco(cli))}</div>
        <div><strong>Total do orçamento:</strong> ${_fmtBRL(data.total)}</div>
      </div>
      <p style="margin:12px 0 6px;font-size:12px;font-weight:700;color:var(--text)">Empresa emissora (cadastro fiscal)</p>
      <div style="font-size:12px;line-height:1.45">
        <div><strong>CNPJ:</strong> ${_fmtDoc(cfgFiscal?.cnpj || '')}</div>
        <div><strong>Ambiente NF-e:</strong> ${_esc(cfgFiscal?.nfe_ambiente || '—')}</div>
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
      const cfgData = cfg?.data || cfg;
      _lastCfgFiscal = cfgData && typeof cfgData === 'object' ? cfgData : null;
      _orcSnapshot = orcData;
      _fiscalItensDirty = false;
      _renderContextoOrcamento(orcData, cfg?.data || cfg);
      _renderTabelaFiscalItens();
    } catch (e) {
      _orcSnapshot = null;
      _lastCfgFiscal = null;
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
    modal.style.display = 'flex';
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
    _setNfePollUi(0, false);
    const areaPrep = document.getElementById('nfe-prep-resultado');
    if (areaPrep) areaPrep.innerHTML = '';
    await Promise.all([carregarNotasExistentes(orcamentoId), _carregarContextoOrcamento()]);
    await _preparar();
  }

  function fecharModal() {
    const modal = document.getElementById('modal-nfe');
    if (modal) {
      modal.style.display = 'none';
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
    _lastCfgFiscal = null;
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
    _setNfePollUi(0, false);
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
    const temEmitida = notas.some((x) => x && x.status === 'emitida');
    lista.innerHTML = notas.map((n) => {
      const when = n.emitida_em || n.criado_em;
      const whenStr = _fmtDataListaNota(when);
      const numSer = n.numero
        ? `Nº ${_esc(String(n.numero))} · Série ${_esc(String(n.serie != null ? n.serie : ''))}`
        : '—';
      const msgErro = _esc(n.erro_mensagem || n.erro_codigo || '');
      const err =
        n.status === 'erro'
          ? temEmitida
            ? `<details class="nfe-hist-erro" style="margin-top:6px;font-size:12px;line-height:1.35;color:var(--danger,#dc2626)">
                <summary style="cursor:pointer;font-weight:600;color:var(--danger,#dc2626)">Histórico de erro · ${_esc(whenStr || 'tentativa')}</summary>
                <div style="margin-top:6px;padding-top:4px;border-top:1px solid var(--border,#fecaca)">${msgErro}</div>
              </details>`
            : `<div style="font-size:12px;color:var(--danger,#dc2626);margin-top:4px;line-height:1.35">Erro: ${msgErro}</div>`
          : '';
      const acoes = [
        n.danfe_url ? `<a href="${n.danfe_url}" target="_blank" rel="noopener" class="btn btn-ghost btn-sm">DANFE</a>` : '',
        n.xml_url ? `<a href="${n.xml_url}" target="_blank" rel="noopener" class="btn btn-ghost btn-sm">XML</a>` : '',
        n.status === 'emitida' ? `<button type="button" class="btn btn-ghost btn-sm" onclick="NFeService._cancelar(${n.id})">Cancelar</button>` : '',
      ].filter(Boolean).join(' ');
      return `<div class="nfe-item" style="padding:10px 0;border-bottom:1px solid var(--border,#eee)">
        <div style="display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px">
          <span style="font-weight:700;text-transform:uppercase;font-size:11px;letter-spacing:0.04em">${_esc(n.tipo || '')}</span>
          <span style="font-size:13px;color:var(--text)">${numSer}</span>
          <span class="badge badge-${_badgeClass(n.status)}">${_esc(n.status || '')}</span>
          ${whenStr ? `<span style="font-size:11px;color:var(--muted,#666);margin-left:auto">${_esc(whenStr)}</span>` : ''}
        </div>
        ${acoes ? `<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:6px">${acoes}</div>` : ''}
        ${err}
      </div>`;
    }).join('');
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
      _setNfePollUi(0, false);
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

  function _setNfePollUi(tentativas, active) {
    const pollWrap = document.getElementById('nfe-poll-wrap');
    const pollPr = document.getElementById('nfe-poll-progress');
    const pollCap = document.getElementById('nfe-poll-caption');
    if (!pollWrap || !pollPr) return;
    if (!active) {
      pollWrap.style.display = 'none';
      return;
    }
    pollWrap.style.display = 'block';
    pollPr.max = NFE_STATUS_POLL_MAX;
    pollPr.value = Math.min(Math.max(0, tentativas), NFE_STATUS_POLL_MAX);
    if (pollCap) {
      const secs = Math.round((tentativas + 1) * (NFE_STATUS_INTERVAL_MS / 1000));
      pollCap.textContent = `Aguardando retorno da SEFAZ/Focus… tentativa ${tentativas + 1} de ${NFE_STATUS_POLL_MAX} (~${secs}s decorridos).`;
    }
  }

  /**
   * Após a nota ser autorizada: lista de notas já mostra erros antigos em `<details>`;
   * aqui contrai/remove o painel «Analisar erro» no resultado da verificação.
   */
  function _contrairPrepPosEmissaoOk() {
    const area = document.getElementById('nfe-prep-resultado');
    if (!area) return;
    const btn = document.getElementById('btn-analisar-erro-nfe');
    const analise = document.getElementById('nfe-analise-resultado');
    if (!btn && !analise) return;
    const inner = analise && String(analise.innerHTML || '').trim();
    if (inner) {
      area.innerHTML = `<details class="nfe-prep-hist-erro" style="margin-top:8px;border:1px solid var(--border,#e5e5e5);border-radius:8px;padding:8px 10px;background:var(--surface2,rgba(0,0,0,0.02))">
        <summary style="cursor:pointer;font-size:12px;font-weight:600;color:var(--muted,#666);user-select:none">Histórico da análise de erro</summary>
        <div style="margin-top:8px">${inner}</div>
      </details>`;
    } else {
      area.innerHTML = '';
    }
  }

  async function _aguardarStatus(notaId, tentativas = 0) {
    const statusMsg = document.getElementById('nfe-status-msg');
    if (tentativas > NFE_STATUS_POLL_MAX) {
      _setNfePollUi(0, false);
      try {
        await api.post(`/notas-fiscais/${notaId}/sincronizar-focus`, {});
        const resp = await api.get(`/notas-fiscais/${notaId}`);
        const notaSync = resp?.data || resp;
        if (notaSync && notaSync.status === 'emitida') {
          if (statusMsg) {
            statusMsg.textContent = `✓ NF emitida com sucesso! N\xfamero: ${notaSync.numero || '—'}`;
          }
          if (_orcamentoId) await carregarNotasExistentes(_orcamentoId);
          _contrairPrepPosEmissaoOk();
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
    _setNfePollUi(tentativas, true);
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
      _setNfePollUi(0, false);
      if (statusMsg) statusMsg.textContent = `✓ NF emitida com sucesso! N\xfamero: ${nota.numero || '—'}`;
      if (_orcamentoId) await carregarNotasExistentes(_orcamentoId);
      _contrairPrepPosEmissaoOk();
    } else if (nota.status === 'erro') {
      _setNfePollUi(0, false);
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
        <button type="button" id="btn-analisar-erro-nfe" class="btn btn-sm btn-warning" style="width:100%">
          Analisar Erro e Ver O Que Corrigir
        </button>
        <div id="nfe-analise-resultado" style="margin-top:8px"></div>
      </div>`;
    const btnAn = document.getElementById('btn-analisar-erro-nfe');
    if (!btnAn) return;
    btnAn.onclick = async function() {
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

      const checklist = Array.isArray(resultado.checklist) ? resultado.checklist : [];
      const temChecklist = checklist.length > 0;
      const bloqueios = Array.isArray(resultado.bloqueios) ? resultado.bloqueios : [];
      const avisos = Array.isArray(resultado.avisos) ? resultado.avisos : [];
      const falhasCount = _countChecklistFalhas(checklist);
      const colapsarAvisos = avisos.length > 0 && falhasCount === 0 && bloqueios.length === 0;
      const resumoTxt = (resultado.resumo && String(resultado.resumo).trim()) || (_preparadoOk ? 'Pronto para emitir' : 'Verificação concluída');
      const resumoCor = _preparadoOk ? '#15803d' : '#b45309';
      const resumoPeso = _preparadoOk ? '600' : '600';

      const partes = [];
      const epHtml = _renderEmitentePreviewBloco(resultado.emitente_preview, _lastCfgFiscal);
      if (epHtml) partes.push(epHtml);

      partes.push(
        `<div style="font-size:12px;font-weight:${resumoPeso};margin:0 0 8px;line-height:1.35;color:${resumoCor}">${_esc(resumoTxt)}</div>`,
      );

      if (temChecklist) {
        const pendHtml = _renderChecklistHtml(checklist);
        const valHtml = _renderChecklistValidadosDetails(checklist);
        if (pendHtml || valHtml) partes.push(`${pendHtml}${valHtml}`);
      } else if (bloqueios.length) {
        partes.push(
          bloqueios.map(b =>
            `<div style="color:#ef4444;font-size:12px;padding:4px 0">❌ ${_esc(b)}</div>`,
          ).join(''),
        );
      }

      if (colapsarAvisos) {
        const textoCompleto = avisos.map((a) => String(a)).join(' · ');
        partes.push(
          `<div style="margin-top:8px;padding:8px 10px;background:rgba(245,158,11,0.08);border-left:3px solid #f59e0b;border-radius:4px;font-size:12px;line-height:1.35;color:#92400e;display:flex;align-items:baseline;gap:6px;min-width:0;white-space:nowrap;overflow:hidden" title="${_esc(textoCompleto)}">
            <strong style="flex-shrink:0">Resumo das sugestões:</strong>
            <span style="min-width:0;overflow:hidden;text-overflow:ellipsis">${_esc(textoCompleto)}</span>
          </div>`,
        );
      } else if (avisos.length) {
        partes.push(
          avisos.map(a =>
            `<div style="color:#f59e0b;font-size:12px;padding:4px 0">⚠️ ${_esc(a)}</div>`,
          ).join(''),
        );
      }

      if (_preparadoOk && !temChecklist && !bloqueios.length && !avisos.length) {
        partes.push('<div style="color:#15803d;font-size:12px;font-weight:600">✅ Nenhum bloqueio encontrado.</div>');
      }

      if (areaPrep) areaPrep.innerHTML = partes.join('');

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

  _ensureNfeScrollDelegation();

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
    scrollParaChecklistChave,
  };
})();

// Expõe no escopo global para uso em onclick= attributes
window.NFeService = NFeService;
