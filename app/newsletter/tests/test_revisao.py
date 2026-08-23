"""Fila de revisão manual (issue #27, US-05.2)."""
import json
from datetime import datetime

import pytest
from django.contrib.auth.models import User

from newsletter.models import Conteudo, Fonte, Perfil


@pytest.fixture
def fonte(db):
    return Fonte.objects.create(
        nome="Portal", tipo=Fonte.Tipo.HTML, url="https://x/", intervalo_coleta=60
    )


@pytest.fixture
def admin(db, client):
    user = User.objects.create_user("admin", is_staff=True)
    client.force_login(user)
    return client


def _pendente(fonte, titulo="Sem categoria", hash_dedup="h-1"):
    return Conteudo.objects.create(
        titulo=titulo,
        corpo="Corpo sem evidência de categoria.",
        data_publicacao=datetime(2026, 8, 1),
        fonte=fonte,
        status=Conteudo.Status.PENDENTE,
        hash_dedup=hash_dedup,
    )


def test_pendente_aparece_na_fila(fonte, admin):
    _pendente(fonte)
    r = admin.get("/revisao/")
    assert r.status_code == 200
    dados = r.json()
    assert dados["total"] == 1
    item = dados["itens"][0]
    assert "data_publicacao" in item and "fonte_nome" in item


def test_aprovado_nao_aparece_na_fila(fonte, admin):
    Conteudo.objects.create(
        titulo="Ok",
        corpo="c",
        data_publicacao=datetime(2026, 8, 1),
        fonte=fonte,
        status=Conteudo.Status.APROVADO,
        universal=True,
        hash_dedup="h-ok",
    )
    assert admin.get("/revisao/").json()["total"] == 0


def test_aprovar_com_categoria(fonte, admin):
    c = _pendente(fonte)
    r = admin.post(
        f"/revisao/{c.id}/aprovar/",
        data=json.dumps({"categoria": "edital"}),
        content_type="application/json",
    )
    assert r.status_code == 200
    c.refresh_from_db()
    assert c.status == Conteudo.Status.APROVADO
    assert c.categoria.nome == "edital"


def test_aprovado_entra_no_feed(fonte, admin):
    """CA: aprovado entra no fluxo normal de distribuição."""
    from django.contrib.auth.models import User

    from newsletter.feed import feed_queryset_for_perfil

    c = _pendente(fonte, hash_dedup="h-feed")
    user = User.objects.create_user("aluno")
    perfil = Perfil.objects.create(user=user, curso="", periodo=1)

    assert not feed_queryset_for_perfil(perfil).filter(pk=c.pk).exists()

    admin.post(f"/revisao/{c.id}/aprovar/", data=b"{}", content_type="application/json")

    # Universal + aprovado aparece no feed.
    c.refresh_from_db()
    c.universal = True
    c.save(update_fields=["universal"])
    assert feed_queryset_for_perfil(perfil).filter(pk=c.pk).exists()


def test_descartar(fonte, admin):
    c = _pendente(fonte)
    r = admin.post(f"/revisao/{c.id}/descartar/")
    assert r.status_code == 200
    c.refresh_from_db()
    assert c.status == Conteudo.Status.DESCARTADO


def test_reclassificar_aplica_classificador(fonte, admin):
    c = _pendente(fonte, titulo="Edital de monitoria 2026", hash_dedup="h-r")
    r = admin.post(f"/revisao/{c.id}/reclassificar/")
    assert r.status_code == 200
    assert r.json()["reclassificado"] is True
    c.refresh_from_db()
    assert c.categoria is not None


def test_reclassificar_sem_evidencia_continua_na_fila(fonte, admin):
    c = _pendente(fonte)  # corpo/título sem keywords
    r = admin.post(f"/revisao/{c.id}/reclassificar/")
    assert r.json()["reclassificado"] is False
    c.refresh_from_db()
    assert c.status == Conteudo.Status.PENDENTE


def test_acesso_restrito(db, client):
    assert client.get("/revisao/").status_code in (302, 403)


def test_404_para_conteudo_inexistente(admin):
    assert admin.post("/revisao/9999/aprovar/").status_code == 404


def test_aprovar_categoria_invalida(fonte, admin):
    c = _pendente(fonte)
    r = admin.post(
        f"/revisao/{c.id}/aprovar/",
        data=json.dumps({"categoria": "foo"}),
        content_type="application/json",
    )
    assert r.status_code == 400


def test_fila_mostra_origem_e_data(fonte, admin):
    _pendente(fonte)
    item = admin.get("/revisao/").json()["itens"][0]
    assert item["fonte_nome"] == "Portal"
    assert "2026-08-01" in item["data_publicacao"]
