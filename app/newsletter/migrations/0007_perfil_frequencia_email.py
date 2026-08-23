"""Adiciona FrequenciaEmail ao Perfil (issue #24)."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("newsletter", "0005_tipo_fonte_concurso"),
    ]

    operations = [
        migrations.AddField(
            model_name="perfil",
            name="frequencia_email",
            field=models.CharField(
                choices=[("diaria", "Diária"), ("semanal", "Semanal"), ("desativado", "Desativado")],
                default="diaria",
                help_text="Frequência de envio da newsletter por e-mail (issue #24).",
                max_length=20,
            ),
        ),
    ]
