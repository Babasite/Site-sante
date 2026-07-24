from django.shortcuts import render


def miam(request):
    return render(request, "accueil/miam.html")


def sedebrouiller(request):
    return render(request, "accueil/sedebrouiller.html")


def voyagerleger(request):
    return render(request, "accueil/voyagerleger.html")


def bricoler(request):
    return render(request, "accueil/bricoler.html")


def argent(request):
    return render(request, "accueil/argent.html")


def travailler(request):
    return render(request, "accueil/travailler.html")