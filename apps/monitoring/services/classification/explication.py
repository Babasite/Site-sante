"""
Construction d'explications lisibles, stables et auditables.

Ce module agrège les résultats de pertinence, de preuve, de score et de
décision afin de produire une synthèse destinée à l'affichage, ainsi que des
raisons positives, négatives et des points de vigilance structurés.

Il ne recalcule aucune décision métier : il met en forme les données déjà
produites par les étapes précédentes du moteur.
"""

from __future__ import annotations

import math
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, Literal, TypedDict


VERSION_EXPLICATION = "6.0.0"

if TYPE_CHECKING:
    try:
        from .pipeline_v6 import EtatClassification
    except ImportError:  # pragma: no cover - import direct hors package
        from pipeline_v6 import EtatClassification


TypeRaison = Literal[
    "positive",
    "negative",
    "vigilance",
]

NiveauImportance = Literal[
    "faible",
    "moyenne",
    "forte",
]

SourceExplication = Literal[
    "pertinence",
    "preuve",
    "score",
    "decision",
    "qualite",
]


class ElementExplication(TypedDict):
    """Élément structuré utilisé pour construire l'explication."""

    type: TypeRaison
    texte: str
    source: SourceExplication
    importance: NiveauImportance


class ResultatExplication(TypedDict):
    """Structure retournée par :func:`construire_explication`."""

    synthese: str
    explications: list[str]
    elements: list[ElementExplication]
    raisons_positives: list[str]
    raisons_negatives: list[str]
    points_vigilance: list[str]
    decision: str
    decision_libelle: str
    score_global: int
    confiance: int
    preuve_dominante: str
    niveau_preuve: int
    nombre_elements: int
    nombre_positifs: int
    nombre_negatifs: int
    nombre_vigilances: int
    contradiction_detectee: bool
    tronque: bool
    configuration: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ConfigurationExplication:
    """Options de construction et de présentation des explications."""

    inclure_motifs_decision: bool = True
    inclure_alertes_qualite: bool = True
    inclure_trace_decision: bool = False
    inclure_resume_compteurs: bool = True
    max_elements: int | None = None
    max_longueur_raison: int = 500

    def __post_init__(self) -> None:
        """Valide la cohérence des options."""
        options_booleennes = {
            "inclure_motifs_decision": self.inclure_motifs_decision,
            "inclure_alertes_qualite": self.inclure_alertes_qualite,
            "inclure_trace_decision": self.inclure_trace_decision,
            "inclure_resume_compteurs": self.inclure_resume_compteurs,
        }
        for nom, valeur in options_booleennes.items():
            if not isinstance(valeur, bool):
                raise TypeError(f"{nom} doit être un booléen.")

        if self.max_elements is not None:
            if (
                isinstance(self.max_elements, bool)
                or not isinstance(self.max_elements, int)
            ):
                raise TypeError("max_elements doit être un entier ou None.")
            if self.max_elements <= 0:
                raise ValueError("max_elements doit être strictement positif.")

        if (
            isinstance(self.max_longueur_raison, bool)
            or not isinstance(self.max_longueur_raison, int)
        ):
            raise TypeError("max_longueur_raison doit être un entier.")
        if self.max_longueur_raison <= 0:
            raise ValueError(
                "max_longueur_raison doit être strictement positif."
            )


CONFIGURATION_PAR_DEFAUT = ConfigurationExplication()


_DECISION_LIBELLES: dict[str, str] = {
    "rejet": "Rejeté",
    "a_revoir": "À revoir",
    "retenu": "Retenu",
    "prioritaire": "Prioritaire",
}

_PREFIXES: dict[TypeRaison, str] = {
    "positive": "+",
    "negative": "-",
    "vigilance": "!",
}

_IMPORTANCE_PAR_TYPE: dict[TypeRaison, NiveauImportance] = {
    "positive": "moyenne",
    "negative": "moyenne",
    "vigilance": "forte",
}


