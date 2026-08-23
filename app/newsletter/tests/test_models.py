"""Testes das entidades centrais do domínio."""
import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from newsletter.models import (
    Categoria,
    Conteudo,
    Entrega,
    Feedback,
    Fonte,
    Interesse,
    Perfil,
    PushSubscription,
)

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

    def test_push_ativo_default_false(self):
        perfil = Perfil.objects.create(user=_make_user(), curso="Direito", periodo=1)

        assert perfil.push_ativo is False


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

    def test_defaults_dos_campos_de_coleta(self):
        fonte = _make_fonte()

        assert fonte.ativo is True
        assert fonte.ultima_coleta is None


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

    def test_personalizacao_defaults(self):
        conteudo = _make_conteudo()

        assert conteudo.universal is False
        assert conteudo.cursos == []
        assert list(conteudo.interesses.all()) == []

    def test_personalizacao_pode_ser_direcionada(self):
        interesse = Interesse.objects.create(nome="Editais")
        conteudo = _make_conteudo(hash_dedup="hash-direcionado")
        conteudo.cursos = [Perfil.Curso.DIREITO]
        conteudo.interesses.add(interesse)
        conteudo.save()

        conteudo.refresh_from_db()
        assert conteudo.cursos == [Perfil.Curso.DIREITO]
        assert interesse in conteudo.interesses.all()
        assert conteudo in interesse.conteudos.all()

    def test_defaults_dos_campos_de_coleta(self):
        conteudo = _make_conteudo()

        assert conteudo.url == ""
        assert conteudo.status == Conteudo.Status.PENDENTE
        assert conteudo.gerado_por_ia is False
        assert conteudo.prazo is None
        assert conteudo.publico_alvo == ""

    def test_pode_ser_salvo_sem_categoria(self):
        """Conteúdo ainda não classificado (#17) precisa poder ser inserido."""
        conteudo = Conteudo.objects.create(
            titulo="Edital ainda não classificado",
            corpo="Corpo do conteúdo.",
            resumo="Resumo.",
            data_publicacao=timezone.now(),
            categoria=None,
            fonte=_make_fonte(),
            hash_dedup="hash-sem-categoria",
        )

        conteudo.refresh_from_db()
        assert conteudo.categoria is None


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


class TestPushSubscription:
    def test_create(self):
        user = _make_user()
        subscription = PushSubscription.objects.create(
            usuario=user,
            endpoint="https://push.example.com/abc",
            p256dh="chave-p256dh",
            auth="chave-auth",
        )

        assert subscription in user.push_subscriptions.all()

    def test_endpoint_is_unique(self):
        user = _make_user()
        PushSubscription.objects.create(
            usuario=user,
            endpoint="https://push.example.com/abc",
            p256dh="p1",
            auth="a1",
        )

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                PushSubscription.objects.create(
                    usuario=_make_user("outro"),
                    endpoint="https://push.example.com/abc",
                    p256dh="p2",
                    auth="a2",
                )

    def test_usuario_pode_ter_varias_subscriptions(self):
        user = _make_user()
        PushSubscription.objects.create(
            usuario=user, endpoint="https://push.example.com/1", p256dh="p1", auth="a1"
        )
        PushSubscription.objects.create(
            usuario=user, endpoint="https://push.example.com/2", p256dh="p2", auth="a2"
        )

        assert user.push_subscriptions.count() == 2


class TestFeedback:
    def test_create(self):
        user = _make_user()
        conteudo = _make_conteudo()
        feedback = Feedback.objects.create(
            usuario=user, conteudo=conteudo, tipo=Feedback.Tipo.POSITIVO
        )

        assert feedback in user.feedbacks.all()
        assert feedback in conteudo.feedbacks.all()

    def test_unique_together(self):
        user = _make_user()
        conteudo = _make_conteudo()
        Feedback.objects.create(usuario=user, conteudo=conteudo, tipo=Feedback.Tipo.POSITIVO)

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Feedback.objects.create(
                    usuario=user, conteudo=conteudo, tipo=Feedback.Tipo.NEGATIVO
                )
