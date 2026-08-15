"""Coleta conteúdos das Fontes ativas e os persiste como ``Conteudo`` (US-03.1, #16).

Uso:
    python manage.py coletar            # só as fontes devidas (respeita o agendamento)
    python manage.py coletar --todos    # varre todas as fontes ativas, ignorando o intervalo
    python manage.py coletar --fonte 3  # força a coleta de uma fonte específica (pode repetir)
    python manage.py coletar --limite-paginas 5

Cada fonte é varrida pelo adaptador correspondente a ``Fonte.tipo`` (ver
``newsletter/coleta.py``) e, ao terminar, tem sua ``ultima_coleta`` atualizada —
é assim que o scheduler decide quando coletar de novo (ADR-008).
"""
from django.core.management.base import BaseCommand, CommandError

from newsletter.coleta import coletar
from newsletter.models import Fonte


class Command(BaseCommand):
    help = "Coleta conteúdos das Fontes ativas e os persiste como Conteudo (US-03.1, issue #16)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fonte",
            type=int,
            action="append",
            metavar="ID",
            help="Coleta apenas a fonte com este ID (pode ser repetido). Ignora o agendamento.",
        )
        parser.add_argument(
            "--todos",
            action="store_true",
            help="Varre todas as fontes ativas, ignorando o intervalo de coleta.",
        )
        parser.add_argument(
            "--limite-paginas",
            type=int,
            default=100,
            help="Limite de páginas de listagem por fonte (padrão: 100).",
        )

    def handle(self, *args, **options):
        fonte_ids = options.get("fonte")
        forcar = options["todos"]
        max_pages = options["limite_paginas"]

        if fonte_ids:
            fontes = list(Fonte.objects.filter(id__in=fonte_ids))
            ausentes = set(fonte_ids) - {fonte.id for fonte in fontes}
            for id_ausente in sorted(ausentes):
                self.stderr.write(
                    self.style.WARNING(f"Fonte id={id_ausente} não encontrada; será ignorada.")
                )
            if not fontes:
                raise CommandError("Nenhuma das fontes informadas existe.")
        else:
            fontes = None

        resultados = coletar(forcar=forcar, max_pages=max_pages, fontes=fontes)

        total_criados = 0
        for resultado in resultados:
            if resultado.pulado:
                self.stdout.write(
                    self.style.WARNING(
                        f"[pulado] {resultado.fonte.nome}: {resultado.motivo}"
                    )
                )
                continue

            total_criados += resultado.criados
            resumo = f"[ok] {resultado.fonte.nome}: {resultado.criados} novo(s) conteúdo(s)"
            if resultado.erros:
                resumo += f" ({len(resultado.erros)} erro(s) de extração)"
            self.stdout.write(self.style.SUCCESS(resumo))
            for erro in resultado.erros:
                self.stderr.write(f"    - {erro.url}: {erro.reason}")

        total_fontes = len([r for r in resultados if not r.pulado])
        self.stdout.write(
            self.style.SUCCESS(
                f"Coleta concluída: {total_criados} conteúdo(s) novo(s) em "
                f"{total_fontes} fonte(s)."
            )
        )
