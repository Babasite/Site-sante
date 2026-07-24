"""Commande planifiée pour lancer la veille scientifique quotidienne."""

from __future__ import annotations

import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.monitoring.lancerveille import lancer_veille_complete
from accueil.models import ArticleVeille, VeilleQuotidienne


class Command(BaseCommand):
    help = (
        "Lance la veille une fois par jour à partir de l'heure configurée. "
        "La commande peut être appelée régulièrement : elle ne relance pas "
        "une veille déjà terminée aujourd'hui."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Lance une nouvelle veille sans tenir compte de l'heure ni d'une veille déjà terminée.",
        )
        parser.add_argument(
            "--heure",
            type=int,
            default=int(os.getenv("VEILLE_HEURE_AUTO", "7")),
            help=(
                "Heure locale à partir de laquelle la veille peut être lancée "
                "(0 à 23). Valeur par défaut : VEILLE_HEURE_AUTO, sinon 7."
            ),
        )

    def handle(self, *args, **options):
        forcer = bool(options["force"])
        heure_cible = int(options["heure"])

        if not 0 <= heure_cible <= 23:
            raise CommandError("--heure doit être comprise entre 0 et 23.")

        maintenant = timezone.localtime()
        aujourd_hui = maintenant.date()

        if not forcer and maintenant.hour < heure_cible:
            self.stdout.write(
                f"Veille non lancée : il est {maintenant:%H:%M}, "
                f"heure prévue à partir de {heure_cible:02d}:00."
            )
            return

        veille_existante = (
            VeilleQuotidienne.objects.filter(
                date_creation__date=aujourd_hui,
                statut="terminee",
            )
            .order_by("-date_creation")
            .first()
        )

        if veille_existante and not forcer:
            self.stdout.write(
                self.style.WARNING(
                    "Veille non lancée : une veille terminée existe déjà aujourd'hui."
                )
            )
            return

        veille_en_cours = (
            VeilleQuotidienne.objects.filter(
                date_creation__date=aujourd_hui,
                statut="en_cours",
            )
            .order_by("-date_creation")
            .first()
        )

        if veille_en_cours and not forcer:
            self.stdout.write(
                self.style.WARNING(
                    "Veille non lancée : une veille est déjà en cours aujourd'hui."
                )
            )
            return

        veille = VeilleQuotidienne.objects.create(
            statut="en_cours",
            resume="",
            convergence="",
            nombre_articles=0,
            sources_interrogees=0,
            articles_recuperes=0,
            doublons_supprimes=0,
            duree_secondes=0,
        )

        self.stdout.write("Lancement de la veille scientifique quotidienne...")

        try:
            resultats, resume, convergence, statistiques = lancer_veille_complete()

            if not isinstance(resultats, list):
                raise TypeError("Le moteur n'a pas retourné une liste d'articles.")

            with transaction.atomic():
                for ordre, article in enumerate(resultats, start=1):
                    ArticleVeille.objects.create(
                        veille=veille,
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
                        niveau_importance=article.get(
                            "niveau_importance", "Veille documentaire"
                        ),
                        raisons=article.get("raisons", []),
                        mots_detectes=article.get("mots_detectes", []),
                    )

                veille.resume = resume
                veille.convergence = convergence
                veille.nombre_articles = len(resultats)
                veille.sources_interrogees = statistiques.get("sources_interrogees", 0)
                veille.articles_recuperes = statistiques.get("articles_recuperes", 0)
                veille.doublons_supprimes = statistiques.get("doublons_supprimes", 0)
                veille.duree_secondes = statistiques.get("duree_secondes", 0)
                veille.statut = "terminee"
                veille.message_erreur = ""
                veille.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Veille terminée : {len(resultats)} article(s) enregistré(s)."
                )
            )

        except Exception as erreur:
            veille.statut = "erreur"
            veille.message_erreur = str(erreur)
            veille.save(update_fields=["statut", "message_erreur"])
            raise CommandError(f"La veille a échoué : {erreur}") from erreur
