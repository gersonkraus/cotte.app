---
title: Graph Report
tags:
  - tecnico
prioridade: media
status: documentado
---
# Graph Report - docs/  (2026-04-11)

## Corpus Check
- 57 files · ~77,627 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 87 nodes · 76 edges · 23 communities detected
- Extraction: 82% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 14 edges (avg confidence: 0.74)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `System Features Overview` - 8 edges
2. `Financeiro Module` - 7 edges
3. `Orçamentos Module` - 5 edges
4. `Assistente IA Module` - 5 edges
5. `Assistente IA Technical Spec` - 5 edges
6. `AI Domain Tools (clientes/financeiro/catalogo/orcamento)` - 5 edges
7. `ia_service.py — AI Service Core` - 4 edges
8. `Permission System Architecture` - 4 edges
9. `System Audit Spec` - 4 edges
10. `Clientes Module` - 3 edges

## Surprising Connections (you probably didn't know these)
- `Plans Modal README` --conceptually_related_to--> `System Features Overview`  [INFERRED]
  docs/archive/MODAL_PLANOS_README.md → docs/funcionalidades.md
- `Improvement Proposals Plan` --references--> `System Features Overview`  [INFERRED]
  docs/tecnico/plano-melhorias-proposta.md → docs/funcionalidades.md
- `System Use Cases` --references--> `System Features Overview`  [INFERRED]
  docs/operacional/casos-de-uso.md → docs/funcionalidades.md
- `Document Editor Plan` --conceptually_related_to--> `Orçamentos Module`  [INFERRED]
  docs/archive/editor_documentos_plano.md → docs/funcionalidades.md
- `General System Audit` --references--> `Permission System Architecture`  [INFERRED]
  docs/archive/AUDIT.md → docs/archive/audit-permissoes.md

## Communities

### Community 0 - "Database & Backend Architecture"
Cohesion: 0.22
Nodes (9): Alembic Database Migrations, General System Audit, System Audit Index, System Audit Plan, System Audit Report, System Audit Spec, FastAPI Backend Stack, SQLAlchemy ORM Layer (+1 more)

### Community 1 - "AI Service & Orchestration Core"
Cohesion: 0.29
Nodes (8): cotte_ai_hub.py — AI Orchestrator, ia_service.py — AI Service Core, IA Instructions Updated, Assistente IA v2 Plan, Tool-Use v2 Plan, COTTE AI Service v2 Prompt, Tool-Use Architecture, Evolution API WhatsApp Provider

### Community 2 - "System Features & WhatsApp"
Cohesion: 0.25
Nodes (8): COTTE Assistant Analysis, System Use Cases, System Features Overview, IA Import Implementation, Plans Modal README, Assistente IA Module, WhatsApp Integration Module, Improvement Proposals Plan

### Community 3 - "Financial Module & Audit"
Cohesion: 0.33
Nodes (6): Análise Financeiro, Audit Financeiro, Financial Operations Playbook, Financeiro Module, Financial Implementation Plan, Financeiro Module Technical Spec

### Community 4 - "Infrastructure & Cloud Storage"
Cohesion: 0.33
Nodes (6): Cloudflare R2 Storage, CORS R2 Fix, Railway Deploy Guide, R2 Migration Guide, Railway Deployment Platform, Environment Variables Guide

### Community 5 - "AI Tools & Client Domain"
Cohesion: 0.33
Nodes (6): AI Domain Tools (clientes/financeiro/catalogo/orcamento), Assistente Tool-Use Architecture, Client Registration Technical Spec, Clientes Module, Catálogo Module Technical Spec, Tool Trace Logging System

### Community 6 - "Permissions & Security"
Cohesion: 0.4
Nodes (6): Permissions Audit, exigir_permissao — Auth Guard, Scalable Permissions Prompt, Permission System Architecture, Sprint Prioritization Framework, Permissions Module Technical Spec

### Community 7 - "Assistente IA UX & Personalization"
Cohesion: 0.4
Nodes (6): Assistente IA Recent Improvements 2026-04-10, Assistente IA Hybrid Personalization, IA Context Panel (Desktop), Assistente IA Technical Spec, Manual Test Plan — Last 20 Commits, IA Thinking Steps / Breadcrumbs

### Community 8 - "Orçamentos, PDF & OTP"
Cohesion: 0.33
Nodes (6): Orçamento Documents Module, Document Editor Plan, OTP Acceptance Flow, Orçamentos Module, OTP-based Quote Acceptance, PDF Generation Service

