SECRET_KEY = "test-secret-key-for-django-kc-auth-tests"
DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "rest_framework",
    "django_kc_auth",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

SESSION_ENGINE = "django.contrib.sessions.backends.db"

ROOT_URLCONF = "tests.urls"

AUTHENTICATION_BACKENDS = ["django_kc_auth.backends.KeycloakBackend"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

MESSAGE_STORAGE = "django.contrib.messages.storage.cookie.CookieStorage"

# Keycloak settings
KC_SERVER_URL = "http://localhost:8080"
KC_REALM = "test-realm"
KC_CLIENT_ID = "test-client"
KC_CLIENT_SECRET = "test-secret"
KC_ROLES = ["admins", "employees"]
KC_VERIFYING_KEY = {"k": "test-key"}
