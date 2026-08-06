"""Utilitaires déterministes partagés par le moteur de classification.

Version 4.

Aucune dépendance externe et aucune IA : les mêmes entrées produisent toujours
les mêmes sorties.

Cette version conserve l'API V2 et ajoute notamment :

- la préparation immuable des référentiels ;
- la prise en charge sûre des générateurs d'expressions ;
- le comptage des occurrences et leur position ;
- un indice de couverture déterministe ;
- des alertes explicites sur la qualité de l'analyse ;
- une analyse directe d'article ;
- des empreintes séparées pour l'entrée, le résultat et l'analyse complète ;
- des statistiques de cache auditables ;
- une densité de détection et une couverture par expressions ;
- un classement déterministe des règles détectées ;
- des extraits de contexte autour des occurrences ;
- une traçabilité explicite de la troncature ;
- une empreinte dédiée au corpus normalisé.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import lru_cache
from types import MappingProxyType
from typing import Any, Final, Literal, TypedDict


ENGINE_VERSION: Final[str] = "4.0"
RULESET_VERSION: Final[str] = "2026.03"

CHAMPS_TEXTE: Final[tuple[tuple[str, ...], ...]] = (
    ("titre", "title", "headline"),
    ("resume", "résumé", "abstract", "summary", "description"),
    ("contenu", "content", "texte", "body", "full_text", "fulltext"),
    ("mots_cles", "mots-clés", "keywords", "tags", "mesh_terms"),
)

ModeCorrespondance = Literal["limites_alphanumeriques", "sous_chaine"]
QualiteTexte = Literal["vide", "faible", "moyenne", "riche"]
NiveauCouverture = Literal["nulle", "faible", "moyenne", "forte"]
NiveauDensite = Literal["nulle", "faible", "moyenne", "forte"]


class OccurrenceExpression(TypedDict):
    """Occurrence normalisée et localisable d'une expression."""

    expression: str
    expression_normalisee: str
    nombre_occurrences: int
    premiere_position: int
    derniere_position: int
    contexte: str


class TraceRegle(TypedDict):
    """Trace déterministe d'une règle évaluée."""

    ordre: int
    nom: str
    expressions_evaluees: int
    expressions_detectees: list[str]
    nombre_occurrences: int
    premiere_position: int | None
    couverture_expressions: int
    rang_detection: int | None
    declenchee: bool


class StatistiquesCache(TypedDict):
    """Statistiques observables des caches internes."""

    normalisation_hits: int
    normalisation_misses: int
    normalisation_taille: int
    expressions_hits: int
    expressions_misses: int
    expressions_taille: int


class AuditDetection(TypedDict):
    """Informations d'audit et de reproductibilité."""

    engine_version: str
    ruleset_version: str
    configuration_hash: str
    referentiel_hash: str
    corpus_hash: str
    entree_hash: str
    resultat_hash: str
    analyse_hash: str
    nombre_regles: int
    nombre_regles_declenchees: int
    nombre_expressions_evaluees: int
    nombre_expressions_detectees: int
    nombre_occurrences_total: int
    texte_tronque: bool
    caracteres_ignores: int
    statistiques_cache: StatistiquesCache
    journal: list[TraceRegle]


class ResultatDetection(TypedDict):
    """Résultat public enrichi de la détection."""

    elements_detectes: list[str]
    mots_detectes: list[str]
    correspondances_par_regle: dict[str, list[str]]
    occurrences_par_regle: dict[str, list[OccurrenceExpression]]
    qualite_texte: QualiteTexte
    longueur_texte_normalise: int
    nombre_mots: int
    indice_couverture: int
    niveau_couverture: NiveauCouverture
    couverture_expressions: int
    densite_detection: int
    niveau_densite: NiveauDensite
    classement_regles: list[str]
    texte_tronque: bool
    caracteres_ignores: int
    alertes: list[str]
    audit: AuditDetection
    configuration: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ReglePreparee:
    """Règle normalisée et immuable prête à être évaluée."""

    nom: str
    expressions: tuple[str, ...]
    expressions_normalisees: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.nom, str) or not self.nom.strip():
            raise ValueError("nom doit être une chaîne non vide.")
        if not self.expressions:
            raise ValueError("Une règle préparée doit contenir une expression.")
        if len(self.expressions) != len(self.expressions_normalisees):
            raise ValueError(
                "Les expressions originales et normalisées doivent correspondre."
            )


