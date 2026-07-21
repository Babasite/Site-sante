"""
Collecteur Santé publique France.

Le module consulte l'annuaire RSS officiel de Santé publique France,
découvre automatiquement les flux disponibles, puis collecte
les publications récentes.

Une erreur sur un flux ne bloque pas les autres.
"""

from __future__ import annotations

from html.parser import HTMLParser
from typing import Any
import urllib.parse

from .utilitaires import (
    journaliser,
    lire_flux,
    nettoyer_texte,
    supprimer_doublons,
    telecharger,
    telecharger_texte,
)


# ============================================================
# CONFIGURATION
# ============================================================

URL_ANNUAIRE_RSS = (
    "https://www.santepubliquefrance.fr/rss"
)

MAX_FLUX = 12
MAX_ARTICLES_PAR_FLUX = 8


THEMATIQUES_PRIORITAIRES = [
    {
        "mots": [
            "grippe",
            "bronchiolite",
            "covid",
            "infection respiratoire",
        ],
        "categorie": "Infections respiratoires",
        "priorite": 5,
    },
    {
        "mots": [
            "dengue",
            "chikungunya",
            "zika",
            "moustique",
            "vectorielle",
        ],
        "categorie": "Maladies vectorielles",
        "priorite": 5,
    },
    {
        "mots": [
            "vaccination",
            "vaccin",
        ],
        "categorie": "Vaccination",
        "priorite": 5,
    },
    {
        "mots": [
            "climat",
            "canicule",
            "fortes chaleurs",
            "changement climatique",
        ],
        "categorie": "Climat et santé",
        "priorite": 5,
    },
    {
        "mots": [
            "alcool",
            "tabac",
            "drogue",
            "addiction",
        ],
        "categorie": "Addictions",
        "priorite": 4,
    },
    {
        "mots": [
            "santé mentale",
            "depression",
            "anxiété",
            "suicide",
        ],
        "categorie": "Santé mentale",
        "priorite": 4,
    },
    {
        "mots": [
            "cancer",
            "diabète",
            "maladie chronique",
        ],
        "categorie": "Maladies chroniques",
        "priorite": 4,
    },
    {
        "mots": [
            "santé sexuelle",
            "vih",
            "ist",
            "hépatite",
        ],
        "categorie": "Santé sexuelle et infections",
        "priorite": 4,
    },
    {
        "mots": [
            "accident",
            "traumatisme",
            "chute",
            "brûlure",
        ],
        "categorie": "Accidents et traumatismes",
        "priorite": 3,
    },
    {
        "mots": [
            "bulletin épidémiologique",
            "beh",
        ],
        "categorie": "Bulletin épidémiologique",
        "priorite": 5,
    },
    {
        "mots": [
            "actualité",
            "actualités",
            "à la une",
        ],
        "categorie": "Actualités",
        "priorite": 3,
    },
]


# ============================================================
# EXTRACTION DES LIENS
# ============================================================

class ExtracteurLiens(HTMLParser):
    """
    Extrait les liens et leurs libellés depuis une page HTML.
    """

    def __init__(self) -> None:
        super().__init__()
        self.liens: list[dict[str, str]] = []
        self._href = ""
        self._texte: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.lower() != "a":
            return

        attributs = dict(attrs)

        self._href = nettoyer_texte(
            attributs.get("href", "")
        )

        self._texte = []

    def handle_data(
        self,
        data: str,
    ) -> None:
        if self._href:
            self._texte.append(data)

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        if tag.lower() != "a":
            return

        if not self._href:
            return

        self.liens.append(
            {
                "href": self._href,
                "texte": nettoyer_texte(
                    " ".join(self._texte)
                ),
            }
        )

        self._href = ""
        self._texte = []


# ============================================================
# COLLECTE PRINCIPALE
# ============================================================

