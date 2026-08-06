"""API publique et orchestrateur du moteur déterministe de classification V2.

Ce module constitue le point d'entrée officiel du paquet ``classification``.
Il assemble les briques spécialisées sans dupliquer leurs règles métier :

- normalisation et construction du corpus ;
- détection des catégories ;
- détection des dimensions One Health ;
- estimation du niveau de preuve ;
- calcul de pertinence ;
- intégration facultative de l'importance historique ;
- agrégation du score ;
- décision finale ;
- construction d'une explication lisible.

Le fichier est volontairement détaillé. Il fournit également :

- une configuration explicite du pipeline ;
- un contexte d'exécution structuré ;
- des garde-fous sur les résultats des sous-modules ;
- une API fonctionnelle compatible avec l'ancien moteur ;
- une API orientée objet pour les usages avancés ;
- des utilitaires de sérialisation et de diagnostic ;
- des points d'extension déterministes pour l'importance et l'intégrité.

Aucune intelligence artificielle n'est utilisée. À configuration et article
identiques, le résultat est identique.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any, Final, Literal, TypedDict, cast

from .categories import executer as executer_categories_v6
from .contexte import ContexteClassification
from .decision import SEUILS_PAR_DEFAUT, SeuilsDecision
from .decision import executer as executer_decision_v6
from .explication import executer as executer_explication_v6
from .one_health import executer as executer_one_health_v6
from .pertinence import executer as executer_pertinence_v6
from .pipeline import EtatClassification
from .preuve import executer as executer_preuve_v6
from .score import executer as executer_score_v6
from .utils import construire_texte, dedupliquer


# ---------------------------------------------------------------------------
# Types publics
# ---------------------------------------------------------------------------

DecisionNom = Literal["rejet", "a_revoir", "retenu", "prioritaire"]
NiveauImportance = Literal["", "faible", "moderee", "elevee", "critique"]

CalculateurImportance = Callable[
    [Mapping[str, Any]],
    Mapping[str, Any] | int | float | str | None,
]

ExtracteurIntegrite = Callable[[Mapping[str, Any]], Sequence[str] | None]

ObservateurEtape = Callable[
    [str, Mapping[str, Any]],
    None,
]


class ResultatClassification(TypedDict, total=False):
    """Contrat de sortie documenté du moteur V2.

    Le ``TypedDict`` reste volontairement permissif afin de préserver la
    compatibilité avec les consommateurs historiques qui n'utilisent qu'une
    partie des clés.
    """

    categorie: str
    categories: list[str]
    one_health: list[str]
    preuve: str
    niveau_preuve: int
    importance: int
    niveau_importance: str
    mots_detectes: list[str]
    pertinence: dict[str, Any]
    score_pertinence: int
    confiance: int
    score: dict[str, Any]
    score_global: int
    decision: DecisionNom
    decision_libelle: str
    retenu: bool
    prioritaire: bool
    revision_humaine: bool
    raisons: list[str]
    explication: dict[str, Any]
    analyse_preuve: dict[str, Any]
    mots_categories: list[str]
    mots_one_health: list[str]
    statut_publication: str
    version_moteur: str
    diagnostic: dict[str, Any]


# ---------------------------------------------------------------------------
# Constantes et configuration
# ---------------------------------------------------------------------------

VERSION_MOTEUR: Final[str] = "6.0.0-v2-compatible"
CATEGORIE_PAR_DEFAUT: Final[str] = "Non classé"
PREUVE_PAR_DEFAUT: Final[str] = "Non déterminé"


@dataclass(frozen=True, slots=True)
class ConfigurationClassification:
    """Paramètres stables de l'orchestrateur.

    Les règles thématiques restent dans leurs modules respectifs. Cette
    configuration ne contrôle que le comportement transversal du pipeline.
    """

    seuils_decision: SeuilsDecision = SEUILS_PAR_DEFAUT
    inclure_diagnostic: bool = False
    inclure_details_preuve: bool = True
    inclure_details_score: bool = True
    inclure_explication: bool = True
    conserver_cles_compatibilite: bool = True
    importance_par_defaut: int = 0
    categorie_par_defaut: str = CATEGORIE_PAR_DEFAUT
    preuve_par_defaut: str = PREUVE_PAR_DEFAUT
    version_moteur: str = VERSION_MOTEUR

    def __post_init__(self) -> None:
        if not 0 <= self.importance_par_defaut <= 100:
            raise ValueError("importance_par_defaut doit être comprise entre 0 et 100.")
        if not self.categorie_par_defaut.strip():
            raise ValueError("categorie_par_defaut ne peut pas être vide.")
        if not self.preuve_par_defaut.strip():
            raise ValueError("preuve_par_defaut ne peut pas être vide.")
        if not self.version_moteur.strip():
            raise ValueError("version_moteur ne peut pas être vide.")


CONFIGURATION_PAR_DEFAUT: Final[ConfigurationClassification] = (
    ConfigurationClassification()
)


@dataclass(slots=True)
class EtatPipeline:
    """État de compatibilité V2 adossé à l'état partagé du Pipeline V6.

    L'objet public historique est conservé. Les modules métier reçoivent
    toutefois ``etat_v6`` afin qu'un seul état officiel porte les extensions,
    l'audit et les résultats du Pipeline V6.
    """

    contexte: ContexteClassification
    importance_detail: Mapping[str, Any] | int = 0
    integrite_publication: list[str] = field(default_factory=list)
    erreurs_non_bloquantes: list[str] = field(default_factory=list)
    etapes_executees: list[str] = field(default_factory=list)
    etat_v6: EtatClassification = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.etat_v6 = EtatClassification(
            contexte=self.contexte,
            importance_detail=self.importance_detail,
            integrite_publication=self.integrite_publication,
        )

    def synchroniser_v6(self) -> None:
        """Synchronise les données transversales avant une étape V6."""
        self.etat_v6.importance_detail = self.importance_detail
        self.etat_v6.integrite_publication = list(self.integrite_publication)

    @property
    def article(self) -> Mapping[str, Any]:
        return self.contexte.article

    @property
    def texte(self) -> str:
        return self.contexte.texte

    def marquer_etape(self, nom: str) -> None:
        if nom not in self.etapes_executees:
            self.etapes_executees.append(nom)

    def ajouter_erreur(self, message: str) -> None:
        message_propre = str(message or "").strip()
        if message_propre and message_propre not in self.erreurs_non_bloquantes:
            self.erreurs_non_bloquantes.append(message_propre)


# ---------------------------------------------------------------------------
# Fonctions de normalisation transversales
# ---------------------------------------------------------------------------


def _article_valide(article: Mapping[str, Any] | None) -> Mapping[str, Any]:
    """Retourne toujours un mapping exploitable par le pipeline."""
    return article if isinstance(article, Mapping) else {}



def _entier_borne(
    valeur: Any,
    *,
    minimum: int = 0,
    maximum: int = 100,
    defaut: int = 0,
) -> int:
    """Convertit une valeur en entier borné sans lever d'exception métier."""
    try:
        entier = int(float(valeur))
    except (TypeError, ValueError, OverflowError):
        entier = defaut
    return max(minimum, min(maximum, entier))



