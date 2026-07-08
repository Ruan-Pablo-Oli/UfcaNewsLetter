"""Testes da tela de preenchimento e edição do perfil acadêmico."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from newsletter.models import Interesse, Perfil

pytestmark = pytest.mark.django_db


def _make_user_with_perfil(**perfil_kwargs):
    user = get_user_model().objects.create_user(username="aluno", password="senha123")
    defaults = {"curso": "", "periodo": 1}
    defaults.update(perfil_kwargs)
    Perfil.objects.create(user=user, **defaults)
    return user


class TestPerfilEditarAcesso:
    def test_requires_login(self, client):
        response = client.get(reverse("perfil_editar"))

        assert response.status_code == 302
        assert response.url.startswith(reverse("login"))

    def test_authenticated_user_sees_form(self, client):
        user = _make_user_with_perfil()
        client.force_login(user)

        response = client.get(reverse("perfil_editar"))

        assert response.status_code == 200
        assert b"curso" in response.content.lower()


class TestPerfilEditarSalvar:
    def test_valid_submission_updates_perfil_and_confirms(self, client):
        user = _make_user_with_perfil()
        interesse = Interesse.objects.create(nome="Editais")
        client.force_login(user)

        response = client.post(
            reverse("perfil_editar"),
            {
                "curso": Perfil.Curso.ENGENHARIA_DE_SOFTWARE,
                "periodo": 4,
                "interesses": [interesse.pk],
            },
            follow=True,
        )

        assert response.status_code == 200
        user.perfil.refresh_from_db()
        assert user.perfil.curso == Perfil.Curso.ENGENHARIA_DE_SOFTWARE
        assert user.perfil.periodo == 4
        assert interesse in user.perfil.interesses.all()
        assert "Perfil atualizado com sucesso." in [
            str(m) for m in response.context["messages"]
        ]

    def test_editing_existing_perfil_prefills_and_updates(self, client):
        interesse_antigo = Interesse.objects.create(nome="Bolsas")
        interesse_novo = Interesse.objects.create(nome="Estágios")
        user = _make_user_with_perfil(curso=Perfil.Curso.DIREITO, periodo=2)
        user.perfil.interesses.add(interesse_antigo)
        client.force_login(user)

        get_response = client.get(reverse("perfil_editar"))
        assert get_response.status_code == 200

        response = client.post(
            reverse("perfil_editar"),
            {
                "curso": Perfil.Curso.DIREITO,
                "periodo": 5,
                "interesses": [interesse_novo.pk],
            },
        )

        assert response.status_code == 302
        user.perfil.refresh_from_db()
        assert user.perfil.periodo == 5
        assert list(user.perfil.interesses.all()) == [interesse_novo]

    def test_rejects_zero_interesses(self, client):
        user = _make_user_with_perfil()
        client.force_login(user)

        response = client.post(
            reverse("perfil_editar"),
            {"curso": Perfil.Curso.MEDICINA, "periodo": 1, "interesses": []},
        )

        assert response.status_code == 200
        assert "Selecione ao menos" in response.content.decode()
        user.perfil.refresh_from_db()
        assert user.perfil.curso == ""

    def test_rejects_more_than_five_interesses(self, client):
        user = _make_user_with_perfil()
        interesses = [Interesse.objects.create(nome=f"Interesse {i}") for i in range(6)]
        client.force_login(user)

        response = client.post(
            reverse("perfil_editar"),
            {
                "curso": Perfil.Curso.MEDICINA,
                "periodo": 1,
                "interesses": [i.pk for i in interesses],
            },
        )

        assert response.status_code == 200
        assert "no máximo" in response.content.decode()

    def test_rejects_missing_curso(self, client):
        user = _make_user_with_perfil()
        interesse = Interesse.objects.create(nome="Editais")
        client.force_login(user)

        response = client.post(
            reverse("perfil_editar"),
            {"curso": "", "periodo": 1, "interesses": [interesse.pk]},
        )

        assert response.status_code == 200
        user.perfil.refresh_from_db()
        assert user.perfil.curso == ""
