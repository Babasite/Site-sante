from datetime import datetime
import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


REQUETES_ARXIV = [
    {
        "nom": "Épidémiologie et maladies émergentes",
        "expression": (
            '(ti:"emerging disease" OR abs:"emerging disease" '
            'OR ti:outbreak OR abs:outbreak '
            'OR ti:epidemic OR abs:epidemic) '
            'AND '
            '(ti:health OR abs:health '
            'OR ti:clinical OR abs:clinical '
            'OR ti:epidemiology OR abs:epidemiology)'
        ),
    },
    {
        "nom": "Vaccins",
        "expression": (
            '(ti:vaccine OR abs:vaccine '
            'OR ti:vaccination OR abs:vaccination '
            'OR ti:immunization OR abs:immunization) '
            'AND '
            '(ti:human OR abs:human '
            'OR ti:animal OR abs:animal '
            'OR ti:clinical OR abs:clinical '
            'OR ti:public_health OR abs:public_health)'
        ),
    },
    {
        "nom": "Nouveaux traitements",
        "expression": (
            '(ti:"new treatment" OR abs:"new treatment" '
            'OR ti:"gene therapy" OR abs:"gene therapy" '
            'OR ti:immunotherapy OR abs:immunotherapy '
            'OR ti:"monoclonal antibody" '
            'OR abs:"monoclonal antibody") '
            'AND '
            '(ti:disease OR abs:disease '
            'OR ti:patient OR abs:patient '
            'OR ti:clinical OR abs:clinical)'
        ),
    },
    {
        "nom": "Santé animale et zoonoses",
        "expression": (
            '(ti:zoonosis OR abs:zoonosis '
            'OR ti:zoonotic OR abs:zoonotic '
            'OR ti:"animal health" OR abs:"animal health" '
            'OR ti:veterinary OR abs:veterinary '
            'OR ti:"avian influenza" OR abs:"avian influenza")'
        ),
    },
    {
        "nom": "Santé environnementale",
        "expression": (
            '(ti:"environmental health" '
            'OR abs:"environmental health" '
            'OR ti:"air pollution" OR abs:"air pollution" '
            'OR ti:"water pollution" OR abs:"water pollution" '
            'OR ti:"climate change" OR abs:"climate change" '
            'OR ti:heatwave OR abs:heatwave '
            'OR ti:pesticide OR abs:pesticide '
            'OR ti:microplastic OR abs:microplastic) '
            'AND '
            '(ti:health OR abs:health '
            'OR ti:disease OR abs:disease '
            'OR ti:mortality OR abs:mortality)'
        ),
    },
    {
        "nom": "IA en santé",
        "expression": (
            '(ti:"artificial intelligence" '
            'OR abs:"artificial intelligence" '
            'OR ti:"machine learning" '
            'OR abs:"machine learning" '
            'OR ti:"large language model" '
            'OR abs:"large language model") '
            'AND '
            '(ti:medicine OR abs:medicine '
            'OR ti:medical OR abs:medical '
            'OR ti:clinical OR abs:clinical '
            'OR ti:healthcare OR abs:healthcare '
            'OR ti:patient OR abs:patient)'
        ),
    },
]


URL_PUBMED_RSS = (
    "https://pubmed.ncbi.nlm.nih.gov/rss/search/"
    "1XcGXNf4jP0xA1qAq9Qn/"
    "?limit=10&utm_campaign=pubmed-2"
)


TERMES_SANTE_OBLIGATOIRES = [
    "health",
    "medical",
    "medicine",
    "clinical",
    "patient",
    "disease",
    "infection",
    "infectious",
    "epidemic",
    "outbreak",
    "vaccine",
    "vaccination",
    "treatment",
    "therapy",
    "drug",
    "public health",
    "epidemiology",
    "mortality",
    "hospital",
    "diagnosis",
    "screening",
    "zoonosis",
    "zoonotic",
    "veterinary",
    "animal health",
    "environmental health",
    "air pollution",
    "water pollution",
    "climate change",
]


TERMES_HORS_SUJET = [
    "dark matter",
    "black hole",
    "gravitational wave",
    "galaxy",
    "galaxies",
    "cosmology",
    "astrophysics",
    "quantum gravity",
    "particle collider",
    "supernova",
    "lisa mission",
    "stellar",
]


def collecter_articles():
    """
    Lance toutes les collectes actuellement disponibles.

    Retourne toujours une liste de dictionnaires.
    """
    articles = []

    articles.extend(collecter_arxiv())
    articles.extend(collecter_pubmed())

    return articles


