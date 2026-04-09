#!/bin/bash

# Lista tarefas pendentes do Notion

NOTION_TOKEN="ntn_u15160279237JsHCPSTgk1Bm9sDzylBzOugxDzCTHRjg6p"
TAREFAS_DB="45ec8ca9-a98d-46f8-9cb9-891b1dea67e4"

curl -s -X POST "https://api.notion.com/v1/databases/$TAREFAS_DB/query" \
  -H "Authorization: Bearer $NOTION_TOKEN" \
  -H 'Notion-Version: 2022-06-28' \
  -H 'Content-Type: application/json' \
  -d '{
    "filter": {
      "or": [
        {"property": "Status", "select": {"equals": "A fazer"}},
        {"property": "Status", "select": {"equals": "Em progresso"}}
      ]
    },
    "sorts": [
      {"property": "Ref", "direction": "ascending"}
    ]
  }' | python3 -c "
import sys, json

data = json.load(sys.stdin)
results = data.get('results', [])

if not results:
    print('✅ Nenhuma tarefa pendente!')
    sys.exit(0)

print(f'📋 Tarefas pendentes: {len(results)}')
print()

for task in results:
    props = task['properties']
    
    # Título
    title = props['Tarefa']['title'][0]['plain_text'] if props['Tarefa']['title'] else 'Sem título'
    
    # Ref
    ref = props['Ref']['number'] if props['Ref'] else '?'
    
    # Status
    status = props['Status']['select']['name'] if props['Status']['select'] else 'N/A'
    
    # Prioridade
    prioridade = props['Prioridade']['select']['name'] if props['Prioridade']['select'] else '—'
    
    # Responsável
    responsavel = props['Responsável']['select']['name'] if props['Responsável']['select'] else '—'
    
    # Prazo
    prazo = props['Prazo']['date']['start'] if props['Prazo']['date'] else '—'
    
    # Sprint
    sprint = props['Sprint']['select']['name'] if props['Sprint']['select'] else '—'
    
    # Status emoji
    status_emoji = '🔴' if status == 'A fazer' else '🟡'
    
    print(f'{status_emoji} #{ref}: {title}')
    print(f'   Prioridade: {prioridade} | Responsável: {responsavel} | Prazo: {prazo} | Sprint: {sprint}')
    print()
"
