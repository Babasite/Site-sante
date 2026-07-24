from datetime import datetime
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET


REQUETES = [
    "artificial intelligence medicine",
    "large language model healthcare",
    "clinical trial artificial intelligence",
    "digital health",
]

SOURCES_RSS = [
    {
        "source": "arXiv",
        "url": "https://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results=5",
    },
    {
        "source": "PubMed",
        "url": "https://pubmed.ncbi.nlm.nih.gov/rss/search/1XcGXNf4jP0xA1qAq9Qn/?limit=5&utm_campaign=pubmed-2&fc=20260101000000",
    },
]

ACTEURS = [
    {
        "source": "OpenAI",
        "titre": "Actualités OpenAI",
        "lien": "https://openai.com/news/",
    },
    {
        "source": "Google DeepMind",
        "titre": "Actualités Google DeepMind",
        "lien": "https://deepmind.google/discover/blog/",
    },
    {
        "source": "Anthropic",
        "titre": "Actualités Anthropic",
        "lien": "https://www.anthropic.com/news",
    },
    {
        "source": "Meta AI",
        "titre": "Actualités Meta AI",
        "lien": "https://ai.meta.com/blog/",
    },
    {
        "source": "Microsoft Research",
        "titre": "Actualités Microsoft Research",
        "lien": "https://www.microsoft.com/en-us/research/blog/",
    },
    {
        "source": "Mistral AI",
        "titre": "Actualités Mistral AI",
        "lien": "https://mistral.ai/news/",
    },
]


def lancer_veille():
    resultats = []

    resultats.extend(rechercher_arxiv())
    resultats.extend(rechercher_acteurs())

    resume = generer_resume_global(resultats)

    return resultats, resume


def rechercher_arxiv():
    articles = []

    for requete in REQUETES:
        query = urllib.parse.quote(requete)
        url = f"https://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results=3"

        try:
            contenu = telecharger(url)
            racine = ET.fromstring(contenu)

            namespace = {"atom": "http://www.w3.org/2005/Atom"}

            for entry in racine.findall("atom:entry", namespace):
                titre = nettoyer(entry.findtext("atom:title", default="", namespaces=namespace))
                lien = entry.findtext("atom:id", default="", namespaces=namespace)
                date = entry.findtext("atom:published", default="", namespaces=namespace)
                resume = nettoyer(entry.findtext("atom:summary", default="", namespaces=namespace))

                articles.append(
                    {
                        "source": "arXiv",
                        "titre": titre,
                        "lien": lien,
                        "date": format_date(date),
                        "resume": resume[:700] + "..." if len(resume) > 700 else resume,
                    }
                )

        except Exception as erreur:
            articles.append(
                {
                    "source": "arXiv",
                    "titre": f"Erreur lors de la recherche : {requete}",
                    "lien": "https://arxiv.org/",
                    "date": datetime.today().strftime("%d/%m/%Y"),
                    "resume": str(erreur),
                }
            )

    return articles


def rechercher_acteurs():
    articles = []

    for acteur in ACTEURS:
        articles.append(
            {
                "source": acteur["source"],
                "titre": acteur["titre"],
                "lien": acteur["lien"],
                "date": datetime.today().strftime("%d/%m/%Y"),
                "resume": (
                    "Source ajoutée à la veille. Pour l'instant, cette entrée sert à suivre "
                    "les pages officielles de l'acteur. L'étape suivante consistera à lire "
                    "automatiquement les nouveautés publiées sur cette page."
                ),
            }
        )

    return articles


def telecharger(url):
    requete = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 veille-scientifique"
        }
    )

    with urllib.request.urlopen(requete, timeout=10) as reponse:
        return reponse.read()


def generer_resume_global(resultats):
    if not resultats:
        return "Aucune nouveauté n'a été trouvée."

    sources = sorted(set(article.get("source", "Source inconnue") for article in resultats))

    texte = "Synthèse de la veille scientifique\n\n"

    texte += (
        f"{len(resultats)} élément(s) ont été identifiés dans cette veille. "
        f"Les sources couvertes sont : {', '.join(sources)}.\n\n"
    )

    texte += "Résumé des nouveautés détectées :\n"

    for article in resultats[:12]:
        texte += f"\n- {article.get('source')} — {article.get('titre')}\n"
        texte += f"  {article.get('resume', '')[:350]}...\n"

    texte += (
        "\nAnalyse générale :\n"
        "Cette veille combine des bases scientifiques et des acteurs clés de l'intelligence artificielle. "
        "Les résultats issus d'arXiv correspondent à des publications récentes ou indexées par mots-clés. "
        "Les entrées concernant les acteurs comme OpenAI, DeepMind, Anthropic, Meta AI, Microsoft Research "
        "et Mistral AI sont pour l'instant des points de surveillance officiels.\n\n"
    )

    texte += (
        "Prochaine amélioration recommandée :\n"
        "connecter automatiquement les flux RSS ou les pages d'actualité de chaque acteur, puis utiliser GPT "
        "pour produire une vraie synthèse d'une page, hiérarchisée par importance."
    )

    return texte


def nettoyer(texte):
    return " ".join(texte.replace("\n", " ").split())


def format_date(date):
    if not date:
        return "Date non disponible"

    try:
        return datetime.fromisoformat(date.replace("Z", "+00:00")).strftime("%d/%m/%Y")
    except Exception:
        return date
    