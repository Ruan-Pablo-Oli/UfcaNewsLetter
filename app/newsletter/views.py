"""Views do app newsletter (feed de conteúdo personalizado e feedback de relevância)."""
import json

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from .busca import buscar_conteudos
from .feed import feed_queryset_for_perfil, motivo_recomendacao
from .models import Conteudo, Entrega, Feedback, Perfil
from .resumidor import resumo_para_exibicao

FEED_PAGE_SIZE_PADRAO = 20
FEED_PAGE_SIZE_MAXIMO = 50


def _parse_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@login_required
def feed(request):
    """`GET /feed/` — lista paginada de conteúdos personalizados para o perfil do usuário."""
    perfil, _ = Perfil.objects.get_or_create(
        user=request.user, defaults={"curso": "", "periodo": 1}
    )

    page_number = _parse_int(request.GET.get("page"), 1)
    page_size = _parse_int(request.GET.get("page_size"), FEED_PAGE_SIZE_PADRAO)
    page_size = max(1, min(page_size, FEED_PAGE_SIZE_MAXIMO))

    conteudos = feed_queryset_for_perfil(perfil)
    pagina = Paginator(conteudos, page_size).get_page(page_number)
    interesse_ids = set(perfil.interesses.values_list("id", flat=True))

    resultados = [
        {
            "id": conteudo.id,
            "titulo": conteudo.titulo,
            "resumo": resumo_para_exibicao(conteudo),
            "categoria": conteudo.categoria.nome if conteudo.categoria else None,
            "fonte": conteudo.fonte.nome,
            "data_publicacao": conteudo.data_publicacao.isoformat(),
            "universal": conteudo.universal,
            "motivo": motivo_recomendacao(conteudo, perfil, interesse_ids=interesse_ids),
        }
        for conteudo in pagina.object_list
    ]

    return JsonResponse(
        {
            "count": pagina.paginator.count,
            "page": pagina.number,
            "page_size": page_size,
            "total_pages": pagina.paginator.num_pages,
            "results": resultados,
        }
    )


@login_required
@require_http_methods(["POST"])
def feedback(request):
    """`POST /feedback/` — marca um conteúdo como útil (positivo) ou irrelevante (negativo).

    Corpo esperado (JSON): `{"conteudo_id": <int>, "tipo": "positivo"|"negativo"}`.
    Um novo envio para o mesmo conteúdo substitui a marcação anterior do usuário.
    """
    try:
        dados = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON inválido."}, status=400)

    conteudo_id = _parse_int(dados.get("conteudo_id"), None)
    tipo = dados.get("tipo")

    if conteudo_id is None or tipo not in Feedback.Tipo.values:
        return JsonResponse(
            {"erro": "Informe 'conteudo_id' e 'tipo' ('positivo' ou 'negativo')."},
            status=400,
        )

    conteudo = get_object_or_404(Conteudo, id=conteudo_id)

    registro, criado = Feedback.objects.update_or_create(
        usuario=request.user,
        conteudo=conteudo,
        defaults={"tipo": tipo},
    )

    return JsonResponse(
        {
            "id": registro.id,
            "conteudo_id": conteudo.id,
            "tipo": registro.tipo,
            "criado_em": registro.criado_em.isoformat(),
        },
        status=201 if criado else 200,
    )


@login_required
def feedback_historico(request):
    """`GET /feedback/historico/` — histórico paginado das marcações de relevância do estudante."""
    page_number = _parse_int(request.GET.get("page"), 1)
    page_size = _parse_int(request.GET.get("page_size"), FEED_PAGE_SIZE_PADRAO)
    page_size = max(1, min(page_size, FEED_PAGE_SIZE_MAXIMO))

    registros = (
        Feedback.objects.filter(usuario=request.user)
        .select_related("conteudo")
        .order_by("-criado_em")
    )
    pagina = Paginator(registros, page_size).get_page(page_number)

    resultados = [
        {
            "id": registro.id,
            "conteudo_id": registro.conteudo_id,
            "conteudo_titulo": registro.conteudo.titulo,
            "tipo": registro.tipo,
            "criado_em": registro.criado_em.isoformat(),
        }
        for registro in pagina.object_list
    ]

    return JsonResponse(
        {
            "count": pagina.paginator.count,
            "page": pagina.number,
            "page_size": page_size,
            "total_pages": pagina.paginator.num_pages,
            "results": resultados,
        }
    )


