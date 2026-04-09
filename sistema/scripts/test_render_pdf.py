import os
import sys
from datetime import datetime

# Adicionar o caminho da app para os imports funcionarem
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.services.pdf_service import gerar_pdf_orcamento

def test_render():
    orcamento = {
        "numero": "ORC-2026-001",
        "validade_dias": 10,
        "forma_pagamento": "PIX",
        "status": "aprovado",
        "cliente": {
            "nome": "Gerson Kraus",
            "documento": "123.456.789-00",
            "telefone": "(48) 99999-8888",
            "email": "gerson@example.com"
        },
        "itens": [
            {
                "descricao": "Consultoria de Software Especializada",
                "observacoes": "Análise de arquitetura e implementação de IA",
                "quantidade": 1,
                "valor_unit": 1500.0,
                "total": 1500.0
            },
            {
                "descricao": "Desenvolvimento de Módulo PDF",
                "observacoes": "Migração para WeasyPrint com CSS semântico",
                "quantidade": 10,
                "valor_unit": 200.0,
                "total": 2000.0
            }
        ],
        "desconto": 10,
        "desconto_valor": 350.0,
        "total": 3150.0,
        "observacoes": "Este é um orçamento de teste para validar o novo layout minimalista B2B.\nFavor considerar as condições comerciais anexas.",
        "aceite_nome": "Gerson Kraus",
        "aceite_em": "03/04/2026 14:30",
        "aceite_ip": "127.0.0.1"
    }

    empresa = {
        "nome": "Precision Atelier",
        "cor_primaria": "#00a372",
        "cnpj": "00.000.000/0001-00",
        "endereco": "Rua Tecnológica, 123 - Florianópolis/SC",
        "telefone": "(48) 3333-4444",
        "email": "contato@precision.com",
        "logo_url": "../static/logos/empresa_5_4a50f6b9.png",
        "template_orcamento": "moderno"
    }

    print("Gerando PDF Moderno (WeasyPrint)...")
    try:
        pdf_bytes = gerar_pdf_orcamento(orcamento, empresa)
        output_path = "test_orcamento_moderno.pdf"
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
        print(f"Sucesso! PDF Moderno gerado em: {os.path.abspath(output_path)}")
    except Exception as e:
        print(f"Erro ao gerar PDF Moderno: {e}")

    print("\nGerando PDF Clássico (FPDF2)...")
    empresa["template_orcamento"] = "classico"
    try:
        pdf_bytes = gerar_pdf_orcamento(orcamento, empresa)
        output_path = "test_orcamento_classico.pdf"
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
        print(f"Sucesso! PDF Clássico gerado em: {os.path.abspath(output_path)}")
    except Exception as e:
        print(f"Erro ao gerar PDF Clássico: {e}")

if __name__ == "__main__":
    test_render()
