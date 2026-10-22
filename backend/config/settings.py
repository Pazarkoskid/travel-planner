"""Django settings for AI Travel Planner Macedonia.

Сите тајни и конфигурации се читаат од environment variables.
Без POSTGRES_DB се користи SQLite за брз локален развој и тестови.
"""
import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def load_dotenv():
    """Чита KEY=VALUE од .env (во root на проектот или во backend/), без надворешна библиотека.

    Вредностите од вистинскиот environment имаат предност.
    """
    for path in (BASE_DIR.parent / ".env", BASE_DIR / ".env"):
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8-sig").splitlines():  # utf-8-sig: Notepad BOM
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip().strip('"').strip("'")
            if value:
                os.environ.setdefault(key.strip(), value)


load_dotenv()


def env_bool(name, default=False):
    return os.environ.get(name, "1" if default else "0").lower() in ("1", "true", "yes")


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,backend").split(",") if h.strip()]
# Render го поставува RENDER_EXTERNAL_HOSTNAME (пр. travel-backend.onrender.com).
if os.environ.get("RENDER_EXTERNAL_HOSTNAME"):
    ALLOWED_HOSTS.append(os.environ["RENDER_EXTERNAL_HOSTNAME"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "storages",
    "corsheaders",
    "core",
    "accounts",
    "destinations",
    "businesses",
    "reservations",
    "reviews",
    "trips",
    "gamification",
    "notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

if os.environ.get("DATABASE_URL"):
    # Supabase / Render / било кој PostgreSQL преку еден connection string.
    import dj_database_url

    _db = dj_database_url.parse(os.environ["DATABASE_URL"], conn_max_age=600, conn_health_checks=True,
                                ssl_require=env_bool("DATABASE_SSL", True))
    if _db.get("PORT") in (6543, "6543"):
        # Supabase transaction pooler (Supavisor :6543): без серверски курсори и без трајни конекции.
        _db["DISABLE_SERVER_SIDE_CURSORS"] = True
        _db["CONN_MAX_AGE"] = 0
    DATABASES = {"default": _db}
elif os.environ.get("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["POSTGRES_DB"],
            "USER": os.environ.get("POSTGRES_USER", "postgres"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            "ATOMIC_REQUESTS": False,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "mk"
TIME_ZONE = "Europe/Skopje"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media"))
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Статични фајлови (Django admin) ги служи WhiteNoise — без посебен сервер.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
                    if not DEBUG else "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Медиуми (фото-посети, аватари) во Supabase Storage преку S3 API.
# Render (free) нема траен диск — без ова качените фотографии се губат при секој deploy.
SUPABASE_S3_ENDPOINT = os.environ.get("SUPABASE_S3_ENDPOINT", "")  # https://<ref>.storage.supabase.co/storage/v1/s3
if SUPABASE_S3_ENDPOINT:
    # boto3 >= 1.36 праќа нови checksum заглавја кои S3-компатибилните сервиси не секогаш ги примаат.
    os.environ.setdefault("AWS_REQUEST_CHECKSUM_CALCULATION", "when_required")
    os.environ.setdefault("AWS_RESPONSE_CHECKSUM_VALIDATION", "when_required")
    _bucket = os.environ.get("SUPABASE_S3_BUCKET", "media")
    _ref = os.environ.get("SUPABASE_PROJECT_REF") or SUPABASE_S3_ENDPOINT.split("//", 1)[-1].split(".", 1)[0]
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "endpoint_url": SUPABASE_S3_ENDPOINT,
            "region_name": os.environ.get("SUPABASE_S3_REGION", "eu-central-1"),
            "access_key": os.environ.get("SUPABASE_S3_ACCESS_KEY_ID", ""),
            "secret_key": os.environ.get("SUPABASE_S3_SECRET_ACCESS_KEY", ""),
            "bucket_name": _bucket,
            "addressing_style": "path",
            "signature_version": "s3v4",
            "default_acl": None,
            "file_overwrite": False,
            "querystring_auth": False,
            # Јавен bucket → трајни јавни URL-и без потпис.
            "custom_domain": f"{_ref}.supabase.co/storage/v1/object/public/{_bucket}",
        },
    }

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework_simplejwt.authentication.JWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticatedOrReadOnly",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "EXCEPTION_HANDLER": "core.exceptions.api_exception_handler",
    # ?format= го користиме за извоз (csv), не за избор на renderer.
    "URL_FORMAT_OVERRIDE": None,
    "DEFAULT_RENDERER_CLASSES": ("core.renderers.LangJSONRenderer", "rest_framework.renderers.BrowsableAPIRenderer"),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.environ.get("THROTTLE_ANON", "300/hour"),
        "user": os.environ.get("THROTTLE_USER", "3000/hour"),
        "login": os.environ.get("THROTTLE_LOGIN", "20/minute"),
        "ai_generate": os.environ.get("THROTTLE_AI", "30/hour"),
        "uploads": os.environ.get("THROTTLE_UPLOADS", "60/hour"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.environ.get("JWT_ACCESS_MINUTES", "30"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
}

CORS_ALLOWED_ORIGINS = [o.strip().rstrip("/") for o in
                        os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip().rstrip("/") for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]
if os.environ.get("RENDER_EXTERNAL_HOSTNAME"):
    CSRF_TRUSTED_ORIGINS.append(f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}")

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- AI ---------------------------------------------------------------
# LLM_PROVIDER: "none" (правила + OR-Tools) или "anthropic".
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "none")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-5-5")
LLM_TIMEOUT_SECONDS = int(os.environ.get("LLM_TIMEOUT_SECONDS", "25"))

# --- Рутирање ---------------------------------------------------------
# ROUTING_PROVIDER: "haversine" (без надворешен сервис) или "osrm".
ROUTING_PROVIDER = os.environ.get("ROUTING_PROVIDER", "haversine")
OSRM_URL = os.environ.get("OSRM_URL", "https://router.project-osrm.org")
ROUTING_TIMEOUT_SECONDS = int(os.environ.get("ROUTING_TIMEOUT_SECONDS", "8"))

# --- Временска прогноза (OpenWeather) ---------------------------------
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")
WEATHER_CACHE_SECONDS = int(os.environ.get("WEATHER_CACHE_SECONDS", "1800"))
WEATHER_TIMEOUT_SECONDS = int(os.environ.get("WEATHER_TIMEOUT_SECONDS", "8"))

# --- Гејмификација ----------------------------------------------------
CHECKIN_DEFAULT_RADIUS_M = int(os.environ.get("CHECKIN_DEFAULT_RADIUS_M", "300"))
MACEDONIA_EXPLORER_MIN_CITIES = int(os.environ.get("MACEDONIA_EXPLORER_MIN_CITIES", "3"))
MAX_PHOTO_BYTES = int(os.environ.get("MAX_PHOTO_BYTES", str(8 * 1024 * 1024)))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}
