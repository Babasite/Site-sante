"""
Collecteur PubMed pour la veille scientifique.

Le module utilise les E-utilities officielles du NCBI :
- ESearch recherche les identifiants PubMed ;
- EFetch récupère les notices complètes en XML.

PubMed constitue la source scientifique principale de la veille.
"""

from __future__ import annotations

import time
from typing import Any
import urllib.parse
import xml.etree.ElementTree as ET

from .utilitaires import (
    construire_article,
    journaliser,
    nettoyer_texte,
    telecharger,
    telecharger_json,
    texte_xml_complet,
)


# ============================================================
# CONFIGURATION
# ============================================================

URL_ESEARCH = (
    "https://eutils.ncbi.nlm.nih.gov/"
    "entrez/eutils/esearch.fcgi"
)

URL_EFETCH = (
    "https://eutils.ncbi.nlm.nih.gov/"
    "entrez/eutils/efetch.fcgi"
)

# Sans clé API, cette pause maintient un rythme inférieur
# à trois requêtes par seconde.
PAUSE_ENTRE_APPELS = 0.40

NOMBRE_JOURS = 14
MAX_RESULTATS_PAR_REQUETE = 10


REQUETES_PUBMED = [
    {
        "nom": "Maladies émergentes et épidémies",
        "expression": (
            '("Disease Outbreaks"[Mesh] '
            'OR outbreak*[Title/Abstract] '
            'OR epidemic*[Title/Abstract] '
            'OR "emerging infectious disease*"[Title/Abstract])'
        ),
    },
    {
        "nom": "Vaccination",
        "expression": (
            '("Vaccines"[Mesh] '
            'OR vaccin*[Title/Abstract] '
            'OR immunization[Title/Abstract] '
            'OR immunisation[Title/Abstract])'
        ),
    },
    {
        "nom": "Zoonoses et One Health",
        "expression": (
            '("Zoonoses"[Mesh] '
            'OR zoonos*[Title/Abstract] '
            'OR "One Health"[Title/Abstract] '
            'OR "animal health"[Title/Abstract] '
            'OR veterinary[Title/Abstract])'
        ),
    },
    {
        "nom": "Santé environnementale",
        "expression": (
            '("Environmental Health"[Mesh] '
            'OR "air pollution"[Title/Abstract] '
            'OR "water pollution"[Title/Abstract] '
            'OR "climate change"[Title/Abstract] '
            'OR heatwave*[Title/Abstract] '
            'OR pesticide*[Title/Abstract] '
            'OR microplastic*[Title/Abstract])'
        ),
    },
    {
        "nom": "Antibiorésistance",
        "expression": (
            '("Drug Resistance, Microbial"[Mesh] '
            'OR "antimicrobial resistance"[Title/Abstract] '
            'OR "antibiotic resistance"[Title/Abstract])'
        ),
    },
    {
        "nom": "Prévention et dépistage",
        "expression": (
            '("Preventive Health Services"[Mesh] '
            'OR prevention[Title/Abstract] '
            'OR screening[Title/Abstract] '
            'OR "early detection"[Title/Abstract])'
        ),
    },
    {
        "nom": "Santé publique et surveillance",
        "expression": (
            '("Public Health"[Mesh] '
            'OR "public health surveillance"[Title/Abstract] '
            'OR epidemiological surveillance[Title/Abstract] '
            'OR syndromic surveillance[Title/Abstract])'
        ),
    },
    {
        "nom": "Nutrition et santé",
        "expression": (
            '("Nutrition Therapy"[Mesh] '
            'OR nutrition[Title/Abstract] '
            'OR dietary[Title/Abstract] '
            'OR diet[Title/Abstract]) '
            'AND (health[Title/Abstract] '
            'OR disease[Title/Abstract] '
            'OR prevention[Title/Abstract])'
        ),
    },
    {
        "nom": "Santé mentale",
        "expression": (
            '("Mental Health"[Mesh] '
            'OR "mental health"[Title/Abstract] '
            'OR depression[Title/Abstract] '
            'OR anxiety[Title/Abstract]) '
            'AND (prevention[Title/Abstract] '
            'OR treatment[Title/Abstract] '
            'OR epidemiology[Title/Abstract])'
        ),
    },
    {
        "nom": "Essais cliniques et traitements",
        "expression": (
            '("Clinical Trial"[Publication Type] '
            'OR "Randomized Controlled Trial"[Publication Type] '
            'OR "Systematic Review"[Publication Type] '
            'OR "Meta-Analysis"[Publication Type]) '
            'AND (treatment[Title/Abstract] '
            'OR therapy[Title/Abstract] '
            'OR intervention[Title/Abstract])'
        ),
    },
    {
        "nom": "Intelligence artificielle en santé",
        "expression": (
            '("Artificial Intelligence"[Mesh] '
            'OR "machine learning"[Title/Abstract] '
            'OR "large language model*"[Title/Abstract]) '
            'AND (health[Title/Abstract] '
            'OR clinical[Title/Abstract] '
            'OR medical[Title/Abstract] '
            'OR healthcare[Title/Abstract])'
        ),
    },
    {
        "nom": "Urgences et soins critiques",
        "expression": (
            '("Emergency Medicine"[Mesh] '
            'OR emergency[Title/Abstract] '
            'OR "critical care"[Title/Abstract] '
            'OR intensive care[Title/Abstract]) '
            'AND (prevention[Title/Abstract] '
            'OR diagnosis[Title/Abstract] '
            'OR treatment[Title/Abstract])'
        ),
    },
]


