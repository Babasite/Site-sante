"""
Exports du moteur de veille V2.

Ce module génère des fichiers JSON, CSV et HTML à partir des articles
collectés. Il n'exécute aucune collecte et ne dépend pas de Django.
"""

from __future__ import annotations

import csv
from datetime import date, datetime
from html import escape
import json
from pathlib import Path
from typing import Any, Iterable

from .configuration import (
    ACTIVER_EXPORT_CSV,
    ACTIVER_EXPORT_HTML,
    ACTIVER_EXPORT_JSON,
    COLONNES_EXPORT_CSV,
    ENCODAGE_PAR_DEFAUT,
    FORMATS_DATE_FICHIER,
    MAX_ARTICLES_PAR_SOURCE_DANS_EXPORT,
    PREFIXE_FICHIER_EXPORT,
    REPERTOIRE_EXPORTS,
    creer_repertoires,
)
from .utilitaires import journaliser, nettoyer_texte


Article = dict[str, Any]
Rapport = dict[str, Any]


def _convertir_valeur_json(
    valeur: Any,
) -> Any:
    """
    Convertit les objets non directement sérialisables en JSON.
    """
    if isinstance(
        valeur,
        (
            datetime,
            date,
        ),
    ):
        return valeur.isoformat()

    if isinstance(
        valeur,
        Path,
    ):
        return str(
            valeur
        )

    if isinstance(
        valeur,
        set,
    ):
        return sorted(
            _convertir_valeur_json(
                element
            )
            for element in valeur
        )

    if isinstance(
        valeur,
        tuple,
    ):
        return [
            _convertir_valeur_json(
                element
            )
            for element in valeur
        ]

    if isinstance(
        valeur,
        list,
    ):
        return [
            _convertir_valeur_json(
                element
            )
            for element in valeur
        ]

    if isinstance(
        valeur,
        dict,
    ):
        return {
            str(cle): _convertir_valeur_json(
                element
            )
            for cle, element in valeur.items()
        }

    return valeur


def _aplatir_valeur_csv(
    valeur: Any,
) -> str:
    """
    Transforme une valeur complexe en texte utilisable dans un CSV.
    """
    if valeur is None:
        return ""

    if isinstance(
        valeur,
        (
            datetime,
            date,
        ),
    ):
        return valeur.isoformat()

    if isinstance(
        valeur,
        (
            list,
            tuple,
            set,
        ),
    ):
        return " | ".join(
            nettoyer_texte(
                element
            )
            for element in valeur
            if nettoyer_texte(
                element
            )
        )

    if isinstance(
        valeur,
        dict,
    ):
        return json.dumps(
            _convertir_valeur_json(
                valeur
            ),
            ensure_ascii=False,
            sort_keys=True,
        )

    return nettoyer_texte(
        valeur
    )


def _nom_base(
    horodatage: datetime | None = None,
) -> str:
    """
    Construit le nom de base commun aux fichiers exportés.
    """
    instant = horodatage or datetime.now()

    return (
        f"{PREFIXE_FICHIER_EXPORT}_"
        f"{instant.strftime(FORMATS_DATE_FICHIER)}"
    )


def _preparer_repertoire(
    repertoire: str | Path | None = None,
) -> Path:
    """
    Crée et retourne le répertoire d'export.
    """
    creer_repertoires()

    chemin = (
        Path(
            repertoire
        )
        if repertoire is not None
        else REPERTOIRE_EXPORTS
    )

    chemin = chemin.expanduser().resolve()

    chemin.mkdir(
        parents=True,
        exist_ok=True,
    )

    return chemin


