"""
Point d'entrée principal de la veille scientifique.

Fonction publique principale :

    lancer_veille_complete()

Cette version finale consolide l'orchestration du pipeline tout en conservant
le contrat historique :

    (articles, résumé, convergence, statistiques)

Elle ajoute notamment :

- une configuration validée et immuable ;
- des dépendances injectables pour les tests ;
- un contexte d'exécution structuré ;
- des étapes observables et sérialisables ;
- des hooks optionnels avant et après chaque étape ;
- une gestion homogène des erreurs, avertissements et étapes ignorées ;
- une validation stricte des résultats retournés par les services ;
- la matérialisation unique de l'historique ;
- une compatibilité complète avec le moteur de données V6 ;
- une API simple pour l'application Django existante.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
import logging
from time import perf_counter
from typing import Any, Generic, TypeVar
from uuid import uuid4

from apps.monitoring.services.collecte import (
    collecter_toutes_les_sources,
)
from apps.monitoring.services.donnees import (
    Article,
    construire_statistiques,
    preparer_articles,
)
from apps.monitoring.services.exports import (
    exporter_tous_formats,
)
from apps.monitoring.services.journaux import (
    generer_resume_executif,
)
from apps.monitoring.services.summarization import (
    generer_convergence,
)


LOGGER = logging.getLogger(__name__)

LONGUEUR_MAX_ERREUR = 1_000

MODES_TRI_AUTORISES = frozenset(
    {
        "pertinence",
        "recence",
        "nouveaute",
    }
)

NOMS_ETAPES = (
    "collecte",
    "preparation",
    "resume_executif",
    "convergence",
    "statistiques",
    "exports",
)

ResultatVeille = tuple[
    list[Article],
    str,
    str,
    dict[str, Any],
]

_T = TypeVar("_T")


@dataclass(frozen=True, slots=True)
class ConfigurationVeille:
    """
    Paramètres d'exécution du pipeline.

    ``limite=None`` conserve tous les articles. Une limite entière positive
    est appliquée après classification et classement.

    ``mode_tri`` accepte ``pertinence``, ``recence`` ou ``nouveaute``.

    ``traiter_si_vide=False`` évite les synthèses et les exports lorsqu'aucun
    article n'est retenu.

    ``erreur_si_vide=True`` considère une veille vide comme une anomalie.

    ``arreter_apres_erreur=True`` bloque les traitements secondaires après une
    erreur de collecte ou de préparation.

    ``journaliser_exceptions=True`` transmet les exceptions au module
    ``logging``.

    ``inclure_rapport_collecte=True`` ajoute une copie du rapport brut de
    collecte dans les diagnostics finaux.
    """

    limite: int | None = None
    mode_tri: str = "pertinence"
    exporter: bool = True
    generer_resume: bool = True
    generer_convergence: bool = True
    traiter_si_vide: bool = False
    erreur_si_vide: bool = False
    arreter_apres_erreur: bool = False
    journaliser_exceptions: bool = True
    inclure_rapport_collecte: bool = False
    strict: bool = False


@dataclass(frozen=True, slots=True)
class DependancesVeille:
    """
    Services utilisés par l'orchestrateur.

    Leur injection facilite les tests unitaires sans réseau, sans base de
    données et sans écriture de fichiers.
    """

    collecter: Callable[[], Any] = collecter_toutes_les_sources
    preparer: Callable[..., Any] = preparer_articles
    resumer: Callable[[list[Article]], Any] = generer_resume_executif
    converger: Callable[[list[Article]], Any] = generer_convergence
    statistiques: Callable[[dict[str, Any], list[Article]], Any] = (
        construire_statistiques
    )
    exporter: Callable[[list[Article], dict[str, Any]], Any] = (
        exporter_tous_formats
    )


@dataclass(frozen=True, slots=True)
class HooksVeille:
    """
    Callbacks optionnels d'observation.

    Les hooks ne doivent pas modifier les données du pipeline. Toute exception
    levée par un hook est enregistrée comme avertissement et n'interrompt pas
    la veille, sauf en mode strict.
    """

    avant_etape: Callable[[str, "ContexteVeille"], None] | None = None
    apres_etape: Callable[[str, "ContexteVeille"], None] | None = None


@dataclass(slots=True)
class EtatEtape:
    """État sérialisable d'une étape du pipeline."""

    statut: str = "en_attente"
    debut_utc: str | None = None
    fin_utc: str | None = None
    duree_secondes: float = 0.0
    details: dict[str, Any] = field(
        default_factory=dict
    )

    def convertir(self) -> dict[str, Any]:
        """Convertit l'état en dictionnaire JSON-compatible."""
        return {
            "statut": self.statut,
            "debut_utc": self.debut_utc,
            "fin_utc": self.fin_utc,
            "duree_secondes": self.duree_secondes,
            "details": dict(
                self.details
            ),
        }


