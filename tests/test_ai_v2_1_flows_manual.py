
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime

# Importar componentes do sistema
import sys
import os
sys.path.append(os.path.abspath("sistema"))
sys.path.append(os.path.abspath("."))

from app.services.cotte_ai_hub import assistente_v2_stream_core
from app.services.ai_intention_classifier import detectar_intencao_assistente_async, IntencaoUsuario
from app.models.models import Usuario, Empresa

async def test_listar_orcamentos_flow():
    print("\n=== Testando Fluxo: Lista de Orçamentos Aprovados ===")
    
    # Mock de DB e Usuário
    db = MagicMock()
    user = Usuario(id=1, empresa_id=1, ativo=True)
    user.empresa = Empresa(id=1, ativo=True)
    
    mensagem = "lista de orçamentos aprovados"
    
    # 1. Verificar Intenção
    classificacao = await detectar_intencao_assistente_async(mensagem)
    print(f"Intenção detectada: {classificacao.intencao.value}")
    
    # 2. Executar Core (Stream)
    events = []
    async for event_str in assistente_v2_stream_core(
        mensagem=mensagem,
        sessao_id="test_session",
        db=db,
        current_user=user
    ):
        if event_str.startswith("data: "):
            events.append(json.loads(event_str[6:]))
    
    # Procurar o evento final com metadata
    final_event = next((e for e in events if e.get("is_final")), None)
    if final_event:
        meta = final_event.get("metadata", {})
        print(f"Tipo de Resposta: {meta.get('tipo_resposta')}")
        print(f"Intenção no Contexto: {meta.get('contexto_operacional', {}).get('objetivo_ativo')}")
        
        # Verificar se os dados de orçamentos foram coletados (mesmo se mockados)
        # Como o db.query está mockado e não retorna nada, 'orcamentos' deve ser vazio, 
        # mas a chave deve existir no metadata agora.
        dados = meta.get("dados", {})
        print(f"Chave 'orcamentos' presente nos dados: {'orcamentos' in dados}")
    else:
        print("Erro: Evento final não encontrado.")

async def test_criar_orcamento_flow():
    print("\n=== Testando Fluxo: Criação de Orçamento (Fastpath) ===")
    
    db = MagicMock()
    user = Usuario(id=1, empresa_id=1, ativo=True)
    user.empresa = Empresa(id=1, ativo=True)
    
    mensagem = "orçamento de pintura para Gerson por 500"
    
    # 1. Verificar Intenção
    classificacao = await detectar_intencao_assistente_async(mensagem)
    print(f"Intenção detectada: {classificacao.intencao.value}")
    
    # 2. Executar Core
    events = []
    async for event_str in assistente_v2_stream_core(
        mensagem=mensagem,
        sessao_id="test_session",
        db=db,
        current_user=user
    ):
        if event_str.startswith("data: "):
            events.append(json.loads(event_str[6:]))
            
    final_event = next((e for e in events if e.get("is_final")), None)
    if final_event:
        meta = final_event.get("metadata", {})
        print(f"Tipo de Resposta: {meta.get('tipo_resposta')}")
        dados = meta.get("dados", {})
        print(f"Dados extraídos: {json.dumps({k:v for k,v in dados.items() if k in ['cliente_nome', 'servico', 'valor']}, indent=2)}")
    else:
        print("Erro: Evento final não encontrado.")

if __name__ == "__main__":
    asyncio.run(test_listar_orcamentos_flow())
    asyncio.run(test_criar_orcamento_flow())
