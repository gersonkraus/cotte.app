import asyncio
import json
from types import SimpleNamespace

from starlette.requests import Request

from datetime import date
from pydantic import BaseModel

from app.models.models import (
    AuditLog,
    CategoriaFinanceira,
    CommercialLead,
    ContaFinanceira,
    Empresa,
    MovimentacaoCaixa,
    Notificacao,
    Orcamento,
    OrcamentoDocumento,
    Cliente,
    StatusConta,
    TipoConta,
    OrigemRegistro,
    StatusOrcamento,
    ToolCallLog,
)
from app.services.ai_tools import REGISTRY
from app.services.ai_tools._base import ToolSpec
from app.routers.financeiro import excluir_conta_soft, excluir_movimentacao_caixa
from app.routers.comercial_leads import delete_lead
from app.routers.notificacoes import marcar_todas_lidas
from app.routers.orcamentos import remover_documento_do_orcamento
from app.services.audit_service import registrar_auditoria
from app.services.tool_executor import execute as execute_tool
from tests.conftest import TestingSessionLocal, sync_engine_test, make_empresa, make_usuario
from app.core.database import Base


def _build_request(path: str, method: str = "PATCH", request_id: str = "req-test-1") -> Request:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "state": {},
    }
    request = Request(scope)
    request.state.log_context = SimpleNamespace(request_id=request_id)
    return request


def _reset_db():
    Base.metadata.create_all(bind=sync_engine_test)
    db = TestingSessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    db.close()


def test_registrar_auditoria_persiste_request_id_e_detalhes():
    _reset_db()
    db = TestingSessionLocal()
    empresa = make_empresa(db, nome="Empresa Audit", telefone_operador="5511999940001")
    usuario = make_usuario(db, empresa, email="audit-sprint2@teste.com")
    db.commit()

    registrar_auditoria(
        db=db,
        usuario=usuario,
        acao="acao_teste_sprint2",
        recurso="teste",
        recurso_id="123",
        detalhes={"origem": "teste"},
        request=_build_request("/api/v1/teste", method="POST", request_id="req-audit-123"),
    )
    db.close()

    verify_db = TestingSessionLocal()
    log = verify_db.query(AuditLog).filter(AuditLog.acao == "acao_teste_sprint2").first()
    assert log is not None
    detalhes = json.loads(log.detalhes)
    assert detalhes["origem"] == "teste"
    assert detalhes["request_id"] == "req-audit-123"
    assert detalhes["request_method"] == "POST"
    assert detalhes["request_path"] == "/api/v1/teste"
    verify_db.close()


def test_marcar_todas_lidas_nao_afeta_outra_empresa_e_gera_auditoria():
    _reset_db()
    db = TestingSessionLocal()
    empresa_a = make_empresa(db, nome="Empresa Notif A", telefone_operador="5511999941001")
    empresa_b = make_empresa(db, nome="Empresa Notif B", telefone_operador="5511999941002")
    usuario_a = make_usuario(db, empresa_a, email="notif-a@teste.com")

    db.add_all(
        [
            Notificacao(empresa_id=empresa_a.id, tipo="info", titulo="A1", mensagem="x", lida=False),
            Notificacao(empresa_id=empresa_a.id, tipo="info", titulo="A2", mensagem="x", lida=False),
            Notificacao(empresa_id=empresa_b.id, tipo="info", titulo="B1", mensagem="x", lida=False),
        ]
    )
    db.commit()
    empresa_a_id = empresa_a.id
    empresa_b_id = empresa_b.id

    result = marcar_todas_lidas(
        request=_build_request("/api/v1/notificacoes/marcar-todas-lidas", request_id="req-notif-1"),
        db=db,
        usuario=usuario_a,
    )
    assert result == {"ok": True}
    db.close()

    verify_db = TestingSessionLocal()
    empresa_a_lidas = verify_db.query(Notificacao).filter_by(empresa_id=empresa_a_id, lida=True).count()
    empresa_b_lidas = verify_db.query(Notificacao).filter_by(empresa_id=empresa_b_id, lida=True).count()
    assert empresa_a_lidas == 2
    assert empresa_b_lidas == 0

    log = verify_db.query(AuditLog).filter(AuditLog.acao == "notificacoes_marcadas_lidas").first()
    assert log is not None
    detalhes = json.loads(log.detalhes)
    assert detalhes["total_marcadas"] == 2
    assert detalhes["request_id"] == "req-notif-1"
    verify_db.close()


