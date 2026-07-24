from django.shortcuts import render


def bouger_questionnaire(request):
    return render(request, "accueil/bouger_questionnaire.html")


def resultat_sport(request):
    return render(request, "accueil/resultat_sport.html")


def fiche_sport(request, sport_id):
    return render(request, "accueil/fiche_sport.html", {"sport_id": sport_id})