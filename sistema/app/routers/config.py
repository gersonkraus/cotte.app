from fastapi import APIRouter, Header, HTTPException, Query

from app.core.config import settings
from app.services.pricing_config import get_pricing_config
from app.services.email_service import email_habilitado, enviar_email_teste

router = APIRouter(prefix="/config", tags=["Config Pública"])


@router.get("/pricing")
def get_pricing_public():
    """Retorna configuração pública de preços/limites para a landing."""
    return get_pricing_config()


@router.post("/test-email")
def test_email(
    email: str = Query(..., description="E-mail que receberá o teste"),
    x_setup_key: str | None = Header(None, alias="X-Setup-Key"),
):
    """
    Envia um e-mail de teste para o endereço informado.
    Use para validar SMTP (Brevo, etc.) na Railway.
    Requer header: X-Setup-Key com o valor de ADMIN_SETUP_KEY (variável de ambiente).
    """
    if x_setup_key != settings.ADMIN_SETUP_KEY:
        raise HTTPException(status_code=403, detail="Chave de setup inválida")
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="E-mail inválido")
    if not email_habilitado():
        raise HTTPException(
            status_code=503,
            detail="E-mail não configurado. Defina BREVO_API_KEY (recomendado na Railway) ou SMTP_HOST/SMTP_USER/SMTP_PASS.",
        )
    ok, erro = enviar_email_teste(email.strip())
    if ok:
        return {"ok": True, "mensagem": "E-mail de teste enviado. Verifique a caixa de entrada."}
    raise HTTPException(status_code=502, detail=f"Falha ao enviar: {erro}")

