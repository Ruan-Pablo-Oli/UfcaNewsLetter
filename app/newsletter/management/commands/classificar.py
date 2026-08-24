"""Classifica conteúdos sem categoria (US-03.2, issue #17).

Uso:
    python manage.py classificar                 # classifica conteúdos sem categoria
    python manage.py classificar --relatorio     # imprime métricas de cobertura
    python manage.py classificar --todos         # aceito por simetria com o coletor;
                                                 # o classificador sempre processa
                                                 # conteúdos sem categoria

O classificador é por regras (sem IA): decide a categoria a partir de
palavras-chave no título/corpo e preenche `Conteudo.cursos` quando identifica
curso/área. Conteúdos sem evidência permanecem sem categoria — ficam na fila
de revisão manual do admin (US-05.2, issue #27).
"""
from django.core.management.base import BaseCommand

from newsletter.classificador import classificar_pendentes, direcionar_conteudo
from newsletter.models import Categoria, Conteudo


class Command(BaseCommand):
    help = "Classifica conteúdos sem categoria por regras de palavras-chave (US-03.2, issue #17)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--todos",
            action="store_true",
            help=(
                "Processa todos os conteúdos sem categoria (padrão) — flag aceita "
                "por simetria com o coletor."
            ),
        )
        parser.add_argument(
            "--redirecionar",
            action="store_true",
            help=(
                "Reaplica o direcionamento (curso, interesses, universal) a TODO o "
                "conteúdo, inclusive o já classificado. Use para o backfill de "
                "conteúdo coletado antes das regras de direcionamento existirem."
            ),
        )
        parser.add_argument(
            "--relatorio",
            action="store_true",
            help="Após classificar, imprime métricas de cobertura por categoria e fila de revisão.",
        )

    def handle(self, *args, **options):
        if options["redirecionar"]:
            self._redirecionar()

        alvo = Conteudo.objects.filter(categoria__isnull=True)
        total = alvo.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS("Nenhum conteúdo sem categoria para classificar."))
            if options["relatorio"]:
                self._relatorio()
            return

        resumo = classificar_pendentes(alvo.iterator())
        self.stdout.write(
            self.style.SUCCESS(
                f"Classificação concluída: {resumo['classificados']} classificado(s), "
                f"{resumo['fila_revisao']} na fila de revisão (sem evidência)."
            )
        )

        if options["relatorio"]:
            self._relatorio()

    def _redirecionar(self):
        """Backfill: aplica direcionar_conteudo ao conteúdo já classificado."""
        alterados = 0
        total = 0
        for conteudo in Conteudo.objects.all().iterator():
            total += 1
            if direcionar_conteudo(conteudo):
                alterados += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Direcionamento reaplicado: {alterados} de {total} conteúdo(s) alterado(s)."
            )
        )

    def _relatorio(self):
        self.stdout.write("--- Relatório de classificação ---")
        for categoria in Categoria.objects.order_by("nome"):
            total = Conteudo.objects.filter(categoria=categoria).count()
            self.stdout.write(f"  {categoria.get_nome_display()}: {total}")
        sem_categoria = Conteudo.objects.filter(categoria__isnull=True).count()
        com_categoria = Conteudo.objects.exclude(categoria__isnull=True).count()
        cobertura = 100.0 * com_categoria / max(1, com_categoria + sem_categoria)
        self.stdout.write(f"  Sem categoria (fila de revisão): {sem_categoria}")
        self.stdout.write(f"  Cobertura: {cobertura:.1f}%")
