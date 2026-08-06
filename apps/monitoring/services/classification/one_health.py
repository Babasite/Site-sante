"""
Détection déterministe, explicable et configurable des dimensions One Health.

Ce module identifie les dimensions humaine, animale et environnementale à
partir d'un texte ou d'un article structuré. Il s'appuie exclusivement sur des
règles lexicales explicites afin de garantir des résultats reproductibles,
auditables et simples à tester.

Les règles sont validées et normalisées au chargement du module. L'analyse
publique expose les dimensions détectées, les dimensions absentes, les règles
déclenchées, les occurrences, le niveau de transversalité et une synthèse
directement exploitable par une interface ou un export.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, Final, Literal, TypedDict, cast

from .utils import construire_texte, detecter_regles

if TYPE_CHECKING:
    from .pipeline import EtatClassification


VERSION_ONE_HEALTH: Final[str] = "3.0.0"


DimensionOneHealth = Literal[
    "Humain",
    "Animal",
    "Environnement",
]

NiveauTransversalite = Literal[
    "aucune",
    "faible",
    "partielle",
    "complete",
]


class DetailDimension(TypedDict):
    """Détail de détection pour une dimension One Health."""

    detectee: bool
    nombre_occurrences: int
    mots_detectes: list[str]


class ResultatOneHealth(TypedDict):
    """Structure retournée par :func:`analyser_one_health`."""

    one_health: list[DimensionOneHealth]
    dimensions_absentes: list[DimensionOneHealth]
    mots_one_health: list[str]
    regles_declenchees: dict[DimensionOneHealth, list[str]]
    est_transversal: bool
    nombre_dimensions: int
    score_transversalite: int
    niveau_transversalite: NiveauTransversalite
    details_dimensions: dict[DimensionOneHealth, DetailDimension]
    texte_analyse_vide: bool
    resume: str
    configuration: dict[str, int]


@dataclass(frozen=True, slots=True)
class ConfigurationOneHealth:
    """Paramètres utilisés pour qualifier la transversalité One Health."""

    dimensions_minimales_transversalite: int = 2

    def __post_init__(self) -> None:
        """Valide la cohérence de la configuration."""
        valeur = self.dimensions_minimales_transversalite

        if isinstance(valeur, bool) or not isinstance(valeur, int):
            raise TypeError(
                "dimensions_minimales_transversalite doit être un entier."
            )

        if not 1 <= valeur <= 3:
            raise ValueError(
                "dimensions_minimales_transversalite doit être comprise "
                "entre 1 et 3."
            )


@dataclass(frozen=True, slots=True)
class _AnalyseDimension:
    """Représentation interne d'une dimension analysée."""

    dimension: DimensionOneHealth
    mots_detectes: tuple[str, ...]
    nombre_occurrences: int

    @property
    def detectee(self) -> bool:
        """Indique si au moins une règle de la dimension a été détectée."""
        return bool(self.mots_detectes)

    def exporter(self) -> DetailDimension:
        """Retourne la représentation publique de l'analyse."""
        return {
            "detectee": self.detectee,
            "nombre_occurrences": self.nombre_occurrences,
            "mots_detectes": list(self.mots_detectes),
        }


CONFIGURATION_PAR_DEFAUT = ConfigurationOneHealth()


