from django.shortcuts import render


def check_up_rapide(request):
    return render(request, "accueil/check_up_rapide.html")


def suivi_personnalise(request):
    return render(request, "accueil/suivi_personnalise.html")


def healthcompare(request):
    return render(request, "accueil/healthcompare.html")