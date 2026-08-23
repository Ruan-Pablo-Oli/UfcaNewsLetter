"""Painel de gerenciamento de fontes (issue #26, US-05.1)."""
import json
from datetime import datetime

import pytest
from django.contrib.auth.models import User

from newsletter.models import Conteudo, Fonte


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        "admin", is_staff=True, is_superuser=True
    )


@pytest.fixture
def usuario(db):
    return User.objects.create_user("comum")


@pytest.fixture
def cliente_admin(admin, client):
    client.force_login(admin)
    return client


def _criar(cliente, **overrides):
    payload = {
        "nome": "Portal UFCA",
        "tipo": "html",
        "url": "https://www.ufca.edu.br/noticias/",
        "intervalo_coleta": 60,
    }
    payload.update(overrides)
    return cliente.post(
        "/fontes/criar/",
        data=json.dumps(payload),
        content_type="application/json",
    )


# --- controle de acesso ---


@pytest.mark.django_db
def test_anonimo_nao_acessa(client):
    r = client.get("/fontes/")
    assert r.status_code in (302, 401, 403)


@pytest.mark.django_db
def test_usuario_comum_nao_acessa(usuario, client):
    client.force_login(usuario)
    r = client.get("/fontes/")
    assert r.status_code in (302, 403)


@pytest.mark.django_db
def test_admin_lista_fontes(cliente_admin):
    Fonte.objects.create(nome="F", tipo="html", url="https://x/", intervalo_coleta=60)
    r = cliente_admin.get("/fontes/")
    assert r.status_code == 200
    assert len(r.json()["fontes"]) == 1


# --- criar ---


@pytest.mark.django_db
def test_admin_cria_fonte(cliente_admin):
    r = _criar(cliente_admin)
    assert r.status_code == 201
    fonte = Fonte.objects.get(nome="Portal UFCA")
    assert fonte.tipo == "html"
    assert fonte.ativo is True


@pytest.mark.django_db
def test_criar_rejeita_tipo_invalido(cliente_admin):
    r = _criar(cliente_admin, tipo="rss")
    assert r.status_code == 400
    assert not Fonte.objects.filter(nome="Portal UFCA").exists()


@pytest.mark.django_db
def test_criar_rejeita_intervalo_negativo(cliente_admin):
    r = _criar(cliente_admin, intervalo_coleta=-5)
    assert r.status_code == 400


# --- editar ---


@pytest.mark.django_db
def test_admin_desativa_e_ativa_fonte(cliente_admin):
    fonte = Fonte.objects.create(
        nome="F", tipo="html", url="https://x/", intervalo_coleta=60
    )
    r = cliente_admin.patch(
        f"/fontes/{fonte.id}/",
        data=json.dumps({"ativo": False}),
        content_type="application/json",
    )
    assert r.status_code == 200
    fonte.refresh_from_db()
    assert fonte.ativo is False

    cliente_admin.patch(
        f"/fontes/{fonte.id}/",
        data=json.dumps({"ativo": True}),
        content_type="application/json",
    )
    fonte.refresh_from_db()
    assert fonte.ativo is True


@pytest.mark.django_db
def test_editar_url_valida(cliente_admin):
    fonte = Fonte.objects.create(
        nome="F", tipo="html", url="https://x/", intervalo_coleta=60
    )
    r = cliente_admin.patch(
        f"/fontes/{fonte.id}/",
        data=json.dumps({"url": "https://novo.ufca.edu.br/"}),
        content_type="application/json",
    )
    assert r.status_code == 200
    fonte.refresh_from_db()
    assert fonte.url == "https://novo.ufca.edu.br/"


# --- remover ---


@pytest.mark.django_db
def test_remover_fonte_sem_conteudo(cliente_admin):
    fonte = Fonte.objects.create(
        nome="F", tipo="html", url="https://x/", intervalo_coleta=60
    )
    r = cliente_admin.delete(f"/fontes/{fonte.id}/remover/")
    assert r.status_code == 200
    assert not Fonte.objects.filter(pk=fonte.id).exists()


@pytest.mark.django_db
def test_delete_bloqueado_por_protect(admin, client, db):

    client.force_login(admin)
    f = Fonte.objects.create(
        nome="Com conteudo", tipo="html", url="https://x/", intervalo_coleta=60
    )
    Conteudo.objects.create(
        titulo="C",
        corpo="c",
        data_publicacao=datetime(2026, 8, 1),
        fonte=f,
        hash_dedup="hash-x",
    )
    r = client.delete(f"/fontes/{f.id}/remover/")
    assert r.status_code == 409
    assert Fonte.objects.filter(pk=f.id).exists()


@pytest.mark.django_db
def test_404_em_fonte_inexistente(cliente_admin):
    assert cliente_admin.delete("/fontes/9999/remover/").status_code == 404


# --- integração com coletor: alteração vale no próximo ciclo ---


@pytest.mark.django_db
def test_fonte_desativada_sai_da_fila_de_coleta(cliente_admin):
    from newsletter.coleta import fontes_devidas

    fonte = Fonte.objects.create(
        nome="F", tipo="html", url="https://x/", intervalo_coleta=60
    )
    assert fonte in fontes_devidas()

    cliente_admin.patch(
        f"/fontes/{fonte.id}/",
        data=json.dumps({"ativo": False}),
        content_type="application/json",
    )
    assert fonte not in fontes_devidas()
