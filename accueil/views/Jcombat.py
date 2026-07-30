from django.shortcuts import render

def combat(request):
    return render(request, "accueil/Jeux/combat.html")