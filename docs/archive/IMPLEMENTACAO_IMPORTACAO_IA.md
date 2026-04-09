---
title: Implementacao Importacao Ia
tags:
  - implementacao
prioridade: media
status: documentado
---
---
title: Implementacao Importacao Ia
tags:
  - implementacao
prioridade: alta
status: documentado
---
# Implementação de Importação de Leads com IA

## Visão Geral

Esta implementação adiciona a capacidade de importar leads a partir de textos não estruturados usando inteligência artificial, integrando-se ao fluxo existente de importação no módulo comercial do COTTE.

## Arquivos Modificados

### 1. Backend - `sistema/app/routers/comercial.py`

**Endpoint criado:**
- `POST /comercial/leads/analisar-importacao`
- **Descrição:** Analisa texto não estruturado e extrai informações de leads usando IA
- **Parâmetros:** `texto` (string) - Texto contendo informações de contatos
- **Retorno:** Lista de leads extraídos com validação de duplicatas

**Funcionalidades:**
- Integração com COTTE AI Hub para análise de texto
- Extração automática de nome, empresa, WhatsApp, email e cidade
- Geração de nomes de empresa a partir do nome da pessoa
- Verificação de duplicatas por WhatsApp e email
- Validação de formatos de contato

### 2. Frontend - `sistema/cotte-frontend/comercial.html`

**Alterações realizadas:**
- Adicionado método "IA" na seleção de métodos de importação
- Atualizada lógica de seleção para incluir área de texto para IA
- Integrada chamada à API de análise de IA na função `previewImport()`
- Removida referência ao arquivo removido `comercial-import.html`

**Novos elementos:**
- Card de método "IA" com ícone de robô
- Lógica para exibir área de texto quando método IA é selecionado
- Tratamento de erro para falhas na análise de IA

### 3. Arquivos Removidos
- `sistema/cotte-frontend/comercial-import.html` - Código incorporado ao `comercial.html`
- Referências em `comercial-templates.html` e `comercial-campanhas.html`

## Fluxo de Importação com IA

1. **Seleção do Método:** Usuário seleciona "IA" como método de importação
2. **Entrada de Dados:** Usuário cola texto não estruturado na área de texto
3. **Análise:** Sistema envia texto para análise de IA via API
4. **Extração:** IA extrai informações de contato do texto
5. **Validação:** Sistema valida e verifica duplicatas
6. **Pré-visualização:** Usuário visualiza leads extraídos antes da importação
7. **Importação:** Usuário confirma e os leads são criados no sistema

## Exemplos de Texto Suportados

### Formato 1 - Descrições livres
```
João Silva, gerente de projetos na TechCorp, telefone 5548999999999, email joao.silva@techcorp.com, cidade São Paulo.
```

### Formato 2 - Listas simples
```
Maria Santos - 5548988888888 - maria.santos@inovasoft.com.br - Rio de Janeiro
Carlos Oliveira - 5548977777777 - carlos.oliveira@datatech.com - Florianópolis
```

### Formato 3 - Textos mistos
```
Contatos de potenciais clientes:
- Ana Costa (SoftWorks): 5548966666666, ana.costa@softworks.com, Porto Alegre
- Pedro Lima (WebSolutions): 5548955555555, pedro.lima@websolutions.com, Belo Horizonte
```

## Benefícios da Implementação

1. **Flexibilidade:** Aceita diversos formatos de texto não estruturado
2. **Inteligência:** Usa IA para extrair informações automaticamente
3. **Validação:** Verifica duplicatas e valida formatos de contato
4. **Integração:** Mantém o fluxo existente de importação
5. **Usabilidade:** Interface consistente com os demais métodos de importação

## Testes

### Arquivo de Teste
- `test_importacao_ia.html` - Página de teste para validar a funcionalidade

### Cenários de Teste
1. Texto com múltiplos contatos em formatos diferentes
2. Texto com informações incompletas
3. Texto com duplicatas
4. Texto sem informações válidas
5. Erros de conexão com a API de IA

## Requisitos Técnicos

### Backend
- FastAPI com rotas assíncronas
- Integração com COTTE AI Hub
- Validação de dados e tratamento de erros
- Conexão com banco de dados para verificação de duplicatas

### Frontend
- JavaScript vanilla (sem frameworks)
- Fetch API para chamadas HTTP
- Manipulação do DOM para atualização de interface
- Tratamento de erros e mensagens de feedback

## Considerações de Segurança

1. **Validação de Entrada:** O texto é validado no backend antes de ser enviado para IA
2. **Tratamento de Erros:** Erros de IA são capturados e retornados de forma amigável
3. **Duplicatas:** Verificação de duplicatas evita criação de leads repetidos
4. **Sanitização:** Dados são sanitizados antes de serem armazenados no banco

## Próximos Passos

1. **Testes de Integração:** Testar o fluxo completo em ambiente de desenvolvimento
2. **Documentação:** Atualizar documentação do sistema com a nova funcionalidade
3. **Treinamento:** Treinar equipe comercial sobre o novo método de importação
4. **Feedback:** Coletar feedback dos usuários para melhorias futuras

## Histórico de Alterações

- **Data:** 18/03/2026
- **Versão:** 1.0
- **Descrição:** Implementação inicial da importação de leads com IA
- **Arquivos:** 4 arquivos modificados, 1 arquivo removido, 2 arquivos criados