"""
Configuration centrale du moteur de veille V2 de Découverte Santé.

Ce module contient uniquement la configuration transversale du moteur :

- identité de l'application ;
- activation et ordre des collecteurs ;
- paramètres transmis aux collecteurs ;
- limites globales ;
- règles de filtrage et de classement ;
- chemins de stockage et d'export ;
- variables d'environnement ;
- validation de la configuration.

Les configurations propres à chaque source restent dans leurs modules :

- pubmed.py ;
- has.py ;
- anses.py ;
- sante_publique_france.py ;
- inserm.py.

Aucun collecteur n'est importé ici afin d'éviter les dépendances
circulaires. Les fonctions sont désignées par leur module et leur nom,
puis chargées par l'orchestrateur.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any
import os


# ============================================================
# IDENTITÉ DU PROJET
# ============================================================

NOM_APPLICATION = "Découverte Santé"
NOM_MOTEUR = "Moteur de veille V2"
VERSION_MOTEUR = "2.0.0"

DESCRIPTION_APPLICATION = (
    "Veille scientifique, sanitaire et institutionnelle "
    "pour Découverte Santé."
)

LANGUE_PAR_DEFAUT = "fr"
FUSEAU_HORAIRE = "Europe/Paris"

ENCODAGE_PAR_DEFAUT = "utf-8"

USER_AGENT = (
    "Decouverte-Sante/"
    f"{VERSION_MOTEUR} "
    "(veille scientifique et sanitaire)"
)


# ============================================================
# LECTURE DES VARIABLES D'ENVIRONNEMENT
# ============================================================

def lire_chaine_environnement(
    nom: str,
    valeur_par_defaut: str = "",
) -> str:
    """
    Lit une variable d'environnement sous forme de chaîne.

    Les espaces placés au début et à la fin sont supprimés.
    """
    return os.getenv(
        nom,
        valeur_par_defaut,
    ).strip()


def lire_entier_environnement(
    nom: str,
    valeur_par_defaut: int,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    """
    Lit une variable d'environnement entière.

    En cas de valeur absente ou invalide, la valeur par défaut
    est utilisée. Les bornes sont appliquées quand elles existent.
    """
    valeur_brute = os.getenv(nom)

    try:
        valeur = (
            int(valeur_brute)
            if valeur_brute is not None
            else int(valeur_par_defaut)
        )

    except (
        TypeError,
        ValueError,
    ):
        valeur = int(valeur_par_defaut)

    if minimum is not None:
        valeur = max(
            minimum,
            valeur,
        )

    if maximum is not None:
        valeur = min(
            maximum,
            valeur,
        )

    return valeur


def lire_flottant_environnement(
    nom: str,
    valeur_par_defaut: float,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    """
    Lit une variable d'environnement décimale.
    """
    valeur_brute = os.getenv(nom)

    try:
        valeur = (
            float(valeur_brute)
            if valeur_brute is not None
            else float(valeur_par_defaut)
        )

    except (
        TypeError,
        ValueError,
    ):
        valeur = float(valeur_par_defaut)

    if minimum is not None:
        valeur = max(
            minimum,
            valeur,
        )

    if maximum is not None:
        valeur = min(
            maximum,
            valeur,
        )

    return valeur


def lire_booleen_environnement(
    nom: str,
    valeur_par_defaut: bool,
) -> bool:
    """
    Lit une variable d'environnement booléenne.

    Valeurs reconnues comme vraies :
    1, true, yes, oui, on, active, actif.

    Valeurs reconnues comme fausses :
    0, false, no, non, off, inactive, inactif.
    """
    valeur_brute = os.getenv(nom)

    if valeur_brute is None:
        return valeur_par_defaut

    valeur = valeur_brute.strip().lower()

    valeurs_vraies = {
        "1",
        "true",
        "yes",
        "oui",
        "on",
        "active",
        "actif",
    }

    valeurs_fausses = {
        "0",
        "false",
        "no",
        "non",
        "off",
        "inactive",
        "inactif",
    }

    if valeur in valeurs_vraies:
        return True

    if valeur in valeurs_fausses:
        return False

    return valeur_par_defaut


# ============================================================
# CHEMINS DU PROJET
# ============================================================

REPERTOIRE_MODULE = Path(__file__).resolve().parent

REPERTOIRE_PROJET = Path(
    lire_chaine_environnement(
        "DECOUVERTE_SANTE_REPERTOIRE_PROJET",
        str(REPERTOIRE_MODULE),
    )
).expanduser().resolve()

REPERTOIRE_DONNEES = Path(
    lire_chaine_environnement(
        "DECOUVERTE_SANTE_REPERTOIRE_DONNEES",
        str(REPERTOIRE_PROJET / "donnees"),
    )
).expanduser().resolve()

REPERTOIRE_EXPORTS = Path(
    lire_chaine_environnement(
        "DECOUVERTE_SANTE_REPERTOIRE_EXPORTS",
        str(REPERTOIRE_PROJET / "exports"),
    )
).expanduser().resolve()

REPERTOIRE_JOURNAUX = Path(
    lire_chaine_environnement(
        "DECOUVERTE_SANTE_REPERTOIRE_JOURNAUX",
        str(REPERTOIRE_PROJET / "journaux"),
    )
).expanduser().resolve()

REPERTOIRE_CACHE = Path(
    lire_chaine_environnement(
        "DECOUVERTE_SANTE_REPERTOIRE_CACHE",
        str(REPERTOIRE_PROJET / "cache"),
    )
).expanduser().resolve()

FICHIER_ETAT = Path(
    lire_chaine_environnement(
        "DECOUVERTE_SANTE_FICHIER_ETAT",
        str(REPERTOIRE_DONNEES / "etat_veille.json"),
    )
).expanduser().resolve()

FICHIER_HISTORIQUE = Path(
    lire_chaine_environnement(
        "DECOUVERTE_SANTE_FICHIER_HISTORIQUE",
        str(REPERTOIRE_DONNEES / "historique_articles.json"),
    )
).expanduser().resolve()

FICHIER_JOURNAL = Path(
    lire_chaine_environnement(
        "DECOUVERTE_SANTE_FICHIER_JOURNAL",
        str(REPERTOIRE_JOURNAUX / "veille.log"),
    )
).expanduser().resolve()


def creer_repertoires() -> None:
    """
    Crée les répertoires nécessaires au fonctionnement du moteur.

    Cette fonction n'est pas exécutée automatiquement à l'import.
    L'orchestrateur doit l'appeler au démarrage.
    """
    for repertoire in (
        REPERTOIRE_DONNEES,
        REPERTOIRE_EXPORTS,
        REPERTOIRE_JOURNAUX,
        REPERTOIRE_CACHE,
    ):
        repertoire.mkdir(
            parents=True,
            exist_ok=True,
        )


# ============================================================
# PARAMÈTRES RÉSEAU GLOBAUX
# ============================================================

TIMEOUT_HTTP = lire_entier_environnement(
    "DECOUVERTE_SANTE_TIMEOUT_HTTP",
    30,
    minimum=5,
    maximum=180,
)

NOMBRE_TENTATIVES_HTTP = lire_entier_environnement(
    "DECOUVERTE_SANTE_TENTATIVES_HTTP",
    3,
    minimum=1,
    maximum=10,
)

PAUSE_ENTRE_TENTATIVES = lire_flottant_environnement(
    "DECOUVERTE_SANTE_PAUSE_TENTATIVES",
    1.5,
    minimum=0.0,
    maximum=60.0,
)

VERIFIER_CERTIFICATS_SSL = lire_booleen_environnement(
    "DECOUVERTE_SANTE_VERIFIER_SSL",
    True,
)


# ============================================================
# PÉRIODE ET VOLUMES DE COLLECTE
# ============================================================

NOMBRE_JOURS_VEILLE = lire_entier_environnement(
    "DECOUVERTE_SANTE_NOMBRE_JOURS",
    14,
    minimum=1,
    maximum=365,
)

MAX_ARTICLES_PUBMED_PAR_REQUETE = lire_entier_environnement(
    "DECOUVERTE_SANTE_MAX_PUBMED",
    10,
    minimum=1,
    maximum=100,
)

MAX_ARTICLES_HAS_PAR_FLUX = lire_entier_environnement(
    "DECOUVERTE_SANTE_MAX_HAS",
    10,
    minimum=1,
    maximum=100,
)

MAX_ARTICLES_ANSES_PAR_FLUX = lire_entier_environnement(
    "DECOUVERTE_SANTE_MAX_ANSES",
    10,
    minimum=1,
    maximum=100,
)

MAX_ARTICLES_SPF_PAR_FLUX = lire_entier_environnement(
    "DECOUVERTE_SANTE_MAX_SPF",
    10,
    minimum=1,
    maximum=100,
)

MAX_ARTICLES_INSERM_PAR_FLUX = lire_entier_environnement(
    "DECOUVERTE_SANTE_MAX_INSERM",
    8,
    minimum=1,
    maximum=100,
)

MAX_ARTICLES_BRUTS = lire_entier_environnement(
    "DECOUVERTE_SANTE_MAX_ARTICLES_BRUTS",
    1000,
    minimum=10,
    maximum=10000,
)

MAX_ARTICLES_RETENUS = lire_entier_environnement(
    "DECOUVERTE_SANTE_MAX_ARTICLES_RETENUS",
    100,
    minimum=1,
    maximum=1000,
)

MAX_ARTICLES_PAR_SOURCE_DANS_EXPORT = lire_entier_environnement(
    "DECOUVERTE_SANTE_MAX_PAR_SOURCE_EXPORT",
    30,
    minimum=1,
    maximum=500,
)


# ============================================================
# ACTIVATION DES SOURCES
# ============================================================

ACTIVER_PUBMED = lire_booleen_environnement(
    "DECOUVERTE_SANTE_ACTIVER_PUBMED",
    True,
)

ACTIVER_HAS = lire_booleen_environnement(
    "DECOUVERTE_SANTE_ACTIVER_HAS",
    True,
)

ACTIVER_ANSES = lire_booleen_environnement(
    "DECOUVERTE_SANTE_ACTIVER_ANSES",
    True,
)

ACTIVER_SANTE_PUBLIQUE_FRANCE = lire_booleen_environnement(
    "DECOUVERTE_SANTE_ACTIVER_SPF",
    True,
)

ACTIVER_INSERM = lire_booleen_environnement(
    "DECOUVERTE_SANTE_ACTIVER_INSERM",
    True,
)


# ============================================================
# REGISTRE DES COLLECTEURS
# ============================================================

COLLECTEURS = [
    {
        "identifiant": "pubmed",
        "nom": "PubMed",
        "module": "pubmed",
        "fonction": "collecter_pubmed",
        "active": ACTIVER_PUBMED,
        "ordre": 10,
        "priorite_source": 5,
        "type_source": "Base bibliographique scientifique",
        "langue": "en",
        "parametres": {
            "nombre_jours": NOMBRE_JOURS_VEILLE,
            "limite_par_requete": (
                MAX_ARTICLES_PUBMED_PAR_REQUETE
            ),
        },
    },
    {
        "identifiant": "has",
        "nom": "HAS",
        "module": "has",
        "fonction": "collecter_has",
        "active": ACTIVER_HAS,
        "ordre": 20,
        "priorite_source": 5,
        "type_source": "Autorité sanitaire officielle",
        "langue": "fr",
        "parametres": {
            "limite_par_flux": (
                MAX_ARTICLES_HAS_PAR_FLUX
            ),
        },
    },
    {
        "identifiant": "anses",
        "nom": "ANSES",
        "module": "anses",
        "fonction": "collecter_anses",
        "active": ACTIVER_ANSES,
        "ordre": 30,
        "priorite_source": 5,
        "type_source": "Agence sanitaire officielle",
        "langue": "fr",
        "parametres": {
            "limite_par_flux": (
                MAX_ARTICLES_ANSES_PAR_FLUX
            ),
        },
    },
    {
        "identifiant": "sante_publique_france",
        "nom": "Santé publique France",
        "module": "sante_publique_france",
        "fonction": "collecter_sante_publique_france",
        "active": ACTIVER_SANTE_PUBLIQUE_FRANCE,
        "ordre": 40,
        "priorite_source": 5,
        "type_source": (
            "Agence nationale de santé publique"
        ),
        "langue": "fr",
        "parametres": {
            "limite_par_flux": (
                MAX_ARTICLES_SPF_PAR_FLUX
            ),
        },
    },
    {
        "identifiant": "inserm",
        "nom": "Inserm",
        "module": "inserm",
        "fonction": "collecter_inserm",
        "active": ACTIVER_INSERM,
        "ordre": 50,
        "priorite_source": 4,
        "type_source": "Organisme public de recherche",
        "langue": "fr",
        "parametres": {
            "limite_par_flux": (
                MAX_ARTICLES_INSERM_PAR_FLUX
            ),
        },
    },
]


def obtenir_collecteurs(
    *,
    actifs_uniquement: bool = True,
) -> list[dict[str, Any]]:
    """
    Retourne une copie indépendante du registre des collecteurs.

    Les collecteurs sont classés selon leur champ ``ordre``.
    """
    collecteurs = deepcopy(
        COLLECTEURS
    )

    if actifs_uniquement:
        collecteurs = [
            collecteur
            for collecteur in collecteurs
            if collecteur.get("active", False)
        ]

    collecteurs.sort(
        key=lambda collecteur: (
            int(
                collecteur.get(
                    "ordre",
                    9999,
                )
            ),
            str(
                collecteur.get(
                    "nom",
                    "",
                )
            ).lower(),
        )
    )

    return collecteurs


def obtenir_collecteur(
    identifiant: str,
) -> dict[str, Any] | None:
    """
    Retourne la configuration d'un collecteur par identifiant.
    """
    identifiant_normalise = str(
        identifiant
    ).strip().lower()

    for collecteur in COLLECTEURS:
        if (
            str(
                collecteur.get(
                    "identifiant",
                    "",
                )
            ).strip().lower()
            == identifiant_normalise
        ):
            return deepcopy(
                collecteur
            )

    return None


# ============================================================
# CHAMPS DU FORMAT COMMUN
# ============================================================

CHAMPS_ARTICLE_OBLIGATOIRES = (
    "source",
    "titre",
    "lien",
    "date",
    "date_brute",
    "resume",
    "requete",
)

CHAMPS_ARTICLE_OPTIONNELS = (
    "organisme",
    "type_source",
    "categorie_source",
    "priorite_source",
    "langue",
    "pmid",
    "doi",
    "journal",
    "auteurs",
    "types_publication",
    "categories",
    "mots_cles",
    "score",
    "niveau_importance",
    "nouveaute",
)


# ============================================================
# DÉDOUBLONNAGE
# ============================================================

DEDUPLIQUER_PAR_LIEN = True
DEDUPLIQUER_PAR_TITRE = True
DEDUPLIQUER_PAR_DOI = True
DEDUPLIQUER_PAR_PMID = True

SEUIL_SIMILARITE_TITRES = lire_flottant_environnement(
    "DECOUVERTE_SANTE_SEUIL_SIMILARITE",
    0.92,
    minimum=0.0,
    maximum=1.0,
)

LONGUEUR_MINIMALE_TITRE_SIMILAIRE = (
    lire_entier_environnement(
        "DECOUVERTE_SANTE_LONGUEUR_TITRE_SIMILAIRE",
        20,
        minimum=5,
        maximum=500,
    )
)


# ============================================================
# FILTRAGE SANITAIRE
# ============================================================

EXIGER_TITRE = True
EXIGER_LIEN = True

LONGUEUR_MINIMALE_TITRE = 5
LONGUEUR_MINIMALE_RESUME = 0

CONSERVER_ARTICLE_SANS_DATE = True
CONSERVER_ARTICLE_SANS_RESUME = True

PRIORITE_SOURCE_MINIMALE = lire_entier_environnement(
    "DECOUVERTE_SANTE_PRIORITE_MINIMALE",
    1,
    minimum=1,
    maximum=5,
)

TERMES_HORS_SUJET = (
    "astrophysics",
    "black hole",
    "black holes",
    "cosmology",
    "dark matter",
    "galaxy",
    "galaxies",
    "gravitational wave",
    "particle collider",
    "quantum gravity",
    "stellar evolution",
    "supernova",
)

TERMES_SANITAIRES_GENERAUX = (
    "santé",
    "health",
    "médical",
    "medical",
    "médecine",
    "medicine",
    "clinique",
    "clinical",
    "patient",
    "patients",
    "maladie",
    "disease",
    "infection",
    "infectious",
    "épidémie",
    "epidemic",
    "outbreak",
    "vaccin",
    "vaccine",
    "vaccination",
    "traitement",
    "treatment",
    "therapy",
    "prévention",
    "prevention",
    "dépistage",
    "screening",
    "diagnostic",
    "diagnosis",
    "mortalité",
    "mortality",
    "hôpital",
    "hospital",
    "public health",
    "santé publique",
    "surveillance",
    "epidemiology",
    "épidémiologie",
    "zoonose",
    "zoonosis",
    "one health",
    "santé animale",
    "animal health",
    "veterinary",
    "environnement",
    "environmental health",
)


# ============================================================
# THÉMATIQUES DE LA VEILLE
# ============================================================

THEMATIQUES = [
    {
        "identifiant": "maladies_infectieuses",
        "nom": "Maladies infectieuses",
        "priorite": 5,
        "mots": [
            "infection",
            "infectious",
            "épidémie",
            "epidemic",
            "outbreak",
            "pandémie",
            "pandemic",
            "virus",
            "bacteria",
            "bactérie",
            "pathogen",
            "pathogène",
        ],
    },
    {
        "identifiant": "vaccination",
        "nom": "Vaccination",
        "priorite": 5,
        "mots": [
            "vaccin",
            "vaccine",
            "vaccination",
            "immunization",
            "immunisation",
        ],
    },
    {
        "identifiant": "one_health",
        "nom": "One Health et zoonoses",
        "priorite": 5,
        "mots": [
            "one health",
            "zoonose",
            "zoonosis",
            "zoonotic",
            "santé animale",
            "animal health",
            "veterinary",
            "vétérinaire",
        ],
    },
    {
        "identifiant": "sante_environnement",
        "nom": "Santé environnementale",
        "priorite": 5,
        "mots": [
            "santé environnementale",
            "environmental health",
            "pollution",
            "air pollution",
            "water pollution",
            "pesticide",
            "microplastic",
            "microplastique",
            "exposome",
        ],
    },
    {
        "identifiant": "climat_sante",
        "nom": "Climat et santé",
        "priorite": 5,
        "mots": [
            "climate change",
            "changement climatique",
            "heatwave",
            "canicule",
            "chaleur",
            "extreme weather",
        ],
    },
    {
        "identifiant": "antibioresistance",
        "nom": "Antibiorésistance",
        "priorite": 5,
        "mots": [
            "antibiorésistance",
            "antimicrobial resistance",
            "antibiotic resistance",
            "drug resistance",
            "amr",
        ],
    },
    {
        "identifiant": "prevention",
        "nom": "Prévention et dépistage",
        "priorite": 4,
        "mots": [
            "prévention",
            "prevention",
            "dépistage",
            "screening",
            "early detection",
            "promotion de la santé",
            "health promotion",
        ],
    },
    {
        "identifiant": "surveillance",
        "nom": "Surveillance épidémiologique",
        "priorite": 5,
        "mots": [
            "surveillance épidémiologique",
            "epidemiological surveillance",
            "public health surveillance",
            "syndromic surveillance",
            "veille sanitaire",
            "signal sanitaire",
        ],
    },
    {
        "identifiant": "traitements",
        "nom": "Traitements et essais cliniques",
        "priorite": 4,
        "mots": [
            "clinical trial",
            "randomized controlled trial",
            "essai clinique",
            "traitement",
            "treatment",
            "therapy",
            "intervention",
            "systematic review",
            "meta-analysis",
        ],
    },
    {
        "identifiant": "nutrition",
        "nom": "Nutrition et alimentation",
        "priorite": 4,
        "mots": [
            "nutrition",
            "alimentation",
            "diet",
            "dietary",
            "food safety",
            "sécurité alimentaire",
        ],
    },
    {
        "identifiant": "sante_mentale",
        "nom": "Santé mentale",
        "priorite": 4,
        "mots": [
            "santé mentale",
            "mental health",
            "dépression",
            "depression",
            "anxiété",
            "anxiety",
            "suicide",
            "psychiatrie",
            "psychiatry",
        ],
    },
    {
        "identifiant": "urgences",
        "nom": "Urgences et soins critiques",
        "priorite": 4,
        "mots": [
            "urgence",
            "emergency",
            "critical care",
            "intensive care",
            "soins critiques",
            "réanimation",
        ],
    },
    {
        "identifiant": "ia_sante",
        "nom": "Intelligence artificielle en santé",
        "priorite": 3,
        "mots": [
            "artificial intelligence",
            "intelligence artificielle",
            "machine learning",
            "deep learning",
            "large language model",
            "modèle de langage",
            "clinical decision support",
        ],
    },
]


# ============================================================
# PONDÉRATION ET CLASSEMENT
# ============================================================

POIDS_PRIORITE_SOURCE = 2.0
POIDS_PRIORITE_THEMATIQUE = 2.0
POIDS_RECENCE = 2.0
POIDS_TYPE_PUBLICATION = 1.5
POIDS_PRESENCE_RESUME = 0.5
POIDS_IDENTIFIANT_SCIENTIFIQUE = 0.5

BONUS_SOURCE_OFFICIELLE = 2.0
BONUS_REVUE_SYSTEMATIQUE = 2.0
BONUS_META_ANALYSE = 2.0
BONUS_ESSAI_CLINIQUE = 1.5
BONUS_RECOMMANDATION = 2.0
BONUS_ALERTE_SANITAIRE = 2.5

MALUS_SANS_DATE = 0.5
MALUS_SANS_RESUME = 0.5

SEUIL_IMPORTANCE_CRITIQUE = 14.0
SEUIL_IMPORTANCE_ELEVEE = 10.0
SEUIL_IMPORTANCE_SURVEILLER = 6.0

NIVEAUX_IMPORTANCE = (
    {
        "identifiant": "critique",
        "nom": "Prioritaire",
        "icone": "🔴",
        "score_minimal": SEUIL_IMPORTANCE_CRITIQUE,
    },
    {
        "identifiant": "elevee",
        "nom": "Important",
        "icone": "🟠",
        "score_minimal": SEUIL_IMPORTANCE_ELEVEE,
    },
    {
        "identifiant": "surveiller",
        "nom": "À surveiller",
        "icone": "🟡",
        "score_minimal": SEUIL_IMPORTANCE_SURVEILLER,
    },
    {
        "identifiant": "information",
        "nom": "Information",
        "icone": "🟢",
        "score_minimal": 0.0,
    },
)


# ============================================================
# NOUVEAUTÉ ET HISTORIQUE
# ============================================================

ACTIVER_HISTORIQUE = lire_booleen_environnement(
    "DECOUVERTE_SANTE_ACTIVER_HISTORIQUE",
    True,
)

DUREE_CONSERVATION_HISTORIQUE_JOURS = (
    lire_entier_environnement(
        "DECOUVERTE_SANTE_RETENTION_HISTORIQUE",
        365,
        minimum=1,
        maximum=3650,
    )
)

IDENTIFIANTS_HISTORIQUE = (
    "pmid",
    "doi",
    "lien",
    "titre",
)

MARQUER_COMME_NOUVEAU_SI_INCONNU = True


# ============================================================
# RÉSUMÉS ET TEXTES
# ============================================================

LONGUEUR_MAXIMALE_RESUME_ARTICLE = (
    lire_entier_environnement(
        "DECOUVERTE_SANTE_LONGUEUR_RESUME",
        1200,
        minimum=100,
        maximum=10000,
    )
)

LONGUEUR_MAXIMALE_TITRE_EXPORT = (
    lire_entier_environnement(
        "DECOUVERTE_SANTE_LONGUEUR_TITRE_EXPORT",
        300,
        minimum=50,
        maximum=1000,
    )
)

NOMBRE_ARTICLES_RESUME_EXECUTIF = (
    lire_entier_environnement(
        "DECOUVERTE_SANTE_ARTICLES_RESUME_EXECUTIF",
        10,
        minimum=1,
        maximum=50,
    )
)


# ============================================================
# EXPORTS
# ============================================================

ACTIVER_EXPORT_JSON = lire_booleen_environnement(
    "DECOUVERTE_SANTE_EXPORT_JSON",
    True,
)

ACTIVER_EXPORT_CSV = lire_booleen_environnement(
    "DECOUVERTE_SANTE_EXPORT_CSV",
    True,
)

ACTIVER_EXPORT_HTML = lire_booleen_environnement(
    "DECOUVERTE_SANTE_EXPORT_HTML",
    True,
)

ACTIVER_EXPORT_PDF = lire_booleen_environnement(
    "DECOUVERTE_SANTE_EXPORT_PDF",
    False,
)

PREFIXE_FICHIER_EXPORT = "veille_decouverte_sante"

FORMATS_DATE_FICHIER = "%Y-%m-%d_%H-%M-%S"
FORMAT_DATE_AFFICHAGE = "%d/%m/%Y"
FORMAT_DATE_HEURE_AFFICHAGE = "%d/%m/%Y à %H:%M"

COLONNES_EXPORT_CSV = (
    "source",
    "organisme",
    "titre",
    "date",
    "lien",
    "resume",
    "requete",
    "categorie_source",
    "priorite_source",
    "categories",
    "score",
    "niveau_importance",
    "nouveaute",
    "pmid",
    "doi",
    "journal",
)


# ============================================================
# JOURNALISATION
# ============================================================

NIVEAU_JOURNAL = lire_chaine_environnement(
    "DECOUVERTE_SANTE_NIVEAU_JOURNAL",
    "INFO",
).upper()

NIVEAUX_JOURNAL_AUTORISES = (
    "DEBUG",
    "INFO",
    "AVERTISSEMENT",
    "ERREUR",
    "CRITIQUE",
)

JOURNALISER_DANS_CONSOLE = lire_booleen_environnement(
    "DECOUVERTE_SANTE_JOURNAL_CONSOLE",
    True,
)

JOURNALISER_DANS_FICHIER = lire_booleen_environnement(
    "DECOUVERTE_SANTE_JOURNAL_FICHIER",
    True,
)

TAILLE_MAXIMALE_JOURNAL_OCTETS = (
    lire_entier_environnement(
        "DECOUVERTE_SANTE_TAILLE_MAX_JOURNAL",
        5_000_000,
        minimum=100_000,
        maximum=100_000_000,
    )
)

NOMBRE_FICHIERS_JOURNAL_CONSERVES = (
    lire_entier_environnement(
        "DECOUVERTE_SANTE_NOMBRE_JOURNAUX",
        5,
        minimum=1,
        maximum=50,
    )
)


# ============================================================
# COMPORTEMENT EN CAS D'ERREUR
# ============================================================

CONTINUER_SI_SOURCE_EN_ERREUR = True
CONTINUER_SI_ARTICLE_INVALIDE = True

LEVER_ERREUR_SI_AUCUN_COLLECTEUR_ACTIF = True
LEVER_ERREUR_SI_AUCUN_ARTICLE = False

INCLURE_ERREURS_DANS_RAPPORT = True
INCLURE_DETAILS_COLLECTE_DANS_RAPPORT = True


# ============================================================
# VALIDATION
# ============================================================

def valider_configuration() -> list[str]:
    """
    Vérifie la cohérence de la configuration.

    Retourne une liste de messages d'erreur.
    Une liste vide signifie que la configuration est cohérente.
    """
    erreurs: list[str] = []

    identifiants_vus: set[str] = set()
    ordres_vus: set[int] = set()

    for collecteur in COLLECTEURS:
        identifiant = str(
            collecteur.get(
                "identifiant",
                "",
            )
        ).strip()

        nom = str(
            collecteur.get(
                "nom",
                "",
            )
        ).strip()

        module = str(
            collecteur.get(
                "module",
                "",
            )
        ).strip()

        fonction = str(
            collecteur.get(
                "fonction",
                "",
            )
        ).strip()

        ordre = collecteur.get(
            "ordre"
        )

        parametres = collecteur.get(
            "parametres"
        )

        if not identifiant:
            erreurs.append(
                "Un collecteur ne possède pas d'identifiant."
            )

        elif identifiant in identifiants_vus:
            erreurs.append(
                (
                    "Identifiant de collecteur en double : "
                    f"{identifiant}."
                )
            )

        else:
            identifiants_vus.add(
                identifiant
            )

        if not nom:
            erreurs.append(
                (
                    "Le collecteur "
                    f"{identifiant or '<inconnu>'} "
                    "ne possède pas de nom."
                )
            )

        if not module:
            erreurs.append(
                (
                    "Le collecteur "
                    f"{identifiant or '<inconnu>'} "
                    "ne possède pas de module."
                )
            )

        if not fonction:
            erreurs.append(
                (
                    "Le collecteur "
                    f"{identifiant or '<inconnu>'} "
                    "ne possède pas de fonction."
                )
            )

        if not isinstance(
            ordre,
            int,
        ):
            erreurs.append(
                (
                    "L'ordre du collecteur "
                    f"{identifiant or '<inconnu>'} "
                    "doit être un entier."
                )
            )

        elif ordre in ordres_vus:
            erreurs.append(
                (
                    "Ordre de collecteur en double : "
                    f"{ordre}."
                )
            )

        else:
            ordres_vus.add(
                ordre
            )

        if not isinstance(
            collecteur.get("active"),
            bool,
        ):
            erreurs.append(
                (
                    "Le champ active du collecteur "
                    f"{identifiant or '<inconnu>'} "
                    "doit être booléen."
                )
            )

        if not isinstance(
            parametres,
            dict,
        ):
            erreurs.append(
                (
                    "Les paramètres du collecteur "
                    f"{identifiant or '<inconnu>'} "
                    "doivent être un dictionnaire."
                )
            )

    if (
        LEVER_ERREUR_SI_AUCUN_COLLECTEUR_ACTIF
        and not any(
            collecteur.get(
                "active",
                False,
            )
            for collecteur in COLLECTEURS
        )
    ):
        erreurs.append(
            "Aucun collecteur n'est actif."
        )

    if MAX_ARTICLES_RETENUS > MAX_ARTICLES_BRUTS:
        erreurs.append(
            (
                "MAX_ARTICLES_RETENUS ne peut pas dépasser "
                "MAX_ARTICLES_BRUTS."
            )
        )

    if not (
        0.0
        <= SEUIL_SIMILARITE_TITRES
        <= 1.0
    ):
        erreurs.append(
            (
                "SEUIL_SIMILARITE_TITRES doit être compris "
                "entre 0 et 1."
            )
        )

    if PRIORITE_SOURCE_MINIMALE not in {
        1,
        2,
        3,
        4,
        5,
    }:
        erreurs.append(
            (
                "PRIORITE_SOURCE_MINIMALE doit être comprise "
                "entre 1 et 5."
            )
        )

    if (
        SEUIL_IMPORTANCE_SURVEILLER
        > SEUIL_IMPORTANCE_ELEVEE
    ):
        erreurs.append(
            (
                "Le seuil « À surveiller » ne peut pas être "
                "supérieur au seuil « Important »."
            )
        )

    if (
        SEUIL_IMPORTANCE_ELEVEE
        > SEUIL_IMPORTANCE_CRITIQUE
    ):
        erreurs.append(
            (
                "Le seuil « Important » ne peut pas être "
                "supérieur au seuil « Prioritaire »."
            )
        )

    if (
        NIVEAU_JOURNAL
        not in NIVEAUX_JOURNAL_AUTORISES
    ):
        erreurs.append(
            (
                "NIVEAU_JOURNAL invalide : "
                f"{NIVEAU_JOURNAL}."
            )
        )

    return erreurs


def verifier_configuration() -> None:
    """
    Valide la configuration et lève une exception si elle est invalide.
    """
    erreurs = valider_configuration()

    if not erreurs:
        return

    details = "\n".join(
        f"- {erreur}"
        for erreur in erreurs
    )

    raise ValueError(
        (
            "Configuration du moteur de veille invalide :\n"
            f"{details}"
        )
    )


# ============================================================
# EXPORT PUBLIC
# ============================================================

__all__ = [
    "NOM_APPLICATION",
    "NOM_MOTEUR",
    "VERSION_MOTEUR",
    "DESCRIPTION_APPLICATION",
    "LANGUE_PAR_DEFAUT",
    "FUSEAU_HORAIRE",
    "ENCODAGE_PAR_DEFAUT",
    "USER_AGENT",
    "REPERTOIRE_PROJET",
    "REPERTOIRE_DONNEES",
    "REPERTOIRE_EXPORTS",
    "REPERTOIRE_JOURNAUX",
    "REPERTOIRE_CACHE",
    "FICHIER_ETAT",
    "FICHIER_HISTORIQUE",
    "FICHIER_JOURNAL",
    "TIMEOUT_HTTP",
    "NOMBRE_TENTATIVES_HTTP",
    "PAUSE_ENTRE_TENTATIVES",
    "VERIFIER_CERTIFICATS_SSL",
    "NOMBRE_JOURS_VEILLE",
    "MAX_ARTICLES_BRUTS",
    "MAX_ARTICLES_RETENUS",
    "MAX_ARTICLES_PAR_SOURCE_DANS_EXPORT",
    "COLLECTEURS",
    "CHAMPS_ARTICLE_OBLIGATOIRES",
    "CHAMPS_ARTICLE_OPTIONNELS",
    "THEMATIQUES",
    "TERMES_HORS_SUJET",
    "TERMES_SANITAIRES_GENERAUX",
    "SEUIL_SIMILARITE_TITRES",
    "PRIORITE_SOURCE_MINIMALE",
    "NIVEAUX_IMPORTANCE",
    "ACTIVER_HISTORIQUE",
    "DUREE_CONSERVATION_HISTORIQUE_JOURS",
    "IDENTIFIANTS_HISTORIQUE",
    "REPERTOIRE_EXPORTS",
    "COLONNES_EXPORT_CSV",
    "NIVEAU_JOURNAL",
    "CONTINUER_SI_SOURCE_EN_ERREUR",
    "CONTINUER_SI_ARTICLE_INVALIDE",
    "creer_repertoires",
    "obtenir_collecteurs",
    "obtenir_collecteur",
    "valider_configuration",
    "verifier_configuration",
]