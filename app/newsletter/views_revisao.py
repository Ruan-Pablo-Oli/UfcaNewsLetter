"""Fila de revisão manual (issue #27, US-05.2).

Conteúdos que o classificador não conseguiu categorizar ficam pendentes
(``status=pendente``, ``categoria=None``). Este módulo expõe a fila via API
JSON restrita a staff com ações de aprovar, descartar e reclassificar.
Aprovados entram no fluxo normal de distribuição (feed/digest já filtram
por ``status=aprovado``).
"""
from __future__ import annotations

import json

from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from .classificador import classificar_texto
from .models import Conteudo


def _staff(user) -> bool:
    return user.is_authenticated and user.is_staff


def _item(conteudo: Conteudo) -> dict:
    return {
        "id": conteudo.id,
        "titulo": conteudo.titulo,
        "categoria": conteudo.categoria_id,
        "cursos": conteudo.cursos,
        "fonte_id": conteudo.fonte_id,
        "fonte_nome": conteudo.fonte.nome,
        "url": conteudo.url,
        "data_publicacao": conteudo.data_publicacao.isoformat(),
        "criado_em": conteudo.criado_em.isoformat(),
    }


@user_passes_test(_staff)
@require_http_methods(["GET"])
def fila_revisao(request):
    """Lista conteúdos pendentes (sem categoria ou status=pendente)."""
    qs = (
        Conteudo.objects.filter(status=Conteudo.Status.PENDENTE)
        .select_related("fonte")
        .order_by("criado_em")
    )
    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get("page", 1))
    return JsonResponse(
        {"itens": [_item(c) for c in page.object_list], "total": paginator.count}
    )


def _carregar_pendente(request, conteudo_id: int):
    return get_object_or_404(Conteudo, pk=conteudo_id, status=Conteudo.Status.PENDENTE)


@user_passes_test(_staff)
@require_http_methods(["POST"])
def aprovar(request, conteudo_id: int):
    """Aprova o conteúdo; opcionalmente aplica categoria/cursos antes."""
    conteudo = _carregar_pendente(request, conteudo_id)

    try:
        corpo = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON inválido."}, status=400)

    from .models import Categoria

    if "categoria" in corpo:
        tipo = corpo["categoria"]
        if tipo not in Categoria.Tipo.values:
            return JsonResponse({"erro": "categoria inválida"}, status=400)
        categoria, _ = Categoria.objects.get_or_create(nome=tipo)
        conteudo.categoria = categoria

    if "cursos" in corpo:
        cursos = corpo["cursos"]
        if not isinstance(cursos, list) or not all(
            c in Perfil_Curso_values() for c in cursos
        ):
            return JsonResponse({"erro": "curso inválido"}, status=400)
        conteudo.cursos = cursos

    conteudo.status = Conteudo.Status.APROVADO
    conteudo.save()
    return JsonResponse({"id": conteudo.id, "status": conteudo.status})


def Perfil_Curso_values():
    from .models import Perfil

    return Perfil.Curso.values


@user_passes_test(_staff)
@require_http_methods(["POST"])
def descartar(request, conteudo_id: int):
    """Descarta o conteúdo (não entra no feed)."""
    conteudo = _carregar_pendente(request, conteudo_id)
    conteudo.status = Conteudo.Status.DESCARTADO
    conteudo.save(update_fields=["status"])
    return JsonResponse({"id": conteudo.id, "status": conteudo.status})


@user_passes_test(_staff)
@require_http_methods(["POST"])
def reclassificar(request, conteudo_id: int):
    """Reaplica o classificador automático sobre o conteúdo."""
    conteudo = _carregar_pendente(request, conteudo_id)
    from .models import Categoria

    tipo, cursos = classificar_texto(conteudo.titulo, conteudo.corpo)
    alterado = False
    if tipo is not None:
        categoria, _ = Categoria.objects.get_or_create(nome=tipo)
        conteudo.categoria = categoria
        alterado = True
    if cursos and not conteudo.cursos:
        conteudo.cursos = cursos
        alterado = True
    if alterado:
        conteudo.save()

    # Reclassificado com sucesso → segue para aprovação implícita? Não:
    # permanece na fila para o admin confirmar. Retorna estado atual.
    return JsonResponse({**_item(conteudo), "reclassificado": alterado})
