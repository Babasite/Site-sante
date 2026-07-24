from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("notice/", views.notice, name="notice"),
    path("outils/", views.outils, name="outils"),
    path("terrain/", views.terrain, name="terrain"),
    path("apropos/", views.apropos, name="apropos"),
    path("pompier/", views.pompier, name="pompier"),
    path("jeu/", views.jeu, name="jeu"),
    path("tetris/", views.tetris, name="tetris"),
    path("space/", views.space, name="space"),
    path("combat/", views.combat, name="combat"),
    path("karate/", views.karate, name="karate"),
    path("miam/", views.miam, name="miam"),
    path("pharmacie/", views.pharmacie, name="pharmacie"),
    path("sedebrouiller/", views.sedebrouiller, name="sedebrouiller"),
    path("voyager-leger/", views.voyagerleger, name="voyagerleger"),
    path("bricoler/", views.bricoler, name="bricoler"),
    path("argent/", views.argent, name="argent"),
    path("travailler/", views.travailler, name="travailler"),
    path("check-up-rapide/", views.check_up_rapide, name="check_up_rapide"),
    path("suivi-personnalise/", views.suivi_personnalise, name="suivi_personnalise"),
    path("healthcompare/", views.healthcompare, name="healthcompare"),
    path("contact/", views.contact, name="contact"),
]