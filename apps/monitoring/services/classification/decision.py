"""
Décision finale du moteur déterministe de veille sanitaire.

Ce module transforme un score agrégé en décision explicite, stable et
traçable. La décision numérique initiale peut ensuite être ajustée par des
règles de sûreté liées à la qualité des entrées, à la pertinence et au niveau
de confiance.

Les seuils, la politique d'ajustement et la trace d'exécution sont séparés
afin de faciliter les tests, l'audit et l'évolution des règles métier.
"""

from __future__ import annotations

import math
import unicodedata
from dataclasses import asdict, dataclass, fields
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Mapping, TypedDict


VERSION_DECISION = "6.0.0"

if TYPE_CHECKING:
    try:
        from .pipeline_v6 import EtatClassification
    except ImportError:  # pragma: no cover - import direct hors package
        from pipeline_v6 import EtatClassification


DecisionFinale = Literal[
    "rejet",
    "a_revoir",
    "retenu",
    "prioritaire",
]

NiveauPertinence = Literal[
    "",
    "rejet",
    "a_revoir",
    "retenu",
    "prioritaire",
]

QualiteEntree = Literal[
    "valide",
    "absente",
    "invalide",
    "bornee",
]

CodeRegle = Literal[
    "score_global",
    "score_absent",
    "score_invalide",
    "score_borne",
    "confiance_absente",
    "confiance_insuffisante",
    "confiance_bornee",
    "pertinence_inconnue",
    "pertinence_rejet",
    "pertinence_a_revoir",
    "pertinence_prioritaire",
]

ScoreDecision = Mapping[str, Any] | int | float
PertinenceDecision = Mapping[str, Any] | None


class TraceRegle(TypedDict):
    """Trace d'une règle évaluée ou appliquée."""

    code: CodeRegle
    decision_avant: DecisionFinale
    decision_apres: DecisionFinale
    modifie_decision: bool
    motif: str


class ResultatDecision(TypedDict):
    """Structure détaillée retournée par :func:`decider`."""

    decision: DecisionFinale
    decision_initiale: DecisionFinale
    decision_libelle: str
    decision_modifiee: bool
    retenu: bool
    prioritaire: bool
    revision_humaine: bool

    score_global: int
    score_brut: str
    score_present: bool
    score_valide: bool
    score_borne: bool
    qualite_score: QualiteEntree

    niveau_pertinence: NiveauPertinence
    niveau_pertinence_brut: str
    pertinence_reconnue: bool

    confiance: int
    confiance_brute: str
    confiance_presente: bool
    confiance_valide: bool
    confiance_bornee: bool
    qualite_confiance: QualiteEntree

    regles_appliquees: list[CodeRegle]
    motifs: list[str]
    alertes_qualite: list[str]
    trace: list[TraceRegle]

    seuils_decision: dict[str, int]
    politique_decision: dict[str, bool]


@dataclass(frozen=True, slots=True)
class SeuilsDecision:
    """Seuils numériques utilisés pour établir la décision initiale."""

    SCORE_MINIMUM: ClassVar[int] = 0
    SCORE_MAXIMUM: ClassVar[int] = 100

    a_revoir: int = 20
    retenu: int = 50
    prioritaire: int = 75
    confiance_minimale: int = 45

    def __post_init__(self) -> None:
        """Valide la cohérence de tous les seuils."""
        valeurs = {
            "a_revoir": self.a_revoir,
            "retenu": self.retenu,
            "prioritaire": self.prioritaire,
            "confiance_minimale": self.confiance_minimale,
        }

        for nom, valeur in valeurs.items():
            if isinstance(valeur, bool) or not isinstance(valeur, int):
                raise TypeError(f"{nom} doit être un nombre entier.")

        if not (
            self.SCORE_MINIMUM
            <= self.a_revoir
            < self.retenu
            < self.prioritaire
            <= self.SCORE_MAXIMUM
        ):
            raise ValueError(
                "Les seuils de décision doivent être strictement croissants "
                "entre 0 et 100."
            )

        if not (
            self.SCORE_MINIMUM
            <= self.confiance_minimale
            <= self.SCORE_MAXIMUM
        ):
            raise ValueError(
                "confiance_minimale doit être comprise entre 0 et 100."
            )

    def classer(self, score_global: int) -> DecisionFinale:
        """Classe un score déjà normalisé selon les seuils courants."""
        if not (
            self.SCORE_MINIMUM
            <= score_global
            <= self.SCORE_MAXIMUM
        ):
            raise ValueError("score_global doit être compris entre 0 et 100.")

        if score_global < self.a_revoir:
            return "rejet"
        if score_global < self.retenu:
            return "a_revoir"
        if score_global < self.prioritaire:
            return "retenu"
        return "prioritaire"


