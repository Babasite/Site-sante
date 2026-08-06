"""
Pipeline de classification — stabilisation et validation contractuelle V6.

Ce module constitue le contrat commun du moteur de classification. Il décrit
l'ordre officiel des étapes et fournit l'objet d'état unique qui accompagne un
article du début à la fin de son traitement.

Le pipeline connaît l'existence des étapes, leur ordre et leur état
d'exécution. Il ne connaît aucune règle scientifique ou métier. Les calculs
restent exclusivement dans les modules spécialisés :

    categories.py   -> catégories thématiques
    one_health.py   -> dimensions One Health
    preuve.py       -> niveau de preuve
    pertinence.py   -> pertinence
    importance      -> importance de l'article
    score.py        -> score global
    decision.py     -> décision finale
    explication.py  -> explication de la décision

Principes fondamentaux
----------------------

1. Une classification utilise une seule instance d'``EtatClassification``.
2. Chaque module enrichit cet état ; aucun module ne le remplace.
3. Une donnée métier possède un seul producteur officiel.
4. Le pipeline transporte les résultats, mais ne les recalcule jamais.
5. L'ordre des étapes est défini ici et non dans les modules métier.
6. Les diagnostics techniques ne doivent pas modifier la décision métier.
7. À entrée et configuration identiques, le moteur doit rester déterministe.
8. Chaque article reçoit un nouvel état ; un état ne doit pas être recyclé.

Déroulement officiel
--------------------

    préparation
        -> catégories
        -> One Health
        -> preuve
        -> pertinence
        -> importance
        -> score
        -> décision
        -> explication

Portée de la V6
---------------

Cette sixième version stabilise l'API publique de la V5 et ajoute une validation
contractuelle explicite des entrées et sorties de chaque étape. La validation reste
technique : elle vérifie la présence des données déclarées par ``ContratEtape`` sans
interpréter leur valeur scientifique.

La V6 introduit aussi une prévalidation du moteur, des rapports de conformité
sérialisables et une politique configurable de validation bloquante ou informative.
Elle conserve l'exécution partielle, la reprise, la traçabilité et l'indépendance
complète vis-à-vis des modules métier.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from hashlib import sha256
import json
import math
from time import perf_counter_ns
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Final, TypeAlias

from .contexte import ContexteClassification


# ---------------------------------------------------------------------------
# API publique et versions
# ---------------------------------------------------------------------------

VERSION_PIPELINE: Final[str] = "6.0.0"
VERSION_CONTRAT_ETAT: Final[str] = "6"
ALGORITHME_EMPREINTE: Final[str] = "sha256"

NomEtape: TypeAlias = str
DonneesAudit: TypeAlias = dict[str, Any]


# ---------------------------------------------------------------------------
# Sérialisation canonique et empreintes déterministes
# ---------------------------------------------------------------------------

def _normaliser_pour_empreinte(valeur: Any) -> Any:
    """Convertit une valeur en structure JSON stable et indépendante.

    Cette fonction n'introduit ni date, ni durée, ni identité mémoire. Les
    ensembles sont triés, les clés de dictionnaire sont converties en texte et
    les nombres flottants non finis sont représentés explicitement.
    """
    if valeur is None or isinstance(valeur, (bool, int, str)):
        return valeur
    if isinstance(valeur, float):
        if math.isnan(valeur):
            return {"__float__": "nan"}
        if math.isinf(valeur):
            return {"__float__": "inf" if valeur > 0 else "-inf"}
        return valeur
    if isinstance(valeur, bytes):
        return {"__bytes_utf8__": valeur.decode("utf-8", errors="replace")}
    if isinstance(valeur, Enum):
        return _normaliser_pour_empreinte(valeur.value)
    if isinstance(valeur, Mapping):
        return {
            str(cle): _normaliser_pour_empreinte(item)
            for cle, item in sorted(valeur.items(), key=lambda paire: str(paire[0]))
        }
    if isinstance(valeur, (list, tuple)):
        return [_normaliser_pour_empreinte(item) for item in valeur]
    if isinstance(valeur, (set, frozenset)):
        normalisees = [_normaliser_pour_empreinte(item) for item in valeur]
        return sorted(
            normalisees,
            key=lambda item: json.dumps(
                item, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ),
        )
    if hasattr(valeur, "exporter") and callable(valeur.exporter):
        return _normaliser_pour_empreinte(valeur.exporter())
    if hasattr(valeur, "__slots__"):
        return _normaliser_pour_empreinte(
            {
                nom: getattr(valeur, nom)
                for nom in valeur.__slots__
                if isinstance(nom, str) and hasattr(valeur, nom)
            }
        )
    return {"__type__": type(valeur).__qualname__, "__texte__": str(valeur)}


def serialiser_canonique(valeur: Any) -> str:
    """Retourne un JSON canonique utilisé uniquement pour les empreintes."""
    return json.dumps(
        _normaliser_pour_empreinte(valeur),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def calculer_empreinte(valeur: Any) -> str:
    """Calcule l'empreinte SHA-256 hexadécimale d'une valeur canonique."""
    return sha256(serialiser_canonique(valeur).encode("utf-8")).hexdigest()


class EtapeClassification(str, Enum):
    """Noms canoniques des étapes du moteur, dans leur ordre conceptuel."""

    PREPARATION = "preparation"
    CATEGORIES = "categories"
    ONE_HEALTH = "one_health"
    PREUVE = "preuve"
    PERTINENCE = "pertinence"
    IMPORTANCE = "importance"
    SCORE = "score"
    DECISION = "decision"
    EXPLICATION = "explication"


ORDRE_ETAPES: Final[tuple[EtapeClassification, ...]] = tuple(
    EtapeClassification
)

INDEX_ETAPES: Final[dict[EtapeClassification, int]] = {
    etape: index for index, etape in enumerate(ORDRE_ETAPES)
}


def _normaliser_noms(valeurs: Any) -> tuple[str, ...]:
    """Normalise une collection de noms techniques en tuple unique."""
    if valeurs is None:
        return ()
    if isinstance(valeurs, (str, bytes)):
        valeurs = (valeurs,)
    resultat: list[str] = []
    vus: set[str] = set()
    for valeur in valeurs:
        nom = str(valeur or "").strip()
        if not nom:
            raise ValueError("Un nom technique ne peut pas être vide.")
        if nom not in vus:
            vus.add(nom)
            resultat.append(nom)
    return tuple(resultat)


@dataclass(frozen=True, slots=True)
class ContratEtape:
    """Description architecturale immuable d'une étape du moteur.

    Le contrat indique ce que l'étape représente sans contenir son algorithme.
    Il permet au pipeline de valider l'ordre, les dépendances et la propriété
    des données sans importer les modules métier.

    ``module`` désigne le module Python responsable. ``entrees`` et ``sorties``
    utilisent les noms d'attributs du contexte ou de l'état partagé. Ces noms
    sont documentaires en V2 ; leur contrôle automatique sera renforcé lors de
    l'intégration des modules.
    """

    etape: EtapeClassification
    module: str
    description: str
    dependances: tuple[EtapeClassification, ...] = ()
    entrees: tuple[str, ...] = ()
    sorties: tuple[str, ...] = ()
    obligatoire: bool = True

    def __post_init__(self) -> None:
        module = str(self.module or "").strip()
        description = " ".join(str(self.description or "").split())
        if not module:
            raise ValueError("Le module propriétaire d'une étape est obligatoire.")
        if not description:
            raise ValueError("La description d'une étape est obligatoire.")
        if self.etape in self.dependances:
            raise ValueError("Une étape ne peut pas dépendre d'elle-même.")
        if len(set(self.dependances)) != len(self.dependances):
            raise ValueError("Les dépendances d'une étape doivent être uniques.")
        object.__setattr__(self, "module", module)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "entrees", _normaliser_noms(self.entrees))
        object.__setattr__(self, "sorties", _normaliser_noms(self.sorties))

    @property
    def proprietaire(self) -> str:
        """Alias explicite du module qui produit les sorties de l'étape."""
        return self.module

    def exporter(self) -> dict[str, Any]:
        return {
            "etape": self.etape.value,
            "module": self.module,
            "description": self.description,
            "dependances": [item.value for item in self.dependances],
            "entrees": list(self.entrees),
            "sorties": list(self.sorties),
            "obligatoire": self.obligatoire,
        }


