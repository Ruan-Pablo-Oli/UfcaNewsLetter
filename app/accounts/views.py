"""Views de cadastro, login/logout, perfil acadêmico e área protegida de exemplo."""
import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from newsletter.forms import PerfilForm
from newsletter.models import Interesse, Perfil, PushSubscription

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
            "frequencia_email": perfil.frequencia_email,
            "push_ativo": perfil.push_ativo,
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
        "frequencia_email": perfil.frequencia_email,
        "push_ativo": perfil.push_ativo,
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


@require_http_methods(["GET"])
def api_frequencias_email(request):
    return JsonResponse({
        "frequencias": [
            {"value": f.value, "label": f.label} for f in Perfil.FrequenciaEmail
        ]
    })


@require_http_methods(["GET"])
def api_vapid_public_key(request):
    """Chave pública VAPID, necessária ao navegador como `applicationServerKey`
    de `PushManager.subscribe()` (issue #22). Pública por definição: a chave
    privada nunca sai do servidor (fica só em `WEBPUSH_VAPID_PRIVATE_KEY`).
    """
    return JsonResponse({"public_key": settings.WEBPUSH_VAPID_PUBLIC_KEY})


@login_required
@require_http_methods(["POST", "DELETE"])
def api_push_subscription(request):
    """Registra ou remove uma `PushSubscription` do usuário logado (issue #22).

    Corpo esperado (formato de `PushSubscription.toJSON()` do navegador):
    ``{"endpoint": "...", "keys": {"p256dh": "...", "auth": "..."}}``.
    Em DELETE, apenas ``endpoint`` é necessário.
    """
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON inválido."}, status=400)

    endpoint = data.get("endpoint", "")
    if not endpoint:
        return JsonResponse({"erro": "endpoint é obrigatório."}, status=400)

    if request.method == "DELETE":
        PushSubscription.objects.filter(endpoint=endpoint, usuario=request.user).delete()
        return JsonResponse({"mensagem": "Subscription removida."})

    keys = data.get("keys", {})
    p256dh = keys.get("p256dh", "")
    auth = keys.get("auth", "")
    if not p256dh or not auth:
        return JsonResponse({"erro": "keys.p256dh e keys.auth são obrigatórios."}, status=400)

    PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={"usuario": request.user, "p256dh": p256dh, "auth": auth},
    )
    return JsonResponse({"mensagem": "Subscription registrada."}, status=201)


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
