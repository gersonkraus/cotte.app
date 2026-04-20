const assert = require('assert');
const fs = require('fs');
const path = require('path');

const htmlPath = path.join(__dirname, '../../sistema/cotte-frontend/assistente-ia.html');
const html = fs.readFileSync(htmlPath, 'utf8');

assert.ok(html.includes('id="welcomeState"'), 'Deve manter #welcomeState para fallback e restauração');
assert.ok(html.includes('id="assistenteWelcomeShortcutsFinanceiro"'), 'Deve manter container financeiro para hidratação');
assert.ok(html.includes('id="assistenteWelcomeShortcutsVendas"'), 'Deve manter container de vendas para hidratação');
assert.ok(html.includes('id="assistenteWelcomeShortcutsRelatorios"'), 'Deve manter container de relatórios para hidratação');
assert.ok(html.includes('id="quickActionsSheet"'), 'Deve manter sheet de ações rápidas');
assert.ok(html.includes('id="assistenteQuickActionsList"'), 'Deve manter container da lista de ações rápidas');

assert.ok(!html.includes('Vendas &amp; Serviços'), 'Não deve manter grupo estático de vendas no fallback');
assert.ok(!html.includes('Relatórios'), 'Não deve manter grupo estático de relatórios no fallback');
assert.ok(!html.includes('data-quick-action="Qual meu saldo atual?"'), 'Não deve manter ações rápidas hardcoded no fallback');
assert.ok(!html.includes('data-quick-message="Taxa de conversão de orçamentos este mês"'), 'Não deve manter atalhos estáticos redundantes de relatórios');

console.log('assistente-ia-html-fallback: ok');
