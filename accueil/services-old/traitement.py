from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

from .classification import classifier_article


MOTS_CLES_IMPORTANTS = [
    # Alertes et événements sanitaires
    "outbreak",
    "epidemic",
    "pandemic",
    "emerging disease",
    "health alert",
    "public health emergency",
    "cluster",
    "surveillance",
    "incidence",
    "prevalence",
    "mortality",
    "hospitalization",
    "hospitalisation",

    # Maladies infectieuses
    "infectious disease",
    "infection",
    "virus",
    "viral",
    "bacteria",
    "bacterial",
    "fungal",
    "parasite",
    "zoonosis",
    "zoonotic",
    "antimicrobial resistance",
    "antibiotic resistance",
    "influenza",
    "avian influenza",
    "dengue",
    "measles",
    "mpox",
    "covid",
    "tuberculosis",
    "malaria",
    "rabies",
    "west nile",

    # Vaccination et prévention
    "vaccine",
    "vaccination",
    "immunization",
    "immunisation",
    "booster",
    "prevention",
    "preventive",
    "screening",
    "protection",
    "hygiene",
    "risk reduction",

    # Traitements et innovations médicales
    "treatment",
    "therapy",
    "therapeutic",
    "drug",
    "medication",
    "antiviral",
    "antibiotic",
    "immunotherapy",
    "gene therapy",
    "monoclonal antibody",
    "new treatment",
    "new drug",
    "approved",
    "authorization",
    "authorisation",

    # Niveau de preuve
    "clinical trial",
    "randomized",
    "randomised",
    "phase i",
    "phase ii",
    "phase iii",
    "phase iv",
    "systematic review",
    "meta-analysis",
    "meta analysis",
    "guideline",
    "recommendation",
    "consensus statement",
    "position statement",

    # Santé humaine
    "human health",
    "patient",
    "clinical",
    "hospital",
    "healthcare",
    "public health",
    "diagnosis",
    "treatment",
    "screening",

    # Santé animale
    "animal health",
    "veterinary",
    "livestock",
    "wildlife",
    "avian",
    "poultry",
    "cattle",
    "swine",
    "animal disease",

    # Santé environnementale
    "environmental health",
    "climate change",
    "air pollution",
    "water pollution",
    "air quality",
    "water quality",
    "heatwave",
    "wildfire",
    "pesticide",
    "pfas",
    "microplastic",
    "mosquito",
    "tick",
    "vector-borne",

    # Recommandations et changements officiels
    "new recommendation",
    "updated recommendation",
    "guideline update",
    "policy change",
    "official advice",
    "public health advice",
]


MOTS_TROP_COURANTS = {
    # Anglais
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "into",
    "using",
    "use",
    "used",
    "study",
    "studies",
    "research",
    "analysis",
    "results",
    "effect",
    "effects",
    "health",
    "medical",
    "medicine",
    "clinical",
    "patient",
    "patients",
    "new",
    "based",

    # Français
    "les",
    "des",
    "une",
    "dans",
    "pour",
    "avec",
    "sans",
    "sur",
    "par",
    "aux",
    "est",
    "sont",
    "étude",
    "études",
    "analyse",
    "résultats",
    "santé",
    "médical",
    "médicale",
    "nouveau",
    "nouvelle",
}


def traiter_articles(articles, limite=20):
    """
    Version simple conservée pour compatibilité.

    Retourne uniquement la liste des articles retenus.
    """
    articles_retenus, _, _ = traiter_articles_avec_statistiques(
        articles,
        limite=limite,
    )

    return articles_retenus


