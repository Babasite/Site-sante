"""
Évaluation déterministe, explicable et configurable de la pertinence sanitaire.

Version 5.

Ce module sépare la pertinence thématique du niveau de preuve scientifique.
Il combine catégories explicites, signaux sanitaires, dimensions One Health,
pénalités contextuelles et règles de convergence.

Aucune IA ni dépendance externe n'est utilisée. Chaque variation du score est
représentée par une contribution traçable, stable et exportable.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
from typing import TYPE_CHECKING, Any, Final, Literal, TypedDict

from .categories import detecter_categories_dans_texte
from .one_health import detecter_one_health_dans_texte
from .utils import (
    construire_texte,
    contient_expression,
    dedupliquer,
    normaliser,
)


if TYPE_CHECKING:
    from .pipeline import EtatClassification


VERSION_PERTINENCE: Final[str] = "6.0.0"
ENGINE_VERSION: Final[str] = "5.0"
RULESET_VERSION: Final[str] = "2026.01"


DecisionPertinence = Literal[
    "rejet",
    "a_revoir",
    "pertinent",
    "prioritaire",
]

TypeContribution = Literal["bonus", "malus"]

FamilleContribution = Literal[
    "categorie",
    "signal",
    "one_health",
    "contexte",
    "convergence",
]

QualiteEntree = Literal[
    "valide",
    "vide",
    "partielle",
]

SourceMetadonnees = Literal[
    "detectee",
    "fournie",
]

NiveauConflit = Literal[
    "aucun",
    "modere",
    "fort",
]

StatutRegle = Literal[
    "declenchee",
    "non_declenchee",
    "ignoree",
]

NiveauStabilite = Literal[
    "stable",
    "sensible",
    "domine",
]


class ContributionExportee(TypedDict):
    """Représentation publique d'une contribution au score."""

    ordre: int
    regle: str
    famille: FamilleContribution
    type: TypeContribution
    points: int
    raison: str
    correspondances: list[str]


class ResumeScores(TypedDict):
    """Résumé des points par famille et par sens."""

    bonus: int
    malus: int
    net: int


class TraceRegle(TypedDict):
    """Trace d'évaluation d'une règle métier."""

    ordre: int
    identifiant: str
    famille: FamilleContribution
    statut: StatutRegle
    raison: str


class StabiliteScore(TypedDict):
    """Indicateurs simples de stabilité du score."""

    niveau: NiveauStabilite
    part_contribution_principale: int
    proche_seuil: bool
    domine_par_une_regle: bool


class AuditPertinence(TypedDict):
    """Informations facilitant la reproductibilité d'une analyse."""

    empreinte: str
    source_categories: SourceMetadonnees
    source_one_health: SourceMetadonnees
    categories_inconnues: list[str]
    dimensions_inconnues: list[str]
    marge_decision: int
    decision_fragile: bool
    engine_version: str
    ruleset_version: str
    configuration_hash: str
    referentiel_hash: str
    regles_evaluees: int
    regles_declenchees: int
    regles_non_declenchees: int
    journal_regles: list[TraceRegle]


class ResultatPertinence(TypedDict):
    """Structure retournée par les fonctions d'analyse."""

    score_pertinence: int
    score_pertinence_brut: int
    score_borne: bool
    niveau_pertinence: DecisionPertinence
    retenu: bool
    confiance: int
    qualite_entree: QualiteEntree
    categories: list[str]
    one_health: list[str]
    contextes_hors_cible: list[str]
    signaux_detectes: dict[str, list[str]]
    raisons: list[str]
    raisons_positives: list[str]
    raisons_negatives: list[str]
    contributions: list[ContributionExportee]
    scores_par_famille: dict[FamilleContribution, ResumeScores]
    nombre_contributions: int
    nombre_bonus: int
    nombre_malus: int
    contradiction_detectee: bool
    indice_conflit: int
    niveau_conflit: NiveauConflit
    marge_decision: int
    decision_fragile: bool
    categorie_plus_contributive: str | None
    principal_bonus: ContributionExportee | None
    principal_malus: ContributionExportee | None
    audit: AuditPertinence
    stabilite_score: StabiliteScore
    synthese: str
    configuration: dict[str, Any]


@dataclass(slots=True)
class _JournalRegles:
    """Journal interne ordonné des règles évaluées."""

    traces: list[TraceRegle]

    def enregistrer(
        self,
        *,
        identifiant: str,
        famille: FamilleContribution,
        condition: bool,
        raison_declenchee: str,
        raison_non_declenchee: str,
    ) -> None:
        statut: StatutRegle = (
            "declenchee" if condition else "non_declenchee"
        )
        raison = (
            raison_declenchee
            if condition
            else raison_non_declenchee
        )
        self.traces.append(
            {
                "ordre": len(self.traces) + 1,
                "identifiant": identifiant,
                "famille": famille,
                "statut": statut,
                "raison": raison,
            }
        )


@dataclass(frozen=True, slots=True)
class Contribution:
    """Élément explicable ayant modifié le score."""

    ordre: int
    regle: str
    famille: FamilleContribution
    points: int
    raison: str
    correspondances: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Valide qu'une contribution est exploitable."""
        if isinstance(self.ordre, bool) or not isinstance(self.ordre, int):
            raise TypeError("ordre doit être un entier.")
        if self.ordre < 1:
            raise ValueError("ordre doit être supérieur ou égal à 1.")

        if not isinstance(self.regle, str) or not self.regle.strip():
            raise ValueError("Une contribution doit posséder une règle.")

        if not isinstance(self.raison, str) or not self.raison.strip():
            raise ValueError("Une contribution doit posséder une raison.")

        if isinstance(self.points, bool) or not isinstance(self.points, int):
            raise TypeError(
                "Les points d'une contribution doivent être entiers."
            )

        if self.points == 0:
            raise ValueError(
                "Une contribution ne peut pas valoir zéro point."
            )

    @property
    def type(self) -> TypeContribution:
        """Retourne le sens de la contribution."""
        return "bonus" if self.points > 0 else "malus"

    def exporter(self) -> ContributionExportee:
        """Retourne une structure sérialisable et stable."""
        return {
            "ordre": self.ordre,
            "regle": self.regle,
            "famille": self.famille,
            "type": self.type,
            "points": self.points,
            "raison": self.raison,
            "correspondances": list(self.correspondances),
        }