def collecter(
    *,
    limite_par_flux: int = MAX_ARTICLES_PAR_FLUX,
) -> list[dict[str, Any]]:
    """
    Découvre et interroge les flux RSS de Santé publique France.
    """
    limite_par_flux = max(
        1,
        int(limite_par_flux),
    )

    articles: list[dict[str, Any]] = []

    try:
        flux = decouvrir_flux()

    except Exception as erreur:
        journaliser(
            (
                "Santé publique France — "
                "impossible de lire l'annuaire RSS : "
                f"{erreur}"
            ),
            "ERREUR",
        )

        return articles

    journaliser(
        (
            "Santé publique France : "
            f"{len(flux)} flux officiel(s) découvert(s)."
        )
    )

    for configuration in flux:
        nom_flux = configuration["nom"]
        url = configuration["url"]
        categorie = configuration["categorie"]
        priorite = configuration["priorite"]

        try:
            contenu = telecharger(url)

            resultats = lire_flux(
                contenu,
                source="Santé publique France",
                requete=nom_flux,
                limite=limite_par_flux,
            )

            for article in resultats:
                article["categorie_source"] = categorie
                article["priorite_source"] = priorite
                article["organisme"] = (
                    "Santé publique France"
                )
                article["type_source"] = (
                    "Agence nationale de santé publique"
                )
                article["langue"] = "fr"

            articles.extend(resultats)

            journaliser(
                (
                    "Santé publique France — "
                    f"{nom_flux} : "
                    f"{len(resultats)} article(s)."
                )
            )

        except Exception as erreur:
            journaliser(
                (
                    "Santé publique France — "
                    f"flux indisponible « {nom_flux} » : "
                    f"{erreur}"
                ),
                "AVERTISSEMENT",
            )

    articles = supprimer_doublons(
        articles
    )

    journaliser(
        (
            "Santé publique France : "
            f"{len(articles)} article(s) "
            "après dédoublonnage."
        )
    )

    return articles


# ============================================================
# DÉCOUVERTE DES FLUX
# ============================================================

def decouvrir_flux() -> list[dict[str, Any]]:
    """
    Lit l'annuaire RSS officiel et classe les flux par priorité.
    """
    page_html = telecharger_texte(
        URL_ANNUAIRE_RSS
    )

    extracteur = ExtracteurLiens()
    extracteur.feed(page_html)

    candidats: list[dict[str, Any]] = []

    for lien in extracteur.liens:
        href = lien["href"]
        texte = lien["texte"]

        url_absolue = urllib.parse.urljoin(
            URL_ANNUAIRE_RSS,
            href,
        )

        contenu_comparable = (
            f"{texte} {url_absolue}"
        ).lower()

        ressemble_a_un_flux = any(
            marqueur in contenu_comparable
            for marqueur in (
                "rss",
                ".xml",
                "/feed",
                "atom",
            )
        )

        if not ressemble_a_un_flux:
            continue

        categorie, priorite = identifier_thematique(
            contenu_comparable
        )

        candidats.append(
            {
                "nom": (
                    texte
                    or categorie
                    or "Flux Santé publique France"
                ),
                "url": url_absolue,
                "categorie": categorie,
                "priorite": priorite,
            }
        )

    candidats = dedoublonner_flux(
        candidats
    )

    candidats.sort(
        key=lambda element: (
            int(element["priorite"]),
            str(element["nom"]).lower(),
        ),
        reverse=True,
    )

    return candidats[:MAX_FLUX]


def identifier_thematique(
    contenu: str,
) -> tuple[str, int]:
    """
    Associe un flux à une catégorie et à une priorité.
    """
    for configuration in THEMATIQUES_PRIORITAIRES:
        if any(
            mot.lower() in contenu
            for mot in configuration["mots"]
        ):
            return (
                str(configuration["categorie"]),
                int(configuration["priorite"]),
            )

    return "Thématique de santé publique", 3


def dedoublonner_flux(
    flux: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Supprime les URL de flux en double.
    """
    resultat: list[dict[str, Any]] = []
    urls_vues: set[str] = set()

    for configuration in flux:
        url = nettoyer_texte(
            configuration.get("url", "")
        )

        cle = url.lower().rstrip("/")

        if not cle or cle in urls_vues:
            continue

        urls_vues.add(cle)
        resultat.append(configuration)

    return resultat


# ============================================================
# ALIAS EXPLICITE
# ============================================================

def collecter_sante_publique_france(
    *,
    limite_par_flux: int = MAX_ARTICLES_PAR_FLUX,
) -> list[dict[str, Any]]:
    """
    Alias compatible avec un import explicite.
    """
    return collecter(
        limite_par_flux=limite_par_flux,
    )