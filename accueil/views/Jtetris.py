from django.shortcuts import render

def tetris(request):
    return render(request, "accueil/Jeux/tetris.html")
