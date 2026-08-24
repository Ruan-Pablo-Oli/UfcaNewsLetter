from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

import fitz
import requests

# Hosts de onde aceitamos baixar anexos. O repositório de documentos da UFCA é
# "documentos" (português) — "documents.ufca.edu.br" não resolve em DNS, e a
# grafia errada fazia todo anexo ser rejeitado antes do download.
DEFAULT_ALLOWED_HOSTS = {
    "documentos.ufca.edu.br",
    "sites.ufca.edu.br",
}

DEFAULT_TIMEOUT = 20
DEFAULT_MAX_SIZE = 20 * 1024 * 1024  # 20 MB


class PDFProcessingError(Exception):
    """Erro base do processamento de um anexo PDF."""


class PDFValidationError(PDFProcessingError):
    """Resposta ou arquivo não corresponde a um PDF válido."""


class PDFDownloadError(PDFProcessingError):
    """Erro durante o download do anexo."""


class PDFExtractionError(PDFProcessingError):
    """Erro ao abrir ou extrair conteúdo do PDF."""


@dataclass(frozen=True, slots=True)
class ProcessedPDF:
    """Resultado do processamento de um anexo PDF."""

    url: str
    source_url: str
    file_hash: str
    text: str
    metadata: dict[str, str]
    edital_number: str | None
    edital_year: int | None
    is_rectification: bool


@dataclass(frozen=True, slots=True)
class _CachedPDF:
    """Informações mantidas pelo cache durante a execução."""

    result: ProcessedPDF
    etag: str | None
    last_modified: str | None


