const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

function createElement(tagName) {
  const element = {
    tagName: String(tagName || '').toUpperCase(),
    children: [],
    attributes: {},
    dataset: {},
    className: '',
    innerHTML: '',
    textContent: '',
    value: '',
    disabled: false,
    parentNode: null,
    focused: false,
    appended: false,
    listeners: {},
    appendChild(child) {
      child.parentNode = this;
      this.children.push(child);
      this.appended = true;
      return child;
    },
    setAttribute(name, value) {
      this.attributes[name] = String(value);
    },
    getAttribute(name) {
      return this.attributes[name];
    },
    addEventListener(type, handler) {
      this.listeners[type] = handler;
    },
    focus() {
      this.focused = true;
    },
    querySelector() {
      return null;
    },
    querySelectorAll() {
      return [];
    },
  };
  element.classList = {
    add(cls) {
      element.className = element.className ? `${element.className} ${cls}` : cls;
    },
  };
  return element;
}

function loadModule() {
  const modulePath = path.join(__dirname, 'assistente-ia-insights.js');
  const source = fs.readFileSync(modulePath, 'utf8');
  const chatMessages = createElement('div');
  const input = createElement('textarea');
  const posts = [];
  const context = {
    console,
    window: {
      ApiService: {
        get: async () => ({ insights: [] }),
        post: async (endpoint, body) => posts.push({ endpoint, body }),
      },
      resizeMessageInput: () => { input.resized = true; },
      scrollChatToBottom: () => { chatMessages.scrolled = true; },
    },
    document: {
      createElement,
      getElementById(id) {
        if (id === 'chatMessages') return chatMessages;
        if (id === 'messageInput') return input;
        return null;
      },
      querySelector() {
        return null;
      },
      addEventListener() {},
    },
    setTimeout(fn) { fn(); },
  };
  context.window.document = context.document;
  vm.runInNewContext(source, context, { filename: modulePath });
  return { api: context.window.AssistenteInsights, chatMessages, input, posts };
}

function loadRenderTypesModule() {
  const modulePath = path.join(__dirname, 'assistente-ia-render-types.js');
  const source = fs.readFileSync(modulePath, 'utf8');
  const context = {
    console,
    window: {},
    document: {},
    escapeHtml(value) {
      return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    },
    escapeHtmlAttr(value) {
      return String(value ?? '').replace(/"/g, '&quot;');
    },
    textToHtmlRich(value) {
      return String(value);
    },
    formatValue(value) {
      return String(value);
    },
  };
  vm.runInNewContext(source, context, { filename: modulePath });
  return context;
}

(async () => {
  const { api, chatMessages, input, posts } = loadModule();
  assert.ok(api, 'expõe window.AssistenteInsights');
  assert.strictEqual(typeof api.render, 'function');
  assert.strictEqual(typeof api.renderFromResponse, 'function');

  const insights = [{
    id: 'abc',
    prioridade: 'alta',
    dominio: 'financeiro',
    titulo: 'Cobrar inadimplentes',
    descricao: 'Há contas vencidas nesta semana.',
    acao: 'Liste clientes inadimplentes',
    contexto: { total: 3 },
  }];

  api.render(insights, { placement: 'welcome' });
  assert.strictEqual(chatMessages.children.length, 1, 'renderiza um bloco no chat');
  assert.match(chatMessages.children[0].innerHTML, /Cobrar inadimplentes/);
  assert.match(chatMessages.children[0].innerHTML, /Usar ação/);

  api.applyInsightAction(insights[0]);
  assert.strictEqual(input.value, 'Liste clientes inadimplentes');
  assert.strictEqual(input.focused, true);
  assert.strictEqual(input.resized, true);

  assert.strictEqual(JSON.stringify(posts[0]), JSON.stringify({
    endpoint: '/ai/insights/feedback',
    body: { insight_id: 'abc', acao: 'executar', sessao_id: null },
  }));

  await api.sendFeedback(insights[0], 'clicou');
  assert.strictEqual(JSON.stringify(posts[1]), JSON.stringify({
    endpoint: '/ai/insights/feedback',
    body: { insight_id: 'abc', acao: 'clicou', sessao_id: null },
  }));

  const renderTypes = loadRenderTypesModule();
  const legacyHtml = renderTypes.renderAnaliseTexto({
    insights: [{ titulo: 'Fluxo de caixa crítico', descricao: 'Revise vencimentos hoje.' }],
  }, false);
  assert.doesNotMatch(legacyHtml, /\[object Object\]/);
  assert.match(legacyHtml, /Fluxo de caixa crítico/);
})();
