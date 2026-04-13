---
title: Graph Report
tags:
  - documentacao
prioridade: media
status: documentado
---
# Graph Report - sistema/app/  (2026-04-11)

## Corpus Check
- 125 files · ~144,594 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3066 nodes · 20231 edges · 69 communities detected
- Extraction: 25% EXTRACTED · 75% INFERRED · 0% AMBIGUOUS · INFERRED: 15221 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `Usuario` - 524 edges
2. `StatusOrcamento` - 478 edges
3. `Orcamento` - 435 edges
4. `Empresa` - 428 edges
5. `Cliente` - 374 edges
6. `ModoAgendamentoOrcamento` - 310 edges
7. `StatusDocumentoEmpresa` - 246 edges
8. `LeadScore` - 243 edges
9. `StatusPipeline` - 242 edges
10. `TipoInteracao` - 240 edges

## Surprising Connections (you probably didn't know these)
- `Máquina de estados de orçamento — transições compartilhadas entre API e bot.` --uses--> `StatusOrcamento`  [INFERRED]
  sistema/app/utils/orcamento_status.py → sistema/app/models/models.py
- `Retorna True se a transição de status for permitida pela máquina de estados (ide` --uses--> `StatusOrcamento`  [INFERRED]
  sistema/app/utils/orcamento_status.py → sistema/app/models/models.py
- `Mensagem quando a transição não é permitida (HTTP ou bot WhatsApp/dashboard).` --uses--> `StatusOrcamento`  [INFERRED]
  sistema/app/utils/orcamento_status.py → sistema/app/models/models.py
- `Sistema de cache para repositórios e serviços. Implementa cache com Redis (fallb` --uses--> `ConfiguracaoFinanceira`  [INFERRED]
  sistema/app/core/cache.py → sistema/app/models/models.py
- `Cria cliente Redis se REDIS_URL estiver configurado.` --uses--> `ConfiguracaoFinanceira`  [INFERRED]
  sistema/app/core/cache.py → sistema/app/models/models.py

## Communities

### Community 0 - "Admin Router & Auth"
Cohesion: 0.03
Nodes (439): Gera plano de correção sugerido sem executar SQL/migrations., Converte ORM Empresa → EmpresaAdminOut (inclui campos de assinatura)., Endpoint de uso único para criar o superadmin. Protegido por setup_key., Retorna estatísticas gerais do painel admin., Lista todas as empresas com contagem de orçamentos, clientes e usuários., Cria uma nova empresa com seu primeiro usuário gestor., Edita os dados de uma empresa existente., Ativa ou desativa uma empresa. (+431 more)

### Community 1 - "Plans & Modules Admin"
Cohesion: 0.02
Nodes (359): atualizar_modulo(), atualizar_plano(), criar_modulo(), criar_plano(), deletar_plano(), listar_modulos(), listar_planos(), Atualiza um plano/pacote e seus módulos associados. (+351 more)

### Community 2 - "Client Auth Flow"
Cohesion: 0.09
Nodes (305): Cadastro self-service: cria empresa em trial (14 dias) e envia credenciais por W, Retorna configurações públicas do sistema, úteis para telas de login ou landing, Autentica o usuário e retorna um token JWT de acesso., Inicia recuperação de senha por token temporário.     Sempre retorna sucesso par, Redefine a senha do usuário a partir de um token de recuperação., Retorna os dados do usuário autenticado., Registra uma nova empresa e o usuário gestor fundador., BaseModel (+297 more)

### Community 3 - "Financial Categories & Cache"
Cohesion: 0.1
Nodes (215): Retorna o backend atual: 'redis' ou 'memory'., CategoriaFinanceiraRepository,  enrich conta,  enrich pagamento, atualizar_categoria(), atualizar_configuracoes(), atualizar_conta(), atualizar_despesa() (+207 more)

### Community 4 - "Audio Transcription & WhatsApp"
Cohesion: 0.01
Nodes (166): _baixar_audio_evolution(), mensagem_voz_nao_configurada(), [INOVAÇÃO] Transcrição de áudio para o canal WhatsApp do operador.  Fluxo: 1. Ba, Mensagem amigável quando a transcrição não está disponível., Baixa e transcreve um áudio do WhatsApp.      Args:         message_data: dict c, Baixa o áudio da Evolution API e retorna os bytes., Envia áudio para a API Whisper (OpenAI) e retorna a transcrição., transcrever_audio_wpp() (+158 more)

