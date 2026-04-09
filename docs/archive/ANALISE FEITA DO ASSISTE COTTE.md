---
title: Analise Feita Do Assiste Cotte
tags:
  - analise
prioridade: alta
status: documentado
---
---
title: Analise Feita Do Assiste Cotte
tags:
  - analise
  - frontend
prioridade: alta
status: documentado
---
  Resumo das Alterações

  ETAPA 1 — Bloquear fallback de criação sem ID

  sistema/app/routers/orcamentos.py
  - Adicionado guarda acoes_operacionais antes do fallback de criação: se acao ∈ {VER, APROVAR, RECUSAR, ENVIAR,
  DESCONTO, ADICIONAR, REMOVER} e orc_id é null → retorna mensagem pedindo o número, nunca chama
  interpretar_mensagem para criar.

  sistema/app/routers/whatsapp.py
  - Mesma guarda: elif acao in {"VER", "APROVAR", "RECUSAR", "ENVIAR", "DESCONTO", "ADICIONAR", "REMOVER"} and not
  orc_id → enviar_mensagem_texto pedindo o número.
  - Bug pré-existente corrigido: adicionados elif acao == "APROVAR" and orc_id e elif acao == "RECUSAR" and orc_id
  que antes não existiam (causavam fallback para criar).
  - Adicionadas funções _aprovar_orcamento_via_bot e _recusar_orcamento_via_bot.

  ETAPA 2 — Sinônimos e extração de ID no prompt

  sistema/app/services/ia_service.py
  - SYSTEM_PROMPT_OPERADOR: adicionados "mostra" como sinônimo de VER; "aprovar orçamento 5", "ver orçamento 5",
  "envia o 5", "confirma 5" como exemplos; regra explícita: "aprovar" sozinho → orcamento_id=null (NUNCA criar;
  pedir o número).

  ETAPA 3 — Novas intenções financeiras

  sistema/app/services/ai_intention_classifier.py
  - Enum IntencaoUsuario: adicionados FATURAMENTO, CONTAS_RECEBER, CONTAS_PAGAR.
  - Novos padrões Regex: FATURAMENTO_KEYWORDS, CONTAS_RECEBER_KEYWORDS, CONTAS_PAGAR_KEYWORDS.
  - _classificar_regex: reordenado para verificar receber/pagar antes de classificar como SALDO; adicionadas
  verificações negativas (negar SALDO se mensagem contém "receber", "pagar", "faturamento").
  - Prompt do Haiku: atualizado com todas as novas categorias e regras de diferenciação.
  - Mapeamento INTENCAO_TO_FUNC: adicionados faturamento_ia, contas_receber_ia, contas_pagar_ia.

  sistema/app/services/cotte_ai_hub.py
  - Adicionadas 3 novas funções handler: faturamento_ia, contas_receber_ia, contas_pagar_ia — todas com consulta
  direta ao banco (sem IA), formatando respostas simples em português.


