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
});
