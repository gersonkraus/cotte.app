"""
Script para verificar URLs salvas no banco de dados.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
from app.models.models import DocumentoEmpresa, Servico, Empresa

def verificar_urls():
    """Verifica URLs salvas no banco."""
    
    db = SessionLocal()
    
    try:
        print("🔍 Verificando URLs no banco de dados...\n")
        
        # Verificar documentos
        documentos = db.query(DocumentoEmpresa).limit(10).all()
        print(f"📄 Documentos (primeiros 10):")
        if documentos:
            for doc in documentos:
                print(f"   ID {doc.id}: {doc.arquivo_path}")
        else:
            print("   Nenhum documento encontrado")
        print()
        
        # Verificar serviços
        servicos = db.query(Servico).filter(Servico.imagem_url.isnot(None)).limit(10).all()
        print(f"🖼️  Imagens de serviços (primeiros 10):")
        if servicos:
            for srv in servicos:
                print(f"   ID {srv.id}: {srv.imagem_url}")
        else:
            print("   Nenhuma imagem encontrada")
        print()
        
        # Verificar empresas
        empresas = db.query(Empresa).filter(Empresa.logo_url.isnot(None)).limit(10).all()
        print(f"🏢 Logos de empresas (primeiros 10):")
        if empresas:
            for emp in empresas:
                print(f"   ID {emp.id}: {emp.logo_url}")
        else:
            print("   Nenhum logo encontrado")
        print()
        
        # Buscar especificamente por URLs do R2
        docs_r2 = db.query(DocumentoEmpresa).filter(
            DocumentoEmpresa.arquivo_path.like('%r2.cloudflarestorage.com%')
        ).all()
        print(f"📊 Documentos com URL do R2 storage: {len(docs_r2)}")
        
        servicos_r2 = db.query(Servico).filter(
            Servico.imagem_url.like('%r2.cloudflarestorage.com%')
        ).all()
        print(f"📊 Serviços com URL do R2 storage: {len(servicos_r2)}")
        
        empresas_r2 = db.query(Empresa).filter(
            Empresa.logo_url.like('%r2.cloudflarestorage.com%')
        ).all()
        print(f"📊 Empresas com URL do R2 storage: {len(empresas_r2)}")
        
    finally:
        db.close()


if __name__ == "__main__":
    verificar_urls()
