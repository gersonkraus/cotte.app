"""
Testes dos endpoints de Agendamentos — todos os 18 endpoints.
Usa TestClient do FastAPI com token JWT do usuário gestor.
"""

import sys
import json
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/home/gk/Projeto-izi/sistema")

from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import criar_token

client = TestClient(app)

# Token do gestor (user_id=1, empresa_id=5)
TOKEN = criar_token({"sub": "1", "empresa_id": 5, "v": 191})
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

# Dados de teste
EMPRESA_ID = 5
CLIENTE_ID = 1  # Ana Julia
ORCAMENTO_APROVADO_ID = 30  # ORC-30-26 (sem agendamento prévio)
RESPONSAVEL_ID = 1  # Gerson (gestor)

amanha = datetime(2026, 3, 27, 14, 0, 0, tzinfo=timezone(timedelta(hours=-3)))
amanha_14h = datetime(2026, 3, 27, 15, 0, 0, tzinfo=timezone(timedelta(hours=-3)))
proxima_semana = datetime(2026, 4, 2, 10, 0, 0, tzinfo=timezone(timedelta(hours=-3)))

agendamento_criado_id = None
slot_bloqueado_id = None


def _print_result(test_name, response, expect_error=False):
    if expect_error:
        status = "✅" if response.status_code >= 400 else "❌"
        tag = " (erro esperado)"
    else:
        status = "✅" if response.status_code < 400 else "❌"
        tag = ""
    print(f"\n{status} {test_name}{tag}")
    print(f"   Status: {response.status_code}")
    if not expect_error or response.status_code < 400:
        try:
            body = response.json()
            if isinstance(body, dict) and len(str(body)) < 500:
                print(f"   Body: {json.dumps(body, indent=2, default=str, ensure_ascii=False)}")
            elif isinstance(body, list):
                print(f"   Body: [{len(body)} itens]")
                if body and len(str(body[0])) < 300:
                    print(f"   Primeiro: {json.dumps(body[0], indent=2, default=str, ensure_ascii=False)}")
        except:
            print(f"   Body: {response.text[:300]}")
    return response


# ══════════════════════════════════════════════════════════════════════════════
print("=" * 70)
print("TESTES DO MÓDULO DE AGENDAMENTOS")
print("=" * 70)

# ── 1. Config Empresa (GET) ──
r = client.get("/api/v1/agendamentos/config/empresa", headers=HEADERS)
_print_result("1. GET /config/empresa", r)

# ── 2. Config Empresa (PUT) ──
r = client.put("/api/v1/agendamentos/config/empresa", headers=HEADERS, json={
    "horario_inicio": "08:00",
    "horario_fim": "18:00",
    "dias_trabalho": [0, 1, 2, 3, 4],
    "duracao_padrao_min": 60,
    "antecedencia_minima_horas": 0,
    "requer_confirmacao": True,
})
_print_result("2. PUT /config/empresa", r)

# ── 3. Config Usuário (POST) ──
r = client.post("/api/v1/agendamentos/config/usuario", headers=HEADERS, json={
    "usuario_id": RESPONSAVEL_ID,
    "horario_inicio": "09:00",
    "horario_fim": "17:00",
    "dias_trabalho": [0, 1, 2, 3, 4],
})
_print_result("3. POST /config/usuario", r)

# ── 4. Listar Config Usuários (GET) ──
r = client.get("/api/v1/agendamentos/config/usuarios", headers=HEADERS)
_print_result("4. GET /config/usuarios", r)

# ── 5. Criar Agendamento (POST) ──
r = client.post("/api/v1/agendamentos/", headers=HEADERS, json={
    "cliente_id": CLIENTE_ID,
    "tipo": "servico",
    "data_agendada": amanha.isoformat(),
    "duracao_estimada_min": 60,
    "responsavel_id": RESPONSAVEL_ID,
    "observacoes": "Teste de agendamento via API",
})
_print_result("5. POST /agendamentos/ (criar)", r)
if r.status_code == 200:
    agendamento_criado_id = r.json().get("id")
    print(f"   → agendamento_id = {agendamento_criado_id}")

