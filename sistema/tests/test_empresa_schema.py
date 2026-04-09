"""
Testes para os validators de EmpresaUpdate.
Cobre: numero_prefixo, numero_prefixo_aprovado, desconto_max_percent.
"""
import pytest
from pydantic import ValidationError
from app.schemas.schemas import EmpresaUpdate


# ── numero_prefixo ────────────────────────────────────────────────────────────

class TestNumeroPrefixo:
    def test_prefixo_valido_simples(self):
        m = EmpresaUpdate(numero_prefixo="ORC")
        assert m.numero_prefixo == "ORC"

    def test_prefixo_convertido_para_maiusculo(self):
        m = EmpresaUpdate(numero_prefixo="orc")
        assert m.numero_prefixo == "ORC"

    def test_prefixo_alfanumerico(self):
        m = EmpresaUpdate(numero_prefixo="ORC2025")
        assert m.numero_prefixo == "ORC2025"

    def test_prefixo_maximo_8_chars(self):
        m = EmpresaUpdate(numero_prefixo="ABCD1234")
        assert m.numero_prefixo == "ABCD1234"

    def test_prefixo_muito_longo_rejeitado(self):
        with pytest.raises(ValidationError) as exc:
            EmpresaUpdate(numero_prefixo="ABCDEFGHI")  # 9 chars
        assert "Prefixo" in str(exc.value)

    def test_prefixo_com_hifen_rejeitado(self):
        with pytest.raises(ValidationError):
            EmpresaUpdate(numero_prefixo="ORC-2025")

    def test_prefixo_com_espaco_rejeitado(self):
        with pytest.raises(ValidationError):
            EmpresaUpdate(numero_prefixo="ORC 25")

    def test_prefixo_none_permitido(self):
        m = EmpresaUpdate(numero_prefixo=None)
        assert m.numero_prefixo is None

    def test_prefixo_aprovado_valido(self):
        m = EmpresaUpdate(numero_prefixo_aprovado="AP")
        assert m.numero_prefixo_aprovado == "AP"

    def test_prefixo_aprovado_none_permitido(self):
        m = EmpresaUpdate(numero_prefixo_aprovado=None)
        assert m.numero_prefixo_aprovado is None

    def test_prefixo_aprovado_com_simbolo_rejeitado(self):
        with pytest.raises(ValidationError):
            EmpresaUpdate(numero_prefixo_aprovado="AP@")


# ── desconto_max_percent ──────────────────────────────────────────────────────

class TestDescontoMaxPercent:
    def test_desconto_zero(self):
        m = EmpresaUpdate(desconto_max_percent=0)
        assert m.desconto_max_percent == 0

    def test_desconto_cem(self):
        m = EmpresaUpdate(desconto_max_percent=100)
        assert m.desconto_max_percent == 100

    def test_desconto_intermediario(self):
        m = EmpresaUpdate(desconto_max_percent=50)
        assert m.desconto_max_percent == 50

    def test_desconto_negativo_rejeitado(self):
        with pytest.raises(ValidationError) as exc:
            EmpresaUpdate(desconto_max_percent=-1)
        assert "desconto_max_percent" in str(exc.value)

    def test_desconto_acima_cem_rejeitado(self):
        with pytest.raises(ValidationError) as exc:
            EmpresaUpdate(desconto_max_percent=101)
        assert "desconto_max_percent" in str(exc.value)

    def test_desconto_none_permitido(self):
        m = EmpresaUpdate(desconto_max_percent=None)
        assert m.desconto_max_percent is None

    def test_desconto_convertido_de_string(self):
        # mode="before" converte string para int antes de validar
        m = EmpresaUpdate(desconto_max_percent="30")
        assert m.desconto_max_percent == 30


# ── campos sem validators não quebram ────────────────────────────────────────

class TestSemValidadores:
    def test_campos_normais_funcionam(self):
        m = EmpresaUpdate(nome="Empresa Teste", email="teste@exemplo.com")
        assert m.nome == "Empresa Teste"
        assert m.email == "teste@exemplo.com"

    def test_objeto_vazio_valido(self):
        m = EmpresaUpdate()
        assert m.nome is None
        assert m.numero_prefixo is None
        assert m.desconto_max_percent is None