### Community 5 - "Base Repository Pattern"
Cohesion: 0.02
Nodes (131): Remove um registro por ID., Verifica se um registro existe pelo ID., Busca um registro por um campo específico., Repositório base com operações CRUD síncronas e cache., Busca um registro por ID., Busca múltiplos registros com paginação e filtros., Cria um novo registro., Atualiza um registro existente. (+123 more)

### Community 6 - "Auth Middleware & Presence"
Cohesion: 0.03
Nodes (121):  normalizar utc,  presenca esta desatualizada,  verificar modulo legado,  agora ts,  hash token reset,  normalizar ip,  validar rate limit reset, esqueci_senha() (+113 more)

### Community 7 - "WhatsApp Provider Abstraction"
Cohesion: 0.04
Nodes (46): ABC, Notifications, Whatsapp Base, Whatsapp Service, SendResult, Interface abstrata para providers de WhatsApp.  Qualquer provider (Z-API, Evolut, Executa uma coroutine com retry em caso de falhas transitárias de rede.      Ten, Contrato que todo provider de WhatsApp deve cumprir. (+38 more)

### Community 8 - "Scheduling Schemas"
Cohesion: 0.24
Nodes (87): AgendamentoCalendario, AgendamentoComOpcoes, AgendamentoCreate, AgendamentoCreateComOpcoes, AgendamentoDashboard, AgendamentoOpcaoCreate, AgendamentoOpcaoOut, AgendamentoOut (+79 more)

### Community 9 - "Discount & Validation Utils"
Cohesion: 0.03
Nodes (78): aplicar_desconto(), erro_validacao_desconto(), Validação e cálculo de desconto em orçamentos (NEG-05)., Limite de desconto efetivo: primeiro do usuário, depois da empresa, depois 100., Retorna mensagem de erro se o desconto for inválido; None se válido.     - Perce, Retorna o total após aplicar o desconto (usa Decimal para precisão monetária)., resolver_max_percent_desconto(), Desconto (+70 more)

### Community 10 - "Financial Service Core"
Cohesion: 0.06
Nodes (66):  assert empresa,  atualizar status orcamento,  build busca filter,  buscar pagamento por idempotencia,  calcular estatisticas caixa,  criar conta saldo se necessario,  normalizar chave idempotencia,  recalcular status conta (+58 more)

### Community 11 - "Company Router"
Cohesion: 0.05
Nodes (62):  erro instancia inexistente, atualizar_banco_pix(), atualizar_empresa(), atualizar_usuario_empresa(), criar_banco_pix(), criar_usuario_empresa(), deletar_banco_pix(), _erro_instancia_inexistente() (+54 more)

### Community 12 - "Scheduling Service"
Cohesion: 0.08
Nodes (63):  calcular data fim,  enriquecer out,  gerar numero,  ja notificado agendamento,  merge config,  montar mensagem agendamento template,  normalize to utc,  now (+55 more)

### Community 13 - "Email Service"
Cohesion: 0.08
Nodes (50):  enviar via brevo api,  enviar via smtp,  esta em event loop,  formatar brl,  montar html email confirmacao aceite,  montar html email orcamento,  montar html email reset senha,  montar texto email reset senha (+42 more)

### Community 14 - "AI Intent Classifier"
Cohesion: 0.06
Nodes (36): AIResponse, detectar_intencao_assistente(), detectar_intencao_assistente_async(), from_string(), get_intention_classifier(), IntentionClassifier, Classificador de Intenção Híbrido - COTTE AI Hub Etapa 4: Classificador de Inten, Compila padrões regex para performance (+28 more)

### Community 15 - "Admin Panel & Reports"
Cohesion: 0.09
Nodes (43):  serialize snapshot,  to out,  to out with counts, atualizar_assinatura(), atualizar_template_admin(), atualizar_usuario_admin(), criar_broadcast(), criar_empresa() (+35 more)

### Community 16 - "Catalog Service"
Cohesion: 0.17
Nodes (35): _adicionar_item_orcamento(), _aprovar_orcamento_via_bot(), _brl_fmt(), _buscar_orcamento(), _calcular_total(), _cliente_por_telefone(), _confirmar_aceite_pendente(), _criar_orcamento_via_bot() (+27 more)

### Community 17 - "Commercial CRM Pipeline"
Cohesion: 0.1
Nodes (34):  seed categorias padrao,  seed servicos demonstracao, Service para lógica de negócio do catálogo de serviços/produtos., Cria categorias padrão para empresa recém-criada (idempotente)., Cria serviços de demonstração para empresa recém-criada (idempotente)., Executa todos os seeds padrão do catálogo para uma empresa., seed_catalogo_padrao(), _seed_categorias_padrao() (+26 more)

### Community 18 - "PDF Generation"
Cohesion: 0.12
Nodes (30): Tool Executor,  args hash,  cache get,  cache prune,  cache put,  check rate limit,  consume token,  issue token (+22 more)

### Community 19 - "PIX Payment Integration"
Cohesion: 0.12
Nodes (28): add_seen_suggestions(), append(), append_db(), build(), build_context(), _build_dynamic_profile(), _cache_get(), _cache_key() (+20 more)

### Community 20 - "WhatsApp Bot Orchestrator"
Cohesion: 0.09
Nodes (20):  build redis client, _build_redis_client(), cached(), CacheManager, generate_cache_key(), get_cached_config(), invalidate_cache_for_model(), Sistema de cache para repositórios e serviços. Implementa cache com Redis (fallb (+12 more)

### Community 21 - "Quote Notifications"
Cohesion: 0.1
Nodes (27): Pdf Service,  brl,  enriquecer orcamento,  hex to rgb,  normalizar logo url,  registrar fontes,  sanitize,  texto sobre cor (+19 more)

### Community 22 - "OTP & Security"
Cohesion: 0.11
Nodes (19): AIPromptLoader, get_prompt(), get_prompt_loader(), load_prompts(), PromptConfig, PromptLoader - COTTE AI Hub Etapa 3: Externalização de Prompts para arquivos YAM, Configuração de um prompt específico, Inicializa o PromptLoader.                  Args:             prompts_dir: Diret (+11 more)

### Community 23 - "AI Hub Router"
Cohesion: 0.15
Nodes (12): Rate Limit Service, _agora_ts(), IaInterpretarRateLimiter, _now(), PublicEndpointRateLimiter, RateLimitResult, Rate limit para endpoints públicos sem autenticação (aceitar/recusar/ajuste)., Rate limit para o webhook WhatsApp (POST /whatsapp/webhook).     Limite mais gen (+4 more)

### Community 24 - "Webhooks & External"
Cohesion: 0.2
Nodes (16): Openapi Docs, add_error_responses(), add_examples_to_schemas(), create_api_documentation(), enhance_openapi_schema(), enhance_schemas_descriptions(), generate_model_documentation(), get_model_example() (+8 more)

### Community 25 - "Subscription Management"
Cohesion: 0.17
Nodes (15): Pix Service,  crc16,  emv field,  sanitize name, _crc16(), _emv_field(), gerar_payload_pix(), gerar_qrcode_pix() (+7 more)

### Community 26 - "Rate Limiting"
Cohesion: 0.28
Nodes (15): _detectar_plano(), _extrair_cupom(), _extrair_data(), _extrair_email(), _extrair_evento(), _extrair_nome_plano(), _extrair_signature(), _extrair_token() (+7 more)

### Community 27 - "Context Builder"
Cohesion: 0.26
Nodes (14): criar_preview_html(), extrair_variaveis_html(), gerar_valores_padrao(), processar_documento_html_com_variaveis(), Serviço para processamento de documentos HTML com substituição de variáveis.  Es, Gera valores padrão para variáveis com base em nomes comuns.          Args:, Extrai todas as variáveis do formato {nome_variavel} de um conteúdo HTML., Processa um documento HTML com variáveis, realizando validação e substituição. (+6 more)

### Community 28 - "Document Service"
Cohesion: 0.41
Nodes (12): _acao_adicionar_item(), _acao_aprovar(), _acao_criar(), _acao_desconto(), _acao_enviar(), _acao_recusar(), _acao_remover_item(), _acao_ver() (+4 more)

### Community 29 - "Client Service"
Cohesion: 0.24
Nodes (7): _extrair_bearer_token(), _processar_audio_operador(), _tratar_connection_update(), _validar_autenticacao_webhook(), _webhook_evolution(), webhook_whatsapp(), _webhook_zapi()

### Community 30 - "Template & Segment"
Cohesion: 0.35
Nodes (10): _detectar_resposta_poll(), _enviar_resposta(), _limpar_pending_wpp(), _mensagem_confirmacao_whatsapp(), processar_operador_wpp(), Monta texto da enquete com contexto operacional (cliente, orçamento, alterações), _recuperar_pending_wpp(), _salvar_pending_wpp() (+2 more)

### Community 31 - "R2 Cloud Storage"
Cohesion: 0.25
Nodes (9):  extensao do nome,  resolver caminho base empresa, _extensao_do_nome(), gerar_slug_documento(), montar_nome_download(), Retorna a URL do arquivo.     Para arquivos no R2, retorna a URL diretamente., resolver_arquivo_path(), salvar_upload_documento() (+1 more)

### Community 32 - "Audit & Logging"
Cohesion: 0.38
Nodes (9): _base_playbook_por_setor(), build_playbook_setor(), get_context_for_prompt(), inferir_dominio(), _normalizar_dominio(), _normalizar_formato(), obter_preferencia_visualizacao(), _resolver_setor_usuario() (+1 more)

### Community 33 - "Onboarding Service"
Cohesion: 0.39
Nodes (7): Onboarding Service,  calcular status,  payload vazio, _calcular_status(), formatar_resposta_onboarding(), get_onboarding_status(), _payload_vazio()

### Community 34 - "Auto Scheduling"
Cohesion: 0.46
Nodes (7):  gerar opcoes automaticas, criar_agendamento_automatico(), _gerar_opcoes_automaticas(), liberar_pre_agendamento_lote(), listar_pre_agendamento_fila(), processar_agendamento_apos_aprovacao(), Agendamento Auto Service

### Community 35 - "Lead Import"
Cohesion: 0.25
Nodes (8): Operador Wpp Service,  detectar resposta poll,  limpar pending wpp,  mensagem confirmacao whatsapp,  recuperar pending wpp,  salvar pending wpp,  titulo confirmacao tool,  wpp sessao id

### Community 36 - "AI Tools Base"
Cohesion: 0.62
Nodes (6): checar_limite_ia(), checar_limite_orcamentos(), checar_limite_usuarios(), checar_limite_whatsapp(), get_plano_empresa(), verificar_modulo()

### Community 37 - "AI Catalog Tools"
Cohesion: 0.38
Nodes (6):  migrar json se necessario, get_admin_config(), _migrar_json_se_necessario(), Na primeira execução, importa dados do JSON legado para o banco., save_admin_config(), Admin Config

### Community 38 - "AI Client Tools"
Cohesion: 0.33
Nodes (6): Plan Defaults Config, get_plan_defaults(), Configuração de limites padrão por plano (trial, starter, pro, business). Persis, Lê plan_defaults.json ou retorna os valores padrão., Salva plan_defaults.json.     Espera chaves trial, starter, pro, business com li, save_plan_defaults()

### Community 39 - "AI Financial Tools"
Cohesion: 0.33
Nodes (6): Whatsapp Sanitizer, Sanitização de inputs não-confiáveis recebidos pelo webhook do WhatsApp.  SEC-05, Extrai apenas dígitos do telefone e valida o comprimento.     Retorna a string d, Remove bytes nulos e caracteres de controle (exceto \\t, \\n, \\r),     normaliz, sanitizar_mensagem(), sanitizar_telefone()

### Community 40 - "AI Schedule Tools"
Cohesion: 0.33
Nodes (6): Orcamento Status, Máquina de estados de orçamento — transições compartilhadas entre API e bot., Retorna True se a transição de status for permitida pela máquina de estados (ide, Mensagem quando a transição não é permitida (HTTP ou bot WhatsApp/dashboard)., texto_transicao_negada(), transicao_permitida()

### Community 41 - "AI Quote Tools"
Cohesion: 0.4
Nodes (5): Pricing Config, get_pricing_config(), Lê o pricing.json ou retorna defaults., Salva o pricing.json (merge com defaults) e retorna o resultado., save_pricing_config()

### Community 42 - "AI Log Tools"
Cohesion: 0.33
Nodes (6):  calcular score,  is usuario online,  lead to out,  render template,  validar contato lead, Comercial Helpers

### Community 43 - "Destructive Preview Guard"
Cohesion: 0.4
Nodes (4): gerar_csv_response(), Utilitários centralizados para geração de CSV.  Elimina duplicação do padrão io., Gera StreamingResponse CSV com delimitador ponto-e-vírgula.      Args:         h, Csv Utils

### Community 44 - "Phone Utils"
Cohesion: 0.5
Nodes (3): parse_csv_to_leads(), Parse CSV base64 para lista de leads., Csv Parser

### Community 45 - "CSV Import Utils"
Cohesion: 1.0
Nodes (2): openai tools payload,   Init  

### Community 46 - "OpenAPI Docs"
Cohesion: 1.0
Nodes (2): ToolSpec,  Base

### Community 47 - "Config & Settings"
Cohesion: 1.0
Nodes (1): URL da imagem do serviço vinculado (catálogo), para exibir no orçamento.

### Community 48 - "Database & Session"
Cohesion: 1.0
Nodes (1): Extrai JSON válido de texto da IA.                  Args:             text: Text

### Community 49 - "Security Middleware"
Cohesion: 1.0
Nodes (1): Tenta uma estratégia específica de extração

### Community 50 - "Static Cache Middleware"
Cohesion: 1.0
Nodes (1): Extrai JSON de codeblocks markdown ```json ... ```

### Community 51 - "JSON Extractor"
Cohesion: 1.0
Nodes (1): Extrai JSON usando regex com balanceamento de chaves.         Encontra o primeir

### Community 52 - "Prompt Loader"
Cohesion: 1.0
Nodes (1): Extrai JSON localizando o primeiro '{' e o último '}'.         Útil quando a IA

### Community 53 - "Seed & Defaults"
Cohesion: 1.0
Nodes (1): Estratégia greedy - pega tudo entre o primeiro { e último }

### Community 54 - "Notification Router"
Cohesion: 1.0
Nodes (1): Extrai JSON e retorna metadados sobre o processo.                  Returns:

### Community 55 - "Public Quote View"
Cohesion: 1.0
Nodes (1): Retorna o status de conexão da instância (deve incluir chave 'connected': bool).

### Community 56 - "Commercial Templates"
Cohesion: 1.0
Nodes (1): Retorna o QR Code para conectar o WhatsApp (chave 'qrcode' em base64).

### Community 57 - "Commercial Campaigns"
Cohesion: 1.0
Nodes (1): Desconecta a instância. Retorna True em caso de sucesso.

### Community 58 - "Commercial Leads"
Cohesion: 1.0
Nodes (1): Envia texto simples. Retorna True em caso de sucesso.

### Community 59 - "Commercial Proposals"
Cohesion: 1.0
Nodes (1): Envia um arquivo PDF como anexo. Retorna True em caso de sucesso.

### Community 60 - "Schema Drift Monitor"
Cohesion: 1.0
Nodes (1): Envia o orçamento ao cliente (link clicável + PDF).         O dict 'orcamento' c

### Community 61 - "Operator WhatsApp Service"
Cohesion: 1.0
Nodes (1): Notifica o operador quando o cliente abre o orçamento pela primeira vez.

### Community 62 - "Comercial Config"
Cohesion: 1.0
Nodes (1): Notifica o operador quando o cliente aceita o orçamento.

### Community 63 - "Financeiro Router"
Cohesion: 1.0
Nodes (1): Notifica o operador quando o cliente recusa o orçamento.

### Community 64 - "Documents Router"
Cohesion: 1.0
Nodes (1): Envia lembrete automático ao cliente sobre orçamento pendente.

### Community 65 - "Roles & Permissions"
Cohesion: 1.0
Nodes (1): Garante DDI 55 nos dígitos: 5548999887766

### Community 66 - "Relatorios Router"
Cohesion: 1.0
Nodes (1): Calcula a data de validade a partir de hoje + dias, retorna no formato DD/MM/AAA

### Community 67 - "Catalogo Router"
Cohesion: 1.0
Nodes (1): Assets do frontend não devem consumir o contador: um carregamento de página

### Community 68 - "Client Router"
Cohesion: 1.0
Nodes (1): Knowledge Base

## Knowledge Gaps
- **444 isolated node(s):** `Repositório base com operações CRUD síncronas e cache.`, `Busca um registro por ID.`, `Busca múltiplos registros com paginação e filtros.`, `Cria um novo registro.`, `Atualiza um registro existente.` (+439 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `CSV Import Utils`** (2 nodes): `openai tools payload`, `  Init  `
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `OpenAPI Docs`** (2 nodes): `ToolSpec`, ` Base`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Config & Settings`** (1 nodes): `URL da imagem do serviço vinculado (catálogo), para exibir no orçamento.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Database & Session`** (1 nodes): `Extrai JSON válido de texto da IA.                  Args:             text: Text`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Security Middleware`** (1 nodes): `Tenta uma estratégia específica de extração`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Static Cache Middleware`** (1 nodes): `Extrai JSON de codeblocks markdown ```json ... ````
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `JSON Extractor`** (1 nodes): `Extrai JSON usando regex com balanceamento de chaves.         Encontra o primeir`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Prompt Loader`** (1 nodes): `Extrai JSON localizando o primeiro '{' e o último '}'.         Útil quando a IA`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Seed & Defaults`** (1 nodes): `Estratégia greedy - pega tudo entre o primeiro { e último }`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Notification Router`** (1 nodes): `Extrai JSON e retorna metadados sobre o processo.                  Returns:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Public Quote View`** (1 nodes): `Retorna o status de conexão da instância (deve incluir chave 'connected': bool).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Commercial Templates`** (1 nodes): `Retorna o QR Code para conectar o WhatsApp (chave 'qrcode' em base64).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Commercial Campaigns`** (1 nodes): `Desconecta a instância. Retorna True em caso de sucesso.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Commercial Leads`** (1 nodes): `Envia texto simples. Retorna True em caso de sucesso.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Commercial Proposals`** (1 nodes): `Envia um arquivo PDF como anexo. Retorna True em caso de sucesso.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Schema Drift Monitor`** (1 nodes): `Envia o orçamento ao cliente (link clicável + PDF).         O dict 'orcamento' c`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Operator WhatsApp Service`** (1 nodes): `Notifica o operador quando o cliente abre o orçamento pela primeira vez.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Comercial Config`** (1 nodes): `Notifica o operador quando o cliente aceita o orçamento.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Financeiro Router`** (1 nodes): `Notifica o operador quando o cliente recusa o orçamento.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Documents Router`** (1 nodes): `Envia lembrete automático ao cliente sobre orçamento pendente.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Roles & Permissions`** (1 nodes): `Garante DDI 55 nos dígitos: 5548999887766`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Relatorios Router`** (1 nodes): `Calcula a data de validade a partir de hoje + dias, retorna no formato DD/MM/AAA`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Catalogo Router`** (1 nodes): `Assets do frontend não devem consumir o contador: um carregamento de página`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Client Router`** (1 nodes): `Knowledge Base`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Models` connect `Plans & Modules Admin` to `Admin Router & Auth`, `Client Auth Flow`, `Financial Categories & Cache`, `Audio Transcription & WhatsApp`, `Base Repository Pattern`, `Auth Middleware & Presence`, `WhatsApp Provider Abstraction`, `Scheduling Schemas`, `Discount & Validation Utils`, `Financial Service Core`, `Company Router`, `Scheduling Service`, `AI Intent Classifier`, `Admin Panel & Reports`, `Commercial CRM Pipeline`, `PDF Generation`, `WhatsApp Bot Orchestrator`, `Onboarding Service`, `Auto Scheduling`, `AI Catalog Tools`, `AI Schedule Tools`, `AI Log Tools`?**
  _High betweenness centrality (0.232) - this node is a cross-community bridge._
- **Why does `Empresa` connect `Plans & Modules Admin` to `Admin Router & Auth`, `Client Auth Flow`, `Financial Categories & Cache`, `Audio Transcription & WhatsApp`, `WhatsApp Provider Abstraction`, `Scheduling Schemas`?**
  _High betweenness centrality (0.142) - this node is a cross-community bridge._
- **Why does `Usuario` connect `Plans & Modules Admin` to `Admin Router & Auth`, `Client Auth Flow`, `Financial Categories & Cache`, `Base Repository Pattern`, `Auth Middleware & Presence`, `Scheduling Schemas`, `PDF Generation`?**
  _High betweenness centrality (0.131) - this node is a cross-community bridge._
- **Are the 521 inferred relationships involving `Usuario` (e.g. with `EmpresaRepository` and `Repositório para operações com empresas.`) actually correct?**
  _`Usuario` has 521 INFERRED edges - model-reasoned connections that need verification._
- **Are the 475 inferred relationships involving `StatusOrcamento` (e.g. with `OrcamentoRepository` and `Repositório especializado para orçamentos.`) actually correct?**
  _`StatusOrcamento` has 475 INFERRED edges - model-reasoned connections that need verification._
- **Are the 432 inferred relationships involving `Orcamento` (e.g. with `OrcamentoRepository` and `Repositório especializado para orçamentos.`) actually correct?**
  _`Orcamento` has 432 INFERRED edges - model-reasoned connections that need verification._
- **Are the 425 inferred relationships involving `Empresa` (e.g. with `Monta a lista de origens CORS a partir do .env.` and `Garante que erros 500 retornem JSON; não sobrescreve HTTPException (400, 401, 40`) actually correct?**
  _`Empresa` has 425 INFERRED edges - model-reasoned connections that need verification._