@dataclass(frozen=True, slots=True)
class ReferentielPrepare:
    """Référentiel validé, matérialisé et immuable."""

    regles: tuple[ReglePreparee, ...]
    empreinte: str

    def __post_init__(self) -> None:
        if not isinstance(self.empreinte, str) or len(self.empreinte) != 64:
            raise ValueError("empreinte doit être une empreinte SHA-256.")
        noms = [regle.nom for regle in self.regles]
        if len(noms) != len(set(noms)):
            raise ValueError("Les noms des règles préparées doivent être uniques.")


@dataclass(frozen=True, slots=True)
class ConfigurationUtilitaires:
    """Configuration déterministe des utilitaires textuels."""

    profondeur_max_aplatissement: int = 12
    taille_max_texte: int = 1_000_000
    mode_correspondance: ModeCorrespondance = "limites_alphanumeriques"
    trier_cles_mapping: bool = False
    refuser_regles_invalides: bool = True
    compter_occurrences: bool = True
    seuil_qualite_faible: int = 80
    seuil_qualite_moyenne: int = 500
    seuil_couverture_faible: int = 20
    seuil_couverture_moyenne: int = 50
    seuil_couverture_forte: int = 80
    seuil_densite_faible: int = 1
    seuil_densite_moyenne: int = 3
    seuil_densite_forte: int = 8
    taille_contexte: int = 40

    def __post_init__(self) -> None:
        champs_entiers = (
            "profondeur_max_aplatissement",
            "taille_max_texte",
            "seuil_qualite_faible",
            "seuil_qualite_moyenne",
            "seuil_couverture_faible",
            "seuil_couverture_moyenne",
            "seuil_couverture_forte",
            "seuil_densite_faible",
            "seuil_densite_moyenne",
            "seuil_densite_forte",
            "taille_contexte",
        )
        for nom in champs_entiers:
            valeur = getattr(self, nom)
            if isinstance(valeur, bool) or not isinstance(valeur, int):
                raise TypeError(f"{nom} doit être un entier.")

        if not 1 <= self.profondeur_max_aplatissement <= 100:
            raise ValueError(
                "profondeur_max_aplatissement doit être comprise entre 1 et 100."
            )
        if not 1 <= self.taille_max_texte <= 10_000_000:
            raise ValueError(
                "taille_max_texte doit être comprise entre 1 et 10 000 000."
            )
        if not (
            1 <= self.seuil_qualite_faible
            < self.seuil_qualite_moyenne
            <= self.taille_max_texte
        ):
            raise ValueError(
                "Les seuils de qualité doivent être croissants et compatibles "
                "avec taille_max_texte."
            )
        if not (
            0
            <= self.seuil_couverture_faible
            < self.seuil_couverture_moyenne
            < self.seuil_couverture_forte
            <= 100
        ):
            raise ValueError(
                "Les seuils de couverture doivent être strictement croissants "
                "entre 0 et 100."
            )
        if not (
            0
            <= self.seuil_densite_faible
            < self.seuil_densite_moyenne
            < self.seuil_densite_forte
            <= 100
        ):
            raise ValueError(
                "Les seuils de densité doivent être strictement croissants "
                "entre 0 et 100."
            )
        if not 0 <= self.taille_contexte <= 500:
            raise ValueError(
                "taille_contexte doit être comprise entre 0 et 500."
            )

        if self.mode_correspondance not in {
            "limites_alphanumeriques",
            "sous_chaine",
        }:
            raise ValueError("mode_correspondance non reconnu.")

        for nom in (
            "trier_cles_mapping",
            "refuser_regles_invalides",
            "compter_occurrences",
        ):
            if not isinstance(getattr(self, nom), bool):
                raise TypeError(f"{nom} doit être un booléen.")


CONFIGURATION_PAR_DEFAUT = ConfigurationUtilitaires()