@dataclass(slots=True)
class ContexteVeille:
    """
    Contexte mutable interne d'une exécution.

    Il centralise les données techniques du pipeline et évite de transmettre
    de nombreux paramètres indépendants entre les fonctions internes.
    """

    configuration: ConfigurationVeille
    dependances: DependancesVeille
    hooks: HooksVeille
    identifiant_execution: str
    debut_performance: float
    diagnostics: dict[str, Any]
    etapes: dict[str, EtatEtape]
    historique: tuple[Article | str, ...]
    articles_bruts: list[Article] = field(
        default_factory=list
    )
    rapport: dict[str, Any] = field(
        default_factory=dict
    )
    resultats: list[Article] = field(
        default_factory=list
    )
    resume: str = ""
    convergence: str = ""
    statistiques: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True, slots=True)
class SortieEtape(Generic[_T]):
    """Résultat interne d'une étape sécurisée."""

    valeur: _T
    reussie: bool


def _instant_utc_iso() -> str:
    """Retourne un instant UTC ISO 8601 sérialisable."""
    return datetime.now(
        timezone.utc
    ).isoformat(
        timespec="seconds"
    )


def _normaliser_configuration(
    configuration: ConfigurationVeille | None,
) -> ConfigurationVeille:
    """Valide et normalise la configuration."""
    config = configuration or ConfigurationVeille()

    if not isinstance(
        config,
        ConfigurationVeille,
    ):
        raise TypeError(
            "configuration doit être une instance de ConfigurationVeille "
            "ou None."
        )

    mode_tri = str(
        config.mode_tri or ""
    ).strip().casefold()

    if mode_tri not in MODES_TRI_AUTORISES:
        valeurs = ", ".join(
            sorted(
                MODES_TRI_AUTORISES
            )
        )
        raise ValueError(
            f"mode_tri invalide : {config.mode_tri!r}. "
            f"Valeurs autorisées : {valeurs}."
        )

    limite = config.limite

    if limite is not None:
        if isinstance(
            limite,
            bool,
        ) or not isinstance(
            limite,
            int,
        ):
            raise TypeError(
                "limite doit être un entier positif ou None."
            )

        if limite < 0:
            raise ValueError(
                "limite ne peut pas être négative."
            )

    if mode_tri != config.mode_tri:
        config = replace(
            config,
            mode_tri=mode_tri,
        )

    return config


def _normaliser_dependances(
    dependances: DependancesVeille | None,
) -> DependancesVeille:
    """Valide l'ensemble des dépendances."""
    resultat = dependances or DependancesVeille()

    if not isinstance(
        resultat,
        DependancesVeille,
    ):
        raise TypeError(
            "dependances doit être une instance de DependancesVeille ou None."
        )

    for nom in (
        "collecter",
        "preparer",
        "resumer",
        "converger",
        "statistiques",
        "exporter",
    ):
        if not callable(
            getattr(
                resultat,
                nom,
            )
        ):
            raise TypeError(
                f"La dépendance {nom!r} doit être appelable."
            )

    return resultat


def _normaliser_hooks(
    hooks: HooksVeille | None,
) -> HooksVeille:
    """Valide les hooks optionnels."""
    resultat = hooks or HooksVeille()

    if not isinstance(
        resultat,
        HooksVeille,
    ):
        raise TypeError(
            "hooks doit être une instance de HooksVeille ou None."
        )

    for nom in (
        "avant_etape",
        "apres_etape",
    ):
        hook = getattr(
            resultat,
            nom,
        )

        if hook is not None and not callable(
            hook
        ):
            raise TypeError(
                f"Le hook {nom!r} doit être appelable ou None."
            )

    return resultat


def _materialiser_historique(
    historique_articles: Iterable[Article | str] | None,
) -> tuple[Article | str, ...]:
    """Matérialise l'historique une seule fois."""
    if historique_articles is None:
        return ()

    if isinstance(
        historique_articles,
        (str, bytes, Mapping),
    ):
        raise TypeError(
            "historique_articles doit être un itérable d'articles, d'URL "
            "ou d'empreintes, et non une valeur unique."
        )

    try:
        return tuple(
            historique_articles
        )
    except TypeError as erreur:
        raise TypeError(
            "historique_articles doit être itérable."
        ) from erreur


