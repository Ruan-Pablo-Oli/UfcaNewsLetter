from datetime import datetime
from pathlib import Path

import pytest

from newsletter.collectors.noticias_informes import NewsInformeCollector

FIXTURES = Path(__file__).parent / "fixtures" / "collectors"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


def test_parse_post_extracts_contract_fields():
    record = NewsInformeCollector().parse_post(
        fixture("noticias-post.html"),
        "https://www.ufca.edu.br/noticias/primeira/",
    )

    assert record.source_url == "https://www.ufca.edu.br/noticias/primeira/"
    assert record.canonical_url == "https://www.ufca.edu.br/noticias/primeira/"
    assert record.title == "Primeira notícia"
    assert record.body == "Corpo principal da notícia.\nSegundo parágrafo."
    assert record.published_at == datetime(2026, 7, 30)
    assert record.updated_at == datetime(2026, 7, 31)
    assert record.category == "Ensino"
    assert record.attachment_urls == ("https://documentos.ufca.edu.br/edital.pdf",)
    assert len(record.content_hash) == 64


def test_collect_follows_next_page_and_deduplicates_records():
    pages = {
        "https://www.ufca.edu.br/noticias/": fixture("noticias-listing.html"),
        "https://www.ufca.edu.br/noticias/page/2/": fixture("noticias-page-2.html"),
        "https://www.ufca.edu.br/noticias/primeira/": fixture("noticias-post.html"),
        "https://www.ufca.edu.br/noticias/segunda/": fixture("noticias-post-no-date.html"),
    }

    collector = NewsInformeCollector()
    records = collector.collect(
        "https://www.ufca.edu.br/noticias/",
        fetch_html=pages.__getitem__,
    )

    assert [record.title for record in records] == ["Primeira notícia", "Segunda notícia"]
    assert records[1].published_at is None
    assert len({record.content_hash for record in records}) == 2


def test_collect_reports_article_error_and_keeps_other_records():
    pages = {
        "https://www.ufca.edu.br/noticias/": fixture("noticias-listing-with-invalid.html"),
        "https://www.ufca.edu.br/noticias/primeira/": "<html><body><h1></h1></body></html>",
        "https://www.ufca.edu.br/noticias/segunda/": fixture("noticias-post-no-date.html"),
    }

    collector = NewsInformeCollector()
    records = collector.collect(
        "https://www.ufca.edu.br/noticias/",
        fetch_html=pages.__getitem__,
    )

    assert [record.title for record in records] == ["Segunda notícia"]
    assert len(collector.errors) == 1
    assert collector.errors[0].url.endswith("/primeira/")
    assert "titulo ausente" in collector.errors[0].reason


def test_collect_skips_known_canonical_urls():
    pages = {
        "https://www.ufca.edu.br/informes/": fixture("informes-listing.html"),
        "https://www.ufca.edu.br/informes/aviso/": fixture("informes-post.html"),
    }
    known = {"https://www.ufca.edu.br/informes/aviso/"}

    records = NewsInformeCollector().collect(
        "https://www.ufca.edu.br/informes/",
        fetch_html=pages.__getitem__,
        known_canonical_urls=known,
    )

    assert records == []


def test_collect_reports_listing_error_without_losing_previous_records():
    def fetch(url: str) -> str:
        if url == "https://www.ufca.edu.br/noticias/page/2/":
            raise RuntimeError("timeout da listagem")
        return (
            fixture("noticias-listing.html")
            if url.endswith("/noticias/")
            else fixture("noticias-post.html")
        )

    collector = NewsInformeCollector()
    records = collector.collect(
        "https://www.ufca.edu.br/noticias/",
        fetch_html=fetch,
    )

    assert [record.title for record in records] == ["Primeira notícia"]
    assert len(collector.errors) == 1
    assert collector.errors[0].url.endswith("/page/2/")
    assert collector.errors[0].reason == "timeout da listagem"


def test_parse_informes_fixture():
    records = NewsInformeCollector().collect(
        "https://www.ufca.edu.br/informes/",
        fetch_html={
            "https://www.ufca.edu.br/informes/": fixture("informes-listing.html"),
            "https://www.ufca.edu.br/informes/aviso/": fixture("informes-post.html"),
        }.__getitem__,
    )

    assert [record.title for record in records] == ["Aviso importante"]


def test_parse_post_rejects_missing_title():
    with pytest.raises(ValueError, match="titulo"):
        NewsInformeCollector().parse_post(
            "<html><body><div class='entry-content'><p>Texto</p></div></body></html>",
            "https://www.ufca.edu.br/noticias/sem-titulo/",
        )


def test_parse_listing_extracts_informe_category_items_outside_listing_prefix():
    article_urls, _ = NewsInformeCollector().parse_listing(
        fixture("informe-category-listing.html"),
        "https://www.ufca.edu.br/noticias/informe_category/graduacao/",
    )

    assert article_urls == ["https://www.ufca.edu.br/informes/matriculas-2026-2/"]


def test_collect_informe_category_extracts_items_under_informes_prefix():
    pages = {
        "https://www.ufca.edu.br/noticias/informe_category/graduacao/": fixture(
            "informe-category-listing.html"
        ),
        "https://www.ufca.edu.br/informes/matriculas-2026-2/": fixture(
            "informe-category-post.html"
        ),
    }

    records = NewsInformeCollector().collect(
        "https://www.ufca.edu.br/noticias/informe_category/graduacao/",
        fetch_html=pages.__getitem__,
    )

    assert [record.title for record in records] == ["Matrículas 2026.2"]
    assert records[0].canonical_url == "https://www.ufca.edu.br/informes/matriculas-2026-2/"


def test_collect_informe_category_skips_item_already_known_from_other_source():
    pages = {
        "https://www.ufca.edu.br/noticias/informe_category/graduacao/": fixture(
            "informe-category-listing.html"
        ),
    }
    known = {"https://www.ufca.edu.br/informes/matriculas-2026-2/"}

    records = NewsInformeCollector().collect(
        "https://www.ufca.edu.br/noticias/informe_category/graduacao/",
        fetch_html=pages.__getitem__,
        known_canonical_urls=known,
    )

    assert records == []