def _json_compatible(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(cle): _json_compatible(valeur)
            for cle, valeur in value.items()
        }
    if isinstance(value, (tuple, list)):
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
    configuration: ConfigurationUtilitaires,
) -> dict[str, Any]:
    return {
        "profondeur_max_aplatissement": (
            configuration.profondeur_max_aplatissement
        ),
        "taille_max_texte": configuration.taille_max_texte,
        "mode_correspondance": configuration.mode_correspondance,
        "trier_cles_mapping": configuration.trier_cles_mapping,
        "refuser_regles_invalides": configuration.refuser_regles_invalides,
        "compter_occurrences": configuration.compter_occurrences,
        "seuil_qualite_faible": configuration.seuil_qualite_faible,
        "seuil_qualite_moyenne": configuration.seuil_qualite_moyenne,
        "seuil_couverture_faible": configuration.seuil_couverture_faible,
        "seuil_couverture_moyenne": configuration.seuil_couverture_moyenne,
        "seuil_couverture_forte": configuration.seuil_couverture_forte,
        "seuil_densite_faible": configuration.seuil_densite_faible,
        "seuil_densite_moyenne": configuration.seuil_densite_moyenne,
        "seuil_densite_forte": configuration.seuil_densite_forte,
        "taille_contexte": configuration.taille_contexte,
    }


def _tronquer(texte: str, limite: int) -> str:
    return texte if len(texte) <= limite else texte[:limite]


def _aplatir_valeur(
    valeur: Any,
    *,
    configuration: ConfigurationUtilitaires,
    profondeur: int,
    visites: set[int],
) -> str:
    if valeur is None:
        return ""
    if profondeur > configuration.profondeur_max_aplatissement:
        return ""

    if isinstance(valeur, str):
        sans_html = re.sub(r"<[^>]+>", " ", html.unescape(valeur))
        return _tronquer(
            " ".join(sans_html.split()),
            configuration.taille_max_texte,
        )

    if isinstance(valeur, (bytes, bytearray)):
        return _tronquer(
            valeur.decode("utf-8", errors="replace"),
            configuration.taille_max_texte,
        )

    identifiant = id(valeur)
    est_conteneur = isinstance(valeur, (Mapping, Iterable))
    if est_conteneur:
        if identifiant in visites:
            return ""
        visites.add(identifiant)

    try:
        if isinstance(valeur, Mapping):
            items: Iterable[tuple[Any, Any]] = valeur.items()
            if configuration.trier_cles_mapping:
                items = sorted(items, key=lambda item: str(item[0]))
            morceaux = (
                _aplatir_valeur(
                    element,
                    configuration=configuration,
                    profondeur=profondeur + 1,
                    visites=visites,
                )
                for _, element in items
            )
            return _tronquer(
                " ".join(morceau for morceau in morceaux if morceau),
                configuration.taille_max_texte,
            )

        if isinstance(valeur, Iterable):
            morceaux = (
                _aplatir_valeur(
                    element,
                    configuration=configuration,
                    profondeur=profondeur + 1,
                    visites=visites,
                )
                for element in valeur
            )
            return _tronquer(
                " ".join(morceau for morceau in morceaux if morceau),
                configuration.taille_max_texte,
            )

        return _tronquer(str(valeur), configuration.taille_max_texte)
    finally:
        if est_conteneur:
            visites.discard(identifiant)


def aplatir_valeur(
    valeur: Any,
    configuration: ConfigurationUtilitaires = CONFIGURATION_PAR_DEFAUT,
) -> str:
    """Convertit récursivement une valeur RSS/API en texte stable."""
    if not isinstance(configuration, ConfigurationUtilitaires):
        raise TypeError(
            "configuration doit être une instance de ConfigurationUtilitaires."
        )
    return _aplatir_valeur(
        valeur,
        configuration=configuration,
        profondeur=0,
        visites=set(),
    )


def extraire_champ(
    article: Mapping[str, Any],
    noms: Iterable[str],
    configuration: ConfigurationUtilitaires = CONFIGURATION_PAR_DEFAUT,
) -> Any:
    """Retourne la première valeur réellement exploitable parmi les alias."""
    if not isinstance(article, Mapping):
        raise TypeError("article doit être compatible avec Mapping.")

    for nom in noms:
        if not isinstance(nom, str) or not nom:
            continue
        valeur = article.get(nom)
        if aplatir_valeur(valeur, configuration).strip():
            return valeur
    return ""


