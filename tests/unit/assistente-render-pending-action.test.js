const assert = require('assert');
const fs = require('fs');
const path = require('path');

global.window = global;
global.escapeHtml = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
global.escapeHtmlAttr = (s) => global.escapeHtml(s).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
global.humanizeToolName = (t) => t === 'criar_orcamento' ? 'Criar Orçamento' : t;
global.formatPendingArgs = (t, args, extras) => 'Resumo do payload';

const renderTypesPath = path.join(__dirname, '../../sistema/cotte-frontend/js/assistente-ia-render-types.js');
const renderTypesCode = fs.readFileSync(renderTypesPath, 'utf8');

new Function(renderTypesCode)();

assert.ok(typeof window.renderPendingActionCard === 'function', 'Deve existir window.renderPendingActionCard()');

const tokenStr = 'test-token-12345';
const pendingAction = {
    confirmation_token: tokenStr,
    tool: 'criar_orcamento',
    args: { cliente: 'Teste' },
    extras: { materiais_novos: ['Prego'] }
};

const html = window.renderPendingActionCard(pendingAction);

assert.ok(html.includes('pending-action-card'), 'Deve renderizar card de pending action');
assert.ok(html.includes(tokenStr), 'Deve incluir o confirmation_token');
assert.ok(html.includes('btn-confirm-alt'), 'Deve exibir botão de cadastrar material novo quando materiais_novos existir');
assert.ok(html.includes('Criar Orçamento'), 'Deve exibir nome da tool humanizado');

console.log('assistente-render-pending-action: ok');