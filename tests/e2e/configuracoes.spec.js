// @ts-check
const { test, expect } = require('@playwright/test');

// Credenciais de teste — substitua por um usuário real de desenvolvimento
const TEST_EMAIL = process.env.TEST_EMAIL || 'teste@playwright.com';
const TEST_PASSWORD = process.env.TEST_PASSWORD || 'senha123';

/**
 * Faz login e retorna o token JWT via API.
 * Injeta o token no localStorage antes de carregar a página.
 */
async function loginComToken(page) {
  const resp = await page.request.post('/auth/login', {
    data: { email: TEST_EMAIL, senha: TEST_PASSWORD },
  });
  if (!resp.ok()) throw new Error(`Login falhou: ${resp.status()}`);
  const { access_token } = await resp.json();
  await page.addInitScript((token) => {
    localStorage.setItem('cotte_token', token);
  }, access_token);
}

test.beforeEach(async ({ page }) => {
  await loginComToken(page);
  await page.goto('/app/configuracoes.html');
  await page.waitForLoadState('networkidle');
});

// ─────────────────────────────────────────────
// NAVEGAÇÃO LATERAL
// ─────────────────────────────────────────────
test.describe('Navegação lateral', () => {
  const secoes = [
    { id: 'empresa',           label: 'Empresa' },
    { id: 'orcamentos',        label: 'Orçamentos' },
    { id: 'formas-pagamento',  label: 'Formas de Pagamento' },
    { id: 'aparencia',         label: 'Aparência' },
    { id: 'comunicacao',       label: 'Comunicação' },
    { id: 'integracoes',       label: 'Integrações' },
    { id: 'plano',             label: 'Plano' },
    { id: 'seguranca',         label: 'Segurança' },
  ];

  for (const { id, label } of secoes) {
    test(`N — click em "${label}" exibe seção correta`, async ({ page }) => {
      await page.click(`[data-secao="${id}"]`);
      await expect(page.locator(`#sec-${id}`)).toBeVisible();
      await expect(page.locator(`[data-secao="${id}"]`)).toHaveClass(/active/);
    });
  }

  test('N — URL hash navega direto para seção ao carregar', async ({ page }) => {
    // Simula o que a IIFE faz ao detectar o hash na URL
    await page.evaluate(() => {
      const hash = 'orcamentos';
      const secoes = ['empresa', 'orcamentos', 'aparencia', 'comunicacao', 'integracoes', 'plano', 'seguranca', 'preferencias'];
      if (secoes.includes(hash)) window.irSecao(hash);
    });
    await expect(page.locator('#sec-orcamentos')).toBeVisible();
    await expect(page.locator('[data-secao="orcamentos"]')).toHaveClass(/active/);
  });
});

// ─────────────────────────────────────────────
// SEÇÃO EMPRESA — carregamento
// ─────────────────────────────────────────────
test.describe('Empresa — carregamento', () => {
  test('E — GET /empresa/ preenche campos ao carregar', async ({ page }) => {
    // Campos já foram preenchidos no beforeEach via carregarEmpresa()
    await expect(page.locator('#emp-nome')).not.toBeEmpty();
  });

  test('E — preview do cabeçalho atualiza ao digitar nome', async ({ page }) => {
    await page.locator('#emp-nome').fill('Empresa Teste Playwright');
    const preview = page.locator('#preview-nome-fallback, #preview-header');
    await expect(preview.first()).toContainText('Empresa Teste Playwright');
  });

  test('E — campos cor HEX e color picker sincronizam', async ({ page }) => {
    await page.locator('#emp-cor-hex').fill('#ff5500');
    await page.locator('#emp-cor-hex').press('Tab');

    const corPicker = await page.locator('#emp-cor').inputValue();
    expect(corPicker.toLowerCase()).toBe('#ff5500');
  });
});

