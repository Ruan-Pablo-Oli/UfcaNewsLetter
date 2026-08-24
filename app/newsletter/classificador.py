"""Classificação de conteúdos por categoria e curso/área (US-03.2, issue #17).

Usa regras de palavras-chave (sem IA) para decidir a categoria de um
`Conteudo` coletado: edital, comunicado, evento ou prazo. Quando o texto
menciona um curso/área conhecido, preenche também `Conteudo.cursos`.

Conteúdos sem evidência suficiente ficam com `categoria=None` — é o
comportamento de "fila de revisão manual": o admin lista esses itens e o
revisor atribui a categoria (US-05.2, issue #27).
"""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable

from .models import Categoria, Conteudo, Perfil

# Cada regra é (tipo, lista de padrões). A ordem das regras define a
# prioridade: a primeira regra com pelo menos um padrão presente vence.
# Padrões são casados em texto normalizado (minúsculo, sem acentos).
REGRA_CATEGORIAS: list[tuple[str, list[str]]] = [
    (
        "edital",
        [
            r"\bedital",
            r"concurso\s+p[úu]blico",
            r"processo\s+seletivo",
            r"chamada\s+p[úu]blica",
            r"\bchamada\b",
            r"\bsele[çc][ãa]o\s+de\s+(professor|monitor|estagi|bolsista|discente)",
            r"\bsele[çc][ãa]o\s+aberta",
            r"\bmonitoria",
            r"\bbolsas?\b",
            r"\bvagas?\s+para\s+est[áa]gio",
        ],
    ),
    (
        "prazo",
        [
            r"\bprazo\b",
            r"data\s+limite",
            r"at[eé]\s+o\s+dia",
            r"at[eé]\s+\d{1,2}\s+de",
            r"entre\s+os\s+dias",
            r"trancamento",
            r"entrega\s+do\s+relat[óo]rio",
            r"homologad",
            r"sob\s+pena\s+de\s+suspens[ãa]o",
        ],
    ),
    (
        "evento",
        [
            r"\bsemana\b",
            r"\bsimp[óo]sio",
            r"\bhackathon",
            r"\bmutir[ãa]o",
            r"\bmostra\b",
            r"\bpalestra",
            r"\bsemin[áa]rio",
            r"\bworkshop",
            r"\bcongresso",
            r"\bencontro\b",
            r"\bdefesa\s+de\s+tcc",
            r"\bvisita\s+t[ée]cnica",
            r"\bmesa[-\s]redonda",
            r"\bexposi[çc][ãa]o",
            r"atividades?\s+pr[áa]ticas",
            r"\bcurso\s+de\s+extens[ãa]o",
            r"inscri[çc][õo]es?\s+gratuitas",
        ],
    ),
    (
        "comunicado",
        [
            r"\bcomunicado",
            r"\baviso\b",
            r"\bnota\s+oficial",
            r"\binforme\b",
            r"\bcard[áa]pio",
            r"\bhor[áa]rio\s+reduzido",
            r"\bdivulgad",
            r"\bentra\s+em\s+vigor",
            r"\bcampanha\b",
            r"\brestaurante\s+universit[áa]rio",
        ],
    ),
]

# Mapeia valor do curso (Perfil.Curso) -> padrões de menção no texto.
REGRA_CURSOS: dict[str, list[str]] = {
    Perfil.Curso.ADMINISTRACAO: [r"\badministra[çc][ãa]o\b"],
    Perfil.Curso.AGRONOMIA: [r"\bagronomia\b"],
    Perfil.Curso.ARQUITETURA_E_URBANISMO: [r"arquitetura\s+e\s+urbanismo", r"\barquitetura\b"],
    Perfil.Curso.BIOMEDICINA: [r"\bbiomedicina\b"],
    Perfil.Curso.CIENCIA_DA_COMPUTACAO: [
        r"ci[êe]ncia\s+da\s+computa[çc][ãa]o",
        r"\bcomputa[çc][ãa]o\b",
    ],
    Perfil.Curso.CIENCIAS_BIOLOGICAS: [r"ci[êe]ncias\s+biol[óo]gicas"],
    Perfil.Curso.CIENCIAS_ECONOMICAS: [r"ci[êe]ncias\s+ec[ôo]nomicas", r"\bec[ôo]nomia\b"],
    Perfil.Curso.DESIGN: [r"\bdesign\b"],
    Perfil.Curso.DIREITO: [r"\bdireito\b"],
    Perfil.Curso.EDUCACAO_FISICA: [r"educa[çc][ãa]o\s+f[íi]sica"],
    Perfil.Curso.ENFERMAGEM: [r"\benfermagem\b"],
    Perfil.Curso.ENGENHARIA_CIVIL: [r"engenharia\s+civil"],
    Perfil.Curso.ENGENHARIA_DE_PRODUCAO: [r"engenharia\s+de\s+produ[çc][ãa]o"],
    Perfil.Curso.ENGENHARIA_DE_SOFTWARE: [r"engenharia\s+de\s+software"],
    Perfil.Curso.ENGENHARIA_MECANICA: [r"engenharia\s+mec[âa]nica"],
    Perfil.Curso.ESTATISTICA: [r"\bestat[íi]stica\b"],
    Perfil.Curso.FARMACIA: [r"\bfarm[áa]cia\b"],
    Perfil.Curso.FISICA: [r"\bf[íi]sica\b"],
    Perfil.Curso.FISIOTERAPIA: [r"\bfisioterapia\b"],
    Perfil.Curso.GEOGRAFIA: [r"\bgeografia\b"],
    Perfil.Curso.HISTORIA: [r"\bhist[óo]ria\b"],
    Perfil.Curso.LETRAS: [r"\bletras\b"],
    Perfil.Curso.MATEMATICA: [r"\bmatem[áa]tica\b"],
    Perfil.Curso.MEDICINA: [r"\bmedicina\b"],
    Perfil.Curso.MEDICINA_VETERINARIA: [r"medicina\s+veterin[áa]ria"],
    Perfil.Curso.NUTRICAO: [r"\bnutri[çc][ãa]o\b"],
    Perfil.Curso.ODONTOLOGIA: [r"\bodontologia\b"],
    Perfil.Curso.PEDAGOGIA: [r"\bpedagogia\b"],
    Perfil.Curso.PSICOLOGIA: [r"\bpsicologia\b"],
    Perfil.Curso.QUIMICA: [r"\bqu[íi]mica\b"],
    Perfil.Curso.SERVICO_SOCIAL: [r"servi[çc]o\s+social"],
    Perfil.Curso.SISTEMAS_DE_INFORMACAO: [r"sistemas\s+de\s+informa[çc][ãa]o"],
    Perfil.Curso.ZOOTECNIA: [r"\bzootecnia\b"],
}


