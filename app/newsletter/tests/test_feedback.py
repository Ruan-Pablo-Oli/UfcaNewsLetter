"""Testes dos endpoints de feedback de relevância (US-01.3)."""
import json

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from newsletter.models import Categoria, Conteudo, Feedback, Fonte

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


def _make_conteudo(hash_dedup="hash-1", categoria=None, **kwargs):
    dados = {
        "titulo": kwargs.pop("titulo", f"Conteúdo {hash_dedup}"),
        "corpo": "Corpo do conteúdo.",
        "resumo": "Resumo.",
        "data_publicacao": kwargs.pop("data_publicacao", timezone.now()),
        "categoria": categoria or _make_categoria(),
        "fonte": kwargs.pop("fonte", None) or _make_fonte(),
        "hash_dedup": hash_dedup,
        "universal": kwargs.pop("universal", True),
        "cursos": kwargs.pop("cursos", []),
    }
    dados.update(kwargs)
    return Conteudo.objects.create(**dados)


class TestFeedbackAcesso:
    def test_post_requires_login(self, client):
        conteudo = _make_conteudo()

        response = client.post(
            reverse("feedback"),
            data=json.dumps({"conteudo_id": conteudo.id, "tipo": "positivo"}),
            content_type="application/json",
        )

        assert response.status_code == 302
        assert response.url.startswith(reverse("login"))

    def test_historico_requires_login(self, client):
        response = client.get(reverse("feedback_historico"))

        assert response.status_code == 302
        assert response.url.startswith(reverse("login"))

    def test_get_not_allowed_on_feedback(self, client):
        user = _make_user()
        client.force_login(user)

        response = client.get(reverse("feedback"))

        assert response.status_code == 405


