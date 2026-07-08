"""Testes do comando de seed de interesses."""
import pytest
from django.core.management import call_command

from newsletter.models import Interesse

pytestmark = pytest.mark.django_db


def test_seed_cria_interesses():
    call_command("seed_interesses")

    assert Interesse.objects.filter(nome="Editais").exists()
    assert Interesse.objects.count() >= 10


def test_seed_e_idempotente():
    call_command("seed_interesses")
    total = Interesse.objects.count()

    call_command("seed_interesses")

    assert Interesse.objects.count() == total
