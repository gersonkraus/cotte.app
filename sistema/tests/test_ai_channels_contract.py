import pytest
from pydantic import ValidationError
from app.ai.channels.types import ChannelMessage
from app.ai.channels.web import from_web_payload
from app.ai.channels.whatsapp import from_whatsapp_payload
from app.ai.channels.voice import from_voice_payload

def test_from_web_payload_with_mensagem():
    payload = {
        "mensagem": "Hello Web",
        "empresa_id": 1,
        "usuario_id": 2,
        "sessao_id": "sess-123",
        "engine": "default",
        "contexto_operacional": {"foo": "bar"}
    }
    msg = from_web_payload(payload)
    assert msg.channel == "web"
    assert msg.text == "Hello Web"
    assert msg.empresa_id == 1
    assert msg.usuario_id == 2
    assert msg.sessao_id == "sess-123"
    assert msg.metadata["engine"] == "default"
    assert msg.metadata["contexto_operacional"] == {"foo": "bar"}

def test_from_web_payload_with_texto():
    payload = {
        "texto": "Hello Text",
        "empresa_id": 5
    }
    msg = from_web_payload(payload)
    assert msg.channel == "web"
    assert msg.text == "Hello Text"
    assert msg.empresa_id == 5

def test_from_whatsapp_payload():
    msg = from_whatsapp_payload(
        empresa_id=10,
        telefone="5511999999999",
        mensagem="Hello WhatsApp",
        contexto_extra={"push": True}
    )
    assert msg.channel == "whatsapp"
    assert msg.text == "Hello WhatsApp"

def test_from_voice_payload():
    msg = from_voice_payload(
        empresa_id=20,
        texto_transcrito="Hello Voice",
        usuario_id=99,
        sessao_id="voice-sess"
    )
    assert msg.channel == "voice"
    assert msg.text == "Hello Voice"

# --- NEW TESTS FOR REVIEW REQUIRMENTS ---

def test_from_web_payload_missing_empresa_id_raises_validation_error():
    # Should raise Pydantic's ValidationError instead of KeyError
    payload = {"mensagem": "teste"}
    with pytest.raises(ValidationError):
        from_web_payload(payload)

def test_from_web_payload_explicit_none_text():
    # Ensure explicit None in text fields doesn't break schema
    payload = {"mensagem": None, "texto": None, "empresa_id": 1}
    msg = from_web_payload(payload)
    assert msg.text == ""

def test_from_web_payload_metadata_deepcopy():
    # Test mutability is prevented via deepcopy
    original_context = {"key": "val", "nested": [1, 2]}
    payload = {"empresa_id": 1, "contexto_operacional": original_context}
    msg = from_web_payload(payload)
    
    # mutate original
    original_context["nested"].append(3)
    
    assert msg.metadata["contexto_operacional"]["nested"] == [1, 2]

def test_from_whatsapp_payload_metadata_deepcopy():
    original_context = {"foo": ["bar"]}
    msg = from_whatsapp_payload(empresa_id=1, telefone="123", mensagem="teste", contexto_extra=original_context)
    
    # mutate original
    original_context["foo"].append("baz")
    
    assert msg.metadata["foo"] == ["bar"]

def test_from_voice_payload_none_text():
    msg = from_voice_payload(empresa_id=1, texto_transcrito=None)
    assert msg.text == ""