class PDFProcessor:
    """Baixa, valida, extrai e processa PDFs referenciados por um adaptador.
       Recebe uma URL de anexo já encontrada por um adaptador.
    """

    def __init__(
        self,
        session: requests.Session | None = None,
        *,
        allowed_hosts: set[str] | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        max_size: int = DEFAULT_MAX_SIZE,
    ):
        self.session = session or requests.Session()
        self.allowed_hosts = {
            host.lower().strip()
            for host in (allowed_hosts or DEFAULT_ALLOWED_HOSTS)
        }
        self.timeout = timeout
        self.max_size = max_size
        self._cache: dict[str, _CachedPDF] = {}

    def process(
        self,
        url: str,
        *,
        source_url: str,
    ) -> ProcessedPDF:
        """Processa um PDF e retorna seus dados extraídos."""

        self._validate_url(url)

        cached = self._cache.get(url)
        if cached is not None:
            return cached.result

        pdf_bytes, etag, last_modified = self._download(
            url,
            cached=cached,
        )

        if pdf_bytes is None:
            if cached is None:
                raise PDFDownloadError(
                    f"servidor retornou 304 sem entrada de cache para {url}"
                )

            return cached.result

        file_hash = self._calculate_hash(pdf_bytes)

        if cached is not None and cached.result.file_hash == file_hash:
            return cached.result

        text, metadata = self._extract_pdf(pdf_bytes)

        edital_number, edital_year = self._extract_edital_fields(text)
        is_rectification = self._detect_rectification(text)

        result = ProcessedPDF(
            url=url,
            source_url=source_url,
            file_hash=file_hash,
            text=text,
            metadata=metadata,
            edital_number=edital_number,
            edital_year=edital_year,
            is_rectification=is_rectification,
        )

        self._cache[url] = _CachedPDF(
            result=result,
            etag=etag,
            last_modified=last_modified,
        )

        return result

    def clear_cache(self) -> None:
        """Limpa o cache de execução."""

        self._cache.clear()

    def _validate_url(self, url: str) -> None:
        parts = urlsplit(url)

        if parts.scheme not in {"http", "https"}:
            raise PDFValidationError(
                f"esquema de URL não permitido: {parts.scheme!r}"
            )

        host = (parts.hostname or "").lower()

        if not host:
            raise PDFValidationError("URL sem hostname")

        if host not in self.allowed_hosts:
            raise PDFValidationError(
                f"host não permitido para PDF: {host}"
            )

    def _download(
        self,
        url: str,
        *,
        cached: _CachedPDF | None,
    ) -> tuple[bytes | None, str | None, str | None]:
        headers: dict[str, str] = {}

        if cached is not None:
            if cached.etag:
                headers["If-None-Match"] = cached.etag

            if cached.last_modified:
                headers["If-Modified-Since"] = cached.last_modified

        try:
            response = self.session.get(
                url,
                headers=headers,
                timeout=self.timeout,
                stream=True,
            )
        except requests.RequestException as exc:
            raise PDFDownloadError(
                f"falha ao baixar PDF {url}: {exc}"
            ) from exc

        try:
            if response.status_code == 304:
                return None, cached.etag if cached else None, (
                    cached.last_modified if cached else None
                )

            try:
                response.raise_for_status()
            except requests.RequestException as exc:
                raise PDFDownloadError(
                    f"resposta HTTP inválida para {url}: "
                    f"{response.status_code}"
                ) from exc

            content_type = response.headers.get("Content-Type", "")
            content_type = content_type.split(";", 1)[0].strip().lower()

            if content_type not in {
                "",
                "application/pdf",
                "application/octet-stream",
            }:
                raise PDFValidationError(
                    f"resposta não é PDF: Content-Type={content_type!r}"
                )

            content_length = response.headers.get("Content-Length")

            if content_length:
                try:
                    if int(content_length) > self.max_size:
                        raise PDFValidationError(
                            f"PDF excede o tamanho máximo permitido "
                            f"({self.max_size} bytes)"
                        )
                except ValueError:
                    pass

            chunks: list[bytes] = []
            total_size = 0

            try:
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue

                    total_size += len(chunk)

                    if total_size > self.max_size:
                        raise PDFValidationError(
                            f"PDF excede o tamanho máximo permitido "
                            f"({self.max_size} bytes)"
                        )

                    chunks.append(chunk)
            except requests.RequestException as exc:
                raise PDFDownloadError(
                    f"falha durante o download de {url}: {exc}"
                ) from exc

            pdf_bytes = b"".join(chunks)

            self._validate_pdf_bytes(pdf_bytes, url)

            return (
                pdf_bytes,
                response.headers.get("ETag"),
                response.headers.get("Last-Modified"),
            )
        finally:
            response.close()

    @staticmethod
    def _validate_pdf_bytes(pdf_bytes: bytes, url: str) -> None:
        if not pdf_bytes:
            raise PDFValidationError(
                f"resposta vazia ao baixar PDF: {url}"
            )

        if not pdf_bytes.startswith(b"%PDF-"):
            raise PDFValidationError(
                f"resposta não contém assinatura PDF válida: {url}"
            )

    @staticmethod
    def _calculate_hash(pdf_bytes: bytes) -> str:
        return hashlib.sha256(pdf_bytes).hexdigest()

    @staticmethod
    def _extract_pdf(
        pdf_bytes: bytes,
    ) -> tuple[str, dict[str, str]]:
        try:
            document = fitz.open(
                stream=pdf_bytes,
                filetype="pdf",
            )
        except Exception as exc:
            raise PDFExtractionError(
                "não foi possível abrir o PDF"
            ) from exc

        try:
            pages = [
                page.get_text()
                for page in document
            ]

            text = "\n".join(
                page_text.strip()
                for page_text in pages
                if page_text.strip()
            )

            raw_metadata = document.metadata or {}

            metadata = {
                key: value
                for key, value in raw_metadata.items()
                if value
            }

            return text, metadata
        except Exception as exc:
            raise PDFExtractionError(
                "falha ao extrair conteúdo do PDF"
            ) from exc
        finally:
            document.close()

    @staticmethod
    def _extract_edital_fields(
        text: str,
    ) -> tuple[str | None, int | None]:
        pattern = re.compile(
            r"\bedital\b"
            r"\s*(?:n[º°.]?|número)?"
            r"\s*"
            r"(\d+)"
            r"(?:\s*/\s*(\d{4}))?",
            re.IGNORECASE,
        )

        match = pattern.search(text)

        if not match:
            return None, None

        number = match.group(1)
        year = int(match.group(2)) if match.group(2) else None

        return number, year

    @staticmethod
    def _detect_rectification(text: str) -> bool:
        return bool(
            re.search(
                r"\bretifica(?:ção|cao|r)\b",
                text,
                re.IGNORECASE,
            )
        )