@dataclass(frozen=True, slots=True)
class SeuilsPertinence:
    """Seuils de classement du score de pertinence."""

    a_revoir: int = 20
    pertinent: int = 40
    prioritaire: int = 70

    def __post_init__(self) -> None:
        valeurs = (self.a_revoir, self.pertinent, self.prioritaire)

        if any(
            isinstance(valeur, bool) or not isinstance(valeur, int)
            for valeur in valeurs
        ):
            raise TypeError(
                "Les seuils de pertinence doivent être entiers."
            )

        if not (
            0
            <= self.a_revoir
            < self.pertinent
            < self.prioritaire
            <= 100
        ):
            raise ValueError(
                "Les seuils doivent vérifier : "
                "0 <= a_revoir < pertinent < prioritaire <= 100."
            )

    def classer(self, score: int) -> DecisionPertinence:
        """Classe un score déjà borné entre 0 et 100."""
        if isinstance(score, bool) or not isinstance(score, int):
            raise TypeError("score doit être un entier.")
        if not 0 <= score <= 100:
            raise ValueError("score doit être compris entre 0 et 100.")

        if score < self.a_revoir:
            return "rejet"
        if score < self.pertinent:
            return "a_revoir"
        if score < self.prioritaire:
            return "pertinent"
        return "prioritaire"


@dataclass(frozen=True, slots=True)
class ConfigurationPertinence:
    """Configuration complète des règles d'agrégation."""

    seuils: SeuilsPertinence = SeuilsPertinence()
    nombre_categories_max: int = 4

    bonus_signal_infectieux: int = 18
    bonus_signal_alerte: int = 24
    bonus_surveillance: int = 13
    bonus_donnees_cliniques: int = 8

    bonus_one_health_deux_dimensions: int = 14
    bonus_one_health_trois_dimensions: int = 22
    malus_animal_isole: int = -12

    malus_recherche_fondamentale: int = -18
    malus_recherche_fondamentale_corroboree: int = -8
    malus_hors_cible: int = -24
    malus_hors_cible_corrobore: int = -8
    malus_terme_generique_non_corrobore: int = -18

    bonus_convergence_alerte: int = 12
    bonus_vaccination_clinique: int = 10
    bonus_amr_actionnable: int = 10

    confiance_base: int = 35
    confiance_par_famille: int = 7
    confiance_bonus_max: int = 45
    confiance_malus_conflit: int = 7
    confiance_malus_max: int = 25
    confiance_max_sans_bonus: int = 25

    marge_decision_fragile: int = 5
    seuil_conflit_fort: int = 50
    refuser_valeurs_inconnues: bool = False
    seuil_dominance_regle: int = 60

    def __post_init__(self) -> None:
        """Valide tous les paramètres de calcul."""
        if not isinstance(self.seuils, SeuilsPertinence):
            raise TypeError(
                "seuils doit être une instance de SeuilsPertinence."
            )

        valeurs = asdict(self)
        valeurs.pop("seuils", None)
        refuser_valeurs_inconnues = valeurs.pop(
            "refuser_valeurs_inconnues"
        )

        if not isinstance(refuser_valeurs_inconnues, bool):
            raise TypeError(
                "refuser_valeurs_inconnues doit être un booléen."
            )

        for nom, valeur in valeurs.items():
            if isinstance(valeur, bool) or not isinstance(valeur, int):
                raise TypeError(f"{nom} doit être un entier.")

        if self.nombre_categories_max <= 0:
            raise ValueError(
                "nombre_categories_max doit être strictement positif."
            )

        bonus = {
            nom: valeur
            for nom, valeur in valeurs.items()
            if nom.startswith("bonus_")
        }
        for nom, valeur in bonus.items():
            if valeur <= 0:
                raise ValueError(f"{nom} doit être strictement positif.")

        malus = {
            nom: valeur
            for nom, valeur in valeurs.items()
            if nom.startswith("malus_")
        }
        for nom, valeur in malus.items():
            if valeur >= 0:
                raise ValueError(f"{nom} doit être strictement négatif.")

        if (
            self.bonus_one_health_trois_dimensions
            < self.bonus_one_health_deux_dimensions
        ):
            raise ValueError(
                "Le bonus One Health à trois dimensions doit être "
                "supérieur ou égal à celui à deux dimensions."
            )

        for nom in (
            "confiance_base",
            "confiance_bonus_max",
            "confiance_malus_max",
            "confiance_max_sans_bonus",
        ):
            valeur = getattr(self, nom)
            if not 0 <= valeur <= 100:
                raise ValueError(
                    f"{nom} doit être compris entre 0 et 100."
                )

        for nom in (
            "confiance_par_famille",
            "confiance_malus_conflit",
            "marge_decision_fragile",
        ):
            if getattr(self, nom) < 0:
                raise ValueError(f"{nom} doit être positif ou nul.")

        if not 0 <= self.seuil_conflit_fort <= 100:
            raise ValueError(
                "seuil_conflit_fort doit être compris entre 0 et 100."
            )

        if not 1 <= self.seuil_dominance_regle <= 100:
            raise ValueError(
                "seuil_dominance_regle doit être compris entre 1 et 100."
            )


CONFIGURATION_PAR_DEFAUT = ConfigurationPertinence()


SIGNAUX_INFECTIEUX: Final[tuple[str, ...]] = (
    "infectious disease",
    "human infection",
    "pathogen",
    "viral infection",
    "bacterial infection",
    "fungal infection",
    "parasitic infection",
    "sepsis",
    "zoonosis",
    "zoonotic",
    "maladie infectieuse",
    "infection humaine",
    "agent pathogene",
    "infection virale",
    "infection bacterienne",
    "infection fongique",
    "infection parasitaire",
    "zoonose",
)

SIGNAUX_ALERTE: Final[tuple[str, ...]] = (
    "outbreak",
    "epidemic",
    "pandemic",
    "cluster of cases",
    "first case",
    "first human case",
    "emerging pathogen",
    "reemerging pathogen",
    "novel variant",
    "variant of concern",
    "spillover",
    "public health emergency",
    "flambee epidemique",
    "epidemie",
    "pandemie",
    "foyer de cas",
    "premier cas",
    "agent pathogene emergent",
    "nouveau variant",
    "urgence de sante publique",
)

SIGNAUX_SURVEILLANCE: Final[tuple[str, ...]] = (
    "disease surveillance",
    "epidemiological surveillance",
    "genomic surveillance",
    "wastewater surveillance",
    "sentinel surveillance",
    "contact tracing",
    "surveillance epidemiologique",
    "surveillance genomique",
    "surveillance des eaux usees",
    "surveillance sentinelle",
    "tracage des contacts",
)

SIGNAUX_CLINIQUES: Final[tuple[str, ...]] = (
    "patients",
    "hospitalized patients",
    "clinical outcome",
    "mortality",
    "morbidity",
    "case fatality",
    "intensive care",
    "patients hospitalises",
    "resultat clinique",
    "mortalite",
    "morbidite",
    "letalite",
    "soins intensifs",
)

