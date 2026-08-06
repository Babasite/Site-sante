"""Détection déterministe des catégories d'un article de veille V2.

Ce module est autonome et ne dépend d'aucun service d'IA. Il reprend les
règles historiques du classificateur afin de permettre une extraction sans
régression, tout en exposant une API plus simple à tester.
"""

from __future__ import annotations

import html
import re
import unicodedata
from collections.abc import Iterable, Mapping
from functools import lru_cache
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .pipeline import EtatClassification

VERSION_CATEGORIES = "2.0.0"

REGLES_CATEGORIES = {
    "Vaccination": (
        "vaccine",
        "vaccination",
        "vaccinated",
        "booster dose",
        "immunization",
        "immunisation",
        "mrna vaccine",
        "messenger rna vaccine",
        "vaccine candidate",
        "vaccine efficacy",
        "vaccine effectiveness",
        "vaccin",
        "vaccination",
        "dose de rappel",
        "candidat vaccin",
        "efficacite vaccinale",
    ),
    "Traitements": (
        "treatment",
        "therapy",
        "therapeutic",
        "drug treatment",
        "medication",
        "antiviral",
        "antibiotic treatment",
        "antifungal treatment",
        "antiparasitic treatment",
        "immunotherapy",
        "gene therapy",
        "cell therapy",
        "monoclonal antibody",
        "small molecule inhibitor",
        "traitement",
        "therapie",
        "medicament",
        "antiviral",
        "antibiotherapie",
        "immunotherapie",
        "therapie genique",
        "anticorps monoclonal",
    ),
    "Maladies infectieuses": (
        "infectious disease",
        "infectious diseases",
        "human infection",
        "community acquired infection",
        "healthcare associated infection",
        "hospital acquired infection",
        "outbreak",
        "epidemic",
        "pandemic",
        "disease transmission",
        "pathogen transmission",
        "zoonosis",
        "zoonotic disease",
        "emerging pathogen",
        "reemerging pathogen",
        "maladie infectieuse",
        "maladies infectieuses",
        "infection humaine",
        "flambee epidemique",
        "epidemie",
        "pandemie",
        "transmission infectieuse",
        "zoonose",
        "agent pathogene emergent",
    ),
    "Recommandations": (
        "clinical guideline",
        "practice guideline",
        "public health guideline",
        "official recommendation",
        "updated recommendation",
        "consensus statement",
        "position statement",
        "official update",
        "public health advice",
        "guidance document",
        "recommandation officielle",
        "recommandations de pratique",
        "recommandation clinique",
        "mise a jour officielle",
        "avis de sante publique",
        "document d orientation",
    ),
    "Essais cliniques": (
        "clinical trial",
        "controlled trial",
        "randomized trial",
        "randomised trial",
        "randomized controlled trial",
        "randomised controlled trial",
        "placebo controlled",
        "double blind trial",
        "single blind trial",
        "phase 1 trial",
        "phase 2 trial",
        "phase 3 trial",
        "phase 4 trial",
        "phase 1",
        "phase 2",
        "phase 3",
        "phase 4",
        "phase i trial",
        "phase ii trial",
        "phase iii trial",
        "phase iv trial",
        "essai clinique",
        "essai controle",
        "essai randomise",
        "essai comparatif randomise",
        "controle par placebo",
        "essai en double aveugle",
        "essai de phase i",
        "essai de phase ii",
        "essai de phase iii",
        "essai de phase iv",
    ),
    "Revues scientifiques": (
        "systematic review",
        "meta analysis",
        "umbrella review",
        "scoping review",
        "rapid review",
        "living systematic review",
        "narrative review",
        "revue systematique",
        "meta analyse",
        "revue parapluie",
        "revue de portee",
        "revue rapide",
        "revue systematique vivante",
        "revue narrative",
    ),
    "IA médicale": (
        "artificial intelligence",
        "machine learning",
        "deep learning",
        "large language model",
        "foundation model",
        "neural network",
        "computer aided diagnosis",
        "clinical decision support algorithm",
        "intelligence artificielle",
        "apprentissage automatique",
        "apprentissage profond",
        "grand modele de langage",
        "modele de fondation",
        "reseau de neurones",
        "diagnostic assiste par ordinateur",
    ),
    "Santé environnementale": (
        "environmental health",
        "environmental exposure",
        "air pollution",
        "water pollution",
        "soil pollution",
        "climate change",
        "extreme heat",
        "heatwave",
        "wildfire smoke",
        "pesticide exposure",
        "pfas exposure",
        "microplastic exposure",
        "air quality",
        "drinking water quality",
        "sante environnementale",
        "exposition environnementale",
        "pollution de l air",
        "pollution de l eau",
        "pollution des sols",
        "changement climatique",
        "chaleur extreme",
        "vague de chaleur",
        "fumee d incendie",
        "exposition aux pesticides",
        "qualite de l air",
        "qualite de l eau potable",
    ),
    "Santé animale": (
        "veterinary medicine",
        "veterinary health",
        "animal health",
        "livestock health",
        "wildlife health",
        "poultry disease",
        "cattle disease",
        "swine disease",
        "equine disease",
        "companion animal disease",
        "avian influenza in birds",
        "veterinary surveillance",
        "medecine veterinaire",
        "sante veterinaire",
        "sante animale",
        "sante du betail",
        "sante de la faune sauvage",
        "maladie aviaire",
        "maladie porcine",
        "maladie bovine",
        "surveillance veterinaire",
    ),
    "Prévention": (
        "disease prevention",
        "preventive intervention",
        "screening program",
        "screening strategy",
        "infection prevention",
        "infection control",
        "public health measure",
        "risk reduction",
        "harm reduction",
        "contact tracing",
        "quarantine measure",
        "isolation measure",
        "prevention des maladies",
        "intervention preventive",
        "programme de depistage",
        "strategie de depistage",
        "prevention des infections",
        "controle des infections",
        "mesure de sante publique",
        "reduction des risques",
        "tracage des contacts",
    ),
    "Diagnostic": (
        "diagnostic test",
        "diagnostic accuracy",
        "diagnostic performance",
        "sensitivity and specificity",
        "point of care test",
        "rapid diagnostic test",
        "molecular diagnosis",
        "biomarker validation",
        "test diagnostique",
        "precision diagnostique",
        "performance diagnostique",
        "sensibilite et specificite",
        "test au point de soin",
        "test diagnostique rapide",
        "diagnostic moleculaire",
        "validation de biomarqueur",
    ),
    "Antibiorésistance": (
        "antimicrobial resistance",
        "antibiotic resistance",
        "multidrug resistant",
        "extensively drug resistant",
        "carbapenem resistant",
        "methicillin resistant",
        "antimicrobial stewardship",
        "resistance aux antimicrobiens",
        "resistance aux antibiotiques",
        "multiresistant",
        "resistant aux carbapenemes",
        "bon usage des antimicrobiens",
    ),
}

