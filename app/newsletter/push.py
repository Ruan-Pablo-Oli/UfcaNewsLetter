"""Notificações push (issue #22, US-04.3).

Para cada `Perfil` com `push_ativo`, monta a lista de conteúdos aprovados e
relevantes ainda não entregues por push, envia via Web Push padrão
(`pywebpush`, chaves VAPID) a cada `PushSubscription` do usuário e registra
cada conteúdo entregue em `Entrega` — mesmo cursor usado por `digest.py`, que
garante (via `unique_together`) que ninguém recebe o mesmo conteúdo duas vezes.

Diferente do digest por e-mail, aqui não há "período" — mas há um corte: só
entra conteúdo publicado a partir da assinatura mais antiga do usuário. Sem
isso, ativar o push faria o estudante receber uma notificação para cada
conteúdo relevante já aprovado no banco, dezenas de uma vez; e conteúdo
anterior ao opt-in não é "novo" para quem acabou de assinar.

Web Push só confirma que o serviço do navegador aceitou a mensagem (HTTP
201) — não que ela foi exibida. `Entrega` registra esse aceite. Um HTTP
404/410 indica subscription expirada; nesse caso ela é removida para o banco
não acumular lixo que falharia para sempre.
"""
from __future__ import annotations

import json
from collections.abc import Iterable

from django.conf import settings
from pywebpush import WebPushException, webpush

from .feed import feed_queryset_for_perfil
from .models import Conteudo, Entrega, Perfil, PushSubscription

SUBSCRIPTION_EXPIRADA_STATUS = (404, 410)


def inicio_da_assinatura(perfil: Perfil):
    """Momento a partir do qual o usuário pode ser notificado; None se não assinou.

    É a `PushSubscription` mais antiga do usuário — o corte que impede notificar
    em massa o histórico anterior ao opt-in.
    """
    return (
        PushSubscription.objects.filter(usuario=perfil.user)
        .order_by("criado_em")
        .values_list("criado_em", flat=True)
        .first()
    )


def montar_notificacoes_perfil(perfil: Perfil) -> list[Conteudo]:
    """Conteúdos aprovados/relevantes publicados desde o opt-in e não entregues."""
    if not perfil.push_ativo:
        return []

    inicio = inicio_da_assinatura(perfil)
    if inicio is None:
        return []

    entregues = Entrega.objects.filter(
        usuario=perfil.user, canal=Entrega.Canal.PUSH
    ).values_list("conteudo_id", flat=True)

    return list(
        feed_queryset_for_perfil(perfil)
        .filter(data_publicacao__gte=inicio)
        .exclude(id__in=entregues)
        .order_by("-data_publicacao")
    )


def _payload_conteudo(conteudo: Conteudo) -> str:
    return json.dumps(
        {
            "title": conteudo.titulo,
            "categoria": conteudo.categoria.get_nome_display() if conteudo.categoria else "",
            "url": conteudo.url,
        }
    )


def _enviar_para_subscription(subscription: PushSubscription, payload: str) -> bool:
    """Envia `payload` a uma subscription; retorna True se o navegador aceitou.

    Remove a subscription se o serviço de push responder 404/410 (expirada).
    """
    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=payload,
            vapid_private_key=settings.WEBPUSH_VAPID_PRIVATE_KEY,
            vapid_claims={"sub": settings.WEBPUSH_VAPID_SUBJECT},
        )
        return True
    except WebPushException as exc:
        status_code = getattr(exc.response, "status_code", None)
        if status_code in SUBSCRIPTION_EXPIRADA_STATUS:
            subscription.delete()
        return False


def enviar_push_perfil(perfil: Perfil) -> int:
    """Envia as notificações pendentes do perfil; retorna nº de conteúdos entregues."""
    if not perfil.push_ativo:
        return 0

    subscriptions = list(PushSubscription.objects.filter(usuario=perfil.user))
    if not subscriptions:
        return 0

    conteudos = montar_notificacoes_perfil(perfil)
    enviados = 0
    for conteudo in conteudos:
        payload = _payload_conteudo(conteudo)
        resultados = [
            _enviar_para_subscription(subscription, payload)
            for subscription in subscriptions
            if subscription.pk is not None
        ]
        if any(resultados):
            Entrega.objects.get_or_create(
                conteudo=conteudo, usuario=perfil.user, canal=Entrega.Canal.PUSH
            )
            enviados += 1
    return enviados


def enviar_notificacoes_push(perfis: Iterable[Perfil] | None = None) -> int:
    """Envia notificações push de todos os perfis elegíveis; retorna nº de envios."""
    if perfis is None:
        perfis = Perfil.objects.filter(push_ativo=True).select_related("user")

    total = 0
    for perfil in perfis:
        total += enviar_push_perfil(perfil)
    return total
