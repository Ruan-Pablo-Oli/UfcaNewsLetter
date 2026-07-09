"""Testes do endpoint de feed de conteúdo personalizado (US-01.2)."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from newsletter.models import Categoria, Conteudo, Feedback, Fonte, Interesse, Perfil

pytestmark = pytest.mark.django_db


def _make_user_with_perfil(username="aluno", **perfil_kwargs):
    user = get_user_model().objects.create_user(username=username, password="senha123")
    defaults = {"curso": Perfil.Curso.CIENCIA_DA_COMPUTACAO, "periodo": 1}
    defaults.update(perfil_kwargs)
    Perfil.objects.create(user=user, **defaults)
    return user


def _make_categoria(nome=Categoria.Tipo.EDITAL):
    return Categoria.objects.get_or_create(nome=nome)[0]


def _make_fonte():
    return Fonte.objects.get_or_create(
        nome="Portal UFCA",
        defaults={
            "tipo": Fonte.Tipo.HTML,
            "url": "https://www.ufca.edu.br/",
            "intervalo_coleta": 60,
        },
    )[0]


def _make_conteudo(hash_dedup, cursos=None, interesses=None, universal=False, **kwargs):
    dados = {
        "titulo": kwargs.pop("titulo", f"Conteúdo {hash_dedup}"),
        "corpo": "Corpo do conteúdo.",
        "resumo": "Resumo.",
        "data_publicacao": kwargs.pop("data_publicacao", timezone.now()),
        "categoria": kwargs.pop("categoria", None) or _make_categoria(),
        "fonte": kwargs.pop("fonte", None) or _make_fonte(),
        "hash_dedup": hash_dedup,
        "universal": universal,
        "cursos": cursos or [],
    }
    dados.update(kwargs)
    conteudo = Conteudo.objects.create(**dados)
    if interesses:
        conteudo.interesses.set(interesses)
    return conteudo


class TestFeedAcesso:
    def test_requires_login(self, client):
        response = client.get(reverse("feed"))

        assert response.status_code == 302
        assert response.url.startswith(reverse("login"))


class TestFeedFiltragem:
    def test_conteudo_universal_aparece_para_qualquer_perfil(self, client):
        user = _make_user_with_perfil(curso=Perfil.Curso.DIREITO)
        _make_conteudo("u1", universal=True)
        client.force_login(user)

        response = client.get(reverse("feed"))

        assert response.status_code == 200
        titulos = [item["titulo"] for item in response.json()["results"]]
        assert "Conteúdo u1" in titulos

    def test_filtra_por_curso_do_perfil(self, client):
        user = _make_user_with_perfil(curso=Perfil.Curso.DIREITO)
        _make_conteudo("c1", cursos=[Perfil.Curso.DIREITO])
        _make_conteudo("c2", cursos=[Perfil.Curso.MEDICINA])
        client.force_login(user)

        response = client.get(reverse("feed"))

        titulos = [item["titulo"] for item in response.json()["results"]]
        assert "Conteúdo c1" in titulos
        assert "Conteúdo c2" not in titulos

    def test_filtra_por_interesses_do_perfil(self, client):
        interesse_seguido = Interesse.objects.create(nome="Editais")
        interesse_nao_seguido = Interesse.objects.create(nome="Estágios")
        user = _make_user_with_perfil(curso="")
        user.perfil.interesses.add(interesse_seguido)
        _make_conteudo("i1", interesses=[interesse_seguido])
        _make_conteudo("i2", interesses=[interesse_nao_seguido])
        client.force_login(user)

        response = client.get(reverse("feed"))

        titulos = [item["titulo"] for item in response.json()["results"]]
        assert "Conteúdo i1" in titulos
        assert "Conteúdo i2" not in titulos

    def test_conteudo_sem_relacao_nao_aparece(self, client):
        user = _make_user_with_perfil(curso=Perfil.Curso.DIREITO)
        _make_conteudo("n1", cursos=[Perfil.Curso.MEDICINA])
        client.force_login(user)

        response = client.get(reverse("feed"))

        assert response.json()["results"] == []


class TestFeedMotivo:
    def test_motivo_explica_conteudo_universal(self, client):
        user = _make_user_with_perfil()
        _make_conteudo("u1", universal=True)
        client.force_login(user)

        response = client.get(reverse("feed"))

        item = response.json()["results"][0]
        assert "institucional" in item["motivo"].lower()

    def test_motivo_explica_match_por_curso(self, client):
        user = _make_user_with_perfil(curso=Perfil.Curso.DIREITO)
        _make_conteudo("c1", cursos=[Perfil.Curso.DIREITO])
        client.force_login(user)

        response = client.get(reverse("feed"))

        item = response.json()["results"][0]
        assert "curso" in item["motivo"].lower()

    def test_motivo_explica_match_por_interesse(self, client):
        interesse = Interesse.objects.create(nome="Editais")
        user = _make_user_with_perfil(curso="")
        user.perfil.interesses.add(interesse)
        _make_conteudo("i1", interesses=[interesse])
        client.force_login(user)

        response = client.get(reverse("feed"))

        item = response.json()["results"][0]
        assert "editais" in item["motivo"].lower()


class TestFeedAjusteDeRelevancia:
    def test_conteudo_marcado_como_irrelevante_some_do_feed(self, client):
        user = _make_user_with_perfil()
        conteudo = _make_conteudo("r1", universal=True)
        Feedback.objects.create(usuario=user, conteudo=conteudo, tipo=Feedback.Tipo.NEGATIVO)
        client.force_login(user)

        response = client.get(reverse("feed"))

        titulos = [item["titulo"] for item in response.json()["results"]]
        assert "Conteúdo r1" not in titulos

    def test_categoria_com_feedback_positivo_e_priorizada_na_ordenacao(self, client):
        user = _make_user_with_perfil()
        categoria_curtida = _make_categoria(Categoria.Tipo.EDITAL)
        categoria_neutra = _make_categoria(Categoria.Tipo.COMUNICADO)
        agora = timezone.now()

        conteudo_curtido_antigo = _make_conteudo(
            "antigo",
            universal=True,
            categoria=categoria_curtida,
            data_publicacao=agora - timezone.timedelta(days=1),
        )
        _make_conteudo(
            "recente",
            universal=True,
            categoria=categoria_neutra,
            data_publicacao=agora,
        )
        Feedback.objects.create(
            usuario=user, conteudo=conteudo_curtido_antigo, tipo=Feedback.Tipo.POSITIVO
        )
        # outro conteúdo da categoria curtida, ainda sem feedback
        _make_conteudo(
            "novo_da_categoria_curtida",
            universal=True,
            categoria=categoria_curtida,
            data_publicacao=agora - timezone.timedelta(hours=1),
        )
        client.force_login(user)

        response = client.get(reverse("feed"))

        titulos = [item["titulo"] for item in response.json()["results"]]
        # mesmo sendo mais antigo, o conteúdo de categoria curtida vem antes do
        # conteúdo mais recente de categoria sem histórico de feedback
        assert titulos.index("Conteúdo novo_da_categoria_curtida") < titulos.index(
            "Conteúdo recente"
        )

    def test_categoria_com_feedback_negativo_e_rebaixada_na_ordenacao(self, client):
        user = _make_user_with_perfil()
        categoria_rejeitada = _make_categoria(Categoria.Tipo.PRAZO)
        categoria_neutra = _make_categoria(Categoria.Tipo.COMUNICADO)
        agora = timezone.now()

        conteudo_rejeitado_original = _make_conteudo(
            "rejeitado_original", universal=True, categoria=categoria_rejeitada
        )
        Feedback.objects.create(
            usuario=user, conteudo=conteudo_rejeitado_original, tipo=Feedback.Tipo.NEGATIVO
        )
        _make_conteudo(
            "mesma_categoria_rejeitada",
            universal=True,
            categoria=categoria_rejeitada,
            data_publicacao=agora,
        )
        _make_conteudo(
            "categoria_neutra",
            universal=True,
            categoria=categoria_neutra,
            data_publicacao=agora - timezone.timedelta(hours=1),
        )
        client.force_login(user)

        response = client.get(reverse("feed"))

        titulos = [item["titulo"] for item in response.json()["results"]]
        assert titulos.index("Conteúdo categoria_neutra") < titulos.index(
            "Conteúdo mesma_categoria_rejeitada"
        )


class TestFeedPaginacao:
    def test_pagina_padrao_traz_ate_20_itens_mais_recentes(self, client):
        user = _make_user_with_perfil()
        agora = timezone.now()
        for i in range(25):
            _make_conteudo(
                f"p{i}", universal=True, data_publicacao=agora - timezone.timedelta(minutes=i)
            )
        client.force_login(user)

        response = client.get(reverse("feed"))
        corpo = response.json()

        assert corpo["count"] == 25
        assert corpo["page_size"] == 20
        assert len(corpo["results"]) == 20
        assert corpo["total_pages"] == 2
        # o mais recente (i=0) deve vir primeiro
        assert corpo["results"][0]["titulo"] == "Conteúdo p0"

    def test_segunda_pagina_traz_itens_restantes(self, client):
        user = _make_user_with_perfil()
        agora = timezone.now()
        for i in range(25):
            _make_conteudo(
                f"p{i}", universal=True, data_publicacao=agora - timezone.timedelta(minutes=i)
            )
        client.force_login(user)

        response = client.get(reverse("feed"), {"page": 2})
        corpo = response.json()

        assert len(corpo["results"]) == 5
        assert corpo["page"] == 2
