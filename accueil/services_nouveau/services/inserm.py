"""
Collecteur Inserm.

Le module interroge plusieurs flux officiels de l'Inserm :
- salle de presse générale ;
- santé publique ;
- cancer ;
- neurosciences ;
- immunologie et infectiologie ;
- technologies pour la santé.

Les flux thématiques WordPress peuvent évoluer. Chaque appel est donc
isolé : une erreur ne bloque pas les autres, et le flux général reste
la source de repli principale.
"""

from __future__ import annotations

from typing import Any

from .utilitaires import (
    journaliser,
    lire_flux,
    supprimer_doublons,
    telecharger,
)


# ============================================================
# CONFIGURATION
# ============================================================

MAX_ARTICLES_PAR_FLUX = 8

FLUX_INSERM = [
    {
        "nom": "Salle de presse Inserm",
        "url": "https://presse.inserm.fr/feed/",
        "categorie": "Actualités et communiqués",
        "priorite": 5,
    },
    {
        "nom": "Santé publique",
        "url": (
            "https://presse.inserm.fr/category/"
            "sante-publique-communiquesdossiers/feed/"
        ),
        "categorie": "Santé publique",
        "priorite": 5,
    },
    {
        "nom": "Cancer",
        "url": (
            "https://presse.inserm.fr/category/"
            "cancer-communiquesdossiers/feed/"
        ),
        "categorie": "Cancer",
        "priorite": 4,
    },
    {
        "nom": "Neurosciences",
        "url": (
            "https://presse.inserm.fr/category/"
            "neurosciences-sciences-cognitives-"
            "neurologie-psychiatrie/feed/"
        ),
        "categorie": "Neurosciences et santé mentale",
        "priorite": 4,
    },
    {
        "nom": "Immunologie et infectiologie",
        "url": (
            "https://presse.inserm.fr/category/"
            "immunologie-inflammation-infectiologie-"
            "et-microbiologie/feed/"
        ),
        "categorie": "Immunologie et infectiologie",
        "priorite": 5,
    },
    {
        "nom": "Technologies pour la santé",
        "url": (
            "https://presse.inserm.fr/category/"
            "technologie-pour-la-sante-"
            "communiquesdossiers/feed/"
        ),
        "categorie": "Technologies pour la santé",
        "priorite": 3,
    },
]


# ============================================================
# COLLECTE PRINCIPALE
# ============================================================

def collecter(
    *,
    limite_par_flux: int = MAX_ARTICLES_PAR_FLUX,
) -> list[dict[str, Any]]:
    """
    Interroge les flux Inserm configurés.

    Une erreur sur un flux thématique ne bloque pas
    la collecte générale.
    """
    limite_par_flux = max(
        1,
        int(limite_par_flux),
    )

    articles: list[dict[str, Any]] = []

    journaliser(
        (
            "Inserm : lancement de "
            f"{len(FLUX_INSERM)} flux officiels."
        )
    )

    for configuration in FLUX_INSERM:
        nom_flux = configuration["nom"]
        url = configuration["url"]
        categorie = configuration["categorie"]
        priorite = configuration["priorite"]

        try:
            contenu = telecharger(url)

            resultats = lire_flux(
                contenu,
                source="Inserm",
                requete=nom_flux,
                limite=limite_par_flux,
            )

            for article in resultats:
                article["categorie_source"] = categorie
                article["priorite_source"] = priorite
                article["organisme"] = (
                    "Institut national de la santé "
                    "et de la recherche médicale"
                )
                article["type_source"] = (
                    "Organisme public de recherche"
                )
                article["langue"] = "fr"

            articles.extend(resultats)

            journaliser(
                (
                    f"Inserm — {nom_flux} : "
                    f"{len(resultats)} article(s)."
                )
            )

        except Exception as erreur:
            journaliser(
                (
                    f"Inserm — flux indisponible "
                    f"« {nom_flux} » : {erreur}"
                ),
                "AVERTISSEMENT",
            )

    articles = supprimer_doublons(
        articles
    )

    journaliser(
        (
            "Inserm : "
            f"{len(articles)} article(s) "
            "après dédoublonnage."
        )
    )

    return articles


# ============================================================
# ALIAS EXPLICITE
# ============================================================

def collecter_inserm(
    *,
    limite_par_flux: int = MAX_ARTICLES_PAR_FLUX,
) -> list[dict[str, Any]]:
    """
    Alias compatible avec un import explicite.
    """
    return collecter(
        limite_par_flux=limite_par_flux,
    )