def limiter_articles_par_source(
    articles: Iterable[Article],
    limite: int = MAX_ARTICLES_PAR_SOURCE_DANS_EXPORT,
) -> list[Article]:
    """
    Limite le nombre d'articles exportés pour chaque source.
    """
    limite = max(
        1,
        int(
            limite
        ),
    )

    compteurs: dict[str, int] = {}
    resultat: list[Article] = []

    for article in articles:
        if not isinstance(
            article,
            dict,
        ):
            continue

        source = nettoyer_texte(
            article.get(
                "source",
                "Source inconnue",
            )
        ) or "Source inconnue"

        nombre = compteurs.get(
            source,
            0,
        )

        if nombre >= limite:
            continue

        compteurs[source] = nombre + 1

        resultat.append(
            dict(
                article
            )
        )

    return resultat


def exporter_json(
    articles: Iterable[Article],
    rapport: Rapport | None = None,
    *,
    repertoire: str | Path | None = None,
    nom_fichier: str | None = None,
) -> Path:
    """
    Écrit les articles et le rapport de collecte dans un fichier JSON.
    """
    dossier = _preparer_repertoire(
        repertoire
    )

    chemin = dossier / (
        nom_fichier
        or f"{_nom_base()}.json"
    )

    if chemin.suffix.lower() != ".json":
        chemin = chemin.with_suffix(
            ".json"
        )

    articles_prepares = limiter_articles_par_source(
        articles
    )

    contenu = {
        "date_export": datetime.now().isoformat(
            timespec="seconds"
        ),
        "nombre_articles": len(
            articles_prepares
        ),
        "rapport": rapport or {},
        "articles": articles_prepares,
    }

    chemin.write_text(
        json.dumps(
            _convertir_valeur_json(
                contenu
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding=ENCODAGE_PAR_DEFAUT,
    )

    journaliser(
        f"Export JSON créé : {chemin}"
    )

    return chemin


def exporter_csv(
    articles: Iterable[Article],
    *,
    repertoire: str | Path | None = None,
    nom_fichier: str | None = None,
) -> Path:
    """
    Écrit les articles dans un fichier CSV compatible avec Excel.
    """
    dossier = _preparer_repertoire(
        repertoire
    )

    chemin = dossier / (
        nom_fichier
        or f"{_nom_base()}.csv"
    )

    if chemin.suffix.lower() != ".csv":
        chemin = chemin.with_suffix(
            ".csv"
        )

    articles_prepares = limiter_articles_par_source(
        articles
    )

    with chemin.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as fichier:
        redacteur = csv.DictWriter(
            fichier,
            fieldnames=list(
                COLONNES_EXPORT_CSV
            ),
            extrasaction="ignore",
            delimiter=";",
        )

        redacteur.writeheader()

        for article in articles_prepares:
            redacteur.writerow(
                {
                    colonne: _aplatir_valeur_csv(
                        article.get(
                            colonne
                        )
                    )
                    for colonne
                    in COLONNES_EXPORT_CSV
                }
            )

    journaliser(
        f"Export CSV créé : {chemin}"
    )

    return chemin


def exporter_html(
    articles: Iterable[Article],
    rapport: Rapport | None = None,
    *,
    repertoire: str | Path | None = None,
    nom_fichier: str | None = None,
    titre: str = "Veille Découverte Santé",
) -> Path:
    """
    Génère un rapport HTML autonome.
    """
    dossier = _preparer_repertoire(
        repertoire
    )

    chemin = dossier / (
        nom_fichier
        or f"{_nom_base()}.html"
    )

    if chemin.suffix.lower() not in {
        ".html",
        ".htm",
    }:
        chemin = chemin.with_suffix(
            ".html"
        )

    articles_prepares = limiter_articles_par_source(
        articles
    )

    cartes: list[str] = []

    for article in articles_prepares:
        titre_article = escape(
            nettoyer_texte(
                article.get(
                    "titre",
                    "Titre non disponible",
                )
            )
        )

        source = escape(
            nettoyer_texte(
                article.get(
                    "source",
                    "Source inconnue",
                )
            )
        )

        date_article = escape(
            nettoyer_texte(
                article.get(
                    "date",
                    "Date non disponible",
                )
            )
        )

        lien = nettoyer_texte(
            article.get(
                "lien",
                "",
            )
        )

        resume = escape(
            nettoyer_texte(
                article.get(
                    "resume",
                    "",
                )
            )
        )

        categories = escape(
            _aplatir_valeur_csv(
                article.get(
                    "categories",
                    [],
                )
            )
        )

        if lien:
            titre_html = (
                f'<a href="{escape(lien, quote=True)}" '
                'target="_blank" '
                'rel="noopener noreferrer">'
                f"{titre_article}"
                "</a>"
            )

        else:
            titre_html = titre_article

        meta = (
            f"{source} — {date_article}"
        )

        if categories:
            meta += (
                f" — {categories}"
            )

        cartes.append(
            "<article>"
            f"<h2>{titre_html}</h2>"
            f'<p class="meta">{meta}</p>'
            f"<p>{resume or 'Aucun résumé disponible.'}</p>"
            "</article>"
        )

    rapport_html = ""

    if rapport:
        rapport_html = (
            "<details>"
            "<summary>"
            "Rapport technique de collecte"
            "</summary>"
            "<pre>"
            f"{escape(json.dumps(
                _convertir_valeur_json(rapport),
                ensure_ascii=False,
                indent=2,
            ))}"
            "</pre>"
            "</details>"
        )

    contenu_articles = (
        "".join(
            cartes
        )
        if cartes
        else "<p>Aucun article à exporter.</p>"
    )

    date_export = datetime.now().strftime(
        "%d/%m/%Y à %H:%M"
    )

    document = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(titre)}</title>
