---
title: Claude
tags:
  - documentacao
prioridade: alta
status: documentado
---
---
title: Claude
tags:
  - documentacao
prioridade: alta
status: documentado
---
# CLAUDE.md — GUIA OFICIAL COTTE (Atualizado 06/04/2026)

import @RTK.md

@memory/user.md
@memory/preferences.md
@memory/decisions.md
@memory/people.md

---

## ⚡ AUTO-TAGGING BASE (Automático)

Toda sessão inicia com:
```bash
python scripts/auto_tagging_base.py --apply
Ver detalhes em scripts/README_TAGGING.md.

🧠 MEMÓRIA PERSISTENTE E MCP (OBRIGATÓRIO)
Ao iniciar cada sessão
### MCP e Inicialização (OBRIGATÓRIO)
- **Sempre comece lendo o arquivo stacklit.json via MCP antes de qualquer coisa.**
- **Use as ferramentas stacklit para navegar no codebase.**

Ler obrigatoriamente os 4 arquivos de memória.
Ao encerrar cada sessão
Atualizar apenas informações duráveis (decisões técnicas, padrões, arquitetura, preferências).

🎯 Stack Oficial (NUNCA MUDE)

Backend: FastAPI + SQLAlchemy (async) + Python 3.11+
Frontend: HTML5 + CSS3 (Tailwind CDN + CSS custom) + JavaScript Vanilla puro
IA: LiteLLM (`app/services/ia_service.py` + `cotte_ai_hub.py`) — modelos e chaves via `.env` (`AI_PROVIDER`, `AI_MODEL`, `AI_TECHNICAL_MODEL`, `AI_MODEL_FALLBACK`, `OPENROUTER_API_KEY` / `AI_API_KEY`, etc.)
WhatsApp: Evolution API (provider default — whatsapp_evolution.py)
E-mail: Brevo
Armazenamento: Cloudflare R2 (r2_service.py)
Deploy: Railway (Root Directory = sistema)
Banco: PostgreSQL + Alembic


🚀 Objetivo de Trabalho (Nova Prioridade)

Performance máxima
Frontend Vanilla JS perfeito integrado com backend
Mínimo absoluto de falhas (idempotência, error handling robusto, cache, retry)

Regra de ouro: Alterar o mínimo necessário, mas sempre melhorar performance e robustez quando tocar em um arquivo.

⚙️ Fluxo Obrigatório de Execução

Entender o pedido
Localizar com qmd (busca rápida em todo o diretório)
Ler a documentação real do projeto:
README.md
arquitetura_sistema.md
fluxo_do_sistema.md
docs/ (todos os arquivos)
conductor/code_styleguides/

Montar plano curto
Avaliar impacto em performance/integração/falhas
Editar


🔒 Regras Críticas para MÍNIMO DE FALHAS
Integração Frontend ↔ Backend (OBRIGATÓRIO)

Frontend → Sempre usar cotte-frontend/js/services/ApiService.js + CacheService.js. Nunca usar fetch direto.
Todo endpoint deve retornar { success: bool, data?: any, error?: string, code?: string }.
Todo botão/ação no frontend deve ter loading state + error handling (usar ux-improvements.js como base).
PDF, envio WhatsApp e aprovação → polling máximo 30s + feedback visual imediato.
Retry automático (3 tentativas) em chamadas críticas.

Performance (OBRIGATÓRIO)

Backend: selectinload/joinedload, índices em FK, cache Redis quando disponível.
Frontend: limite inicial 8 itens + “Carregar mais”, cache agressivo, evitar reflows.
IA: usar ai_prompt_loader.py + limite de tokens.
WhatsApp: sempre passar por whatsapp_sanitizer.py.

Idempotência e Segurança

Aprovação de orçamento → sempre usar quote_notification_service (nunca chamar WhatsApp direto).
Pagamentos, envios e status → usar chaves de idempotência existentes.
Sanitizar todo input externo (telefone, mensagem, WhatsApp).
Usar exigir_permissao + verificar_ownership em todos os endpoints protegidos.


🧱 Estrutura Principal (Respeitar Sempre)

routers/ → orquestração + validação
services/ → toda regra de negócio
repositories/ → queries SQLAlchemy
cotte-frontend/js/ → modular (nunca scripts inline grandes)

Fluxo: router → service → repository → model

📤 Formato de Resposta (OBRIGATÓRIO)
Antes de editar:

Plano curto (3-5 linhas)

Após execução:

Arquivos alterados
O que mudou
Impacto na performance/integração
Riscos
Testes recomendados (pytest ou Playwright)

Ao final de TODA tarefa concluída (implementação, melhoria ou correção), obrigatoriamente incluir **três** sugestões novas de melhorias inovadoras, além do resumo do trabalho:

[INOVAÇÃO] — três itens distintos: funcionalidades novas, automações com IA, UX ou arquitetura que o sistema ainda não tem e que agregariam valor real ao negócio (pode numerar 1–3 ou usar três linhas com [INOVAÇÃO]).

Opcional (quando fizer sentido): até duas linhas [SUGESTÃO] — melhorias de performance, segurança ou qualidade **diretamente relacionadas** ao que foi alterado (não contam nas três inovações).

Regras para as sugestões:
- As **três** inovações são obrigatórias e devem ser diferentes entre si e novas na sessão quando possível
- Sempre concretas e aplicáveis à stack atual (FastAPI + Vanilla JS)
- Não repetir as mesmas ideias já dadas na mesma sessão, salvo refinamento explícito do usuário
- Marcar com o prefixo [INOVAÇÃO] (e [SUGESTÃO] só no bloco opcional)

Em caso de dúvida: separar fato | hipótese | incerteza.

🛠️ Scripts Importantes

scripts/auto_tagging_base.py --apply
scripts/migrar_urls_r2.py (quando necessário)

Este arquivo é lei. Qualquer sugestão deve respeitar 100% estas regras.
Última atualização: 06/04/2026