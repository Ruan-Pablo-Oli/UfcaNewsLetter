"""Testes do classificador por regras (US-03.2, issue #17)."""
import pytest
from django.core.management import call_command

from newsletter.classificador import (
    classificar_conteudo,
    classificar_pendentes,
    classificar_texto,
)
from newsletter.models import Categoria, Conteudo, Fonte


@pytest.fixture
def categoria_edital(db):
    return Categoria.objects.create(nome=Categoria.Tipo.EDITAL)


@pytest.fixture
def fonte(db):
    return Fonte.objects.create(
        nome="Portal Fake",
        tipo=Fonte.Tipo.HTML,
        url="https://www.ufca.edu.br/noticias/",
        intervalo_coleta=60,
    )


def _conteudo(fonte, titulo, corpo=""):
    return Conteudo.objects.create(
        titulo=titulo,
        corpo=corpo or titulo,
        data_publicacao="2026-08-01T10:00:00Z",
        fonte=fonte,
        hash_dedup=f"hash-{titulo}",
        status=Conteudo.Status.PENDENTE,
    )


# --- classificar_texto ------------------------------------------------------


def test_classifica_edital():
    tipo, cursos = classificar_texto(
        "Edital PRAE nº 12/2026 — Auxílio Moradia",
        "Inscrições abertas para o auxílio moradia do semestre 2026.2.",
    )
    assert tipo == Categoria.Tipo.EDITAL
    assert cursos == []


def test_classifica_prazo():
    tipo, _ = classificar_texto(
        "Prazo para entrega do relatório parcial de bolsistas",
        "Bolsistas devem entregar o relatório até o dia 15.",
    )
    assert tipo == Categoria.Tipo.PRAZO


def test_classifica_evento():
    tipo, _ = classificar_texto(
        "Semana Universitária 2026 tem inscrições abertas",
        "Programação com minicursos, palestras e apresentações de trabalhos.",
    )
    assert tipo == Categoria.Tipo.EVENTO


def test_classifica_comunicado():
    tipo, _ = classificar_texto(
        "Restaurante Universitário funcionará em horário reduzido",
        "Por conta da manutenção, o RU servirá apenas almoço nesta quinta.",
    )
    assert tipo == Categoria.Tipo.COMUNICADO


def test_sem_evidencia_retorna_none():
    tipo, cursos = classificar_texto(
        "Reunião ordinária do colegiado", "Pauta será enviada por e-mail."
    )
    assert tipo is None
    assert cursos == []


def test_edital_prevalece_sobre_prazo():
    # "até o dia" casaria prazo, mas a menção a edital tem prioridade.
    tipo, _ = classificar_texto(
        "Edital de Monitoria 2026.2",
        "Inscrições até o dia 30 de agosto pelo SIGAA.",
    )
    assert tipo == Categoria.Tipo.EDITAL


def test_identifica_curso():
    tipo, cursos = classificar_texto(
        "Seleção de monitores para laboratórios de Química",
        "Vagas para discentes de Química e Farmácia.",
    )
    assert tipo == Categoria.Tipo.EDITAL
    assert "quimica" in cursos
    assert "farmacia" in cursos


def test_normaliza_acentos_e_maiusculas():
    tipo, _ = classificar_texto("EDITAL DE ABERTURA Nº 5/2026", "Processo seletivo para bolsas.")
    assert tipo == Categoria.Tipo.EDITAL


# --- classificar_conteudo ---------------------------------------------------


def test_classifica_conteudo_pendente(db, fonte, categoria_edital):
    conteudo = _conteudo(fonte, "Edital de Monitoria 2026.2", "Seleção de monitores para Química.")

    assert classificar_conteudo(conteudo) is True
    conteudo.refresh_from_db()
    assert conteudo.categoria.nome == Categoria.Tipo.EDITAL
    assert conteudo.cursos == ["quimica"]


