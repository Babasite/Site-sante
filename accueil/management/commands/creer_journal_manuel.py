from django.core.management.base import BaseCommand
from accueil.models import VeilleQuotidienne


class Command(BaseCommand):
    help = "Crée un journal manuel vide sans lancer la veille scientifique."

    def handle(self, *args, **options):
        veille = VeilleQuotidienne.objects.create(
            statut="terminee",
            resume="",
            resume_manuel="",
            resume_manuel_publie=False,
            convergence="",
            nombre_articles=0,
            sources_interrogees=0,
            articles_recuperes=0,
            doublons_supprimes=0,
            duree_secondes=0,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Journal manuel créé avec l'identifiant {veille.id}."
            )
        )