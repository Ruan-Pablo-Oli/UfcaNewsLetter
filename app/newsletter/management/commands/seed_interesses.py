"""Popula a tabela Interesse com um conjunto inicial de áreas de interesse.

Idempotente (usa get_or_create): pode ser executado várias vezes sem duplicar.
É chamado automaticamente na subida dos contêineres (`make up`) para que a tela
de perfil (`/accounts/perfil/`) já tenha opções para o estudante escolher.
"""
from django.core.management.base import BaseCommand

from newsletter.models import Interesse

INTERESSES_INICIAIS = [
    "Editais",
    "Bolsas",
    "Estágios",
    "Eventos",
    "Monitoria",
    "Iniciação Científica",
    "Extensão",
    "Restaurante Universitário",
    "Calendário Acadêmico",
    "Concursos e Seleções",
]


class Command(BaseCommand):
    help = "Popula a tabela Interesse com um conjunto inicial de áreas de interesse."

    def handle(self, *args, **options):
        novos = 0
        for nome in INTERESSES_INICIAIS:
            _, criado = Interesse.objects.get_or_create(nome=nome)
            novos += int(criado)
        self.stdout.write(
            self.style.SUCCESS(
                f"Interesses garantidos: {len(INTERESSES_INICIAIS)} ({novos} novos)."
            )
        )