def collecter_arxiv():
    """
    Recherche des publications arXiv avec des requêtes strictes.

    Les résultats manifestement hors du champ sanitaire sont rejetés.
    """
    articles = []

    namespace = {
        "atom": "http://www.w3.org/2005/Atom",
    }

    for configuration in REQUETES_ARXIV:
        nom_requete = configuration["nom"]
        expression = configuration["expression"]

        parametres = urllib.parse.urlencode(
            {
                "search_query": expression,
                "start": 0,
                "max_results": 5,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
        )

        url = (
            "https://export.arxiv.org/api/query?"
            f"{parametres}"
        )

        try:
            contenu = telecharger(url)
            racine = ET.fromstring(contenu)

            for entree in racine.findall(
                "atom:entry",
                namespace,
            ):
                titre = nettoyer_texte(
                    entree.findtext(
                        "atom:title",
                        default="",
                        namespaces=namespace,
                    )
                )

                lien = nettoyer_texte(
                    entree.findtext(
                        "atom:id",
                        default="",
                        namespaces=namespace,
                    )
                )

                date_publication = nettoyer_texte(
                    entree.findtext(
                        "atom:published",
                        default="",
                        namespaces=namespace,
                    )
                )

                resume = nettoyer_texte(
                    entree.findtext(
                        "atom:summary",
                        default="",
                        namespaces=namespace,
                    )
                )

                if not titre or not lien:
                    continue

                if not article_est_sanitaire(
                    titre=titre,
                    resume=resume,
                ):
                    continue

                articles.append(
                    {
                        "source": "arXiv",
                        "titre": titre,
                        "lien": lien,
                        "date": formater_date(
                            date_publication
                        ),
                        "date_brute": date_publication,
                        "resume": resume,
                        "requete": nom_requete,
                    }
                )

        except Exception as erreur:
            print(
                f"Erreur arXiv pour la requête "
                f"'{nom_requete}' : {erreur}"
            )

    return articles


def collecter_pubmed():
    """
    Lit le flux RSS PubMed configuré.

    Une indisponibilité de PubMed ne bloque pas les autres sources.
    """
    articles = []

    try:
        contenu = telecharger(
            URL_PUBMED_RSS
        )

        racine = ET.fromstring(
            contenu
        )

        canal = racine.find("channel")

        if canal is None:
            return articles

        for item in canal.findall("item"):
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

            description = nettoyer_html(
                item.findtext(
                    "description",
                    default="",
                )
            )

            date_publication = nettoyer_texte(
                item.findtext(
                    "pubDate",
                    default="",
                )
            )

            if not titre or not lien:
                continue

            articles.append(
                {
                    "source": "PubMed",
                    "titre": titre,
                    "lien": lien,
                    "date": (
                        date_publication
                        or "Date non disponible"
                    ),
                    "date_brute": date_publication,
                    "resume": description,
                    "requete": "Flux RSS PubMed",
                }
            )

    except Exception as erreur:
        print(
            f"Erreur PubMed : {erreur}"
        )

    return articles


def article_est_sanitaire(
    titre,
    resume,
):
    """
    Vérifie qu’un résultat arXiv contient réellement
    un vocabulaire sanitaire pertinent.

    Ce filtre est volontairement conservateur.
    """
    contenu = normaliser_pour_filtre(
        f"{titre} {resume}"
    )

    if any(
        terme in contenu
        for terme in TERMES_HORS_SUJET
    ):
        return False

    return any(
        terme in contenu
        for terme in TERMES_SANTE_OBLIGATOIRES
    )


def telecharger(url):
    """
    Télécharge une ressource distante et retourne son contenu binaire.
    """
    requete = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Sante-Prevention-Terrain/"
                "1.0 veille-scientifique"
            )
        },
    )

    with urllib.request.urlopen(
        requete,
        timeout=30,
    ) as reponse:
        return reponse.read()


def nettoyer_texte(texte):
    """
    Supprime les retours à la ligne et les espaces inutiles.
    """
    if not texte:
        return ""

    return " ".join(
        str(texte)
        .replace("\n", " ")
        .replace("\r", " ")
        .split()
    )


def nettoyer_html(texte):
    """
    Nettoie le HTML simple parfois présent dans les flux RSS.
    """
    if not texte:
        return ""

    texte = html.unescape(
        str(texte)
    )

    texte = re.sub(
        r"<[^>]+>",
        " ",
        texte,
    )

    return nettoyer_texte(
        texte
    )


def normaliser_pour_filtre(texte):
    """
    Prépare un texte pour le filtrage sanitaire.
    """
    texte = str(texte).lower()

    texte = re.sub(
        r"[^a-z0-9\s-]",
        " ",
        texte,
    )

    return " ".join(
        texte.split()
    )


def formater_date(date):
    """
    Transforme une date ISO arXiv en date française.
    """
    if not date:
        return "Date non disponible"

    try:
        date_convertie = datetime.fromisoformat(
            date.replace(
                "Z",
                "+00:00",
            )
        )

        return date_convertie.strftime(
            "%d/%m/%Y"
        )

    except (ValueError, TypeError):
        return date
    