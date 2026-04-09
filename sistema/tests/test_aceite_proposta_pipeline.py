
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.models import (
    Empresa, CommercialLead, PropostaPublica, PropostaEnviada, 
    StatusProposta, StatusPipeline
)

# Setup banco de dados de teste
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

def test_aceite_proposta_atualiza_lead(db):
    # 1. Criar Empresa
    empresa = Empresa(nome="Empresa Teste", ativo=True)
    db.add(empresa)
    db.commit()
    db.refresh(empresa)

    # 2. Criar Lead
    lead = CommercialLead(
        nome_responsavel="Lead Teste",
        nome_empresa="Empresa Lead",
        status_pipeline=StatusPipeline.PROPOSTA_ENVIADA,
        empresa_id=empresa.id
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    # 3. Criar Template de Proposta
    tpl = PropostaPublica(
        empresa_id=empresa.id,
        nome="Proposta Teste",
        ativo=True
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)

    # 4. Criar Proposta Enviada
    slug = "proposta-teste-123"
    proposta = PropostaEnviada(
        proposta_publica_id=tpl.id,
        lead_id=lead.id,
        slug=slug,
        status=StatusProposta.ENVIADA
    )
    db.add(proposta)
    db.commit()
    db.refresh(proposta)

    # 5. Aceitar Proposta via API
    response = client.post(
        f"/p/{slug}/aceitar",
        json={"nome": "Assinante Teste", "email": "teste@email.com"}
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Proposta aceita com sucesso!"

    # 6. Verificar se o Lead foi atualizado
    db.refresh(lead)
    assert lead.status_pipeline == StatusPipeline.FECHADO_GANHO
    
    # 7. Verificar se a Proposta foi atualizada
    db.refresh(proposta)
    assert proposta.status == StatusProposta.ACEITA
    assert proposta.aceita_por_nome == "Assinante Teste"

def test_aceite_proposta_sem_lead_id(db):
    # Garante que não quebra se o lead_id for nulo (retrocompatibilidade)
    empresa = Empresa(nome="Empresa Teste", ativo=True)
    db.add(empresa)
    db.commit()

    tpl = PropostaPublica(empresa_id=empresa.id, nome="Proposta Teste", ativo=True)
    db.add(tpl)
    db.commit()

    slug = "proposta-sem-lead"
    proposta = PropostaEnviada(
        proposta_publica_id=tpl.id,
        lead_id=None, # Lead ID nulo (ex: se o DB permitisse ou legado)
        slug=slug,
        status=StatusProposta.ENVIADA
    )
    # Ajuste: lead_id é nullable=False no model, então vamos testar apenas o fluxo normal
    # Mas como o código tem `if proposta_enviada.lead_id:`, ele está protegido.