REGLES_ONE_HEALTH: Final[
    dict[DimensionOneHealth, tuple[str, ...]]
] = {
    "Humain": (
        "human health",
        "human population",
        "human cases",
        "human infection",
        "patients",
        "hospitalized patients",
        "healthcare workers",
        "public health",
        "clinical outcomes",
        "sante humaine",
        "population humaine",
        "cas humains",
        "infection humaine",
        "patients hospitalises",
        "professionnels de sante",
        "sante publique",
        "resultats cliniques",
    ),
    "Animal": (
        "animal health",
        "animal population",
        "animal cases",
        "veterinary",
        "livestock",
        "wildlife",
        "poultry flock",
        "cattle herd",
        "swine herd",
        "companion animals",
        "animal reservoir",
        "sante animale",
        "population animale",
        "cas animaux",
        "veterinaire",
        "betail",
        "faune sauvage",
        "elevage de volailles",
        "troupeau bovin",
        "reservoir animal",
    ),
    "Environnement": (
        "environmental health",
        "environmental exposure",
        "environmental reservoir",
        "environmental surveillance",
        "wastewater surveillance",
        "drinking water",
        "surface water",
        "soil contamination",
        "air pollution",
        "water pollution",
        "climate change",
        "vector borne",
        "mosquito borne",
        "tick borne",
        "sante environnementale",
        "exposition environnementale",
        "reservoir environnemental",
        "surveillance environnementale",
        "surveillance des eaux usees",
        "eau potable",
        "eaux de surface",
        "contamination des sols",
        "pollution de l air",
        "pollution de l eau",
        "changement climatique",
        "transmis par les moustiques",
        "transmis par les tiques",
    ),
}


_ORDRE_DIMENSIONS: Final[tuple[DimensionOneHealth, ...]] = (
    "Humain",
    "Animal",
    "Environnement",
)


def _normaliser_texte(texte: Any) -> str:
    """Normalise un texte pour les comparaisons lexicales."""
    propre = " ".join(str(texte or "").split()).casefold()
    return "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", propre)
        if not unicodedata.combining(caractere)
    )


def _verifier_regles_one_health() -> None:
    """Valide la cohérence, l'unicité et l'exhaustivité des règles."""
    dimensions_regles = tuple(REGLES_ONE_HEALTH)
    if dimensions_regles != _ORDRE_DIMENSIONS:
        raise ValueError(
            "L'ordre des clés de REGLES_ONE_HEALTH doit correspondre à "
            "_ORDRE_DIMENSIONS."
        )

    regles_globales: dict[str, DimensionOneHealth] = {}

    for dimension in _ORDRE_DIMENSIONS:
        regles = REGLES_ONE_HEALTH[dimension]
        if not regles:
            raise ValueError(
                f"La dimension {dimension!r} doit contenir au moins une règle."
            )

        regles_dimension: set[str] = set()

        for regle in regles:
            if not isinstance(regle, str):
                raise TypeError(
                    f"Chaque règle de {dimension!r} doit être une chaîne."
                )

            normalisee = _normaliser_texte(regle)
            if not normalisee:
                raise ValueError(
                    f"La dimension {dimension!r} contient une règle vide."
                )

            if normalisee in regles_dimension:
                raise ValueError(
                    f"Règle dupliquée dans {dimension!r} : {regle!r}."
                )
            regles_dimension.add(normalisee)

            autre_dimension = regles_globales.get(normalisee)
            if autre_dimension is not None:
                raise ValueError(
                    f"La règle {regle!r} est partagée entre "
                    f"{autre_dimension!r} et {dimension!r}."
                )

            regles_globales[normalisee] = dimension


_verifier_regles_one_health()


REGLES_NORMALISEES: Final[
    dict[DimensionOneHealth, frozenset[str]]
] = {
    dimension: frozenset(
        _normaliser_texte(regle)
        for regle in REGLES_ONE_HEALTH[dimension]
    )
    for dimension in _ORDRE_DIMENSIONS
}


def _uniques(elements: Sequence[str]) -> list[str]:
    """Déduplique des chaînes en conservant leur ordre d'apparition."""
    resultat: list[str] = []
    vus: set[str] = set()

    for element in elements:
        propre = " ".join(str(element or "").split())
        if not propre:
            continue

        cle = _normaliser_texte(propre)
        if cle in vus:
            continue

        vus.add(cle)
        resultat.append(propre)

    return resultat


