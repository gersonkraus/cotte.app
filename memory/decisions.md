---
title: Decisions
tags:
  - memoria
prioridade: media
status: documentado
---
---
title: Decisions — COTTE
tags:
  - decisao
  - arquitetura
  - memoria
prioridade: alta
status: ativo
---

# Decisions — COTTE

## Stack definida
- Backend: FastAPI + SQLAlchemy
- Frontend: HTML, CSS, JS (Vanilla)
- Banco: PostgreSQL
- IA: Anthropic (Claude — Sonnet + Haiku)
- WhatsApp: Evolution API / Z-API

### Rationale
- Simplicidade > complexidade
- Controle total do frontend
- Baixo custo e fácil manutenção

---

## Arquitetura IA
- interpretador principal: Sonnet
- tarefas simples: Haiku
- evitar uso desnecessário de modelos caros

---

## Diretriz crítica do assistente
- NUNCA executar ação operacional sem ID explícito
- Ex: "aprovar" sem número NÃO pode criar orçamento

---

## Financeiro
- Deve ser integrado com orçamentos
- Separação clara:
  - saldo (Caixa Operacional)
  - a receber
  - a pagar

### Cálculo de Caixa Operacional (Unificado em 21/03/2026)
Para garantir consistência entre Dashboard, Aba de Caixa e Assistente IA, o motor de cálculo foi unificado em `_calcular_estatisticas_caixa`:
- **Fórmula**: `Saldo Inicial` + `Entradas Confirmadas` - `Saídas Confirmadas`.
- **Entradas**: Pagamentos de Orçamentos/Recebíveis + Movimentações Manuais de 'entrada'.
- **Saídas**: Pagamentos de Despesas + Movimentações Manuais de 'saida'.
- **Regra**: Apenas valores com `status == CONFIRMADO` entram no caixa real. Projeções e pendências ficam em "A Receber/Pagar".

---

## UX do sistema
- Sistema feito para usuários leigos
- Tudo deve ser:
  - simples
  - direto
  - sem necessidade de treinamento

---

## Automações
- WhatsApp é canal principal
- Sistema deve:
  - enviar mensagens automáticas
  - permitir ações manuais controladas
  - evitar spam (futuro: rate limit)

---

## Performance
- Evitar loops desnecessários no backend
- Preferir agregações no banco (SQLAlchemy func)

---

## Onboarding (em evolução)
- Ideias aprovadas:
  - auto-trigger no primeiro login
  - sugestão de serviços por segmento
---

## Configurações Globais (Admin)
- Para configurações do painel admin que afetam toda a plataforma (como lista de WhatsApps para monitoramento de novos cadastros), utilizamos arquivos JSON em `static/config/` (ex: `admin_settings.json`), gerenciados por um serviço dedicado (ex: `admin_config.py`).
- Isso evita a criação de colunas no banco de dados para configurações voláteis ou que não pertencem a uma entidade específica (já que a tabela `Usuario` não possui telefone).
- A interface de gerência fica restrita a usuários `is_superadmin = True` através do `admin.html`.

---

## Sistema de Broadcast (23/03/2026)
- Superadmin envia mensagens globais que aparecem como banner no dashboard das empresas
- Model: `Broadcast` (tabela `broadcasts`) — campos: mensagem, tipo (info/aviso/urgente), ativo, expira_em, criado_por_id
- Rotas admin: `POST/GET/DELETE/PATCH /admin/broadcasts`
- Rota empresa: `GET /empresa/broadcasts` — retorna apenas ativos e não expirados
- Frontend admin-config.html: textarea + seletor de tipo + lista com toggle/delete
- Frontend index.html: banners coloridos por tipo com dismiss (localStorage)
---

## Geração de PDF e Templates (03/04/2026)
- **Motores Duais**: O sistema suporta dois motores de renderização:
  - **Moderno**: HTML/CSS via WeasyPrint (Visual Premium B2B).
  - **Clássico**: Desenho direto via FPDF2 (Original Compacto).