CHAMPS_TEXTE = (
    ("titre", "title", "headline"),
    ("resume", "résumé", "abstract", "summary", "description"),
    ("contenu", "content", "texte", "body", "full_text", "fulltext"),
    ("mots_cles", "mots-clés", "keywords", "tags", "mesh_terms"),
)


@lru_cache(maxsize=8192)
def normaliser_chaine(texte: str) -> str:
    """Normalise une chaîne pour rendre les comparaisons reproductibles."""
    texte_normalise = unicodedata.normalize("NFKD", texte.lower())
    texte_sans_accents = "".join(
        caractere
        for caractere in texte_normalise
        if not unicodedata.combining(caractere)
    )
    texte_alphanumerique = re.sub(r"[^a-z0-9]+", " ", texte_sans_accents)
    return " ".join(texte_alphanumerique.split())


def normaliser(texte: Any) -> str:
    return normaliser_chaine(str(texte or ""))


@lru_cache(maxsize=8192)
def compiler_expression(expression: str) -> re.Pattern[str]:
    """Compile une expression avec des limites alphanumériques strictes."""
    motif = rf"(?<![a-z0-9]){re.escape(expression)}(?![a-z0-9])"
    return re.compile(motif)


def contient_expression(texte: str, expression: str) -> bool:
    if not texte or not expression:
        return False
    return compiler_expression(expression).search(texte) is not None


def aplatir_valeur(valeur: Any) -> str:
    """Convertit récursivement les valeurs RSS/API en texte stable."""
    if valeur is None:
        return ""
    if isinstance(valeur, str):
        sans_html = re.sub(r"<[^>]+>", " ", html.unescape(valeur))
        return " ".join(sans_html.split())
    if isinstance(valeur, Mapping):
        return " ".join(
            morceau
            for morceau in (aplatir_valeur(v) for v in valeur.values())
            if morceau
        )
    if isinstance(valeur, Iterable) and not isinstance(valeur, (bytes, bytearray)):
        return " ".join(
            morceau
            for morceau in (aplatir_valeur(v) for v in valeur)
            if morceau
        )
    return str(valeur)


def extraire_champ(article: Mapping[str, Any], noms: Iterable[str]) -> Any:
    """Retourne la première valeur non vide parmi plusieurs alias."""
    for nom in noms:
        valeur = article.get(nom)
        if aplatir_valeur(valeur).strip():
            return valeur
    return ""


def construire_texte(article: Mapping[str, Any] | None) -> str:
    """Construit le corpus utilisé pour la catégorisation."""
    article = article if isinstance(article, Mapping) else {}
    champs = (
        extraire_champ(article, alias)
        for alias in CHAMPS_TEXTE
    )
    texte_brut = " ".join(aplatir_valeur(champ) for champ in champs)
    return normaliser(texte_brut)


