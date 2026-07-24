from django.shortcuts import render


def terrain(request):
    return render(request, "accueil/terrain.html")