def test_classifica_cria_categoria_quando_ausente(db, fonte):
    # Banco vazio não tem Categoria cadastrada (só o seed cria); o classificador
    # deve garantir a categoria ao classificar (US-03.2).
    assert Categoria.objects.count() == 0

    conteudo = _conteudo(fonte, "Edital de Monitoria 2026.2", "Seleção de monitores.")

    assert classificar_conteudo(conteudo) is True
    conteudo.refresh_from_db()
    assert conteudo.categoria.nome == Categoria.Tipo.EDITAL
    assert Categoria.objects.count() == 1


def test_nao_sobrescreve_categoria_manual(db, fonte, categoria_edital):
    evento = Categoria.objects.create(nome=Categoria.Tipo.EVENTO)
    conteudo = _conteudo(fonte, "Edital que já foi categorizado")
    conteudo.categoria = evento
    conteudo.save()

    assert classificar_conteudo(conteudo) is False
    conteudo.refresh_from_db()
    assert conteudo.categoria == evento


def test_conteudo_sem_evidencia_fica_na_fila(db, fonte):
    conteudo = _conteudo(fonte, "Reunião ordinária do colegiado")

    assert classificar_conteudo(conteudo) is False
    conteudo.refresh_from_db()
    assert conteudo.categoria is None
    assert conteudo.status == Conteudo.Status.PENDENTE


def test_conteudo_classificado_e_aprovado_automaticamente(db, fonte, categoria_edital):
    conteudo = _conteudo(fonte, "Edital PIBIC 2026", "Bolsas de iniciação científica.")

    assert classificar_conteudo(conteudo) is True
    conteudo.refresh_from_db()
    assert conteudo.categoria == categoria_edital
    assert conteudo.status == Conteudo.Status.APROVADO


def test_conteudo_descartado_nao_volta_ao_feed_ao_ser_classificado(db, fonte, categoria_edital):
    conteudo = _conteudo(fonte, "Edital PIBIC 2026", "Bolsas de iniciação científica.")
    conteudo.status = Conteudo.Status.DESCARTADO
    conteudo.save(update_fields=["status"])

    assert classificar_conteudo(conteudo) is True
    conteudo.refresh_from_db()
    assert conteudo.categoria == categoria_edital
    assert conteudo.status == Conteudo.Status.DESCARTADO


def test_classificar_pendentes_resumo(db, fonte, categoria_edital):
    _conteudo(fonte, "Edital PIBIC 2026/2027", "Bolsas de iniciação científica.")
    _conteudo(fonte, "Reunião ordinária", "Pauta enviada por e-mail.")

    resumo = classificar_pendentes(Conteudo.objects.all())

    assert resumo == {"classificados": 1, "fila_revisao": 1}


def test_classificar_pendentes_ignora_ja_categorizados(db, fonte, categoria_edital):
    # Conteúdo já categorizado não é contado como fila de revisão nem reavaliado.
    conteudo = _conteudo(fonte, "Edital já revisado", "Bolsas de iniciação científica.")
    conteudo.categoria = categoria_edital
    conteudo.save()
    _conteudo(fonte, "Reunião ordinária", "Pauta enviada por e-mail.")

    resumo = classificar_pendentes(Conteudo.objects.all())

    assert resumo == {"classificados": 0, "fila_revisao": 1}


# --- comando ----------------------------------------------------------------


def test_comando_classifica_e_relatorio(db, fonte, categoria_edital, capsys):
    _conteudo(fonte, "Edital PIBIC 2026/2027", "Bolsas de iniciação científica.")
    _conteudo(fonte, "Reunião ordinária", "Pauta enviada por e-mail.")

    call_command("classificar", "--relatorio")

    saida = capsys.readouterr().out
    assert "1 classificado(s), 1 na fila de revisão" in saida
    assert "Edital: 1" in saida
    assert "Sem categoria (fila de revisão): 1" in saida


def test_comando_sem_pendentes(db, capsys):
    call_command("classificar")
    saida = capsys.readouterr().out
    assert "Nenhum conteúdo sem categoria" in saida
