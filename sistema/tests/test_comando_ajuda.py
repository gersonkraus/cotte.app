#!/usr/bin/env python3
"""
Teste rápido para verificar se o comando 'ajuda' está funcionando.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.ia_service import interpretar_comando_operador
import asyncio

async def test_ajuda():
    """Testa se o comando 'ajuda' é interpretado corretamente."""
    print("Testando interpretação do comando 'ajuda'...")
    
    # Testa várias variações do comando ajuda
    testes = [
        "ajuda",
        "ajuda por favor",
        "mostra ajuda",
        "quais comandos?",
        "o que posso fazer?",
        "comandos disponíveis"
    ]
    
    for mensagem in testes:
        try:
            resultado = await interpretar_comando_operador(mensagem)
            acao = resultado.get("acao", "").upper()
            print(f"  '{mensagem}' -> acao: {acao}")
            if acao == "AJUDA":
                print(f"    ✓ Reconheceu como AJUDA")
            else:
                print(f"    ✗ Não reconheceu como AJUDA (esperado: AJUDA, obtido: {acao})")
        except Exception as e:
            print(f"  '{mensagem}' -> ERRO: {e}")

async def test_novas_acoes():
    """Testa se as novas ações são reconhecidas."""
    print("\nTestando novas ações...")
    
    testes = [
        ("Como estão as finanças?", "ANALISE_FINANCEIRA"),
        ("Analisar conversão", "ANALISE_CONVERSAO"),
        ("Como aumentar vendas?", "SUGESTOES_NEGOCIO"),
        ("Qual meu ticket médio?", "ANALISE_CONVERSAO"),
        ("Quais clientes devendo?", "SUGESTOES_NEGOCIO"),
    ]
    
    for mensagem, acao_esperada in testes:
        try:
            resultado = await interpretar_comando_operador(mensagem)
            acao = resultado.get("acao", "").upper()
            print(f"  '{mensagem}' -> acao: {acao}")
            if acao == acao_esperada:
                print(f"    ✓ Reconheceu como {acao_esperada}")
            else:
                print(f"    ✗ Esperado: {acao_esperada}, obtido: {acao}")
        except Exception as e:
            print(f"  '{mensagem}' -> ERRO: {e}")

async def main():
    print("=== Teste do Comando Ajuda ===\n")
    await test_ajuda()
    await test_novas_acoes()
    print("\n=== Fim do teste ===")

if __name__ == "__main__":
    asyncio.run(main())