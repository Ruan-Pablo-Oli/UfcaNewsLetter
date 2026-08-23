"""Integração do PDFProcessor ao fluxo de coleta (issue #54)."""
from dataclasses import dataclass
from datetime import datetime

import pytest

from newsletter.coleta import coletar_fonte
from newsletter.collectors import CollectionError
from newsletter.collectors.pdf_newsletter import PDFProcessingError, ProcessedPDF
from newsletter.models import Conteudo, Fonte


@dataclass(frozen=True, slots=True)
class FakeRecord:
    source_url: str
    canonical_url: str
    title: str
    body: str
    published_at: datetime | None
    updated_at: datetime | None
    category: str | None
    attachment_urls: tuple[str, ...]
    content_hash: str


def _record(*attachment_urls: str) -> FakeRecord:
    return FakeRecord(
        source_url="https://www.ufca.edu.br/noticias/fake/",
        canonical_url="https://www.ufca.edu.br/noticias/fake/",
        title="Notícia com anexo",
        body="Corpo.",
        published_at=datetime(2026, 8, 1),
        updated_at=None,
        category=None,
        attachment_urls=attachment_urls,
        content_hash="hash-com-anexo",
    )


def _processed(url: str) -> ProcessedPDF:
    return ProcessedPDF(
        url=url,
        source_url="https://www.ufca.edu.br/noticias/fake/",
        file_hash=f"hash-{url}",
        text="texto do edital",
        metadata={"format": "PDF"},
        edital_number="12",
        edital_year=2026,
        is_rectification=False,
    )


class FakePDFProcessor:
    def __init__(self, falhas: set[str] | None = None):
        self.falhas = falhas or set()
        self.processed: list[str] = []

    def process(self, url, *, source_url):
        self.processed.append(url)
        if url in self.falhas:
            raise PDFProcessingError(f"falha simulada: {url}")
        return _processed(url)


class _FakeCollectorComAnexos:
    """Coletor falso instanciado por ``coletar_fonte`` via REGISTRO_COLETORES."""

    records: tuple[FakeRecord, ...] = ()
    errors: list[CollectionError] = []

    @classmethod
    def com(cls, *records: FakeRecord) -> type:
        namespace = {
            "records": records,
            "errors": [],
            "collect": cls.collect,
            "__init__": cls.__init__,
        }
        return type("FakeCollectorComAnexosFixo", (), namespace)

    def __init__(self, session=None, user_agent=""):
        pass

    def collect(self, listing_url, *, fetch_html=None, max_pages=100, known_canonical_urls=None):
        return list(self.records)


def _ativar_coletor_falso(monkeypatch, records):
    monkeypatch.setattr(
        "newsletter.coleta.REGISTRO_COLETORES",
        {Fonte.Tipo.HTML: _FakeCollectorComAnexos.com(*records)},
    )


@pytest.fixture
def fonte_html(db):
    return Fonte.objects.create(
        nome="Portal Fake",
        tipo=Fonte.Tipo.HTML,
        url="https://www.ufca.edu.br/noticias/",
        intervalo_coleta=60,
    )


@pytest.mark.django_db
def test_anexos_sao_processados_e_persistidos(fonte_html, monkeypatch):
    """CA: PDF referenciado pelo adaptador chega ao Conteudo."""
    _ativar_coletor_falso(monkeypatch, [_record("https://documentos.ufca.edu.br/a.pdf")])
    processor = FakePDFProcessor()

    resultado = coletar_fonte(fonte_html, pdf_processor=processor)

    assert resultado.ok
    assert resultado.criados == 1
    conteudo = Conteudo.objects.get(hash_dedup="hash-com-anexo")
    assert processor.processed == ["https://documentos.ufca.edu.br/a.pdf"]
    assert len(conteudo.anexos) == 1
    anexo = conteudo.anexos[0]
    assert anexo["url"] == "https://documentos.ufca.edu.br/a.pdf"
    assert anexo["file_hash"] == "hash-https://documentos.ufca.edu.br/a.pdf"
    assert anexo["edital_number"] == "12"
    assert anexo["edital_year"] == 2026
    assert anexo["is_rectification"] is False


@pytest.mark.django_db
def test_falha_em_um_anexo_nao_quebra_coleta_nem_outros_anexos(fonte_html, monkeypatch):
    """CA: erro explícito num anexo não interrompe o item nem os demais anexos."""
    _ativar_coletor_falso(
        monkeypatch,
        [
            _record(
                "https://sites.ufca.edu.br/quebrado.pdf",
                "https://documentos.ufca.edu.br/bom.pdf",
            )
        ],
    )
    processor = FakePDFProcessor(falhas={"https://sites.ufca.edu.br/quebrado.pdf"})

    resultado = coletar_fonte(fonte_html, pdf_processor=processor)

    assert resultado.ok
    conteudo = Conteudo.objects.get(hash_dedup="hash-com-anexo")
    assert [a["url"] for a in conteudo.anexos] == [
        "https://documentos.ufca.edu.br/bom.pdf"
    ]
    assert any("quebrado.pdf" in e.url for e in resultado.erros)


@pytest.mark.django_db
def test_conteudo_sem_anexos_tem_lista_vazia(fonte_html, monkeypatch):
    """Default do campo: lista vazia, sem mudança de comportamento atual."""
    _ativar_coletor_falso(monkeypatch, [_record()])
    processor = FakePDFProcessor()

    resultado = coletar_fonte(fonte_html, pdf_processor=processor)

    assert resultado.ok
    conteudo = Conteudo.objects.get(hash_dedup="hash-com-anexo")
    assert conteudo.anexos == []
    assert processor.processed == []