def traiter_articles_avec_statistiques(articles, limite=20):
    """
    Nettoie, dédoublonne, classifie et classe les articles.

    Retourne :
        - les articles retenus ;
        - les statistiques de traitement ;
        - le texte de convergence éventuel.
    """
    if not isinstance(articles, list):
        articles = []

    nombre_recupere = len(articles)

    articles_nettoyes = normaliser_articles(articles)
    articles_uniques = supprimer_doublons(articles_nettoyes)
    articles_classes = classer_articles(articles_uniques)
    articles_retenus = articles_classes[:limite]

    doublons_supprimes = max(
        0,
        len(articles_nettoyes) - len(articles_uniques),
    )

    statistiques = {
        "articles_recuperes": nombre_recupere,
        "articles_valides": len(articles_nettoyes),
        "articles_uniques": len(articles_uniques),
        "articles_retenus": len(articles_retenus),
        "doublons_supprimes": doublons_supprimes,
        "sources_interrogees": compter_sources(
            articles_nettoyes
        ),
    }

    convergence = detecter_convergences(
        articles_retenus
    )

    return articles_retenus, statistiques, convergence


def normaliser_articles(articles):
    """
    Vérifie que chaque article possède les champs attendus
    et uniformise son format.
    """
    articles_normalises = []

    for article in articles:
        if not isinstance(article, dict):
            continue

        titre = nettoyer_texte(
            article.get("titre", "")
        )

        source = nettoyer_texte(
            article.get(
                "source",
                "Source inconnue",
            )
        )

        lien = nettoyer_texte(
            article.get("lien", "")
        )

        date = nettoyer_texte(
            article.get(
                "date",
                "Date non disponible",
            )
        )

        date_brute = nettoyer_texte(
            article.get("date_brute", "")
        )

        resume = nettoyer_texte(
            article.get("resume", "")
        )

        requete = nettoyer_texte(
            article.get("requete", "")
        )

        if not titre or not lien:
            continue

        articles_normalises.append(
            {
                "source": source,
                "titre": titre,
                "lien": nettoyer_lien(lien),
                "date": date,
                "date_brute": date_brute,
                "resume": resume,
                "requete": requete,
            }
        )

    return articles_normalises


def supprimer_doublons(articles):
    """
    Supprime les articles ayant le même lien
    ou le même titre normalisé.
    """
    articles_uniques = []
    liens_vus = set()
    titres_vus = set()

    for article in articles:
        lien_normalise = normaliser_pour_comparaison(
            article.get("lien", "")
        )

        titre_normalise = normaliser_pour_comparaison(
            article.get("titre", "")
        )

        if (
            lien_normalise
            and lien_normalise in liens_vus
        ):
            continue

        if (
            titre_normalise
            and titre_normalise in titres_vus
        ):
            continue

        if lien_normalise:
            liens_vus.add(lien_normalise)

        if titre_normalise:
            titres_vus.add(titre_normalise)

        articles_uniques.append(article)

    return articles_uniques


def classer_articles(articles):
    """
    Ajoute la classification One Health et le score documentaire,
    puis classe les articles.

    Priorités de tri :
        1. importance One Health ;
        2. pertinence documentaire ;
        3. récence.
    """
    articles_classes = []

    for article in articles:
        copie = article.copy()

        classification = classifier_article(
            copie
        )

        copie["categories"] = classification.get(
            "categories",
            [],
        )

        copie["one_health"] = classification.get(
            "one_health",
            [],
        )

        copie["preuve"] = classification.get(
            "preuve",
            "Non déterminé",
        )

        copie["niveau_preuve"] = classification.get(
            "niveau_preuve",
            0,
        )

        copie["importance"] = classification.get(
            "importance",
            0,
        )

        copie["niveau_importance"] = (
            classification.get(
                "niveau_importance",
                "Veille documentaire",
            )
        )

        copie["raisons"] = classification.get(
            "raisons",
            [],
        )

        copie["mots_detectes"] = classification.get(
            "mots_detectes",
            [],
        )

        copie["score"] = calculer_score(
            copie
        )

        articles_classes.append(copie)

    return sorted(
        articles_classes,
        key=lambda article: (
            article.get("importance", 0),
            article.get("score", 0),
            convertir_date_tri(
                article.get("date_brute", "")
            ),
        ),
        reverse=True,
    )


