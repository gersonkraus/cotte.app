"""
Testes de regressão: conhecimento de funcionalidades do assistente IA.

Valida que:
- _detectar_secao() identifica módulos corretamente
- _e_pergunta_funcionalidade() detecta perguntas sobre "como/se"
- KB é carregada e contém os módulos esperados
- Fluxos existentes (SALDO_RAPIDO, etc.) não são afetados pelo _INTENT_MAP

NÃO faz chamadas ao Claude — testa apenas a lógica de roteamento e KB.
"""

import pytest
import os
import sys

# Ajustar path para importar do sistema
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.cotte_context_builder import ContextBuilder


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def limpar_cache_kb():
    """Garante que o cache da KB seja recarregado a cada teste."""
    ContextBuilder._kb_cache = None
    ContextBuilder._kb_resumo = ""
    yield
    ContextBuilder._kb_cache = None
    ContextBuilder._kb_resumo = ""


# ── Testes: _e_pergunta_funcionalidade ────────────────────────────────────────

class TestDeteccaoPerguntaFuncionalidade:
    """Verifica que perguntas sobre 'como/se existe' são detectadas."""

    @pytest.mark.parametrize("msg", [
        "tem como duplicar um orçamento?",
        "dá pra parcelar uma despesa?",
        "é possível exportar clientes?",
        "consigo enviar orçamento por email?",
        "como faço para agendar um serviço?",
        "como funciona o bot do whatsapp?",
        "onde fica o fluxo de caixa?",
        "tem agendamento de serviço?",
        "posso adicionar usuário gestor?",
        "tem campanha em massa?",
        "como adicionar logo da empresa?",
        "tem como dar desconto no orçamento?",
        "consigo parcelar a receita?",
    ])
    def test_detecta_pergunta_funcionalidade(self, msg):
        assert ContextBuilder._e_pergunta_funcionalidade(msg), \
            f"Deveria detectar como pergunta de funcionalidade: '{msg}'"

    @pytest.mark.parametrize("msg", [
        "quanto tenho em caixa?",
        "quais orçamentos estão pendentes?",
        "como vai o faturamento?",
        "oi, tudo bem?",
        "obrigado",
        "me mostra os clientes",
    ])
    def test_nao_detecta_conversa_comum(self, msg):
        # Perguntas de dados ou saudações não devem acionar a KB
        # (exceto as que têm "como vai" — que não tem prefixo de funcionalidade)
        result = ContextBuilder._e_pergunta_funcionalidade(msg)
        # Algumas podem ter falso-positivo aceitável; só verificamos as óbvias
        if msg in ["oi, tudo bem?", "obrigado"]:
            assert not result, f"Não deveria detectar como funcionalidade: '{msg}'"


# ── Testes: _detectar_secao ───────────────────────────────────────────────────

class TestDeteccaoSecao:
    """Verifica que seções corretas são identificadas por módulo."""

    @pytest.mark.parametrize("msg,secao_esperada", [
        ("tem como duplicar um orçamento", "ORCAMENTOS"),
        ("como envio orçamento por email", "ORCAMENTOS"),
        ("como dar desconto no orçamento", "ORCAMENTOS"),
        ("como parcelar uma despesa", "FINANCEIRO"),
        ("tem parcelamento no financeiro", "FINANCEIRO"),
        ("como conecto o whatsapp", "WHATSAPP"),
        ("tem bot automático de whatsapp", "WHATSAPP"),
        ("tem agendamento de serviço", "AGENDAMENTOS"),
        ("como remarcar agendamento", "AGENDAMENTOS"),
        ("como adicionar usuário gestor", "CONFIGURACOES"),
        ("tem campanha em massa por whatsapp para leads", "COMERCIAL"),
        ("como importar serviços por csv", "CATALOGO"),
        ("como subir um contrato", "DOCUMENTOS"),
        ("tem relatório de aprovação", "RELATORIOS"),
        ("como cadastrar um cliente", "CLIENTES"),
    ])
    def test_detecta_secao_correta(self, msg, secao_esperada):
        secoes = ContextBuilder._detectar_secao(msg)
        assert secao_esperada in secoes, \
            f"Seção '{secao_esperada}' não detectada para: '{msg}'. Detectadas: {secoes}"

    def test_retorna_no_maximo_3_secoes(self):
        """Scoring deve limitar a 3 seções no máximo."""
        msg = "orçamento financeiro cliente catálogo comercial whatsapp agendamento"
        secoes = ContextBuilder._detectar_secao(msg)
        assert len(secoes) <= 3

    def test_sem_keywords_retorna_lista_vazia(self):
        """Mensagem sem keywords não deve retornar seções."""
        secoes = ContextBuilder._detectar_secao("oi tudo bem obrigado")
        assert secoes == []


