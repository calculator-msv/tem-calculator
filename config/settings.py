"""
Django settings for config project.

Налаштування для локальної роботи (SQLite) та для Render.com + Neon (PostgreSQL).
Секрети та адреси задаються через змінні середовища (Render -> Environment).
"""

import os
import warnings
from pathlib import Path

import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------
# БЕЗПЕКА
# --------------------------------------------------------------------------

# True локально, False на Render (Render сам виставляє змінну RENDER)
DEBUG = os.environ.get('RENDER', '') == ''

# На Render обов'язково задайте змінну SECRET_KEY (Environment -> Add variable).
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-)+vt91r6shl89m!75q!3(cf8r!#78c+miof(j-8h04une)_k&b',
)
if not DEBUG and 'SECRET_KEY' not in os.environ:
    warnings.warn(
        'SECRET_KEY не задано у змінних середовища: використовується відомий '
        'ключ із коду. Задайте власний SECRET_KEY на Render.',
        RuntimeWarning,
    )

# Дозволені хости: локальні + адреса Render (Render сам задає RENDER_EXTERNAL_HOSTNAME)
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'tem-calculator.onrender.com']
_render_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if _render_host:
    ALLOWED_HOSTS.append(_render_host)
# додаткові хости через змінну: ALLOWED_HOSTS=example.com,www.example.com
ALLOWED_HOSTS += [h.strip() for h in os.environ.get('ALLOWED_HOSTS', '').split(',') if h.strip()]

# Для POST-запитів із захистом CSRF на https-адресах
CSRF_TRUSTED_ORIGINS = [
    f'https://{h}' for h in ALLOWED_HOSTS if h not in ('localhost', '127.0.0.1')
]

if not DEBUG:
    # Render працює за проксі: довіряємо заголовку про https
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# --------------------------------------------------------------------------
# ЗАСТОСУНКИ ТА МІДЛВАРИ
# --------------------------------------------------------------------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'main_app',  # система обліку ПММ
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # роздача статичних файлів на продакшені
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'main_app' / 'templates'],
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

WSGI_APPLICATION = 'config.wsgi.application'

# Куди перенаправляти неавторизованих (декоратор @login_required).
# Сторінка входу в системі — це головна сторінка з іменем 'index'.
LOGIN_URL = 'index'


# --------------------------------------------------------------------------
# БАЗА ДАНИХ
# --------------------------------------------------------------------------
# Локально: SQLite. На Render: змінна DATABASE_URL з рядком підключення Neon.
# Для Neon використовуйте адресу з "-pooler" у назві хоста (пул з'єднань PgBouncer),
# наприклад: postgresql://user:pass@ep-xxxx-pooler.eu-central-1.aws.neon.tech/db?sslmode=require

DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=300,         # Neon засинає після 5 хв без запитів
            conn_health_checks=True,  # перевірка з'єднання перед запитом (після «засинання»)
        )
    }
    if '-pooler' in DATABASE_URL:
        # PgBouncer у режимі transaction не підтримує серверні курсори
        DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS'] = True
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# --------------------------------------------------------------------------
# ПАРОЛІ ТА МІЖНАРОДНІ НАЛАШТУВАННЯ
# --------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Дозволений розмір POST-запиту: за замовчуванням 2,5 МБ, а PDF-документи бібліотеки
# (до 16 МБ у Base64) та зображення маршрутів потребують більше.
DATA_UPLOAD_MAX_MEMORY_SIZE = 30 * 1024 * 1024

LANGUAGE_CODE = 'uk-ua'
TIME_ZONE = 'Europe/Kyiv'
USE_I18N = True
USE_TZ = True


# --------------------------------------------------------------------------
# СТАТИЧНІ ФАЙЛИ
# --------------------------------------------------------------------------

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Параметр STATICFILES_STORAGE видалено з Django 5.1 — використовується STORAGES
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}


# --------------------------------------------------------------------------
# ЛИСТИ
# --------------------------------------------------------------------------
# (у Django немає налаштування MAILERS — використовується EMAIL_BACKEND)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Сеанс: закінчується при закритті браузера та після 30 хв без активності.
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 30 * 60
SESSION_SAVE_EVERY_REQUEST = True