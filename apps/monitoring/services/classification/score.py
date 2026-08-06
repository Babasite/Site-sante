"""
Agrégation déterministe, explicable et configurable des scores du moteur.

Version 7.

Ce module ne détecte aucun thème. Il agrège uniquement les résultats déjà
produits par les modules de pertinence, de preuve et d'importance. Le calcul
reste borné, reproductible, auditable et sans dépendance externe.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
import hashlib
import json
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Final, Literal, TypedDict


ENGINE_VERSION: Final[str] = "7.0"
RULESET_VERSION: Final[str] = "2026.03"
VERSION_SCORE: Final[str] = "8.0.0"

if TYPE_CHECKING:
    from .pipeline import EtatClassification


FacteurLimitant = Literal[
    "aucun",
    "pertinence",
    "importance",
    "preuve",
    "plafond",
]

ComposanteDominante = Literal[
    "aucune",
    "pertinence",
    "importance",
    "preuve",
]

NiveauRobustesseScore = Literal[
    "nulle",
    "faible",
    "moderee",
    "forte",
    "tres_forte",
]

NiveauStabiliteScore = Literal[
    "instable",
    "fragile",
    "stable",
    "tres_stable",
]

QualiteEntreeScore = Literal[
    "insuffisante",
    "partielle",
    "complete",
]

NiveauCoherenceScore = Literal[
    "incoherente",
    "fragile",
    "coherente",
    "fortement_coherente",
]

ClasseDecisionScore = Literal[
    "rejet",
    "surveillance",
    "prioritaire",
    "hautement_prioritaire",
]


class TraceComposanteScore(TypedDict):
    """Trace détaillée d'une composante du score global."""

    ordre: int
    nom: str
    valeur_entree: int
    ponderation: int | None
    contribution: int
    part_score_brut: int
    raison: str


class ControleScore(TypedDict):
    """Résultat d'un contrôle déterministe de cohérence."""

    identifiant: str
    conforme: bool
    severite: str
    explication: str


class AuditScore(TypedDict):
    """Informations de traçabilité et de reproductibilité."""

    engine_version: str
    ruleset_version: str
    configuration_hash: str
    calcul_hash: str
    resultat_hash: str
    nombre_composantes: int
    nombre_controles: int
    controles_conformes: int
    controles_non_conformes: int
    score_avant_plafond: int
    plafond_applique: int
    plafond_active: bool
    composante_dominante: ComposanteDominante
    facteur_limitant: FacteurLimitant
    facteurs_limitants: list[FacteurLimitant]
    controles: list[ControleScore]
    journal_calcul: list[TraceComposanteScore]


class ResultatScore(TypedDict):
    """Résultat public complet du moteur d'agrégation."""

    score_global: int
    score_global_brut: int
    score_avant_plafond: int
    score_normalise: int
    score_pertinence: int
    score_importance: int
    niveau_preuve: int
    plafond_applique: int
    plafond_active: bool
    composantes_score: list[dict[str, Any]]
    composante_dominante: ComposanteDominante
    facteur_limitant: FacteurLimitant
    robustesse_score: NiveauRobustesseScore
    stabilite_score: NiveauStabiliteScore
    indice_stabilite: int
    score_confiance: int
    qualite_entree: QualiteEntreeScore
    decision_fragile: bool
    marge_plafond: int
    ecart_composantes: int
    facteurs_limitants: list[FacteurLimitant]
    indice_coherence: int
    niveau_coherence: NiveauCoherenceScore
    classe_decision: ClasseDecisionScore
    alertes: list[str]
    controles: list[ControleScore]
    synthese: str
    audit: AuditScore
    configuration: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ComposanteScore:
    """Contribution explicable d'une composante."""

    nom: str
    points: int
    raison: str

    def __post_init__(self) -> None:
        if not isinstance(self.nom, str) or not self.nom.strip():
            raise ValueError("nom doit être une chaîne non vide.")
        if isinstance(self.points, bool) or not isinstance(self.points, int):
            raise TypeError("points doit être un entier.")
        if not isinstance(self.raison, str) or not self.raison.strip():
            raise ValueError("raison doit être une chaîne non vide.")


def _bonus_preuve_defaut() -> dict[int, int]:
    return {
        0: 0,
        1: 2,
        2: 5,
        3: 9,
        4: 13,
        5: 16,
    }


