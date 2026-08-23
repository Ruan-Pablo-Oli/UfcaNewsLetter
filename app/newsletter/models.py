"""Entidades centrais do domínio da UFCA Newsletter."""
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Interesse(models.Model):
    """Tag de interesse que um `Perfil` pode seguir."""

    nome = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Perfil(models.Model):
    """Perfil acadêmico de um usuário do sistema."""

    class Curso(models.TextChoices):
        """Cursos de graduação atualmente oferecidos pela UFCA."""

        ADMINISTRACAO = "administracao", "Administração"
        AGRONOMIA = "agronomia", "Agronomia"
        ARQUITETURA_E_URBANISMO = "arquitetura_e_urbanismo", "Arquitetura e Urbanismo"
        BIOMEDICINA = "biomedicina", "Biomedicina"
        CIENCIA_DA_COMPUTACAO = "ciencia_da_computacao", "Ciência da Computação"
        CIENCIAS_BIOLOGICAS = "ciencias_biologicas", "Ciências Biológicas"
        CIENCIAS_ECONOMICAS = "ciencias_economicas", "Ciências Econômicas"
        DESIGN = "design", "Design"
        DIREITO = "direito", "Direito"
        EDUCACAO_FISICA = "educacao_fisica", "Educação Física"
        ENFERMAGEM = "enfermagem", "Enfermagem"
        ENGENHARIA_CIVIL = "engenharia_civil", "Engenharia Civil"
        ENGENHARIA_DE_PRODUCAO = "engenharia_de_producao", "Engenharia de Produção"
        ENGENHARIA_DE_SOFTWARE = "engenharia_de_software", "Engenharia de Software"
        ENGENHARIA_MECANICA = "engenharia_mecanica", "Engenharia Mecânica"
        ESTATISTICA = "estatistica", "Estatística"
        FARMACIA = "farmacia", "Farmácia"
        FISICA = "fisica", "Física"
        FISIOTERAPIA = "fisioterapia", "Fisioterapia"
        GEOGRAFIA = "geografia", "Geografia"
        HISTORIA = "historia", "História"
        LETRAS = "letras", "Letras"
        MATEMATICA = "matematica", "Matemática"
        MEDICINA = "medicina", "Medicina"
        MEDICINA_VETERINARIA = "medicina_veterinaria", "Medicina Veterinária"
        NUTRICAO = "nutricao", "Nutrição"
        ODONTOLOGIA = "odontologia", "Odontologia"
        PEDAGOGIA = "pedagogia", "Pedagogia"
        PSICOLOGIA = "psicologia", "Psicologia"
        QUIMICA = "quimica", "Química"
        SERVICO_SOCIAL = "servico_social", "Serviço Social"
        SISTEMAS_DE_INFORMACAO = "sistemas_de_informacao", "Sistemas de Informação"
        ZOOTECNIA = "zootecnia", "Zootecnia"

    MIN_INTERESSES = 1
    MAX_INTERESSES = 5

    class FrequenciaEmail(models.TextChoices):
        """Frequência do digest por e-mail (issue #24)."""

        DIARIA = "diaria", "Diária"
        SEMANAL = "semanal", "Semanal"
        DESATIVADO = "desativado", "Desativado"


    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil",
    )
    curso = models.CharField(max_length=150, choices=Curso.choices, blank=True)
    periodo = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(20)],
    )
    interesses = models.ManyToManyField(
        Interesse,
        related_name="perfis",
        blank=True,
    )
    frequencia_email = models.CharField(
        max_length=20,
        choices=FrequenciaEmail.choices,
        default=FrequenciaEmail.DIARIA,
        help_text="Frequência de envio da newsletter por e-mail (issue #24).",
    )

    def __str__(self):
        return f"{self.user} ({self.curso})"


class Categoria(models.Model):
    """Categoria de classificação de um `Conteudo`."""

    class Tipo(models.TextChoices):
        EDITAL = "edital", "Edital"
        COMUNICADO = "comunicado", "Comunicado"
        EVENTO = "evento", "Evento"
        PRAZO = "prazo", "Prazo"

    nome = models.CharField(max_length=20, choices=Tipo.choices, unique=True)

    class Meta:
        ordering = ["nome"]
        verbose_name_plural = "categorias"

    def __str__(self):
        return self.get_nome_display()