def _decrire_erreur(
    erreur: BaseException,
) -> str:
    """Construit un message d'erreur borné."""
    message = str(
        erreur
    ).strip()
    description = type(
        erreur
    ).__name__

    if message:
        description = f"{description}: {message}"

    return description[:LONGUEUR_MAX_ERREUR]


def _enregistrer_erreur(
    contexte: ContexteVeille,
    etape: str,
    erreur: Exception,
    *,
    bloquante: bool,
) -> None:
    """Ajoute une erreur structurée et la journalise si demandé."""
    contexte.diagnostics.setdefault(
        "erreurs_pipeline",
        [],
    ).append(
        {
            "etape": etape,
            "erreur": _decrire_erreur(
                erreur
            ),
            "type": type(
                erreur
            ).__name__,
            "bloquante": bool(
                bloquante
            ),
            "instant_utc": _instant_utc_iso(),
        }
    )

    if contexte.configuration.journaliser_exceptions:
        LOGGER.exception(
            "Erreur pendant l'étape %s de la veille %s.",
            etape,
            contexte.identifiant_execution,
        )


def _enregistrer_avertissement(
    contexte: ContexteVeille,
    etape: str,
    message: str,
) -> None:
    """Ajoute un avertissement structuré."""
    contexte.diagnostics.setdefault(
        "avertissements_pipeline",
        [],
    ).append(
        {
            "etape": etape,
            "message": str(
                message
            )[:LONGUEUR_MAX_ERREUR],
            "instant_utc": _instant_utc_iso(),
        }
    )


def _initialiser_etapes() -> dict[str, EtatEtape]:
    """Crée le registre des étapes connues."""
    return {
        nom: EtatEtape()
        for nom in NOMS_ETAPES
    }


def _executer_hook(
    contexte: ContexteVeille,
    nom_hook: str,
    etape: str,
) -> None:
    """Exécute un hook sans fragiliser le pipeline."""
    hook = getattr(
        contexte.hooks,
        nom_hook,
    )

    if hook is None:
        return

    try:
        hook(
            etape,
            contexte,
        )

    except Exception as erreur:
        _enregistrer_avertissement(
            contexte,
            etape,
            f"Le hook {nom_hook!r} a échoué : {_decrire_erreur(erreur)}",
        )

        if contexte.configuration.strict:
            raise


def _marquer_etape_ignoree(
    contexte: ContexteVeille,
    etape: str,
    raison: str,
) -> None:
    """Marque explicitement une étape comme ignorée."""
    etat = contexte.etapes[etape]
    etat.statut = "ignoree"
    etat.debut_utc = None
    etat.fin_utc = _instant_utc_iso()
    etat.duree_secondes = 0.0
    etat.details["raison"] = raison


def _executer_etape(
    contexte: ContexteVeille,
    etape: str,
    fonction: Callable[[], _T],
    valeur_secours: _T,
) -> SortieEtape[_T]:
    """Exécute, mesure et sécurise une étape."""
    etat = contexte.etapes[etape]
    etat.statut = "en_cours"
    etat.debut_utc = _instant_utc_iso()
    debut = perf_counter()

    _executer_hook(
        contexte,
        "avant_etape",
        etape,
    )

    try:
        valeur = fonction()
        etat.statut = "reussie"

        return SortieEtape(
            valeur=valeur,
            reussie=True,
        )

    except Exception as erreur:
        etat.statut = "echec"
        etat.details["erreur"] = _decrire_erreur(
            erreur
        )

        _enregistrer_erreur(
            contexte,
            etape,
            erreur,
            bloquante=contexte.configuration.strict,
        )

        if contexte.configuration.strict:
            raise

        return SortieEtape(
            valeur=valeur_secours,
            reussie=False,
        )

    finally:
        etat.fin_utc = _instant_utc_iso()
        etat.duree_secondes = round(
            max(
                perf_counter() - debut,
                0.0,
            ),
            3,
        )

        _executer_hook(
            contexte,
            "apres_etape",
            etape,
        )


