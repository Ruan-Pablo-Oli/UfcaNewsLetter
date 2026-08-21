"""Coleta deterministica de Concursos e Seleções do portal UFCA.

Segue o mesmo contrato do adaptador de Notícias e Informes
(``NewsInformeCollector``): não toca no banco, expõe ``collect(listing_url, *,
fetch_html, max_pages, known_canonical_urls)``, acumula falhas em ``errors`` e
devolve registros com ``body``/``content_hash`` — é isso que ``newsletter.coleta``
consome para persistir em ``Conteudo``.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Callable
from urllib.parse import parse_qsl, urldefrag, urlencode, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

from .noticias_informes import CollectionError

DEFAULT_SOURCE_URLS = (
    "https://www.ufca.edu.br/admissao/concursos-e-selecoes/docentes/efetivo/",
    "https://www.ufca.edu.br/admissao/concursos-e-selecoes/"
    "docentes/substituto-temporario/",
    "https://www.ufca.edu.br/admissao/concursos-e-selecoes/"
    "tecnicos-administrativos/efetivo/",
    "https://www.ufca.edu.br/admissao/concursos-e-selecoes/"
    "tecnicos-administrativos/temporario/",
)

# Aceita as grafias usadas nos editais da UFCA: "Edital 20/2026",
# "Edital nº 20/2026", "EDITAL N° 20/2026", "Edital N. 20/2026".
_EDITAL_RE = re.compile(
    r"\bEdital\s*(?:n[º°o]?\.?\s*)?(\d{1,5})(?:\s*/\s*(\d{4}))?",
    re.IGNORECASE,
)
# "retificação", "retificações", "retificado", "retificar", ...
_RECTIFICATION_RE = re.compile(r"\bretifica\w*", re.IGNORECASE)
_EDITAL_WORD_RE = re.compile(r"\bedital\b", re.IGNORECASE)
_DATE_RE = re.compile(r"(?:Publicado|Atualizado)\s+em\s+(\d{2}/\d{2}/\d{4})", re.IGNORECASE)
_NEXT_RE = re.compile(r"(?:pr[óo]ximo|next)", re.IGNORECASE)

# Unidades que publicam editais. Lista explícita (e não um padrão genérico) para
# não transformar qualquer sigla da página em "organização".
_ORGANIZATION_RE = re.compile(
    r"\b(PROGEP|PROEN|PROEX|PROPLAN|PROAD|PRPI|PRAE|REITORIA)\b",
    re.IGNORECASE,
)

_TRACKING_PARAMS = {
    "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "utm_campaign", "utm_medium",
    "utm_source", "utm_term",
}

_UFCA_HOSTS = {"ufca.edu.br", "documentos.ufca.edu.br"}


@dataclass(frozen=True, slots=True)
class ConcursoRecord:
    source_url: str
    canonical_url: str
    title: str
    body: str
    organization: str | None
    edital_number: str | None
    edital_year: int | None
    published_at: datetime | None
    updated_at: datetime | None
    attachment_urls: tuple[str, ...]
    is_rectification: bool
    related_url: str | None
    content_hash: str


class ConcursosSelecoesCollector:
    """Extrai editais de concursos e seleções sem persistir no banco."""

    def __init__(
        self,
        session: requests.Session | None = None,
        *,
        user_agent: str = "UfcaNewsLetter/0.1",
    ):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.errors: list[CollectionError] = []

    def collect(
        self,
        listing_url: str,
        *,
        fetch_html: Callable[[str], str] | None = None,
        max_pages: int = 100,
        known_canonical_urls: set[str] | None = None,
    ) -> list[ConcursoRecord]:
        """Percorre uma listagem paginada e retorna registros sem duplicatas.

        Falhas em uma página ou em um item são registradas em ``errors`` e a
        varredura continua — um 404 num edital não pode descartar os demais.
        """
        fetch = fetch_html or self._fetch_html
        self.errors = []
        known_urls = {self._canonicalize_url(url) for url in (known_canonical_urls or set())}
        pending = [listing_url]
        visited_listing_urls: set[str] = set()
        visited_item_urls: set[str] = set()
        records: list[ConcursoRecord] = []

        while pending and len(visited_listing_urls) < max_pages:
            current_url = self._canonicalize_url(pending.pop(0))
            if current_url in visited_listing_urls:
                continue
            visited_listing_urls.add(current_url)

            try:
                html = fetch(current_url)
                item_urls, next_url = self.parse_listing(html, current_url)
            except Exception as exc:
                self.errors.append(CollectionError(current_url, str(exc)))
                continue

            for item_url in item_urls:
                if item_url in visited_item_urls or item_url in known_urls:
                    continue
                visited_item_urls.add(item_url)
                try:
                    record = self.parse_item(fetch(item_url), item_url, listing_url)
                except Exception as exc:
                    self.errors.append(CollectionError(item_url, str(exc)))
                    continue
                records.append(record)

            if next_url:
                pending.append(next_url)

        return records

    def parse_listing(self, html: str, listing_url: str) -> tuple[list[str], str | None]:
        """Retorna as URLs dos itens da listagem e a URL da próxima página.

        O filtro é pelo *caminho* do link (tem que estar sob a própria listagem),
        não pelo texto da âncora: filtrar por "contém a palavra Edital" perdia
        itens como "Processo Seletivo Simplificado nº 05/2026" e ao mesmo tempo
        aceitava links de menu/"posts recentes" que só mencionam a palavra.
        """
        soup = BeautifulSoup(html, "lxml")
        base = self._path_prefix(listing_url)
        item_urls: list[str] = []
        seen: set[str] = set()

        for anchor in soup.find_all("a", href=True):
            href = urljoin(listing_url, anchor["href"])
            if not self._is_ufca_url(href):
                continue
            path = urlsplit(href).path.rstrip("/") + "/"
            if not self._is_item_path(path, base):
                continue
            canonical = self._canonicalize_url(href)
            if canonical not in seen:
                seen.add(canonical)
                item_urls.append(canonical)

        next_url = None
        for anchor in soup.find_all("a", href=True):
            rel = anchor.get("rel", [])
            rel_values = rel if isinstance(rel, list) else [rel]
            text = anchor.get_text(" ", strip=True)
            if "next" in {str(value).lower() for value in rel_values} or _NEXT_RE.search(text):
                next_url = self._canonicalize_url(urljoin(listing_url, anchor["href"]))
                break

        return item_urls, next_url

    def parse_item(self, html: str, source_url: str, listing_url: str) -> ConcursoRecord:
        soup = BeautifulSoup(html, "lxml")
        canonical_url = self._canonicalize_url(source_url)

        title = self._extract_title(soup)
        content = self._content_node(soup)
        body = self._extract_body(content)

        edital_number, edital_year = self._extract_edital_fields(title, body)
        published_at, updated_at = self._extract_dates(soup.get_text(" ", strip=True))
        organization = self._extract_organization(soup)
        attachment_urls = self._extract_documents(content, canonical_url)
        is_rectification, related_url = self._extract_rectification(
            content, title, canonical_url
        )

        # O hash cobre só identidade + conteúdo textual (mesma regra do
        # NewsInformeCollector). Incluir `updated_at` ou a lista de anexos faria
        # o mesmo edital virar um `Conteudo` novo a cada errata publicada,
        # quebrando a idempotência de reprocessamento exigida pela US-03.1.4.
        content_hash = hashlib.sha256(
            f"{canonical_url}\n{title}\n{body}".encode("utf-8")
        ).hexdigest()

        return ConcursoRecord(
            source_url=listing_url,
            canonical_url=canonical_url,
            title=title,
            body=body,
            organization=organization,
            edital_number=edital_number,
            edital_year=edital_year,
            published_at=published_at,
            updated_at=updated_at,
            attachment_urls=attachment_urls,
            is_rectification=is_rectification,
            related_url=related_url,
            content_hash=content_hash,
        )

    @staticmethod
    def _extract_edital_fields(title: str, body: str) -> tuple[str | None, int | None]:
        match = _EDITAL_RE.search(title) or _EDITAL_RE.search(body)
        if match is None:
            return None, None
        year = int(match.group(2)) if match.group(2) else None
        return match.group(1), year

    @staticmethod
    def _extract_dates(text: str) -> tuple[datetime | None, datetime | None]:
        published = updated = None
        for match in _DATE_RE.finditer(text):
            value = datetime.strptime(match.group(1), "%d/%m/%Y")
            if match.group(0).lower().startswith("publicado") and published is None:
                published = value
            elif match.group(0).lower().startswith("atualizado") and updated is None:
                updated = value
        return published, updated

    @staticmethod
    def _extract_organization(soup: BeautifulSoup) -> str | None:
        """Normaliza para maiúsculas: "progep" e "PROGEP" são a mesma unidade."""
        match = _ORGANIZATION_RE.search(soup.get_text(" ", strip=True))
        return match.group(1).upper() if match else None

    @staticmethod
    def _extract_title(soup: BeautifulSoup) -> str:
        for node in (soup.find("h1"), soup.find("title")):
            if node is not None:
                text = node.get_text(" ", strip=True)
                if text:
                    return text
        return ""

    @staticmethod
    def _content_node(soup: BeautifulSoup):
        """Delimita o corpo do post, para não varrer menu/sidebar/rodapé."""
        content = (
            soup.select_one(".entry-content, .post-content, .article-content")
            or soup.find("main")
            or soup.body
            or soup
        )
        for node in content.select("script, style, nav"):
            node.decompose()
        return content

    @staticmethod
    def _extract_body(content) -> str:
        paragraphs = [node.get_text(" ", strip=True) for node in content.find_all("p")]
        body = "\n".join(part for part in paragraphs if part)
        return body or content.get_text(" ", strip=True)

    @classmethod
    def _extract_documents(cls, content, source_url: str) -> tuple[str, ...]:
        """Só PDFs, e só dentro do corpo do post.

        Aceitar qualquer âncora cujo *texto* mencionasse "edital"/"documento"
        guardava páginas HTML como se fossem anexos.
        """
        urls: list[str] = []
        seen: set[str] = set()
        for anchor in content.find_all("a", href=True):
            url = cls._canonicalize_url(urljoin(source_url, anchor["href"]))
            if not cls._looks_like_pdf(url) or not cls._is_ufca_url(url):
                continue
            if url not in seen:
                seen.add(url)
                urls.append(url)
        return tuple(urls)

    @classmethod
    def _extract_rectification(
        cls, content, title: str, canonical_url: str
    ) -> tuple[bool, str | None]:
        """Decide pelo *título da própria página*, não por links que ela contém.

        Um edital original quase sempre linka a própria errata; marcar a página
        como retificação por causa desse link invertia a relação (o original
        virava retificação de si mesmo). Só o título identifica a página.
        """
        if not _RECTIFICATION_RE.search(title):
            return False, None

        # A página é uma retificação: o `related_url` é o edital que ela altera —
        # um link HTML (não o PDF da própria errata) para outra página da UFCA.
        for anchor in content.find_all("a", href=True):
            text = anchor.get_text(" ", strip=True)
            if not _EDITAL_WORD_RE.search(text) or _RECTIFICATION_RE.search(text):
                continue
            url = cls._canonicalize_url(urljoin(canonical_url, anchor["href"]))
            if cls._looks_like_pdf(url) or not cls._is_ufca_url(url):
                continue
            if url != canonical_url:
                return True, url

        return True, None

    @staticmethod
    def _looks_like_pdf(url: str) -> bool:
        return urlsplit(url).path.lower().endswith(".pdf")

    @staticmethod
    def _path_prefix(url: str) -> str:
        path = urlsplit(url).path.rstrip("/")
        path = re.sub(r"/page/\d+$", "", path)
        return path if path else "/"

    @staticmethod
    def _is_item_path(path: str, base: str) -> bool:
        prefix = base.rstrip("/") + "/"
        if not path.startswith(prefix):
            return False
        suffix = path[len(prefix):].strip("/")
        if not suffix or suffix.startswith(("categoria/", "page/", "tag/", "author/")):
            return False
        return "/" not in suffix

    @staticmethod
    def _canonicalize_url(url: str) -> str:
        """Mesma normalização do ``NewsInformeCollector``.

        Precisa bater exatamente com a dele: é essa string que vai para
        ``Conteudo.url`` e que volta em ``known_canonical_urls``, e é por ela
        que uma retificação é ligada ao edital original (``related_url``).
        """
        without_fragment, _ = urldefrag(url)
        parts = urlsplit(without_fragment)
        query = [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if key not in _TRACKING_PARAMS
        ]
        path = parts.path or "/"
        if path != "/" and not path.endswith("/") and "." not in path.rsplit("/", 1)[-1]:
            path += "/"
        return urlunsplit((parts.scheme, parts.netloc, path, urlencode(query), ""))

    @staticmethod
    def _is_ufca_url(url: str) -> bool:
        parts = urlsplit(url)
        if parts.scheme not in {"http", "https"}:
            return False
        hostname = parts.hostname.lower() if parts.hostname else ""
        return hostname in _UFCA_HOSTS or hostname.endswith(".ufca.edu.br")

    def _fetch_html(self, url: str) -> str:
        response = self.session.get(url, timeout=20)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()
        if (
            content_type
            and "text/html" not in content_type
            and "application/xhtml+xml" not in content_type
        ):
            raise ValueError(f"Expected HTML response, got {content_type!r}")
        return response.text
