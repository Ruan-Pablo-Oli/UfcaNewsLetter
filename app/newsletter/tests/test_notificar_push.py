"""Comando `notificar_push` (issue #22)."""
from io import StringIO
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from newsletter.models import Conteudo, Entrega, Fonte, Perfil, PushSubscription

pytestmark = pytest.mark.django_db


@pytest.fixture
def fonte():
    return Fonte.objects.create(
        nome="Portal", tipo=Fonte.Tipo.HTML, url="https://x/", intervalo_coleta=60
    )


@pytest.fixture
def perfil():
    user = get_user_model().objects.create_user("estudante", email="estudante@ufca.edu.br")
    perfil = Perfil.objects.create(user=user, curso="", periodo=1, push_ativo=True)
    PushSubscription.objects.create(
        usuario=user, endpoint="https://push.example.com/abc", p256dh="p", auth="a"
    )
    return perfil


def _criar_conteudo(fonte):
    return Conteudo.objects.create(
        titulo="Edital A",
        corpo="Corpo.",
        data_publicacao=timezone.now(),
        fonte=fonte,
        status=Conteudo.Status.APROVADO,
        universal=True,
        hash_dedup="h-a",
    )


def test_dry_run_nao_envia_nem_grava(fonte, perfil):
    _criar_conteudo(fonte)
    out = StringIO()

    with patch("newsletter.push.webpush") as mock_webpush:
        call_command("notificar_push", "--dry-run", stdout=out)

    mock_webpush.assert_not_called()
    assert not Entrega.objects.exists()
    assert "1 perfil" in out.getvalue()


def test_envia_e_reporta_quantidade(fonte, perfil):
    _criar_conteudo(fonte)
    out = StringIO()

    with patch("newsletter.push.webpush") as mock_webpush:
        call_command("notificar_push", stdout=out)

    mock_webpush.assert_called_once()
    assert Entrega.objects.filter(canal=Entrega.Canal.PUSH).count() == 1
    assert "1 notificacao" in out.getvalue()
