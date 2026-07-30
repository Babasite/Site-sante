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

from apps.monitoring.services.collecte import (
    collecter_toutes_les_sources,
)
from apps.monitoring.services.utilitaires import (
    nettoyer_texte,
)
from apps.monitoring.services.classification_legacy import (
    classifier_article,
)
from apps.monitoring.services.export import (
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
    """
    Produit un journal parlé déterministe, sans IA, traduction
    ni information inventée.
    """
    import hashlib
    import random
    import re

    ouverture = (
        "Bonjour à tous, hello everybody.\n"
        "Aujourd’hui dans l’actualité, today in the news..."
    )
    conclusion = (
        "C’était votre Journal du jour.\n"
        "Thank you for watching.\n"
        "See you tomorrow for another update."
    )

    if not articles:
        return (
            f"{ouverture}\n \n"
            "Aucune publication pertinente n’a été retenue pour cette veille.\n\n"
            f"{conclusion}"
        )

    try:
        limite = max(
            1,
            int(nombre_articles),
        )
    except (
        TypeError,
        ValueError,
    ):
        limite = 10

    selection = articles[
        :min(
            limite,
            len(articles),
        )
    ]

    etiquettes = (
        "abstract",
        "aim",
        "aims",
        "background",
        "conclusion",
        "conclusions",
        "context",
        "design",
        "discussion",
        "findings",
        "introduction",
        "method",
        "methods",
        "objective",
        "objectives",
        "purpose",
        "result",
        "results",
        "summary",
    )

    motif_etiquettes = re.compile(
        r"^(?:"
        + "|".join(
            re.escape(
                etiquette
            )
            for etiquette in etiquettes
        )
        + r")\s*(?::|[-–—])\s*",
        flags=re.IGNORECASE,
    )

    champs_revue = (
        "revue",
        "journal",
        "publication",
        "nom_revue",
        "journal_title",
        "publication_title",
        "source_revue",
    )

    formulations_avec_revue = (
        "Selon une publication parue dans {source}, {contenu}",
        "D’après des travaux publiés dans {source}, {contenu}",
        "Une étude publiée dans {source} rapporte que {contenu}",
        "Les travaux présentés dans {source} indiquent que {contenu}",
        "Une publication de {source} met en avant le fait que {contenu}",
        "Dans {source}, des chercheurs rapportent que {contenu}",
        "Autre sujet aujourd’hui : dans {source}, {contenu}",
        "Poursuivons avec une publication de {source} : {contenu}",
        "Dans un autre domaine, une étude de {source} indique que {contenu}",
        "Une autre publication, parue dans {source}, souligne que {contenu}",
    )

    formulations_avec_base = (
        "Selon une publication référencée dans {source}, {contenu}",
        "D’après des travaux recensés dans {source}, {contenu}",
        "Une étude disponible dans {source} rapporte que {contenu}",
        "Autre sujet aujourd’hui : une publication issue de {source} indique que {contenu}",
        "Poursuivons avec une étude référencée dans {source} : {contenu}",
    )

    formulations_sans_source = (
        "Selon cette publication, {contenu}",
        "D’après ces travaux, {contenu}",
        "Une nouvelle étude rapporte que {contenu}",
        "Autre sujet aujourd’hui : {contenu}",
        "Poursuivons avec une autre publication : {contenu}",
        "Dans un autre domaine, des chercheurs indiquent que {contenu}",
    )

    bases_documentaires = {
        "pubmed",
        "europe pmc",
        "crossref",
        "google scholar",
        "semantic scholar",
        "scopus",
        "web of science",
    }

    def nettoyer_debut(texte: Any) -> str:
        contenu = nettoyer_texte(
            texte
        )

        precedent = None

        while contenu and contenu != precedent:
            precedent = contenu
            contenu = motif_etiquettes.sub(
                "",
                contenu,
                count=1,
            ).lstrip()

        return contenu

    def extraire_premiere_phrase(
        texte: Any,
        longueur_maximale: int = 220,
    ) -> str:
        """
        Extrait la première phrase sans la couper au milieu d'une idée.

        Si elle dépasse la longueur maximale, une virgule, un point-virgule
        ou un deux-points n'est transformé en point que lorsque le passage
        précédent contient vraisemblablement au moins un sujet et un verbe.
        Aucun analyseur externe ni service payant n'est utilisé.
        """
        contenu = nettoyer_debut(
            texte
        )

        amorces_scientifiques = (
            r"^Using\b[^,]{0,120},\s*",
            r"^In this study,\s*",
            r"^In the present study,\s*",
            r"^Here,\s*",
            r"^Overall,\s*",
            r"^Specifically,\s*",
            r"^Conceptually,\s*",
        )

        for motif_amorce in amorces_scientifiques:
            contenu = re.sub(
                motif_amorce,
                "",
                contenu,
                count=1,
                flags=re.IGNORECASE,
            ).lstrip()

        if not contenu:
            return ""

        correspondance = re.search(
            r"(?<=[.!?])\s+",
            contenu,
        )

        if correspondance:
            contenu = contenu[
                :correspondance.start()
            ].strip()

        if len(
            contenu
        ) <= longueur_maximale:
            return contenu

        verbes_courants = {
            "am", "is", "are", "was", "were", "be", "been", "being",
            "has", "have", "had", "do", "does", "did",
            "can", "could", "may", "might", "must", "shall", "should",
            "will", "would",
            "show", "shows", "showed", "shown",
            "suggest", "suggests", "suggested",
            "indicate", "indicates", "indicated",
            "report", "reports", "reported",
            "find", "finds", "found",
            "estimate", "estimates", "estimated",
            "evaluate", "evaluates", "evaluated",
            "assess", "assesses", "assessed",
            "examine", "examines", "examined",
            "investigate", "investigates", "investigated",
            "demonstrate", "demonstrates", "demonstrated",
            "reveal", "reveals", "revealed",
            "remain", "remains", "remained",
            "increase", "increases", "increased",
            "decrease", "decreases", "decreased",
            "depend", "depends", "depended",
            "aim", "aims", "aimed",
            "include", "includes", "included",
            "involve", "involves", "involved",
            "provide", "provides", "provided",
            "use", "uses", "used",
        }

        def contient_sujet_et_verbe(segment: str) -> bool:
            mots = re.findall(
                r"[A-Za-zÀ-ÖØ-öø-ÿ]+(?:['’-][A-Za-zÀ-ÖØ-öø-ÿ]+)?",
                segment,
            )

            if len(mots) < 3:
                return False

            for position, mot in enumerate(mots):
                mot_minuscule = mot.lower()

                verbe_probable = (
                    mot_minuscule in verbes_courants
                    or (
                        len(mot_minuscule) > 4
                        and mot_minuscule.endswith(
                            (
                                "ed",
                                "ates",
                                "ises",
                                "izes",
                                "ifies",
                            )
                        )
                    )
                )

                if verbe_probable and position >= 1:
                    return True

            return False

        separateurs = list(
            re.finditer(
                r"[,;:]",
                contenu,
            )
        )

        for separateur in separateurs:
            if separateur.start() < 40:
                continue
            proposition = contenu[
                :separateur.start()
            ].strip()

            if contient_sujet_et_verbe(
                proposition
            ):
                return proposition.rstrip(
                    " ,;:-"
                ) + "."

        return contenu


    def ajuster_debut_apres_transition(texte: str) -> str:
        """
        Met en minuscule le premier mot après une transition, tout en
        préservant les sigles (COVID-19, HIV-1, WHO...) et les noms propres
        composés (Papua New Guinea, New York...).
        """
        contenu = nettoyer_texte(texte)
        if not contenu:
            return contenu

        m = re.match(r"^([A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'’-]*)(.*)$", contenu)
        if not m:
            return contenu

        premier, suite = m.groups()

        # Sigle ou mot entièrement en majuscules
        lettres = re.sub(r"[^A-Za-zÀ-ÖØ-öø-ÿ]", "", premier)
        if lettres and len(lettres) > 1 and lettres.isupper():
            return contenu

        # Nom propre composé : ex. Papua New...
        m2 = re.match(r"^\s+([A-Z][A-Za-zÀ-ÖØ-öø-ÿ'’-]+)", suite)
        if m2:
            return contenu

        return premier[:1].lower() + premier[1:] + suite

    def extraire_source_affichee(
        article: Article,
    ) -> tuple[str, bool]:
        for champ in champs_revue:
            valeur = nettoyer_texte(
                article.get(
                    champ,
                    "",
                )
            )

            if valeur:
                return valeur, True

        source = nettoyer_texte(
            article.get(
                "source",
                "",
            )
        )

        return source, False

    materiau_graine = "|".join(
        nettoyer_texte(
            valeur
        )
        for article in selection
        for valeur in (
            article.get(
                "titre",
                "",
            ),
            article.get(
                "date",
                article.get(
                    "date_brute",
                    "",
                ),
            ),
            article.get(
                "source",
                "",
            ),
        )
    )

    empreinte = hashlib.sha256(
        materiau_graine.encode(
            "utf-8",
        )
    ).hexdigest()

    generateur = random.Random(
        int(
            empreinte[
                :16
            ],
            16,
        )
    )

    sujets: list[str] = []
    index_formulations: dict[str, int] = {}
    ordres_formulations: dict[str, list[int]] = {}

    for index, article in enumerate(selection):
        contenu = extraire_premiere_phrase(
            article.get(
                "resume",
                "",
            ),
            220,
        )

        if not contenu:
            contenu = tronquer_texte(
                article.get(
                    "titre",
                    "Titre non disponible",
                ),
                300,
            ) or "Titre non disponible"

        source, est_revue = extraire_source_affichee(
            article
        )

        source_connue = (
            source
            and source.lower()
            not in {
                "source inconnue",
                "non disponible",
            }
        )

        if not source_connue:
            cle = "sans_source"
            formulations = formulations_sans_source
        elif est_revue:
            cle = "revue"
            formulations = formulations_avec_revue
        elif source.lower() in bases_documentaires:
            cle = "base"
            formulations = formulations_avec_base
        else:
            cle = "revue"
            formulations = formulations_avec_revue

        if cle not in ordres_formulations:
            ordre = list(
                range(
                    len(
                        formulations
                    )
                )
            )
            generateur.shuffle(
                ordre
            )
            ordres_formulations[
                cle
            ] = ordre

        ordre = ordres_formulations[
            cle
        ]
        position = index_formulations.get(
            cle,
            0,
        )

        # La dernière formulation doit rester compatible avec « Enfin ».
        # L'ordre déterministe est conservé : on avance simplement jusqu'à
        # la première tournure qui ne contient pas déjà une transition.
        formulations_incompatibles_avec_enfin = (
            "Poursuivons avec",
            "Autre sujet aujourd’hui",
            "Une autre publication",
        )

        if index == len(selection) - 1 and len(selection) > 1:
            for decalage in range(
                len(
                    ordre
                )
            ):
                formulation_candidate = formulations[
                    ordre[
                        (position + decalage)
                        % len(
                            ordre
                        )
                    ]
                ]

                if not formulation_candidate.startswith(
                    formulations_incompatibles_avec_enfin
                ):
                    formulation = formulation_candidate
                    position += decalage
                    break
            else:
                formulation = formulations[
                    ordre[
                        position
                        % len(
                            ordre
                        )
                    ]
                ]
        else:
            formulation = formulations[
                ordre[
                    position
                    % len(
                        ordre
                    )
                ]
            ]

        # Le premier article ne doit jamais commencer par une transition
        # qui suppose qu'un article précédent a déjà été présenté.
        if index == 0:
            formulations_interdites_premier_article = (
                "Autre sujet aujourd’hui",
                "Poursuivons avec",
                "Dans un autre domaine",
                "Une autre publication",
            )

            for decalage in range(
                len(
                    ordre
                )
            ):
                formulation_candidate = formulations[
                    ordre[
                        (position + decalage)
                        % len(
                            ordre
                        )
                    ]
                ]

                if not formulation_candidate.startswith(
                    formulations_interdites_premier_article
                ):
                    formulation = formulation_candidate
                    position += decalage
                    break

        index_formulations[
            cle
        ] = position + 1

        if index>0:
            precedent,_=extraire_source_affichee(selection[index-1])
        else:
            precedent=""
        if precedent and precedent.lower()==source.lower() and est_revue:
            sujet=f"Toujours dans {source}, {ajuster_debut_apres_transition(contenu)}"
        else:
            sujet = formulation.format(
                source=source,
                contenu=ajuster_debut_apres_transition(contenu),
            )

        if index == len(selection) - 1 and len(selection) > 1:
            sujet = "Enfin, " + sujet[
                0
            ].lower() + sujet[
                1:
            ]

        sujets.append(
            sujet
        )

    # Une ligne visuellement vide est conservée après l'ouverture,
    # sans créer un séparateur de page pour le premier article.
    blocs = [
        ouverture + "\n \n" + sujets[
            0
        ]
    ]

    if len(sujets) > 1:
        blocs.extend(
            sujets[
                1:
            ]
        )

    # La conclusion constitue toujours le dernier bloc du journal.
    # Elle ne peut donc pas disparaître si la page précédente est pleine.
    # Le séparateur entre les blocs crée systématiquement une ligne vide
    # avant « C’était votre Journal du jour. ».
    blocs.append(
        conclusion
    )

    return "\n\n".join(
        blocs
    )


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