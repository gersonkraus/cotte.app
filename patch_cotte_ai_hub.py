import re

with open('sistema/app/services/cotte_ai_hub.py', 'r') as f:
    content = f.read()

# Patch 1: assistente_v2_stream_core
content = re.sub(
    r'if _tool_exec == "editar_orcamento":\s+final_text = "✅ Orçamento atualizado com sucesso."\s+tipo_resp = "orcamento_atualizado"\s+else:\s+final_text = "✅ Ação concluída com sucesso."\s+tipo_resp = "orcamento_criado"',
    r'''if _tool_exec == "editar_orcamento":
                final_text = "✅ Orçamento atualizado com sucesso."
                tipo_resp = "orcamento_atualizado"
            elif _tool_exec == "aprovar_orcamento":
                final_text = "✅ Orçamento aprovado com sucesso."
                tipo_resp = "orcamento_aprovado"
            elif _tool_exec == "recusar_orcamento":
                final_text = "✅ Orçamento recusado com sucesso."
                tipo_resp = "orcamento_recusado"
            else:
                final_text = "✅ Ação concluída com sucesso."
                tipo_resp = "orcamento_criado"''',
    content
)

# Patch 2: assistente_unificado_v2
content = re.sub(
    r'if _tool_exec == "editar_orcamento":\s+final_text = "✅ Orçamento atualizado com sucesso."\s+tipo_resp = "orcamento_atualizado"\s+else:\s+final_text = "✅ Orçamento criado com sucesso."\s+tipo_resp = "orcamento_criado"',
    r'''if _tool_exec == "editar_orcamento":
                        final_text = "✅ Orçamento atualizado com sucesso."
                        tipo_resp = "orcamento_atualizado"
                    elif _tool_exec == "aprovar_orcamento":
                        final_text = "✅ Orçamento aprovado com sucesso."
                        tipo_resp = "orcamento_aprovado"
                    elif _tool_exec == "recusar_orcamento":
                        final_text = "✅ Orçamento recusado com sucesso."
                        tipo_resp = "orcamento_recusado"
                    else:
                        final_text = "✅ Orçamento criado com sucesso."
                        tipo_resp = "orcamento_criado"''',
    content
)

with open('sistema/app/services/cotte_ai_hub.py', 'w') as f:
    f.write(content)