class Fonte(models.Model):
    """Origem de onde os conteúdos são coletados."""

    class Tipo(models.TextChoices):
        HTML = "html", "HTML"
        PDF = "pdf", "PDF"
        CALENDARIO = "calendario", "Calendário"
        CONCURSO = "concurso", "Concursos e Seleções"

    nome = models.CharField(max_length=150)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    url = models.URLField()
    intervalo_coleta = models.PositiveIntegerField(
        help_text="Intervalo entre coletas, em minutos.",
    )
    ativo = models.BooleanField(
        default=True,
        help_text="Fontes inativas são ignoradas pelo coletor (US-03.1, issue #16).",
    )
    ultima_coleta = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data/hora da última coleta bem-sucedida. O scheduler compara com "
        "`intervalo_coleta` para decidir se já é hora de coletar de novo.",
    )

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Conteudo(models.Model):
    """Conteúdo coletado de uma `Fonte` e classificado em uma `Categoria`."""

    class Status(models.TextChoices):
        """Fila de revisão manual (US-05.2, issue #27)."""

        PENDENTE = "pendente", "Pendente"
        APROVADO = "aprovado", "Aprovado"
        DESCARTADO = "descartado", "Descartado"

    titulo = models.CharField(max_length=255)
    corpo = models.TextField()
    resumo = models.TextField(blank=True)
    url = models.URLField(
        blank=True,
        default="",
        help_text="Link do conteúdo original na fonte (ex.: página do edital).",
    )
    data_publicacao = models.DateTimeField()
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="conteudos",
        null=True,
        blank=True,
        help_text="Nulo enquanto o conteúdo não é classificado (US-03.2, issue #17).",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
        help_text="Só conteúdo aprovado aparece no feed dos estudantes.",
    )
    gerado_por_ia = models.BooleanField(
        default=False,
        help_text="Indica se o resumo foi gerado por IA (transparência exigida por #18).",
    )
    prazo = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data-limite extraída do conteúdo (ex.: prazo de inscrição), quando houver.",
    )
    publico_alvo = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Público-alvo extraído do conteúdo na sumarização (ex.: 'discentes de "
        "graduação').",
    )
    fonte = models.ForeignKey(
        Fonte,
        on_delete=models.PROTECT,
        related_name="conteudos",
    )
    hash_dedup = models.CharField(
        max_length=64,
        unique=True,
        help_text="Hash usado para deduplicação de conteúdo.",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    universal = models.BooleanField(
        default=False,
        help_text="Se marcado, o conteúdo aparece no feed de todos os perfis "
        "(ex.: avisos institucionais), ignorando curso e interesses.",
    )
    cursos = ArrayField(
        models.CharField(max_length=150, choices=Perfil.Curso.choices),
        blank=True,
        default=list,
        help_text="Cursos aos quais o conteúdo é direcionado. Vazio = nenhum curso específico.",
    )
    interesses = models.ManyToManyField(
        Interesse,
        related_name="conteudos",
        blank=True,
        help_text="Interesses aos quais o conteúdo é direcionado.",
    )

    class Meta:
        ordering = ["-data_publicacao"]

    def __str__(self):
        return self.titulo


class Entrega(models.Model):
    """Registro de entrega de um `Conteudo` a um usuário em um canal."""

    class Canal(models.TextChoices):
        EMAIL = "email", "E-mail"
        PUSH = "push", "Push"
        WHATSAPP = "whatsapp", "WhatsApp"

    conteudo = models.ForeignKey(
        Conteudo,
        on_delete=models.CASCADE,
        related_name="entregas",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="entregas",
    )
    canal = models.CharField(max_length=20, choices=Canal.choices)
    data_envio = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data_envio"]
        unique_together = ("conteudo", "usuario", "canal")

    def __str__(self):
        return f"{self.conteudo} -> {self.usuario} ({self.canal})"


class Feedback(models.Model):
    """Feedback (positivo/negativo) de um usuário sobre um `Conteudo`."""

    class Tipo(models.TextChoices):
        POSITIVO = "positivo", "Positivo"
        NEGATIVO = "negativo", "Negativo"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="feedbacks",
    )
    conteudo = models.ForeignKey(
        Conteudo,
        on_delete=models.CASCADE,
        related_name="feedbacks",
    )
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        unique_together = ("usuario", "conteudo")

    def __str__(self):
        return f"{self.usuario} - {self.conteudo} ({self.tipo})"