def _ordonner_dimensions(
    dimensions: Sequence[str],
) -> list[DimensionOneHealth]:
    """Filtre et ordonne les dimensions selon l'ordre métier officiel."""
    presentes = {str(dimension) for dimension in dimensions}
    return [
        dimension
        for dimension in _ORDRE_DIMENSIONS
        if dimension in presentes
    ]


def _compter_occurrences(
    texte_normalise: str,
    mots: Sequence[str],
) -> int:
    """Compte les occurrences littérales des règles détectées."""
    total = 0
    for mot in mots:
        motif = _normaliser_texte(mot)
        if motif:
            total += texte_normalise.count(motif)
    return total


def _analyser_dimension(
    dimension: DimensionOneHealth,
    *,
    texte_normalise: str,
    mots_detectes: Sequence[str],
) -> _AnalyseDimension:
    """Construit l'analyse interne d'une dimension."""
    regles_dimension = REGLES_NORMALISEES[dimension]
    mots_dimension = tuple(
        mot
        for mot in mots_detectes
        if _normaliser_texte(mot) in regles_dimension
    )

    return _AnalyseDimension(
        dimension=dimension,
        mots_detectes=mots_dimension,
        nombre_occurrences=_compter_occurrences(
            texte_normalise,
            mots_dimension,
        ),
    )


def _determiner_niveau_transversalite(
    nombre_dimensions: int,
) -> NiveauTransversalite:
    """Convertit le nombre de dimensions détectées en niveau lisible."""
    niveaux: Final[dict[int, NiveauTransversalite]] = {
        0: "aucune",
        1: "faible",
        2: "partielle",
        3: "complete",
    }
    return niveaux[nombre_dimensions]


def _construire_resume(
    *,
    dimensions: Sequence[DimensionOneHealth],
    dimensions_absentes: Sequence[DimensionOneHealth],
    est_transversal: bool,
    score_transversalite: int,
    texte_analyse_vide: bool,
) -> str:
    """Construit une synthèse stable directement exploitable."""
    if texte_analyse_vide:
        return (
            "Aucun texte exploitable n'a été fourni. "
            "Aucune dimension One Health n'a été détectée."
        )

    if dimensions:
        dimensions_texte = ", ".join(dimensions)
        debut = f"Dimensions détectées : {dimensions_texte}."
    else:
        debut = "Aucune dimension One Health détectée."

    statut = (
        "L'analyse est transversale."
        if est_transversal
        else "L'analyse n'est pas transversale."
    )

    morceaux = [
        debut,
        statut,
        f"Score de transversalité : {score_transversalite}/100.",
    ]

    if dimensions_absentes:
        morceaux.append(
            "Dimensions absentes : "
            + ", ".join(dimensions_absentes)
            + "."
        )

    return " ".join(morceaux)


def detecter_one_health_dans_texte(
    texte: str,
) -> tuple[list[DimensionOneHealth], list[str]]:
    """Retourne les dimensions et mots One Health détectés dans un texte."""
    if not isinstance(texte, str):
        raise TypeError("texte doit être une chaîne de caractères.")

    dimensions, mots_detectes = detecter_regles(
        texte,
        REGLES_ONE_HEALTH,
    )

    return _ordonner_dimensions(dimensions), _uniques(mots_detectes)


def detecter_one_health(
    article: Mapping[str, Any] | None,
) -> tuple[list[DimensionOneHealth], list[str]]:
    """Construit le texte d'un article puis applique la détection."""
    if article is not None and not isinstance(article, Mapping):
        raise TypeError(
            "article doit être un objet compatible avec Mapping ou None."
        )

    return detecter_one_health_dans_texte(construire_texte(article))


