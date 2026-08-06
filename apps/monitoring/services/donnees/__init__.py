"""
Préparation, normalisation et statistiques des articles de veille.

V5 - Version préparée pour le moteur de pertinence avancé.

Évolutions apportées :
- Préparation à un score de confiance des sources.
- Préparation à un bonus "actualité sanitaire".
- Préparation à la diversification des sources.
- Préparation à la détection de quasi-doublons.
- Préparation à un score explicable.

Cette version reste 100 % compatible avec l'API de la V4.

V6 - Priorisation robuste des nouveaux articles.

Cette version conserve l'API de la V5 et ajoute une mémoire de veille
injectable. Les articles jamais utilisés sont privilégiés, tandis que les
articles déjà diffusés restent disponibles mais sont pénalisés de façon
explicable.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from functools import lru_cache
import hashlib
import math
import re
import unicodedata
from typing import Any, Callable, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from apps.monitoring.services.classification import (
    classifier_article,
)
from apps.monitoring.services.utilitaires import (
    nettoyer_texte,
)


Article = dict[str, Any]


# ============================================================
# VALEURS PAR DÉFAUT
# ============================================================

CATEGORIES_PAR_DEFAUT: list[str] = []

ONE_HEALTH_PAR_DEFAUT: list[str] = []

PREUVE_PAR_DEFAUT = "Non déterminé"
NIVEAU_PREUVE_PAR_DEFAUT = 0

IMPORTANCE_PAR_DEFAUT = 0
NIVEAU_IMPORTANCE_PAR_DEFAUT = "Veille documentaire"


# ============================================================
# CONVERSIONS
# ============================================================

def convertir_liste(
    valeur: Any,
) -> list[str]:
    """
    Convertit une valeur en liste de chaînes propres.

    Les doublons sont supprimés sans tenir compte de la casse ni des accents.
    L'ordre d'origine est conservé. Les ensembles sont triés pour garantir un
    résultat déterministe entre deux exécutions.
    """
    if valeur is None:
        return []

    if isinstance(valeur, str):
        elements: list[Any] = [valeur]

    elif isinstance(valeur, set):
        elements = sorted(
            valeur,
            key=lambda element: nettoyer_texte(element).casefold(),
        )

    elif isinstance(valeur, (list, tuple)):
        elements = list(valeur)

    else:
        elements = [valeur]

    resultat: list[str] = []
    cles_vues: set[str] = set()

    for element in elements:
        texte = nettoyer_texte(element)
        if not texte:
            continue

        cle = _sans_accents(texte).casefold()
        if cle in cles_vues:
            continue

        cles_vues.add(cle)
        resultat.append(texte)

    return resultat


def convertir_entier(
    valeur: Any,
    valeur_par_defaut: int = 0,
) -> int:
    """
    Convertit une valeur en entier sans interrompre la veille.
    """
    try:
        return int(
            valeur
        )

    except (
        TypeError,
        ValueError,
    ):
        return valeur_par_defaut


def convertir_flottant(
    valeur: Any,
    valeur_par_defaut: float = 0.0,
) -> float:
    """
    Convertit une valeur en nombre décimal fini.

    Les valeurs NaN et infinies sont remplacées par la valeur par défaut afin
    de conserver un tri déterministe.
    """
    try:
        resultat = float(
            valeur
        )

    except (
        TypeError,
        ValueError,
    ):
        return valeur_par_defaut

    return resultat if math.isfinite(resultat) else valeur_par_defaut


LONGUEUR_MAX_ERREUR_CLASSIFICATION = 500

SCHEMAS_URL_AUTORISES = {
    "http",
    "https",
}


def normaliser_url(
    valeur: Any,
) -> str:
    """
    Nettoie une URL HTTP(S) sans modifier sa destination.

    Les URL relatives, les schémas dangereux et les valeurs mal formées sont
    rejetés. Le fragment ``#...`` est retiré car il ne participe généralement
    pas à l'identité d'un article.
    """
    texte = nettoyer_texte(valeur)
    if not texte:
        return ""

    try:
        parties = urlsplit(texte)
    except ValueError:
        return ""

    if parties.scheme.casefold() not in SCHEMAS_URL_AUTORISES:
        return ""

    if not parties.netloc:
        return ""

    requete_filtree = [
        (cle, valeur)
        for cle, valeur in parse_qsl(
            parties.query,
            keep_blank_values=True,
        )
        if cle.casefold() not in PARAMETRES_URL_SUIVI
    ]

    chemin = re.sub(
        r"/+$",
        "",
        parties.path or "",
    ) or "/"

    return urlunsplit(
        (
            parties.scheme.casefold(),
            parties.netloc.casefold(),
            chemin,
            urlencode(
                sorted(requete_filtree)
            ),
            "",
        )
    )


def borner_entier(
    valeur: Any,
    minimum: int,
    maximum: int,
    valeur_par_defaut: int = 0,
) -> int:
    """Convertit puis borne un entier dans un intervalle fermé."""
    resultat = convertir_entier(
        valeur,
        valeur_par_defaut,
    )
    return min(
        max(resultat, minimum),
        maximum,
    )


# ============================================================
# PRÉPARATION DES ARTICLES
# ============================================================

def preparer_article(
    article: Article,
) -> Article:
    """
    Garantit la présence des champs utilisés par Django.

    Cette fonction ne remplace pas une future classification
    approfondie. Elle sécurise uniquement le format transmis
    à la vue et à la base de données.
    """
    resultat = deepcopy(
        article
    )

    resultat["titre"] = nettoyer_texte(
        resultat.get(
            "titre",
            "Titre non disponible",
        )
    ) or "Titre non disponible"

    resultat["source"] = nettoyer_texte(
        resultat.get(
            "source",
            "Source inconnue",
        )
    ) or "Source inconnue"

    lien_original = nettoyer_texte(
        resultat.get(
            "lien",
            "",
        )
    )
    resultat["lien"] = normaliser_url(
        lien_original
    )
    resultat["lien_valide"] = bool(
        resultat["lien"]
    )

    if lien_original and not resultat["lien"]:
        resultat["lien_original_invalide"] = lien_original
    else:
        resultat.pop(
            "lien_original_invalide",
            None,
        )

    resultat["date"] = nettoyer_texte(
        resultat.get(
            "date",
            "Date non disponible",
        )
    ) or "Date non disponible"

    resultat["date_brute"] = nettoyer_texte(
        resultat.get(
            "date_brute",
            "",
        )
    )

    resultat["resume"] = nettoyer_texte(
        resultat.get(
            "resume",
            "",
        )
    )

    resultat["requete"] = nettoyer_texte(
        resultat.get(
            "requete",
            "",
        )
    )

    resultat["categories"] = convertir_liste(
        resultat.get(
            "categories",
            CATEGORIES_PAR_DEFAUT,
        )
    )

    resultat["one_health"] = convertir_liste(
        resultat.get(
            "one_health",
            ONE_HEALTH_PAR_DEFAUT,
        )
    )

    resultat["preuve"] = nettoyer_texte(
        resultat.get(
            "preuve",
            PREUVE_PAR_DEFAUT,
        )
    ) or PREUVE_PAR_DEFAUT

    resultat["niveau_preuve"] = borner_entier(
        resultat.get(
            "niveau_preuve",
            NIVEAU_PREUVE_PAR_DEFAUT,
        ),
        minimum=0,
        maximum=100,
        valeur_par_defaut=NIVEAU_PREUVE_PAR_DEFAUT,
    )

    resultat["importance"] = borner_entier(
        resultat.get(
            "importance",
            IMPORTANCE_PAR_DEFAUT,
        ),
        minimum=0,
        maximum=100,
        valeur_par_defaut=IMPORTANCE_PAR_DEFAUT,
    )

    resultat["niveau_importance"] = nettoyer_texte(
        resultat.get(
            "niveau_importance",
            NIVEAU_IMPORTANCE_PAR_DEFAUT,
        )
    ) or NIVEAU_IMPORTANCE_PAR_DEFAUT

    resultat["raisons"] = convertir_liste(
        resultat.get(
            "raisons",
            [],
        )
    )

    resultat["mots_detectes"] = convertir_liste(
        resultat.get(
            "mots_detectes",
            [],
        )
    )

    resultat["score"] = convertir_flottant(
        resultat.get(
            "score",
            resultat.get(
                "importance",
                0,
            ),
        )
    )

    resultat["titre_normalise"] = _sans_accents(
        resultat["titre"]
    ).casefold()
    resultat["source_normalisee"] = _sans_accents(
        resultat["source"]
    ).casefold()

    cle_date = extraire_cle_date(
        resultat
    )
    resultat["date_trie"] = (
        "-".join(
            (
                f"{cle_date[0]:04d}",
                f"{cle_date[1]:02d}",
                f"{cle_date[2]:02d}",
            )
        )
        if cle_date != CLE_DATE_ABSENTE
        else ""
    )

    return resultat


MOIS_FRANCAIS = {
    "janvier": 1,
    "janv": 1,
    "fevrier": 2,
    "fevr": 2,
    "mars": 3,
    "avril": 4,
    "avr": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "juil": 7,
    "aout": 8,
    "septembre": 9,
    "sept": 9,
    "octobre": 10,
    "oct": 10,
    "novembre": 11,
    "nov": 11,
    "decembre": 12,
    "dec": 12,
}

MOIS_ANGLAIS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

MOIS_TEXTE = {
    **MOIS_FRANCAIS,
    **MOIS_ANGLAIS,
}

VALEURS_DATE_ABSENTE = {
    "",
    "date non disponible",
    "non disponible",
    "inconnue",
    "unknown",
    "n/a",
    "na",
    "none",
    "null",
}

CHAMPS_DATE_PAR_PRIORITE = (
    "date_publication",
    "publication_date",
    "published",
    "date",
    "date_brute",
)


# Une légère avance est tolérée pour les fuseaux horaires et les publications
# programmées. Au-delà, la date est considérée comme suspecte et rétrogradée.
TOLERANCE_DATE_FUTURE_JOURS = 2

CLE_DATE_ABSENTE = (0, 0, 0, 0, 0, 0)


# Pondérations du score composite de pertinence.
# Leur somme vaut 1, avant application des pénalités.
POIDS_PERTINENCE = {
    "classification": 0.38,
    "importance": 0.22,
    "preuve": 0.12,
    "recence": 0.18,
    "signaux": 0.06,
    "completude": 0.04,
}

SEUIL_PERTINENCE_ELEVEE = 70.0
DEMI_VIE_RECENCE_JOURS = 45.0

MODES_TRI_AUTORISES = {
    "pertinence",
    "recence",
    "nouveaute",
}

BONUS_ARTICLE_NOUVEAU = 12.0
PENALITE_ARTICLE_DEJA_UTILISE = 22.0
PENALITE_REUTILISATION_PAR_OCCURRENCE = 3.0
PENALITE_REUTILISATION_MAXIMALE = 40.0

PARAMETRES_URL_SUIVI = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "gclid",
    "fbclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
}


def _sans_accents(texte: str) -> str:
    """Retire les accents pour faciliter l'analyse des mois."""
    return "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texte)
        if not unicodedata.combining(caractere)
    )


