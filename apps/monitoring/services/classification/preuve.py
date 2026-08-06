"""
Évaluation déterministe, explicable et configurable du niveau de preuve.

Version 5.

Le module identifie les principaux plans d'étude, distingue les protocoles des
résultats, applique les alertes d'intégrité éditoriale et fournit un audit
stable. Aucune IA ni dépendance externe n'est utilisée.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
from typing import TYPE_CHECKING, Any, Final, Literal, TypedDict

if TYPE_CHECKING:
    from .pipeline import EtatClassification

from .utils import (
    construire_texte,
    contient_expression,
    dedupliquer,
    normaliser,
)


VERSION_PREUVE: Final[str] = "6.0.0"
ENGINE_VERSION: Final[str] = "5.0"
RULESET_VERSION: Final[str] = "2026.03"


StatutPublication = Literal[
    "Protocole",
    "Analyse secondaire",
    "Résultats principaux ou statut non précisé",
]

TypeAjustement = Literal[
    "aucun",
    "protocole",
    "integrite",
]

NiveauConfiancePreuve = Literal[
    "indeterminee",
    "faible",
    "moderee",
    "elevee",
]

StatutReglePreuve = Literal[
    "declenchee",
    "non_declenchee",
]

NiveauContradiction = Literal[
    "aucune",
    "moderee",
    "forte",
]

ClassePreuve = Literal[
    "indeterminee",
    "tres_faible",
    "faible",
    "moderee",
    "forte",
    "tres_forte",
]

MaturitePublication = Literal[
    "invalide",
    "immature",
    "secondaire",
    "principale",
]

QualiteEntreePreuve = Literal[
    "vide",
    "partielle",
    "exploitable",
]

NiveauRobustesse = Literal[
    "nulle",
    "faible",
    "moderee",
    "forte",
]


class PreuveDetectee(TypedDict):
    """Preuve détectée et informations ayant conduit à sa détection."""

    nom: str
    niveau: int
    niveau_initial: int
    priorite: int
    priorite_initiale: int
    correspondances: list[str]
    ajustements: list[str]


class AjustementPreuve(TypedDict):
    """Ajustement appliqué au niveau de preuve dominant."""

    type: TypeAjustement
    motif: str
    niveau_avant: int
    niveau_apres: int


class TraceReglePreuve(TypedDict):
    """Trace d'évaluation d'une règle de preuve."""

    ordre: int
    identifiant: str
    statut: StatutReglePreuve
    niveau: int
    priorite: int
    correspondances: list[str]


class FacteurConfiance(TypedDict):
    """Facteur explicable ayant influencé la confiance."""

    code: str
    points: int
    raison: str


class AuditPreuve(TypedDict):
    """Informations de reproductibilité et de traçabilité."""

    engine_version: str
    ruleset_version: str
    empreinte_analyse: str
    configuration_hash: str
    referentiel_hash: str
    regles_evaluees: int
    regles_declenchees: int
    couverture_referentiel: int
    correspondances_total: int
    integrite_inconnue: list[str]
    preuve_dominante_identifiant: str | None
    preuve_secondaire_identifiant: str | None
    journal_regles: list[TraceReglePreuve]


class ResultatPreuve(TypedDict):
    """Structure publique retournée par l'analyse complète."""

    preuve: str
    niveau_preuve: int
    niveau_preuve_initial: int
    score_preuve: int
    classe_preuve: ClassePreuve
    confiance_preuve: NiveauConfiancePreuve
    score_confiance: int
    robustesse: NiveauRobustesse
    qualite_entree: QualiteEntreePreuve
    facteurs_confiance: list[FacteurConfiance]
    raison_preuve: str
    preuves_detectees: list[PreuveDetectee]
    statut_publication: StatutPublication
    integrite_publication: list[str]
    ajustements: list[AjustementPreuve]
    nombre_preuves_detectees: int
    contradiction_detectee: bool
    indice_contradiction: int
    niveau_contradiction: NiveauContradiction
    ecart_niveaux: int
    marge_preuve_dominante: int
    preuve_dominante_stable: bool
    preuve_secondaire: str | None
    maturite_publication: MaturitePublication
    alertes_qualite: list[str]
    alertes_critiques: list[str]
    regles_declenchees: list[str]
    audit: AuditPreuve
    synthese: str
    configuration: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ReglePreuve:
    """Règle déclarative de détection d'un type d'étude."""

    identifiant: str
    nom: str
    expressions: tuple[str, ...]
    niveau: int
    priorite: int

    def __post_init__(self) -> None:
        if not self.identifiant.strip():
            raise ValueError("identifiant ne peut pas être vide.")
        if not self.nom.strip():
            raise ValueError("nom ne peut pas être vide.")
        if not self.expressions:
            raise ValueError(
                f"La règle {self.identifiant!r} doit contenir une expression."
            )
        if isinstance(self.niveau, bool) or not isinstance(self.niveau, int):
            raise TypeError("niveau doit être un entier.")
        if not 1 <= self.niveau <= 5:
            raise ValueError("niveau doit être compris entre 1 et 5.")
        if isinstance(self.priorite, bool) or not isinstance(
            self.priorite,
            int,
        ):
            raise TypeError("priorite doit être un entier.")
        if self.priorite < 0:
            raise ValueError("priorite doit être positive ou nulle.")


