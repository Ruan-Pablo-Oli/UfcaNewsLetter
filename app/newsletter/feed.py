"""Algoritmo de personalização do feed de conteúdos por perfil (US-01.2)."""
from django.db.models import Q

from .models import Conteudo


def feed_queryset_for_perfil(perfil):
    """Retorna os `Conteudo` relevantes para `perfil`, do mais recente ao mais antigo.

    Um conteúdo aparece no feed se for `universal`, ou se tiver sido direcionado
    ao curso do perfil, ou a algum dos interesses seguidos pelo perfil.
    """
    interesse_ids = list(perfil.interesses.values_list("id", flat=True))

    filtro = Q(universal=True)
    if perfil.curso:
        filtro |= Q(cursos__contains=[perfil.curso])
    if interesse_ids:
        filtro |= Q(interesses__id__in=interesse_ids)

    return (
        Conteudo.objects.filter(filtro)
        .distinct()
        .select_related("categoria", "fonte")
        .prefetch_related("interesses")
        .order_by("-data_publicacao")
    )


def motivo_recomendacao(conteudo, perfil, interesse_ids=None):
    """Explica por que `conteudo` foi recomendado a `perfil` (dado para a #47).

    `interesse_ids` pode ser fornecido (ids dos interesses do perfil, já
    carregados) para evitar uma consulta repetida a cada conteúdo do feed.
    """
    if interesse_ids is None:
        interesse_ids = set(perfil.interesses.values_list("id", flat=True))

    motivos = []

    if conteudo.universal:
        motivos.append("Aviso institucional, visível para todos os perfis")

    if perfil.curso and perfil.curso in conteudo.cursos:
        motivos.append(f"Direcionado ao seu curso ({perfil.get_curso_display()})")

    interesses_em_comum = sorted(
        interesse.nome for interesse in conteudo.interesses.all() if interesse.id in interesse_ids
    )
    for nome in interesses_em_comum:
        motivos.append(f"Relacionado ao seu interesse em '{nome}'")

    return " · ".join(motivos)
