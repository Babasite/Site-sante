"""
Analyse de convergence des sources.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from apps.monitoring.services.utilitaires import (
    nettoyer_texte,
)

from apps.monitoring.services.donnees import (
    convertir_liste,
)

Article = dict[str, Any]

# ============================================================
# CONVERGENCE DES SOURCES
# ============================================================

def generer_convergence(
    articles: list[Article],
) -> str:
    """
    Décrit les éléments communs réellement présents.

    La convergence est établie uniquement à partir des catégories,
    dimensions One Health et sources renseignées dans les articles.
    """
    if not articles:
        return ""

    compteur_sources: Counter[str] = Counter()
    compteur_categories: Counter[str] = Counter()
    compteur_one_health: Counter[str] = Counter()

    for article in articles:
        source = nettoyer_texte(
            article.get(
                "source",
                "",
            )
        )

        if source:
            compteur_sources[
                source
            ] += 1

        for categorie in convertir_liste(
            article.get(
                "categories",
                [],
            )
        ):
            compteur_categories[
                categorie
            ] += 1

        for dimension in convertir_liste(
            article.get(
                "one_health",
                [],
            )
        ):
            compteur_one_health[
                dimension
            ] += 1

    lignes: list[str] = []

    sources_multiples = [
        (
            source,
            nombre,
        )
        for source, nombre
        in compteur_sources.most_common()
        if nombre > 1
    ]

    if sources_multiples:
        lignes.append(
            "Répartition principale des publications : "
            + ", ".join(
                f"{source} ({nombre})"
                for source, nombre
                in sources_multiples[:5]
            )
            + "."
        )

    categories_recurrentes = [
        (
            categorie,
            nombre,
        )
        for categorie, nombre
        in compteur_categories.most_common()
        if nombre > 1
    ]

    if categories_recurrentes:
        lignes.append(
            "Thématiques retrouvées dans plusieurs résultats : "
            + ", ".join(
                f"{categorie} ({nombre})"
                for categorie, nombre
                in categories_recurrentes[:5]
            )
            + "."
        )

    dimensions_recurrentes = [
        (
            dimension,
            nombre,
        )
        for dimension, nombre
        in compteur_one_health.most_common()
        if nombre > 1
    ]

    if dimensions_recurrentes:
        lignes.append(
            "Dimensions One Health récurrentes : "
            + ", ".join(
                f"{dimension} ({nombre})"
                for dimension, nombre
                in dimensions_recurrentes[:5]
            )
            + "."
        )

    if not lignes:
        if len(
            compteur_sources
        ) > 1:
            return (
                "Plusieurs sources ont fourni des résultats, "
                "mais aucune convergence thématique ne peut être "
                "établie avec les métadonnées actuellement disponibles."
            )

        return (
            "Les métadonnées disponibles ne permettent pas encore "
            "d’établir une convergence entre plusieurs sources."
        )

    return "\n".join(
        lignes
    )

__all__ = [
    "generer_convergence",
]