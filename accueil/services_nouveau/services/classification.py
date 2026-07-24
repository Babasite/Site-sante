import re
import unicodedata


REGLES_CATEGORIES = {
    "Vaccination": [
        "vaccine",
        "vaccination",
        "vaccinated",
        "booster",
        "immunization",
        "immunisation",
        "mrna vaccine",
        "messenger rna vaccine",
    ],
    "Traitements": [
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
    ],
    "Maladies infectieuses": [
        "infection",
        "infectious disease",
        "outbreak",
        "epidemic",
        "pandemic",
        "virus",
        "viral",
        "bacteria",
        "bacterial",
        "fungal",
        "parasite",
        "zoonosis",
        "zoonotic",
    ],
    "Recommandations": [
        "guideline",
        "recommendation",
        "consensus",
        "position statement",
        "official update",
        "public health advice",
    ],
    "Essais cliniques": [
        "clinical trial",
        "randomized trial",
        "randomised trial",
        "phase i",
        "phase ii",
        "phase iii",
        "phase iv",
        "placebo-controlled",
    ],
    "Revues scientifiques": [
        "systematic review",
        "meta-analysis",
        "meta analysis",
        "scoping review",
        "umbrella review",
    ],
    "IA médicale": [
        "artificial intelligence",
        "machine learning",
        "deep learning",
        "large language model",
        "llm",
        "foundation model",
        "neural network",
    ],
    "Santé environnementale": [
        "air pollution",
        "water pollution",
        "environmental health",
        "climate change",
        "heatwave",
        "wildfire",
        "pesticide",
        "pfas",
        "microplastic",
        "air quality",
        "water quality",
    ],
    "Santé animale": [
        "veterinary",
        "animal health",
        "livestock",
        "wildlife",
        "avian",
        "poultry",
        "cattle",
        "swine",
        "pig",
        "bird",
        "bat",
    ],
    "Prévention": [
        "prevention",
        "preventive",
        "screening",
        "protection",
        "hygiene",
        "public health measure",
        "risk reduction",
    ],
}


REGLES_ONE_HEALTH = {
    "Humain": [
        "human",
        "patient",
        "clinical",
        "hospital",
        "healthcare",
        "population",
        "public health",
        "medicine",
        "medical",
    ],
    "Animal": [
        "animal",
        "veterinary",
        "livestock",
        "wildlife",
        "avian",
        "poultry",
        "cattle",
        "swine",
        "pig",
        "bird",
        "bat",
    ],
    "Environnement": [
        "environment",
        "environmental",
        "climate",
        "air",
        "water",
        "soil",
        "pollution",
        "heatwave",
        "wildfire",
        "mosquito",
        "tick",
        "vector-borne",
    ],
}


REGLES_PREUVE = [
    (
        "Recommandation officielle",
        [
            "guideline",
            "recommendation",
            "consensus statement",
            "position statement",
        ],
        5,
    ),
    (
        "Revue systématique ou méta-analyse",
        [
            "systematic review",
            "meta-analysis",
            "meta analysis",
            "umbrella review",
        ],
        5,
    ),
    (
        "Essai clinique de phase III",
        [
            "phase iii",
        ],
        4,
    ),
    (
        "Essai clinique randomisé",
        [
            "randomized trial",
            "randomised trial",
            "randomized controlled trial",
            "randomised controlled trial",
        ],
        4,
    ),
    (
        "Essai clinique",
        [
            "clinical trial",
            "phase i",
            "phase ii",
            "phase iv",
        ],
        3,
    ),
    (
        "Étude observationnelle",
        [
            "cohort study",
            "case-control",
            "cross-sectional",
            "observational study",
        ],
        3,
    ),
    (
        "Prépublication ou résultats préliminaires",
        [
            "preprint",
            "preliminary",
            "pilot study",
            "proof of concept",
        ],
        1,
    ),
]


SOURCES_OFFICIELLES = {
    "OMS",
    "WHO",
    "HAS",
    "Santé publique France",
    "ANSES",
    "ECDC",
    "CDC",
    "EMA",
    "FDA",
    "INSERM",
}