<style>
body {{
    font-family: Arial, sans-serif;
    max-width: 1000px;
    margin: 0 auto;
    padding: 2rem;
    line-height: 1.55;
}}
h1 {{
    margin-bottom: .25rem;
}}
article {{
    border-top: 1px solid #ddd;
    padding: 1.25rem 0;
}}
h2 {{
    font-size: 1.15rem;
    margin: 0 0 .35rem;
}}
.meta {{
    color: #555;
    font-size: .92rem;
}}
a {{
    color: inherit;
}}
pre {{
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    background: #f5f5f5;
    padding: 1rem;
}}
</style>
</head>
<body>
<h1>{escape(titre)}</h1>
<p>
    Export généré le {escape(date_export)}
    — {len(articles_prepares)} article(s).
</p>
{contenu_articles}
{rapport_html}
</body>
</html>
"""

    chemin.write_text(
        document,
        encoding=ENCODAGE_PAR_DEFAUT,
    )

    journaliser(
        f"Export HTML créé : {chemin}"
    )

    return chemin


def exporter_tous_formats(
    articles: Iterable[Article],
    rapport: Rapport | None = None,
    *,
    repertoire: str | Path | None = None,
) -> dict[str, Path]:
    """
    Crée tous les formats activés dans configuration.py.
    """
    articles_materialises = list(
        articles
    )

    horodatage = datetime.now()
    base = _nom_base(
        horodatage
    )

    fichiers: dict[str, Path] = {}

    if ACTIVER_EXPORT_JSON:
        fichiers["json"] = exporter_json(
            articles_materialises,
            rapport,
            repertoire=repertoire,
            nom_fichier=f"{base}.json",
        )

    if ACTIVER_EXPORT_CSV:
        fichiers["csv"] = exporter_csv(
            articles_materialises,
            repertoire=repertoire,
            nom_fichier=f"{base}.csv",
        )

    if ACTIVER_EXPORT_HTML:
        fichiers["html"] = exporter_html(
            articles_materialises,
            rapport,
            repertoire=repertoire,
            nom_fichier=f"{base}.html",
        )

    return fichiers


__all__ = [
    "exporter_csv",
    "exporter_html",
    "exporter_json",
    "exporter_tous_formats",
    "limiter_articles_par_source",
]