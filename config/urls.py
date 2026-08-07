"""
===============================================================================
ROUTEUR PRINCIPAL DE L'APPLICATION DJANGO
===============================================================================

Ce fichier est le point d'entrée des URL du projet.

Son unique responsabilité est de répartir les routes entre les différentes
applications. Il ne doit jamais contenir les routes métier directement.

Répartition actuelle :

    accueil/
        → pages générales du site

    apps/monitoring/
        → veille scientifique

    apps/recommendations/
        → recommandations d'activité physique

IMPORTANT
---------
Si une nouvelle fonctionnalité est créée, ajouter ses routes dans le fichier
urls.py de son application, puis inclure ce fichier ici avec include().

Ce fichier doit rester le plus simple possible.
===============================================================================
"""

from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    # -------------------------------------------------------------------------
    # Administration Django
    # -------------------------------------------------------------------------
    path("admin/", admin.site.urls),

    # -------------------------------------------------------------------------
    # Pages générales
    # -------------------------------------------------------------------------
    path("", include("accueil.urls")),

    # -------------------------------------------------------------------------
    # Veille scientifique
    # -------------------------------------------------------------------------
    path("", include("apps.monitoring.urls")),

    # -------------------------------------------------------------------------
    # Recommandations
    # -------------------------------------------------------------------------
    path("", include("apps.recommendations.urls")),
]

# -----------------------------------------------------------------------------
# Gestion des erreurs
# -----------------------------------------------------------------------------

handler404 = "apps.core.views.erreur_404"
handler500 = "apps.core.views.erreur_500"