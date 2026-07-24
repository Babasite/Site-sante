"""Sélection automatique des réglages Django.

Le développement est utilisé par défaut. En production, définir :
DJANGO_SETTINGS_MODULE=config.settings.production
"""

from .development import *  # noqa: F403