def calculer_score(article):
    """
    Calcule un score de pertinence documentaire.

    Ce score est distinct du niveau d'importance One Health.
    Il sert à départager les articles de même importance.
    """
    score = 0

    source = article.get(
        "source",
        "",
    ).lower()

    titre = article.get(
        "titre",
        "",
    ).lower()

    resume = article.get(
        "resume",
        "",
    ).lower()

    contenu = f"{titre} {resume}"

    # Poids des sources actuellement disponibles.
    if source == "pubmed":
        score += 5

    elif source == "arxiv":
        score += 1

    # Les sources officielles seront valorisées
    # lorsqu'elles seront ajoutées à la collecte.
    elif source in {
        "oms",
        "who",
        "has",
        "santé publique france",
        "anses",
        "ecdc",
        "cdc",
        "ema",
        "fda",
        "inserm",
    }:
        score += 8

    for mot_cle in MOTS_CLES_IMPORTANTS:
        if mot_cle in contenu:
            score += 1

    # Types de publications solides.
    if "systematic review" in contenu:
        score += 4

    if (
        "meta-analysis" in contenu
        or "meta analysis" in contenu
    ):
        score += 4

    if (
        "randomized" in contenu
        or "randomised" in contenu
    ):
        score += 3

    if "phase iii" in contenu:
        score += 4

    elif "clinical trial" in contenu:
        score += 2

    if (
        "guideline" in contenu
        or "recommendation" in contenu
        or "position statement" in contenu
    ):
        score += 4

    # Signaux sanitaires.
    if any(
        expression in contenu
        for expression in [
            "outbreak",
            "epidemic",
            "pandemic",
            "public health emergency",
            "health alert",
            "emerging disease",
            "unusual increase",
        ]
    ):
        score += 5

    # Nouveaux vaccins et traitements.
    if any(
        expression in contenu
        for expression in [
            "new vaccine",
            "vaccine approved",
            "new treatment",
            "new therapy",
            "drug approved",
            "new recommendation",
        ]
    ):
        score += 4

    # Santé animale et environnementale.
    if any(
        expression in contenu
        for expression in [
            "zoonotic",
            "zoonosis",
            "avian influenza",
            "animal health",
            "wildlife",
            "environmental health",
            "air pollution",
            "water pollution",
            "climate change",
            "vector-borne",
        ]
    ):
        score += 2

    if len(article.get("resume", "")) >= 300:
        score += 1

    if date_est_recente(
        article.get("date_brute", "")
    ):
        score += 3

    niveau_preuve = article.get(
        "niveau_preuve",
        0,
    )

    if niveau_preuve >= 5:
        score += 4

    elif niveau_preuve == 4:
        score += 3

    elif niveau_preuve == 3:
        score += 2

    return score


def compter_sources(articles):
    """
    Compte les sources réellement représentées
    dans les résultats collectés.
    """
    sources = {
        article.get("source", "").strip()
        for article in articles
        if article.get("source", "").strip()
    }

    return len(sources)