def _rapport_securise(
    contexte: ContexteVeille,
    rapport: Any,
) -> dict[str, Any]:
    """Garantit un rapport mutable."""
    if isinstance(
        rapport,
        Mapping,
    ):
        return dict(
            rapport
        )

    _enregistrer_avertissement(
        contexte,
        "collecte",
        "Le collecteur n'a pas retourné un mapping de rapport.",
    )

    return {
        "statut": "rapport_invalide",
        "erreurs": [
            "Le collecteur n'a pas retourné un dictionnaire de rapport.",
        ],
    }


def _articles_securises(
    contexte: ContexteVeille,
    articles: Any,
) -> list[Article]:
    """Garantit une liste d'articles exploitable."""
    if articles is None:
        return []

    if isinstance(
        articles,
        (str, bytes, Mapping),
    ):
        _enregistrer_avertissement(
            contexte,
            "collecte",
            "Le collecteur n'a pas retourné une collection d'articles.",
        )
        return []

    try:
        resultat = list(
            articles
        )
    except TypeError:
        _enregistrer_avertissement(
            contexte,
            "collecte",
            "Le résultat de collecte n'est pas itérable.",
        )
        return []

    nombre_invalides = sum(
        1
        for article in resultat
        if not isinstance(
            article,
            dict,
        )
    )

    if nombre_invalides:
        contexte.diagnostics["articles_bruts_invalides"] = nombre_invalides
        _enregistrer_avertissement(
            contexte,
            "collecte",
            f"{nombre_invalides} élément(s) collecté(s) seront ignorés "
            "car ils ne sont pas des dictionnaires.",
        )

    return resultat


def _erreur_pipeline_presente(
    contexte: ContexteVeille,
) -> bool:
    """Indique si au moins une erreur a été enregistrée."""
    return bool(
        contexte.diagnostics.get(
            "erreurs_pipeline",
            [],
        )
    )


def _statut_pipeline(
    contexte: ContexteVeille,
) -> str:
    """Déduit le statut global du pipeline."""
    erreurs = contexte.diagnostics.get(
        "erreurs_pipeline",
        [],
    )
    avertissements = contexte.diagnostics.get(
        "avertissements_pipeline",
        [],
    )

    if erreurs and not contexte.resultats:
        return "echec"

    if erreurs:
        return "partiel"

    if not contexte.resultats:
        return "vide"

    if avertissements:
        return "reussi_avec_avertissements"

    return "reussi"


def _raison_etape_ignoree(
    activee: bool,
    contenu_disponible: bool,
    traitements_autorises: bool,
    *,
    libelle_desactive: str,
    libelle_vide: str,
) -> str:
    """Produit une raison cohérente pour une étape ignorée."""
    if not activee:
        return libelle_desactive

    if not contenu_disponible:
        return libelle_vide

    if not traitements_autorises:
        return (
            "une erreur antérieure impose l'arrêt des traitements secondaires"
        )

    return "étape non exécutée"


def _finaliser_diagnostics(
    contexte: ContexteVeille,
) -> None:
    """Finalise les diagnostics globaux."""
    contexte.diagnostics["fin_utc"] = _instant_utc_iso()
    contexte.diagnostics["duree_totale_pipeline"] = round(
        max(
            perf_counter() - contexte.debut_performance,
            0.0,
        ),
        3,
    )
    contexte.diagnostics["nombre_erreurs"] = len(
        contexte.diagnostics["erreurs_pipeline"]
    )
    contexte.diagnostics["nombre_avertissements"] = len(
        contexte.diagnostics["avertissements_pipeline"]
    )
    contexte.diagnostics["statut_pipeline"] = _statut_pipeline(
        contexte
    )
    contexte.diagnostics["pipeline_reussi"] = contexte.diagnostics[
        "statut_pipeline"
    ] in {
        "reussi",
        "reussi_avec_avertissements",
        "vide",
    }
    contexte.diagnostics["etapes"] = {
        nom: etat.convertir()
        for nom, etat in contexte.etapes.items()
    }