def _chaine_propre(valeur: Any, defaut: str = "") -> str:
    """Produit une chaîne nettoyée tout en préservant un défaut explicite."""
    texte = str(valeur or "").strip()
    return texte or defaut



def _liste_chaines(valeurs: Iterable[Any] | None) -> list[str]:
    """Normalise et déduplique une collection de libellés."""
    if valeurs is None:
        return []
    return cast(
        list[str],
        dedupliquer(
            _chaine_propre(valeur)
            for valeur in valeurs
            if _chaine_propre(valeur)
        ),
    )



def _extraire_integrite_depuis_article(
    article: Mapping[str, Any],
) -> list[str]:
    """Lit les alertes d'intégrité déjà présentes dans un article.

    Plusieurs alias sont acceptés afin de faciliter la migration depuis les
    flux historiques.
    """
    alias = (
        "integrite_publication",
        "intégrité_publication",
        "publication_integrity",
        "integrite",
        "integrity",
    )

    for nom in alias:
        valeur = article.get(nom)
        if valeur is None:
            continue
        if isinstance(valeur, str):
            return _liste_chaines([valeur])
        if isinstance(valeur, Iterable) and not isinstance(
            valeur,
            (bytes, bytearray, Mapping),
        ):
            return _liste_chaines(valeur)

    return []



