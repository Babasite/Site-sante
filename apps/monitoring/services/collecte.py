"""
Façade publique du moteur de collecte V2.

Ce module constitue l'API stable utilisée par le reste de l'application
(Django, commandes de gestion, tests et API).

Toute la logique d'orchestration est centralisée dans ``orchestrateur.py``
afin d'éviter toute duplication et de préserver la rétrocompatibilité.
"""

from __future__ import annotations

from typing import Any, TypeAlias

from .orchestrateur import (
    collecter_articles as _collecter_articles,
    collecter_toutes_les_sources,
    executer_collecteur,
    lancer_collecte,
    obtenir_dernier_rapport_collecte,
)


Article: TypeAlias = dict[str, Any]
RapportCollecte: TypeAlias = dict[str, Any]


def collecter_articles() -> list[Article]:
    """
    Lance tous les collecteurs actifs et retourne uniquement les articles.

    Cette fonction conserve le nom utilisé par l'ancien moteur.
    """
    return _collecter_articles()


def collecter_articles_avec_rapport() -> tuple[
    list[Article],
    RapportCollecte,
]:
    """
    Lance tous les collecteurs actifs et retourne les articles avec le rapport.

    Returns:
        Un tuple contenant :
        - la liste des articles collectés ;
        - le rapport détaillé de collecte.
    """
    return collecter_toutes_les_sources()


def collecter() -> list[Article]:
    """
    Alias court de :func:`collecter_articles`.
    """
    return _collecter_articles()


__all__ = [
    "collecter",
    "collecter_articles",
    "collecter_articles_avec_rapport",
    "collecter_toutes_les_sources",
    "executer_collecteur",
    "lancer_collecte",
    "obtenir_dernier_rapport_collecte",
]