@dataclass(frozen=True, slots=True)
class PolitiqueDecision:
    """Active ou désactive les ajustements du verdict numérique."""

    reviser_si_score_absent: bool = True
    reviser_si_score_invalide: bool = True
    reviser_si_score_borne: bool = False
    retrograder_si_confiance_faible: bool = True
    reviser_si_confiance_absente: bool = False
    imposer_rejet_pertinence: bool = True
    imposer_revision_pertinence: bool = True
    autoriser_promotion_prioritaire: bool = False
    tracer_pertinence_inconnue: bool = True

    def __post_init__(self) -> None:
        """Vérifie que les options sont strictement booléennes."""
        for champ in fields(self):
            valeur = getattr(self, champ.name)
            if not isinstance(valeur, bool):
                raise TypeError(f"{champ.name} doit être un booléen.")


@dataclass(frozen=True, slots=True)
class _ValeurNormalisee:
    """Valeur numérique normalisée accompagnée de ses métadonnées."""

    valeur: int
    brute: str
    presente: bool
    valide: bool
    bornee: bool

    @property
    def qualite(self) -> QualiteEntree:
        """Retourne un état synthétique de qualité."""
        if not self.presente:
            return "absente"
        if not self.valide:
            return "invalide"
        if self.bornee:
            return "bornee"
        return "valide"


@dataclass(frozen=True, slots=True)
class _PertinenceNormalisee:
    """Données de pertinence normalisées pour l'évaluation."""

    niveau: NiveauPertinence
    niveau_brut: str
    reconnue: bool
    confiance: _ValeurNormalisee


SEUILS_PAR_DEFAUT = SeuilsDecision()
POLITIQUE_PAR_DEFAUT = PolitiqueDecision()


_LIBELLES_DECISION: dict[DecisionFinale, str] = {
    "rejet": "Rejeté",
    "a_revoir": "À revoir",
    "retenu": "Retenu",
    "prioritaire": "Prioritaire",
}

_ALIAS_PERTINENCE: dict[str, NiveauPertinence] = {
    "": "",
    "rejet": "rejet",
    "rejete": "rejet",
    "a_revoir": "a_revoir",
    "a revoir": "a_revoir",
    "revision": "a_revoir",
    "retenu": "retenu",
    "pertinent": "retenu",
    "prioritaire": "prioritaire",
    "priorite": "prioritaire",
}

_ABSENT = object()


def _representation_sure(valeur: Any) -> str:
    """Produit une représentation courte et robuste pour l'audit."""
    if valeur is _ABSENT:
        return ""

    try:
        representation = repr(valeur)
    except Exception:
        return f"<{type(valeur).__name__}>"

    return representation[:200]


def _normaliser_chaine(valeur: Any) -> str:
    """Normalise une chaîne pour les comparaisons métier."""
    texte = str(valeur or "").strip().casefold()
    texte = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texte)
        if not unicodedata.combining(caractere)
    )
    return " ".join(texte.split())


