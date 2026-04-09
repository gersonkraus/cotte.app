---
title: Padroes Interface
tags:
  - documentacao
prioridade: alta
status: documentado
---
---
title: Padrões de Interface — COTTE
tags:
  - frontend
  - design
  - padrao
prioridade: media
status: documentado
---

# Padrões de Interface — COTTE

## Objetivo

Manter consistência visual em todo o sistema.

## Estilo de design

O COTTE deve seguir padrões de SaaS modernos inspirados em:
- Stripe
- Linear
- Vercel
- Supabase

## Princípios

- interface limpa
- boa hierarquia visual
- foco nas ações principais
- pouco ruído visual

## Layout

Usar estrutura baseada em:

- sidebar lateral
- área principal com cards
- tabelas organizadas
- espaçamento generoso

## Componentes principais

Cards
Utilizados para agrupar informações.

Tabelas
Usadas para listagem de dados como orçamentos e clientes.

Botões
Ação principal deve sempre ter destaque.

Formulários
Devem ser simples e organizados.

## Experiência do usuário

Sempre priorizar:
- clareza
- rapidez
- simplicidade

## Formulários — Padrões de UX

### Campos com instrução contextual (`field-help`)

Todo campo que exige um formato específico ou tem impacto importante deve ter um texto de ajuda abaixo usando a classe `field-help`.

Exemplos aplicados:

- **WhatsApp**: `"Digite apenas os números com DDD. Você receberá login e senha por este número."`
- **E-mail**: `"Este e-mail será usado para acessar o sistema."`

### Máscaras de input

Campos de telefone/WhatsApp devem usar máscara automática em JS (vanilla):
- Formatar em tempo real: `(XX) XXXXX-XXXX` (celular) ou `(XX) XXXX-XXXX` (fixo)
- Bloquear caracteres não numéricos via `keydown`
- Adicionar `inputmode="numeric"` para abrir teclado numérico no mobile
- Enviar à API apenas os dígitos (`.replace(/\D/g, '')`)