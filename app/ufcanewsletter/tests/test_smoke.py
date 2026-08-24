"""Smoke tests: the app boots and responds."""
import pytest


def test_raiz_entrega_a_spa(client):
    """A raiz devolve a SPA; sem build, a página de instrução (dev/CI)."""
    response = client.get("/")

    assert response.status_code == 200
    assert b"UFCA Newsletter" in response.content


def test_rota_do_react_router_cai_na_spa(client):
    """Recarregar uma rota do front não pode dar 404 no Django."""
    response = client.get("/qualquer-rota-do-front")

    assert response.status_code == 200
    assert b"UFCA Newsletter" in response.content


@pytest.mark.django_db
def test_rotas_do_django_nao_sao_engolidas_pelo_curinga(client):
    """O curinga da SPA não pode capturar as rotas da API nem do admin."""
    assert client.get("/admin/login/").status_code == 200
    # /feed/ exige login: 302 prova que a rota do Django respondeu, não a SPA.
    assert client.get("/feed/").status_code == 302


@pytest.mark.django_db
def test_admin_login_page_responds_200(client):
    response = client.get("/admin/login/")

    assert response.status_code == 200