def _normaliser_nombre(
    valeur: Any = _ABSENT,
    *,
    minimum: int = 0,
    maximum: int = 100,
    valeur_par_defaut: int = 0,
) -> _ValeurNormalisee:
    """
    Convertit une valeur en entier borné avec ses métadonnées.

    Une valeur booléenne, non numérique, NaN ou infinie est considérée comme
    invalide. Une valeur hors limites reste valide mais est signalée comme
    bornée.
    """
    brute = _representation_sure(valeur)

    if valeur is _ABSENT or valeur is None:
        return _ValeurNormalisee(
            valeur=valeur_par_defaut,
            brute=brute,
            presente=False,
            valide=False,
            bornee=False,
        )

    if isinstance(valeur, bool):
        return _ValeurNormalisee(
            valeur=valeur_par_defaut,
            brute=brute,
            presente=True,
            valide=False,
            bornee=False,
        )

    try:
        nombre = float(valeur)
    except (TypeError, ValueError, OverflowError):
        return _ValeurNormalisee(
            valeur=valeur_par_defaut,
            brute=brute,
            presente=True,
            valide=False,
            bornee=False,
        )

    if not math.isfinite(nombre):
        return _ValeurNormalisee(
            valeur=valeur_par_defaut,
            brute=brute,
            presente=True,
            valide=False,
            bornee=False,
        )

    entier_brut = int(nombre)
    entier_borne = min(max(entier_brut, minimum), maximum)

    return _ValeurNormalisee(
        valeur=entier_borne,
        brute=brute,
        presente=True,
        valide=True,
        bornee=entier_borne != entier_brut,
    )


def _extraire_score_global(score: ScoreDecision) -> _ValeurNormalisee:
    """Extrait et normalise le score global."""
    if isinstance(score, Mapping):
        valeur = score.get("score_global", _ABSENT)
    elif isinstance(score, (int, float)) and not isinstance(score, bool):
        valeur = score
    else:
        raise TypeError(
            "score doit être un nombre ou un objet compatible avec Mapping."
        )

    return _normaliser_nombre(valeur)


def _extraire_pertinence(
    pertinence: PertinenceDecision,
) -> _PertinenceNormalisee:
    """Extrait et normalise le verdict thématique et sa confiance."""
    if pertinence is None:
        return _PertinenceNormalisee(
            niveau="",
            niveau_brut="",
            reconnue=True,
            confiance=_normaliser_nombre(),
        )

    if not isinstance(pertinence, Mapping):
        raise TypeError(
            "pertinence doit être un objet compatible avec Mapping ou None."
        )

    niveau_brut = _normaliser_chaine(
        pertinence.get("niveau_pertinence", "")
    )
    niveau = _ALIAS_PERTINENCE.get(niveau_brut, "")
    reconnue = niveau_brut in _ALIAS_PERTINENCE

    return _PertinenceNormalisee(
        niveau=niveau,
        niveau_brut=niveau_brut,
        reconnue=reconnue,
        confiance=_normaliser_nombre(
            pertinence.get("confiance", _ABSENT)
        ),
    )


def _tracer_regle(
    trace: list[TraceRegle],
    *,
    code: CodeRegle,
    decision_avant: DecisionFinale,
    decision_apres: DecisionFinale,
    motif: str,
) -> DecisionFinale:
    """Ajoute une entrée de trace et retourne la décision résultante."""
    trace.append(
        {
            "code": code,
            "decision_avant": decision_avant,
            "decision_apres": decision_apres,
            "modifie_decision": decision_avant != decision_apres,
            "motif": motif,
        }
    )
    return decision_apres


