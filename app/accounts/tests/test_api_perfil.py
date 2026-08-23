"""Testes da API de perfil para a frequência de entrega do digest (US-04.2, issue #25)."""
import json

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from newsletter.digest import enviar_digests
from newsletter.models import Conteudo, Fonte, Interesse, Perfil

pytestmark = pytest.mark.django_db


def _make_user_with_perfil(**perfil_kwargs):
    user = get_user_model().objects.create_user(username="aluno", password="senha123")
    defaults = {"curso": "", "periodo": 1}
    defaults.update(perfil_kwargs)
    Perfil.objects.create(user=user, **defaults)
    return user


def _patch(client, payload):
    return client.patch(
        reverse("api_perfil"), data=json.dumps(payload), content_type="application/json"
    )


class TestApiPerfilFrequencia:
    def test_get_retorna_frequencia_atual(self, client):
        user = _make_user_with_perfil(frequencia_email=Perfil.FrequenciaEmail.SEMANAL)
        client.force_login(user)

        response = client.get(reverse("api_perfil"))

        assert response.status_code == 200
        assert response.json()["frequencia_email"] == Perfil.FrequenciaEmail.SEMANAL

    def test_novo_perfil_nasce_diaria(self, client):
        user = _make_user_with_perfil()
        client.force_login(user)

        response = client.get(reverse("api_perfil"))

        assert response.json()["frequencia_email"] == Perfil.FrequenciaEmail.DIARIA

    def test_patch_altera_e_persiste_frequencia(self, client):
        user = _make_user_with_perfil()
        interesse = Interesse.objects.create(nome="Editais")
        client.force_login(user)

        response = _patch(
            client,
            {
                "curso": Perfil.Curso.ENGENHARIA_DE_SOFTWARE,
                "periodo": 3,
                "interesses": [interesse.pk],
                "frequencia_email": Perfil.FrequenciaEmail.SEMANAL,
            },
        )

        assert response.status_code == 200
        assert response.json()["frequencia_email"] == Perfil.FrequenciaEmail.SEMANAL
        user.perfil.refresh_from_db()
        assert user.perfil.frequencia_email == Perfil.FrequenciaEmail.SEMANAL

    def test_patch_sem_frequencia_mantem_valor_atual(self, client):
        user = _make_user_with_perfil(frequencia_email=Perfil.FrequenciaEmail.SEMANAL)
        interesse = Interesse.objects.create(nome="Editais")
        client.force_login(user)

        response = _patch(
            client,
            {
                "curso": Perfil.Curso.ENGENHARIA_DE_SOFTWARE,
                "periodo": 3,
                "interesses": [interesse.pk],
            },
        )

        assert response.status_code == 200
        user.perfil.refresh_from_db()
        assert user.perfil.frequencia_email == Perfil.FrequenciaEmail.SEMANAL

    def test_patch_valor_invalido_retorna_400(self, client):
        user = _make_user_with_perfil()
        interesse = Interesse.objects.create(nome="Editais")
        client.force_login(user)

        response = _patch(
            client,
            {
                "curso": Perfil.Curso.ENGENHARIA_DE_SOFTWARE,
                "periodo": 3,
                "interesses": [interesse.pk],
                "frequencia_email": "mensal",
            },
        )

        assert response.status_code == 400
        assert "frequencia_email" in response.json()["erro"]
        user.perfil.refresh_from_db()
        assert user.perfil.frequencia_email == Perfil.FrequenciaEmail.DIARIA

    def test_requires_login(self, client):
        response = client.get(reverse("api_perfil"))

        assert response.status_code == 302


class TestApiFrequenciasEmail:
    def test_lista_as_tres_opcoes(self, client):
        response = client.get(reverse("api_frequencias_email"))

        assert response.status_code == 200
        valores = {f["value"] for f in response.json()["frequencias"]}
        assert valores == {"diaria", "semanal", "desativado"}


@pytest.fixture
def fonte():
    return Fonte.objects.create(
        nome="Portal", tipo=Fonte.Tipo.HTML, url="https://x/", intervalo_coleta=60
    )


class TestPreferenciaAplicadaNoProximoEnvio:
    """CA: 'as preferências são aplicadas no próximo ciclo de envio'."""

    def _criar_conteudo(self, fonte, hash_dedup):
        return Conteudo.objects.create(
            titulo="Edital A",
            corpo="Corpo do edital.",
            data_publicacao=timezone.now(),
            fonte=fonte,
            status=Conteudo.Status.APROVADO,
            universal=True,
            hash_dedup=hash_dedup,
        )

    def test_desativar_via_api_impede_envio_seguinte(self, client, fonte):
        user = _make_user_with_perfil()
        user.email = "aluno@ufca.edu.br"
        user.save()
        interesse = Interesse.objects.create(nome="Editais")
        client.force_login(user)

        _patch(
            client,
            {
                "curso": Perfil.Curso.ENGENHARIA_DE_SOFTWARE,
                "periodo": 3,
                "interesses": [interesse.pk],
                "frequencia_email": Perfil.FrequenciaEmail.DESATIVADO,
            },
        )
        self._criar_conteudo(fonte, "h-a")

        assert enviar_digests() == 0

    def test_reativar_via_api_permite_envio_seguinte(self, client, fonte):
        user = _make_user_with_perfil(frequencia_email=Perfil.FrequenciaEmail.DESATIVADO)
        user.email = "aluno@ufca.edu.br"
        user.save()
        interesse = Interesse.objects.create(nome="Editais")
        client.force_login(user)
        self._criar_conteudo(fonte, "h-a")

        _patch(
            client,
            {
                "curso": Perfil.Curso.ENGENHARIA_DE_SOFTWARE,
                "periodo": 3,
                "interesses": [interesse.pk],
                "frequencia_email": Perfil.FrequenciaEmail.DIARIA,
            },
        )

        assert enviar_digests() == 1
