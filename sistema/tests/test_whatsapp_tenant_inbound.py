import asyncio

from fastapi import BackgroundTasks

from app.models.models import AuditLog, TenantCommercialInteraction, TenantCommercialLead
from app.routers.whatsapp import _webhook_evolution
from app.schemas.schemas import WebhookEvolution
from app.services.tenant_commercial_service import registrar_interacao_whatsapp
from tests.conftest import make_empresa


def _executar_tarefas_registro(background_tasks: BackgroundTasks) -> None:
    for task in background_tasks.tasks:
        if getattr(task.func, "__name__", "") == "registrar_interacao_whatsapp":
            resultado = task.func(*task.args, **task.kwargs)
            if asyncio.iscoroutine(resultado):
                asyncio.run(resultado)


def test_webhook_evolution_mensagem_texto_desembrulha_ephemeral():
    """Texto dentro de ephemeralMessage deve ser extraído (caso comum em respostas)."""
    payload = WebhookEvolution(
        event="messages.upsert",
        data={
            "key": {
                "remoteJid": "5511888776655@s.whatsapp.net",
                "fromMe": False,
            },
            "messageType": "extendedTextMessage",
            "message": {
                "ephemeralMessage": {
                    "message": {
                        "extendedTextMessage": {
                            "text": "Resposta do cliente",
                        }
                    }
                }
            },
        },
    )
    assert payload.mensagem_texto == "Resposta do cliente"


def test_webhook_evolution_phone_usa_remote_jid_alt_quando_lid():
    payload = WebhookEvolution(
        event="messages.upsert",
        data={
            "key": {
                "remoteJid": "123456789012345@lid",
                "remoteJidAlt": "5511888776655@s.whatsapp.net",
                "fromMe": False,
            },
            "message": {"conversation": "oi"},
        },
    )
    assert payload.phone == "5511888776655"


def test_webhook_evolution_phone_remove_sufixo_device():
    payload = WebhookEvolution(
        event="messages.upsert",
        data={
            "key": {
                "remoteJid": "5511999998888:45@s.whatsapp.net",
                "fromMe": False,
            },
            "messageType": "conversation",
            "message": {"conversation": "oi"},
        },
    )
    assert payload.phone == "5511999998888"


def test_webhook_evolution_registra_mensagem_recebida_no_tenant(db):
    empresa = make_empresa(db)
    lead = TenantCommercialLead(
        empresa_id=empresa.id,
        nome="Lead Tenant",
        nome_empresa="Lead Tenant LTDA",
        telefone="5511991112222",
        status_pipeline="novo",
        ativo=True,
    )
    db.add(lead)
    db.commit()

    background = BackgroundTasks()
    payload = {
        "event": "messages.upsert",
        "instance": "tenant-inst",
        "data": {
            "key": {
                "fromMe": False,
                "remoteJid": "5511991112222:26@s.whatsapp.net",
                "id": "MSG-001",
            },
            "messageType": "conversation",
            "message": {"conversation": "Cliente respondeu"},
        },
    }

    resposta = asyncio.run(
        _webhook_evolution(payload, background, db, empresa_instancia=empresa)
    )
    assert resposta["status"] == "ok"

    _executar_tarefas_registro(background)
    db.expire_all()

    interacao = (
        db.query(TenantCommercialInteraction)
        .filter(
            TenantCommercialInteraction.empresa_id == empresa.id,
            TenantCommercialInteraction.lead_id == lead.id,
            TenantCommercialInteraction.message_id == "MSG-001",
        )
        .first()
    )
    assert interacao is not None
    assert interacao.direcao == "recebido"
    assert interacao.conteudo == "Cliente respondeu"


def test_webhook_evolution_registra_placeholder_midia_no_tenant(db):
    empresa = make_empresa(db)
    lead = TenantCommercialLead(
        empresa_id=empresa.id,
        nome="Lead Midia",
        nome_empresa="Lead Midia LTDA",
        telefone="5511993334444",
        status_pipeline="novo",
        ativo=True,
    )
    db.add(lead)
    db.commit()

    background = BackgroundTasks()
    payload = {
        "event": "messages.upsert",
        "instance": "tenant-inst",
        "data": {
            "key": {
                "fromMe": False,
                "remoteJid": "5511993334444@s.whatsapp.net",
                "id": "MSG-IMG-1",
            },
            "messageType": "imageMessage",
            "message": {"imageMessage": {"mimetype": "image/jpeg"}},
        },
    }

    resposta = asyncio.run(
        _webhook_evolution(payload, background, db, empresa_instancia=empresa)
    )
    assert resposta["status"] == "ignored"

    _executar_tarefas_registro(background)
    db.expire_all()

    interacao = (
        db.query(TenantCommercialInteraction)
        .filter(
            TenantCommercialInteraction.empresa_id == empresa.id,
            TenantCommercialInteraction.lead_id == lead.id,
            TenantCommercialInteraction.message_id == "MSG-IMG-1",
        )
        .first()
    )
    assert interacao is not None
    assert interacao.conteudo == "[imagem recebida]"
    assert interacao.direcao == "recebido"


def test_registrar_interacao_sem_lead_gera_auditlog(db):
    empresa = make_empresa(db)

    ok = asyncio.run(
        registrar_interacao_whatsapp(
            empresa_id=empresa.id,
            telefone="5511990001122",
            mensagem="Lead ainda não cadastrado",
            direcao="recebido",
            message_id="NO-LEAD-001",
            db=db,
        )
    )
    assert ok is False

    db.expire_all()
    registro = (
        db.query(AuditLog)
        .filter(
            AuditLog.empresa_id == empresa.id,
            AuditLog.acao == "whatsapp_inbound_nao_vinculado",
        )
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert registro is not None
    assert "NO-LEAD-001" in (registro.detalhes or "")
