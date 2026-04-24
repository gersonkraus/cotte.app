import pytest
from app.models.models import CopilotoUserSkill


class TestCopilotoSkillEndpoint:
    """Testes para o endpoint de skill do copiloto técnico"""

    @pytest.fixture
    def auth_headers(self, admin_token):
        return {"Authorization": f"Bearer {admin_token}"}

    def test_get_skill_sem_skill_cadastrada(self, http_client, auth_headers):
        """Deve retornar skill vazia quando não há skill cadastrada"""
        response = http_client.get(
            "/api/v1/ai/copiloto-interno/skill", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["skill_text"] == ""

    def test_put_skill_valida(self, http_client, auth_headers):
        """Deve salvar skill válida (10-2000 chars)"""
        skill_text = "Seja sempre objetivo e focado em dados técnicos."
        response = http_client.put(
            "/api/v1/ai/copiloto-interno/skill",
            json={"skill_text": skill_text},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["skill_text"] == skill_text

    def test_put_skill_muito_curta(self, http_client, auth_headers):
        """Deve rejeitar skill com menos de 10 caracteres"""
        response = http_client.put(
            "/api/v1/ai/copiloto-interno/skill",
            json={"skill_text": "curta"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_put_skill_muito_longa(self, http_client, auth_headers):
        """Deve rejeitar skill com mais de 2000 caracteres"""
        long_skill = "a" * 2001
        response = http_client.put(
            "/api/v1/ai/copiloto-interno/skill",
            json={"skill_text": long_skill},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_skill_aplicada_no_prompt(self, http_client, auth_headers, db):
        """Deve injetar skill no system prompt do copiloto"""
        skill_text = "Aja como especialista em finanças."
        response = http_client.put(
            "/api/v1/ai/copiloto-interno/skill",
            json={"skill_text": skill_text},
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Acessa o usuário através do token para garantir que estamos pegando o ID correto
        from app.core.auth import get_usuario_atual
        from jose import jwt
        from app.core.config import settings
        
        token = auth_headers["Authorization"].split(" ")[1]
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")

        skill = db.query(CopilotoUserSkill).filter_by(usuario_id=user_id).first()
        assert skill is not None
        assert skill.skill_text == skill_text

