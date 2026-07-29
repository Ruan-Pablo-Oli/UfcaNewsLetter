"""Testes do comando de seed de conteúdos de demonstração."""
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from newsletter.feed import feed_queryset_for_perfil
from newsletter.models import Categoria, Conteudo, Fonte, Interesse, Perfil

pytestmark = pytest.mark.django_db


def test_seed_cria_conteudos_fontes_e_categorias():
    call_command("seed_conteudos")

    assert Conteudo.objects.count() >= 30
    assert Fonte.objects.count() == 3
    assert Categoria.objects.count() == len(Categoria.Tipo.values)


def test_seed_e_idempotente():
    call_command("seed_conteudos")
    total = Conteudo.objects.count()

    call_command("seed_conteudos")

    assert Conteudo.objects.count() == total
    assert Fonte.objects.count() == 3


def test_seed_cobre_os_tres_caminhos_do_feed():
    """Universal, por curso e por interesse — os três ramos de `feed_queryset_for_perfil`."""
    call_command("seed_conteudos")

    assert Conteudo.objects.filter(universal=True).exists()
    assert Conteudo.objects.filter(cursos__contains=["ciencia_da_computacao"]).exists()
    assert Conteudo.objects.filter(interesses__isnull=False).exists()


def _perfil(interesses=(), curso=Perfil.Curso.CIENCIA_DA_COMPUTACAO):
    user = get_user_model().objects.create_user(username="aluno", password="senha123")
    perfil = Perfil.objects.create(user=user, curso=curso, periodo=1)
    perfil.interesses.set(Interesse.objects.filter(nome__in=interesses))
    return perfil


def test_feed_de_perfil_sem_interesses_tem_os_universais():
    """Mesmo sem interesses escolhidos, o feed não pode nascer vazio."""
    call_command("seed_conteudos")

    conteudos = feed_queryset_for_perfil(_perfil())

    assert conteudos.count() >= 10


def test_feed_de_perfil_tipico_tem_mais_de_uma_pagina():
    """O ponto do comando: dar volume suficiente para exercitar a paginação (20/página)."""
    call_command("seed_conteudos")
    perfil = _perfil(interesses=["Editais", "Estágios", "Eventos"])

    conteudos = feed_queryset_for_perfil(perfil)

    assert conteudos.count() > 20, "deve haver mais de uma página de feed"