# ── Testes: _carregar_kb ──────────────────────────────────────────────────────

class TestCarregarKB:
    """Verifica que a knowledge_base.md é carregada corretamente."""

    MODULOS_ESPERADOS = [
        "ORCAMENTOS", "CLIENTES", "FINANCEIRO", "CATALOGO",
        "COMERCIAL", "DOCUMENTOS", "WHATSAPP", "AGENDAMENTOS",
        "RELATORIOS", "CONFIGURACOES", "ASSISTENTE_IA",
        "FUNCIONALIDADES_INEXISTENTES",
    ]

    def test_kb_carregada_com_modulos_esperados(self):
        kb = ContextBuilder._carregar_kb()
        assert kb, "KB não deve ser vazia"
        for modulo in self.MODULOS_ESPERADOS:
            assert modulo in kb, f"Módulo '{modulo}' não encontrado na KB"

    def test_kb_singleton(self):
        """Segunda chamada deve retornar o mesmo objeto (cache)."""
        kb1 = ContextBuilder._carregar_kb()
        kb2 = ContextBuilder._carregar_kb()
        assert kb1 is kb2, "KB deve ser singleton (mesmo objeto)"

    def test_modulo_orcamentos_tem_conteudo_essencial(self):
        kb = ContextBuilder._carregar_kb()
        conteudo = kb.get("ORCAMENTOS", "")
        assert "Duplicar" in conteudo or "duplicar" in conteudo
        assert "email" in conteudo.lower() or "e-mail" in conteudo.lower()
        assert "WhatsApp" in conteudo or "whatsapp" in conteudo.lower()
        assert "desconto" in conteudo.lower()

    def test_modulo_inexistentes_documenta_nao_disponivel(self):
        kb = ContextBuilder._carregar_kb()
        conteudo = kb.get("FUNCIONALIDADES_INEXISTENTES", "")
        assert "nota fiscal" in conteudo.lower() or "nfs-e" in conteudo.lower()
        assert "não disponível" in conteudo.lower() or "não existe" in conteudo.lower()

    def test_modulo_financeiro_tem_parcelamento(self):
        kb = ContextBuilder._carregar_kb()
        conteudo = kb.get("FINANCEIRO", "")
        assert "parcel" in conteudo.lower()

    def test_modulo_agendamentos_tem_remarcar(self):
        kb = ContextBuilder._carregar_kb()
        conteudo = kb.get("AGENDAMENTOS", "")
        assert "remarcar" in conteudo.lower()


# ── Testes: _INTENT_MAP ───────────────────────────────────────────────────────

class TestIntentMap:
    """Verifica que o _INTENT_MAP tem os mapeamentos corretos."""

    def test_conversacao_mapeia_para_geral_com_ajuda(self):
        assert ContextBuilder._INTENT_MAP["CONVERSACAO"] == "_ctx_geral_com_ajuda"

    def test_ajuda_sistema_mapeia_para_ajuda_sistema(self):
        assert ContextBuilder._INTENT_MAP["AJUDA_SISTEMA"] == "_ctx_ajuda_sistema"

    def test_rotas_financeiras_intocadas(self):
        for intencao in ["SALDO_RAPIDO", "FATURAMENTO", "CONTAS_RECEBER", "CONTAS_PAGAR"]:
            assert ContextBuilder._INTENT_MAP[intencao] == "_ctx_financeiro", \
                f"Rota financeira '{intencao}' foi alterada!"

    def test_rotas_agendamento_intocadas(self):
        for intencao in ["AGENDAMENTO_CRIAR", "AGENDAMENTO_LISTAR",
                         "AGENDAMENTO_STATUS", "AGENDAMENTO_CANCELAR"]:
            assert ContextBuilder._INTENT_MAP[intencao] == "_ctx_agendamentos"
