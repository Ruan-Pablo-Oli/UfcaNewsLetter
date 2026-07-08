"""Testes de cadastro, login/logout e proteção de rotas."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from newsletter.models import Perfil

pytestmark = pytest.mark.django_db

VALID_EMAIL = "aluno@aluno.ufca.edu.br"


def _signup_payload(**overrides):
    payload = {
        "username": "aluno1",
        "email": VALID_EMAIL,
        "password1": "senha-super-secreta-123",
        "password2": "senha-super-secreta-123",
    }
    payload.update(overrides)
    return payload


class TestSignup:
    def test_signup_creates_user_and_empty_perfil(self, client):
        response = client.post(reverse("signup"), _signup_payload())

        assert response.status_code == 302
        user = get_user_model().objects.get(username="aluno1")
        assert user.perfil.curso == ""
        assert user.is_staff is False

    def test_signup_logs_user_in(self, client):
        client.post(reverse("signup"), _signup_payload())

        response = client.get(reverse("dashboard"))
        assert response.status_code == 200

    def test_signup_requires_institutional_email(self, client):
        response = client.post(reverse("signup"), _signup_payload(email="aluno@gmail.com"))

        assert response.status_code == 200
        assert not get_user_model().objects.filter(username="aluno1").exists()

    def test_signup_rejects_duplicate_email(self, client):
        get_user_model().objects.create_user(
            username="existente", email=VALID_EMAIL, password="outrasenha123"
        )

        response = client.post(reverse("signup"), _signup_payload(username="novo"))

        assert response.status_code == 200
        assert not get_user_model().objects.filter(username="novo").exists()


class TestLoginLogout:
    def test_login_and_logout(self, client):
        user = get_user_model().objects.create_user(username="aluno2", password="senha123")
        Perfil.objects.create(user=user, curso="Direito", periodo=2)

        response = client.post(reverse("login"), {"username": "aluno2", "password": "senha123"})
        assert response.status_code == 302
        assert client.get(reverse("dashboard")).status_code == 200

        response = client.post(reverse("logout"))
        assert response.status_code == 302
        assert client.get(reverse("dashboard")).status_code == 302

    def test_login_with_wrong_password_fails(self, client):
        get_user_model().objects.create_user(username="aluno3", password="senha123")

        response = client.post(reverse("login"), {"username": "aluno3", "password": "errada"})

        assert response.status_code == 200
        assert not response.wsgi_request.user.is_authenticated


class TestProtectedRoutes:
    def test_dashboard_rejects_anonymous(self, client):
        response = client.get(reverse("dashboard"))

        assert response.status_code == 302
        assert response.url.startswith(reverse("login"))

    def test_dashboard_allows_authenticated_user(self, client):
        user = get_user_model().objects.create_user(username="aluno4", password="senha123")
        Perfil.objects.create(user=user, curso="Medicina", periodo=1)
        client.force_login(user)

        response = client.get(reverse("dashboard"))

        assert response.status_code == 200
        assert b"aluno4" in response.content


class TestRoleDistinction:
    def test_staff_user_is_administrador(self, client):
        admin_user = get_user_model().objects.create_user(
            username="admin1", password="senha123", is_staff=True
        )
        Perfil.objects.create(user=admin_user, curso="-", periodo=1)
        client.force_login(admin_user)

        response = client.get(reverse("dashboard"))

        assert b"administrador" in response.content

    def test_regular_user_is_estudante(self, client):
        user = get_user_model().objects.create_user(username="aluno5", password="senha123")
        Perfil.objects.create(user=user, curso="-", periodo=1)
        client.force_login(user)

        response = client.get(reverse("dashboard"))

        assert b"estudante" in response.content
