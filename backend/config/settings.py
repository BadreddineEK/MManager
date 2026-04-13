"""
Configuration Django — Mosquée Manager
=======================================
Toute la configuration provient des variables d'environnement (.env).
Aucune valeur secrète en dur dans ce fichier.

Lecture : django-environ lit DATABASE_URL, DJANGO_SECRET_KEY, etc.
Local (sans Docker) : copier .env.example → .env à la racine du projet.
Docker : les vars sont injectées via env_file dans docker-compose.yml.
"""
import os
from datetime import timedelta
from pathlib import Path

import environ

# ── Chemins ───────────────────────────────────────────────────────────────────
# BASE_DIR = répertoire backend/ (où se trouve manage.py)
BASE_DIR = Path(__file__).resolve().parent.parent

# ── Initialisation django-environ ─────────────────────────────────────────────
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    TIMEZONE=(str, "Europe/Paris"),
)

# Lecture du fichier .env si présent (dev local sans Docker)
# En Docker, les variables sont injectées directement → le fichier n'est pas monté
_env_file = BASE_DIR.parent / ".env"
if _env_file.exists():
    environ.Env.read_env(str(_env_file), overwrite=False)

# ── Sécurité ──────────────────────────────────────────────────────────────────
SECRET_KEY: str = env("DJANGO_SECRET_KEY")
DEBUG: bool = env("DJANGO_DEBUG")
ALLOWED_HOSTS: list[str] = env("ALLOWED_HOSTS")

# Origines de confiance pour CSRF (Django Admin + Cloudflare Tunnel)
# En dev : vide (DEBUG=True → CSRF moins strict)
# En prod : liste des URLs depuis lesquelles l'app est accédée
_csrf_raw = os.environ.get("CSRF_TRUSTED_ORIGINS", "http://localhost,http://127.0.0.1")
CSRF_TRUSTED_ORIGINS: list[str] = [s.strip() for s in _csrf_raw.split(",") if s.strip()]

# ── Applications installées (multi-tenant) ───────────────────────────────────
# SHARED_APPS : schéma public (partagé entre tous les tenants)
SHARED_APPS = [
    "django_tenants",                             # EN PREMIER obligatoire
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Tiers
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    # Core : Mosque (tenant model), Domain, User, Settings, AuditLog...
    "core.apps.CoreConfig",
]

# TENANT_APPS : schéma isolé par mosquée
TENANT_APPS = [
    "school.apps.SchoolConfig",
    "membership.apps.MembershipConfig",
    "treasury.apps.TreasuryConfig",
    "kpi.apps.KpiConfig",
]

INSTALLED_APPS = list(SHARED_APPS) + TENANT_APPS

# ── Multi-tenant ───────────────────────────────────────────────────────────────
TENANT_MODEL = "core.Mosque"
TENANT_DOMAIN_MODEL = "core.Domain"
DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)
PUBLIC_SCHEMA_URLCONF = "config.urls_public"

# ── Middleware ─────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django_tenants.middleware.main.TenantMainMiddleware",  # EN PREMIER
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # RBAC multi-tenant : doit être après AuthenticationMiddleware
    "core.middleware.MosqueRBACMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "config.wsgi.application"

# ── Base de données ────────────────────────────────────────────────────────────
# Lue depuis DATABASE_URL : postgres://user:pass@host:port/dbname
DATABASES = {
    "default": {
        "ENGINE": "django_tenants.postgresql_backend",
        "NAME": env("POSTGRES_DB"),
        "USER": env("POSTGRES_USER"),
        "PASSWORD": env("POSTGRES_PASSWORD"),
        "HOST": env("POSTGRES_HOST", default="db"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    }
}

# ── Authentification ───────────────────────────────────────────────────────────
# AUTH_USER_MODEL doit être défini avant la première migration
# Le modèle User est dans core/models.py (étendu à l'étape 2 avec mosque + role)
AUTH_USER_MODEL = "core.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── Internationalisation ───────────────────────────────────────────────────────
LANGUAGE_CODE = "fr-fr"
TIME_ZONE: str = env("TIMEZONE")
USE_I18N = True
USE_TZ = True

# ── Fichiers statiques ─────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ── Clé primaire par défaut ────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Django REST Framework ──────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    # API navigable en dev, JSON pur en prod
    "DEFAULT_RENDERER_CLASSES": (
        [
            "rest_framework.renderers.JSONRenderer",
            "rest_framework.renderers.BrowsableAPIRenderer",
        ]
        if DEBUG
        else ["rest_framework.renderers.JSONRenderer"]
    ),
}

# ── JWT (djangorestframework-simplejwt) ───────────────────────────────────────
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),   # Journée de travail
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "UPDATE_LAST_LOGIN": True,
}

# ── CORS ───────────────────────────────────────────────────────────────────────
# En dev : toutes origines autorisées. En prod : lister explicitement.
CORS_ALLOW_ALL_ORIGINS: bool = DEBUG
CORS_ALLOW_CREDENTIALS = True
# En prod (DEBUG=False), définir CORS_ALLOWED_ORIGINS dans .env :
# CORS_ALLOWED_ORIGINS=https://mosque.votredomaine.com
CORS_ALLOWED_ORIGINS: list[str] = env.list("CORS_ALLOWED_ORIGINS", default=[])

# ── Sécurité HTTPS (prod derrière Cloudflare Tunnel) ─────────────────────────
# CSRF_COOKIE_SECURE et SESSION_COOKIE_SECURE nécessitent HTTPS.
# En accès local HTTP (Raspberry Pi LAN), on les désactive.
# Ils seront réactivés automatiquement quand Cloudflare Tunnel (HTTPS) sera configuré.
_https = os.environ.get("HTTPS_ENABLED", "false").lower() == "true"
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = False          # Cloudflare gère le redirect HTTP→HTTPS
    SESSION_COOKIE_SECURE = _https
    CSRF_COOKIE_SECURE = _https

# ── Logging ────────────────────────────────────────────────────────────────────
# Pas de print() en prod — tout passe par le logger standard Django
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} {module} — {message}",
            "style": "{",
        },
        "simple": {
            "format": "[{levelname}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            # Passer à DEBUG pour voir les requêtes SQL (dev uniquement)
            "level": "WARNING",
            "propagate": False,
        },
        "core": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}