class TestFeedbackRegistro:
    def test_registra_feedback_positivo(self, client):
        user = _make_user()
        conteudo = _make_conteudo()
        client.force_login(user)

        response = client.post(
            reverse("feedback"),
            data=json.dumps({"conteudo_id": conteudo.id, "tipo": "positivo"}),
            content_type="application/json",
        )

        assert response.status_code == 201
        corpo = response.json()
        assert corpo["conteudo_id"] == conteudo.id
        assert corpo["tipo"] == "positivo"
        assert Feedback.objects.get(usuario=user, conteudo=conteudo).tipo == "positivo"

    def test_reenvio_atualiza_marcacao_existente(self, client):
        user = _make_user()
        conteudo = _make_conteudo()
        Feedback.objects.create(usuario=user, conteudo=conteudo, tipo=Feedback.Tipo.POSITIVO)
        client.force_login(user)

        response = client.post(
            reverse("feedback"),
            data=json.dumps({"conteudo_id": conteudo.id, "tipo": "negativo"}),
            content_type="application/json",
        )

        assert response.status_code == 200
        assert Feedback.objects.filter(usuario=user, conteudo=conteudo).count() == 1
        assert Feedback.objects.get(usuario=user, conteudo=conteudo).tipo == "negativo"

    def test_tipo_invalido_retorna_400(self, client):
        user = _make_user()
        conteudo = _make_conteudo()
        client.force_login(user)

        response = client.post(
            reverse("feedback"),
            data=json.dumps({"conteudo_id": conteudo.id, "tipo": "neutro"}),
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_conteudo_id_ausente_retorna_400(self, client):
        user = _make_user()
        client.force_login(user)

        response = client.post(
            reverse("feedback"),
            data=json.dumps({"tipo": "positivo"}),
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_conteudo_inexistente_retorna_404(self, client):
        user = _make_user()
        client.force_login(user)

        response = client.post(
            reverse("feedback"),
            data=json.dumps({"conteudo_id": 9999, "tipo": "positivo"}),
            content_type="application/json",
        )

        assert response.status_code == 404

    def test_json_invalido_retorna_400(self, client):
        user = _make_user()
        client.force_login(user)

        response = client.post(
            reverse("feedback"),
            data="não é json",
            content_type="application/json",
        )

        assert response.status_code == 400


class TestFeedbackHistorico:
    def test_lista_apenas_feedbacks_do_usuario(self, client):
        user = _make_user("aluno1")
        outro_user = _make_user("aluno2")
        conteudo1 = _make_conteudo("h1")
        conteudo2 = _make_conteudo("h2")
        Feedback.objects.create(usuario=user, conteudo=conteudo1, tipo=Feedback.Tipo.POSITIVO)
        Feedback.objects.create(usuario=outro_user, conteudo=conteudo2, tipo=Feedback.Tipo.NEGATIVO)
        client.force_login(user)

        response = client.get(reverse("feedback_historico"))

        corpo = response.json()
        assert corpo["count"] == 1
        assert corpo["results"][0]["conteudo_id"] == conteudo1.id
        assert corpo["results"][0]["tipo"] == "positivo"

    def test_ordena_do_mais_recente_para_o_mais_antigo(self, client):
        user = _make_user()
        conteudo1 = _make_conteudo("h1")
        conteudo2 = _make_conteudo("h2")
        mais_antigo = Feedback.objects.create(
            usuario=user, conteudo=conteudo1, tipo=Feedback.Tipo.POSITIVO
        )
        mais_antigo.criado_em = timezone.now() - timezone.timedelta(days=1)
        mais_antigo.save(update_fields=["criado_em"])
        Feedback.objects.create(usuario=user, conteudo=conteudo2, tipo=Feedback.Tipo.NEGATIVO)
        client.force_login(user)

        response = client.get(reverse("feedback_historico"))

        titulos = [item["conteudo_id"] for item in response.json()["results"]]
        assert titulos == [conteudo2.id, conteudo1.id]


class TestDesfazerMarcacao:
    """Desfazer é apagar o registro, não trocá-lo por positivo (US-01.3)."""

    def test_delete_apaga_a_marcacao(self, client):
        user = _make_user()
        client.force_login(user)
        conteudo = _make_conteudo()
        Feedback.objects.create(usuario=user, conteudo=conteudo, tipo=Feedback.Tipo.NEGATIVO)

        response = client.delete(f"/feedback/{conteudo.id}/")

        assert response.status_code == 200
        assert response.json()["removido"] is True
        assert not Feedback.objects.filter(usuario=user, conteudo=conteudo).exists()

    def test_conteudo_volta_ao_feed_depois_de_desfazer(self, client):
        from newsletter.feed import feed_queryset_for_perfil
        from newsletter.models import Perfil

        user = _make_user()
        client.force_login(user)
        perfil = Perfil.objects.create(user=user, curso="", periodo=1)
        # O helper cria conteúdo pendente; o feed só mostra aprovado.
        conteudo = _make_conteudo(universal=True, status=Conteudo.Status.APROVADO)
        Feedback.objects.create(usuario=user, conteudo=conteudo, tipo=Feedback.Tipo.NEGATIVO)
        assert conteudo not in feed_queryset_for_perfil(perfil)

        client.delete(f"/feedback/{conteudo.id}/")

        assert conteudo in feed_queryset_for_perfil(perfil)

    def test_delete_de_marcacao_inexistente_devolve_404(self, client):
        user = _make_user()
        client.force_login(user)
        conteudo = _make_conteudo()

        assert client.delete(f"/feedback/{conteudo.id}/").status_code == 404

    def test_delete_nao_apaga_marcacao_de_outro_usuario(self, client):
        dono = _make_user("dono")
        outro = _make_user("outro")
        client.force_login(outro)
        conteudo = _make_conteudo()
        Feedback.objects.create(usuario=dono, conteudo=conteudo, tipo=Feedback.Tipo.NEGATIVO)

        assert client.delete(f"/feedback/{conteudo.id}/").status_code == 404
        assert Feedback.objects.filter(usuario=dono, conteudo=conteudo).exists()

    def test_delete_requires_login(self, client):
        conteudo = _make_conteudo()

        response = client.delete(f"/feedback/{conteudo.id}/")

        assert response.status_code == 302


class TestHistoricoDeMarcacoes:
    def test_filtra_por_tipo(self, client):
        user = _make_user()
        client.force_login(user)
        ruim = _make_conteudo("hash-ruim")
        bom = _make_conteudo("hash-bom")
        Feedback.objects.create(usuario=user, conteudo=ruim, tipo=Feedback.Tipo.NEGATIVO)
        Feedback.objects.create(usuario=user, conteudo=bom, tipo=Feedback.Tipo.POSITIVO)

        dados = client.get("/feedback/historico/?tipo=negativo").json()

        assert dados["count"] == 1
        assert dados["results"][0]["conteudo_id"] == ruim.id

    def test_tipo_invalido_e_ignorado(self, client):
        user = _make_user()
        client.force_login(user)
        Feedback.objects.create(
            usuario=user, conteudo=_make_conteudo(), tipo=Feedback.Tipo.NEGATIVO
        )

        assert client.get("/feedback/historico/?tipo=qualquer").json()["count"] == 1

    def test_traz_dados_para_reconhecer_o_conteudo(self, client):
        user = _make_user()
        client.force_login(user)
        conteudo = _make_conteudo()
        Feedback.objects.create(usuario=user, conteudo=conteudo, tipo=Feedback.Tipo.NEGATIVO)

        item = client.get("/feedback/historico/").json()["results"][0]

        assert item["conteudo_titulo"] == conteudo.titulo
        assert item["conteudo_resumo"]
        assert "conteudo_url" in item
        assert item["fonte"] == conteudo.fonte.nome
