"""
Orchestrateur du moteur de veille V2 de Découverte Santé.

Ce module :

- charge les collecteurs déclarés dans configuration.py ;
- exécute chaque source active ;
- empêche l'échec d'une source de bloquer toute la veille ;
- contrôle le format minimal des articles ;
- supprime les doublons entre toutes les sources ;
- limite le volume final ;
- produit un rapport détaillé de collecte.

Il ne contient aucune URL ni configuration propre aux sources.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import importlib
import time
from typing import Any, Callable

from .configuration import (
    CHAMPS_ARTICLE_OBLIGATOIRES,
    CONTINUER_SI_ARTICLE_INVALIDE,
    CONTINUER_SI_SOURCE_EN_ERREUR,
    LEVER_ERREUR_SI_AUCUN_ARTICLE,
    MAX_ARTICLES_BRUTS,
    MAX_ARTICLES_RETENUS,
    creer_repertoires,
    obtenir_collecteurs,
    verifier_configuration,
)

from .utilitaires import (
    journaliser,
    nettoyer_texte,
    supprimer_doublons,
)


Article = dict[str, Any]
ConfigurationCollecteur = dict[str, Any]
FonctionCollecteur = Callable[..., list[Article]]


# ============================================================
# RAPPORT DE LA DERNIÈRE COLLECTE
# ============================================================

DERNIER_RAPPORT_COLLECTE: dict[str, Any] = {}


def obtenir_dernier_rapport_collecte() -> dict[str, Any]:
    """
    Retourne une copie du dernier rapport de collecte.
    """
    return deepcopy(
        DERNIER_RAPPORT_COLLECTE
    )


# ============================================================
# CHARGEMENT DES COLLECTEURS
# ============================================================

def charger_module(
    nom_module: str,
):
    """
    Charge un module du même paquet Python que l'orchestrateur.

    Exemple :
        nom_module = "pubmed"
    """
    nom_module = nettoyer_texte(
        nom_module
    )

    if not nom_module:
        raise ValueError(
            "Le nom du module collecteur est vide."
        )

    paquet = __package__

    if paquet:
        return importlib.import_module(
            f".{nom_module}",
            package=paquet,
        )

    return importlib.import_module(
        nom_module
    )


def charger_fonction_collecteur(
    configuration: ConfigurationCollecteur,
) -> FonctionCollecteur:
    """
    Charge la fonction publique d'un collecteur.

    La configuration doit contenir :

    - module ;
    - fonction.
    """
    nom_module = nettoyer_texte(
        configuration.get(
            "module",
            "",
        )
    )

    nom_fonction = nettoyer_texte(
        configuration.get(
            "fonction",
            "",
        )
    )

    if not nom_module:
        raise ValueError(
            "Module de collecteur non renseigné."
        )

    if not nom_fonction:
        raise ValueError(
            (
                "Fonction de collecteur non renseignée "
                f"pour le module {nom_module}."
            )
        )

    module = charger_module(
        nom_module
    )

    fonction = getattr(
        module,
        nom_fonction,
        None,
    )

    if fonction is None:
        raise AttributeError(
            (
                f"La fonction {nom_fonction} "
                f"est absente du module {nom_module}."
            )
        )

    if not callable(fonction):
        raise TypeError(
            (
                f"{nom_module}.{nom_fonction} "
                "n'est pas appelable."
            )
        )

    return fonction


# ============================================================
# CONTRÔLE DES ARTICLES
# ============================================================

def article_est_valide(
    article: Any,
) -> tuple[bool, list[str]]:
    """
    Vérifie qu'un article possède le format minimal attendu.

    Retourne :

        (valide, erreurs)
    """
    erreurs: list[str] = []

    if not isinstance(
        article,
        dict,
    ):
        return (
            False,
            [
                (
                    "L'article retourné par le collecteur "
                    "n'est pas un dictionnaire."
                )
            ],
        )

    for champ in CHAMPS_ARTICLE_OBLIGATOIRES:
        if champ not in article:
            erreurs.append(
                f"Champ absent : {champ}."
            )

    titre = nettoyer_texte(
        article.get(
            "titre",
            "",
        )
    )

    lien = nettoyer_texte(
        article.get(
            "lien",
            "",
        )
    )

    source = nettoyer_texte(
        article.get(
            "source",
            "",
        )
    )

    if not titre:
        erreurs.append(
            "Titre vide."
        )

    if not lien:
        erreurs.append(
            "Lien vide."
        )

    if not source:
        erreurs.append(
            "Source vide."
        )

    return (
        not erreurs,
        erreurs,
    )


def normaliser_article(
    article: Article,
    configuration: ConfigurationCollecteur,
) -> Article:
    """
    Harmonise les champs fondamentaux d'un article.

    Les données déjà fournies par le collecteur sont conservées.
    """
    resultat = dict(
        article
    )

    resultat["source"] = nettoyer_texte(
        resultat.get(
            "source",
            configuration.get(
                "nom",
                "",
            ),
        )
    )

    resultat["titre"] = nettoyer_texte(
        resultat.get(
            "titre",
            "",
        )
    )

    resultat["lien"] = nettoyer_texte(
        resultat.get(
            "lien",
            "",
        )
    )

    resultat["date"] = nettoyer_texte(
        resultat.get(
            "date",
            "",
        )
    )

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

    resultat.setdefault(
        "organisme",
        configuration.get(
            "nom",
            "",
        ),
    )

    resultat.setdefault(
        "type_source",
        configuration.get(
            "type_source",
            "",
        ),
    )

    resultat.setdefault(
        "priorite_source",
        configuration.get(
            "priorite_source",
            1,
        ),
    )

    resultat.setdefault(
        "langue",
        configuration.get(
            "langue",
            "",
        ),
    )

    resultat["identifiant_collecteur"] = (
        configuration.get(
            "identifiant",
            "",
        )
    )

    return resultat


def preparer_articles_collecteur(
    articles: Any,
    configuration: ConfigurationCollecteur,
) -> tuple[list[Article], list[dict[str, Any]]]:
    """
    Vérifie et normalise les résultats d'un collecteur.

    Retourne :

        articles_valides, erreurs_articles
    """
    articles_valides: list[Article] = []
    erreurs_articles: list[dict[str, Any]] = []

    if articles is None:
        return (
            articles_valides,
            [
                {
                    "index": None,
                    "erreurs": [
                        (
                            "Le collecteur a retourné None "
                            "au lieu d'une liste."
                        )
                    ],
                }
            ],
        )

    if not isinstance(
        articles,
        list,
    ):
        return (
            articles_valides,
            [
                {
                    "index": None,
                    "erreurs": [
                        (
                            "Le collecteur n'a pas retourné "
                            "une liste."
                        )
                    ],
                }
            ],
        )

    for index, article in enumerate(
        articles
    ):
        valide, erreurs = article_est_valide(
            article
        )

        if not valide:
            erreurs_articles.append(
                {
                    "index": index,
                    "erreurs": erreurs,
                }
            )

            if CONTINUER_SI_ARTICLE_INVALIDE:
                continue

            raise ValueError(
                (
                    "Article invalide retourné par "
                    f"{configuration.get('nom', 'collecteur')} "
                    f"à l'index {index} : "
                    f"{' '.join(erreurs)}"
                )
            )

        articles_valides.append(
            normaliser_article(
                article,
                configuration,
            )
        )

    return (
        articles_valides,
        erreurs_articles,
    )


# ============================================================
# EXÉCUTION D'UN COLLECTEUR
# ============================================================

def executer_collecteur(
    configuration: ConfigurationCollecteur,
) -> tuple[list[Article], dict[str, Any]]:
    """
    Exécute un collecteur et retourne ses articles et son rapport.
    """
    identifiant = nettoyer_texte(
        configuration.get(
            "identifiant",
            "",
        )
    )

    nom = nettoyer_texte(
        configuration.get(
            "nom",
            identifiant,
        )
    )

    heure_debut = datetime.now()
    instant_debut = time.monotonic()

    rapport: dict[str, Any] = {
        "identifiant": identifiant,
        "nom": nom,
        "module": configuration.get(
            "module",
            "",
        ),
        "fonction": configuration.get(
            "fonction",
            "",
        ),
        "statut": "en_cours",
        "heure_debut": heure_debut.isoformat(),
        "heure_fin": None,
        "duree_secondes": 0.0,
        "articles_bruts": 0,
        "articles_valides": 0,
        "articles_invalides": 0,
        "erreurs_articles": [],
        "erreur": None,
    }

    journaliser(
        f"{nom} : démarrage du collecteur."
    )

    try:
        fonction = charger_fonction_collecteur(
            configuration
        )

        parametres = configuration.get(
            "parametres",
            {},
        )

        if not isinstance(
            parametres,
            dict,
        ):
            raise TypeError(
                (
                    "Les paramètres du collecteur "
                    f"{nom} doivent former un dictionnaire."
                )
            )

        resultat = fonction(
            **parametres
        )

        nombre_brut = (
            len(resultat)
            if isinstance(
                resultat,
                list,
            )
            else 0
        )

        articles, erreurs_articles = (
            preparer_articles_collecteur(
                resultat,
                configuration,
            )
        )

        rapport["articles_bruts"] = nombre_brut
        rapport["articles_valides"] = len(
            articles
        )
        rapport["articles_invalides"] = len(
            erreurs_articles
        )
        rapport["erreurs_articles"] = (
            erreurs_articles
        )
        rapport["statut"] = "termine"

        journaliser(
            (
                f"{nom} : "
                f"{len(articles)} article(s) valide(s)."
            )
        )

        return (
            articles,
            rapport,
        )

    except Exception as erreur:
        rapport["statut"] = "erreur"
        rapport["erreur"] = (
            f"{type(erreur).__name__} : {erreur}"
        )

        journaliser(
            (
                f"{nom} : échec du collecteur — "
                f"{erreur}"
            ),
            "ERREUR",
        )

        if not CONTINUER_SI_SOURCE_EN_ERREUR:
            raise

        return (
            [],
            rapport,
        )

    finally:
        heure_fin = datetime.now()

        rapport["heure_fin"] = (
            heure_fin.isoformat()
        )

        rapport["duree_secondes"] = round(
            time.monotonic() - instant_debut,
            3,
        )


# ============================================================
# COLLECTE GLOBALE
# ============================================================

def collecter_toutes_les_sources() -> tuple[
    list[Article],
    dict[str, Any],
]:
    """
    Lance tous les collecteurs actifs.

    Retourne :

        articles, rapport
    """
    global DERNIER_RAPPORT_COLLECTE

    verifier_configuration()
    creer_repertoires()

    collecteurs = obtenir_collecteurs(
        actifs_uniquement=True
    )

    heure_debut = datetime.now()
    instant_debut = time.monotonic()

    rapport: dict[str, Any] = {
        "moteur": "Découverte Santé — veille V2",
        "statut": "en_cours",
        "heure_debut": heure_debut.isoformat(),
        "heure_fin": None,
        "duree_secondes": 0.0,
        "sources_prevues": len(
            collecteurs
        ),
        "sources_interrogees": 0,
        "sources_reussies": 0,
        "sources_en_erreur": 0,
        "articles_bruts": 0,
        "articles_valides": 0,
        "articles_avant_dedoublonnage": 0,
        "articles_apres_dedoublonnage": 0,
        "doublons_supprimes": 0,
        "articles_retenus": 0,
        "limite_brute_atteinte": False,
        "limite_finale_atteinte": False,
        "collecteurs": [],
        "erreurs": [],
    }

    tous_les_articles: list[Article] = []

    journaliser(
        (
            "Moteur V2 : lancement de "
            f"{len(collecteurs)} collecteur(s)."
        )
    )

    try:
        for configuration in collecteurs:
            if len(
                tous_les_articles
            ) >= MAX_ARTICLES_BRUTS:
                rapport[
                    "limite_brute_atteinte"
                ] = True

                journaliser(
                    (
                        "Limite globale d'articles bruts "
                        "atteinte. Les collecteurs suivants "
                        "ne seront pas exécutés."
                    ),
                    "AVERTISSEMENT",
                )

                break

            articles, rapport_collecteur = (
                executer_collecteur(
                    configuration
                )
            )

            rapport["sources_interrogees"] += 1
            rapport["collecteurs"].append(
                rapport_collecteur
            )

            rapport["articles_bruts"] += int(
                rapport_collecteur.get(
                    "articles_bruts",
                    0,
                )
            )

            rapport["articles_valides"] += len(
                articles
            )

            if (
                rapport_collecteur.get(
                    "statut"
                )
                == "termine"
            ):
                rapport["sources_reussies"] += 1

            else:
                rapport["sources_en_erreur"] += 1

                erreur = rapport_collecteur.get(
                    "erreur"
                )

                if erreur:
                    rapport["erreurs"].append(
                        {
                            "source": (
                                rapport_collecteur.get(
                                    "nom",
                                    "",
                                )
                            ),
                            "erreur": erreur,
                        }
                    )

            place_restante = (
                MAX_ARTICLES_BRUTS
                - len(
                    tous_les_articles
                )
            )

            if place_restante <= 0:
                rapport[
                    "limite_brute_atteinte"
                ] = True
                break

            tous_les_articles.extend(
                articles[:place_restante]
            )

            if len(
                articles
            ) > place_restante:
                rapport[
                    "limite_brute_atteinte"
                ] = True
                break

        rapport[
            "articles_avant_dedoublonnage"
        ] = len(
            tous_les_articles
        )

        articles_uniques = supprimer_doublons(
            tous_les_articles
        )

        rapport[
            "articles_apres_dedoublonnage"
        ] = len(
            articles_uniques
        )

        rapport["doublons_supprimes"] = (
            len(
                tous_les_articles
            )
            - len(
                articles_uniques
            )
        )

        if (
            len(
                articles_uniques
            )
            > MAX_ARTICLES_RETENUS
        ):
            rapport[
                "limite_finale_atteinte"
            ] = True

        articles_retenus = articles_uniques[
            :MAX_ARTICLES_RETENUS
        ]

        rapport["articles_retenus"] = len(
            articles_retenus
        )

        if (
            not articles_retenus
            and LEVER_ERREUR_SI_AUCUN_ARTICLE
        ):
            raise RuntimeError(
                (
                    "Aucun article n'a été récupéré "
                    "par les collecteurs actifs."
                )
            )

        rapport["statut"] = (
            "termine_avec_erreurs"
            if rapport["sources_en_erreur"]
            else "termine"
        )

        journaliser(
            (
                "Moteur V2 : collecte terminée — "
                f"{rapport['articles_retenus']} article(s), "
                f"{rapport['doublons_supprimes']} doublon(s) "
                "supprimé(s)."
            )
        )

        return (
            articles_retenus,
            rapport,
        )

    except Exception as erreur:
        rapport["statut"] = "erreur"

        rapport["erreurs"].append(
            {
                "source": "orchestrateur",
                "erreur": (
                    f"{type(erreur).__name__} : {erreur}"
                ),
            }
        )

        journaliser(
            (
                "Moteur V2 : erreur générale — "
                f"{erreur}"
            ),
            "ERREUR",
        )

        raise

    finally:
        heure_fin = datetime.now()

        rapport["heure_fin"] = (
            heure_fin.isoformat()
        )

        rapport["duree_secondes"] = round(
            time.monotonic() - instant_debut,
            3,
        )

        DERNIER_RAPPORT_COLLECTE = deepcopy(
            rapport
        )


# ============================================================
# ALIAS DE COMPATIBILITÉ
# ============================================================

def collecter_articles() -> list[Article]:
    """
    Lance la collecte complète et retourne uniquement les articles.

    Cet alias permet de remplacer progressivement l'ancien
    ``collecter_articles`` sans modifier immédiatement tout le projet.
    """
    articles, _rapport = (
        collecter_toutes_les_sources()
    )

    return articles


def lancer_collecte() -> tuple[
    list[Article],
    dict[str, Any],
]:
    """
    Alias explicite retournant les articles et le rapport.
    """
    return collecter_toutes_les_sources()


__all__ = [
    "collecter_articles",
    "collecter_toutes_les_sources",
    "executer_collecteur",
    "lancer_collecte",
    "obtenir_dernier_rapport_collecte",
]