def _resoudre_integrite(
    article: Mapping[str, Any],
    extracteur: ExtracteurIntegrite | None,
) -> list[str]:
    """Résout les alertes d'intégrité avec un extracteur facultatif."""
    if extracteur is None:
        return _extraire_integrite_depuis_article(article)

    resultat = extracteur(article)
    return _liste_chaines(resultat)



def _normaliser_importance(
    article: Mapping[str, Any],
    calculateur: CalculateurImportance | None,
    *,
    valeur_par_defaut: int,
) -> tuple[int, Mapping[str, Any] | int]:
    """Exécute le calculateur d'importance et harmonise son résultat.

    Le calculateur peut renvoyer :

    - un entier ;
    - un flottant ;
    - une chaîne numérique ;
    - un mapping contenant ``importance`` ou ``score_importance`` ;
    - ``None``.
    """
    if calculateur is None:
        score = _entier_borne(valeur_par_defaut)
        return score, score

    resultat = calculateur(article)

    if isinstance(resultat, Mapping):
        valeur = resultat.get(
            "importance",
            resultat.get("score_importance", valeur_par_defaut),
        )
        score = _entier_borne(valeur, defaut=valeur_par_defaut)
        return score, resultat

    score = _entier_borne(resultat, defaut=valeur_par_defaut)
    return score, score



def _niveau_importance(
    importance_detail: Mapping[str, Any] | int,
    score_importance: int,
) -> str:
    """Détermine un libellé d'importance stable."""
    if isinstance(importance_detail, Mapping):
        libelle = _chaine_propre(
            importance_detail.get(
                "niveau_importance",
                importance_detail.get("niveau", ""),
            )
        )
        if libelle:
            return libelle

    if score_importance >= 85:
        return "critique"
    if score_importance >= 65:
        return "elevee"
    if score_importance >= 35:
        return "moderee"
    if score_importance > 0:
        return "faible"
    return ""



def _notifier(
    observateur: ObservateurEtape | None,
    etape: str,
    donnees: Mapping[str, Any],
) -> None:
    """Informe un observateur sans modifier la logique de classification."""
    if observateur is not None:
        observateur(etape, donnees)


# ---------------------------------------------------------------------------
# Validation des résultats des sous-modules
# ---------------------------------------------------------------------------


def _valider_categories(
    categories: Iterable[Any],
    mots: Iterable[Any],
) -> tuple[list[str], list[str]]:
    return _liste_chaines(categories), _liste_chaines(mots)



def _valider_one_health(
    dimensions: Iterable[Any],
    mots: Iterable[Any],
) -> tuple[list[str], list[str]]:
    dimensions_valides = _liste_chaines(dimensions)
    mots_valides = _liste_chaines(mots)
    return dimensions_valides, mots_valides



