---
title: Integração Mercado Livre
tags:
  - tecnico
  - integracao
  - mercado-livre
prioridade: media
status: documentado
---

# Integração Mercado Livre (Cotte)

Documentação de referência do fluxo **OAuth**, **sincronização de pedidos e anúncios**, **webhooks** e **como validar sem depender de uma venda nova**.  
Código principal: `sistema/app/services/mercadolivre_service.py`, rotas em `sistema/app/routers/mercadolivre.py`, montagem sob **`/api/v1`** (`sistema/app/main.py`).

---

## 1. Comportamento quando há uma venda no Mercado Livre

1. O Mercado Livre pode notificar o Cotte via **`POST /api/v1/mercadolivre/notifications`** com `topic: orders` e `resource` apontando para o pedido (ex.: URL ou ID).
2. O serviço obtém o detalhe do pedido na API oficial (**`GET /orders/{id}`**), persiste/atualiza o **snapshot** (`MercadoLivrePedidoSnapshot`) e executa a importação para **orçamentos**.
3. Para cada pedido novo (sem vínculo existente), o sistema chama **`criar_orcamento_core`** com **`origem="Mercado Livre"`**, cliente resolvido a partir do payload do ML, linhas montadas a partir de **`order_items`** (quantidade, `unit_price`, título), e registra o vínculo **`MercadoLivrePedidoVinculo`** (`ml_order_id` ↔ `orcamento_id`).
4. Se o pedido **já** estiver vinculado, o foco é **sincronizar o status** do orçamento com o status do pedido no ML (quando o mapeamento existir em `_status_ml_para_orcamento`).

Não é criada uma entidade separada “Pedido” no domínio do Cotte: a venda entra como **`Orcamento`**, alinhada ao contrato atual do serviço de importação.

---

## 2. Variáveis de ambiente relevantes

| Variável | Papel |
|----------|--------|
| `ML_CLIENT_ID` / `ML_CLIENT_SECRET` | Aplicativo no Mercado Livre / troca de tokens |
| `ML_REDIRECT_URI` | Deve coincidir **exatamente** com o cadastrado no app |
| `ML_AUTH_URL` | URL de autorização (padrão `https://auth.mercadolivre.com.br/authorization`) |
| `ML_API_BASE_URL` | Base da API REST (padrão `https://api.mercadolibre.com`) |
| `ML_OAUTH_SCOPE` | Escopos OAuth (padrão `offline_access read write`) |
| `ML_TOKEN_CRYPTO_SECRET` | Segredo para cifrar tokens no banco (recomendado em produção) |
| `ML_SYNC_CRON_TOKEN` | Token do header `X-ML-Sync-Token` no sync periódico agendado |
| `ML_SYNC_PERIODIC_ENABLED` | Liga o job periódico de sync (ver `sistema/app/main.py`) |
| `ML_SYNC_PERIODIC_INTERVAL_MINUTES` | Intervalo do job |

Detalhes gerais de env: [variaveis_ambiente.md](../../variaveis_ambiente.md) (raiz do repositório).

---

## 3. Endpoints úteis (todos com prefixo `/api/v1/mercadolivre`)

| Método | Caminho | Descrição |
|--------|---------|-----------|
| `GET` | `/auth/url` | Inicia OAuth (PKCE); requer permissão de configurações |
| `GET` | `/oauth/callback` | Callback OAuth (redirect para `configuracoes.html`) |
| `GET` | `/status` | Status da integração (conexão, usuário ML, etc.) |
| `POST` | `/sync/pedidos` | Busca pedidos recentes na API ML e importa orçamentos |
| `POST` | `/sync/anuncios` | Sincroniza anúncios e reflete no catálogo conforme regras do serviço |
| `POST` | `/sync/executar?escopo=...` | `pedidos` \| `catalogo_pull` \| `catalogo_push` (com lock e job) |
| `POST` | `/sync/periodico/run` | Sync em lote para empresas conectadas (header com `ML_SYNC_CRON_TOKEN`) |
| `POST` | `/notifications` | Webhook de notificações do ML (body JSON array ou objeto) |
| `POST` | `/reprocessar/pedido/{ml_order_id}` | Reexecuta importação a partir do **snapshot já existente** |
| `GET` | `/vinculos/pedidos` | Lista vínculos pedido ML ↔ orçamento |
| `GET` | `/vinculos/catalogo` | Lista vínculos item ML ↔ serviço do catálogo |
| `POST` | `/vinculos/catalogo/configurar` | Configura vínculo e modos de sync/push |

