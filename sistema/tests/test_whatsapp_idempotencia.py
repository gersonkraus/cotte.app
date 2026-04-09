import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.services.quote_notification_service import notify_quote_approved
from app.models.models import Orcamento, StatusOrcamento, Empresa, Usuario, Cliente

@pytest.mark.asyncio
async def test_notify_quote_approved_idempotencia(db: Session):
    """Testa se a notificação de aprovação é enviada apenas uma vez (idempotência)."""
    
    # Setup: Criar empresa, usuário e orçamento
    empresa = Empresa(nome="Empresa Teste", telefone_operador="5511999990001", ativo=True)
    db.add(empresa)
    db.commit()
    db.refresh(empresa)
    empresa_id = empresa.id
    
    usuario = Usuario(empresa_id=empresa_id, nome="User Teste", email="test@test.com", senha_hash="fakehash", ativo=True, is_gestor=True)
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    usuario_id = usuario.id
    
    cliente = Cliente(empresa_id=empresa_id, nome="Cliente Teste", telefone="5511988880001")
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    cliente_id = cliente.id
    
    orcamento = Orcamento(
        empresa_id=empresa_id,
        cliente_id=cliente_id,
        criado_por_id=usuario_id,
        numero="ORC-123",
        status=StatusOrcamento.APROVADO,
        total=1000.0,
        approved_notification_sent_at=None
    )
    db.add(orcamento)
    db.commit()
    db.refresh(orcamento)

    # Mock do envio de mensagem
    mock_send = AsyncMock()
    mock_send.return_value = MagicMock(success=True)
    
    # Mock das configurações de WhatsApp
    with patch("app.services.quote_notification_service.send_whatsapp_message", mock_send), \
         patch("app.services.quote_notification_service._is_whatsapp_config_available", return_value=True), \
         patch("app.services.financeiro_service.criar_contas_receber_aprovacao", return_value=None):
        
        # Primeira chamada: deve enviar
        await notify_quote_approved(db, orcamento, source="test")
        assert mock_send.call_count == 1
        
        # Segunda chamada: NÃO deve enviar novamente
        await notify_quote_approved(db, orcamento, source="test")
        assert mock_send.call_count == 1
        
        # Verificar se o campo approved_notification_sent_at foi preenchido
        assert orcamento.approved_notification_sent_at is not None