RECHERCHE_FONDAMENTALE: Final[tuple[str, ...]] = (
    "in vitro",
    "cell line",
    "cell culture",
    "murine model",
    "mouse model",
    "mice model",
    "animal model",
    "molecular docking",
    "in silico",
    "organoid",
    "modele murin",
    "culture cellulaire",
    "ligne cellulaire",
    "modele animal",
)

CONTEXTES_HORS_CIBLE: Final[dict[str, tuple[str, ...]]] = {
    "Orthopédie": (
        "orthopedic",
        "orthopaedic",
        "hip replacement",
        "knee replacement",
        "prosthesis",
        "arthroplasty",
        "fracture fixation",
        "musculoskeletal",
        "orthopedie",
        "prothese",
        "arthroplastie",
    ),
    "Oncologie": (
        "cancer vaccine",
        "tumor vaccine",
        "cancer immunotherapy",
        "tumour immunotherapy",
        "oncology",
        "neoplasm",
        "anticancer",
        "vaccin anticancer",
        "immunotherapie anticancereuse",
        "oncologie",
        "tumeur",
    ),
    "Neurologie": (
        "alzheimer",
        "parkinson",
        "multiple sclerosis",
        "epilepsy",
        "stroke rehabilitation",
        "neurodegenerative",
        "sclerose en plaques",
        "epilepsie",
        "neurodegeneratif",
    ),
    "Cardiologie": (
        "heart failure",
        "myocardial infarction",
        "coronary artery",
        "cardiac rehabilitation",
        "insuffisance cardiaque",
        "infarctus du myocarde",
        "artere coronaire",
    ),
    "Allergologie": (
        "allergy immunotherapy",
        "allergen immunotherapy",
        "allergic rhinitis",
        "food allergy",
        "immunotherapie allergenique",
        "rhinite allergique",
        "allergie alimentaire",
    ),
}

POIDS_CATEGORIES: Final[dict[str, int]] = {
    "Maladies infectieuses": 32,
    "Antibiorésistance": 24,
    "Vaccination": 14,
    "Santé animale": 12,
    "Santé environnementale": 10,
    "Prévention": 10,
    "Diagnostic": 9,
    "Essais cliniques": 8,
    "Recommandations": 12,
    "Traitements": 6,
    "Revues scientifiques": 4,
    "IA médicale": 2,
}

DIMENSIONS_ONE_HEALTH_AUTORISEES: Final[frozenset[str]] = frozenset(
    {"Humain", "Animal", "Environnement"}
)


TERMES_GENERIQUES_FRAGILES: Final[tuple[str, ...]] = (
    "treatment",
    "therapy",
    "therapeutic",
    "medication",
    "traitement",
    "therapie",
    "medicament",
    "vaccine",
    "vaccin",
)


_GROUPES_EXPRESSIONS: Final[dict[str, tuple[str, ...]]] = {
    "infectieux": SIGNAUX_INFECTIEUX,
    "alerte": SIGNAUX_ALERTE,
    "surveillance": SIGNAUX_SURVEILLANCE,
    "clinique": SIGNAUX_CLINIQUES,
    "recherche_fondamentale": RECHERCHE_FONDAMENTALE,
    "termes_generiques_fragiles": TERMES_GENERIQUES_FRAGILES,
}


def _verifier_referentiels() -> None:
    """Valide les expressions, contextes et poids au chargement."""
    groupes: dict[str, tuple[str, ...]] = dict(_GROUPES_EXPRESSIONS)
    groupes.update(
        {
            f"hors_cible:{nom}": expressions
            for nom, expressions in CONTEXTES_HORS_CIBLE.items()
        }
    )

    for nom_groupe, expressions in groupes.items():
        if not expressions:
            raise ValueError(
                f"Le groupe d'expressions {nom_groupe!r} est vide."
            )

        vues: set[str] = set()

        for expression in expressions:
            if not isinstance(expression, str):
                raise TypeError(
                    f"Les expressions de {nom_groupe!r} doivent être "
                    "des chaînes."
                )

            normalisee = normaliser(expression)
            if not normalisee:
                raise ValueError(
                    f"Le groupe {nom_groupe!r} contient une expression vide."
                )

            if normalisee in vues:
                raise ValueError(
                    f"Expression dupliquée dans {nom_groupe!r} : "
                    f"{expression!r}."
                )

            vues.add(normalisee)

    for categorie, poids in POIDS_CATEGORIES.items():
        if not isinstance(categorie, str) or not categorie.strip():
            raise ValueError(
                "Une catégorie pondérée doit être une chaîne non vide."
            )

        if isinstance(poids, bool) or not isinstance(poids, int):
            raise TypeError(
                f"Le poids de la catégorie {categorie!r} doit être entier."
            )

        if poids <= 0:
            raise ValueError(
                f"Le poids de la catégorie {categorie!r} doit être positif."
            )


_verifier_referentiels()


def _normaliser_sequence(
    valeurs: Sequence[str] | None,
    *,
    nom: str,
) -> list[str]:
    """Valide, nettoie et déduplique une séquence de chaînes."""
    if valeurs is None:
        return []

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



def _separer_valeurs_connues(
    valeurs: Sequence[str],
    *,
    autorisees: Iterable[str],
) -> tuple[list[str], list[str]]:
    """Sépare les valeurs reconnues des valeurs inconnues."""
    ensemble_autorise = set(autorisees)
    connues = [valeur for valeur in valeurs if valeur in ensemble_autorise]
    inconnues = [
        valeur for valeur in valeurs if valeur not in ensemble_autorise
    ]
    return connues, inconnues


def _calculer_indice_conflit(
    contributions: Sequence[Contribution],
) -> int:
    """Mesure la part des points opposés dans le volume total d'impact."""
    total_bonus = sum(
        contribution.points
        for contribution in contributions
        if contribution.points > 0
    )
    total_malus = abs(
        sum(
            contribution.points
            for contribution in contributions
            if contribution.points < 0
        )
    )
    volume = total_bonus + total_malus

    if volume == 0 or total_bonus == 0 or total_malus == 0:
        return 0

    opposition = min(total_bonus, total_malus)
    return round(opposition / volume * 200)


def _determiner_niveau_conflit(
    indice_conflit: int,
    *,
    configuration: ConfigurationPertinence,
) -> NiveauConflit:
    """Convertit l'indice de conflit en niveau lisible."""
    if indice_conflit == 0:
        return "aucun"
    if indice_conflit >= configuration.seuil_conflit_fort:
        return "fort"
    return "modere"


