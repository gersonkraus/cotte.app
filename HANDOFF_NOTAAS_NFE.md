# Handoff: Correção e estabilização da emissão fiscal via Notaas (NF-e e NFS-e)

**Data:** 2026-05-12  
**Status:** em andamento — código corrigido e publicado, validação end-to-end pendente

---

## 1. Objetivo

Corrigir a integração de emissão de notas fiscais (NF-e, NFC-e e NFS-e) do sistema COTTE com a API Notaas, tornando o processo funcional para operadores sem conhecimento fiscal. As correções se concentram em alinhar o payload enviado ao formato REST JSON esperado pela Notaas, que é completamente diferente das tags XML do SEFAZ, e em adicionar mecanismos de diagnóstico de erro. O objetivo secundário é preparar o catálogo de produtos/serviços com os campos fiscais necessários (NCM, CFOP, CSOSN) para que a emissão não dependa de entrada manual.

---

## 2. Contexto essencial

- **Projeto:** `/home/gk/Projeto-izi`
- **Backend:** FastAPI em `sistema/app/`
- **Frontend:** HTML/CSS/JS vanilla em `sistema/cotte-frontend/`
- **Integração fiscal:** `sistema/app/services/nfe_service.py`
- **API Notaas:** base `https://platform.notaas.com.br/api/v1`, autenticação por header `x-api-key` por empresa (multi-tenant)
- **Documentação da API:** `docs/API-NOTAAS.txt` (arquivo local, use como referência principal)
- **Deploy:** automático por hook `post-commit` ao fazer push — nunca fazer deploy manual
- **Migrations:** Alembic em `sistema/alembic/versions/`, convenção de nome `zNNN_descricao.py`

**Decisões já tomadas (não reverter sem justificativa explícita):**
1. Para CPF/CNPJ do cliente, usar **presença real do documento** (não `tipo_pessoa`), pois há clientes PJ com apenas CPF preenchido e vice-versa.
2. Para NFS-e, campos do tomador são **lowercase** (`cnpj`, `cpf`, `nome`, `endereco`) — formato Notaas, não SEFAZ.
3. Para NF-e, payload segue **formato REST Notaas** (`dest.nome`, `items[].descricao`, `pagamentos[]`) — não usa tags XML SEFAZ.
4. `emit` (emitente) **não vai no payload** da Notaas — fica configurado na conta Notaas vinculada à API key.
5. Botão "Analisar e Corrigir" usa **mapeamento de regras** (não IA) porque os erros da Notaas já vêm estruturados e com campos identificados.
6. Não alterar `.env` sem pedido explícito do usuário.

---

## 3. O que já foi feito

### Sessões anteriores (acumulado)

1. **Identificado** que a emissão fiscal falhava por incompatibilidade de payload com a API Notaas.
2. **Corrigido** `_montar_payload_nfse`: lógica de documento passou a usar presença real de CNPJ/CPF em vez de `tipo_pessoa`.
3. **Adicionada** validação explícita: cliente sem CPF e sem CNPJ levanta `ValueError` antes de chamar a API.
4. **Implementado** `POST /notas-fiscais/preparar` — endpoint de pré-validação que verifica dados fiscais antes de emitir (retorna `bloqueios`, `avisos`, `pronto`).
5. **Implementado** modal de 2 etapas no frontend (`nfe.js`): "Verificar" primeiro, "Emitir" depois.
6. **Adicionados** campos fiscais ao catálogo de serviços: `ncm`, `cfop`, `csosn`, `origem`, `unidade_fiscal`, `dados_fiscais_ok` (migration z029).
7. **Adicionado** endpoint `GET /catalogo/{id}/sugerir-fiscal` com IA para sugerir NCM/CFOP/CSOSN a partir da descrição do produto.
8. **Adicionado** endpoint `PATCH /catalogo/{id}/fiscal` para salvar dados fiscais.
9. **Implementado** `POST /notas-fiscais/{id}/analisar-erro` — endpoint que parseia o JSON de erro da Notaas e retorna sugestões legíveis por operador.
10. **Implementado** `POST /notas-fiscais/{id}/reemitir` — cria nova `NotaFiscal` a partir de uma com erro, com eager loading correto.
11. **Adicionado** botão "Analisar e Corrigir" no frontend (`notas-fiscais.js`) que chama o endpoint acima e exibe modal com sugestões + botão "Reemitir".
12. **Adicionado** botão equivalente inline no modal de emissão (`nfe.js`), exibido automaticamente após erro.

