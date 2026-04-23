// @ts-check
const { test, expect } = require('@playwright/test');

async function loginComToken(page) {
  const email = process.env.TEST_EMAIL || 'teste@playwright.com';
  const senha = process.env.TEST_PASSWORD || 'senha123';
  
  const resp = await page.request.post('/api/v1/auth/login', {
    data: { email, senha },
  });
  
  if (!resp.ok()) {
    throw new Error(`Login falhou com status ${resp.status()}. Verifique se o usuário existe.`);
  }

  const { access_token } = await resp.json();
  
  const userObj = {
    id: 1,
    nome: 'Teste Playwright',
    email: 'teste@playwright.com',
    is_gestor: true,
    is_superadmin: false,
    empresa_id: 1
  };

  await page.addInitScript(({ token, user }) => {
    localStorage.setItem('cotte_token', token);
    localStorage.setItem('cotte_usuario', JSON.stringify(user));
  }, { token: access_token, user: userObj });

  await page.route('**/api/v1/auth/me', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 1,
        nome: 'Teste Playwright',
        email: 'teste@playwright.com',
        is_gestor: true,
        is_superadmin: false,
        empresa_id: 1
      }),
    });
  });
}

test.beforeEach(async ({ page }) => {
  await loginComToken(page);
  await page.goto('/app/agendamentos.html'); // Navega primeiro

  // Agora, no contexto da página, podemos acessar o localStorage
  const token = await page.evaluate(() => localStorage.getItem('cotte_token'));
  
  let clientes = await page.request.get('/api/v1/clientes', { headers: { Authorization: `Bearer ${token}` } }).then(res => res.json());
  let clienteId;
  if (clientes.length === 0) {
    const novoCliente = await page.request.post('/api/v1/clientes', { 
      headers: { Authorization: `Bearer ${token}` },
      data: { nome: 'Cliente de Teste para Agendamento' }
    }).then(res => res.json());
    clienteId = novoCliente.id;
  } else {
    clienteId = clientes[0].id;
  }

  const dataAgendamento = new Date();
  dataAgendamento.setDate(dataAgendamento.getDate() + 1);
  dataAgendamento.setHours(10, 0, 0, 0);

  await page.request.post('/api/v1/agendamentos', {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      cliente_id: clienteId,
      data_agendada: dataAgendamento.toISOString(),
      tipo: 'servico',
      status: 'pendente'
    }
  });

  // Recarrega a página para garantir que o novo agendamento apareça
  await page.reload();
  await page.waitForLoadState('networkidle');
});

test.describe('Modal de Chips de Status', () => {
  test('Clicar no chip abre modal com lista', async ({ page }) => {
    const consoleLogs = [];
    page.on('console', msg => consoleLogs.push(msg.text()));

    try {
      await page.waitForSelector('.agd-status-chip', { timeout: 20000 }); // Aumentado para 20s
      await page.locator('.agd-status-chip:has-text("Pendente")').click();
      await page.waitForLoadState('networkidle');

      await expect(page.locator('#modal-dash')).toBeVisible();
      await expect(page.locator('#modal-dash-titulo')).toContainText('Pendente');

      const cards = await page.locator('.agd-dash-card').count();
      if (cards === 0) {
        await expect(page.locator('.agd-dash-empty')).toContainText('Nenhum agendamento encontrado');
      }
    } catch (error) {
      console.log('Logs do console capturados:', consoleLogs);
      throw error; // Re-lança o erro para o teste falhar
    }
  });

  test('Botão Confirmar remove card da lista', async ({ page }) => {
    await page.waitForSelector('.agd-status-chip', { timeout: 10000 });
    await page.click('.agd-status-chip:has-text("Pendente")');
    await expect(page.locator('#modal-dash')).toBeVisible();
    
    const cardsBefore = await page.locator('.agd-dash-card').count();
    if (cardsBefore === 0) {
      test.skip('Nenhum agendamento pendente para testar');
      return;
    }
    
    await page.locator('.btn-action-confirm').first().click();
    await expect(page.locator('.toast, [class*="toast"]')).toBeVisible();
    await expect(page.locator('.agd-dash-card')).toHaveCount(cardsBefore - 1);
  });

  test('Botão Cancelar pede confirmação', async ({ page }) => {
    await page.waitForSelector('.agd-status-chip', { timeout: 10000 });
    await page.click('.agd-status-chip:has-text("Pendente")');
    await expect(page.locator('#modal-dash')).toBeVisible();

    const cardsBefore = await page.locator('.agd-dash-card').count();
    if (cardsBefore === 0) {
      test.skip('Nenhum agendamento pendente para testar');
      return;
    }
    
    page.on('dialog', async dialog => {
      expect(dialog.message()).toContain('Tem certeza');
      await dialog.dismiss();
    });
    
    await page.locator('.btn-action-cancel').first().click();
    await expect(page.locator('.agd-dash-card')).toHaveCount(cardsBefore);
  });

  test('Botão Editar abre modal de edição de agendamento', async ({ page }) => {
    await page.waitForSelector('.agd-status-chip', { timeout: 10000 });
    await page.click('.agd-status-chip:has-text("Pendente")');
    await expect(page.locator('#modal-dash')).toBeVisible();

    const cards = page.locator('.agd-dash-card');
    if (await cards.count() === 0) {
      test.skip('Nenhum agendamento pendente para testar a edição');
      return;
    }

    await cards.first().locator('.btn-action-edit').click();

    await expect(page.locator('#modal-agendamento')).toBeVisible();
    await expect(page.locator('#modal-agendamento-title')).toContainText('Editar Agendamento');
  });

  test('Contagem do chip deve ser atualizada após ação', async ({ page }) => {
    await page.waitForSelector('.agd-status-chip', { timeout: 10000 });

    const chipPendente = page.locator('.agd-status-chip:has-text("Pendente")');
    const countLocator = chipPendente.locator('.chip-count');

    const initialCountText = await countLocator.innerText();
    const initialCount = parseInt(initialCountText, 10);

    if (initialCount === 0) {
      test.skip('Nenhum agendamento pendente para testar a atualização da contagem');
      return;
    }

    await chipPendente.click();
    await expect(page.locator('#modal-dash')).toBeVisible();

    await page.locator('.btn-action-confirm').first().click();
    await expect(page.locator('.toast, [class*="toast"]')).toBeVisible();
    
    await page.locator('#btn-fechar-modal-dash').click();
    await expect(page.locator('#modal-dash')).toBeHidden();
    
    await expect(countLocator).toHaveText(`${initialCount - 1}`);
  });
});
