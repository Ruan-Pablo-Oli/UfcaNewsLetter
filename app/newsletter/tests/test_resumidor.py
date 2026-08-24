"""Resumidor de conteúdo extenso (issue #18, opção extrativa + LLM injetável)."""
from datetime import datetime
from unittest.mock import patch

import pytest

from newsletter.models import Conteudo, Fonte
from newsletter.resumidor import (
    Resumo,
    extrair_prazo,
    extrair_publico_alvo,
    resumir_conteudo,
    resumir_extrativo,
    resumir_pendentes,
    resumo_para_exibicao,
)

TEXTO_LONGO = (
    "A Universidade Federal do Cariri torna pública a abertura de inscrições "
    "para o processo seletivo de monitoria do curso de Engenharia de Software. "
) * 30 + (
    "As inscrições vão até 30/09/2026 e são destinadas a discentes de graduação "
    "regularmente matriculados. O candidato deve entregar o histórico escolar na "
    "secretaria do curso. Mais informações pelo edital disponível no site."
)


@pytest.fixture
def fonte(db):
    return Fonte.objects.create(
        nome="Portal", tipo=Fonte.Tipo.HTML, url="https://x/", intervalo_coleta=60
    )


@pytest.fixture
def conteudo_longo(fonte):
    return Conteudo.objects.create(
        titulo="Edital de monitoria",
        corpo=TEXTO_LONGO,
        data_publicacao=datetime(2026, 8, 1),
        fonte=fonte,
        hash_dedup="hash-longo",
    )


def _palavras(texto: str) -> int:
    return len(texto.split())


# --- funções puras ---


_EDITAL_LONGO = (
    "A Pró-Reitoria de Assuntos Estudantis torna pública a seleção. "
    "As inscrições são destinadas a discentes de graduação em situação de "
    "vulnerabilidade socioeconômica. As inscrições vão até 30/09/2026. "
) + ("Item do edital sobre documentação, prazos e critérios de avaliação. " * 90)


def test_resumo_nao_gerado_para_texto_curto():
    assert resumir_extrativo("Título", "Corpo curto.") is None


def test_resumo_extrativo_e_menor_que_original():
    r = resumir_extrativo("Edital", TEXTO_LONGO)
    assert r is not None
    assert isinstance(r, Resumo)
    assert _palavras(r.texto) < _palavras(TEXTO_LONGO)
    assert _palavras(r.texto) <= 120  # resumo curto


def test_resumo_destaca_sentencas_com_prazo():
    r = resumir_extrativo("Edital", TEXTO_LONGO)
    assert "30/09/2026" in r.texto


def test_extrair_prazo_encontra_data_limite():
    prazo = extrair_prazo("As inscrições vão até 30/09/2026.")
    assert prazo is not None
    assert (prazo.day, prazo.month, prazo.year) == (30, 9, 2026)


def test_extrair_prazo_sem_data_retorna_none():
    assert extrair_prazo("Não há data aqui.") is None


def test_extrair_publico_alvo():
    assert extrair_publico_alvo("destinadas a discentes de graduação") is not None


def test_extrair_publico_alvo_ausente():
    assert extrair_publico_alvo("sem público definido") is None


# --- integração com o modelo ---


@pytest.mark.django_db
def test_conteudo_longo_ganha_resumo(conteudo_longo):
    alterado = resumir_conteudo(conteudo_longo)
    conteudo_longo.refresh_from_db()

    assert alterado
    assert conteudo_longo.resumo
    assert conteudo_longo.prazo is not None
    assert conteudo_longo.publico_alvo
    # Extrativo puro NÃO é gerado por IA (transparência).
    assert conteudo_longo.gerado_por_ia is False


@pytest.mark.django_db
def test_conteudo_curto_nao_e_resumido(fonte):
    c = Conteudo.objects.create(
        titulo="Aviso",
        corpo="Corpo curto.",
        data_publicacao=datetime(2026, 8, 1),
        fonte=fonte,
        hash_dedup="hash-curto",
    )
    assert resumir_conteudo(c) is False
    c.refresh_from_db()
    assert c.resumo == ""