def _calculer_marge_decision(
    score: int,
    seuils: SeuilsPertinence,
) -> int:
    """Retourne la distance du score au seuil de décision le plus proche."""
    distances = (
        abs(score - seuils.a_revoir),
        abs(score - seuils.pertinent),
        abs(score - seuils.prioritaire),
    )
    return min(distances)


def _contribution_extreme(
    contributions: Sequence[Contribution],
    *,
    type_recherche: TypeContribution,
) -> Contribution | None:
    """Retourne la contribution la plus forte, avec ordre stable."""
    candidates = [
        contribution
        for contribution in contributions
        if contribution.type == type_recherche
    ]
    if not candidates:
        return None

    if type_recherche == "bonus":
        return max(candidates, key=lambda contribution: contribution.points)

    return min(candidates, key=lambda contribution: contribution.points)


def _categorie_plus_contributive(
    contributions: Sequence[Contribution],
) -> str | None:
    """Retourne la catégorie ayant apporté le plus de points."""
    categories = [
        contribution
        for contribution in contributions
        if contribution.famille == "categorie"
    ]
    if not categories:
        return None

    principale = max(
        categories,
        key=lambda contribution: contribution.points,
    )
    return principale.regle.removeprefix("categorie:")


def _construire_empreinte(
    *,
    texte_normalise: str,
    categories: Sequence[str],
    dimensions: Sequence[str],
    configuration: ConfigurationPertinence,
) -> str:
    """Produit une empreinte déterministe de l'entrée et de la configuration."""
    charge = {
        "texte": texte_normalise,
        "categories": list(categories),
        "one_health": list(dimensions),
        "configuration": asdict(configuration),
        "version": 5,
    }
    serialise = json.dumps(
        charge,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialise.encode("utf-8")).hexdigest()




def _empreinte_json(objet: Any) -> str:
    """Calcule une empreinte SHA-256 stable d'un objet sérialisable."""
    serialise = json.dumps(
        objet,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialise.encode("utf-8")).hexdigest()


def _calculer_configuration_hash(
    configuration: ConfigurationPertinence,
) -> str:
    """Retourne l'empreinte stable de la configuration."""
    return _empreinte_json(asdict(configuration))


def _calculer_referentiel_hash() -> str:
    """Retourne l'empreinte stable des référentiels métier."""
    charge = {
        "poids_categories": POIDS_CATEGORIES,
        "signaux": _GROUPES_EXPRESSIONS,
        "hors_cible": CONTEXTES_HORS_CIBLE,
        "dimensions_one_health": sorted(
            DIMENSIONS_ONE_HEALTH_AUTORISEES
        ),
        "ruleset_version": RULESET_VERSION,
    }
    return _empreinte_json(charge)


def _analyser_stabilite(
    contributions: Sequence[Contribution],
    *,
    marge_decision: int,
    configuration: ConfigurationPertinence,
) -> StabiliteScore:
    """Évalue la sensibilité du score aux seuils et à une règle dominante."""
    impacts = [abs(contribution.points) for contribution in contributions]
    total = sum(impacts)
    maximum = max(impacts, default=0)
    part = round(maximum / total * 100) if total else 0
    domine = part >= configuration.seuil_dominance_regle
    proche = marge_decision <= configuration.marge_decision_fragile

    niveau: NiveauStabilite
    if domine:
        niveau = "domine"
    elif proche:
        niveau = "sensible"
    else:
        niveau = "stable"

    return {
        "niveau": niveau,
        "part_contribution_principale": part,
        "proche_seuil": proche,
        "domine_par_une_regle": domine,
    }



def _correspondances(
    texte: str,
    expressions: Iterable[str],
) -> list[str]:
    """Retourne les expressions présentes dans le texte normalisé."""
    return [
        expression
        for expression in expressions
        if contient_expression(texte, normaliser(expression))
    ]


def _ajouter(
    contributions: list[Contribution],
    *,
    regle: str,
    famille: FamilleContribution,
    points: int,
    raison: str,
    correspondances: Sequence[str] = (),
) -> None:
    """Ajoute une contribution non nulle et dédupliquée."""
    correspondances_uniques = tuple(dedupliquer(correspondances))

    if any(
        contribution.regle == regle
        and contribution.points == points
        and contribution.correspondances == correspondances_uniques
        for contribution in contributions
    ):
        return

    contributions.append(
        Contribution(
            ordre=len(contributions) + 1,
            regle=regle,
            famille=famille,
            points=points,
            raison=raison,
            correspondances=correspondances_uniques,
        )
    )


def _extraire_signaux(
    texte_normalise: str,
) -> dict[str, list[str]]:
    """Détecte tous les groupes de signaux en un seul point."""
    return {
        nom: _correspondances(texte_normalise, expressions)
        for nom, expressions in _GROUPES_EXPRESSIONS.items()
    }


def _ajouter_bonus_categories(
    contributions: list[Contribution],
    categories: Sequence[str],
    *,
    configuration: ConfigurationPertinence,
) -> None:
    """Ajoute les catégories les plus contributives."""
    bonus = [
        (nom, POIDS_CATEGORIES[nom])
        for nom in categories
        if nom in POIDS_CATEGORIES
    ]
    bonus.sort(key=lambda item: (-item[1], item[0]))

    for nom, points in bonus[: configuration.nombre_categories_max]:
        _ajouter(
            contributions,
            regle=f"categorie:{nom}",
            famille="categorie",
            points=points,
            raison=f"Catégorie pertinente détectée : {nom}.",
            correspondances=(nom,),
        )


def _score_confiance(
    contributions: Sequence[Contribution],
    categories: Sequence[str],
    dimensions: Sequence[str],
    *,
    configuration: ConfigurationPertinence,
) -> int:
    """Mesure la cohérence des indices, non une probabilité statistique."""
    bonus = [c for c in contributions if c.points > 0]
    malus = [c for c in contributions if c.points < 0]
    familles_positives = {c.famille for c in bonus}

    nombre_familles = (
        len(familles_positives)
        + int(bool(categories))
        + int(bool(dimensions))
    )

    confiance = (
        configuration.confiance_base
        + min(
            configuration.confiance_bonus_max,
            nombre_familles * configuration.confiance_par_famille,
        )
    )

    if bonus and malus:
        confiance -= min(
            configuration.confiance_malus_max,
            len(malus) * configuration.confiance_malus_conflit,
        )

    if not bonus:
        confiance = min(
            confiance,
            configuration.confiance_max_sans_bonus,
        )

    return max(0, min(100, confiance))


