"""Testes do comando de seed das Fontes de unidades (US-03.1.5, #57)."""
import pytest
from django.core.management import call_command

from newsletter.management.commands.seed_fontes_unidades import CATEGORIAS_DE_VALOR_ALTO
from newsletter.models import Fonte

pytestmark = pytest.mark.django_db


def test_seed_cria_fonte_por_categoria_de_valor_alto():
    call_command("seed_fontes_unidades")

    assert Fonte.objects.count() == len(CATEGORIAS_DE_VALOR_ALTO)
    graduacao = Fonte.objects.get(url="https://www.ufca.edu.br/noticias/informe_category/graduacao/")
    assert graduacao.tipo == Fonte.Tipo.HTML
    assert graduacao.ativo is True


def test_seed_e_idempotente():
    call_command("seed_fontes_unidades")
    total = Fonte.objects.count()

    call_command("seed_fontes_unidades")

    assert Fonte.objects.count() == total


def test_seed_nao_cria_categorias_de_baixo_valor():
    call_command("seed_fontes_unidades")

    baixo_valor = [
        "licitacoes",
        "corregedoria",
        "gestao-de-pessoas",
        "expediente",
        "covid-19",
    ]
    for slug in baixo_valor:
        url = f"https://www.ufca.edu.br/noticias/informe_category/{slug}/"
        assert not Fonte.objects.filter(url=url).exists()
