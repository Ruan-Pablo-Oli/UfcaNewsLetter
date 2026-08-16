"""Testes do endpoint de histórico de entregas (US-07.2, issue #29)."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from newsletter.models import Categoria, Conteudo, Entrega, Fonte

pytestmark = pytest.mark.django_db


def _make_user(username="aluno"):
    return get_user_model().objects.create_user(username=username, password="senha123")


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


def _make_conteudo(hash_dedup, titulo=None, **kwargs):
    dados = {
        "titulo": titulo or f"Conteúdo {hash_dedup}",
        "corpo": "Corpo do conteúdo.",
        "resumo": "Resumo.",
        "data_publicacao": timezone.now(),
        "categoria": kwargs.pop("categoria", None) or _make_categoria(),
        "fonte": kwargs.pop("fonte", None) or _make_fonte(),
        "hash_dedup": hash_dedup,
        "universal": True,
        "cursos": [],
        "status": Conteudo.Status.APROVADO,
        "url": kwargs.pop("url", f"https://www.ufca.edu.br/{hash_dedup}/"),
    }
    dados.update(kwargs)
    return Conteudo.objects.create(**dados)


def _make_entrega(usuario, conteudo, canal=Entrega.Canal.EMAIL, data_envio=None):
    entrega = Entrega.objects.create(
        conteudo=conteudo,
        usuario=usuario,
        canal=canal,
    )
    if data_envio is not None:
        # data_envio é auto_now_add: só é alterável via update().
        Entrega.objects.filter(pk=entrega.pk).update(data_envio=data_envio)
        entrega.refresh_from_db()
    return entrega


def _login(client, user):
    client.force_login(user)


class TestHistoricoAcesso:
    def test_requires_login(self, client):
        response = client.get(reverse("historico"))

        assert response.status_code == 302
        assert response.url.startswith(reverse("login"))


class TestHistoricoListagem:
    def test_lista_entregas_do_usuario(self, client):
        user = _make_user()
        outro = _make_user("outro")
        _login(client, user)
        conteudo = _make_conteudo("hash-1", titulo="Edital PIBIC")
        _make_entrega(user, conteudo)
        _make_entrega(outro, conteudo)

        response = client.get(reverse("historico"))
        dados = response.json()

        assert response.status_code == 200
        assert dados["count"] == 1
        assert dados["results"][0]["titulo"] == "Edital PIBIC"

    def test_ordena_por_data_envio_decrescente(self, client):
        user = _make_user()
        _login(client, user)
        antigo = _make_conteudo("hash-1", titulo="Aviso antigo")
        recente = _make_conteudo("hash-2", titulo="Aviso recente")
        _make_entrega(user, antigo, data_envio=timezone.now() - timezone.timedelta(days=10))
        _make_entrega(user, recente, data_envio=timezone.now())

        response = client.get(reverse("historico"))
        dados = response.json()

        assert [item["titulo"] for item in dados["results"]] == [
            "Aviso recente",
            "Aviso antigo",
        ]

    def test_inclui_link_para_conteudo_original(self, client):
        user = _make_user()
        _login(client, user)
        conteudo = _make_conteudo("hash-1", titulo="Edital PIBIC")
        _make_entrega(user, conteudo)

        response = client.get(reverse("historico"))
        dados = response.json()

        assert dados["results"][0]["url"] == "https://www.ufca.edu.br/hash-1/"


class TestHistoricoFiltros:
    def test_filtra_por_periodo(self, client):
        user = _make_user()
        _login(client, user)
        antigo = _make_conteudo("hash-1", titulo="Aviso antigo")
        recente = _make_conteudo("hash-2", titulo="Aviso recente")
        _make_entrega(user, antigo, data_envio=timezone.now() - timezone.timedelta(days=30))
        _make_entrega(user, recente, data_envio=timezone.now())
        inicio = (timezone.now() - timezone.timedelta(days=7)).date().isoformat()

        response = client.get(reverse("historico"), {"data_inicio": inicio})
        dados = response.json()

        assert dados["count"] == 1
        assert dados["results"][0]["titulo"] == "Aviso recente"

    def test_filtra_por_categoria(self, client):
        user = _make_user()
        _login(client, user)
        edital = _make_categoria(Categoria.Tipo.EDITAL)
        evento = _make_categoria(Categoria.Tipo.EVENTO)
        conteudo_edital = _make_conteudo("hash-1", titulo="Edital PIBIC", categoria=edital)
        conteudo_evento = _make_conteudo("hash-2", titulo="Semana Universitária", categoria=evento)
        _make_entrega(user, conteudo_edital)
        _make_entrega(user, conteudo_evento)

        response = client.get(reverse("historico"), {"categoria": Categoria.Tipo.EVENTO})
        dados = response.json()

        assert dados["count"] == 1
        assert dados["results"][0]["titulo"] == "Semana Universitária"


class TestHistoricoPaginacao:
    def test_pagina_resultados(self, client):
        user = _make_user()
        _login(client, user)
        for i in range(3):
            _make_entrega(user, _make_conteudo(f"hash-{i}", titulo=f"Aviso {i}"))

        response = client.get(reverse("historico"), {"page_size": 2})
        dados = response.json()

        assert dados["count"] == 3
        assert dados["total_pages"] == 2
        assert len(dados["results"]) == 2