Contexto

 O assistente IA do COTTE possui falhas críticas de interpretação que geram falhas operacionais (aprovar sem ID
 cria orçamento) e respostas financeiramente incorretas (mistura saldo com faturamento). A correção exige mudanças
 pontuais no interpretar_comando_operador, no classificador Regex+Haiku, e nos fluxos de fallback do comando-bot e
 webhook WhatsApp.

 ---
 1. Resumo Executivo

 Os 5 maiores problemas

 1. Ação operacional sem ID cai em fallback de criação
   - "aprovar" ou "ver" sem número tenta criar orçamento com o texto digitado como serviço
   - Impacto: dados fantasma criados no banco; frustração do operador
   - Correção primeiro: nunca ir para CRIAR quando há intenção operacional sem ID
 2. "receber" e "pendente" não mapeados como inadimplência
   - "quanto tenho pra receber" → SALDO_RAPIDO (errado) ou CONVERSACAO
   - Impacto: usuário não encontra sua inadimplência; acha que sistema não tem
   - Correção: adicionar keywords específicas em INADIMPLENCIA
 3. Contexto temporal ausente em perguntas financeiras
   - "quanto entrou esse mês?" → trata como saldo geral, não filtra por período
   - Impacto: resposta imprecisa; usuário perde confiança
   - Correção: extrair referência temporal e passar para a função de consulta
 4. Fuzzy matching inexistente para erros de digitação
   - "caixaa", "sado", "resumoo" → CONVERSACAO
   - Impacto: usuário leigo erra muito; abandona o bot
   - Correção: verificar similaridade léxica antes de classificar como conversa
 5. Mistura conceitual: saldo × faturamento × a receber
   - saldo_rapido_ia usa valor_pago; "quanto entrou" não distingue entradas pagas de faturamento bruto
   - Impacto: gestor toma decisão com dado errado
   - Correção: separar os três conceitos nas respostas

 ---
 2. Priorização de Correções

 Prioridade Crítica

 ┌─────┬──────────────────────────────────────┬─────────────────────────────────┬─────────────────────┬───────┐
 │  #  │               Problema               │              Risco              │       Esforço       │ Ganho │
 ├─────┼──────────────────────────────────────┼─────────────────────────────────┼─────────────────────┼───────┤
 │ P1  │ Ação sem ID vai para fallback de     │ Dados fantasma criados;         │ Baixo (lógica       │ Alto  │
 │     │ criação                              │ operador perde confiança        │ condicional)        │       │
 ├─────┼──────────────────────────────────────┼─────────────────────────────────┼─────────────────────┼───────┤
 │ P2  │ "receber" não mapeado como           │ Usuário não encontra            │ Baixo (adicionar    │ Alto  │
 │     │ inadimplência                        │ informações de dívida           │ keywords)           │       │
 ├─────┼──────────────────────────────────────┼─────────────────────────────────┼─────────────────────┼───────┤
 │ P3  │ orcamento_id=null não dispara pedido │ Falha silenciosa                │ Baixo (nova         │ Alto  │
 │     │  de complemento                      │                                 │ condicional)        │       │
 └─────┴──────────────────────────────────────┴─────────────────────────────────┴─────────────────────┴───────┘

 Prioridade Alta

 ┌─────┬─────────────────────────────┬─────────────────────────────────┬──────────────────────────────┬───────┐
 │  #  │          Problema           │              Risco              │           Esforço            │ Ganho │
 ├─────┼─────────────────────────────┼─────────────────────────────────┼──────────────────────────────┼───────┤
 │ P4  │ Contexto temporal ausente   │ Resposta imprecisa              │ Médio (adicionar campo       │ Alto  │
 │     │                             │                                 │ periodo)                     │       │
 ├─────┼─────────────────────────────┼─────────────────────────────────┼──────────────────────────────┼───────┤
 │ P5  │ Fuzzy matching inexistente  │ Usuário leigo abandona bot      │ Médio (lib difflib)          │ Médio │
 ├─────┼─────────────────────────────┼─────────────────────────────────┼──────────────────────────────┼───────┤
 │ P6  │ "pendente" mal classificado │ Classe não localizada           │ Baixo (adicionar keywords)   │ Médio │
 ├─────┼─────────────────────────────┼─────────────────────────────────┼──────────────────────────────┼───────┤
 │ P7  │ "mostra" não mapeado como   │ Ação reconhecida mas não        │ Baixo (adicionar sinônimo)   │ Médio │
 │     │ VER                         │ executada                       │                              │       │
 └─────┴─────────────────────────────┴─────────────────────────────────┴──────────────────────────────┴───────┘

 Prioridade Média

 ┌─────┬─────────────────────────────────┬────────────────────────────┬────────────────────────────────┬───────┐
 │  #  │            Problema             │           Risco            │            Esforço             │ Ganho │
 ├─────┼─────────────────────────────────┼────────────────────────────┼────────────────────────────────┼───────┤
 │ P8  │ Separação                       │ Decisão gerencial com dado │ Médio (novos campos na         │ Alto  │
 │     │ saldo/faturamento/receber       │  errado                    │ resposta)                      │       │
 ├─────┼─────────────────────────────────┼────────────────────────────┼────────────────────────────────┼───────┤
 │ P9  │ Modo "curto" inexistente        │ Respostas longas para      │ Médio (parâmetro de estilo)    │ Médio │
 │     │                                 │ usuários leigos            │                                │       │
 ├─────┼─────────────────────────────────┼────────────────────────────┼────────────────────────────────┼───────┤
 │ P10 │ "aprovar orçamento 5" não       │ Funciona na prática mas    │ Baixo (regex mais forte)       │ Médio │
 │     │ extrai ID                       │ frágil                     │                                │       │
 ├─────┼─────────────────────────────────┼────────────────────────────┼────────────────────────────────┼───────┤
 │ P11 │ Gírias e abreviações não        │ "tb", "vc", "oq" →         │ Baixo (normalização            │ Baixo │
 │     │ tratadas                        │ confusão                   │ pré-classificação)             │       │
 └─────┴─────────────────────────────────┴────────────────────────────┴────────────────────────────────┴───────┘

 ---
 3. Regras Novas de Interpretação

 SALDO_CAIXA

 - Keywords: caixa, saldo, meu caixa, meu saldo, saldo atual, caixa atual, saldo de hoje, caixa hoje, valor em
 caixa, saldo do caixa, disponível, meu disponível, livre, meu livre, quanto tenho, caiu na conta, dinheiro em
 caixa
 - Negar: quanto tenho pra pagar, quanto tenho pra receber, faturamento, quanto entrou
 - Contexto temporal: se mencionar "hoje", "esse mês", "semana", extrair e passar como filtro

 FATURAMENTO

 - Keywords: faturamento, faturamos, quanto fatura, receita total, total faturado, vendas, total de vendas
 - Diferença de saldo: faturamento = soma de todos os orçamentos aprovados (pagos ou não); saldo = líquido em caixa
 - Resposta deve conter: valor bruto e distinguishing note

 CONTAS_RECEBER (em aberto)

 - Keywords: a receber, pra receber, tenho pra receber, receber, contas a receber, valor a receber
 - Diferença de saldo: é o total em aberto (vencido ou não); saldo é o que já entrou no caixa
 - Exige contexto: se não especificar cliente, listar todos; se especificar, filtrar

 CONTAS_PAGAR (em aberto)

 - Keywords: a pagar, pra pagar, tenho pra pagar, contas a pagar, quanto devo, parcelas
 - Similar à CONTAS_RECEBER: lista geral ou filtrada por cliente

 INADIMPLENCIA

 - Keywords: devendo, inadimplente, atrasado, atrasada, vencidas, contas vencidas, quem deve, clientes devendo,
 pendências, pendente (se junto com "cobrança" ou "cliente")
 - Diferença de CONTAS_RECEBER: inadimplência = vencido + não pago; contas a receber = todos os em aberto
 - Resposta: lista de clientes com valor e dias de atraso

 DASHBOARD_RESUMO

 - Keywords: resumo, painel, dashboard, panorama, situação, como estão, visao geral, visão geral
 - Resposta: KPIs principais em formato condensado (4-6 números)
 - Negar: se usuário pedir "só o principal" → max 3 números

 ORCAMENTO_VER

 - Keywords: ver, mostra, exibe, visualizar, detalhes, o orçamento
 - Sinônimos: "mostra o 5" = VER 5; "me mostra o orc 3" = VER 3
 - Sem ID: pedir "Qual orçamento? Digite: ver 5"

 ORCAMENTO_APROVAR

 - Keywords: aprovar, aprova, confirma, aceitar
 - Extração de ID: "aprovar orçamento 5" → ID=5; "aprovar" → null → pedir ID
 - Sem ID: nunca fallback para criar; pedir "Qual orçamento?"

 ORCAMENTO_RECUSAR

 - Keywords: recusar, recusa, reprovar, rejeitar, negar
 - Sem ID: pedir "Qual orçamento?"

 ORCAMENTO_ENVIAR

 - Keywords: envia, manda, enviar, mandar, mandou, enviei, mandou
 - Contexto: deve acompanhar ID; sem ID, pedir

 ORCAMENTO_CRIAR

 - Keywords: nome de serviço + valor + "para/de" + nome de cliente
 - Exemplo: "pintura 800 para joão", "cabelo 150 pra maria"
 - Regras: só ativa quando há pelo menos serviço E valor E (cliente ou "A definir")
 - Confiança baixa: não criar; pedir mais informações

 ANALISE_CONVERSAO

 - Keywords: ticket médio, ticket medio, taxa de aprovação, mais vendido, serviço mais, conversão, aprovados,
 recusados
 - Resposta: métricas com contexto comparativo

 PREVISAO_CAIXA

 - Keywords: previsão, projeção, fluxo de caixa, caixa futuro, quanto vou, próximos dias, próximas semanas, vou
 receber, vou pagar
 - Diferença de SALDO_CAIXA: projeção é futuro; saldo é atual

 AJUDA

 - Keywords: ajuda, help, comandos, o que você faz, como funciona
 - Resposta: lista de 5-7 comandos mais comuns

 CONVERSA

 - Keywords: saudações, off-topic, gírias, mensagens que não casam com nenhuma regra acima
 - Regra: nunca executar ação; sempre responder com algo útil ou pedir contexto

 ---
 4. Fluxos de Fallback Corretos

 Fluxo A: Ação identificada, ID ausente

 Usuário: "aprovar"
   → Classifica como APROVAR, orcamento_id=null
   → Verifica: acao ≠ DESCONHECIDO E orcamento_id is null
   → RESPOSTA: "Para aprovar um orçamento preciso do número. "
               "Exemplo: 'aprovar 5' (para o orçamento ORC-5)"
   → NÃO vai para fallback de criar

 Usuário: "ver"
   → Mesmo fluxo
   → RESPOSTA: "Qual orçamento você quer ver? Digite: ver 5"

 Usuário: "aprovar orçamento"
   → Classifica como APROVAR, orcamento_id=null
   → RESPOSTA: "Qual orçamento você quer aprovar? "
               "Digite: 'aprovar 5' para o orçamento ORC-5"

 Fluxo B: Frase ambígua

 Usuário: "quanto tenho pra receber"
   → Classifica como SALDO_RAPIDO (pela keyword "quanto tenho")
   → detecta palavra "receber"
   → UPGRADE para CONTAS_RECEBER
   → RESPOSTA: "Você tem R$ X a receber, sendo R$ Y vencidos."
               "(Não mostra saldo de caixa)"

 Usuário: "resumo"
   → Classifica como DASHBOARD_RESUMO
   → RESPOSTA: "📊 Resumo do mês: Entradas R$ X | Saídas R$ Y "
               "| A receber R$ Z | Saldo R$ W"

 Usuário: "tá como"
   → Classifica como CONVERSA (sem match Regex)
   → Haiku tenta classificar
   → Se CONVERSA: "Não entendi. Digite 'ajuda' para ver comandos disponíveis"

 Fluxo C: Mensagem muito curta

 Usuário: "ca"
   → Comprimento < 4
   → fuzzy_match com whitelist [caixa, saldo, ver, enviar, aprovar, ajuda]
   → fuzzy_match encontra "caixa" (distância 1)
   → Classifica como SALDO_RAPIDO

 Usuário: "x"
   → fuzzy_match não encontra nenhum match próximo
   → CONVERSA: "Não entendi. Digite 'ajuda' para ver os comandos."

 Fluxo D: Erro de digitação

 Usuário: "caixaa"
   → Regex SALDO_RAPIDO não bate
   → fuzzy_match("caixaa", whitelist) → "caixa" (dist=1)
   → SALDO_RAPIDO

 Usuário: "saldoo"
   → fuzzy_match("saldoo") → "saldo" (dist=1)
   → SALDO_RAPIDO

 Usuário: "aprovarr"
   → fuzzy_match("aprovarr") → "aprovar" (dist=1)
   → ORCAMENTO_APROVAR
   → ID=null → pede "Qual orçamento?"

 Fluxo E: Ação não executável

 Usuário: "faz um pix pra mim"
   → Classifica como CONVERSA (nenhuma ação bate)
   → RESPOSTA: "Não consigo fazer transferências. "
               "Posso te ajudar com saldo, orçamentos ou finanças?"

 Usuário: "apaga tudo"
   → CONVERSA
   → RESPOSTA: "Não tenho acesso para excluir dados. "
               "Entre em contato com o suporte se precisar de ajuda."

 Usuário: "mostra meus dados"
   → CONVERSA
   → RESPOSTA: "Posso mostrar saldo, finanças, orçamentos ou clientes. "
               "O que você precisa?"

 Fluxo F: Financeiro sem período

 Usuário: "quanto entrou"
   → SALDO_RAPIDO
   → detecta ausência de período
   → Filtra: mês atual
   → RESPOSTA: "Neste mês entraram R$ X em caixa. "
               "(Se quiser outro período, me diga: 'quanto entrou em fevereiro')"

 Usuário: "faturamento"
   → FATURAMENTO
   → Sem período → mês atual
   → RESPOSTA: "Faturamento este mês: R$ X "
               "(orçamentos aprovados, independente do pagamento)"

 ---
 5. Especificação Funcional para o Desenvolvedor

 5.1 Entradas

 mensagem: string (1-500 caracteres, sanitizada por parry)
 empresa_id: int (do contexto de autenticação)
 db: Session (conexão ativa)

 5.2 Pré-processamento

 1. Sanitizar mensagem (parry: 500 char limit, controle chars, injection patterns)
 2. Normalizar: lowercase, collapse spaces, remover acentos
 3. Verificar tamanho:
    - < 4 chars: fuzzy_match com whitelist de comandos; se não encontrar → CONVERSA
    - >= 4 chars: seguir fluxo normal
 4. Verificar se é saudação off-topic: fuzzy_match com ["oi", "ola", "bom dia", "boa tarde"]
    → se match E não contém outras keywords → CONVERSA (saudacao)

 5.3 Classificação de Intenção

 Ordem de avaliação (primeiro match vence):

 1. VER          → ["ver", "mostra", "exibe", "visualizar"] + número
 2. APROVAR      → ["aprovar", "aprova", "confirma", "aceitar"] + número
 3. RECUSAR      → ["recusar", "recusa", "reprovar", "rejeitar"] + número
 4. ENVIAR       → ["envia", "manda", "enviar", "mandar"] + número
 5. DESCONTO     → ["desconto", "%", "por cento"] + número
 6. ADICIONAR    → ["adiciona", "coloca", "adicionar"] + texto + número
 7. REMOVER      → ["remove", "tira", "remover"] + "item" + número
 8. SALDO_CAIXA  → ["caixa", "saldo", "disponível", "livre", "caiu"] + (não "receber", não "pagar")
 9. FATURAMENTO  → ["faturamento", "faturamos", "vendas", "total de vendas"]
 10. CONTAS_RECEBER → ["receber", "a receber", "pra receber"] (com ou sem + "tenho", "quanto")
 11. CONTAS_PAGAR  → ["a pagar", "pra pagar", "tenho pra pagar"]
 12. INADIMPLENCIA → ["devendo", "atrasado", "vencida", "inadimplente", "pendência"]
 13. DASHBOARD_RESUMO → ["resumo", "dashboard", "painel", "panorama", "situação"]
 14. ANALISE_CONVERSAO → ["ticket", "conversão", "mais vendido", "aprovados", "recusados"]
 15. PREVISAO_CAIXA → ["previsão", "projeção", "fluxo", "futuro", "vou receber", "vou pagar"]
 16. AJUDA        → ["ajuda", "help", "comandos"]
 17. CONVERSA     → fallback (nenhuma das anteriores)

 5.4 Extração de ID do Orçamento

 Padrões aceitos para extrair ID:
   - "ver 5"               → extrai 5
   - "ver o 5"             → extrai 5
   - "ver orc 5"           → extrai 5
   - "ver orçamento 5"     → extrai 5
   - "aprovar orçamento 5" → extrai 5
   - "aprovar o orcamento 5" → extrai 5
   - "#5"                  → extrai 5

 Se nenhuma extração possível → orcamento_id = null

 5.5 Validações Obrigatórias

 1. AÇÃO operacional (VER/APROVAR/RECUSAR/ENVIAR) + orcamento_id null
    → NÃO executar; retornar mensagem de pedido de ID

 2. AÇÃO = CRIAR + confianca < 0.5 + sem serviço E sem valor
    → retornar mensagem de ajuda: "Para criar um orçamento, diga: "
      "'pintura 800 para João'"

 3. Mensagem contém "ignora" ou "desconsidera" (parry já limpa, mas redundância)
    → classificar como CONVERSA; nunca executar ação

 4. Ação DESTROY (não existe ainda, mas se criar: RECUSAR não é destroy)
    → SEMPRE exigir confirmação antes de executar

 5. Valor negativo em DESCONTO
    → rejeitar: "O desconto precisa ser um valor positivo"

 5.6 Quando Perguntar Complemento

 CRÍTICO — sempre perguntar (nunca adivinhar):
   - APROVAR + orc_id=null
   - RECUSAR + orc_id=null
   - VER + orc_id=null
   - ENVIAR + orc_id=null
   - DESCONTO + orc_id=null
   - ADICIONAR + orc_id=null
   - REMOVER + orc_id=null

 OPCIONAL — inferir se possível:
   - Período temporal ausente → assumir mês atual, mencionar na resposta
   - Cliente não especificado em criar → "A definir" + perguntar "Qual o nome do cliente?"
   - Valor não especificado em criar → usar preço do catálogo se existir; senão perguntar

 NUNCA perguntar:
   - SALDO_CAIXA (resposta direta)
   - FATURAMENTO (resposta direta com filtro de período)
   - CONTAS_RECEBER (pode listar todos se não especificar)
   - DASHBOARD_RESUMO (resposta direta)
   - AJUDA (lista direta)
   - CONVERSA (resposta genérica)

 5.7 Quando Responder Direto

 - SALDO_CAIXA: R$ X em caixa
 - FATURAMENTO: R$ X faturamento no período |orçamentos aprovados|
 - CONTAS_RECEBER: R$ X a receber (Y vencido)
 - CONTAS_PAGAR: R$ X a pagar
 - INADIMPLENCIA: lista de clientes + valores + dias
 - DASHBOARD_RESUMO: 4 KPIs condensados
 - ANALISE_CONVERSAO: ticket médio, top serviço, taxa aprovação
 - PREVISAO_CAIXA: projeção 30 dias
 - AJUDA: lista de comandos
 - CONVERSA: resposta empática curta (máx 1-2 frases)

 5.8 Quando Nunca Cair em Fallback de Criação

 REGRA ABSOLUTA:
 if acao in [VER, APROVAR, RECUSAR, ENVIAR, DESCONTO, ADICIONAR, REMOVER]:
     if orcamento_id is null:
         return mensagem_de_pedido_de_id  # NUNCA chamar interpretar_mensagem/CRIAR

 Só vai para CRIAR quando:
   1. acao = CRIAR (explicitamente identificada)
   2. acao = DESCONHECIDO E mensagem contém pelo menos:
      - um valor numérico OU nome de serviço reconhecível
      - um nome que pareça um cliente

 ---
 6. Tabela de Intenções Melhorada

 Intenção: SALDO_CAIXA
 Exemplos válidos: "caixa", "meu saldo", "quanto tenho em caixa", "caiu na conta"
 Exemplos ambíguos: "caixa" sozinho pode ser SALDO ou DASHBOARD (contexto)
 Resposta ideal: "R$ X em caixa hoje"
 Dados necessários: nenhum (busca direta)
 Risco de erro: Médio: "caixa" com intent implícita
 Fallback: DASHBOARD se contexto amplia
 ────────────────────────────────────────
 Intenção: FATURAMENTO
 Exemplos válidos: "faturamento", "quanto fatura", "total de vendas", "vendas"
 Exemplos ambíguos: "vendas" sozinho pode ser ANALISE_CONVERSAO
 Resposta ideal: "R$ X faturados [período]"
 Dados necessários: período (default: mês atual)
 Risco de erro: Alto: usuário quer vendas vs saída
 Fallback: SALDO_CAIXA se "vendas" sozinho
 ────────────────────────────────────────
 Intenção: CONTAS_RECEBER
 Exemplos válidos: "quanto tenho pra receber", "a receber", "tenho a receber"
 Exemplos ambíguos: "receber" sozinho é ambíguo com SALDO_CAIXA
 Resposta ideal: "R$ X a receber [Y vencidos]"
 Dados necessários: nenhum (lista todos)
 Risco de erro: Alto: "receber" sem "tenho" classifica errado
 Fallback: SALDO_CAIXA
 ────────────────────────────────────────
 Intenção: CONTAS_PAGAR
 Exemplos válidos: "quanto tenho pra pagar", "a pagar", "tenho a pagar"
 Exemplos ambíguos: "pagar" sozinho é muito genérico
 Resposta ideal: "R$ X a pagar"
 Dados necessários: nenhum
 Risco de erro: Médio
 Fallback: não classifica errado facilmente
 ────────────────────────────────────────
 Intenção: INADIMPLENCIA
 Exemplos válidos: "quem tá devendo", "clientes inadimplentes", "contas vencidas", "pendências"
 Exemplos ambíguos: "pendente" sozinho pode ser CONVERSA
 Resposta ideal: Lista: Cliente + Valor + Dias atraso
 Dados necessários: nenhum
 Risco de erro: Baixo: keywords claras
 Fallback: CONTAS_RECEBER
 ────────────────────────────────────────
 Intenção: DASHBOARD_RESUMO
 Exemplos válidos: "resumo", "dashboard", "panorama", "situação", "visao geral"
 Exemplos ambíguos: "resumo" sozinho pode conflitar com "mostra resumo de X"
 Resposta ideal: 4 KPIs condensados
 Dados necessários: nenhum
 Risco de erro: Médio: pode ser longo demais
 Fallback: SALDO_CAIXA (se "resumo de caixa")
 ────────────────────────────────────────
 Intenção: ORCAMENTO_VER
 Exemplos válidos: "ver 5", "mostra o 5", "detalhes do orc 3"
 Exemplos ambíguos: "mostra" sem número
 Resposta ideal: Detalhes: itens, total, status
 Dados necessários: orcamento_id
 Risco de erro: Baixo: ID obrigatório
 Fallback: Pedir ID
 ────────────────────────────────────────
 Intenção: ORCAMENTO_APROVAR
 Exemplos válidos: "aprovar 5", "aprovar orc 3", "confirma 5"
 Exemplos ambíguos: "aprovar" sem número
 Resposta ideal: Confirmação + criação contas
 Dados necessários: orcamento_id
 Risco de erro: Crítico: ID obrigatório
 Fallback: Pedir ID (NUNCA criar)
 ────────────────────────────────────────
 Intenção: ORCAMENTO_RECUSAR
 Exemplos válidos: "recusar 5", "recusa o 3"
 Exemplos ambíguos: "recusar" sem número
 Resposta ideal: Confirmação
 Dados necessários: orcamento_id
 Risco de erro: Crítico: ID obrigatório
 Fallback: Pedir ID (NUNCA criar)
 ────────────────────────────────────────
 Intenção: ORCAMENTO_ENVIAR
 Exemplos válidos: "envia o 5", "manda o 3 pro cliente"
 Exemplos ambíguos: "envia" sem número
 Resposta ideal: Confirma envio WhatsApp
 Dados necessários: orcamento_id
 Risco de erro: Médio
 Fallback: Pedir ID
 ────────────────────────────────────────
 Intenção: ORCAMENTO_CRIAR
 Exemplos válidos: "pintura 800 para joão", "corte 150 pra maria"
 Exemplos ambíguos: "pintura" (sem valor) ou "joão" sozinho
 Resposta ideal: Confirmação do orçamento criado
 Dados necessários: cliente + serviço + valor
 Risco de erro: Alto: confiança baixa sem valor
 Fallback: Pedir mais informações
 ────────────────────────────────────────
 Intenção: ANALISE_CONVERSAO
 Exemplos válidos: "ticket médio", "taxa aprovação", "mais vendido", "serviço mais vendido"
 Exemplos ambíguos: "aprovados" pode ser orçamento
 Resposta ideal: Ticket R$ X
 Dados necessários: nenhum
 Risco de erro: Baixo: keywords específicas
 Fallback: não confunde facilmente
 ────────────────────────────────────────
 Intenção: PREVISAO_CAIXA
 Exemplos válidos: "previsão de caixa", "quanto vou receber", "próximos 30 dias"
 Exemplos ambíguos: "caixa" sozinho
 Resposta ideal: Projeção entrada/saída
 Dados necessários: nenhum
 Risco de erro: Baixo: prefixos claros
 Fallback: SALDO_CAIXA
 ────────────────────────────────────────
 Intenção: AJUDA
 Exemplos válidos: "ajuda", "comandos", "o que você faz", "help"
 Exemplos ambíguos: "ajuda" com contexto parcial
 Resposta ideal: Lista de 7 comandos mais úteis
 Dados necessários: nenhum
 Risco de erro: Baixo
 Fallback: não aplica
 ────────────────────────────────────────
 Intenção: CONVERSA
 Exemplos válidos: "oi", "bom dia", "obrigado", "xpto", gírias, off-topic
 Exemplos ambíguos: qualquer coisa que não casou acima
 Resposta ideal: Resposta empática curta (max 2 frases)
 Dados necessários: nenhum
 Risco de erro: Alto: pode ser intenção real perdida
 Fallback: dar resposta útil + ajuda

 ---
 7. Prompt do Classificador — Versão Produção

 # CLASSIFICADOR DE INTENÇÃO — COTTE ASSISTANT v3

 ## REGRAS FUNDAMENTAIS

 1. Você é um classificador de mensagens de operadores de pequenas empresas brasileiras.
 2. Retorne APENAS JSON válido: {"intencao":"NOME","confianca":0.0,"orcamento_id":null,"periodo":null,"valor":null,
 "desconto_tipo":"percentual","descricao":null,"num_item":null}
 3. NUNCA invente intenções fora da lista oficial.
 4. Se a mensagem for uma saudação ou off-topic, retorne CONVERSA com confianca alta.
 5. Quando acao for VER/APROVAR/RECUSAR/ENVIAR e não houver número → orcamento_id=null (não tente extrair do
 texto).
 6. Quando periodo for mencionado ("janeiro", "mês passado", "março/26"), capture em "periodo": "janeiro 2026".
 7. Valor: ponto decimal. "800", "800 reais", "800,00" → 800.0.
 8. Confianca: 0.0 a 1.0. Reduza se a mensagem for ambígua ou muito curta.

 ## INTENÇÕES DISPONÍVEIS

 SALDO_CAIXA: perguntas diretas sobre quanto há em caixa ou disponível.
   → "caixa", "saldo", "meu saldo", "meu caixa", "saldo atual", "caixa atual",
     "valor em caixa", "disponível", "livre", "meu livre", "quanto tenho",
     "caiu na conta", "caiu na minha conta", "dinheiro em caixa",
     "saldo de hoje", "caixa de hoje", "meu disponível"
   → NEGAR se conter: "receber", "pagar", "faturamento", "vendas", "entrada", "saída"

 FATURAMENTO: total de receitas de orçamentos aprovados.
   → "faturamento", "quanto fatura", "total faturado", "faturamos",
     "total de vendas", "receita total", "quanto vendemos"

 CONTAS_RECEBER: valores em aberto a receber de clientes.
   → "a receber", "pra receber", "tenho pra receber", "tenho a receber",
     "quanto tenho a receber", "contas a receber", "valor a receber"
   → Diferente de SALDO_CAIXA: é o que ainda NÃO entrou no caixa.

 CONTAS_PAGAR: valores em aberto a pagar.
   → "a pagar", "pra pagar", "tenho pra pagar", "contas a pagar",
     "quanto tenho a pagar", "valor a pagar", "parcelas a pagar"

 INADIMPLENCIA: clientes atrasados ou inadimplentes.
   → "devendo", "inadimplente", "atrasado", "atrasada", "vencidas",
     "contas vencidas", "quem deve", "clientes devendo", "pendências",
     "pendente" (se junto com "cobrança" ou "cliente")
   → Se não especificar cliente: listar todos os inadimplentes.

 DASHBOARD_RESUMO: pedido de visão geral condensada.
   → "resumo", "dashboard", "painel", "panorama", "visao geral",
     "visão geral", "situação", "como estão", "como tá"

 ORCAMENTO_VER: ver detalhes de um orçamento específico.
   → "ver 5", "mostra 5", "exibe 3", "detalhes do orc 2",
     "ver o orçamento 5", "me mostra o 3"
   → Sinônimos de "ver": mostra, exibe, visualizar, detalhes
   → ID obrigatório: se ausente → orcamento_id=null

 ORCAMENTO_APROVAR: aprovar um orçamento.
   → "aprovar 5", "aprova o 3", "confirma 5", "aceitar orcamento 2"
   → ID obrigatório: se ausente → orcamento_id=null
   → NUNCA tente criar orçamento a partir do texto.

 ORCAMENTO_RECUSAR: recusar um orçamento.
   → "recusar 5", "recusa o 3", "reprovar 2", "rejeitar orcamento 5"
   → ID obrigatório: se ausente → orcamento_id=null

 ORCAMENTO_ENVIAR: enviar orçamento por WhatsApp.
   → "envia o 5", "manda o 3", "enviar 2", "mandar o orçamento 5"
   → ID obrigatório: se ausente → orcamento_id=null

 ORCAMENTO_CRIAR: criar novo orçamento a partir de descrição.
   → "pintura 800 para joão", "corte 150 pra maria", "orçamento de formatura 1500"
   → REGRAS: deve ter pelo menos serviço + valor (numérico)
   → Se valor ausente E sem match de catálogo → confianca ≤ 0.4
   → Se serviço ausente → confianca ≤ 0.3

 DESCONTO: aplicar desconto em orçamento existente.
   → "10% no 5", "50 reais de desconto no 3", "desconto 15% no orc 2"
   → valor: número | desconto_tipo: "percentual" ou "fixo"
   → ID obrigatório

 ADICIONAR_ITEM: adicionar item a orçamento existente.
   → "adiciona pintura 200 no 3", "coloca limpeza 150 no orc 2"
   → REQUER: orcamento_id + descricao + valor

 REMOVER_ITEM: remover item de orçamento existente.
   → "remove item 2 do 5", "tira o item 1 do orçamento 3"
   → REQUER: orcamento_id + num_item

 ANALISE_CONVERSAO: métricas de vendas e conversão.
   → "ticket médio", "ticket medio", "taxa de aprovação", "mais vendido",
     "serviço mais vendido", "conversão", "aprovados", "recusados",
     "taxa de conversão", "ranking de vendas"

 PREVISAO_CAIXA: projeção de fluxo futuro.
   → "previsão de caixa", "projeção", "fluxo de caixa", "caixa futuro",
     "quanto vou receber", "próximos 30 dias", "próximas semanas",
     "vou pagar", "previsão financeira"

 AJUDA: listar comandos disponíveis.
   → "ajuda", "help", "comandos", "o que você faz", "como funciona",
     "me ajuda"

 CONVERSA: saudação, off-topic, gíria, ou texto que não se encaixa em nenhuma intenção.
   → "oi", "olá", "bom dia", "boa tarde", "obrigado", "tchau",
     "xpto", "oi?", "tudo bem", "blz"
   → Se não souber classificar → CONVERSA
   → NUNCA tente executar ação operacional a partir de CONVERSA

 ## REGRAS DE CLASSIFICAÇÃO

 A) 먼저 verifique se há número de orçamento na mensagem (1-3 dígitos):
    → Se encontrar E a mensagem contém VER/APROVAR/RECUSAR/ENVIAR/DESCONTO → extraia o número

 B) Se mensagem contém "caixa" ou "saldo":
    → Se também contém "receber" → CONTAS_RECEBER
    → Se também contém "pagar" → CONTAS_PAGAR
    → Se também contém "faturamento" ou "vendas" → FATURAMENTO
    → Caso contrário → SALDO_CAIXA

 C) Se mensagem contém "devendo", "atrasado", "vencida" → INADIMPLENCIA

 D) Se mensagem contém "resumo", "dashboard", "panorama" → DASHBOARD_RESUMO

 E) Se mensagem contém "ticket", "conversão", "mais vendido" → ANALISE_CONVERSAO

 F) Se mensagem contém "previsão", "projeção", "futuro", "vou receber" → PREVISAO_CAIXA

 G) Se nenhuma das anteriores E parece ser criação de orçamento:
    → ORCAMENTO_CRIAR se tiver valor numérico E (cliente ou serviço)
    → CONVERSA caso contrário

 H) Se saudação ou off-topic → CONVERSA

 ## EXTRAS

 - Erros de digitação comuns: normalizar antes de classificar
   (ex: "caixaa" → "caixa"; "saldoo" → "saldo")
 - Gírias: "tb" → "também"; "vc" → "você"; "oq" → "o que"
 - Números por extenso: "cem" → 100; "oitocentos" → 800
 - Monotone: temperature=0 para resultado determinístico

 ---
 8. Casos de Teste Finais de Aceitação

 ┌─────┬─────────────────────┬──────────────────────────┬─────────────────────────────────┬───────────────────┐
 │  #  │      Mensagem       │     Intenção correta     │        Resposta esperada        │    Observação     │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 1   │ caixa               │ SALDO_CAIXA              │ "R$ X em caixa"                 │ Funciona via      │
 │     │                     │                          │                                 │ Regex             │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 2   │ meu saldo           │ SALDO_CAIXA              │ "R$ X em caixa"                 │ Regex cobre       │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 3   │ quanto tenho em     │ SALDO_CAIXA              │ "R$ X em caixa"                 │ Contexto direto   │
 │     │ caixa               │                          │                                 │                   │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 4   │ caixaa              │ SALDO_CAIXA              │ "R$ X em caixa"                 │ Fuzzy corrige     │
 │     │                     │                          │                                 │ erro              │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 5   │ disponivel          │ SALDO_CAIXA              │ "R$ X disponível"               │ Mapeado           │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 6   │ quanto tenho pra    │ CONTAS_RECEBER           │ "R$ X a receber, R$ Y vencidos" │ Palavra "receber" │
 │     │ receber             │                          │                                 │                   │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 7   │ a receber           │ CONTAS_RECEBER           │ "R$ X a receber"                │ Keyword           │
 │     │                     │                          │                                 │ específica        │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 8   │ contas vencidas     │ INADIMPLENCIA            │ Lista de inadimplentes          │ Keyword clara     │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 9   │ quem tá devendo     │ INADIMPLENCIA            │ Lista de devedores              │ Expressão comum   │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 10  │ pendências          │ INADIMPLENCIA            │ Lista de pendências             │ Keyword mapeada   │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 11  │ faturamento         │ FATURAMENTO              │ "R$ X faturados este mês"       │ Distinto de saldo │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 12  │ quanto fatura       │ FATURAMENTO              │ "R$ X faturados"                │ Mapeado           │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 13  │ resumo              │ DASHBOARD_RESUMO         │ 4 KPIs condensados              │ Contexto direto   │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 14  │ dashboard           │ DASHBOARD_RESUMO         │ KPIs principais                 │ Mapeado           │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 15  │ ver 5               │ ORCAMENTO_VER            │ Detalhes ORC-5                  │ ID extraído       │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 16  │ mostra o 5          │ ORCAMENTO_VER            │ Detalhes ORC-5                  │ "mostra" = ver    │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 17  │ ver                 │ ORCAMENTO_VER (sem ID)   │ "Qual orçamento? Digite: ver 5" │ ID ausente, pedir │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 18  │ aprovar 5           │ ORCAMENTO_APROVAR        │ Confirmação aprovação           │ ID extraído       │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 19  │ aprovar             │ ORCAMENTO_APROVAR (sem   │ "Qual orçamento? Digite:        │ NUNCA criar       │
 │     │                     │ ID)                      │ aprovar 5"                      │                   │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 20  │ aprovar orçamento 5 │ ORCAMENTO_APROVAR        │ Confirmação aprovação           │ ID extraído do    │
 │     │                     │                          │                                 │ texto             │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 21  │ recusar 5           │ ORCAMENTO_RECUSAR        │ Confirmação recusa              │ ID extraído       │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 22  │ recusar             │ ORCAMENTO_RECUSAR (sem   │ "Qual orçamento? Digite:        │ NUNCA criar       │
 │     │                     │ ID)                      │ recusar 5"                      │                   │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 23  │ envia o 5           │ ORCAMENTO_ENVIAR         │ Confirma envio WhatsApp         │ ID extraído       │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 24  │ envia               │ ORCAMENTO_ENVIAR (sem    │ "Qual orçamento? Digite: envia  │ ID ausente, pedir │
 │     │                     │ ID)                      │ 5"                              │                   │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 25  │ pintura 800 para    │ ORCAMENTO_CRIAR          │ Confirmação criação             │ Com ID de cliente │
 │     │ joão                │                          │                                 │                   │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 26  │ pintura             │ ORCAMENTO_CRIAR (baixa   │ "Para criar, diga: pintura 800  │ Valor ausente     │
 │     │                     │ conf)                    │ para João"                      │                   │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 27  │ ticket médio        │ ANALISE_CONVERSAO        │ Ticket R$ X                     │ Métrica           │
 │     │                     │                          │                                 │ específica        │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 28  │ previsão de caixa   │ PREVISAO_CAIXA           │ Projeção 30 dias                │ Prefix claro      │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 29  │ ajuda               │ AJUDA                    │ Lista de comandos               │ Mapeado           │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 30  │ oi tudo bem         │ CONVERSA                 │ Resposta empática curta         │ Saudação, não     │
 │     │                     │                          │                                 │ executar          │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 31  │ 10% no 5            │ DESCONTO                 │ Desconto aplicado ORC-5         │ ID extraído       │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 32  │ caiu na conta       │ SALDO_CAIXA              │ "Entradas recentes: R$ X"       │ Keyword mapeada   │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 33  │ vendas              │ FATURAMENTO              │ "R$ X em vendas este mês"       │ Ambíguo mas       │
 │     │                     │                          │                                 │ aceito            │
 ├─────┼─────────────────────┼──────────────────────────┼─────────────────────────────────┼───────────────────┤
 │ 34  │ o que tenho         │ SALDO_CAIXA              │ "R$ X em caixa"                 │ Genérico, mas     │
 │     │                     │                          │                                 │ direto            │
 └─────┴─────────────────────┴──────────────────────────┴─────────────────────────────────┴───────────────────┘

 ---
 Arquivos Críticos a Modificar

 ┌──────────────────────────────────────────────────────┬──────────────────────────────────────────────────────┐
 │                       Arquivo                        │                       Mudança                        │
 ├──────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ sistema/app/services/ia_service.py                   │ Adicionar sinônimos no SYSTEM_PROMPT_OPERADOR        │
 │                                                      │ (mostra→VER, "receber"→INADIMPLENCIA)                │
 ├──────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │                                                      │ Adicionar CONTAS_RECEBER, CONTAS_PAGAR, FATURAMENTO  │
 │ sistema/app/services/ai_intention_classifier.py      │ como intenções; adicionar fuzzy matching; reordenar  │
 │                                                      │ regras de classificação                              │
 ├──────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ sistema/app/services/ai_intention_classifier.py      │ Separar FATURAMENTO de SALDO; CONTAS_RECEBER como    │
 │ (saldo_rapido_ia)                                    │ intenção própria                                     │
 ├──────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ sistema/app/routers/orcamentos.py (comando-bot)      │ Impedir fallback de criação quando ação operacional  │
 │                                                      │ sem ID                                               │
 ├──────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ sistema/app/routers/whatsapp.py                      │ Mesmo fluxo de fallback do comando-bot               │
 ├──────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ sistema/app/services/cotte_ai_hub.py                 │ Adicionar handlers para CONTAS_RECEBER,              │
 │                                                      │ CONTAS_PAGAR, FATURAMENTO                            │
 └──────────────────────────────────────────────────────┴──────────────────────────────────────────────────────┘

 Verificação

 1. Rodar pytest em sistema/tests/test_webhook_whatsapp.py e sistema/tests/
 2. Testar os 34 casos deaceitação manualmente via endpoint /orcamentos/comando-bot
 3. Verificar que "aprovar" retorna mensagem de pedido de ID (não tenta criar orçamento)
 4. Verificar que "receber" classifica como CONTAS_RECEBER, não SALDO_CAIXA
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌

 Claude has written up a plan and is ready to execute. Would you like to proceed?

 ❯ 1. Yes, clear context (5% used) and auto-accept edits (shift+tab)
   2. Yes, auto-accept edits
   3. Yes, manually approve edits
   4. Type here to tell Claude what to change