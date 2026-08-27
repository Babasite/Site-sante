from django.shortcuts import render


def karate(request):
    return render(request, "accueil/karate.html")

def osteo(request):
    return render(request, "accueil/osteo.html")

def bouger_questionnaire(request):
    """Affiche le questionnaire consacré à l'activité physique."""
    return render(request, "accueil/bouger_questionnaire.html")

def resultat_sport(request):
    """Affiche les résultats du questionnaire sport."""
    return render(request, "accueil/resultat_sport.html")

def fiche_sport(request, sport_id):
    """Affiche la fiche correspondant à un sport."""
    return render(
        request,
        "accueil/fiche_sport.html",
        {"sport_id": sport_id},
    )