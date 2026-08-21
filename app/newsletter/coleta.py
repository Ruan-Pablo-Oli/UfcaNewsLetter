"""Orquestra a coleta periódica das Fontes ativas e a persistência em ``Conteudo``.

A extração em si fica nos adaptadores em ``newsletter/collectors/`` (que não
tocam no banco, por decisão da US-03.1.1 / issue #53). Este módulo é a "cola"
entre os adaptadores e o modelo ``Conteudo`` (issue #16): decide quais ``Fonte``
estão na hora de ser varridas, despacha para o adaptador correto conforme
``Fonte.tipo``, grava os registros (com deduplicação por ``hash_dedup``) e
atualiza ``Fonte.ultima_coleta``.

O agendamento ("rodar a cada N minutos") fica fora do código, num scheduler
simples (cron / management command), conforme ADR-008.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.timezone import is_naive, make_aware

from .collectors import (
    CollectionError,
    ConcursosSelecoesCollector,
    NewsInformeCollector,
)
from .models import Conteudo, Fonte

# Mapeia ``Fonte.tipo`` para a classe de adaptador responsável por extrair
# registros desse tipo de origem. Tipos sem coletor implementado (ainda: PDF e
# Calendário, issues #54 e #55) são pulados na varredura, sem quebrar as demais.
REGISTRO_COLETORES = {
    Fonte.Tipo.HTML: NewsInformeCollector,
    Fonte.Tipo.CONCURSO: ConcursosSelecoesCollector,
}


@dataclass(frozen=True, slots=True)
class ResultadoColeta:
    """Resultado da coleta de uma única ``Fonte``."""

    fonte: Fonte
    criados: int = 0
    pulado: bool = False
    motivo: str = ""
    erros: tuple[CollectionError, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.pulado


def _data_publicacao(record) -> object:
    """``Conteudo.data_publicacao`` é obrigatório; cai num fallback estável.

    Usa a data de publicação extraída; se ausente, a de atualização; se também
    ausente, o instante da coleta. Datas ingênuas (sem tz) são localizadas para
    o fuso padrão do Django, evitando o warning de datetime naive.
    """
    valor = record.published_at or record.updated_at or timezone.now()
    if is_naive(valor):
        return make_aware(valor)
    return valor


@transaction.atomic
def _persistir(record, fonte: Fonte) -> bool:
    """Grava um registro extraído como ``Conteudo``; retorna True se foi criado.

    A deduplicação usa ``Conteudo.hash_dedup`` (único): se já existe um conteúdo
    com o mesmo hash, ``get_or_create`` não duplica e retorna ``criado=False``.
    """
    _, criado = Conteudo.objects.get_or_create(
        hash_dedup=record.content_hash,
        defaults={
            "titulo": record.title,
            "corpo": record.body,
            "url": record.canonical_url,
            "data_publicacao": _data_publicacao(record),
            "fonte": fonte,
            "status": Conteudo.Status.PENDENTE,
        },
    )
    return criado


def coletar_fonte(fonte: Fonte, *, fetch_html=None, max_pages: int = 100) -> ResultadoColeta:
    """Coleta uma ``Fonte`` específica e persiste os registros extraídos.

    ``fetch_html`` permite injetar a busca de HTML (usado nos testes); quando
    ``None``, o adaptador faz a requisição HTTP de verdade.
    """
    coletor_cls = REGISTRO_COLETORES.get(fonte.tipo)
    if coletor_cls is None:
        return ResultadoColeta(
            fonte=fonte,
            pulado=True,
            motivo=f"sem coletor implementado para o tipo '{fonte.tipo}'",
        )

    coletor = coletor_cls()
    registros = coletor.collect(
        fonte.url, fetch_html=fetch_html, max_pages=max_pages
    )

    criados = 0
    for registro in registros:
        if _persistir(registro, fonte):
            criados += 1

    return ResultadoColeta(
        fonte=fonte,
        criados=criados,
        erros=tuple(coletor.errors),
    )


def fontes_devidas(agora=None) -> list[Fonte]:
    """Retorna as ``Fonte`` ativas que já passaram do ``intervalo_coleta``.

    Uma fonte está "devida" se nunca foi coletada (``ultima_coleta=None``) ou se
    ``agora - ultima_coleta >= intervalo_coleta`` minutos.
    """
    agora = agora or timezone.now()
    devidas: list[Fonte] = []
    for fonte in Fonte.objects.filter(ativo=True):
        if fonte.ultima_coleta is None:
            devidas.append(fonte)
        elif agora - fonte.ultima_coleta >= timedelta(minutes=fonte.intervalo_coleta):
            devidas.append(fonte)
    return devidas


def coletar(
    *,
    forcar: bool = False,
    fetch_html=None,
    max_pages: int = 100,
    fontes: list[Fonte] | None = None,
) -> list[ResultadoColeta]:
    """Varre as fontes e persiste os conteúdos, atualizando ``ultima_coleta``.

    Sem argumentos, coleta só as fontes devidas (``fontes_devidas``). Com
    ``forcar=True``, varre todas as fontes ativas ignorando o agendamento. Com
    ``fontes`` explícitas (ex.: ``--fonte``), coleta só essas.
    """
    if fontes is None:
        fontes = Fonte.objects.filter(ativo=True) if forcar else fontes_devidas()

    resultados: list[ResultadoColeta] = []
    for fonte in fontes:
        resultado = coletar_fonte(fonte, fetch_html=fetch_html, max_pages=max_pages)
        resultados.append(resultado)
        if not resultado.pulado:
            fonte.ultima_coleta = timezone.now()
            fonte.save(update_fields=["ultima_coleta"])
    return resultados
