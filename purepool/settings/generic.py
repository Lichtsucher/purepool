import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/

ALLOWED_HOSTS = []

TASK_DEBUG = False

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'biblepay',
    'puretransaction',
    'purepool.core',
    'purepool.frontend',
    'purepool.interface',
    'purepool.models.miner',
    'purepool.models.solution',
    'purepool.models.block',    
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

ROOT_URLCONF = 'purepool.core.urls'

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
                'purepool.core.context_processors.add_purepool_data',
            ],
        },
    },
]

WSGI_APPLICATION = 'purepool.wsgi.application'

# The celery task routing is used to create a separate task queue for the
# important tasks of block finding, payout and other things
CELERY_TASK_ROUTES = {
    # own queue, as it MUST run as quick as possible
    'purepool.models.block.tasks.find_new_blocks': {'queue': 'find_new_blocks'}, 
    
    # the transaction has its own queue, we don't want more then one of it
    # running. Easier then using locks
    'puretransaction.tasks.send_autopayments': {'queue': 'send_autopayments'},
    
    # important tasks that need to run quick and not stopped by
    # processing solutions
    'purepool.models.block.tasks.process_next_block': {'queue': 'important'},
    'purepool.models.block.tasks.shareout_next_block': {'queue': 'important'},    
    
    # low priority, but must run with a lot of runners
    'purepool.models.solution.tasks.process_solution': {'queue': 'standard'}, 
    'purepool.models.solution.tasks.cleanup_solutions': {'queue': 'standard'},
}


# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

STATIC_URL = '/static/'
