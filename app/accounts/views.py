"""Views de cadastro, login/logout, perfil acadêmico e área protegida de exemplo."""
import json

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from newsletter.forms import PerfilForm
from newsletter.models import Interesse, Perfil

from .forms import SignUpForm


@ensure_csrf_cookie
@require_http_methods(["GET"])
def api_csrf(request):
    return JsonResponse({"mensagem": "CSRF cookie set."})

@ensure_csrf_cookie
@require_http_methods(["POST"])
def api_login(request):
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        data = request.POST
    username = data.get("username", "")
    password = data.get("password", "")
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return JsonResponse({"username": user.username, "email": user.email})
    return JsonResponse({"erro": "Usuário ou senha inválidos."}, status=400)


@require_http_methods(["POST"])
def api_logout(request):
    logout(request)
    return JsonResponse({"mensagem": "Sessão encerrada."})


@require_http_methods(["GET"])
def api_me(request):
    if request.user.is_authenticated:
        return JsonResponse({"username": request.user.username, "email": request.user.email})
    return JsonResponse({"erro": "Não autenticado."}, status=401)


@require_http_methods(["POST"])
def api_signup(request):
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON inválido."}, status=400)

    form = SignUpForm(data)
    if not form.is_valid():
        erros = {}
        for field, msgs in form.errors.items():
            erros[field] = msgs[0] if isinstance(msgs, list) else msgs
        return JsonResponse({"erro": erros}, status=400)

    user = form.save()
    Perfil.objects.get_or_create(user=user, defaults={"curso": "", "periodo": 1})
    login(request, user)
    return JsonResponse({"username": user.username, "email": user.email}, status=201)


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
@require_http_methods(["GET", "PATCH"])
def api_perfil(request):
    perfil, _ = Perfil.objects.get_or_create(
        user=request.user, defaults={"curso": "", "periodo": 1}
    )

    if request.method == "GET":
        return JsonResponse({
            "curso": perfil.curso,
            "periodo": perfil.periodo,
            "interesses": list(perfil.interesses.values_list("id", flat=True)),
        })

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON inválido."}, status=400)

    form = PerfilForm(data, instance=perfil)
    if not form.is_valid():
        erros = {}
        for field, msgs in form.errors.items():
            erros[field] = msgs[0] if isinstance(msgs, list) else msgs
        return JsonResponse({"erro": erros}, status=400)

    form.save()
    return JsonResponse({
        "curso": perfil.curso,
        "periodo": perfil.periodo,
        "interesses": list(perfil.interesses.values_list("id", flat=True)),
    })


@require_http_methods(["GET"])
def api_cursos(request):
    return JsonResponse({
        "cursos": [{"value": c.value, "label": c.label} for c in Perfil.Curso]
    })


@require_http_methods(["GET"])
def api_interesses(request):
    interesses = Interesse.objects.all().values("id", "nome")
    return JsonResponse({"interesses": list(interesses)})


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
