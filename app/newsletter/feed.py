"""Algoritmo de personalização do feed de conteúdos por perfil (US-01.2, US-01.3)."""
from collections import defaultdict

from django.db.models import Case, Count, IntegerField, Q, Value, When

from .models import Conteudo, Feedback


def _pesos_de_relevancia_por_categoria(usuario):
    """Calcula, por categoria, o saldo de feedback (positivos - negativos) do usuário.

    Usado para impulsionar conteúdos de categorias bem avaliadas e reduzir a
    posição de categorias mal avaliadas nas próximas recomendações do feed.
    """
    contagens = (
        Feedback.objects.filter(usuario=usuario)
        .values("conteudo__categoria_id", "tipo")
        .annotate(total=Count("id"))
    )

    pesos = defaultdict(int)
    for linha in contagens:
        sinal = 1 if linha["tipo"] == Feedback.Tipo.POSITIVO else -1
        pesos[linha["conteudo__categoria_id"]] += sinal * linha["total"]
    return pesos


def _ordenar_por_relevancia(queryset, usuario):
    pesos = _pesos_de_relevancia_por_categoria(usuario)
    if not pesos:
        return queryset.order_by("-data_publicacao")

    condicoes = [
        When(categoria_id=categoria_id, then=Value(peso)) for categoria_id, peso in pesos.items()
    ]
    return queryset.annotate(
        peso_relevancia=Case(*condicoes, default=Value(0), output_field=IntegerField())
    ).order_by("-peso_relevancia", "-data_publicacao")


def feed_queryset_for_perfil(perfil):
    """Retorna os `Conteudo` relevantes para `perfil`, ajustados pelo feedback do usuário.

    Um conteúdo aparece no feed se for `universal`, ou se tiver sido direcionado
    ao curso do perfil, ou a algum dos interesses seguidos pelo perfil — exceto
    se o próprio usuário já o marcou como irrelevante. A ordenação prioriza
    categorias que o usuário costuma avaliar como úteis, e rebaixa as que
    costuma marcar como irrelevantes.
    """
    interesse_ids = list(perfil.interesses.values_list("id", flat=True))

    filtro = Q(universal=True)
    if perfil.curso:
        filtro |= Q(cursos__contains=[perfil.curso])
    if interesse_ids:
        filtro |= Q(interesses__id__in=interesse_ids)

    conteudos_irrelevantes = Feedback.objects.filter(
        usuario=perfil.user, tipo=Feedback.Tipo.NEGATIVO
    ).values_list("conteudo_id", flat=True)

    queryset = (
        Conteudo.objects.filter(filtro)
        .exclude(id__in=conteudos_irrelevantes)
        .distinct()
        .select_related("categoria", "fonte")
        .prefetch_related("interesses")
    )
    return _ordenar_por_relevancia(queryset, perfil.user)


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
