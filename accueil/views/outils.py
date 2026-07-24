from django.shortcuts import render


def outils(request):
    return render(request, "accueil/outils.html")