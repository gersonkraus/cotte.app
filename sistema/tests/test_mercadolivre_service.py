from app.models.models import StatusOrcamento
from app.services.mercadolivre_service import MercadoLivreService
from app.core.config import settings


def test_status_ml_para_orcamento_mapping():
    assert MercadoLivreService._status_ml_para_orcamento("paid") == StatusOrcamento.APROVADO
    assert MercadoLivreService._status_ml_para_orcamento("payment_required") == StatusOrcamento.AGUARDANDO_PAGAMENTO
    assert MercadoLivreService._status_ml_para_orcamento("cancelled") == StatusOrcamento.RECUSADO
    assert MercadoLivreService._status_ml_para_orcamento("unknown") is None


def test_token_crypto_roundtrip():
    original_secret = settings.ML_TOKEN_CRYPTO_SECRET
    settings.ML_TOKEN_CRYPTO_SECRET = "segredo_teste_ml"
    try:
        service = MercadoLivreService(db=None)  # type: ignore[arg-type]
        plain = "token-super-secreto"
        encrypted = service._encrypt_token(plain)
        assert encrypted and encrypted != plain
        assert service._decrypt_token(encrypted) == plain
    finally:
        settings.ML_TOKEN_CRYPTO_SECRET = original_secret
