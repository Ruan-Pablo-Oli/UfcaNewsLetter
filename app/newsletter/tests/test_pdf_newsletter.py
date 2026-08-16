import hashlib

import fitz
import pytest
import requests

from newsletter.collectors.pdf_newsletter import (
    PDFDownloadError,
    PDFExtractionError,
    PDFProcessor,
    PDFValidationError,
)

PDF_URL = (
    "https://documents.ufca.edu.br/edital.pdf"
)

SOURCE_URL = (
    "https://www.ufca.edu.br/noticias/edital/"
)


class FakeResponse:

    def __init__(
        self,
        *,
        content: bytes,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        if 400 <= self.status_code < 600:
            raise requests.HTTPError(
                f"HTTP {self.status_code} error"
            )

    def iter_content(self, chunk_size=65536):
        yield self.content

    def close(self):
        pass


class FakeSession:

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(
            (url, kwargs)
        )

        return self.responses.pop(0)


def make_pdf(text: str) -> bytes:
    document = fitz.open()

    page = document.new_page()

    page.insert_text(
        (72, 72),
        text,
    )

    pdf_bytes = document.tobytes()

    document.close()

    return pdf_bytes


def test_processes_valid_pdf():

    pdf = make_pdf(
        "EDITAL Nº 12/2026\n"
        "RETIFICAÇÃO DO EDITAL Nº 12/2026"
    )

    session = FakeSession(
        [
            FakeResponse(
                content=pdf,
                headers={
                    "Content-Type": "application/pdf"
                },
            )
        ]
    )

    processor = PDFProcessor(
        session=session
    )

    result = processor.process(
        PDF_URL,
        source_url=SOURCE_URL,
    )

    assert result.url == PDF_URL

    assert result.source_url == SOURCE_URL

    assert result.file_hash == (
        hashlib.sha256(pdf).hexdigest()
    )

    assert "EDITAL Nº 12/2026" in result.text

    assert result.edital_number == "12"

    assert result.edital_year == 2026

    assert result.is_rectification is True


def test_rejects_disallowed_host():

    session = FakeSession([])

    processor = PDFProcessor(
        session=session
    )

    with pytest.raises(
        PDFValidationError,
        match="host não permitido",
    ):
        processor.process(
            "https://example.com/test.pdf",
            source_url=SOURCE_URL,
        )

    assert session.calls == []


def test_rejects_non_pdf():

    session = FakeSession(
        [
            FakeResponse(
                content=b"<html>pagina</html>",
                headers={
                    "Content-Type": "text/html"
                },
            )
        ]
    )

    processor = PDFProcessor(
        session=session
    )

    with pytest.raises(
        PDFValidationError,
        match="resposta não é PDF",
    ):
        processor.process(
            PDF_URL,
            source_url=SOURCE_URL,
        )


def test_rejects_html_disguised_as_pdf():

    session = FakeSession(
        [
            FakeResponse(
                content=b"<html>pagina</html>",
                headers={
                    "Content-Type": "application/pdf"
                },
            )
        ]
    )

    processor = PDFProcessor(
        session=session
    )

    with pytest.raises(
        PDFValidationError,
        match="assinatura PDF válida",
    ):
        processor.process(
            PDF_URL,
            source_url=SOURCE_URL,
        )


def test_extracts_metadata():

    document = fitz.open()

    document.new_page()

    document.set_metadata(
        {
            "title": "Edital UFCA",
            "author": "UFCA",
        }
    )

    pdf = document.tobytes()

    document.close()

    session = FakeSession(
        [
            FakeResponse(
                content=pdf,
                headers={
                    "Content-Type": "application/pdf"
                },
            )
        ]
    )

    processor = PDFProcessor(
        session=session
    )

    result = processor.process(
        PDF_URL,
        source_url=SOURCE_URL,
    )

    assert result.metadata["title"] == "Edital UFCA"

    assert result.metadata["author"] == "UFCA"


def test_cache_prevents_second_download():

    pdf = make_pdf(
        "EDITAL Nº 10/2026"
    )

    session = FakeSession(
        [
            FakeResponse(
                content=pdf,
                headers={
                    "Content-Type": "application/pdf"
                },
            ),
            FakeResponse(
                content=pdf,
                headers={
                    "Content-Type": "application/pdf"
                },
            ),
        ]
    )

    processor = PDFProcessor(
        session=session
    )

    first = processor.process(
        PDF_URL,
        source_url=SOURCE_URL,
    )

    second = processor.process(
        PDF_URL,
        source_url=SOURCE_URL,
    )

    assert first == second

    assert len(session.calls) == 1


def test_changed_hash_reprocesses_pdf():

    first_pdf = make_pdf(
        "EDITAL Nº 1/2026"
    )

    second_pdf = make_pdf(
        "EDITAL Nº 2/2026"
    )

    session = FakeSession(
        [
            FakeResponse(
                content=first_pdf,
                headers={
                    "Content-Type": "application/pdf"
                },
            ),
            FakeResponse(
                content=second_pdf,
                headers={
                    "Content-Type": "application/pdf"
                },
            ),
        ]
    )

    processor = PDFProcessor(
        session=session
    )

    first = processor.process(
        PDF_URL,
        source_url=SOURCE_URL,
    )

    processor.clear_cache()

    second = processor.process(
        PDF_URL,
        source_url=SOURCE_URL,
    )

    assert first.file_hash != second.file_hash

    assert first.edital_number == "1"

    assert second.edital_number == "2"


def test_rejects_unreadable_pdf():

    invalid_pdf = (
        b"%PDF-this-is-not-a-valid-pdf"
    )

    session = FakeSession(
        [
            FakeResponse(
                content=invalid_pdf,
                headers={
                    "Content-Type": "application/pdf"
                },
            )
        ]
    )

    processor = PDFProcessor(
        session=session
    )

    with pytest.raises(
        PDFExtractionError,
        match="não foi possível abrir o PDF",
    ):
        processor.process(
            PDF_URL,
            source_url=SOURCE_URL,
        )


def test_download_error():

    class FailingSession:

        def get(self, url, **kwargs):

            raise requests.Timeout(
                "tempo esgotado"
            )

    processor = PDFProcessor(
        session=FailingSession()
    )

    with pytest.raises(
        PDFDownloadError,
        match="falha ao baixar PDF",
    ):
        processor.process(
            PDF_URL,
            source_url=SOURCE_URL,
        )


def test_does_not_infer_missing_year():

    pdf = make_pdf(
        "EDITAL Nº 42\n"
        "Processo seletivo"
    )

    session = FakeSession(
        [
            FakeResponse(
                content=pdf,
                headers={
                    "Content-Type": "application/pdf"
                },
            )
        ]
    )

    processor = PDFProcessor(
        session=session
    )

    result = processor.process(
        PDF_URL,
        source_url=SOURCE_URL,
    )

    assert result.edital_number == "42"

    assert result.edital_year is None


def test_detects_rectification():

    pdf = make_pdf(
        "RETIFICAÇÃO DO EDITAL Nº 7"
    )

    session = FakeSession(
        [
            FakeResponse(
                content=pdf,
                headers={
                    "Content-Type": "application/pdf"
                },
            )
        ]
    )

    processor = PDFProcessor(
        session=session
    )

    result = processor.process(
        PDF_URL,
        source_url=SOURCE_URL,
    )

    assert result.edital_number == "7"

    assert result.edital_year is None

    assert result.is_rectification is True