@lru_cache(maxsize=8192)
def normaliser_chaine(texte: str) -> str:
    """Normalise accents, casse, espaces et ponctuation."""
    if not isinstance(texte, str):
        raise TypeError("texte doit être une chaîne.")

    texte_normalise = unicodedata.normalize("NFKD", texte.casefold())
    texte_sans_accents = "".join(
        caractere
        for caractere in texte_normalise
        if not unicodedata.combining(caractere)
    )
    texte_alphanumerique = re.sub(
        r"[^a-z0-9]+",
        " ",
        texte_sans_accents,
    )
    return " ".join(texte_alphanumerique.split())


def normaliser(texte: Any) -> str:
    """Normalise toute valeur en chaîne comparable."""
    return normaliser_chaine(str(texte or ""))


@lru_cache(maxsize=8192)
def compiler_expression(expression: str) -> re.Pattern[str]:
    """Compile une expression normalisée avec des limites strictes."""
    if not isinstance(expression, str):
        raise TypeError("expression doit être une chaîne.")

    expression_normalisee = normaliser(expression)
    if not expression_normalisee:
        raise ValueError("expression ne peut pas être vide après normalisation.")

    motif = (
        rf"(?<![a-z0-9])"
        rf"{re.escape(expression_normalisee)}"
        rf"(?![a-z0-9])"
    )
    return re.compile(motif)


def _positions_expression(
    texte_normalise: str,
    expression_normalisee: str,
    mode: ModeCorrespondance,
) -> list[int]:
    if not texte_normalise or not expression_normalisee:
        return []

    if mode == "limites_alphanumeriques":
        return [
            correspondance.start()
            for correspondance in compiler_expression(
                expression_normalisee
            ).finditer(texte_normalise)
        ]

    if mode == "sous_chaine":
        positions: list[int] = []
        depart = 0
        while True:
            position = texte_normalise.find(expression_normalisee, depart)
            if position < 0:
                return positions
            positions.append(position)
            depart = position + max(1, len(expression_normalisee))

    raise ValueError("mode de correspondance non reconnu.")


def contient_expression(
    texte: str,
    expression: str,
    *,
    mode: ModeCorrespondance = "limites_alphanumeriques",
) -> bool:
    """Indique si une expression normalisée est présente dans le texte."""
    if not isinstance(texte, str) or not isinstance(expression, str):
        raise TypeError("texte et expression doivent être des chaînes.")

    return bool(
        _positions_expression(
            normaliser(texte),
            normaliser(expression),
            mode,
        )
    )


def construire_texte(
    article: Mapping[str, Any] | None,
    configuration: ConfigurationUtilitaires = CONFIGURATION_PAR_DEFAUT,
) -> str:
    """Construit le corpus scientifique sans injecter le nom de la source."""
    if article is None:
        article = {}
    if not isinstance(article, Mapping):
        raise TypeError("article doit être compatible avec Mapping ou None.")
    if not isinstance(configuration, ConfigurationUtilitaires):
        raise TypeError(
            "configuration doit être une instance de ConfigurationUtilitaires."
        )

    champs = (
        extraire_champ(article, alias, configuration)
        for alias in CHAMPS_TEXTE
    )
    texte_brut = " ".join(
        aplatir_valeur(champ, configuration)
        for champ in champs
    )
    return _tronquer(
        normaliser(texte_brut),
        configuration.taille_max_texte,
    )


def dedupliquer(elements: Iterable[Any]) -> list[Any]:
    """Déduplique en conservant l'ordre de première apparition."""
    resultat: list[Any] = []
    deja_vus_hashables: set[Any] = set()
    deja_vus_non_hashables: list[Any] = []

    for element in elements:
        if element is None or element == "":
            continue

        try:
            deja_vu = element in deja_vus_hashables
        except TypeError:
            deja_vu = any(
                element == ancien
                for ancien in deja_vus_non_hashables
            )
            if not deja_vu:
                deja_vus_non_hashables.append(element)
        else:
            if not deja_vu:
                deja_vus_hashables.add(element)

        if not deja_vu:
            resultat.append(element)

    return resultat


