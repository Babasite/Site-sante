from django.shortcuts import render

def pharmacie(request):
    return render(request, "accueil/pharmacie.html")