"""
Collecteur Haute Autorité de santé (HAS).

Le module interroge plusieurs flux RSS officiels de la HAS :
- recommandations et guides ;
- dispositifs médicaux ;
- médicaments ;
- accès précoces ;
- avis économiques ;
- actualités ;
- certification, évaluation et indicateurs ;
- bulletin officiel.

Chaque flux est isolé : une erreur ne bloque pas les autres.
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

MAX_ARTICLES_PAR_FLUX = 10

FLUX_HAS = [
    {
        "nom": "Recommandations et guides",
        "url": (
            "https://www.has-sante.fr/jcms/"
            "c_1771214/fr/feed/Rss2.jsp?id=p_3081452"
        ),
        "categorie": "Recommandations",
        "priorite": 5,
    },
    {
        "nom": "Avis sur les dispositifs médicaux",
        "url": (
            "https://www.has-sante.fr/jcms/"
            "c_1771214/fr/feed/Rss2.jsp?id=p_3081446"
        ),
        "categorie": "Dispositifs médicaux",
        "priorite": 4,
    },
    {
        "nom": "Avis sur les médicaments",
        "url": (
            "https://www.has-sante.fr/jcms/"
            "c_1771214/fr/feed/Rss2.jsp?id=p_3081449"
        ),
        "categorie": "Médicaments",
        "priorite": 4,
    },
    {
        "nom": "Décisions sur les accès précoces",
        "url": (
            "https://www.has-sante.fr/jcms/"
            "c_1771214/fr/feed/Rss2.jsp?id=p_3298842"
        ),
        "categorie": "Accès précoce",
        "priorite": 4,
    },
    {
        "nom": "Avis économiques",
        "url": (
            "https://www.has-sante.fr/jcms/"
            "c_1771214/fr/feed/Rss2.jsp?id=p_3081454"
        ),
        "categorie": "Évaluation économique",
        "priorite": 3,
    },
    {
        "nom": "Actualités",
        "url": (
            "https://www.has-sante.fr/jcms/"
            "c_1771214/fr/feed/Rss2.jsp?id=p_3081656"
        ),
        "categorie": "Actualités",
        "priorite": 2,
    },
    {
        "nom": (
            "Certification, évaluation des établissements "
            "et indicateurs"
        ),
        "url": (
            "https://www.has-sante.fr/jcms/"
            "c_1771214/fr/feed/Rss2.jsp?id=p_3082237"
        ),
        "categorie": "Qualité et sécurité des soins",
        "priorite": 3,
    },
    {
        "nom": "Bulletin officiel",
        "url": (
            "https://www.has-sante.fr/jcms/"
            "c_1771214/fr/feed/Rss2.jsp?id=p_3113093"
        ),
        "categorie": "Bulletin officiel",
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
    Interroge tous les flux HAS configurés.

    Retourne une liste d'articles au format commun du projet.
    """
    limite_par_flux = max(
        1,
        int(limite_par_flux),
    )

    articles: list[dict[str, Any]] = []

    journaliser(
        (
            "HAS : lancement de "
            f"{len(FLUX_HAS)} flux officiels."
        )
    )

    for configuration in FLUX_HAS:
        nom_flux = configuration["nom"]
        url = configuration["url"]
        categorie = configuration["categorie"]
        priorite = configuration["priorite"]

        try:
            contenu = telecharger(url)

            resultats = lire_flux(
                contenu,
                source="HAS",
                requete=nom_flux,
                limite=limite_par_flux,
            )

            for article in resultats:
                article["categorie_source"] = categorie
                article["priorite_source"] = priorite
                article["organisme"] = (
                    "Haute Autorité de santé"
                )
                article["type_source"] = (
                    "Autorité sanitaire officielle"
                )
                article["langue"] = "fr"

            articles.extend(resultats)

            journaliser(
                (
                    f"HAS — {nom_flux} : "
                    f"{len(resultats)} article(s)."
                )
            )

        except Exception as erreur:
            journaliser(
                (
                    f"HAS — erreur pour "
                    f"« {nom_flux} » : {erreur}"
                ),
                "ERREUR",
            )

    articles = supprimer_doublons(
        articles
    )

    journaliser(
        (
            "HAS : "
            f"{len(articles)} article(s) "
            "après dédoublonnage."
        )
    )

    return articles


# ============================================================
# ALIAS EXPLICITE
# ============================================================

def collecter_has(
    *,
    limite_par_flux: int = MAX_ARTICLES_PAR_FLUX,
) -> list[dict[str, Any]]:
    """
    Alias pratique, compatible avec un import explicite.
    """
    return collecter(
        limite_par_flux=limite_par_flux,
    )