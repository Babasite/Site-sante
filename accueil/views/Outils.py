from django.shortcuts import render

def outils(request):
    return render(request, "accueil/outils.html")


def check_up_rapide(request):
    return render(request, "accueil/check_up_rapide.html")

def suivi_personnalise(request):
    return render(request, "accueil/suivi_personnalise.html")

def healthcompare(request):
    return render(request, "accueil/healthcompare.html")

def maladies_data(request):
    return render(request, "accueil/maladies.html")



def score_analogique(request):
    return render(request, "accueil/Scores/analogique.html")


def score_cha(request):
    return render(request, "accueil/Scores/CHA.html")


def score_cockcroft_gault(request):
    return render(request, "accueil/Scores/Cockcroft-Gault.html")


def score_glasgow(request):
    return render(request, "accueil/Scores/Glasgow.html")


def score_iadl(request):
    return render(request, "accueil/Scores/IADL.html")


def score_katz(request):
    return render(request, "accueil/Scores/Katz.html")


def score_numerique(request):
    return render(request, "accueil/Scores/numérique.html")


def score_wells_embolie(request):
    return render(request, "accueil/Scores/WellsEmbolie.html")


def score_wells_thrombose(request):
    return render(request, "accueil/Scores/WellsThrombose.html")