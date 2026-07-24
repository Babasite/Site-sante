from django.shortcuts import render


def apropos(request):
    return render(request, "accueil/apropos.html")