def decider(
    score: ScoreDecision,
    *,
    pertinence: PertinenceDecision = None,
    seuils: SeuilsDecision = SEUILS_PAR_DEFAUT,
    politique: PolitiqueDecision = POLITIQUE_PAR_DEFAUT,
) -> ResultatDecision:
    """
    Transforme un score en décision stable, explicable et auditable.

    Les défauts de qualité du score sont traités avant les règles de confiance
    et de pertinence. Par défaut, un score absent ou invalide conduit à une
    revue humaine plutôt qu'à un rejet silencieux.
    """
    if not isinstance(seuils, SeuilsDecision):
        raise TypeError("seuils doit être une instance de SeuilsDecision.")
    if not isinstance(politique, PolitiqueDecision):
        raise TypeError(
            "politique doit être une instance de PolitiqueDecision."
        )

    score_normalise = _extraire_score_global(score)
    pertinence_normalisee = _extraire_pertinence(pertinence)

    decision_initiale = seuils.classer(score_normalise.valeur)
    decision = decision_initiale
    trace: list[TraceRegle] = []
    alertes_qualite: list[str] = []

    decision = _tracer_regle(
        trace,
        code="score_global",
        decision_avant=decision,
        decision_apres=decision,
        motif=(
            f"Le score global de {score_normalise.valeur}/100 conduit "
            f"initialement à « {_LIBELLES_DECISION[decision_initiale]} »."
        ),
    )

    if not score_normalise.presente:
        alertes_qualite.append("Le score global est absent.")
        decision_apres = (
            "a_revoir"
            if politique.reviser_si_score_absent
            else decision
        )
        decision = _tracer_regle(
            trace,
            code="score_absent",
            decision_avant=decision,
            decision_apres=decision_apres,
            motif="Aucun score global exploitable n'a été fourni.",
        )
    elif not score_normalise.valide:
        alertes_qualite.append("Le score global est invalide.")
        decision_apres = (
            "a_revoir"
            if politique.reviser_si_score_invalide
            else decision
        )
        decision = _tracer_regle(
            trace,
            code="score_invalide",
            decision_avant=decision,
            decision_apres=decision_apres,
            motif=(
                "Le score global fourni est invalide et a été remplacé "
                "par la valeur par défaut."
            ),
        )
    elif score_normalise.bornee:
        alertes_qualite.append(
            "Le score global a été ramené dans l'intervalle 0–100."
        )
        decision_apres = (
            "a_revoir"
            if politique.reviser_si_score_borne
            else decision
        )
        decision = _tracer_regle(
            trace,
            code="score_borne",
            decision_avant=decision,
            decision_apres=decision_apres,
            motif=(
                f"Le score brut {score_normalise.brute} a été borné à "
                f"{score_normalise.valeur}/100."
            ),
        )

    confiance = pertinence_normalisee.confiance

    if confiance.bornee:
        alertes_qualite.append(
            "La confiance a été ramenée dans l'intervalle 0–100."
        )
        decision = _tracer_regle(
            trace,
            code="confiance_bornee",
            decision_avant=decision,
            decision_apres=decision,
            motif=(
                f"La confiance brute {confiance.brute} a été bornée à "
                f"{confiance.valeur}/100."
            ),
        )

    if (
        politique.reviser_si_confiance_absente
        and decision in {"retenu", "prioritaire"}
        and not confiance.presente
    ):
        decision = _tracer_regle(
            trace,
            code="confiance_absente",
            decision_avant=decision,
            decision_apres="a_revoir",
            motif=(
                "Aucune confiance n'a été fournie alors que la politique "
                "exige une validation humaine dans ce cas."
            ),
        )
    elif (
        politique.retrograder_si_confiance_faible
        and decision in {"retenu", "prioritaire"}
        and confiance.presente
        and (
            not confiance.valide
            or confiance.valeur < seuils.confiance_minimale
        )
    ):
        if not confiance.valide:
            alertes_qualite.append("La confiance fournie est invalide.")
            motif = "La confiance fournie est invalide."
        else:
            motif = (
                f"La confiance de {confiance.valeur}/100 est inférieure "
                f"au seuil minimal de {seuils.confiance_minimale}/100."
            )

        decision = _tracer_regle(
            trace,
            code="confiance_insuffisante",
            decision_avant=decision,
            decision_apres="a_revoir",
            motif=motif,
        )

    niveau = pertinence_normalisee.niveau

    if (
        politique.tracer_pertinence_inconnue
        and not pertinence_normalisee.reconnue
    ):
        alertes_qualite.append(
            "Le niveau de pertinence fourni n'est pas reconnu."
        )
        decision = _tracer_regle(
            trace,
            code="pertinence_inconnue",
            decision_avant=decision,
            decision_apres=decision,
            motif=(
                "Le niveau de pertinence "
                f"{pertinence_normalisee.niveau_brut!r} n'est pas reconnu."
            ),
        )

    if politique.imposer_rejet_pertinence and niveau == "rejet":
        decision = _tracer_regle(
            trace,
            code="pertinence_rejet",
            decision_avant=decision,
            decision_apres="rejet",
            motif="Le verdict thématique impose le rejet de l'article.",
        )
    elif (
        politique.imposer_revision_pertinence
        and niveau == "a_revoir"
        and decision in {"retenu", "prioritaire"}
    ):
        decision = _tracer_regle(
            trace,
            code="pertinence_a_revoir",
            decision_avant=decision,
            decision_apres="a_revoir",
            motif="Le verdict thématique impose une revue humaine.",
        )
    elif (
        politique.autoriser_promotion_prioritaire
        and niveau == "prioritaire"
        and decision == "retenu"
        and confiance.presente
        and confiance.valide
        and confiance.valeur >= seuils.confiance_minimale
    ):
        decision = _tracer_regle(
            trace,
            code="pertinence_prioritaire",
            decision_avant=decision,
            decision_apres="prioritaire",
            motif=(
                "Le verdict thématique prioritaire est confirmé par une "
                "confiance suffisante."
            ),
        )

    return {
        "decision": decision,
        "decision_initiale": decision_initiale,
        "decision_libelle": _LIBELLES_DECISION[decision],
        "decision_modifiee": decision != decision_initiale,
        "retenu": decision in {"retenu", "prioritaire"},
        "prioritaire": decision == "prioritaire",
        "revision_humaine": decision == "a_revoir",
        "score_global": score_normalise.valeur,
        "score_brut": score_normalise.brute,
        "score_present": score_normalise.presente,
        "score_valide": score_normalise.valide,
        "score_borne": score_normalise.bornee,
        "qualite_score": score_normalise.qualite,
        "niveau_pertinence": niveau,
        "niveau_pertinence_brut": pertinence_normalisee.niveau_brut,
        "pertinence_reconnue": pertinence_normalisee.reconnue,
        "confiance": confiance.valeur,
        "confiance_brute": confiance.brute,
        "confiance_presente": confiance.presente,
        "confiance_valide": confiance.valide,
        "confiance_bornee": confiance.bornee,
        "qualite_confiance": confiance.qualite,
        "regles_appliquees": [entree["code"] for entree in trace],
        "motifs": [entree["motif"] for entree in trace],
        "alertes_qualite": alertes_qualite,
        "trace": trace,
        "seuils_decision": asdict(seuils),
        "politique_decision": asdict(politique),
    }