### Esta sessão (2026-05-12)

13. **Identificado** que `_montar_payload_nfe` ainda usava nomes de tags XML SEFAZ nos campos internos de `dest` e `items`, mesmo após correção anterior dos nomes externos.
14. **Corrigido** `_montar_payload_nfe` completamente:
    - `dest.xNome` → `dest.nome`; `dest.IE` → `dest.ie`
    - `dest.endereco`: todos os campos `xLgr`/`nro`/`xBairro`/`xMun`/`UF`/`CEP` → `logradouro`/`numero`/`bairro`/`cidade`/`uf`/`cep`
    - `items`: saiu da estrutura aninhada `prod.xProd / imposto.ICMS.ICMSSN400` para estrutura flat `descricao / ncm / cfop / valorTotal / csosn`
    - `pag.detPag[].tPag` → `pagamentos[].tipoPagamento` com `valor` como float (não string)
    - Removidos blocos `ide`, `emit`, `total`, `transp` (não fazem parte da API Notaas)
15. **Corrigido** `_montar_payload_nfse`: substituída lógica `tipo_pessoa == "PJ"` por presença real de CNPJ.
16. **Corrigido** `_normalizar_codigo_servico`: "01070" (5 dígitos) agora vira "010700" corretamente (padding à direita, não à esquerda).
17. **Adicionado** `codigo_municipio_ibge` (nullable, String(7)) ao modelo `Cliente` — campo obrigatório pela Notaas NF-e para `dest.endereco.codigoMunicipio`.
18. **Criada** migration `z031_add_codigo_municipio_ibge_clientes.py`.
19. **Testes** `test_nfe_service.py` (6 testes) e `test_nfe_router.py` (3 testes) passando.
20. **Push** feito para `origin/main`.

---

## 4. Estado atual

### O que está corrigido e publicado

- `_montar_payload_nfe`: payload NF-e agora usa formato REST Notaas correto.
- `_montar_payload_nfse`: lógica de documento consistente.
- `_normalizar_codigo_servico`: cobre formatos "X.XX", "01070", "17.06", "1.07".
- Botão "Analisar e Corrigir" funcionando em `notas-fiscais.html` e no modal de emissão.
- Endpoint `/reemitir` funcionando.
- Campos fiscais no catálogo (NCM, CFOP, CSOSN) com sugestão IA.

### Pendências críticas

**1. Migration z031 não rodou no Railway ainda.**  
A coluna `codigo_municipio_ibge` não existe no banco de produção. Sem ela, o `getattr(cliente, "codigo_municipio_ibge", None)` retorna None silenciosamente (não quebra), mas `codigoMunicipio` não vai no payload. Para NF-e isso pode causar rejeição SEFAZ (cStat 225).

**2. Migrations z029 e z030 também podem estar pendentes no Railway.**  
Se não rodaram, campos `ncm`, `cfop`, `csosn` da tabela `servicos` não existem em produção e o acesso pelo `nfe_service.py` vai gerar `AttributeError` silencioso (só retorna None por causa dos `getattr`).

**3. Validação end-to-end não foi feita.**  
As correções foram aplicadas e testadas unitariamente, mas nenhuma emissão real foi testada contra a API Notaas em homologação após as mudanças desta sessão.

### O que ainda está quebrado (conhecido, fora do escopo atual)

- **Erro SQL enum `statusorcamento`:** valor `"aprovado"` pode ser rejeitado se o banco espera outro literal.
- **Erro bind parameter `empresa_id`** em alguma query de serviços — aparece em log mas não foi investigado.
- **PATCH template retorna 405** — frontend chamando método errado ou endpoint errado.
- **Upload de anexo de template retorna 503.**