def detecter_categories_dans_texte(texte: str) -> tuple[list[str], list[str]]:
    """Détecte les catégories et les expressions responsables du résultat."""
    texte_normalise = normaliser(texte)
    categories: list[str] = []
    mots_detectes: list[str] = []

    for categorie, expressions in REGLES_CATEGORIES.items():
        correspondances = [
            expression
            for expression in expressions
            if contient_expression(texte_normalise, normaliser(expression))
        ]
        if correspondances:
            categories.append(categorie)
            mots_detectes.extend(correspondances)

    # Ordre stable et suppression des doublons sans perdre l'ordre métier.
    mots_uniques = list(dict.fromkeys(mots_detectes))
    return categories, mots_uniques


def detecter_categories(
    article: Mapping[str, Any] | None,
) -> tuple[list[str], list[str]]:
    """API principale compatible avec le comportement historique."""
    return detecter_categories_dans_texte(construire_texte(article))


def analyser_categories(article: Mapping[str, Any] | None) -> dict[str, Any]:
    """Retour explicable pratique pour les tests et l'orchestrateur."""
    categories, mots_detectes = detecter_categories(article)
    return {
        "categories": categories,
        "mots_categories": mots_detectes,
    }


def categories_detectees(
    valeur: Mapping[str, Any] | Iterable[str] | None,
) -> tuple[str, ...]:
    """Retourne les catégories présentes sous une forme immuable et stable."""
    if valeur is None:
        return ()
    if isinstance(valeur, Mapping):
        valeur = valeur.get("categories", ())
    valeurs: Iterable[Any] = (valeur,) if isinstance(valeur, str) else valeur
    resultat: list[str] = []
    cles_vues: set[str] = set()
    for categorie in valeurs:
        libelle = " ".join(str(categorie or "").split())
        if not libelle:
            continue
        cle = normaliser(libelle)
        if cle in cles_vues:
            continue
        cles_vues.add(cle)
        resultat.append(libelle)
    return tuple(resultat)


def contient_categorie(
    valeur: Mapping[str, Any] | Iterable[str] | None,
    categorie: str,
) -> bool:
    """Teste la présence d'une catégorie sans dépendre de sa casse ou accents."""
    cible = normaliser(categorie)
    return bool(cible) and any(
        normaliser(element) == cible for element in categories_detectees(valeur)
    )


def statistiques_categories(
    valeur: Mapping[str, Any] | None = None,
    *,
    categories: Iterable[str] | None = None,
    mots_detectes: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Produit des statistiques techniques sans modifier le résultat métier."""
    if valeur is not None:
        categories = valeur.get("categories", categories or ())
        mots_detectes = valeur.get("mots_categories", mots_detectes or ())
    categories_stables = categories_detectees(categories)
    mots_stables = tuple(dict.fromkeys(
        mot for mot in (" ".join(str(item or "").split()) for item in (mots_detectes or ()))
        if mot
    ))
    return {
        "nombre_categories": len(categories_stables),
        "nombre_expressions": len(mots_stables),
        "categories": list(categories_stables),
        "mots_categories": list(mots_stables),
    }


def executer(etat: "EtatClassification") -> None:
    """Exécute l'étape officielle ``categories`` du pipeline V6.

    Le pipeline gère le cycle de vie. Ce module applique uniquement ses règles
    métier et écrit les sorties ``categories`` et ``mots_categories``.
    """
    contexte = getattr(etat, "contexte", None)
    if contexte is None:
        raise TypeError("etat doit exposer un attribut contexte.")
    texte = getattr(contexte, "texte", None)
    if not isinstance(texte, str):
        raise TypeError("etat.contexte.texte doit être une chaîne de caractères.")

    categories, mots_detectes = detecter_categories_dans_texte(texte)
    definir_categories = getattr(contexte, "definir_categories", None)
    if callable(definir_categories):
        definir_categories(categories, mots_detectes)
    else:
        contexte.categories = list(categories)
        contexte.mots_categories = list(mots_detectes)

    audit = getattr(etat, "audit", None)
    enregistrer = getattr(audit, "enregistrer", None)
    if callable(enregistrer):
        enregistrer(
            "categories_calculees",
            donnees={
                "version_module": VERSION_CATEGORIES,
                **statistiques_categories(
                    categories=categories,
                    mots_detectes=mots_detectes,
                ),
            },
        )


executer_categories = executer


__all__ = [
    "REGLES_CATEGORIES",
    "VERSION_CATEGORIES",
    "analyser_categories",
    "categories_detectees",
    "construire_texte",
    "contient_categorie",
    "detecter_categories",
    "detecter_categories_dans_texte",
    "executer",
    "executer_categories",
    "statistiques_categories",
]