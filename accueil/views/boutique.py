from django.shortcuts import render

def boutique(request):
    return render(request, "accueil/boutique.html")