@dataclass(frozen=True, slots=True)
class ConfigurationPreuve:
    """Configuration des ajustements et seuils du moteur."""

    niveau_max_protocole: int = 1
    priorite_max_protocole: int = 15
    niveau_article_retracte: int = 0
    niveau_max_publication_retiree: int = 1
    niveau_max_expression_preoccupation: int = 2
    ecart_contradiction: int = 3
    seuil_contradiction_forte: int = 60
    marge_dominance_stable: int = 10
    points_par_niveau: int = 18
    bonus_priorite_max: int = 10
    refuser_integrite_inconnue: bool = False
    confiance_base: int = 35
    confiance_bonus_preuve_unique: int = 25
    confiance_bonus_preuve_stable: int = 20
    confiance_bonus_maturite_principale: int = 15
    confiance_malus_contradiction_forte: int = 25
    confiance_malus_integrite: int = 40
    confiance_malus_protocole: int = 40

    def __post_init__(self) -> None:
        valeurs = asdict(self)
        refuser_integrite_inconnue = valeurs.pop(
            "refuser_integrite_inconnue"
        )

        if not isinstance(refuser_integrite_inconnue, bool):
            raise TypeError(
                "refuser_integrite_inconnue doit être un booléen."
            )

        for nom, valeur in valeurs.items():
            if isinstance(valeur, bool) or not isinstance(valeur, int):
                raise TypeError(f"{nom} doit être un entier.")

        if not 0 <= self.niveau_max_protocole <= 5:
            raise ValueError(
                "niveau_max_protocole doit être compris entre 0 et 5."
            )
        if self.priorite_max_protocole < 0:
            raise ValueError(
                "priorite_max_protocole doit être positive ou nulle."
            )
        if not 0 <= self.niveau_article_retracte <= 5:
            raise ValueError(
                "niveau_article_retracte doit être compris entre 0 et 5."
            )
        if not 0 <= self.niveau_max_publication_retiree <= 5:
            raise ValueError(
                "niveau_max_publication_retiree doit être compris entre 0 et 5."
            )
        if not 0 <= self.niveau_max_expression_preoccupation <= 5:
            raise ValueError(
                "niveau_max_expression_preoccupation doit être compris "
                "entre 0 et 5."
            )
        if self.ecart_contradiction < 1:
            raise ValueError(
                "ecart_contradiction doit être strictement positif."
            )

        if not 1 <= self.seuil_contradiction_forte <= 100:
            raise ValueError(
                "seuil_contradiction_forte doit être compris entre 1 et 100."
            )

        if self.marge_dominance_stable < 0:
            raise ValueError(
                "marge_dominance_stable doit être positive ou nulle."
            )

        if self.points_par_niveau <= 0:
            raise ValueError(
                "points_par_niveau doit être strictement positif."
            )

        if not 0 <= self.bonus_priorite_max <= 100:
            raise ValueError(
                "bonus_priorite_max doit être compris entre 0 et 100."
            )

        for nom in (
            "confiance_base",
            "confiance_bonus_preuve_unique",
            "confiance_bonus_preuve_stable",
            "confiance_bonus_maturite_principale",
            "confiance_malus_contradiction_forte",
            "confiance_malus_integrite",
            "confiance_malus_protocole",
        ):
            valeur = getattr(self, nom)
            if not 0 <= valeur <= 100:
                raise ValueError(
                    f"{nom} doit être compris entre 0 et 100."
                )


CONFIGURATION_PAR_DEFAUT = ConfigurationPreuve()


REGLES_PREUVE: Final[tuple[ReglePreuve, ...]] = (
    ReglePreuve(
        "recommandation_officielle",
        "Recommandation officielle fondée sur les preuves",
        (
            "evidence based guideline",
            "evidence based recommendation",
            "clinical practice guideline",
            "public health guideline",
            "recommandation fondee sur les preuves",
            "recommandation de pratique clinique",
        ),
        5,
        100,
    ),
    ReglePreuve(
        "revue_parapluie",
        "Revue parapluie",
        (
            "umbrella review",
            "overview of systematic reviews",
            "revue parapluie",
        ),
        5,
        95,
    ),
    ReglePreuve(
        "meta_analyse",
        "Méta-analyse",
        (
            "meta analysis",
            "meta analytic",
            "meta analyse",
        ),
        5,
        90,
    ),
    ReglePreuve(
        "revue_systematique",
        "Revue systématique",
        (
            "systematic review",
            "living systematic review",
            "revue systematique",
        ),
        5,
        85,
    ),
    ReglePreuve(
        "essai_phase_iii_randomise",
        "Essai clinique randomisé de phase III",
        (
            "phase iii randomized",
            "phase iii randomised",
            "randomized phase iii",
            "randomised phase iii",
            "essai randomise de phase iii",
        ),
        4,
        80,
    ),
    ReglePreuve(
        "essai_phase_iii",
        "Essai clinique de phase III",
        (
            "phase iii trial",
            "phase 3 trial",
            "phase iii study",
            "phase 3 study",
            "essai de phase iii",
            "etude de phase iii",
        ),
        4,
        78,
    ),
    ReglePreuve(
        "essai_randomise",
        "Essai clinique randomisé",
        (
            "randomized controlled trial",
            "randomised controlled trial",
            "randomized trial",
            "randomised trial",
            "cluster randomized trial",
            "cluster randomised trial",
            "essai controle randomise",
            "essai comparatif randomise",
            "essai randomise",
        ),
        4,
        75,
    ),
    ReglePreuve(
        "intervention_non_randomisee",
        "Étude d'intervention non randomisée",
        (
            "non randomized trial",
            "non randomised trial",
            "quasi experimental study",
            "controlled before after study",
            "interrupted time series",
            "etude quasi experimentale",
            "essai non randomise",
        ),
        3,
        70,
    ),
    ReglePreuve(
        "cohorte_prospective",
        "Étude de cohorte prospective",
        (
            "prospective cohort",
            "longitudinal cohort",
            "cohorte prospective",
            "cohorte longitudinale",
        ),
        3,
        65,
    ),
    ReglePreuve(
        "cohorte_retrospective",
        "Étude de cohorte rétrospective",
        (
            "retrospective cohort",
            "historical cohort",
            "cohorte retrospective",
        ),
        3,
        62,
    ),
    ReglePreuve(
        "cas_temoins",
        "Étude cas-témoins",
        (
            "case control study",
            "case control",
            "nested case control",
            "etude cas temoins",
        ),
        3,
        60,
    ),
    ReglePreuve(
        "etude_diagnostique",
        "Étude diagnostique",
        (
            "diagnostic accuracy study",
            "diagnostic validation study",
            "sensitivity and specificity",
            "etude de precision diagnostique",
            "etude de validation diagnostique",
        ),
        3,
        58,
    ),
    ReglePreuve(
        "etude_transversale",
        "Étude transversale",
        (
            "cross sectional study",
            "cross sectional survey",
            "etude transversale",
        ),
        2,
        55,
    ),
    ReglePreuve(
        "etude_ecologique_surveillance",
        "Étude écologique ou de surveillance",
        (
            "ecological study",
            "surveillance study",
            "population surveillance",
            "sentinel surveillance",
            "etude ecologique",
            "etude de surveillance",
            "surveillance sentinelle",
        ),
        2,
        50,
    ),
    ReglePreuve(
        "etude_modelisation",
        "Étude de modélisation",
        (
            "modelling study",
            "modeling study",
            "mathematical model",
            "simulation study",
            "etude de modelisation",
            "modele mathematique",
        ),
        2,
        45,
    ),
    ReglePreuve(
        "etude_qualitative",
        "Étude qualitative",
        (
            "qualitative study",
            "focus group study",
            "semi structured interviews",
            "etude qualitative",
            "entretiens semi structures",
        ),
        2,
        40,
    ),
    ReglePreuve(
        "serie_rapport_cas",
        "Série ou rapport de cas",
        (
            "case series",
            "case report",
            "serie de cas",
            "rapport de cas",
        ),
        1,
        35,
    ),
    ReglePreuve(
        "pilote_preuve_concept",
        "Étude pilote ou preuve de concept",
        (
            "pilot study",
            "feasibility study",
            "proof of concept",
            "etude pilote",
            "etude de faisabilite",
            "preuve de concept",
        ),
        1,
        30,
    ),
    ReglePreuve(
        "prepublication_preliminaire",
        "Prépublication ou résultats préliminaires",
        (
            "preprint",
            "not peer reviewed",
            "preliminary results",
            "interim analysis",
            "prepublication",
            "non evalue par les pairs",
            "resultats preliminaires",
            "analyse intermediaire",
        ),
        1,
        25,
    ),
    ReglePreuve(
        "revue_portee_narrative",
        "Revue de portée ou revue narrative",
        (
            "scoping review",
            "narrative review",
            "rapid review",
            "revue de portee",
            "revue narrative",
            "revue rapide",
        ),
        2,
        20,
    ),
    ReglePreuve(
        "avis_expert_commentaire",
        "Avis d'experts ou commentaire",
        (
            "expert opinion",
            "editorial",
            "commentary",
            "perspective article",
            "avis d expert",
            "commentaire",
        ),
        1,
        10,
    ),
)


