"""Smoke tests: the app boots and responds."""
import pytest


def test_hello_world_responds_200(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.content == b"Hello World"


@pytest.mark.django_db
def test_admin_login_page_responds_200(client):
    response = client.get("/admin/login/")

    assert response.status_code == 200
