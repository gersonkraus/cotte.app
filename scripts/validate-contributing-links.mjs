#!/usr/bin/env node
/**
 * Garante que AGENTS.md e CONTRIBUTING.md mantenham os mesmos títulos ## para
 * seções críticas definidas em docs/contribuicao.yaml (critical: true).
 *
 * Uso: node scripts/validate-contributing-links.mjs
 *      npm run validate:contributing
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { parse as parseYaml } from 'yaml';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, '..');
const YAML_PATH = path.join(ROOT, 'docs', 'contribuicao.yaml');

function extractH2(md) {
  const h2 = [];
  for (const line of md.split(/\r?\n/)) {
    const m = line.match(/^## (.+)$/);
    if (m) h2.push(m[1].trim());
  }
  return h2;
}

function loadCriticalTitles() {
  if (!fs.existsSync(YAML_PATH)) {
    console.error('validate-contributing-links: falta docs/contribuicao.yaml');
    process.exit(1);
  }
  const doc = parseYaml(fs.readFileSync(YAML_PATH, 'utf8'));
  const sections = Array.isArray(doc.sections) ? doc.sections : [];
  const critical = sections.filter((s) => s && s.critical === true);
  const titles = critical.map((s) => s.title).filter(Boolean);
  if (!titles.length) {
    console.error('validate-contributing-links: nenhuma secção critical: true em docs/contribuicao.yaml');
    process.exit(1);
  }
  return titles;
}

function main() {
  const agentsPath = path.join(ROOT, 'AGENTS.md');
  const contributingPath = path.join(ROOT, 'CONTRIBUTING.md');
  if (!fs.existsSync(agentsPath) || !fs.existsSync(contributingPath)) {
    console.error('validate-contributing-links: AGENTS.md ou CONTRIBUTING.md não encontrado(s).');
    process.exit(1);
  }
  const CRITICAL_SECTIONS = loadCriticalTitles();
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
    console.error('\nAjuste os ficheiros ou docs/contribuicao.yaml (secções com critical: true).');
    process.exit(1);
  }
  console.log('validate-contributing-links: OK (títulos críticos alinhados entre AGENTS.md e CONTRIBUTING.md).');
}

main();