Permissões exatas estão nos `Depends` de cada rota em `mercadolivre.py`.

---

## 4. Como testar **sem** aprovar uma venda nova no ML

O Cotte **não** possui um modo “pedido fictício” interno. As opções reais são:

### 4.1 Usar pedidos que já existem na conta

Se a conta do vendedor já teve vendas antigas, **`POST /api/v1/mercadolivre/sync/pedidos`** (ou **`sync/executar?escopo=pedidos`**) chama **`/orders/search/recent`**, grava snapshots e importa. Assim você valida o pipeline **sem criar pedido novo**.

Ordem sugerida de verificação: orçamentos com origem Mercado Livre → **`GET /api/v1/mercadolivre/vinculos/pedidos`**.

### 4.2 Ambiente de desenvolvedores / usuários de teste (Mercado Livre)

O Mercado Livre documenta fluxos com **aplicação de teste** e **usuários de teste** (comprador/vendedor) para simular operações sem dinheiro real. O Cotte usa tokens OAuth normais; o que muda é **credencial e política do lado do ML**, não um segundo endpoint “fake” no backend.

Consulte a documentação oficial atual em [developers.mercadolibre.com](https://developers.mercadolibre.com).

### 4.3 Simular apenas o webhook

**`POST /notifications`** aceita o formato de notificação do ML, mas o processamento de **`topic: orders`** faz **`GET /orders/{id}`** na API real com o token da empresa. Portanto:

- O **`user_id`** da notificação deve corresponder à integração salva.
- O **ID do pedido** deve existir e ser retornado pela API para aquele token.

Notificações totalmente inventadas **sem** pedido válido na API **não** exercitam o fluxo completo.

### 4.4 Reprocessar importação

**`POST /reprocessar/pedido/{ml_order_id}`** só funciona se já existir **`MercadoLivrePedidoSnapshot`** para esse `resource_id`. Serve para **retestar** a importação/atualização do orçamento após mudanças de código ou dados locais, **não** para buscar o pedido pela primeira vez.

---

## 5. Testes automatizados no repositório

- Arquivo: `sistema/tests/test_mercadolivre_service.py`
- Cobertura atual inclui mapeamento de status ML → `StatusOrcamento`, PKCE e round-trip de criptografia de token.

Para fluxos HTTP completos, use mocks de cliente HTTP ou testes de integração dedicados (não obrigatórios neste documento).

---

## 6. Checklist rápido de produção

- [ ] `ML_REDIRECT_URI` igual ao app no ML; OAuth completa com `ml=connected` nas configurações.
- [ ] `ML_TOKEN_CRYPTO_SECRET` definido se usar tokens cifrados (`encv1:`).
- [ ] Migrações aplicadas para tabelas/colunas ML (Alembic em `sistema/alembic/versions/`).
- [ ] URL de notificações do Mercado Livre apontando para **`https://<APP>/api/v1/mercadolivre/notifications`** (ajustar conforme `APP_URL` e proxy).
- [ ] Para sync agendado: `ML_SYNC_CRON_TOKEN` e chamada ao endpoint periódico protegido por header.

---

## 7. Referências de código

| Tema | Onde |
|------|------|
| Importação pedido → orçamento | `MercadoLivreService._importar_pedidos_snapshot_para_orcamentos` |
| Montagem de linhas | `_montar_itens_orcamento_de_pedido` |
| Webhook | `processar_notificacao_webhook`, `_processar_notificacao_pedido` |
| Sync pedidos | `sync_pedidos` |
| Push catálogo | `_push_catalogo_updates` |
| Normalização ID do anúncio | `normalizar_ml_item_id`, `ml_item_api_id_valido` |

---

*Última revisão alinhada ao código em 2026-05.*