def test_delete_lead_nao_remove_lead_global_e_remove_apenas_lead_da_empresa():
    _reset_db()
    db = TestingSessionLocal()
    empresa = make_empresa(db, nome="Empresa Lead", telefone_operador="5511999942001")
    usuario = make_usuario(db, empresa, email="lead-sprint2@teste.com")

    lead_global = CommercialLead(
        nome_responsavel="Lead Global",
        nome_empresa="Lead Sem Empresa",
        email="global@teste.com",
        empresa_id=None,
    )
    lead_empresa = CommercialLead(
        nome_responsavel="Lead Empresa",
        nome_empresa="Lead da Empresa",
        email="empresa@teste.com",
        empresa_id=empresa.id,
    )
    db.add_all([lead_global, lead_empresa])
    db.commit()
    lead_global_id = lead_global.id
    lead_empresa_id = lead_empresa.id

    delete_lead(
        lead_id=lead_global_id,
        request=_build_request(f"/api/v1/comercial/leads/{lead_global_id}", method="DELETE", request_id="req-lead-global"),
        db=db,
        usuario=usuario,
    )
    delete_lead(
        lead_id=lead_empresa_id,
        request=_build_request(f"/api/v1/comercial/leads/{lead_empresa_id}", method="DELETE", request_id="req-lead-own"),
        db=db,
        usuario=usuario,
    )
    db.close()

    verify_db = TestingSessionLocal()
    assert verify_db.query(CommercialLead).filter(CommercialLead.id == lead_global_id).first() is not None
    assert verify_db.query(CommercialLead).filter(CommercialLead.id == lead_empresa_id).first() is None

    log = verify_db.query(AuditLog).filter(AuditLog.acao == "comercial_lead_excluido").first()
    assert log is not None
    detalhes = json.loads(log.detalhes)
    assert detalhes["nome_empresa"] == "Lead da Empresa"
    assert detalhes["request_id"] == "req-lead-own"
    verify_db.close()


def test_excluir_movimentacao_caixa_gera_auditoria_e_respeita_empresa():
    _reset_db()
    db = TestingSessionLocal()
    empresa_a = make_empresa(db, nome="Empresa Caixa A", telefone_operador="5511999943001")
    empresa_b = make_empresa(db, nome="Empresa Caixa B", telefone_operador="5511999943002")
    usuario_a = make_usuario(db, empresa_a, email="caixa-a@teste.com")

    mov_b = MovimentacaoCaixa(
        empresa_id=empresa_b.id,
        tipo="saida",
        valor=150,
        descricao="Mov B",
        categoria="teste",
        data=date.today(),
    )
    mov_a = MovimentacaoCaixa(
        empresa_id=empresa_a.id,
        tipo="entrada",
        valor=200,
        descricao="Mov A",
        categoria="venda",
        data=date.today(),
    )
    db.add_all([mov_b, mov_a])
    db.commit()
    mov_b_id = mov_b.id
    mov_a_id = mov_a.id

    try:
        excluir_movimentacao_caixa(
            movimentacao_id=mov_b_id,
            request=_build_request(f"/api/v1/financeiro/caixa/movimentacoes/{mov_b_id}", method="DELETE", request_id="req-caixa-other"),
            db=db,
            usuario=usuario_a,
        )
        assert False, "Era esperado 404 ao excluir movimentação de outra empresa"
    except Exception as exc:
        from fastapi import HTTPException
        assert isinstance(exc, HTTPException)
        assert exc.status_code == 404

    excluir_movimentacao_caixa(
        movimentacao_id=mov_a_id,
        request=_build_request(f"/api/v1/financeiro/caixa/movimentacoes/{mov_a_id}", method="DELETE", request_id="req-caixa-own"),
        db=db,
        usuario=usuario_a,
    )
    db.close()

    verify_db = TestingSessionLocal()
    assert verify_db.query(MovimentacaoCaixa).filter(MovimentacaoCaixa.id == mov_b_id).first() is not None
    assert verify_db.query(MovimentacaoCaixa).filter(MovimentacaoCaixa.id == mov_a_id).first() is None
    log = verify_db.query(AuditLog).filter(AuditLog.acao == "financeiro_movimentacao_excluida").first()
    assert log is not None
    detalhes = json.loads(log.detalhes)
    assert detalhes["descricao"] == "Mov A"
    assert detalhes["request_id"] == "req-caixa-own"
    verify_db.close()


