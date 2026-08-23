"""Popula `Fonte` com as categorias de informe de unidades aprovadas (US-03.1.5, #57).

O inventário completo das categorias de informe do portal está em
`docs/fontes-inventario.md` (#77). Só as categorias de valor alto para o público
do produto (graduação, assuntos estudantis, auxílios, estágio, editais,
bolsistas, ensino, extensão, cultura, bibliotecas, acessibilidade e
integralização) viram `Fonte`; as demais (licitações, corregedoria,
gestão-de-pessoas, expediente etc.) ficam de fora por decisão do critério de
aceitação ("o adaptador extrai somente ... o que tenha valor para o público").

Cada categoria usa `tipo=Fonte.Tipo.HTML`: é o que o `NewsInformeCollector`
(`newsletter/collectors/noticias_informes.py`) atende.

Idempotente (usa `get_or_create` por `url`): pode ser executado várias vezes
sem duplicar. Chamado automaticamente na subida dos contêineres (`make up`),
como `seed_interesses`, pois sem essas `Fonte` o coletor (`python manage.py
coletar`) não tem o que varrer num clone novo do repositório.
"""
from django.core.management.base import BaseCommand

from newsletter.models import Fonte

CATEGORIAS_DE_VALOR_ALTO = [
    ("Informes — Graduação", "https://www.ufca.edu.br/noticias/informe_category/graduacao/"),
    (
        "Informes — Assuntos Estudantis",
        "https://www.ufca.edu.br/noticias/informe_category/assuntos-estudantis/",
    ),
    ("Informes — Auxílios", "https://www.ufca.edu.br/noticias/informe_category/auxilios/"),
    ("Informes — Estágio", "https://www.ufca.edu.br/noticias/informe_category/estagio/"),
    ("Informes — Editais", "https://www.ufca.edu.br/noticias/informe_category/editais/"),
    ("Informes — Bolsistas", "https://www.ufca.edu.br/noticias/informe_category/bolsistas/"),
    ("Informes — Ensino", "https://www.ufca.edu.br/noticias/informe_category/ensino/"),
    ("Informes — Extensão", "https://www.ufca.edu.br/noticias/informe_category/extensao/"),
    ("Informes — Cultura", "https://www.ufca.edu.br/noticias/informe_category/cultura/"),
    ("Informes — Bibliotecas", "https://www.ufca.edu.br/noticias/informe_category/bibliotecas/"),
    (
        "Informes — Acessibilidade",
        "https://www.ufca.edu.br/noticias/informe_category/acessibilidade/",
    ),
    (
        "Informes — Integralização",
        "https://www.ufca.edu.br/noticias/informe_category/integralizacao/",
    ),
]

INTERVALO_COLETA_MINUTOS = 60


class Command(BaseCommand):
    help = "Popula Fonte com as categorias de informe de unidades aprovadas (US-03.1.5, #57)."

    def handle(self, *args, **options):
        novas = 0
        for nome, url in CATEGORIAS_DE_VALOR_ALTO:
            _, criada = Fonte.objects.get_or_create(
                url=url,
                defaults={
                    "nome": nome,
                    "tipo": Fonte.Tipo.HTML,
                    "intervalo_coleta": INTERVALO_COLETA_MINUTOS,
                },
            )
            novas += int(criada)

        self.stdout.write(
            self.style.SUCCESS(
                f"Fontes de unidades garantidas: {len(CATEGORIAS_DE_VALOR_ALTO)} ({novas} novas)."
            )
        )