---

## 5. Próximos passos

**Imediato (antes de qualquer outra coisa):**

1. Rodar migrations no Railway:
   ```bash
   python -m alembic upgrade head
   ```
   Isso aplica z029, z030 e z031 (campos fiscais em `servicos` + `codigo_municipio_ibge` em `clientes`).

2. Testar emissão NF-e em homologação com um orçamento real:
   - Cliente com CNPJ preenchido
   - Itens com NCM e CFOP cadastrados no catálogo
   - Verificar se o payload enviado é aceito pela Notaas (sem HTTP 400/422)

3. Testar emissão NFS-e em homologação:
   - Cliente PF (só CPF)
   - Cliente PJ (só CNPJ)
   - Código de serviço no formato "X.XX" (ex: "1.07", "17.06")

**Próximas melhorias:**

4. Adicionar campo `codigo_municipio_ibge` na UI de cadastro/edição de clientes (campo opcional, exibir como "Código IBGE do município").

5. Implementar preenchimento automático de `codigo_municipio_ibge` a partir do CEP (via API ViaCEP ou similar) ao salvar cliente.

6. Investigar e corrigir os problemas pendentes separadamente: enum `statusorcamento`, bind `empresa_id`, PATCH template, upload 503.

---

## 6. Perguntas em aberto

- A Notaas aceita `dest.endereco` sem `codigoMunicipio` para NF-e? Ou rejeita com 400 mesmo tendo `cidade` e `uf`?
- O campo `codigoMunicipio` é resolvido automaticamente pela Notaas a partir de `cidade`+`uf` para NF-e (como faz para NFS-e) ou é estritamente obrigatório?
- As migrations z029/z030 já foram aplicadas no Railway em algum momento, ou ainda estão pendentes?
- O ambiente Notaas da empresa de teste está em homologação ou produção? (`notaas_ambiente` no banco)
- O erro SQL de enum `statusorcamento` — é `"aprovado"` vs `"Aprovado"` (case), ou o enum no banco está com valores diferentes do código Python?
- O endpoint de template — é `PATCH /catalogo/templates/{id}` ou outro path? O frontend está chamando qual método?

---

## 7. Artefatos relevantes

### Arquivos principais

| Arquivo | Papel |
|---|---|
| `sistema/app/services/nfe_service.py` | Serviço fiscal: `_montar_payload_nfe`, `_montar_payload_nfse`, `_normalizar_codigo_servico`, `emitir_nota`, `emitir_nota_background`, `cancelar_nota` |
| `sistema/app/routers/notas_fiscais.py` | Router: `/emitir`, `/preparar`, `/analisar-erro`, `/reemitir`, `/cancelar` |
| `sistema/app/routers/catalogo.py` | Router: `/sugerir-fiscal`, `/fiscal` (dados fiscais do catálogo) |
| `sistema/app/services/fiscal_ai_service.py` | IA para sugestão de NCM/CFOP/CSOSN |
| `sistema/app/models/models.py` | Modelos: `Empresa`, `Cliente` (novo campo `codigo_municipio_ibge`), `Servico` (campos fiscais), `NotaFiscal` |
| `sistema/cotte-frontend/js/nfe.js` | Modal de emissão: verificar → emitir, botão analisar erro inline |
| `sistema/cotte-frontend/js/notas-fiscais.js` | Página Notas Fiscais: listagem, cancelar, analisar erro, reemitir |
| `sistema/alembic/versions/z029_add_fiscal_fields_servicos.py` | Migration: campos fiscais em `servicos` |
| `sistema/alembic/versions/z030_merge_fiscal_and_head_*.py` | Migration: merge de branches Alembic |
| `sistema/alembic/versions/z031_add_codigo_municipio_ibge_clientes.py` | Migration: `codigo_municipio_ibge` em `clientes` |
| `sistema/tests/test_nfe_service.py` | Testes unitários do serviço fiscal |
| `sistema/tests/test_nfe_router.py` | Testes do router NF-e |
| `docs/API-NOTAAS.txt` | Documentação completa da API Notaas (NFS-e e NF-e) |

