// @ts-check
const { test, expect } = require('@playwright/test');
const { prepararPaginaAssistente } = require('./assistente-ia-fixture');

test.beforeEach(async ({ page }) => {
  await prepararPaginaAssistente(page, { viewport: { width: 1440, height: 960 } });
});

test.describe('Assistente IA desktop', () => {
  test('mantém shell desktop e não exibe quick replies fora do mobile', async ({ page }) => {
    await expect(page.locator('.topbar')).toBeVisible();
    await expect(page.locator('#quickReplyArea')).toBeHidden();

    await page.locator('#messageInput').fill('Como está meu caixa hoje?');
    await page.locator('#sendButton').click();

    await expect(page.locator('.message.ai').last()).toContainText('Resumo executivo do caixa.');
    await expect(page.locator('#quickReplyArea')).toBeHidden();
    await expect(page.locator('.sugestoes-container')).toBeVisible();
  });

  test('renderiza card de operador com ações contextuais no desktop', async ({ page }) => {
    await page.locator('#messageInput').fill('Ver orçamento 321');
    await page.locator('#sendButton').click();

    const card = page.locator('.opr-card');
    await expect(card).toBeVisible();
    await expect(card).toContainText('ORC-321-26');
    await expect(card.locator('[data-enviar-wa]')).toBeVisible();
    await expect(card.locator('[data-enviar-email]')).toBeVisible();
    await expect(card.locator('[data-quick-send]')).toBeVisible();
  });

  test('mantém o card de orçamento criado com ações completas e grid compacto no desktop', async ({ page }) => {
    await page.locator('#messageInput').fill('Prévia orçamento');
    await page.locator('#sendButton').click();
    await page.locator('.orc-preview-card [data-orc-confirm]').click();

    const successCard = page.locator('.orc-success-card');
    await expect(successCard).toBeVisible();
    const actionButtons = successCard.locator('.orc-action-btn');
    await expect(actionButtons).toHaveCount(4);

    const layout = await successCard.evaluate((card) => {
      const actions = card.querySelector('.orc-action-btns--success');
      const styles = actions ? window.getComputedStyle(actions) : null;
      return {
        columnCount: styles ? styles.gridTemplateColumns.split(' ').filter(Boolean).length : 0,
        hasOverflow: card.scrollWidth > card.clientWidth,
      };
    });

    expect(layout.columnCount).toBe(2);
    expect(layout.hasOverflow).toBeFalsy();
    await expect(actionButtons.nth(0)).toContainText('Enviar WhatsApp');
    await expect(actionButtons.nth(1)).toContainText('Copiar link');
  });

  test('renderiza gráfico financeiro no desktop', async ({ page }) => {
    await page.locator('#messageInput').fill('Mostrar gráfico financeiro');
    await page.locator('#sendButton').click();

    await expect(page.locator('.message.ai').last()).toContainText('Segue o gráfico financeiro.');
    await expect(page.locator('.chart-container canvas')).toHaveCount(1);
  });
});
