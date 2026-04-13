import requests

payload = {
    "cliente_id": 1,
    "itens": [
        {"descricao": "Teste", "quantidade": 1, "valor_unit": 100}
    ],
    "agendamento_modo": "OPCIONAL"
}
# We can't really call the API without a token easily, I will just inspect the router