def _resumer_scores(
    contributions: Sequence[Contribution],
) -> dict[FamilleContribution, ResumeScores]:
    """Agrège les points par famille."""
    familles: tuple[FamilleContribution, ...] = (
        "categorie",
        "signal",
        "one_health",
        "contexte",
        "convergence",
    )
    resultat: dict[FamilleContribution, ResumeScores] = {}

    for famille in familles:
        points = [
            contribution.points
            for contribution in contributions
            if contribution.famille == famille
        ]
        bonus = sum(point for point in points if point > 0)
        malus = sum(point for point in points if point < 0)

        resultat[famille] = {
            "bonus": bonus,
            "malus": malus,
            "net": bonus + malus,
        }

    return resultat


def _determiner_qualite_entree(
    texte_normalise: str,
    categories: Sequence[str],
    dimensions: Sequence[str],
) -> QualiteEntree:
    """Qualifie sommairement la richesse de l'entrée analysée."""
    if not texte_normalise:
        return "vide"

    if not categories and not dimensions:
        return "partielle"

    return "valide"


def _detecter_contradiction(
    contributions: Sequence[Contribution],
) -> bool:
    """Indique si bonus et malus coexistent dans l'analyse."""
    return (
        any(contribution.points > 0 for contribution in contributions)
        and any(contribution.points < 0 for contribution in contributions)
    )


def _construire_synthese(
    *,
    score: int,
    score_brut: int,
    decision: DecisionPertinence,
    confiance: int,
    nombre_bonus: int,
    nombre_malus: int,
    contradiction_detectee: bool,
    marge_decision: int,
    decision_fragile: bool,
) -> str:
    """Construit une synthèse courte et stable."""
    libelles: Final[dict[DecisionPertinence, str]] = {
        "rejet": "Rejet",
        "a_revoir": "À revoir",
        "pertinent": "Pertinent",
        "prioritaire": "Prioritaire",
    }

    synthese = (
        f"Pertinence : {libelles[decision]}. "
        f"Score : {score}/100"
    )

    if score != score_brut:
        synthese += f" (score brut : {score_brut})"

    synthese += (
        f". Confiance : {confiance}/100. "
        f"Contributions : {nombre_bonus} bonus, "
        f"{nombre_malus} malus."
    )

    if contradiction_detectee:
        synthese += " Des indices favorables et défavorables coexistent."

    synthese += f" Marge de décision : {marge_decision} point(s)."

    if decision_fragile:
        synthese += " La décision est proche d'un seuil ou fortement conflictuelle."

    return synthese


