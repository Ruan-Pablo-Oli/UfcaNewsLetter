"""Testes do adaptador de calendários e eventos (US-03.1.3, issue #55)."""
from datetime import datetime
from pathlib import Path

from newsletter.collectors.calendario import CalendarioCollector

FIXTURES = Path(__file__).parent / "fixtures" / "collectors"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


def test_parse_ics_contrato_real():
    """O ICS real do portal (The Events Calendar) é parseado com campos corretos."""
    ics = fixture("calendario-ics-real.ics")
    collector = CalendarioCollector()

    records = collector.parse_ics(
        ics, "https://www.ufca.edu.br/calendarios/?ical=1"
    )

    assert len(records) == 1
    record = records[0]
    assert "Fórum de Qualidade de Vida" in record.title
    assert record.start == datetime(2026, 8, 12, 14, 30)
    assert record.end == datetime(2026, 8, 12, 17, 0)
    assert record.location and "Campus Crato" in record.location
    assert record.category == "Eventos"
    assert record.canonical_url == (
        "https://www.ufca.edu.br/evento/10o-forum-de-qualidade-de-vida-do-estudante/"
    )
    assert len(record.content_hash) == 64


def test_parse_ics_sem_dtstart_gera_pendencia():
    ics = "\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "BEGIN:VEVENT",
            "UID:1@teste",
            "SUMMARY:Evento sem data",
            "URL:https://www.ufca.edu.br/evento/sem-data/",
            "END:VEVENT",
            "END:VCALENDAR",
        ]
    )
    collector = CalendarioCollector()

    records = collector.parse_ics(ics, "https://www.ufca.edu.br/calendarios/?ical=1")

    assert len(records) == 1
    assert records[0].start is None
    assert records[0].end is None
    assert any("DTSTART" in e.reason for e in collector.errors)


def test_parse_ics_deduplica_por_url_canonica():
    ics = "\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "BEGIN:VEVENT",
            "UID:1@teste",
            "SUMMARY:Evento repetido",
            "URL:https://www.ufca.edu.br/evento/repetido/",
            "DTSTART:20260812T143000",
            "END:VEVENT",
            "BEGIN:VEVENT",
            "UID:2@teste",
            "SUMMARY:Evento repetido",
            "URL:https://www.ufca.edu.br/evento/repetido/",
            "DTSTART:20260812T143000",
            "END:VEVENT",
            "END:VCALENDAR",
        ]
    )
    collector = CalendarioCollector()

    records = collector.parse_ics(ics, "https://www.ufca.edu.br/calendarios/?ical=1")

    assert len(records) == 1


def test_parse_ics_respeita_urls_ja_conhecidas():
    ics = "\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "BEGIN:VEVENT",
            "UID:1@teste",
            "SUMMARY:Evento ja coletado",
            "URL:https://www.ufca.edu.br/evento/ja-coletado/",
            "DTSTART:20260812T143000",
            "END:VEVENT",
            "END:VCALENDAR",
        ]
    )
    collector = CalendarioCollector()

    records = collector.parse_ics(
        ics,
        "https://www.ufca.edu.br/calendarios/?ical=1",
        known_canonical_urls={"https://www.ufca.edu.br/evento/ja-coletado/"},
    )

    assert records == []


def test_parse_ics_ignora_vevent_sem_summary():
    ics = "\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "BEGIN:VEVENT",
            "UID:3@teste",
            "DTSTART:20260812T143000",
            "END:VEVENT",
            "END:VCALENDAR",
        ]
    )
    collector = CalendarioCollector()

    records = collector.parse_ics(ics, "https://www.ufca.edu.br/calendarios/?ical=1")

    assert records == []
    assert any("SUMMARY" in e.reason for e in collector.errors)


def test_parse_event_html_contrato():
    """Fallback HTML: página de evento no formato do The Events Calendar."""
    collector = CalendarioCollector()
    record = collector.parse_event(
        fixture("calendario-evento.html"),
        "https://www.ufca.edu.br/evento/semana-de-engenharia-2026/",
    )

    assert record.title == "Semana de Engenharia 2026"
    assert record.start == datetime(datetime.today().year, 8, 12, 14, 30)
    assert record.end == datetime(datetime.today().year, 8, 12, 17, 0)
    assert record.location and "Campus Juazeiro do Norte" in record.location
    assert record.inscription_url == "https://www.even3.com.br/semana-engenharia-2026/"
    assert record.category == "Eventos"
    assert len(record.content_hash) == 64


