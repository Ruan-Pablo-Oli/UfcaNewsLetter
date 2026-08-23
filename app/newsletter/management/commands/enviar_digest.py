"""Envia digests por e-mail (issue #24). Uso: python manage.py enviar_digest."""
from django.core.management.base import BaseCommand

from newsletter.digest import enviar_digests


class Command(BaseCommand):
    help = "Monta e envia os digests por e-mail dos perfis elegíveis (issue #24)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra quantos perfis receberiam e-mail, sem enviar.",
        )

    def handle(self, *args, **options):
        if options["dry_run"]:
            from newsletter.digest import montar_digest_perfil
            from newsletter.models import Perfil

            elegiveis = 0
            for perfil in Perfil.objects.select_related("user").all():
                if montar_digest_perfil(perfil):
                    elegiveis += 1
            self.stdout.write(f"{elegiveis} perfil(is) receberiam digest.")
            return

        enviados = enviar_digests()
        self.stdout.write(f"{enviados} digest(s) enviado(s).")
