from django.urls import path

from .views import bouger


urlpatterns = [
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