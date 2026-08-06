from apps.pays.views import fiche_pays

def pays(request, pays):
    return fiche_pays(request, pays)