def analyser_one_health(
    article: Mapping[str, Any] | None,
    *,
    configuration: ConfigurationOneHealth = CONFIGURATION_PAR_DEFAUT,
) -> ResultatOneHealth:
    """
    Produit une analyse One Health détaillée, stable et explicable.

    La transversalité dépend du nombre minimal de dimensions défini dans la
    configuration. Le score correspond à la proportion de dimensions détectées
    parmi les trois dimensions One Health possibles.
    """
    if article is not None and not isinstance(article, Mapping):
        raise TypeError(
            "article doit être un objet compatible avec Mapping ou None."
        )

    if not isinstance(configuration, ConfigurationOneHealth):
        raise TypeError(
            "configuration doit être une instance de "
            "ConfigurationOneHealth."
        )

    texte = construire_texte(article)
    if not isinstance(texte, str):
        raise TypeError(
            "construire_texte(article) doit retourner une chaîne."
        )

    texte_normalise = _normaliser_texte(texte)
    dimensions_detectees, mots_detectes = (
        detecter_one_health_dans_texte(texte)
    )

    analyses = {
        dimension: _analyser_dimension(
            dimension,
            texte_normalise=texte_normalise,
            mots_detectes=mots_detectes,
        )
        for dimension in _ORDRE_DIMENSIONS
    }

    dimensions = [
        dimension
        for dimension in _ORDRE_DIMENSIONS
        if analyses[dimension].detectee
    ]
    dimensions_absentes = [
        dimension
        for dimension in _ORDRE_DIMENSIONS
        if not analyses[dimension].detectee
    ]

    # Défense contre un éventuel écart entre detecter_regles et l'analyse
    # locale des règles précompilées.
    if dimensions != dimensions_detectees:
        dimensions = dimensions_detectees
        dimensions_absentes = [
            dimension
            for dimension in _ORDRE_DIMENSIONS
            if dimension not in dimensions
        ]

    nombre_dimensions = len(dimensions)
    score_transversalite = round(
        nombre_dimensions / len(_ORDRE_DIMENSIONS) * 100
    )
    niveau_transversalite = _determiner_niveau_transversalite(
        nombre_dimensions
    )
    est_transversal = (
        nombre_dimensions
        >= configuration.dimensions_minimales_transversalite
    )
    texte_analyse_vide = not bool(texte_normalise)

    details_dimensions = {
        dimension: analyses[dimension].exporter()
        for dimension in _ORDRE_DIMENSIONS
    }
    regles_declenchees = {
        dimension: list(analyses[dimension].mots_detectes)
        for dimension in _ORDRE_DIMENSIONS
    }

    return {
        "one_health": cast(list[DimensionOneHealth], dimensions),
        "dimensions_absentes": cast(
            list[DimensionOneHealth],
            dimensions_absentes,
        ),
        "mots_one_health": mots_detectes,
        "regles_declenchees": regles_declenchees,
        "est_transversal": est_transversal,
        "nombre_dimensions": nombre_dimensions,
        "score_transversalite": score_transversalite,
        "niveau_transversalite": niveau_transversalite,
        "details_dimensions": details_dimensions,
        "texte_analyse_vide": texte_analyse_vide,
        "resume": _construire_resume(
            dimensions=dimensions,
            dimensions_absentes=dimensions_absentes,
            est_transversal=est_transversal,
            score_transversalite=score_transversalite,
            texte_analyse_vide=texte_analyse_vide,
        ),
        "configuration": asdict(configuration),
    }