def _valider_preuve(
    preuve: Mapping[str, Any] | None,
    *,
    preuve_par_defaut: str,
) -> dict[str, Any]:
    """Garantit le contrat minimal requis par le score et l'explication."""
    resultat = dict(preuve or {})
    resultat["preuve"] = _chaine_propre(
        resultat.get("preuve"),
        preuve_par_defaut,
    )
    resultat["niveau_preuve"] = _entier_borne(
        resultat.get("niveau_preuve"),
        maximum=5,
    )
    resultat["raison_preuve"] = _chaine_propre(
        resultat.get("raison_preuve"),
        "Le niveau de preuve n'a pas pu être déterminé automatiquement.",
    )
    resultat["statut_publication"] = _chaine_propre(
        resultat.get("statut_publication"),
        "Résultats principaux ou statut non précisé",
    )
    resultat.setdefault("preuves_detectees", [])
    resultat.setdefault("mots_detectes", [])
    return resultat



def _valider_pertinence(
    pertinence: Mapping[str, Any] | None,
    *,
    categories: Sequence[str],
    one_health: Sequence[str],
) -> dict[str, Any]:
    """Normalise le profil de pertinence sans recalculer les règles."""
    resultat = dict(pertinence or {})
    score = _entier_borne(resultat.get("score_pertinence"))
    confiance = _entier_borne(resultat.get("confiance"))

    resultat["score_pertinence"] = score
    resultat["score_pertinence_brut"] = _entier_borne(
        resultat.get("score_pertinence_brut", score),
        minimum=-1000,
        maximum=1000,
        defaut=score,
    )
    resultat["confiance"] = confiance
    resultat["categories"] = _liste_chaines(
        resultat.get("categories", categories)
    )
    resultat["one_health"] = _liste_chaines(
        resultat.get("one_health", one_health)
    )
    resultat["raisons"] = _liste_chaines(resultat.get("raisons", []))
    resultat["raisons_positives"] = _liste_chaines(
        resultat.get("raisons_positives", [])
    )
    resultat["raisons_negatives"] = _liste_chaines(
        resultat.get("raisons_negatives", [])
    )
    resultat.setdefault("contextes_hors_cible", [])
    resultat.setdefault("contributions", [])

    niveau = _chaine_propre(resultat.get("niveau_pertinence"))
    if niveau not in {"rejet", "a_revoir", "pertinent", "prioritaire"}:
        if score < 20:
            niveau = "rejet"
        elif score < 40:
            niveau = "a_revoir"
        elif score < 70:
            niveau = "pertinent"
        else:
            niveau = "prioritaire"

    resultat["niveau_pertinence"] = niveau
    resultat["retenu"] = niveau in {"pertinent", "prioritaire"}
    return resultat



def _valider_score(score: Mapping[str, Any] | None) -> dict[str, Any]:
    resultat = dict(score or {})
    resultat["score_global"] = _entier_borne(resultat.get("score_global"))
    resultat["score_global_brut"] = _entier_borne(
        resultat.get("score_global_brut", resultat["score_global"]),
        minimum=-1000,
        maximum=1000,
        defaut=resultat["score_global"],
    )
    resultat["score_pertinence"] = _entier_borne(
        resultat.get("score_pertinence")
    )
    resultat["score_importance"] = _entier_borne(
        resultat.get("score_importance")
    )
    resultat["niveau_preuve"] = _entier_borne(
        resultat.get("niveau_preuve"),
        maximum=5,
    )
    resultat["plafond_applique"] = _entier_borne(
        resultat.get("plafond_applique", 100)
    )
    resultat.setdefault("composantes_score", [])
    return resultat



def _valider_decision(
    decision: Mapping[str, Any] | None,
    score_global: int,
) -> dict[str, Any]:
    resultat = dict(decision or {})
    nom = _chaine_propre(resultat.get("decision"), "rejet")

    if nom not in {"rejet", "a_revoir", "retenu", "prioritaire"}:
        nom = "rejet"

    libelles = {
        "rejet": "Rejeté",
        "a_revoir": "À revoir",
        "retenu": "Retenu",
        "prioritaire": "Prioritaire",
    }

    resultat["decision"] = nom
    resultat["decision_libelle"] = _chaine_propre(
        resultat.get("decision_libelle"),
        libelles[nom],
    )
    resultat["retenu"] = nom in {"retenu", "prioritaire"}
    resultat["prioritaire"] = nom == "prioritaire"
    resultat["revision_humaine"] = nom == "a_revoir"
    resultat["score_global"] = _entier_borne(
        resultat.get("score_global", score_global)
    )
    return resultat