def _materialiser_regles(
    regles: Mapping[str, Iterable[str]],
) -> dict[str, tuple[Any, ...]]:
    """Matérialise une seule fois les itérables, y compris les générateurs."""
    if not isinstance(regles, Mapping):
        raise TypeError("Le référentiel doit être compatible avec Mapping.")

    resultat: dict[str, tuple[Any, ...]] = {}
    for nom, expressions in regles.items():
        if isinstance(expressions, str):
            resultat[str(nom)] = (expressions,)
            continue
        try:
            resultat[str(nom)] = tuple(expressions)
        except TypeError:
            resultat[str(nom)] = ()
    return resultat


def valider_regles(
    regles: Mapping[str, Iterable[str]],
) -> list[str]:
    """Retourne les anomalies déterministes d'un référentiel."""
    if not isinstance(regles, Mapping):
        return ["Le référentiel doit être compatible avec Mapping."]

    materiel = _materialiser_regles(regles)
    anomalies: list[str] = []
    noms_normalises: set[str] = set()

    for nom_original, expressions_originales in regles.items():
        if not isinstance(nom_original, str) or not nom_original.strip():
            anomalies.append("Une règle possède un nom vide ou invalide.")
            continue

        nom_normalise = normaliser(nom_original)
        if nom_normalise in noms_normalises:
            anomalies.append(
                f"Nom de règle dupliqué après normalisation : "
                f"{nom_original!r}."
            )
        noms_normalises.add(nom_normalise)

        if isinstance(expressions_originales, str):
            anomalies.append(
                f"La règle {nom_original!r} doit contenir un itérable "
                "d'expressions, pas une chaîne unique."
            )
            continue

        expressions = materiel[str(nom_original)]
        if not expressions:
            anomalies.append(
                f"La règle {nom_original!r} ne contient aucune expression."
            )
            continue

        expressions_normalisees: set[str] = set()
        for expression in expressions:
            if not isinstance(expression, str):
                anomalies.append(
                    f"La règle {nom_original!r} contient une expression "
                    "non textuelle."
                )
                continue

            normalisee = normaliser(expression)
            if not normalisee:
                anomalies.append(
                    f"La règle {nom_original!r} contient une expression vide."
                )
            elif normalisee in expressions_normalisees:
                anomalies.append(
                    f"Expression dupliquée dans {nom_original!r} : "
                    f"{expression!r}."
                )
            expressions_normalisees.add(normalisee)

    return anomalies


def preparer_regles(
    regles: Mapping[str, Iterable[str]],
    *,
    refuser_invalides: bool = True,
) -> ReferentielPrepare:
    """Valide et transforme un référentiel en structure immuable."""
    if not isinstance(refuser_invalides, bool):
        raise TypeError("refuser_invalides doit être un booléen.")
    if not isinstance(regles, Mapping):
        raise TypeError("Le référentiel doit être compatible avec Mapping.")

    materiel = _materialiser_regles(regles)
    anomalies = valider_regles(
        {
            nom: expressions
            for nom, expressions in materiel.items()
        }
    )
    if anomalies and refuser_invalides:
        raise ValueError(
            "Référentiel de règles invalide : " + " | ".join(anomalies)
        )

    regles_preparees: list[ReglePreparee] = []
    for nom, expressions in materiel.items():
        if not isinstance(nom, str) or not nom.strip():
            continue

        originales: list[str] = []
        normalisees: list[str] = []
        deja_vues: set[str] = set()
        for expression in expressions:
            if not isinstance(expression, str):
                continue
            expression_normalisee = normaliser(expression)
            if not expression_normalisee or expression_normalisee in deja_vues:
                continue
            deja_vues.add(expression_normalisee)
            originales.append(expression)
            normalisees.append(expression_normalisee)

        if originales:
            regles_preparees.append(
                ReglePreparee(
                    nom=nom,
                    expressions=tuple(originales),
                    expressions_normalisees=tuple(normalisees),
                )
            )

    serialisable = {
        regle.nom: list(regle.expressions)
        for regle in regles_preparees
    }
    return ReferentielPrepare(
        regles=tuple(regles_preparees),
        empreinte=_empreinte_json(serialisable),
    )


def _qualite_texte(
    texte: str,
    configuration: ConfigurationUtilitaires,
) -> QualiteTexte:
    longueur = len(texte)
    if longueur == 0:
        return "vide"
    if longueur < configuration.seuil_qualite_faible:
        return "faible"
    if longueur < configuration.seuil_qualite_moyenne:
        return "moyenne"
    return "riche"


