//////verificar se foi feito/////
Melhorias Essenciais
1. Persistência de Memória Semântica: Em vez da Regex tentar adivinhar a frase sozinha, colocar um contexto no prompt do LLM: "Você é um assistente operacional universal, suas instruções da empresa são {instrucoes}. Se precisar de dados analíticos, faça queries SQL". Isso devolve o "cérebro" de volta à IA.
2. Reconhecimento de Prompts Direto no Frontend: O Frontend já manda o ID do prompt para usar. A chamada /usar deveria sinalizar ao backend de que esta é uma Macro Ação de Empresa, ativando automaticamente o fluxo de "Alta Capacidade Analítica".
///////////////////



6. Ideias Inovadoras
1. Guardrails Proativos (Anti-Delírio Baseado nas Instruções): Utilizar as próprias instrucoes_empresa no validador de saída do assistente. Se o administrador da empresa configurar "Não prometer prazos abaixo de 24h", o validador irá checar as promessas da IA antes de exibi-las na tela.
2. Dashboard Visual Flexível: Ao permitir que o formato preferido ("tabela" vs "resumo") seja entendido pela IA, a IA pode instruir o assistente-ia-render.js a trocar de Layout via capability dinamicamente, em vez de fixar um output só.