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
  const path = options.path || '/app/assistente-ia.html';
  let currentOperationalContext = null;

  await page.addInitScript(({ user }) => {
    localStorage.setItem('cotte_token', 'token-playwright');
    localStorage.setItem('cotte_usuario', JSON.stringify(user));
    let clipboardValue = '';
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: async (text) => { clipboardValue = String(text); },
        readText: async () => clipboardValue,
      },
    });
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

    if (path.endsWith('/ai/assistente/contexto/limpar')) {
      currentOperationalContext = null;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          sucesso: true,
          tipo_resposta: 'contexto_limpo',
          dados: { contexto_operacional: {} },
        }),
      });
      return;
    }

    if (path.endsWith('/ai/assistente/contexto/definir')) {
      const body = request.postDataJSON();
      currentOperationalContext = body?.contexto_operacional || null;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          sucesso: true,
          tipo_resposta: 'contexto_atualizado',
          dados: { contexto_operacional: currentOperationalContext || {} },
        }),
      });
      return;
    }

    if (path.endsWith('/ai/assistente/contexto')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          sucesso: true,
          tipo_resposta: 'contexto_operacional',
          dados: { contexto_operacional: currentOperationalContext || {} },
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
      currentOperationalContext = {
        orcamento_id_ativo: 321,
        orcamento_numero_ativo: 'ORC-321-26',
        cliente_nome_ativo: 'Maria',
      };
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
            contexto_operacional: currentOperationalContext,
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

      if ((mensagem.includes('ver orçamento') || mensagem.includes('ver orcamento')) && mensagem.includes('321')) {
        currentOperationalContext = {
          orcamento_id_ativo: 321,
          orcamento_numero_ativo: 'ORC-321-26',
          cliente_nome_ativo: 'Maria',
        };
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
                  contexto_operacional: currentOperationalContext,
                },
              },
            },
          ]),
        });
        return;
      }

      if (mensagem.includes('grafico') || mensagem.includes('gráfico')) {
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          body: sse([
            { phase: 'thinking' },
            { chunk: 'Segue o gráfico financeiro.' },
            {
              is_final: true,
              final_text: 'Segue o gráfico financeiro.',
              metadata: {
                final_text: 'Segue o gráfico financeiro.',
                tipo: 'financeiro',
                dados: {},
                grafico: {
                  tipo: 'bar',
                  dados: {
                    labels: ['Seg', 'Ter', 'Qua'],
                    datasets: [
                      {
                        label: 'Entradas',
                        data: [120, 90, 150],
                        backgroundColor: ['#0891b2', '#0891b2', '#0891b2'],
                      },
                    ],
                  },
                },
              },
            },
          ]),
        });
        return;
      }

      if (mensagem.includes('listar notas') || mensagem.includes('listar produtos') || mensagem.includes('entidade generica')) {
        const entityKey = mensagem.includes('notas') ? 'notas_fiscais' : (mensagem.includes('produtos') ? 'produtos' : 'servicos');
        const entityLabel = entityKey === 'notas_fiscais' ? 'Notas Fiscais' : (entityKey === 'produtos' ? 'Produtos' : 'Serviços');
        const items = [
          { id: 1, nome: entityLabel + ' A', valor: 150.00, status: 'ativo', criado_em: '2026-04-10T10:00:00' },
          { id: 2, nome: entityLabel + ' B', valor: 320.50, status: 'pendente', criado_em: '2026-04-12T14:30:00' },
          { id: 3, nome: entityLabel + ' C', valor: 89.90, status: 'ativo', criado_em: '2026-04-15T09:00:00' },
        ];
        const listDados = {
          is_list: true,
          total: items.length,
          has_more: true,
          next_cursor: 'cursor-test-123',
          limit: 10,
          filtros: {},
          totais_por_status: { ativo: 2, pendente: 1 },
        };
        listDados[entityKey] = items;
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          body: sse([
            { phase: 'thinking' },
            { chunk: 'Encontrei ' + items.length + ' registros.' },
            {
              is_final: true,
              final_text: 'Encontrei ' + items.length + ' registros.',
              metadata: {
                final_text: 'Encontrei ' + items.length + ' registros.',
                tipo: 'geral',
                dados: listDados,
              },
            },
          ]),
        });
        return;
      }

      if (mensagem.includes('lista vazia') || mensagem.includes('sem registros')) {
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          body: sse([
            { phase: 'thinking' },
            { chunk: 'Nenhum registro encontrado.' },
            {
              is_final: true,
              final_text: 'Nenhum registro encontrado.',
              metadata: {
                final_text: 'Nenhum registro encontrado.',
                tipo: 'geral',
                dados: {
                  is_list: true,
                  total: 0,
                  has_more: false,
                  next_cursor: null,
                  itens_desconhecidos: [],
                  filtros: { status: 'cancelado' },
                },
              },
            },
          ]),
        });
        return;
      }

      if (mensagem.includes('register entity')) {
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          body: sse([
            { phase: 'thinking' },
            {
              is_final: true,
              final_text: 'Entidade registrada.',
              metadata: {
                final_text: 'Entidade registrada.',
                tipo: 'geral',
                dados: {
                  is_list: true,
                  total: 2,
                  has_more: false,
                  veiculos: [
                    { id: 1, modelo: ' Civic', placa: 'ABC-1234', ano: 2024 },
                    { id: 2, modelo: 'Corolla', placa: 'XYZ-5678', ano: 2025 },
                  ],
                },
              },
            },
          ]),
        });
        return;
      }

      if (mensagem.includes('entity config auto')) {
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          body: sse([
            { phase: 'thinking' },
            { chunk: 'Listagem com config do backend.' },
            {
              is_final: true,
              final_text: 'Listagem com config do backend.',
              metadata: {
                final_text: 'Listagem com config do backend.',
                tipo: 'geral',
                dados: {
                  is_list: true,
                  total: 2,
                  has_more: false,
                  entity_config: {
                    title: 'Fornecedores',
                    title_key: 'razao_social',
                    columns: [
                      { key: 'razao_social', label: 'Razão Social' },
                      { key: 'cnpj', label: 'CNPJ', format: 'cnpj' },
                      { key: 'total_compras', label: 'Total Compras', format: 'currency', align: 'right' },
                      { key: 'status', label: 'Situação' }
                    ],
                    load_more_label: 'Carregar mais fornecedores'
                  },
                  fornecedores: [
                    { razao_social: 'Empresa Alpha', cnpj: '12345678000190', total_compras: 15000.50, status: 'ativo' },
                    { razao_social: 'Comércio Beta', cnpj: '98765432000110', total_compras: 8500.00, status: 'inativo' },
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
  await page.goto(path);
  await page.waitForLoadState('networkidle');
}

module.exports = {
  USER,
  prepararPaginaAssistente,
};
