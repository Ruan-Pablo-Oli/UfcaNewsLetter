"""Notificações push (issue #22, US-04.3).

`pywebpush.webpush` é sempre mockado: os testes não podem depender de chave
VAPID real nem de rede.
"""
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from pywebpush import WebPushException

from newsletter.models import Conteudo, Entrega, Fonte, Perfil, PushSubscription
from newsletter.push import (
    enviar_notificacoes_push,
    enviar_push_perfil,
    montar_notificacoes_perfil,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def fonte():
    return Fonte.objects.create(
        nome="Portal", tipo=Fonte.Tipo.HTML, url="https://x/", intervalo_coleta=60
    )


def _criar_conteudo(fonte, titulo="Edital A", hash_dedup="h-a"):
    return Conteudo.objects.create(
        titulo=titulo,
        corpo=f"Corpo de {titulo}.",
        data_publicacao=timezone.now(),
        fonte=fonte,
        status=Conteudo.Status.APROVADO,
        universal=True,
        hash_dedup=hash_dedup,
    )


@pytest.fixture
def perfil():
    user = get_user_model().objects.create_user("estudante", email="estudante@ufca.edu.br")
    return Perfil.objects.create(user=user, curso="", periodo=1, push_ativo=True)


@pytest.fixture
def subscription(perfil):
    return PushSubscription.objects.create(
        usuario=perfil.user,
        endpoint="https://push.example.com/abc",
        p256dh="chave-p256dh",
        auth="chave-auth",
    )


# --- montagem ---


def test_push_desativado_nao_monta_nada(fonte, perfil):
    _criar_conteudo(fonte)
    perfil.push_ativo = False
    perfil.save()

    assert montar_notificacoes_perfil(perfil) == []


def test_monta_aprovados_relevantes(fonte, perfil):
    _criar_conteudo(fonte)

    assert [c.titulo for c in montar_notificacoes_perfil(perfil)] == ["Edital A"]


def test_nao_inclui_ja_entregues_por_push(fonte, perfil):
    conteudo = _criar_conteudo(fonte)
    Entrega.objects.create(conteudo=conteudo, usuario=perfil.user, canal=Entrega.Canal.PUSH)

    assert montar_notificacoes_perfil(perfil) == []


def test_nao_inclui_pendente(fonte, perfil):
    Conteudo.objects.create(
        titulo="Pendente",
        corpo="c",
        data_publicacao=timezone.now(),
        fonte=fonte,
        hash_dedup="h-p",
    )

    assert montar_notificacoes_perfil(perfil) == []


# --- envio ---


def test_push_ativo_false_nao_recebe(fonte, perfil, subscription):
    _criar_conteudo(fonte)
    perfil.push_ativo = False
    perfil.save()

    with patch("newsletter.push.webpush") as mock_webpush:
        assert enviar_push_perfil(perfil) == 0
        mock_webpush.assert_not_called()


def test_sem_subscription_nao_envia(fonte, perfil):
    _criar_conteudo(fonte)

    with patch("newsletter.push.webpush") as mock_webpush:
        assert enviar_push_perfil(perfil) == 0
        mock_webpush.assert_not_called()


def test_envia_e_registra_entrega(fonte, perfil, subscription):
    _criar_conteudo(fonte)

    with patch("newsletter.push.webpush") as mock_webpush:
        enviados = enviar_push_perfil(perfil)

    assert enviados == 1
    mock_webpush.assert_called_once()
    kwargs = mock_webpush.call_args.kwargs
    assert kwargs["subscription_info"]["endpoint"] == subscription.endpoint
    assert "Edital A" in kwargs["data"]
    assert Entrega.objects.filter(
        conteudo__titulo="Edital A", usuario=perfil.user, canal=Entrega.Canal.PUSH
    ).exists()


def test_payload_inclui_titulo_e_categoria(fonte, perfil, subscription):
    from newsletter.models import Categoria

    categoria = Categoria.objects.create(nome=Categoria.Tipo.EDITAL)
    conteudo = _criar_conteudo(fonte)
    conteudo.categoria = categoria
    conteudo.save()

    with patch("newsletter.push.webpush") as mock_webpush:
        enviar_push_perfil(perfil)

    payload = mock_webpush.call_args.kwargs["data"]
    assert "Edital A" in payload
    assert categoria.get_nome_display() in payload


def test_nao_reenvia_conteudo_ja_entregue(fonte, perfil, subscription):
    _criar_conteudo(fonte)

    with patch("newsletter.push.webpush"):
        enviar_push_perfil(perfil)

    with patch("newsletter.push.webpush") as mock_webpush:
        assert enviar_push_perfil(perfil) == 0
        mock_webpush.assert_not_called()


def test_relevancia_respeitada(fonte, perfil, subscription):
    """Conteúdo não direcionado ao perfil (curso/interesse diferentes) não é enviado."""
    Conteudo.objects.create(
        titulo="Só para outro curso",
        corpo="c",
        data_publicacao=timezone.now(),
        fonte=fonte,
        status=Conteudo.Status.APROVADO,
        universal=False,
        cursos=[Perfil.Curso.DIREITO],
        hash_dedup="h-direito",
    )

    with patch("newsletter.push.webpush") as mock_webpush:
        assert enviar_push_perfil(perfil) == 0
        mock_webpush.assert_not_called()


def test_410_remove_subscription(fonte, perfil, subscription):
    _criar_conteudo(fonte)
    response = MagicMock(status_code=410)

    with patch(
        "newsletter.push.webpush", side_effect=WebPushException("gone", response=response)
    ):
        enviados = enviar_push_perfil(perfil)

    assert enviados == 0
    assert not PushSubscription.objects.filter(pk=subscription.pk).exists()
    assert not Entrega.objects.filter(canal=Entrega.Canal.PUSH).exists()


def test_404_remove_subscription(fonte, perfil, subscription):
    _criar_conteudo(fonte)
    response = MagicMock(status_code=404)

    with patch(
        "newsletter.push.webpush", side_effect=WebPushException("not found", response=response)
    ):
        enviar_push_perfil(perfil)

    assert not PushSubscription.objects.filter(pk=subscription.pk).exists()


def test_erro_generico_nao_remove_subscription_nem_registra_entrega(fonte, perfil, subscription):
    _criar_conteudo(fonte)
    response = MagicMock(status_code=500)

    with patch(
        "newsletter.push.webpush", side_effect=WebPushException("erro", response=response)
    ):
        enviados = enviar_push_perfil(perfil)

    assert enviados == 0
    assert PushSubscription.objects.filter(pk=subscription.pk).exists()
    assert not Entrega.objects.filter(canal=Entrega.Canal.PUSH).exists()


def test_enviar_notificacoes_push_soma_todos_os_perfis(fonte, perfil, subscription):
    outro_user = get_user_model().objects.create_user("outro", email="outro@ufca.edu.br")
    outro_perfil = Perfil.objects.create(user=outro_user, curso="", periodo=1, push_ativo=True)
    PushSubscription.objects.create(
        usuario=outro_user, endpoint="https://push.example.com/xyz", p256dh="p", auth="a"
    )
    _criar_conteudo(fonte)

    with patch("newsletter.push.webpush"):
        total = enviar_notificacoes_push()

    assert total == 2
    assert outro_perfil.push_ativo is True


def test_enviar_notificacoes_push_ignora_perfis_sem_push_ativo(fonte, perfil, subscription):
    outro_user = get_user_model().objects.create_user("outro", email="outro@ufca.edu.br")
    Perfil.objects.create(user=outro_user, curso="", periodo=1, push_ativo=False)
    _criar_conteudo(fonte)

    with patch("newsletter.push.webpush") as mock_webpush:
        enviar_notificacoes_push()

    assert mock_webpush.call_count == 1