# ── 6. Criar do Orçamento (POST) ──
r = client.post(f"/api/v1/agendamentos/criar-do-orcamento/{ORCAMENTO_APROVADO_ID}",
    headers=HEADERS,
    json={
        "responsavel_id": RESPONSAVEL_ID,
        "tipo": "servico",
        "data_agendada": amanha_14h.isoformat(),
        "duracao_estimada_min": 90,
        "observacoes": "Serviço do orçamento ORC-42-26",
    })
_print_result("6. POST /criar-do-orcamento/{id}", r)

# ── 7. Listar Agendamentos (GET) ──
r = client.get("/api/v1/agendamentos/", headers=HEADERS)
_print_result("7. GET /agendamentos/ (listar)", r)

# ── 8. Buscar Agendamento (GET) ──
if agendamento_criado_id:
    r = client.get(f"/api/v1/agendamentos/{agendamento_criado_id}", headers=HEADERS)
    _print_result(f"8. GET /agendamentos/{agendamento_criado_id}", r)

# ── 9. Dashboard (GET) ──
r = client.get("/api/v1/agendamentos/dashboard", headers=HEADERS)
_print_result("9. GET /dashboard", r)

# ── 10. Hoje (GET) ──
r = client.get("/api/v1/agendamentos/hoje", headers=HEADERS)
_print_result("10. GET /hoje", r)

# ── 11. Disponíveis (GET) ──
r = client.get("/api/v1/agendamentos/disponiveis",
    headers=HEADERS,
    params={"data": amanha.isoformat(), "responsavel_id": RESPONSAVEL_ID})
_print_result("11. GET /disponiveis", r)

# ── 12. Responsáveis (GET) ──
r = client.get("/api/v1/agendamentos/responsaveis", headers=HEADERS)
_print_result("12. GET /responsaveis", r)

# ── 13. Atualizar Agendamento (PUT) ──
if agendamento_criado_id:
    r = client.put(f"/api/v1/agendamentos/{agendamento_criado_id}", headers=HEADERS, json={
        "observacoes": "Observação atualizada via teste",
    })
    _print_result(f"13. PUT /agendamentos/{agendamento_criado_id} (obs)", r)

# ── 14. Atualizar Status (PATCH) ──
if agendamento_criado_id:
    r = client.patch(f"/api/v1/agendamentos/{agendamento_criado_id}/status",
        headers=HEADERS,
        json={"status": "confirmado"})
    _print_result(f"14. PATCH /agendamentos/{agendamento_criado_id}/status → confirmado", r)

# ── 15. Reagendar (PATCH) ──
if agendamento_criado_id:
    r = client.patch(f"/api/v1/agendamentos/{agendamento_criado_id}/reagendar",
        headers=HEADERS,
        json={
            "nova_data": proxima_semana.isoformat(),
            "motivo": "Cliente pediu para reagendar (teste)",
        })
    _print_result(f"15. PATCH /agendamentos/{agendamento_criado_id}/reagendar", r)

# ── 16. Histórico (GET) ──
if agendamento_criado_id:
    r = client.get(f"/api/v1/agendamentos/{agendamento_criado_id}/historico", headers=HEADERS)
    _print_result(f"16. GET /agendamentos/{agendamento_criado_id}/historico", r)

# ── 17. Bloquear Slot (POST) ──
bloqueio_inicio = datetime(2026, 3, 30, 12, 0, 0, tzinfo=timezone(timedelta(hours=-3)))
bloqueio_fim = datetime(2026, 3, 30, 13, 0, 0, tzinfo=timezone(timedelta(hours=-3)))
r = client.post("/api/v1/agendamentos/bloquear-slot", headers=HEADERS, json={
    "data_inicio": bloqueio_inicio.isoformat(),
    "data_fim": bloqueio_fim.isoformat(),
    "motivo": "Almoço (teste)",
    "recorrente": False,
})
_print_result("17. POST /bloquear-slot", r)
if r.status_code == 200:
    slot_bloqueado_id = r.json().get("id")
    print(f"   → slot_id = {slot_bloqueado_id}")

