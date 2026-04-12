# CONVENTIONS.md
- Responder e explicar em português do Brasil PT-BR. 
- Identificar a Fonte: Qual ação do usuário ou chamada de API origina os dados? (Ex: aprovar_orcamento).
- Analisar a Estrutura da Resposta: Qual é a estrutura exata do JSON de resposta para essa ação específica? Onde os
   dados relevantes (ex: id, numero, cliente_nome) estão localizados? (Ex: na raiz do objeto, em data.dados, em
   data.orcamento?).
- Analisar o Consumidor: Qual função no frontend irá consumir esses dados? (Ex: renderOrcamentoAprovado).
- Verificar a Compatibilidade: A estrutura da resposta (passo 2) é diretamente compatível com o que a função
   consumidora (passo 3) espera como argumento?
- Propor a Transformação: Se não for compatível, a alteração de código proposta deve incluir explicitamente a
   lógica para transformar/mapear os dados da estrutura da API para a estrutura esperada pela função do frontend.
- Antes de editar, localizar a causa raiz.
- Depois de editar, validar com teste, build ou execução relevante.
- Em bugs, corrigir um problema por vez.

## Regras para Deploy e Commits (Aider / AI Agents)
- O processo de deploy e espelhamento é **100% automatizado** via hook `post-commit`.
- Quando o usuário pedir "commit e push" ou "faça o deploy", você deve **APENAS** rodar `git commit` e `git push` no repositório local principal (`/home/gk/Projeto-izi`).
- **NÃO** tente fazer deploy manual ou rodar scripts de deploy arbitrários.
- **NÃO** tente copiar arquivos para outras pastas do sistema (como `/home/gk/cotte.app`).
- O hook automático cuidará de tudo em background (Notion, espelhamento, checagem de `.env`, push para Railway e Graphify).

-Sempre analisar os arquivos relevantes primeiro.
-Analise a cadeia de eventos completa — da ação do usuário à resposta da API e à renderização final — para garantir que a correção seja aplicada no local exato e mais eficaz.