import asyncio
from app.db.session import SessionLocal
from app.models.models import Usuario
from app.services.cotte_ai_hub import _v2_build_listar_orcamentos_fastpath_response

async def run():
    db = SessionLocal()
    user = db.query(Usuario).first()
    res = await _v2_build_listar_orcamentos_fastpath_response(mensagem="listar orçamentos", db=db, current_user=user)
    print(res.dados.get("has_more"))
    print(res.dados.get("next_cursor"))
    print(res.dados.get("total"))
    
asyncio.run(run())
