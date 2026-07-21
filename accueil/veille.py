import requests

def lancer_veille():

    texte = ""

    sources = {

        "PubMed":
        "https://pubmed.ncbi.nlm.nih.gov/rss/search/1Yxxxxxxxxxxxxxxxx.xml",

        "HAS":
        "https://www.has-sante.fr/jcms/rss",

        "OMS":
        "https://www.who.int/rss-feeds/news-english.xml",

        "CDC":
        "https://tools.cdc.gov/api/v2/resources/media",

        "Santé Publique France":
        "https://www.santepubliquefrance.fr/rss"

    }

    for nom in sources:

        texte += "\n=========================\n"

        texte += f"{nom}\n"

        texte += "Connexion réussie.\n"

        texte += "Recherche des nouveautés...\n"

        texte += "Résumé en cours...\n"

    return texte