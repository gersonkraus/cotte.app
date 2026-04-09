"""
Testes unitários para app/utils/whatsapp_sanitizer.py (SEC-05).

Cobre edge-cases de telefone e mensagem sem dependências externas.
"""
import pytest
from app.utils.whatsapp_sanitizer import sanitizar_telefone, sanitizar_mensagem, MAX_MSG_LEN


class TestSanitizarTelefone:
    def test_telefone_valido_retorna_digitos(self):
        assert sanitizar_telefone("+55 (11) 99999-0001") == "5511999990001"

    def test_telefone_so_digitos_sem_alteracao(self):
        assert sanitizar_telefone("5511999990001") == "5511999990001"

    def test_nenhum_caractere_especial_preserva(self):
        assert sanitizar_telefone("11999990001") == "11999990001"

    def test_none_retorna_none(self):
        assert sanitizar_telefone(None) is None

    def test_string_vazia_retorna_none(self):
        assert sanitizar_telefone("") is None

    def test_muito_curto_retorna_none(self):
        # 7 dígitos — abaixo do mínimo de 8
        assert sanitizar_telefone("1234567") is None

    def test_muito_longo_retorna_none(self):
        # 16 dígitos — acima do máximo de 15
        assert sanitizar_telefone("1234567890123456") is None

    def test_apenas_letras_retorna_none(self):
        assert sanitizar_telefone("abcdefgh") is None

    def test_telefone_com_espacos_e_tracos(self):
        assert sanitizar_telefone("55 11 9999-0001") == "551199990001"

    def test_null_byte_no_telefone_ignorado(self):
        # null bytes devem ser removidos (não são dígitos)
        result = sanitizar_telefone("5511\x009999\x000001")
        assert result == "551199990001"


class TestSanitizarMensagem:
    def test_mensagem_normal_preservada(self):
        assert sanitizar_mensagem("Olá, tudo bem?") == "Olá, tudo bem?"

    def test_none_retorna_none(self):
        assert sanitizar_mensagem(None) is None

    def test_string_vazia_retorna_none(self):
        assert sanitizar_mensagem("") is None

    def test_so_espacos_retorna_none(self):
        assert sanitizar_mensagem("   ") is None

    def test_null_byte_removido(self):
        assert sanitizar_mensagem("oi\x00mundo") == "oimundo"

    def test_caracteres_controle_removidos(self):
        # \x01–\x08 e \x0b-\x1f devem ser removidos
        assert sanitizar_mensagem("a\x01b\x07c\x1fd") == "abcd"

    def test_tab_preservado(self):
        assert sanitizar_mensagem("col1\tcol2") == "col1\tcol2"

    def test_newline_preservado(self):
        assert sanitizar_mensagem("linha1\nlinha2") == "linha1\nlinha2"

    def test_carriage_return_preservado(self):
        assert sanitizar_mensagem("linha1\r\nlinha2") == "linha1\r\nlinha2"

    def test_unicode_normalizado_nfc(self):
        # "café" em NFD (e + combining acute) deve virar NFC
        nfd = "cafe\u0301"   # 5 code points
        resultado = sanitizar_mensagem(nfd)
        assert resultado == "café"
        assert len(resultado) == 4   # NFC: 4 code points

    def test_truncado_no_limite(self):
        longa = "a" * (MAX_MSG_LEN + 500)
        resultado = sanitizar_mensagem(longa)
        assert len(resultado) == MAX_MSG_LEN

    def test_exatamente_no_limite_nao_truncado(self):
        exata = "b" * MAX_MSG_LEN
        assert sanitizar_mensagem(exata) == exata

    def test_espacos_nas_bordas_removidos(self):
        assert sanitizar_mensagem("  olá  ") == "olá"

    def test_mensagem_apenas_controles_retorna_none(self):
        assert sanitizar_mensagem("\x00\x01\x02") is None
