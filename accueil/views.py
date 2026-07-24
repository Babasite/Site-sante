from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .lancerveille import lancer_veille_complete
from .models import ArticleVeille, VeilleQuotidienne
from .services_nouveau.services.pdf import generer_pdf_veille


def home(request):
    return render(request, "accueil/home.html")


def outils(request):
    return render(request, "accueil/outils.html")


def _contexte_veille(veille_selectionnee):
    articles = veille_selectionnee.articles.all().order_by("ordre", "-score")
    return {
        "veille": veille_selectionnee,
        "veille_id": veille_selectionnee.id,
        "resultats": articles,
        "convergence": veille_selectionnee.convergence,
        "date_veille": veille_selectionnee.date_creation,
        "nombre_articles": veille_selectionnee.nombre_articles,
        "sources_interrogees": veille_selectionnee.sources_interrogees,
        "articles_recuperes": veille_selectionnee.articles_recuperes,
        "doublons_supprimes": veille_selectionnee.doublons_supprimes,
        "duree_secondes": veille_selectionnee.duree_secondes,
    }


def veille(request):
    derniere_veille = (
        VeilleQuotidienne.objects.filter(statut="terminee")
        .order_by("-date_creation")
        .first()
    )

    if request.method == "POST":
        if not request.user.is_authenticated or not request.user.is_staff:
            messages.error(request, "Connectez-vous comme rédacteur pour lancer une veille.")
            return redirect("redacteur_connexion")

        veille_en_cours = VeilleQuotidienne.objects.create(
            statut="en_cours",
            resume="",
            convergence="",
            nombre_articles=0,
            sources_interrogees=0,
            articles_recuperes=0,
            doublons_supprimes=0,
            duree_secondes=0,
        )

        try:
            resultats, resume, convergence, statistiques = lancer_veille_complete()

            with transaction.atomic():
                for ordre, article in enumerate(resultats, start=1):
                    ArticleVeille.objects.create(
                        veille=veille_en_cours,
                        titre=article.get("titre", "Titre non disponible"),
                        source=article.get("source", "Source inconnue"),
                        lien=article.get("lien", ""),
                        date_publication=article.get("date", ""),
                        resume=article.get("resume", ""),
                        score=article.get("score", 0),
                        ordre=ordre,
                        categories=article.get("categories", []),
                        one_health=article.get("one_health", []),
                        preuve=article.get("preuve", "Non déterminé"),
                        niveau_preuve=article.get("niveau_preuve", 0),
                        importance=article.get("importance", 0),
                        niveau_importance=article.get("niveau_importance", "Veille documentaire"),
                        raisons=article.get("raisons", []),
                        mots_detectes=article.get("mots_detectes", []),
                    )

                veille_en_cours.resume = resume
                veille_en_cours.convergence = convergence
                veille_en_cours.nombre_articles = len(resultats)
                veille_en_cours.sources_interrogees = statistiques.get("sources_interrogees", 0)
                veille_en_cours.articles_recuperes = statistiques.get("articles_recuperes", 0)
                veille_en_cours.doublons_supprimes = statistiques.get("doublons_supprimes", 0)
                veille_en_cours.duree_secondes = statistiques.get("duree_secondes", 0)
                veille_en_cours.statut = "terminee"
                veille_en_cours.message_erreur = ""
                veille_en_cours.save()

            return redirect("detail_veille", veille_id=veille_en_cours.id)

        except Exception as erreur:
            veille_en_cours.statut = "erreur"
            veille_en_cours.message_erreur = str(erreur)
            veille_en_cours.save(update_fields=["statut", "message_erreur"])
            return render(
                request,
                "accueil/veille.html",
                {
                    "derniere_veille": derniere_veille,
                    "erreur": f"La veille n’a pas pu être terminée : {erreur}",
                },
                status=500,
            )

    return render(request, "accueil/veille.html", {"derniere_veille": derniere_veille})


@require_GET
def detail_veille(request, veille_id):
    veille_selectionnee = get_object_or_404(VeilleQuotidienne, id=veille_id, statut="terminee")
    return render(request, "accueil/resultats_veille.html", _contexte_veille(veille_selectionnee))


@require_GET
def exporter_veille_pdf(request, veille_id):
    veille_selectionnee = get_object_or_404(
        VeilleQuotidienne.objects.prefetch_related("articles"),
        id=veille_id,
        statut="terminee",
    )
    contenu_pdf = generer_pdf_veille(veille_selectionnee)
    date_fichier = timezone.localtime(veille_selectionnee.date_creation).date().isoformat()
    reponse = HttpResponse(contenu_pdf, content_type="application/pdf")
    reponse["Content-Disposition"] = f'attachment; filename="Veille_scientifique_{date_fichier}.pdf"'
    return reponse


def staff_required(view_function):
    return user_passes_test(lambda user: user.is_authenticated and user.is_staff, login_url="redacteur_connexion")(view_function)