CONTRATS_ETAPES: Final[dict[EtapeClassification, ContratEtape]] = {
    EtapeClassification.PREPARATION: ContratEtape(
        etape=EtapeClassification.PREPARATION,
        module="contexte.py",
        description="Prépare et normalise les données communes de l'article.",
        entrees=("article",),
        sorties=("texte",),
    ),
    EtapeClassification.CATEGORIES: ContratEtape(
        etape=EtapeClassification.CATEGORIES,
        module="categories.py",
        description="Détecte les catégories thématiques de l'article.",
        dependances=(EtapeClassification.PREPARATION,),
        entrees=("texte",),
        sorties=("categories", "mots_categories"),
    ),
    EtapeClassification.ONE_HEALTH: ContratEtape(
        etape=EtapeClassification.ONE_HEALTH,
        module="one_health.py",
        description="Détecte les dimensions One Health présentes dans l'article.",
        dependances=(EtapeClassification.PREPARATION,),
        entrees=("texte",),
        sorties=("one_health", "mots_one_health"),
    ),
    EtapeClassification.PREUVE: ContratEtape(
        etape=EtapeClassification.PREUVE,
        module="preuve.py",
        description="Évalue le niveau de preuve associé à l'article.",
        dependances=(EtapeClassification.CATEGORIES, EtapeClassification.ONE_HEALTH),
        entrees=("texte", "categories", "one_health"),
        sorties=("preuve",),
    ),
    EtapeClassification.PERTINENCE: ContratEtape(
        etape=EtapeClassification.PERTINENCE,
        module="pertinence.py",
        description="Évalue la pertinence de l'article pour la surveillance.",
        dependances=(EtapeClassification.PREUVE,),
        entrees=("texte", "categories", "one_health", "preuve"),
        sorties=("pertinence",),
    ),
    EtapeClassification.IMPORTANCE: ContratEtape(
        etape=EtapeClassification.IMPORTANCE,
        module="calculateur_importance",
        description="Évalue l'importance opérationnelle de l'article.",
        dependances=(EtapeClassification.PERTINENCE,),
        entrees=("article", "pertinence"),
        sorties=("importance", "importance_detail"),
    ),
    EtapeClassification.SCORE: ContratEtape(
        etape=EtapeClassification.SCORE,
        module="score.py",
        description="Calcule le score global à partir des résultats précédents.",
        dependances=(
            EtapeClassification.CATEGORIES,
            EtapeClassification.ONE_HEALTH,
            EtapeClassification.PREUVE,
            EtapeClassification.PERTINENCE,
            EtapeClassification.IMPORTANCE,
        ),
        entrees=(
            "categories",
            "one_health",
            "preuve",
            "pertinence",
            "importance",
        ),
        sorties=("score",),
    ),
    EtapeClassification.DECISION: ContratEtape(
        etape=EtapeClassification.DECISION,
        module="decision.py",
        description="Produit la décision finale à partir du score et du contexte.",
        dependances=(EtapeClassification.SCORE,),
        entrees=("score", "integrite_publication"),
        sorties=("decision",),
    ),
    EtapeClassification.EXPLICATION: ContratEtape(
        etape=EtapeClassification.EXPLICATION,
        module="explication.py",
        description="Construit une explication lisible et auditable de la décision.",
        dependances=(EtapeClassification.DECISION,),
        entrees=("decision", "score", "preuve", "pertinence"),
        sorties=("explication",),
    ),
}


def _valider_contrats_etapes() -> None:
    """Vérifie une fois la cohérence du référentiel architectural."""
    if set(CONTRATS_ETAPES) != set(ORDRE_ETAPES):
        raise RuntimeError("Chaque étape officielle doit posséder un contrat unique.")
    sorties: dict[str, EtapeClassification] = {}
    for etape in ORDRE_ETAPES:
        contrat = CONTRATS_ETAPES[etape]
        if contrat.etape is not etape:
            raise RuntimeError("La clé d'un contrat doit correspondre à son étape.")
        for dependance in contrat.dependances:
            if INDEX_ETAPES[dependance] >= INDEX_ETAPES[etape]:
                raise RuntimeError(
                    f"La dépendance {dependance.value!r} doit précéder "
                    f"l'étape {etape.value!r}."
                )
        for sortie in contrat.sorties:
            precedente = sorties.get(sortie)
            if precedente is not None:
                raise RuntimeError(
                    f"La donnée {sortie!r} possède plusieurs producteurs : "
                    f"{precedente.value!r} et {etape.value!r}."
                )
            sorties[sortie] = etape


_valider_contrats_etapes()


class StatutEtape(str, Enum):
    """États techniques possibles d'une étape du pipeline."""

    EN_ATTENTE = "en_attente"
    EN_COURS = "en_cours"
    TERMINEE = "terminee"
    IGNOREE = "ignoree"
    ECHEC = "echec"


class StatutClassification(str, Enum):
    """Cycle de vie global d'une classification."""

    CREEE = "creee"
    EN_COURS = "en_cours"
    TERMINEE = "terminee"
    TERMINEE_AVEC_AVERTISSEMENTS = "terminee_avec_avertissements"
    ECHEC = "echec"


class NiveauDiagnostic(str, Enum):
    """Niveaux techniques utilisables dans le diagnostic du pipeline."""

    INFORMATION = "information"
    AVERTISSEMENT = "avertissement"
    ERREUR = "erreur"


class PolitiqueErreur(str, Enum):
    """Comportement attendu lorsqu'une étape échoue."""

    ARRETER = "arreter"
    CONTINUER = "continuer"


@dataclass(slots=True)
class ConfigurationPipeline:
    """Configuration technique immuable par convention pour une exécution.

    La configuration ne contient aucune règle scientifique. Elle indique
    seulement quelles étapes sont actives et comment le cycle de vie doit être
    validé. Une copie normalisée est créée avec chaque ``EtatClassification``.
    """

    etapes_actives: tuple[EtapeClassification, ...] = ORDRE_ETAPES
    ordre_strict: bool = True
    politique_erreur: PolitiqueErreur = PolitiqueErreur.ARRETER
    valider_contrats: bool = True
    validation_bloquante: bool = False
    exiger_sorties_non_nulles: bool = False
    extensions: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        actives = tuple(normaliser_etape(item) for item in self.etapes_actives)
        if len(set(actives)) != len(actives):
            raise ValueError("Une étape active ne peut être déclarée qu'une fois.")
        actives = tuple(item for item in ORDRE_ETAPES if item in set(actives))
        if not actives:
            raise ValueError("Le pipeline doit contenir au moins une étape active.")
        self.etapes_actives = actives
        if not isinstance(self.politique_erreur, PolitiqueErreur):
            self.politique_erreur = PolitiqueErreur(str(self.politique_erreur))
        self.extensions = deepcopy(dict(self.extensions))
        self._valider_dependances_actives()

    def _valider_dependances_actives(self) -> None:
        actives = set(self.etapes_actives)
        for etape in self.etapes_actives:
            manquantes = [
                dep for dep in CONTRATS_ETAPES[etape].dependances if dep not in actives
            ]
            if manquantes and self.ordre_strict:
                noms = ", ".join(dep.value for dep in manquantes)
                raise ValueError(
                    f"L'étape {etape.value!r} requiert les étapes actives : {noms}."
                )

    def est_active(self, etape: EtapeClassification | str) -> bool:
        return normaliser_etape(etape) in self.etapes_actives

    def exporter(self) -> dict[str, Any]:
        return {
            "etapes_actives": [item.value for item in self.etapes_actives],
            "ordre_strict": self.ordre_strict,
            "politique_erreur": self.politique_erreur.value,
            "valider_contrats": self.valider_contrats,
            "validation_bloquante": self.validation_bloquante,
            "exiger_sorties_non_nulles": self.exiger_sorties_non_nulles,
            "extensions": deepcopy(self.extensions),
        }


@dataclass(frozen=True, slots=True)
class MessageDiagnostic:
    """Message technique immuable produit pendant une classification.

    ``code`` est une clé stable destinée aux tests et aux journaux. ``message``
    est une explication lisible. ``etape`` peut rester absente pour un message
    transversal au pipeline.
    """

    niveau: NiveauDiagnostic
    code: str
    message: str
    etape: EtapeClassification | None = None
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        code = str(self.code or "").strip()
        message = str(self.message or "").strip()
        if not code:
            raise ValueError("Le code d'un diagnostic ne peut pas être vide.")
        if not message:
            raise ValueError("Le message d'un diagnostic ne peut pas être vide.")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "details", deepcopy(dict(self.details)))

    def exporter(self) -> dict[str, Any]:
        """Retourne une représentation indépendante et sérialisable."""
        return {
            "niveau": self.niveau.value,
            "code": self.code,
            "message": self.message,
            "etape": self.etape.value if self.etape else None,
            "details": deepcopy(dict(self.details)),
        }


