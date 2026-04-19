import re
text = 'Liste mais orçamentos com cursor "2024-04-18T10:30:00|123", limite 10. Status aprovado.'
pat = r'\b(quais|liste|lista|ver|mostrar|mostre)\s+(mais\s+)?((os|meus)\s+)?or[çc]amentos?\b'
print(re.search(pat, text, re.IGNORECASE))