def _valider_explication(
    explication: Mapping[str, Any] | None,
) -> dict[str, Any]:
    resultat = dict(explication or {})
    resultat["synthese"] = _chaine_propre(resultat.get("synthese"))
    resultat["explications"] = _liste_chaines(
        resultat.get("explications", [])
    )
    resultat["raisons_positives"] = _liste_chaines(
        resultat.get("raisons_positives", [])
    )
    resultat["raisons_negatives"] = _liste_chaines(
        resultat.get("raisons_negatives", [])
    )
    return resultat


# ---------------------------------------------------------------------------
# Étapes du pipeline
# ---------------------------------------------------------------------------


def _etape_categories(
    etat: EtatPipeline,
    observateur: ObservateurEtape | None,
) -> None:
    etat.synchroniser_v6()
    executer_categories_v6(etat.etat_v6)
    (
        etat.contexte.categories,
        etat.contexte.mots_categories,
    ) = _valider_categories(
        etat.contexte.categories,
        etat.contexte.mots_categories,
    )
    etat.marquer_etape("categories")
    _notifier(
        observateur,
        "categories",
        {
            "categories": etat.contexte.categories,
            "mots_categories": etat.contexte.mots_categories,
        },
    )



def _etape_one_health(
    etat: EtatPipeline,
    observateur: ObservateurEtape | None,
) -> None:
    etat.synchroniser_v6()
    executer_one_health_v6(etat.etat_v6)
    (
        etat.contexte.one_health,
        etat.contexte.mots_one_health,
    ) = _valider_one_health(
        etat.contexte.one_health,
        etat.contexte.mots_one_health,
    )
    etat.marquer_etape("one_health")
    _notifier(
        observateur,
        "one_health",
        {
            "one_health": etat.contexte.one_health,
            "mots_one_health": etat.contexte.mots_one_health,
        },
    )



def _etape_preuve(
    etat: EtatPipeline,
    observateur: ObservateurEtape | None,
    *,
    preuve_par_defaut: str,
) -> None:
    etat.synchroniser_v6()
    executer_preuve_v6(etat.etat_v6)
    etat.contexte.preuve = _valider_preuve(
        etat.contexte.preuve,
        preuve_par_defaut=preuve_par_defaut,
    )
    etat.marquer_etape("preuve")
    _notifier(observateur, "preuve", etat.contexte.preuve)



def _etape_pertinence(
    etat: EtatPipeline,
    observateur: ObservateurEtape | None,
) -> None:
    etat.synchroniser_v6()
    executer_pertinence_v6(etat.etat_v6)
    etat.contexte.pertinence = _valider_pertinence(
        etat.contexte.pertinence,
        categories=etat.contexte.categories,
        one_health=etat.contexte.one_health,
    )
    etat.marquer_etape("pertinence")
    _notifier(observateur, "pertinence", etat.contexte.pertinence)



def _etape_importance(
    etat: EtatPipeline,
    observateur: ObservateurEtape | None,
    calculateur_importance: CalculateurImportance | None,
    *,
    valeur_par_defaut: int,
) -> None:
    importance, detail = _normaliser_importance(
        etat.article,
        calculateur_importance,
        valeur_par_defaut=valeur_par_defaut,
    )
    etat.contexte.importance = importance
    etat.importance_detail = detail
    etat.synchroniser_v6()
    etat.marquer_etape("importance")
    _notifier(
        observateur,
        "importance",
        {
            "importance": importance,
            "detail": detail,
        },
    )



