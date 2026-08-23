"""Coleta deterministica de Noticias e Informes do portal UFCA."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Callable
from urllib.parse import parse_qsl, urldefrag, urlencode, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

_DATE_RE = re.compile(r"(?:Publicado|Atualizado)\s+em\s+(\d{2}/\d{2}/\d{4})", re.I)
_NEXT_RE = re.compile(r"(?:pr[óo]ximo|next)", re.I)
_TRACKING_PARAMS = {
    "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "utm_campaign", "utm_medium",
    "utm_source", "utm_term",
}


@dataclass(frozen=True, slots=True)
class NewsInformeRecord:
    source_url: str
    canonical_url: str
    title: str
    body: str
    published_at: datetime | None
    updated_at: datetime | None
    category: str | None
    attachment_urls: tuple[str, ...]
    content_hash: str


@dataclass(frozen=True, slots=True)
class CollectionError:
    url: str
    reason: str


class NewsInformeCollector:
    """Extrai registros de posts sem persistir no banco.

    A persistência em ``Conteudo`` fica deliberadamente fora deste adaptador,
    pois depende do contrato de dados definido na issue #52.
    """

    def __init__(
        self,
        session: requests.Session | None = None,
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
    ) -> list[NewsInformeRecord]:
        """Percorre uma listagem paginada e retorna registros sem duplicatas."""
        fetch = fetch_html or self._fetch_html
        self.errors = []
        known_urls = {self._canonicalize_url(url) for url in (known_canonical_urls or set())}
        pending = [listing_url]
        visited_listing_urls: set[str] = set()
        visited_article_urls: set[str] = set()
        records: list[NewsInformeRecord] = []

        while pending and len(visited_listing_urls) < max_pages:
            current_url = pending.pop(0)
            current_url = self._canonicalize_url(current_url)
            if current_url in visited_listing_urls:
                continue
            visited_listing_urls.add(current_url)

            try:
                html = fetch(current_url)
                article_urls, next_url = self.parse_listing(html, current_url)
            except Exception as exc:
                self.errors.append(CollectionError(current_url, str(exc)))
                continue
            for article_url in article_urls:
                article_url = self._canonicalize_url(article_url)
                if article_url in visited_article_urls or article_url in known_urls:
                    continue
                visited_article_urls.add(article_url)
                try:
                    record = self.parse_post(fetch(article_url), article_url)
                except Exception as exc:
                    self.errors.append(CollectionError(article_url, str(exc)))
                    continue
                records.append(record)

            if next_url:
                pending.append(next_url)

        return records

    def parse_listing(self, html: str, listing_url: str) -> tuple[list[str], str | None]:
        soup = BeautifulSoup(html, "lxml")
        base = self._path_prefix(listing_url)
        article_urls: list[str] = []
        seen: set[str] = set()

        for anchor in soup.find_all("a", href=True):
            href = urljoin(listing_url, anchor["href"])
            parts = urlsplit(href)
            path = parts.path.rstrip("/") + "/"
            if not self._is_article_path(path, base):
                continue
            canonical = self._canonicalize_url(href)
            if canonical not in seen:
                seen.add(canonical)
                article_urls.append(canonical)

        next_url = None
        for anchor in soup.find_all("a", href=True):
            rel = anchor.get("rel", [])
            rel_values = rel if isinstance(rel, list) else [rel]
            text = anchor.get_text(" ", strip=True)
            if "next" in {str(value).lower() for value in rel_values} or _NEXT_RE.search(text):
                next_url = self._canonicalize_url(urljoin(listing_url, anchor["href"]))
                break

        return article_urls, next_url

    def parse_post(self, html: str, source_url: str) -> NewsInformeRecord:
        soup = BeautifulSoup(html, "lxml")
        canonical_tag = soup.find("link", rel=lambda value: value and "canonical" in value)
        canonical_url = self._canonicalize_url(
            canonical_tag.get("href") if canonical_tag and canonical_tag.get("href") else source_url
        )

        title_node = soup.find("h1")
        if title_node is None or not title_node.get_text(" ", strip=True):
            raise ValueError(f"titulo ausente em {source_url}")
        title = title_node.get_text(" ", strip=True)

        body_node = soup.select_one(
            ".entry-content, .post-content, .article-content"
        ) or soup.find("main")
        if body_node is None:
            raise ValueError(f"corpo ausente em {source_url}")
        for node in body_node.select("script, style, nav"):
            node.decompose()
        paragraphs = [node.get_text(" ", strip=True) for node in body_node.find_all("p")]
        body = "\n".join(part for part in paragraphs if part)
        if not body:
            body = body_node.get_text(" ", strip=True)

        dates = self._extract_dates(soup.get_text(" ", strip=True))
        category = self._extract_category(soup)
        attachment_urls = tuple(
            dict.fromkeys(
                self._canonicalize_url(urljoin(source_url, anchor["href"]))
                for anchor in body_node.find_all("a", href=True)
                if self._looks_like_pdf(anchor["href"])
            )
        )
        content_hash = hashlib.sha256(
            f"{canonical_url}\n{title}\n{body}".encode("utf-8")
        ).hexdigest()

        return NewsInformeRecord(
            source_url=source_url,
            canonical_url=canonical_url,
            title=title,
            body=body,
            published_at=dates[0],
            updated_at=dates[1],
            category=category,
            attachment_urls=attachment_urls,
            content_hash=content_hash,
        )

    def _fetch_html(self, url: str) -> str:
        response = self.session.get(url, timeout=20)
        response.raise_for_status()
        return response.text

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
    def _extract_category(soup: BeautifulSoup) -> str | None:
        breadcrumb = soup.select_one(".breadcrumb, .breadcrumbs, nav[aria-label*='breadcrumb' i]")
        if breadcrumb is None:
            return None
        values = [
            item.get_text(" ", strip=True)
            for item in breadcrumb.find_all(["a", "span", "li"])
        ]
        values = [
            value for value in values
            if value and value.lower() not in {"início", "inicio", ">"}
        ]
        return values[-1] if values else None

    @staticmethod
    def _looks_like_pdf(href: str) -> bool:
        return urlsplit(href).path.lower().endswith(".pdf")

    @staticmethod
    def _path_prefix(url: str) -> str:
        path = urlsplit(url).path.rstrip("/")
        path = re.sub(r"/page/\d+$", "", path)
        return path if path else "/"

    # Categorias de informe (`/noticias/informe_category/<slug>/`) listam itens
    # hospedados em `/informes/<slug>/`, fora do prefixo da própria listagem.
    # Aceitar esses prefixos fixos (além do prefixo da listagem) resolve o caso
    # sem afrouxar a ponto de capturar links de menu como `/instituicao/...`.
    _ARTICLE_PATH_PREFIXES = ("/noticias/", "/informes/")
    _BLOCKED_PATH_SEGMENTS = {"categoria", "page", "tag", "author", "informe_category"}

    @classmethod
    def _is_article_path(cls, path: str, base: str) -> bool:
        prefixes = (base.rstrip("/") + "/", *cls._ARTICLE_PATH_PREFIXES)
        matched_prefix = next((prefix for prefix in prefixes if path.startswith(prefix)), None)
        if matched_prefix is None:
            return False
        suffix = path[len(matched_prefix) :].strip("/")
        if not suffix or "/" in suffix:
            return False
        return suffix not in cls._BLOCKED_PATH_SEGMENTS

    @staticmethod
    def _canonicalize_url(url: str) -> str:
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