// ─────────────────────────────────────────────
// SEÇÃO EMPRESA — salvar
// ─────────────────────────────────────────────
test.describe('Empresa — salvar', () => {
  test('E — PATCH /empresa/ enviado ao clicar em salvar', async ({ page }) => {
    await page.click('[data-secao="empresa"]');

    const [request] = await Promise.all([
      page.waitForRequest(r => r.url().includes('/empresa/') && r.method() === 'PATCH'),
      page.click('#btn-salvar-empresa'),
    ]);

    expect(request).toBeTruthy();
  });

  test('E — notificação de sucesso aparece após salvar', async ({ page }) => {
    await page.click('[data-secao="empresa"]');

    await Promise.all([
      page.waitForResponse(r => r.url().includes('/empresa/') && r.request().method() === 'PATCH'),
      page.click('#btn-salvar-empresa'),
    ]);

    await expect(page.locator('#notif')).toBeVisible({ timeout: 4000 });
  });
});

// ─────────────────────────────────────────────
// SEÇÃO ORÇAMENTOS
// ─────────────────────────────────────────────
test.describe('Orçamentos — campos', () => {
  test('O — campos de validade e desconto carregados da API', async ({ page }) => {
    await page.click('[data-secao="orcamentos"]');

    await expect(page.locator('#emp-validade')).toBeVisible();
    await expect(page.locator('#emp-desconto-max')).toBeVisible();
    await expect(page.locator('#emp-politica-agendamento-orc')).toBeVisible();
  });

  test('O — PATCH ao salvar padrões de orçamento envia política de agendamento', async ({ page }) => {
    await page.click('[data-secao="orcamentos"]');
    await page.selectOption('#emp-politica-agendamento-orc', 'PADRAO_SIM');

    const [request] = await Promise.all([
      page.waitForRequest(r => r.url().includes('/empresa/') && r.method() === 'PATCH'),
      page.click('#btn-salvar-orc'),
    ]);

    const body = request.postDataJSON();
    expect(body.agendamento_modo_padrao).toBe('OPCIONAL');
    expect(body.agendamento_escolha_obrigatoria).toBe(false);
  });

  test('O — chips de variáveis de lembrete visíveis', async ({ page }) => {
    await page.click('[data-secao="orcamentos"]');
    await expect(page.locator('text={cliente_nome}')).toBeVisible();
    await expect(page.locator('text={numero_orc}')).toBeVisible();
  });
});

test.describe('Orçamentos — template público', () => {
  test.beforeEach(async ({ page }) => {
    await page.click('[data-secao="orcamentos"]');
    await expect(page.locator('#tpl-classico')).toBeVisible();
  });

  test('O — seleção visual alterna entre clássico e moderno', async ({ page }) => {
    await page.click('#tpl-moderno');
    await expect(page.locator('#check-moderno svg')).toBeVisible();

    await page.click('#tpl-classico');
    await expect(page.locator('#check-classico svg')).toBeVisible();
  });

  test('O — salva template e mantém seleção após recarregar', async ({ page }) => {
    await page.click('#tpl-moderno');
    await Promise.all([
      page.waitForResponse(r => r.url().includes('/empresa/') && r.request().method() === 'PATCH'),
      page.click('#btn-salvar-template'),
    ]);

    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.click('[data-secao="orcamentos"]');
    await expect(page.locator('#check-moderno svg')).toBeVisible();
  });

  test('O — botão de preview abre modal estático do layout público', async ({ page }) => {
    await page.click('#tpl-classico');
    await page.click('#btn-preview-template');

    await expect(page.locator('#modal-preview-template-publico.open')).toBeVisible();
    await expect(page.locator('#static-preview-template-host')).toContainText('ORC-123-26');

    await page.click('#btn-fechar-preview-template');
    await expect(page.locator('#modal-preview-template-publico.open')).toHaveCount(0);
  });
});

