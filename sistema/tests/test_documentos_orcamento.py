"""Testes para funcionalidade de documentos em orçamentos."""
import pytest
from sqlalchemy.orm import Session

from app.models.models import (
    Orcamento, OrcamentoDocumento, DocumentoEmpresa, Empresa, Cliente, Usuario,
    StatusOrcamento, TipoDocumentoEmpresa, TipoConteudoDocumento
)
from tests.conftest import make_empresa, make_cliente, make_usuario, make_orcamento


@pytest.fixture
def empresa_teste(db: Session):
    return make_empresa(db, nome="Empresa Teste Docs", telefone_operador="5511999990001")


@pytest.fixture
def cliente_teste(db: Session, empresa_teste):
    return make_cliente(db, empresa_teste, nome="Cliente Teste Docs", telefone="5511888880001")


@pytest.fixture
def documento_empresa(db: Session, empresa_teste):
    doc = DocumentoEmpresa(
        empresa_id=empresa_teste.id,
        nome="Certificado de Garantia",
        tipo=TipoDocumentoEmpresa.CERTIFICADO_GARANTIA,
        tipo_conteudo=TipoConteudoDocumento.PDF,
        arquivo_path="/uploads/teste/certificado.pdf",
        permite_download=True,
        visivel_no_portal=True
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@pytest.fixture
def orcamento_com_documento(db: Session, empresa_teste, cliente_teste, documento_empresa):
    usuario = make_usuario(db, empresa_teste, nome="Operador Teste")
    orc = make_orcamento(
        db, empresa_teste, cliente_teste, usuario,
        status=StatusOrcamento.ENVIADO,
        total=1000.00,
        link_publico="teste-docs-abc123",
        numero="ORC-TEST-DOC-001"
    )
    
    # Vincular documento ao orçamento
    orc_doc = OrcamentoDocumento(
        orcamento_id=orc.id,
        documento_id=documento_empresa.id,
        ordem=1,
        exibir_no_portal=True,
        enviar_por_email=False,
        enviar_por_whatsapp=False,
        obrigatorio=True,
        documento_nome=documento_empresa.nome,
        documento_tipo=documento_empresa.tipo.value,
        arquivo_path=documento_empresa.arquivo_path,
        permite_download=documento_empresa.permite_download
    )
    db.add(orc_doc)
    db.commit()
    db.refresh(orc_doc)
    return orc


class TestDocumentosOrcamento:
    """Testes para funcionalidade de documentos em orçamentos."""
    
    def test_orcamento_tem_documentos_vinculados(self, db: Session, orcamento_com_documento):
        """Verifica se o orçamento tem documentos vinculados."""
        docs = db.query(OrcamentoDocumento).filter(
            OrcamentoDocumento.orcamento_id == orcamento_com_documento.id
        ).all()
        
        assert len(docs) == 1
        assert docs[0].documento_nome == "Certificado de Garantia"
        assert docs[0].obrigatorio == True
        assert docs[0].exibir_no_portal == True
    
    def test_documento_tem_campos_rastreamento(self, db: Session, orcamento_com_documento):
        """Verifica se os documentos têm campos de rastreamento."""
        doc = db.query(OrcamentoDocumento).filter(
            OrcamentoDocumento.orcamento_id == orcamento_com_documento.id
        ).first()
        
        assert doc.visualizado_em is None
        assert doc.aceito_em is None
        assert doc.criado_em is not None
    
    def test_documento_pode_ser_marcado_como_visualizado(self, db: Session, orcamento_com_documento):
        """Verifica se o documento pode ser marcado como visualizado."""
        from datetime import datetime, timezone
        
        doc = db.query(OrcamentoDocumento).filter(
            OrcamentoDocumento.orcamento_id == orcamento_com_documento.id
        ).first()
        
        doc.visualizado_em = datetime.now(timezone.utc)
        db.commit()
        db.refresh(doc)
        
        assert doc.visualizado_em is not None
    
    def test_documento_pode_ser_marcado_como_aceito(self, db: Session, orcamento_com_documento):
        """Verifica se o documento pode ser marcado como aceito."""
        from datetime import datetime, timezone
        
        doc = db.query(OrcamentoDocumento).filter(
            OrcamentoDocumento.orcamento_id == orcamento_com_documento.id
        ).first()
        
        doc.aceito_em = datetime.now(timezone.utc)
        db.commit()
        db.refresh(doc)
        
        assert doc.aceito_em is not None
    
    def test_documento_obrigatorio_tem_flag(self, db: Session, orcamento_com_documento):
        """Verifica se documentos obrigatórios têm a flag correta."""
        doc = db.query(OrcamentoDocumento).filter(
            OrcamentoDocumento.orcamento_id == orcamento_com_documento.id
        ).first()
        
        assert doc.obrigatorio == True
    
    def test_orcamento_sem_documentos_retorna_lista_vazia(self, db: Session, empresa_teste, cliente_teste):
        """Verifica se orçamento sem documentos retorna lista vazia."""
        import secrets
        usuario = make_usuario(db, empresa_teste, nome="Operador Sem Docs")
        orc = make_orcamento(
            db, empresa_teste, cliente_teste, usuario,
            status=StatusOrcamento.ENVIADO,
            total=500.00,
            link_publico=secrets.token_urlsafe(12),
            numero="ORC-TEST-SEM-DOC-001"
        )
        
        docs = db.query(OrcamentoDocumento).filter(
            OrcamentoDocumento.orcamento_id == orc.id
        ).all()
        
        assert len(docs) == 0
