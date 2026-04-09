#!/usr/bin/env python3
"""
Teste para verificar onde o conteúdo HTML está sendo salvo no cadastro de documentos.
"""
import sys
import json
from pathlib import Path

# Adiciona o diretório atual ao path
sys.path.append(str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.models.models import DocumentoEmpresa, TipoConteudoDocumento, TipoDocumentoEmpresa, StatusDocumentoEmpresa
from datetime import datetime, timezone

def test_criar_documento_html():
    """Testa a criação de um documento HTML diretamente no banco de dados."""
    db = SessionLocal()
    
    try:
        # Criar um documento HTML de teste
        doc = DocumentoEmpresa(
            empresa_id=5,  # Empresa ID do usuário de teste
            criado_por_id=1,  # Usuário ID
            nome="Teste Documento HTML",
            slug="teste-documento-html",
            tipo=TipoDocumentoEmpresa.CONTRATO,
            descricao="Documento de teste criado via script",
            tipo_conteudo=TipoConteudoDocumento.HTML,
            conteudo_html="<h1>Contrato de Serviço</h1><p>Este é um contrato para o cliente {nome_cliente}.</p><p>Valor: {valor_orcamento}</p><p>Data: {data}</p>",
            variaveis_suportadas=["nome_cliente", "valor_orcamento", "data"],
            arquivo_path=None,  # Importante: NULL para documentos HTML
            arquivo_nome_original=None,
            mime_type="text/html",
            tamanho_bytes=150,
            versao="1.0",
            status=StatusDocumentoEmpresa.ATIVO,
            permite_download=True,
            visivel_no_portal=True,
            criado_em=datetime.now(timezone.utc),
            atualizado_em=datetime.now(timezone.utc)
        )
        
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        print(f"✅ Documento HTML criado com sucesso!")
        print(f"   ID: {doc.id}")
        print(f"   Nome: {doc.nome}")
        print(f"   Tipo Conteúdo: {doc.tipo_conteudo}")
        print(f"   Conteúdo HTML: {len(doc.conteudo_html or '')} caracteres")
        print(f"   Arquivo Path: {doc.arquivo_path}")
        print(f"   Variáveis: {doc.variaveis_suportadas}")
        
        # Verificar se o documento foi salvo corretamente
        doc_db = db.query(DocumentoEmpresa).filter(DocumentoEmpresa.id == doc.id).first()
        if doc_db:
            print(f"\n✅ Documento recuperado do banco:")
            print(f"   ID: {doc_db.id}")
            print(f"   Conteúdo HTML salvo: {'SIM' if doc_db.conteudo_html else 'NÃO'}")
            print(f"   Arquivo Path é NULL: {'SIM' if doc_db.arquivo_path is None else 'NÃO'}")
            print(f"   MIME Type: {doc_db.mime_type}")
            
            # Mostrar primeiros 100 caracteres do conteúdo
            if doc_db.conteudo_html:
                print(f"   Preview conteúdo: {doc_db.conteudo_html[:100]}...")
        
        return doc.id
        
    except Exception as e:
        print(f"❌ Erro ao criar documento: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()

def test_listar_documentos_html():
    """Lista todos os documentos HTML no banco."""
    db = SessionLocal()
    
    try:
        docs = db.query(DocumentoEmpresa).filter(
            DocumentoEmpresa.tipo_conteudo == TipoConteudoDocumento.HTML
        ).all()
        
        print(f"\n📋 Documentos HTML no banco ({len(docs)} encontrados):")
        for doc in docs:
            print(f"  - ID: {doc.id}, Nome: {doc.nome}")
            print(f"    Conteúdo: {len(doc.conteudo_html or '')} chars")
            print(f"    Arquivo Path: {doc.arquivo_path}")
            print(f"    Criado em: {doc.criado_em}")
            print()
            
    finally:
        db.close()

def test_fluxo_completo():
    """Testa o fluxo completo de criação e recuperação."""
    print("=" * 60)
    print("TESTE DE FLUXO DE DOCUMENTO HTML")
    print("=" * 60)
    
    # Primeiro, listar documentos existentes
    test_listar_documentos_html()
    
    # Criar um novo documento
    doc_id = test_criar_documento_html()
    
    if doc_id:
        # Listar novamente para confirmar
        test_listar_documentos_html()
        
        print("\n✅ Teste concluído com sucesso!")
        print(f"   Documento HTML criado e salvo no banco de dados.")
        print(f"   Localização: tabela 'documentos_empresa', coluna 'conteudo_html'")
        print(f"   Arquivo físico: NÃO (arquivo_path = NULL para documentos HTML)")
    else:
        print("\n❌ Teste falhou!")

if __name__ == "__main__":
    test_fluxo_completo()