from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accueil.lancerveille import lancer_veille_complete
from accueil.models import ArticleVeille, VeilleQuotidienne


class Command(BaseCommand):
    help = (
        "Lance la veille scientifique complète, "
        "génère le résumé et enregistre les résultats."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help=(
                "Crée une nouvelle veille même si une veille "
                "terminée existe déjà aujourd'hui."
            ),
        )

    def handle(self, *args, **options):
        aujourd_hui = timezone.localdate()
        forcer = options["force"]

        veille_existante = (
            VeilleQuotidienne.objects
            .filter(
                date_creation__date=aujourd_hui,
                statut="terminee",
            )
            .order_by("-date_creation")
            .first()
        )

        if veille_existante and not forcer:
            self.stdout.write(
                self.style.WARNING(
                    "Une veille terminée existe déjà aujourd'hui. "
                    "Utilisez --force pour en créer une nouvelle."
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

        self.stdout.write(
            "Lancement de la veille scientifique complète..."
        )

        try:
            (
                resultats,
                resume,
                convergence,
                statistiques,
            ) = lancer_veille_complete()

            if not isinstance(resultats, list):
                raise TypeError(
                    "Le moteur n'a pas retourné une liste d'articles."
                )

            with transaction.atomic():
                for ordre, article in enumerate(
                    resultats,
                    start=1,
                ):
                    ArticleVeille.objects.create(
                        veille=veille,
                        titre=article.get(
                            "titre",
                            "Titre non disponible",
                        ),
                        source=article.get(
                            "source",
                            "Source inconnue",
                        ),
                        lien=article.get(
                            "lien",
                            "",
                        ),
                        date_publication=article.get(
                            "date",
                            "",
                        ),
                        resume=article.get(
                            "resume",
                            "",
                        ),
                        score=article.get(
                            "score",
                            0,
                        ),
                        ordre=ordre,

                        # Classification One Health
                        categories=article.get(
                            "categories",
                            [],
                        ),
                        one_health=article.get(
                            "one_health",
                            [],
                        ),
                        preuve=article.get(
                            "preuve",
                            "Non déterminé",
                        ),
                        niveau_preuve=article.get(
                            "niveau_preuve",
                            0,
                        ),
                        importance=article.get(
                            "importance",
                            0,
                        ),
                        niveau_importance=article.get(
                            "niveau_importance",
                            "Veille documentaire",
                        ),
                        raisons=article.get(
                            "raisons",
                            [],
                        ),
                        mots_detectes=article.get(
                            "mots_detectes",
                            [],
                        ),
                    )

                veille.resume = resume
                veille.convergence = convergence
                veille.nombre_articles = len(resultats)

                veille.sources_interrogees = statistiques.get(
                    "sources_interrogees",
                    0,
                )

                veille.articles_recuperes = statistiques.get(
                    "articles_recuperes",
                    0,
                )

                veille.doublons_supprimes = statistiques.get(
                    "doublons_supprimes",
                    0,
                )

                veille.duree_secondes = statistiques.get(
                    "duree_secondes",
                    0,
                )

                veille.statut = "terminee"
                veille.message_erreur = ""

                veille.save(
                    update_fields=[
                        "resume",
                        "convergence",
                        "nombre_articles",
                        "sources_interrogees",
                        "articles_recuperes",
                        "doublons_supprimes",
                        "duree_secondes",
                        "statut",
                        "message_erreur",
                    ]
                )

            self.stdout.write(
                self.style.SUCCESS(
                    "Veille terminée avec succès : "
                    f"{len(resultats)} article(s) enregistré(s)."
                )
            )

            self.stdout.write(
                f"Sources interrogées : "
                f"{veille.sources_interrogees}"
            )

            self.stdout.write(
                f"Articles récupérés : "
                f"{veille.articles_recuperes}"
            )

            self.stdout.write(
                f"Doublons supprimés : "
                f"{veille.doublons_supprimes}"
            )

            self.stdout.write(
                f"Durée totale : "
                f"{veille.duree_secondes:.1f} seconde(s)"
            )

            if convergence:
                self.stdout.write(
                    self.style.SUCCESS(
                        "Une convergence potentielle a été détectée."
                    )
                )
            else:
                self.stdout.write(
                    "Aucune convergence suffisamment nette détectée."
                )

        except Exception as erreur:
            veille.statut = "erreur"
            veille.message_erreur = str(erreur)

            veille.save(
                update_fields=[
                    "statut",
                    "message_erreur",
                ]
            )

            self.stderr.write(
                self.style.ERROR(
                    f"La veille a échoué : {erreur}"
                )
            )