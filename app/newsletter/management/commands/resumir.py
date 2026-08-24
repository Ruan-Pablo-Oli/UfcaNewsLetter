"""Resume conteúdos extensos ainda sem resumo (US-03.3, issue #18).

Uso:
    python manage.py resumir              # resume o que está sem resumo
    python manage.py resumir --relatorio  # imprime a cobertura de resumos

O resumidor é extrativo e determinístico (sem IA, sem rede): seleciona as
sentenças com prazo, público-alvo e palavras-chave. Conteúdo curto não é
resumido — nesse caso as telas mostram o início do corpo
(`resumo_para_exibicao`). Um `summarizer` de LLM pode ser injetado em código,
e aí `gerado_por_ia` fica True.
"""
from django.core.management.base import BaseCommand

from newsletter.models import Conteudo
from newsletter.resumidor import resumir_pendentes


class Command(BaseCommand):
    help = "Resume conteúdos extensos ainda sem resumo (US-03.3, issue #18)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--relatorio",
            action="store_true",
            help="Depois de resumir, imprime a cobertura de resumos.",
        )

    def handle(self, *args, **options):
        alvo = Conteudo.objects.filter(resumo="")
        resumo = resumir_pendentes(alvo.iterator())
        self.stdout.write(
            self.style.SUCCESS(
                f"Resumo concluído: {resumo['resumidos']} resumido(s), "
                f"{resumo['pulados']} pulado(s) (curtos ou já resumidos)."
            )
        )

        if options["relatorio"]:
            total = Conteudo.objects.count()
            com_resumo = Conteudo.objects.exclude(resumo="").count()
            por_ia = Conteudo.objects.filter(gerado_por_ia=True).count()
            cobertura = 100.0 * com_resumo / max(1, total)
            self.stdout.write("--- Relatório de resumos ---")
            self.stdout.write(f"  Com resumo: {com_resumo} de {total} ({cobertura:.1f}%)")
            self.stdout.write(f"  Gerados por IA: {por_ia}")
