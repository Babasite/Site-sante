from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import ArticleVeille, VeilleQuotidienne


class ModeRedacteurTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="redacteur", password="motdepasse-test", is_staff=True
        )
        self.veille = VeilleQuotidienne.objects.create(
            statut="terminee", resume="Résumé automatique", nombre_articles=1
        )
        self.article = ArticleVeille.objects.create(
            veille=self.veille,
            titre="Titre original",
            source="Source",
            lien="https://example.com/article",
            resume="Résumé original",
        )

    def test_tableau_de_bord_est_protege(self):
        response = self.client.get(reverse("tableau_de_bord"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("redacteur_connexion"), response.url)

    def test_tableau_de_bord_staff(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("tableau_de_bord"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tableau de bord rédacteur")

    def test_historique_staff(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("historique_veilles"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Historique des veilles")

    def test_modification_resume(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("modifier_resume", args=[self.veille.id]),
            {"resume_manuel": "Résumé vérifié", "resume_manuel_publie": "on"},
        )
        self.assertEqual(response.status_code, 302)
        self.veille.refresh_from_db()
        self.assertEqual(self.veille.resume_manuel, "Résumé vérifié")
        self.assertTrue(self.veille.resume_manuel_publie)

    def test_modification_traduction(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("modifier_traduction", args=[self.article.id]),
            {
                "titre_traduit_manuel": "Titre traduit",
                "resume_traduit_manuel": "Résumé traduit",
                "traduction_manuelle_publiee": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.article.refresh_from_db()
        self.assertEqual(self.article.titre_affiche, "Titre traduit")
        self.assertTrue(self.article.traduction_manuelle_publiee)
