from django.shortcuts import render

def miam(request):
    """Affiche la page consacrée à l'alimentation."""
    return render(request, "accueil/miam.html")

def pharmacie(request):
    return render(request, "accueil/pharmacie.html")
