import pytest

from app.core.auth import criar_token
from app.models.models import DocumentoEmpresa, StatusDocumentoEmpresa
from tests.conftest import (
    make_cliente,
    make_empresa,
    make_orcamento,
    make_usuario,
)


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestOrcamentosDocumentosDisponiveisPermissao:
    @pytest.mark.asyncio
    async def test_requer_documentos_leitura_alem_de_orcamentos_leitura(
        self, db, client
    ):
        emp = make_empresa(db)
        cli = make_cliente(db, emp)
        usr = make_usuario(db, emp, is_gestor=False)
        usr.token_versao = 1
        usr.permissoes = {"orcamentos": "leitura"}
        db.commit()

        orc = make_orcamento(db, emp, cli, usr)

        # Mesmo sem documentos cadastrados, o endpoint deve ser protegido por permissão.
        token = criar_token(data={"sub": str(usr.id), "v": 1})

        r = await client.get(
            f"/api/v1/orcamentos/{orc.id}/documentos/disponiveis",
            headers=_auth_headers(token),
        )
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_permite_quando_tem_documentos_leitura(self, db, client):
        emp = make_empresa(db)
        cli = make_cliente(db, emp)
        usr = make_usuario(db, emp, is_gestor=False)
        usr.token_versao = 1
        usr.permissoes = {"orcamentos": "leitura", "documentos": "leitura"}
        db.commit()

        orc = make_orcamento(db, emp, cli, usr)

        # Cria um documento ativo para confirmar retorno 200 + lista.
        doc = DocumentoEmpresa(
            empresa_id=emp.id,
            criado_por_id=usr.id,
            nome="Doc Teste",
            slug="doc-teste",
            status=StatusDocumentoEmpresa.ATIVO,
        )
        db.add(doc)
        db.commit()

        token = criar_token(data={"sub": str(usr.id), "v": 1})

        r = await client.get(
            f"/api/v1/orcamentos/{orc.id}/documentos/disponiveis",
            headers=_auth_headers(token),
        )
        assert r.status_code == 200
        assert isinstance(r.json(), list)