def lancer_veille_complete(
    configuration: ConfigurationVeille | None = None,
    historique_articles: Iterable[Article | str] | None = None,
    dependances: DependancesVeille | None = None,
    hooks: HooksVeille | None = None,
) -> ResultatVeille:
    """
    Lance la veille complète.

    ``historique_articles`` peut contenir des articles complets, des URL ou
    des empreintes SHA-256.

    ``dependances`` permet de substituer les services lors des tests.

    ``hooks`` permet d'observer les étapes du pipeline sans modifier son
    comportement.

    L'appel sans argument reste compatible avec les versions précédentes.
    """
    config = _normaliser_configuration(
        configuration
    )
    services = _normaliser_dependances(
        dependances
    )
    hooks_valides = _normaliser_hooks(
        hooks
    )
    historique = _materialiser_historique(
        historique_articles
    )

    identifiant_execution = uuid4().hex

    diagnostics: dict[str, Any] = {
        "identifiant_execution": identifiant_execution,
        "debut_utc": _instant_utc_iso(),
        "mode_tri": config.mode_tri,
        "limite": config.limite,
        "export_demande": config.exporter,
        "resume_demande": config.generer_resume,
        "convergence_demandee": config.generer_convergence,
        "traiter_si_vide": config.traiter_si_vide,
        "erreur_si_vide": config.erreur_si_vide,
        "arreter_apres_erreur": config.arreter_apres_erreur,
        "strict": config.strict,
        "historique_fourni": bool(
            historique
        ),
        "taille_historique": len(
            historique
        ),
        "erreurs_pipeline": [],
        "avertissements_pipeline": [],
    }

    contexte = ContexteVeille(
        configuration=config,
        dependances=services,
        hooks=hooks_valides,
        identifiant_execution=identifiant_execution,
        debut_performance=perf_counter(),
        diagnostics=diagnostics,
        etapes=_initialiser_etapes(),
        historique=historique,
    )

    # 1. Collecte
    collecte = _executer_etape(
        contexte,
        "collecte",
        services.collecter,
        (
            [],
            {
                "statut": "erreur_collecte",
                "erreurs": [
                    "La collecte n'a pas pu être exécutée.",
                ],
            },
        ),
    )

    retour_collecte = collecte.valeur

    if (
        not isinstance(
            retour_collecte,
            tuple,
        )
        or len(
            retour_collecte
        ) != 2
    ):
        erreur = TypeError(
            "La collecte doit retourner un tuple (articles, rapport)."
        )
        _enregistrer_erreur(
            contexte,
            "collecte",
            erreur,
            bloquante=config.strict,
        )
        contexte.etapes["collecte"].statut = "echec"

        if config.strict:
            raise erreur

        retour_collecte = (
            [],
            {
                "statut": "retour_collecte_invalide",
                "erreurs": [
                    _decrire_erreur(
                        erreur
                    ),
                ],
            },
        )

    articles_collectes, rapport_collecte = retour_collecte
    contexte.articles_bruts = _articles_securises(
        contexte,
        articles_collectes,
    )
    contexte.rapport = _rapport_securise(
        contexte,
        rapport_collecte,
    )

    contexte.diagnostics["articles_bruts_pipeline"] = len(
        contexte.articles_bruts
    )
    contexte.etapes["collecte"].details["articles_bruts"] = len(
        contexte.articles_bruts
    )

    if config.inclure_rapport_collecte:
        contexte.diagnostics["rapport_collecte"] = dict(
            contexte.rapport
        )

    # 2. Préparation
    preparation = _executer_etape(
        contexte,
        "preparation",
        lambda: services.preparer(
            contexte.articles_bruts,
            limite=config.limite,
            mode_tri=config.mode_tri,
            historique_articles=contexte.historique,
        ),
        [],
    )

    contexte.resultats = preparation.valeur

    if not isinstance(
        contexte.resultats,
        list,
    ):
        erreur = TypeError(
            "preparer_articles() doit retourner une liste."
        )
        _enregistrer_erreur(
            contexte,
            "preparation",
            erreur,
            bloquante=config.strict,
        )
        contexte.etapes["preparation"].statut = "echec"

        if config.strict:
            raise erreur

        contexte.resultats = []

    contexte.diagnostics["articles_resultats_pipeline"] = len(
        contexte.resultats
    )
    contexte.diagnostics["pipeline_vide"] = not bool(
        contexte.resultats
    )
    contexte.etapes["preparation"].details["articles_retenus"] = len(
        contexte.resultats
    )

    if not contexte.resultats and config.erreur_si_vide:
        erreur_vide = RuntimeError(
            "La veille n'a retenu aucun article."
        )
        _enregistrer_erreur(
            contexte,
            "preparation",
            erreur_vide,
            bloquante=config.strict,
        )

        if config.strict:
            raise erreur_vide

    contenu_disponible = bool(
        contexte.resultats
    ) or config.traiter_si_vide

    traitements_autorises = not (
        config.arreter_apres_erreur
        and _erreur_pipeline_presente(
            contexte
        )
    )

    # 3. Résumé
    if (
        config.generer_resume
        and contenu_disponible
        and traitements_autorises
    ):
        sortie_resume = _executer_etape(
            contexte,
            "resume_executif",
            lambda: services.resumer(
                contexte.resultats
            ),
            "",
        )
        contexte.resume = str(
            sortie_resume.valeur or ""
        )

    else:
        _marquer_etape_ignoree(
            contexte,
            "resume_executif",
            _raison_etape_ignoree(
                config.generer_resume,
                contenu_disponible,
                traitements_autorises,
                libelle_desactive="désactivé par configuration",
                libelle_vide="aucun article à traiter",
            ),
        )

    # 4. Convergence
    if (
        config.generer_convergence
        and contenu_disponible
        and traitements_autorises
    ):
        sortie_convergence = _executer_etape(
            contexte,
            "convergence",
            lambda: services.converger(
                contexte.resultats
            ),
            "",
        )
        contexte.convergence = str(
            sortie_convergence.valeur or ""
        )

    else:
        _marquer_etape_ignoree(
            contexte,
            "convergence",
            _raison_etape_ignoree(
                config.generer_convergence,
                contenu_disponible,
                traitements_autorises,
                libelle_desactive="désactivée par configuration",
                libelle_vide="aucun article à traiter",
            ),
        )

    # 5. Statistiques
    sortie_statistiques = _executer_etape(
        contexte,
        "statistiques",
        lambda: services.statistiques(
            contexte.rapport,
            contexte.resultats,
        ),
        {
            "statut": "erreur_statistiques",
            "articles_recuperes": len(
                contexte.articles_bruts
            ),
            "articles_retenus": len(
                contexte.resultats
            ),
        },
    )

    contexte.statistiques = sortie_statistiques.valeur

    if not isinstance(
        contexte.statistiques,
        dict,
    ):
        erreur = TypeError(
            "construire_statistiques() doit retourner un dictionnaire."
        )
        _enregistrer_erreur(
            contexte,
            "statistiques",
            erreur,
            bloquante=config.strict,
        )
        contexte.etapes["statistiques"].statut = "echec"

        if config.strict:
            raise erreur

        contexte.statistiques = {
            "statut": "erreur_statistiques",
            "articles_recuperes": len(
                contexte.articles_bruts
            ),
            "articles_retenus": len(
                contexte.resultats
            ),
        }

    # 6. Exports
    contexte.statistiques["exports"] = {}

    export_autorise = not (
        config.arreter_apres_erreur
        and _erreur_pipeline_presente(
            contexte
        )
    )

    if (
        config.exporter
        and contenu_disponible
        and export_autorise
    ):
        sortie_exports = _executer_etape(
            contexte,
            "exports",
            lambda: services.exporter(
                contexte.resultats,
                contexte.rapport,
            ),
            {},
        )
        exports = sortie_exports.valeur

        if not isinstance(
            exports,
            Mapping,
        ):
            erreur = TypeError(
                "exporter_tous_formats() doit retourner un mapping."
            )
            _enregistrer_erreur(
                contexte,
                "exports",
                erreur,
                bloquante=config.strict,
            )
            contexte.etapes["exports"].statut = "echec"

            if config.strict:
                raise erreur

            exports = {}

        contexte.statistiques["exports"] = {
            str(
                format_export
            ): str(
                chemin
            )
            for format_export, chemin in exports.items()
            if chemin is not None
        }
        contexte.etapes["exports"].details["nombre_exports"] = len(
            contexte.statistiques["exports"]
        )

    else:
        _marquer_etape_ignoree(
            contexte,
            "exports",
            _raison_etape_ignoree(
                config.exporter,
                contenu_disponible,
                export_autorise,
                libelle_desactive="désactivés par configuration",
                libelle_vide="aucun article à exporter",
            ),
        )

    # 7. Finalisation
    _finaliser_diagnostics(
        contexte
    )

    contexte.statistiques["pipeline"] = contexte.diagnostics
    contexte.statistiques["identifiant_execution"] = (
        contexte.identifiant_execution
    )

    return (
        contexte.resultats,
        contexte.resume,
        contexte.convergence,
        contexte.statistiques,
    )


__all__ = [
    "ConfigurationVeille",
    "ContexteVeille",
    "DependancesVeille",
    "EtatEtape",
    "HooksVeille",
    "MODES_TRI_AUTORISES",
    "NOMS_ETAPES",
    "ResultatVeille",
    "SortieEtape",
    "lancer_veille_complete",
]