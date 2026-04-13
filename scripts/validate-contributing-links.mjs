#!/usr/bin/env node
/**
 * Garante que AGENTS.md e CONTRIBUTING.md mantenham os mesmos títulos ## para
 * seções consideradas críticas (contrato documental entre guia de agentes e guia humano).
 *
 * Uso: node scripts/validate-contributing-links.mjs
 *      npm run validate:contributing
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, '..');

/** Deve existir com o mesmo texto em ambos os arquivos (linha ## Título). */
const CRITICAL_SECTIONS = [
  'Ordem de precedência',
  'Regras para backend',
  'Regras para frontend',
  'Regras para debug',
  'Regras para configuração',
  'Regras para testes e validação',
  'O que evitar',
  'Princípio final',
];

function extractH2(md) {
  const h2 = [];
  for (const line of md.split(/\r?\n/)) {
    const m = line.match(/^## (.+)$/);
    if (m) h2.push(m[1].trim());
  }
  return h2;
}

function main() {
  const agentsPath = path.join(ROOT, 'AGENTS.md');
  const contributingPath = path.join(ROOT, 'CONTRIBUTING.md');
  if (!fs.existsSync(agentsPath) || !fs.existsSync(contributingPath)) {
    console.error('validate-contributing-links: AGENTS.md ou CONTRIBUTING.md não encontrado(s).');
    process.exit(1);
  }
  const agents = fs.readFileSync(agentsPath, 'utf8');
  const contributing = fs.readFileSync(contributingPath, 'utf8');
  const agentsH2 = new Set(extractH2(agents));
  const contributingH2 = new Set(extractH2(contributing));
  const missing = [];
  for (const title of CRITICAL_SECTIONS) {
    if (!agentsH2.has(title)) missing.push(`AGENTS.md: falta ou título diferente de "## ${title}"`);
    if (!contributingH2.has(title)) missing.push(`CONTRIBUTING.md: falta ou título diferente de "## ${title}"`);
  }
  if (missing.length) {
    console.error('validate-contributing-links: desalinhamento em títulos críticos:\n');
    for (const m of missing) console.error(`  - ${m}`);
    console.error('\nEdite um dos arquivos para restaurar o mesmo título ## ou atualize CRITICAL_SECTIONS no script.');
    process.exit(1);
  }
  console.log('validate-contributing-links: OK (títulos críticos alinhados entre AGENTS.md e CONTRIBUTING.md).');
}

main();
