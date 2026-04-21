Sintoma
Múltiplas tools com funcionalidades sobrepostas podem causar comportamento imprevisível, onde o mesmo comando gera resultados diferentes dependendo de qual tool o LLM escolhe.
Onde está o problema
Backend - sistema/app/services/ai_tools/ e sistema/app/services/ai_intention_classifier.py
Evidência
🔴 CONFLITOS CRÍTICOS IDENTIFICADOS
---
1. Conflito: "Ranking de Clientes"
Gatilho	Tools que podem responder
"ranking de clientes"	gerar_relatorio_dinamico (domínio: clientes)
"top clientes"	gerar_relatorio_dinamico (domínio: orcamentos, agrupamento: cliente)
"melhores clientes"	gerar_relatorio_ranking_clientes
"quem mais comprou"	gerar_relatorio_vendas (agrupar_por: cliente)
Problema: 4 tools diferentes competem pelo mesmo gatilho. O LLM decide arbitrariamente.
Localização:
- relatorio_tools.py linha 1124 - gerar_relatorio_dinamico
- financeiro_reports_tools.py linha 104 - gerar_relatorio_ranking_clientes
- financeiro_tools.py linha 599 - gerar_relatorio_vendas
---
2. Conflito: "Faturamento"
Gatilho	Classificador	Tool provável
"faturamento"	FATURAMENTO	gerar_relatorio_dinamico (orcamentos)
"faturamento do mês"	GERAR_RELATORIO	gerar_relatorio_dinamico ou gerar_relatorio_vendas
Problema: A mesma intenção é tratada por classificadores diferentes dependendo da frase.
Localização: ai_intention_classifier.py linhas 132-141 vs 297-298
---
3. Conflito: "Serviços Mais Vendidos"
Gatilho	Tools que podem responder
"serviços mais vendidos"	gerar_relatorio_dinamico (domínio: servicos)
"o que mais vende"	gerar_relatorio_dinamico (domínio: orcamentos, agrupamento: servico)
"vendas por serviço"	gerar_relatorio_vendas (agrupar_por: servico)
Problema: 3 formas diferentes de obter o mesmo dado.
---
4. Conflito: "Contas a Receber" vs "Inadimplência"
Gatilho	Classificador	Resultado
"contas a receber"	CONTAS_RECEBER	Pendentes + vencidas
"contas vencidas"	INADIMPLENCIA	Apenas vencidas
"quem está devendo"	INADIMPLENCIA	Clientes devedores
Problema: "contas a receber vencidas" é ambíguo - pode cair em CONTAS_RECEBER (vem primeiro na ordem) ou INADIMPLENCIA.
Localização: ai_intention_classifier.py linhas 599-622
---
5. Conflito: "Relatório de Orçamentos" vs "Listar Orçamentos"
Gatilho	Classificador	Tool
"listar orçamentos"	LISTAR_ORCAMENTOS	listar_orcamentos (paginado)
"relatório de orçamentos"	GERAR_RELATORIO	gerar_relatorio_orcamentos ou gerar_relatorio_dinamico
"todos os orçamentos"	LISTAR_ORCAMENTOS	listar_orcamentos
Problema: gerar_relatorio_orcamentos e gerar_relatorio_dinamico (domínio: orcamentos) fazem quase a mesma coisa.
---
6. BUG: Ordem de Precedência do Classificador
No ai_intention_classifier.py, a ordem de verificação é:
1. SALDO_RAPIDO
2. GERAR_RELATORIO  ← Verificado ANTES de FATURAMENTO
3. OPERADOR
4. LISTAR_ORCAMENTOS
5. FATURAMENTO     ← Verificado DEPOIS de GERAR_RELATORIO
6. CONTAS_RECEBER
7. CONTAS_PAGAR
8. PREVISAO
9. INADIMPLENCIA
...
Problema: "/red" cai em GERAR_RELATORIO (tem regex para isso), mas "faturamento" sozinho cai em FATURAMENTO. Comportamento inconsistente.
---
7. BUG: Sobreposição de Descrições de Tools
gerar_relatorio_dinamico (relatorio_tools.py:1124):
> "Gera relatórios analíticos completos sobre qualquer área do negócio..."
gerar_relatorio_vendas (financeiro_tools.py:599):
> "Gera um relatório de vendas com base em orçamentos aprovados..."
gerar_relatorio_ranking_clientes (financeiro_reports_tools.py:104):
> "Gera um relatório com o ranking dos clientes por faturamento..."
Problema: As descrições não orientam claramente quando usar cada uma. O LLM não tem como saber que gerar_relatorio_dinamico (domínio: clientes) faz quase a mesma coisa que gerar_relatorio_ranking_clientes.
---
Causa Raiz Provável
1. Ferramentas redundantes foram criadas em momentos diferentes sem descontinuação das anteriores
2. Descrições não diferenciam claramente os casos de uso de cada tool
3. Classificador de intenção tem ordem de precedência que causa inconsistências
4. Ausência de "ownership" de gatilhos - múltiplas tools competem pelos mesmos comandos
---
Correção Mínima
Opção A: Consolidar Tools (Recomendado)
1. Descontinuar gerar_relatorio_vendas, gerar_relatorio_ranking_clientes, gerar_relatorio_contas_a_receber
2. Usar apenas gerar_relatorio_dinamico com domínios específicos
3. Atualizar descrições para tornar gerar_relatorio_dinamico a "tool canônica"
Opção B: Diferenciar Gatilhos (Menos Intrusivo)
Atualizar descrições das tools para guiar o LLM:
# gerar_relatorio_ranking_clientes
description=(
    "Use APENAS para ranking comparativo mês-atual vs mês-anterior. "
    "Para ranking simples por faturamento, use gerar_relatorio_dinamico."
)
# gerar_relatorio_vendas  
description=(
    "Use APENAS para relatório de vendas por período específico. "
    "Para análises gerais de faturamento, use gerar_relatorio_dinamico."
)
Opção C: Orquestrar no Classificador
No ai_intention_classifier.py, adicionar lógica para direcionar para a tool correta:
# Dentro de GERAR_RELATORIO, diferenciar por sub-padrões
if re.search(r'ranking.*cliente', mensagem_lower):
    # Direciona para gerar_relatorio_ranking_clientes
    ...
---
## Validação Rápida
1. Testar `"ranking de clientes"` 5 vezes e verificar qual tool é chamada
2. Testar `"faturamento do mês"` vs `"faturamento"` e comparar resultados
3. Verificar logs de `tool_trace` para identificar qual tool foi selecionada
---
Observações
- Risco de regressão: Consolidar tools pode quebrar código existente que espera as tools antigas
- Duplicação de código: _orcamentos em relatorio_tools.py e gerar_relatorio_orcamentos fazem queries similares
- Documentação: O arquivo docs/gatilhos.md reflete os gatilhos ideais, mas a implementação pode divergir
//////////////////////////Melhorias////////
1. Definir um "Contrato de Intenção": Criar um arquivo YAML simples que mapeia explicitamente gatilhos ("ranking de clientes") para a tool canônica (gerar_relatorio_dinamico). O teste de regressão deve ler este arquivo e validar seu cumprimento.
2.  Log Simples de Tool Calls: Começar com uma tabela tool_call_logs com (timestamp, user_id, session_id, tool_name, user_input) para iniciar a coleta de dados de telemetria com baixo esforço.