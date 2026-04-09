#!/usr/bin/env python
"""Script para verificar dados nas tabelas comerciais."""
import os
os.chdir('/home/gk/Projeto-izi/sistema')

from app.core.database import async_session
from sqlalchemy import text
import asyncio

async def main():
    async with async_session() as session:
        # Contar registros em cada tabela
        tables = ['commercial_leads', 'commercial_segments', 'commercial_lead_sources']
        print("=== Contagem de registros ===")
        for table in tables:
            result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            print(f"  {table}: {count} registros")
        
        # Verificar se há leads
        print("\n=== Primeiros 3 leads ===")
        result = await session.execute(text("""
            SELECT id, nome_responsavel, nome_empresa, status_pipeline, ativo
            FROM commercial_leads 
            LIMIT 3
        """))
        for row in result:
            print(f"  ID: {row[0]}, Responsável: {row[1]}, Empresa: {row[2]}, Status: {row[3]}, Ativo: {row[4]}")
        
        # Verificar segmentos
        print("\n=== Segmentos ===")
        result = await session.execute(text("SELECT id, nome FROM commercial_segments ORDER BY id"))
        for row in result:
            print(f"  ID: {row[0]}, Nome: {row[1]}")
        
        # Verificar origens
        print("\n=== Origens de Lead ===")
        result = await session.execute(text("SELECT id, nome FROM commercial_lead_sources ORDER BY id"))
        for row in result:
            print(f"  ID: {row[0]}, Nome: {row[1]}")

asyncio.run(main())
