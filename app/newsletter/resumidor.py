"""Resumidor de conteúdo extenso (issue #18, US-03.3).

Estratégia híbrida (opção 3 acordada):

- **Extrativo determinístico** (default): seleção de sentenças por score
  (presença de prazo, público-alvo, posição) + extração regex de ``prazo``
  e ``publico_alvo``. Sem rede, sem custo, determinístico — e
  ``gerado_por_ia`` permanece ``False`` porque nenhum modelo gerou o texto.
- **LLM injetável**: qualquer chamável ``summarizer(titulo, corpo) -> str``
  pode ser passado; quando usado, ``gerado_por_ia=True`` (transparência).

Cache: um ``Conteudo`` com ``resumo`` preenchido nunca é reprocessado.
Conteúdos com menos de ``LIMITE_PALAVRAS`` não são resumidos.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone

LIMITE_PALAVRAS = 500
MAX_PALAVRAS_RESUMO = 120

_SENTENCAO_RE = re.compile(r"(?<=[.!?])\s+")
_DATA_LIMITE_RE = re.compile(
    r"(?:até|até o dia|prazo:|limite|até dia)\s*(\d{1,2}/\d{1,2}/\d{4})",
    re.IGNORECASE,
)
_PUBLICO_RE = re.compile(
    r"destinad[ao]s?\s+a\s+([^.,;]{4,120})",
    re.IGNORECASE,
)

# Palavras que aumentam o score de uma sentença para o resumo.
_KEYWORDS = (
    "inscriç", "prazo", "edital", "resultado", "vaga", "monitoria",
    "destinada", "matrícula", "candidato", "data", "evento", "abertura",
)


@dataclass(frozen=True, slots=True)
class Resumo:
    """Resultado do resumo extrativo."""

    texto: str


def _sentencas(texto: str) -> list[str]:
    partes = [s.strip() for s in _SENTENCAO_RE.split(texto) if s.strip()]
    return partes or ([texto.strip()] if texto.strip() else [])


def extrair_prazo(corpo: str) -> datetime | None:
    """Encontra data-limite explícita ("até 30/09/2026"). None se ausente."""
    m = _DATA_LIMITE_RE.search(corpo)
    if m is None:
        return None
    try:
        dia, mes, ano = (int(p) for p in m.group(1).split("/"))
        return datetime(ano, mes, dia)
    except ValueError:
        return None


def extrair_publico_alvo(corpo: str | None) -> str | None:
    """Encontra o público-alvo após "destinadas a ...". None se ausente."""
    if not corpo:
        return None
    m = _PUBLICO_RE.search(corpo)
    if m is None:
        return None
    alvo = m.group(1).strip()
    return alvo or None


def resumir_extrativo(titulo: str, corpo: str) -> Resumo | None:
    """Resumo extrativo: melhores sentenças até MAX_PALAVRAS_RESUMO.

    Retorna None quando o corpo não atinge LIMITE_PALAVRAS (não precisa).
    """
    if len(corpo.split()) < LIMITE_PALAVRAS:
        return None

    tem_prazo = bool(_DATA_LIMITE_RE.search(corpo))
    sentencas = _sentencas(corpo)

    def _score(i: int, s: str) -> tuple[int, int]:
        score = sum(2 for kw in _KEYWORDS if kw in s.lower())
        if tem_prazo and _DATA_LIMITE_RE.search(s):
            score += 10
        if _PUBLICO_RE.search(s):
            score += 5
        # Desempate estável: sentenças mais próximas do início vencem.
        return (-score, i)

    ordenadas = sorted(enumerate(sentencas), key=lambda p: _score(p[0], p[1]))

    escolhidas: list[str] = []
    palavras = 0
    for _, s in ordenadas:
        n = len(s.split())
        if palavras + n > MAX_PALAVRAS_RESUMO:
            continue
        escolhidas.append(s)
        palavras += n
        if palavras >= MAX_PALAVRAS_RESUMO // 2:
            break

    if not escolhidas:
        return None

    # Restaura ordem original das sentenças escolhidas.
    indices = {id(s): i for i, s in enumerate(sentencas)}
    escolhidas.sort(key=lambda s: indices[id(s)])
    return Resumo(texto=" ".join(escolhidas))


def resumir_conteudo(
    conteudo,
    *,
    summarizer: Callable[[str, str], str] | None = None,
) -> bool:
    """Resume um ``Conteudo`` longo sem resumo; retorna True se alterou.

    - Sem ``summarizer``, usa o extrativo e mantém ``gerado_por_ia=False``.
    - Com ``summarizer(titulo, corpo) -> str``, usa o texto gerado e marca
      ``gerado_por_ia=True`` (transparência exigida pelo critério da issue).
    - Cache: conteúdos que já têm ``resumo`` não são reprocessados.
    """
    if conteudo.resumo:
        return False

    if len(conteudo.corpo.split()) < LIMITE_PALAVRAS:
        return False

    prazo = extrair_prazo(f"{conteudo.titulo}\n{conteudo.corpo}")
    publico = extrair_publico_alvo(conteudo.corpo) or ""

    if summarizer is not None:
        texto_resumo = summarizer(conteudo.titulo, conteudo.corpo).strip()
        gerado_por_ia = True
    else:
        r = resumir_extrativo(conteudo.titulo, conteudo.corpo)
        texto_resumo = r.texto if r else ""
        gerado_por_ia = False

    if not texto_resumo:
        return False

    conteudo.resumo = texto_resumo
    conteudo.gerado_por_ia = gerado_por_ia
    alterado = True
    campos = ["resumo", "gerado_por_ia"]

    if prazo is not None and conteudo.prazo is None:
        tz_prazo = timezone.make_aware(prazo) if timezone.is_naive(prazo) else prazo
        conteudo.prazo = tz_prazo
        campos.append("prazo")

    if publico and not conteudo.publico_alvo:
        conteudo.publico_alvo = publico[:255]
        campos.append("publico_alvo")

    conteudo.save(update_fields=campos)
    return alterado


def resumir_pendentes(conteudos) -> dict[str, int]:
    """Resume conteúdos longos sem resumo. Retorna contagem para o comando."""
    resumidos = 0
    pulados = 0
    for c in conteudos:
        if resumir_conteudo(c):
            resumidos += 1
        else:
            pulados += 1
    return {"resumidos": resumidos, "pulados": pulados}
