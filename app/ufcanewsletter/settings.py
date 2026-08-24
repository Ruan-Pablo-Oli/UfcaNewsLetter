"""Django settings for ufcanewsletter project."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Build da SPA (frontend/dist), copiado para cá pela imagem de produção.
# Em desenvolvimento o diretório não existe: o front roda no servidor do Vite.
SPA_DIR = BASE_DIR / "spa"


def _env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _env_list(name, default=""):
    value = os.environ.get(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-change-me-in-production")

DEBUG = _env_bool("DJANGO_DEBUG", False)

ALLOWED_HOSTS = _env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

CSRF_TRUSTED_ORIGINS = _env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000",
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "newsletter",
    "accounts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Serve os estáticos (inclusive os da SPA) sem depender de nginx; precisa
    # vir logo depois do SecurityMiddleware.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ufcanewsletter.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # index.html da SPA é renderizado como template, para o Django poder
        # devolvê-lo em qualquer rota do React Router.
        "DIRS": [SPA_DIR] if SPA_DIR.is_dir() else [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "ufcanewsletter.wsgi.application"
ASGI_APPLICATION = "ufcanewsletter.asgi.application"

# Database
# Configurado via variáveis de ambiente (ver .env.example)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "ufcanewsletter"),
        "USER": os.environ.get("POSTGRES_USER", "ufcanewsletter"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "ufcanewsletter"),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Fortaleza"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [SPA_DIR] if SPA_DIR.is_dir() else []

# Sem manifest: o Vite já versiona os arquivos por hash no nome, então basta a
# compressão do WhiteNoise.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "spa"

# Web Push (VAPID) — notificações push (issue #22, ver .env.example)
# E-mail (digest da US-04.1). O padrão é o backend de console: em
# desenvolvimento o digest é impresso no log do contêiner, sem depender de um
# SMTP e sem risco de disparar e-mail de verdade para estudantes. Produção troca
# DJANGO_EMAIL_BACKEND para o backend SMTP e preenche as credenciais.
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = _env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL", "UFCA Newsletter <noreply@ufca.edu.br>"
)

WEBPUSH_VAPID_PUBLIC_KEY = os.environ.get("WEBPUSH_VAPID_PUBLIC_KEY", "")
WEBPUSH_VAPID_PRIVATE_KEY = os.environ.get("WEBPUSH_VAPID_PRIVATE_KEY", "")
WEBPUSH_VAPID_SUBJECT = os.environ.get("WEBPUSH_VAPID_SUBJECT", "mailto:contato@ufca.edu.br")


# Segurança para produção. Ligadas só fora do DEBUG, e as que dependem de HTTPS
# ficam atrás de DJANGO_SECURE_SSL — assim dá para rodar o modo produção em
# http://localhost sem entrar em laço de redirecionamento.
SECURE_SSL = _env_bool("DJANGO_SECURE_SSL", False)

if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_SAMESITE = "Lax"

    SECURE_SSL_REDIRECT = SECURE_SSL
    SESSION_COOKIE_SECURE = SECURE_SSL
    CSRF_COOKIE_SECURE = SECURE_SSL
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if SECURE_SSL else None
    SECURE_HSTS_SECONDS = 31536000 if SECURE_SSL else 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_SSL
    SECURE_HSTS_PRELOAD = SECURE_SSL