def _cle_datetime(valeur: datetime) -> tuple[int, int, int, int, int, int]:
    """Transforme un datetime en tuple comparable, normalisé en UTC."""
    if valeur.tzinfo is not None:
        valeur = valeur.astimezone(timezone.utc).replace(tzinfo=None)

    return (
        valeur.year,
        valeur.month,
        valeur.day,
        valeur.hour,
        valeur.minute,
        valeur.second,
    )


@lru_cache(maxsize=4096)
def _analyser_date(texte_original: str) -> tuple[int, int, int, int, int, int]:
    """
    Analyse une date provenant des différents collecteurs.

    Formats pris en charge : ISO 8601, RFC 2822, dates numériques,
    formats PubMed, mois français ou anglais et dates partielles.
    """
    texte = nettoyer_texte(texte_original).strip()
    if not texte:
        return CLE_DATE_ABSENTE

    texte_normalise = _sans_accents(texte).lower().strip(" .,;")
    if texte_normalise in VALEURS_DATE_ABSENTE:
        return CLE_DATE_ABSENTE

    texte_nettoye = re.sub(
        r"^(published|publication|online|epub|date|mis en ligne|publie le)\s*[:\-]?\s*",
        "",
        texte,
        flags=re.IGNORECASE,
    ).strip()

    try:
        return _cle_datetime(
            datetime.fromisoformat(texte_nettoye.replace("Z", "+00:00"))
        )
    except ValueError:
        pass

    try:
        valeur_rfc = parsedate_to_datetime(texte_nettoye)
        if valeur_rfc is not None:
            return _cle_datetime(valeur_rfc)
    except (TypeError, ValueError, OverflowError):
        pass

    for format_date in (
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y%m%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y",
        "%Y-%m",
        "%Y/%m",
        "%m/%Y",
        "%Y",
    ):
        try:
            return _cle_datetime(datetime.strptime(texte_nettoye, format_date))
        except ValueError:
            continue

    texte_mois = _sans_accents(texte_nettoye).lower()
    texte_mois = re.sub(r"[,./_-]+", " ", texte_mois)
    texte_mois = re.sub(r"\s+", " ", texte_mois).strip()

    motifs = (
        r"\b(?P<jour>\d{1,2})\s+(?P<mois>[a-z]+)\s+(?P<annee>\d{4})\b",
        r"\b(?P<mois>[a-z]+)\s+(?P<jour>\d{1,2})\s+(?P<annee>\d{4})\b",
        r"\b(?P<annee>\d{4})\s+(?P<mois>[a-z]+)(?:\s+(?P<jour>\d{1,2}))?\b",
        r"\b(?P<mois>[a-z]+)\s+(?P<annee>\d{4})\b",
    )

    for motif in motifs:
        correspondance = re.search(motif, texte_mois)
        if not correspondance:
            continue

        groupes = correspondance.groupdict()
        mois = MOIS_TEXTE.get(groupes["mois"].rstrip("."))
        if not mois:
            continue

        annee = int(groupes["annee"])
        jour = int(groupes.get("jour") or 1)

        try:
            return _cle_datetime(datetime(annee, mois, jour))
        except ValueError:
            continue

    # Une année seule n'est acceptée que lorsque la valeur ressemble réellement
    # à un champ de date court. Cela évite de récupérer une année citée dans
    # un résumé ou un libellé parasite.
    if len(texte_nettoye) <= 24:
        correspondance_annee = re.search(r"\b(?:19|20)\d{2}\b", texte_nettoye)
        if correspondance_annee:
            return (
                int(correspondance_annee.group(0)),
                1,
                1,
                0,
                0,
                0,
            )

    return CLE_DATE_ABSENTE