def test_excluir_conta_soft_gera_auditoria_com_request_id():
    _reset_db()
    db = TestingSessionLocal()
    empresa = make_empresa(db, nome="Empresa Conta", telefone_operador="5511999944001")
    usuario = make_usuario(db, empresa, email="conta-soft@teste.com")
    conta = ContaFinanceira(
        empresa_id=empresa.id,
        tipo=TipoConta.RECEBER,
        descricao="Conta Soft",
        valor=500,
        valor_pago=0,
        status=StatusConta.PENDENTE,
        origem=OrigemRegistro.MANUAL,
    )
    db.add(conta)
    db.commit()

    from types import SimpleNamespace as _SN
    body = _SN(motivo="teste soft delete")
    excluir_conta_soft(
        conta_id=conta.id,
        body=body,
        request=_build_request(f"/api/v1/financeiro/contas/{conta.id}/soft", method="DELETE", request_id="req-soft-1"),
        db=db,
        usuario=usuario,
    )
    db.close()

    verify_db = TestingSessionLocal()
    conta_db = verify_db.query(ContaFinanceira).filter(ContaFinanceira.id == conta.id).first()
    assert conta_db is not None
    assert conta_db.excluido_em is not None
    assert conta_db.status == StatusConta.CANCELADO
    log = verify_db.query(AuditLog).filter(AuditLog.acao == "financeiro_conta_soft_delete").first()
    assert log is not None
    detalhes = json.loads(log.detalhes)
    assert detalhes["motivo_exclusao"] == "teste soft delete"
    assert detalhes["request_id"] == "req-soft-1"
    verify_db.close()


def test_remover_documento_do_orcamento_gera_auditoria():
    _reset_db()
    db = TestingSessionLocal()
    empresa = make_empresa(db, nome="Empresa Orc", telefone_operador="5511999945001")
    usuario = make_usuario(db, empresa, email="orc-doc@teste.com")
    cliente = Cliente(empresa_id=empresa.id, nome="Cliente Doc")
    db.add(cliente)
    db.flush()

    orc = Orcamento(
        empresa_id=empresa.id,
        cliente_id=cliente.id,
        criado_por_id=usuario.id,
        numero="ORC-TESTE-1",
        status=StatusOrcamento.RASCUNHO,
        total=100,
    )
    db.add(orc)
    db.flush()

    vinc = OrcamentoDocumento(
        orcamento_id=orc.id,
        documento_id=None,
        documento_nome="Termo de Garantia",
        documento_tipo="termo",
        documento_versao="1",
    )
    db.add(vinc)
    db.commit()
    vinc_id = vinc.id

    remover_documento_do_orcamento(
        orcamento_id=orc.id,
        orcamento_documento_id=vinc_id,
        request=_build_request(f"/api/v1/orcamentos/{orc.id}/documentos/{vinc_id}", method="DELETE", request_id="req-orc-doc-1"),
        db=db,
        usuario=usuario,
    )
    db.close()

    verify_db = TestingSessionLocal()
    assert verify_db.query(OrcamentoDocumento).filter(OrcamentoDocumento.id == vinc_id).first() is None
    log = verify_db.query(AuditLog).filter(AuditLog.acao == "orcamento_documento_removido").first()
    assert log is not None
    detalhes = json.loads(log.detalhes)
    assert detalhes["orcamento_numero"] == "ORC-TESTE-1"
    assert detalhes["documento_nome"] == "Termo de Garantia"
    assert detalhes["request_id"] == "req-orc-doc-1"
    verify_db.close()


def test_tool_executor_registra_request_id_no_tool_log():
    _reset_db()
    db = TestingSessionLocal()
    empresa = make_empresa(db, nome="Empresa Tool", telefone_operador="5511999946001")
    usuario = make_usuario(db, empresa, email="tool-log@teste.com")
    usuario.token_versao = 1
    db.commit()

    class _Input(BaseModel):
        valor: int

    async def _handler(input_data, *, db, current_user):
        return {"echo": input_data.valor, "empresa_id": current_user.empresa_id}

    spec = ToolSpec(
        name="tool_teste_sprint2",
        description="Tool de teste da sprint 2",
        input_model=_Input,
        handler=_handler,
        destrutiva=False,
    )
    REGISTRY["tool_teste_sprint2"] = spec
    try:
        result = asyncio.run(
            execute_tool(
                {
                    "id": "tc-s2",
                    "type": "function",
                    "function": {
                        "name": "tool_teste_sprint2",
                        "arguments": json.dumps({"valor": 7}),
                    },
                },
                db=db,
                current_user=usuario,
                sessao_id="sessao-sprint2",
                request_id="req-tool-1",
            )
        )
        assert result.status == "ok"
    finally:
        REGISTRY.pop("tool_teste_sprint2", None)
        db.close()

    verify_db = TestingSessionLocal()
    log = verify_db.query(ToolCallLog).filter(ToolCallLog.tool == "tool_teste_sprint2").first()
    assert log is not None
    assert log.args_json["_meta"]["request_id"] == "req-tool-1"
    assert log.resultado_json["_meta"]["request_id"] == "req-tool-1"
    assert log.resultado_json["_meta"]["sessao_id"] == "sessao-sprint2"
    verify_db.close()