def obtenir_decision(resultat: Mapping[str, Any]) -> DecisionFinale:
    """Retourne la décision finale normalisée."""
    valeur = resultat.get("decision", "a_revoir")
    if valeur in {"rejet", "a_revoir", "retenu", "prioritaire"}:
        return valeur  # type: ignore[return-value]
    return "a_revoir"


def obtenir_libelle_decision(resultat: Mapping[str, Any]) -> str:
    """Retourne le libellé public de la décision."""
    valeur = resultat.get("decision_libelle")
    if isinstance(valeur, str) and valeur.strip():
        return valeur.strip()
    return _LIBELLES_DECISION[obtenir_decision(resultat)]


def est_prioritaire(resultat: Mapping[str, Any]) -> bool:
    """Indique si la décision finale est prioritaire."""
    return obtenir_decision(resultat) == "prioritaire"


def est_retenu(resultat: Mapping[str, Any]) -> bool:
    """Indique si l'article est retenu, prioritaire inclus."""
    return obtenir_decision(resultat) in {"retenu", "prioritaire"}


def necessite_revision(resultat: Mapping[str, Any]) -> bool:
    """Indique si une revue humaine est nécessaire."""
    return obtenir_decision(resultat) == "a_revoir"


def est_rejete(resultat: Mapping[str, Any]) -> bool:
    """Indique si la décision finale est un rejet."""
    return obtenir_decision(resultat) == "rejet"


