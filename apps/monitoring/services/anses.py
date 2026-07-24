"""
Collecteur ANSES.

Le module consulte l'annuaire officiel des flux RSS de l'Anses,
découvre automatiquement les flux disponibles, puis les interroge.

Cette approche évite de dépendre uniquement d'anciennes URL
qui peuvent changer ou devenir indisponibles.

Thématiques annoncées par l'Anses :
- toutes les actualités ;
- alimentation humaine et nutrition ;
- alimentation et santé animale ;
- santé au travail ;
- santé et environnement ;
- médicament vétérinaire ;
- santé et protection du végétal ;
- produits phytopharmaceutiques, biocides et fertilisants.
"""

from __future__ import annotations

from html.parser import HTMLParser
from typing import Any
import urllib.parse

from .utilitaires import (
    journaliser,
    lire_flux,
    nettoyer_texte,
    supprimer_doublons,
    telecharger,
    telecharger_texte,
)


# ============================================================
# CONFIGURATION
# ============================================================

URL_ANNUAIRE_RSS = (
    "https://www.anses.fr/fr/content/"
    "flux-rss-de-lanses"
)

MAX_FLUX = 8
MAX_ARTICLES_PAR_FLUX = 10


THEMATIQUES = [
    {
        "mots": [
            "toutes nos actualités",
            "flux-actualites",
        ],
        "categorie": "Actualités générales",
        "priorite": 2,
    },
    {
        "mots": [
            "alimentation humaine",
            "nutrition",
            "theme-alimentation",
        ],
        "categorie": "Alimentation et nutrition humaine",
        "priorite": 5,
    },
    {
        "mots": [
            "alimentation et santé animale",
            "sante animal",
            "theme-sante-animal",
        ],
        "categorie": "Alimentation et santé animale",
        "priorite": 5,
    },
    {
        "mots": [
            "santé-travail",
            "sante-travail",
            "theme-sante-travail",
        ],
        "categorie": "Santé au travail",
        "priorite": 4,
    },
    {
        "mots": [
            "santé-environnement",
            "sante-environnement",
            "theme-sante-environnement",
        ],
        "categorie": "Santé et environnement",
        "priorite": 5,
    },
    {
        "mots": [
            "médicament vétérinaire",
            "medicament veterinaire",
            "theme-medicament",
        ],
        "categorie": "Médicament vétérinaire",
        "priorite": 4,
    },
    {
        "mots": [
            "santé et protection du végétal",
            "sante vegetal",
            "theme-sante-vegetal",
        ],
        "categorie": "Santé et protection du végétal",
        "priorite": 3,
    },
    {
        "mots": [
            "phytopharmaceutiques",
            "biocides",
            "fertilisants",
            "theme-pesticides",
        ],
        "categorie": (
            "Produits phytopharmaceutiques, "
            "biocides et fertilisants"
        ),
        "priorite": 4,
    },
]


# ============================================================
# EXTRACTION DES LIENS
# ============================================================

class ExtracteurLiens(HTMLParser):
    """
    Extrait les liens et leur libellé depuis une page HTML.
    """

    def __init__(self) -> None:
        super().__init__()
        self.liens: list[dict[str, str]] = []
        self._href = ""
        self._texte: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.lower() != "a":
            return

        attributs = dict(attrs)

        self._href = nettoyer_texte(
            attributs.get("href", "")
        )

        self._texte = []

    def handle_data(
        self,
        data: str,
    ) -> None:
        if self._href:
            self._texte.append(data)

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        if tag.lower() != "a":
            return

        if not self._href:
            return

        self.liens.append(
            {
                "href": self._href,
                "texte": nettoyer_texte(
                    " ".join(self._texte)
                ),
            }
        )

        self._href = ""
        self._texte = []


# ============================================================
# COLLECTE PRINCIPALE
# ============================================================

