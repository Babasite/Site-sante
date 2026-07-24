from django.urls import path

from . import views


urlpatterns = [
    path("veille/", views.veille, name="veille"),
    path("veille/<int:veille_id>/", views.detail_veille, name="detail_veille"),
    path(
        "veille/<int:veille_id>/pdf/",
        views.exporter_veille_pdf,
        name="exporter_veille_pdf",
    ),
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