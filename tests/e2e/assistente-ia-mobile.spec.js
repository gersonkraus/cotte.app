// @ts-check
const { test, expect } = require('@playwright/test');
const { prepararPaginaAssistente } = require('./assistente-ia-fixture');

test.beforeEach(async ({ page }) => {
  await prepararPaginaAssistente(page, { viewport: { width: 390, height: 844 } });
});

test.describe('Assistente IA mobile', () => {
  test('mostra a experiência mobile essencial ao carregar', async ({ page }) => {
    await expect(page.locator('.chat-header')).toBeVisible();
    await expect(page.locator('#messageInput')).toHaveAttribute('placeholder', 'Digite sua mensagem...');
    await expect(page.locator('#welcomeState')).toBeVisible();
  });

  test('processa resposta SSE e exibe quick replies no mobile', async ({ page }) => {
    await page.locator('#messageInput').fill('Como está meu caixa hoje?');
    await page.locator('#sendButton').click();

    await expect(page.locator('.message.user')).toContainText('Como está meu caixa hoje?');
    await expect(page.locator('.message.ai').last()).toContainText('Resumo executivo do caixa.');
    await expect(page.locator('#quickReplyArea')).toBeVisible();
    await expect(page.locator('#quickReplyArea .quick-reply-chip')).toHaveCount(3);
    await expect(page.locator('.tool-trace').nth(1)).toContainText('listar_movimentacoes_financeiras');
  });

  test('mantém fluxo de confirmação pendente no mobile', async ({ page }) => {
    await page.locator('#messageInput').fill('Confirmar orçamento');
    await page.locator('#sendButton').click();

    const card = page.locator('.pending-action-card');
    await expect(card).toBeVisible();
    await expect(card).toContainText('Confirmação necessária');
    await expect(card).toContainText('Maria');

    await card.locator('[data-confirm-ia]').click();
    await expect(page.locator('.message.ai').last()).toContainText('Ação confirmada com sucesso.');
  });

  test('permite cancelar a ação pendente sem chamar confirmação', async ({ page }) => {
    await page.locator('#messageInput').fill('Confirmar orçamento');
    await page.locator('#sendButton').click();

    const card = page.locator('.pending-action-card');
    await expect(card).toBeVisible();
    await card.locator('[data-cancel-ia]').click();
    await expect(card).toContainText('Ação cancelada');
  });

  test('abre e fecha preferências pelo header mobile', async ({ page }) => {
    await page.locator('#btnPreferenciasGear').click();
    await expect(page.locator('#assistentePreferenciasCard')).toHaveClass(/is-open/);
    await page.locator('#btnFecharPreferenciasAssistente').click();
    await expect(page.locator('#assistentePreferenciasCard')).not.toHaveClass(/is-open/);
  });

  test('confirma a prévia de orçamento e exibe card de sucesso', async ({ page }) => {
    await page.locator('#messageInput').fill('Prévia orçamento');
    await page.locator('#sendButton').click();

    const preview = page.getByTestId('assistente-orc-preview-card');
    await expect(preview).toBeVisible();
    await preview.locator('[data-orc-confirm]').click();

    // Resposta de POST /ai/orcamento/confirmar usa renderOrcamentoCriado (data-testid orc-created-card)
    const successBubble = page.locator('.message.ai').last();
    await expect(successBubble).toBeVisible();
    await expect(successBubble).toContainText('ORC-321-26', { timeout: 15000 });
    await expect(successBubble).toContainText('Instalação elétrica');

    const successCard = page.getByTestId('orc-created-card');
    await expect(successCard).toBeVisible();

    await expect(successBubble.locator('.sugestoes-header')).toContainText('Próximos passos');

    await expect(successCard.locator('.orc-card-v2__icon-btn.btn-whats')).toHaveAttribute('title', 'Enviar WhatsApp');
    await expect(successCard.locator('.orc-card-v2__icon-btn.btn-link')).toHaveAttribute('title', 'Copiar link');
    await expect(successCard.locator('.orc-card-v2__icon-btn.btn-email')).toHaveAttribute('title', 'Enviar E-mail');
    await expect(successCard.locator('.orc-card-v2__aprovar-btn.btn-aprovar')).toContainText('Aprovar');

    const layout = await successCard.evaluate((card) => {
      const actions = card.querySelector('.orc-card-v2__actions');
      const buttons = Array.from(
        card.querySelectorAll('.orc-card-v2__icon-btn, .orc-card-v2__aprovar-btn'),
      ).map((btn) => {
        const rect = btn.getBoundingClientRect();
        return { top: rect.top, left: rect.left, width: rect.width };
      });
      return {
        cardClientWidth: card.clientWidth,
        cardScrollWidth: card.scrollWidth,
        actionsClientWidth: actions ? actions.clientWidth : 0,
        actionsScrollWidth: actions ? actions.scrollWidth : 0,
        buttons,
      };
    });

    expect(layout.cardScrollWidth).toBeLessThanOrEqual(layout.cardClientWidth + 1);
    expect(layout.actionsScrollWidth).toBeLessThanOrEqual(layout.actionsClientWidth + 1);
    // v2: ícones na mesma linha; segundo à direita do primeiro
    expect(layout.buttons.length).toBeGreaterThanOrEqual(2);
    expect(layout.buttons[1].left).toBeGreaterThan(layout.buttons[0].left + 8);
    expect(Math.abs(layout.buttons[1].top - layout.buttons[0].top)).toBeLessThan(4);
  });

  test('abre modal de reenvio e envia por WhatsApp e e-mail', async ({ page }) => {
    await page.locator('#messageInput').fill('Ver orçamento 321');
    await page.locator('#sendButton').click();

    const card = page.locator('.opr-card');
    await expect(card).toBeVisible();

    await card.locator('[data-enviar-wa]').click();
    await expect(page.locator('#modal-reenvio-orcamento')).toHaveClass(/open/);
    await page.locator('#reenvio-orc-btn-confirmar').click();
    await expect(page.locator('.message.ai').last()).toContainText('enviado por WhatsApp com sucesso');

    await card.locator('[data-enviar-email]').click();
    await expect(page.locator('#modal-reenvio-orcamento')).toHaveClass(/open/);
    await page.locator('#reenvio-orc-btn-confirmar').click();
    await expect(page.locator('.message.ai').last()).toContainText('enviado por e-mail com sucesso');
  });

  test('copia o link público no card de orçamento criado', async ({ page }) => {
    await page.locator('#messageInput').fill('Prévia orçamento');
    await page.locator('#sendButton').click();
    await page.getByTestId('assistente-orc-preview-card').locator('[data-orc-confirm]').click();

    const copyBtn = page.locator('[data-copy-public-token]');
    await expect(copyBtn).toBeVisible();
    await copyBtn.click();
    await expect(copyBtn).toContainText('Copiado');
  });

  test('envia feedback positivo e negativo', async ({ page }) => {
    await page.locator('#messageInput').fill('Como está meu caixa hoje?');
    await page.locator('#sendButton').click();

    const feedbackBar = page.locator('.feedback-bar').last();
    await feedbackBar.locator('[data-feedback-val="positivo"]').click();
    await expect(feedbackBar).toContainText('Obrigado');

    await page.locator('#messageInput').fill('Como está meu caixa hoje?');
    await page.locator('#sendButton').click();

    const feedbackNegativo = page.locator('.feedback-bar').last();
    await feedbackNegativo.locator('[data-feedback-val="negativo"]').click();
    await page.locator('.feedback-textarea').fill('Faltou detalhar os vencidos');
    await page.locator('.feedback-send-btn').click();
    await expect(feedbackNegativo).toContainText('Obrigado pelo retorno');
  });

  test('nova conversa limpa o estado visual e restaura o welcome', async ({ page }) => {
    await page.locator('#messageInput').fill('Como está meu caixa hoje?');
    await page.locator('#sendButton').click();
    await expect(page.locator('.message.ai').last()).toContainText('Resumo executivo do caixa.');

    await page.locator('#btnNovaConversaMobile').click();
    await expect(page.locator('#welcomeState')).toBeVisible();
    await expect(page.locator('.message.ai')).toHaveCount(1);
  });

  test('restaura histórico salvo após recarregar a página', async ({ page }) => {
    await page.locator('#messageInput').fill('Como está meu caixa hoje?');
    await page.locator('#sendButton').click();
    await expect(page.locator('.message.ai').last()).toContainText('Resumo executivo do caixa.');
    await expect.poll(async () => {
      return await page.evaluate(() => localStorage.getItem('ai_chat_history') || '');
    }).toContain('Resumo executivo do caixa.');

    await page.reload();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.message.ai').last()).toContainText('Resumo executivo do caixa.');
  });
});
