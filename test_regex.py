import re

mensagens = [
    "listar orçamentos da ana julia ID 1",
    "orçamentos da ana julia",
    "orçamentos do joão silva nos últimos 30 dias",
    "orçamentos de maria",
    "listar orçamentos do cliente joão da silva pereira limit 10",
]

for msg in mensagens:
    # match cliente/id
    id_match = re.search(r'(?:cliente|id|código|codigo)\s*(\d+)', msg.lower())
    if id_match:
        print(f"ID match: {id_match.group(1)} in {msg}")
    else:
        # tentar nome
        nome_match = re.search(r'(?:orçamentos?|or[çc]amentos?)\s+(?:da|do|de|para|cliente)\s+([a-záàâãéèêíïóôõöúçñ ]+?)(?:\s+(?:nos?|últimos?|hoje|ontem|dias|id|código|limit|status|aprovado)|$)', msg.lower())
        if nome_match:
            print(f"Nome match: {nome_match.group(1).strip()} in {msg}")
        else:
            print(f"NO MATCH in {msg}")
