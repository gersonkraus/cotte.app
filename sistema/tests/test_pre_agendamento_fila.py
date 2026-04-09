"""Fila de pré-agendamento pós-aprovação (z018)."""

from unittest.mock import MagicMock, patch

from app.models.models import ModoAgendamentoOrcamento, StatusOrcamento
from app.services import agendamento_auto_service


def test_processar_enfileira_quando_somente_apos_liberacao():
    db = MagicMock()
    orc = MagicMock()
    orc.id = 5
    orc.empresa_id = 1
    orc.numero = "ORC-1-26"
    orc.agendamento_modo = ModoAgendamentoOrcamento.OPCIONAL
    orc.agendamento_opcoes_pendente_liberacao = False

    emp = MagicMock()
    emp.utilizar_agendamento_automatico = True
    emp.agendamento_opcoes_somente_apos_liberacao = True

    db.query.return_value.filter.return_value.first.return_value = emp

    out = agendamento_auto_service.processar_agendamento_apos_aprovacao(
        db, orc, canal="publico"
    )
    assert out == {"situacao": "fila_pre_agendamento", "orcamento_id": 5}
    assert orc.agendamento_opcoes_pendente_liberacao is True
    assert orc.aprovado_canal == "publico"
    db.add.assert_called_once()


def test_processar_chama_criar_automatico_quando_imediato():
    db = MagicMock()
    orc = MagicMock()
    orc.id = 7
    orc.empresa_id = 1
    orc.agendamento_modo = ModoAgendamentoOrcamento.OBRIGATORIO
    orc.agendamento_opcoes_pendente_liberacao = False

    emp = MagicMock()
    emp.utilizar_agendamento_automatico = True
    emp.agendamento_opcoes_somente_apos_liberacao = False

    db.query.return_value.filter.return_value.first.return_value = emp

    with patch.object(
        agendamento_auto_service,
        "criar_agendamento_automatico",
        return_value={"agendamento_id": 99},
    ) as m_criar:
        out = agendamento_auto_service.processar_agendamento_apos_aprovacao(
            db, orc, canal="manual", usuario_id=3
        )
    m_criar.assert_called_once_with(db, orc, usuario_id=3)
    assert out == {"agendamento_id": 99}


def test_liberar_bloqueia_sem_pagamento_100():
    db = MagicMock()
    empresa = MagicMock()
    empresa.id = 1
    empresa.agendamento_exige_pagamento_100 = True

    orc = MagicMock()
    orc.id = 10
    orc.empresa_id = 1
    orc.status = StatusOrcamento.APROVADO
    orc.agendamento_opcoes_pendente_liberacao = True

    q_emp = MagicMock()
    q_emp.filter.return_value.first.return_value = empresa
    q_orc = MagicMock()
    q_orc.filter.return_value.first.return_value = orc

    def query_side(model):
        if model is agendamento_auto_service.Empresa:
            return q_emp
        if model is agendamento_auto_service.Orcamento:
            return q_orc
        m = MagicMock()
        m.filter.return_value.first.return_value = None
        return m

    db.query.side_effect = query_side

    with patch(
        "app.services.agendamento_service._verificar_pagamento_100",
        return_value=False,
    ):
        with patch(
            "app.services.agendamento_service.percentual_pago_orcamento",
            return_value=40.0,
        ):
            res = agendamento_auto_service.liberar_pre_agendamento_lote(
                db, 1, [10], usuario_id=2
            )
    assert res[0]["ok"] is False
    assert "100%" in res[0]["detalhe"]
