---
title: Ultimas Atualiza Testar
tags:
  - tecnico
prioridade: media
status: documentado
---
---
title: Ultimas Atualiza Testar
tags:
  - tecnico
prioridade: media
status: documentado
---
# Últimas Atualizações para Testar

Lista baseada nos últimos 20 commits do projeto.

---

## 1. Fluxo de Aceite com OTP (feat)
- **Commit:** `565108e`
- **O que testar:**
  - Fluxo completo de aceite de orçamento público com OTP
  - Envio de e-mail com código OTP
  - Validação do código OTP na página pública
  - Configurações flexíveis de OTP (regras por empresa)
  - Regras de aceite configuráveis

## 2. Página Pública de Orçamento - Melhorias de UX
- **Commits:** `3a776c4`, `4b3250e`, `af1678b`
- **O que testar:**
  - Botão de WhatsApp funcional na página pública
  - Timeline de status do orçamento
  - Selos de segurança (badges)
  - Funcionamento correto da API no link público
  - Redirecionamentos e parâmetros de URL

## 3. Funcionalidade de Desaprovar Orçamento
- **Commits:** `4ae1b29`, `8692eb7`
- **O que testar:**
  - Botão de desaprovar orçamento acessível na interface
  - Ação de desaprovar orçamento funcional
  - Notificação ao desaprovar (quote_notification_service)
  - Total duplicado ocultado corretamente

## 4. Unificação do Fluxo de Orçamento no Comercial
- **Commit:** `735b3ac`
- **O que testar:**
  - Fluxo unificado de orçamento na tela comercial
  - Campos duplicados removidos
  - Integração com IA (prompt v2)
  - Geração de documentos via comercial

## 5. Cadastro de Clientes (PJ) - Melhorias
- **Commit:** `bfc7878`
- **O que testar:**
  - Formulário de cadastro de Pessoa Jurídica
  - Responsividade do formulário em diferentes telas
  - Campos específicos para PJ (CNPJ, IE, etc.)

## 6. Catálogo - Cálculo de Preço e Margem
- **Commits:** `896de9a`, `2d6b7ef`
- **O que testar:**
  - Margem **NÃO** deve aparecer nos cards do catálogo (visão cliente)
  - Explicação do cálculo de preço visível e compreensível
  - Catálogo público com preços corretos

## 7. Modal de Orçamento - Botões Duplicados
- **Commit:** `555c68b`
- **O que testar:**
  - Botões no rodapé do modal de orçamento **sem duplicação**
  - Botões funcionando corretamente (editar, salvar, excluir)

## 8. Correção de Erros no Dashboard
- **Commit:** `296983e`
- **O que testar:**
  - Dashboard carregando sem erros de console (redeclaração de `params`)

## 9. Página de Configurações - Refatoração
- **Commit:** `2f479a5`
- **O que testar:**
  - Página de configurações carregando corretamente
  - JavaScript extraído (não mais inline)
  - Validação de campos funcionando
  - Correção de bugs de comportamento
  - Testes unitários: `pytest sistema/tests/test_empresa_schema.py`

## 10. Correções de Deploy e Rotas da API
- **Commits:** `dff5702`, `d73e08e`, `4b3250e`
- **O que testar:**
  - Deploy sem erros (correção de imports: `Literal`)
  - Rotas da API respondendo corretamente
  - Funções de IA funcionando após correções
  - Redundâncias removidas nas rotas

## 11. Coluna `conteudo_html` em Orçamento Documentos
- **Commit:** `7d0861f`
- **O que testar:**
  - Geração de PDF/Documento de orçamento sem erros
  - Migração aplicada corretamente (verificar tabela `orcamento_documentos`)

## 12. Template de Segmento - Configurações Avançadas
- **Commit:** `d73e08e`
- **O que testar:**
  - Página de administração de configurações (`admin-config.html`)
  - Configurações de template por segmento
  - Catálogo com novas funcionalidades de segmento

## 13. Documentação Técnica Atualizada
- **Commits:** `565108e`, `2f479a5`, `9b8aa1e`, `a2dba60`, `3d9e46c`
- **Arquivos criados/atualizados:**
  - `docs/mapa-tec-banco.md`
  - `docs/mapa-tec-permissao.md`
  - `docs/mapa-tec-configuracoes.md`
  - `docs/mapa-tecnico-cadastro-cliente.md`
  - `docs/mapa-tecnico-catalogo.md`
  - `sistema/docs/fluxo-otp-aceite-publico.md`
  - `sistema/docs/mapa-tec-assistente.md`
  - `sistema/docs/mapa-tecico-financeiro.md`
  - `sistema/docs/prompt-cotte-ai-service-v2.md`

---

## Resumo Rápido de Testes

| # | Funcionalidade | Prioridade |
|---|---------------|------------|
| 1 | Fluxo OTP de aceite | Alta |
| 2 | Página pública (WhatsApp, timeline, badges) | Alta |
| 3 | Desaprovar orçamento | Alta |
| 4 | Fluxo comercial unificado | Alta |
| 5 | Cadastro PJ responsivo | Média |
| 6 | Catálogo (sem margem, explicação preço) | Média |
| 7 | Modal orçamento (botões) | Média |
| 8 | Dashboard sem erros | Baixa |
| 9 | Configurações refatoradas | Média |
| 10 | Deploy e rotas API | Alta |
| 11 | Documentos HTML orçamento | Média |
| 12 | Admin configurações segmento | Média |
| 13 | Documentação técnica | Informativo |
