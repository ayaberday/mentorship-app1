from pathlib import Path
import os
from dotenv import load_dotenv
import dj_database_url

# --- Configuration Email (SMTP) ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'votre_email@gmail.com')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', 'votre_mot_de_passe')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

BASE_DIR = Path(__file__).resolve().parent.parent

# charger .env en local
load_dotenv()

# --- Base de données ---
DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL')
    )
}
DEBUG = os.getenv("DEBUG", "True") == "True"

SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-key-change-me")

def _split_env(name):
    raw = os.getenv(name, "")
    return [x.strip() for x in raw.split(",") if x.strip()]

ALLOWED_HOSTS = ["mentorship-app1.onrender.com"]
CSRF_TRUSTED_ORIGINS = ["https://mentorship-app1.onrender.com"]


# --- Applications ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
]

# --- Templates ---
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

AUTH_USER_MODEL = 'accounts.User'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGIN_URL = '/login/'

# --- Middleware (WhiteNoise) ---
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # <— ajouté
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

WSGI_APPLICATION = 'config.wsgi.application'

# (Optionnel) vous pouvez ajuster conn_max_age/ssl_require via les env vars si nécessaire

# --- Static (WhiteNoise) ---
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / 'static',  # Dossier static à la racine du projet
]

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    }
}

# --- Internationalisation ---
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Casablanca'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- HTTPS derrière le proxy de Render ---
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