# ── 18. Bloquear Slot Individual (POST) ──
r = client.post("/api/v1/agendamentos/bloquear-slot", headers=HEADERS, json={
    "usuario_id": RESPONSAVEL_ID,
    "data_inicio": bloqueio_inicio.isoformat(),
    "data_fim": bloqueio_fim.isoformat(),
    "motivo": "Ausência individual (teste)",
})
_print_result("18. POST /bloquear-slot (individual)", r)

# ── 19. Listar Bloqueados (GET) ──
r = client.get("/api/v1/agendamentos/bloqueados", headers=HEADERS)
_print_result("19. GET /bloqueados", r)

# ── 20. Listar Bloqueados com filtro (GET) ──
r = client.get("/api/v1/agendamentos/bloqueados",
    headers=HEADERS,
    params={"usuario_id": RESPONSAVEL_ID})
_print_result("20. GET /bloqueados?usuario_id=X", r)

# ── 21. Remover Slot Bloqueado (DELETE) ──
if slot_bloqueado_id:
    r = client.delete(f"/api/v1/agendamentos/bloquear-slot/{slot_bloqueado_id}", headers=HEADERS)
    _print_result(f"21. DELETE /bloquear-slot/{slot_bloqueado_id}", r)

# ── 22. Remover Config Usuário (DELETE) ──
r = client.delete(f"/api/v1/agendamentos/config/usuario/{RESPONSAVEL_ID}", headers=HEADERS)
_print_result(f"22. DELETE /config/usuario/{RESPONSAVEL_ID}", r)

# ── 23. Teste erro: criar sem cliente (esperado 400/422) ──
r = client.post("/api/v1/agendamentos/", headers=HEADERS, json={
    "cliente_id": 99999,
    "tipo": "servico",
    "data_agendada": amanha.isoformat(),
})
_print_result("23. POST /agendamentos/ (cliente inexistente → erro esperado)", r, expect_error=True)

# ── 24. Teste erro: orçamento não aprovado (esperado 400) ──
r = client.post("/api/v1/agendamentos/criar-do-orcamento/1", headers=HEADERS, json={
    "data_agendada": amanha.isoformat(),
})
_print_result("24. POST /criar-do-orcamento/1 (orc não aprovado → erro esperado)", r, expect_error=True)

# ── 25. Teste erro: buscar inexistente (esperado 404) ──
r = client.get("/api/v1/agendamentos/99999", headers=HEADERS)
_print_result("25. GET /agendamentos/99999 (não existe → 404 esperado)", r, expect_error=True)

# ── 26. Teste erro: reagendar concluído (após status → em_andamento → concluido) ──
if agendamento_criado_id:
    # O agendamento foi reagendado, então criou um novo. Buscar o novo.
    r_list = client.get("/api/v1/agendamentos/", headers=HEADERS, params={"status": "pendente"})
    if r_list.status_code == 200:
        novos = r_list.json()
        if novos:
            novo_id = novos[0]["id"]
            # Confirmar
            client.patch(f"/api/v1/agendamentos/{novo_id}/status", headers=HEADERS, json={"status": "confirmado"})
            # Em andamento
            client.patch(f"/api/v1/agendamentos/{novo_id}/status", headers=HEADERS, json={"status": "em_andamento"})
            # Concluir
            r = client.patch(f"/api/v1/agendamentos/{novo_id}/status", headers=HEADERS, json={"status": "concluido"})
            _print_result(f"26. PATCH status pendente → confirmado → em_andamento → concluido", r)

# ── 27. Listar com filtros ──
r = client.get("/api/v1/agendamentos/", headers=HEADERS, params={
    "tipo": "servico",
    "responsavel_id": RESPONSAVEL_ID,
    "per_page": 5,
})
_print_result("27. GET /agendamentos/ (com filtros)", r)

# ── 28. Listar por orçamento ──
r = client.get("/api/v1/agendamentos/", headers=HEADERS, params={
    "orcamento_id": ORCAMENTO_APROVADO_ID,
})
_print_result(f"28. GET /agendamentos/?orcamento_id={ORCAMENTO_APROVADO_ID}", r)


print("\n" + "=" * 70)
print("TESTES CONCLUÍDOS")
print("=" * 70)
