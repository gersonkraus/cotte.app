---
title: Corrigir Cors R2
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Corrigir Cors R2
tags:
  - documentacao
prioridade: media
status: documentado
---
# Corrigir erro de CORS no R2

## Problema
```
Requisição cross-origin bloqueada: A diretiva Same Origin não permite a leitura do recurso remoto em https://f3879bc7b6450b31d4abe0002ce8371d.r2.cloudflarestorage.com/...
```

## Causa
Os arquivos foram salvos com a URL de storage interno (`r2.cloudflarestorage.com`) ao invés da URL pública. Isso acontece quando `R2_PUBLIC_URL` não está configurada.

## Solução em 3 passos

### 1. Configurar URL pública no Cloudflare

1. Acesse https://dash.cloudflare.com/
2. Vá em **R2** → Selecione seu bucket
3. Vá em **Settings** → **Public Access**
4. Clique em **Allow Access**
5. Copie a URL pública que aparece (ex: `https://pub-xxxxxxxxxxxxx.r2.dev`)

### 2. Adicionar variável na Railway

No painel da Railway, adicione a variável:

```
R2_PUBLIC_URL=https://pub-xxxxxxxxxxxxx.r2.dev
```

(Use a URL que você copiou no passo 1)

A Railway vai reiniciar automaticamente.

### 3. Migrar URLs dos arquivos existentes

**Opção A: Via Railway (Recomendado)**

No painel da Railway, vá em **Deployments** → Clique nos 3 pontos → **Run Command**:

```bash
python scripts/migrar_urls_r2.py
```

**Opção B: Localmente**

```bash
cd sistema
venv/Scripts/python.exe scripts/migrar_urls_r2.py
```

O script vai:
- ✅ Atualizar URLs de documentos
- ✅ Atualizar URLs de imagens de serviços
- ✅ Atualizar URLs de logos de empresas

## Verificar se funcionou

1. Acesse a página de documentos
2. Tente visualizar um documento
3. A URL deve ser `https://pub-xxx.r2.dev/...` (não mais `r2.cloudflarestorage.com`)
4. Não deve mais aparecer erro de CORS

## Configurar CORS (se ainda necessário)

Se mesmo após migrar as URLs ainda tiver erro de CORS:

1. No bucket do R2, vá em **Settings** → **CORS Policy**
2. Adicione:

```json
[
  {
    "AllowedOrigins": ["https://cotte.app", "https://www.cotte.app"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3000
  }
]
```

Substitua pelos domínios corretos do seu sistema.

## Próximos uploads

Todos os novos uploads já vão usar a URL pública automaticamente (desde que `R2_PUBLIC_URL` esteja configurada).