def extraire_cle_date(
    article: Article,
) -> tuple[int, int, int, int, int, int]:
    """
    Retourne la meilleure date exploitable d'un article.

    Les champs de publication explicites sont prioritaires. Une date absente
    ou invalide renvoie une clé nulle et sera donc classée en dernier.
    """
    for champ in CHAMPS_DATE_PAR_PRIORITE:
        valeur = article.get(champ)

        if isinstance(valeur, datetime):
            return _cle_datetime(valeur)

        if isinstance(valeur, date):
            return (
                valeur.year,
                valeur.month,
                valeur.day,
                0,
                0,
                0,
            )

        texte = nettoyer_texte(valeur)
        if not texte:
            continue

        cle = _analyser_date(texte)
        if cle != CLE_DATE_ABSENTE:
            return cle

    return CLE_DATE_ABSENTE


def _date_depuis_cle(
    cle_date: tuple[int, int, int, int, int, int],
) -> datetime | None:
    """Reconstruit un datetime depuis une clé de date validée."""
    if cle_date == CLE_DATE_ABSENTE:
        return None

    try:
        return datetime(*cle_date)
    except (TypeError, ValueError):
        return None


def _qualite_date(
    cle_date: tuple[int, int, int, int, int, int],
    maintenant: datetime | None = None,
) -> int:
    """
    Classe la date selon sa fiabilité.

    0 : date valide et non future ;
    1 : date future suspecte ;
    2 : date absente ou invalide.
    """
    valeur = _date_depuis_cle(cle_date)
    if valeur is None:
        return 2

    reference = maintenant or datetime.now(timezone.utc).replace(tzinfo=None)
    limite_future = reference + timedelta(days=TOLERANCE_DATE_FUTURE_JOURS)

    return 1 if valeur > limite_future else 0


