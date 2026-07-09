"""Views do app newsletter (feed de conteúdo personalizado)."""
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse

from .feed import feed_queryset_for_perfil, motivo_recomendacao
from .models import Perfil

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
            "resumo": conteudo.resumo,
            "categoria": conteudo.categoria.nome,
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
