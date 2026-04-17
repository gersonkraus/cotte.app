---
title: Deploy Railway
tags:
  - deploy
prioridade: alta
status: documentado
---
---
title: COTTE — Deploy no Railway
tags:
  - deploy
  - railway
  - infraestrutura
prioridade: alta
status: documentado
---

# COTTE — Deploy no Railway

Guia passo a passo para colocar o COTTE na nuvem usando [Railway](https://railway.app).

---

## Pré-requisitos

- Conta no [Railway](https://railway.app) (login com GitHub)
- Projeto do COTTE em um **repositório Git** (GitHub, GitLab ou Bitbucket)

Se o projeto ainda não estiver no Git:

```bash
cd "c:\Users\Gerson\Desktop\Projeto iZi"
git init
git add .
git commit -m "Projeto COTTE inicial"
# Crie um repositório no GitHub e faça:
# git remote add origin https://github.com/SEU_USUARIO/cotte.git
# git push -u origin main
```

---

## 1. Criar o projeto no Railway

1. Acesse [railway.app](https://railway.app) e faça login (GitHub).
2. Clique em **"New Project"**.
3. Escolha **"Deploy from GitHub repo"** e autorize o Railway a acessar seu repositório.
4. Selecione o repositório do COTTE (ex.: `Projeto COTTE` ou o nome que você deu).
5. Railway vai detectar o projeto. **Importante:** vamos configurar o diretório raiz no próximo passo.

---

## 2. Configurar o diretório raiz (Root Directory) — obrigatório

O código do backend está na pasta **`sistema`**. Se isso não for configurado, o Railway analisa a raiz do repositório (onde só há `sistema/`, `README.md`, etc.) e dá erro tipo: *"Script start.sh not found"* ou *"Railpack could not determine how to build"*.

**Como configurar:**

1. No projeto Railway, clique no **serviço** (o retângulo do deploy, não o do banco).
2. Abra **Settings** (ícone de engrenagem ou "Config").
3. Procure **"Root Directory"** ou **"Source"** / **"Build Path"**.
4. Preencha exatamente: **`sistema`** (sem barra no início).
5. Clique em **Save** / **Deploy** ou salve as alterações.

O Railway passa a usar a pasta `sistema/` como raiz (onde estão `main.py`, `requirements.txt`, `Procfile`, `railway.toml`).

---

## 3. Adicionar o banco PostgreSQL

O COTTE usa PostgreSQL. É preciso **criar um serviço de banco** no mesmo projeto e depois preencher a variável `DATABASE_URL` no serviço da API.

### 3.1 Criar o Postgres (se ainda não existe)

1. No **dashboard do projeto** no Railway, você deve ver pelo menos um retângulo (o serviço do app).
2. Clique em **"+ New"** ou **"Add Service"** (pode estar no canto ou no meio da tela).
3. Escolha **"Database"** → **"PostgreSQL"** (ou **"Add PostgreSQL"**).
4. O Railway cria um segundo retângulo no projeto: um é o **seu app**, o outro é o **Postgres**. Aguarde o Postgres ficar "Ready" / verde.

### 3.2 Pegar a DATABASE_URL para o serviço da API

**Opção A — Referência (se o Railway mostrar):**  
No serviço da **API** → **Variables** → **"+ New Variable"** ou **"Add Variable"** → procure **"Add Reference"** ou **"Reference"** → selecione o serviço **Postgres** (ou "PostgreSQL") → escolha a variável **`DATABASE_URL`**. Pronto.

**Opção B — Copiar e colar (quando não aparecer Postgres na referência):**

1. Clique no **retângulo do Postgres** (o serviço do banco, não o do app).
2. Vá na aba **Variables** (ou **Connect** / **Data**).
3. Procure a variável **`DATABASE_URL`** ou **`DATABASE_PRIVATE_URL`** — o Railway mostra o valor (ou um botão para copiar).
4. **Copie** essa URL inteira (começa com `postgresql://` ou `postgres://`).
5. Volte ao **serviço da API** (clique no retângulo do app).
6. Abra **Variables** → **"+ New Variable"**.
7. Nome: **`DATABASE_URL`**. Valor: **cole a URL** que você copiou do Postgres.
8. Salve.

Agora o serviço da API tem a `DATABASE_URL`. Continue no passo 4 para preencher as demais variáveis.

---

## 3.1 Migrations (Alembic)

O schema do banco é aplicado com **Alembic** (não mais na subida do app).

- **Banco já existente** (produção que já rodava antes): uma vez, marque o estado como aplicado sem rodar SQL:
  ```bash
  cd sistema && python -m alembic stamp head
  ```
  (Conecte ao Railway via **Connect** / terminal ou use um job de release; veja 6.1.)

- **Banco novo** ou após criar novas revisões: aplique as migrations:
  ```bash
  cd sistema && python -m alembic upgrade head
  ```

No **deploy contínuo**, configure um **release command** no Railway (se disponível) para rodar `alembic upgrade head` antes de iniciar o app. Assim cada deploy aplica apenas as revisões novas. Se não houver release command, rode `alembic upgrade head` manualmente após cada deploy que incluir mudanças em `alembic/versions/`.

Detalhes: `sistema/alembic/README`.

---

## 4. Variáveis de ambiente

No serviço da **API** (o que faz deploy do código), abra **Variables** e configure **todas** as variáveis abaixo. Se alguma obrigatória faltar, o app dá **Crashed** com `ValidationError: Field required`.

### Como preencher no painel do Railway

1. Clique no **serviço da API** (não no do Postgres).
2. Abra a aba **Variables** (ou **Config** → Variables).
3. **DATABASE_URL:**  
   - Se você criou o Postgres no mesmo projeto: clique em **"+ New Variable"** ou **"Add Variable"** → **"Add Reference"** (ou "Reference Variable") → escolha o serviço **Postgres** → selecione **`DATABASE_URL`**. Assim a URL do banco é injetada automaticamente.  
   - Se preferir colar na mão: copie a `DATABASE_URL` que aparece nas variáveis do serviço Postgres e crie uma variável com o mesmo nome no serviço da API.
4. **Demais variáveis:** clique em **"+ New Variable"** e adicione **nome** e **valor** para cada linha da tabela abaixo. Use os valores do seu `.env` local (menos a DATABASE_URL, que vem do Postgres).

| Variável | Valor | Obrigatório |
|----------|--------|-------------|
| `DATABASE_URL` | Referência ao Postgres (veja acima) | Sim |
| `SECRET_KEY` | Chave longa e aleatória (ex.: [randomkeygen.com](https://randomkeygen.com)) | Sim |
| `ALGORITHM` | `HS256` | Sim |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Sim |
| `OPENROUTER_API_KEY` ou `AI_API_KEY` | Chave do provedor de IA usado pelo LiteLLM (ex.: OpenRouter); ver `sistema/.env.example` para `AI_MODEL`, `AI_PROVIDER` | Sim (ou a combinação de chaves exigida pela rota escolhida) |
| `AI_MODEL` | Slug do modelo principal (ex.: `openai/gpt-4o-mini`) | Recomendado (há default em `config.py`) |
| `AI_PROVIDER` | Ex.: `openrouter` | Opcional (há default) |
| `WHATSAPP_PROVIDER` | `zapi` ou `evolution` | Sim |
| `ZAPI_INSTANCE_ID` | Instance ID da Z-API (quando provider=zapi) | Se Z-API |
| `ZAPI_TOKEN` | Token da Z-API | Se Z-API |
| `ZAPI_CLIENT_TOKEN` | Client token (se usar) | Não |
| `ZAPI_BASE_URL` | `https://api.z-api.io/instances` | Se Z-API |
| `EVOLUTION_API_URL` | URL da Evolution API (ex.: `https://sua-evolution.com`) | Se evolution |
| `EVOLUTION_API_KEY` | Chave da Evolution API | Se evolution |
| `EVOLUTION_INSTANCE` | Nome da instância global (fallback) | Se evolution |
| `APP_URL` | URL do app no Railway (ex.: `https://seu-app.up.railway.app`) | Sim |
| `ENVIRONMENT` | `production` | Recomendado |
| `REDIS_URL` | URL do Redis (opcional; ver seção 4.1) | Não |

**APP_URL:** depois do primeiro deploy, o Railway gera um domínio.

### 4.1 Redis (opcional) — rate limit em produção

O sistema usa **rate limit** para recuperação de senha e para aceitar/recusar no link público. Sem Redis, isso funciona em **memória local** (cada instância do app tem seu próprio limite). Com **Redis**, os limites são compartilhados entre todas as instâncias e reinícios.

**Como ativar:**

1. No projeto Railway, clique em **"+ New"** → **Database** → **Redis** (ou **Add Redis**).
2. Aguarde o Redis ficar "Ready". Clique no serviço Redis → aba **Variables** (ou **Connect**).
3. Copie a variável **`REDIS_URL`** (ou **`REDIS_PRIVATE_URL`**).
4. No **serviço da API** → **Variables** → **"+ New Variable"** → **"Add Reference"** (se existir) → escolha o serviço **Redis** → selecione **`REDIS_URL`**.  
   Ou crie manualmente: nome **`REDIS_URL`**, valor = a URL que o Redis mostrou (formato `redis://default:senha@host:porta`).
5. Faça um novo deploy. O app detecta `REDIS_URL` e usa Redis para rate limit; se o Redis cair, volta automaticamente para memória local.

**Sem REDIS_URL:** o app continua funcionando; o rate limit fica só em memória (válido para uma única instância).

---

## 5. Comando de start (Procfile)

O arquivo **`sistema/Procfile`** já está configurado:

```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

O Railway usa esse comando automaticamente. Se no painel existir um campo **"Start Command"**, você pode deixar em branco para usar o Procfile, ou preencher:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

## 6. Deploy

1. Faça **commit** e **push** do código (incluindo o `Procfile` na pasta `sistema`).
2. Se o banco já existia e é a primeira vez com Alembic: rode **uma vez** `alembic stamp head` (conexão ao Postgres do Railway). Depois, a cada deploy com novas migrations, rode `alembic upgrade head` (por release command ou manualmente).
3. O Railway faz o deploy automático. Acompanhe em **Deployments**.
3. Quando terminar, abra a **URL pública** do serviço (ex.: **"Generate Domain"** em Settings se ainda não tiver).
4. Teste:
   - `https://SEU-DOMINIO.up.railway.app/` → resposta da API
   - `https://SEU-DOMINIO.up.railway.app/docs` → Swagger
   - `https://SEU-DOMINIO.up.railway.app/app` → frontend (dashboard)

---

## 7. PDFs e logos (arquivos persistentes)

No Railway, o disco é **efêmero**: arquivos em `static/pdfs` e `static/logos` são apagados quando o container reinicia.

**Opção A — Railway Volume (recomendado para começar)**

1. No serviço da API, vá em **Settings**.
2. Em **Volumes**, clique em **"Add Volume"**.
3. Monte o volume no caminho: **`/app/static`** (ou o caminho absoluto onde o app roda; no Railway costuma ser `/app` como working dir, então **`static`** pode ser suficiente — confira na doc do Railway).
4. Reinicie o deploy. Os PDFs e logos passam a persistir nesse disco.

**Opção B — Armazenamento externo (S3, R2, etc.)**

Para maior escalabilidade, você pode alterar o código para salvar PDFs e logos em um bucket S3 (ou Cloudflare R2) e servir por URL. Isso exige mudanças em `pdf_service.py` e nos endpoints de upload de logo.

---

## 8. Webhook do WhatsApp

O provider (Z-API ou Evolution) precisa chamar sua API quando chega mensagem.

- **URL do webhook:** `https://SEU-DOMINIO.up.railway.app/whatsapp/webhook`
- **Z-API:** configure essa URL no painel da Z-API na definição do webhook da instância.
- **Evolution API (multi-tenant):** use `https://SEU-DOMINIO.up.railway.app/whatsapp/webhook?instance=NOME_DA_INSTANCIA` para cada instância vinculada a uma empresa; o parâmetro `instance` identifica a empresa.

---

## 9. Resumo rápido

| Passo | Ação |
|-------|------|
| 1 | Novo projeto → Deploy from GitHub repo → selecionar repositório |
| 2 | Settings do serviço → Root Directory = `sistema` |
| 3 | New → Database → PostgreSQL → ligar DATABASE_URL ao serviço da API |
| 4 | Variables: preencher SECRET_KEY, APP_URL, chaves de IA (LiteLLM/OpenRouter), Z-API, etc. |
| 5 | Procfile já existe em `sistema/Procfile` |
| 6 | Push no Git → deploy automático → gerar domínio |
| 7 | (Opcional) Volume em `static` para PDFs/logos |
| 8 | Configurar webhook Z-API com a URL do Railway |
| 9 | Migrations: `alembic stamp head` (banco já existente) ou `alembic upgrade head` (banco novo); depois a cada deploy com novas revisões |

---

## Problemas comuns

- **"Crashed" após o deploy**  
  1. Veja o **erro real**: no Railway → seu serviço → **Deployments** → clique no último deploy → abra **View Logs**. O traceback mostra o que quebrou.  
  2. Confira as **variáveis**: no serviço → **Variables**. Obrigatórias: `DATABASE_URL`, `SECRET_KEY`, variáveis de IA (`OPENROUTER_API_KEY` / `AI_API_KEY` e modelo conforme `.env.example`), `WHATSAPP_PROVIDER`. Se usar Z-API: `ZAPI_INSTANCE_ID`, `ZAPI_TOKEN`, `ZAPI_BASE_URL`. Se usar Evolution: `EVOLUTION_API_URL`, `EVOLUTION_API_KEY` (e opcionalmente `EVOLUTION_INSTANCE`).  
  3. **DATABASE_URL**: use referência ao Postgres do projeto quando disponível (ex.: `${{Postgres.DATABASE_URL}}`).

- **"Script start.sh not found" ou "Railpack could not determine how to build"**  
  O Railway está buildando na **raiz do repositório** em vez da pasta do backend. No **serviço** → **Settings** → **Root Directory**, defina **`sistema`**, salve e faça um novo deploy.

- **502 Bad Gateway:** o app pode estar demorando para subir. Veja os **logs** no Railway (aba "Deployments" → último deploy → View Logs). Confirme se `DATABASE_URL` está correta.
- **Tabelas não existem:** o `main.py` já chama `Base.metadata.create_all(bind=engine)`, então as tabelas são criadas na primeira requisição. Se usar Alembic, rode as migrações em um job de release.
- **.env no Git:** não faça commit do arquivo `.env`. Use apenas as variáveis do painel do Railway. O `.env` é para desenvolvimento local.

Se quiser, na próxima etapa podemos ajustar o **Volume** exato para a sua versão do Railway ou preparar o uso de **S3/R2** para os arquivos.
