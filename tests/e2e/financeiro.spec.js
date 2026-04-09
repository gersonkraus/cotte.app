// @ts-check
const { test, expect } = require('@playwright/test');

const TEST_EMAIL = process.env.TEST_EMAIL || 'teste@playwright.com';
const TEST_PASSWORD = process.env.TEST_PASSWORD || 'senha123';

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
  await Promise.all([
    page.waitForResponse(r => r.url().includes('/financeiro/resumo')),
    page.goto('/app/financeiro.html'),
  ]);
  await page.waitForLoadState('networkidle');
});

// ─────────────────────────────────────────────
// KPI CARDS
// ─────────────────────────────────────────────
test.describe('KPI Cards', () => {
  test('K — kpi-recebido preenchido após carregar', async ({ page }) => {
    const texto = await page.locator('#kpi-recebido').textContent();
    expect(texto).toMatch(/R\$/);
  });

  test('K — kpi-a-receber preenchido após carregar', async ({ page }) => {
    const texto = await page.locator('#kpi-a-receber').textContent();
    expect(texto).toMatch(/R\$/);
  });

  test('K — kpi-vencido preenchido após carregar', async ({ page }) => {
    const texto = await page.locator('#kpi-vencido').textContent();
    expect(texto).toMatch(/R\$/);
  });

  test('K — kpi-ticket preenchido após carregar', async ({ page }) => {
    const texto = await page.locator('#kpi-ticket').textContent();
    expect(texto).toMatch(/R\$/);
  });
});

// ─────────────────────────────────────────────
// TABELAS — estado após carregar
// ─────────────────────────────────────────────
test.describe('Tabelas', () => {
  test('T — tabela de pagamentos carregada (dados ou vazio)', async ({ page }) => {
    const tbody = page.locator('#tabela-pagamentos');
    await expect(tbody).not.toContainText('Carregando...');
    // Deve ter linhas de dados OU mensagem de vazio
    const html = await tbody.innerHTML();
    const temDados = html.includes('<tr') && !html.includes('Carregando');
    expect(temDados).toBe(true);
  });

  test('T — tabela de contas a receber carregada (dados ou vazio)', async ({ page }) => {
    const tbody = page.locator('#tabela-contas-receber');
    await expect(tbody).not.toContainText('Verificando...');
    const html = await tbody.innerHTML();
    expect(html.includes('<tr')).toBe(true);
  });

  test('T — tabela de inadimplentes carregada (dados ou vazio)', async ({ page }) => {
    const tbody = page.locator('#tabela-inadimplentes');
    await expect(tbody).not.toContainText('Verificando...');
    const html = await tbody.innerHTML();
    expect(html.includes('<tr')).toBe(true);
  });

  test('T — empresa sem dados exibe mensagem de vazio em pagamentos', async ({ page }) => {
    await expect(page.locator('#tabela-pagamentos')).toContainText('Nenhum pagamento registrado.');
  });

  test('T — empresa sem dados exibe mensagem de vazio em contas', async ({ page }) => {
    await expect(page.locator('#tabela-contas-receber')).toContainText('Nenhuma conta pendente');
  });

  test('T — empresa sem dados exibe mensagem de vazio em inadimplentes', async ({ page }) => {
    await expect(page.locator('#tabela-inadimplentes')).toContainText('Nenhuma conta vencida.');
  });
});

// ─────────────────────────────────────────────
// MODAL — REGISTRAR PAGAMENTO
// ─────────────────────────────────────────────
test.describe('Modal — Registrar Pagamento', () => {
  test.beforeEach(async ({ page }) => {
    await page.click('button:has-text("Registrar Pagamento")');
    await expect(page.locator('#modal-pagamento')).toBeVisible();
  });

  test('M — modal abre ao clicar em Registrar Pagamento', async ({ page }) => {
    await expect(page.locator('#modal-pagamento')).toBeVisible();
  });

  test('M — formas de pagamento carregam no modal', async ({ page }) => {
    const cards = page.locator('#forma-cards .forma-card');
    await expect(cards.first()).toBeVisible();
    expect(await cards.count()).toBeGreaterThan(0);
  });

  test('M — data de hoje preenchida automaticamente', async ({ page }) => {
    const dataVal = await page.locator('#pag-data').inputValue();
    expect(dataVal).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  test('M — tipo padrão é quitacao', async ({ page }) => {
    const tipo = await page.locator('#pag-tipo').inputValue();
    expect(tipo).toBe('quitacao');
  });

  test('M — click em forma de pagamento seleciona card', async ({ page }) => {
    const primeiroCard = page.locator('#forma-cards .forma-card').first();
    await primeiroCard.click();
    await expect(primeiroCard).toHaveClass(/selected/);
  });

  test('M — botão Cancelar fecha o modal', async ({ page }) => {
    await page.click('button:has-text("Cancelar")');
    await expect(page.locator('#modal-pagamento')).toBeHidden();
  });

  test('M — click fora do modal fecha o modal', async ({ page }) => {
    // Clica no overlay (área fora do modal-box)
    await page.locator('#modal-pagamento').click({ position: { x: 10, y: 10 } });
    await expect(page.locator('#modal-pagamento')).toBeHidden();
  });

  test('M — salvar sem preencher campos exibe erro no feedback', async ({ page }) => {
    await page.click('#btn-salvar-pagamento');
    await expect(page.locator('#pag-feedback')).toBeVisible();
  });

});
