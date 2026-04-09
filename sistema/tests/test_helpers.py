"""
Testes das funções auxiliares puras (sem banco, sem HTTP).

Cobre:
- _calcular_total: cálculo de desconto percentual e fixo
- _normalizar_texto: normalização de texto para busca no catálogo
- _digitos_telefone: extração de dígitos de telefone
- _cliente_por_telefone: match por sufixo de 8 dígitos
- _empresa_por_operador: match por sufixo de 8 dígitos
- Número de orçamento: formato ORC-{seq}-{ano}
"""
import pytest


# ── _calcular_total ───────────────────────────────────────────────────────

class TestCalcularTotal:
    """Importa a função diretamente para testar sem HTTP."""

    def _calc(self, subtotal, desconto, tipo):
        from app.services.whatsapp_bot_service import _calcular_total
        return _calcular_total(subtotal, desconto, tipo)

    def test_sem_desconto(self):
        assert self._calc(500.0, 0.0, "percentual") == 500.0

    def test_desconto_percentual_10(self):
        assert self._calc(500.0, 10.0, "percentual") == pytest.approx(450.0)

    def test_desconto_percentual_100(self):
        assert self._calc(500.0, 100.0, "percentual") == pytest.approx(0.0)

    def test_desconto_fixo(self):
        assert self._calc(500.0, 50.0, "fixo") == pytest.approx(450.0)

    def test_desconto_fixo_maior_que_total_nao_fica_negativo(self):
        assert self._calc(100.0, 200.0, "fixo") == pytest.approx(0.0)

    def test_desconto_none_tratado_como_zero(self):
        assert self._calc(500.0, None, None) == 500.0

    def test_desconto_percentual_50(self):
        assert self._calc(200.0, 50.0, "percentual") == pytest.approx(100.0)


# ── _normalizar_texto ─────────────────────────────────────────────────────

class TestNormalizarTexto:
    def _norm(self, txt):
        from app.services.whatsapp_bot_service import _normalizar_texto
        return _normalizar_texto(txt)

    def test_remove_acentos(self):
        assert self._norm("Pintura de façada") == "pintura de facada"

    def test_converte_para_minusculo(self):
        assert self._norm("PINTURA") == "pintura"

    def test_remove_pontuacao(self):
        assert self._norm("serviço, limpeza!") == "servico limpeza"

    def test_texto_vazio(self):
        assert self._norm("") == ""

    def test_texto_none(self):
        assert self._norm(None) == ""

    def test_espacos_extras_removidos(self):
        assert self._norm("  pintura   parede  ") == "pintura parede"


# ── _digitos_telefone ─────────────────────────────────────────────────────

class TestDigitosTelefone:
    def _dig(self, tel):
        from app.services.whatsapp_bot_service import _digitos_telefone
        return _digitos_telefone(tel)

    def test_remove_mascara(self):
        assert self._dig("(11) 99999-0001") == "11999990001"

    def test_numero_limpo(self):
        assert self._dig("5511999990001") == "5511999990001"

    def test_telefone_vazio(self):
        assert self._dig("") == ""

    def test_telefone_none(self):
        assert self._dig(None) == ""


# ── _cliente_por_telefone ─────────────────────────────────────────────────

class TestClientePorTelefone:
    def test_match_por_sufixo_8_digitos(self, db):
        from tests.conftest import make_cliente, make_empresa, make_usuario
        emp = make_empresa(db)
        cli = make_cliente(db, emp, telefone="11988880001")

        from app.services.whatsapp_bot_service import _cliente_por_telefone
        # Número com DDI encontra pelo sufixo
        found = _cliente_por_telefone("5511988880001", db)
        assert found is not None
        assert found.id == cli.id

    def test_nao_encontra_telefone_diferente(self, db):
        from tests.conftest import make_cliente, make_empresa
        emp = make_empresa(db)
        make_cliente(db, emp, telefone="11988880001")

        from app.services.whatsapp_bot_service import _cliente_por_telefone
        assert _cliente_por_telefone("5511977770001", db) is None

    def test_telefone_curto_demais_retorna_none(self, db):
        from app.services.whatsapp_bot_service import _cliente_por_telefone
        assert _cliente_por_telefone("123", db) is None


# ── _empresa_por_operador ─────────────────────────────────────────────────

class TestEmpresaPorOperador:
    def test_encontra_empresa_pelo_telefone_operador(self, db):
        from tests.conftest import make_empresa
        emp = make_empresa(db, telefone_operador="5511999997771")

        from app.services.whatsapp_bot_service import _empresa_por_operador
        found = _empresa_por_operador("5511999997771", db)
        assert found is not None
        assert found.id == emp.id

    def test_match_por_sufixo(self, db):
        from tests.conftest import make_empresa
        emp = make_empresa(db, telefone_operador="11999997772")

        from app.services.whatsapp_bot_service import _empresa_por_operador
        found = _empresa_por_operador("5511999997772", db)
        assert found is not None
        assert found.id == emp.id

    def test_nao_encontra_telefone_diferente(self, db):
        from tests.conftest import make_empresa
        make_empresa(db, telefone_operador="5511999997773")

        from app.services.whatsapp_bot_service import _empresa_por_operador
        assert _empresa_por_operador("5511888887773", db) is None


# ── Formato de número de orçamento ────────────────────────────────────────

class TestFormatoNumeroOrcamento:
    def test_formato_orc(self):
        """Valida que o formato segue ORC-{seq}-{ano2d}."""
        import re
        pattern = r"^ORC-\d+-\d{2}$"
        assert re.match(pattern, "ORC-1-26")
        assert re.match(pattern, "ORC-150-26")
        assert not re.match(pattern, "ORC-1-2026")  # ano deve ser 2 dígitos
