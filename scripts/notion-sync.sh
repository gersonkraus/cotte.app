#!/bin/bash

# Sincroniza tarefa do Notion via commit
# Uso: ./notion-sync.sh "mensagem do commit" "abc123"

NOTION_TOKEN="ntn_u15160279237JsHCPSTgk1Bm9sDzylBzOugxDzCTHRjg6p"
TAREFAS_DB="45ec8ca9-a98d-46f8-9cb9-891b1dea67e4"
REPO_URL="https://github.com/gersonkraus/Projeto-izi"

COMMIT_MSG="$1"
COMMIT_HASH="$2"
COMMIT_URL="$REPO_URL/commit/$COMMIT_HASH"

# Extrai número da tarefa (#123) da mensagem
if [[ "$COMMIT_MSG" =~ \#([0-9]+) ]]; then
    TASK_REF="${BASH_REMATCH[1]}"
else
    echo "⚠️  Nenhuma referência de tarefa encontrada na mensagem"
    exit 0
fi

echo "🔍 Buscando tarefa com Ref=$TASK_REF..."

# Busca tarefa pelo campo Ref
SEARCH_RESULT=$(curl -s -X POST "https://api.notion.com/v1/databases/$TAREFAS_DB/query" \
  -H "Authorization: Bearer $NOTION_TOKEN" \
  -H 'Notion-Version: 2022-06-28' \
  -H 'Content-Type: application/json' \
  -d "{
    \"filter\": {
      \"property\": \"Ref\",
      \"number\": {
        \"equals\": $TASK_REF
      }
    }
  }")

# Extrai ID da página da tarefa
TASK_PAGE_ID=$(echo "$SEARCH_RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
results = data.get('results', [])
if results:
    print(results[0]['id'])
else:
    print('')
")

if [ -z "$TASK_PAGE_ID" ]; then
    echo "❌ Tarefa #$TASK_REF não encontrada"
    exit 1
fi

# Extrai nome da tarefa
TASK_NAME=$(echo "$SEARCH_RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
results = data.get('results', [])
if results:
    title = results[0]['properties']['Tarefa']['title']
    if title:
        print(title[0]['plain_text'])
    else:
        print('Sem título')
else:
    print('Não encontrada')
")

echo "📋 Tarefa encontrada: $TASK_NAME"

# Atualiza status e último commit
UPDATE_RESULT=$(curl -s -X PATCH "https://api.notion.com/v1/pages/$TASK_PAGE_ID" \
  -H "Authorization: Bearer $NOTION_TOKEN" \
  -H 'Notion-Version: 2022-06-28' \
  -H 'Content-Type: application/json' \
  -d "{
    \"properties\": {
      \"Status\": {
        \"select\": {\"name\": \"Feito\"}
      },
      \"Último Commit\": {
        \"url\": \"$COMMIT_URL\"
      }
    }
  }")

if echo "$UPDATE_RESULT" | grep -q '"object":"page"'; then
    echo "✅ Tarefa #$TASK_REF atualizada para 'Feito'"
    echo "🔗 $COMMIT_URL"
else
    echo "❌ Erro ao atualizar tarefa"
    exit 1
fi
