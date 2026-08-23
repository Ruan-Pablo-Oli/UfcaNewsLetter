"""Coleta determinística de Calendários e Eventos da UFCA (US-03.1.3, issue #55).

Estratégia em duas etapas, conforme a issue:
1. **ICS/iCal primeiro**: o portal expõe exportação em
   ``https://www.ufca.edu.br/calendarios/?ical=1`` (plugin The Events Calendar).
   O parser lê os blocos ``VEVENT`` e extrai título, início/fim, local,
   descrição, link e URL de origem.
2. **Fallback HTML**: quando o ICS não estiver disponível, navega a listagem
   mensal e extrai somente eventos presentes no markup (título no ``h1``,
   meta de Data/Hora em ``.tribe-events-meta-group``, link de inscrição).

Datas incompletas ou ambíguas NÃO são convertidas silenciosamente: ficam como
pendência de parsing (``None`` + registro em ``errors``). Timezone normalizada
para ``America/Fortaleza`` quando a fonte não informar outra.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable, Iterable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

DEFAULT_TZ = "America/Fortaleza"

# Campos que podem aparecer quebrados em múltiplas linhas no ICS (folded lines).
_FOLDED_FIELDS = {"SUMMARY", "DESCRIPTION", "LOCATION", "URL"}


@dataclass(frozen=True, slots=True)
class CalendarioEventRecord:
    """Registro extraído de um evento do calendário (contrato US-03.1.1)."""

    source_url: str
    canonical_url: str
    title: str
    body: str
    published_at: datetime | None
    updated_at: datetime | None
    category: str | None
    attachment_urls: tuple[str, ...]
    content_hash: str
    # Campos específicos de calendário/evento.
    start: datetime | None
    end: datetime | None
    location: str | None
    inscription_url: str | None


@dataclass(frozen=True, slots=True)
class CollectionError:
    url: str
    reason: str


class CalendarioCollector:
    """Extrai eventos do calendário UFCA sem persistir no banco.

    Segue o mesmo princípio dos demais adaptadores (US-03.1.1): a persistência
    em ``Conteudo`` fica fora deste módulo (orquestrada em ``newsletter/coleta.py``).
    """

    def __init__(
        self,
        session: requests.Session | None = None,
        user_agent: str = "UfcaNewsletter/0.1",
    ):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.errors: list[CollectionError] = []

    def collect(
        self,
        listing_url: str,
        *,
        fetch_html: Callable[[str], str] | None = None,
        max_pages: int = 12,
        known_canonical_urls: set[str] | None = None,
    ) -> list[CalendarioEventRecord]:
        """Coleta eventos da listagem; tenta ICS e cai para HTML quando necessário.

        ``listing_url`` deve apontar para a listagem de calendário (ex.:
        ``https://www.ufca.edu.br/calendarios/``). O ICS é tentado em
        ``<listing_url>?ical=1``; se falhar ou não tiver eventos, usa o HTML.
        """
        fetch = fetch_html or self._fetch_html
        self.errors = []
        known = set(known_canonical_urls or set())

        # Etapa 1: ICS.
        ics_url = listing_url.rstrip("/") + "/?ical=1"
        try:
            ics_text = fetch(ics_url)
            if "BEGIN:VCALENDAR" in ics_text:
                records = self.parse_ics(ics_text, ics_url, known_canonical_urls=known)
                if records:
                    return records
                # ICS vazio (sem VEVENT): tenta HTML como fallback.
        except Exception as exc:
            self.errors.append(CollectionError(ics_url, f"falha no ICS: {exc}"))

        # Etapa 2: HTML (listagem mensal).
        records = self.collect_html(listing_url, fetch_html=fetch, known=known)
        return records

    def parse_ics(
        self,
        ics_text: str,
        source_url: str,
        *,
        known_canonical_urls: set[str] | None = None,
    ) -> list[CalendarioEventRecord]:
        """Parse de um texto iCalendar; retorna os VEVENTs com os campos mapeados."""
        known = known_canonical_urls or set()
        records: list[CalendarioEventRecord] = []
        seen: set[str] = set()

        for vevent in _iter_vevents(ics_text):
            fields = _parse_vevent_fields(vevent)
            uid = fields.get("UID", "")
            summary = _unfold(fields.get("SUMMARY", "")).strip()
            if not summary:
                self.errors.append(CollectionError(source_url, "VEVENT sem SUMMARY"))
                continue

            canonical = _canonicalize_url(
                urljoin(source_url, _unfold(fields.get("URL", "")).strip())
            )
            if not canonical or canonical in known or canonical in seen:
                continue
            seen.add(canonical)

            start = _parse_ics_datetime(fields.get("DTSTART", ""))
            end = _parse_ics_datetime(fields.get("DTEND", ""))
            if start is None:
                self.errors.append(
                    CollectionError(canonical or source_url, "DTSTART ausente ou inválido")
                )

            description = _unfold(fields.get("DESCRIPTION", "")).strip()
            location = _unfold(fields.get("LOCATION", "")).strip() or None
            inscription_url = _extract_inscription_url(description, canonical)

            body = description or ""
            record = CalendarioEventRecord(
                source_url=source_url,
                canonical_url=canonical or f"{source_url}#{uid}",
                title=summary,
                body=body,
                published_at=start,
                updated_at=None,
                category=_extract_category_from_ics(fields),
                attachment_urls=(),
                content_hash=_content_hash(canonical, summary, body),
                start=start,
                end=end,
                location=location,
                inscription_url=inscription_url,
            )
            records.append(record)

        return records

    def collect_html(
        self,
        listing_url: str,
        *,
        fetch_html: Callable[[str], str] | None = None,
        known: set[str] | None = None,
    ) -> list[CalendarioEventRecord]:
        """Navega a listagem HTML mensal e extrai os eventos presentes no markup."""
        fetch = fetch_html or self._fetch_html
        known = known or set()
        records: list[CalendarioEventRecord] = []
        visited: set[str] = set()
        pending = [listing_url]

        while pending:
            current = _canonicalize_url(pending.pop(0))
            if current in visited:
                continue
            visited.add(current)

            try:
                html = fetch(current)
            except Exception as exc:
                self.errors.append(CollectionError(current, str(exc)))
                continue

            event_urls, next_url = self.parse_listing(html, current)
            for event_url in event_urls:
                if event_url in known:
                    continue
                try:
                    record = self.parse_event(fetch(event_url), event_url)
                except Exception as exc:
                    self.errors.append(CollectionError(event_url, str(exc)))
                    continue
                records.append(record)
                known.add(record.canonical_url)

            if next_url:
                pending.append(next_url)

        return records

    def parse_listing(self, html: str, listing_url: str) -> tuple[list[str], str | None]:
        """Extrai URLs de eventos da listagem e o link de próxima página (se houver)."""
        soup = BeautifulSoup(html, "lxml")
        event_urls: list[str] = []
        seen: set[str] = set()

        for anchor in soup.find_all("a", href=True):
            href = urljoin(listing_url, anchor["href"])
            if "/evento/" not in href:
                continue
            canonical = _canonicalize_url(href)
            if canonical not in seen:
                seen.add(canonical)
                event_urls.append(canonical)

        next_url = None
        for anchor in soup.find_all("a", href=True):
            text = anchor.get_text(" ", strip=True)
            if re.search(r"pr[óo]ximo", text, re.I) or "next" in (anchor.get("rel") or []):
                next_url = _canonicalize_url(urljoin(listing_url, anchor["href"]))
                break

        return event_urls, next_url

    def parse_event(self, html: str, source_url: str) -> CalendarioEventRecord:
        """Extrai um evento da página HTML de detalhe (fallback sem ICS)."""
        soup = BeautifulSoup(html, "lxml")

        title_node = soup.find("h1")
        if title_node is None or not title_node.get_text(" ", strip=True):
            raise ValueError(f"titulo ausente em {source_url}")
        title = title_node.get_text(" ", strip=True)

        body_node = soup.select_one(
            ".tribe-events-single-event-description, .entry-content"
        ) or soup.find("main")
        body = ""
        if body_node is not None:
            for node in body_node.select("script, style, nav"):
                node.decompose()
            paragraphs = [p.get_text(" ", strip=True) for p in body_node.find_all("p")]
            body = "\n".join(part for part in paragraphs if part)
            if not body:
                body = body_node.get_text(" ", strip=True)

        meta = soup.select_one(".tribe-events-meta-group")
        meta_text = meta.get_text(" | ", strip=True) if meta else ""

        start, end = _parse_html_datetime(meta_text)
        location = _extract_location(soup, meta_text)
        inscription_url = _extract_inscription_url_from_soup(soup, meta_text)
        category = _extract_category_from_html(meta_text)

        record = CalendarioEventRecord(
            source_url=source_url,
            canonical_url=_canonicalize_url(source_url),
            title=title,
            body=body,
            published_at=start,
            updated_at=None,
            category=category,
            attachment_urls=(),
            content_hash=_content_hash(source_url, title, body),
            start=start,
            end=end,
            location=location,
            inscription_url=inscription_url,
        )
        return record

    def _fetch_html(self, url: str) -> str:
        response = self.session.get(url, timeout=20)
        response.raise_for_status()
        return response.text


# ---------------------------------------------------------------------------
# Helpers de parsing
# ---------------------------------------------------------------------------

def _iter_vevents(ics_text: str) -> Iterable[str]:
    """Divide o ICS em blocos VEVENT (preservando o texto cru de cada um)."""
    current: list[str] = []
    in_vevent = False
    for raw_line in ics_text.splitlines():
        line = raw_line.strip()
        if line.startswith("BEGIN:VEVENT"):
            in_vevent = True
            current = [line]
        elif line.startswith("END:VEVENT"):
            current.append(line)
            yield "\n".join(current)
            in_vevent = False
        elif in_vevent:
            current.append(line)


def _parse_vevent_fields(vevent: str) -> dict[str, str]:
    """Agrupa linhas do VEVENT; dobra linhas continuadas (começam com espaço/tab)."""
    fields: dict[str, str] = {}
    for raw_line in vevent.splitlines():
        if raw_line.startswith(("BEGIN:", "END:")):
            continue
        if raw_line[:1] in (" ", "\t") and fields:
            key = list(fields)[-1]
            fields[key] += raw_line[1:]
            continue
        if ":" not in raw_line:
            continue
        key, _, value = raw_line.partition(":")
        # remove parametros (ex.: DTSTART;TZID=...:valor)
        key = key.split(";")[0].strip().upper()
        if key in _FOLDED_FIELDS or key in {
            "DTSTART", "DTEND", "UID", "URL", "LOCATION", "SUMMARY",
            "DESCRIPTION", "CATEGORIES", "ATTACH",
        }:
            fields[key] = value
    return fields


def _unfold(value: str) -> str:
    return value.replace("\\n", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


def _parse_ics_datetime(value: str) -> datetime | None:
    """Parse de DTSTART/DTEND: com/sem TZID e com/sem hora.

    Retorna `None` para valores ausentes/inválidos (pendência de parsing), em vez
    de inferir uma data.
    """
    value = value.strip()
    if not value:
        return None

    # Remove parâmetros que podem preceder o valor (ex.: DTSTART;TZID="..." ou
    # DTSTART;VALUE=DATE): o valor ICS em si nunca contém ":" (horários são
    # 20260812T143000), então tudo após o último ":" é o valor limpo.
    value = value.rsplit(":", 1)[-1].strip()

    # Formato completo: 20260812T143000
    m = re.fullmatch(r"(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})", value)
    if m:
        return datetime(*(int(g) for g in m.groups()))

    # Só data: 20260812
    m = re.fullmatch(r"(\d{4})(\d{2})(\d{2})", value)
    if m:
        return datetime(*(int(g) for g in m.groups()))

    return None


def _parse_html_datetime(meta_text: str) -> tuple[datetime | None, datetime | None]:
    """Extrai início/fim de textos como 'Data: | 12 de agosto | Hora: | 14h30 a 17h00'."""
    # O separador " | " do get_text pode aparecer entre o rótulo e o valor.
    data_m = re.search(r"Data:\s*(?:\|\s*)?(\d{1,2})\s+de\s+([a-zç]+)", meta_text, re.I)
    hora_m = re.search(r"Hora:\s*(?:\|\s*)?(\d{1,2})h(\d{2})?", meta_text, re.I)
    if not data_m or not hora_m:
        return None, None

    dia = int(data_m.group(1))
    mes_nome = _mes_para_numero(data_m.group(2))
    if mes_nome is None:
        return None, None
    hora = int(hora_m.group(1))
    minuto = int(hora_m.group(2) or 0)

    # Sem ano explícito no meta; usa o ano corrente (documentado como limitação:
    # datas ambíguas não são resolvidas silenciosamente em outro cenário).
    ano = date.today().year
    try:
        inicio = datetime(ano, mes_nome, dia, hora, minuto)
    except ValueError:
        return None, None

    fim_m = re.search(r"a\s+(\d{1,2})h(\d{2})?", meta_text, re.I)
    if fim_m:
        try:
            fim = datetime(ano, mes_nome, dia, int(fim_m.group(1)), int(fim_m.group(2) or 0))
        except ValueError:
            fim = None
    else:
        fim = None
    return inicio, fim


_MESES = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
    "outubro": 10, "novembro": 11, "dezembro": 12,
}


def _mes_para_numero(nome: str) -> int | None:
    return _MESES.get(nome.lower())


def _extract_location(soup: BeautifulSoup, meta_text: str) -> str | None:
    venue = soup.select_one(".tribe-events-venue-details, .tribe-venue")
    if venue:
        text = venue.get_text(" ", strip=True)
        if text:
            return text
    m = re.search(r"Local:\s*([^\n|]+)", meta_text)
    return m.group(1).strip() if m else None


def _extract_inscription_url(text: str, source_url: str = "") -> str | None:
    """Procura URL de inscrição (Even3 ou 'inscri').

    Primeiro tenta um link Even3 explícito no texto; depois qualquer URL cujo
    texto ao redor indique inscrição. Retorna None quando não há evidência.
    """
    for url in re.findall(r"https?://[^\s|]+", text):
        url = url.rstrip(".,;")
        if "even3.com.br" in url:
            return url
    m = re.search(r"https?://[^\s|]+", text)
    if m:
        url = m.group(0).rstrip(".,;")
        if "inscric" in url.lower():
            return url
    return None


def _extract_inscription_url_from_soup(soup: BeautifulSoup, meta_text: str) -> str | None:
    """Busca link de inscrição nas âncoras do HTML (Even3, 'inscrição', 'participar')."""
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "")
        texto = anchor.get_text(" ", strip=True).lower()
        if "even3.com.br" in href:
            return href
        if "inscric" in href.lower() or any(
            k in texto for k in ("inscrição", "inscricao", "participar")
        ):
            if href.startswith("http"):
                return href
    return _extract_inscription_url(meta_text)


def _extract_category_from_ics(fields: dict[str, str]) -> str | None:
    cat = _unfold(fields.get("CATEGORIES", "")).strip()
    return cat or None


def _extract_category_from_html(meta_text: str) -> str | None:
    m = re.search(r"Categoria de Evento:\s*(?:\|\s*)?([^\n|]+)", meta_text)
    return m.group(1).strip() if m else None


def _content_hash(canonical: str, title: str, body: str) -> str:
    import hashlib

    return hashlib.sha256(f"{canonical}\n{title}\n{body}".encode("utf-8")).hexdigest()


def _canonicalize_url(url: str) -> str:
    from urllib.parse import urldefrag, urlsplit, urlunsplit

    without_fragment, _ = urldefrag(url)
    parts = urlsplit(without_fragment)
    path = parts.path or "/"
    if path != "/" and not path.endswith("/"):
        path += "/"
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))
