from pydantic import BaseModel


class SendResult(BaseModel):
    success: bool
    provider: str | None = None
    normalized_phone: str | None = None
    error: str | None = None
    context: dict | None = None