TERMES_PROTOCOLE: Final[tuple[str, ...]] = (
    "study protocol",
    "trial protocol",
    "protocol paper",
    "registered protocol",
    "protocol for a systematic review",
    "protocole d etude",
    "protocole d essai",
    "article de protocole",
    "protocole enregistre",
)

TERMES_ANALYSE_SECONDAIRE: Final[tuple[str, ...]] = (
    "secondary analysis",
    "post hoc analysis",
    "subgroup analysis",
    "exploratory analysis",
    "secondary outcome analysis",
    "analyse secondaire",
    "analyse post hoc",
    "analyse de sous groupe",
    "analyse exploratoire",
)

INTEGRITE_PUBLICATION_AUTORISEE: Final[tuple[str, ...]] = (
    "Article rétracté",
    "Publication retirée",
    "Expression de préoccupation",
)



def _verifier_referentiels() -> None:
    """Valide les règles et expressions au chargement du module."""
    identifiants: set[str] = set()
    noms: set[str] = set()

    for regle in REGLES_PREUVE:
        if regle.identifiant in identifiants:
            raise ValueError(
                f"Identifiant de règle dupliqué : {regle.identifiant!r}."
            )
        if regle.nom in noms:
            raise ValueError(
                f"Nom de preuve dupliqué : {regle.nom!r}."
            )

        identifiants.add(regle.identifiant)
        noms.add(regle.nom)

        expressions_vues: set[str] = set()
        for expression in regle.expressions:
            if not isinstance(expression, str):
                raise TypeError(
                    f"Expression non textuelle dans {regle.identifiant!r}."
                )
            normalisee = normaliser(expression)
            if not normalisee:
                raise ValueError(
                    f"Expression vide dans {regle.identifiant!r}."
                )
            if normalisee in expressions_vues:
                raise ValueError(
                    f"Expression dupliquée dans {regle.identifiant!r} : "
                    f"{expression!r}."
                )
            expressions_vues.add(normalisee)


_verifier_referentiels()


def _normaliser_sequence(
    valeurs: Sequence[str],
    *,
    nom: str,
) -> list[str]:
    """Valide et déduplique une séquence textuelle."""
    if isinstance(valeurs, (str, bytes)):
        raise TypeError(f"{nom} doit être une séquence de chaînes.")

    resultat: list[str] = []
    for valeur in valeurs:
        if not isinstance(valeur, str):
            raise TypeError(
                f"Chaque élément de {nom} doit être une chaîne."
            )
        propre = " ".join(valeur.split())
        if propre:
            resultat.append(propre)

    return list(dedupliquer(resultat))


def _correspondances(
    texte_normalise: str,
    expressions: Iterable[str],
) -> list[str]:
    """Retourne les expressions présentes dans un texte normalisé."""
    return [
        expression
        for expression in expressions
        if contient_expression(
            texte_normalise,
            normaliser(expression),
        )
    ]


def _contient_un_des(
    texte_normalise: str,
    expressions: Sequence[str],
) -> bool:
    return bool(_correspondances(texte_normalise, expressions))



def _empreinte_json(objet: Any) -> str:
    """Calcule une empreinte SHA-256 stable."""
    serialise = json.dumps(
        objet,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialise.encode("utf-8")).hexdigest()


def _configuration_hash(
    configuration: ConfigurationPreuve,
) -> str:
    """Retourne l'empreinte stable de la configuration."""
    return _empreinte_json(asdict(configuration))


def _referentiel_hash() -> str:
    """Retourne l'empreinte stable du référentiel de preuve."""
    charge = {
        "ruleset_version": RULESET_VERSION,
        "regles": [
            {
                "identifiant": regle.identifiant,
                "nom": regle.nom,
                "expressions": list(regle.expressions),
                "niveau": regle.niveau,
                "priorite": regle.priorite,
            }
            for regle in REGLES_PREUVE
        ],
        "termes_protocole": TERMES_PROTOCOLE,
        "termes_analyse_secondaire": TERMES_ANALYSE_SECONDAIRE,
        "integrite_autorisee": INTEGRITE_PUBLICATION_AUTORISEE,
    }
    return _empreinte_json(charge)


def _empreinte_analyse(
    *,
    texte_normalise: str,
    integrite_publication: Sequence[str],
    configuration: ConfigurationPreuve,
) -> str:
    """Identifie de façon déterministe une analyse complète."""
    return _empreinte_json(
        {
            "texte": texte_normalise,
            "integrite_publication": list(integrite_publication),
            "configuration": asdict(configuration),
            "engine_version": ENGINE_VERSION,
            "ruleset_version": RULESET_VERSION,
        }
    )


def _journal_regles(
    texte_normalise: str,
) -> list[TraceReglePreuve]:
    """Construit le journal complet des règles évaluées."""
    traces: list[TraceReglePreuve] = []

    for ordre, regle in enumerate(REGLES_PREUVE, start=1):
        correspondances = _correspondances(
            texte_normalise,
            regle.expressions,
        )
        traces.append(
            {
                "ordre": ordre,
                "identifiant": regle.identifiant,
                "statut": (
                    "declenchee"
                    if correspondances
                    else "non_declenchee"
                ),
                "niveau": regle.niveau,
                "priorite": regle.priorite,
                "correspondances": list(
                    dedupliquer(correspondances)
                ),
            }
        )

    return traces



