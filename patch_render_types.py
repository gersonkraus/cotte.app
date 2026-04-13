import re

with open('sistema/cotte-frontend/js/assistente-ia-render-types.js', 'r') as f:
    content = f.read()

# Remove the bad button
content = re.sub(r'\n                    <button type="button" class="orc-card-v2__icon-btn btn-calendar".*?</button>', '', content)

# Add the correct button
pattern = r'(function renderOrcamentoAprovado\(dados\) \{.*?<div class="orc-card-v2__icon-btns">)'
replacement = r"""\1
                    <button type="button" class="orc-card-v2__icon-btn btn-calendar" onclick="abrirModalAgendamentoRapido(${orcId}, '${escapeHtml(orcNum)}', '${(clienteNome || '').replace(/'/g, "\\\\'")}')" title="Agendar">📅</button>"""

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open('sistema/cotte-frontend/js/assistente-ia-render-types.js', 'w') as f:
    f.write(content)