@dataclass(slots=True)
class DiagnosticPipeline:
    """Collection centralisée des informations, avertissements et erreurs.

    Les diagnostics sont techniques. Ils décrivent l'exécution mais ne doivent
    jamais devenir une seconde source de règles métier.
    """

    messages: list[MessageDiagnostic] = field(default_factory=list)

    def ajouter(
        self,
        niveau: NiveauDiagnostic,
        code: str,
        message: str,
        *,
        etape: EtapeClassification | str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> MessageDiagnostic:
        """Ajoute un message unique et retourne l'objet effectivement stocké."""
        etape_normalisee = normaliser_etape(etape) if etape is not None else None
        nouveau = MessageDiagnostic(
            niveau=niveau,
            code=code,
            message=message,
            etape=etape_normalisee,
            details=details or {},
        )
        if nouveau not in self.messages:
            self.messages.append(nouveau)
        return nouveau

    def information(
        self,
        code: str,
        message: str,
        **kwargs: Any,
    ) -> MessageDiagnostic:
        return self.ajouter(NiveauDiagnostic.INFORMATION, code, message, **kwargs)

    def avertissement(
        self,
        code: str,
        message: str,
        **kwargs: Any,
    ) -> MessageDiagnostic:
        return self.ajouter(NiveauDiagnostic.AVERTISSEMENT, code, message, **kwargs)

    def erreur(
        self,
        code: str,
        message: str,
        **kwargs: Any,
    ) -> MessageDiagnostic:
        return self.ajouter(NiveauDiagnostic.ERREUR, code, message, **kwargs)

    @property
    def a_des_erreurs(self) -> bool:
        return any(m.niveau is NiveauDiagnostic.ERREUR for m in self.messages)

    @property
    def a_des_avertissements(self) -> bool:
        return any(
            m.niveau is NiveauDiagnostic.AVERTISSEMENT for m in self.messages
        )

    def exporter(self) -> dict[str, Any]:
        return {
            "nombre": len(self.messages),
            "erreurs": sum(
                m.niveau is NiveauDiagnostic.ERREUR for m in self.messages
            ),
            "avertissements": sum(
                m.niveau is NiveauDiagnostic.AVERTISSEMENT
                for m in self.messages
            ),
            "messages": [message.exporter() for message in self.messages],
        }


@dataclass(slots=True)
class ExecutionEtape:
    """État d'exécution technique d'une étape unique."""

    etape: EtapeClassification
    statut: StatutEtape = StatutEtape.EN_ATTENTE
    nombre_executions: int = 0
    motif: str = ""

    @property
    def est_finalisee(self) -> bool:
        return self.statut in {
            StatutEtape.TERMINEE,
            StatutEtape.IGNOREE,
            StatutEtape.ECHEC,
        }

    def exporter(self) -> dict[str, Any]:
        return {
            "etape": self.etape.value,
            "statut": self.statut.value,
            "nombre_executions": self.nombre_executions,
            "motif": self.motif,
        }


@dataclass(slots=True)
class ExecutionPipeline:
    """Suivi et validation du cycle de vie technique d'une classification.

    La V2 garantit qu'une étape ne démarre qu'après ses dépendances et, lorsque
    l'ordre strict est actif, après la finalisation de toutes les étapes actives
    qui la précèdent. Cette classe ne lance jamais la logique métier.
    """

    statut: StatutClassification = StatutClassification.CREEE
    etape_courante: EtapeClassification | None = None
    etapes: dict[EtapeClassification, ExecutionEtape] = field(
        default_factory=lambda: {
            etape: ExecutionEtape(etape=etape) for etape in ORDRE_ETAPES
        }
    )

    def __post_init__(self) -> None:
        normalisees: dict[EtapeClassification, ExecutionEtape] = {}
        for etape in ORDRE_ETAPES:
            suivi = self.etapes.get(etape)
            if suivi is None:
                suivi = ExecutionEtape(etape=etape)
            if suivi.etape is not etape:
                raise ValueError("Le suivi d'une étape ne correspond pas à sa clé.")
            normalisees[etape] = suivi
        self.etapes = normalisees

    def obtenir(self, etape: EtapeClassification | str) -> ExecutionEtape:
        return self.etapes[normaliser_etape(etape)]

    def dependances_satisfaites(
        self,
        etape: EtapeClassification | str,
    ) -> bool:
        cible = normaliser_etape(etape)
        return all(
            self.etapes[dependance].statut
            in {StatutEtape.TERMINEE, StatutEtape.IGNOREE}
            for dependance in CONTRATS_ETAPES[cible].dependances
        )

    def dependances_manquantes(
        self,
        etape: EtapeClassification | str,
    ) -> tuple[EtapeClassification, ...]:
        cible = normaliser_etape(etape)
        return tuple(
            dependance
            for dependance in CONTRATS_ETAPES[cible].dependances
            if self.etapes[dependance].statut
            not in {StatutEtape.TERMINEE, StatutEtape.IGNOREE}
        )

    def peut_demarrer(
        self,
        etape: EtapeClassification | str,
        *,
        configuration: ConfigurationPipeline | None = None,
    ) -> tuple[bool, str]:
        """Retourne une décision technique et son motif sans modifier l'état."""
        cible = normaliser_etape(etape)
        config = configuration or ConfigurationPipeline()
        suivi = self.obtenir(cible)

        if cible not in config.etapes_actives:
            return False, f"L'étape {cible.value!r} n'est pas active."
        if self.statut in {
            StatutClassification.TERMINEE,
            StatutClassification.TERMINEE_AVEC_AVERTISSEMENTS,
            StatutClassification.ECHEC,
        }:
            return False, "La classification est déjà finalisée."
        if self.etape_courante is not None:
            return False, f"L'étape {self.etape_courante.value!r} est déjà active."
        if suivi.est_finalisee:
            return False, f"L'étape {cible.value!r} est déjà finalisée."

        manquantes = self.dependances_manquantes(cible)
        if manquantes:
            noms = ", ".join(item.value for item in manquantes)
            return False, f"Dépendances non finalisées : {noms}."

        if config.ordre_strict:
            for precedente in config.etapes_actives:
                if precedente is cible:
                    break
                if not self.etapes[precedente].est_finalisee:
                    return (
                        False,
                        f"L'étape précédente {precedente.value!r} n'est pas finalisée.",
                    )
        return True, ""

    def demarrer(
        self,
        etape: EtapeClassification | str,
        *,
        configuration: ConfigurationPipeline | None = None,
    ) -> ExecutionEtape:
        """Marque une étape comme active après validation de sa transition."""
        cible = normaliser_etape(etape)
        autorisee, motif = self.peut_demarrer(cible, configuration=configuration)
        if not autorisee:
            raise RuntimeError(motif)
        suivi = self.obtenir(cible)
        suivi.statut = StatutEtape.EN_COURS
        suivi.nombre_executions += 1
        suivi.motif = ""
        self.etape_courante = cible
        self.statut = StatutClassification.EN_COURS
        return suivi

    def terminer(self, etape: EtapeClassification | str) -> ExecutionEtape:
        cible = self._exiger_etape_courante(etape)
        cible.statut = StatutEtape.TERMINEE
        cible.motif = ""
        self.etape_courante = None
        return cible

    def ignorer(
        self,
        etape: EtapeClassification | str,
        *,
        motif: str,
        configuration: ConfigurationPipeline | None = None,
    ) -> ExecutionEtape:
        cible = normaliser_etape(etape)
        suivi = self.obtenir(cible)
        config = configuration or ConfigurationPipeline()
        motif_propre = " ".join(str(motif or "").split())
        if not motif_propre:
            raise ValueError("Le motif d'une étape ignorée ne peut pas être vide.")
        if cible not in config.etapes_actives:
            raise RuntimeError(f"L'étape {cible.value!r} n'est pas active.")
        if suivi.statut is StatutEtape.EN_COURS:
            raise RuntimeError("Une étape en cours ne peut pas être ignorée.")
        if suivi.est_finalisee:
            raise RuntimeError(f"L'étape {cible.value!r} est déjà finalisée.")
        if CONTRATS_ETAPES[cible].obligatoire and config.ordre_strict:
            raise RuntimeError(
                f"L'étape obligatoire {cible.value!r} ne peut pas être ignorée "
                "en mode strict."
            )
        suivi.statut = StatutEtape.IGNOREE
        suivi.motif = motif_propre
        return suivi

    def echouer(
        self,
        etape: EtapeClassification | str,
        *,
        motif: str,
        configuration: ConfigurationPipeline | None = None,
    ) -> ExecutionEtape:
        cible = self._exiger_etape_courante(etape)
        motif_propre = " ".join(str(motif or "").split())
        if not motif_propre:
            raise ValueError("Le motif d'un échec ne peut pas être vide.")
        cible.statut = StatutEtape.ECHEC
        cible.motif = motif_propre
        self.etape_courante = None
        config = configuration or ConfigurationPipeline()
        if config.politique_erreur is PolitiqueErreur.ARRETER:
            self.statut = StatutClassification.ECHEC
        else:
            self.statut = StatutClassification.EN_COURS
        return cible

    def finaliser(
        self,
        *,
        configuration: ConfigurationPipeline | None = None,
        avec_avertissements: bool = False,
    ) -> None:
        config = configuration or ConfigurationPipeline()
        if self.etape_courante is not None:
            raise RuntimeError("Impossible de finaliser pendant une étape active.")
        echecs = [
            item
            for item in config.etapes_actives
            if self.etapes[item].statut is StatutEtape.ECHEC
        ]
        if echecs:
            self.statut = StatutClassification.ECHEC
            return
        non_finalisees = [
            item
            for item in config.etapes_actives
            if not self.etapes[item].est_finalisee
        ]
        if non_finalisees:
            noms = ", ".join(item.value for item in non_finalisees)
            raise RuntimeError(f"Étapes actives non finalisées : {noms}.")
        self.statut = (
            StatutClassification.TERMINEE_AVEC_AVERTISSEMENTS
            if avec_avertissements
            else StatutClassification.TERMINEE
        )

    def _exiger_etape_courante(
        self,
        etape: EtapeClassification | str,
    ) -> ExecutionEtape:
        cible = self.obtenir(etape)
        if self.etape_courante is not cible.etape:
            attendue = self.etape_courante.value if self.etape_courante else "aucune"
            raise RuntimeError(
                f"L'étape active est {attendue!r}, pas {cible.etape.value!r}."
            )
        return cible

    @property
    def etapes_terminees(self) -> tuple[EtapeClassification, ...]:
        return tuple(
            etape
            for etape in ORDRE_ETAPES
            if self.etapes[etape].statut is StatutEtape.TERMINEE
        )

    @property
    def etapes_finalisees(self) -> tuple[EtapeClassification, ...]:
        return tuple(
            etape for etape in ORDRE_ETAPES if self.etapes[etape].est_finalisee
        )

    def exporter(self) -> dict[str, Any]:
        return {
            "statut": self.statut.value,
            "etape_courante": (
                self.etape_courante.value if self.etape_courante else None
            ),
            "etapes": [self.etapes[etape].exporter() for etape in ORDRE_ETAPES],
        }


@dataclass(slots=True)
class MetriquesEtape:
    """Mesures techniques d'une étape, sans influence sur le résultat métier."""

    etape: EtapeClassification
    nombre_demarrages: int = 0
    nombre_succes: int = 0
    nombre_echecs: int = 0
    nombre_ignorances: int = 0
    duree_totale_ns: int = 0
    derniere_duree_ns: int | None = None

    @property
    def duree_totale_ms(self) -> float:
        return self.duree_totale_ns / 1_000_000

    def exporter(self) -> dict[str, Any]:
        return {
            "etape": self.etape.value,
            "nombre_demarrages": self.nombre_demarrages,
            "nombre_succes": self.nombre_succes,
            "nombre_echecs": self.nombre_echecs,
            "nombre_ignorances": self.nombre_ignorances,
            "duree_totale_ns": self.duree_totale_ns,
            "duree_totale_ms": self.duree_totale_ms,
            "derniere_duree_ns": self.derniere_duree_ns,
        }


@dataclass(slots=True)
class MetriquesPipeline:
    """Observabilité locale du pipeline fondée sur une horloge monotone."""

    etapes: dict[EtapeClassification, MetriquesEtape] = field(
        default_factory=lambda: {
            etape: MetriquesEtape(etape=etape) for etape in ORDRE_ETAPES
        }
    )
    _demarrages_ns: dict[EtapeClassification, int] = field(
        default_factory=dict, repr=False
    )

    def __post_init__(self) -> None:
        self.etapes = {
            etape: self.etapes.get(etape, MetriquesEtape(etape=etape))
            for etape in ORDRE_ETAPES
        }

    def demarrer(self, etape: EtapeClassification | str) -> None:
        cible = normaliser_etape(etape)
        if cible in self._demarrages_ns:
            raise RuntimeError(f"Les métriques de {cible.value!r} sont déjà actives.")
        self.etapes[cible].nombre_demarrages += 1
        self._demarrages_ns[cible] = perf_counter_ns()

    def _arreter(self, etape: EtapeClassification | str) -> int:
        cible = normaliser_etape(etape)
        debut = self._demarrages_ns.pop(cible, None)
        if debut is None:
            raise RuntimeError(f"Aucune mesure active pour l'étape {cible.value!r}.")
        duree = max(0, perf_counter_ns() - debut)
        mesure = self.etapes[cible]
        mesure.derniere_duree_ns = duree
        mesure.duree_totale_ns += duree
        return duree

    def terminer(self, etape: EtapeClassification | str) -> int:
        cible = normaliser_etape(etape)
        duree = self._arreter(cible)
        self.etapes[cible].nombre_succes += 1
        return duree

    def echouer(self, etape: EtapeClassification | str) -> int:
        cible = normaliser_etape(etape)
        duree = self._arreter(cible)
        self.etapes[cible].nombre_echecs += 1
        return duree

    def ignorer(self, etape: EtapeClassification | str) -> None:
        cible = normaliser_etape(etape)
        self.etapes[cible].nombre_ignorances += 1

    @property
    def duree_totale_ns(self) -> int:
        return sum(item.duree_totale_ns for item in self.etapes.values())

    def exporter(self) -> dict[str, Any]:
        return {
            "horloge": "perf_counter_ns",
            "mesures_actives": [item.value for item in self._demarrages_ns],
            "duree_totale_ns": self.duree_totale_ns,
            "duree_totale_ms": self.duree_totale_ns / 1_000_000,
            "etapes": [self.etapes[item].exporter() for item in ORDRE_ETAPES],
        }


@dataclass(slots=True)
class EmpreintesPipeline:
    """Empreintes déterministes permettant de comparer et vérifier une exécution."""

    algorithme: str = ALGORITHME_EMPREINTE
    entree: str = ""
    configuration: str = ""
    referentiel: str = ""
    resultat: str = ""
    audit: str = ""

    def initialiser(
        self,
        *,
        entree: Any,
        configuration: Any,
        referentiel: Any,
    ) -> None:
        self.entree = calculer_empreinte(entree)
        self.configuration = calculer_empreinte(configuration)
        self.referentiel = calculer_empreinte(referentiel)

    def finaliser(self, *, resultat: Any, audit: Any) -> None:
        self.resultat = calculer_empreinte(resultat)
        self.audit = calculer_empreinte(audit)

    @property
    def est_initialisee(self) -> bool:
        return bool(self.entree and self.configuration and self.referentiel)

    @property
    def est_finalisee(self) -> bool:
        return bool(self.resultat and self.audit)

    def exporter(self) -> dict[str, Any]:
        return {
            "algorithme": self.algorithme,
            "entree": self.entree,
            "configuration": self.configuration,
            "referentiel": self.referentiel,
            "resultat": self.resultat,
            "audit": self.audit,
        }


@dataclass(slots=True)
class AuditPipeline:
    """Journal déterministe chaîné des événements techniques du pipeline V3."""

    version_pipeline: str = VERSION_PIPELINE
    version_contrat_etat: str = VERSION_CONTRAT_ETAT
    evenements: list[DonneesAudit] = field(default_factory=list)

    def enregistrer(
        self,
        evenement: str,
        *,
        etape: EtapeClassification | str | None = None,
        donnees: Mapping[str, Any] | None = None,
    ) -> None:
        nom = str(evenement or "").strip()
        if not nom:
            raise ValueError("Le nom d'un événement d'audit ne peut pas être vide.")
        etape_normalisee = normaliser_etape(etape) if etape is not None else None
        precedente = (
            self.evenements[-1]["empreinte"] if self.evenements else "0" * 64
        )
        contenu = {
            "index": len(self.evenements),
            "evenement": nom,
            "etape": etape_normalisee.value if etape_normalisee else None,
            "donnees": deepcopy(dict(donnees or {})),
            "empreinte_precedente": precedente,
        }
        contenu["empreinte"] = calculer_empreinte(contenu)
        self.evenements.append(contenu)

    def verifier_integrite(self) -> bool:
        precedente = "0" * 64
        for index, evenement in enumerate(self.evenements):
            copie = deepcopy(evenement)
            empreinte_attendue = copie.pop("empreinte", "")
            if copie.get("index") != index:
                return False
            if copie.get("empreinte_precedente") != precedente:
                return False
            if calculer_empreinte(copie) != empreinte_attendue:
                return False
            precedente = empreinte_attendue
        return True

    @property
    def empreinte_finale(self) -> str:
        return self.evenements[-1]["empreinte"] if self.evenements else "0" * 64

    def exporter(self) -> dict[str, Any]:
        return {
            "version_pipeline": self.version_pipeline,
            "version_contrat_etat": self.version_contrat_etat,
            "integrite_valide": self.verifier_integrite(),
            "empreinte_finale": self.empreinte_finale,
            "evenements": deepcopy(self.evenements),
        }



# ---------------------------------------------------------------------------
# Registre des exécutants et orchestration effective
# ---------------------------------------------------------------------------

ExecutantEtape: TypeAlias = Callable[["EtatClassification"], Any]


class ErreurOrchestration(RuntimeError):
    """Erreur technique levée par le moteur d'orchestration.

    L'exception conserve l'étape concernée et la cause d'origine sans exposer
    de décision métier au pipeline.
    """

    def __init__(
        self,
        message: str,
        *,
        etape: EtapeClassification | str | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(str(message))
        self.etape = normaliser_etape(etape) if etape is not None else None
        self.cause = cause


@dataclass(frozen=True, slots=True)
class ComposantEtape:
    """Association immuable entre une étape officielle et son exécutant.

    ``executant`` doit accepter une unique instance d'``EtatClassification``.
    Sa valeur de retour est informative : le moteur ne remplace jamais l'état
    partagé par cette valeur.
    """

    etape: EtapeClassification
    executant: ExecutantEtape
    nom: str = ""
    version: str = ""
    description: str = ""

    def __post_init__(self) -> None:
        if not callable(self.executant):
            raise TypeError("L'exécutant d'une étape doit être appelable.")
        nom = str(self.nom or getattr(self.executant, "__qualname__", "")).strip()
        version = str(self.version or "").strip()
        description = " ".join(str(self.description or "").split())
        if not nom:
            raise ValueError("Le nom d'un composant d'étape ne peut pas être vide.")
        object.__setattr__(self, "nom", nom)
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "description", description)

    def exporter(self) -> dict[str, Any]:
        """Exporte uniquement les métadonnées, jamais l'objet appelable."""
        return {
            "etape": self.etape.value,
            "nom": self.nom,
            "version": self.version,
            "description": self.description,
            "module": getattr(self.executant, "__module__", ""),
        }


@dataclass(slots=True)
class RegistreEtapes:
    """Registre explicite des implémentations métier du pipeline.

    Le registre est volontairement distinct de ``CONTRATS_ETAPES`` : le contrat
    décrit l'architecture stable, tandis que le registre contient les fonctions
    concrètes choisies par l'application au moment de la composition.
    """

    composants: dict[EtapeClassification, ComposantEtape] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        normalises: dict[EtapeClassification, ComposantEtape] = {}
        for etape, composant in self.composants.items():
            cible = normaliser_etape(etape)
            if not isinstance(composant, ComposantEtape):
                raise TypeError("Chaque entrée du registre doit être un ComposantEtape.")
            if composant.etape is not cible:
                raise ValueError("La clé du registre doit correspondre à son composant.")
            normalises[cible] = composant
        self.composants = normalises

    def enregistrer(
        self,
        etape: EtapeClassification | str,
        executant: ExecutantEtape,
        *,
        nom: str = "",
        version: str = "",
        description: str = "",
        remplacer: bool = False,
    ) -> ComposantEtape:
        cible = normaliser_etape(etape)
        if cible in self.composants and not remplacer:
            raise ValueError(f"Un exécutant est déjà enregistré pour {cible.value!r}.")
        composant = ComposantEtape(
            etape=cible,
            executant=executant,
            nom=nom,
            version=version,
            description=description,
        )
        self.composants[cible] = composant
        return composant

    def retirer(self, etape: EtapeClassification | str) -> ComposantEtape:
        cible = normaliser_etape(etape)
        try:
            return self.composants.pop(cible)
        except KeyError as erreur:
            raise KeyError(f"Aucun exécutant enregistré pour {cible.value!r}.") from erreur

    def obtenir(self, etape: EtapeClassification | str) -> ComposantEtape:
        cible = normaliser_etape(etape)
        try:
            return self.composants[cible]
        except KeyError as erreur:
            raise KeyError(f"Aucun exécutant enregistré pour {cible.value!r}.") from erreur

    def contient(self, etape: EtapeClassification | str) -> bool:
        return normaliser_etape(etape) in self.composants

    def manquants(
        self,
        configuration: ConfigurationPipeline | None = None,
    ) -> tuple[EtapeClassification, ...]:
        config = configuration or ConfigurationPipeline()
        return tuple(
            etape for etape in config.etapes_actives if etape not in self.composants
        )

    def valider(
        self,
        configuration: ConfigurationPipeline | None = None,
        *,
        exiger_complet: bool = True,
    ) -> tuple[EtapeClassification, ...]:
        manquants = self.manquants(configuration)
        if manquants and exiger_complet:
            noms = ", ".join(etape.value for etape in manquants)
            raise ErreurOrchestration(f"Exécutants manquants : {noms}.")
        return manquants

    def exporter(self) -> dict[str, Any]:
        return {
            "nombre": len(self.composants),
            "composants": [
                self.composants[etape].exporter()
                for etape in ORDRE_ETAPES
                if etape in self.composants
            ],
        }


@dataclass(frozen=True, slots=True)
class IncidentExecution:
    """Description sérialisable d'un incident rencontré par l'orchestrateur."""

    etape: EtapeClassification
    type_exception: str
    message: str

    def exporter(self) -> dict[str, str]:
        return {
            "etape": self.etape.value,
            "type_exception": self.type_exception,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ViolationContrat:
    """Écart technique entre un état et le contrat déclaré d'une étape."""

    etape: EtapeClassification
    phase: str
    donnee: str
    message: str

    def exporter(self) -> dict[str, str]:
        return {
            "etape": self.etape.value,
            "phase": self.phase,
            "donnee": self.donnee,
            "message": self.message,
        }


@dataclass(slots=True)
class RapportValidation:
    """Rapport sérialisable de validation contractuelle."""

    violations: list[ViolationContrat] = field(default_factory=list)

    @property
    def est_valide(self) -> bool:
        return not self.violations

    def ajouter(self, violation: ViolationContrat) -> None:
        if violation not in self.violations:
            self.violations.append(violation)

    def exporter(self) -> dict[str, Any]:
        return {
            "est_valide": self.est_valide,
            "nombre_violations": len(self.violations),
            "violations": [item.exporter() for item in self.violations],
        }


def _resoudre_donnee(etat: "EtatClassification", nom: str) -> tuple[bool, Any]:
    if hasattr(etat, nom):
        return True, getattr(etat, nom)
    if hasattr(etat.contexte, nom):
        return True, getattr(etat.contexte, nom)
    return False, None


def valider_contrat_etape(
    etat: "EtatClassification",
    etape: EtapeClassification | str,
    *,
    phase: str = "entrees",
) -> RapportValidation:
    """Vérifie la présence des données déclarées, sans règle métier."""
    cible = normaliser_etape(etape)
    if phase not in {"entrees", "sorties"}:
        raise ValueError("phase doit valoir 'entrees' ou 'sorties'.")
    noms = getattr(CONTRATS_ETAPES[cible], phase)
    rapport = RapportValidation()
    for nom in noms:
        existe, valeur = _resoudre_donnee(etat, nom)
        if not existe:
            rapport.ajouter(ViolationContrat(
                cible, phase, nom,
                f"La donnée contractuelle {nom!r} est absente de l'état et du contexte.",
            ))
        elif phase == "sorties" and etat.configuration.exiger_sorties_non_nulles and valeur is None:
            rapport.ajouter(ViolationContrat(
                cible, phase, nom,
                f"La sortie contractuelle {nom!r} ne peut pas être nulle.",
            ))
    return rapport


@dataclass(frozen=True, slots=True)
class PlanExecution:
    """Sélection immuable des étapes à traiter lors d'un passage du moteur.

    ``demandees`` contient les étapes explicitement visées par l'appelant.
    ``planifiees`` contient ces étapes plus, si demandé, leurs dépendances actives.
    Le plan respecte toujours l'ordre officiel du pipeline.
    """

    demandees: tuple[EtapeClassification, ...]
    planifiees: tuple[EtapeClassification, ...]
    dependances_ajoutees: tuple[EtapeClassification, ...] = ()
    finaliser: bool = False

    def __post_init__(self) -> None:
        if not self.demandees:
            raise ValueError("Un plan d'exécution doit demander au moins une étape.")
        if not self.planifiees:
            raise ValueError("Un plan d'exécution doit planifier au moins une étape.")
        if not set(self.demandees).issubset(self.planifiees):
            raise ValueError("Toutes les étapes demandées doivent être planifiées.")
        ordre = tuple(item for item in ORDRE_ETAPES if item in set(self.planifiees))
        if ordre != self.planifiees:
            raise ValueError("Les étapes planifiées doivent respecter l'ordre officiel.")

    def exporter(self) -> dict[str, Any]:
        return {
            "demandees": [item.value for item in self.demandees],
            "planifiees": [item.value for item in self.planifiees],
            "dependances_ajoutees": [
                item.value for item in self.dependances_ajoutees
            ],
            "finaliser": self.finaliser,
        }


def construire_plan_execution(
    configuration: ConfigurationPipeline,
    *,
    debut: EtapeClassification | str | None = None,
    fin: EtapeClassification | str | None = None,
    etapes: tuple[EtapeClassification | str, ...] | list[EtapeClassification | str] | None = None,
    inclure_dependances: bool = True,
    finaliser: bool | None = None,
) -> PlanExecution:
    """Construit un plan cohérent à partir d'une plage ou d'une liste d'étapes.

    ``etapes`` est exclusif avec ``debut`` et ``fin``. Sans sélection explicite,
    toutes les étapes actives sont demandées. Les dépendances sont ajoutées de
    manière transitive lorsqu'``inclure_dependances`` vaut ``True``.
    """
    if not isinstance(configuration, ConfigurationPipeline):
        raise TypeError("configuration doit être une instance de ConfigurationPipeline.")
    if etapes is not None and (debut is not None or fin is not None):
        raise ValueError("etapes ne peut pas être combiné avec debut ou fin.")

    actives = configuration.etapes_actives
    if etapes is not None:
        normalisees = tuple(normaliser_etape(item) for item in etapes)
        if not normalisees:
            raise ValueError("La sélection d'étapes ne peut pas être vide.")
        if len(set(normalisees)) != len(normalisees):
            raise ValueError("Une étape ne peut être demandée qu'une fois.")
        hors_configuration = [item for item in normalisees if item not in actives]
        if hors_configuration:
            noms = ", ".join(item.value for item in hors_configuration)
            raise ValueError(f"Étapes non actives demandées : {noms}.")
        demandees = tuple(item for item in actives if item in set(normalisees))
    else:
        debut_normalise = normaliser_etape(debut) if debut is not None else actives[0]
        fin_normalisee = normaliser_etape(fin) if fin is not None else actives[-1]
        if debut_normalise not in actives or fin_normalisee not in actives:
            raise ValueError("Les bornes d'exécution doivent être des étapes actives.")
        debut_index = actives.index(debut_normalise)
        fin_index = actives.index(fin_normalisee)
        if debut_index > fin_index:
            raise ValueError("L'étape de début doit précéder l'étape de fin.")
        demandees = actives[debut_index : fin_index + 1]

    planifiees_set = set(demandees)
    if inclure_dependances:
        pile = list(demandees)
        while pile:
            cible = pile.pop()
            for dependance in CONTRATS_ETAPES[cible].dependances:
                if dependance in actives and dependance not in planifiees_set:
                    planifiees_set.add(dependance)
                    pile.append(dependance)

    planifiees = tuple(item for item in actives if item in planifiees_set)
    dependances_ajoutees = tuple(item for item in planifiees if item not in demandees)
    finalisation = (
        set(planifiees) == set(actives)
        if finaliser is None
        else bool(finaliser)
    )
    return PlanExecution(
        demandees=demandees,
        planifiees=planifiees,
        dependances_ajoutees=dependances_ajoutees,
        finaliser=finalisation,
    )


@dataclass(slots=True)
class RapportOrchestration:
    """Compte rendu d'un passage du moteur, séparé de l'état métier partagé."""

    plan: PlanExecution
    executees: list[EtapeClassification] = field(default_factory=list)
    deja_finalisees: list[EtapeClassification] = field(default_factory=list)
    bloquees: list[EtapeClassification] = field(default_factory=list)
    hors_plan: list[EtapeClassification] = field(default_factory=list)
    incidents: list[IncidentExecution] = field(default_factory=list)
    reprise: bool = False
    finalisation_effectuee: bool = False

    @property
    def finalisation_demandee(self) -> bool:
        return self.plan.finaliser

    @property
    def a_echoue(self) -> bool:
        return bool(self.incidents)

    def exporter(self) -> dict[str, Any]:
        return {
            "plan": self.plan.exporter(),
            "executees": [item.value for item in self.executees],
            "deja_finalisees": [item.value for item in self.deja_finalisees],
            "bloquees": [item.value for item in self.bloquees],
            "hors_plan": [item.value for item in self.hors_plan],
            "incidents": [item.exporter() for item in self.incidents],
            "reprise": self.reprise,
            "finalisation_demandee": self.finalisation_demandee,
            "finalisation_effectuee": self.finalisation_effectuee,
            "a_echoue": self.a_echoue,
        }


@dataclass(slots=True)
class MoteurPipeline:
    """Orchestrateur déterministe, partiel et reprenable des étapes enregistrées."""

    registre: RegistreEtapes = field(default_factory=RegistreEtapes)
    exiger_registre_complet: bool = True

    def enregistrer(
        self,
        etape: EtapeClassification | str,
        executant: ExecutantEtape,
        **metadonnees: Any,
    ) -> ComposantEtape:
        return self.registre.enregistrer(etape, executant, **metadonnees)

    def prevalider(
        self,
        etat: "EtatClassification",
        *,
        etapes: tuple[EtapeClassification, ...] | None = None,
    ) -> RapportValidation:
        """Valide le registre et les entrées disponibles avant exécution."""
        if not isinstance(etat, EtatClassification):
            raise TypeError("etat doit être une instance de EtatClassification.")
        cibles = etapes or etat.configuration.etapes_actives
        configuration = ConfigurationPipeline(
            etapes_actives=cibles,
            ordre_strict=etat.configuration.ordre_strict,
            politique_erreur=etat.configuration.politique_erreur,
            valider_contrats=etat.configuration.valider_contrats,
            validation_bloquante=etat.configuration.validation_bloquante,
            exiger_sorties_non_nulles=etat.configuration.exiger_sorties_non_nulles,
            extensions=etat.configuration.extensions,
        )
        self.registre.valider(configuration, exiger_complet=self.exiger_registre_complet)
        rapport = RapportValidation()
        if etat.configuration.valider_contrats:
            for cible in cibles:
                for violation in valider_contrat_etape(etat, cible, phase="entrees").violations:
                    rapport.ajouter(violation)
        return rapport

    def executer(
        self,
        etat: "EtatClassification",
        *,
        debut: EtapeClassification | str | None = None,
        fin: EtapeClassification | str | None = None,
        etapes: tuple[EtapeClassification | str, ...] | list[EtapeClassification | str] | None = None,
        inclure_dependances: bool = True,
        finaliser: bool | None = None,
    ) -> RapportOrchestration:
        """Exécute un plan complet ou partiel sur un état non finalisé.

        Un état déjà partiellement exécuté est repris sans rejouer les étapes
        finalisées. Une classification totalement finalisée reste immuable.
        """
        if not isinstance(etat, EtatClassification):
            raise TypeError("etat doit être une instance de EtatClassification.")
        if etat.est_finalisee:
            raise ErreurOrchestration("Une classification finalisée ne peut être rejouée.")
        if etat.execution.etape_courante is not None:
            raise ErreurOrchestration(
                "Une orchestration ne peut pas commencer pendant une étape active.",
                etape=etat.execution.etape_courante,
            )

        plan = construire_plan_execution(
            etat.configuration,
            debut=debut,
            fin=fin,
            etapes=etapes,
            inclure_dependances=inclure_dependances,
            finaliser=finaliser,
        )
        reprise = bool(etat.execution.etapes_finalisees)
        rapport = RapportOrchestration(plan=plan, reprise=reprise)
        rapport.hors_plan.extend(
            item
            for item in etat.configuration.etapes_actives
            if item not in plan.planifiees
        )

        configuration_plan = ConfigurationPipeline(
            etapes_actives=plan.planifiees,
            ordre_strict=etat.configuration.ordre_strict,
            politique_erreur=etat.configuration.politique_erreur,
            valider_contrats=etat.configuration.valider_contrats,
            validation_bloquante=etat.configuration.validation_bloquante,
            exiger_sorties_non_nulles=etat.configuration.exiger_sorties_non_nulles,
            extensions=etat.configuration.extensions,
        )
        manquants = self.registre.valider(
            configuration_plan,
            exiger_complet=self.exiger_registre_complet,
        )
        etat.audit.enregistrer(
            "orchestration_demarree",
            donnees={
                "plan": plan.exporter(),
                "reprise": reprise,
                "registre": self.registre.exporter(),
                "executants_manquants": [item.value for item in manquants],
            },
        )

        for etape in plan.planifiees:
            suivi = etat.execution.obtenir(etape)
            if suivi.est_finalisee:
                rapport.deja_finalisees.append(etape)
                continue

            dependances = etat.execution.dependances_manquantes(etape)
            if dependances:
                rapport.bloquees.append(etape)
                etat.audit.enregistrer(
                    "etape_bloquee",
                    etape=etape,
                    donnees={"dependances": [item.value for item in dependances]},
                )
                continue

            composant = self.registre.composants.get(etape)
            if composant is None:
                incident = self._echouer_sans_executant(etat, etape)
                rapport.incidents.append(incident)
                if etat.configuration.politique_erreur is PolitiqueErreur.ARRETER:
                    break
                continue

            if etat.configuration.valider_contrats:
                validation_entrees = valider_contrat_etape(etat, etape, phase="entrees")
                for violation in validation_entrees.violations:
                    etat.ajouter_avertissement(
                        violation.message,
                        code="pipeline.contrat_entree",
                        etape=etape,
                        details=violation.exporter(),
                    )
                if validation_entrees.violations and etat.configuration.validation_bloquante:
                    incident = self._echouer_validation(etat, etape, validation_entrees)
                    rapport.incidents.append(incident)
                    if etat.configuration.politique_erreur is PolitiqueErreur.ARRETER:
                        break
                    continue

            etat.demarrer_etape(etape)
            try:
                valeur_retour = composant.executant(etat)
                if isinstance(valeur_retour, EtatClassification) and valeur_retour is not etat:
                    raise ErreurOrchestration(
                        "Un exécutant ne peut pas remplacer l'état partagé.",
                        etape=etape,
                    )
            except Exception as erreur:  # frontière volontaire de l'orchestrateur
                message = self._message_exception(erreur)
                etat.echouer_etape(
                    etape,
                    motif=message,
                    code="pipeline.execution_exception",
                )
                rapport.incidents.append(
                    IncidentExecution(
                        etape=etape,
                        type_exception=type(erreur).__qualname__,
                        message=message,
                    )
                )
                if etat.configuration.politique_erreur is PolitiqueErreur.ARRETER:
                    break
            else:
                validation_sorties = (
                    valider_contrat_etape(etat, etape, phase="sorties")
                    if etat.configuration.valider_contrats
                    else RapportValidation()
                )
                for violation in validation_sorties.violations:
                    etat.ajouter_avertissement(
                        violation.message,
                        code="pipeline.contrat_sortie",
                        etape=etape,
                        details=violation.exporter(),
                    )
                if validation_sorties.violations and etat.configuration.validation_bloquante:
                    message = "; ".join(v.message for v in validation_sorties.violations)
                    etat.echouer_etape(etape, motif=message, code="pipeline.validation_sortie")
                    rapport.incidents.append(IncidentExecution(
                        etape=etape,
                        type_exception="ViolationContrat",
                        message=message,
                    ))
                    if etat.configuration.politique_erreur is PolitiqueErreur.ARRETER:
                        break
                    continue
                etat.terminer_etape(etape)
                rapport.executees.append(etape)
                etat.audit.enregistrer(
                    "executant_termine",
                    etape=etape,
                    donnees={
                        "nom": composant.nom,
                        "version": composant.version,
                        "type_retour": type(valeur_retour).__qualname__,
                    },
                )

        etat.audit.enregistrer(
            "orchestration_terminee",
            donnees={
                "rapport": rapport.exporter(),
                "statut_avant_finalisation": etat.execution.statut.value,
            },
        )

        if plan.finaliser:
            restantes = [
                item
                for item in etat.configuration.etapes_actives
                if not etat.execution.obtenir(item).est_finalisee
            ]
            if restantes:
                noms = ", ".join(item.value for item in restantes)
                raise ErreurOrchestration(
                    f"Finalisation impossible, étapes non finalisées : {noms}."
                )
            etat.finaliser()
            rapport.finalisation_effectuee = True
        return rapport

    def reprendre(
        self,
        etat: "EtatClassification",
        **options: Any,
    ) -> RapportOrchestration:
        """Alias explicite d'``executer`` pour reprendre un état partiel."""
        return self.executer(etat, **options)

    def executer_article(
        self,
        article: Mapping[str, Any],
        *,
        texte: str = "",
        configuration: ConfigurationPipeline | None = None,
        debut: EtapeClassification | str | None = None,
        fin: EtapeClassification | str | None = None,
        etapes: tuple[EtapeClassification | str, ...] | list[EtapeClassification | str] | None = None,
        inclure_dependances: bool = True,
        finaliser: bool | None = None,
    ) -> tuple["EtatClassification", RapportOrchestration]:
        """Construit un état, applique le plan demandé et retourne état plus rapport."""
        etat = EtatClassification.depuis_article(
            article,
            texte=texte,
            configuration=configuration,
        )
        rapport = self.executer(
            etat,
            debut=debut,
            fin=fin,
            etapes=etapes,
            inclure_dependances=inclure_dependances,
            finaliser=finaliser,
        )
        return etat, rapport

    @staticmethod
    def _message_exception(erreur: BaseException) -> str:
        message = " ".join(str(erreur or "").split())
        return message or type(erreur).__qualname__

    def _echouer_validation(
        self,
        etat: "EtatClassification",
        etape: EtapeClassification,
        validation: RapportValidation,
    ) -> IncidentExecution:
        message = "; ".join(item.message for item in validation.violations)
        etat.demarrer_etape(etape)
        etat.echouer_etape(etape, motif=message, code="pipeline.validation_entree")
        return IncidentExecution(
            etape=etape,
            type_exception="ViolationContrat",
            message=message,
        )

    def _echouer_sans_executant(
        self,
        etat: "EtatClassification",
        etape: EtapeClassification,
    ) -> IncidentExecution:
        message = f"Aucun exécutant enregistré pour l'étape {etape.value!r}."
        etat.demarrer_etape(etape)
        etat.echouer_etape(
            etape,
            motif=message,
            code="pipeline.executant_absent",
        )
        return IncidentExecution(
            etape=etape,
            type_exception="ExecutantAbsent",
            message=message,
        )


def creer_moteur(
    composants: Mapping[
        EtapeClassification | str,
        ExecutantEtape | ComposantEtape,
    ] | None = None,
    *,
    exiger_registre_complet: bool = True,
) -> MoteurPipeline:
    """Crée un moteur via l'API publique stable de la V5."""
    registre = RegistreEtapes()
    for etape, valeur in (composants or {}).items():
        cible = normaliser_etape(etape)
        if isinstance(valeur, ComposantEtape):
            if valeur.etape is not cible:
                raise ValueError("Le composant fourni ne correspond pas à sa clé.")
            registre.composants[cible] = valeur
        else:
            registre.enregistrer(cible, valeur)
    return MoteurPipeline(
        registre=registre,
        exiger_registre_complet=exiger_registre_complet,
    )


def executer_pipeline(
    moteur: MoteurPipeline,
    etat: "EtatClassification",
    **options: Any,
) -> RapportOrchestration:
    """Façade stable pour exécuter ou reprendre un état existant."""
    if not isinstance(moteur, MoteurPipeline):
        raise TypeError("moteur doit être une instance de MoteurPipeline.")
    return moteur.executer(etat, **options)


def classifier_article(
    moteur: MoteurPipeline,
    article: Mapping[str, Any],
    **options: Any,
) -> tuple["EtatClassification", RapportOrchestration]:
    """Façade stable pour créer puis exécuter une classification."""
    if not isinstance(moteur, MoteurPipeline):
        raise TypeError("moteur doit être une instance de MoteurPipeline.")
    return moteur.executer_article(article, **options)


@dataclass(slots=True)
class EtatClassification:
    """État partagé unique d'une classification en cours.

    Chaque article possède sa propre instance. Les modules métier lisent le
    contexte et y déposent leurs résultats ; le pipeline gère uniquement la
    configuration technique, l'exécution, les diagnostics et l'audit.

    La V5 conserve le propriétaire, les entrées, les sorties et les
    dépendances de chaque étape au moyen de ``CONTRATS_ETAPES``. Elle ne protège
    pas encore physiquement chaque attribut contre une écriture incorrecte.
    """

    contexte: ContexteClassification
    configuration: ConfigurationPipeline = field(
        default_factory=ConfigurationPipeline
    )
    execution: ExecutionPipeline = field(default_factory=ExecutionPipeline)
    diagnostic: DiagnosticPipeline = field(default_factory=DiagnosticPipeline)
    audit: AuditPipeline = field(default_factory=AuditPipeline)
    metriques: MetriquesPipeline = field(default_factory=MetriquesPipeline)
    empreintes: EmpreintesPipeline = field(default_factory=EmpreintesPipeline)
    importance_detail: Mapping[str, Any] | int = 0
    integrite_publication: list[str] = field(default_factory=list)
    extensions: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.contexte, ContexteClassification):
            raise TypeError(
                "contexte doit être une instance de ContexteClassification."
            )
        if not isinstance(self.configuration, ConfigurationPipeline):
            raise TypeError(
                "configuration doit être une instance de ConfigurationPipeline."
            )
        if not isinstance(self.execution, ExecutionPipeline):
            raise TypeError("execution doit être une instance de ExecutionPipeline.")
        if not isinstance(self.diagnostic, DiagnosticPipeline):
            raise TypeError(
                "diagnostic doit être une instance de DiagnosticPipeline."
            )
        if not isinstance(self.audit, AuditPipeline):
            raise TypeError("audit doit être une instance de AuditPipeline.")
        if not isinstance(self.metriques, MetriquesPipeline):
            raise TypeError("metriques doit être une instance de MetriquesPipeline.")
        if not isinstance(self.empreintes, EmpreintesPipeline):
            raise TypeError("empreintes doit être une instance de EmpreintesPipeline.")

        self.importance_detail = deepcopy(self.importance_detail)
        self.integrite_publication = _normaliser_liste_textes(
            self.integrite_publication
        )
        self.extensions = deepcopy(dict(self.extensions))
        texte_vide = not bool(str(getattr(self.contexte, "texte", "") or "").strip())
        self.audit.enregistrer(
            "etat_classification_cree",
            donnees={
                "texte_vide": texte_vide,
                "etapes_actives": [
                    item.value for item in self.configuration.etapes_actives
                ],
                "ordre_strict": self.configuration.ordre_strict,
            },
        )
        self.empreintes.initialiser(
            entree={"article": self.article, "texte": self.texte},
            configuration=self.configuration.exporter(),
            referentiel=[CONTRATS_ETAPES[item].exporter() for item in ORDRE_ETAPES],
        )

    @classmethod
    def depuis_article(
        cls,
        article: Mapping[str, Any],
        *,
        texte: str = "",
        configuration: ConfigurationPipeline | None = None,
    ) -> EtatClassification:
        """Crée un nouvel état indépendant depuis un article."""
        return cls(
            contexte=ContexteClassification(article=article, texte=texte),
            configuration=configuration or ConfigurationPipeline(),
        )

    @property
    def article(self) -> Mapping[str, Any]:
        return self.contexte.article

    @property
    def texte(self) -> str:
        return self.contexte.texte

    @property
    def est_finalisee(self) -> bool:
        return self.execution.statut in {
            StatutClassification.TERMINEE,
            StatutClassification.TERMINEE_AVEC_AVERTISSEMENTS,
            StatutClassification.ECHEC,
        }

    @property
    def contrat_etape_courante(self) -> ContratEtape | None:
        etape = self.execution.etape_courante
        return CONTRATS_ETAPES[etape] if etape is not None else None

    def obtenir_contrat(
        self,
        etape: EtapeClassification | str,
    ) -> ContratEtape:
        return CONTRATS_ETAPES[normaliser_etape(etape)]

    def ajouter_erreur(
        self,
        message: str,
        *,
        code: str = "pipeline.erreur",
        etape: EtapeClassification | str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> MessageDiagnostic:
        return self.diagnostic.erreur(
            code,
            message,
            etape=etape,
            details=details,
        )

    def ajouter_avertissement(
        self,
        message: str,
        *,
        code: str = "pipeline.avertissement",
        etape: EtapeClassification | str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> MessageDiagnostic:
        return self.diagnostic.avertissement(
            code,
            message,
            etape=etape,
            details=details,
        )

    def demarrer_etape(
        self,
        etape: EtapeClassification | str,
    ) -> ExecutionEtape:
        """Démarre techniquement une étape, sans appeler son module métier."""
        cible = normaliser_etape(etape)
        suivi = self.execution.demarrer(
            cible,
            configuration=self.configuration,
        )
        self.metriques.demarrer(cible)
        self.audit.enregistrer(
            "etape_demarree",
            etape=cible,
            donnees={"execution": suivi.nombre_executions},
        )
        return suivi

    def terminer_etape(
        self,
        etape: EtapeClassification | str,
    ) -> ExecutionEtape:
        cible = normaliser_etape(etape)
        suivi = self.execution.terminer(cible)
        self.metriques.terminer(cible)
        self.audit.enregistrer("etape_terminee", etape=cible)
        return suivi

    def ignorer_etape(
        self,
        etape: EtapeClassification | str,
        *,
        motif: str,
    ) -> ExecutionEtape:
        cible = normaliser_etape(etape)
        suivi = self.execution.ignorer(
            cible,
            motif=motif,
            configuration=self.configuration,
        )
        self.metriques.ignorer(cible)
        self.audit.enregistrer(
            "etape_ignoree",
            etape=cible,
            donnees={"motif": suivi.motif},
        )
        return suivi

    def echouer_etape(
        self,
        etape: EtapeClassification | str,
        *,
        motif: str,
        code: str = "pipeline.etape_echec",
    ) -> ExecutionEtape:
        cible = normaliser_etape(etape)
        suivi = self.execution.echouer(
            cible,
            motif=motif,
            configuration=self.configuration,
        )
        self.metriques.echouer(cible)
        self.diagnostic.erreur(code, motif, etape=cible)
        self.audit.enregistrer(
            "etape_echouee",
            etape=cible,
            donnees={"motif": suivi.motif},
        )
        return suivi

    def marquer_etape(self, nom: EtapeClassification | str) -> None:
        """Alias transitoire compatible avec l'ancien orchestrateur.

        Cette méthode respecte désormais les dépendances et l'ordre configuré.
        Le nouveau code doit préférer ``demarrer_etape`` et ``terminer_etape``.
        """
        etape = normaliser_etape(nom)
        suivi = self.execution.obtenir(etape)
        if suivi.statut is StatutEtape.TERMINEE:
            return
        self.demarrer_etape(etape)
        self.terminer_etape(etape)

    @property
    def etapes_executees(self) -> list[str]:
        """Alias de migration compatible avec la structure historique."""
        return [etape.value for etape in self.execution.etapes_terminees]

    @property
    def erreurs_non_bloquantes(self) -> list[str]:
        """Alias historique ; le diagnostic structuré reste la source officielle."""
        return [
            message.message
            for message in self.diagnostic.messages
            if message.niveau is NiveauDiagnostic.ERREUR
        ]

    def valider_etape(
        self,
        etape: EtapeClassification | str,
        *,
        phase: str = "entrees",
    ) -> RapportValidation:
        return valider_contrat_etape(self, etape, phase=phase)

    def finaliser(self) -> None:
        self.execution.finaliser(
            configuration=self.configuration,
            avec_avertissements=self.diagnostic.a_des_avertissements,
        )
        self.audit.enregistrer(
            "classification_finalisee",
            donnees={"statut": self.execution.statut.value},
        )
        self.empreintes.finaliser(
            resultat=self._donnees_deterministes(),
            audit=self.audit.exporter()["evenements"],
        )

    def _donnees_deterministes(self) -> dict[str, Any]:
        """Vue stable excluant métriques temporelles et empreintes récursives."""
        contexte_exporte = (
            self.contexte.exporter()
            if hasattr(self.contexte, "exporter")
            else {
                nom: deepcopy(getattr(self.contexte, nom))
                for nom in getattr(self.contexte, "__slots__", ())
                if hasattr(self.contexte, nom)
            }
        )
        return {
            "version_contrat_etat": VERSION_CONTRAT_ETAT,
            "configuration": self.configuration.exporter(),
            "contexte": contexte_exporte,
            "execution": self.execution.exporter(),
            "diagnostic": self.diagnostic.exporter(),
            "importance_detail": deepcopy(self.importance_detail),
            "integrite_publication": list(self.integrite_publication),
            "extensions": deepcopy(self.extensions),
        }

    def verifier_tracabilite(self) -> bool:
        """Vérifie la chaîne d'audit et les empreintes initiales connues."""
        referentiel = [CONTRATS_ETAPES[item].exporter() for item in ORDRE_ETAPES]
        return (
            self.audit.verifier_integrite()
            and self.empreintes.entree
            == calculer_empreinte({"article": self.article, "texte": self.texte})
            and self.empreintes.configuration
            == calculer_empreinte(self.configuration.exporter())
            and self.empreintes.referentiel == calculer_empreinte(referentiel)
        )

    def exporter(self) -> dict[str, Any]:
        """Produit une vue technique indépendante et sérialisable."""
        contexte_exporte = (
            self.contexte.exporter()
            if hasattr(self.contexte, "exporter")
            else {
                nom: deepcopy(getattr(self.contexte, nom))
                for nom in getattr(self.contexte, "__slots__", ())
                if hasattr(self.contexte, nom)
            }
        )
        return {
            "version_pipeline": VERSION_PIPELINE,
            "version_contrat_etat": VERSION_CONTRAT_ETAT,
            "configuration": self.configuration.exporter(),
            "referentiel_etapes": [
                CONTRATS_ETAPES[item].exporter() for item in ORDRE_ETAPES
            ],
            "contexte": contexte_exporte,
            "execution": self.execution.exporter(),
            "diagnostic": self.diagnostic.exporter(),
            "audit": self.audit.exporter(),
            "metriques": self.metriques.exporter(),
            "empreintes": self.empreintes.exporter(),
            "tracabilite_valide": self.verifier_tracabilite(),
            "importance_detail": deepcopy(self.importance_detail),
            "integrite_publication": list(self.integrite_publication),
            "extensions": deepcopy(self.extensions),
        }


# Alias transitoire destiné à simplifier la migration de l'ancien orchestrateur.
EtatPipeline = EtatClassification


def normaliser_etape(
    etape: EtapeClassification | str,
) -> EtapeClassification:
    """Convertit un nom d'étape en valeur canonique ou lève ``ValueError``."""
    if isinstance(etape, EtapeClassification):
        return etape
    valeur = str(etape or "").strip().casefold().replace("-", "_").replace(" ", "_")
    try:
        return EtapeClassification(valeur)
    except ValueError as erreur:
        valeurs = ", ".join(item.value for item in ORDRE_ETAPES)
        raise ValueError(
            f"Étape inconnue {etape!r}. Valeurs autorisées : {valeurs}."
        ) from erreur


def position_etape(etape: EtapeClassification | str) -> int:
    """Retourne la position zéro-indexée d'une étape dans l'ordre officiel."""
    return INDEX_ETAPES[normaliser_etape(etape)]


def etape_precedente(
    etape: EtapeClassification | str,
) -> EtapeClassification | None:
    """Retourne l'étape précédente, ou ``None`` pour la préparation."""
    index = position_etape(etape)
    return ORDRE_ETAPES[index - 1] if index > 0 else None


def etape_suivante(
    etape: EtapeClassification | str,
) -> EtapeClassification | None:
    """Retourne l'étape suivante, ou ``None`` pour l'explication."""
    index = position_etape(etape)
    return ORDRE_ETAPES[index + 1] if index + 1 < len(ORDRE_ETAPES) else None


def _normaliser_liste_textes(valeurs: Any) -> list[str]:
    if valeurs is None:
        return []
    if isinstance(valeurs, (str, bytes)):
        valeurs = [valeurs]
    resultat: list[str] = []
    vues: set[str] = set()
    for valeur in valeurs:
        texte = (
            valeur.decode("utf-8", errors="replace")
            if isinstance(valeur, bytes)
            else str(valeur or "")
        )
        texte = " ".join(texte.split())
        cle = texte.casefold()
        if texte and cle not in vues:
            vues.add(cle)
            resultat.append(texte)
    return resultat


__all__ = [
    "ComposantEtape",
    "ErreurOrchestration",
    "ExecutantEtape",
    "IncidentExecution",
    "MoteurPipeline",
    "PlanExecution",
    "RapportOrchestration",
    "RapportValidation",
    "RegistreEtapes",
    "ViolationContrat",
    "classifier_article",
    "construire_plan_execution",
    "creer_moteur",
    "executer_pipeline",
    "valider_contrat_etape",
    "ALGORITHME_EMPREINTE",
    "AuditPipeline",
    "ConfigurationPipeline",
    "CONTRATS_ETAPES",
    "ContratEtape",
    "DiagnosticPipeline",
    "EtatClassification",
    "EtatPipeline",
    "EtapeClassification",
    "ExecutionEtape",
    "ExecutionPipeline",
    "EmpreintesPipeline",
    "MessageDiagnostic",
    "MetriquesEtape",
    "MetriquesPipeline",
    "NiveauDiagnostic",
    "ORDRE_ETAPES",
    "PolitiqueErreur",
    "StatutClassification",
    "StatutEtape",
    "VERSION_CONTRAT_ETAT",
    "VERSION_PIPELINE",
    "calculer_empreinte",
    "serialiser_canonique",
    "etape_precedente",
    "etape_suivante",
    "normaliser_etape",
    "position_etape",
]