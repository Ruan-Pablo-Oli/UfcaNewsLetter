"""URL configuration for the accounts app."""
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("api/csrf/", views.api_csrf, name="api_csrf"),
    path("api/login/", views.api_login, name="api_login"),
    path("api/logout/", views.api_logout, name="api_logout"),
    path("api/me/", views.api_me, name="api_me"),
    path("api/signup/", views.api_signup, name="api_signup"),
    path("api/perfil/", views.api_perfil, name="api_perfil"),
    path("api/cursos/", views.api_cursos, name="api_cursos"),
    path("api/interesses/", views.api_interesses, name="api_interesses"),
    path("signup/", views.signup, name="signup"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("perfil/", views.perfil_editar, name="perfil_editar"),
]
