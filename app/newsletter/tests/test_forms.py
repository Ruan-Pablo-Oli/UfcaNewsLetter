"""Testes do formulário de perfil acadêmico."""
import pytest
from django.contrib.auth import get_user_model

from newsletter.forms import PerfilForm
from newsletter.models import Interesse, Perfil

pytestmark = pytest.mark.django_db


def _make_perfil():
    user = get_user_model().objects.create_user(username="aluno", password="senha123")
    return Perfil.objects.create(user=user, curso="", periodo=1)


def _payload(**overrides):
    payload = {"curso": Perfil.Curso.CIENCIA_DA_COMPUTACAO, "periodo": 3}
    payload.update(overrides)
    return payload


class TestPerfilForm:
    def test_valid_with_one_interesse(self):
        interesse = Interesse.objects.create(nome="Editais")

        form = PerfilForm(_payload(interesses=[interesse.pk]), instance=_make_perfil())

        assert form.is_valid(), form.errors

    def test_valid_with_five_interesses(self):
        interesses = [Interesse.objects.create(nome=f"Interesse {i}") for i in range(5)]

        form = PerfilForm(
            _payload(interesses=[i.pk for i in interesses]), instance=_make_perfil()
        )

        assert form.is_valid(), form.errors

    def test_rejects_zero_interesses(self):
        form = PerfilForm(_payload(interesses=[]), instance=_make_perfil())

        assert not form.is_valid()
        assert "interesses" in form.errors

    def test_rejects_more_than_five_interesses(self):
        interesses = [Interesse.objects.create(nome=f"Interesse {i}") for i in range(6)]

        form = PerfilForm(
            _payload(interesses=[i.pk for i in interesses]), instance=_make_perfil()
        )

        assert not form.is_valid()
        assert "interesses" in form.errors

    def test_requires_curso(self):
        interesse = Interesse.objects.create(nome="Editais")

        form = PerfilForm(
            _payload(curso="", interesses=[interesse.pk]), instance=_make_perfil()
        )

        assert not form.is_valid()
        assert "curso" in form.errors

    def test_rejects_periodo_out_of_range(self):
        interesse = Interesse.objects.create(nome="Editais")

        form = PerfilForm(
            _payload(periodo=0, interesses=[interesse.pk]), instance=_make_perfil()
        )

        assert not form.is_valid()
        assert "periodo" in form.errors