def analyser_pertinence_dans_texte(
    texte: str,
    *,
    categories: Sequence[str] | None = None,
    one_health: Sequence[str] | None = None,
    configuration: ConfigurationPertinence = CONFIGURATION_PAR_DEFAUT,
) -> ResultatPertinence:
    """Évalue un texte déjà disponible et renvoie un résultat explicable."""
    if not isinstance(texte, str):
        raise TypeError("texte doit être une chaîne de caractères.")

    if not isinstance(configuration, ConfigurationPertinence):
        raise TypeError(
            "configuration doit être une instance de "
            "ConfigurationPertinence."
        )

    texte_normalise = normaliser(texte)

    source_categories: SourceMetadonnees = (
        "detectee" if categories is None else "fournie"
    )
    source_one_health: SourceMetadonnees = (
        "detectee" if one_health is None else "fournie"
    )

    if categories is None:
        categories_detectees, _ = detecter_categories_dans_texte(
            texte_normalise
        )
        categories_finales = _normaliser_sequence(
            categories_detectees,
            nom="categories détectées",
        )
    else:
        categories_finales = _normaliser_sequence(
            categories,
            nom="categories",
        )

    if one_health is None:
        dimensions_detectees, _ = detecter_one_health_dans_texte(
            texte_normalise
        )
        dimensions = _normaliser_sequence(
            dimensions_detectees,
            nom="one_health détecté",
        )
    else:
        dimensions = _normaliser_sequence(
            one_health,
            nom="one_health",
        )

    _, categories_inconnues = _separer_valeurs_connues(
        categories_finales,
        autorisees=POIDS_CATEGORIES,
    )
    dimensions_connues, dimensions_inconnues = _separer_valeurs_connues(
        dimensions,
        autorisees=DIMENSIONS_ONE_HEALTH_AUTORISEES,
    )

    if configuration.refuser_valeurs_inconnues:
        if categories_inconnues:
            raise ValueError(
                "Catégories inconnues : "
                + ", ".join(categories_inconnues)
            )
        if dimensions_inconnues:
            raise ValueError(
                "Dimensions One Health inconnues : "
                + ", ".join(dimensions_inconnues)
            )

    # Les dimensions inconnues ne doivent jamais modifier le bonus One Health.
    dimensions = dimensions_connues

    contributions: list[Contribution] = []
    journal = _JournalRegles(traces=[])

    journal.enregistrer(
        identifiant="categories_ponderees",
        famille="categorie",
        condition=any(
            categorie in POIDS_CATEGORIES
            for categorie in categories_finales
        ),
        raison_declenchee="Au moins une catégorie pondérée est disponible.",
        raison_non_declenchee="Aucune catégorie pondérée n'est disponible.",
    )

    _ajouter_bonus_categories(
        contributions,
        categories_finales,
        configuration=configuration,
    )

    signaux = _extraire_signaux(texte_normalise)
    infectieux = signaux["infectieux"]
    alertes = signaux["alerte"]
    surveillance = signaux["surveillance"]
    clinique = signaux["clinique"]
    fondamental = signaux["recherche_fondamentale"]
    fragiles = signaux["termes_generiques_fragiles"]

    journal.enregistrer(
        identifiant="signal_infectieux",
        famille="signal",
        condition=bool(infectieux),
        raison_declenchee="Un signal infectieux explicite est présent.",
        raison_non_declenchee="Aucun signal infectieux explicite.",
    )
    if infectieux:
        _ajouter(
            contributions,
            regle="signal_infectieux",
            famille="signal",
            points=configuration.bonus_signal_infectieux,
            raison="Contexte infectieux explicite.",
            correspondances=infectieux,
        )

    journal.enregistrer(
        identifiant="signal_alerte",
        famille="signal",
        condition=bool(alertes),
        raison_declenchee="Un signal d'alerte sanitaire est présent.",
        raison_non_declenchee="Aucun signal d'alerte sanitaire.",
    )
    if alertes:
        _ajouter(
            contributions,
            regle="signal_alerte",
            famille="signal",
            points=configuration.bonus_signal_alerte,
            raison="Signal sanitaire nécessitant une veille rapide.",
            correspondances=alertes,
        )

    journal.enregistrer(
        identifiant="surveillance",
        famille="signal",
        condition=bool(surveillance),
        raison_declenchee="Un signal de surveillance est présent.",
        raison_non_declenchee="Aucun signal de surveillance.",
    )
    if surveillance:
        _ajouter(
            contributions,
            regle="surveillance",
            famille="signal",
            points=configuration.bonus_surveillance,
            raison="Activité de surveillance sanitaire détectée.",
            correspondances=surveillance,
        )

    journal.enregistrer(
        identifiant="donnees_cliniques",
        famille="signal",
        condition=bool(clinique),
        raison_declenchee="Des données cliniques sont présentes.",
        raison_non_declenchee="Aucune donnée clinique détectée.",
    )
    if clinique:
        _ajouter(
            contributions,
            regle="donnees_cliniques",
            famille="signal",
            points=configuration.bonus_donnees_cliniques,
            raison="Présence de données ou résultats cliniques.",
            correspondances=clinique,
        )

    journal.enregistrer(
        identifiant="one_health_transversal_3d",
        famille="one_health",
        condition=len(dimensions) >= 3,
        raison_declenchee="Trois dimensions One Health convergent.",
        raison_non_declenchee="Moins de trois dimensions One Health.",
    )
    journal.enregistrer(
        identifiant="one_health_transversal_2d",
        famille="one_health",
        condition=len(dimensions) == 2,
        raison_declenchee="Deux dimensions One Health convergent.",
        raison_non_declenchee="Le texte ne contient pas exactement deux dimensions.",
    )
    journal.enregistrer(
        identifiant="animal_isole",
        famille="one_health",
        condition=(
            dimensions == ["Animal"]
            and not infectieux
            and not alertes
        ),
        raison_declenchee="Dimension animale isolée sans corroboration.",
        raison_non_declenchee="La condition d'animal isolé n'est pas remplie.",
    )
    if len(dimensions) >= 3:
        _ajouter(
            contributions,
            regle="one_health_transversal",
            famille="one_health",
            points=configuration.bonus_one_health_trois_dimensions,
            raison="Convergence humain-animal-environnement.",
            correspondances=dimensions,
        )
    elif len(dimensions) == 2:
        _ajouter(
            contributions,
            regle="one_health_transversal",
            famille="one_health",
            points=configuration.bonus_one_health_deux_dimensions,
            raison="Deux dimensions One Health sont reliées.",
            correspondances=dimensions,
        )
    elif dimensions == ["Animal"] and not infectieux and not alertes:
        _ajouter(
            contributions,
            regle="animal_isole",
            famille="one_health",
            points=configuration.malus_animal_isole,
            raison=(
                "Contexte animal isolé sans enjeu zoonotique "
                "ou humain explicite."
            ),
            correspondances=dimensions,
        )

    journal.enregistrer(
        identifiant="recherche_fondamentale",
        famille="contexte",
        condition=bool(fondamental),
        raison_declenchee="Un contexte fondamental ou préclinique est présent.",
        raison_non_declenchee="Aucun contexte fondamental détecté.",
    )
    if fondamental:
        malus = (
            configuration.malus_recherche_fondamentale_corroboree
            if (infectieux or alertes or clinique)
            else configuration.malus_recherche_fondamentale
        )
        _ajouter(
            contributions,
            regle="recherche_fondamentale",
            famille="contexte",
            points=malus,
            raison="Contexte surtout expérimental ou préclinique.",
            correspondances=fondamental,
        )

    hors_cible_detectes: list[str] = []

    for domaine, expressions in CONTEXTES_HORS_CIBLE.items():
        correspondances = _correspondances(
            texte_normalise,
            expressions,
        )
        journal.enregistrer(
            identifiant=f"hors_cible:{domaine}",
            famille="contexte",
            condition=bool(correspondances),
            raison_declenchee=(
                f"Le contexte hors cible {domaine} est détecté."
            ),
            raison_non_declenchee=(
                f"Le contexte hors cible {domaine} n'est pas détecté."
            ),
        )
        if not correspondances:
            continue

        hors_cible_detectes.append(domaine)

        malus = (
            configuration.malus_hors_cible_corrobore
            if (infectieux or alertes)
            else configuration.malus_hors_cible
        )

        _ajouter(
            contributions,
            regle=f"hors_cible:{domaine}",
            famille="contexte",
            points=malus,
            raison=(
                "Contexte dominant potentiellement hors cible : "
                f"{domaine}."
            ),
            correspondances=correspondances,
        )

    categories_generiques = {
        "Traitements",
        "Vaccination",
    }.intersection(categories_finales)

    corroboration = bool(
        infectieux
        or alertes
        or surveillance
        or "Maladies infectieuses" in categories_finales
        or "Antibiorésistance" in categories_finales
    )

    condition_generique_fragile = bool(
        categories_generiques and fragiles and not corroboration
    )
    journal.enregistrer(
        identifiant="terme_generique_non_corrobore",
        famille="contexte",
        condition=condition_generique_fragile,
        raison_declenchee="Un terme générique n'est pas corroboré.",
        raison_non_declenchee="Aucun terme générique fragile non corroboré.",
    )
    if condition_generique_fragile:
        _ajouter(
            contributions,
            regle="terme_generique_non_corrobore",
            famille="contexte",
            points=configuration.malus_terme_generique_non_corrobore,
            raison=(
                "Une catégorie repose sur un terme générique sans "
                "contexte infectieux suffisant."
            ),
            correspondances=fragiles,
        )

    condition_convergence_alerte = bool(
        alertes and (infectieux or len(dimensions) >= 2)
    )
    journal.enregistrer(
        identifiant="convergence_alerte",
        famille="convergence",
        condition=condition_convergence_alerte,
        raison_declenchee="L'alerte converge avec d'autres indices.",
        raison_non_declenchee="L'alerte ne converge pas suffisamment.",
    )
    if condition_convergence_alerte:
        _ajouter(
            contributions,
            regle="convergence_alerte",
            famille="convergence",
            points=configuration.bonus_convergence_alerte,
            raison=(
                "Plusieurs indices cohérents renforcent "
                "le signal sanitaire."
            ),
        )

    if (
        "Vaccination" in categories_finales
        and "Essais cliniques" in categories_finales
        and corroboration
    ):
        _ajouter(
            contributions,
            regle="vaccination_clinique",
            famille="convergence",
            points=configuration.bonus_vaccination_clinique,
            raison=(
                "Vaccination étudiée dans un contexte clinique infectieux."
            ),
        )

    if (
        "Antibiorésistance" in categories_finales
        and (surveillance or clinique or alertes)
    ):
        _ajouter(
            contributions,
            regle="amr_actionnable",
            famille="convergence",
            points=configuration.bonus_amr_actionnable,
            raison=(
                "Signal d'antibiorésistance associé à "
                "des données actionnables."
            ),
        )

    score_brut = sum(
        contribution.points
        for contribution in contributions
    )
    score = max(0, min(100, score_brut))
    score_borne = score != score_brut
    decision = configuration.seuils.classer(score)

    confiance = _score_confiance(
        contributions,
        categories_finales,
        dimensions,
        configuration=configuration,
    )

    raisons_positives = [
        contribution.raison
        for contribution in contributions
        if contribution.points > 0
    ]
    raisons_negatives = [
        contribution.raison
        for contribution in contributions
        if contribution.points < 0
    ]

    if not raisons_positives:
        raisons_negatives.insert(
            0,
            "Aucun signal thématique suffisamment spécifique "
            "n'a été détecté.",
        )

    bonus = [
        contribution
        for contribution in contributions
        if contribution.points > 0
    ]
    malus = [
        contribution
        for contribution in contributions
        if contribution.points < 0
    ]

    contradiction_detectee = _detecter_contradiction(contributions)
    indice_conflit = _calculer_indice_conflit(contributions)
    niveau_conflit = _determiner_niveau_conflit(
        indice_conflit,
        configuration=configuration,
    )
    marge_decision = _calculer_marge_decision(
        score,
        configuration.seuils,
    )
    decision_fragile = (
        marge_decision <= configuration.marge_decision_fragile
        or niveau_conflit == "fort"
    )
    principal_bonus = _contribution_extreme(
        contributions,
        type_recherche="bonus",
    )
    principal_malus = _contribution_extreme(
        contributions,
        type_recherche="malus",
    )
    categorie_principale = _categorie_plus_contributive(contributions)
    empreinte = _construire_empreinte(
        texte_normalise=texte_normalise,
        categories=categories_finales,
        dimensions=dimensions,
        configuration=configuration,
    )

    stabilite_score = _analyser_stabilite(
        contributions,
        marge_decision=marge_decision,
        configuration=configuration,
    )
    configuration_hash = _calculer_configuration_hash(configuration)
    referentiel_hash = _calculer_referentiel_hash()

    qualite_entree = _determiner_qualite_entree(
        texte_normalise,
        categories_finales,
        dimensions,
    )

    return {
        "score_pertinence": score,
        "score_pertinence_brut": score_brut,
        "score_borne": score_borne,
        "niveau_pertinence": decision,
        "retenu": decision in {"pertinent", "prioritaire"},
        "confiance": confiance,
        "qualite_entree": qualite_entree,
        "categories": categories_finales,
        "one_health": dimensions,
        "contextes_hors_cible": list(
            dedupliquer(hors_cible_detectes)
        ),
        "signaux_detectes": {
            nom: list(valeurs)
            for nom, valeurs in signaux.items()
        },
        "raisons": list(
            dedupliquer(raisons_positives + raisons_negatives)
        ),
        "raisons_positives": list(
            dedupliquer(raisons_positives)
        ),
        "raisons_negatives": list(
            dedupliquer(raisons_negatives)
        ),
        "contributions": [
            contribution.exporter()
            for contribution in contributions
        ],
        "scores_par_famille": _resumer_scores(contributions),
        "nombre_contributions": len(contributions),
        "nombre_bonus": len(bonus),
        "nombre_malus": len(malus),
        "contradiction_detectee": contradiction_detectee,
        "indice_conflit": indice_conflit,
        "niveau_conflit": niveau_conflit,
        "marge_decision": marge_decision,
        "decision_fragile": decision_fragile,
        "categorie_plus_contributive": categorie_principale,
        "principal_bonus": (
            principal_bonus.exporter()
            if principal_bonus is not None
            else None
        ),
        "principal_malus": (
            principal_malus.exporter()
            if principal_malus is not None
            else None
        ),
        "audit": {
            "empreinte": empreinte,
            "source_categories": source_categories,
            "source_one_health": source_one_health,
            "categories_inconnues": categories_inconnues,
            "dimensions_inconnues": dimensions_inconnues,
            "marge_decision": marge_decision,
            "decision_fragile": decision_fragile,
            "engine_version": ENGINE_VERSION,
            "ruleset_version": RULESET_VERSION,
            "configuration_hash": configuration_hash,
            "referentiel_hash": referentiel_hash,
            "regles_evaluees": len(journal.traces),
            "regles_declenchees": sum(
                trace["statut"] == "declenchee"
                for trace in journal.traces
            ),
            "regles_non_declenchees": sum(
                trace["statut"] == "non_declenchee"
                for trace in journal.traces
            ),
            "journal_regles": list(journal.traces),
        },
        "stabilite_score": stabilite_score,
        "synthese": _construire_synthese(
            score=score,
            score_brut=score_brut,
            decision=decision,
            confiance=confiance,
            nombre_bonus=len(bonus),
            nombre_malus=len(malus),
            contradiction_detectee=contradiction_detectee,
            marge_decision=marge_decision,
            decision_fragile=decision_fragile,
        ),
        "configuration": asdict(configuration),
    }


