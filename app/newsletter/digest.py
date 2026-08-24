"""Digest periódico por e-mail (issue #24, US-04.1).

Monta, para cada ``Perfil`` ativo (frequência != desativado), a lista de
conteúdos aprovados e relevantes ainda não entregues por e-mail, envia via
``django.core.mail`` (backend configurável; default locável sem SMTP) e
registra cada item em ``Entrega`` — que serve de cursor: "desde o último
envio" é derivado das entregas anteriores.

Estudante sem conteúdo novo não recebe e-mail vazio.
"""
from __future__ import annotations

from collections.abc import Iterable

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .feed import feed_queryset_for_perfil
from .models import Conteudo, Entrega, Perfil
from .resumidor import resumo_para_exibicao

ASSUNTO = "UFCA Newsletter — novidades para você"
LINK_PREFERENCIAS = "/preferencias/"


def _intervalo_dias(frequencia: str) -> int:
    if frequencia == Perfil.FrequenciaEmail.SEMANAL:
        return 7
    return 1


def ultimo_envio(perfil: Perfil):
    """Data do último e-mail enviado ao perfil; None se nunca enviou."""
    ultima = (
        Entrega.objects.filter(
            usuario=perfil.user, canal=Entrega.Canal.EMAIL
        )
        .order_by("-data_envio")
        .values_list("data_envio", flat=True)
        .first()
    )
    return ultima


def _deve_enviar(perfil: Perfil) -> bool:
    """Respeita a frequência configurada pelo estudante."""
    if perfil.frequencia_email == Perfil.FrequenciaEmail.DESATIVADO:
        return False
    ultima = ultimo_envio(perfil)
    if ultima is None:
        return True
    return timezone.now() - ultima >= timedelta_dias(_intervalo_dias(perfil.frequencia_email))


def timedelta_dias(n: int):
    from datetime import timedelta

    return timedelta(days=n)


def montar_digest_perfil(perfil: Perfil) -> list[Conteudo]:
    """Conteúdos aprovados/relevantes do período ainda não entregues por e-mail."""
    base = feed_queryset_for_perfil(perfil).filter(
        status=Conteudo.Status.APROVADO
    )

    entregues = Entrega.objects.filter(
        usuario=perfil.user, canal=Entrega.Canal.EMAIL
    ).values_list("conteudo_id", flat=True)

    ultima = ultimo_envio(perfil)
    if ultima is not None:
        base = base.filter(data_publicacao__gte=ultima)

    return list(base.exclude(id__in=entregues).order_by("-data_publicacao"))


def _montar_email(perfil: Perfil, conteudos: list[Conteudo]) -> tuple[str, str]:
    """Retorna ``(assunto, corpo_texto)`` do digest."""
    linhas = []
    for c in conteudos:
        resumo = resumo_para_exibicao(c)
        link = c.url or "sem link"
        linhas.append(f"- {c.titulo}\n  {resumo}\n  {link}")

    corpo = (
        "Novidades da UFCA para o seu perfil:\n\n"
        + "\n\n".join(linhas)
        + f"\n\nGerencie suas preferências: {LINK_PREFERENCIAS}"
    )
    return ASSUNTO, corpo


def enviar_digest_perfil(perfil: Perfil) -> int:
    """Envia o digest de um perfil; retorna nº de conteúdos enviados."""
    if not _deve_enviar(perfil):
        return 0

    conteudos = montar_digest_perfil(perfil)
    if not conteudos:
        return 0

    assunto, corpo = _montar_email(perfil, conteudos)
    destinatario = perfil.user.email
    if not destinatario:
        return 0

    send_mail(
        subject=assunto,
        message=corpo,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@ufca.edu.br"),
        recipient_list=[destinatario],
        fail_silently=False,
    )

    Entrega.objects.bulk_create(
        [
            Entrega(conteudo=c, usuario=perfil.user, canal=Entrega.Canal.EMAIL)
            for c in conteudos
        ],
        ignore_conflicts=True,
    )
    return len(conteudos)


def enviar_digests(perfis: Iterable[Perfil] | None = None) -> int:
    """Envia digests de todos os perfis elegíveis; retorna nº de e-mails."""
    if perfis is None:
        perfis = Perfil.objects.select_related("user").all()

    emails = 0
    for perfil in perfis:
        if enviar_digest_perfil(perfil) > 0:
            emails += 1
    return emails
