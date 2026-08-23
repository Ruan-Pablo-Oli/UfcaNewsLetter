"""API de subscription push e preferência `push_ativo` (issue #22, US-04.3)."""
import json

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from newsletter.models import Interesse, Perfil, PushSubscription

pytestmark = pytest.mark.django_db


def _make_user_with_perfil(**perfil_kwargs):
    user = get_user_model().objects.create_user(username="aluno", password="senha123")
    defaults = {"curso": "", "periodo": 1}
    defaults.update(perfil_kwargs)
    Perfil.objects.create(user=user, **defaults)
    return user


def _patch_perfil(client, payload):
    return client.patch(
        reverse("api_perfil"), data=json.dumps(payload), content_type="application/json"
    )


class TestApiPerfilPushAtivo:
    def test_get_retorna_push_ativo(self, client):
        user = _make_user_with_perfil(push_ativo=True)
        client.force_login(user)

        response = client.get(reverse("api_perfil"))

        assert response.status_code == 200
        assert response.json()["push_ativo"] is True

    def test_novo_perfil_nasce_com_push_desativado(self, client):
        user = _make_user_with_perfil()
        client.force_login(user)

        response = client.get(reverse("api_perfil"))

        assert response.json()["push_ativo"] is False

    def test_patch_ativa_push(self, client):
        user = _make_user_with_perfil()
        interesse = Interesse.objects.create(nome="Editais")
        client.force_login(user)

        response = _patch_perfil(
            client,
            {
                "curso": Perfil.Curso.ENGENHARIA_DE_SOFTWARE,
                "periodo": 3,
                "interesses": [interesse.pk],
                "push_ativo": True,
            },
        )

        assert response.status_code == 200
        assert response.json()["push_ativo"] is True
        user.perfil.refresh_from_db()
        assert user.perfil.push_ativo is True

    def test_patch_sem_push_ativo_preserva_valor_atual(self, client):
        user = _make_user_with_perfil(push_ativo=True)
        interesse = Interesse.objects.create(nome="Editais")
        client.force_login(user)

        response = _patch_perfil(
            client,
            {
                "curso": Perfil.Curso.ENGENHARIA_DE_SOFTWARE,
                "periodo": 3,
                "interesses": [interesse.pk],
            },
        )

        assert response.status_code == 200
        user.perfil.refresh_from_db()
        assert user.perfil.push_ativo is True

    def test_patch_desativa_push(self, client):
        user = _make_user_with_perfil(push_ativo=True)
        interesse = Interesse.objects.create(nome="Editais")
        client.force_login(user)

        _patch_perfil(
            client,
            {
                "curso": Perfil.Curso.ENGENHARIA_DE_SOFTWARE,
                "periodo": 3,
                "interesses": [interesse.pk],
                "push_ativo": False,
            },
        )

        user.perfil.refresh_from_db()
        assert user.perfil.push_ativo is False


class TestApiPushSubscription:
    def _payload(self, endpoint="https://push.example.com/abc"):
        return {"endpoint": endpoint, "keys": {"p256dh": "chave-p256dh", "auth": "chave-auth"}}

    def test_requires_login(self, client):
        response = client.post(
            reverse("api_push_subscription"),
            data=json.dumps(self._payload()),
            content_type="application/json",
        )

        assert response.status_code == 302

    def test_registra_subscription(self, client):
        user = _make_user_with_perfil()
        client.force_login(user)

        response = client.post(
            reverse("api_push_subscription"),
            data=json.dumps(self._payload()),
            content_type="application/json",
        )

        assert response.status_code == 201
        subscription = PushSubscription.objects.get(endpoint="https://push.example.com/abc")
        assert subscription.usuario == user
        assert subscription.p256dh == "chave-p256dh"
        assert subscription.auth == "chave-auth"

    def test_registrar_endpoint_ja_existente_atualiza(self, client):
        user = _make_user_with_perfil()
        client.force_login(user)
        payload = self._payload()
        client.post(
            reverse("api_push_subscription"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        payload["keys"]["p256dh"] = "nova-chave"
        response = client.post(
            reverse("api_push_subscription"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 201
        assert PushSubscription.objects.filter(endpoint=payload["endpoint"]).count() == 1
        assert PushSubscription.objects.get(endpoint=payload["endpoint"]).p256dh == "nova-chave"

    def test_registrar_sem_endpoint_retorna_400(self, client):
        user = _make_user_with_perfil()
        client.force_login(user)

        response = client.post(
            reverse("api_push_subscription"),
            data=json.dumps({"keys": {"p256dh": "p", "auth": "a"}}),
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_registrar_sem_keys_retorna_400(self, client):
        user = _make_user_with_perfil()
        client.force_login(user)

        response = client.post(
            reverse("api_push_subscription"),
            data=json.dumps({"endpoint": "https://push.example.com/abc"}),
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_remove_subscription(self, client):
        user = _make_user_with_perfil()
        client.force_login(user)
        subscription = PushSubscription.objects.create(
            usuario=user, endpoint="https://push.example.com/abc", p256dh="p", auth="a"
        )

        response = client.delete(
            reverse("api_push_subscription"),
            data=json.dumps({"endpoint": subscription.endpoint}),
            content_type="application/json",
        )

        assert response.status_code == 200
        assert not PushSubscription.objects.filter(pk=subscription.pk).exists()

    def test_remove_subscription_de_outro_usuario_nao_afeta(self, client):
        outro = get_user_model().objects.create_user(username="outro", password="senha123")
        subscription = PushSubscription.objects.create(
            usuario=outro, endpoint="https://push.example.com/abc", p256dh="p", auth="a"
        )
        user = _make_user_with_perfil()
        client.force_login(user)

        client.delete(
            reverse("api_push_subscription"),
            data=json.dumps({"endpoint": subscription.endpoint}),
            content_type="application/json",
        )

        assert PushSubscription.objects.filter(pk=subscription.pk).exists()
