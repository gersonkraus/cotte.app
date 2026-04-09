/**
 * api-financeiro.js — Módulo centralizado de chamadas de API do Financeiro COTTE.
 * Usa apiRequest() global definido em api.js.
 * Todas as funções retornam Promises e lançam Error em caso de falha HTTP.
 */

/* global apiRequest */

const Financeiro = (() => {

  // ── Cache simples com TTL ─────────────────────────────────────────────────
  const _CACHE = {};
  const _TTL = { resumo: 30000, formas: 300000 }; // resumo: 30s, formas: 5min

  function _cached(key, ttl, fn) {
    const hit = _CACHE[key];
    if (hit && Date.now() - hit.t < ttl) return Promise.resolve(hit.d);
    return fn().then(d => { _CACHE[key] = { d, t: Date.now() }; return d; });
  }

  function _invalidar(key) { delete _CACHE[key]; }
  function _invalidarTudo() { Object.keys(_CACHE).forEach(k => delete _CACHE[k]); }

  // ── Formas de Pagamento ───────────────────────────────────────────────────

  function listarFormasPagamento() {
    return _cached('formas', _TTL.formas, () => apiRequest('GET', '/financeiro/formas-pagamento'));
  }

  function invalidarFormas() { _invalidar('formas'); }

  // ── Pagamentos ─────────────────────────────────────────────────────────────

  /**
   * Registra um pagamento.
   * @param {Object} dados - { orcamento_id, valor, tipo, forma_pagamento_id,
   *                           data_pagamento, observacao, comprovante_url,
   *                           parcela_numero, txid_pix }
   */
  function registrarPagamento(dados) {
    return apiRequest('POST', '/financeiro/pagamentos', dados)
      .then(r => { _invalidarTudo(); return r; });
  }

  /**
   * Lista pagamentos com filtros opcionais.
   * @param {Object} [filtros] - { orcamento_id, cliente, data_inicio, data_fim, todos, limit, offset }
   */
  function listarPagamentos(filtros = {}) {
    const params = new URLSearchParams();
    Object.entries(filtros).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') params.append(k, v);
    });
    const qs = params.toString();
    return apiRequest('GET', `/financeiro/pagamentos${qs ? '?' + qs : ''}`);
  }

  /**
   * Estorna um pagamento.
   * @param {number} pagamentoId
   * @param {string} [motivo]
   */
  function estornarPagamento(pagamentoId, motivo = '') {
    return apiRequest('POST', `/financeiro/pagamentos/${pagamentoId}/estornar`, { motivo })
      .then(r => { _invalidarTudo(); return r; });
  }

  // ── Contas Financeiras ────────────────────────────────────────────────────

  function criarConta(dados) {
    return apiRequest('POST', '/financeiro/contas', dados);
  }

  function listarContas(filtros = {}) {
    const params = new URLSearchParams();
    Object.entries(filtros).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') params.append(k, v);
    });
    const qs = params.toString();
    return apiRequest('GET', `/financeiro/contas${qs ? '?' + qs : ''}`);
  }

  function listarInadimplentes() {
    return apiRequest('GET', '/financeiro/contas/inadimplentes');
  }

  function atualizarConta(contaId, dados) {
    return apiRequest('PATCH', `/financeiro/contas/${contaId}`, dados);
  }

  // ── Dashboard ─────────────────────────────────────────────────────────────

  function resumo(params = {}) {
    // Se houver params, não usar cache
    if (Object.keys(params).length > 0) {
      const qs = new URLSearchParams(params).toString();
      return apiRequest('GET', `/financeiro/resumo?${qs}`);
    }
    return _cached('resumo', _TTL.resumo, () => apiRequest('GET', '/financeiro/resumo'));
  }

  // ── Templates ─────────────────────────────────────────────────────────────

  function listarTemplates() {
    return apiRequest('GET', '/financeiro/templates');
  }

  function atualizarTemplate(templateId, dados) {
    return apiRequest('PATCH', `/financeiro/templates/${templateId}`, dados);
  }

  // ── Despesas (Contas a Pagar) ─────────────────────────────────────────────

  function criarDespesa(dados) {
    return apiRequest('POST', '/financeiro/despesas', dados)
      .then(r => { _invalidarTudo(); return r; });
  }

  function listarDespesas(filtros = {}) {
    const params = new URLSearchParams();
    Object.entries(filtros).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') params.append(k, v);
    });
    const qs = params.toString();
    return apiRequest('GET', `/financeiro/despesas${qs ? '?' + qs : ''}`);
  }

  function atualizarDespesa(contaId, dados) {
    return apiRequest('PATCH', `/financeiro/despesas/${contaId}`, dados);
  }

  function pagarDespesa(contaId) {
    return apiRequest('POST', `/financeiro/despesas/${contaId}/pagar`, {})
      .then(r => { _invalidarTudo(); return r; });
  }

  function receberConta(contaId, dados = {}) {
    // dados pode conter valor, forma_pagamento_id, observacao, etc.
    return apiRequest('POST', `/financeiro/contas/${contaId}/receber`, dados)
      .then(r => { _invalidarTudo(); return r; });
  }

  // ── Cobrança WhatsApp ─────────────────────────────────────────────────────

  function cobrarViaWhatsapp(contaId) {
    return apiRequest('POST', `/financeiro/contas/${contaId}/cobrar`, {})
      .then(r => { _invalidar('resumo'); return r; });
  }

  function listarHistoricoCobrancas(filtros = {}) {
    const params = new URLSearchParams();
    Object.entries(filtros).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') params.append(k, v);
    });
    const qs = params.toString();
    return apiRequest('GET', `/financeiro/historico-cobrancas${qs ? '?' + qs : ''}`);
  }

  // ── Fluxo de Caixa ────────────────────────────────────────────────────────

  function fluxoCaixa(dataInicio, dataFim) {
    const params = new URLSearchParams();
    if (dataInicio) params.append('data_inicio', dataInicio);
    if (dataFim)    params.append('data_fim', dataFim);
    const qs = params.toString();
    return apiRequest('GET', `/financeiro/fluxo-caixa${qs ? '?' + qs : ''}`);
  }

  // ── Categorias de Despesas ────────────────────────────────────────────────

  let _categoriasCache = null;

  function listarCategorias(forceFetch = false) {
    if (_categoriasCache && !forceFetch) return Promise.resolve(_categoriasCache);
    return apiRequest('GET', '/financeiro/categorias').then(cats => {
      _categoriasCache = cats;
      return cats;
    });
  }

  function invalidarCategorias() { _categoriasCache = null; }

  // ── Configurações Financeiras ─────────────────────────────────────────────

  function obterConfiguracoes() {
    return apiRequest('GET', '/financeiro/configuracoes');
  }

  function salvarConfiguracoes(dados) {
    return apiRequest('PATCH', '/financeiro/configuracoes', dados)
      .then(r => { invalidarCategorias(); return r; });
  }

  // ── Expose ────────────────────────────────────────────────────────────────

  return {
    listarFormasPagamento,
    invalidarFormas,
    registrarPagamento,
    listarPagamentos,
    estornarPagamento,
    criarConta,
    listarContas,
    listarInadimplentes,
    atualizarConta,
    resumo,
    listarTemplates,
    atualizarTemplate,
    // Despesas
    criarDespesa,
    listarDespesas,
    atualizarDespesa,
    pagarDespesa,
    // Recebimentos
    receberConta,
    // Cobrança
    cobrarViaWhatsapp,
    listarHistoricoCobrancas,
    // Fluxo de caixa
    fluxoCaixa,
    // Categorias
    listarCategorias,
    invalidarCategorias,
    // Configurações
    obterConfiguracoes,
    salvarConfiguracoes,
    invalidarCache: _invalidarTudo,
  };
})();
