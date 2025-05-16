"""
Django settings for aquarea project.

"""

# Tundliku info eraldamiseks programmifailidest
# Kasutus KEY = config('KEY')
from decouple import config
import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'd2(t&+q!x+5#@tr2-kxenm0#kil&vylj==d%8$u-4#c3yxr3ty'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    '192.168.1.143',
    's9a.lan',
    '127.0.0.1', 'localhost',
]


# Application definition

INSTALLED_APPS = [
    'ajalugu',
    'app',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'aquarea.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'aquarea.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Europe/Tallinn'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# STATICFILES_DIRS = (
#     os.path.join(BASE_DIR, 'static'),
# )

# app
AQUAREA_USR = config('AQUAREA_USR')
AQUAREA_PWD = config('AQUAREA_PWD')
AQUAREA_PWD_SERVICE = config('AQUAREA_PWD_SERVICE')
AQUAREA_ACCESS_TOKEN = config('AQUAREA_accessToken')
AQUAREA_SELECTEDGWID = config('AQUAREA_selectedGwid')
AQUAREA_SELECTEDDEVICEID = config('AQUAREA_selectedDeviceId')

TUYA_USER=config('TUYA_USER')
TUYA_USER_PASSWORD=config('TUYA_USER_PASSWORD')
TUYA_DEVICE_ID = config('TUYA_DEVICE_ID')
TUYA_IP_ADDRESS = config('TUYA_IP_ADDRESS')
TUYA_LOCAL_KEY = config('TUYA_LOCAL_KEY')
TUYA_DEVICE_ID_2 = config('TUYA_DEVICE_ID_2')
TUYA_IP_ADDRESS_2 = config('TUYA_IP_ADDRESS_2')
TUYA_LOCAL_KEY_2 = config('TUYA_LOCAL_KEY_2')

EZR_IP_ADDRESS = config('EZR_IP_ADDRESS')

VALGAVESI_USERNAME = config('VALGAVESI_USERNAME')
VALGAVESI_PASSWORD = config('VALGAVESI_PASSWORD')
VALGAVESI_MOOTURI_NR = config('VALGAVESI_MOOTURI_NR')