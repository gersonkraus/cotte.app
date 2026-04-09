---
title: Migracao R2
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Migracao R2
tags:
  - documentacao
prioridade: media
status: documentado
---
# Migração para Cloudflare R2

Este documento descreve a migração do armazenamento de arquivos local para o Cloudflare R2.

## O que foi implementado

### 1. Dependências
- **boto3**: Adicionado ao `requirements.txt` para integração com R2 (compatível S3)

### 2. Configuração
Novas variáveis no `.env`:
```env
R2_ACCOUNT_ID=seu_account_id
R2_ACCESS_KEY_ID=seu_access_key
R2_SECRET_ACCESS_KEY=seu_secret_key
R2_BUCKET_NAME=cotte-files
R2_PUBLIC_URL=https://pub-xxx.r2.dev
```

### 3. Novo Serviço: `r2_service.py`
- Upload de arquivos para R2
- Deleção de arquivos
- Geração de URLs públicas
- Organização: `empresas/{empresa_id}/{tipo}/{uuid}.{ext}`
  - `tipo`: catalogo, logos, documentos

### 4. Arquivos Adaptados

#### `documentos_service.py`
- `salvar_upload_documento()`: Faz upload para R2 e retorna URL
- `resolver_arquivo_path()`: Retorna URL do R2 ou caminho local (fallback)

#### `catalogo.py`
- `upload_imagem_servico()`: Salva imagens no R2
- `remover_imagem_servico()`: Deleta do R2

#### `empresa.py`
- `upload_logo()`: Salva logos no R2
- `remover_logo()`: Deleta do R2

#### `documentos.py`
- `baixar_arquivo_documento()`: Redireciona para URL do R2 ou serve arquivo local

#### `publico.py`
- `baixar_documento_publico()`: Redireciona para URL do R2 ou serve arquivo local

## Como configurar o R2

### 1. Criar conta Cloudflare
1. Acesse https://dash.cloudflare.com/
2. Vá em **R2** no menu lateral
3. Crie um bucket (ex: `cotte-files`)

### 2. Gerar credenciais
1. Em **R2** → **Manage R2 API Tokens**
2. Clique em **Create API Token**
3. Permissões: **Object Read & Write**
4. Copie:
   - Access Key ID
   - Secret Access Key
   - Account ID (visível na URL ou no dashboard)

### 3. Configurar acesso público
1. No bucket, vá em **Settings**
2. Em **Public Access**, ative **Allow Access**
3. Copie a URL pública (ex: `https://pub-xxx.r2.dev`)

### 4. Configurar variáveis na Railway
No painel da Railway, adicione as variáveis:
```
R2_ACCOUNT_ID=abc123
R2_ACCESS_KEY_ID=xyz789
R2_SECRET_ACCESS_KEY=secret_key_here
R2_BUCKET_NAME=cotte-files
R2_PUBLIC_URL=https://pub-xxx.r2.dev
```

### 5. Deploy
```bash
git add .
git commit -m "feat: migrar armazenamento para Cloudflare R2"
git push origin main
```

## Compatibilidade com arquivos existentes

O sistema mantém **compatibilidade total** com arquivos já salvos localmente:

- Arquivos novos: Salvos no R2 com URL completa (`https://...`)
- Arquivos antigos: Continuam funcionando com caminho relativo
- `resolver_arquivo_path()` detecta automaticamente o tipo

## Migração de arquivos existentes (opcional)

Para migrar arquivos já salvos localmente para o R2, você pode criar um script:

```python
# script_migrar_arquivos.py
from app.services.r2_service import r2_service
from app.models.models import DocumentoEmpresa, Servico, Empresa
from app.core.database import SessionLocal
import os

db = SessionLocal()

# Migrar documentos
for doc in db.query(DocumentoEmpresa).all():
    if not doc.arquivo_path.startswith("http"):
        with open(doc.arquivo_path, "rb") as f:
            url = r2_service.upload_file(
                f, doc.empresa_id, "documentos", ".pdf", "application/pdf"
            )
        doc.arquivo_path = url
        db.commit()

# Migrar imagens de serviços
for srv in db.query(Servico).filter(Servico.imagem_url.isnot(None)).all():
    if not srv.imagem_url.startswith("http"):
        path = srv.imagem_url.lstrip("/")
        if os.path.exists(path):
            ext = os.path.splitext(path)[1]
            with open(path, "rb") as f:
                url = r2_service.upload_file(
                    f, srv.empresa_id, "catalogo", ext, "image/jpeg"
                )
            srv.imagem_url = url
            db.commit()

# Migrar logos
for emp in db.query(Empresa).filter(Empresa.logo_url.isnot(None)).all():
    if not emp.logo_url.startswith("http"):
        path = emp.logo_url.lstrip("/")
        if os.path.exists(path):
            ext = os.path.splitext(path)[1]
            with open(path, "rb") as f:
                url = r2_service.upload_file(
                    f, emp.id, "logos", ext, "image/png"
                )
            emp.logo_url = url
            db.commit()

db.close()
```

## Vantagens do R2

✅ **Persistência**: Arquivos não são perdidos em redeploys da Railway  
✅ **Performance**: CDN global da Cloudflare  
✅ **Custo**: Sem taxas de egress (tráfego de saída)  
✅ **Escalabilidade**: Armazenamento ilimitado  
✅ **Compatível S3**: Usa boto3 padrão  

## Estrutura de pastas no R2

```
cotte-files/
├── empresas/
│   ├── 1/
│   │   ├── catalogo/
│   │   │   ├── abc123.jpg
│   │   │   └── def456.png
│   │   ├── logos/
│   │   │   └── xyz789.png
│   │   └── documentos/
│   │       ├── doc1.pdf
│   │       └── doc2.pdf
│   ├── 2/
│   │   ├── catalogo/
│   │   ├── logos/
│   │   └── documentos/
│   └── ...
```

## Troubleshooting

### Erro: "Armazenamento de arquivos não configurado"
- Verifique se todas as variáveis R2 estão configuradas no `.env` ou Railway
- Reinicie o servidor após adicionar as variáveis

### Arquivos não aparecem
- Verifique se o bucket tem **Public Access** habilitado
- Confirme que a `R2_PUBLIC_URL` está correta

### Erro de permissão
- Verifique se o API Token tem permissões de **Object Read & Write**
- Confirme que o `R2_ACCOUNT_ID` está correto
