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
    await page.locator('#messageInput').press('Enter');

    await expect(page.locator('.message.ai').last()).toContainText('Resumo executivo do caixa.');
    await expect(page.locator('#quickReplyArea')).toBeHidden();
    await expect(page.locator('.sugestoes-container')).toBeVisible();
  });

  test('renderiza card de operador com ações contextuais no desktop', async ({ page }) => {
    await page.locator('#messageInput').fill('Ver orçamento 321');
    await page.locator('#messageInput').press('Enter');

    const card = page.locator('.opr-card');
    await expect(card).toBeVisible();
    await expect(card).toContainText('ORC-321-26');
    await expect(card.locator('[data-enviar-wa]')).toBeVisible();
    await expect(card.locator('[data-enviar-email]')).toBeVisible();
    await expect(card.locator('[data-quick-send]')).toBeVisible();
  });

  test('mantém o card de orçamento criado com ações completas e grid compacto no desktop', async ({ page }) => {
    await page.locator('#messageInput').fill('Prévia orçamento');
    await page.locator('#messageInput').press('Enter');
    await page.getByTestId('assistente-orc-preview-card').locator('[data-orc-confirm]').click();

    const successCard = page.getByTestId('orc-created-card');
    await expect(successCard).toBeVisible({ timeout: 15000 });
    await expect(successCard.locator('.orc-card-v2__icon-btn.btn-whats')).toHaveAttribute('title', 'Enviar WhatsApp');
    await expect(successCard.locator('.orc-card-v2__icon-btn.btn-link')).toHaveAttribute('title', 'Copiar link');
    await expect(successCard.locator('.orc-card-v2__aprovar-btn')).toBeVisible();

    const layout = await successCard.evaluate((card) => {
      const actions = card.querySelector('.orc-card-v2__actions');
      return {
        hasOverflow: card.scrollWidth > card.clientWidth,
        actionsDisplay: actions ? window.getComputedStyle(actions).display : '',
      };
    });

    expect(layout.hasOverflow).toBeFalsy();
    expect(layout.actionsDisplay).toBe('flex');
  });

  test('renderiza gráfico financeiro no desktop', async ({ page }) => {
    await page.locator('#messageInput').fill('Mostrar gráfico financeiro');
    await page.locator('#messageInput').press('Enter');

    await expect(page.locator('.message.ai').last()).toContainText('Segue o gráfico financeiro.');
    await expect(page.locator('.chart-container canvas')).toHaveCount(1);
  });
});