def detecter_convergences(articles):
    """
    Recherche des titres proches provenant de sources différentes.

    La fonction reste volontairement prudente :
    une proximité de vocabulaire ne signifie pas nécessairement
    que les conclusions scientifiques sont identiques.
    """
    convergences = []
    paires_vues = set()

    for index, premier in enumerate(articles):
        mots_premier = extraire_mots_significatifs(
            premier.get("titre", "")
        )

        if len(mots_premier) < 3:
            continue

        for second in articles[index + 1:]:
            source_premier = premier.get(
                "source",
                "",
            )

            source_second = second.get(
                "source",
                "",
            )

            if (
                not source_premier
                or not source_second
                or source_premier == source_second
            ):
                continue

            mots_second = extraire_mots_significatifs(
                second.get("titre", "")
            )

            communs = mots_premier.intersection(
                mots_second
            )

            if len(communs) < 3:
                continue

            union = mots_premier.union(
                mots_second
            )

            if not union:
                continue

            similarite = (
                len(communs) / len(union)
            )

            if similarite < 0.30:
                continue

            cle_paire = tuple(
                sorted(
                    [
                        source_premier,
                        source_second,
                    ]
                )
            )

            if cle_paire in paires_vues:
                continue

            paires_vues.add(cle_paire)

            sujet = ", ".join(
                sorted(communs)[:5]
            )

            convergences.append(
                (
                    f"Des publications de "
                    f"{source_premier} et "
                    f"{source_second} abordent "
                    f"un sujet proche autour de : "
                    f"{sujet}."
                )
            )

            if len(convergences) >= 3:
                break

        if len(convergences) >= 3:
            break

    if not convergences:
        return ""

    introduction = (
        "Plusieurs sources distinctes semblent traiter "
        "de thèmes proches. Cette proximité ne signifie "
        "pas nécessairement que leurs conclusions sont "
        "identiques.\n\n"
    )

    return introduction + "\n".join(
        f"– {texte}"
        for texte in convergences
    )


def extraire_mots_significatifs(texte):
    """
    Extrait les mots utiles pour comparer deux titres.
    """
    texte = texte.lower()
    mot_courant = ""
    mots = []

    for caractere in texte:
        if (
            caractere.isalnum()
            or caractere
            in "éèêëàâäîïôöùûüç"
        ):
            mot_courant += caractere

        else:
            if mot_courant:
                mots.append(mot_courant)
                mot_courant = ""

    if mot_courant:
        mots.append(mot_courant)

    return {
        mot
        for mot in mots
        if (
            len(mot) >= 4
            and mot not in MOTS_TROP_COURANTS
        )
    }


def date_est_recente(
    date_brute,
    nombre_jours=7,
):
    """
    Vérifie si une date ISO est récente.
    """
    date_article = convertir_date(
        date_brute
    )

    if date_article is None:
        return False

    maintenant = datetime.now(
        timezone.utc
    )

    difference = maintenant - date_article

    return (
        difference.total_seconds() >= 0
        and difference.days <= nombre_jours
    )


def convertir_date(date_brute):
    """
    Convertit une date ISO en objet datetime.

    Les dates RSS non ISO ne sont pas converties ici.
    """
    if not date_brute:
        return None

    try:
        date_convertie = datetime.fromisoformat(
            date_brute.replace(
                "Z",
                "+00:00",
            )
        )

        if date_convertie.tzinfo is None:
            date_convertie = (
                date_convertie.replace(
                    tzinfo=timezone.utc
                )
            )

        return date_convertie

    except (ValueError, TypeError):
        return None


def convertir_date_tri(date_brute):
    """
    Retourne une date utilisable pour le classement.
    """
    date_convertie = convertir_date(
        date_brute
    )

    if date_convertie is None:
        return datetime.min.replace(
            tzinfo=timezone.utc
        )

    return date_convertie


def nettoyer_lien(lien):
    """
    Retire le fragment d'une URL pour faciliter
    le dédoublonnage.
    """
    if not lien:
        return ""

    try:
        parties = urlsplit(lien)

        return urlunsplit(
            (
                parties.scheme,
                parties.netloc,
                parties.path,
                parties.query,
                "",
            )
        )

    except ValueError:
        return lien


def normaliser_pour_comparaison(texte):
    """
    Transforme un texte pour comparer
    les titres et les liens.
    """
    if not texte:
        return ""

    caracteres_conserves = []

    for caractere in texte.lower():
        if caractere.isalnum():
            caracteres_conserves.append(
                caractere
            )

    return "".join(
        caracteres_conserves
    )


def nettoyer_texte(texte):
    """
    Nettoie les retours à la ligne
    et les espaces multiples.
    """
    if texte is None:
        return ""

    texte = str(texte)

    return " ".join(
        texte
        .replace("\n", " ")
        .replace("\r", " ")
        .split()
    )
