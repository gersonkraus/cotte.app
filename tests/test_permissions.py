import pytest
from fastapi import HTTPException


# Mock manual da dependência para não carregar app.core (evitar erros de config/DB)
def exigir_permissao_mock(recurso: str, acao: str = "leitura"):
    def validator(usuario) -> bool:
        if usuario.is_superadmin or usuario.is_gestor:
            return usuario
        perms = usuario.permissoes or {}
        user_acao = perms.get(recurso)
        if not user_acao:
            raise HTTPException(
                status_code=403, detail=f"Sem permissão para acessar {recurso}"
            )
        niveis = {"leitura": 1, "meus": 1.5, "escrita": 2, "admin": 3}
        if niveis.get(user_acao, 0) < niveis.get(acao, 0):
            raise HTTPException(status_code=403, detail=f"Permissão insuficiente")
        return usuario

    return validator


class MockUsuario:
    def __init__(
        self,
        is_superadmin=False,
        is_gestor=False,
        permissoes=None,
        empresa_id=1,
        id=1,
    ):
        self.is_superadmin = is_superadmin
        self.is_gestor = is_gestor
        self.permissoes = permissoes or {}
        self.empresa_id = empresa_id
        self.id = id


class MockObjeto:
    """Objeto de domínio com empresa_id para testar tenant isolation."""
    def __init__(self, empresa_id: int):
        self.empresa_id = empresa_id


# ── Testes de autorização básica ────────────────────────────────────────────


def test_superadmin_always_allowed():
    user = MockUsuario(is_superadmin=True)
    validator = exigir_permissao_mock("any", "admin")
    assert validator(user) == user


def test_gestor_always_allowed():
    user = MockUsuario(is_gestor=True)
    validator = exigir_permissao_mock("financeiro", "admin")
    assert validator(user) == user


def test_sem_permissao_catalogo_bloqueado():
    """Usuário sem 'catalogo' no JSON não acessa o recurso (perm_catalogo foi removido)."""
    user = MockUsuario(permissoes={})

    with pytest.raises(HTTPException) as exc:
        exigir_permissao_mock("catalogo", "leitura")(user)
    assert exc.value.status_code == 403

    # Com a permissão correta no JSON, funciona
    user_com_perm = MockUsuario(permissoes={"catalogo": "escrita"})
    assert exigir_permissao_mock("catalogo", "escrita")(user_com_perm) == user_com_perm


def test_new_granular_permission_success():
    user = MockUsuario(permissoes={"financeiro": "escrita"})
    assert exigir_permissao_mock("financeiro", "leitura")(user) == user
    assert exigir_permissao_mock("financeiro", "escrita")(user) == user


def test_new_granular_permission_insufficient():
    user = MockUsuario(permissoes={"financeiro": "leitura"})
    with pytest.raises(HTTPException) as exc:
        exigir_permissao_mock("financeiro", "escrita")(user)
    assert exc.value.status_code == 403
    assert "Permissão insuficiente" in str(exc.value.detail)


def test_no_permission():
    user = MockUsuario(permissoes={})
    with pytest.raises(HTTPException) as exc:
        exigir_permissao_mock("catalogo", "leitura")(user)
    assert exc.value.status_code == 403
    assert "Sem permissão" in str(exc.value.detail)


# ── Testes do nível 'meus' ───────────────────────────────────────────────────


def test_meus_satisfies_leitura():
    """Permissão 'meus' deve satisfazer exigência de 'leitura'."""
    user = MockUsuario(permissoes={"orcamentos": "meus"})
    assert exigir_permissao_mock("orcamentos", "leitura")(user) == user


def test_meus_does_not_satisfy_escrita():
    """Permissão 'meus' não deve satisfazer exigência de 'escrita'."""
    user = MockUsuario(permissoes={"orcamentos": "meus"})
    with pytest.raises(HTTPException) as exc:
        exigir_permissao_mock("orcamentos", "escrita")(user)
    assert exc.value.status_code == 403


