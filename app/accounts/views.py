"""Views de cadastro, login/logout e área protegida de exemplo."""
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
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
