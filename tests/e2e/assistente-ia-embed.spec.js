// @ts-check
const { test, expect } = require('@playwright/test');
const { prepararPaginaAssistente } = require('./assistente-ia-fixture');

test.beforeEach(async ({ page }) => {
  await prepararPaginaAssistente(page, {
    viewport: { width: 480, height: 720 },
    path: '/app/assistente-ia.html?embed=1',
  });
});

test.describe('Assistente IA embed', () => {
  test('mostra sticky context bar com último comando e entidade, e limpa em nova conversa', async ({ page }) => {
    const contextBar = page.locator('#embedContextBar');
    await expect(contextBar).toBeHidden();

    await page.locator('#messageInput').fill('Ver orçamento 321');
    await page.locator('#sendButton').click();

    await expect(page.locator('.opr-card')).toBeVisible();
    await expect(contextBar).toBeVisible();
    await expect(contextBar).toContainText('Último comando: Consultar orçamento');
    await expect(contextBar).toContainText('Orçamento ORC-321-26');

    const newChatBtn = page
      .locator('#btnNovaConversaEmbed:visible, #btnNovaConversaMobile:visible, #btnNovaConversaTop:visible')
      .first();
    if (await newChatBtn.count()) {
      await newChatBtn.click();
    } else {
      await page.evaluate(() => {
        if (typeof window.novaConversaAssistente === 'function') {
          window.novaConversaAssistente();
          return;
        }
        throw new Error('novaConversaAssistente não disponível');
      });
    }
    await expect(page.locator('#welcomeState')).toBeVisible();
    await expect(contextBar).toBeHidden();
  });

  test('restaura a context bar após reload com histórico salvo', async ({ page }) => {
    await page.locator('#messageInput').fill('Como está meu caixa hoje?');
    await page.locator('#sendButton').click();

    await expect(page.locator('.message.ai').last()).toContainText('Resumo executivo do caixa.');
    await expect(page.locator('#embedContextBar')).toContainText('Último comando: Caixa');
    await expect.poll(async () => {
      return await page.evaluate(() => localStorage.getItem('ai_chat_meta') || '');
    }).toContain('Caixa');
    await expect.poll(async () => {
      return await page.evaluate(() => localStorage.getItem('ai_chat_history') || '');
    }).toContain('Resumo executivo do caixa.');

    await page.reload();
    await page.waitForLoadState('networkidle');

    await expect(page.locator('#embedContextBar')).toBeVisible();
    await expect(page.locator('#embedContextBar')).toContainText('Último comando: Caixa');
    await expect(page.locator('.message.ai').last()).toContainText('Resumo executivo do caixa.');
  });

  test('compacta bolhas antigas no embed quando o histórico cresce', async ({ page }) => {
    for (let i = 0; i < 5; i += 1) {
      await page.locator('#messageInput').fill(`Como está meu caixa hoje? #${i}`);
      await page.locator('#sendButton').click();
      await expect(page.locator('.message.ai').last()).toContainText('Resumo executivo do caixa.');
    }

    const compactMessages = page.locator('.message.message--compact');
    await expect(compactMessages).toHaveCount(6);
    await expect(page.locator('.chat-messages')).toHaveClass(/chat-messages--dense/);
    await expect(page.locator('.message').last()).not.toHaveClass(/message--compact/);
  });

  test('pausa e retoma focus follow quando o usuário revisa o histórico', async ({ page }) => {
    await page.evaluate(() => {
      const filler = 'texto extra do histórico '.repeat(12);
      for (let i = 0; i < 16; i += 1) {
        window.addMessage(`Pergunta ${i}`, true, false, false, { forceScroll: true });
        window.addMessage(`Resposta ${i} com algum contexto adicional para ocupar mais espaço no histórico. ${filler}`);
      }
    });
    await page.waitForTimeout(450);

    const beforePause = await page.evaluate(() => {
      const box = document.getElementById('chatMessages');
      window.setChatAutoFollow(false, { scroll: false });
      box.scrollTop = 0;
      box.dispatchEvent(new Event('scroll'));
      return {
        scrollTop: box.scrollTop,
        hasOverflow: box.scrollHeight > box.clientHeight + 100,
        title: document.getElementById('chatScrollBottomBtn')?.getAttribute('title'),
      };
    });

    expect(beforePause.hasOverflow).toBeTruthy();
    expect(beforePause.title).toBe('Retomar acompanhamento da resposta');

    const afterPausedAppend = await page.evaluate(() => {
      const box = document.getElementById('chatMessages');
      const before = box.scrollTop;
      window.addMessage('Continuação da resposta da IA enquanto o usuário lê o histórico.');
      return {
        before,
        after: box.scrollTop,
      };
    });

    expect(afterPausedAppend.after).toBe(afterPausedAppend.before);

    await page.locator('#chatScrollBottomBtn').click();
    await page.waitForTimeout(300);

    const afterResume = await page.evaluate(() => {
      const box = document.getElementById('chatMessages');
      window.addMessage('Mais uma atualização da IA após retomar o follow.');
      return {
        remaining: box.scrollHeight - box.scrollTop - box.clientHeight,
        title: document.getElementById('chatScrollBottomBtn')?.getAttribute('title'),
      };
    });

    expect(afterResume.remaining).toBeLessThan(40);
    expect(afterResume.title).toBe('Últimas mensagens');
  });

  test('usa skeleton clean no loading e renderiza paginação de orçamentos', async ({ page }) => {
    await page.evaluate(() => {
      window.addMessage('', false, false, true);
    });

    await expect(page.locator('.ai-loading-row--skeleton .ai-skeleton-line')).toHaveCount(3);

    await page.evaluate(() => {
      window.processAIResponse({
        sucesso: true,
        tipo_resposta: 'operador_resultado',
        dados: {
          total: 12,
          itens_retornados: 10,
          has_more: true,
          next_cursor: '2026-04-12T00:00:00|123',
          filtros: { status: 'APROVADO', dias: 2 },
          totais_por_status: { APROVADO: 12 },
          orcamentos: [
            { id: 1, numero: 'ORC-1-26', status: 'APROVADO', total: 1200, cliente_nome: 'Ana', criado_em: '2026-04-12T10:00:00' },
            { id: 2, numero: 'ORC-2-26', status: 'APROVADO', total: 980, cliente_nome: 'Bruno', criado_em: '2026-04-12T11:00:00' },
          ],
        },
      }, null, false);
    });

    await expect(page.locator('.orc-list-card')).toBeVisible();
    await expect(page.locator('.orc-list-card__meta')).toContainText('Mostrando 10 de 12');
    await expect(page.locator('[data-orcamentos-load-more]')).toBeVisible();
  });
});
