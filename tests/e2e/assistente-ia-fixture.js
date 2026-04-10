// @ts-check

const USER = {
  id: 1,
  nome: 'Teste Assistente',
  email: 'teste@playwright.com',
  is_gestor: true,
  is_superadmin: false,
  empresa_id: 1,
};

function sse(events) {
  return events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join('');
}

async function prepararPaginaAssistente(page, options = {}) {
  const viewport = options.viewport || { width: 390, height: 844 };

  await page.addInitScript(({ user }) => {
    localStorage.setItem('cotte_token', 'token-playwright');
    localStorage.setItem('cotte_usuario', JSON.stringify(user));
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

    if (path.endsWith('/ai/orcamento/confirmar')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          sucesso: true,
          tipo_resposta: 'orcamento_criado',
          dados: {
            id: 321,
            numero: 'ORC-321-26',
            cliente_nome: 'Maria',
            servico: 'Instalação elétrica',
            total: 350,
            link_publico: 'tok-public-321',
            tem_telefone: true,
            tem_email: true,
          },
        }),
      });
      return;
    }

    if (path.endsWith('/orcamentos/321')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 321,
          numero: 'ORC-321-26',
          status: 'enviado',
          enviado_em: '2026-04-10T10:00:00',
          tem_telefone: true,
          tem_email: true,
        }),
      });
      return;
    }

    if (path.endsWith('/orcamentos/321/enviar-whatsapp') || path.endsWith('/orcamentos/321/enviar-email')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ sucesso: true }),
      });
      return;
    }

    if (path.endsWith('/ai/assistente/stream')) {
      const body = request.postDataJSON();
      const mensagem = String(body.mensagem || '').toLowerCase();

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

      if (mensagem.includes('confirmar')) {
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

      if (mensagem.includes('prévia') || mensagem.includes('previa')) {
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          body: sse([
            { phase: 'thinking' },
            {
              is_final: true,
              final_text: 'Prévia pronta.',
              metadata: {
                final_text: 'Prévia pronta.',
                tipo: 'orcamento_preview',
                dados: {
                  cliente_nome: 'Maria',
                  servico: 'Instalação elétrica',
                  valor: 350,
                  desconto: 0,
                  desconto_tipo: 'percentual',
                  observacoes: 'Executar amanhã',
                },
              },
            },
          ]),
        });
        return;
      }

      if (mensagem.includes('ver orçamento')) {
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          body: sse([
            { phase: 'thinking' },
            {
              is_final: true,
              final_text: 'Aqui estão os detalhes.',
              metadata: {
                final_text: 'Aqui estão os detalhes.',
                tipo: 'operador_resultado',
                dados: {
                  acao: 'VER',
                  id: 321,
                  numero: 'ORC-321-26',
                  cliente: 'Maria',
                  total: 350,
                  status: 'Enviado',
                  tem_telefone: true,
                  tem_email: true,
                  itens: [
                    { descricao: 'Instalação elétrica', total: 350 },
                  ],
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

  await page.setViewportSize(viewport);
  await page.goto('/assistente-ia.html');
  await page.waitForLoadState('networkidle');
}

module.exports = {
  USER,
  prepararPaginaAssistente,
};
