from django.contrib import admin

from .models import ArticleVeille, VeilleQuotidienne


class ArticleVeilleInline(admin.TabularInline):
    model = ArticleVeille
    extra = 0
    fields = (
        "ordre", "source", "titre", "titre_traduit_manuel",
        "traduction_manuelle_publiee",
    )
    readonly_fields = ("ordre", "source", "titre")
    show_change_link = True


@admin.register(VeilleQuotidienne)
class VeilleQuotidienneAdmin(admin.ModelAdmin):
    list_display = (
        "date_creation", "statut", "nombre_articles", "resume_manuel_publie",
    )
    list_filter = ("statut", "resume_manuel_publie", "date_creation")
    search_fields = ("resume", "resume_manuel")
    readonly_fields = (
        "date_creation", "resume", "convergence", "nombre_articles",
        "sources_interrogees", "articles_recuperes", "doublons_supprimes",
        "duree_secondes",
    )
    fieldsets = (
        ("Publication", {"fields": ("statut", "date_creation")}),
        ("Résumé automatique", {"fields": ("resume", "convergence")}),
        ("Ton résumé", {"fields": ("resume_manuel", "resume_manuel_publie")}),
        ("Statistiques", {"fields": (
            "nombre_articles", "sources_interrogees", "articles_recuperes",
            "doublons_supprimes", "duree_secondes",
        )}),
        ("Erreur éventuelle", {"fields": ("message_erreur",)}),
    )
    inlines = [ArticleVeilleInline]


@admin.register(ArticleVeille)
class ArticleVeilleAdmin(admin.ModelAdmin):
    list_display = ("titre_court", "source", "veille", "traduction_manuelle_publiee")
    list_filter = ("source", "traduction_manuelle_publiee", "veille")
    search_fields = (
        "titre", "resume", "titre_traduit_auto", "titre_traduit_manuel",
    )
    readonly_fields = (
        "veille", "titre", "resume", "source", "lien", "date_publication",
        "score", "categories", "one_health", "preuve", "niveau_preuve",
        "importance", "niveau_importance", "raisons", "mots_detectes",
    )
    fieldsets = (
        ("Article original", {"fields": (
            "veille", "source", "date_publication", "lien", "titre", "resume",
        )}),
        ("Traduction automatique provisoire", {"fields": (
            "titre_traduit_auto", "resume_traduit_auto",
        )}),
        ("Ta traduction", {"fields": (
            "titre_traduit_manuel", "resume_traduit_manuel",
            "traduction_manuelle_publiee",
        )}),
        ("Classement", {"fields": (
            "score", "categories", "one_health", "preuve", "niveau_preuve",
            "importance", "niveau_importance", "raisons", "mots_detectes",
        )}),
    )

    @admin.display(description="Titre")
    def titre_court(self, article):
        return article.titre if len(article.titre) <= 80 else article.titre[:77] + "..."
