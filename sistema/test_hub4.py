import sys
import os
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.DEBUG)

sys.path.insert(0, os.path.dirname(__file__))
load_dotenv("/home/gk/Projeto-izi/sistema/.env")

import asyncio
from app.core.database import SessionLocal
from app.models.models import Usuario
from app.services.cotte_ai_hub import _v2_build_listar_orcamentos_fastpath_response

async def run():
    db = SessionLocal()
    user = db.query(Usuario).filter(Usuario.empresa_id == 1).first()
    res = await _v2_build_listar_orcamentos_fastpath_response(mensagem="liste os orçamentos aprovados", db=db, current_user=user)
    print("res:", res)
    
asyncio.run(run())