def _normaliser_texte(
    valeur: Any,
    *,
    longueur_maximale: int | None = None,
) -> str:
    """Convertit une valeur en texte propre et éventuellement tronqué."""
    if valeur is None:
        return ""

    if isinstance(valeur, bytes):
        texte = valeur.decode("utf-8", errors="replace")
    else:
        texte = str(valeur)

    propre = " ".join(texte.split())

    if (
        longueur_maximale is not None
        and len(propre) > longueur_maximale
    ):
        return propre[: max(1, longueur_maximale - 1)].rstrip() + "…"

    return propre


def _cle_texte(texte: str) -> str:
    """Produit une clé insensible aux accents, à la casse et aux espaces."""
    sans_accents = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texte)
        if not unicodedata.combining(caractere)
    )
    return " ".join(sans_accents.casefold().split())


def _iterer_valeurs(valeurs: Any) -> Iterable[Any]:
    """Transforme une valeur isolée ou une collection en itérable sûr."""
    if valeurs is None:
        return ()

    if isinstance(valeurs, (str, bytes)):
        return (valeurs,)

    if isinstance(valeurs, Mapping):
        return (valeurs,)

    if isinstance(valeurs, Iterable):
        return valeurs

    return (valeurs,)


def _normaliser_entier(
    valeur: Any,
    *,
    minimum: int = 0,
    maximum: int = 100,
    valeur_par_defaut: int = 0,
) -> int:
    """Convertit une valeur en entier borné de façon sûre."""
    if valeur is None or isinstance(valeur, bool):
        return valeur_par_defaut

    try:
        nombre = float(valeur)
    except (TypeError, ValueError, OverflowError):
        return valeur_par_defaut

    if not math.isfinite(nombre):
        return valeur_par_defaut

    return min(max(int(nombre), minimum), maximum)


def _verifier_mapping(
    valeur: Mapping[str, Any] | None,
    *,
    nom: str,
) -> Mapping[str, Any]:
    """Valide un mapping facultatif et retourne un mapping exploitable."""
    if valeur is None:
        return {}

    if not isinstance(valeur, Mapping):
        raise TypeError(
            f"{nom} doit être un objet compatible avec Mapping ou None."
        )

    return valeur


def _ajouter_element(
    elements: list[ElementExplication],
    *,
    type_raison: TypeRaison,
    texte: Any,
    source: SourceExplication,
    importance: NiveauImportance | None = None,
    longueur_maximale: int,
) -> None:
    """
    Ajoute un élément structuré sans doublon global.

    Lorsqu'un même texte existe déjà avec un autre type, le doublon est
    conservé afin de rendre une éventuelle contradiction visible.
    """
    propre = _normaliser_texte(
        texte,
        longueur_maximale=longueur_maximale,
    )
    if not propre:
        return

    cle = _cle_texte(propre)
    if any(
        element["type"] == type_raison
        and _cle_texte(element["texte"]) == cle
        for element in elements
    ):
        return

    elements.append(
        {
            "type": type_raison,
            "texte": propre,
            "source": source,
            "importance": importance or _IMPORTANCE_PAR_TYPE[type_raison],
        }
    )


def _extraire_decision(
    decision: Mapping[str, Any],
) -> tuple[str, str]:
    """Extrait le code et le libellé de décision."""
    code = _normaliser_texte(decision.get("decision", "")).casefold()
    libelle = _normaliser_texte(decision.get("decision_libelle", ""))

    if not libelle:
        libelle = _DECISION_LIBELLES.get(code, "Non déterminée")

    return code, libelle


def _extraire_preuve(
    preuve: Mapping[str, Any],
) -> tuple[str, int, str]:
    """Extrait le nom, le niveau et la raison associés à la preuve."""
    nom = _normaliser_texte(
        preuve.get("preuve")
        or preuve.get("preuve_dominante")
        or "Non déterminée"
    )
    niveau = _normaliser_entier(preuve.get("niveau_preuve", 0))
    raison = _normaliser_texte(preuve.get("raison_preuve", ""))

    return nom, niveau, raison


