const assert = require('assert');
const fs = require('fs');
const path = require('path');

global.window = global;
global.escapeHtml = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
global.textToHtmlRich = (s) => `<p>${s}</p>`;

global.renderTabelaRica = () => null;
global.renderAnaliseTexto = () => 'Texto analitico fallback';
global.renderOrcamentoCardUnificado = () => 'Card de orcamento';
global.renderListaOrcamentos = () => 'Lista de orcamentos';
global.renderOperadorResultado = () => 'Resultado de operacao';
global.renderSaldoRapido = () => 'Saldo rapido';
global.renderOnboarding = () => 'Onboarding';
global.renderCatalogoSugestao = () => 'Catalogo';
global.renderSemanticContract = () => 'Contrato semantico';

const renderTypesPath = path.join(__dirname, '../../sistema/cotte-frontend/js/assistente-ia-render-types.js');
const renderTypesCode = fs.readFileSync(renderTypesPath, 'utf8');

new Function(renderTypesCode)();

let res = window.resolveAssistenteRenderResult({ tipo_resposta: 'geral', resposta: 'Olá mundo' }, false);
assert.strictEqual(res.rendererId, 'resposta-direta');
assert.ok(res.html.includes('Olá mundo'));

res = window.resolveAssistenteRenderResult({ tipo_resposta: 'geral', resposta: 'stream in progress', stream_has_chunks: true }, true);
assert.strictEqual(res.rendererId, 'streaming_chunks');
assert.strictEqual(res.html, '');

res = window.resolveAssistenteRenderResult({ tipo_resposta: 'analise_financeira', dados: [{a: 1}] }, false);
assert.strictEqual(res.rendererId, 'renderTabelaRica');
assert.ok(res.html.includes('<table'));

global.renderTabelaRica = () => null;
global.renderAnaliseTexto = () => '';
res = window.resolveAssistenteRenderResult({ tipo_resposta: 'geral', dados: null }, true);
assert.strictEqual(res.rendererId, 'fallback_erro');
assert.ok(res.html.includes('Não consegui montar a resposta completa agora'));

console.log('assistente-render-types-fallback: ok');