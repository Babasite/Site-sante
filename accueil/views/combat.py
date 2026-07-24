from django.shortcuts import render

def combat(request):
    return render(request, "accueil/combat.html")