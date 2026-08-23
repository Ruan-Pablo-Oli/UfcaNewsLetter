"""Envia notificações push (issue #22). Uso: python manage.py notificar_push."""
from django.core.management.base import BaseCommand

from newsletter.push import enviar_notificacoes_push


class Command(BaseCommand):
    help = "Envia notificações push aos perfis elegíveis com conteúdo novo (issue #22)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra quantos perfis receberiam push, sem enviar.",
        )

    def handle(self, *args, **options):
        if options["dry_run"]:
            from newsletter.models import Perfil
            from newsletter.push import montar_notificacoes_perfil

            elegiveis = 0
            for perfil in Perfil.objects.filter(push_ativo=True).select_related("user"):
                if montar_notificacoes_perfil(perfil):
                    elegiveis += 1
            self.stdout.write(f"{elegiveis} perfil(is) receberiam push.")
            return

        enviados = enviar_notificacoes_push()
        self.stdout.write(f"{enviados} notificacao(oes) push enviada(s).")
