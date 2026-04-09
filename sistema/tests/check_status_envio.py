#!/usr/bin/env python
"""Script para verificar se a coluna status_envio existe na tabela commercial_leads."""
import os
os.chdir('/home/gk/Projeto-izi/sistema')

from app.core.database import async_session
from sqlalchemy import text
import asyncio

async def main():
    async with async_session() as session:
        result = await session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'commercial_leads' 
            AND column_name = 'status_envio'
        """))
        exists = bool(result.scalar())
        print(f"status_envio exists: {exists}")

asyncio.run(main())