"""Portfólio: listagem para grade e geração com servicos_ids."""

from decimal import Decimal
from unittest.mock import patch

import pytest

from tests.conftest import make_empresa, make_usuario


def _auth(usuario):
    from app.core.auth import criar_token

    return {"Authorization": "Bearer " + criar_token(data={"sub": str(usuario.id), "v": usuario.token_versao})}


@pytest.fixture
def empresa_catalogo(db):
    emp = make_empresa(db, nome="Empresa Portfólio Cat")
    db.commit()
    db.refresh(emp)
    return emp


def test_listar_produtos_para_portfolio(http_client, db, empresa_catalogo):
    from app.models.models import CategoriaCatalogo, Servico

    usuario = make_usuario(db, empresa_catalogo, is_gestor=True)
    usuario.token_versao = 1
    db.commit()
    db.refresh(usuario)

    cat = CategoriaCatalogo(empresa_id=empresa_catalogo.id, nome="Grupo A")
    db.add(cat)
    db.flush()
    s1 = Servico(
        empresa_id=empresa_catalogo.id,
        nome="Item Alfa",
        preco_padrao=Decimal("10.00"),
        ativo=True,
        categoria_id=cat.id,
        imagem_url="https://exemplo.invalid/img.png",
    )
    s2 = Servico(
        empresa_id=empresa_catalogo.id,
        nome="Item Beta",
        preco_padrao=Decimal("20.00"),
        ativo=True,
        categoria_id=cat.id,
        imagem_url=None,
    )
    db.add_all([s1, s2])
    db.commit()

    r = http_client.get(
        "/api/v1/catalogo/portfolio/produtos",
        headers=_auth(usuario),
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    ids = {row["id"] for row in data}
    assert s1.id in ids and s2.id in ids

    r2 = http_client.get(
        f"/api/v1/catalogo/portfolio/produtos?categoria_id={cat.id}&apenas_com_imagem=true",
        headers=_auth(usuario),
    )
    assert r2.status_code == 200
    apenas = r2.json()
    assert len(apenas) == 1
    assert apenas[0]["id"] == s1.id


@patch("app.routers.catalogo.gerar_pdf_portfolio", return_value=b"%PDF-1 teste")
def test_portfolio_pdf_com_servicos_ids(_mock_pdf, http_client, db, empresa_catalogo):
    from app.models.models import CategoriaCatalogo, Servico

    usuario = make_usuario(db, empresa_catalogo, is_gestor=True)
    usuario.token_versao = 1
    db.commit()
    db.refresh(usuario)

    cat = CategoriaCatalogo(empresa_id=empresa_catalogo.id, nome="Cat X")
    db.add(cat)
    db.flush()
    s1 = Servico(
        empresa_id=empresa_catalogo.id,
        nome="Só Este",
        descricao="d1",
        preco_padrao=Decimal("15.50"),
        preco_custo=Decimal("5.00"),
        ativo=True,
        categoria_id=cat.id,
    )
    s2 = Servico(
        empresa_id=empresa_catalogo.id,
        nome="Outro",
        preco_padrao=Decimal("99.00"),
        ativo=True,
        categoria_id=cat.id,
    )
    db.add_all([s1, s2])
    db.commit()

    payload = {
        "titulo": "Portfólio Unit",
        "servicos_ids": [s1.id],
        "exibir_preco_venda": True,
        "incluir_custo": True,
        "tema": "classico",
    }
    r = http_client.post(
        "/api/v1/catalogo/portfolio/pdf",
        json=payload,
        headers=_auth(usuario),
    )
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")


def test_portfolio_html_servicos_ids_fora_do_tenant(http_client, db, empresa_catalogo):
    """IDs de outra empresa não entram no portfólio."""
    from app.models.models import CategoriaCatalogo, Servico

    usuario = make_usuario(db, empresa_catalogo, is_gestor=True)
    usuario.token_versao = 1
    db.commit()
    db.refresh(usuario)

    outra = make_empresa(db, nome="Outra Empresa")
    db.flush()
    cat_o = CategoriaCatalogo(empresa_id=outra.id, nome="Lá")
    db.add(cat_o)
    db.flush()
    srv_outro = Servico(
        empresa_id=outra.id,
        nome="Produto vizinho",
        preco_padrao=Decimal("1.00"),
        ativo=True,
        categoria_id=cat_o.id,
    )
    db.add(srv_outro)
    db.commit()

    payload = {
        "titulo": "Vazio",
        "servicos_ids": [srv_outro.id],
        "tema": "classico",
    }
    r = http_client.post(
        "/api/v1/catalogo/portfolio/html",
        json=payload,
        headers=_auth(usuario),
    )
    assert r.status_code == 200
    body = r.text
    assert "Produto vizinho" not in body
