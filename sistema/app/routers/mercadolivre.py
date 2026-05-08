from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.auth import exigir_permissao, get_usuario_atual
from app.core.database import get_db
from app.core.tenant_context import set_tenant_context
from app.services.mercadolivre_service import MercadoLivreService

router = APIRouter(prefix="/mercadolivre", tags=["Mercado Livre"])


def _frontend_integracoes_url(resultado: str, detalhe: str = "") -> str:
    query = {"ml": resultado}
    if detalhe:
        query["msg"] = detalhe[:180]
    return f"/app/configuracoes.html?{urlencode(query)}#integracoes"


@router.get("/auth/url")
def obter_url_autorizacao(
    usuario=Depends(exigir_permissao("configuracoes", "escrita")),
    db: Session = Depends(get_db),
):
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    service = MercadoLivreService(db)
    data = service.build_auth_url(usuario.empresa_id)
    return {"success": True, "data": data}


@router.get("/oauth/callback")
async def oauth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if error:
        return RedirectResponse(
            _frontend_integracoes_url("error", f"Autorização negada: {error}"),
            status_code=302,
        )
    if not code or not state:
        return RedirectResponse(
            _frontend_integracoes_url("error", "Parâmetros de callback ausentes."),
            status_code=302,
        )

    service = MercadoLivreService(db)
    try:
        await service.process_oauth_callback(code=code, state=state)
    except HTTPException as exc:
        db.rollback()
        return RedirectResponse(
            _frontend_integracoes_url("error", str(exc.detail)),
            status_code=302,
        )
    except Exception:
        db.rollback()
        return RedirectResponse(
            _frontend_integracoes_url("error", "Falha inesperada no callback OAuth."),
            status_code=302,
        )
    return RedirectResponse(_frontend_integracoes_url("connected"), status_code=302)


@router.get("/status")
def status_integracao(
    usuario=Depends(exigir_permissao("configuracoes", "leitura")),
    db: Session = Depends(get_db),
):
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    service = MercadoLivreService(db)
    data = service.get_status(usuario.empresa_id)
    return {"success": True, "data": data}


@router.post("/sync/pedidos")
async def sincronizar_pedidos(
    limit: int = Query(default=50, ge=1, le=200),
    usuario=Depends(exigir_permissao("configuracoes", "escrita")),
    db: Session = Depends(get_db),
):
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    service = MercadoLivreService(db)
    data = await service.sync_pedidos(usuario.empresa_id, limit=limit)
    return {"success": True, "data": data}


@router.post("/sync/anuncios")
async def sincronizar_anuncios(
    limit: int = Query(default=50, ge=1, le=100),
    usuario=Depends(exigir_permissao("configuracoes", "escrita")),
    db: Session = Depends(get_db),
):
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    service = MercadoLivreService(db)
    data = await service.sync_anuncios(usuario.empresa_id, limit=limit)
    return {"success": True, "data": data}


@router.delete("/desconectar")
def desconectar_integracao(
    usuario=Depends(exigir_permissao("configuracoes", "escrita")),
    db: Session = Depends(get_db),
):
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    service = MercadoLivreService(db)
    data = service.disconnect(usuario.empresa_id)
    return {"success": True, "data": data}
