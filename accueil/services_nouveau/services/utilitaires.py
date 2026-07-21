"""
Fonctions utilitaires communes à tous les collecteurs.

Ce module fournit :
- le téléchargement HTTP avec timeout et User-Agent ;
- la lecture de flux RSS et Atom ;
- le nettoyage de texte et de HTML ;
- la normalisation des dates ;
- le dédoublonnage simple ;
- des fonctions de journalisation légères.

Aucune bibliothèque externe n'est nécessaire.
"""

from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from html import unescape
import json
import re
import time
from typing import Any, Iterable
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


# ============================================================
# RÉGLAGES GÉNÉRAUX
# ============================================================

USER_AGENT = (
    "Sante-Prevention-Terrain/2.0 "
    "(veille scientifique locale)"
)

TIMEOUT_PAR_DEFAUT = 30
NOMBRE_TENTATIVES = 2
PAUSE_ENTRE_TENTATIVES = 1.2


# ============================================================
# JOURNALISATION
# ============================================================

def journaliser(
    message: str,
    niveau: str = "INFO",
) -> None:
    """
    Affiche un message lisible dans le terminal Django.

    Exemples :
        journaliser("PubMed : 12 articles")
        journaliser("Erreur de connexion", "ERREUR")
    """
    niveau_normalise = str(niveau).upper().strip()

    horodatage = datetime.now().strftime(
        "%H:%M:%S"
    )

    print(
        f"[{horodatage}] "
        f"[VEILLE] "
        f"[{niveau_normalise}] "
        f"{message}"
    )


# ============================================================
# TÉLÉCHARGEMENT HTTP
# ============================================================

def telecharger(
    url: str,
    *,
    timeout: int = TIMEOUT_PAR_DEFAUT,
    entetes: dict[str, str] | None = None,
    tentatives: int = NOMBRE_TENTATIVES,
) -> bytes:
    """
    Télécharge une ressource distante et retourne son contenu binaire.

    Une nouvelle tentative est effectuée en cas d'erreur temporaire.
    """
    if not url:
        raise ValueError(
            "L'URL de téléchargement est vide."
        )

    entetes_requete = {
        "User-Agent": USER_AGENT,
        "Accept": (
            "application/rss+xml,"
            "application/atom+xml,"
            "application/xml,"
            "text/xml,"
            "application/json,"
            "text/html,"
            "*/*;q=0.8"
        ),
    }

    if entetes:
        entetes_requete.update(entetes)

    derniere_erreur: Exception | None = None

    for numero_tentative in range(
        1,
        max(1, tentatives) + 1,
    ):
        try:
            requete = urllib.request.Request(
                url,
                headers=entetes_requete,
            )

            with urllib.request.urlopen(
                requete,
                timeout=timeout,
            ) as reponse:
                return reponse.read()

        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
            OSError,
        ) as erreur:
            derniere_erreur = erreur

            journaliser(
                (
                    f"Téléchargement impossible "
                    f"({numero_tentative}/"
                    f"{max(1, tentatives)}) : "
                    f"{url} — {erreur}"
                ),
                "AVERTISSEMENT",
            )

            if numero_tentative < max(
                1,
                tentatives,
            ):
                time.sleep(
                    PAUSE_ENTRE_TENTATIVES
                )

    raise RuntimeError(
        f"Échec du téléchargement : {url}"
    ) from derniere_erreur


def telecharger_texte(
    url: str,
    *,
    encodage: str = "utf-8",
    **options: Any,
) -> str:
    """
    Télécharge une ressource et la convertit en texte.
    """
    contenu = telecharger(
        url,
        **options,
    )

    return contenu.decode(
        encodage,
        errors="replace",
    )


def telecharger_json(
    url: str,
    **options: Any,
) -> dict[str, Any] | list[Any]:
    """
    Télécharge et décode une réponse JSON.
    """
    texte = telecharger_texte(
        url,
        **options,
    )

    try:
        return json.loads(texte)

    except json.JSONDecodeError as erreur:
        raise ValueError(
            f"Réponse JSON invalide : {url}"
        ) from erreur


# ============================================================
# NETTOYAGE DU TEXTE
# ============================================================

def nettoyer_texte(
    texte: Any,
) -> str:
    """
    Supprime les retours à la ligne et espaces superflus.
    """
    if texte is None:
        return ""

    return " ".join(
        str(texte)
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("\t", " ")
        .split()
    )


def nettoyer_html(
    texte: Any,
) -> str:
    """
    Retire les balises HTML simples et décode les entités HTML.
    """
    if texte is None:
        return ""

    contenu = unescape(
        str(texte)
    )

    contenu = re.sub(
        r"<script\b[^>]*>.*?</script>",
        " ",
        contenu,
        flags=re.IGNORECASE | re.DOTALL,
    )

    contenu = re.sub(
        r"<style\b[^>]*>.*?</style>",
        " ",
        contenu,
        flags=re.IGNORECASE | re.DOTALL,
    )

    contenu = re.sub(
        r"<[^>]+>",
        " ",
        contenu,
    )

    return nettoyer_texte(
        contenu
    )


