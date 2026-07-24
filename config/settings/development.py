"""Réglages pour le développement local."""

from .base import *  # noqa: F403
from .base import env_bool, env_list

DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")

# En développement, une clé locale stable évite de devoir configurer un .env
# pour simplement lancer le projet. Elle ne doit jamais être utilisée en production.
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-local-development-key")  # noqa: F405
