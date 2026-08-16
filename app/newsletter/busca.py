"""Busca de conteúdos visíveis ao perfil (US-07.1, issue #28)."""
from __future__ import annotations

from django.db import models
from django.db.models import Case, IntegerField, Q, Value, When

from .feed import feed_queryset_for_perfil
from .models import Conteudo, Perfil


def buscar_conteudos(
    perfil: Perfil,
    *,
    q: str = "",
    categoria: str = "",
    curso: str = "",
    data_inicio: str = "",
    data_fim: str = "",
) -> models.QuerySet[Conteudo]:
    """Retorna conteúdos visíveis ao perfil que casam com os filtros.

    A base é o mesmo queryset do feed (`feed_queryset_for_perfil`): a busca só
    enxerga conteúdos que o estudante poderia ver no feed. Filtros:
    - `q`: palavra-chave em título/corpo (icontains), com relevância — título
      vale mais que corpo;
    - `categoria`: slug da categoria (ex.: `edital`);
    - `curso`: slug do curso (ex.: `ciencia_da_computacao`);
    - `data_inicio` / `data_fim`: recorte por data de publicação (ISO yyyy-mm-dd).

    Ordenação: relevância (título > corpo) e depois data de publicação.
    """
    queryset = feed_queryset_for_perfil(perfil)

    if q:
        q_clean = q.strip()
        if q_clean:
            queryset = queryset.filter(
                Q(titulo__icontains=q_clean) | Q(corpo__icontains=q_clean)
            ).annotate(
                _peso_busca=Case(
                    When(titulo__icontains=q_clean, then=Value(2)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            )
        else:
            queryset = queryset.annotate(_peso_busca=Value(1, output_field=IntegerField()))
    else:
        queryset = queryset.annotate(_peso_busca=Value(1, output_field=IntegerField()))

    if categoria:
        queryset = queryset.filter(categoria__nome=categoria)

    if curso:
        queryset = queryset.filter(cursos__contains=[curso])

    if data_inicio:
        queryset = queryset.filter(data_publicacao__date__gte=data_inicio)

    if data_fim:
        queryset = queryset.filter(data_publicacao__date__lte=data_fim)

    return queryset.order_by("-_peso_busca", "-data_publicacao")
