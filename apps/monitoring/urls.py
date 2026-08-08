"""
===============================================================================
URLS DE LA VEILLE SCIENTIFIQUE
===============================================================================

Ce fichier contient uniquement les routes liées à la veille scientifique.

Les vues correspondantes sont définies dans :

    apps/monitoring/views.py

Responsabilités :
    - affichage et lancement de la veille ;
    - consultation du détail d'une veille ;
    - export PDF ;
    - connexion et déconnexion des rédacteurs ;
    - tableau de bord et historique ;
    - modification des résumés et traductions manuelles.

Les routes des pages générales du site doivent rester dans :

    accueil/urls.py

Les routes du système de recommandations doivent rester dans :

    apps/recommendations/urls.py

IMPORTANT
---------
===============================================================================
"""

from django.urls import path

from . import views


urlpatterns = [
    # -------------------------------------------------------------------------
    # Consultation de la veille
    # -------------------------------------------------------------------------
    path(
        "veille/",
        views.veille,
        name="veille",
    ),
    path(
        "veille/<int:veille_id>/",
        views.detail_veille,
        name="detail_veille",
    ),
    path(
        "veille/<int:veille_id>/pdf/",
        views.exporter_veille_pdf,
        name="exporter_veille_pdf",
    ),

    # -------------------------------------------------------------------------
    # Authentification des rédacteurs
    # -------------------------------------------------------------------------
    path(
        "redacteur/connexion/",
        views.redacteur_connexion,
        name="redacteur_connexion",
    ),
    path(
        "redacteur/deconnexion/",
        views.redacteur_deconnexion,
        name="redacteur_deconnexion",
    ),

    # -------------------------------------------------------------------------
    # Administration de la veille
    # -------------------------------------------------------------------------
    path(
        "redacteur/tableau-de-bord/",
        views.tableau_de_bord,
        name="tableau_de_bord",
    ),
    path(
        "redacteur/historique/",
        views.historique_veilles,
        name="historique_veilles",
    ),

    # Création d'un journal manuel sans lancer la veille scientifique
    path(
        "redacteur/journal/nouveau/",
        views.creer_journal_manuel,
        name="creer_journal_manuel",
    ),

    path(
        "redacteur/veille/<int:veille_id>/resume/",
        views.modifier_resume,
        name="modifier_resume",
    ),
    path(
        "redacteur/article/<int:article_id>/traduction/",
        views.modifier_traduction,
        name="modifier_traduction",
    ),
]