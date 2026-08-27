"""

URLS DES PAGES GÉNÉRALES DU SITE

Ce fichier contient uniquement les routes des pages générales gérées par :

    accueil/views.py

Il ne doit pas contenir les routes de la veille scientifique.
Ces routes doivent être placées dans :

    apps/monitoring/urls.py

Il ne doit pas non plus contenir les routes du système de recommandations.
Ces routes doivent être placées dans :

    apps/recommendations/urls.py

IMPORTANT

Chaque vue référencée dans ce fichier doit réellement exister dans
accueil/views.py.

"""

from django.urls import path

from . import views

urlpatterns = [
    # =========================================================================
    # ACCUEIL ET INFORMATIONS GÉNÉRALES
    # =========================================================================
    path("", views.home, name="home"),
    path("notice/", views.notice, name="notice"),
    path("outils/", views.outils, name="outils"),
    path("terrain/", views.terrain, name="terrain"),
    path("apropos/", views.apropos, name="apropos"),
    path("pompier/", views.pompier, name="pompier"),
    path("contact/", views.contact, name="contact"),
    path("boutique/", views.boutique, name="boutique"),

    # =========================================================================
    # ACTIVITÉS ET JEUX
    # =========================================================================
    path("jeu/", views.jeu, name="jeu"),
    path("tetris/", views.tetris, name="tetris"),
    path("space/", views.space, name="space"),
    path("combat/", views.combat, name="combat"),
    path("karate/", views.karate, name="karate"),
    path("osteo/", views.osteo, name="osteo"),
    # PAYS

    path("pays/<slug:pays>/", views.pays, name="pays"),

    # =========================================================================
    # VIE QUOTIDIENNE
    # =========================================================================
    path("miam/", views.miam, name="miam"),
    path("pharmacie/", views.pharmacie, name="pharmacie"),
    path(
        "sedebrouiller/",
        views.sedebrouiller,
        name="sedebrouiller",
    ),
    path(
        "organisation/",
        views.organisation,
        name="organisation",
    ),
    path(
        "organisation/commencer-pc/",
        views.commencerpc,
        name="commencerpc",
    ),
    path(
        "voyager-leger/",
        views.voyagerleger,
        name="voyagerleger",
    ),
    path("bricoler/", views.bricoler, name="bricoler"),
    path("argent/", views.argent, name="argent"),
    path("travailler/", views.travailler, name="travailler"),
    path("investissement/", views.investissement, name="investissement"),

    # =========================================================================
    # SANTÉ ET SUIVI
    # =========================================================================
path("scores/analogique/", views.score_analogique, name="score_analogique"),

path("scores/cha/", views.score_cha, name="score_cha"),

path("scores/cockcroft-gault/", views.score_cockcroft_gault, name="score_cockcroft_gault"),

path("scores/glasgow/", views.score_glasgow, name="score_glasgow"),

path("scores/iadl/", views.score_iadl, name="score_iadl"),

path("scores/katz/", views.score_katz, name="score_katz"),

path("scores/numerique/", views.score_numerique, name="score_numerique"),

path("scores/wells-embolie/", views.score_wells_embolie, name="score_wells_embolie"),

path("scores/wells-thrombose/", views.score_wells_thrombose, name="score_wells_thrombose"),


    path(
        "check-up-rapide/",
        views.check_up_rapide,
        name="check_up_rapide",
    ),
    path(
        "suivi-personnalise/",
        views.suivi_personnalise,
        name="suivi_personnalise",
    ),
    path(
        "healthcompare/",
        views.healthcompare,
        name="healthcompare",
    ),
    path(
    "healthcompare/maladies/",
    views.maladies_data,
    name="maladies_data",
),
]