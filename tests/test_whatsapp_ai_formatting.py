
import asyncio
import json
import os
import sys
from unittest.mock import MagicMock, AsyncMock
from decimal import Decimal

# Adicionar caminhos
sys.path.append(os.path.abspath("sistema"))
sys.path.append(os.path.abspath("."))

# Mock global para evitar quebras em ferramentas reais durante o teste de formatacao
from app.models.models import Usuario, Empresa, Cliente, SaldoCaixaConfig, Orcamento

async def simulate_whatsapp_full_flow():
    print("📱 AUDITORIA DE EXIBIÇÃO WHATSAPP (v2.1)\n")
    
    db = MagicMock()
    
    # Mock do Usuário Real
    mock_user = MagicMock(spec=Usuario)
    mock_user.id = 1
    mock_user.empresa_id = 1
    mock_user.is_gestor = True
    mock_user.permissoes = {"financeiro": "total"}
    mock_user.nome = "Gerson"
    
    # Mock da Empresa
    mock_empresa = MagicMock(spec=Empresa)
    mock_empresa.id = 1
    mock_empresa.empresa_id = 1
    mock_empresa.nome = "Empresa de Teste"
    
    # Configuração do Mock do DB (Evitando erros de literal SQL no Mock)
    def db_query_side_effect(model):
        q = MagicMock()
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.offset.return_value = q
        q.join.return_value = q
        
        # Simula retorno de dados para não vir vazio
        if model == Usuario:
            q.first.return_value = mock_user
        elif model == SaldoCaixaConfig:
            config = MagicMock()
            config.saldo_inicial = Decimal("1000.00")
            q.first.return_value = config
        elif model == Cliente:
            c = MagicMock()
            c.id = 1
            c.nome = "Ana Julia"
            c.telefone = "5511999999999"
            q.all.return_value = [c]
            q.first.return_value = c
        elif model == Orcamento:
            o = MagicMock()
            o.id = 100
            o.numero = "O-100"
            o.cliente = MagicMock(nome="Ana Julia")
            o.total = 500.0
            o.status = MagicMock()
            o.status.value = "ENVIADO"
            o.status.__str__.return_value = "ENVIADO"
            q.all.return_value = [o]
            q.scalar.return_value = 500.0
        else:
            q.first.return_value = MagicMock()
        return q

    db.query.side_effect = db_query_side_effect

    # Mock da função de enviar mensagem
    import app.services.whatsapp_bot_service as wbs
    from app.services.whatsapp_bot_service import _processar_assistente_gestor

    async def mock_enviar(tel, txt, **kwargs):
        print(f"\n[WHATSAPP ➔ {tel}]:\n{txt}\n" + "-"*50)

    wbs.enviar_mensagem_texto = mock_enviar
    # Forçamos o retorno do mock_user no resolvedor
    wbs._resolver_usuario_criador_orcamento = lambda e, t, d: mock_user

    # Lista de comandos da interface solicitados pelo usuário
    test_messages = [
        "💰 Caixa",
        "📊 Resumo financeiro",
        "📝 Novo orçamento",
        "⏳ Orçamentos pendentes",
        "lista de clientes"
    ]

    for msg in test_messages:
        print(f"📥 USUÁRIO ENVIOU: '{msg}'")
        try:
            await _processar_assistente_gestor(
                telefone="5511999999999",
                mensagem=msg,
                empresa=mock_empresa,
                db=db
            )
        except Exception as e:
            print(f"❌ ERRO AO PROCESSAR '{msg}': {e}")

if __name__ == "__main__":
    asyncio.run(simulate_whatsapp_full_flow())
