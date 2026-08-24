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
_DATA = r"\d{1,2}/\d{1,2}/\d{4}"

# Padrões de data-limite, em ordem de prioridade. O segundo elemento é o grupo
# que contém o prazo — em intervalos ("de X a Y"), o prazo é o **fim**.
#
# Deliberadamente conservador: a expressão mais comum no corpus não é prazo
# nenhum, é "atualizado em DATA" (194 ocorrências em 224 conteúdos), a data de
# atualização da própria página. Casar isso encheria os cards de prazos falsos,
# o que é pior do que card sem prazo. Por isso toda regra exige uma palavra que
# indique limite ("até", "prazo", "encerram", "período de ... a").
_PADROES_PRAZO: list[tuple[re.Pattern[str], int]] = [
    (
        re.compile(
            rf"(?:no\s+per[íi]odo\s+de|do\s+dia|entre\s+os\s+dias|de)\s+({_DATA})"
            rf"\s*(?:at[ée]\s+(?:o\s+dia\s+)?|a\s+|[-–]\s*)({_DATA})",
            re.IGNORECASE,
        ),
        2,
    ),
    (
        re.compile(
            rf"(?:at[ée]\s+(?:o\s+dia\s+|[àa]s\s+\d{{1,2}}(?:h\d{{0,2}}|:\d{{2}})?\s+"
            rf"(?:do\s+dia\s+)?)?"
            rf"|prazo(?:\s+(?:final|limite))?\s*:?\s*"
            rf"|data(?:\s+e\s+hor[áa]rio)?\s+limite\s*:?\s*"
            rf"|encerram(?:-se)?\s+em\s+"
            rf"|submiss[ãa]o\s*:?\s*)({_DATA})",
            re.IGNORECASE,
        ),
        1,
    ),
]

# Mantido para o score das sentenças: "esta frase fala de prazo?".
_DATA_LIMITE_RE = re.compile(
    rf"(?:at[ée]|prazo|limite|encerram|per[íi]odo\s+de)\s*[^.]{{0,30}}?({_DATA})",
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
    # "DA MATRÍCULA", "3.1", "Art. 5º" não são frases: entram no resumo como
    # ruído, sem informar nada ao estudante.
    partes = [
        s for s in partes if not _RUIDO_DE_PDF_RE.match(s) and not _TIMBRE_RE.search(s)
    ]
    return partes or ([texto.strip()] if texto.strip() else [])


def extrair_prazo(corpo: str) -> datetime | None:
    """Encontra a data-limite do conteúdo. None quando não há uma explícita.

    Reconhece "até 30/09/2026", "até as 23h59 do dia 30/09/2026", "prazo final:
    30/09/2026" e intervalos como "no período de 01/09/2026 a 30/09/2026" — nos
    intervalos, o prazo é o fim. Datas sem palavra de limite por perto são
    ignoradas de propósito (ver `_PADROES_PRAZO`).
    """
    for padrao, grupo in _PADROES_PRAZO:
        m = padrao.search(corpo)
        if m is None:
            continue
        try:
            dia, mes, ano = (int(p) for p in m.group(grupo).split("/"))
            return datetime(ano, mes, dia)
        except ValueError:
            continue
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


_ESPACOS_RE = re.compile(r"\s+")
# Cabeçalho/numeração de seção de edital: "3.1", "DA MATRÍCULA", "Art. 5º".
_RUIDO_DE_PDF_RE = re.compile(
    r"^(?:\d+(?:\.\d+)*\s*[-–.)]?\s*$|[A-ZÁÉÍÓÚÂÊÔÃÕÇ\s]{4,}$|art\.?\s*\d+)",
    re.IGNORECASE,
)
# Timbre e rodapé de ofício: endereço, telefone, site e e-mail institucional.
# Aparecem em toda página do PDF e não informam nada sobre o edital.
_TIMBRE_RE = re.compile(
    r"(?:@ufca\.edu\.br|www\.ufca\.edu\.br|\bfone\b|\bcep\b|cidade\s+universit[áa]ria"
    r"|minist[ée]rio\s+da\s+educa[çc][ãa]o|universidade\s+federal\s+do\s+cariri)",
    re.IGNORECASE,
)


def _limpar_texto_de_pdf(texto: str) -> str:
    """Junta as quebras de linha que a extração de PDF deixa no meio das frases.

    O texto vindo do PyMuPDF quebra linha a cada linha do documento, então uma
    sentença chega picada. Sem isso, o recorte por sentença e as regex de prazo
    e público-alvo caem no meio de uma frase — foi o que produziu um
    público-alvo com quebra de linha no meio.
    """
    return _ESPACOS_RE.sub(" ", texto).strip()


def texto_completo(conteudo) -> str:
    """Corpo do conteúdo somado ao texto dos anexos PDF já processados.

    Os informes da UFCA são curtos (mediana de ~177 palavras) e costumam
    apontar para um PDF onde está o documento de verdade — um edital de 8 mil
    palavras contra 465 no corpo. Resumir só o corpo deixaria de fora
    justamente o conteúdo extenso que a US-03.3 existe para tratar.
    """
    partes = [conteudo.corpo]
    for anexo in conteudo.anexos or []:
        texto = (anexo or {}).get("text") or ""
        if texto:
            partes.append(_limpar_texto_de_pdf(texto))
    return "\n".join(partes)


def resumo_para_exibicao(conteudo, limite: int = 200) -> str:
    """Resumo do conteúdo para as telas; cai no início do corpo se não houver.

    A maior parte do conteúdo coletado é curta demais para ser resumida, e um
    card sem texto nenhum é pior do que um trecho do começo. Era o que o digest
    já fazia por conta própria; agora é uma regra só, usada por feed, busca,
    histórico e digest.
    """
    if conteudo.resumo:
        return conteudo.resumo
    corpo = (conteudo.corpo or "").strip()
    if len(corpo) <= limite:
        return corpo
    return corpo[:limite].rstrip() + "…"


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

    texto = texto_completo(conteudo)
    if len(texto.split()) < LIMITE_PALAVRAS:
        return False

    prazo = extrair_prazo(f"{conteudo.titulo}\n{texto}")
    publico = extrair_publico_alvo(texto) or ""

    if summarizer is not None:
        texto_resumo = summarizer(conteudo.titulo, texto).strip()
        gerado_por_ia = True
    else:
        r = resumir_extrativo(conteudo.titulo, texto)
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
