"""
Script para migrar URLs do R2 de storage interno para URL pública.

Corrige arquivos que foram salvos com:
  https://ACCOUNT_ID.r2.cloudflarestorage.com/...
  
Para:
  https://pub-xxx.r2.dev/...
  ou
  https://seu-dominio-customizado.com/...

Uso:
  python scripts/migrar_urls_r2.py
"""

import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
from app.models.models import DocumentoEmpresa, Servico, Empresa
from app.core.config import settings

def migrar_urls():
    """Migra URLs de storage interno para URL pública."""
    
    if not settings.R2_PUBLIC_URL:
        print("❌ ERRO: R2_PUBLIC_URL não está configurada no .env")
        print("Configure a variável R2_PUBLIC_URL antes de executar este script.")
        return
    
    public_url = settings.R2_PUBLIC_URL.rstrip("/")
    # Busca por qualquer URL de r2.cloudflarestorage.com
    storage_pattern = "%.r2.cloudflarestorage.com%"
    
    print(f"🔄 Migrando URLs de R2...")
    print(f"   De: *.r2.cloudflarestorage.com")
    print(f"   Para: {public_url}")
    print()
    
    db = SessionLocal()
    
    try:
        # Migrar documentos
        documentos = db.query(DocumentoEmpresa).filter(
            DocumentoEmpresa.arquivo_path.like(storage_pattern)
        ).all()
        
        print(f"📄 Documentos encontrados: {len(documentos)}")
        for doc in documentos:
            old_url = doc.arquivo_path
            # Extrai apenas o path após .r2.cloudflarestorage.com
            if ".r2.cloudflarestorage.com/" in old_url:
                path = old_url.split(".r2.cloudflarestorage.com/", 1)[1]
                new_url = f"{public_url}/{path}"
                doc.arquivo_path = new_url
                print(f"   ✓ Documento #{doc.id}: {doc.nome}")
        
        if documentos:
            db.commit()
            print(f"   ✅ {len(documentos)} documentos migrados")
        print()
        
        # Migrar imagens de serviços
        servicos = db.query(Servico).filter(
            Servico.imagem_url.like(storage_pattern)
        ).all()
        
        print(f"🖼️  Imagens de serviços encontradas: {len(servicos)}")
        for srv in servicos:
            old_url = srv.imagem_url
            if ".r2.cloudflarestorage.com/" in old_url:
                path = old_url.split(".r2.cloudflarestorage.com/", 1)[1]
                new_url = f"{public_url}/{path}"
                srv.imagem_url = new_url
                print(f"   ✓ Serviço #{srv.id}: {srv.nome}")
        
        if servicos:
            db.commit()
            print(f"   ✅ {len(servicos)} imagens de serviços migradas")
        print()
        
        # Migrar logos de empresas
        empresas = db.query(Empresa).filter(
            Empresa.logo_url.like(storage_pattern)
        ).all()
        
        print(f"🏢 Logos de empresas encontrados: {len(empresas)}")
        for emp in empresas:
            old_url = emp.logo_url
            if ".r2.cloudflarestorage.com/" in old_url:
                path = old_url.split(".r2.cloudflarestorage.com/", 1)[1]
                new_url = f"{public_url}/{path}"
                emp.logo_url = new_url
                print(f"   ✓ Empresa #{emp.id}: {emp.nome}")
        
        if empresas:
            db.commit()
            print(f"   ✅ {len(empresas)} logos migrados")
        print()
        
        total = len(documentos) + len(servicos) + len(empresas)
        if total > 0:
            print(f"✅ Migração concluída! {total} arquivos atualizados.")
        else:
            print("ℹ️  Nenhum arquivo precisou ser migrado.")
            
    except Exception as e:
        db.rollback()
        print(f"❌ Erro durante migração: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrar_urls()
