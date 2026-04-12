# CONVENTIONS.md

- Responder e explicar em português do Brasil.
- Fazer a menor alteração possível.
- Não quebrar frontend existente sem necessidade.
- Não refatorar partes grandes sem pedido explícito.
- Antes de editar, localizar a causa raiz.
- Depois de editar, validar com teste, build ou execução relevante.
- Em bugs, corrigir um problema por vez.

## Regras para Deploy e Commits (Aider / AI Agents)
- O processo de deploy e espelhamento é **100% automatizado** via hook `post-commit`.
- Quando o usuário pedir "commit e push" ou "faça o deploy", você deve **APENAS** rodar `git commit` e `git push` no repositório local principal (`/home/gk/Projeto-izi`).
- **NÃO** tente fazer deploy manual ou rodar scripts de deploy arbitrários.
- **NÃO** tente copiar arquivos para outras pastas do sistema (como `/home/gk/cotte.app`).
- O hook automático cuidará de tudo em background (Notion, espelhamento, checagem de `.env`, push para Railway e Graphify).