### Community 9 - "Frontend Refactor & UX"
Cohesion: 0.5
Nodes (4): Refatoração Documentation, New Frontend Plan, UX Improvements Archive, Vanilla JS Frontend Stack

### Community 10 - "PWA & Service Workers"
Cohesion: 0.5
Nodes (4): Bubblewrap TWA Plan, PWA / Android App via TWA, Service Worker (Workbox), Workbox Service Worker Migration

### Community 11 - "Notion & OpenClaw Integration"
Cohesion: 1.0
Nodes (2): Notion Databases (Tasks/Changelog/Roadmap), OpenClaw Notion Integration

### Community 12 - "Agendamento Module"
Cohesion: 1.0
Nodes (2): Agendamento Bug Fix, Agendamento Module Technical Spec

### Community 13 - "Implementation Archive"
Cohesion: 1.0
Nodes (2): Change Documentation, Complete Implementation Archive

### Community 14 - "Roadmap & Improvements"
Cohesion: 1.0
Nodes (2): GRK Improvements List, Connected Roadmap

### Community 15 - "Email (Brevo) Integration"
Cohesion: 1.0
Nodes (2): Brevo Email Service, Brevo Email Setup

### Community 16 - "Company Settings"
Cohesion: 1.0
Nodes (2): Company Settings Model, Configurações Module Technical Spec

### Community 17 - "User Guide"
Cohesion: 1.0
Nodes (1): User Guide - COTTE

### Community 18 - "Session Notes"
Cohesion: 1.0
Nodes (1): Session Notes / Scratch Doc

### Community 19 - "Technical Audit Archive"
Cohesion: 1.0
Nodes (1): Technical Audit

### Community 20 - "Implementation Summary"
Cohesion: 1.0
Nodes (1): Implementation Summary

### Community 21 - "Updates Tracker"
Cohesion: 1.0
Nodes (1): Latest Updates To Test

### Community 22 - "Implementation Review"
Cohesion: 1.0
Nodes (1): Review Implementation Checklist

## Knowledge Gaps
- **52 isolated node(s):** `OpenClaw Notion Integration`, `Notion Databases (Tasks/Changelog/Roadmap)`, `WhatsApp Integration Module`, `User Guide - COTTE`, `Session Notes / Scratch Doc` (+47 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Notion & OpenClaw Integration`** (2 nodes): `Notion Databases (Tasks/Changelog/Roadmap)`, `OpenClaw Notion Integration`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Agendamento Module`** (2 nodes): `Agendamento Bug Fix`, `Agendamento Module Technical Spec`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Implementation Archive`** (2 nodes): `Change Documentation`, `Complete Implementation Archive`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Roadmap & Improvements`** (2 nodes): `GRK Improvements List`, `Connected Roadmap`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Email (Brevo) Integration`** (2 nodes): `Brevo Email Service`, `Brevo Email Setup`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Company Settings`** (2 nodes): `Company Settings Model`, `Configurações Module Technical Spec`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `User Guide`** (1 nodes): `User Guide - COTTE`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Session Notes`** (1 nodes): `Session Notes / Scratch Doc`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Technical Audit Archive`** (1 nodes): `Technical Audit`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Implementation Summary`** (1 nodes): `Implementation Summary`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Updates Tracker`** (1 nodes): `Latest Updates To Test`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Implementation Review`** (1 nodes): `Review Implementation Checklist`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `System Features Overview` connect `System Features & WhatsApp` to `Orçamentos, PDF & OTP`, `Financial Module & Audit`, `AI Tools & Client Domain`?**
  _High betweenness centrality (0.107) - this node is a cross-community bridge._
- **Why does `Assistente IA Module` connect `System Features & WhatsApp` to `AI Service & Orchestration Core`, `Assistente IA UX & Personalization`?**
  _High betweenness centrality (0.097) - this node is a cross-community bridge._
- **Why does `Financeiro Module` connect `Financial Module & Audit` to `System Features & WhatsApp`, `AI Tools & Client Domain`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `System Features Overview` (e.g. with `Plans Modal README` and `Improvement Proposals Plan`) actually correct?**
  _`System Features Overview` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `OpenClaw Notion Integration`, `Notion Databases (Tasks/Changelog/Roadmap)`, `WhatsApp Integration Module` to the rest of the system?**
  _52 weakly-connected nodes found - possible documentation gaps or missing edges._