@dataclass(frozen=True, slots=True)
class ConfigurationScore:
    """Configuration complète du moteur de score."""

    poids_pertinence: int = 75
    poids_importance: int = 15
    bonus_preuve: Mapping[int, int] = field(
        default_factory=_bonus_preuve_defaut
    )

    seuil_rejet_pertinence: int = 20
    seuil_limitation_pertinence: int = 40
    plafond_rejet: int = 19
    plafond_limitation: int = 49

    seuil_robustesse_faible: int = 25
    seuil_robustesse_moderee: int = 50
    seuil_robustesse_forte: int = 70
    seuil_robustesse_tres_forte: int = 85

    seuil_stabilite_fragile: int = 25
    seuil_stabilite_stable: int = 50
    seuil_stabilite_tres_stable: int = 75
    seuil_decision_fragile: int = 35

    seuil_coherence_fragile: int = 35
    seuil_coherence_coherente: int = 65
    seuil_coherence_forte: int = 85

    seuil_classe_surveillance: int = 20
    seuil_classe_prioritaire: int = 50
    seuil_classe_hautement_prioritaire: int = 80

    def __post_init__(self) -> None:
        champs_entiers = (
            "poids_pertinence",
            "poids_importance",
            "seuil_rejet_pertinence",
            "seuil_limitation_pertinence",
            "plafond_rejet",
            "plafond_limitation",
            "seuil_robustesse_faible",
            "seuil_robustesse_moderee",
            "seuil_robustesse_forte",
            "seuil_robustesse_tres_forte",
            "seuil_stabilite_fragile",
            "seuil_stabilite_stable",
            "seuil_stabilite_tres_stable",
            "seuil_decision_fragile",
            "seuil_coherence_fragile",
            "seuil_coherence_coherente",
            "seuil_coherence_forte",
            "seuil_classe_surveillance",
            "seuil_classe_prioritaire",
            "seuil_classe_hautement_prioritaire",
        )

        for nom in champs_entiers:
            valeur = getattr(self, nom)
            if isinstance(valeur, bool) or not isinstance(valeur, int):
                raise TypeError(f"{nom} doit être un entier.")

        if not 0 <= self.poids_pertinence <= 100:
            raise ValueError(
                "poids_pertinence doit être compris entre 0 et 100."
            )
        if not 0 <= self.poids_importance <= 100:
            raise ValueError(
                "poids_importance doit être compris entre 0 et 100."
            )
        if self.poids_pertinence + self.poids_importance > 100:
            raise ValueError(
                "La somme des poids pertinence et importance "
                "ne peut pas dépasser 100."
            )
        if self.poids_pertinence <= self.poids_importance:
            raise ValueError(
                "La pertinence doit rester la composante pondérée dominante."
            )

        if not (
            0
            <= self.seuil_rejet_pertinence
            < self.seuil_limitation_pertinence
            <= 100
        ):
            raise ValueError(
                "Les seuils de pertinence doivent être croissants "
                "et compris entre 0 et 100."
            )

        if not 0 <= self.plafond_rejet <= self.plafond_limitation <= 100:
            raise ValueError(
                "Les plafonds doivent être croissants et compris "
                "entre 0 et 100."
            )

        seuils_robustesse = (
            self.seuil_robustesse_faible,
            self.seuil_robustesse_moderee,
            self.seuil_robustesse_forte,
            self.seuil_robustesse_tres_forte,
        )
        if not (
            0
            <= seuils_robustesse[0]
            < seuils_robustesse[1]
            < seuils_robustesse[2]
            < seuils_robustesse[3]
            <= 100
        ):
            raise ValueError(
                "Les seuils de robustesse doivent être strictement "
                "croissants entre 0 et 100."
            )

        seuils_stabilite = (
            self.seuil_stabilite_fragile,
            self.seuil_stabilite_stable,
            self.seuil_stabilite_tres_stable,
        )
        if not (
            0
            <= seuils_stabilite[0]
            < seuils_stabilite[1]
            < seuils_stabilite[2]
            <= 100
        ):
            raise ValueError(
                "Les seuils de stabilité doivent être strictement "
                "croissants entre 0 et 100."
            )
        if not 0 <= self.seuil_decision_fragile <= 100:
            raise ValueError(
                "seuil_decision_fragile doit être compris entre 0 et 100."
            )

        seuils_coherence = (
            self.seuil_coherence_fragile,
            self.seuil_coherence_coherente,
            self.seuil_coherence_forte,
        )
        if not (
            0
            <= seuils_coherence[0]
            < seuils_coherence[1]
            < seuils_coherence[2]
            <= 100
        ):
            raise ValueError(
                "Les seuils de cohérence doivent être strictement "
                "croissants entre 0 et 100."
            )

        seuils_classes = (
            self.seuil_classe_surveillance,
            self.seuil_classe_prioritaire,
            self.seuil_classe_hautement_prioritaire,
        )
        if not (
            0
            <= seuils_classes[0]
            < seuils_classes[1]
            < seuils_classes[2]
            <= 100
        ):
            raise ValueError(
                "Les seuils de classe doivent être strictement "
                "croissants entre 0 et 100."
            )

        bonus = dict(self.bonus_preuve)
        if set(bonus) != set(range(6)):
            raise ValueError(
                "bonus_preuve doit contenir exactement les niveaux 0 à 5."
            )

        precedent = -1
        for niveau in range(6):
            valeur = bonus[niveau]
            if isinstance(valeur, bool) or not isinstance(valeur, int):
                raise TypeError(
                    f"Le bonus du niveau {niveau} doit être un entier."
                )
            if not 0 <= valeur <= 100:
                raise ValueError(
                    f"Le bonus du niveau {niveau} doit être compris "
                    "entre 0 et 100."
                )
            if valeur < precedent:
                raise ValueError(
                    "Les bonus de preuve doivent être croissants."
                )
            precedent = valeur

        object.__setattr__(
            self,
            "bonus_preuve",
            MappingProxyType(bonus),
        )


