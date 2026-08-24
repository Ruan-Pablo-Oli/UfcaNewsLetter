"""URL configuration for ufcanewsletter project."""
from django.contrib import admin
from django.urls import include, path, re_path

from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("newsletter.urls")),
    # Curinga da SPA: precisa ser o último, e não pode engolir as rotas acima
    # nem os estáticos servidos pelo WhiteNoise.
    re_path(
        r"^(?!admin/|accounts/|feed/|feedback/|busca/|historico/|fontes/|revisao/|static/).*$",
        views.spa,
        name="spa",
    ),
]
