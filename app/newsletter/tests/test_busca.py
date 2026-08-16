"""Testes do endpoint de busca de conteúdos (US-07.1, issue #28)."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from newsletter.models import Categoria, Conteudo, Fonte, Perfil

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


def _make_conteudo(hash_dedup, titulo=None, corpo=None, **kwargs):
    dados = {
        "titulo": titulo or f"Conteúdo {hash_dedup}",
        "corpo": corpo or "Corpo do conteúdo.",
        "resumo": "Resumo.",
        "data_publicacao": kwargs.pop("data_publicacao", timezone.now()),
        "categoria": kwargs.pop("categoria", None) or _make_categoria(),
        "fonte": kwargs.pop("fonte", None) or _make_fonte(),
        "hash_dedup": hash_dedup,
        "universal": kwargs.pop("universal", False),
        "cursos": kwargs.pop("cursos", []),
        "status": kwargs.pop("status", Conteudo.Status.APROVADO),
    }
    dados.update(kwargs)
    return Conteudo.objects.create(**dados)


def _login(client, user):
    client.force_login(user)


class TestBuscaAcesso:
    def test_requires_login(self, client):
        response = client.get(reverse("busca"))

        assert response.status_code == 302
        assert response.url.startswith(reverse("login"))


class TestBuscaPalavraChave:
    def test_busca_por_titulo(self, client):
        user = _make_user_with_perfil()
        _login(client, user)
        _make_conteudo("hash-1", titulo="Edital de Monitoria 2026.2", universal=True)
        _make_conteudo("hash-2", titulo="Cardápio do Restaurante", universal=True)

        response = client.get(reverse("busca"), {"q": "monitoria"})
        dados = response.json()

        assert response.status_code == 200
        assert dados["count"] == 1
        assert dados["results"][0]["titulo"] == "Edital de Monitoria 2026.2"

    def test_busca_por_corpo(self, client):
        user = _make_user_with_perfil()
        _login(client, user)
        _make_conteudo(
            "hash-1",
            titulo="Aviso importante",
            corpo="Prazo de inscrição em 10 dias",
            universal=True,
        )
        _make_conteudo("hash-2", titulo="Outro aviso", corpo="Sem relação", universal=True)

        response = client.get(reverse("busca"), {"q": "inscrição"})
        dados = response.json()

        assert dados["count"] == 1
        assert dados["results"][0]["titulo"] == "Aviso importante"

    def test_relevancia_titulo_antes_do_corpo(self, client):
        user = _make_user_with_perfil()
        _login(client, user)
        _make_conteudo(
            "hash-1",
            titulo="Comunicado genérico",
            corpo="Edital de bolsas 2026",
            universal=True,
        )
        _make_conteudo(
            "hash-2",
            titulo="Edital de bolsas 2026",
            corpo="Inscrições abertas",
            universal=True,
        )

        response = client.get(reverse("busca"), {"q": "edital de bolsas"})
        dados = response.json()

        assert dados["count"] == 2
        assert dados["results"][0]["titulo"] == "Edital de bolsas 2026"

    def test_sem_resultado(self, client):
        user = _make_user_with_perfil()
        _login(client, user)
        _make_conteudo("hash-1", titulo="Aviso institucional", universal=True)

        response = client.get(reverse("busca"), {"q": "inexistente"})
        dados = response.json()

        assert dados["count"] == 0
        assert dados["results"] == []


class TestBuscaFiltros:
    def test_filtro_por_categoria(self, client):
        user = _make_user_with_perfil()
        _login(client, user)
        edital = _make_categoria(Categoria.Tipo.EDITAL)
        evento = _make_categoria(Categoria.Tipo.EVENTO)
        _make_conteudo("hash-1", titulo="Edital PIBIC", categoria=edital, universal=True)
        _make_conteudo("hash-2", titulo="Semana Universitária", categoria=evento, universal=True)

        response = client.get(reverse("busca"), {"categoria": Categoria.Tipo.EVENTO})
        dados = response.json()

        assert dados["count"] == 1
        assert dados["results"][0]["titulo"] == "Semana Universitária"

    def test_filtro_por_curso(self, client):
        user = _make_user_with_perfil(curso=Perfil.Curso.DIREITO)
        _login(client, user)
        _make_conteudo(
            "hash-1",
            titulo="Edital de Direito",
            cursos=[Perfil.Curso.DIREITO],
        )
        _make_conteudo(
            "hash-2",
            titulo="Edital de Computação",
            cursos=[Perfil.Curso.CIENCIA_DA_COMPUTACAO],
            universal=False,
        )

        response = client.get(reverse("busca"), {"curso": Perfil.Curso.DIREITO})
        dados = response.json()

        assert dados["count"] == 1
        assert dados["results"][0]["titulo"] == "Edital de Direito"

    def test_filtro_por_periodo(self, client):
        user = _make_user_with_perfil()
        _login(client, user)
        _make_conteudo(
            "hash-1",
            titulo="Aviso antigo",
            data_publicacao=timezone.now() - timezone.timedelta(days=30),
            universal=True,
        )
        _make_conteudo(
            "hash-2",
            titulo="Aviso recente",
            data_publicacao=timezone.now(),
            universal=True,
        )
        inicio = (timezone.now() - timezone.timedelta(days=7)).date().isoformat()

        response = client.get(reverse("busca"), {"data_inicio": inicio})
        dados = response.json()

        assert dados["count"] == 1
        assert dados["results"][0]["titulo"] == "Aviso recente"


class TestBuscaVisibilidade:
    def test_ignora_conteudo_pendente(self, client):
        user = _make_user_with_perfil()
        _login(client, user)
        _make_conteudo(
            "hash-1",
            titulo="Edital pendente",
            status=Conteudo.Status.PENDENTE,
            universal=True,
        )

        response = client.get(reverse("busca"), {"q": "edital"})
        dados = response.json()

        assert dados["count"] == 0

    def test_nao_mostra_conteudo_fora_do_perfil(self, client):
        user = _make_user_with_perfil(curso=Perfil.Curso.DIREITO)
        _login(client, user)
        _make_conteudo(
            "hash-1",
            titulo="Edital de Computação",
            cursos=[Perfil.Curso.CIENCIA_DA_COMPUTACAO],
            universal=False,
        )

        response = client.get(reverse("busca"), {"q": "edital"})
        dados = response.json()

        assert dados["count"] == 0
