from django.shortcuts import render


def jeu(request):
    return render(request, "accueil/jeu.html")