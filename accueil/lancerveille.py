"""
Point d'entrée principal de la veille scientifique.

Ce module relie :

- l'orchestrateur des collecteurs ;
- la préparation des articles pour Django ;
- la production du résumé exécutif ;
- l'analyse de convergence des sources ;
- les statistiques attendues par views.py.

La fonction publique à utiliser est :

    lancer_veille_complete()
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any

from .services_nouveau.services.collecte import (
    collecter_toutes_les_sources,
)
from .services_nouveau.services.utilitaires import (
    nettoyer_texte,
)
from .services_nouveau.services.classification import (
    classifier_article,
)
from .services_nouveau.services.export import (
    exporter_tous_formats,
)
Article = dict[str, Any]


# ============================================================
# VALEURS PAR DÉFAUT
# ============================================================

CATEGORIES_PAR_DEFAUT: list[str] = []

ONE_HEALTH_PAR_DEFAUT: list[str] = []

PREUVE_PAR_DEFAUT = "Non déterminé"
NIVEAU_PREUVE_PAR_DEFAUT = 0

IMPORTANCE_PAR_DEFAUT = 0
NIVEAU_IMPORTANCE_PAR_DEFAUT = "Veille documentaire"


# ============================================================
# PRÉPARATION DES ARTICLES
# ============================================================

def convertir_liste(
    valeur: Any,
) -> list[str]:
    """
    Convertit une valeur en liste de chaînes propres.

    Accepte :

    - une liste ;
    - un tuple ;
    - un ensemble ;
    - une chaîne unique ;
    - une valeur vide.
    """
    if valeur is None:
        return []

    if isinstance(
        valeur,
        str,
    ):
        texte = nettoyer_texte(
            valeur
        )

        return [texte] if texte else []

    if isinstance(
        valeur,
        (
            list,
            tuple,
            set,
        ),
    ):
        resultat: list[str] = []

        for element in valeur:
            texte = nettoyer_texte(
                element
            )

            if texte and texte not in resultat:
                resultat.append(
                    texte
                )

        return resultat

    texte = nettoyer_texte(
        valeur
    )

    return [texte] if texte else []


def convertir_entier(
    valeur: Any,
    valeur_par_defaut: int = 0,
) -> int:
    """
    Convertit une valeur en entier sans interrompre la veille.
    """
    try:
        return int(
            valeur
        )

    except (
        TypeError,
        ValueError,
    ):
        return valeur_par_defaut


def convertir_flottant(
    valeur: Any,
    valeur_par_defaut: float = 0.0,
) -> float:
    """
    Convertit une valeur en nombre décimal.
    """
    try:
        return float(
            valeur
        )

    except (
        TypeError,
        ValueError,
    ):
        return valeur_par_defaut


def preparer_article(
    article: Article,
) -> Article:
    """
    Garantit la présence des champs utilisés par Django.

    Cette fonction ne remplace pas une future classification
    approfondie. Elle sécurise uniquement le format transmis
    à la vue et à la base de données.
    """
    resultat = deepcopy(
        article
    )

    resultat["titre"] = nettoyer_texte(
        resultat.get(
            "titre",
            "Titre non disponible",
        )
    ) or "Titre non disponible"

    resultat["source"] = nettoyer_texte(
        resultat.get(
            "source",
            "Source inconnue",
        )
    ) or "Source inconnue"

    resultat["lien"] = nettoyer_texte(
        resultat.get(
            "lien",
            "",
        )
    )

    resultat["date"] = nettoyer_texte(
        resultat.get(
            "date",
            "Date non disponible",
        )
    ) or "Date non disponible"

    resultat["date_brute"] = nettoyer_texte(
        resultat.get(
            "date_brute",
            "",
        )
    )

    resultat["resume"] = nettoyer_texte(
        resultat.get(
            "resume",
            "",
        )
    )

    resultat["requete"] = nettoyer_texte(
        resultat.get(
            "requete",
            "",
        )
    )

    resultat["categories"] = convertir_liste(
        resultat.get(
            "categories",
            CATEGORIES_PAR_DEFAUT,
        )
    )

    resultat["one_health"] = convertir_liste(
        resultat.get(
            "one_health",
            ONE_HEALTH_PAR_DEFAUT,
        )
    )

    resultat["preuve"] = nettoyer_texte(
        resultat.get(
            "preuve",
            PREUVE_PAR_DEFAUT,
        )
    ) or PREUVE_PAR_DEFAUT

    resultat["niveau_preuve"] = convertir_entier(
        resultat.get(
            "niveau_preuve",
            NIVEAU_PREUVE_PAR_DEFAUT,
        ),
        NIVEAU_PREUVE_PAR_DEFAUT,
    )

    resultat["importance"] = convertir_entier(
        resultat.get(
            "importance",
            IMPORTANCE_PAR_DEFAUT,
        ),
        IMPORTANCE_PAR_DEFAUT,
    )

    resultat["niveau_importance"] = nettoyer_texte(
        resultat.get(
            "niveau_importance",
            NIVEAU_IMPORTANCE_PAR_DEFAUT,
        )
    ) or NIVEAU_IMPORTANCE_PAR_DEFAUT

    resultat["raisons"] = convertir_liste(
        resultat.get(
            "raisons",
            [],
        )
    )

    resultat["mots_detectes"] = convertir_liste(
        resultat.get(
            "mots_detectes",
            [],
        )
    )

    resultat["score"] = convertir_flottant(
        resultat.get(
            "score",
            resultat.get(
                "importance",
                0,
            ),
        )
    )

    return resultat


def preparer_articles(
    articles: list[Article],
) -> list[Article]:
    """
    Prépare, classe et trie les articles.
    """
    resultat: list[Article] = []

    for article in articles:
        if not isinstance(article, dict):
            continue

        article_prepare = preparer_article(article)

        try:
            article_classe = classifier_article(article_prepare)
            if isinstance(article_classe, dict):
                article_prepare.update(article_classe)
                article_prepare = preparer_article(article_prepare)
        except Exception as erreur:
            raisons = convertir_liste(article_prepare.get("raisons", []))
            raisons.append(f"Classification non appliquée : {type(erreur).__name__}.")
            article_prepare["raisons"] = raisons
            article_prepare["erreur_classification"] = str(erreur)

        resultat.append(article_prepare)

    resultat.sort(
        key=lambda article: (
            -convertir_flottant(article.get("score", article.get("importance", 0))),
            -convertir_entier(article.get("importance", 0)),
            -convertir_entier(article.get("priorite_source", 0)),
            nettoyer_texte(article.get("titre", "")).lower(),
        )
    )

    return resultat

# ============================================================
# RÉSUMÉ EXÉCUTIF
# ============================================================

def tronquer_texte(
    texte: Any,
    longueur_maximale: int = 280,
) -> str:
    """
    Tronque un texte sans couper brutalement un mot.
    """
    contenu = nettoyer_texte(
        texte
    )

    if len(
        contenu
    ) <= longueur_maximale:
        return contenu

    contenu = contenu[
        :longueur_maximale
    ]

    if " " in contenu:
        contenu = contenu.rsplit(
            " ",
            1,
        )[0]

    return contenu.rstrip(
        " ,;:-"
    ) + "…"


def generer_resume_executif(
    articles: list[Article],
    *,
    nombre_articles: int = 10,
) -> str:
    """Produit un résumé déterministe, sans IA et sans information inventée."""
    if not articles:
        return "Aucune publication pertinente n’a été retenue pour cette veille."

    selection = articles[:max(1, int(nombre_articles))]
    compteur_sources: Counter[str] = Counter()
    compteur_categories: Counter[str] = Counter()

    for article in articles:
        source = nettoyer_texte(article.get("source", "Source inconnue"))
        if source:
            compteur_sources[source] += 1
        for categorie in convertir_liste(article.get("categories", [])):
            compteur_categories[categorie] += 1

    lignes = [
        f"{len(articles)} publication(s) ont été retenue(s) par le moteur de veille."
    ]

    sources = [source for source, _ in compteur_sources.most_common(5)]
    if sources:
        lignes.append("Sources principalement représentées : " + ", ".join(sources) + ".")

    categories = [categorie for categorie, _ in compteur_categories.most_common(5)]
    if categories:
        lignes.append("Thématiques les plus représentées : " + ", ".join(categories) + ".")

    lignes.extend(["", "Principales publications sélectionnées :"])
    for article in selection[:5]:
        titre = nettoyer_texte(article.get("titre", "Titre non disponible"))
        source = nettoyer_texte(article.get("source", "Source inconnue"))
        date = nettoyer_texte(article.get("date", ""))
        reference = source + (f", {date}" if date else "")
        lignes.append(f"– {titre} ({reference}).")

    lignes.extend([
        "",
        "Ce résumé est produit automatiquement à partir des métadonnées des publications. Il ne constitue pas une analyse scientifique de leurs résultats.",
    ])
    return "\n".join(lignes)


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


# ============================================================
# STATISTIQUES
# ============================================================

def construire_statistiques(
    rapport: dict[str, Any],
    articles: list[Article],
) -> dict[str, Any]:
    """
    Convertit le rapport de l'orchestrateur au format attendu
    par la vue Django existante.
    """
    articles_recuperes = convertir_entier(
        rapport.get(
            "articles_avant_dedoublonnage",
            rapport.get(
                "articles_bruts",
                len(
                    articles
                ),
            ),
        )
    )

    statistiques = {
        "sources_interrogees": convertir_entier(
            rapport.get(
                "sources_interrogees",
                0,
            )
        ),
        "sources_reussies": convertir_entier(
            rapport.get(
                "sources_reussies",
                0,
            )
        ),
        "sources_en_erreur": convertir_entier(
            rapport.get(
                "sources_en_erreur",
                0,
            )
        ),
        "articles_recuperes": articles_recuperes,
        "articles_retenus": len(
            articles
        ),
        "doublons_supprimes": convertir_entier(
            rapport.get(
                "doublons_supprimes",
                0,
            )
        ),
        "duree_secondes": round(
            convertir_flottant(
                rapport.get(
                    "duree_secondes",
                    0,
                )
            ),
            2,
        ),
        "statut": nettoyer_texte(
            rapport.get(
                "statut",
                "",
            )
        ),
        "details": deepcopy(
            rapport.get(
                "collecteurs",
                [],
            )
        ),
        "erreurs": deepcopy(
            rapport.get(
                "erreurs",
                [],
            )
        ),
    }

    return statistiques


# ============================================================
# POINT D'ENTRÉE PUBLIC
# ============================================================

def lancer_veille_complete() -> tuple[
    list[Article],
    str,
    str,
    dict[str, Any],
]:
    """
    Lance la veille complète.
    """
    articles_bruts, rapport = collecter_toutes_les_sources()

    resultats = preparer_articles(articles_bruts)
    resume = generer_resume_executif(resultats)
    convergence = generer_convergence(resultats)
    statistiques = construire_statistiques(rapport, resultats)

    try:
        exports = exporter_tous_formats(resultats, rapport)
        statistiques["exports"] = {
            fmt: str(path)
            for fmt, path in exports.items()
        }
    except Exception as erreur:
        statistiques["exports"] = {}
        statistiques["erreur_export"] = f"{type(erreur).__name__}: {erreur}"

    return (
        resultats,
        resume,
        convergence,
        statistiques,
    )

__all__ = [
    "construire_statistiques",
    "generer_convergence",
    "generer_resume_executif",
    "lancer_veille_complete",
    "preparer_article",
    "preparer_articles",
]
