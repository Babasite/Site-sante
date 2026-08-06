"""
===============================================================================
URLS DU SYSTÈME DE RECOMMANDATIONS (En compléments des routes générales)
===============================================================================

Ce fichier contient uniquement les routes du module de recommandations.

Les vues correspondantes sont définies dans :

    apps/recommendations/views/bouger.py

Responsabilités :
    - questionnaire d'activité physique ;
    - calcul et affichage des résultats ;
    - affichage des fiches sportives.

Les routes des pages générales doivent rester dans :

    accueil/urls.py

Les routes de la veille scientifique doivent rester dans :

    apps/monitoring/urls.py

IMPORTANT
---------
Avant d'ajouter une route ici, vérifier que la vue existe bien dans
apps/recommendations/views/ et qu'elle concerne le système de recommandations.
===============================================================================
"""

from django.urls import path

from .views import bouger


urlpatterns = [
    # -------------------------------------------------------------------------
    # Activité physique
    # -------------------------------------------------------------------------
    path(
        "bouger/questionnaire/",
        bouger.bouger_questionnaire,
        name="bouger_questionnaire",
    ),
    path(
        "bouger/resultat/",
        bouger.resultat_sport,
        name="bouger_resultat",
    ),
    path(
        "bouger/sport/<slug:sport_id>/",
        bouger.fiche_sport,
        name="fiche_sport",
    ),
]