def _etape_score(
    etat: EtatPipeline,
    observateur: ObservateurEtape | None,
) -> None:
    etat.synchroniser_v6()
    executer_score_v6(etat.etat_v6)
    etat.contexte.score = _valider_score(etat.contexte.score)
    etat.marquer_etape("score")
    _notifier(observateur, "score", etat.contexte.score)



def _etape_decision(
    etat: EtatPipeline,
    observateur: ObservateurEtape | None,
    *,
    seuils: SeuilsDecision,
) -> None:
    etat.synchroniser_v6()
    etat.etat_v6.extensions["seuils_decision_v2"] = seuils
    executer_decision_v6(etat.etat_v6)
    etat.contexte.decision = _valider_decision(
        etat.contexte.decision,
        etat.contexte.score["score_global"],
    )
    etat.marquer_etape("decision")
    _notifier(observateur, "decision", etat.contexte.decision)



def _etape_explication(
    etat: EtatPipeline,
    observateur: ObservateurEtape | None,
) -> None:
    etat.synchroniser_v6()
    executer_explication_v6(etat.etat_v6)
    etat.contexte.explication = _valider_explication(
        etat.contexte.explication
    )
    etat.marquer_etape("explication")
    _notifier(observateur, "explication", etat.contexte.explication)


# ---------------------------------------------------------------------------
# Construction du résultat final
# ---------------------------------------------------------------------------


def _mots_preuve(preuve: Mapping[str, Any]) -> list[str]:
    """Récupère les expressions de preuve même si elles sont imbriquées."""
    mots_directs = preuve.get("mots_detectes", [])
    resultat = _liste_chaines(
        mots_directs if isinstance(mots_directs, Iterable) else []
    )

    preuves_detectees = preuve.get("preuves_detectees", [])
    if isinstance(preuves_detectees, Iterable):
        for element in preuves_detectees:
            if not isinstance(element, Mapping):
                continue
            correspondances = element.get("correspondances", [])
            if isinstance(correspondances, Iterable) and not isinstance(
                correspondances,
                (str, bytes, bytearray, Mapping),
            ):
                resultat.extend(_liste_chaines(correspondances))

    return _liste_chaines(resultat)



def _diagnostic(etat: EtatPipeline) -> dict[str, Any]:
    """Construit un diagnostic technique sans exposer l'article complet."""
    return {
        "version_moteur": VERSION_MOTEUR,
        "longueur_texte_normalise": len(etat.texte),
        "texte_vide": not bool(etat.texte),
        "etapes_executees": list(etat.etapes_executees),
        "erreurs_non_bloquantes": list(etat.erreurs_non_bloquantes),
        "nombre_categories": len(etat.contexte.categories),
        "nombre_dimensions_one_health": len(etat.contexte.one_health),
        "nombre_mots_categories": len(etat.contexte.mots_categories),
        "nombre_mots_one_health": len(etat.contexte.mots_one_health),
        "integrite_publication": list(etat.integrite_publication),
    }



