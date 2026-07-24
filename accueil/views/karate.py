from django.shortcuts import render


def karate(request):
    return render(request, "accueil/karate.html")