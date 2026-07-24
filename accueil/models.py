from django.db import models


class VeilleQuotidienne(models.Model):
    """Représente une veille complète produite par le moteur."""

    STATUTS = [
        ("en_cours", "En cours"),
        ("terminee", "Terminée"),
        ("erreur", "Erreur"),
    ]

    date_creation = models.DateTimeField(auto_now_add=True)
    resume = models.TextField(blank=True, verbose_name="Résumé automatique")
    resume_manuel = models.TextField(blank=True, verbose_name="Résumé manuel")
    resume_manuel_publie = models.BooleanField(
        default=False,
        verbose_name="Publier le résumé manuel",
    )
    convergence = models.TextField(blank=True)
    statut = models.CharField(max_length=20, choices=STATUTS, default="en_cours")
    message_erreur = models.TextField(blank=True)
    nombre_articles = models.PositiveIntegerField(default=0)
    sources_interrogees = models.PositiveIntegerField(default=0)
    articles_recuperes = models.PositiveIntegerField(default=0)
    doublons_supprimes = models.PositiveIntegerField(default=0)
    duree_secondes = models.FloatField(default=0)

    @property
    def resume_affiche(self):
        if self.resume_manuel_publie and self.resume_manuel.strip():
            return self.resume_manuel
        return self.resume

    def __str__(self):
        return f"Veille du {self.date_creation.strftime('%d/%m/%Y à %H:%M')}"

    class Meta:
        ordering = ["-date_creation"]
        verbose_name = "Veille quotidienne"
        verbose_name_plural = "Veilles quotidiennes"


class ArticleVeille(models.Model):
    """Représente un article retenu dans une veille quotidienne."""

    veille = models.ForeignKey(
        VeilleQuotidienne,
        on_delete=models.CASCADE,
        related_name="articles",
    )
    titre = models.CharField(max_length=1000)
    source = models.CharField(max_length=200)
    lien = models.URLField(max_length=2000)
    date_publication = models.CharField(max_length=100, blank=True)
    resume = models.TextField(blank=True)

    titre_traduit_auto = models.TextField(
        blank=True,
        verbose_name="Titre traduit automatiquement",
    )
    resume_traduit_auto = models.TextField(
        blank=True,
        verbose_name="Résumé traduit automatiquement",
    )
    titre_traduit_manuel = models.TextField(
        blank=True,
        verbose_name="Titre traduit manuellement",
    )
    resume_traduit_manuel = models.TextField(
        blank=True,
        verbose_name="Résumé traduit manuellement",
    )
    traduction_manuelle_publiee = models.BooleanField(
        default=False,
        verbose_name="Publier la traduction manuelle",
    )

    score = models.IntegerField(default=0)
    ordre = models.PositiveIntegerField(default=0)
    categories = models.JSONField(default=list, blank=True)
    one_health = models.JSONField(default=list, blank=True)
    preuve = models.CharField(max_length=250, default="Non déterminé", blank=True)
    niveau_preuve = models.PositiveSmallIntegerField(default=0)
    importance = models.PositiveSmallIntegerField(default=0)
    niveau_importance = models.CharField(
        max_length=100,
        default="Veille documentaire",
        blank=True,
    )
    raisons = models.JSONField(default=list, blank=True)
    mots_detectes = models.JSONField(default=list, blank=True)

    @property
    def titre_affiche(self):
        if self.traduction_manuelle_publiee and self.titre_traduit_manuel.strip():
            return self.titre_traduit_manuel
        if self.titre_traduit_auto.strip():
            return self.titre_traduit_auto
        return self.titre

    @property
    def resume_affiche(self):
        if self.traduction_manuelle_publiee and self.resume_traduit_manuel.strip():
            return self.resume_traduit_manuel
        if self.resume_traduit_auto.strip():
            return self.resume_traduit_auto
        return self.resume

    @property
    def traduction_est_automatique(self):
        return (
            not self.traduction_manuelle_publiee
            and bool(self.titre_traduit_auto.strip() or self.resume_traduit_auto.strip())
        )

    def __str__(self):
        return f"{self.source} — {self.titre}"

    class Meta:
        ordering = ["ordre", "-score"]
        verbose_name = "Article de veille"
        verbose_name_plural = "Articles de veille"
