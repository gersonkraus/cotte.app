// @ts-check
const { test, expect } = require('@playwright/test');
const { prepararPaginaAssistente } = require('./assistente-ia-fixture');

test.beforeEach(async ({ page }) => {
  await prepararPaginaAssistente(page, { viewport: { width: 1440, height: 960 } });
});

test.describe('Renderizador generico de lista paginada', () => {
  test('renderiza tabela generica para entidade desconhecida (notas_fiscais)', async ({ page }) => {
    await page.locator('#messageInput').fill('listar notas');
    await page.locator('#messageInput').press('Enter');

    const card = page.getByTestId('assistente-generic-list-card');
    await expect(card).toBeVisible({ timeout: 10000 });
    await expect(card.locator('.ai-table')).toBeVisible();
    await expect(card.locator('.ai-table tbody tr')).toHaveCount(3);
    await expect(card.locator('.ai-table-wrapper')).toBeVisible();
  });

  test('renderiza tabela generica para entidade produtos', async ({ page }) => {
    await page.locator('#messageInput').fill('listar produtos');
    await page.locator('#messageInput').press('Enter');

    const card = page.getByTestId('assistente-generic-list-card');
    await expect(card).toBeVisible({ timeout: 10000 });
    await expect(card.locator('.ai-table tbody tr')).toHaveCount(3);
  });

  test('exibe botao Carregar mais quando has_more=true', async ({ page }) => {
    await page.locator('#messageInput').fill('entidade generica');
    await page.locator('#messageInput').press('Enter');

    const card = page.getByTestId('assistente-generic-list-card');
    await expect(card).toBeVisible({ timeout: 10000 });
    await expect(card.locator('.orc-list-card__load-more')).toBeVisible();
    await expect(card.locator('.orc-list-card__load-more')).toHaveAttribute('data-generic-load-more', '1');
    await expect(card.locator('.orc-list-card__load-more')).toHaveAttribute('data-cursor', 'cursor-test-123');
  });

  test('exibe pills de totais por status', async ({ page }) => {
    await page.locator('#messageInput').fill('entidade generica');
    await page.locator('#messageInput').press('Enter');

    const card = page.getByTestId('assistente-generic-list-card');
    await expect(card).toBeVisible({ timeout: 10000 });
    await expect(card.locator('.orc-list-card__status-pill')).toHaveCount(2);
    await expect(card.locator('.orc-list-card__status-pill').first()).toContainText('ativo');
  });

  test('exibe printable card com botoes Imprimir e Exportar', async ({ page }) => {
    await page.locator('#messageInput').fill('entidade generica');
    await page.locator('#messageInput').press('Enter');

    const card = page.getByTestId('assistente-generic-list-card');
    await expect(card).toBeVisible({ timeout: 10000 });
    await expect(card.locator('[data-semantic-print-now]')).toBeVisible();
    await expect(card.locator('[data-export-format="csv"]')).toBeVisible();
    await expect(card.locator('[data-export-format="pdf"]')).toBeVisible();
  });

  test('exibe fallback visual para lista vazia', async ({ page }) => {
    await page.locator('#messageInput').fill('lista vazia');
    await page.locator('#messageInput').press('Enter');

    const emptyMsg = page.locator('.orc-list-empty');
    await expect(emptyMsg).toBeVisible({ timeout: 10000 });
    await expect(emptyMsg).toContainText('Nenhum registro encontrado');
  });

  test('registerGenericEntityConfig registra nova entidade dinamicamente', async ({ page }) => {
    await page.evaluate(() => {
      if (typeof window.registerGenericEntityConfig === 'function') {
        window.registerGenericEntityConfig('veiculos', {
          titleDefault: 'Meus Veiculos',
          titleKey: 'modelo',
          loadMoreLabel: 'Carregar mais veiculos',
        });
      }
    });

    const configs = await page.evaluate(() => {
      return typeof window.getRegisteredEntityConfigs === 'function'
        ? window.getRegisteredEntityConfigs()
        : {};
    });

    expect(configs.veiculos).toBeDefined();
    expect(configs.veiculos.titleDefault).toBe('Meus Veiculos');

    await page.locator('#messageInput').fill('register entity');
    await page.locator('#messageInput').press('Enter');

    const card = page.getByTestId('assistente-generic-list-card');
    await expect(card).toBeVisible({ timeout: 10000 });
    await expect(card).toHaveAttribute('data-entity-key', 'veiculos');
    await expect(card.locator('.ai-table tbody tr')).toHaveCount(2);
  });

  test('columnSchema define labels e ordem customizados', async ({ page }) => {
    await page.evaluate(() => {
      if (typeof window.registerGenericEntityConfig === 'function') {
        window.registerGenericEntityConfig('veiculos', {
          titleDefault: 'Frota de Veículos',
          columnSchema: [
            { key: 'modelo', label: 'Modelo', align: 'left' },
            { key: 'placa', label: 'Placa' },
            { key: 'ano', label: 'Ano Fabricação' }
          ]
        });
      }
    });

    await page.locator('#messageInput').fill('register entity');
    await page.locator('#messageInput').press('Enter');

    const card = page.getByTestId('assistente-generic-list-card');
    await expect(card).toBeVisible({ timeout: 10000 });

    const headers = card.locator('.ai-table thead th');
    await expect(headers).toHaveCount(3);
    await expect(headers.nth(0)).toContainText('Modelo');
    await expect(headers.nth(1)).toContainText('Placa');
    await expect(headers.nth(2)).toContainText('Ano Fabricação');
  });

  test('entity_config do backend auto-registra colunas com labels customizados', async ({ page }) => {
    await page.evaluate(() => {
      if (typeof window.registerGenericEntityConfig === 'function') {
        window.registerGenericEntityConfig('notas_fiscais', {
          columnSchema: [
            { key: 'nome', label: 'Descrição' },
            { key: 'valor', label: 'Valor Total', format: 'currency', align: 'right' },
            { key: 'status', label: 'Situação' },
            { key: 'criado_em', label: 'Emissão', format: 'date' }
          ]
        });
      }
    });

    await page.locator('#messageInput').fill('listar notas');
    await page.locator('#messageInput').press('Enter');

    const card = page.getByTestId('assistente-generic-list-card');
    await expect(card).toBeVisible({ timeout: 10000 });

    const headers = card.locator('.ai-table thead th');
    await expect(headers.nth(0)).toContainText('Descrição');
    await expect(headers.nth(1)).toContainText('Valor Total');

    const firstRow = card.locator('.ai-table tbody tr').first();
    await expect(firstRow).toContainText('R$');
  });

  test('unregisterGenericEntityConfig remove entidade registrada', async ({ page }) => {
    await page.evaluate(() => {
      if (typeof window.registerGenericEntityConfig === 'function') {
        window.registerGenericEntityConfig('veiculos', { titleDefault: 'Veiculos' });
      }
    });

    let configs = await page.evaluate(() => window.getRegisteredEntityConfigs());
    expect(configs.veiculos).toBeDefined();

    await page.evaluate(() => {
      if (typeof window.unregisterGenericEntityConfig === 'function') {
        window.unregisterGenericEntityConfig('veiculos');
      }
    });

    configs = await page.evaluate(() => window.getRegisteredEntityConfigs());
    expect(configs.veiculos).toBeUndefined();
  });

  test('formata colunas monetarias e datas automaticamente', async ({ page }) => {
    await page.locator('#messageInput').fill('listar notas');
    await page.locator('#messageInput').press('Enter');

    const card = page.getByTestId('assistente-generic-list-card');
    await expect(card).toBeVisible({ timeout: 10000 });
    const firstRow = card.locator('.ai-table tbody tr').first();
    await expect(firstRow).toContainText('R$');
  });

  test('entity_config do payload auto-registra entidade sem registro manual', async ({ page }) => {
    await page.locator('#messageInput').fill('entity config auto');
    await page.locator('#messageInput').press('Enter');

    const card = page.getByTestId('assistente-generic-list-card');
    await expect(card).toBeVisible({ timeout: 10000 });

    await expect(card.locator('.ai-table tbody tr')).toHaveCount(2);

    const headers = card.locator('.ai-table thead th');
    await expect(headers.nth(0)).toContainText('Razão Social');
    await expect(headers.nth(1)).toContainText('CNPJ');
    await expect(headers.nth(2)).toContainText('Total Compras');
    await expect(headers.nth(3)).toContainText('Situação');

    const firstRow = card.locator('.ai-table tbody tr').first();
    await expect(firstRow).toContainText('12.345.678/0001-90');
    await expect(firstRow).toContainText('R$');

    const configs = await page.evaluate(() => {
      return typeof window.getRegisteredEntityConfigs === 'function'
        ? Object.keys(window.getRegisteredEntityConfigs())
        : [];
    });
    expect(configs).toContain('fornecedores');
  });
});