def analyser_pertinence(
    article: Mapping[str, Any] | None,
    *,
    categories: Sequence[str] | None = None,
    one_health: Sequence[str] | None = None,
    configuration: ConfigurationPertinence = CONFIGURATION_PAR_DEFAUT,
) -> ResultatPertinence:
    """Évalue un article normalisé ou issu d'un flux RSS/API."""
    if article is not None and not isinstance(article, Mapping):
        raise TypeError(
            "article doit être un objet compatible avec Mapping ou None."
        )

    texte = construire_texte(article)
    if not isinstance(texte, str):
        raise TypeError(
            "construire_texte(article) doit retourner une chaîne."
        )

    return analyser_pertinence_dans_texte(
        texte,
        categories=categories,
        one_health=one_health,
        configuration=configuration,
    )


def calculer_pertinence(
    article: Mapping[str, Any] | None,
    *,
    configuration: ConfigurationPertinence = CONFIGURATION_PAR_DEFAUT,
) -> int:
    """API courte lorsque seul le score est nécessaire."""
    return analyser_pertinence(
        article,
        configuration=configuration,
    )["score_pertinence"]



# ---------------------------------------------------------------------------
# Intégration officielle au pipeline V6
# ---------------------------------------------------------------------------


def _resultat_pertinence_valide(
    resultat: Mapping[str, Any],
) -> ResultatPertinence:
    """Valide le minimum contractuel d'un résultat de pertinence."""
    if not isinstance(resultat, Mapping):
        raise TypeError("resultat doit être compatible avec Mapping.")

    champs_requis = {
        "score_pertinence",
        "niveau_pertinence",
        "retenu",
        "confiance",
        "niveau_conflit",
        "decision_fragile",
        "stabilite_score",
    }
    manquants = sorted(champs_requis.difference(resultat))
    if manquants:
        raise ValueError(
            "Résultat de pertinence incomplet : " + ", ".join(manquants)
        )
    return dict(resultat)  # type: ignore[return-value]


