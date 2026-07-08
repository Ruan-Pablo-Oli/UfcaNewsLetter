"""Views de cadastro, login/logout, perfil acadêmico e área protegida de exemplo."""
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from newsletter.forms import PerfilForm
from newsletter.models import Perfil

from .forms import SignUpForm


def signup(request):
    """Cadastra um novo estudante e cria seu `Perfil` vazio automaticamente."""
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            Perfil.objects.get_or_create(user=user, defaults={"curso": "", "periodo": 1})
            login(request, user)
            return redirect("dashboard")
    else:
        form = SignUpForm()
    return render(request, "accounts/signup.html", {"form": form})


@login_required
def dashboard(request):
    """Rota protegida de exemplo, usada para validar autenticação/autorização."""
    perfil, _ = Perfil.objects.get_or_create(
        user=request.user, defaults={"curso": "", "periodo": 1}
    )
    papel = "administrador" if request.user.is_staff else "estudante"
    return render(request, "accounts/dashboard.html", {"perfil": perfil, "papel": papel})


@login_required
def perfil_editar(request):
    """Preenchimento e edição do perfil acadêmico (curso, período e interesses)."""
    perfil, _ = Perfil.objects.get_or_create(
        user=request.user, defaults={"curso": "", "periodo": 1}
    )
    if request.method == "POST":
        form = PerfilForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil atualizado com sucesso.")
            return redirect("perfil_editar")
    else:
        form = PerfilForm(instance=perfil)
    return render(request, "accounts/perfil_form.html", {"form": form})
