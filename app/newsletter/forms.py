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

    class Meta:
        model = Perfil
        fields = ["curso", "periodo", "interesses"]

    def clean_interesses(self):
        interesses = self.cleaned_data["interesses"]
        if len(interesses) > Perfil.MAX_INTERESSES:
            raise forms.ValidationError(
                f"Selecione no máximo {Perfil.MAX_INTERESSES} áreas de interesse."
            )
        return interesses
