"""Painel administrativo de fontes (issue #26, US-05.1).

CRUD de ``Fonte`` via API JSON restrita a staff, complementando o Django
Admin. Alterações valem no próximo ciclo: o orquestrador (``coleta.py``)
consulta ``Fonte.objects.filter(ativo=True)`` a cada execução, então
ativar/desativar/editar aqui surte efeito sem reinício.
"""
from __future__ import annotations

import json

from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .models import Fonte


def _staff(user) -> bool:
    return user.is_authenticated and user.is_staff


def _fonte_dict(fonte: Fonte) -> dict:
    return {
        "id": fonte.id,
        "nome": fonte.nome,
        "tipo": fonte.tipo,
        "url": fonte.url,
        "intervalo_coleta": fonte.intervalo_coleta,
        "ativo": fonte.ativo,
        "ultima_coleta": (
            fonte.ultima_coleta.isoformat() if fonte.ultima_coleta else None
        ),
    }


@user_passes_test(_staff)
@require_http_methods(["GET"])
def listar_fontes(request):
    dados = [_fonte_dict(f) for f in Fonte.objects.all()]
    return JsonResponse({"fontes": dados})


@user_passes_test(_staff)
@require_http_methods(["POST"])
def criar_fonte(request):
    try:
        corpo = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON inválido."}, status=400)

    nome = (corpo.get("nome") or "").strip()
    tipo = (corpo.get("tipo") or "").strip()
    url = (corpo.get("url") or "").strip()
    intervalo = corpo.get("intervalo_coleta", 60)

    erros = {}
    if not nome:
        erros["nome"] = "obrigatório"
    if tipo not in Fonte.Tipo.values:
        erros["tipo"] = f"deve ser um de {list(Fonte.Tipo.values)}"
    if not url.startswith(("http://", "https://")):
        erros["url"] = "deve ser uma URL http(s)"
    if not isinstance(intervalo, int) or intervalo <= 0:
        erros["intervalo_coleta"] = "inteiro positivo em minutos"
    if erros:
        return JsonResponse({"erros": erros}, status=400)

    fonte = Fonte.objects.create(
        nome=nome, tipo=tipo, url=url, intervalo_coleta=intervalo
    )
    return JsonResponse(_fonte_dict(fonte), status=201)


def _carregar_fonte(request, fonte_id: int):
    try:
        return Fonte.objects.get(pk=fonte_id)
    except Fonte.DoesNotExist:
        return None


@user_passes_test(_staff)
@require_http_methods(["PATCH", "PUT"])
def editar_fonte(request, fonte_id: int):
    fonte = _carregar_fonte(request, fonte_id)
    if fonte is None:
        return JsonResponse({"erro": "Fonte não encontrada."}, status=404)

    try:
        corpo = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON inválido."}, status=400)

    if "nome" in corpo:
        nome = (corpo["nome"] or "").strip()
        if not nome:
            return JsonResponse({"erros": {"nome": "obrigatório"}}, status=400)
        fonte.nome = nome

    if "tipo" in corpo:
        if corpo["tipo"] not in Fonte.Tipo.values:
            return JsonResponse(
                {"erros": {"tipo": "tipo inválido"}}, status=400
            )
        fonte.tipo = corpo["tipo"]

    if "url" in corpo:
        url = (corpo["url"] or "").strip()
        if not url.startswith(("http://", "https://")):
            return JsonResponse({"erros": {"url": "URL http(s) inválida"}}, status=400)
        fonte.url = url

    if "intervalo_coleta" in corpo:
        intervalo = corpo["intervalo_coleta"]
        if not isinstance(intervalo, int) or intervalo <= 0:
            return JsonResponse(
                {"erros": {"intervalo_coleta": "inteiro positivo em minutos"}},
                status=400,
            )
        fonte.intervalo_coleta = intervalo

    if "ativo" in corpo:
        fonte.ativo = bool(corpo["ativo"])

    fonte.save()
    return JsonResponse(_fonte_dict(fonte))


@user_passes_test(_staff)
@require_http_methods(["DELETE"])
def remover_fonte(request, fonte_id: int):
    fonte = _carregar_fonte(request, fonte_id)
    if fonte is None:
        return JsonResponse({"erro": "Fonte não encontrada."}, status=404)

    # PROTECT em Conteudo.fonte impede apagar fontes com conteúdo vinculado.
    try:
        fonte.delete()
    except Exception:
        return JsonResponse(
            {"erro": "Fonte possui conteúdos vinculados; desative em vez de remover."},
            status=409,
        )
    return JsonResponse({"removido": True})
