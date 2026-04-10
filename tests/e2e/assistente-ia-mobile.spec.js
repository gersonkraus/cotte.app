// @ts-check
const { test, expect } = require('@playwright/test');

const USER = {
  id: 1,
  nome: 'Teste Mobile',
  email: 'teste@playwright.com',
  is_gestor: true,
  is_superadmin: false,
  empresa_id: 1,
};

function sse(events) {
  return events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join('');
}

async function prepararPagina(page) {
  await page.addInitScript(({ user }) => {
    localStorage.setItem('cotte_token', 'token-playwright');
    localStorage.setItem('cotte_usuario', JSON.stringify(user));
    localStorage.removeItem('ai_chat_history');
    localStorage.removeItem('ai_sessao_id');
    localStorage.removeItem('onboarding_pending');
  }, { user: USER });

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;

    if (path.endsWith('/auth/me')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(USER),
      });
      return;
    }

    if (path.endsWith('/empresa/')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 1,
          nome: 'Empresa Teste',
          plano_nome: 'Premium',
          logo_url: null,
        }),
      });
      return;
    }

    if (path.endsWith('/empresa/resumo-sidebar')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          empresa_nome: 'Empresa Teste',
          plano_nome: 'Premium',
        }),
      });
      return;
    }

    if (path.endsWith('/empresa/uso')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          orcamentos: { atual: 2, limite: 100 },
          usuarios: { atual: 1, limite: 10 },
          validade: null,
        }),
      });
      return;
    }

    if (path.includes('/notificacoes/contagem-nao-lidas')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ total: 0, quantidade: 0, nao_lidas: 0 }),
      });
      return;
    }

    if (path.includes('/notificacoes/')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
      return;
    }

    if (path.endsWith('/ai/status')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'operacional',
          modulos_disponiveis: ['financeiro', 'orcamentos', 'conversacao'],
          cache_stats: { ttl_segundos: 300 },
          versoes_modelos: { principal: 'gpt-4o-mini' },
        }),
      });
      return;
    }

    if (path.endsWith('/ai/assistente/preferencias')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          preferencia_visualizacao: { formato_preferido: 'auto' },
          playbook_setor: { setor: 'geral' },
          instrucoes_empresa: '',
          pode_editar_instrucoes: true,
        }),
      });
      return;
    }

    if (path.endsWith('/ai/feedback')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ sucesso: true }),
      });
      return;
    }

    if (path.endsWith('/ai/assistente/stream')) {
      const body = request.postDataJSON();
      if (body.confirmation_token) {
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          body: sse([
            { phase: 'thinking' },
            { chunk: 'Ação confirmada com sucesso.' },
            {
              is_final: true,
              final_text: 'Ação confirmada com sucesso.',
              metadata: {
                final_text: 'Ação confirmada com sucesso.',
                tipo: 'operador_resultado',
                dados: { acao: 'APROVADO', resposta: 'Ação confirmada com sucesso.' },
                sugestoes: ['Ver orçamento atualizado'],
              },
            },
          ]),
        });
        return;
      }

      if ((body.mensagem || '').toLowerCase().includes('confirmar')) {
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          body: sse([
            { phase: 'thinking' },
            {
              is_final: true,
              final_text: 'Para concluir, confirme os dados abaixo.',
              metadata: {
                final_text: 'Para concluir, confirme os dados abaixo.',
                tipo: 'geral',
                dados: {},
                pending_action: {
                  tool: 'criar_orcamento',
                  confirmation_token: 'tok-mobile-1',
                  args: {
                    cliente_nome: 'Maria',
                    itens: [{ descricao: 'Instalação elétrica', quantidade: 1, valor_unit: 350 }],
                  },
                  extras: {
                    cliente_nome_resolvido: 'Maria',
                  },
                },
              },
            },
          ]),
        });
        return;
      }

      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: sse([
          { phase: 'thinking' },
          { phase: 'tool_running', tool: 'listar_movimentacoes_financeiras' },
          { chunk: 'Resumo executivo do caixa.' },
          {
            is_final: true,
            final_text: 'Resumo executivo do caixa.',
            metadata: {
              final_text: 'Resumo executivo do caixa.',
              tipo: 'financeiro',
              dados: {
                visualizacao_recomendada: { formato_preferido: 'resumo' },
              },
              sugestoes: [
                'Ver contas vencidas',
                'Cobrar clientes em atraso',
                'Projetar caixa dos próximos 7 dias',
              ],
              tool_trace: [
                { tool: 'listar_movimentacoes_financeiras', status: 'ok' },
              ],
            },
          },
        ]),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({}),
    });
  });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/assistente-ia.html');
  await page.waitForLoadState('networkidle');
}

test.beforeEach(async ({ page }) => {
  await prepararPagina(page);
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

  test('abre e fecha preferências pelo header mobile', async ({ page }) => {
    await page.locator('#btnPreferenciasGear').click();
    await expect(page.locator('#assistentePreferenciasCard')).toHaveClass(/is-open/);
    await page.locator('#btnFecharPreferenciasAssistente').click();
    await expect(page.locator('#assistentePreferenciasCard')).not.toHaveClass(/is-open/);
  });
});
