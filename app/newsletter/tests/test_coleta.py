"""Testes da orquestração de coleta (issue #16)."""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.utils import timezone

from newsletter.coleta import coletar_fonte, fontes_devidas
from newsletter.collectors import CollectionError
from newsletter.models import Conteudo, Fonte

FIXTURES = Path(__file__).parent / "fixtures" / "collectors"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


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


class FakeCollector:
    """Adaptador falso: devolve registros pré-definidos, sem tocar na rede."""

    def __init__(self, session=None, user_agent=""):
        self.errors: list[CollectionError] = []
        self.session = session

    def collect(self, listing_url, *, fetch_html=None, max_pages=100, known_canonical_urls=None):
        return [
            FakeRecord(
                source_url="https://www.ufca.edu.br/noticias/fake/",
                canonical_url="https://www.ufca.edu.br/noticias/fake/",
                title="Conteúdo de teste",
                body="Corpo do conteúdo de teste.",
                published_at=datetime(2026, 8, 1),
                updated_at=None,
                category=None,
                attachment_urls=(),
                content_hash="hash-fixo-de-teste",
            )
        ]


@pytest.fixture
def fonte_html(db):
    return Fonte.objects.create(
        nome="Portal Fake",
        tipo=Fonte.Tipo.HTML,
        url="https://www.ufca.edu.br/noticias/",
        intervalo_coleta=60,
    )


@pytest.mark.django_db
def test_coletar_fonte_cria_conteudo_pendente(fonte_html):
    pages = {
        "https://www.ufca.edu.br/noticias/": fixture("noticias-listing.html"),
        "https://www.ufca.edu.br/noticias/primeira/": fixture("noticias-post.html"),
    }
    resultado = coletar_fonte(fonte_html, fetch_html=pages.__getitem__)

    assert resultado.ok
    assert resultado.criados == 1
    conteudo = Conteudo.objects.get(titulo="Primeira notícia")
    assert conteudo.fonte_id == fonte_html.id
    assert conteudo.status == Conteudo.Status.PENDENTE
    assert conteudo.categoria is None
    assert conteudo.url.endswith("/noticias/primeira/")
    assert conteudo.data_publicacao.date() == datetime(2026, 7, 30).date()


@pytest.mark.django_db
def test_coletar_aprova_o_que_o_classificador_categoriza(fonte_html):
    """Conteúdo classificável entra publicável, sem passar pela fila (ADR-009)."""
    post = fixture("noticias-post.html").replace(
        "Primeira notícia", "Edital de Monitoria 2026.2"
    )
    pages = {
        "https://www.ufca.edu.br/noticias/": fixture("noticias-listing.html"),
        "https://www.ufca.edu.br/noticias/primeira/": post,
    }
    resultado = coletar_fonte(fonte_html, fetch_html=pages.__getitem__)

    assert resultado.criados == 1
    conteudo = Conteudo.objects.get(hash_dedup__isnull=False)
    assert conteudo.categoria is not None
    assert conteudo.categoria.nome == "edital"
    assert conteudo.status == Conteudo.Status.APROVADO


@pytest.mark.django_db
def test_coletar_fonte_deduplica_por_hash(fonte_html):
    pages = {
        "https://www.ufca.edu.br/noticias/": fixture("noticias-listing.html"),
        "https://www.ufca.edu.br/noticias/primeira/": fixture("noticias-post.html"),
    }
    r1 = coletar_fonte(fonte_html, fetch_html=pages.__getitem__)
    r2 = coletar_fonte(fonte_html, fetch_html=pages.__getitem__)

    assert r1.criados == 1
    assert r2.criados == 0
    assert Conteudo.objects.count() == 1


@pytest.mark.django_db
def test_coletar_fonte_cai_em_fallback_quando_sem_data():
    fonte = Fonte.objects.create(
        nome="Sem data",
        tipo=Fonte.Tipo.HTML,
        url="https://www.ufca.edu.br/noticias/",
        intervalo_coleta=60,
    )
    listing = '<html><body><a href="/noticias/segunda/">Segunda</a></body></html>'
    pages = {
        "https://www.ufca.edu.br/noticias/": listing,
        "https://www.ufca.edu.br/noticias/segunda/": fixture("noticias-post-no-date.html"),
    }
    # Post sem data de publicação: deve usar timezone.now() como fallback.
    antes = timezone.now()
    coletar_fonte(fonte, fetch_html=pages.__getitem__)
    conteudo = Conteudo.objects.get(titulo="Segunda notícia")
    assert conteudo.data_publicacao >= antes


