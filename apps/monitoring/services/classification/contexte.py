"""
Contexte partagé par les étapes du moteur de classification V3.

Ce module définit l'état de travail mutable utilisé pendant la classification
d'un article. Le texte exploitable est construit une seule fois, puis les
résultats intermédiaires sont conservés dans le même contexte.

Le contexte reste volontairement indépendant des règles métier : il stocke,
normalise, fusionne et expose les résultats sans décider de la classification.

Portée de la V3
---------------

Cette version aligne le contexte sur le pipeline V6 sans déplacer la logique
scientifique. Elle conserve toutes les API historiques, ajoute une façade
d'export stable attendue par ``EtatClassification``, des opérations de
remplacement explicites pour les producteurs officiels et un exécutant de
préparation directement enregistrable dans ``MoteurPipeline``.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable, Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, ClassVar, Final, TypeAlias

from .utils import construire_texte


Article: TypeAlias = Mapping[str, Any]
ResultatEtape: TypeAlias = dict[str, Any]
ExportClassification: TypeAlias = dict[str, Any]

VERSION_CONTEXTE: Final[str] = "3.0.0"


@dataclass(slots=True)
class ContexteClassification:
    """
    État de travail interne à la classification d'un article.

    Le texte fourni explicitement est prioritaire. Lorsqu'il est vide,
    ``construire_texte()`` est appelé une seule fois pendant l'initialisation.

    Toutes les collections reçues sont copiées et normalisées afin d'éviter
    qu'une modification extérieure altère silencieusement le contexte.
    """

    IMPORTANCE_MINIMALE: ClassVar[int] = 0
    IMPORTANCE_MAXIMALE: ClassVar[int] = 100

    CHAMPS_LISTES: ClassVar[tuple[str, ...]] = (
        "categories",
        "mots_categories",
        "one_health",
        "mots_one_health",
    )

    CHAMPS_RESULTATS: ClassVar[tuple[str, ...]] = (
        "preuve",
        "pertinence",
        "score",
        "decision",
        "explication",
    )

    CHAMPS_EXPORTES: ClassVar[tuple[str, ...]] = (
        *CHAMPS_LISTES,
        "importance",
        *CHAMPS_RESULTATS,
    )

    # Noms techniques utilisés par les contrats du pipeline V6. Cette table
    # reste locale afin d'éviter toute dépendance circulaire vers pipeline.py.
    CHAMPS_CONTRACTUELS: ClassVar[tuple[str, ...]] = (
        "article",
        "texte",
        *CHAMPS_EXPORTES,
    )

    PRODUCTEURS_OFFICIELS: ClassVar[dict[str, str]] = {
        "texte": "preparation",
        "categories": "categories",
        "mots_categories": "categories",
        "one_health": "one_health",
        "mots_one_health": "one_health",
        "preuve": "preuve",
        "pertinence": "pertinence",
        "importance": "importance",
        "score": "score",
        "decision": "decision",
        "explication": "explication",
    }

    article: Article
    texte: str = ""

    categories: list[str] = field(default_factory=list)
    mots_categories: list[str] = field(default_factory=list)

    one_health: list[str] = field(default_factory=list)
    mots_one_health: list[str] = field(default_factory=list)

    preuve: ResultatEtape = field(default_factory=dict)
    pertinence: ResultatEtape = field(default_factory=dict)
    importance: int = 0
    score: ResultatEtape = field(default_factory=dict)
    decision: ResultatEtape = field(default_factory=dict)
    explication: ResultatEtape = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Valide et normalise l'état initial du contexte."""
        if not isinstance(self.article, Mapping):
            raise TypeError(
                "article doit être un objet compatible avec Mapping."
            )

        # Le contexte devient propriétaire de sa copie d'entrée. Une mutation
        # extérieure ne peut donc pas altérer silencieusement les empreintes du
        # pipeline ou les résultats d'une classification en cours.
        self.article = deepcopy(dict(self.article))

        self.texte = self._normaliser_texte_initial(self.texte)
        self.importance = self._normaliser_importance(self.importance)

        for champ in self.CHAMPS_LISTES:
            setattr(
                self,
                champ,
                self._valeurs_uniques(getattr(self, champ)),
            )

        for champ in self.CHAMPS_RESULTATS:
            setattr(
                self,
                champ,
                self._normaliser_resultat(
                    getattr(self, champ),
                    nom_champ=champ,
                ),
            )

    def _normaliser_texte_initial(self, texte: Any) -> str:
        """Nettoie le texte fourni ou le construit depuis l'article."""
        if not isinstance(texte, str):
            raise TypeError("texte doit être une chaîne de caractères.")

        texte_normalise = self._nettoyer_libelle(texte)
        if texte_normalise:
            return texte_normalise

        return self._construire_texte_article()

    def _construire_texte_article(self) -> str:
        """Construit et valide le texte depuis l'article courant."""
        texte_construit = construire_texte(self.article)

        if not isinstance(texte_construit, str):
            raise TypeError(
                "construire_texte() doit retourner une chaîne de caractères."
            )

        return self._nettoyer_libelle(texte_construit)

    @classmethod
    def _normaliser_importance(cls, valeur: Any) -> int:
        """
        Convertit et borne l'importance dans l'intervalle autorisé.

        Une valeur absente, booléenne, infinie ou invalide devient zéro.
        """
        if isinstance(valeur, bool):
            return cls.IMPORTANCE_MINIMALE

        try:
            importance = int(valeur)
        except (TypeError, ValueError, OverflowError):
            return cls.IMPORTANCE_MINIMALE

        return min(
            max(importance, cls.IMPORTANCE_MINIMALE),
            cls.IMPORTANCE_MAXIMALE,
        )

    @staticmethod
    def _normaliser_resultat(
        valeur: Any,
        *,
        nom_champ: str,
    ) -> ResultatEtape:
        """Convertit un résultat d'étape en dictionnaire indépendant."""
        if valeur is None:
            return {}

        if not isinstance(valeur, Mapping):
            raise TypeError(
                f"{nom_champ} doit être un objet compatible avec Mapping."
            )

        return deepcopy(dict(valeur))

    @staticmethod
    def _iterer_valeurs(valeurs: Any) -> Iterable[Any]:
        """
        Transforme une valeur isolée ou une collection en itérable sûr.

        Les chaînes et les octets sont traités comme une valeur unique.
        Les dictionnaires sont également traités comme une valeur unique afin
        d'éviter d'ajouter accidentellement leurs clés comme libellés.
        """
        if valeurs is None:
            return ()

        if isinstance(valeurs, (str, bytes, Mapping)):
            return (valeurs,)

        if isinstance(valeurs, Iterable):
            return valeurs

        return (valeurs,)

    @staticmethod
    def _nettoyer_libelle(valeur: Any) -> str:
        """Convertit une valeur en texte propre avec espaces normalisés."""
        if valeur is None:
            return ""

        if isinstance(valeur, bytes):
            texte = valeur.decode("utf-8", errors="replace")
        else:
            texte = str(valeur)

        return " ".join(texte.split())

    @staticmethod
    def _cle_libelle(texte: str) -> str:
        """
        Construit une clé de comparaison insensible à la casse et aux accents.
        """
        sans_accents = "".join(
            caractere
            for caractere in unicodedata.normalize("NFKD", texte)
            if not unicodedata.combining(caractere)
        )
        return sans_accents.casefold()

    @classmethod
    def _valeurs_uniques(cls, valeurs: Any) -> list[str]:
        """
        Nettoie des libellés et supprime les doublons.

        L'ordre d'origine est conservé. La comparaison ignore la casse,
        les accents et les variations d'espacement.
        """
        resultat: list[str] = []
        cles_vues: set[str] = set()

        for valeur in cls._iterer_valeurs(valeurs):
            if isinstance(valeur, Mapping):
                raise TypeError(
                    "Une collection de libellés ne peut pas contenir "
                    "directement un objet Mapping."
                )

            texte = cls._nettoyer_libelle(valeur)
            if not texte:
                continue

            cle = cls._cle_libelle(texte)
            if cle in cles_vues:
                continue

            cles_vues.add(cle)
            resultat.append(texte)

        return resultat

    @classmethod
    def _fusionner_valeurs(
        cls,
        valeurs_existantes: Iterable[Any],
        nouvelles_valeurs: Any,
    ) -> list[str]:
        """Fusionne deux ensembles ordonnés de libellés sans doublon."""
        return cls._valeurs_uniques(
            (
                *valeurs_existantes,
                *cls._iterer_valeurs(nouvelles_valeurs),
            )
        )

    @staticmethod
    def _fusionner_dictionnaires(
        actuel: Mapping[str, Any],
        ajout: Mapping[str, Any],
        *,
        remplacer: bool,
    ) -> ResultatEtape:
        """Fusionne récursivement deux mappings indépendants."""
        resultat = deepcopy(dict(actuel))

        for cle, nouvelle_valeur in ajout.items():
            valeur_actuelle = resultat.get(cle)

            if (
                isinstance(valeur_actuelle, Mapping)
                and isinstance(nouvelle_valeur, Mapping)
            ):
                resultat[cle] = (
                    ContexteClassification._fusionner_dictionnaires(
                        valeur_actuelle,
                        nouvelle_valeur,
                        remplacer=remplacer,
                    )
                )
            elif remplacer or cle not in resultat:
                resultat[cle] = deepcopy(nouvelle_valeur)

        return resultat

    @property
    def est_vide(self) -> bool:
        """Indique si aucun texte exploitable n'a pu être construit."""
        return not self.texte

    @property
    def a_des_resultats(self) -> bool:
        """Indique si au moins une étape a produit un résultat."""
        return bool(
            any(getattr(self, champ) for champ in self.CHAMPS_LISTES)
            or self.importance
            or any(getattr(self, champ) for champ in self.CHAMPS_RESULTATS)
        )

    @property
    def etapes_renseignees(self) -> tuple[str, ...]:
        """Retourne les étapes qui possèdent actuellement un résultat."""
        return tuple(
            champ
            for champ in self.CHAMPS_RESULTATS
            if getattr(self, champ)
        )

    def reconstruire_texte(self, *, forcer: bool = False) -> str:
        """
        Reconstruit le texte depuis l'article.

        Sans ``forcer``, un texte déjà présent est conservé.
        """
        if forcer or self.est_vide:
            self.texte = self._construire_texte_article()

        return self.texte

    def ajouter_categories(
        self,
        categories: Any,
        mots_detectes: Any = (),
    ) -> None:
        """Ajoute des catégories et leurs termes déclencheurs sans doublon."""
        self.categories = self._fusionner_valeurs(
            self.categories,
            categories,
        )
        self.mots_categories = self._fusionner_valeurs(
            self.mots_categories,
            mots_detectes,
        )

    def ajouter_one_health(
        self,
        dimensions: Any,
        mots_detectes: Any = (),
    ) -> None:
        """Ajoute des dimensions One Health et leurs termes sans doublon."""
        self.one_health = self._fusionner_valeurs(
            self.one_health,
            dimensions,
        )
        self.mots_one_health = self._fusionner_valeurs(
            self.mots_one_health,
            mots_detectes,
        )

    def definir_categories(
        self,
        categories: Any,
        mots_detectes: Any = (),
    ) -> None:
        """Remplace les sorties officielles de l'étape ``categories``.

        Cette opération complète ``ajouter_categories`` : elle est adaptée à
        l'exécutant officiel, qui doit produire un résultat autonome plutôt que
        fusionner involontairement avec un état antérieur.
        """
        self.categories = self._valeurs_uniques(categories)
        self.mots_categories = self._valeurs_uniques(mots_detectes)

    def definir_one_health(
        self,
        dimensions: Any,
        mots_detectes: Any = (),
    ) -> None:
        """Remplace les sorties officielles de l'étape ``one_health``."""
        self.one_health = self._valeurs_uniques(dimensions)
        self.mots_one_health = self._valeurs_uniques(mots_detectes)

    def definir_importance(self, valeur: Any) -> None:
        """Définit une importance normalisée et bornée."""
        self.importance = self._normaliser_importance(valeur)

    def definir_resultat(
        self,
        nom_etape: str,
        resultat: Mapping[str, Any] | None,
    ) -> None:
        """Remplace de façon contrôlée le résultat d'une étape."""
        self._verifier_nom_etape(nom_etape)
        setattr(
            self,
            nom_etape,
            self._normaliser_resultat(
                resultat,
                nom_champ=nom_etape,
            ),
        )

    def fusionner_resultat(
        self,
        nom_etape: str,
        resultat: Mapping[str, Any] | None,
        *,
        remplacer: bool = True,
        recursif: bool = True,
    ) -> None:
        """
        Fusionne des données dans le résultat d'une étape.

        ``recursif`` permet de préserver les sous-dictionnaires existants.
        """
        self._verifier_nom_etape(nom_etape)

        ajout = self._normaliser_resultat(
            resultat,
            nom_champ=nom_etape,
        )
        actuel = getattr(self, nom_etape)

        if recursif:
            fusion = self._fusionner_dictionnaires(
                actuel,
                ajout,
                remplacer=remplacer,
            )
        elif remplacer:
            fusion = {**deepcopy(actuel), **ajout}
        else:
            fusion = {**ajout, **deepcopy(actuel)}

        setattr(self, nom_etape, fusion)

    def effacer_resultat(self, nom_etape: str) -> None:
        """Efface le résultat d'une seule étape."""
        self._verifier_nom_etape(nom_etape)
        getattr(self, nom_etape).clear()

    @classmethod
    def _verifier_nom_etape(cls, nom_etape: str) -> None:
        """Vérifie qu'un nom correspond à une étape enregistrable."""
        if nom_etape not in cls.CHAMPS_RESULTATS:
            noms_valides = ", ".join(cls.CHAMPS_RESULTATS)
            raise ValueError(
                f"Étape inconnue : {nom_etape!r}. "
                f"Valeurs autorisées : {noms_valides}."
            )

    def contient_donnee(self, nom: str) -> bool:
        """Indique si une donnée contractuelle appartient au contexte."""
        return str(nom or "").strip() in self.CHAMPS_CONTRACTUELS

    def obtenir_donnee(
        self,
        nom: str,
        *,
        copie: bool = False,
    ) -> Any:
        """Retourne une donnée contractuelle après validation de son nom."""
        nom_normalise = str(nom or "").strip()
        if not self.contient_donnee(nom_normalise):
            valeurs = ", ".join(self.CHAMPS_CONTRACTUELS)
            raise KeyError(
                f"Donnée contextuelle inconnue : {nom!r}. "
                f"Valeurs autorisées : {valeurs}."
            )
        valeur = getattr(self, nom_normalise)
        return deepcopy(valeur) if copie else valeur

    @classmethod
    def producteur_officiel(cls, nom: str) -> str | None:
        """Retourne l'étape propriétaire d'une sortie contextuelle."""
        return cls.PRODUCTEURS_OFFICIELS.get(str(nom or "").strip())

    @property
    def sorties_renseignees(self) -> tuple[str, ...]:
        """Retourne toutes les sorties contextuelles actuellement renseignées."""
        return tuple(
            champ
            for champ in self.CHAMPS_EXPORTES
            if bool(getattr(self, champ))
        )

    def reinitialiser_resultats(self) -> None:
        """Efface les résultats sans reconstruire le texte de l'article."""
        for champ in self.CHAMPS_LISTES:
            getattr(self, champ).clear()

        for champ in self.CHAMPS_RESULTATS:
            getattr(self, champ).clear()

        self.importance = self.IMPORTANCE_MINIMALE

    def exporter_resultats(self) -> ExportClassification:
        """Retourne une copie profonde des résultats de classification."""
        return {
            champ: deepcopy(getattr(self, champ))
            for champ in self.CHAMPS_EXPORTES
        }

    def exporter_contexte(
        self,
        *,
        inclure_article: bool = False,
        inclure_texte: bool = False,
    ) -> ExportClassification:
        """Exporte les résultats et, facultativement, les données d'entrée."""
        export = self.exporter_resultats()

        if inclure_article:
            export["article"] = deepcopy(dict(self.article))

        if inclure_texte:
            export["texte"] = self.texte

        return export

    def exporter(self) -> ExportClassification:
        """Façade d'export stable utilisée par ``EtatClassification``.

        Contrairement à ``exporter_resultats()``, cette vue inclut les données
        d'entrée nécessaires aux empreintes déterministes et à la persistance.
        """
        return self.exporter_contexte(
            inclure_article=True,
            inclure_texte=True,
        )

    @classmethod
    def depuis_export(
        cls,
        donnees: Mapping[str, Any],
    ) -> ContexteClassification:
        """Reconstruit un contexte indépendant depuis une exportation complète."""
        if not isinstance(donnees, Mapping):
            raise TypeError("donnees doit être un objet compatible avec Mapping.")

        article = donnees.get("article", {})
        texte = donnees.get("texte", "")
        resultats = {
            champ: deepcopy(donnees.get(champ, [] if champ in cls.CHAMPS_LISTES else {}))
            for champ in cls.CHAMPS_EXPORTES
            if champ != "importance"
        }
        resultats["importance"] = donnees.get(
            "importance",
            cls.IMPORTANCE_MINIMALE,
        )
        return cls(
            article=article,
            texte=texte,
            **resultats,
        )

    def copier(self) -> ContexteClassification:
        """Crée une copie entièrement indépendante du contexte courant."""
        return ContexteClassification(
            article=deepcopy(dict(self.article)),
            texte=self.texte,
            **self.exporter_resultats(),
        )

def executer_preparation(etat: Any) -> None:
    """Exécutant officiel de l'étape ``preparation`` pour le pipeline V6.

    L'import de ``EtatClassification`` est volontairement évité afin de ne pas
    créer de cycle entre ``contexte.py`` et ``pipeline.py``. La validation
    structurelle demeure stricte : l'objet doit exposer un contexte compatible.
    """
    contexte = getattr(etat, "contexte", None)
    if not isinstance(contexte, ContexteClassification):
        raise TypeError(
            "etat doit exposer un contexte de type ContexteClassification."
        )
    contexte.reconstruire_texte()


__all__ = [
    "Article",
    "ContexteClassification",
    "VERSION_CONTEXTE",
    "executer_preparation",
    "ExportClassification",
    "ResultatEtape",
]