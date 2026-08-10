from django.shortcuts import render


def organisation(request):
    return render(
        request,
        "accueil/organisation.html",
    )


def commencerpc(request):
    return render(
        request,
        "accueil/commencerpc.html",
    )