@login_required
def busca(request):
    """`GET /busca/?q=...&categoria=...&curso=...&data_inicio=...&data_fim=...`

    Busca conteúdos visíveis ao perfil do estudante (mesmo queryset do feed),
    ordenados por relevância (título > corpo) e depois data. Apenas conteúdos
    aprovados e direcionados ao perfil aparecem (US-07.1, issue #28).
    """
    perfil, _ = Perfil.objects.get_or_create(
        user=request.user, defaults={"curso": "", "periodo": 1}
    )

    page_number = _parse_int(request.GET.get("page"), 1)
    page_size = _parse_int(request.GET.get("page_size"), FEED_PAGE_SIZE_PADRAO)
    page_size = max(1, min(page_size, FEED_PAGE_SIZE_MAXIMO))

    conteudos = buscar_conteudos(
        perfil,
        q=request.GET.get("q", ""),
        categoria=request.GET.get("categoria", ""),
        curso=request.GET.get("curso", ""),
        data_inicio=request.GET.get("data_inicio", ""),
        data_fim=request.GET.get("data_fim", ""),
    )
    pagina = Paginator(conteudos, page_size).get_page(page_number)

    resultados = [
        {
            "id": conteudo.id,
            "titulo": conteudo.titulo,
            "resumo": resumo_para_exibicao(conteudo),
            "categoria": conteudo.categoria.nome if conteudo.categoria else None,
            "fonte": conteudo.fonte.nome,
            "data_publicacao": conteudo.data_publicacao.isoformat(),
            "url": conteudo.url,
        }
        for conteudo in pagina.object_list
    ]

    return JsonResponse(
        {
            "count": pagina.paginator.count,
            "page": pagina.number,
            "page_size": page_size,
            "total_pages": pagina.paginator.num_pages,
            "results": resultados,
        }
    )


@login_required
def historico(request):
    """`GET /historico/?data_inicio=...&data_fim=...&categoria=...`

    Histórico de conteúdos já entregues ao estudante, em ordem cronológica
    decrescente, paginado. Filtros opcionais por período (data de envio) e
    categoria (US-07.2, issue #29).
    """
    entregas = Entrega.objects.filter(usuario=request.user).select_related(
        "conteudo", "conteudo__categoria", "conteudo__fonte"
    )

    data_inicio = request.GET.get("data_inicio")
    data_fim = request.GET.get("data_fim")
    if data_inicio:
        entregas = entregas.filter(data_envio__date__gte=data_inicio)
    if data_fim:
        entregas = entregas.filter(data_envio__date__lte=data_fim)

    categoria = request.GET.get("categoria")
    if categoria:
        entregas = entregas.filter(conteudo__categoria__nome=categoria)

    page_number = _parse_int(request.GET.get("page"), 1)
    page_size = _parse_int(request.GET.get("page_size"), FEED_PAGE_SIZE_PADRAO)
    page_size = max(1, min(page_size, FEED_PAGE_SIZE_MAXIMO))

    pagina = Paginator(entregas, page_size).get_page(page_number)

    resultados = [
        {
            "id": entrega.id,
            "conteudo_id": entrega.conteudo_id,
            "titulo": entrega.conteudo.titulo,
            "resumo": resumo_para_exibicao(entrega.conteudo),
            "categoria": (
                entrega.conteudo.categoria.nome if entrega.conteudo.categoria else None
            ),
            "fonte": entrega.conteudo.fonte.nome,
            "canal": entrega.canal,
            "data_envio": entrega.data_envio.isoformat(),
            "url": entrega.conteudo.url,
        }
        for entrega in pagina.object_list
    ]

    return JsonResponse(
        {
            "count": pagina.paginator.count,
            "page": pagina.number,
            "page_size": page_size,
            "total_pages": pagina.paginator.num_pages,
            "results": resultados,
        }
    )