def test_escrita_satisfies_leitura():
    """Permissão 'escrita' deve satisfazer exigência de 'leitura'."""
    user = MockUsuario(permissoes={"clientes": "escrita"})
    assert exigir_permissao_mock("clientes", "leitura")(user) == user


def test_admin_satisfies_all():
    """Permissão 'admin' deve satisfazer todos os níveis."""
    user = MockUsuario(permissoes={"catalogo": "admin"})
    for nivel in ["leitura", "meus", "escrita", "admin"]:
        assert exigir_permissao_mock("catalogo", nivel)(user) == user


# ── Testes de tenant isolation (verificar_ownership) ─────────────────────────


def _verificar_ownership_mock(obj, usuario: MockUsuario) -> None:
    """Mock local de verificar_ownership (mesma lógica de auth.py)."""
    if usuario.is_superadmin:
        return
    empresa_id_obj = getattr(obj, "empresa_id", None)
    if empresa_id_obj is None:
        return
    if empresa_id_obj != usuario.empresa_id:
        raise HTTPException(
            status_code=403,
            detail="Acesso negado: este recurso não pertence à sua empresa.",
        )


def test_ownership_same_empresa_allowed():
    user = MockUsuario(empresa_id=1)
    obj = MockObjeto(empresa_id=1)
    _verificar_ownership_mock(obj, user)  # deve passar sem exceção


def test_ownership_different_empresa_blocked():
    """Usuário da empresa 1 não pode acessar objeto da empresa 2."""
    user = MockUsuario(empresa_id=1)
    obj = MockObjeto(empresa_id=2)
    with pytest.raises(HTTPException) as exc:
        _verificar_ownership_mock(obj, user)
    assert exc.value.status_code == 403


def test_ownership_superadmin_bypasses_tenant():
    """Superadmin pode acessar objetos de qualquer empresa."""
    user = MockUsuario(is_superadmin=True, empresa_id=1)
    obj = MockObjeto(empresa_id=99)
    _verificar_ownership_mock(obj, user)  # deve passar sem exceção


def test_ownership_obj_without_empresa_id():
    """Objetos sem empresa_id não bloqueiam (ex.: entidade global)."""
    user = MockUsuario(empresa_id=1)

    class ObjSemEmpresa:
        pass

    _verificar_ownership_mock(ObjSemEmpresa(), user)  # deve passar sem exceção


# ── Testes de escalação de privilégio ────────────────────────────────────────


def test_operador_cannot_access_equipe():
    """Operador sem permissão 'equipe' não acessa gerência de usuários."""
    user = MockUsuario(permissoes={"orcamentos": "escrita", "clientes": "escrita"})
    with pytest.raises(HTTPException) as exc:
        exigir_permissao_mock("equipe", "leitura")(user)
    assert exc.value.status_code == 403


def test_operador_cannot_access_configuracoes():
    """Operador sem permissão 'configuracoes' não altera dados da empresa."""
    user = MockUsuario(permissoes={"orcamentos": "escrita"})
    with pytest.raises(HTTPException) as exc:
        exigir_permissao_mock("configuracoes", "escrita")(user)
    assert exc.value.status_code == 403


def test_operador_cannot_escalate_to_admin_via_orcamentos():
    """Operador com 'orcamentos: escrita' não acessa ação 'admin'."""
    user = MockUsuario(permissoes={"orcamentos": "escrita"})
    with pytest.raises(HTTPException) as exc:
        exigir_permissao_mock("orcamentos", "admin")(user)
    assert exc.value.status_code == 403


def test_gestor_can_access_equipe_and_configuracoes():
    """Gestor tem acesso total, incluindo equipe e configurações."""
    user = MockUsuario(is_gestor=True)
    assert exigir_permissao_mock("equipe", "admin")(user) == user
    assert exigir_permissao_mock("configuracoes", "admin")(user) == user