def collecter(
    *,
    limite_par_flux: int = MAX_ARTICLES_PAR_FLUX,
) -> list[dict[str, Any]]:
    """
    Découvre puis interroge les flux RSS officiels de l'Anses.

    Une erreur sur un flux ne bloque pas les autres.
    """
    limite_par_flux = max(
        1,
        int(limite_par_flux),
    )

    articles: list[dict[str, Any]] = []

    try:
        flux = decouvrir_flux()

    except Exception as erreur:
        journaliser(
            (
                "ANSES — impossible de lire "
                f"l'annuaire RSS : {erreur}"
            ),
            "ERREUR",
        )

        return articles

    journaliser(
        (
            "ANSES : "
            f"{len(flux)} flux officiel(s) découvert(s)."
        )
    )

    for configuration in flux:
        nom_flux = configuration["nom"]
        url = configuration["url"]
        categorie = configuration["categorie"]
        priorite = configuration["priorite"]

        try:
            contenu = telecharger(url)

            resultats = lire_flux(
                contenu,
                source="ANSES",
                requete=nom_flux,
                limite=limite_par_flux,
            )

            for article in resultats:
                article["categorie_source"] = categorie
                article["priorite_source"] = priorite
                article["organisme"] = (
                    "Agence nationale de sécurité "
                    "sanitaire de l’alimentation, "
                    "de l’environnement et du travail"
                )
                article["type_source"] = (
                    "Agence sanitaire officielle"
                )
                article["langue"] = "fr"

            articles.extend(resultats)

            journaliser(
                (
                    f"ANSES — {nom_flux} : "
                    f"{len(resultats)} article(s)."
                )
            )

        except Exception as erreur:
            journaliser(
                (
                    f"ANSES — flux indisponible "
                    f"« {nom_flux} » : {erreur}"
                ),
                "AVERTISSEMENT",
            )

    articles = supprimer_doublons(
        articles
    )

    journaliser(
        (
            "ANSES : "
            f"{len(articles)} article(s) "
            "après dédoublonnage."
        )
    )

    return articles


# ============================================================
# DÉCOUVERTE DES FLUX
# ============================================================

def decouvrir_flux() -> list[dict[str, Any]]:
    """
    Lit la page officielle des flux RSS de l'Anses
    et sélectionne les liens RSS annoncés.
    """
    page_html = telecharger_texte(
        URL_ANNUAIRE_RSS
    )

    extracteur = ExtracteurLiens()
    extracteur.feed(page_html)

    candidats: list[dict[str, Any]] = []

    for lien in extracteur.liens:
        href = lien["href"]
        texte = lien["texte"]

        url_absolue = urllib.parse.urljoin(
            URL_ANNUAIRE_RSS,
            href,
        )

        contenu_comparable = (
            f"{texte} {url_absolue}"
        ).lower()

        ressemble_a_un_flux = any(
            marqueur in contenu_comparable
            for marqueur in (
                ".rss",
                ".xml",
                "/feed",
                "rss",
                "atom",
            )
        )

        if not ressemble_a_un_flux:
            continue

        categorie, priorite = identifier_thematique(
            contenu_comparable
        )

        candidats.append(
            {
                "nom": (
                    texte
                    or categorie
                    or "Flux officiel ANSES"
                ),
                "url": url_absolue,
                "categorie": (
                    categorie
                    or "Actualités ANSES"
                ),
                "priorite": priorite,
            }
        )

    return dedoublonner_flux(
        candidats
    )[:MAX_FLUX]


def identifier_thematique(
    contenu: str,
) -> tuple[str, int]:
    """
    Associe un flux à une thématique et une priorité.
    """
    for configuration in THEMATIQUES:
        if any(
            mot.lower() in contenu
            for mot in configuration["mots"]
        ):
            return (
                str(configuration["categorie"]),
                int(configuration["priorite"]),
            )

    return "Actualités ANSES", 2


def dedoublonner_flux(
    flux: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Supprime les URL de flux en double.
    """
    resultat: list[dict[str, Any]] = []
    urls_vues: set[str] = set()

    for configuration in flux:
        url = nettoyer_texte(
            configuration.get("url", "")
        )

        cle = url.lower().rstrip("/")

        if not cle or cle in urls_vues:
            continue

        urls_vues.add(cle)
        resultat.append(configuration)

    return resultat


# ============================================================
# ALIAS EXPLICITE
# ============================================================

def collecter_anses(
    *,
    limite_par_flux: int = MAX_ARTICLES_PAR_FLUX,
) -> list[dict[str, Any]]:
    """
    Alias compatible avec un import explicite.
    """
    return collecter(
        limite_par_flux=limite_par_flux,
    )