def _niveau_couverture(
    indice: int,
    configuration: ConfigurationUtilitaires,
) -> NiveauCouverture:
    if indice < configuration.seuil_couverture_faible:
        return "nulle"
    if indice < configuration.seuil_couverture_moyenne:
        return "faible"
    if indice < configuration.seuil_couverture_forte:
        return "moyenne"
    return "forte"


def _niveau_densite(
    densite: int,
    configuration: ConfigurationUtilitaires,
) -> NiveauDensite:
    if densite < configuration.seuil_densite_faible:
        return "nulle"
    if densite < configuration.seuil_densite_moyenne:
        return "faible"
    if densite < configuration.seuil_densite_forte:
        return "moyenne"
    return "forte"


def _extraire_contexte(
    texte: str,
    position: int,
    longueur_expression: int,
    rayon: int,
) -> str:
    debut = max(0, position - rayon)
    fin = min(len(texte), position + longueur_expression + rayon)
    return texte[debut:fin].strip()


def _statistiques_cache() -> StatistiquesCache:
    normalisation = normaliser_chaine.cache_info()
    expressions = compiler_expression.cache_info()
    return {
        "normalisation_hits": normalisation.hits,
        "normalisation_misses": normalisation.misses,
        "normalisation_taille": normalisation.currsize,
        "expressions_hits": expressions.hits,
        "expressions_misses": expressions.misses,
        "expressions_taille": expressions.currsize,
    }


def vider_caches() -> None:
    """Vide explicitement les caches internes."""
    normaliser_chaine.cache_clear()
    compiler_expression.cache_clear()


