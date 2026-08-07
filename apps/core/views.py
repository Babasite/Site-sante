from django.shortcuts import render


def erreur_404(request, exception):
    return render(
        request,
        "errors/404.html",
        status=404,
    )


def erreur_500(request):
    return render(
        request,
        "errors/500.html",
        status=500,
    )