def _importance_preuve(niveau_preuve: int) -> NiveauImportance:
    """Déduit une importance lisible à partir du niveau de preuve."""
    if niveau_preuve >= 4:
        return "forte"
    if niveau_preuve >= 2:
        return "moyenne"
    return "faible"


def _ajouter_trace_decision(
    elements: list[ElementExplication],
    trace: Any,
    *,
    longueur_maximale: int,
) -> None:
    """Ajoute les motifs issus d'une trace de décision structurée."""
    for entree in _iterer_valeurs(trace):
        if not isinstance(entree, Mapping):
            continue

        motif = entree.get("motif", "")
        modifie_decision = bool(entree.get("modifie_decision", False))
        _ajouter_element(
            elements,
            type_raison="vigilance",
            texte=motif,
            source="decision",
            importance="forte" if modifie_decision else "faible",
            longueur_maximale=longueur_maximale,
        )


def _detecter_contradiction(
    elements: list[ElementExplication],
) -> bool:
    """Détecte un même motif classé à la fois positif et négatif."""
    positives = {
        _cle_texte(element["texte"])
        for element in elements
        if element["type"] == "positive"
    }
    negatives = {
        _cle_texte(element["texte"])
        for element in elements
        if element["type"] == "negative"
    }
    return bool(positives & negatives)


