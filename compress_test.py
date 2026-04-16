def to_llm_payload(data):
    if not isinstance(data, dict):
        return data
    
    result = {"summary": "Dados agregados resumidos (apenas para o LLM raciocinar). Os dados completos estão salvos no contexto da interface."}
    
    for key, value in data.items():
        if isinstance(value, list) and len(value) > 10:
            result[key] = {
                "total_items": len(value),
                "rows_preview": value[:10],
                "note": f"Exibindo 10 de {len(value)} itens. O UI tem acesso à lista completa."
            }
        else:
            result[key] = value
            
    return result

print(to_llm_payload({"items": [1]*20, "total": 100}))
