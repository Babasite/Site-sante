from django.shortcuts import render


def investissement(request):
    return render(request, "accueil/investissement.html")