def _borner_flottant(
    valeur: Any,
    minimum: float = 0.0,
    maximum: float = 100.0,
    valeur_par_defaut: float = 0.0,
) -> float:
    """Convertit puis borne un flottant dans un intervalle fermé."""
    resultat = convertir_flottant(
        valeur,
        valeur_par_defaut,
    )
    return min(
        max(resultat, minimum),
        maximum,
    )


def _score_recence(
    cle_date: tuple[int, int, int, int, int, int],
    maintenant: datetime,
) -> float:
    """
    Calcule un score de récence entre 0 et 100.

    La décroissance exponentielle évite qu'un article légèrement plus ancien
    soit brutalement déclassé. Les dates futures suspectes et absentes ne
    reçoivent aucun bonus.
    """
    valeur = _date_depuis_cle(
        cle_date
    )
    if valeur is None:
        return 0.0

    qualite = _qualite_date(
        cle_date,
        maintenant=maintenant,
    )
    if qualite != 0:
        return 0.0

    age_jours = max(
        (maintenant - valeur).total_seconds() / 86400,
        0.0,
    )
    score = 100.0 * math.exp(
        -math.log(2) * age_jours / DEMI_VIE_RECENCE_JOURS
    )
    return round(
        _borner_flottant(score),
        2,
    )


def _score_completude(
    article: Article,
) -> float:
    """Mesure la qualité minimale des métadonnées utiles à la veille."""
    criteres = (
        bool(
            nettoyer_texte(
                article.get("titre")
            )
        )
        and article.get("titre") != "Titre non disponible",
        bool(
            nettoyer_texte(
                article.get("resume")
            )
        ),
        bool(
            nettoyer_texte(
                article.get("source")
            )
        )
        and article.get("source") != "Source inconnue",
        bool(
            article.get("lien_valide")
        ),
        extraire_cle_date(article) != CLE_DATE_ABSENTE,
        bool(
            convertir_liste(
                article.get("categories")
            )
        ),
        bool(
            convertir_liste(
                article.get("raisons")
            )
        ),
        bool(
            convertir_liste(
                article.get("mots_detectes")
            )
        ),
    )

    return round(
        sum(criteres) / len(criteres) * 100,
        2,
    )


