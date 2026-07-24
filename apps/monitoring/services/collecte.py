"""
Façade de collecte du moteur de veille V2.

La logique d'orchestration est centralisée dans orchestrateur.py.
Ce module fournit des fonctions simples et compatibles avec le reste
de l'application, sans dupliquer la logique de collecte.
"""

from __future__ import annotations

from typing import Any

from .orchestrateur import (
    collecter_articles as _collecter_articles,
    collecter_toutes_les_sources,
    executer_collecteur,
    lancer_collecte,
    obtenir_dernier_rapport_collecte,
)


Article = dict[str, Any]
RapportCollecte = dict[str, Any]


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
    Lance tous les collecteurs actifs.

    Retourne :
        - la liste des articles ;
        - le rapport détaillé de collecte.
    """
    return collecter_toutes_les_sources()


def collecter() -> list[Article]:
    """
    Alias court de collecter_articles().
    """
    return collecter_articles()


__all__ = [
    "collecter",
    "collecter_articles",
    "collecter_articles_avec_rapport",
    "collecter_toutes_les_sources",
    "executer_collecteur",
    "lancer_collecte",
    "obtenir_dernier_rapport_collecte",
]