def _construire_resultat(
    etat: EtatPipeline,
    configuration: ConfigurationClassification,
) -> ResultatClassification:
    contexte = etat.contexte
    preuve = contexte.preuve
    pertinence = contexte.pertinence
    score = contexte.score
    decision = contexte.decision
    explication = contexte.explication

    mots_detectes = _liste_chaines(
        [
            *contexte.mots_categories,
            *contexte.mots_one_health,
            *_mots_preuve(preuve),
        ]
    )

    categorie_principale = (
        contexte.categories[0]
        if contexte.categories
        else configuration.categorie_par_defaut
    )

    resultat: ResultatClassification = {
        "categorie": categorie_principale,
        "categories": list(contexte.categories),
        "one_health": list(contexte.one_health),
        "preuve": _chaine_propre(
            preuve.get("preuve"),
            configuration.preuve_par_defaut,
        ),
        "niveau_preuve": _entier_borne(
            preuve.get("niveau_preuve"),
            maximum=5,
        ),
        "importance": contexte.importance,
        "niveau_importance": _niveau_importance(
            etat.importance_detail,
            contexte.importance,
        ),
        "mots_detectes": mots_detectes,
        "pertinence": pertinence,
        "score_pertinence": _entier_borne(
            pertinence.get("score_pertinence")
        ),
        "confiance": _entier_borne(pertinence.get("confiance")),
        "score": score,
        "score_global": _entier_borne(score.get("score_global")),
        "decision": cast(DecisionNom, decision["decision"]),
        "decision_libelle": _chaine_propre(
            decision.get("decision_libelle")
        ),
        "retenu": bool(decision.get("retenu", False)),
        "prioritaire": bool(decision.get("prioritaire", False)),
        "revision_humaine": bool(
            decision.get("revision_humaine", False)
        ),
        "raisons": _liste_chaines(explication.get("explications", [])),
        "explication": explication,
        "analyse_preuve": preuve,
        "mots_categories": list(contexte.mots_categories),
        "mots_one_health": list(contexte.mots_one_health),
        "statut_publication": _chaine_propre(
            preuve.get("statut_publication"),
            "Résultats principaux ou statut non précisé",
        ),
        "version_moteur": configuration.version_moteur,
    }

    if configuration.inclure_diagnostic:
        resultat["diagnostic"] = _diagnostic(etat)

    if not configuration.inclure_details_preuve:
        resultat.pop("analyse_preuve", None)

    if not configuration.inclure_details_score:
        resultat.pop("score", None)

    if not configuration.inclure_explication:
        resultat.pop("explication", None)
        resultat.pop("raisons", None)

    if not configuration.conserver_cles_compatibilite:
        for cle in (
            "categorie",
            "preuve",
            "niveau_preuve",
            "importance",
            "niveau_importance",
            "mots_detectes",
        ):
            resultat.pop(cle, None)

    return resultat


# ---------------------------------------------------------------------------
# Moteur orienté objet
# ---------------------------------------------------------------------------


class MoteurClassification:
    """Orchestrateur réutilisable et configurable.

    Une instance peut être conservée au niveau du module Django. Elle ne garde
    aucun état spécifique à un article entre deux appels.
    """

    def __init__(
        self,
        *,
        configuration: ConfigurationClassification = CONFIGURATION_PAR_DEFAUT,
        calculateur_importance: CalculateurImportance | None = None,
        extracteur_integrite: ExtracteurIntegrite | None = None,
        observateur: ObservateurEtape | None = None,
    ) -> None:
        self.configuration = configuration
        self.calculateur_importance = calculateur_importance
        self.extracteur_integrite = extracteur_integrite
        self.observateur = observateur

    def creer_etat(
        self,
        article: Mapping[str, Any] | None,
    ) -> EtatPipeline:
        article_normalise = _article_valide(article)
        contexte = ContexteClassification(article=article_normalise)
        etat = EtatPipeline(contexte=contexte)
        etat.integrite_publication = _resoudre_integrite(
            article_normalise,
            self.extracteur_integrite,
        )
        etat.marquer_etape("normalisation")
        _notifier(
            self.observateur,
            "normalisation",
            {
                "texte": contexte.texte,
                "longueur": len(contexte.texte),
            },
        )
        return etat

    def executer_pipeline(self, etat: EtatPipeline) -> None:
        _etape_categories(etat, self.observateur)
        _etape_one_health(etat, self.observateur)
        _etape_preuve(
            etat,
            self.observateur,
            preuve_par_defaut=self.configuration.preuve_par_defaut,
        )
        _etape_pertinence(etat, self.observateur)
        _etape_importance(
            etat,
            self.observateur,
            self.calculateur_importance,
            valeur_par_defaut=self.configuration.importance_par_defaut,
        )
        _etape_score(etat, self.observateur)
        _etape_decision(
            etat,
            self.observateur,
            seuils=self.configuration.seuils_decision,
        )
        _etape_explication(etat, self.observateur)

    def classifier(
        self,
        article: Mapping[str, Any] | None,
    ) -> ResultatClassification:
        etat = self.creer_etat(article)
        self.executer_pipeline(etat)
        resultat = _construire_resultat(etat, self.configuration)
        _notifier(self.observateur, "resultat", resultat)
        return resultat

    def classifier_plusieurs(
        self,
        articles: Iterable[Mapping[str, Any] | None],
    ) -> list[ResultatClassification]:
        """Classifie une séquence en conservant l'ordre d'entrée."""
        return [self.classifier(article) for article in articles]

    def configuration_dict(self) -> dict[str, Any]:
        """Expose la configuration sous une forme sérialisable."""
        resultat = asdict(self.configuration)
        resultat["seuils_decision"] = asdict(
            self.configuration.seuils_decision
        )
        return resultat