def analyser_regles_preparees(
    texte: str,
    referentiel: ReferentielPrepare,
    configuration: ConfigurationUtilitaires = CONFIGURATION_PAR_DEFAUT,
) -> ResultatDetection:
    """Analyse un texte à partir d'un référentiel déjà préparé."""
    if not isinstance(texte, str):
        raise TypeError("texte doit être une chaîne.")
    if not isinstance(referentiel, ReferentielPrepare):
        raise TypeError("referentiel doit être une instance de ReferentielPrepare.")
    if not isinstance(configuration, ConfigurationUtilitaires):
        raise TypeError(
            "configuration doit être une instance de ConfigurationUtilitaires."
        )

    texte_normalise_complet = normaliser(texte)
    texte_normalise = _tronquer(
        texte_normalise_complet,
        configuration.taille_max_texte,
    )
    texte_tronque = len(texte_normalise_complet) > len(texte_normalise)
    caracteres_ignores = (
        len(texte_normalise_complet) - len(texte_normalise)
    )

    elements_detectes: list[str] = []
    mots_detectes: list[str] = []
    correspondances_par_regle: dict[str, list[str]] = {}
    occurrences_par_regle: dict[str, list[OccurrenceExpression]] = {}
    journal: list[TraceRegle] = []

    total_expressions = 0
    total_occurrences = 0
    total_expressions_detectees = 0

    for ordre, regle in enumerate(referentiel.regles, start=1):
        total_expressions += len(regle.expressions)
        correspondances: list[str] = []
        occurrences: list[OccurrenceExpression] = []
        premiere_position: int | None = None
        occurrences_regle = 0

        for expression, expression_normalisee in zip(
            regle.expressions,
            regle.expressions_normalisees,
            strict=True,
        ):
            positions = _positions_expression(
                texte_normalise,
                expression_normalisee,
                configuration.mode_correspondance,
            )
            if not positions:
                continue

            correspondances.append(expression)
            nombre_occurrences = (
                len(positions)
                if configuration.compter_occurrences
                else 1
            )
            position = positions[0]
            occurrences_regle += nombre_occurrences
            total_occurrences += nombre_occurrences
            total_expressions_detectees += 1
            premiere_position = (
                position
                if premiere_position is None
                else min(premiere_position, position)
            )
            occurrences.append(
                {
                    "expression": expression,
                    "expression_normalisee": expression_normalisee,
                    "nombre_occurrences": nombre_occurrences,
                    "premiere_position": position,
                    "derniere_position": positions[-1],
                    "contexte": _extraire_contexte(
                        texte_normalise,
                        position,
                        len(expression_normalisee),
                        configuration.taille_contexte,
                    ),
                }
            )

        declenchee = bool(correspondances)
        if declenchee:
            elements_detectes.append(regle.nom)
            mots_detectes.extend(correspondances)
            correspondances_par_regle[regle.nom] = correspondances
            occurrences_par_regle[regle.nom] = occurrences

        journal.append(
            {
                "ordre": ordre,
                "nom": regle.nom,
                "expressions_evaluees": len(regle.expressions),
                "expressions_detectees": correspondances,
                "nombre_occurrences": occurrences_regle,
                "premiere_position": premiere_position,
                "couverture_expressions": (
                    round(
                        len(correspondances)
                        * 100
                        / len(regle.expressions)
                    )
                    if regle.expressions
                    else 0
                ),
                "rang_detection": None,
                "declenchee": declenchee,
            }
        )

    mots_detectes = dedupliquer(mots_detectes)
    nombre_regles = len(referentiel.regles)
    indice_couverture = (
        round(len(elements_detectes) * 100 / nombre_regles)
        if nombre_regles
        else 0
    )
    niveau_couverture = _niveau_couverture(
        indice_couverture,
        configuration,
    )
    qualite = _qualite_texte(texte_normalise, configuration)
    couverture_expressions = (
        round(total_expressions_detectees * 100 / total_expressions)
        if total_expressions
        else 0
    )
    densite_detection = (
        round(total_occurrences * 1000 / max(1, len(texte_normalise.split())))
    )
    densite_detection = min(100, densite_detection)
    niveau_densite = _niveau_densite(
        densite_detection,
        configuration,
    )

    traces_detectees = sorted(
        (trace for trace in journal if trace["declenchee"]),
        key=lambda trace: (
            trace["premiere_position"]
            if trace["premiere_position"] is not None
            else len(texte_normalise) + 1,
            -trace["nombre_occurrences"],
            trace["ordre"],
        ),
    )
    classement_regles = [trace["nom"] for trace in traces_detectees]
    rangs = {
        trace["nom"]: rang
        for rang, trace in enumerate(traces_detectees, start=1)
    }
    for trace in journal:
        trace["rang_detection"] = rangs.get(trace["nom"])

    alertes: list[str] = []
    if qualite == "vide":
        alertes.append("Le texte analysé est vide.")
    elif qualite == "faible":
        alertes.append("Le texte analysé est très court.")
    if nombre_regles == 0:
        alertes.append("Le référentiel ne contient aucune règle exploitable.")
    if not elements_detectes and texte_normalise:
        alertes.append("Aucune règle n'a été déclenchée.")
    if texte_tronque:
        alertes.append(
            f"Le texte a été tronqué de {caracteres_ignores} caractères."
        )

    configuration_dict = _configuration_dict(configuration)
    corpus_hash = hashlib.sha256(
        texte_normalise.encode("utf-8")
    ).hexdigest()
    entree_hash = _empreinte_json(
        {
            "texte": texte_normalise,
            "texte_tronque": texte_tronque,
            "caracteres_ignores": caracteres_ignores,
        }
    )
    resultat_serialisable = {
        "elements_detectes": elements_detectes,
        "mots_detectes": mots_detectes,
        "correspondances_par_regle": correspondances_par_regle,
        "occurrences_par_regle": occurrences_par_regle,
        "indice_couverture": indice_couverture,
        "niveau_couverture": niveau_couverture,
        "couverture_expressions": couverture_expressions,
        "densite_detection": densite_detection,
        "niveau_densite": niveau_densite,
        "classement_regles": classement_regles,
        "texte_tronque": texte_tronque,
        "caracteres_ignores": caracteres_ignores,
    }
    resultat_hash = _empreinte_json(resultat_serialisable)
    analyse_hash = _empreinte_json(
        {
            "engine_version": ENGINE_VERSION,
            "ruleset_version": RULESET_VERSION,
            "corpus_hash": corpus_hash,
            "entree_hash": entree_hash,
            "referentiel_hash": referentiel.empreinte,
            "configuration": configuration_dict,
            "resultat": resultat_serialisable,
            "journal": journal,
        }
    )

    audit: AuditDetection = {
        "engine_version": ENGINE_VERSION,
        "ruleset_version": RULESET_VERSION,
        "configuration_hash": _empreinte_json(configuration_dict),
        "referentiel_hash": referentiel.empreinte,
        "corpus_hash": corpus_hash,
        "entree_hash": entree_hash,
        "resultat_hash": resultat_hash,
        "analyse_hash": analyse_hash,
        "nombre_regles": nombre_regles,
        "nombre_regles_declenchees": len(elements_detectes),
        "nombre_expressions_evaluees": total_expressions,
        "nombre_expressions_detectees": len(mots_detectes),
        "nombre_occurrences_total": total_occurrences,
        "texte_tronque": texte_tronque,
        "caracteres_ignores": caracteres_ignores,
        "statistiques_cache": _statistiques_cache(),
        "journal": journal,
    }

    return {
        "elements_detectes": elements_detectes,
        "mots_detectes": mots_detectes,
        "correspondances_par_regle": correspondances_par_regle,
        "occurrences_par_regle": occurrences_par_regle,
        "qualite_texte": qualite,
        "longueur_texte_normalise": len(texte_normalise),
        "nombre_mots": len(texte_normalise.split()),
        "indice_couverture": indice_couverture,
        "niveau_couverture": niveau_couverture,
        "couverture_expressions": couverture_expressions,
        "densite_detection": densite_detection,
        "niveau_densite": niveau_densite,
        "classement_regles": classement_regles,
        "texte_tronque": texte_tronque,
        "caracteres_ignores": caracteres_ignores,
        "alertes": alertes,
        "audit": audit,
        "configuration": configuration_dict,
    }


