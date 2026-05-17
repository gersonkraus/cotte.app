
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

async def run_targeted_audit():
    print("🚀 INICIANDO AUDITORIA DIRECIONADA: COMANDOS DA INTERFACE (v2.1)\n")
    
    # Setup Mocks
    db = MagicMock()
    mock_empresa = MagicMock()
    mock_empresa.id = 1
    mock_empresa.empresa_id = 1
    db.query().filter().first.return_value = mock_empresa
    db.query().filter().first.side_effect = lambda *args, **kwargs: mock_empresa

    user = Usuario(id=1, empresa_id=1, ativo=True)
    user.empresa = Empresa(id=1, ativo=True)
    
    # Casos de teste baseados na lista do usuário
    test_cases = [
        ("caixa", "SALDO_RAPIDO", "saldo_caixa"),
        ("resumo financeiro", "DASHBOARD", "financeiro_dashboard"),
        ("clientes em atraso", "INADIMPLENCIA", "financeiro_inadimplencia"),
        ("novo orçamento", "CRIAR_ORCAMENTO", "orcamento_preview"),
        ("orçamentos pendentes", "LISTAR_ORCAMENTOS", "lista_orcamentos"),
        ("taxa de conversão", "CONVERSAO", "vendas_conversao"),
        ("faturamento por cliente", "FATURAMENTO", "financeiro_faturamento"),
        ("serviços mais vendidos", "FATURAMENTO", "financeiro_faturamento"), # Geralmente cai em faturamento agrupado
        ("visão geral de orçamentos", "DASHBOARD", "financeiro_dashboard"),
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
                sessao_id=f"audit_{expected_intent}",
                db=db,
                current_user=user,
                agent_name="ConversationalAgent" # Testar bypass/interceptação
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
        
        # Validação flexível: sucesso se a intenção bate ou se o tipo de resposta é condizente
        # (ex: DASHBOARD pode retornar 'financeiro_dashboard' ou similar)
        intent_ok = (detected_intent == expected_intent)
        type_ok = (resp_type is not None)
        
        success = intent_ok and not errors
        
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
    print("\n" + "="*95)
    print(f"{'MENSAGEM':<30} | {'INTENÇÃO DETECTADA':<20} | {'TIPO RESPOSTA':<25} | {'STATUS'}")
    print("-" * 95)
    
    all_ok = True
    for r in results:
        status = "✅ OK" if r.sucesso else "❌ FALHA"
        if not r.sucesso: all_ok = False
        print(f"{r.mensagem[:30]:<30} | {r.intencao_detectada:<20} | {r.tipo_resposta:<25} | {status}")
    
    print("="*95)
    
    if all_ok:
        print("\n🏆 TODOS OS COMANDOS DE INTERFACE ESTÃO OPERACIONAIS - SAÚDE 100%")
    else:
        print("\n⚠️ ALGUNS COMANDOS PODEM PRECISAR DE AJUSTE NO REGEX.")

if __name__ == "__main__":
    asyncio.run(run_targeted_audit())