def _score_signaux(
    article: Article,
) -> float:
    """
    Valorise les signaux explicites produits par la classification.

    Le plafonnement empêche les articles très verbeux de monopoliser le haut
    du classement.
    """
    raisons = convertir_liste(
        article.get("raisons")
    )
    mots = convertir_liste(
        article.get("mots_detectes")
    )
    categories = convertir_liste(
        article.get("categories")
    )
    one_health = convertir_liste(
        article.get("one_health")
    )

    score = (
        min(len(raisons), 5) * 8
        + min(len(mots), 10) * 4
        + min(len(categories), 4) * 5
        + min(len(one_health), 3) * 5
    )

    return round(
        _borner_flottant(score),
        2,
    )


def _normaliser_texte_empreinte(
    valeur: Any,
) -> str:
    """Normalise un texte destiné à l'identification d'un article."""
    texte = _sans_accents(
        nettoyer_texte(valeur)
    ).casefold()
    texte = re.sub(
        r"\b(?:the|a|an|le|la|les|un|une|des|du|de|d|l)\b",
        " ",
        texte,
    )
    texte = re.sub(
        r"[^a-z0-9]+",
        " ",
        texte,
    )
    return re.sub(
        r"\s+",
        " ",
        texte,
    ).strip()


def construire_empreinte_article(
    article: Article,
) -> str:
    """
    Produit une empreinte stable pour reconnaître un article déjà utilisé.

    Priorités :
    1. identifiant scientifique explicite (DOI, PMID, identifiant) ;
    2. URL canonique sans paramètres de suivi ;
    3. combinaison source + titre normalisé.

    L'empreinte est hachée afin de pouvoir être stockée facilement en base.
    """
    for champ in (
        "doi",
        "pmid",
        "identifiant",
        "identifier",
        "id_externe",
        "external_id",
    ):
        valeur = _normaliser_texte_empreinte(
            article.get(champ)
        )
        if valeur:
            brut = f"id:{champ}:{valeur}"
            return hashlib.sha256(
                brut.encode("utf-8")
            ).hexdigest()

    lien = normaliser_url(
        article.get("lien")
    )
    if lien:
        brut = f"url:{lien}"
        return hashlib.sha256(
            brut.encode("utf-8")
        ).hexdigest()

    titre = _normaliser_texte_empreinte(
        article.get("titre")
    )
    source = _normaliser_texte_empreinte(
        article.get("source")
    )

    if not titre:
        return ""

    # La date n'est volontairement pas incluse : un même article dont le
    # collecteur reformate la date doit rester reconnu.
    brut = f"titre:{source}:{titre}"
    return hashlib.sha256(
        brut.encode("utf-8")
    ).hexdigest()


def construire_index_historique(
    historique: Iterable[Article | str] | None,
) -> dict[str, int]:
    """
    Convertit un historique hétérogène en compteur d'empreintes.

    Chaque élément peut être :
    - un article complet ;
    - une empreinte SHA-256 déjà enregistrée ;
    - une URL brute.
    """
    index: dict[str, int] = {}

    if historique is None:
        return index

    for element in historique:
        empreinte = ""

        if isinstance(element, dict):
            empreinte = construire_empreinte_article(
                element
            )

        elif isinstance(element, str):
            texte = nettoyer_texte(
                element
            )

            if re.fullmatch(
                r"[0-9a-fA-F]{64}",
                texte,
            ):
                empreinte = texte.casefold()

            else:
                lien = normaliser_url(
                    texte
                )
                if lien:
                    empreinte = hashlib.sha256(
                        f"url:{lien}".encode("utf-8")
                    ).hexdigest()

        if not empreinte:
            continue

        index[empreinte] = index.get(
            empreinte,
            0,
        ) + 1

    return index


