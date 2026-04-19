import sys
import os
from dotenv import load_dotenv

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
    print("has_more:", res.dados.get("has_more"))
    print("next_cursor:", res.dados.get("next_cursor"))
    print("total:", res.dados.get("total"))
    
asyncio.run(run())
