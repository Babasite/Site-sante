from django.shortcuts import render


def notice(request):
    return render(request, "accueil/notice.html")