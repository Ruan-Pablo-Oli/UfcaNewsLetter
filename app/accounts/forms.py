"""Formulários de autenticação."""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

INSTITUTIONAL_EMAIL_SUFFIX = "@aluno.ufca.edu.br"


class SignUpForm(UserCreationForm):
    """Cadastro de estudantes com e-mail institucional da UFCA."""

    email = forms.EmailField(
        required=True,
        help_text=f"Use seu e-mail institucional ({INSTITUTIONAL_EMAIL_SUFFIX}).",
    )

    class Meta:
        model = get_user_model()
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if not email.endswith(INSTITUTIONAL_EMAIL_SUFFIX):
            raise ValidationError(
                f"Cadastre-se com seu e-mail institucional ({INSTITUTIONAL_EMAIL_SUFFIX})."
            )
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise ValidationError("Já existe uma conta cadastrada com este e-mail.")
        return email