def analyser_one_health_dans_texte(
    texte: str,
    *,
    configuration: ConfigurationOneHealth = CONFIGURATION_PAR_DEFAUT,
) -> ResultatOneHealth:
    """Analyse directement le texte canonique déjà préparé par le pipeline.

    Cette variante évite de reconstruire le corpus depuis l'article lorsque
    ``ContexteClassification`` possède déjà son texte de référence. Elle
    applique exactement les mêmes règles et la même qualification de
    transversalité que :func:`analyser_one_health`.
    """
    if not isinstance(texte, str):
        raise TypeError("texte doit être une chaîne de caractères.")
    if not isinstance(configuration, ConfigurationOneHealth):
        raise TypeError(
            "configuration doit être une instance de ConfigurationOneHealth."
        )

    texte_normalise = _normaliser_texte(texte)
    dimensions_detectees, mots_detectes = detecter_one_health_dans_texte(texte)

    analyses = {
        dimension: _analyser_dimension(
            dimension,
            texte_normalise=texte_normalise,
            mots_detectes=mots_detectes,
        )
        for dimension in _ORDRE_DIMENSIONS
    }

    dimensions = [
        dimension
        for dimension in _ORDRE_DIMENSIONS
        if analyses[dimension].detectee
    ]
    dimensions_absentes = [
        dimension
        for dimension in _ORDRE_DIMENSIONS
        if not analyses[dimension].detectee
    ]

    if dimensions != dimensions_detectees:
        dimensions = dimensions_detectees
        dimensions_absentes = [
            dimension
            for dimension in _ORDRE_DIMENSIONS
            if dimension not in dimensions
        ]

    nombre_dimensions = len(dimensions)
    score_transversalite = round(
        nombre_dimensions / len(_ORDRE_DIMENSIONS) * 100
    )
    niveau_transversalite = _determiner_niveau_transversalite(
        nombre_dimensions
    )
    est_transversal = (
        nombre_dimensions
        >= configuration.dimensions_minimales_transversalite
    )
    texte_analyse_vide = not bool(texte_normalise)

    details_dimensions = {
        dimension: analyses[dimension].exporter()
        for dimension in _ORDRE_DIMENSIONS
    }
    regles_declenchees = {
        dimension: list(analyses[dimension].mots_detectes)
        for dimension in _ORDRE_DIMENSIONS
    }

    return {
        "one_health": cast(list[DimensionOneHealth], dimensions),
        "dimensions_absentes": cast(
            list[DimensionOneHealth],
            dimensions_absentes,
        ),
        "mots_one_health": mots_detectes,
        "regles_declenchees": regles_declenchees,
        "est_transversal": est_transversal,
        "nombre_dimensions": nombre_dimensions,
        "score_transversalite": score_transversalite,
        "niveau_transversalite": niveau_transversalite,
        "details_dimensions": details_dimensions,
        "texte_analyse_vide": texte_analyse_vide,
        "resume": _construire_resume(
            dimensions=dimensions,
            dimensions_absentes=dimensions_absentes,
            est_transversal=est_transversal,
            score_transversalite=score_transversalite,
            texte_analyse_vide=texte_analyse_vide,
        ),
        "configuration": asdict(configuration),
    }


def dimensions_detectees(
    valeur: Mapping[str, Any] | Iterable[str] | None,
) -> tuple[DimensionOneHealth, ...]:
    """Retourne les dimensions reconnues dans leur ordre métier officiel."""
    if valeur is None:
        return ()
    if isinstance(valeur, Mapping):
        valeur = valeur.get("one_health", ())
    if isinstance(valeur, str):
        valeurs: Iterable[Any] = (valeur,)
    else:
        valeurs = valeur
    return tuple(_ordonner_dimensions([str(item) for item in valeurs]))


def contient_dimension(
    valeur: Mapping[str, Any] | Iterable[str] | None,
    dimension: str,
) -> bool:
    """Teste la présence d'une dimension sans dépendre de casse ou d'accents."""
    cible = _normaliser_texte(dimension)
    return bool(cible) and any(
        _normaliser_texte(element) == cible
        for element in dimensions_detectees(valeur)
    )


def obtenir_score_transversalite(
    valeur: Mapping[str, Any] | Iterable[str] | None,
) -> int:
    """Calcule le score technique de transversalité sur les trois dimensions."""
    if isinstance(valeur, Mapping):
        score = valeur.get("score_transversalite")
        if isinstance(score, int) and not isinstance(score, bool):
            return min(max(score, 0), 100)
    return round(len(dimensions_detectees(valeur)) / len(_ORDRE_DIMENSIONS) * 100)


