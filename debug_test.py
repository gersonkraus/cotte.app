import asyncio
from unittest.mock import AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.models import Base, Empresa, Usuario
from app.services.cotte_ai_hub import assistente_v2_stream_core
import app.services.ia_service as ia_service_module

engine = create_engine('sqlite:///:memory:')
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

emp = Empresa(nome="Teste")
db.add(emp)
db.commit()
user = Usuario(empresa_id=emp.id, nome="User")
db.add(user)
db.commit()

async def fake_chat(messages, tools=None, **kw):
    return {"choices": [{"message": {"content": "Resumo final do orçamento."}, "finish_reason": "stop"}]}

async def fake_chat_stream(messages, **kw):
    yield "Resumo "
    yield "final."

ia_service_module.ia_service.chat = fake_chat
ia_service_module.ia_service.chat_stream = fake_chat_stream

async def run():
    gen = assistente_v2_stream_core(
        mensagem="me diga os pendentes",
        sessao_id="sess-stream-final-text",
        db=db,
        current_user=user,
    )
    async for event in gen:
        print(repr(event))

asyncio.run(run())
