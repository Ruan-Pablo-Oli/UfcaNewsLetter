"""Avaliação do classificador contra títulos reais rotulados (US-03.2).

Diferente de `test_classificador.py`, que verifica regras uma a uma, aqui se
mede **acerto agregado**: o conjunto em `fixtures/titulos_rotulados.json` tem
títulos coletados dos portais da UFCA com o rótulo que um humano daria.

Honestidade sobre o número: as regras foram ajustadas olhando para este
conjunto, então 100% aqui **não** é uma estimativa de acurácia em dados novos —
é uma trava de regressão. A validação independente foi rodar as regras sobre os
224 conteúdos coletados e revisar as mudanças (ver ADR-013).
"""
import json
from pathlib import Path

import pytest

from newsletter.classificador import classificar_texto

FIXTURE = Path(__file__).parent / "fixtures" / "titulos_rotulados.json"
AMOSTRAS = json.loads(FIXTURE.read_text(encoding="utf-8"))["amostras"]

# Abaixo disso, alguma regra regrediu.
ACERTO_MINIMO = 0.90


@pytest.mark.parametrize("titulo,esperado", AMOSTRAS)
def test_classifica_titulo_real(titulo, esperado):
    tipo, _ = classificar_texto(titulo, titulo)

    assert tipo == esperado


def test_acerto_agregado_acima_do_minimo():
    acertos = sum(
        1 for titulo, esperado in AMOSTRAS if classificar_texto(titulo, titulo)[0] == esperado
    )
    taxa = acertos / len(AMOSTRAS)

    assert taxa >= ACERTO_MINIMO, f"acerto caiu para {taxa:.0%} ({acertos}/{len(AMOSTRAS)})"


def test_titulo_decide_mesmo_com_corpo_ruidoso():
    """Corpo cheio de avisos não pode derrubar um título inequívoco."""
    corpo = (
        "O restaurante universitário funcionará em horário reduzido. "
        "Comunicado sobre o funcionamento das bibliotecas. Campanha divulgada. "
        "O aviso entra em vigor na próxima semana."
    )

    tipo, _ = classificar_texto("Edital nº 05/2026 — Seleção de bolsistas", corpo)

    assert tipo == "edital"


def test_corpo_decide_quando_o_titulo_nao_diz_nada():
    tipo, _ = classificar_texto(
        "Mistura Cariri", "A palestra acontece no auditório do bloco H."
    )

    assert tipo == "evento"


@pytest.mark.parametrize(
    "titulo",
    [
        # "sexta-feira" fazia qualquer aviso com data virar evento por causa de
        # \bfeira\b; "durante a semana", idem por \bsemana\b.
        "Prae divulga resultado do edital nesta sexta-feira",
        "Atendimento do setor ocorre durante a semana no bloco administrativo",
    ],
)
def test_dia_da_semana_nao_vira_evento(titulo):
    tipo, _ = classificar_texto(titulo, titulo)

    assert tipo != "evento"
