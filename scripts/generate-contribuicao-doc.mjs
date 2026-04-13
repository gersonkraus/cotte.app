#!/usr/bin/env node
/**
 * Gera docs/contribuicao.md a partir de docs/contribuicao.yaml.
 *
 * Uso: node scripts/generate-contribuicao-doc.mjs
 *      npm run generate:contribuicao
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { parse as parseYaml } from 'yaml';
import GithubSlugger from 'github-slugger';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, '..');
const YAML_PATH = path.join(ROOT, 'docs', 'contribuicao.yaml');
const OUT_PATH = path.join(ROOT, 'docs', 'contribuicao.md');

/** Âncora GitHub para um único título (primeira ocorrência no ficheiro). */
function anchor(heading) {
  return new GithubSlugger().slug(heading);
}

function resolveHeading(section, role) {
  const t = section.title || '';
  if (role === 'agents') {
    if (section.contributing_only) return null;
    return section.agents_heading ?? t;
  }
  if (role === 'contributing') {
    if (section.agents_only) return null;
    return section.contributing_heading ?? t;
  }
  return t;
}

function main() {
  if (!fs.existsSync(YAML_PATH)) {
    console.error('generate-contribuicao-doc: falta docs/contribuicao.yaml');
    process.exit(1);
  }
  const raw = fs.readFileSync(YAML_PATH, 'utf8');
  const doc = parseYaml(raw);
  const hub = doc.hub || {};
  const sections = Array.isArray(doc.sections) ? doc.sections : [];

  const lines = [];
  lines.push('<!-- Gerado por scripts/generate-contribuicao-doc.mjs — não editar manualmente -->');
  lines.push('<!-- Fonte: docs/contribuicao.yaml -->');
  lines.push('');
  lines.push(`# ${hub.title || 'Contribuição — índice'}`);
  lines.push('');
  if (hub.intro) {
    lines.push(hub.intro.trim());
    lines.push('');
  }

  for (const section of sections) {
    const title = section.title || 'Sem título';
    lines.push(`## ${title}`);
    lines.push('');
    if (section.summary) {
      lines.push(`**Resumo:** ${section.summary.trim().replace(/\s+/g, ' ')}`);
      lines.push('');
    }
    const ah = resolveHeading(section, 'agents');
    const ch = resolveHeading(section, 'contributing');
    const links = [];
    if (ah) {
      const slug = anchor(ah);
      links.push(`[AGENTS.md — ${ah}](../AGENTS.md#${slug})`);
    }
    if (ch) {
      const slug = anchor(ch);
      links.push(`[CONTRIBUTING.md — ${ch}](../CONTRIBUTING.md#${slug})`);
    }
    if (links.length) {
      lines.push(`- ${links.join('\n- ')}`);
    } else {
      lines.push('*Sem ligações definidas no YAML.*');
    }
    lines.push('');
  }

  const out = `${lines.join('\n').trim()}\n`;
  fs.writeFileSync(OUT_PATH, out, 'utf8');
  console.log(`generate-contribuicao-doc: escrito ${path.relative(ROOT, OUT_PATH)} (${sections.length} secções).`);
}

main();
