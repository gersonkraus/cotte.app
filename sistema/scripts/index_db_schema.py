"""Script para rodar a indexação do esquema do banco de dados no pgvector."""
import asyncio
import os
import sys

# Adiciona o diretório raiz ao path para importar app
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.ai.rag.schema_indexer import index_all_tables
from app.models.models import AIDatabaseSchemaIndex

async def main():
    from app.models.models import Vector
    print(f"DEBUG: Vector type is {Vector}")
    print("🚀 Iniciando indexação de schema...")
    db = SessionLocal()
    try:
        await index_all_tables(db)
        print("✅ Indexação concluída com sucesso!")
    except Exception as e:
        print(f"❌ Erro na indexação: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
