---
title: Tech Stack
tags:
  - tecnico
prioridade: alta
status: documentado
---
---
title: Tech Stack
tags:
  - tecnico
prioridade: alta
status: documentado
---
# Pilha Tecnológica (Tech Stack): COTTE (Projeto iZi)

## Backend
- **Linguagem Principal:** Python 3.11+
- **Framework Web:** FastAPI (Alta performance, tipagem forte e suporte assíncrono).
- **Manipulação de Dados:** SQLAlchemy (Async) para o banco de dados e Pydantic v2 para validação de esquemas e entradas.
- **Gerenciamento de Migrações:** Alembic.
- **Testes:** Configuração com `pytest` para a lógica de negócio e `playwright` para E2E.

## Banco de Dados
- **Relacional:** PostgreSQL, para garantir durabilidade e confiabilidade nas transações comerciais e financeiras.

## Frontend
- **Linguagens:** Vanilla JavaScript, HTML5 Semântico e CSS3 Moderno (com Grid e Flexbox).
- **Sem Dependências Pesadas:** A interface é mantida propositalmente simples, sem o uso de frameworks SPA massivos (como React/Angular), garantindo velocidade de entrega.

## Integrações e Ferramentas Externas
- **Inteligência Artificial:** Integração via Anthropic SDK (Claude) para processamento de interações, interpretação de áudios/textos e geração inteligente de conteúdo.
- **Comunicação via WhatsApp:** Integração nativa com APIs de envio e confirmação.
- **Geração de Documentos:** WeasyPrint para criação de orçamentos estilizados em formato PDF (com FPDF2 como fallback para layouts clássicos).
- **E-mail:** SMTP Transacional (Brevo) para notificar ações assíncronas do sistema e relatórios gerenciais.