"""Digest por e-mail (issue #24, US-04.1)."""
from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone

from newsletter.digest import (
    enviar_digests,
    montar_digest_perfil,
)
from newsletter.models import Conteudo, Entrega, Fonte, Perfil


@pytest.fixture
def fonte(db):
    return Fonte.objects.create(
        nome="Portal", tipo=Fonte.Tipo.HTML, url="https://x/", intervalo_coleta=60
    )


def _criar_conteudo(fonte, titulo, hash_dedup, dias_atras=0):
    return Conteudo.objects.create(
        titulo=titulo,
        corpo=f"Corpo de {titulo}.",
        resumo=f"Resumo de {titulo}.",
        url=f"https://origem.ufca.edu.br/{hash_dedup}",
        data_publicacao=timezone.now() - timedelta(days=dias_atras),
        fonte=fonte,
        status=Conteudo.Status.APROVADO,
        universal=True,
        hash_dedup=hash_dedup,
    )


@pytest.fixture
def perfil(db):
    user = __import__("django.contrib.auth.models", fromlist=["User"]).User.objects.create_user(
        "estudante", email="estudante@ufca.edu.br"
    )
    return Perfil.objects.create(user=user, curso="", periodo=1)


# --- campo frequencia ---


def test_perfil_tem_frequencia_padrao_diaria(perfil):
    assert perfil.frequencia_email == Perfil.FrequenciaEmail.DIARIA


def test_frequencia_desativada_e_opcao_valida(perfil):
    perfil.frequencia_email = Perfil.FrequenciaEmail.DESATIVADO
    perfil.save()
    perfil.refresh_from_db()
    assert perfil.frequencia_email == Perfil.FrequenciaEmail.DESATIVADO


# --- montagem do digest ---


@pytest.mark.django_db
def test_monta_com_aprovados_do_periodo(fonte, perfil):
    _criar_conteudo(fonte, "Edital A", "h-a")
    itens = montar_digest_perfil(perfil)
    assert [i.titulo for i in itens] == ["Edital A"]


@pytest.mark.django_db
def test_nao_inclui_ja_entregues(fonte, perfil):
    c = _criar_conteudo(fonte, "Edital A", "h-a")
    Entrega.objects.create(
        conteudo=c, usuario=perfil.user, canal=Entrega.Canal.EMAIL
    )
    assert montar_digest_perfil(perfil) == []


@pytest.mark.django_db
def test_nao_inclui_pendentes_ou_descartados(fonte, perfil):
    Conteudo.objects.create(
        titulo="Pendente",
        corpo="c",
        data_publicacao=timezone.now(),
        fonte=fonte,
        hash_dedup="h-p",
    )
    assert montar_digest_perfil(perfil) == []


# --- envio ---


@pytest.mark.django_db
def test_envia_email_com_assunto_resumo_e_links(fonte, perfil):
    _criar_conteudo(fonte, "Edital A", "h-a")
    enviados = enviar_digests()

    assert enviados == 1
    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.to == ["estudante@ufca.edu.br"]
    assert "UFCA" in msg.subject
    corpo = msg.body
    assert "Edital A" in corpo
    assert "Resumo de Edital A" in corpo
    assert "https://origem.ufca.edu.br/h-a" in corpo
    assert "/preferencias/" in corpo  # link de gerenciamento


@pytest.mark.django_db
def test_sem_conteudo_novo_nao_envia(fonte, perfil):
    assert enviar_digests() == 0
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_desativado_nao_recebe(fonte, perfil):
    _criar_conteudo(fonte, "Edital A", "h-a")
    perfil.frequencia_email = Perfil.FrequenciaEmail.DESATIVADO
    perfil.save()

    assert enviar_digests() == 0
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_envio_registra_entrega(fonte, perfil):
    _criar_conteudo(fonte, "Edital A", "h-a")
    enviar_digests()

    assert Entrega.objects.filter(
        usuario=perfil.user, canal=Entrega.Canal.EMAIL
    ).count() == 1


@pytest.mark.django_db
def test_segundo_envio_vazio_idempotente(fonte, perfil):
    _criar_conteudo(fonte, "Edital A", "h-a")
    enviar_digests()
    # Tudo já entregue; rodar de novo não envia nada.
    assert enviar_digests() == 0
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_semanal_so_recebe_apos_sete_dias(fonte, perfil):
    _criar_conteudo(fonte, "Edital A", "h-a")
    perfil.frequencia_email = Perfil.FrequenciaEmail.SEMANAL
    perfil.save()

    # Nunca recebeu: recebe agora.
    assert enviar_digests() == 1

    # Novo conteúdo logo depois: semanal não deve receber antes de 7 dias.
    _criar_conteudo(fonte, "Edital B", "h-b")
    assert enviar_digests() == 0
