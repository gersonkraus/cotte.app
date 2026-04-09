# Referência Rápida - Notion API

## Configuração
```bash
NOTION_TOKEN="ntn_u15160279237JsHCPSTgk1Bm9sDzylBzOugxDzCTHRjg6p"
TAREFAS_DB="45ec8ca9-a98d-46f8-9cb9-891b1dea67e4"
CHANGELOG_DB="9e7c839c-0b2a-4d30-861f-37a1d0c45d54"
ROADMAP_DB="32e05a5c-c013-8165-b1e5-c6d1b9c656cd"
```

## Listar tarefas pendentes
```bash
./scripts/notion-tasks.sh
```

## Criar tarefa
```bash
curl -s -X POST 'https://api.notion.com/v1/pages' \
  -H "Authorization: Bearer $NOTION_TOKEN" \
  -H 'Notion-Version: 2022-06-28' \
  -H 'Content-Type: application/json' \
  -d '{
    "parent": {"database_id": "'$TAREFAS_DB'"},
    "properties": {
      "Tarefa": {"title": [{"text": {"content": "Título"}}]},
      "Status": {"select": {"name": "A fazer"}},
      "Prioridade": {"select": {"name": "🔴 Alta"}},
      "Responsável": {"select": {"name": "IA"}},
      "Ref": {"number": 5}
    }
  }'
```

## Atualizar status
```bash
curl -s -X PATCH 'https://api.notion.com/v1/pages/PAGE_ID' \
  -H "Authorization: Bearer $NOTION_TOKEN" \
  -H 'Notion-Version: 2022-06-28' \
  -H 'Content-Type: application/json' \
  -d '{"properties": {"Status": {"select": {"name": "Feito"}}}}'
```

## Buscar tarefa por Ref
```bash
curl -s -X POST "https://api.notion.com/v1/databases/$TAREFAS_DB/query" \
  -H "Authorization: Bearer $NOTION_TOKEN" \
  -H 'Notion-Version: 2022-06-28' \
  -H 'Content-Type: application/json' \
  -d '{"filter": {"property": "Ref", "number": {"equals": 4}}}'
```

## Status disponíveis
- Backlog (não listado automaticamente)
- A fazer
- Em progresso
- Feito
