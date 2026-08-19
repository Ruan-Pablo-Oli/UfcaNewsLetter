from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

DEFAULT_SOURCE_URLS = (
    "https://www.ufca.edu.br/admissao/concursos-e-selecoes/docentes/efetivo/",
    "https://www.ufca.edu.br/admissao/concursos-e-selecoes/"
    "docentes/substituto-temporario/",
    "https://www.ufca.edu.br/admissao/concursos-e-selecoes/"
    "tecnicos-administrativos/efetivo/",
    "https://www.ufca.edu.br/admissao/concursos-e-selecoes/"
    "tecnicos-administrativos/temporario/",
)


@dataclass(frozen=True, slots=True)
class ConcursoRecord:
    source_url: str
    canonical_url: str
    title: str
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
    def __init__(
        self,
        session: requests.Session | None = None,
        *,
        user_agent: str = "UfcaNewsLetter/0.1",
    ):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

    def collect(
        self,
        listing_url: str,
        *,
        fetch_html=None,
        known_canonical_urls: set[str] | None = None,
    ) -> list[ConcursoRecord]:
        fetch = fetch_html or self._fetch_html

        known_urls = {
            self._canonicalize_url(url)
            for url in (known_canonical_urls or set())
        }

        listing_html = fetch(listing_url)

        item_urls = self.parse_listing(
            listing_html,
            listing_url,
        )

        records = []

        for item_url in item_urls:
            canonical_url = self._canonicalize_url(item_url)

            if canonical_url in known_urls:
                continue

            html = fetch(canonical_url)

            records.append(
                self.parse_item(
                    html,
                    canonical_url,
                    listing_url,
                )
            )

        return records

    def parse_listing(
        self,
        html: str,
        listing_url: str,
    ) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")

        urls: list[str] = []
        seen: set[str] = set()

        for anchor in soup.find_all("a", href=True):
            text = anchor.get_text(" ", strip=True)

            if not re.search(
                r"\bEdital\b",
                text,
                re.IGNORECASE,
            ):
                continue

            href = urljoin(
                listing_url,
                anchor["href"],
            )

            canonical = self._canonicalize_url(href)

            if canonical in seen:
                continue

            if not self._is_ufca_url(canonical):
                continue

            seen.add(canonical)
            urls.append(canonical)

        return urls

    def parse_item(
        self,
        html: str,
        source_url: str,
        listing_url: str,
    ) -> ConcursoRecord:
        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        text = soup.get_text(
            " ",
            strip=True,
        )

        title = self._extract_title(soup)

        edital_number, edital_year = (
            self._extract_edital_fields(
                title,
                text,
            )
        )

        published_at, updated_at = (
            self._extract_dates(text)
        )

        organization = self._extract_organization(
            soup,
        )

        attachment_urls = self._extract_documents(
            soup,
            source_url,
        )

        is_rectification, related_url = (
            self._extract_rectification(
                soup,
                source_url,
            )
        )

        content_hash = self._calculate_hash(
            source_url=source_url,
            title=title,
            organization=organization,
            edital_number=edital_number,
            edital_year=edital_year,
            published_at=published_at,
            updated_at=updated_at,
            attachment_urls=attachment_urls,
        )

        return ConcursoRecord(
            source_url=listing_url,
            canonical_url=source_url,
            title=title,
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
    def _extract_edital_fields(
        title: str,
        text: str,
    ) -> tuple[str | None, int | None]:
        match = re.search(
            r"\bEdital\s+(\d+)(?:/(\d{4}))?",
            title,
            re.IGNORECASE,
        )

        if match is None:
            match = re.search(
                r"\bEdital\s+(\d+)(?:/(\d{4}))?",
                text,
                re.IGNORECASE,
            )

        if match is None:
            return None, None

        number = match.group(1)
        year = (
            int(match.group(2))
            if match.group(2)
            else None
        )

        return number, year

    @staticmethod
    def _extract_dates(
        text: str,
    ) -> tuple[datetime | None, datetime | None]:
        published_at = None
        updated_at = None

        published_match = re.search(
            r"Publicado em\s+(\d{2}/\d{2}/\d{4})",
            text,
            re.IGNORECASE,
        )

        updated_match = re.search(
            r"Atualizado em\s+(\d{2}/\d{2}/\d{4})",
            text,
            re.IGNORECASE,
        )

        if published_match:
            published_at = datetime.strptime(
                published_match.group(1),
                "%d/%m/%Y",
            )

        if updated_match:
            updated_at = datetime.strptime(
                updated_match.group(1),
                "%d/%m/%Y",
            )

        return published_at, updated_at

    @staticmethod
    def _extract_organization(
        soup: BeautifulSoup,
    ) -> str | None:
        text = soup.get_text(
            " ",
            strip=True,
        )

        match = re.search(
            r"\bPROGEP\b",
            text,
            re.IGNORECASE,
        )

        if match:
            return match.group(0)

        return None

    @staticmethod
    def _extract_title(
        soup: BeautifulSoup,
    ) -> str:
        title = soup.find("h1")

        if title is not None:
            text = title.get_text(" ", strip=True)

            if text:
                return text

        html_title = soup.find("title")

        if html_title is not None:
            text = html_title.get_text(" ", strip=True)

            if text:
                return text

        return ""

    @staticmethod
    def _extract_documents(
        soup: BeautifulSoup,
        source_url: str,
    ) -> tuple[str, ...]:
        urls: list[str] = []
        seen: set[str] = set()

        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            text = anchor.get_text(" ", strip=True)

            url = urljoin(source_url, href)

            is_pdf = urlsplit(url).path.lower().endswith(".pdf")

            mentions_document = re.search(
                r"\b("
                r"edital|"
                r"retifica(?:ção|cao|r)|"
                r"baixar\s+documento|"
                r"documento"
                r")\b",
                text,
                re.IGNORECASE,
            )

            if not is_pdf and not mentions_document:
                continue

            if url in seen:
                continue

            if not ConcursosSelecoesCollector._is_ufca_url(url):
                continue

            seen.add(url)
            urls.append(url)

        return tuple(urls)

    @staticmethod
    def _extract_rectification(
        soup: BeautifulSoup,
        source_url: str,
    ) -> tuple[bool, str | None]:
        rectification_pattern = re.compile(
            r"\bretifica(?:ção|cao|r)\b",
            re.IGNORECASE,
        )

        for anchor in soup.find_all("a", href=True):
            text = anchor.get_text(" ", strip=True)

            if not rectification_pattern.search(text):
                continue

            href = urljoin(
                source_url,
                anchor["href"],
            )

            return True, href

        page_text = soup.get_text(
            " ",
            strip=True,
        )

        if rectification_pattern.search(page_text):
            return True, None

        return False, None

    @staticmethod
    def _calculate_hash(
        *,
        source_url: str,
        title: str,
        organization: str | None,
        edital_number: str | None,
        edital_year: int | None,
        published_at: datetime | None,
        updated_at: datetime | None,
        attachment_urls: tuple[str, ...],
    ) -> str:
        values = (
            source_url,
            title,
            organization or "",
            edital_number or "",
            str(edital_year) if edital_year is not None else "",
            (
                published_at.isoformat()
                if published_at is not None
                else ""
            ),
            (
                updated_at.isoformat()
                if updated_at is not None
                else ""
            ),
            *attachment_urls,
        )

        content = "\n".join(values).encode("utf-8")

        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def _canonicalize_url(url: str) -> str:
        parts = urlsplit(url)

        scheme = parts.scheme.lower()
        hostname = (
            parts.hostname.lower()
            if parts.hostname
            else ""
        )

        port = parts.port

        if port is None:
            netloc = hostname
        elif (
            (scheme == "http" and port == 80)
            or (scheme == "https" and port == 443)
        ):
            netloc = hostname
        else:
            netloc = f"{hostname}:{port}"

        path = parts.path or "/"

        if path != "/":
            path = path.rstrip("/")

        return urlunsplit(
            (
                scheme,
                netloc,
                path,
                parts.query,
                "",
            )
        )

    @staticmethod
    def _is_ufca_url(url: str) -> bool:
        parts = urlsplit(url)

        if parts.scheme not in {"http", "https"}:
            return False

        hostname = (
            parts.hostname.lower()
            if parts.hostname
            else ""
        )

        allowed_hosts = {
            "ufca.edu.br",
            "www.ufca.edu.br",
            "documents.ufca.edu.br",
            "sites.ufca.edu.br",
        }

        return (
            hostname in allowed_hosts
            or hostname.endswith(".ufca.edu.br")
        )

    def _fetch_html(
        self,
        url: str,
    ) -> str:
        response = self.session.get(
            url,
            timeout=20,
        )

        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type",
            "",
        ).lower()

        if (
            content_type
            and "text/html" not in content_type
            and "application/xhtml+xml" not in content_type
        ):
            raise ValueError(
                f"Expected HTML response, got {content_type!r}"
            )

        return response.text