# ---------------------------------------------------------------------------
# API fonctionnelle publique
# ---------------------------------------------------------------------------


def classifier_article(
    article: Mapping[str, Any] | None,
    *,
    calculateur_importance: CalculateurImportance | None = None,
    extracteur_integrite: ExtracteurIntegrite | None = None,
    configuration: ConfigurationClassification = CONFIGURATION_PAR_DEFAUT,
    observateur: ObservateurEtape | None = None,
) -> ResultatClassification:
    """Classifie un article avec la chaîne V2 complète.

    Cette fonction constitue le point d'entrée recommandé pour préserver la
    compatibilité avec le moteur historique.
    """
    moteur = MoteurClassification(
        configuration=configuration,
        calculateur_importance=calculateur_importance,
        extracteur_integrite=extracteur_integrite,
        observateur=observateur,
    )
    return moteur.classifier(article)



def classifier_articles(
    articles: Iterable[Mapping[str, Any] | None],
    *,
    calculateur_importance: CalculateurImportance | None = None,
    extracteur_integrite: ExtracteurIntegrite | None = None,
    configuration: ConfigurationClassification = CONFIGURATION_PAR_DEFAUT,
    observateur: ObservateurEtape | None = None,
) -> list[ResultatClassification]:
    """Classifie plusieurs articles avec une configuration commune."""
    moteur = MoteurClassification(
        configuration=configuration,
        calculateur_importance=calculateur_importance,
        extracteur_integrite=extracteur_integrite,
        observateur=observateur,
    )
    return moteur.classifier_plusieurs(articles)



def analyser_article(
    article: Mapping[str, Any] | None,
    **options: Any,
) -> ResultatClassification:
    """Alias explicite de ``classifier_article`` pour les appels métier."""
    return classifier_article(article, **options)



def est_article_retenu(
    article: Mapping[str, Any] | None,
    **options: Any,
) -> bool:
    """Retourne uniquement la décision binaire de conservation."""
    return bool(classifier_article(article, **options)["retenu"])



def score_article(
    article: Mapping[str, Any] | None,
    **options: Any,
) -> int:
    """Retourne uniquement le score global final."""
    return int(classifier_article(article, **options)["score_global"])


# Alias de compatibilité avec les usages historiques.
classifier = classifier_article
classer_article = classifier_article


# Instance simple, sans importance externe, adaptée aux appels génériques.
classificateur = MoteurClassification()


__all__ = [
    "CATEGORIE_PAR_DEFAUT",
    "CONFIGURATION_PAR_DEFAUT",
    "CalculateurImportance",
    "ConfigurationClassification",
    "DecisionNom",
    "EtatPipeline",
    "ExtracteurIntegrite",
    "MoteurClassification",
    "NiveauImportance",
    "ObservateurEtape",
    "PREUVE_PAR_DEFAUT",
    "ResultatClassification",
    "VERSION_MOTEUR",
    "analyser_article",
    "classer_article",
    "classificateur",
    "classifier",
    "classifier_article",
    "classifier_articles",
    "est_article_retenu",
    "score_article",
]