// ─────────────────────────────────────────────
// SEÇÃO FORMAS DE PAGAMENTO — bancos PIX
// ─────────────────────────────────────────────
test.describe('Formas de Pagamento — Bancos PIX', () => {
  test.beforeEach(async ({ page }) => {
    // carregarBancosPix() já foi chamado dentro de carregarEmpresa() no load inicial
    await page.click('[data-secao="formas-pagamento"]');
  });

  test('F — modal de novo banco abre com campos vazios', async ({ page }) => {
    await page.click('button:has-text("Novo banco")');
    await expect(page.locator('#modal-banco-pix')).toBeVisible();
    const nome = await page.locator('#banco-nome').inputValue();
    expect(nome).toBe('');
  });

  test('F — modal fecha ao cancelar', async ({ page }) => {
    await page.click('button:has-text("Novo banco")');
    await expect(page.locator('#modal-banco-pix')).toBeVisible();
    await page.click('button:has-text("Cancelar"), .modal-close');
    await expect(page.locator('#modal-banco-pix')).toBeHidden();
  });
});

// ─────────────────────────────────────────────
// SEÇÃO FORMAS DE PAGAMENTO — formas
// ─────────────────────────────────────────────
test.describe('Formas de Pagamento — Lógica de entrada/saldo', () => {
  test.beforeEach(async ({ page }) => {
    await Promise.all([
      page.waitForResponse(r => r.url().includes('/financeiro/formas-pagamento')),
      page.click('[data-secao="formas-pagamento"]'),
    ]);
    await page.click('button:has-text("Nova forma")');
    await expect(page.locator('#modal-forma-pagamento')).toBeVisible();
  });

  test('F — seção de entrada oculta por padrão', async ({ page }) => {
    await expect(page.locator('#forma-campos-entrada')).toBeHidden();
  });

  test('F — marcar "exigir entrada" exibe campos de regra', async ({ page }) => {
    await page.check('#forma-exigir-entrada');
    await expect(page.locator('#forma-campos-entrada')).toBeVisible();
  });

  test('F — saldo calculado automaticamente (100 - entrada)', async ({ page }) => {
    await page.check('#forma-exigir-entrada');
    await page.locator('#forma-pct-entrada').fill('40');
    await page.locator('#forma-pct-entrada').press('Tab');

    const saldo = await page.locator('#forma-pct-saldo').inputValue();
    expect(saldo).toBe('60');
  });

  test('F — erro visível quando entrada + saldo > 100%', async ({ page }) => {
    await page.check('#forma-exigir-entrada');
    await page.locator('#forma-pct-entrada').fill('110');
    await page.locator('#forma-pct-entrada').press('Tab');

    await expect(page.locator('#forma-erro-percentual')).toBeVisible();
  });

  test('F — preview de regra atualiza ao interagir', async ({ page }) => {
    await page.check('#forma-exigir-entrada');
    const previo = await page.locator('#forma-preview').textContent();
    await page.locator('#forma-pct-entrada').fill('30');
    await page.locator('#forma-pct-entrada').press('Tab');

    const depois = await page.locator('#forma-preview').textContent();
    expect(depois).not.toBe(previo);
  });
});

// ─────────────────────────────────────────────
// SEÇÃO APARÊNCIA
// ─────────────────────────────────────────────
test.describe('Aparência — tema', () => {
  test.beforeEach(async ({ page }) => {
    await page.click('[data-secao="aparencia"]');
  });

  test('A — click em tema claro aplica .active no card', async ({ page }) => {
    await page.click('#tema-card-light');
    await expect(page.locator('#tema-check-light')).toBeVisible();
  });

  test('A — click em tema escuro aplica .active no card', async ({ page }) => {
    await page.click('#tema-card-dark');
    await expect(page.locator('#tema-check-dark')).toBeVisible();
  });

  test('A — tema persiste no localStorage', async ({ page }) => {
    await page.click('#tema-card-dark');
    const tema = await page.evaluate(() => localStorage.getItem('cotte_tema'));
    expect(tema).toBe('dark');
  });
});

// ─────────────────────────────────────────────
// SEÇÃO SEGURANÇA
// ─────────────────────────────────────────────
test.describe('Segurança', () => {
  test('S — botão de logout visível na seção de segurança', async ({ page }) => {
    await page.click('[data-secao="seguranca"]');
    await expect(
      page.locator('button:has-text("Sair"), button:has-text("Logout"), button:has-text("logout")')
    ).toBeVisible();
  });
});
