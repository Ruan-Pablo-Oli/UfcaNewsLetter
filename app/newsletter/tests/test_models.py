"""Testes das entidades centrais do domínio."""
import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from newsletter.models import Categoria, Conteudo, Entrega, Feedback, Fonte, Interesse, Perfil

pytestmark = pytest.mark.django_db


def _make_user(username="aluno"):
    return get_user_model().objects.create_user(username=username, password="senha123")


def _make_categoria(nome=Categoria.Tipo.EDITAL):
    return Categoria.objects.create(nome=nome)


def _make_fonte():
    return Fonte.objects.create(
        nome="Portal UFCA",
        tipo=Fonte.Tipo.HTML,
        url="https://www.ufca.edu.br/",
        intervalo_coleta=60,
    )


def _make_conteudo(categoria=None, fonte=None, hash_dedup="hash-1"):
    return Conteudo.objects.create(
        titulo="Edital de bolsas",
        corpo="Corpo do conteúdo.",
        resumo="Resumo.",
        data_publicacao=timezone.now(),
        categoria=categoria or _make_categoria(),
        fonte=fonte or _make_fonte(),
        hash_dedup=hash_dedup,
    )


class TestPerfil:
    def test_str_and_relations(self):
        user = _make_user()
        perfil = Perfil.objects.create(user=user, curso="Ciência da Computação", periodo=3)
        interesse = Interesse.objects.create(nome="Editais")
        perfil.interesses.add(interesse)

        assert perfil.user == user
        assert user.perfil == perfil
        assert interesse in perfil.interesses.all()
        assert perfil in interesse.perfis.all()
        assert str(perfil) == f"{user} (Ciência da Computação)"

    def test_user_can_have_only_one_perfil(self):
        user = _make_user()
        Perfil.objects.create(user=user, curso="Direito", periodo=1)

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Perfil.objects.create(user=user, curso="Direito", periodo=2)


class TestInteresse:
    def test_nome_is_unique(self):
        Interesse.objects.create(nome="Estágios")

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Interesse.objects.create(nome="Estágios")


class TestCategoria:
    def test_nome_is_unique(self):
        Categoria.objects.create(nome=Categoria.Tipo.EVENTO)

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Categoria.objects.create(nome=Categoria.Tipo.EVENTO)


class TestFonte:
    def test_create(self):
        fonte = _make_fonte()

        assert fonte.tipo == Fonte.Tipo.HTML
        assert str(fonte) == "Portal UFCA"


class TestConteudo:
    def test_create_with_relations(self):
        categoria = _make_categoria()
        fonte = _make_fonte()
        conteudo = _make_conteudo(categoria=categoria, fonte=fonte)

        assert conteudo.categoria == categoria
        assert conteudo.fonte == fonte
        assert conteudo in categoria.conteudos.all()
        assert conteudo in fonte.conteudos.all()

    def test_hash_dedup_is_unique(self):
        _make_conteudo(hash_dedup="hash-repetido")

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                _make_conteudo(hash_dedup="hash-repetido")


class TestEntrega:
    def test_create(self):
        user = _make_user()
        conteudo = _make_conteudo()
        entrega = Entrega.objects.create(conteudo=conteudo, usuario=user, canal=Entrega.Canal.EMAIL)

        assert entrega in user.entregas.all()
        assert entrega in conteudo.entregas.all()

    def test_unique_together(self):
        user = _make_user()
        conteudo = _make_conteudo()
        Entrega.objects.create(conteudo=conteudo, usuario=user, canal=Entrega.Canal.EMAIL)

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Entrega.objects.create(conteudo=conteudo, usuario=user, canal=Entrega.Canal.EMAIL)


class TestFeedback:
    def test_create(self):
        user = _make_user()
        conteudo = _make_conteudo()
        feedback = Feedback.objects.create(usuario=user, conteudo=conteudo, tipo=Feedback.Tipo.POSITIVO)

        assert feedback in user.feedbacks.all()
        assert feedback in conteudo.feedbacks.all()

    def test_unique_together(self):
        user = _make_user()
        conteudo = _make_conteudo()
        Feedback.objects.create(usuario=user, conteudo=conteudo, tipo=Feedback.Tipo.POSITIVO)

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Feedback.objects.create(usuario=user, conteudo=conteudo, tipo=Feedback.Tipo.NEGATIVO)