def normaliser_texte(
    texte: Any,
) -> str:
    """
    Prépare un texte pour la comparaison et le dédoublonnage.
    """
    contenu = nettoyer_texte(
        texte
    ).lower()

    contenu = unescape(
        contenu
    )

    contenu = re.sub(
        r"[^a-z0-9à-ÿ\s-]",
        " ",
        contenu,
    )

    return " ".join(
        contenu.split()
    )


def texte_xml_complet(
    element: ET.Element | None,
) -> str:
    """
    Récupère tout le texte contenu dans un élément XML,
    y compris celui de ses sous-balises.
    """
    if element is None:
        return ""

    return nettoyer_texte(
        "".join(
            element.itertext()
        )
    )


# ============================================================
# DATES
# ============================================================

def formater_date(
    date_brute: Any,
) -> str:
    """
    Essaie plusieurs formats de date courants.

    Retourne une date au format JJ/MM/AAAA quand c'est possible.
    """
    date_texte = nettoyer_texte(
        date_brute
    )

    if not date_texte:
        return "Date non disponible"

    # RFC 2822, souvent utilisé par RSS.
    try:
        date_convertie = parsedate_to_datetime(
            date_texte
        )

        return date_convertie.strftime(
            "%d/%m/%Y"
        )

    except (
        ValueError,
        TypeError,
        OverflowError,
    ):
        pass

    # ISO 8601, souvent utilisé par Atom et arXiv.
    try:
        date_convertie = datetime.fromisoformat(
            date_texte.replace(
                "Z",
                "+00:00",
            )
        )

        return date_convertie.strftime(
            "%d/%m/%Y"
        )

    except (
        ValueError,
        TypeError,
    ):
        pass

    # Quelques formats classiques supplémentaires.
    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%b %d, %Y",
        "%d %b %Y",
        "%B %d, %Y",
        "%d %B %Y",
    ]

    for format_date in formats:
        try:
            date_convertie = datetime.strptime(
                date_texte,
                format_date,
            )

            return date_convertie.strftime(
                "%d/%m/%Y"
            )

        except ValueError:
            continue

    return date_texte


# ============================================================
# LECTURE RSS ET ATOM
# ============================================================

def lire_flux(
    contenu: bytes | str,
    *,
    source: str,
    requete: str = "",
    limite: int = 20,
) -> list[dict[str, Any]]:
    """
    Lit automatiquement un flux RSS 2.0, RDF ou Atom.

    Retourne une liste d'articles normalisés.
    """
    if isinstance(contenu, str):
        contenu_xml = contenu.encode(
            "utf-8"
        )
    else:
        contenu_xml = contenu

    try:
        racine = ET.fromstring(
            contenu_xml
        )

    except ET.ParseError as erreur:
        raise ValueError(
            "Le flux XML est invalide."
        ) from erreur

    articles = lire_flux_rss(
        racine,
        source=source,
        requete=requete,
        limite=limite,
    )

    if articles:
        return articles

    return lire_flux_atom(
        racine,
        source=source,
        requete=requete,
        limite=limite,
    )


def lire_flux_rss(
    racine: ET.Element,
    *,
    source: str,
    requete: str,
    limite: int,
) -> list[dict[str, Any]]:
    """
    Lit les éléments <item> d'un flux RSS ou RDF.
    """
    articles: list[dict[str, Any]] = []

    items = racine.findall(
        ".//item"
    )

    for item in items[:limite]:
        titre = nettoyer_texte(
            item.findtext(
                "title",
                default="",
            )
        )

        lien = nettoyer_texte(
            item.findtext(
                "link",
                default="",
            )
        )

        if not lien:
            guid = nettoyer_texte(
                item.findtext(
                    "guid",
                    default="",
                )
            )

            if guid.startswith(
                ("http://", "https://")
            ):
                lien = guid

        resume = nettoyer_html(
            item.findtext(
                "description",
                default="",
            )
        )

        date_brute = nettoyer_texte(
            item.findtext(
                "pubDate",
                default="",
            )
            or item.findtext(
                "date",
                default="",
            )
        )

        if not titre or not lien:
            continue

        articles.append(
            construire_article(
                source=source,
                titre=titre,
                lien=lien,
                resume=resume,
                date_brute=date_brute,
                requete=requete,
            )
        )

    return articles


