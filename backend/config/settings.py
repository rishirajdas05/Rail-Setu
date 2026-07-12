"""
Django settings for the railway platform.

Uses SQLite by default so you can load data and develop immediately.
Switch DATABASES to PostgreSQL when you are ready (block included below,
commented out).
"""

import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Load a local .env file if python-dotenv is installed (handy for secrets/keys).
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

# For local development only. ALWAYS set DJANGO_SECRET_KEY in the environment for anything real.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "dev-insecure-key-change-me-before-deploying"
)
# Safe default: DEBUG is OFF unless DJANGO_DEBUG=1 (set it in your local .env).
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
# Full origins (e.g. https://your-app.onrender.com) for CSRF on HTTPS deploys.
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

# Render provides the external hostname at runtime; trust it automatically.
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS.append("https://" + RENDER_EXTERNAL_HOSTNAME)


def _with_scheme(url):
    """Render's fromService host values arrive without a scheme; add https://."""
    if url and not url.startswith(("http://", "https://")):
        return "https://" + url
    return url

# Allow the Google Sign-In popup to talk back to the page.
# Django defaults this to "same-origin", which blocks the GSI popup and makes
# sign-in hang at accounts.google.com/gsi/transform.
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin-allow-popups"

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

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR.parent / "frontend"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database: Render (and most hosts) provide DATABASE_URL for Postgres.
# Locally, with no DATABASE_URL set, this falls back to zero-setup SQLite.
# conn_max_age=0: required for the Supabase transaction/session pooler so Django
# does not hold pooled connections open across requests.
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL:
    import dj_database_url

    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=0, ssl_require=True)
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# PostgreSQL (manual): uncomment and set DB_* if you prefer explicit config over DATABASE_URL.
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.postgresql",
#         "NAME": os.environ.get("DB_NAME", "railway"),
#         "USER": os.environ.get("DB_USER", "postgres"),
#         "PASSWORD": os.environ.get("DB_PASSWORD", ""),
#         "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
#         "PORT": os.environ.get("DB_PORT", "5432"),
#     }
# }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR.parent / "frontend"]
STATIC_ROOT = BASE_DIR / "staticfiles"  # target for `collectstatic` on deploy
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# WhiteNoise serves static files in production. Use the compressed (non-manifest)
# backend so plain "/static/js/app.js?v=N" URLs keep resolving (the pages don't
# use {% static %} hashed names).
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    # Endpoints are public by default; protect individual views with
    # permission_classes = [IsAuthenticated] where needed (e.g. bookings).
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

# ---- Live data provider (third-party). Leave LIVE_API_KEY empty to disable. ----
LIVE_API_KEY = os.environ.get("LIVE_API_KEY", "")
# Set LIVE_API_HOST only for RapidAPI-style providers (enables header auth).
LIVE_API_HOST = os.environ.get("LIVE_API_HOST", "indian-railway-irctc.p.rapidapi.com")
# Extra provider header, "Name: Value". Empty to disable.
LIVE_API_EXTRA_HEADER = os.environ.get("LIVE_API_EXTRA_HEADER", "x-rapid-api: rapid-api-database")
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

# Standalone FastAPI ML service (waitlist confirmation predictor).
ML_SERVICE_URL = _with_scheme(os.environ.get("ML_SERVICE_URL", "http://127.0.0.1:8001"))

# Google Sign-In: paste your OAuth client ID here or in .env to enable it.
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
# Optional explicit callback; if blank it is built from the request host.
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "")

# Groq LLM for the RAG chatbot (key in .env). Empty disables the assistant.
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
# Base URL the chatbot uses to call RailSetu's own public APIs for live data.
SELF_BASE_URL = _with_scheme(os.environ.get("SELF_BASE_URL", "http://127.0.0.1:8000"))


# --- Email (booking & cancellation notifications) ---
# Dev default prints emails to the console. To send real email, set
# EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend and the SMTP values in .env.
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "1") == "1"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "RailSetu <no-reply@railsetu.local>")


# ============================================================
#  Production hardening (active only when DEBUG is off)
#  Local dev (DJANGO_DEBUG=1) is unaffected by everything below.
# ============================================================
if not DEBUG:
    # Refuse to boot in production with the throwaway dev key.
    if SECRET_KEY == "dev-insecure-key-change-me-before-deploying":
        raise RuntimeError(
            "DJANGO_SECRET_KEY is not set. Generate one and set it in the environment "
            "before running with DEBUG off."
        )
    # Send cookies and traffic over HTTPS only.
    SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SSL_REDIRECT", "1") == "1"
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Trust the platform's HTTPS proxy header (Render/Heroku/Railway etc.).
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    # HSTS: tell browsers to stick to HTTPS.
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True