class ClassificateurOneHealth:
    def classifier(self, article):
        texte = self._construire_texte(article)
        source = str(article.get("source", "")).strip()

        categories, mots_categories = self._detecter_regles(
            texte,
            REGLES_CATEGORIES,
        )

        one_health, mots_one_health = self._detecter_regles(
            texte,
            REGLES_ONE_HEALTH,
        )

        preuve, niveau_preuve, raison_preuve = self._detecter_preuve(
            texte
        )

        importance, niveau_importance, raisons_importance = (
            self._calculer_importance(
                article=article,
                texte=texte,
                source=source,
                categories=categories,
                niveau_preuve=niveau_preuve,
            )
        )

        mots_detectes = sorted(
            set(mots_categories + mots_one_health)
        )

        raisons = []

        if raison_preuve:
            raisons.append(raison_preuve)

        raisons.extend(raisons_importance)

        return {
            "categories": categories,
            "one_health": one_health,
            "preuve": preuve,
            "niveau_preuve": niveau_preuve,
            "importance": importance,
            "niveau_importance": niveau_importance,
            "raisons": raisons,
            "mots_detectes": mots_detectes,
        }

    def _construire_texte(self, article):
        titre = str(article.get("titre", ""))
        resume = str(article.get("resume", ""))
        source = str(article.get("source", ""))

        texte = f"{titre} {resume} {source}"

        return self._normaliser(texte)

    def _detecter_regles(self, texte, regles):
        elements_detectes = []
        mots_detectes = []

        for nom, mots_cles in regles.items():
            correspondances = [
                mot_cle
                for mot_cle in mots_cles
                if self._contient_expression(
                    texte,
                    self._normaliser(mot_cle),
                )
            ]

            if correspondances:
                elements_detectes.append(nom)
                mots_detectes.extend(correspondances)

        return elements_detectes, mots_detectes

    def _detecter_preuve(self, texte):
        for preuve, mots_cles, niveau in REGLES_PREUVE:
            for mot_cle in mots_cles:
                mot_normalise = self._normaliser(mot_cle)

                if self._contient_expression(
                    texte,
                    mot_normalise,
                ):
                    return (
                        preuve,
                        niveau,
                        f"Niveau de preuve détecté : {preuve}.",
                    )

        return (
            "Non déterminé",
            0,
            "Le niveau de preuve n’a pas pu être déterminé automatiquement.",
        )

    def _calculer_importance(
        self,
        article,
        texte,
        source,
        categories,
        niveau_preuve,
    ):
        score = 0
        raisons = []

        if source in SOURCES_OFFICIELLES:
            score += 4
            raisons.append(
                f"Source officielle détectée : {source}."
            )

        if "Recommandations" in categories:
            score += 3
            raisons.append(
                "Présence d’une recommandation ou d’une mise à jour officielle."
            )

        if "Essais cliniques" in categories:
            score += 2
            raisons.append(
                "Présence d’un essai clinique."
            )

        if "Revues scientifiques" in categories:
            score += 3
            raisons.append(
                "Présence d’une revue systématique ou d’une méta-analyse."
            )

        if "Maladies infectieuses" in categories:
            if any(
                mot in texte
                for mot in [
                    "outbreak",
                    "epidemic",
                    "pandemic",
                    "emerging",
                    "cluster",
                ]
            ):
                score += 4
                raisons.append(
                    "Signal infectieux émergent ou événement épidémique détecté."
                )

        if "Vaccination" in categories:
            if any(
                mot in texte
                for mot in [
                    "phase iii",
                    "approved",
                    "authorization",
                    "authorisation",
                    "new recommendation",
                ]
            ):
                score += 3
                raisons.append(
                    "Évolution importante concernant un vaccin."
                )

        if "Traitements" in categories:
            if any(
                mot in texte
                for mot in [
                    "phase iii",
                    "approved",
                    "authorization",
                    "authorisation",
                    "breakthrough",
                ]
            ):
                score += 3
                raisons.append(
                    "Évolution importante concernant un traitement."
                )

        if niveau_preuve >= 4:
            score += 2
            raisons.append(
                "Niveau de preuve élevé."
            )
        elif niveau_preuve == 3:
            score += 1
            raisons.append(
                "Niveau de preuve intermédiaire."
            )

        score_existant = article.get("score", 0)

        try:
            score += min(int(score_existant), 5)
        except (TypeError, ValueError):
            pass

        if score >= 10:
            return 10, "Priorité élevée", raisons

        if score >= 7:
            return score, "Important", raisons

        if score >= 4:
            return score, "À surveiller", raisons

        if score >= 1:
            return score, "Information utile", raisons

        return 0, "Veille documentaire", raisons

    def _normaliser(self, texte):
        texte = unicodedata.normalize(
            "NFKD",
            str(texte).lower(),
        )

        texte = "".join(
            caractere
            for caractere in texte
            if not unicodedata.combining(caractere)
        )

        texte = re.sub(
            r"[^a-z0-9]+",
            " ",
            texte,
        )

        return " ".join(texte.split())

    def _contient_expression(self, texte, expression):
        if not expression:
            return False

        motif = rf"\b{re.escape(expression)}\b"

        return re.search(motif, texte) is not None


classificateur_one_health = ClassificateurOneHealth()


def classifier_article(article):
    """
    Fonction pratique utilisée par le reste du moteur.
    """
    return classificateur_one_health.classifier(article)
