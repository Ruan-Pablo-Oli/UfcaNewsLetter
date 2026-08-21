from pathlib import Path

import pytest

from newsletter.collectors.concursos_selecoes import ConcursosSelecoesCollector

FIXTURES = Path(__file__).parent / "fixtures" / "concursos"

LISTING_URL = "https://www.ufca.edu.br/admissao/concursos-e-selecoes/docentes/efetivo/"
EDITAL_URL = LISTING_URL + "edital-20-2026/"
RETIFICACAO_URL = LISTING_URL + "retificacao-1-edital-20-2026/"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def collector() -> ConcursosSelecoesCollector:
    return ConcursosSelecoesCollector()


def test_extracts_edital(collector):
    record = collector.parse_item(load_fixture("edital.html"), EDITAL_URL, LISTING_URL)

    assert record.edital_number == "20"
    assert record.edital_year == 2026
    assert record.organization == "PROGEP"
    assert record.published_at.strftime("%d/%m/%Y") == "13/04/2026"
    assert record.updated_at.strftime("%d/%m/%Y") == "07/08/2026"
    assert record.body


def test_extracts_edital_number_with_ordinal_abbreviation(collector):
    # "Edital nº 20/2026" é a grafia usada nos editais reais; o padrão antigo
    # exigia o número colado em "Edital" e devolvia (None, None) aqui.
    for title in ("Edital nº 20/2026", "EDITAL N° 20/2026", "Edital N. 20/2026",
                  "Edital 20/2026"):
        assert collector._extract_edital_fields(title, "") == ("20", 2026)


def test_attachments_are_pdfs_from_the_post_body_only(collector):
    record = collector.parse_item(load_fixture("edital.html"), EDITAL_URL, LISTING_URL)

    # O link do menu e o da sidebar ficam de fora; o mesmo PDF com fragmento
    # (#page=3) não vira um segundo anexo.
    assert record.attachment_urls == (
        "https://documentos.ufca.edu.br/edital-20-2026.pdf",
    )


def test_html_link_is_not_stored_as_attachment(collector):
    record = collector.parse_item(load_fixture("sem_pdf.html"), LISTING_URL + "edital-22-2026/",
                                  LISTING_URL)

    assert record.attachment_urls == ()


def test_detects_rectification_and_links_the_original(collector):
    record = collector.parse_item(
        load_fixture("retificacao.html"), RETIFICACAO_URL, LISTING_URL
    )

    assert record.is_rectification is True
    assert record.related_url == EDITAL_URL
    # A retificação herda a identificação do edital que ela altera.
    assert (record.edital_number, record.edital_year) == ("20", 2026)


def test_original_edital_linking_its_errata_is_not_a_rectification(collector):
    # O edital original quase sempre linka a própria errata. Marcá-lo como
    # retificação invertia a relação (o original virava retificação de si mesmo).
    record = collector.parse_item(
        load_fixture("edital_com_errata.html"), LISTING_URL + "edital-21-2026/", LISTING_URL
    )

    assert record.is_rectification is False
    assert record.related_url is None


def test_incomplete_markup_does_not_invent_fields(collector):
    record = collector.parse_item(
        load_fixture("markup_incompleto.html"), LISTING_URL + "processo/", LISTING_URL
    )

    assert record.edital_number is None
    assert record.edital_year is None
    assert record.organization is None
    assert record.attachment_urls == ()
    assert record.is_rectification is False


def test_hash_ignores_update_date_and_attachments(collector):
    # Reprocessamento é idempotente: nem um bump de "Atualizado em" nem uma
    # errata anexada depois podem virar um `Conteudo` duplicado na dedup por
    # hash (`Conteudo.hash_dedup`).
    html = load_fixture("edital.html")
    reeditado = html.replace(
        "Atualizado em 07/08/2026", "Atualizado em 09/08/2026"
    ).replace(
        "</main>",
        '<a href="https://documentos.ufca.edu.br/retificacao-1.pdf">Retificação</a></main>',
    )

    original = collector.parse_item(html, EDITAL_URL, LISTING_URL)
    reprocessed = collector.parse_item(reeditado, EDITAL_URL, LISTING_URL)

    assert original.updated_at != reprocessed.updated_at
    assert original.attachment_urls != reprocessed.attachment_urls
    assert original.content_hash == reprocessed.content_hash


def test_parse_listing_keeps_scope_and_finds_next_page(collector):
    item_urls, next_url = collector.parse_listing(load_fixture("listagem.html"), LISTING_URL)

    assert item_urls == [
        EDITAL_URL,
        LISTING_URL + "processo-seletivo-05-2026/",
    ]
    assert next_url == LISTING_URL + "page/2/"


PROCESSO_URL = LISTING_URL + "processo-seletivo-05-2026/"
EMPTY_PAGE = "<html><body><main class='entry-content'></main></body></html>"


def _fetcher(pages: dict[str, str], fetched: list[str] | None = None):
    def fetch(url: str) -> str:
        if fetched is not None:
            fetched.append(url)
        try:
            return pages[url]
        except KeyError:
            raise ValueError(f"404 em {url}")

    return fetch


def test_collect_records_item_errors_and_continues(collector):
    pages = {
        LISTING_URL: load_fixture("listagem.html"),
        EDITAL_URL: load_fixture("edital.html"),
        LISTING_URL + "page/2/": EMPTY_PAGE,
    }

    records = collector.collect(LISTING_URL, fetch_html=_fetcher(pages))

    # Um item quebrado não descarta os demais: o edital 20/2026 é coletado e a
    # falha do processo seletivo fica registrada em `errors`.
    assert [record.canonical_url for record in records] == [EDITAL_URL]
    assert [error.url for error in collector.errors] == [PROCESSO_URL]


def test_collect_skips_known_urls(collector):
    pages = {
        LISTING_URL: load_fixture("listagem.html"),
        EDITAL_URL: load_fixture("edital.html"),
        PROCESSO_URL: load_fixture("sem_pdf.html"),
        LISTING_URL + "page/2/": EMPTY_PAGE,
    }

    records = collector.collect(
        LISTING_URL, fetch_html=_fetcher(pages), known_canonical_urls={EDITAL_URL}
    )

    assert [record.canonical_url for record in records] == [PROCESSO_URL]
    assert collector.errors == []


def test_collect_respects_max_pages(collector):
    fetched: list[str] = []
    pages = {
        LISTING_URL: load_fixture("listagem.html"),
        EDITAL_URL: load_fixture("edital.html"),
        PROCESSO_URL: load_fixture("sem_pdf.html"),
        LISTING_URL + "page/2/": load_fixture("listagem.html"),
    }

    collector.collect(LISTING_URL, fetch_html=_fetcher(pages, fetched), max_pages=1)

    assert LISTING_URL + "page/2/" not in fetched