@require_http_methods(["GET", "POST"])
def redacteur_connexion(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("veille")

    if request.method == "POST":
        utilisateur = authenticate(
            request,
            username=request.POST.get("username", "").strip(),
            password=request.POST.get("password", ""),
        )
        if utilisateur is not None and utilisateur.is_staff:
            login(request, utilisateur)
            destination = request.GET.get("next") or reverse("veille")
            return redirect(destination)
        messages.error(request, "Identifiant incorrect ou compte non autorisé.")

    return render(request, "accueil/redacteur_connexion.html")


@require_POST
def redacteur_deconnexion(request):
    logout(request)
    return redirect("veille")


@staff_required
@require_GET
def tableau_de_bord(request):
    veilles = VeilleQuotidienne.objects.order_by("-date_creation")
    derniere_veille = veilles.filter(statut="terminee").first()

    statistiques = {
        "nombre_veilles": veilles.filter(statut="terminee").count(),
        "nombre_erreurs": veilles.filter(statut="erreur").count(),
        "nombre_articles": ArticleVeille.objects.count(),
        "nombre_traductions_publiees": ArticleVeille.objects.filter(
            traduction_manuelle_publiee=True
        ).count(),
    }

    if derniere_veille:
        articles_derniere_veille = derniere_veille.articles.all()
        statistiques["articles_derniere_veille"] = articles_derniere_veille.count()
        statistiques["traductions_derniere_veille"] = articles_derniere_veille.filter(
            traduction_manuelle_publiee=True
        ).count()
    else:
        statistiques["articles_derniere_veille"] = 0
        statistiques["traductions_derniere_veille"] = 0

    return render(
        request,
        "accueil/tableau_de_bord.html",
        {"derniere_veille": derniere_veille, "statistiques": statistiques},
    )


@staff_required
@require_GET
def historique_veilles(request):
    veilles = VeilleQuotidienne.objects.prefetch_related("articles").order_by(
        "-date_creation"
    )
    return render(request, "accueil/historique_veilles.html", {"veilles": veilles})


@staff_required
@require_http_methods(["GET", "POST"])
def modifier_resume(request, veille_id):
    veille_selectionnee = get_object_or_404(VeilleQuotidienne, id=veille_id, statut="terminee")
    if request.method == "POST":
        veille_selectionnee.resume_manuel = request.POST.get("resume_manuel", "").strip()
        veille_selectionnee.resume_manuel_publie = request.POST.get("resume_manuel_publie") == "on"
        veille_selectionnee.save(update_fields=["resume_manuel", "resume_manuel_publie"])
        messages.success(request, "Le résumé a été enregistré.")
        return redirect("detail_veille", veille_id=veille_selectionnee.id)
    return render(request, "accueil/modifier_resume.html", {"veille": veille_selectionnee})


@staff_required
@require_http_methods(["GET", "POST"])
def modifier_traduction(request, article_id):
    article = get_object_or_404(ArticleVeille.objects.select_related("veille"), id=article_id)
    if request.method == "POST":
        article.titre_traduit_manuel = request.POST.get("titre_traduit_manuel", "").strip()
        article.resume_traduit_manuel = request.POST.get("resume_traduit_manuel", "").strip()
        article.traduction_manuelle_publiee = request.POST.get("traduction_manuelle_publiee") == "on"
        article.save(update_fields=["titre_traduit_manuel", "resume_traduit_manuel", "traduction_manuelle_publiee"])
        messages.success(request, "La traduction a été enregistrée.")
        return redirect("detail_veille", veille_id=article.veille_id)
    return render(request, "accueil/modifier_traduction.html", {"article": article})


def terrain(request):
    return render(request, "accueil/terrain.html")


def apropos(request):
    return render(request, "accueil/apropos.html")


def notice(request):
    return render(request, "accueil/notice.html")


def pompier(request):
    return render(request, "accueil/pompier.html")


def jeu(request):
    return render(request, "accueil/jeu.html")


def karate(request):
    return render(request, "accueil/karate.html")


def bouger_questionnaire(request):
    return render(request, "accueil/bouger_questionnaire.html")


def resultat_sport(request):
    return render(request, "accueil/resultat_sport.html")


def fiche_sport(request, sport_id):
    return render(request, "accueil/fiche_sport.html", {"sport_id": sport_id})


def miam(request):
    return render(request, "accueil/miam.html")


def sedebrouiller(request):
    return render(request, "accueil/sedebrouiller.html")


def voyagerleger(request):
    return render(request, "accueil/voyagerleger.html")


def bricoler(request):
    return render(request, "accueil/bricoler.html")


def argent(request):
    return render(request, "accueil/argent.html")


def travailler(request):
    return render(request, "accueil/travailler.html")


def check_up_rapide(request):
    return render(request, "accueil/check_up_rapide.html")


def suivi_personnalise(request):
    return render(request, "accueil/suivi_personnalise.html")


def healthcompare(request):
    return render(request, "accueil/healthcompare.html")