- **Fallback Automático**: O `pdf_service.py` possui lógica de segurança; se o motor Moderno falhar (ex: erro de renderização ou dependência), ele tenta gerar o Clássico automaticamente para evitar erro 500 para o usuário final.
- **Unificação de Preferências**: As configurações de `template_publico` (Web) e `template_orcamento` (PDF) foram unificadas na interface. A escolha do usuário em Configurações agora sincroniza ambos os campos para garantir consistência visual em todos os pontos de contato.
- **Mapeamento de Dados Centralizado**: Foi criado o utilitário `app/utils/pdf_utils.py` para centralizar a criação dos dicionários de dados. Nenhum roteador deve montar o `empresa_dict` ou `orc_dict` manualmente, garantindo que o campo `template_orcamento` nunca seja esquecido.
- **Dependências sistêmicas**: Para o motor Moderno funcionar em Debian/Railway, são obrigatórias as bibliotecas: `libgobject-2.0-0`, `libpangocairo-1.0-0` e `fontconfig`.

---

## Organização de Estilos e UX (06/04/2026)
- **Extração de CSS**: Estilos específicos de módulos (como o Precision Atelier do Comercial) devem ser extraídos para arquivos `.css` externos (ex: `comercial-precision.css`) para melhorar a performance (cache) e manutenibilidade.
- **Acessibilidade (A11y)**: Interfaces baseadas em abas e modais devem obrigatoriamente usar papéis ARIA (`role="tablist"`, `tab`, `tabpanel`, `dialog`) e atributos de estado (`aria-selected`, `aria-expanded`) para garantir compatibilidade com tecnologias assistivas.
- **Frontend Services**: O uso de `ApiService.js` e `CacheService.js` é mandatório para novas implementações. Scripts carregados via tag `<script>` não devem usar `export`; devem usar o padrão Singleton/Global. A chave padrão para o token de autenticação no `localStorage` é `cotte_token`.

---

## Evolução do Assistente IA (07/04/2026)
- **Conhecimento Ativo**: O assistente passou a ter um Painel de Contexto (Desktop) que comunica visualmente ao usuário o acesso da IA a módulos específicos (Clientes, Orçamentos, Financeiro, Catálogo).
- **Persistência Turn-by-Turn**: Conversas são persistidas no `localStorage` sob a chave `cotte_ai_history_{sessaoId}`, permitindo continuidade da assistência após recarregamento da página.
- **Transparência de Processamento**: Implementado breadcrumbs de raciocínio (Thinking Steps) para exibir o status interno da IA em tempo real durante o processamento.
- **Multimodalidade e Acessibilidade**: Adicionado suporte nativo a reconhecimento de voz (Speech-to-Text via Web Speech API) e infraestrutura para anexo de arquivos.
- **Rich Text e Links**: Respostas suportam Markdown básico e identificação automática de padrões de entidade (ex: links para `ORC-123`).

---

## UI do Assistente IA — Message Bubble Atelier (07/04/2026)
- A direção visual oficial para `.message-bubble` do assistente IA foi definida como **Direção A (Folha flutuante)**, mantendo frontend **Vanilla JS** e sem alteração obrigatória de markup.
- Bolhas da IA usam hierarquia por materialidade (sombra em camadas, cantos assimétricos e marcador vertical em `::before`) em vez de depender de borda dura 1px.
- O horário permanece em `::after` como **caption** tipográfica (`font-variant-numeric: tabular-nums`) para limpar o bloco principal da mensagem.
- O modo `embed` e o tema `dark` devem manter variações proporcionais da mesma linguagem visual; `prefers-reduced-motion` deve desativar animações/transições de mensagem e indicadores de loading.

---

## Assistente IA — Personalização Híbrida (10/04/2026)
- A personalização do assistente v2 segue regra **híbrida**:
  - `instruções da empresa` = guardrails obrigatórios;
  - `preferência do usuário` = formato de saída e ordem dentro dos guardrails.
- Persistência adicionada:
  - `Empresa.assistente_instrucoes` (instruções por empresa);
  - `assistente_preferencias_usuario` (formato por usuário/domínio: `auto|resumo|tabela`).
- O contexto adaptativo (preferência visual + playbook setorial) é injetado no prompt em ambos os fluxos:
  - `assistente_unificado_v2`;
  - `assistente_v2_stream_core`.
- Governança de edição:
  - somente `gestor/admin` altera instruções da empresa.