def lire_flux_atom(
    racine: ET.Element,
    *,
    source: str,
    requete: str,
    limite: int,
) -> list[dict[str, Any]]:
    """
    Lit les éléments <entry> d'un flux Atom.
    """
    namespace = {
        "atom": (
            "http://www.w3.org/2005/Atom"
        ),
    }

    entrees = racine.findall(
        ".//atom:entry",
        namespace,
    )

    if not entrees:
        # Certains flux Atom n'utilisent pas explicitement
        # le namespace dans leur balise racine.
        entrees = racine.findall(
            ".//entry"
        )

    articles: list[dict[str, Any]] = []

    for entree in entrees[:limite]:
        titre = nettoyer_texte(
            entree.findtext(
                "atom:title",
                default="",
                namespaces=namespace,
            )
            or entree.findtext(
                "title",
                default="",
            )
        )

        lien = extraire_lien_atom(
            entree,
            namespace,
        )

        resume = nettoyer_html(
            entree.findtext(
                "atom:summary",
                default="",
                namespaces=namespace,
            )
            or entree.findtext(
                "atom:content",
                default="",
                namespaces=namespace,
            )
            or entree.findtext(
                "summary",
                default="",
            )
            or entree.findtext(
                "content",
                default="",
            )
        )

        date_brute = nettoyer_texte(
            entree.findtext(
                "atom:published",
                default="",
                namespaces=namespace,
            )
            or entree.findtext(
                "atom:updated",
                default="",
                namespaces=namespace,
            )
            or entree.findtext(
                "published",
                default="",
            )
            or entree.findtext(
                "updated",
                default="",
            )
        )

        if not titre or not lien:
            continue

        articles.append(
            construire_article(
                source=source,
                titre=titre,
                lien=lien,
                resume=resume,
                date_brute=date_brute,
                requete=requete,
            )
        )

    return articles


def extraire_lien_atom(
    entree: ET.Element,
    namespace: dict[str, str],
) -> str:
    """
    Récupère le meilleur lien disponible dans une entrée Atom.
    """
    liens = entree.findall(
        "atom:link",
        namespace,
    )

    if not liens:
        liens = entree.findall(
            "link"
        )

    meilleur_lien = ""

    for element_lien in liens:
        href = nettoyer_texte(
            element_lien.attrib.get(
                "href",
                "",
            )
        )

        relation = nettoyer_texte(
            element_lien.attrib.get(
                "rel",
                "alternate",
            )
        )

        if not href:
            continue

        if relation in {
            "",
            "alternate",
        }:
            return href

        if not meilleur_lien:
            meilleur_lien = href

    return meilleur_lien


def construire_article(
    *,
    source: str,
    titre: str,
    lien: str,
    resume: str = "",
    date_brute: str = "",
    requete: str = "",
    **champs_supplementaires: Any,
) -> dict[str, Any]:
    """
    Construit un article au format commun utilisé par le projet.
    """
    article: dict[str, Any] = {
        "source": nettoyer_texte(
            source
        ),
        "titre": nettoyer_texte(
            titre
        ),
        "lien": nettoyer_texte(
            lien
        ),
        "date": formater_date(
            date_brute
        ),
        "date_brute": nettoyer_texte(
            date_brute
        ),
        "resume": nettoyer_html(
            resume
        ),
        "requete": nettoyer_texte(
            requete
        ),
    }

    article.update(
        champs_supplementaires
    )

    return article


# ============================================================
# DÉDOUBLONNAGE
# ============================================================

def supprimer_doublons(
    articles: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Supprime les doublons exacts à partir du lien ou du titre.

    Le traitement approfondi pourra ensuite appliquer
    une détection plus intelligente.
    """
    resultat: list[dict[str, Any]] = []
    cles_vues: set[str] = set()

    for article in articles:
        lien = normaliser_texte(
            article.get(
                "lien",
                "",
            )
        )

        titre = normaliser_texte(
            article.get(
                "titre",
                "",
            )
        )

        cle = lien or titre

        if not cle:
            continue

        if cle in cles_vues:
            continue

        cles_vues.add(
            cle
        )

        resultat.append(
            article
        )

    return resultat


# ============================================================
# OUTILS DIVERS
# ============================================================

def construire_url(
    url_base: str,
    parametres: dict[str, Any],
) -> str:
    """
    Ajoute proprement des paramètres à une URL.
    """
    separateur = (
        "&"
        if "?" in url_base
        else "?"
    )

    return (
        f"{url_base}"
        f"{separateur}"
        f"{urllib.parse.urlencode(parametres)}"
    )


def limiter_texte(
    texte: Any,
    longueur: int = 500,
) -> str:
    """
    Tronque un texte proprement sans couper au milieu d'un mot.
    """
    contenu = nettoyer_texte(
        texte
    )

    if len(contenu) <= longueur:
        return contenu

    extrait = contenu[:longueur].rsplit(
        " ",
        1,
    )[0]

    return f"{extrait}…"