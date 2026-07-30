from django.shortcuts import render


def pompier(request):
    return render(request, "accueil/pompier.html")

# Les jeux sont à part appelés "Jnomdujeu"
