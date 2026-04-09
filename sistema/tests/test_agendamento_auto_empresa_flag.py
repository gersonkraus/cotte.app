"""Agendamento automático respeita utilizar_agendamento_automatico da empresa."""

from unittest.mock import MagicMock

from app.models.models import ModoAgendamentoOrcamento
from app.services import agendamento_auto_service


def test_criar_automatico_retorna_none_quando_empresa_desliga():
    db = MagicMock()
    orc = MagicMock()
    orc.id = 1
    orc.empresa_id = 10
    orc.agendamento_modo = ModoAgendamentoOrcamento.OPCIONAL

    emp = MagicMock()
    emp.utilizar_agendamento_automatico = False

    db.query.return_value.filter.return_value.first.return_value = emp

    assert agendamento_auto_service.criar_agendamento_automatico(db, orc) is None