def est_transversal_one_health(
    valeur: Mapping[str, Any] | Iterable[str] | None,
    *,
    configuration: ConfigurationOneHealth = CONFIGURATION_PAR_DEFAUT,
) -> bool:
    """Qualifie une collection ou un résultat selon la configuration fournie."""
    if not isinstance(configuration, ConfigurationOneHealth):
        raise TypeError(
            "configuration doit être une instance de ConfigurationOneHealth."
        )
    if isinstance(valeur, Mapping) and isinstance(
        valeur.get("est_transversal"), bool
    ):
        return bool(valeur["est_transversal"])
    return (
        len(dimensions_detectees(valeur))
        >= configuration.dimensions_minimales_transversalite
    )


def statistiques_one_health(
    valeur: Mapping[str, Any] | Iterable[str] | None,
) -> dict[str, Any]:
    """Produit un résumé technique stable sans altérer le résultat métier."""
    dimensions = dimensions_detectees(valeur)
    return {
        "nombre_dimensions": len(dimensions),
        "dimensions": list(dimensions),
        "score_transversalite": obtenir_score_transversalite(valeur),
        "est_transversal": est_transversal_one_health(valeur),
    }


def executer(
    etat: "EtatClassification",
    *,
    configuration: ConfigurationOneHealth = CONFIGURATION_PAR_DEFAUT,
) -> None:
    """Exécute l'étape officielle ``one_health`` du pipeline V6.

    Le pipeline conserve l'orchestration et le cycle de vie. Ce module applique
    uniquement les règles One Health et écrit les sorties dont il est
    propriétaire dans ``ContexteClassification``.
    """
    contexte = getattr(etat, "contexte", None)
    if contexte is None:
        raise TypeError("etat doit exposer un attribut contexte.")

    texte = getattr(contexte, "texte", None)
    if not isinstance(texte, str):
        raise TypeError("etat.contexte.texte doit être une chaîne de caractères.")

    resultat = analyser_one_health_dans_texte(
        texte,
        configuration=configuration,
    )
    dimensions = resultat["one_health"]
    mots_detectes = resultat["mots_one_health"]

    definir = getattr(contexte, "definir_one_health", None)
    if callable(definir):
        definir(dimensions, mots_detectes)
    else:
        contexte.one_health = list(dimensions)
        contexte.mots_one_health = list(mots_detectes)

    extensions = getattr(etat, "extensions", None)
    if isinstance(extensions, dict):
        extensions["one_health"] = dict(resultat)
        extensions.setdefault("versions_modules", {})["one_health"] = (
            VERSION_ONE_HEALTH
        )

    audit = getattr(etat, "audit", None)
    enregistrer = getattr(audit, "enregistrer", None)
    if callable(enregistrer):
        enregistrer(
            "one_health_calcule",
            donnees={
                "version_module": VERSION_ONE_HEALTH,
                "nombre_dimensions": resultat["nombre_dimensions"],
                "dimensions": list(dimensions),
                "nombre_regles_declenchees": len(mots_detectes),
                "score_transversalite": resultat["score_transversalite"],
                "niveau_transversalite": resultat["niveau_transversalite"],
                "est_transversal": resultat["est_transversal"],
                "texte_analyse_vide": resultat["texte_analyse_vide"],
            },
        )


executer_one_health = executer


__all__ = [
    "CONFIGURATION_PAR_DEFAUT",
    "ConfigurationOneHealth",
    "DetailDimension",
    "DimensionOneHealth",
    "NiveauTransversalite",
    "REGLES_NORMALISEES",
    "REGLES_ONE_HEALTH",
    "ResultatOneHealth",
    "VERSION_ONE_HEALTH",
    "analyser_one_health",
    "analyser_one_health_dans_texte",
    "contient_dimension",
    "detecter_one_health",
    "detecter_one_health_dans_texte",
    "dimensions_detectees",
    "est_transversal_one_health",
    "executer",
    "executer_one_health",
    "obtenir_score_transversalite",
    "statistiques_one_health",
]