"""Script manual para exercitar endpoints de agendamentos.

IMPORTANTE:
- Este arquivo NÃO é um teste automatizado de pytest.
- O código roda apenas quando executado diretamente (evita efeitos colaterais ao coletar testes).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone


def _print_result(test_name, response, expect_error: bool = False):
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
                    print(
                        f"   Primeiro: {json.dumps(body[0], indent=2, default=str, ensure_ascii=False)}"
                    )
        except Exception:
            print(f"   Body: {response.text[:300]}")
    return response


def main() -> None:
    sys.path.insert(0, "/home/gk/Projeto-izi/sistema")

    from app.core.auth import criar_token
    from app.main import app
    from tests.asgi_client import SyncASGIClient

    client = SyncASGIClient(app, raise_app_exceptions=False)

    # Token do gestor (user_id=1, empresa_id=5)
    token = criar_token({"sub": "1", "empresa_id": 5, "v": 191})
    headers = {"Authorization": f"Bearer {token}"}

    # Dados de teste
    cliente_id = 1  # Ana Julia
    orcamento_aprovado_id = 30  # ORC-30-26 (sem agendamento prévio)
    responsavel_id = 1  # Gerson (gestor)

    amanha = datetime(2026, 3, 27, 14, 0, 0, tzinfo=timezone(timedelta(hours=-3)))
    amanha_14h = datetime(2026, 3, 27, 15, 0, 0, tzinfo=timezone(timedelta(hours=-3)))
    proxima_semana = datetime(2026, 4, 2, 10, 0, 0, tzinfo=timezone(timedelta(hours=-3)))

    agendamento_criado_id = None
    slot_bloqueado_id = None

    print("=" * 70)
    print("TESTES DO MÓDULO DE AGENDAMENTOS")
    print("=" * 70)

    r = client.get("/api/v1/agendamentos/config/empresa", headers=headers)
    _print_result("1. GET /config/empresa", r)

    r = client.put(
        "/api/v1/agendamentos/config/empresa",
        headers=headers,
        json={
            "horario_inicio": "08:00",
            "horario_fim": "18:00",
            "dias_trabalho": [0, 1, 2, 3, 4],
            "duracao_padrao_min": 60,
            "antecedencia_minima_horas": 0,
            "requer_confirmacao": True,
        },
    )
    _print_result("2. PUT /config/empresa", r)

    r = client.post(
        "/api/v1/agendamentos/config/usuario",
        headers=headers,
        json={
            "usuario_id": responsavel_id,
            "horario_inicio": "09:00",
            "horario_fim": "17:00",
            "dias_trabalho": [0, 1, 2, 3, 4],
        },
    )
    _print_result("3. POST /config/usuario", r)

    r = client.get("/api/v1/agendamentos/config/usuarios", headers=headers)
    _print_result("4. GET /config/usuarios", r)

    r = client.post(
        "/api/v1/agendamentos/",
        headers=headers,
        json={
            "cliente_id": cliente_id,
            "tipo": "servico",
            "data_agendada": amanha.isoformat(),
            "duracao_estimada_min": 60,
            "responsavel_id": responsavel_id,
            "observacoes": "Teste de agendamento via API",
        },
    )
    _print_result("5. POST /agendamentos/ (criar)", r)
    if r.status_code == 200:
        agendamento_criado_id = r.json().get("id")
        print(f"   → agendamento_id = {agendamento_criado_id}")

    r = client.post(
        f"/api/v1/agendamentos/criar-do-orcamento/{orcamento_aprovado_id}",
        headers=headers,
        json={
            "responsavel_id": responsavel_id,
            "tipo": "servico",
            "data_agendada": amanha_14h.isoformat(),
            "duracao_estimada_min": 90,
            "observacoes": "Serviço do orçamento ORC-42-26",
        },
    )
    _print_result("6. POST /criar-do-orcamento/{id}", r)

    r = client.get("/api/v1/agendamentos/", headers=headers)
    _print_result("7. GET /agendamentos/ (listar)", r)

    if agendamento_criado_id:
        r = client.get(f"/api/v1/agendamentos/{agendamento_criado_id}", headers=headers)
        _print_result(f"8. GET /agendamentos/{agendamento_criado_id}", r)

    r = client.get("/api/v1/agendamentos/dashboard", headers=headers)
    _print_result("9. GET /dashboard", r)

    r = client.get("/api/v1/agendamentos/hoje", headers=headers)
    _print_result("10. GET /hoje", r)

    r = client.get(
        "/api/v1/agendamentos/disponiveis",
        headers=headers,
        params={"data": amanha.isoformat(), "responsavel_id": responsavel_id},
    )
    _print_result("11. GET /disponiveis", r)

    r = client.get("/api/v1/agendamentos/responsaveis", headers=headers)
    _print_result("12. GET /responsaveis", r)

    if agendamento_criado_id:
        r = client.put(
            f"/api/v1/agendamentos/{agendamento_criado_id}",
            headers=headers,
            json={"observacoes": "Observação atualizada via teste"},
        )
        _print_result(f"13. PUT /agendamentos/{agendamento_criado_id} (obs)", r)

    if agendamento_criado_id:
        r = client.patch(
            f"/api/v1/agendamentos/{agendamento_criado_id}/status",
            headers=headers,
            json={"status": "confirmado"},
        )
        _print_result(f"14. PATCH /agendamentos/{agendamento_criado_id}/status → confirmado", r)

    if agendamento_criado_id:
        r = client.patch(
            f"/api/v1/agendamentos/{agendamento_criado_id}/reagendar",
            headers=headers,
            json={
                "nova_data": proxima_semana.isoformat(),
                "motivo": "Cliente pediu para reagendar (teste)",
            },
        )
        _print_result(f"15. PATCH /agendamentos/{agendamento_criado_id}/reagendar", r)

    if agendamento_criado_id:
        r = client.get(
            f"/api/v1/agendamentos/{agendamento_criado_id}/historico",
            headers=headers,
        )
        _print_result(f"16. GET /agendamentos/{agendamento_criado_id}/historico", r)

    bloqueio_inicio = datetime(2026, 3, 30, 12, 0, 0, tzinfo=timezone(timedelta(hours=-3)))
    bloqueio_fim = datetime(2026, 3, 30, 13, 0, 0, tzinfo=timezone(timedelta(hours=-3)))
    r = client.post(
        "/api/v1/agendamentos/bloquear-slot",
        headers=headers,
        json={
            "data_inicio": bloqueio_inicio.isoformat(),
            "data_fim": bloqueio_fim.isoformat(),
            "motivo": "Almoço (teste)",
            "recorrente": False,
        },
    )
    _print_result("17. POST /bloquear-slot", r)
    if r.status_code == 200:
        slot_bloqueado_id = r.json().get("id")
        print(f"   → slot_id = {slot_bloqueado_id}")

    r = client.post(
        "/api/v1/agendamentos/bloquear-slot",
        headers=headers,
        json={
            "usuario_id": responsavel_id,
            "data_inicio": bloqueio_inicio.isoformat(),
            "data_fim": bloqueio_fim.isoformat(),
            "motivo": "Ausência individual (teste)",
        },
    )
    _print_result("18. POST /bloquear-slot (individual)", r)

    r = client.get("/api/v1/agendamentos/bloqueados", headers=headers)
    _print_result("19. GET /bloqueados", r)

    r = client.get(
        "/api/v1/agendamentos/bloqueados",
        headers=headers,
        params={"usuario_id": responsavel_id},
    )
    _print_result("20. GET /bloqueados?usuario_id=X", r)

    if slot_bloqueado_id:
        r = client.delete(
            f"/api/v1/agendamentos/bloquear-slot/{slot_bloqueado_id}",
            headers=headers,
        )
        _print_result(f"21. DELETE /bloquear-slot/{slot_bloqueado_id}", r)

    r = client.delete(
        f"/api/v1/agendamentos/config/usuario/{responsavel_id}",
        headers=headers,
    )
    _print_result(f"22. DELETE /config/usuario/{responsavel_id}", r)

    r = client.post(
        "/api/v1/agendamentos/",
        headers=headers,
        json={
            "cliente_id": 99999,
            "tipo": "servico",
            "data_agendada": amanha.isoformat(),
        },
    )
    _print_result("23. POST /agendamentos/ (cliente inexistente → erro esperado)", r, expect_error=True)

    r = client.post(
        "/api/v1/agendamentos/criar-do-orcamento/1",
        headers=headers,
        json={"data_agendada": amanha.isoformat()},
    )
    _print_result("24. POST /criar-do-orcamento/1 (orc não aprovado → erro esperado)", r, expect_error=True)

    r = client.get("/api/v1/agendamentos/99999", headers=headers)
    _print_result("25. GET /agendamentos/99999 (não existe → 404 esperado)", r, expect_error=True)

    if agendamento_criado_id:
        r_list = client.get(
            "/api/v1/agendamentos/",
            headers=headers,
            params={"status": "pendente"},
        )
        if r_list.status_code == 200:
            novos = r_list.json()
            if novos:
                novo_id = novos[0]["id"]
                client.patch(
                    f"/api/v1/agendamentos/{novo_id}/status",
                    headers=headers,
                    json={"status": "confirmado"},
                )
                client.patch(
                    f"/api/v1/agendamentos/{novo_id}/status",
                    headers=headers,
                    json={"status": "em_andamento"},
                )
                r = client.patch(
                    f"/api/v1/agendamentos/{novo_id}/status",
                    headers=headers,
                    json={"status": "concluido"},
                )
                _print_result("26. PATCH status pendente → confirmado → em_andamento → concluido", r)

    r = client.get(
        "/api/v1/agendamentos/",
        headers=headers,
        params={"tipo": "servico", "responsavel_id": responsavel_id, "per_page": 5},
    )
    _print_result("27. GET /agendamentos/ (com filtros)", r)

    r = client.get(
        "/api/v1/agendamentos/",
        headers=headers,
        params={"orcamento_id": orcamento_aprovado_id},
    )
    _print_result(f"28. GET /agendamentos/?orcamento_id={orcamento_aprovado_id}", r)

    print("\n" + "=" * 70)
    print("TESTES CONCLUÍDOS")
    print("=" * 70)


if __name__ == "__main__":
    main()
