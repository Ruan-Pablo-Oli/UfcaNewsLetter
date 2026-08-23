"""Formulários relacionados ao perfil acadêmico do estudante."""
from django import forms

from .models import Interesse, Perfil


class PerfilForm(forms.ModelForm):
    """Preenchimento e edição de curso, período e áreas de interesse."""

    curso = forms.ChoiceField(choices=Perfil.Curso.choices, label="Curso")
    interesses = forms.ModelMultipleChoiceField(
        queryset=Interesse.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="Áreas de interesse",
        error_messages={
            "required": f"Selecione ao menos {Perfil.MIN_INTERESSES} área de interesse."
        },
    )
    frequencia_email = forms.ChoiceField(
        choices=Perfil.FrequenciaEmail.choices,
        required=False,
        label="Frequência de e-mail",
    )
    push_ativo = forms.BooleanField(required=False, label="Notificações push")

    class Meta:
        model = Perfil
        fields = ["curso", "periodo", "interesses", "frequencia_email", "push_ativo"]

    def clean_interesses(self):
        interesses = self.cleaned_data["interesses"]
        if len(interesses) > Perfil.MAX_INTERESSES:
            raise forms.ValidationError(
                f"Selecione no máximo {Perfil.MAX_INTERESSES} áreas de interesse."
            )
        return interesses

    def clean_frequencia_email(self):
        # Campo opcional na edição: se o cliente não enviar (ex.: telas que só
        # mexem em curso/interesses), preserva a frequência já configurada.
        return self.cleaned_data.get("frequencia_email") or self.instance.frequencia_email

    def clean_push_ativo(self):
        # BooleanField/checkbox não distingue "desmarcado" de "ausente" nos
        # dados enviados; usamos a presença da chave para decidir: se o
        # cliente não enviou push_ativo (ex.: PATCH parcial de curso/período),
        # preserva o valor já configurado.
        if "push_ativo" not in self.data:
            return self.instance.push_ativo
        return self.cleaned_data.get("push_ativo", False)