def _normaliser_integrite(
    valeurs: Sequence[str],
    *,
    configuration: ConfigurationPreuve,
) -> tuple[list[str], list[str]]:
    """Normalise les alertes d'intégrité vers leurs libellés canoniques."""
    nettoyees = _normaliser_sequence(
        valeurs,
        nom="integrite_publication",
    )
    index = {
        normaliser(libelle): libelle
        for libelle in INTEGRITE_PUBLICATION_AUTORISEE
    }

    reconnues: list[str] = []
    inconnues: list[str] = []

    for valeur in nettoyees:
        canonique = index.get(normaliser(valeur))
        if canonique is None:
            inconnues.append(valeur)
        else:
            reconnues.append(canonique)

    reconnues = list(dedupliquer(reconnues))
    inconnues = list(dedupliquer(inconnues))

    if configuration.refuser_integrite_inconnue and inconnues:
        raise ValueError(
            "Alertes d'intégrité inconnues : "
            + ", ".join(inconnues)
        )

    return reconnues, inconnues


def _calculer_score_preuve(
    *,
    niveau: int,
    priorite: int,
    configuration: ConfigurationPreuve,
) -> int:
    """Convertit niveau et priorité en score explicable sur 100."""
    if niveau <= 0:
        return 0

    bonus_priorite = min(
        configuration.bonus_priorite_max,
        max(0, priorite // 10),
    )
    return min(
        100,
        niveau * configuration.points_par_niveau + bonus_priorite,
    )


def _classer_score_preuve(score: int) -> ClassePreuve:
    """Classe un score de preuve borné entre 0 et 100."""
    if score <= 0:
        return "indeterminee"
    if score < 25:
        return "tres_faible"
    if score < 45:
        return "faible"
    if score < 65:
        return "moderee"
    if score < 85:
        return "forte"
    return "tres_forte"


def _determiner_maturite(
    *,
    statut: StatutPublication,
    niveau: int,
    integrite: Sequence[str],
) -> MaturitePublication:
    """Qualifie la maturité éditoriale et méthodologique."""
    if "Article rétracté" in integrite or niveau <= 0:
        return "invalide"
    if statut == "Protocole":
        return "immature"
    if statut == "Analyse secondaire":
        return "secondaire"
    return "principale"


def _construire_alertes_qualite(
    *,
    statut: StatutPublication,
    integrite: Sequence[str],
    integrite_inconnue: Sequence[str],
    contradiction: NiveauContradiction,
    preuve_dominante_stable: bool,
) -> list[str]:
    """Construit les alertes de qualité sans modifier le score."""
    alertes: list[str] = []

    if statut == "Protocole":
        alertes.append(
            "Le document décrit un protocole et non des résultats."
        )
    elif statut == "Analyse secondaire":
        alertes.append(
            "Le document rapporte une analyse secondaire."
        )

    if integrite:
        alertes.append(
            "Une alerte d'intégrité éditoriale est présente."
        )
    if integrite_inconnue:
        alertes.append(
            "Certaines alertes d'intégrité ne sont pas reconnues."
        )
    if contradiction != "aucune":
        alertes.append(
            "Des plans d'étude de niveaux éloignés coexistent."
        )
    if not preuve_dominante_stable:
        alertes.append(
            "La preuve dominante est proche de la preuve suivante."
        )

    return alertes




def _determiner_qualite_entree(
    *,
    texte_normalise: str,
    preuves: Sequence[PreuveDetectee],
) -> QualiteEntreePreuve:
    """Qualifie la richesse minimale de l'entrée."""
    if not texte_normalise:
        return "vide"
    if not preuves:
        return "partielle"
    return "exploitable"


def _identifiant_preuve(
    preuve: PreuveDetectee | None,
) -> str | None:
    """Retrouve l'identifiant stable d'une preuve détectée."""
    if preuve is None:
        return None

    nom = preuve["nom"].removeprefix("Protocole — ")
    for regle in REGLES_PREUVE:
        if regle.nom == nom:
            return regle.identifiant
    return None


def _calculer_confiance_detaillee(
    *,
    preuves: Sequence[PreuveDetectee],
    niveau: int,
    statut: StatutPublication,
    maturite: MaturitePublication,
    contradiction: NiveauContradiction,
    preuve_dominante_stable: bool,
    integrite: Sequence[str],
    configuration: ConfigurationPreuve,
) -> tuple[int, list[FacteurConfiance]]:
    """Calcule une confiance heuristique, déterministe et explicable."""
    facteurs: list[FacteurConfiance] = []
    score = configuration.confiance_base

    facteurs.append(
        {
            "code": "base",
            "points": configuration.confiance_base,
            "raison": "Confiance de base du moteur déterministe.",
        }
    )

    if len(preuves) == 1:
        points = configuration.confiance_bonus_preuve_unique
        score += points
        facteurs.append(
            {
                "code": "preuve_unique",
                "points": points,
                "raison": "Un seul plan d'étude domine sans ambiguïté.",
            }
        )

    if preuve_dominante_stable and preuves:
        points = configuration.confiance_bonus_preuve_stable
        score += points
        facteurs.append(
            {
                "code": "dominance_stable",
                "points": points,
                "raison": "La preuve dominante est nettement séparée.",
            }
        )

    if maturite == "principale" and niveau > 0:
        points = configuration.confiance_bonus_maturite_principale
        score += points
        facteurs.append(
            {
                "code": "maturite_principale",
                "points": points,
                "raison": "Le document rapporte des résultats principaux.",
            }
        )

    if contradiction == "forte":
        points = -configuration.confiance_malus_contradiction_forte
        score += points
        facteurs.append(
            {
                "code": "contradiction_forte",
                "points": points,
                "raison": "Des niveaux de preuve très éloignés coexistent.",
            }
        )

    if integrite:
        points = -configuration.confiance_malus_integrite
        score += points
        facteurs.append(
            {
                "code": "alerte_integrite",
                "points": points,
                "raison": "Une alerte d'intégrité éditoriale est présente.",
            }
        )

    if statut == "Protocole":
        points = -configuration.confiance_malus_protocole
        score += points
        facteurs.append(
            {
                "code": "protocole",
                "points": points,
                "raison": "Le document décrit un protocole sans résultats.",
            }
        )

    if niveau <= 0:
        score = 0

    return max(0, min(100, score)), facteurs


def _determiner_robustesse(
    *,
    score_confiance: int,
    niveau: int,
    maturite: MaturitePublication,
) -> NiveauRobustesse:
    """Traduit la confiance et la maturité en robustesse opérationnelle."""
    if niveau <= 0 or maturite == "invalide":
        return "nulle"
    if score_confiance < 40:
        return "faible"
    if score_confiance < 70:
        return "moderee"
    return "forte"


def _construire_alertes_critiques(
    *,
    maturite: MaturitePublication,
    integrite: Sequence[str],
    niveau: int,
) -> list[str]:
    """Retourne uniquement les alertes bloquantes ou majeures."""
    alertes: list[str] = []

    if "Article rétracté" in integrite:
        alertes.append(
            "Publication rétractée : la preuve ne doit pas être utilisée."
        )
    elif "Publication retirée" in integrite:
        alertes.append(
            "Publication retirée : utilisation fortement déconseillée."
        )

    if maturite == "immature":
        alertes.append(
            "Protocole sans résultats : ne pas interpréter comme preuve acquise."
        )

    if niveau <= 0 and not alertes:
        alertes.append(
            "Aucun niveau de preuve exploitable n'a été établi."
        )

    return alertes



def _calculer_indice_contradiction(
    preuves: Sequence[PreuveDetectee],
) -> tuple[int, int]:
    """Retourne l'indice de contradiction et l'écart de niveaux."""
    niveaux = sorted(
        {
            preuve["niveau_initial"]
            for preuve in preuves
        }
    )
    if len(niveaux) < 2:
        return 0, 0

    ecart = niveaux[-1] - niveaux[0]
    indice = round(ecart / 5 * 100)
    return indice, ecart


def _niveau_contradiction(
    *,
    indice: int,
    contradiction_detectee: bool,
    configuration: ConfigurationPreuve,
) -> NiveauContradiction:
    """Traduit l'indice de contradiction en classe lisible."""
    if not contradiction_detectee:
        return "aucune"
    if indice >= configuration.seuil_contradiction_forte:
        return "forte"
    return "moderee"


def _marge_preuve_dominante(
    preuves: Sequence[PreuveDetectee],
) -> int:
    """Calcule l'écart de priorité entre les deux meilleures preuves."""
    if len(preuves) < 2:
        return preuves[0]["priorite"] if preuves else 0

    premiere = preuves[0]
    seconde = preuves[1]
    return (
        (premiere["niveau"] - seconde["niveau"]) * 100
        + premiere["priorite"]
        - seconde["priorite"]
    )


def _construire_synthese(
    *,
    preuve: str,
    niveau: int,
    confiance: NiveauConfiancePreuve,
    statut: StatutPublication,
    contradiction: NiveauContradiction,
    nombre_preuves: int,
    score_preuve: int,
    classe_preuve: ClassePreuve,
    maturite: MaturitePublication,
    score_confiance: int,
    robustesse: NiveauRobustesse,
) -> str:
    """Construit une synthèse courte et stable."""
    return (
        f"Preuve : {preuve}. Niveau : {niveau}/5. "
        f"Confiance : {confiance}. Statut : {statut}. "
        f"Score : {score_preuve}/100 ({classe_preuve}). "
        f"Maturité : {maturite}. "
        f"Confiance déterministe : {score_confiance}/100. "
        f"Robustesse : {robustesse}. "
        f"Types détectés : {nombre_preuves}. "
        f"Contradiction : {contradiction}."
    )



def detecter_statut_publication_dans_texte(
    texte: str,
) -> StatutPublication:
    """Distingue protocole, analyse secondaire et résultats principaux."""
    if not isinstance(texte, str):
        raise TypeError("texte doit être une chaîne.")

    texte_normalise = normaliser(texte)

    if _contient_un_des(texte_normalise, TERMES_PROTOCOLE):
        return "Protocole"

    if _contient_un_des(
        texte_normalise,
        TERMES_ANALYSE_SECONDAIRE,
    ):
        return "Analyse secondaire"

    return "Résultats principaux ou statut non précisé"


def detecter_statut_publication(
    article: Mapping[str, Any] | None,
) -> StatutPublication:
    """Détecte le statut de publication d'un article."""
    if article is not None and not isinstance(article, Mapping):
        raise TypeError(
            "article doit être compatible avec Mapping ou None."
        )

    return detecter_statut_publication_dans_texte(
        construire_texte(article)
    )


def detecter_preuves_dans_texte(
    texte: str,
    *,
    configuration: ConfigurationPreuve = CONFIGURATION_PAR_DEFAUT,
) -> list[PreuveDetectee]:
    """Retourne toutes les preuves détectées, triées par dominance."""
    if not isinstance(texte, str):
        raise TypeError("texte doit être une chaîne.")
    if not isinstance(configuration, ConfigurationPreuve):
        raise TypeError(
            "configuration doit être une instance de ConfigurationPreuve."
        )

    texte_normalise = normaliser(texte)
    statut = detecter_statut_publication_dans_texte(texte_normalise)
    preuves: list[PreuveDetectee] = []

    for regle in REGLES_PREUVE:
        correspondances = _correspondances(
            texte_normalise,
            regle.expressions,
        )
        if not correspondances:
            continue

        niveau = regle.niveau
        priorite = regle.priorite
        ajustements: list[str] = []

        if statut == "Protocole":
            niveau = min(
                niveau,
                configuration.niveau_max_protocole,
            )
            priorite = min(
                priorite,
                configuration.priorite_max_protocole,
            )
            ajustements.append(
                "Niveau et priorité plafonnés car le texte décrit "
                "un protocole."
            )

        nom = (
            f"Protocole — {regle.nom}"
            if statut == "Protocole"
            else regle.nom
        )

        preuves.append(
            {
                "nom": nom,
                "niveau": niveau,
                "niveau_initial": regle.niveau,
                "priorite": priorite,
                "priorite_initiale": regle.priorite,
                "correspondances": list(
                    dedupliquer(correspondances)
                ),
                "ajustements": ajustements,
            }
        )

    return sorted(
        preuves,
        key=lambda preuve: (
            preuve["niveau"],
            preuve["priorite"],
            preuve["nom"],
        ),
        reverse=True,
    )


def detecter_preuves(
    article: Mapping[str, Any] | None,
    *,
    configuration: ConfigurationPreuve = CONFIGURATION_PAR_DEFAUT,
) -> list[PreuveDetectee]:
    """Détecte toutes les preuves présentes dans un article."""
    if article is not None and not isinstance(article, Mapping):
        raise TypeError(
            "article doit être compatible avec Mapping ou None."
        )

    return detecter_preuves_dans_texte(
        construire_texte(article),
        configuration=configuration,
    )


def selectionner_preuve(
    preuves: Sequence[PreuveDetectee],
) -> tuple[str, int, str]:
    """Sélectionne la preuve dominante et construit une explication stable."""
    if isinstance(preuves, (str, bytes)):
        raise TypeError("preuves doit être une séquence de preuves.")

    if not preuves:
        return (
            "Non déterminé",
            0,
            "Le niveau de preuve n’a pas pu être déterminé automatiquement.",
        )

    meilleure = preuves[0]
    autres = list(
        dedupliquer(
            preuve["nom"]
            for preuve in preuves[1:]
        )
    )

    raison = f"Niveau de preuve détecté : {meilleure['nom']}."

    if meilleure["ajustements"]:
        raison += " " + " ".join(meilleure["ajustements"])

    if autres:
        raison += (
            " Autres types d’étude repérés : "
            + ", ".join(autres)
            + "."
        )

    return (
        meilleure["nom"],
        meilleure["niveau"],
        raison,
    )


def ajuster_preuve_integrite(
    preuve: str,
    niveau_preuve: int,
    raison_preuve: str,
    integrite_publication: Sequence[str],
    *,
    configuration: ConfigurationPreuve = CONFIGURATION_PAR_DEFAUT,
) -> tuple[str, int, str]:
    """Déclasse la preuve selon les alertes d'intégrité éditoriale."""
    if not isinstance(preuve, str):
        raise TypeError("preuve doit être une chaîne.")
    if isinstance(niveau_preuve, bool) or not isinstance(
        niveau_preuve,
        int,
    ):
        raise TypeError("niveau_preuve doit être un entier.")
    if not 0 <= niveau_preuve <= 5:
        raise ValueError(
            "niveau_preuve doit être compris entre 0 et 5."
        )
    if not isinstance(raison_preuve, str):
        raise TypeError("raison_preuve doit être une chaîne.")
    if not isinstance(configuration, ConfigurationPreuve):
        raise TypeError(
            "configuration doit être une instance de ConfigurationPreuve."
        )

    integrite, _ = _normaliser_integrite(
        integrite_publication,
        configuration=configuration,
    )

    if "Article rétracté" in integrite:
        return (
            f"Publication rétractée — {preuve}",
            configuration.niveau_article_retracte,
            "Publication rétractée : niveau de preuve ramené à zéro.",
        )

    if "Publication retirée" in integrite:
        return (
            f"Publication retirée — {preuve}",
            min(
                niveau_preuve,
                configuration.niveau_max_publication_retiree,
            ),
            "Publication retirée : niveau de preuve fortement déclassé.",
        )

    if "Expression de préoccupation" in integrite:
        return (
            f"Sous préoccupation éditoriale — {preuve}",
            min(
                niveau_preuve,
                configuration.niveau_max_expression_preoccupation,
            ),
            raison_preuve
            + " Une expression de préoccupation limite "
            "la confiance accordée.",
        )

    return preuve, niveau_preuve, raison_preuve


def _niveau_confiance(
    niveau: int,
) -> NiveauConfiancePreuve:
    """Traduit le niveau numérique en classe lisible."""
    if niveau <= 0:
        return "indeterminee"
    if niveau <= 2:
        return "faible"
    if niveau <= 3:
        return "moderee"
    return "elevee"


def _detecter_contradiction(
    preuves: Sequence[PreuveDetectee],
    *,
    configuration: ConfigurationPreuve,
) -> bool:
    """Détecte la coexistence de preuves très éloignées."""
    niveaux = {
        preuve["niveau_initial"]
        for preuve in preuves
    }
    if len(niveaux) < 2:
        return False

    return max(niveaux) - min(niveaux) >= configuration.ecart_contradiction


def analyser_preuve_dans_texte(
    texte: str,
    *,
    integrite_publication: Sequence[str] = (),
    configuration: ConfigurationPreuve = CONFIGURATION_PAR_DEFAUT,
) -> ResultatPreuve:
    """Produit le profil de preuve complet depuis un texte."""
    if not isinstance(texte, str):
        raise TypeError("texte doit être une chaîne.")
    if not isinstance(configuration, ConfigurationPreuve):
        raise TypeError(
            "configuration doit être une instance de ConfigurationPreuve."
        )

    integrite, integrite_inconnue = _normaliser_integrite(
        integrite_publication,
        configuration=configuration,
    )
    texte_normalise = normaliser(texte)
    journal_regles = _journal_regles(texte_normalise)

    preuves = detecter_preuves_dans_texte(
        texte,
        configuration=configuration,
    )
    preuve_initiale, niveau_initial, raison_initiale = (
        selectionner_preuve(preuves)
    )

    preuve, niveau, raison = ajuster_preuve_integrite(
        preuve_initiale,
        niveau_initial,
        raison_initiale,
        integrite,
        configuration=configuration,
    )

    ajustements: list[AjustementPreuve] = []

    if preuves and preuves[0]["niveau"] != preuves[0]["niveau_initial"]:
        ajustements.append(
            {
                "type": "protocole",
                "motif": (
                    "Le texte décrit un protocole : le niveau théorique "
                    "de l'étude a été plafonné."
                ),
                "niveau_avant": preuves[0]["niveau_initial"],
                "niveau_apres": preuves[0]["niveau"],
            }
        )

    if niveau != niveau_initial:
        ajustements.append(
            {
                "type": "integrite",
                "motif": (
                    "Une alerte d'intégrité éditoriale a modifié "
                    "le niveau de preuve."
                ),
                "niveau_avant": niveau_initial,
                "niveau_apres": niveau,
            }
        )

    if not ajustements:
        ajustements.append(
            {
                "type": "aucun",
                "motif": "Aucun ajustement du niveau dominant.",
                "niveau_avant": niveau,
                "niveau_apres": niveau,
            }
        )

    contradiction_detectee = _detecter_contradiction(
        preuves,
        configuration=configuration,
    )
    indice_contradiction, ecart_niveaux = (
        _calculer_indice_contradiction(preuves)
    )
    niveau_contradiction = _niveau_contradiction(
        indice=indice_contradiction,
        contradiction_detectee=contradiction_detectee,
        configuration=configuration,
    )
    marge_preuve_dominante = _marge_preuve_dominante(preuves)
    preuve_dominante_stable = (
        marge_preuve_dominante
        >= configuration.marge_dominance_stable
    )
    confiance_preuve = _niveau_confiance(niveau)
    statut_publication = detecter_statut_publication_dans_texte(texte)
    empreinte = _empreinte_analyse(
        texte_normalise=texte_normalise,
        integrite_publication=integrite,
        configuration=configuration,
    )
    priorite_dominante = preuves[0]["priorite"] if preuves else 0
    score_preuve = _calculer_score_preuve(
        niveau=niveau,
        priorite=priorite_dominante,
        configuration=configuration,
    )
    classe_preuve = _classer_score_preuve(score_preuve)
    preuve_secondaire = (
        preuves[1]["nom"]
        if len(preuves) >= 2
        else None
    )
    maturite_publication = _determiner_maturite(
        statut=statut_publication,
        niveau=niveau,
        integrite=integrite,
    )
    alertes_qualite = _construire_alertes_qualite(
        statut=statut_publication,
        integrite=integrite,
        integrite_inconnue=integrite_inconnue,
        contradiction=niveau_contradiction,
        preuve_dominante_stable=preuve_dominante_stable,
    )
    nombre_regles_declenchees = sum(
        trace["statut"] == "declenchee"
        for trace in journal_regles
    )
    couverture_referentiel = round(
        nombre_regles_declenchees / len(journal_regles) * 100
    ) if journal_regles else 0
    correspondances_total = sum(
        len(trace["correspondances"])
        for trace in journal_regles
    )
    qualite_entree = _determiner_qualite_entree(
        texte_normalise=texte_normalise,
        preuves=preuves,
    )
    score_confiance, facteurs_confiance = (
        _calculer_confiance_detaillee(
            preuves=preuves,
            niveau=niveau,
            statut=statut_publication,
            maturite=maturite_publication,
            contradiction=niveau_contradiction,
            preuve_dominante_stable=preuve_dominante_stable,
            integrite=integrite,
            configuration=configuration,
        )
    )
    robustesse = _determiner_robustesse(
        score_confiance=score_confiance,
        niveau=niveau,
        maturite=maturite_publication,
    )
    alertes_critiques = _construire_alertes_critiques(
        maturite=maturite_publication,
        integrite=integrite,
        niveau=niveau,
    )
    preuve_dominante_identifiant = _identifiant_preuve(
        preuves[0] if preuves else None
    )
    preuve_secondaire_identifiant = _identifiant_preuve(
        preuves[1] if len(preuves) >= 2 else None
    )

    return {
        "preuve": preuve,
        "niveau_preuve": niveau,
        "niveau_preuve_initial": niveau_initial,
        "score_preuve": score_preuve,
        "classe_preuve": classe_preuve,
        "confiance_preuve": confiance_preuve,
        "score_confiance": score_confiance,
        "robustesse": robustesse,
        "qualite_entree": qualite_entree,
        "facteurs_confiance": facteurs_confiance,
        "raison_preuve": raison,
        "preuves_detectees": preuves,
        "statut_publication": statut_publication,
        "integrite_publication": integrite,
        "ajustements": ajustements,
        "nombre_preuves_detectees": len(preuves),
        "contradiction_detectee": contradiction_detectee,
        "indice_contradiction": indice_contradiction,
        "niveau_contradiction": niveau_contradiction,
        "ecart_niveaux": ecart_niveaux,
        "marge_preuve_dominante": marge_preuve_dominante,
        "preuve_dominante_stable": preuve_dominante_stable,
        "preuve_secondaire": preuve_secondaire,
        "maturite_publication": maturite_publication,
        "alertes_qualite": alertes_qualite,
        "alertes_critiques": alertes_critiques,
        "regles_declenchees": [
            preuve_detectee["nom"]
            for preuve_detectee in preuves
        ],
        "audit": {
            "engine_version": ENGINE_VERSION,
            "ruleset_version": RULESET_VERSION,
            "empreinte_analyse": empreinte,
            "configuration_hash": _configuration_hash(configuration),
            "referentiel_hash": _referentiel_hash(),
            "regles_evaluees": len(journal_regles),
            "regles_declenchees": nombre_regles_declenchees,
            "couverture_referentiel": couverture_referentiel,
            "correspondances_total": correspondances_total,
            "integrite_inconnue": integrite_inconnue,
            "preuve_dominante_identifiant": preuve_dominante_identifiant,
            "preuve_secondaire_identifiant": preuve_secondaire_identifiant,
            "journal_regles": journal_regles,
        },
        "synthese": _construire_synthese(
            preuve=preuve,
            niveau=niveau,
            confiance=confiance_preuve,
            statut=statut_publication,
            contradiction=niveau_contradiction,
            nombre_preuves=len(preuves),
            score_preuve=score_preuve,
            classe_preuve=classe_preuve,
            maturite=maturite_publication,
            score_confiance=score_confiance,
            robustesse=robustesse,
        ),
        "configuration": asdict(configuration),
    }


def analyser_preuve(
    article: Mapping[str, Any] | None,
    *,
    integrite_publication: Sequence[str] = (),
    configuration: ConfigurationPreuve = CONFIGURATION_PAR_DEFAUT,
) -> ResultatPreuve:
    """Produit le profil de preuve complet utilisable par l'orchestrateur."""
    if article is not None and not isinstance(article, Mapping):
        raise TypeError(
            "article doit être compatible avec Mapping ou None."
        )

    texte = construire_texte(article)
    if not isinstance(texte, str):
        raise TypeError(
            "construire_texte(article) doit retourner une chaîne."
        )

    return analyser_preuve_dans_texte(
        texte,
        integrite_publication=integrite_publication,
        configuration=configuration,
    )


# ---------------------------------------------------------------------------
# Intégration officielle au pipeline V6
# ---------------------------------------------------------------------------


def _resultat_preuve_valide(resultat: Mapping[str, Any]) -> ResultatPreuve:
    """Valide le minimum contractuel attendu d'un résultat de preuve."""
    if not isinstance(resultat, Mapping):
        raise TypeError("resultat doit être compatible avec Mapping.")

    champs_requis = {
        "preuve",
        "niveau_preuve",
        "score_preuve",
        "confiance_preuve",
        "score_confiance",
        "robustesse",
        "maturite_publication",
        "alertes_critiques",
    }
    manquants = sorted(champs_requis.difference(resultat))
    if manquants:
        raise ValueError(
            "Résultat de preuve incomplet : " + ", ".join(manquants)
        )
    return dict(resultat)  # type: ignore[return-value]


def obtenir_niveau_preuve(resultat: Mapping[str, Any]) -> int:
    """Retourne le niveau de preuve borné entre 0 et 5."""
    valeur = resultat.get("niveau_preuve", 0)
    if isinstance(valeur, bool) or not isinstance(valeur, int):
        return 0
    return max(0, min(5, valeur))


def obtenir_score_preuve(resultat: Mapping[str, Any]) -> int:
    """Retourne le score de preuve borné entre 0 et 100."""
    valeur = resultat.get("score_preuve", 0)
    if isinstance(valeur, bool) or not isinstance(valeur, int):
        return 0
    return max(0, min(100, valeur))


def obtenir_score_confiance(resultat: Mapping[str, Any]) -> int:
    """Retourne le score de confiance borné entre 0 et 100."""
    valeur = resultat.get("score_confiance", 0)
    if isinstance(valeur, bool) or not isinstance(valeur, int):
        return 0
    return max(0, min(100, valeur))


def obtenir_robustesse(resultat: Mapping[str, Any]) -> NiveauRobustesse:
    """Retourne une robustesse reconnue, sinon ``nulle``."""
    valeur = resultat.get("robustesse")
    if valeur in {"nulle", "faible", "moderee", "forte"}:
        return valeur  # type: ignore[return-value]
    return "nulle"


def obtenir_maturite(resultat: Mapping[str, Any]) -> MaturitePublication:
    """Retourne une maturité reconnue, sinon ``invalide``."""
    valeur = resultat.get("maturite_publication")
    if valeur in {"invalide", "immature", "secondaire", "principale"}:
        return valeur  # type: ignore[return-value]
    return "invalide"


def contient_alerte_critique(resultat: Mapping[str, Any]) -> bool:
    """Indique si au moins une alerte critique est présente."""
    alertes = resultat.get("alertes_critiques", ())
    return isinstance(alertes, Sequence) and not isinstance(
        alertes, (str, bytes)
    ) and bool(alertes)


def preuve_est_exploitable(resultat: Mapping[str, Any]) -> bool:
    """Indique si la preuve peut être utilisée par les étapes aval."""
    return (
        obtenir_niveau_preuve(resultat) > 0
        and obtenir_maturite(resultat) != "invalide"
        and not contient_alerte_critique(resultat)
    )


def preuve_est_forte(resultat: Mapping[str, Any]) -> bool:
    """Indique si la preuve est forte selon niveau, score et robustesse."""
    return (
        preuve_est_exploitable(resultat)
        and obtenir_niveau_preuve(resultat) >= 4
        and obtenir_score_preuve(resultat) >= 65
        and obtenir_robustesse(resultat) in {"moderee", "forte"}
    )


def statistiques_preuve(resultat: Mapping[str, Any]) -> dict[str, Any]:
    """Construit un résumé stable destiné au diagnostic et à l'audit."""
    return {
        "niveau_preuve": obtenir_niveau_preuve(resultat),
        "score_preuve": obtenir_score_preuve(resultat),
        "score_confiance": obtenir_score_confiance(resultat),
        "robustesse": obtenir_robustesse(resultat),
        "maturite_publication": obtenir_maturite(resultat),
        "contradiction": str(resultat.get("niveau_contradiction", "aucune")),
        "nombre_preuves_detectees": int(
            resultat.get("nombre_preuves_detectees", 0) or 0
        ),
        "alertes_critiques": len(resultat.get("alertes_critiques", ()) or ()),
        "exploitable": preuve_est_exploitable(resultat),
        "forte": preuve_est_forte(resultat),
    }


def executer(etat: "EtatClassification") -> None:
    """Exécute l'étape preuve sur l'état partagé du pipeline V6.

    Cette fonction ne contient aucune règle scientifique : elle adapte l'API
    métier existante au contrat d'orchestration, conserve le résultat complet
    dans les extensions et publie la sortie officielle dans le contexte.
    """
    contexte = getattr(etat, "contexte", None)
    if contexte is None:
        raise TypeError("etat doit exposer un attribut contexte.")

    texte = getattr(contexte, "texte", None)
    if not isinstance(texte, str):
        raise TypeError("etat.contexte.texte doit être une chaîne.")

    integrite = getattr(etat, "integrite_publication", ())
    if integrite is None:
        integrite = ()
    if isinstance(integrite, (str, bytes)) or not isinstance(integrite, Sequence):
        raise TypeError("etat.integrite_publication doit être une séquence.")

    resultat = analyser_preuve_dans_texte(
        texte,
        integrite_publication=integrite,
    )

    definir_resultat = getattr(contexte, "definir_resultat", None)
    if callable(definir_resultat):
        definir_resultat("preuve", resultat)
    else:
        setattr(contexte, "preuve", dict(resultat))

    extensions = getattr(etat, "extensions", None)
    if isinstance(extensions, dict):
        extensions["preuve"] = dict(resultat)
        versions = extensions.setdefault("versions_modules", {})
        if isinstance(versions, dict):
            versions["preuve"] = VERSION_PREUVE

    audit = getattr(etat, "audit", None)
    enregistrer = getattr(audit, "enregistrer", None)
    if callable(enregistrer):
        enregistrer(
            "preuve_calculee",
            etape="preuve",
            donnees=statistiques_preuve(resultat),
        )


executer_preuve = executer


__all__ = [
    "VERSION_PREUVE",
    "CONFIGURATION_PAR_DEFAUT",
    "ENGINE_VERSION",
    "AjustementPreuve",
    "ClassePreuve",
    "AuditPreuve",
    "ConfigurationPreuve",
    "FacteurConfiance",
    "NiveauConfiancePreuve",
    "NiveauContradiction",
    "MaturitePublication",
    "NiveauRobustesse",
    "QualiteEntreePreuve",
    "PreuveDetectee",
    "REGLES_PREUVE",
    "RULESET_VERSION",
    "ReglePreuve",
    "ResultatPreuve",
    "StatutPublication",
    "StatutReglePreuve",
    "INTEGRITE_PUBLICATION_AUTORISEE",
    "TERMES_ANALYSE_SECONDAIRE",
    "TERMES_PROTOCOLE",
    "TraceReglePreuve",
    "TypeAjustement",
    "ajuster_preuve_integrite",
    "analyser_preuve",
    "analyser_preuve_dans_texte",
    "detecter_preuves",
    "detecter_preuves_dans_texte",
    "detecter_statut_publication",
    "detecter_statut_publication_dans_texte",
    "selectionner_preuve",
    "contient_alerte_critique",
    "executer",
    "executer_preuve",
    "obtenir_maturite",
    "obtenir_niveau_preuve",
    "obtenir_robustesse",
    "obtenir_score_confiance",
    "obtenir_score_preuve",
    "preuve_est_exploitable",
    "preuve_est_forte",
    "statistiques_preuve",
]