def _normalizar(texto: str) -> str:
    """Minúsculas e sem acentos, para casar padrões independente de grafia."""
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(char for char in texto if unicodedata.category(char) != "Mn")
    return texto.lower()


def _categorias(texto_normalizado: str) -> list[str]:
    """Retorna as categorias cujas regras casam no texto, na ordem de prioridade."""
    encontradas = []
    for tipo, padroes in REGRA_CATEGORIAS:
        if any(re.search(padrao, texto_normalizado) for padrao in padroes):
            encontradas.append(tipo)
    return encontradas


def _cursos(texto_normalizado: str) -> list[str]:
    """Retorna os cursos/áreas mencionados no texto, na ordem do dicionário."""
    encontrados = []
    for curso, padroes in REGRA_CURSOS.items():
        if any(re.search(padrao, texto_normalizado) for padrao in padroes):
            encontrados.append(curso)
    return encontrados


def classificar_texto(titulo: str, corpo: str) -> tuple[str | None, list[str]]:
    """Classifica um texto e retorna `(categoria_tipo | None, cursos)`.

    Retorna `categoria_tipo=None` quando nenhuma regra casa — nesse caso o
    conteúdo deve seguir para revisão manual (categoria vazia na fila).
    """
    texto = _normalizar(f"{titulo}\n{corpo}")
    categorias = _categorias(texto)
    tipo = categorias[0] if categorias else None
    return tipo, _cursos(texto)


def classificar_conteudo(conteudo: Conteudo) -> bool:
    """Classifica um `Conteudo` e salva; retorna True se a categoria mudou.

    Não sobrescreve uma categoria já atribuída (manual ou por coleta): o
    classificador só preenche o que está vazio. Cursos são preenchidos apenas
    quando o campo ainda está vazio, preservando direcionamento manual.

    Conteúdo que ganha categoria é **aprovado automaticamente** (ver ADR-009):
    ter casado com uma regra é a evidência que dispensa a revisão humana. O que
    fica sem categoria continua `pendente`, na fila do admin (US-05.2, #27).
    """
    if conteudo.categoria_id is not None:
        return False

    tipo, cursos = classificar_texto(conteudo.titulo, conteudo.corpo)
    alterado = False
    campos = ["categoria", "cursos"]

    if tipo is not None:
        categoria, _ = Categoria.objects.get_or_create(nome=tipo)
        conteudo.categoria = categoria
        alterado = True

        # Só promove o que está esperando decisão: conteúdo já descartado por um
        # revisor não volta ao feed por ter sido reclassificado depois.
        if conteudo.status == Conteudo.Status.PENDENTE:
            conteudo.status = Conteudo.Status.APROVADO
            campos.append("status")

    if cursos and not conteudo.cursos:
        conteudo.cursos = cursos
        alterado = True

    if alterado:
        conteudo.save(update_fields=campos)
    return alterado


def classificar_pendentes(conteudos: Iterable[Conteudo]) -> dict[str, int]:
    """Classifica conteúdos sem categoria e resume o resultado.

    Espera conteúdos **sem categoria** (pendentes de classificação). Itens que
    já têm categoria são pulados sem contar. Retorna `{"classificados": N,
    "fila_revisao": M}` — fila_revisao são os conteúdos que continuam sem
    categoria após a tentativa (sem evidência para nenhuma regra).
    """
    classificados = 0
    fila = 0
    for conteudo in conteudos:
        if conteudo.categoria_id is not None:
            continue
        if classificar_conteudo(conteudo):
            classificados += 1
        else:
            fila += 1
    return {"classificados": classificados, "fila_revisao": fila}
