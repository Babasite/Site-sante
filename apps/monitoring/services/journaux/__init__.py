"""
Production du journal parlé et du résumé exécutif.
"""

from __future__ import annotations

from typing import Any

from apps.monitoring.services.utilitaires import (
    nettoyer_texte,
)

Article = dict[str, Any]

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

__all__ = [
    "generer_resume_executif",
    "tronquer_texte",
]