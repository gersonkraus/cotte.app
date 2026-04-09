#!/usr/bin/env bash
set -euo pipefail

# Bloqueia commits que contenham entradas gitlink (modo 160000),
# normalmente causadas por sub-repositórios acidentais.
gitlinks="$(git ls-files -s | awk '$1 == "160000" { print $4 }')"

if [[ -n "${gitlinks}" ]]; then
  echo "ERRO: foram detectados gitlinks/submodulos no indice:"
  echo "${gitlinks}" | sed 's/^/ - /'
  echo
  echo "Para corrigir, remova do indice com:"
  echo "  git rm --cached <caminho>"
  echo
  echo "Depois adicione uma regra no .gitignore para o caminho."
  exit 1
fi

echo "OK: nenhum gitlink encontrado no indice."