@pytest.mark.django_db
def test_cache_nao_reprocessa_resumido(conteudo_longo):
    resumir_conteudo(conteudo_longo)
    with patch("newsletter.resumidor.resumir_extrativo") as mock:
        resumir_conteudo(conteudo_longo)
    mock.assert_not_called()


@pytest.mark.django_db
def test_summarizer_llm_injetavel_marca_gerado_por_ia(conteudo_longo):
    """Opção 3: summarizer injetável; quando usado, gerado_por_ia=True."""

    def fake_llm(titulo: str, corpo: str) -> str:
        return "Resumo feito por LLM."

    resumir_conteudo(conteudo_longo, summarizer=fake_llm)
    conteudo_longo.refresh_from_db()

    assert conteudo_longo.resumo == "Resumo feito por LLM."
    assert conteudo_longo.gerado_por_ia is True
    # prazo/público-alvo continuam extraídos deterministicamente.
    assert conteudo_longo.prazo is not None


@pytest.mark.django_db
def test_resumir_pendentes_processa_apenas_longos_sem_resumo(fonte):
    longo = Conteudo.objects.create(
        titulo="Longo",
        corpo=TEXTO_LONGO,
        data_publicacao=datetime(2026, 8, 1),
        fonte=fonte,
        hash_dedup="hash-p-longo",
    )
    curto = Conteudo.objects.create(
        titulo="Curto",
        corpo="Breve.",
        data_publicacao=datetime(2026, 8, 1),
        fonte=fonte,
        hash_dedup="hash-p-curto",
    )
    resultado = resumir_pendentes(Conteudo.objects.all())

    assert resultado["resumidos"] == 1
    assert resultado["pulados"] >= 1
    longo.refresh_from_db()
    curto.refresh_from_db()
    assert longo.resumo
    assert curto.resumo == ""


# --- texto dos anexos e fallback de exibição (ADR-012) ----------------------


@pytest.mark.django_db
def test_resume_usando_o_texto_do_anexo_quando_o_corpo_e_curto(fonte):
    """Informe curto apontando para um edital longo em PDF."""
    conteudo = Conteudo.objects.create(
        titulo="Publicado edital de auxílio",
        corpo="A Prae publicou o edital. Veja o documento anexo.",
        data_publicacao="2026-08-01T10:00:00Z",
        fonte=fonte,
        hash_dedup="hash-anexo-longo",
        anexos=[{"url": "https://documentos.ufca.edu.br/e.pdf", "text": _EDITAL_LONGO}],
    )

    assert resumir_conteudo(conteudo) is True
    conteudo.refresh_from_db()
    assert conteudo.resumo
    assert conteudo.gerado_por_ia is False
    # O prazo estava só no PDF.
    assert conteudo.prazo is not None


@pytest.mark.django_db
def test_conteudo_curto_sem_anexo_continua_sem_resumo(fonte):
    conteudo = Conteudo.objects.create(
        titulo="Aviso rápido",
        corpo="Curto demais para resumir.",
        data_publicacao="2026-08-01T10:00:00Z",
        fonte=fonte,
        hash_dedup="hash-curto-sem-anexo",
    )

    assert resumir_conteudo(conteudo) is False
    assert conteudo.resumo == ""


@pytest.mark.django_db
def test_exibicao_cai_no_inicio_do_corpo_quando_nao_ha_resumo(fonte):
    corpo = "Primeira frase do informe. " * 30
    conteudo = Conteudo.objects.create(
        titulo="Sem resumo",
        corpo=corpo,
        data_publicacao="2026-08-01T10:00:00Z",
        fonte=fonte,
        hash_dedup="hash-exibicao",
    )

    texto = resumo_para_exibicao(conteudo)

    assert texto.endswith("…")
    assert len(texto) <= 201
    assert texto.startswith("Primeira frase")


@pytest.mark.django_db
def test_exibicao_prefere_o_resumo_quando_existe(fonte):
    conteudo = Conteudo.objects.create(
        titulo="Com resumo",
        corpo="Corpo longo que não deve aparecer. " * 20,
        resumo="Resumo curado.",
        data_publicacao="2026-08-01T10:00:00Z",
        fonte=fonte,
        hash_dedup="hash-exibicao-2",
    )

    assert resumo_para_exibicao(conteudo) == "Resumo curado."