def construire_explication(
    *,
    pertinence: Mapping[str, Any],
    preuve: Mapping[str, Any] | None = None,
    score: Mapping[str, Any] | None = None,
    decision: Mapping[str, Any] | None = None,
    configuration: ConfigurationExplication = CONFIGURATION_PAR_DEFAUT,
) -> ResultatExplication:
    """
    Produit une explication lisible, structurée et déterministe.

    Les raisons issues de la pertinence et de la preuve peuvent être
    complétées par les motifs, alertes de qualité et traces de décision.
    """
    if not isinstance(pertinence, Mapping):
        raise TypeError(
            "pertinence doit être un objet compatible avec Mapping."
        )
    if not isinstance(configuration, ConfigurationExplication):
        raise TypeError(
            "configuration doit être une instance de "
            "ConfigurationExplication."
        )

    preuve = _verifier_mapping(preuve, nom="preuve")
    score = _verifier_mapping(score, nom="score")
    decision = _verifier_mapping(decision, nom="decision")

    elements: list[ElementExplication] = []
    longueur_maximale = configuration.max_longueur_raison

    for raison in _iterer_valeurs(
        pertinence.get("raisons_positives", ())
    ):
        if isinstance(raison, Mapping):
            raise TypeError(
                "raisons_positives ne peut pas contenir de Mapping."
            )
        _ajouter_element(
            elements,
            type_raison="positive",
            texte=raison,
            source="pertinence",
            longueur_maximale=longueur_maximale,
        )

    for raison in _iterer_valeurs(
        pertinence.get("raisons_negatives", ())
    ):
        if isinstance(raison, Mapping):
            raise TypeError(
                "raisons_negatives ne peut pas contenir de Mapping."
            )
        _ajouter_element(
            elements,
            type_raison="negative",
            texte=raison,
            source="pertinence",
            longueur_maximale=longueur_maximale,
        )

    preuve_nom, niveau_preuve, raison_preuve = _extraire_preuve(preuve)
    if raison_preuve:
        _ajouter_element(
            elements,
            type_raison="positive" if niveau_preuve > 0 else "negative",
            texte=raison_preuve,
            source="preuve",
            importance=_importance_preuve(niveau_preuve),
            longueur_maximale=longueur_maximale,
        )

    if configuration.inclure_motifs_decision:
        for motif in _iterer_valeurs(decision.get("motifs", ())):
            if isinstance(motif, Mapping):
                continue
            _ajouter_element(
                elements,
                type_raison="vigilance",
                texte=motif,
                source="decision",
                longueur_maximale=longueur_maximale,
            )

    if configuration.inclure_alertes_qualite:
        for alerte in _iterer_valeurs(
            decision.get("alertes_qualite", ())
        ):
            if isinstance(alerte, Mapping):
                continue
            _ajouter_element(
                elements,
                type_raison="vigilance",
                texte=alerte,
                source="qualite",
                importance="forte",
                longueur_maximale=longueur_maximale,
            )

    if configuration.inclure_trace_decision:
        _ajouter_trace_decision(
            elements,
            decision.get("trace", ()),
            longueur_maximale=longueur_maximale,
        )

    contradiction_detectee = _detecter_contradiction(elements)

    if contradiction_detectee:
        _ajouter_element(
            elements,
            type_raison="vigilance",
            texte=(
                "Une même justification apparaît parmi les raisons "
                "positives et négatives."
            ),
            source="qualite",
            importance="forte",
            longueur_maximale=longueur_maximale,
        )

    tronque = False
    if (
        configuration.max_elements is not None
        and len(elements) > configuration.max_elements
    ):
        elements = elements[: configuration.max_elements]
        tronque = True

    positives = [
        element["texte"]
        for element in elements
        if element["type"] == "positive"
    ]
    negatives = [
        element["texte"]
        for element in elements
        if element["type"] == "negative"
    ]
    vigilances = [
        element["texte"]
        for element in elements
        if element["type"] == "vigilance"
    ]

    lignes = [
        f"{_PREFIXES[element['type']]} {element['texte']}"
        for element in elements
    ]

    decision_code, decision_libelle = _extraire_decision(decision)
    score_global = _normaliser_entier(
        score.get(
            "score_global",
            decision.get("score_global", 0),
        )
    )
    confiance = _normaliser_entier(
        pertinence.get(
            "confiance",
            decision.get("confiance", 0),
        )
    )

    synthese = (
        f"Décision : {decision_libelle}. "
        f"Score global : {score_global}/100. "
        f"Confiance des règles : {confiance}/100. "
        f"Preuve dominante : {preuve_nom} "
        f"({niveau_preuve}/5)."
    )

    if configuration.inclure_resume_compteurs:
        synthese += (
            f" Raisons : {len(positives)} positive(s), "
            f"{len(negatives)} négative(s), "
            f"{len(vigilances)} point(s) de vigilance."
        )

    if contradiction_detectee:
        synthese += " Une contradiction explicative a été détectée."

    if tronque:
        synthese += " La liste détaillée a été tronquée."

    return {
        "synthese": synthese,
        "explications": lignes,
        "elements": elements,
        "raisons_positives": positives,
        "raisons_negatives": negatives,
        "points_vigilance": vigilances,
        "decision": decision_code,
        "decision_libelle": decision_libelle,
        "score_global": score_global,
        "confiance": confiance,
        "preuve_dominante": preuve_nom,
        "niveau_preuve": niveau_preuve,
        "nombre_elements": len(elements),
        "nombre_positifs": len(positives),
        "nombre_negatifs": len(negatives),
        "nombre_vigilances": len(vigilances),
        "contradiction_detectee": contradiction_detectee,
        "tronque": tronque,
        "configuration": asdict(configuration),
    }



def obtenir_synthese(resultat: Mapping[str, Any]) -> str:
    """Retourne la synthèse publique de l'explication."""
    valeur = resultat.get("synthese", "")
    return valeur.strip() if isinstance(valeur, str) else ""


def obtenir_explications(resultat: Mapping[str, Any]) -> list[str]:
    """Retourne les lignes d'explication sous forme de liste sûre."""
    valeurs = resultat.get("explications", ())
    if not isinstance(valeurs, list):
        return []
    return [str(v) for v in valeurs if isinstance(v, str) and v.strip()]