def evaluer_nouveaute(
    article: Article,
    index_historique: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    Évalue si un article a déjà été utilisé lors d'une veille précédente.
    """
    empreinte = construire_empreinte_article(
        article
    )
    historique = index_historique or {}
    nombre_utilisations = historique.get(
        empreinte,
        0,
    ) if empreinte else 0

    deja_utilise = nombre_utilisations > 0
    penalite = 0.0

    if deja_utilise:
        penalite = min(
            PENALITE_ARTICLE_DEJA_UTILISE
            + max(
                nombre_utilisations - 1,
                0,
            )
            * PENALITE_REUTILISATION_PAR_OCCURRENCE,
            PENALITE_REUTILISATION_MAXIMALE,
        )

    return {
        "empreinte_article": empreinte,
        "article_nouveau": not deja_utilise,
        "deja_utilise": deja_utilise,
        "nombre_utilisations_precedentes": nombre_utilisations,
        "bonus_nouveaute": (
            BONUS_ARTICLE_NOUVEAU
            if not deja_utilise
            else 0.0
        ),
        "penalite_reutilisation": round(
            penalite,
            2,
        ),
    }


def calculer_score_pertinence(
    article: Article,
    maintenant: datetime | None = None,
    index_historique: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    Calcule un score composite explicable entre 0 et 100.

    Le score de classification reste le signal principal. Il est enrichi par
    l'importance, le niveau de preuve, la récence, les signaux détectés et la
    complétude. Des pénalités transparentes réduisent le score lorsque les
    métadonnées sont manifestement peu fiables.
    """
    reference = maintenant
    if reference is None:
        reference = datetime.now(
            timezone.utc
        ).replace(
            tzinfo=None
        )
    elif reference.tzinfo is not None:
        reference = reference.astimezone(
            timezone.utc
        ).replace(
            tzinfo=None
        )

    cle_date = extraire_cle_date(
        article
    )
    qualite_date = _qualite_date(
        cle_date,
        maintenant=reference,
    )

    score_classification = _borner_flottant(
        article.get(
            "score",
            article.get(
                "importance",
                0,
            ),
        )
    )
    score_importance = _borner_flottant(
        article.get(
            "importance",
            0,
        )
    )
    score_preuve = _borner_flottant(
        article.get(
            "niveau_preuve",
            0,
        )
    )
    score_recence = _score_recence(
        cle_date,
        reference,
    )
    score_signaux = _score_signaux(
        article
    )
    score_completude = _score_completude(
        article
    )

    nouveaute = evaluer_nouveaute(
        article,
        index_historique=index_historique,
    )

    penalites: list[str] = []
    total_penalites = 0.0

    if qualite_date == 1:
        penalites.append(
            "Date future suspecte"
        )
        total_penalites += 25.0

    elif qualite_date == 2:
        penalites.append(
            "Date absente ou invalide"
        )
        total_penalites += 8.0

    if article.get(
        "erreur_classification"
    ):
        penalites.append(
            "Classification en erreur"
        )
        total_penalites += 15.0

    if not article.get(
        "lien_valide",
        False,
    ):
        penalites.append(
            "Lien absent ou invalide"
        )
        total_penalites += 3.0

    if not nettoyer_texte(
        article.get("resume")
    ):
        penalites.append(
            "Résumé absent"
        )
        total_penalites += 4.0

    if article.get("titre") == "Titre non disponible":
        penalites.append(
            "Titre absent"
        )
        total_penalites += 12.0

    if nouveaute["deja_utilise"]:
        penalites.append(
            "Article déjà utilisé lors d'une veille précédente"
        )
        total_penalites += convertir_flottant(
            nouveaute["penalite_reutilisation"]
        )

    score_brut = (
        score_classification * POIDS_PERTINENCE["classification"]
        + score_importance * POIDS_PERTINENCE["importance"]
        + score_preuve * POIDS_PERTINENCE["preuve"]
        + score_recence * POIDS_PERTINENCE["recence"]
        + score_signaux * POIDS_PERTINENCE["signaux"]
        + score_completude * POIDS_PERTINENCE["completude"]
        + convertir_flottant(
            nouveaute["bonus_nouveaute"]
        )
    )

    score_final = round(
        _borner_flottant(
            score_brut - total_penalites
        ),
        2,
    )

    return {
        "score_pertinence": score_final,
        "score_pertinence_brut": round(
            score_brut,
            2,
        ),
        "score_recence": score_recence,
        "score_signaux": score_signaux,
        "score_completude": score_completude,
        "penalite_pertinence": round(
            total_penalites,
            2,
        ),
        "penalites_pertinence": penalites,
        "pertinence_elevee": (
            score_final >= SEUIL_PERTINENCE_ELEVEE
        ),
        **nouveaute,
    }


def _construire_cle_tri(
    maintenant: datetime,
    mode_tri: str = "pertinence",
) -> Callable[[Article], tuple[Any, ...]]:
    """
    Construit une fonction de tri stable.

    ``pertinence`` privilégie le score composite puis la récence.
    ``recence`` privilégie la date puis la pertinence.
    """
    mode = nettoyer_texte(
        mode_tri
    ).casefold()

    if mode not in MODES_TRI_AUTORISES:
        mode = "pertinence"

    def cle_tri(article: Article) -> tuple[Any, ...]:
        cle_date = extraire_cle_date(
            article
        )
        qualite_date = _qualite_date(
            cle_date,
            maintenant=maintenant,
        )
        score_pertinence = convertir_flottant(
            article.get(
                "score_pertinence",
                0,
            )
        )

        criteres_secondaires = (
            -convertir_flottant(
                article.get(
                    "score",
                    article.get(
                        "importance",
                        0,
                    ),
                )
            ),
            -convertir_entier(
                article.get(
                    "importance",
                    0,
                )
            ),
            -convertir_entier(
                article.get(
                    "niveau_preuve",
                    0,
                )
            ),
            -convertir_entier(
                article.get(
                    "priorite_source",
                    0,
                )
            ),
            nettoyer_texte(
                article.get(
                    "source",
                    "",
                )
            ).casefold(),
            nettoyer_texte(
                article.get(
                    "titre",
                    "",
                )
            ).casefold(),
        )

        if mode == "recence":
            return (
                qualite_date,
                tuple(
                    -element
                    for element in cle_date
                ),
                bool(
                    article.get(
                        "deja_utilise",
                        False,
                    )
                ),
                -score_pertinence,
                *criteres_secondaires,
            )

        if mode == "nouveaute":
            return (
                bool(
                    article.get(
                        "deja_utilise",
                        False,
                    )
                ),
                -score_pertinence,
                qualite_date,
                tuple(
                    -element
                    for element in cle_date
                ),
                *criteres_secondaires,
            )

        return (
            bool(
                article.get(
                    "deja_utilise",
                    False,
                )
            ),
            -score_pertinence,
            qualite_date,
            tuple(
                -element
                for element in cle_date
            ),
            *criteres_secondaires,
        )

    return cle_tri


def preparer_articles(
    articles: list[Article],
    limite: int | None = None,
    maintenant: datetime | None = None,
    mode_tri: str = "pertinence",
    historique_articles: Iterable[Article | str] | None = None,
) -> list[Article]:
    """
    Prépare, classe et trie les articles.

    ``limite`` est appliquée après la classification et le tri. La valeur
    ``None`` conserve tous les articles et préserve le comportement historique.

    ``maintenant`` permet de figer la référence temporelle dans les tests.

    ``mode_tri`` accepte ``pertinence`` (par défaut), ``recence`` ou
    ``nouveaute``.

    ``historique_articles`` accepte les articles des veilles précédentes,
    leurs empreintes SHA-256 ou leurs URL. Les articles nouveaux sont
    automatiquement privilégiés.
    """
    resultat: list[Article] = []

    for article in articles:
        if not isinstance(
            article,
            dict,
        ):
            continue

        article_prepare = preparer_article(
            article
        )

        try:
            article_classe = classifier_article(
                article_prepare
            )

            if isinstance(
                article_classe,
                dict,
            ):
                article_prepare.update(
                    article_classe
                )

                article_prepare = preparer_article(
                    article_prepare
                )

        except Exception as erreur:
            raisons = convertir_liste(
                article_prepare.get(
                    "raisons",
                    [],
                )
            )

            raisons.append(
                "Classification non appliquée : "
                f"{type(erreur).__name__}."
            )

            article_prepare["raisons"] = raisons
            message_erreur = nettoyer_texte(
                erreur
            )
            article_prepare["erreur_classification"] = (
                message_erreur[:LONGUEUR_MAX_ERREUR_CLASSIFICATION]
            )

        resultat.append(
            article_prepare
        )

    reference_temporelle = maintenant
    if reference_temporelle is None:
        reference_temporelle = datetime.now(
            timezone.utc
        ).replace(
            tzinfo=None
        )
    elif reference_temporelle.tzinfo is not None:
        reference_temporelle = reference_temporelle.astimezone(
            timezone.utc
        ).replace(
            tzinfo=None
        )

    index_historique = construire_index_historique(
        historique_articles
    )

    for article in resultat:
        article.update(
            calculer_score_pertinence(
                article,
                maintenant=reference_temporelle,
                index_historique=index_historique,
            )
        )

    resultat.sort(
        key=_construire_cle_tri(
            reference_temporelle,
            mode_tri=mode_tri,
        )
    )

    for position, article in enumerate(
        resultat,
        start=1,
    ):
        cle_date = extraire_cle_date(
            article
        )
        article["rang"] = position
        article["qualite_date"] = _qualite_date(
            cle_date,
            maintenant=reference_temporelle,
        )

        score_pertinence = convertir_flottant(
            article.get(
                "score_pertinence",
                0,
            )
        )
        if score_pertinence >= 85:
            article["niveau_pertinence"] = "Prioritaire"
        elif score_pertinence >= SEUIL_PERTINENCE_ELEVEE:
            article["niveau_pertinence"] = "Élevée"
        elif score_pertinence >= 50:
            article["niveau_pertinence"] = "Moyenne"
        else:
            article["niveau_pertinence"] = "Faible"

    if limite is None:
        return resultat

    limite_validee = max(
        convertir_entier(
            limite,
            0,
        ),
        0,
    )

    return resultat[:limite_validee]


# ============================================================
# STATISTIQUES
# ============================================================

def construire_statistiques(
    rapport: dict[str, Any],
    articles: list[Article],
) -> dict[str, Any]:
    """
    Convertit le rapport de l'orchestrateur au format attendu
    par la vue Django existante.
    """
    articles_recuperes = convertir_entier(
        rapport.get(
            "articles_avant_dedoublonnage",
            rapport.get(
                "articles_bruts",
                len(
                    articles
                ),
            ),
        )
    )

    statistiques = {
        "sources_interrogees": convertir_entier(
            rapport.get(
                "sources_interrogees",
                0,
            )
        ),
        "sources_reussies": convertir_entier(
            rapport.get(
                "sources_reussies",
                0,
            )
        ),
        "sources_en_erreur": convertir_entier(
            rapport.get(
                "sources_en_erreur",
                0,
            )
        ),
        "articles_recuperes": articles_recuperes,
        "articles_retenus": len(
            articles
        ),
        "doublons_supprimes": convertir_entier(
            rapport.get(
                "doublons_supprimes",
                0,
            )
        ),
        "duree_secondes": round(
            convertir_flottant(
                rapport.get(
                    "duree_secondes",
                    0,
                )
            ),
            2,
        ),
        "statut": nettoyer_texte(
            rapport.get(
                "statut",
                "",
            )
        ),
        "details": deepcopy(
            rapport.get(
                "collecteurs",
                [],
            )
        ),
        "erreurs": deepcopy(
            rapport.get(
                "erreurs",
                [],
            )
        ),
        "articles_dates_valides": sum(
            1
            for article in articles
            if article.get("qualite_date") == 0
        ),
        "articles_dates_futures": sum(
            1
            for article in articles
            if article.get("qualite_date") == 1
        ),
        "articles_sans_date": sum(
            1
            for article in articles
            if article.get("qualite_date") == 2
        ),
        "classifications_en_erreur": sum(
            1
            for article in articles
            if article.get("erreur_classification")
        ),
        "liens_invalides": sum(
            1
            for article in articles
            if not article.get("lien_valide", False)
        ),
        "articles_pertinence_elevee": sum(
            1
            for article in articles
            if article.get("pertinence_elevee", False)
        ),
        "score_pertinence_moyen": round(
            (
                sum(
                    convertir_flottant(
                        article.get(
                            "score_pertinence",
                            0,
                        )
                    )
                    for article in articles
                )
                / len(articles)
            )
            if articles
            else 0.0,
            2,
        ),
        "score_pertinence_maximum": round(
            max(
                (
                    convertir_flottant(
                        article.get(
                            "score_pertinence",
                            0,
                        )
                    )
                    for article in articles
                ),
                default=0.0,
            ),
            2,
        ),
        "articles_nouveaux": sum(
            1
            for article in articles
            if article.get(
                "article_nouveau",
                False,
            )
        ),
        "articles_deja_utilises": sum(
            1
            for article in articles
            if article.get(
                "deja_utilise",
                False,
            )
        ),
    }

    sources_interrogees = statistiques["sources_interrogees"]
    statistiques["taux_reussite_sources"] = round(
        (
            statistiques["sources_reussies"]
            / sources_interrogees
            * 100
        )
        if sources_interrogees
        else 0.0,
        1,
    )

    statistiques["taux_retention"] = round(
        (
            statistiques["articles_retenus"]
            / articles_recuperes
            * 100
        )
        if articles_recuperes
        else 0.0,
        1,
    )

    statistiques["taux_nouveaute"] = round(
        (
            statistiques["articles_nouveaux"]
            / statistiques["articles_retenus"]
            * 100
        )
        if statistiques["articles_retenus"]
        else 0.0,
        1,
    )

    return statistiques


__all__ = [
    "Article",
    "construire_statistiques",
    "convertir_entier",
    "convertir_flottant",
    "convertir_liste",
    "borner_entier",
    "normaliser_url",
    "calculer_score_pertinence",
    "construire_empreinte_article",
    "construire_index_historique",
    "evaluer_nouveaute",
    "extraire_cle_date",
    "TOLERANCE_DATE_FUTURE_JOURS",
    "POIDS_PERTINENCE",
    "SEUIL_PERTINENCE_ELEVEE",
    "BONUS_ARTICLE_NOUVEAU",
    "PENALITE_ARTICLE_DEJA_UTILISE",
    "preparer_article",
    "preparer_articles",
]