### Payload NF-e correto (formato Notaas)

```json
{
  "naturezaOperacao": "Venda de Mercadorias",
  "modelo": 55,
  "dest": {
    "cnpj": "12345678000195",
    "nome": "Empresa Compradora Ltda",
    "ie": "",
    "email": "financeiro@empresa.com",
    "endereco": {
      "logradouro": "Rua das Flores",
      "numero": "100",
      "bairro": "Centro",
      "cidade": "Curitiba",
      "uf": "PR",
      "cep": "80010100",
      "codigoMunicipio": 4106902
    }
  },
  "items": [
    {
      "descricao": "Camiseta algodão P",
      "ncm": "61091000",
      "cfop": "5102",
      "valorTotal": 99.80,
      "quantidade": 2,
      "valorUnitario": 49.90,
      "unidade": "UN",
      "csosn": "102"
    }
  ],
  "pagamentos": [
    { "tipoPagamento": "99", "valor": 99.80 }
  ]
}
```

### Payload NFS-e correto (formato Notaas)

```json
{
  "tomador": {
    "cnpj": "12345678000195",
    "nome": "Empresa Tomadora Ltda",
    "email": "financeiro@tomadora.com.br",
    "endereco": {
      "logradouro": "Rua das Flores",
      "numero": "100",
      "bairro": "Centro",
      "cidade": "Londrina",
      "uf": "PR",
      "cep": "86010010"
    }
  },
  "servico": {
    "descricao": "Desenvolvimento de software sob demanda",
    "codigo": "010302"
  },
  "valores": {
    "total": 1000.00,
    "aliquotaIss": 2.0,
    "issRetido": false
  },
  "competencia": "2026-05",
  "referencia": "ORC-2026-001"
}
```

### Commits desta sessão

```
ae982b4  fix(nfe): corrigir campos do payload NF-e para formato REST Notaas
f0e23de  fix(nfe): corrigir payload NF-e e adicionar botão Analisar e Corrigir
```

### Comandos úteis

```bash
# Rodar migrations (Railway)
python -m alembic upgrade head

# Testes fiscais
cd sistema && pytest tests/test_nfe_service.py -q
cd sistema && pytest tests/test_nfe_router.py -q

# Verificar estado do git
git log --oneline -5
git diff HEAD~1 -- sistema/app/services/nfe_service.py
```

---

## 8. Instruções para a próxima sessão

- **Responder sempre em português do Brasil**, direto e objetivo.
- **Começar verificando** se as migrations z029/z030/z031 foram aplicadas no Railway antes de tentar qualquer diagnóstico de emissão.
- **Não assumir** que o problema é só código — pode ser dado fiscal (NCM inválido, CFOP errado, código de serviço com formato errado) ou configuração Notaas (certificado, API key, ambiente).
- **Não alterar `.env`** nem credenciais Notaas sem pedido explícito.
- **Não fazer deploy manual** — push aciona o hook automaticamente.
- **Não reverter** as decisões de formato de payload (presença real de CNPJ, lowercase, estrutura flat) sem evidência contrária da documentação Notaas.
- **Ao mexer em qualquer arquivo de roteamento IA** (`ai_intention_classifier.py` ou similar), rodar `cd sistema && pytest tests/test_ai_tool_routing.py` obrigatoriamente.
- **Ao criar commit**, incluir apenas arquivos do escopo fiscal/testes. O repositório tem muitos arquivos não rastreados (graphify-out, todo-pro, etc.) — não adicionar com `git add .`.
- Se aparecer **erro 400/422 da Notaas**, primeiro ler o campo `campos` do JSON de erro para identificar exatamente qual campo está errado, depois comparar com `docs/API-NOTAAS.txt`.
- Se aparecer **erro SEFAZ (cStat)**, consultar a seção "Rejeições SEFAZ" do `docs/API-NOTAAS.txt`.
- **Próximo passo concreto:** rodar `python -m alembic upgrade head` no Railway e testar uma emissão NF-e real em homologação.
