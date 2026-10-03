from pathlib import Path
import os
from urllib.parse import parse_qs, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-evrpv9*y^lx!)+yetc53p3znfh%#6ri-h6t)0ykb1al_4g(2f$'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False' if os.environ.get('VERCEL') else 'True').lower() == 'true'

ALLOWED_HOSTS = [
    'smart-budgett-ai.vercel.app',
    '.vercel.app',
    'localhost',
    '127.0.0.1',
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'users',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://([a-z0-9-]+\.)*vercel\.app$",
]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [
    "https://*.vercel.app",
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

WSGI_APPLICATION = 'core.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

database_url = os.environ.get('DATABASE_URL')
if database_url:
    parsed_database_url = urlparse(database_url)
    if parsed_database_url.scheme not in {'postgres', 'postgresql'}:
        raise ImproperlyConfigured('DATABASE_URL must use the postgres:// or postgresql:// scheme.')

    database_options = {}
    query_options = parse_qs(parsed_database_url.query)
    ssl_modes = query_options.get('sslmode')
    if ssl_modes:
        database_options['sslmode'] = ssl_modes[-1]
    elif os.environ.get('VERCEL'):
        database_options['sslmode'] = 'require'

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': unquote(parsed_database_url.path.lstrip('/')),
            'USER': unquote(parsed_database_url.username or ''),
            'PASSWORD': unquote(parsed_database_url.password or ''),
            'HOST': parsed_database_url.hostname or '',
            'PORT': parsed_database_url.port or '',
            'OPTIONS': database_options,
            'CONN_MAX_AGE': 0,
        }
    }
elif os.environ.get('VERCEL'):
    raise ImproperlyConfigured(
        'DATABASE_URL must be set to a persistent PostgreSQL database on Vercel.'
    )
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_URL = 'static/'


# Email
# https://docs.djangoproject.com/en/6.1/topics/email/#topic-email-configuration

MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.console.EmailBackend',
    },
}


from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1), 
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

GROQ_API_KEY = os.getenv('GROQ_API_KEY') or os.getenv('API_KEY', '')
GROQ_MODEL = os.environ.get('GROQ_MODEL', 'llama-3.1-8b-instant')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'