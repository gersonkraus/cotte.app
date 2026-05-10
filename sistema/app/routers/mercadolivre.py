from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Header
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.auth import exigir_permissao, get_usuario_atual
from app.core.config import settings
from app.core.database import get_db
from app.core.tenant_context import set_tenant_context
from app.services.mercadolivre_service import MercadoLivreService

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mercadolivre", tags=["Mercado Livre"])


def _frontend_integracoes_url(resultado: str, detalhe: str = "") -> str:
    query = {"ml": resultado}
    if detalhe:
        query["msg"] = detalhe[:400]
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


@router.get("/vinculos/pedidos")
def listar_vinculos_pedidos(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    usuario=Depends(exigir_permissao("orcamentos", "leitura")),
    db: Session = Depends(get_db),
):
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    service = MercadoLivreService(db)
    data = service.list_pedido_vinculos(
        usuario.empresa_id,
        limit=limit,
        offset=offset,
    )
    return {"success": True, "data": data}


@router.get("/vinculos/catalogo")
def listar_vinculos_catalogo(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    usuario=Depends(exigir_permissao("catalogo", "leitura")),
    db: Session = Depends(get_db),
):
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    service = MercadoLivreService(db)
    data = service.list_item_vinculos(
        usuario.empresa_id,
        limit=limit,
        offset=offset,
    )
    return {"success": True, "data": data}


@router.get("/jobs")
def listar_jobs_sync(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    usuario=Depends(exigir_permissao("configuracoes", "leitura")),
    db: Session = Depends(get_db),
):
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    service = MercadoLivreService(db)
    data = service.list_sync_jobs(usuario.empresa_id, limit=limit, offset=offset)
    return {"success": True, "data": data}


@router.post("/vinculos/catalogo/configurar")
def configurar_vinculo_catalogo(
    payload: dict = Body(...),
    usuario=Depends(exigir_permissao("catalogo", "escrita")),
    db: Session = Depends(get_db),
):
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    ml_item_id = str(payload.get("ml_item_id") or "").strip()
    if not ml_item_id:
        raise HTTPException(status_code=400, detail="ml_item_id é obrigatório.")
    try:
        servico_id = int(payload.get("servico_id"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="servico_id inválido.") from exc
    service = MercadoLivreService(db)
    data = service.configurar_item_vinculo(
        empresa_id=usuario.empresa_id,
        ml_item_id=ml_item_id,
        servico_id=servico_id,
        sync_mode=str(payload.get("sync_mode") or "ml_only_pull").strip(),
        allow_push_price=bool(payload.get("allow_push_price", False)),
        allow_push_stock=bool(payload.get("allow_push_stock", False)),
        allow_push_title=bool(payload.get("allow_push_title", False)),
        allow_push_description=bool(payload.get("allow_push_description", False)),
    )
    return {"success": True, "data": data}


@router.delete("/vinculos/catalogo/{servico_id}")
def desvincular_catalogo(
    servico_id: int,
    usuario=Depends(exigir_permissao("catalogo", "escrita")),
    db: Session = Depends(get_db),
):
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    service = MercadoLivreService(db)
    data = service.desvincular_item(empresa_id=usuario.empresa_id, servico_id=servico_id)
    return {"success": True, "data": data}


@router.post("/reprocessar/pedido/{ml_order_id}")
async def reprocessar_pedido(
    ml_order_id: str,
    usuario=Depends(exigir_permissao("orcamentos", "escrita")),
    db: Session = Depends(get_db),
):
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    service = MercadoLivreService(db)
    data = await service.reprocessar_pedido(usuario.empresa_id, ml_order_id)
    return {"success": True, "data": data}


@router.post("/sync/executar")
async def executar_sync_escopo(
    escopo: str = Query(..., pattern="^(pedidos|catalogo_pull|catalogo_push)$"),
    usuario=Depends(exigir_permissao("configuracoes", "escrita")),
    db: Session = Depends(get_db),
):
    set_tenant_context(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
    service = MercadoLivreService(db)
    data = await service.executar_sync_escopo(
        empresa_id=usuario.empresa_id,
        escopo=escopo,
        trigger_source="manual",
    )
    return {"success": True, "data": data}


@router.post("/sync/periodico/run")
async def executar_sync_periodico(
    x_ml_sync_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if not settings.ML_SYNC_CRON_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="Sincronização periódica desabilitada: ML_SYNC_CRON_TOKEN não configurado.",
        )
    if x_ml_sync_token != settings.ML_SYNC_CRON_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido para sync periódico.")
    service = MercadoLivreService(db)
    data = await service.executar_sync_periodico_empresas()
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


@router.post("/notifications")
async def receber_notificacao(
    payload: dict | list = Body(...),
    db: Session = Depends(get_db),
):
    notificacoes = payload if isinstance(payload, list) else [payload]
    service = MercadoLivreService(db)
    try:
        resultado = await service.processar_notificacao_webhook(notificacoes)
    except Exception as exc:
        logger.error("Erro geral ao processar notificações ML: %s", exc)
        resultado = {"total": len(notificacoes), "processadas": 0, "ignoradas": 0, "erros": len(notificacoes)}
    return {"success": True, "data": resultado}
