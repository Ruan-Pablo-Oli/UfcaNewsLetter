import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Categoria",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "nome",
                    models.CharField(
                        choices=[
                            ("edital", "Edital"),
                            ("comunicado", "Comunicado"),
                            ("evento", "Evento"),
                            ("prazo", "Prazo"),
                        ],
                        max_length=20,
                        unique=True,
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "categorias",
                "ordering": ["nome"],
            },
        ),
        migrations.CreateModel(
            name="Fonte",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=150)),
                (
                    "tipo",
                    models.CharField(
                        choices=[
                            ("html", "HTML"),
                            ("pdf", "PDF"),
                            ("calendario", "Calendário"),
                        ],
                        max_length=20,
                    ),
                ),
                ("url", models.URLField()),
                (
                    "intervalo_coleta",
                    models.PositiveIntegerField(help_text="Intervalo entre coletas, em minutos."),
                ),
            ],
            options={
                "ordering": ["nome"],
            },
        ),
        migrations.CreateModel(
            name="Interesse",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=100, unique=True)),
            ],
            options={
                "ordering": ["nome"],
            },
        ),
        migrations.CreateModel(
            name="Perfil",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("curso", models.CharField(max_length=150)),
                ("periodo", models.PositiveSmallIntegerField()),
                (
                    "interesses",
                    models.ManyToManyField(blank=True, related_name="perfis", to="newsletter.interesse"),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="perfil",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Conteudo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("titulo", models.CharField(max_length=255)),
                ("corpo", models.TextField()),
                ("resumo", models.TextField(blank=True)),
                ("data_publicacao", models.DateTimeField()),
                (
                    "hash_dedup",
                    models.CharField(
                        help_text="Hash usado para deduplicação de conteúdo.",
                        max_length=64,
                        unique=True,
                    ),
                ),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                (
                    "categoria",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="conteudos",
                        to="newsletter.categoria",
                    ),
                ),
                (
                    "fonte",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="conteudos",
                        to="newsletter.fonte",
                    ),
                ),
            ],
            options={
                "ordering": ["-data_publicacao"],
            },
        ),
        migrations.CreateModel(
            name="Entrega",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "canal",
                    models.CharField(
                        choices=[
                            ("email", "E-mail"),
                            ("push", "Push"),
                            ("whatsapp", "WhatsApp"),
                        ],
                        max_length=20,
                    ),
                ),
                ("data_envio", models.DateTimeField(auto_now_add=True)),
                (
                    "conteudo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entregas",
                        to="newsletter.conteudo",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entregas",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-data_envio"],
                "unique_together": {("conteudo", "usuario", "canal")},
            },
        ),
        migrations.CreateModel(
            name="Feedback",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "tipo",
                    models.CharField(
                        choices=[
                            ("positivo", "Positivo"),
                            ("negativo", "Negativo"),
                        ],
                        max_length=10,
                    ),
                ),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                (
                    "conteudo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="feedbacks",
                        to="newsletter.conteudo",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="feedbacks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-criado_em"],
                "unique_together": {("usuario", "conteudo")},
            },
        ),
    ]