def statistiques_decision(resultat: Mapping[str, Any]) -> dict[str, Any]:
    """Construit un résumé stable pour le diagnostic et l'audit V6."""
    regles = resultat.get("regles_appliquees", ())
    alertes = resultat.get("alertes_qualite", ())
    trace = resultat.get("trace", ())
    return {
        "decision": obtenir_decision(resultat),
        "decision_libelle": obtenir_libelle_decision(resultat),
        "decision_initiale": str(resultat.get("decision_initiale", "")),
        "decision_modifiee": bool(resultat.get("decision_modifiee", False)),
        "retenu": est_retenu(resultat),
        "prioritaire": est_prioritaire(resultat),
        "revision_humaine": necessite_revision(resultat),
        "score_global": int(resultat.get("score_global", 0) or 0),
        "niveau_pertinence": str(resultat.get("niveau_pertinence", "")),
        "confiance": int(resultat.get("confiance", 0) or 0),
        "qualite_score": str(resultat.get("qualite_score", "invalide")),
        "qualite_confiance": str(
            resultat.get("qualite_confiance", "invalide")
        ),
        "nombre_regles": len(regles) if isinstance(regles, list) else 0,
        "nombre_alertes": len(alertes) if isinstance(alertes, list) else 0,
        "nombre_traces": len(trace) if isinstance(trace, list) else 0,
    }


def _resultat_extension(
    etat: "EtatClassification",
    nom: str,
) -> Mapping[str, Any] | None:
    """Lit un résultat amont depuis extensions puis depuis le contexte."""
    extensions = getattr(etat, "extensions", None)
    if isinstance(extensions, Mapping):
        valeur = extensions.get(nom)
        if isinstance(valeur, Mapping):
            return valeur

    contexte = getattr(etat, "contexte", None)
    valeur = getattr(contexte, nom, None)
    return valeur if isinstance(valeur, Mapping) else None


def executer(etat: "EtatClassification") -> None:
    """Exécute la décision finale sur l'état partagé du Pipeline V6.

    Cette interface ne modifie aucune règle métier. Elle consomme le score et
    la pertinence déjà calculés, délègue intégralement le verdict à
    :func:`decider`, puis publie le résultat et sa traçabilité dans l'état.
    """
    contexte = getattr(etat, "contexte", None)
    if contexte is None:
        raise TypeError("etat doit exposer un attribut contexte.")

    score = _resultat_extension(etat, "score")
    if score is None:
        raise RuntimeError(
            "Le résultat du score est requis avant l'étape décision."
        )

    pertinence = _resultat_extension(etat, "pertinence")
    resultat = decider(score, pertinence=pertinence)

    definir_resultat = getattr(contexte, "definir_resultat", None)
    if callable(definir_resultat):
        definir_resultat("decision", resultat)
    else:
        setattr(contexte, "decision", dict(resultat))

    extensions = getattr(etat, "extensions", None)
    if isinstance(extensions, dict):
        extensions["decision"] = dict(resultat)
        versions = extensions.setdefault("versions_modules", {})
        if isinstance(versions, dict):
            versions["decision"] = VERSION_DECISION

    audit = getattr(etat, "audit", None)
    enregistrer = getattr(audit, "enregistrer", None)
    if callable(enregistrer):
        donnees = statistiques_decision(resultat)
        donnees["pertinence_disponible"] = pertinence is not None
        enregistrer(
            "decision_calculee",
            etape="decision",
            donnees=donnees,
        )


executer_decision = executer


__all__ = [
    "VERSION_DECISION",
    "executer",
    "executer_decision",
    "obtenir_decision",
    "obtenir_libelle_decision",
    "est_prioritaire",
    "est_retenu",
    "necessite_revision",
    "est_rejete",
    "statistiques_decision",
    "CodeRegle",
    "DecisionFinale",
    "NiveauPertinence",
    "POLITIQUE_PAR_DEFAUT",
    "PertinenceDecision",
    "PolitiqueDecision",
    "QualiteEntree",
    "ResultatDecision",
    "SEUILS_PAR_DEFAUT",
    "ScoreDecision",
    "SeuilsDecision",
    "TraceRegle",
    "decider",
]