def contient_contradiction(resultat: Mapping[str, Any]) -> bool:
    """Indique si une contradiction explicative a été détectée."""
    return bool(resultat.get("contradiction_detectee", False))


def contient_vigilance(resultat: Mapping[str, Any]) -> bool:
    """Indique si l'explication contient au moins un point de vigilance."""
    return int(resultat.get("nombre_vigilances", 0) or 0) > 0


def statistiques_explication(resultat: Mapping[str, Any]) -> dict[str, Any]:
    """Construit un résumé stable pour le diagnostic et l'audit V6."""
    return {
        "decision": str(resultat.get("decision", "")),
        "decision_libelle": str(resultat.get("decision_libelle", "")),
        "score_global": int(resultat.get("score_global", 0) or 0),
        "confiance": int(resultat.get("confiance", 0) or 0),
        "niveau_preuve": int(resultat.get("niveau_preuve", 0) or 0),
        "nombre_elements": int(resultat.get("nombre_elements", 0) or 0),
        "nombre_positifs": int(resultat.get("nombre_positifs", 0) or 0),
        "nombre_negatifs": int(resultat.get("nombre_negatifs", 0) or 0),
        "nombre_vigilances": int(resultat.get("nombre_vigilances", 0) or 0),
        "contradiction_detectee": contient_contradiction(resultat),
        "tronque": bool(resultat.get("tronque", False)),
    }


def _resultat_amont(
    etat: "EtatClassification",
    nom: str,
) -> Mapping[str, Any] | None:
    """Lit un résultat depuis extensions puis depuis le contexte partagé."""
    extensions = getattr(etat, "extensions", None)
    if isinstance(extensions, Mapping):
        valeur = extensions.get(nom)
        if isinstance(valeur, Mapping):
            return valeur

    contexte = getattr(etat, "contexte", None)
    valeur = getattr(contexte, nom, None)
    return valeur if isinstance(valeur, Mapping) else None


def executer(etat: "EtatClassification") -> None:
    """Construit et publie l'explication finale dans le Pipeline V6."""
    contexte = getattr(etat, "contexte", None)
    if contexte is None:
        raise TypeError("etat doit exposer un attribut contexte.")

    pertinence = _resultat_amont(etat, "pertinence")
    if pertinence is None:
        raise RuntimeError(
            "Le résultat de pertinence est requis avant l'étape explication."
        )

    preuve = _resultat_amont(etat, "preuve")
    score = _resultat_amont(etat, "score")
    decision = _resultat_amont(etat, "decision")

    resultat = construire_explication(
        pertinence=pertinence,
        preuve=preuve,
        score=score,
        decision=decision,
    )

    definir_resultat = getattr(contexte, "definir_resultat", None)
    if callable(definir_resultat):
        definir_resultat("explication", resultat)
    else:
        setattr(contexte, "explication", dict(resultat))

    extensions = getattr(etat, "extensions", None)
    if isinstance(extensions, dict):
        extensions["explication"] = dict(resultat)
        versions = extensions.setdefault("versions_modules", {})
        if isinstance(versions, dict):
            versions["explication"] = VERSION_EXPLICATION

    audit = getattr(etat, "audit", None)
    enregistrer = getattr(audit, "enregistrer", None)
    if callable(enregistrer):
        enregistrer(
            "explication_calculee",
            etape="explication",
            donnees=statistiques_explication(resultat),
        )


executer_explication = executer

__all__ = [
    "VERSION_EXPLICATION",
    "executer",
    "executer_explication",
    "obtenir_synthese",
    "obtenir_explications",
    "contient_contradiction",
    "contient_vigilance",
    "statistiques_explication",
    "CONFIGURATION_PAR_DEFAUT",
    "ConfigurationExplication",
    "ElementExplication",
    "NiveauImportance",
    "ResultatExplication",
    "SourceExplication",
    "TypeRaison",
    "construire_explication",
]