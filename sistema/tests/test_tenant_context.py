from app.core.tenant_context import enable_superadmin_bypass, set_tenant_context
from app.models.models import Cliente, Empresa, Usuario
from app.repositories.cliente_repository import ClienteRepository
from tests.conftest import TestingSessionLocal, make_empresa, make_usuario


def test_tenant_scope_filtra_leituras_automaticamente(db, clean_tables):
    empresa_a = make_empresa(db, nome="Empresa A", telefone_operador="5511999991001")
    empresa_b = make_empresa(db, nome="Empresa B", telefone_operador="5511999991002")
    cliente_a = Cliente(empresa_id=empresa_a.id, nome="Cliente A")
    cliente_b = Cliente(empresa_id=empresa_b.id, nome="Cliente B")
    db.add_all([cliente_a, cliente_b])
    db.commit()

    set_tenant_context(db, empresa_id=empresa_a.id, usuario_id=101)

    repo = ClienteRepository()
    clientes = repo.get_multi(db)
    cliente_get = repo.get(db, cliente_b.id)
    cliente_por_telefone = repo.get_by_telefone(db, "5511999990002")

    assert [c.nome for c in clientes] == ["Cliente A"]
    assert cliente_get is None
    assert cliente_por_telefone is None
    assert db.query(Cliente).filter(Cliente.id == cliente_b.id).first() is None
    assert len(db.query(Empresa).all()) == 2


def test_tenant_scope_preenche_empresa_id_em_novo_registro(db, clean_tables):
    empresa = make_empresa(db, nome="Empresa Tenant", telefone_operador="5511999992001")
    usuario = make_usuario(db, empresa, email="tenant-create@teste.com")

    set_tenant_context(db, empresa_id=empresa.id, usuario_id=usuario.id)

    cliente = Cliente(nome="Cliente Auto Scope")
    db.add(cliente)
    db.commit()
    db.refresh(cliente)

    assert cliente.empresa_id == empresa.id


def test_superadmin_bypass_precisa_ser_explicito(db, clean_tables):
    empresa_a = make_empresa(db, nome="Empresa SA", telefone_operador="5511999993001")
    empresa_b = make_empresa(db, nome="Empresa SB", telefone_operador="5511999993002")
    db.add_all(
        [
            Cliente(empresa_id=empresa_a.id, nome="Cliente SA"),
            Cliente(empresa_id=empresa_b.id, nome="Cliente SB"),
        ]
    )
    admin = Usuario(
        nome="Super Admin",
        email="superadmin-tenant@teste.com",
        senha_hash="hash",
        ativo=True,
        is_superadmin=True,
        token_versao=1,
    )
    db.add(admin)
    db.commit()

    set_tenant_context(
        db,
        empresa_id=empresa_a.id,
        usuario_id=admin.id,
        is_superadmin=True,
    )
    assert len(db.query(Cliente).all()) == 1

    enable_superadmin_bypass(db, usuario=admin, reason="teste_unitario")
    assert sorted(c.nome for c in db.query(Cliente).all()) == ["Cliente SA", "Cliente SB"]


def test_delete_em_repository_base_respeita_tenant_scope(db, clean_tables):
    empresa_a = make_empresa(db, nome="Empresa Del A", telefone_operador="5511999994001")
    empresa_b = make_empresa(db, nome="Empresa Del B", telefone_operador="5511999994002")
    cliente_a = Cliente(empresa_id=empresa_a.id, nome="Cliente Del A")
    cliente_b = Cliente(empresa_id=empresa_b.id, nome="Cliente Del B")
    db.add_all([cliente_a, cliente_b])
    db.commit()

    set_tenant_context(db, empresa_id=empresa_a.id, usuario_id=501)

    repo = ClienteRepository()
    deleted = repo.delete(db, cliente_b.id)

    assert deleted is False
    raw_db = TestingSessionLocal()
    try:
        assert raw_db.query(Cliente).filter(Cliente.id == cliente_b.id).first() is not None
    finally:
        raw_db.close()

    admin = Usuario(
        nome="Super Admin Del",
        email="superadmin-del@teste.com",
        senha_hash="hash",
        ativo=True,
        is_superadmin=True,
        token_versao=1,
    )
    db.add(admin)
    db.commit()

    enable_superadmin_bypass(
        db,
        usuario=admin,
        reason="teste_delete_bypass",
    )
    deleted_with_bypass = repo.delete(db, cliente_b.id)
    assert deleted_with_bypass is True

    raw_db = TestingSessionLocal()
    try:
        assert raw_db.query(Cliente).filter(Cliente.id == cliente_b.id).first() is None
    finally:
        raw_db.close()
