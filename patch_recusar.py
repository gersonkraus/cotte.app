import re

with open('sistema/app/services/ai_tools/orcamento_tools.py', 'r') as f:
    content = f.read()

old_return = """    return {
        "id": orc.id,
        "numero": orc.numero,
        "status": "recusado",
        "impacto_financeiro": {
            "contas_pendentes_removidas": qtd_pendentes,
            "valor_total_pendente_removido": valor_pendente,
            "observacao": (
                "Ao sair de APROVADO, contas a receber pendentes sem pagamento são removidas; "
                "contas com pagamento permanecem para preservar histórico."
            ),
        },
    }"""

new_return = """    return _build_orcamento_response(orc, {
        "status": "recusado",
        "impacto_financeiro": {
            "contas_pendentes_removidas": qtd_pendentes,
            "valor_total_pendente_removido": valor_pendente,
            "observacao": (
                "Ao sair de APROVADO, contas a receber pendentes sem pagamento são removidas; "
                "contas com pagamento permanecem para preservar histórico."
            ),
        },
    })"""

content = content.replace(old_return, new_return)

with open('sistema/app/services/ai_tools/orcamento_tools.py', 'w') as f:
    f.write(content)