@pytest.mark.django_db
def test_fontes_devidas_respeita_intervalo():
    Fonte.objects.create(
        nome="Nunca coletada", tipo=Fonte.Tipo.HTML, url="https://x/noticias/",
        intervalo_coleta=60, ultima_coleta=None,
    )
    Fonte.objects.create(
        nome="Coletada ha pouco", tipo=Fonte.Tipo.HTML, url="https://x/informes/",
        intervalo_coleta=60, ultima_coleta=timezone.now(),
    )
    Fonte.objects.create(
        nome="Inativa", tipo=Fonte.Tipo.HTML, url="https://x/eventos/",
        intervalo_coleta=60, ultima_coleta=None, ativo=False,
    )

    devidas = fontes_devidas()
    nomes = {f.nome for f in devidas}

    assert "Nunca coletada" in nomes
    assert "Coletada ha pouco" not in nomes
    assert "Inativa" not in nomes


@pytest.mark.django_db
def test_coletar_fonte_pula_tipo_sem_coletor():
    fonte_pdf = Fonte.objects.create(
        nome="PDF", tipo=Fonte.Tipo.PDF, url="https://x/editais/", intervalo_coleta=60
    )
    resultado = coletar_fonte(fonte_pdf)

    assert resultado.pulado is True
    assert "sem coletor" in resultado.motivo


@pytest.mark.django_db
def test_comando_coletar_via_call_command_atualiza_ultima_coleta(db, fonte_html):
    with patch.dict(
        "newsletter.coleta.REGISTRO_COLETORES",
        {Fonte.Tipo.HTML: FakeCollector},
    ):
        call_command("coletar", "--todos")

    assert Conteudo.objects.filter(titulo="Conteúdo de teste").exists()
    fonte_html.refresh_from_db()
    assert fonte_html.ultima_coleta is not None


@pytest.mark.django_db
def test_comando_coletar_filtra_por_fonte(db, fonte_html):
    outra = Fonte.objects.create(
        nome="Outra", tipo=Fonte.Tipo.HTML, url="https://x/outra/", intervalo_coleta=60
    )
    with patch.dict(
        "newsletter.coleta.REGISTRO_COLETORES",
        {Fonte.Tipo.HTML: FakeCollector},
    ):
        call_command("coletar", "--fonte", str(fonte_html.id))

    # Só a fonte informada foi coletada (o FakeCollector cria 1 por fonte).
    assert Conteudo.objects.count() == 1
    outra.refresh_from_db()
    assert outra.ultima_coleta is None


@pytest.mark.django_db
def test_coletar_fonte_calendario_persiste_evento(db):
    """Issue #55: Fonte tipo CALENDARIO tem coletor e persiste eventos."""
    from newsletter.collectors import CalendarioCollector

    fonte_cal = Fonte.objects.create(
        nome="Calendário",
        tipo=Fonte.Tipo.CALENDARIO,
        url="https://www.ufca.edu.br/calendario/",
        intervalo_coleta=60,
    )

    class FakeCalendario:
        errors: list[CollectionError] = []

        def collect(self, listing_url, *, fetch_html=None, max_pages=12, known_canonical_urls=None):
            return [
                FakeRecord(
                    source_url="https://www.ufca.edu.br/calendario/evento/",
                    canonical_url="https://www.ufca.edu.br/calendario/evento/",
                    title="Evento de teste",
                    body="Corpo do evento.",
                    published_at=datetime(2026, 8, 1),
                    updated_at=None,
                    category=None,
                    attachment_urls=(),
                    content_hash="hash-evento-calendario",
                )
            ]

    with patch.dict(
        "newsletter.coleta.REGISTRO_COLETORES",
        {Fonte.Tipo.CALENDARIO: CalendarioCollector.__mro__ and FakeCalendario},
    ):
        resultado = coletar_fonte(fonte_cal)

    assert resultado.ok
    assert resultado.criados == 1
    conteudo = Conteudo.objects.get(hash_dedup="hash-evento-calendario")
    assert conteudo.status == Conteudo.Status.PENDENTE


@pytest.mark.django_db
def test_registro_coletores_cobre_calendario():
    """O registro oficial inclui o tipo CALENDARIO (issue #55)."""
    from newsletter.coleta import REGISTRO_COLETORES

    assert Fonte.Tipo.CALENDARIO in REGISTRO_COLETORES
