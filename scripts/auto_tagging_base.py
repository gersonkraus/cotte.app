#!/usr/bin/env python3
"""
Auto-tagging script para COTTE_Documentacao.base

Varre arquivos .md, detecta falta de propriedades YAML e adiciona
automaticamente baseado em padrões de caminho e nome.

Uso:
    python scripts/auto_tagging_base.py --scan      # Ver o que será alterado
    python scripts/auto_tagging_base.py --apply     # Aplicar mudanças
    python scripts/auto_tagging_base.py --history   # Ver histórico
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Configuração
PROJETO_ROOT = Path(__file__).parent.parent
DOCS_IGNORE = {
    'venv', 'node_modules', '.pytest_cache', 'playwright-report', '.git', 'tests',
    '.agentlens', '.claude', '.clinerules', '.windsurf', '.vscode', '.cursor',
    '.continue', '.gemini', '.rtk', '__pycache__', 'memoriaclaude', 'ob-claude'
}
HISTORY_FILE = PROJETO_ROOT / '.rtk' / 'tagging_history.json'

# Padrões de detecção de categoria
PATTERNS = {
    'deploy': [
        r'DEPLOY.*\.md',
        r'.*railway.*\.md',
        r'variaveis_ambiente.*\.md',
        r'docs/.*\.md' if 'DEPLOY' in '' else None,
    ],
    'roadmap': [
        r'.*roadmap.*\.md',
        r'.*plano.*\.md',
    ],
    'implementacao': [
        r'PLANO.*\.md',
        r'IMPLEMENTACAO.*\.md',
        r'.*refator.*\.md',
    ],
    'tecnico': [
        r'mapa-.*\.md',
        r'arquitetura.*\.md',
        r'fluxo.*\.md',
        r'stack.*\.md',
        r'docs/.*\.md',
    ],
    'documentacao': [
        r'README\.md',
        r'guia.*\.md',
        r'padroes.*\.md',
        r'identidade.*\.md',
    ],
    'memoria': [
        r'memory/.*\.md',
    ],
}


def detect_category(file_path: Path) -> str:
    """Detecta categoria baseada no caminho e nome do arquivo."""
    file_str = str(file_path).lower()

    # Padrões especiais
    if 'memory/' in file_str:
        return 'memoria'
    if 'ANALISE' in str(file_path):
        return 'analise'

    # Verificar padrões
    for category, patterns in PATTERNS.items():
        for pattern in patterns:
            if pattern and re.search(pattern, file_str, re.IGNORECASE):
                return category

    return 'documentacao'


def detect_priority(file_path: Path, category: str) -> str:
    """Detecta prioridade baseada no arquivo."""
    priority_high = {
        'README', 'COTTE', 'arquitetura', 'stack', 'fluxo',
        'roadmap', 'deploy', 'ANALISE_FINANCEIRO', 'PLANO'
    }

    file_name = file_path.name

    # Root files and critical docs are high priority
    if file_path.parent == PROJETO_ROOT and file_path.name not in {'claude.md', 'RTK.md'}:
        return 'alta'

    if any(critical in file_name for critical in priority_high):
        return 'alta'

    if category == 'tecnico' and 'mapa' in file_name:
        return 'media'

    return 'media' if category in {'roadmap', 'implementacao'} else 'media'


def detect_status(file_path: Path, category: str) -> str:
    """Detecta status do documento."""
    file_name = file_path.name.lower()

    if 'memoria' in str(file_path):
        return 'ativo'
    if 'IMPLEMENTACAO_COMPLETA' in file_path.name:
        return 'concluído'
    if 'roadmap' in file_name:
        return 'em-andamento'
    if 'PLANO' in file_path.name:
        return 'planejado'

    return 'documentado'


def extract_frontmatter(content: str) -> Optional[Dict]:
    """Extrai YAML frontmatter do arquivo."""
    if not content.startswith('---'):
        return None

    lines = content.split('\n')
    end_idx = None

    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            end_idx = i
            break

    if end_idx is None:
        return None

    try:
        import yaml
        frontmatter_text = '\n'.join(lines[1:end_idx])
        return yaml.safe_load(frontmatter_text)
    except:
        return {}


def has_required_properties(file_path: Path) -> bool:
    """Verifica se arquivo tem as propriedades mínimas."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if not content.startswith('---'):
            return False

        fm = extract_frontmatter(content)
        if not fm:
            return False

        required = {'title', 'tags', 'prioridade', 'status'}
        return required.issubset(set(fm.keys()))
    except Exception as e:
        print(f"Erro ao ler {file_path}: {e}")
        return False