# ============================================================
# COLLECTE PRINCIPALE
# ============================================================

def collecter_pubmed(
    *,
    nombre_jours: int = NOMBRE_JOURS,
    limite_par_requete: int = MAX_RESULTATS_PAR_REQUETE,
) -> list[dict[str, Any]]:
    """
    Lance toutes les requêtes PubMed configurées.

    Une erreur sur une requête n'empêche pas les autres
    recherches de continuer.
    """
    articles: list[dict[str, Any]] = []

    journaliser(
        (
            "PubMed : lancement de "
            f"{len(REQUETES_PUBMED)} recherches."
        )
    )

    for configuration in REQUETES_PUBMED:
        nom_requete = configuration["nom"]
        expression = configuration["expression"]

        try:
            identifiants = rechercher_identifiants(
                expression=expression,
                nombre_jours=nombre_jours,
                limite=limite_par_requete,
            )

            time.sleep(PAUSE_ENTRE_APPELS)

            if not identifiants:
                journaliser(
                    f"PubMed — {nom_requete} : aucun résultat."
                )
                continue

            resultats = recuperer_articles(
                identifiants=identifiants,
                nom_requete=nom_requete,
            )

            articles.extend(resultats)

            journaliser(
                (
                    f"PubMed — {nom_requete} : "
                    f"{len(resultats)} article(s)."
                )
            )

            time.sleep(PAUSE_ENTRE_APPELS)

        except Exception as erreur:
            journaliser(
                (
                    f"PubMed — erreur pour "
                    f"« {nom_requete} » : {erreur}"
                ),
                "ERREUR",
            )

    journaliser(
        f"PubMed : {len(articles)} article(s) collecté(s)."
    )

    return articles


# ============================================================
# ESEARCH
# ============================================================

def rechercher_identifiants(
    *,
    expression: str,
    nombre_jours: int,
    limite: int,
) -> list[str]:
    """
    Recherche les PMID les plus récents correspondant
    à une expression PubMed.
    """
    nombre_jours = max(
        1,
        int(nombre_jours),
    )

    limite = max(
        1,
        int(limite),
    )

    expression_complete = (
        f"({expression}) AND "
        f'("last {nombre_jours} days"[PDat])'
    )

    parametres = urllib.parse.urlencode(
        {
            "db": "pubmed",
            "term": expression_complete,
            "retmode": "json",
            "retmax": limite,
            "sort": "pub date",
            "tool": "SantePreventionTerrain",
        }
    )

    url = f"{URL_ESEARCH}?{parametres}"

    donnees = telecharger_json(url)

    if not isinstance(donnees, dict):
        raise ValueError(
            "La réponse ESearch n'est pas un objet JSON."
        )

    resultat = donnees.get(
        "esearchresult",
        {},
    )

    if not isinstance(resultat, dict):
        return []

    identifiants = resultat.get(
        "idlist",
        [],
    )

    if not isinstance(identifiants, list):
        return []

    return [
        str(identifiant).strip()
        for identifiant in identifiants
        if str(identifiant).strip()
    ]


# ============================================================
# EFETCH
# ============================================================

def recuperer_articles(
    *,
    identifiants: list[str],
    nom_requete: str,
) -> list[dict[str, Any]]:
    """
    Récupère les notices PubMed complètes en XML.
    """
    if not identifiants:
        return []

    parametres = urllib.parse.urlencode(
        {
            "db": "pubmed",
            "id": ",".join(identifiants),
            "retmode": "xml",
            "tool": "SantePreventionTerrain",
        }
    )

    url = f"{URL_EFETCH}?{parametres}"

    contenu = telecharger(url)

    try:
        racine = ET.fromstring(contenu)

    except ET.ParseError as erreur:
        raise ValueError(
            "La réponse XML de PubMed est invalide."
        ) from erreur

    articles: list[dict[str, Any]] = []

    for notice in racine.findall(
        ".//PubmedArticle"
    ):
        article = convertir_notice_pubmed(
            notice=notice,
            nom_requete=nom_requete,
        )

        if article is not None:
            articles.append(article)

    return articles


# ============================================================
# CONVERSION DES NOTICES
# ============================================================

