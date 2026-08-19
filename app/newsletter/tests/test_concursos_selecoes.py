from pathlib import Path

from newsletter.collectors.concursos_selecoes import (
    ConcursosSelecoesCollector,
)

FIXTURES = (
    Path(__file__).parent
    / "fixtures"
    / "concursos"
)


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_extracts_edital():
    collector = ConcursosSelecoesCollector()

    record = collector.parse_item(
        load_fixture("edital.html"),
        "https://www.ufca.edu.br/edital-20-2026/",
        "https://www.ufca.edu.br/concursos/",
    )

    assert record.edital_number == "20"
    assert record.edital_year == 2026
    assert record.attachment_urls == (
        "https://documentos.ufca.edu.br/edital-20-2026.pdf",
    )


def test_detects_rectification():
    collector = ConcursosSelecoesCollector()

    record = collector.parse_item(
        load_fixture("retificacao.html"),
        "https://www.ufca.edu.br/edital-21-2026/",
        "https://www.ufca.edu.br/concursos/",
    )

    assert record.is_rectification is True


def test_item_without_pdf():
    collector = ConcursosSelecoesCollector()

    record = collector.parse_item(
        load_fixture("sem_pdf.html"),
        "https://www.ufca.edu.br/edital-22-2026/",
        "https://www.ufca.edu.br/concursos/",
    )

    assert record.attachment_urls == ()


def test_incomplete_markup_does_not_invent_fields():
    collector = ConcursosSelecoesCollector()

    record = collector.parse_item(
        load_fixture("markup_incompleto.html"),
        "https://www.ufca.edu.br/processo/",
        "https://www.ufca.edu.br/concursos/",
    )

    assert record.edital_number is None
    assert record.edital_year is None
    assert record.organization is None
    assert record.attachment_urls == ()