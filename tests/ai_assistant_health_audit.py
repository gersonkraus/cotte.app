
import asyncio
import json
import os
import sys
import time
from unittest.mock import MagicMock, AsyncMock
from dataclasses import dataclass
from decimal import Decimal

# Adicionar caminhos ao sys.path
sys.path.append(os.path.abspath("sistema"))
sys.path.append(os.path.abspath("."))

from app.services.cotte_ai_hub import assistente_v2_stream_core
from app.services.ai_intention_classifier import detectar_intencao_assistente_async, IntencaoUsuario
from app.models.models import Usuario, Empresa

@dataclass
class HealthCheckResult:
    mensagem: str
    intencao_esperada: str
    intencao_detectada: str
    tipo_resposta: str
    sucesso: bool
    tempo_ms: int
    erros: list[str]
    metadata_ok: bool
    final_text: str

async def run_audit():
    print("🚀 INICIANDO AUDITORIA DE SAÚDE DO ASSISTENTE IA (v2.1)\n")
    
    # Setup Mocks mais inteligentes
    db = MagicMock()
    # Mock do retorno de query().filter().first() para evitar bloqueio de sessão
    mock_empresa = MagicMock()
    mock_empresa.id = 1
    mock_empresa.empresa_id = 1
    db.query().filter().first.return_value = mock_empresa
    
    # Mock para saldo
    db.query().filter().first.side_effect = lambda *args, **kwargs: mock_empresa

    user = Usuario(id=1, empresa_id=1, ativo=True)
    user.empresa = Empresa(id=1, ativo=True)
    
    test_cases = [
        ("quanto tenho no caixa?", "SALDO_RAPIDO", "saldo_caixa"),
        ("qual faturamento de hoje?", "FATURAMENTO", "financeiro_faturamento"),
        ("quais as contas a receber?", "CONTAS_RECEBER", "contas_receber_lista"),
        ("tenho contas a pagar?", "CONTAS_PAGAR", "contas_pagar_lista"),
        ("novo orcamento para Gerson de pintura por 500", "CRIAR_ORCAMENTO", "orcamento_preview"),
        ("me mostre a lista de orçamentos aprovados", "LISTAR_ORCAMENTOS", "lista_orcamentos"),
        ("lista de clientes cadastrados", "LISTAR_CLIENTES", "clientes_lista"),
        ("aprovar orçamento 123", "OPERADOR", "operador_action"),
        ("relatorio de vendas do mes", "GERAR_RELATORIO", "relatorio_dinamico"),
        ("quais os agendamentos de hoje?", "AGENDAMENTO_LISTAR", "agendamentos_lista"),
    ]
    
    results = []
    
    for msg, expected_intent, expected_type in test_cases:
        print(f"Testing: '{msg}'...")
        start_time = time.perf_counter()
        
        # 1. Classificação
        classif = await detectar_intencao_assistente_async(msg)
        detected_intent = classif.intencao.value
            
        # 2. Execução (Stream)
        events = []
        try:
            async for event_str in assistente_v2_stream_core(
                mensagem=msg,
                sessao_id=f"audit_{expected_intent}", # Sessão única por intenção
                db=db,
                current_user=user,
                agent_name="ConversationalAgent" # Testar bypass
            ):
                if event_str.startswith("data: "):
                    events.append(json.loads(event_str[6:]))
        except Exception as e:
            print(f"  EXCEÇÃO: {e}")
            events.append({"error": str(e)})
            
        duration = int((time.perf_counter() - start_time) * 1000)
        
        # Analisar resultado
        final_event = next((e for e in events if e.get("is_final")), None)
        meta = final_event.get("metadata", {}) if final_event else {}
        resp_type = meta.get("tipo_resposta") or meta.get("tipo")
        final_text = final_event.get("final_text", "") if final_event else ""
        
        errors = [e.get("error") for e in events if "error" in e]
        
        # Sucesso se a intenção foi capturada (mesmo que por bypass) e não houve erro técnico
        success = (detected_intent == expected_intent) and not errors
        
        # Se for um desses 4, DEVE ter o resp_type correto (Fastpath Triggered)
        if expected_intent in {"CRIAR_ORCAMENTO", "SALDO_RAPIDO", "LISTAR_ORCAMENTOS", "LISTAR_CLIENTES"}:
            if resp_type != expected_type:
                success = False
                print(f"  FALHA: Esperava tipo {expected_type}, veio {resp_type}")

        results.append(HealthCheckResult(
            mensagem=msg,
            intencao_esperada=expected_intent,
            intencao_detectada=detected_intent,
            tipo_resposta=str(resp_type),
            sucesso=success,
            tempo_ms=duration,
            erros=errors,
            metadata_ok="dados" in meta,
            final_text=final_text
        ))

    # Relatório Final
    print("\n" + "="*90)
    print(f"{'MENSAGEM':<35} | {'INTENÇÃO':<15} | {'TIPO RESP':<20} | {'STATUS'}")
    print("-" * 90)
    
    all_ok = True
    for r in results:
        status = "✅ OK" if r.sucesso else "❌ FALHA"
        if not r.sucesso: all_ok = False
        print(f"{r.mensagem[:35]:<35} | {r.intencao_detectada:<15} | {r.tipo_resposta:<20} | {status}")
    
    print("="*90)
    
    if all_ok:
        print("\n🏆 TODOS OS SISTEMAS OPERACIONAIS - SAÚDE 100%")
    else:
        print("\n⚠️ ALGUNS MÓDULOS EXIGEM ATENÇÃO.")

if __name__ == "__main__":
    asyncio.run(run_audit())
