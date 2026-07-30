from django.shortcuts import render


def jeu(request):
    return render(request, "accueil/Jeux/jeu.html")