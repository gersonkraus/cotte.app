#!/usr/bin/env python
"""Script para verificar estado do banco de dados comercial."""
import os
os.chdir('/home/gk/Projeto-izi/sistema')

from app.core.database import async_session
from sqlalchemy import text
import asyncio

async def main():
    async with async_session() as session:
        # Verificar tabelas
        result = await session.execute(text("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename LIKE 'commercial%'
            ORDER BY tablename
        """))
        tables = [row[0] for row in result]
        print("=== Tabelas comerciais ===")
        for t in tables:
            print(f"  - {t}")
        
        if 'commercial_leads' in tables:
            print("\n=== Colunas de commercial_leads ===")
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'commercial_leads' 
                ORDER BY ordinal_position
            """))
            cols = [row[0] for row in result]
            for c in cols:
                print(f"  - {c}")
            
            # Verificar FKs
            print("\n=== Foreign Keys de commercial_leads ===")
            result = await session.execute(text("""
                SELECT conname, confrelid::regclass, conrelid::regclass
                FROM pg_constraint
                WHERE conrelid = 'commercial_leads'::regclass
                AND contype = 'f'
            """))
            for row in result:
                print(f"  - {row[0]}: -> {row[1]}")

asyncio.run(main())