def convertir_notice_pubmed(
    *,
    notice: ET.Element,
    nom_requete: str,
) -> dict[str, Any] | None:
    """
    Transforme une notice PubMed XML au format commun du projet.
    """
    citation = notice.find(
        "MedlineCitation"
    )

    if citation is None:
        return None

    article_xml = citation.find(
        "Article"
    )

    if article_xml is None:
        return None

    pmid = nettoyer_texte(
        citation.findtext(
            "PMID",
            default="",
        )
    )

    titre = texte_xml_complet(
        article_xml.find(
            "ArticleTitle"
        )
    )

    if not pmid or not titre:
        return None

    resume = extraire_resume(
        article_xml
    )

    date_brute = extraire_date(
        article_xml
    )

    journal = nettoyer_texte(
        article_xml.findtext(
            ".//Journal/Title",
            default="",
        )
    )

    types_publication = [
        nettoyer_texte(
            element.text
        )
        for element in article_xml.findall(
            ".//PublicationTypeList/PublicationType"
        )
        if nettoyer_texte(element.text)
    ]

    auteurs = extraire_auteurs(
        article_xml
    )

    doi = extraire_doi(
        notice
    )

    return construire_article(
        source="PubMed",
        titre=titre,
        lien=(
            "https://pubmed.ncbi.nlm.nih.gov/"
            f"{pmid}/"
        ),
        resume=resume,
        date_brute=date_brute,
        requete=nom_requete,
        pmid=pmid,
        doi=doi,
        journal=journal,
        auteurs=auteurs,
        types_publication=types_publication,
    )


def extraire_resume(
    article_xml: ET.Element,
) -> str:
    """
    Assemble toutes les parties du résumé structuré.
    """
    parties: list[str] = []

    for element in article_xml.findall(
        ".//Abstract/AbstractText"
    ):
        texte = texte_xml_complet(
            element
        )

        if not texte:
            continue

        etiquette = nettoyer_texte(
            element.attrib.get(
                "Label",
                "",
            )
        )

        if etiquette:
            parties.append(
                f"{etiquette} : {texte}"
            )
        else:
            parties.append(texte)

    return " ".join(parties)


def extraire_date(
    article_xml: ET.Element,
) -> str:
    """
    Extrait la date de publication la plus exploitable.
    """
    date_pubmed = article_xml.find(
        ".//ArticleDate"
    )

    if date_pubmed is not None:
        annee = nettoyer_texte(
            date_pubmed.findtext(
                "Year",
                default="",
            )
        )

        mois = nettoyer_texte(
            date_pubmed.findtext(
                "Month",
                default="",
            )
        )

        jour = nettoyer_texte(
            date_pubmed.findtext(
                "Day",
                default="",
            )
        )

        date_complete = "-".join(
            partie
            for partie in (
                annee,
                mois.zfill(2) if mois else "",
                jour.zfill(2) if jour else "",
            )
            if partie
        )

        if date_complete:
            return date_complete

    date_journal = article_xml.find(
        ".//JournalIssue/PubDate"
    )

    if date_journal is None:
        return ""

    annee = nettoyer_texte(
        date_journal.findtext(
            "Year",
            default="",
        )
    )

    mois = nettoyer_texte(
        date_journal.findtext(
            "Month",
            default="",
        )
    )

    jour = nettoyer_texte(
        date_journal.findtext(
            "Day",
            default="",
        )
    )

    date_medline = nettoyer_texte(
        date_journal.findtext(
            "MedlineDate",
            default="",
        )
    )

    morceaux = [
        morceau
        for morceau in (
            jour,
            mois,
            annee,
        )
        if morceau
    ]

    if morceaux:
        return " ".join(morceaux)

    return date_medline


def extraire_auteurs(
    article_xml: ET.Element,
) -> list[str]:
    """
    Retourne une liste courte des auteurs disponibles.
    """
    auteurs: list[str] = []

    for auteur_xml in article_xml.findall(
        ".//AuthorList/Author"
    ):
        collectif = nettoyer_texte(
            auteur_xml.findtext(
                "CollectiveName",
                default="",
            )
        )

        if collectif:
            auteurs.append(collectif)
            continue

        nom = nettoyer_texte(
            auteur_xml.findtext(
                "LastName",
                default="",
            )
        )

        initiales = nettoyer_texte(
            auteur_xml.findtext(
                "Initials",
                default="",
            )
        )

        auteur = nettoyer_texte(
            f"{nom} {initiales}"
        )

        if auteur:
            auteurs.append(auteur)

    return auteurs


def extraire_doi(
    notice: ET.Element,
) -> str:
    """
    Extrait le DOI quand PubMed le fournit.
    """
    for identifiant in notice.findall(
        ".//PubmedData/ArticleIdList/ArticleId"
    ):
        type_identifiant = nettoyer_texte(
            identifiant.attrib.get(
                "IdType",
                "",
            )
        ).lower()

        if type_identifiant == "doi":
            return nettoyer_texte(
                identifiant.text
            )

    return ""