def build_frontmatter(file_path: Path, existing: Optional[Dict] = None) -> str:
    """Constrói novo frontmatter YAML."""
    if existing is None:
        existing = {}

    category = detect_category(file_path)
    priority = detect_priority(file_path, category)
    status = detect_status(file_path, category)

    # Extrair título do nome do arquivo
    title = existing.get('title') or file_path.stem.replace('_', ' ').replace('-', ' ').title()

    # Manter tags existentes se houver
    tags = existing.get('tags', [])
    if not tags:
        tags = [category]
        if category == 'tecnico' and 'mapa' in file_path.name:
            tags.extend(['mapa', 'tecnico'])
        elif 'backend' in str(file_path).lower():
            tags.append('backend')
        elif 'frontend' in str(file_path).lower() or file_path.parent.name == 'cotte-frontend':
            tags.append('frontend')

    fm = f"""---
title: {title}
tags:
"""

    for tag in tags:
        fm += f"  - {tag}\n"

    fm += f"prioridade: {existing.get('prioridade', priority)}\n"
    fm += f"status: {existing.get('status', status)}\n"
    fm += "---\n"

    return fm


def scan_directory(dry_run: bool = True) -> List[Dict]:
    """Varre diretório e retorna arquivos que precisam de atualização."""
    to_update = []

    for md_file in PROJETO_ROOT.rglob('*.md'):
        # Skip ignored directories
        if any(ignore in md_file.parts for ignore in DOCS_IGNORE):
            continue

        # Skip venv and node_modules
        if '.venv' in str(md_file) or 'venv' in str(md_file):
            continue

        if not has_required_properties(md_file):
            rel_path = md_file.relative_to(PROJETO_ROOT)
            to_update.append({
                'path': str(rel_path),
                'category': detect_category(md_file),
                'priority': detect_priority(md_file, detect_category(md_file)),
                'status': detect_status(md_file, detect_category(md_file)),
            })

    return sorted(to_update, key=lambda x: x['path'])


def apply_changes(updates: List[Dict]) -> Dict:
    """Aplica mudanças nos arquivos."""
    results = {
        'updated': [],
        'errors': [],
        'timestamp': datetime.now().isoformat(),
    }

    for update in updates:
        file_path = PROJETO_ROOT / update['path']

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Se já tem frontmatter, extrair e atualizar
            existing_fm = extract_frontmatter(content)

            if existing_fm:
                # Remover frontmatter antigo
                lines = content.split('\n')
                end_idx = 1
                for i in range(1, len(lines)):
                    if lines[i].strip() == '---':
                        end_idx = i + 1
                        break
                content = '\n'.join(lines[end_idx:])
            else:
                existing_fm = {}

            # Atualizar propriedades
            existing_fm.update({
                'prioridade': update['priority'],
                'status': update['status'],
            })

            # Construir novo frontmatter
            new_fm = build_frontmatter(file_path, existing_fm)
            new_content = new_fm + content.lstrip('\n')

            # Escrever arquivo
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            results['updated'].append({
                'path': update['path'],
                'category': update['category'],
            })

        except Exception as e:
            results['errors'].append({
                'path': update['path'],
                'error': str(e),
            })

    return results


def save_history(results: Dict):
    """Salva histórico de alterações."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    history = []
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, 'r') as f:
            history = json.load(f)

    history.append(results)

    # Manter apenas últimos 10 registros
    history = history[-10:]

    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)


def main():
    import sys

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == '--scan':
        print("🔍 Escaneando documentos sem propriedades...\n")
        updates = scan_directory(dry_run=True)

        if not updates:
            print("✅ Todos os documentos têm propriedades corretas!")
            return

        print(f"📋 {len(updates)} arquivo(s) precisam atualização:\n")
        for update in updates:
            print(f"  • {update['path']}")
            print(f"    └─ Categoria: {update['category']}, Prioridade: {update['priority']}")

    elif command == '--apply':
        print("⚙️  Aplicando mudanças...\n")
        updates = scan_directory()

        if not updates:
            print("✅ Nada a fazer!")
            return

        results = apply_changes(updates)
        save_history(results)

        print(f"✅ {len(results['updated'])} arquivo(s) atualizado(s)")
        if results['errors']:
            print(f"❌ {len(results['errors'])} erro(s)")
            for err in results['errors']:
                print(f"   {err['path']}: {err['error']}")

    elif command == '--history':
        if not HISTORY_FILE.exists():
            print("Nenhum histórico encontrado.")
            return

        with open(HISTORY_FILE, 'r') as f:
            history = json.load(f)

        print("📜 Histórico de tagging:\n")
        for i, entry in enumerate(history[-5:], 1):
            print(f"{i}. {entry['timestamp']}")
            print(f"   ✅ Atualizados: {len(entry['updated'])}")
            if entry['errors']:
                print(f"   ❌ Erros: {len(entry['errors'])}")
            print()

    else:
        print(f"Comando desconhecido: {command}")
        print(__doc__)


if __name__ == '__main__':
    main()
