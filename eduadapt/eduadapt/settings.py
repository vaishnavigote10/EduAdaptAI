import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
ON_RENDER = bool(os.getenv("RENDER"))
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-secret")
DEBUG = os.getenv("DJANGO_DEBUG", "0" if ON_RENDER else "1") == "1"
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
CSRF_TRUSTED_ORIGINS = []
_host = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if _host:
    ALLOWED_HOSTS.append(_host)
    CSRF_TRUSTED_ORIGINS.append("https://" + _host)
for _extra in filter(None, os.getenv("EXTRA_HOSTS", "").split(",")):  # custom domains, comma separated
    ALLOWED_HOSTS.append(_extra.strip()); CSRF_TRUSTED_ORIGINS.append("https://" + _extra.strip())
if ON_RENDER:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = True

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "core",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
ROOT_URLCONF = "eduadapt.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "core.context.team",
    ]},
}]
WSGI_APPLICATION = "eduadapt.wsgi.application"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
if os.getenv("DATABASE_URL"):  # Render Postgres
    import dj_database_url
    DATABASES["default"] = dj_database_url.parse(os.environ["DATABASE_URL"], conn_max_age=600)

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"}}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
DATA_UPLOAD_MAX_MEMORY_SIZE = 200 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

LOGIN_URL = "/login"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14

# People credited in the app (login page, sidebar and the Team page). Edit names and roles here.
TEAM = [
    {"name": "Vaishnavi", "role": "Contributor"},
    {"name": "Zainab", "role": "Contributor"},
    {"name": "Mrunal", "role": "Contributor"},
]