def obtenir_score_pertinence(resultat: Mapping[str, Any]) -> int:
    """Retourne le score de pertinence borné entre 0 et 100."""
    valeur = resultat.get("score_pertinence", 0)
    if isinstance(valeur, bool) or not isinstance(valeur, int):
        return 0
    return max(0, min(100, valeur))


def obtenir_decision_pertinence(
    resultat: Mapping[str, Any],
) -> DecisionPertinence:
    """Retourne une décision reconnue, sinon ``rejet``."""
    valeur = resultat.get("niveau_pertinence")
    if valeur in {"rejet", "a_revoir", "pertinent", "prioritaire"}:
        return valeur  # type: ignore[return-value]
    return "rejet"


def obtenir_confiance_pertinence(resultat: Mapping[str, Any]) -> int:
    """Retourne la confiance déterministe bornée entre 0 et 100."""
    valeur = resultat.get("confiance", 0)
    if isinstance(valeur, bool) or not isinstance(valeur, int):
        return 0
    return max(0, min(100, valeur))


def pertinence_est_retenue(resultat: Mapping[str, Any]) -> bool:
    """Indique si le contenu est classé pertinent ou prioritaire."""
    valeur = resultat.get("retenu")
    if isinstance(valeur, bool):
        return valeur
    return obtenir_decision_pertinence(resultat) in {"pertinent", "prioritaire"}


def pertinence_est_prioritaire(resultat: Mapping[str, Any]) -> bool:
    """Indique si la décision de pertinence est prioritaire."""
    return obtenir_decision_pertinence(resultat) == "prioritaire"


def contient_conflit_pertinence(resultat: Mapping[str, Any]) -> bool:
    """Indique si des indices favorables et défavorables coexistent."""
    contradiction = resultat.get("contradiction_detectee")
    if isinstance(contradiction, bool):
        return contradiction
    return resultat.get("niveau_conflit") in {"modere", "fort"}


def statistiques_pertinence(resultat: Mapping[str, Any]) -> dict[str, Any]:
    """Construit un résumé stable destiné au diagnostic et à l'audit."""
    stabilite = resultat.get("stabilite_score", {})
    niveau_stabilite = (
        stabilite.get("niveau", "stable")
        if isinstance(stabilite, Mapping)
        else "stable"
    )
    return {
        "score_pertinence": obtenir_score_pertinence(resultat),
        "niveau_pertinence": obtenir_decision_pertinence(resultat),
        "retenu": pertinence_est_retenue(resultat),
        "prioritaire": pertinence_est_prioritaire(resultat),
        "confiance": obtenir_confiance_pertinence(resultat),
        "niveau_conflit": str(resultat.get("niveau_conflit", "aucun")),
        "decision_fragile": bool(resultat.get("decision_fragile", False)),
        "stabilite": str(niveau_stabilite),
        "nombre_contributions": int(
            resultat.get("nombre_contributions", 0) or 0
        ),
    }


def executer(etat: "EtatClassification") -> None:
    """Exécute l'étape pertinence sur l'état partagé du pipeline V6.

    La fonction réutilise les catégories et dimensions One Health déjà
    calculées, sans déplacer ni modifier aucune règle métier.
    """
    contexte = getattr(etat, "contexte", None)
    if contexte is None:
        raise TypeError("etat doit exposer un attribut contexte.")

    texte = getattr(contexte, "texte", None)
    if not isinstance(texte, str):
        raise TypeError("etat.contexte.texte doit être une chaîne.")

    categories = getattr(contexte, "categories", None)
    if categories is not None and (
        isinstance(categories, (str, bytes))
        or not isinstance(categories, Sequence)
    ):
        raise TypeError("etat.contexte.categories doit être une séquence.")

    one_health = getattr(contexte, "one_health", None)
    if one_health is not None and (
        isinstance(one_health, (str, bytes))
        or not isinstance(one_health, Sequence)
    ):
        raise TypeError("etat.contexte.one_health doit être une séquence.")

    resultat = analyser_pertinence_dans_texte(
        texte,
        categories=categories,
        one_health=one_health,
    )
    resultat = _resultat_pertinence_valide(resultat)

    definir_resultat = getattr(contexte, "definir_resultat", None)
    if callable(definir_resultat):
        definir_resultat("pertinence", resultat)
    else:
        setattr(contexte, "pertinence", dict(resultat))

    extensions = getattr(etat, "extensions", None)
    if isinstance(extensions, dict):
        extensions["pertinence"] = dict(resultat)
        versions = extensions.setdefault("versions_modules", {})
        if isinstance(versions, dict):
            versions["pertinence"] = VERSION_PERTINENCE

    audit = getattr(etat, "audit", None)
    enregistrer = getattr(audit, "enregistrer", None)
    if callable(enregistrer):
        enregistrer(
            "pertinence_calculee",
            etape="pertinence",
            donnees=statistiques_pertinence(resultat),
        )


executer_pertinence = executer


__all__ = [
    "VERSION_PERTINENCE",
    "CONFIGURATION_PAR_DEFAUT",
    "ENGINE_VERSION",
    "CONTEXTES_HORS_CIBLE",
    "AuditPertinence",
    "ConfigurationPertinence",
    "Contribution",
    "ContributionExportee",
    "DecisionPertinence",
    "FamilleContribution",
    "DIMENSIONS_ONE_HEALTH_AUTORISEES",
    "NiveauConflit",
    "NiveauStabilite",
    "POIDS_CATEGORIES",
    "QualiteEntree",
    "RECHERCHE_FONDAMENTALE",
    "RULESET_VERSION",
    "ResultatPertinence",
    "ResumeScores",
    "SIGNAUX_ALERTE",
    "SIGNAUX_CLINIQUES",
    "SIGNAUX_INFECTIEUX",
    "SIGNAUX_SURVEILLANCE",
    "SeuilsPertinence",
    "SourceMetadonnees",
    "StabiliteScore",
    "StatutRegle",
    "TraceRegle",
    "TERMES_GENERIQUES_FRAGILES",
    "TypeContribution",
    "analyser_pertinence",
    "analyser_pertinence_dans_texte",
    "calculer_pertinence",
    "contient_conflit_pertinence",
    "executer",
    "executer_pertinence",
    "obtenir_confiance_pertinence",
    "obtenir_decision_pertinence",
    "obtenir_score_pertinence",
    "pertinence_est_prioritaire",
    "pertinence_est_retenue",
    "statistiques_pertinence",
]