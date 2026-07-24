from django.shortcuts import render


def pompier(request):
    return render(request, "accueil/pompier.html")