def analyser_regles(
    texte: str,
    regles: Mapping[str, Iterable[str]],
    configuration: ConfigurationUtilitaires = CONFIGURATION_PAR_DEFAUT,
) -> ResultatDetection:
    """Analyse un texte et retourne un résultat stable et auditable."""
    if not isinstance(configuration, ConfigurationUtilitaires):
        raise TypeError(
            "configuration doit être une instance de ConfigurationUtilitaires."
        )

    referentiel = preparer_regles(
        regles,
        refuser_invalides=configuration.refuser_regles_invalides,
    )
    return analyser_regles_preparees(
        texte,
        referentiel,
        configuration,
    )


def analyser_article(
    article: Mapping[str, Any] | None,
    regles: Mapping[str, Iterable[str]] | ReferentielPrepare,
    configuration: ConfigurationUtilitaires = CONFIGURATION_PAR_DEFAUT,
) -> ResultatDetection:
    """Construit le texte d'un article puis exécute la détection."""
    texte = construire_texte(article, configuration)
    referentiel = (
        regles
        if isinstance(regles, ReferentielPrepare)
        else preparer_regles(
            regles,
            refuser_invalides=configuration.refuser_regles_invalides,
        )
    )
    return analyser_regles_preparees(
        texte,
        referentiel,
        configuration,
    )


def detecter_regles(
    texte: str,
    regles: Mapping[str, Iterable[str]],
) -> tuple[list[str], list[str]]:
    """API historique compatible avec la V2."""
    resultat = analyser_regles(
        texte,
        regles,
        CONFIGURATION_PAR_DEFAUT,
    )
    return resultat["elements_detectes"], resultat["mots_detectes"]


__all__ = [
    "AuditDetection",
    "CHAMPS_TEXTE",
    "CONFIGURATION_PAR_DEFAUT",
    "ConfigurationUtilitaires",
    "ENGINE_VERSION",
    "ModeCorrespondance",
    "NiveauCouverture",
    "NiveauDensite",
    "OccurrenceExpression",
    "QualiteTexte",
    "RULESET_VERSION",
    "ReferentielPrepare",
    "ReglePreparee",
    "ResultatDetection",
    "StatistiquesCache",
    "TraceRegle",
    "analyser_article",
    "analyser_regles",
    "analyser_regles_preparees",
    "aplatir_valeur",
    "compiler_expression",
    "construire_texte",
    "contient_expression",
    "dedupliquer",
    "detecter_regles",
    "extraire_champ",
    "normaliser",
    "normaliser_chaine",
    "preparer_regles",
    "valider_regles",
    "vider_caches",
]