def test_parse_event_sem_local():
    html = """<html><body><main>
      <h1>Evento sem local</h1>
      <div class="tribe-events-meta-group tribe-events-meta-group-details">
        <dl>
          <dt>Data:</dt><dd>12 de agosto</dd>
          <dt>Hora:</dt><dd>14h30</dd>
          <dt>Categoria de Evento:</dt><dd>Eventos</dd>
        </dl>
      </div>
    </main></body></html>"""
    collector = CalendarioCollector()
    record = collector.parse_event(
        html, "https://www.ufca.edu.br/evento/sem-local/"
    )

    assert record.location is None
    assert record.inscription_url is None


def test_parse_event_datetime_ambigua_fica_pendente():
    html = """<html><body><main>
      <h1>Evento com data estranha</h1>
      <div class="tribe-events-meta-group tribe-events-meta-group-details">
        <dl>
          <dt>Data:</dt><dd>32 de agosto</dd>
          <dt>Hora:</dt><dd>14h30</dd>
        </dl>
      </div>
    </main></body></html>"""
    collector = CalendarioCollector()
    record = collector.parse_event(
        html, "https://www.ufca.edu.br/evento/data-estranha/"
    )

    assert record.start is None


def test_collect_usa_ics_quando_disponivel():
    """Quando o ICS responde, o HTML não é percorrido."""
    pages = {
        "https://www.ufca.edu.br/calendarios/?ical=1": fixture("calendario-ics-real.ics"),
    }

    collector = CalendarioCollector()
    records = collector.collect(
        "https://www.ufca.edu.br/calendarios/",
        fetch_html=pages.__getitem__,
    )

    assert len(records) == 1
    assert "Fórum" in records[0].title


def test_collect_fallback_html_quando_ics_falha():
    """ICS indisponível: navega a listagem HTML e extrai os eventos."""
    pages = {
        "https://www.ufca.edu.br/calendarios/?ical=1": "<html>erro 500</html>",
        "https://www.ufca.edu.br/calendarios/": fixture("calendario-listing.html"),
        "https://www.ufca.edu.br/evento/semana-de-engenharia-2026/": fixture(
            "calendario-evento.html"
        ),
        "https://www.ufca.edu.br/evento/forum-de-qualidade-de-vida/": (
            "<html><body><main><h1>Fórum de Qualidade de Vida</h1>"
            '<div class="tribe-events-meta-group"><dl><dt>Data:</dt><dd>12 de agosto</dd>'
            "<dt>Hora:</dt><dd>14h30</dd></dl></div></main></body></html>"
        ),
    }

    collector = CalendarioCollector()
    records = collector.collect(
        "https://www.ufca.edu.br/calendarios/",
        fetch_html=pages.__getitem__,
    )

    titulos = {record.title for record in records}
    assert "Semana de Engenharia 2026" in titulos
    assert "Fórum de Qualidade de Vida" in titulos


def test_parse_listing_extrai_eventos_e_proxima_pagina():
    collector = CalendarioCollector()
    urls, next_url = collector.parse_listing(
        fixture("calendario-listing.html"),
        "https://www.ufca.edu.br/calendarios/",
    )

    assert len(urls) == 2
    assert urls[0] == "https://www.ufca.edu.br/evento/semana-de-engenharia-2026/"
    assert next_url == "https://www.ufca.edu.br/calendarios/mes/2026-09/"


def test_parse_listing_ignora_links_fora_de_evento():
    html = """<html><body>
      <a href="/noticias/alguma/">Notícia</a>
      <a href="/evento/real/">Evento real</a>
    </body></html>"""
    collector = CalendarioCollector()
    urls, _ = collector.parse_listing(html, "https://www.ufca.edu.br/calendarios/")

    assert urls == ["https://www.ufca.edu.br/evento/real/"]
