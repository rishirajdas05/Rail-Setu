"""
Django settings for the RailSetu railway platform.

Render-ready settings:
- Uses SQLite locally if DATABASE_URL is not set.
- Uses PostgreSQL automatically on Render through DATABASE_URL.
- Uses WhiteNoise for static files.
- DEBUG is off by default.
"""

import os
from datetime import timedelta
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# Load local .env file for development
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass


# ============================================================
# Core security settings
# ============================================================

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "dev-insecure-key-change-me-before-deploying",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get(
        "DJANGO_ALLOWED_HOSTS",
        "localhost,127.0.0.1",
    ).split(",")
    if h.strip()
]

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if o.strip()
]

# Render automatically provides this env variable
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")


# Allow Google Sign-In popup to communicate back
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin-allow-popups"


# ============================================================
# Installed apps
# ============================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",

    "apps.accounts",
    "apps.stations",
    "apps.trains",
    "apps.booking",
    "apps.search",
    "apps.chat",
    "apps.saved",
    "apps.alerts",
    "apps.analytics",
    "apps.history",
]


# ============================================================
# Middleware
# ============================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # Required for serving static files on Render
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ============================================================
# URLs / WSGI / ASGI
# ============================================================

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# ============================================================
# Templates
# ============================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",

        # Your frontend folder is outside backend/
        "DIRS": [BASE_DIR.parent / "frontend"],

        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]


# ============================================================
# Database
# ============================================================

# Local:
#   Uses backend/db.sqlite3 automatically.
#
# Render:
#   Uses PostgreSQL automatically when DATABASE_URL is present.

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}


# ============================================================
# Password validation
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# ============================================================
# Internationalization
# ============================================================

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"

USE_I18N = True
USE_TZ = True


# ============================================================
# Static files
# ============================================================

STATIC_URL = "/static/"

# Your frontend files are served by Django
STATICFILES_DIRS = [
    BASE_DIR.parent / "frontend",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


# ============================================================
# Primary key field type
# ============================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ============================================================
# Django REST Framework
# ============================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],

    # Public by default; protect specific views manually
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],

    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}


# ============================================================
# JWT settings
# ============================================================

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}


# ============================================================
# Live railway data provider
# ============================================================

LIVE_API_KEY = os.environ.get("LIVE_API_KEY", "")

LIVE_API_HOST = os.environ.get(
    "LIVE_API_HOST",
    "indian-railway-irctc.p.rapidapi.com",
)

LIVE_API_EXTRA_HEADER = os.environ.get(
    "LIVE_API_EXTRA_HEADER",
    "x-rapid-api: rapid-api-database",
)

LIVE_API_TIMEOUT = int(os.environ.get("LIVE_API_TIMEOUT", "8"))

LIVE_RUNNING_STATUS_URL = os.environ.get(
    "LIVE_RUNNING_STATUS_URL",
    "https://indian-railway-irctc.p.rapidapi.com/api/trains/v1/train/status"
    "?departure_date={departure_date}&isH5=true&client=web"
    "&deviceIdentifier=Mozilla%20Firefox-138.0.0.0&train_number={train}",
)

LIVE_PNR_STATUS_URL = os.environ.get(
    "LIVE_PNR_STATUS_URL",
    "https://indianrailapi.com/api/v2/PNRCheck/apikey/{key}/PNRNumber/{pnr}/",
)


# ============================================================
# ML service
# ============================================================

# Local default:
#   http://127.0.0.1:8001
#
# Render:
#   Set ML_SERVICE_URL to your deployed FastAPI ML service URL.

ML_SERVICE_URL = os.environ.get("ML_SERVICE_URL", "http://127.0.0.1:8001")


# ============================================================
# Google Sign-In
# ============================================================

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

# Optional explicit callback.
# If blank, your code can build it from the request host.
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "")


# ============================================================
# Groq chatbot / translation
# ============================================================

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

# Base URL used by chatbot to call RailSetu's own APIs
SELF_BASE_URL = os.environ.get("SELF_BASE_URL", "http://127.0.0.1:8000")


# ============================================================
# Email
# ============================================================

EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)

EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "1") == "1"

DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL",
    "RailSetu <no-reply@railsetu.local>",
)


# ============================================================
# Production hardening
# ============================================================

if not DEBUG:
    if SECRET_KEY == "dev-insecure-key-change-me-before-deploying":
        raise RuntimeError(
            "DJANGO_SECRET_KEY is not set. Generate one and set it in the environment "
            "before running with DEBUG off."
        )

    # Render uses HTTPS proxy
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

    # Redirect HTTP to HTTPS
    SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SSL_REDIRECT", "1") == "1"

    # Secure cookies
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # HSTS
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Browser security
    SECURE_CONTENT_TYPE_NOSNIFF = True