CONFIGURATION_PAR_DEFAUT = ConfigurationScore()
BONUS_PREUVE: Final[Mapping[int, int]] = (
    CONFIGURATION_PAR_DEFAUT.bonus_preuve
)


def _entier(value: Any, default: int = 0) -> int:
    """Convertit une valeur en entier sans lever d'exception métier."""
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


def _borner(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _json_compatible(value: Any) -> Any:
    """Transforme les mappings immuables en objets JSON sérialisables."""
    if isinstance(value, Mapping):
        return {
            str(cle): _json_compatible(valeur)
            for cle, valeur in value.items()
        }
    if isinstance(value, tuple):
        return [_json_compatible(element) for element in value]
    return value


def _empreinte_json(value: Any) -> str:
    serialise = json.dumps(
        _json_compatible(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialise.encode("utf-8")).hexdigest()


def _configuration_dict(
    configuration: ConfigurationScore,
) -> dict[str, Any]:
    return {
        "poids_pertinence": configuration.poids_pertinence,
        "poids_importance": configuration.poids_importance,
        "bonus_preuve": dict(configuration.bonus_preuve),
        "seuil_rejet_pertinence": (
            configuration.seuil_rejet_pertinence
        ),
        "seuil_limitation_pertinence": (
            configuration.seuil_limitation_pertinence
        ),
        "plafond_rejet": configuration.plafond_rejet,
        "plafond_limitation": configuration.plafond_limitation,
        "seuil_robustesse_faible": (
            configuration.seuil_robustesse_faible
        ),
        "seuil_robustesse_moderee": (
            configuration.seuil_robustesse_moderee
        ),
        "seuil_robustesse_forte": (
            configuration.seuil_robustesse_forte
        ),
        "seuil_robustesse_tres_forte": (
            configuration.seuil_robustesse_tres_forte
        ),
        "seuil_stabilite_fragile": configuration.seuil_stabilite_fragile,
        "seuil_stabilite_stable": configuration.seuil_stabilite_stable,
        "seuil_stabilite_tres_stable": (
            configuration.seuil_stabilite_tres_stable
        ),
        "seuil_decision_fragile": configuration.seuil_decision_fragile,
        "seuil_coherence_fragile": configuration.seuil_coherence_fragile,
        "seuil_coherence_coherente": (
            configuration.seuil_coherence_coherente
        ),
        "seuil_coherence_forte": configuration.seuil_coherence_forte,
        "seuil_classe_surveillance": (
            configuration.seuil_classe_surveillance
        ),
        "seuil_classe_prioritaire": (
            configuration.seuil_classe_prioritaire
        ),
        "seuil_classe_hautement_prioritaire": (
            configuration.seuil_classe_hautement_prioritaire
        ),
    }


def _configuration_hash(
    configuration: ConfigurationScore,
) -> str:
    return _empreinte_json(_configuration_dict(configuration))


def _extraire_score_importance(
    importance: Mapping[str, Any] | int | None,
) -> int:
    if isinstance(importance, Mapping):
        valeur = importance.get(
            "importance",
            importance.get("score_importance", 0),
        )
        return _entier(valeur)
    return _entier(importance)


def _determiner_plafond(
    *,
    score_pertinence: int,
    configuration: ConfigurationScore,
) -> int:
    if score_pertinence < configuration.seuil_rejet_pertinence:
        return configuration.plafond_rejet
    if score_pertinence < configuration.seuil_limitation_pertinence:
        return configuration.plafond_limitation
    return 100


def _composante_dominante(
    composantes: list[ComposanteScore],
) -> ComposanteDominante:
    if not composantes:
        return "aucune"

    ordre = {
        "pertinence": 3,
        "importance": 2,
        "preuve": 1,
    }
    meilleure = max(
        composantes,
        key=lambda composante: (
            composante.points,
            ordre.get(composante.nom, 0),
        ),
    )

    if meilleure.points <= 0:
        return "aucune"

    if meilleure.nom in {"pertinence", "importance", "preuve"}:
        return meilleure.nom  # type: ignore[return-value]

    return "aucune"


def _facteur_limitant(
    *,
    score_pertinence: int,
    score_importance: int,
    niveau_preuve: int,
    plafond_active: bool,
) -> FacteurLimitant:
    if plafond_active:
        return "plafond"
    if score_pertinence < 40:
        return "pertinence"
    if score_importance < 25:
        return "importance"
    if niveau_preuve <= 1:
        return "preuve"
    return "aucun"


def _facteurs_limitants(
    *,
    score_pertinence: int,
    score_importance: int,
    niveau_preuve: int,
    plafond_active: bool,
) -> list[FacteurLimitant]:
    facteurs: list[FacteurLimitant] = []
    if plafond_active:
        facteurs.append("plafond")
    if score_pertinence < 40:
        facteurs.append("pertinence")
    if score_importance < 25:
        facteurs.append("importance")
    if niveau_preuve <= 1:
        facteurs.append("preuve")
    return facteurs or ["aucun"]


def _qualite_entree(
    *,
    pertinence: Mapping[str, Any],
    preuve: Mapping[str, Any] | None,
    importance: Mapping[str, Any] | int | None,
) -> QualiteEntreeScore:
    presents = 0
    if "score_pertinence" in pertinence:
        presents += 1
    if preuve is not None and "niveau_preuve" in preuve:
        presents += 1
    if isinstance(importance, Mapping):
        if "importance" in importance or "score_importance" in importance:
            presents += 1
    elif importance is not None:
        presents += 1

    if presents == 3:
        return "complete"
    if presents >= 1:
        return "partielle"
    return "insuffisante"


def _indice_stabilite(
    *,
    score_global: int,
    score_brut: int,
    plafond: int,
    composantes: list[ComposanteScore],
    niveau_preuve: int,
) -> tuple[int, int, int]:
    contributions = sorted(
        (composante.points for composante in composantes),
        reverse=True,
    )
    ecart_composantes = (
        contributions[0] - contributions[1]
        if len(contributions) >= 2
        else contributions[0] if contributions else 0
    )
    marge_plafond = max(0, plafond - score_global)

    indice = 50
    indice += min(25, ecart_composantes)
    indice += min(15, marge_plafond // 2)
    indice += niveau_preuve * 2
    if score_global < score_brut:
        indice -= 25
    if score_global < 20:
        indice -= 20

    return _borner(indice, 0, 100), marge_plafond, ecart_composantes


def _niveau_stabilite(
    indice: int,
    configuration: ConfigurationScore,
) -> NiveauStabiliteScore:
    if indice < configuration.seuil_stabilite_fragile:
        return "instable"
    if indice < configuration.seuil_stabilite_stable:
        return "fragile"
    if indice < configuration.seuil_stabilite_tres_stable:
        return "stable"
    return "tres_stable"


def _score_confiance(
    *,
    qualite_entree: QualiteEntreeScore,
    indice_stabilite: int,
    robustesse: NiveauRobustesseScore,
    plafond_active: bool,
) -> int:
    base = {
        "insuffisante": 20,
        "partielle": 55,
        "complete": 80,
    }[qualite_entree]
    ajustement_robustesse = {
        "nulle": -30,
        "faible": -15,
        "moderee": 0,
        "forte": 10,
        "tres_forte": 15,
    }[robustesse]
    score = round(base * 0.6 + indice_stabilite * 0.4)
    score += ajustement_robustesse
    if plafond_active:
        score -= 10
    return _borner(score, 0, 100)


def _mettre_a_jour_parts_journal(
    journal: list[TraceComposanteScore],
    score_brut: int,
) -> None:
    for trace in journal:
        trace["part_score_brut"] = (
            round(trace["contribution"] * 100 / score_brut)
            if score_brut > 0
            else 0
        )


def _controles_coherence(
    *,
    score_pertinence: int,
    score_importance: int,
    niveau_preuve: int,
    score_brut: int,
    score_global: int,
    plafond: int,
    plafond_active: bool,
    qualite_entree: QualiteEntreeScore,
) -> list[ControleScore]:
    return [
        {
            "identifiant": "SCORE_BORNE",
            "conforme": 0 <= score_global <= 100,
            "severite": "critique",
            "explication": "Le score global doit rester compris entre 0 et 100.",
        },
        {
            "identifiant": "PLAFOND_RESPECTE",
            "conforme": score_global <= plafond,
            "severite": "critique",
            "explication": "Le score global ne doit jamais dépasser le plafond.",
        },
        {
            "identifiant": "PLAFOND_COHERENT",
            "conforme": plafond_active == (score_global < score_brut),
            "severite": "majeure",
            "explication": "L'indicateur de plafond doit refléter le calcul réel.",
        },
        {
            "identifiant": "PERTINENCE_DOMINANTE",
            "conforme": not (
                score_pertinence < 20 and score_global >= 20
            ),
            "severite": "critique",
            "explication": (
                "Une pertinence très faible ne doit pas produire "
                "un score global prioritaire."
            ),
        },
        {
            "identifiant": "ENTREES_BORNEES",
            "conforme": (
                0 <= score_pertinence <= 100
                and 0 <= score_importance <= 100
                and 0 <= niveau_preuve <= 5
            ),
            "severite": "critique",
            "explication": "Toutes les entrées normalisées doivent être bornées.",
        },
        {
            "identifiant": "QUALITE_ENTREE",
            "conforme": qualite_entree != "insuffisante",
            "severite": "mineure",
            "explication": "Au moins une entrée explicite doit être disponible.",
        },
    ]


def _indice_coherence(
    controles: list[ControleScore],
) -> int:
    poids = {
        "critique": 3,
        "majeure": 2,
        "mineure": 1,
    }
    total = sum(poids.get(controle["severite"], 1) for controle in controles)
    conforme = sum(
        poids.get(controle["severite"], 1)
        for controle in controles
        if controle["conforme"]
    )
    return round(conforme * 100 / total) if total else 100


def _niveau_coherence(
    indice: int,
    configuration: ConfigurationScore,
) -> NiveauCoherenceScore:
    if indice < configuration.seuil_coherence_fragile:
        return "incoherente"
    if indice < configuration.seuil_coherence_coherente:
        return "fragile"
    if indice < configuration.seuil_coherence_forte:
        return "coherente"
    return "fortement_coherente"


def _classe_decision(
    score_global: int,
    configuration: ConfigurationScore,
) -> ClasseDecisionScore:
    if score_global < configuration.seuil_classe_surveillance:
        return "rejet"
    if score_global < configuration.seuil_classe_prioritaire:
        return "surveillance"
    if score_global < configuration.seuil_classe_hautement_prioritaire:
        return "prioritaire"
    return "hautement_prioritaire"


def _construire_alertes(
    *,
    decision_fragile: bool,
    plafond_active: bool,
    qualite_entree: QualiteEntreeScore,
    niveau_coherence: NiveauCoherenceScore,
    facteurs_limitants: list[FacteurLimitant],
) -> list[str]:
    alertes: list[str] = []
    if decision_fragile:
        alertes.append("La décision est fragile.")
    if plafond_active:
        alertes.append("Le score a été limité par un plafond de pertinence.")
    if qualite_entree != "complete":
        alertes.append("Les données d'entrée sont incomplètes.")
    if niveau_coherence in {"incoherente", "fragile"}:
        alertes.append("La cohérence globale du calcul est insuffisante.")
    limites = [f for f in facteurs_limitants if f != "aucun"]
    if len(limites) >= 2:
        alertes.append("Plusieurs facteurs limitants sont simultanément actifs.")
    return alertes


def _robustesse_score(
    *,
    score_global: int,
    score_pertinence: int,
    niveau_preuve: int,
    plafond_active: bool,
    configuration: ConfigurationScore,
) -> NiveauRobustesseScore:
    if score_global <= 0 or score_pertinence <= 0:
        return "nulle"

    if plafond_active:
        return "faible"

    score_robustesse = score_global
    if niveau_preuve <= 1:
        score_robustesse = min(
            score_robustesse,
            configuration.seuil_robustesse_moderee - 1,
        )

    if score_robustesse < configuration.seuil_robustesse_faible:
        return "faible"
    if score_robustesse < configuration.seuil_robustesse_moderee:
        return "moderee"
    if score_robustesse < configuration.seuil_robustesse_forte:
        return "forte"
    if score_robustesse < configuration.seuil_robustesse_tres_forte:
        return "forte"
    return "tres_forte"


def _construire_synthese(
    *,
    score_global: int,
    score_brut: int,
    plafond: int,
    composante_dominante: ComposanteDominante,
    facteur_limitant: FacteurLimitant,
    robustesse: NiveauRobustesseScore,
    stabilite: NiveauStabiliteScore,
    score_confiance: int,
    niveau_coherence: NiveauCoherenceScore,
    classe_decision: ClasseDecisionScore,
) -> str:
    plafond_texte = (
        f"Un plafond de {plafond} a limité le score brut de {score_brut}."
        if score_global < score_brut
        else "Aucun plafond n'a réduit le score."
    )
    return (
        f"Score global : {score_global}/100. "
        f"Composante dominante : {composante_dominante}. "
        f"Facteur limitant : {facteur_limitant}. "
        f"Robustesse : {robustesse}. "
        f"Stabilité : {stabilite}. "
        f"Confiance du calcul : {score_confiance}/100. "
        f"Cohérence : {niveau_coherence}. "
        f"Classe de décision : {classe_decision}. "
        f"{plafond_texte}"
    )


def calculer_score_global(
    *,
    pertinence: Mapping[str, Any],
    preuve: Mapping[str, Any] | None = None,
    importance: Mapping[str, Any] | int | None = None,
    configuration: ConfigurationScore = CONFIGURATION_PAR_DEFAUT,
) -> ResultatScore:
    """Calcule le score global sans introduire de nouvelle règle métier.

    La pertinence reste dominante. La preuve et l'importance ne peuvent pas
    rendre prioritaire un article thématiquement hors cible.
    """
    if not isinstance(pertinence, Mapping):
        raise TypeError("pertinence doit être compatible avec Mapping.")
    if preuve is not None and not isinstance(preuve, Mapping):
        raise TypeError("preuve doit être compatible avec Mapping ou None.")
    if not (
        importance is None
        or isinstance(importance, Mapping)
        or isinstance(importance, int)
    ):
        raise TypeError(
            "importance doit être un Mapping, un entier ou None."
        )
    if not isinstance(configuration, ConfigurationScore):
        raise TypeError(
            "configuration doit être une instance de ConfigurationScore."
        )

    score_pertinence = _borner(
        _entier(pertinence.get("score_pertinence")),
        0,
        100,
    )
    niveau_preuve = _borner(
        _entier((preuve or {}).get("niveau_preuve")),
        0,
        5,
    )
    score_importance = _borner(
        _extraire_score_importance(importance),
        0,
        100,
    )

    contribution_pertinence = round(
        score_pertinence * configuration.poids_pertinence / 100
    )
    contribution_importance = round(
        score_importance * configuration.poids_importance / 100
    )
    contribution_preuve = configuration.bonus_preuve[niveau_preuve]

    composantes = [
        ComposanteScore(
            "pertinence",
            contribution_pertinence,
            (
                "Contribution issue du score de pertinence "
                f"{score_pertinence}/100 pondéré à "
                f"{configuration.poids_pertinence} %."
            ),
        ),
        ComposanteScore(
            "importance",
            contribution_importance,
            (
                "Contribution issue du score d'importance "
                f"{score_importance}/100 pondéré à "
                f"{configuration.poids_importance} %."
            ),
        ),
        ComposanteScore(
            "preuve",
            contribution_preuve,
            (
                f"Bonus associé au niveau de preuve "
                f"{niveau_preuve}/5."
            ),
        ),
    ]

    journal: list[TraceComposanteScore] = [
        {
            "ordre": 1,
            "nom": "pertinence",
            "valeur_entree": score_pertinence,
            "ponderation": configuration.poids_pertinence,
            "contribution": contribution_pertinence,
            "part_score_brut": 0,
            "raison": composantes[0].raison,
        },
        {
            "ordre": 2,
            "nom": "importance",
            "valeur_entree": score_importance,
            "ponderation": configuration.poids_importance,
            "contribution": contribution_importance,
            "part_score_brut": 0,
            "raison": composantes[1].raison,
        },
        {
            "ordre": 3,
            "nom": "preuve",
            "valeur_entree": niveau_preuve,
            "ponderation": None,
            "contribution": contribution_preuve,
            "part_score_brut": 0,
            "raison": composantes[2].raison,
        },
    ]

    score_brut = sum(composante.points for composante in composantes)
    _mettre_a_jour_parts_journal(journal, score_brut)
    plafond = _determiner_plafond(
        score_pertinence=score_pertinence,
        configuration=configuration,
    )
    score_global = _borner(score_brut, 0, plafond)
    plafond_active = score_global < score_brut

    dominante = _composante_dominante(composantes)
    facteur = _facteur_limitant(
        score_pertinence=score_pertinence,
        score_importance=score_importance,
        niveau_preuve=niveau_preuve,
        plafond_active=plafond_active,
    )
    robustesse = _robustesse_score(
        score_global=score_global,
        score_pertinence=score_pertinence,
        niveau_preuve=niveau_preuve,
        plafond_active=plafond_active,
        configuration=configuration,
    )
    facteurs = _facteurs_limitants(
        score_pertinence=score_pertinence,
        score_importance=score_importance,
        niveau_preuve=niveau_preuve,
        plafond_active=plafond_active,
    )
    qualite_entree = _qualite_entree(
        pertinence=pertinence,
        preuve=preuve,
        importance=importance,
    )
    indice_stabilite, marge_plafond, ecart_composantes = (
        _indice_stabilite(
            score_global=score_global,
            score_brut=score_brut,
            plafond=plafond,
            composantes=composantes,
            niveau_preuve=niveau_preuve,
        )
    )
    stabilite = _niveau_stabilite(
        indice_stabilite,
        configuration,
    )
    confiance = _score_confiance(
        qualite_entree=qualite_entree,
        indice_stabilite=indice_stabilite,
        robustesse=robustesse,
        plafond_active=plafond_active,
    )
    decision_fragile = (
        indice_stabilite < configuration.seuil_decision_fragile
        or plafond_active
    )
    controles = _controles_coherence(
        score_pertinence=score_pertinence,
        score_importance=score_importance,
        niveau_preuve=niveau_preuve,
        score_brut=score_brut,
        score_global=score_global,
        plafond=plafond,
        plafond_active=plafond_active,
        qualite_entree=qualite_entree,
    )
    indice_coherence = _indice_coherence(controles)
    niveau_coherence = _niveau_coherence(
        indice_coherence,
        configuration,
    )
    classe_decision = _classe_decision(
        score_global,
        configuration,
    )
    alertes = _construire_alertes(
        decision_fragile=decision_fragile,
        plafond_active=plafond_active,
        qualite_entree=qualite_entree,
        niveau_coherence=niveau_coherence,
        facteurs_limitants=facteurs,
    )

    configuration_dict = _configuration_dict(configuration)
    calcul_hash = _empreinte_json(
        {
            "engine_version": ENGINE_VERSION,
            "ruleset_version": RULESET_VERSION,
            "entrees": {
                "score_pertinence": score_pertinence,
                "score_importance": score_importance,
                "niveau_preuve": niveau_preuve,
            },
            "configuration": configuration_dict,
            "journal": journal,
            "score_brut": score_brut,
            "plafond": plafond,
            "score_global": score_global,
            "indice_stabilite": indice_stabilite,
            "score_confiance": confiance,
            "qualite_entree": qualite_entree,
            "decision_fragile": decision_fragile,
            "indice_coherence": indice_coherence,
            "niveau_coherence": niveau_coherence,
            "classe_decision": classe_decision,
            "controles": controles,
        }
    )
    resultat_hash = _empreinte_json(
        {
            "score_global": score_global,
            "score_brut": score_brut,
            "plafond": plafond,
            "robustesse": robustesse,
            "stabilite": stabilite,
            "confiance": confiance,
            "facteurs_limitants": facteurs,
            "indice_coherence": indice_coherence,
            "niveau_coherence": niveau_coherence,
            "classe_decision": classe_decision,
            "alertes": alertes,
        }
    )

    synthese = _construire_synthese(
        score_global=score_global,
        score_brut=score_brut,
        plafond=plafond,
        composante_dominante=dominante,
        facteur_limitant=facteur,
        robustesse=robustesse,
        stabilite=stabilite,
        score_confiance=confiance,
        niveau_coherence=niveau_coherence,
        classe_decision=classe_decision,
    )

    return {
        "score_global": score_global,
        "score_global_brut": score_brut,
        "score_avant_plafond": score_brut,
        "score_normalise": score_global,
        "score_pertinence": score_pertinence,
        "score_importance": score_importance,
        "niveau_preuve": niveau_preuve,
        "plafond_applique": plafond,
        "plafond_active": plafond_active,
        "composantes_score": [
            asdict(composante)
            for composante in composantes
        ],
        "composante_dominante": dominante,
        "facteur_limitant": facteur,
        "robustesse_score": robustesse,
        "stabilite_score": stabilite,
        "indice_stabilite": indice_stabilite,
        "score_confiance": confiance,
        "qualite_entree": qualite_entree,
        "decision_fragile": decision_fragile,
        "marge_plafond": marge_plafond,
        "ecart_composantes": ecart_composantes,
        "facteurs_limitants": facteurs,
        "indice_coherence": indice_coherence,
        "niveau_coherence": niveau_coherence,
        "classe_decision": classe_decision,
        "alertes": alertes,
        "controles": controles,
        "synthese": synthese,
        "audit": {
            "engine_version": ENGINE_VERSION,
            "ruleset_version": RULESET_VERSION,
            "configuration_hash": _configuration_hash(configuration),
            "calcul_hash": calcul_hash,
            "resultat_hash": resultat_hash,
            "nombre_composantes": len(composantes),
            "nombre_controles": len(controles),
            "controles_conformes": sum(
                1 for controle in controles if controle["conforme"]
            ),
            "controles_non_conformes": sum(
                1 for controle in controles if not controle["conforme"]
            ),
            "score_avant_plafond": score_brut,
            "plafond_applique": plafond,
            "plafond_active": plafond_active,
            "composante_dominante": dominante,
            "facteur_limitant": facteur,
            "facteurs_limitants": facteurs,
            "controles": controles,
            "journal_calcul": journal,
        },
        "configuration": configuration_dict,
    }


# ---------------------------------------------------------------------------
# Adaptation officielle au Pipeline V6
# ---------------------------------------------------------------------------


def obtenir_score_global(resultat: Mapping[str, Any]) -> int:
    """Retourne le score global borné entre 0 et 100."""
    return _borner(_entier(resultat.get("score_global")), 0, 100)


def obtenir_classe_decision(resultat: Mapping[str, Any]) -> ClasseDecisionScore:
    """Retourne la classe de décision calculée par le moteur."""
    valeur = resultat.get("classe_decision", "rejet")
    if valeur in {
        "rejet",
        "surveillance",
        "prioritaire",
        "hautement_prioritaire",
    }:
        return valeur  # type: ignore[return-value]
    return "rejet"


def obtenir_confiance_score(resultat: Mapping[str, Any]) -> int:
    """Retourne la confiance du calcul, bornée entre 0 et 100."""
    return _borner(_entier(resultat.get("score_confiance")), 0, 100)


def score_est_prioritaire(resultat: Mapping[str, Any]) -> bool:
    """Indique si le score appartient à une classe prioritaire."""
    return obtenir_classe_decision(resultat) in {
        "prioritaire",
        "hautement_prioritaire",
    }


def score_est_hautement_prioritaire(resultat: Mapping[str, Any]) -> bool:
    """Indique si le score appartient à la classe la plus élevée."""
    return obtenir_classe_decision(resultat) == "hautement_prioritaire"


def score_est_fragile(resultat: Mapping[str, Any]) -> bool:
    """Indique si le moteur considère la décision comme fragile."""
    return bool(resultat.get("decision_fragile", False))


def statistiques_score(resultat: Mapping[str, Any]) -> dict[str, Any]:
    """Construit un résumé stable destiné au diagnostic et à l'audit."""
    alertes = resultat.get("alertes", ())
    if isinstance(alertes, (str, bytes)) or not isinstance(alertes, list):
        alertes = []
    return {
        "score_global": obtenir_score_global(resultat),
        "classe_decision": obtenir_classe_decision(resultat),
        "score_confiance": obtenir_confiance_score(resultat),
        "robustesse": str(resultat.get("robustesse_score", "nulle")),
        "stabilite": str(resultat.get("stabilite_score", "instable")),
        "coherence": str(resultat.get("niveau_coherence", "incoherente")),
        "facteur_limitant": str(resultat.get("facteur_limitant", "aucun")),
        "plafond_active": bool(resultat.get("plafond_active", False)),
        "decision_fragile": score_est_fragile(resultat),
        "nombre_alertes": len(alertes),
        "prioritaire": score_est_prioritaire(resultat),
    }


def _resultat_extension(
    etat: "EtatClassification",
    nom: str,
) -> Mapping[str, Any] | None:
    """Lit un résultat amont sans imposer une implémentation du contexte."""
    extensions = getattr(etat, "extensions", None)
    if isinstance(extensions, Mapping):
        valeur = extensions.get(nom)
        if isinstance(valeur, Mapping):
            return valeur

    contexte = getattr(etat, "contexte", None)
    valeur = getattr(contexte, nom, None)
    return valeur if isinstance(valeur, Mapping) else None


def executer(etat: "EtatClassification") -> None:
    """Exécute l'agrégation du score sur l'état partagé du Pipeline V6.

    Le point d'entrée ne crée aucune règle métier. Il consomme les résultats
    déjà produits par pertinence, preuve et, lorsqu'il existe, importance.
    L'absence temporaire du module importance reste représentée par ``None``
    et conserve donc le comportement natif de :func:`calculer_score_global`.
    """
    contexte = getattr(etat, "contexte", None)
    if contexte is None:
        raise TypeError("etat doit exposer un attribut contexte.")

    pertinence = _resultat_extension(etat, "pertinence")
    if pertinence is None:
        raise RuntimeError(
            "Le résultat de pertinence est requis avant l'étape score."
        )

    preuve = _resultat_extension(etat, "preuve")

    extensions = getattr(etat, "extensions", None)
    importance: Mapping[str, Any] | int | None = None
    if isinstance(extensions, Mapping):
        valeur_importance = extensions.get("importance")
        if isinstance(valeur_importance, (Mapping, int)) and not isinstance(
            valeur_importance, bool
        ):
            importance = valeur_importance
    if importance is None:
        valeur_importance = getattr(contexte, "importance", None)
        if isinstance(valeur_importance, (Mapping, int)) and not isinstance(
            valeur_importance, bool
        ):
            importance = valeur_importance

    resultat = calculer_score_global(
        pertinence=pertinence,
        preuve=preuve,
        importance=importance,
    )

    definir_resultat = getattr(contexte, "definir_resultat", None)
    if callable(definir_resultat):
        definir_resultat("score", resultat)
    else:
        setattr(contexte, "score", dict(resultat))

    extensions_mutables = getattr(etat, "extensions", None)
    if isinstance(extensions_mutables, dict):
        extensions_mutables["score"] = dict(resultat)
        versions = extensions_mutables.setdefault("versions_modules", {})
        if isinstance(versions, dict):
            versions["score"] = VERSION_SCORE

    audit = getattr(etat, "audit", None)
    enregistrer = getattr(audit, "enregistrer", None)
    if callable(enregistrer):
        donnees = statistiques_score(resultat)
        donnees["importance_disponible"] = importance is not None
        donnees["preuve_disponible"] = preuve is not None
        enregistrer(
            "score_calcule",
            etape="score",
            donnees=donnees,
        )


executer_score = executer


__all__ = [
    "VERSION_SCORE",
    "executer",
    "executer_score",
    "obtenir_score_global",
    "obtenir_classe_decision",
    "obtenir_confiance_score",
    "score_est_prioritaire",
    "score_est_hautement_prioritaire",
    "score_est_fragile",
    "statistiques_score",
    "AuditScore",
    "ClasseDecisionScore",
    "ControleScore",
    "BONUS_PREUVE",
    "CONFIGURATION_PAR_DEFAUT",
    "ComposanteDominante",
    "ComposanteScore",
    "ConfigurationScore",
    "ENGINE_VERSION",
    "FacteurLimitant",
    "NiveauCoherenceScore",
    "NiveauRobustesseScore",
    "NiveauStabiliteScore",
    "QualiteEntreeScore",
    "RULESET_VERSION",
    "ResultatScore",
    "TraceComposanteScore",
    "calculer_score_global",
]