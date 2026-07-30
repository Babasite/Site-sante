"""Classification déterministe d'articles biomédicaux et One Health.

Version 17 : analyse déterministe de la stratégie statistique (ITT, mITT,
per-protocol et as-treated), des critères composites, des analyses ajustées et
de sensibilité, de l’attrition et des contradictions statistiques explicites.

L'interface publique reste compatible avec la version historique :
    classifier_article(article) -> dict
"""

from __future__ import annotations

import html
import re
import unicodedata
from collections.abc import Iterable, Mapping
from functools import lru_cache
from typing import Any

# ---------------------------------------------------------------------------
# V17 — Qualité méthodologique avancée
# ---------------------------------------------------------------------------

REGLES_QUALITE_METHODOLOGIQUE_V17 = {
    "Randomisation avancée": (
        "allocation concealment",
        "concealed allocation",
        "central randomization",
        "centralised randomization",
        "centralized randomization",
        "computer generated randomization",
        "computer generated sequence",
        "block randomization",
        "permuted block",
        "stratified randomization",
        "web based randomization",
        "interactive web response system",
        "interactive voice response system",
        "iwrs",
        "ivrs",
    ),
    "Double aveugle": (
        "double blind",
        "double blinded",
        "double masked",
        "double aveugle",
    ),
    "Triple aveugle": (
        "triple blind",
        "triple blinded",
        "triple masked",
        "triple aveugle",
    ),
    "Évaluateur aveugle": (
        "outcome assessor blinded",
        "assessor blinded",
        "blinded outcome assessment",
        "blinded endpoint assessment",
        "evaluateur aveugle",
        "evaluation en aveugle",
    ),
    "Étude ouverte": (
        "open label",
        "open labelled",
        "open label trial",
        "essai ouvert",
        "etude ouverte",
    ),
    "Comité indépendant": (
        "dsmb",
        "data safety monitoring board",
        "data monitoring committee",
        "independent data monitoring committee",
        "idmc",
        "independent safety committee",
        "endpoint adjudication committee",
        "clinical event committee",
        "independent event adjudication",
    ),
    "Conformité GCP": (
        "ich gcp",
        "good clinical practice",
        "good clinical practices",
        "independent monitoring",
        "external monitoring",
        "independent audit",
        "audited according to gcp",
        "bonnes pratiques cliniques",
    ),
}

TERMES_CRITERES_SUBJECTIFS = (
    "quality of life",
    "pain score",
    "symptom score",
    "patient reported outcome",
    "patient reported outcomes",
    "self reported",
    "questionnaire",
    "qualite de vie",
    "score de douleur",
    "score symptomatique",
    "critere rapporte par le patient",
    "auto rapporte",
)

# ---------------------------------------------------------------------------
# Règles thématiques
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Entités biomédicales contextuelles
# ---------------------------------------------------------------------------

REGLES_ENTITES_INFECTIEUSES = {
    "Virus respiratoires": (
        "sars cov 2", "covid 19", "influenza a", "influenza b",
        "avian influenza", "swine influenza",
        "respiratory syncytial virus", "human metapneumovirus",
        "virus respiratoire syncytial", "grippe aviaire", "grippe porcine",
    ),
    "Virus émergents et zoonotiques": (
        "mpox virus", "monkeypox virus", "ebola virus", "marburg virus",
        "lassa virus", "nipah virus", "hendra virus",
        "crimean congo hemorrhagic fever", "west nile virus",
        "chikungunya virus", "dengue virus", "zika virus",
        "virus ebola", "virus marburg", "virus nipah",
        "virus du nil occidental",
    ),
    "Bactéries prioritaires": (
        "mycobacterium tuberculosis", "staphylococcus aureus",
        "streptococcus pneumoniae", "klebsiella pneumoniae",
        "escherichia coli", "pseudomonas aeruginosa",
        "acinetobacter baumannii", "neisseria meningitidis",
        "neisseria gonorrhoeae", "clostridioides difficile",
        "salmonella enterica", "listeria monocytogenes",
        "vibrio cholerae", "legionella pneumophila",
    ),
    "Parasites et champignons": (
        "plasmodium falciparum", "plasmodium vivax", "leishmania",
        "trypanosoma cruzi", "candida auris", "aspergillus fumigatus",
        "cryptococcus neoformans", "pneumocystis jirovecii",
        "paludisme", "leishmaniose", "maladie de chagas",
    ),
    "Maladies infectieuses nommées": (
        "tuberculosis", "tuberculose", "measles", "rougeole",
        "cholera", "meningococcal disease", "meningococcie",
        "pertussis", "coqueluche", "diphtheria", "diphterie",
        "rabies", "rage humaine", "hepatitis b", "hepatitis c",
        "hepatite b", "hepatite c", "hiv infection",
        "infection par le vih",
    ),
}

CONTEXTE_INFECTIEUX = (
    "infection", "infectious", "transmission", "outbreak", "epidemic",
    "pandemic", "surveillance", "incidence", "prevalence",
    "case fatality", "hospitalization", "mortality", "diagnosis",
    "vaccine", "treatment", "resistance", "infectieux", "epidemie",
    "pandemie", "letalite", "hospitalisation", "mortalite",
    "diagnostic", "vaccin", "traitement",
)

TERMES_INCERTITUDE = (
    "may", "might", "could", "suggests", "suggested", "possible",
    "potential", "hypothesis", "exploratory", "may be associated",
    "pourrait", "peut etre", "suggere", "potentiel", "hypothese",
    "exploratoire",
)

TERMES_CONFIRMATION = (
    "confirmed", "demonstrated", "significantly reduced",
    "significantly improved", "met the primary endpoint", "approved",
    "authorized", "validated", "confirme", "demontre",
    "reduction significative", "amelioration significative",
    "critere principal atteint", "approuve", "autorise", "valide",
)


# ---------------------------------------------------------------------------
# Interventions biomédicales : plateformes, classes et maturité
# ---------------------------------------------------------------------------

REGLES_INTERVENTIONS = {
    "Plateforme vaccinale ARNm": (
        "mrna vaccine", "messenger rna vaccine", "self amplifying rna vaccine",
        "sa rna vaccine", "vaccin a arn messager", "vaccin arn messager",
        "vaccin a arn auto amplifiant",
    ),
    "Vaccin à vecteur viral": (
        "viral vector vaccine", "adenoviral vector vaccine",
        "adenovirus vector vaccine", "vaccin a vecteur viral",
        "vaccin a vecteur adenoviral",
    ),
    "Vaccin protéique ou sous-unitaire": (
        "protein subunit vaccine", "recombinant protein vaccine",
        "virus like particle vaccine", "vlp vaccine",
        "vaccin proteique", "vaccin sous unitaire",
        "vaccin a proteine recombinante", "particule pseudo virale",
    ),
    "Vaccin vivant ou inactivé": (
        "live attenuated vaccine", "inactivated vaccine",
        "whole virus vaccine", "vaccin vivant attenue",
        "vaccin inactive", "vaccin entier",
    ),
    "Anticorps thérapeutique": (
        "monoclonal antibody", "neutralizing antibody",
        "bispecific antibody", "antibody drug conjugate",
        "anticorps monoclonal", "anticorps neutralisant",
        "anticorps bispecifique", "conjugue anticorps medicament",
    ),
    "Petite molécule": (
        "small molecule inhibitor", "small molecule drug",
        "oral antiviral", "protease inhibitor", "polymerase inhibitor",
        "inhibiteur de petite molecule", "petite molecule",
        "antiviral oral", "inhibiteur de protease",
        "inhibiteur de polymerase",
    ),
    "Thérapie cellulaire ou génique": (
        "gene therapy", "cell therapy", "car t cell",
        "crispr therapy", "gene editing therapy",
        "therapie genique", "therapie cellulaire",
        "cellules car t", "therapie crispr", "edition genetique",
    ),
    "Immunothérapie": (
        "immunotherapy", "immune checkpoint inhibitor",
        "checkpoint blockade", "cancer vaccine",
        "immunotherapie", "inhibiteur de point de controle",
        "blocage des points de controle", "vaccin therapeutique",
    ),
    "Antimicrobien": (
        "antibiotic treatment", "antiviral treatment",
        "antifungal treatment", "antiparasitic treatment",
        "bacteriophage therapy", "phage therapy",
        "traitement antibiotique", "traitement antiviral",
        "traitement antifongique", "traitement antiparasitaire",
        "phagotherapie",
    ),
}

REGLES_STADE_DEVELOPPEMENT = (
    (
        "Autorisation ou approbation",
        (
            "regulatory approval", "marketing authorization",
            "emergency use authorization", "approved by", "authorization granted",
            "autorisation de mise sur le marche", "autorisation d urgence",
            "approuve par", "autorisation accordee",
        ),
        5,
    ),
    (
        "Phase III",
        (
            "phase iii trial", "phase 3 trial", "phase iii study",
            "phase 3 study", "phase iii", "phase 3",
            "essai de phase iii", "etude de phase iii",
        ),
        4,
    ),
    (
        "Phase II",
        (
            "phase ii trial", "phase 2 trial", "phase ii study",
            "phase 2 study", "phase ii", "phase 2",
            "essai de phase ii", "etude de phase ii",
        ),
        3,
    ),
    (
        "Phase I",
        (
            "phase i trial", "phase 1 trial", "phase i study",
            "phase 1 study", "phase i", "phase 1",
            "first in human", "first in humans",
            "essai de phase i", "etude de phase i", "premiere administration humaine",
        ),
        2,
    ),
    (
        "Préclinique",
        (
            "preclinical study", "preclinical model", "animal model",
            "in vitro study", "in vivo study",
            "etude preclinique", "modele preclinique", "modele animal",
            "etude in vitro", "etude in vivo",
        ),
        1,
    ),
)

TERMES_RESULTAT_NEGATIF = (
    "failed to meet the primary endpoint", "did not meet the primary endpoint",
    "no significant difference", "not statistically significant",
    "lack of efficacy", "ineffective", "trial discontinued",
    "development discontinued", "futility analysis",
    "n a pas atteint le critere principal", "aucune difference significative",
    "non statistiquement significatif", "absence d efficacite",
    "inefficace", "essai interrompu", "developpement interrompu",
    "analyse de futilite",
)

TERMES_CRITERE_PRINCIPAL_NEGATIF = (
    "primary endpoint was not met", "primary endpoint not met",
    "failed to meet the primary endpoint", "did not meet the primary endpoint",
    "critere principal non atteint", "n a pas atteint le critere principal",
)

TERMES_CRITERE_PRINCIPAL_POSITIF = (
    "primary endpoint was met", "primary endpoint met",
    "met the primary endpoint", "critere principal atteint",
)

TERMES_RESULTAT_SECONDAIRE_POSITIF = (
    "secondary endpoint was met", "secondary endpoint met",
    "significant secondary endpoint", "positive secondary endpoint",
    "critere secondaire atteint", "resultat secondaire positif",
)

TERMES_EXPLORATOIRES = (
    "exploratory endpoint", "exploratory outcome", "hypothesis generating",
    "post hoc finding", "post hoc result", "critere exploratoire",
    "resultat exploratoire", "generateur d hypothese",
)

TERMES_NON_INFERIORITE = (
    "non inferiority", "non-inferiority", "noninferiority",
    "non inferior", "non-inferieur", "non inferiorite",
)

TERMES_EQUIVALENCE = (
    "equivalence trial", "equivalence study", "equivalent efficacy",
    "essai d equivalence", "etude d equivalence", "efficacite equivalente",
)

TERMES_MARGE_STATISTIQUE = (
    "non inferiority margin", "non-inferiority margin", "equivalence margin",
    "prespecified margin", "pre specified margin", "marge de non inferiorite",
    "marge d equivalence", "marge pre specifiee",
)


# ---------------------------------------------------------------------------
# V16 — Stratégie d'analyse et cohérence statistique
# ---------------------------------------------------------------------------

REGLES_STRATEGIE_ANALYSE = {
    "Intention de traiter": (
        "intention to treat", "intention-to-treat", "itt analysis",
        "intention de traiter", "analyse en intention de traiter",
    ),
    "Intention de traiter modifiée": (
        "modified intention to treat", "modified intention-to-treat",
        "mitt analysis", "m itt analysis", "intention de traiter modifiee",
    ),
    "Per protocole": (
        "per protocol analysis", "per-protocol analysis", "per protocol population",
        "per-protocol population", "analyse per protocole", "population per protocole",
    ),
    "Selon traitement reçu": (
        "as treated analysis", "as-treated analysis", "as treated population",
        "analyse selon le traitement recu", "analyse en fonction du traitement recu",
    ),
}

REGLES_ANALYSES_STATISTIQUES_V16 = {
    "Critère composite": (
        "composite endpoint", "composite outcome", "composite primary endpoint",
        "major adverse cardiovascular events", "major adverse cardiac events",
        "mace", "critere composite", "critere principal composite",
    ),
    "Analyse de sensibilité": (
        "sensitivity analysis", "sensitivity analyses", "robustness analysis",
        "robustness analyses", "analyse de sensibilite", "analyses de sensibilite",
        "analyse de robustesse", "analyses de robustesse",
    ),
    "Analyse ajustée": (
        "adjusted analysis", "adjusted model", "adjusted hazard ratio",
        "adjusted odds ratio", "adjusted risk ratio", "adjusted relative risk",
        "multivariable analysis", "multivariate analysis", "covariate adjusted",
        "analyse ajustee", "modele ajuste", "analyse multivariee",
        "analyse multivariable", "rapport de risque ajuste",
    ),
    "Attrition": (
        "loss to follow up", "lost to follow up", "loss to follow-up",
        "lost to follow-up", "attrition", "dropout rate", "drop out rate",
        "withdrawal rate", "missing outcome data", "perdus de vue",
        "perdu de vue", "taux d attrition", "donnees de resultat manquantes",
    ),
}

TERMES_SENSIBILITE_CONFIRMATOIRE = (
    "sensitivity analysis confirmed", "sensitivity analyses confirmed",
    "results were robust in sensitivity", "findings remained robust",
    "consistent across sensitivity analyses", "robustness analysis confirmed",
    "analyse de sensibilite a confirme", "analyses de sensibilite ont confirme",
    "resultats robustes dans les analyses de sensibilite",
)

TERMES_COMPOSITE_DISCORDANT = (
    "driven by", "mainly driven by", "primarily driven by",
    "individual components were not significant", "components were not significant",
    "no difference in individual components", "discordant components",
    "principalement porte par", "essentiellement porte par",
    "composantes individuelles non significatives", "composantes discordantes",
)

TERMES_CONCLUSION_POSITIVE_FORTE = (
    "significantly reduced", "significantly improved", "statistically significant benefit",
    "superior efficacy", "demonstrated efficacy", "clear benefit",
    "reduction significative", "amelioration significative",
    "benefice statistiquement significatif", "efficacite superieure",
    "efficacite demontree", "benefice clair",
)

TERMES_NON_SIGNIFICATIF_EXPLICITE = (
    "not statistically significant", "no statistically significant difference",
    "did not reach statistical significance", "non statistically significant",
    "non statistiquement significatif", "aucune difference statistiquement significative",
    "n a pas atteint la significativite statistique",
)

TERMES_IC_INCLUANT_VALEUR_NULLE = (
    "confidence interval includes one", "confidence interval included one",
    "confidence interval crossed one", "confidence interval crosses one",
    "confidence interval includes zero", "confidence interval included zero",
    "confidence interval crossed zero", "confidence interval crosses zero",
    "intervalle de confiance inclut 1", "intervalle de confiance incluait 1",
    "intervalle de confiance croise 1", "intervalle de confiance inclut zero",
    "intervalle de confiance incluait zero", "intervalle de confiance croise zero",
)

SEUIL_ATTRITION_MODEREE = 10.0
SEUIL_ATTRITION_ELEVEE = 20.0

TERMES_SECURITE_RASSURANTE = (
    "well tolerated", "acceptable safety profile", "no serious adverse events",
    "no new safety signal", "favorable safety profile",
    "bien tolere", "profil de securite acceptable",
    "aucun evenement indesirable grave", "aucun nouveau signal de securite",
    "profil de securite favorable",
)


# ---------------------------------------------------------------------------
# Intégrité scientifique et interprétation quantitative
# ---------------------------------------------------------------------------

REGLES_INTEGRITE_PUBLICATION = {
    "Article rétracté": (
        "retracted article", "article retracted", "retraction notice",
        "this article has been retracted", "publication retracted",
        "article retracte", "avis de retraction", "publication retractee",
        "cet article a ete retracte",
    ),
    "Expression de préoccupation": (
        "expression of concern", "editorial expression of concern",
        "notice of concern", "expression de preoccupation",
        "avis de preoccupation",
    ),
    "Correction publiée": (
        "corrigendum", "erratum", "correction notice",
        "published correction", "author correction",
        "correctif", "erratum publie", "avis de correction",
        "correction publiee",
    ),
    "Publication retirée": (
        "withdrawn article", "article withdrawn", "withdrawn preprint",
        "manuscript withdrawn", "article retire", "prepublication retiree",
        "manuscrit retire",
    ),
}

# Dans le corps ou le résumé, seules les formulations explicitement rattachées
# à la publication analysée déclenchent une sanction. Cela évite qu'une revue
# citant un « retracted article » soit elle-même considérée comme rétractée.
REGLES_INTEGRITE_CONTENU_EXPLICITE = {
    "Article rétracté": (
        "this article has been retracted", "this paper has been retracted",
        "the present article has been retracted", "publication retracted",
        "cet article a ete retracte", "le present article a ete retracte",
        "cette publication a ete retractee",
    ),
    "Expression de préoccupation": (
        "this article is subject to an expression of concern",
        "an expression of concern has been issued for this article",
        "cet article fait l objet d une expression de preoccupation",
        "une expression de preoccupation a ete emise pour cet article",
    ),
    "Correction publiée": (
        "this article has been corrected", "a correction to this article",
        "this paper has been corrected", "cet article a ete corrige",
        "une correction de cet article",
    ),
    "Publication retirée": (
        "this article has been withdrawn", "this manuscript has been withdrawn",
        "this preprint has been withdrawn", "cet article a ete retire",
        "ce manuscrit a ete retire", "cette prepublication a ete retiree",
    ),
}

CHAMPS_STATUT_EDITORIAL = (
    "publication_status", "publicationStatus", "article_status", "articleStatus",
    "editorial_status", "editorialStatus", "status", "notice_type",
    "noticeType", "publication_type", "publicationType",
)


REGLES_FORMAT_DOCUMENTAIRE = {
    "Résumé de congrès": (
        "conference abstract", "meeting abstract", "congress abstract",
        "poster abstract", "oral presentation abstract",
        "resume de congres", "communication affichee", "resume de conference",
    ),
    "Lettre ou correspondance": (
        "letter to the editor", "research letter", "correspondence",
        "lettre a l editeur", "lettre de recherche", "correspondance",
    ),
    "Actualité ou communiqué": (
        "news article", "press release", "news release", "media release",
        "article d actualite", "communique de presse", "communique officiel",
    ),
    "Notice éditoriale": (
        "editorial notice", "publisher note", "notice to readers",
        "note de l editeur", "avis aux lecteurs", "note editoriale",
    ),
    "Matériel supplémentaire": (
        "supplementary material", "supplemental appendix", "data supplement",
        "materiel supplementaire", "annexe supplementaire",
    ),
}

PLAFONDS_FORMAT_DOCUMENTAIRE = {
    "Résumé de congrès": 4,
    "Lettre ou correspondance": 4,
    "Actualité ou communiqué": 3,
    "Notice éditoriale": 2,
    "Matériel supplémentaire": 2,
}

SEUIL_CONTENU_INSUFFISANT = 24


REGLES_MATURITE_RESULTATS = {
    "Analyse finale": (
        "final analysis", "final results", "final follow up",
        "analyse finale", "resultats finaux", "suivi final",
    ),
    "Suivi à long terme": (
        "long term follow up", "long-term follow-up", "extended follow up",
        "suivi a long terme", "suivi prolonge",
    ),
    "Analyse intermédiaire": (
        "interim analysis", "interim results", "preliminary results",
        "analyse intermediaire", "resultats intermediaires",
        "resultats preliminaires",
    ),
}

SEUIL_GRAND_ECHANTILLON = 1000
SEUIL_PETIT_ECHANTILLON = 30
SEUIL_SUIVI_LONG_MOIS = 12
SEUIL_SUIVI_COURT_MOIS = 1

MARQUEURS_DONNEES_PROJETEES = (
    "planned", "target", "expected", "anticipated", "aim to enroll",
    "will enroll", "will recruit", "will be followed", "study design",
    "protocol", "sample size calculation", "projected",
    "prevu", "cible", "attendu", "devrait inclure", "inclura",
    "seront suivis", "sera suivi", "protocole", "calcul d effectif",
)


PLAFONDS_INTEGRITE = {
    "Article rétracté": 0,
    "Publication retirée": 1,
    "Expression de préoccupation": 2,
}


REGLES_RESULTATS_QUANTITATIFS = {
    "Intervalle de confiance": (
        "confidence interval", "95 ci", "95 confidence interval",
        "intervalle de confiance", "ic 95",
    ),
    "Mesure d'effet": (
        "hazard ratio", "odds ratio", "risk ratio", "relative risk",
        "absolute risk reduction", "number needed to treat",
        "rapport de risque", "rapport des cotes", "risque relatif",
        "reduction absolue du risque", "nombre de sujets a traiter",
    ),
    "Significativité statistique": (
        "statistically significant", "p value", "p-value",
        "statistical significance", "statistiquement significatif",
        "valeur p", "significativite statistique",
    ),
    "Pertinence clinique": (
        "clinically meaningful", "minimal clinically important difference",
        "clinically relevant", "benefice cliniquement pertinent",
        "difference minimale cliniquement importante",
        "cliniquement pertinent",
    ),
}

TERMES_RESULTAT_NON_CONCLUANT = (
    "confidence interval crossed one", "confidence interval includes one",
    "confidence interval crossed zero", "confidence interval includes zero",
    "underpowered study", "insufficient power", "wide confidence interval",
    "intervalle de confiance incluait 1", "intervalle de confiance inclut 1",
    "intervalle de confiance incluait zero", "intervalle de confiance inclut zero",
    "etude sous dimensionnee", "puissance insuffisante",
    "intervalle de confiance large",
)


# ---------------------------------------------------------------------------
# Qualité méthodologique et statut réel de la publication
# ---------------------------------------------------------------------------

REGLES_QUALITE_ETUDE = {
    "Multicentrique": (
        "multicenter study", "multicentre study", "multicenter trial",
        "multicentre trial", "etude multicentrique", "essai multicentrique",
    ),
    "Aveugle": (
        "double blind", "double blinded", "single blind", "single blinded",
        "masked trial", "double aveugle", "simple aveugle", "essai masque",
    ),
    "Contrôle actif ou placebo": (
        "placebo controlled", "active controlled", "active comparator",
        "placebo controle", "comparateur actif", "controle par placebo",
    ),
    "Prospectif": (
        "prospective study", "prospective cohort", "prospectively enrolled",
        "etude prospective", "cohorte prospective", "inclusion prospective",
    ),
    "Rétrospectif": (
        "retrospective study", "retrospective cohort", "retrospective analysis",
        "etude retrospective", "cohorte retrospective", "analyse retrospective",
    ),
    "Population importante": (
        "large cohort", "large population based", "nationwide cohort",
        "population based study", "large scale study",
        "grande cohorte", "etude nationale", "etude en population",
    ),
    "Validation externe": (
        "external validation", "independent validation cohort",
        "externally validated", "validation externe",
        "cohorte de validation independante",
    ),
}

TERMES_PROTOCOLE = (
    "study protocol", "trial protocol", "protocol paper",
    "registered protocol", "protocol for a systematic review",
    "protocole d etude", "protocole d essai",
    "article de protocole", "protocole enregistre",
)

TERMES_ANALYSE_SECONDAIRE = (
    "secondary analysis", "post hoc analysis", "subgroup analysis",
    "exploratory analysis", "secondary outcome analysis",
    "analyse secondaire", "analyse post hoc", "analyse de sous groupe",
    "analyse exploratoire",
)

TERMES_LIMITATIONS_MAJEURES = (
    "small sample size", "single center study", "single centre study",
    "high risk of bias", "substantial heterogeneity",
    "loss to follow up", "short follow up", "no control group",
    "faible taille d echantillon", "etude monocentrique",
    "risque eleve de biais", "heterogeneite importante",
    "perdus de vue", "suivi court", "absence de groupe controle",
)

TERMES_ENREGISTREMENT = (
    "clinicaltrials gov", "trial registration", "prospectively registered",
    "registered trial", "prospero registration",
    "essai enregistre", "enregistrement de l essai",
    "enregistre prospectivement", "enregistrement prospero",
)

# ---------------------------------------------------------------------------
# Portée sanitaire et dynamique des événements de santé publique
# ---------------------------------------------------------------------------

REGLES_PORTEE_SANITAIRE = {
    "Transmission accrue": (
        "increased transmission", "rising transmission", "rapid spread",
        "sustained transmission", "community transmission",
        "transmission en hausse", "augmentation de la transmission",
        "propagation rapide", "transmission soutenue",
        "transmission communautaire",
    ),
    "Extension géographique": (
        "geographic spread", "geographical expansion", "spread to new areas",
        "newly affected region", "cross border spread", "international spread",
        "extension geographique", "propagation geographique",
        "nouvelle region touchee", "propagation transfrontaliere",
        "propagation internationale",
    ),
    "Gravité accrue": (
        "increased severity", "severe disease", "higher mortality",
        "increased mortality", "high case fatality", "excess mortality",
        "gravite accrue", "forme severe", "mortalite accrue",
        "hausse de la mortalite", "letalite elevee", "surmortalite",
    ),
    "Pression hospitalière": (
        "hospital capacity", "hospital pressure", "healthcare capacity",
        "intensive care occupancy", "icu occupancy", "hospital admissions rising",
        "pression hospitaliere", "capacite hospitaliere",
        "occupation des soins intensifs", "hausse des hospitalisations",
        "tension sur le systeme de sante",
    ),
    "Population vulnérable": (
        "high risk population", "vulnerable population", "immunocompromised patients",
        "pregnant women", "older adults", "children under five",
        "population a risque", "population vulnerable",
        "patients immunodeprimes", "femmes enceintes",
        "personnes agees", "enfants de moins de cinq ans",
    ),
    "Mesure de contrôle sanitaire": (
        "public health response", "control measures", "containment measures",
        "emergency response", "vaccination campaign", "screening campaign",
        "reponse de sante publique", "mesures de controle",
        "mesures d endiguement", "reponse d urgence",
        "campagne de vaccination", "campagne de depistage",
    ),
    "Situation stable ou en amélioration": (
        "declining transmission", "decreasing incidence", "cases are decreasing",
        "outbreak under control", "no sustained transmission",
        "transmission en baisse", "incidence en diminution",
        "diminution des cas", "epidemie sous controle",
        "absence de transmission soutenue",
    ),
}


TERMES_NEGATION_SIGNAL = (
    "no", "not", "without", "absence of", "no evidence of",
    "no increase in", "no rise in", "did not show",
    "aucun", "aucune", "sans", "absence de", "pas de",
    "aucune preuve de", "pas d augmentation", "n a pas montre",
)


# Les marqueurs contrastifs limitent la portée d'une négation précédente.
# Exemple : « no increase in mortality, but sustained transmission » doit
# conserver le signal « sustained transmission ».
MARQUEURS_RUPTURE_NEGATION = (
    "but", "however", "although", "whereas", "yet", "nevertheless",
    "mais", "cependant", "toutefois", "alors que", "neanmoins",
)

# Expressions dans lesquelles « not » ne joue pas un rôle négatif classique.
EXCEPTIONS_NEGATION = (
    "not only",
    "non seulement",
)


REGLES_CATEGORIES = {
    "Vaccination": (
        "vaccine",
        "vaccination",
        "vaccinated",
        "booster dose",
        "immunization",
        "immunisation",
        "mrna vaccine",
        "messenger rna vaccine",
        "vaccine candidate",
        "vaccine efficacy",
        "vaccine effectiveness",
        "vaccin",
        "vaccination",
        "dose de rappel",
        "candidat vaccin",
        "efficacite vaccinale",
    ),
    "Traitements": (
        "treatment",
        "therapy",
        "therapeutic",
        "drug treatment",
        "medication",
        "antiviral",
        "antibiotic treatment",
        "antifungal treatment",
        "antiparasitic treatment",
        "immunotherapy",
        "gene therapy",
        "cell therapy",
        "monoclonal antibody",
        "small molecule inhibitor",
        "traitement",
        "therapie",
        "medicament",
        "antiviral",
        "antibiotherapie",
        "immunotherapie",
        "therapie genique",
        "anticorps monoclonal",
    ),
    "Maladies infectieuses": (
        "infectious disease",
        "infectious diseases",
        "human infection",
        "community acquired infection",
        "healthcare associated infection",
        "hospital acquired infection",
        "outbreak",
        "epidemic",
        "pandemic",
        "disease transmission",
        "pathogen transmission",
        "zoonosis",
        "zoonotic disease",
        "emerging pathogen",
        "reemerging pathogen",
        "maladie infectieuse",
        "maladies infectieuses",
        "infection humaine",
        "flambee epidemique",
        "epidemie",
        "pandemie",
        "transmission infectieuse",
        "zoonose",
        "agent pathogene emergent",
    ),
    "Recommandations": (
        "clinical guideline",
        "practice guideline",
        "public health guideline",
        "official recommendation",
        "updated recommendation",
        "consensus statement",
        "position statement",
        "official update",
        "public health advice",
        "guidance document",
        "recommandation officielle",
        "recommandations de pratique",
        "recommandation clinique",
        "mise a jour officielle",
        "avis de sante publique",
        "document d orientation",
    ),
    "Essais cliniques": (
        "clinical trial",
        "controlled trial",
        "randomized trial",
        "randomised trial",
        "randomized controlled trial",
        "randomised controlled trial",
        "placebo controlled",
        "double blind trial",
        "single blind trial",
        "phase 1 trial",
        "phase 2 trial",
        "phase 3 trial",
        "phase 4 trial",
        "phase 1",
        "phase 2",
        "phase 3",
        "phase 4",
        "phase i trial",
        "phase ii trial",
        "phase iii trial",
        "phase iv trial",
        "essai clinique",
        "essai controle",
        "essai randomise",
        "essai comparatif randomise",
        "controle par placebo",
        "essai en double aveugle",
        "essai de phase i",
        "essai de phase ii",
        "essai de phase iii",
        "essai de phase iv",
    ),
    "Revues scientifiques": (
        "systematic review",
        "meta analysis",
        "umbrella review",
        "scoping review",
        "rapid review",
        "living systematic review",
        "narrative review",
        "revue systematique",
        "meta analyse",
        "revue parapluie",
        "revue de portee",
        "revue rapide",
        "revue systematique vivante",
        "revue narrative",
    ),
    "IA médicale": (
        "artificial intelligence",
        "machine learning",
        "deep learning",
        "large language model",
        "foundation model",
        "neural network",
        "computer aided diagnosis",
        "clinical decision support algorithm",
        "intelligence artificielle",
        "apprentissage automatique",
        "apprentissage profond",
        "grand modele de langage",
        "modele de fondation",
        "reseau de neurones",
        "diagnostic assiste par ordinateur",
    ),
    "Santé environnementale": (
        "environmental health",
        "environmental exposure",
        "air pollution",
        "water pollution",
        "soil pollution",
        "climate change",
        "extreme heat",
        "heatwave",
        "wildfire smoke",
        "pesticide exposure",
        "pfas exposure",
        "microplastic exposure",
        "air quality",
        "drinking water quality",
        "sante environnementale",
        "exposition environnementale",
        "pollution de l air",
        "pollution de l eau",
        "pollution des sols",
        "changement climatique",
        "chaleur extreme",
        "vague de chaleur",
        "fumee d incendie",
        "exposition aux pesticides",
        "qualite de l air",
        "qualite de l eau potable",
    ),
    "Santé animale": (
        "veterinary medicine",
        "veterinary health",
        "animal health",
        "livestock health",
        "wildlife health",
        "poultry disease",
        "cattle disease",
        "swine disease",
        "equine disease",
        "companion animal disease",
        "avian influenza in birds",
        "veterinary surveillance",
        "medecine veterinaire",
        "sante veterinaire",
        "sante animale",
        "sante du betail",
        "sante de la faune sauvage",
        "maladie aviaire",
        "maladie porcine",
        "maladie bovine",
        "surveillance veterinaire",
    ),
    "Prévention": (
        "disease prevention",
        "preventive intervention",
        "screening program",
        "screening strategy",
        "infection prevention",
        "infection control",
        "public health measure",
        "risk reduction",
        "harm reduction",
        "contact tracing",
        "quarantine measure",
        "isolation measure",
        "prevention des maladies",
        "intervention preventive",
        "programme de depistage",
        "strategie de depistage",
        "prevention des infections",
        "controle des infections",
        "mesure de sante publique",
        "reduction des risques",
        "tracage des contacts",
    ),
    "Diagnostic": (
        "diagnostic test",
        "diagnostic accuracy",
        "diagnostic performance",
        "sensitivity and specificity",
        "point of care test",
        "rapid diagnostic test",
        "molecular diagnosis",
        "biomarker validation",
        "test diagnostique",
        "precision diagnostique",
        "performance diagnostique",
        "sensibilite et specificite",
        "test au point de soin",
        "test diagnostique rapide",
        "diagnostic moleculaire",
        "validation de biomarqueur",
    ),
    "Antibiorésistance": (
        "antimicrobial resistance",
        "antibiotic resistance",
        "multidrug resistant",
        "extensively drug resistant",
        "carbapenem resistant",
        "methicillin resistant",
        "antimicrobial stewardship",
        "resistance aux antimicrobiens",
        "resistance aux antibiotiques",
        "multiresistant",
        "resistant aux carbapenemes",
        "bon usage des antimicrobiens",
    ),
}


# Les termes One Health sont volontairement contextuels. Des mots isolés comme
# « air », « water », « animal » ou « clinical » provoquaient trop de faux positifs.
REGLES_ONE_HEALTH = {
    "Humain": (
        "human health",
        "human population",
        "human cases",
        "human infection",
        "patients",
        "hospitalized patients",
        "healthcare workers",
        "public health",
        "clinical outcomes",
        "sante humaine",
        "population humaine",
        "cas humains",
        "infection humaine",
        "patients hospitalises",
        "professionnels de sante",
        "sante publique",
        "resultats cliniques",
    ),
    "Animal": (
        "animal health",
        "animal population",
        "animal cases",
        "veterinary",
        "livestock",
        "wildlife",
        "poultry flock",
        "cattle herd",
        "swine herd",
        "companion animals",
        "animal reservoir",
        "sante animale",
        "population animale",
        "cas animaux",
        "veterinaire",
        "betail",
        "faune sauvage",
        "elevage de volailles",
        "troupeau bovin",
        "reservoir animal",
    ),
    "Environnement": (
        "environmental health",
        "environmental exposure",
        "environmental reservoir",
        "environmental surveillance",
        "wastewater surveillance",
        "drinking water",
        "surface water",
        "soil contamination",
        "air pollution",
        "water pollution",
        "climate change",
        "vector borne",
        "mosquito borne",
        "tick borne",
        "sante environnementale",
        "exposition environnementale",
        "reservoir environnemental",
        "surveillance environnementale",
        "surveillance des eaux usees",
        "eau potable",
        "eaux de surface",
        "contamination des sols",
        "pollution de l air",
        "pollution de l eau",
        "changement climatique",
        "transmis par les moustiques",
        "transmis par les tiques",
    ),
}


# Ordre non significatif : toutes les preuves sont recherchées et la meilleure
# est ensuite conservée. Le quatrième champ permet de départager deux preuves de
# même niveau.
REGLES_PREUVE = (
    (
        "Recommandation officielle fondée sur les preuves",
        (
            "evidence based guideline",
            "evidence based recommendation",
            "clinical practice guideline",
            "public health guideline",
            "recommandation fondee sur les preuves",
            "recommandation de pratique clinique",
        ),
        5,
        100,
    ),
    (
        "Revue parapluie",
        ("umbrella review", "overview of systematic reviews", "revue parapluie"),
        5,
        95,
    ),
    (
        "Méta-analyse",
        ("meta analysis", "meta analytic", "meta analyse"),
        5,
        90,
    ),
    (
        "Revue systématique",
        ("systematic review", "living systematic review", "revue systematique"),
        5,
        85,
    ),
    (
        "Essai clinique de phase III",
        (
            "phase iii trial", "phase 3 trial",
            "phase iii study", "phase 3 study",
            "essai de phase iii", "etude de phase iii",
        ),
        4,
        78,
    ),
    (
        "Essai clinique randomisé de phase III",
        (
            "phase iii randomized",
            "phase iii randomised",
            "randomized phase iii",
            "randomised phase iii",
            "essai randomise de phase iii",
        ),
        4,
        80,
    ),
    (
        "Essai clinique randomisé",
        (
            "randomized controlled trial",
            "randomised controlled trial",
            "randomized trial",
            "randomised trial",
            "cluster randomized trial",
            "cluster randomised trial",
            "essai controle randomise",
            "essai comparatif randomise",
            "essai randomise",
        ),
        4,
        75,
    ),
    (
        "Étude d'intervention non randomisée",
        (
            "non randomized trial",
            "non randomised trial",
            "quasi experimental study",
            "controlled before after study",
            "interrupted time series",
            "etude quasi experimentale",
            "essai non randomise",
        ),
        3,
        70,
    ),
    (
        "Étude de cohorte prospective",
        (
            "prospective cohort",
            "longitudinal cohort",
            "cohorte prospective",
            "cohorte longitudinale",
        ),
        3,
        65,
    ),
    (
        "Étude de cohorte rétrospective",
        ("retrospective cohort", "historical cohort", "cohorte retrospective"),
        3,
        62,
    ),
    (
        "Étude cas-témoins",
        ("case control study", "case control", "nested case control", "etude cas temoins"),
        3,
        60,
    ),
    (
        "Étude transversale",
        ("cross sectional study", "cross sectional survey", "etude transversale"),
        2,
        55,
    ),
    (
        "Étude écologique ou de surveillance",
        (
            "ecological study",
            "surveillance study",
            "population surveillance",
            "sentinel surveillance",
            "etude ecologique",
            "etude de surveillance",
            "surveillance sentinelle",
        ),
        2,
        50,
    ),
    (
        "Étude diagnostique",
        (
            "diagnostic accuracy study",
            "diagnostic validation study",
            "sensitivity and specificity",
            "etude de precision diagnostique",
            "etude de validation diagnostique",
        ),
        3,
        58,
    ),
    (
        "Étude de modélisation",
        (
            "modelling study",
            "modeling study",
            "mathematical model",
            "simulation study",
            "etude de modelisation",
            "modele mathematique",
        ),
        2,
        45,
    ),
    (
        "Étude qualitative",
        (
            "qualitative study",
            "focus group study",
            "semi structured interviews",
            "etude qualitative",
            "entretiens semi structures",
        ),
        2,
        40,
    ),
    (
        "Série ou rapport de cas",
        ("case series", "case report", "serie de cas", "rapport de cas"),
        1,
        35,
    ),
    (
        "Étude pilote ou preuve de concept",
        (
            "pilot study",
            "feasibility study",
            "proof of concept",
            "etude pilote",
            "etude de faisabilite",
            "preuve de concept",
        ),
        1,
        30,
    ),
    (
        "Prépublication ou résultats préliminaires",
        (
            "preprint",
            "not peer reviewed",
            "preliminary results",
            "interim analysis",
            "prepublication",
            "non evalue par les pairs",
            "resultats preliminaires",
            "analyse intermediaire",
        ),
        1,
        25,
    ),
    (
        "Revue de portée ou revue narrative",
        (
            "scoping review",
            "narrative review",
            "rapid review",
            "revue de portee",
            "revue narrative",
            "revue rapide",
        ),
        2,
        20,
    ),
    (
        "Avis d'experts ou commentaire",
        (
            "expert opinion",
            "editorial",
            "commentary",
            "perspective article",
            "avis d expert",
            "editorial",
            "commentaire",
        ),
        1,
        10,
    ),
)


SOURCES_OFFICIELLES = {
    "oms",
    "world health organization",
    "who",
    "has",
    "haute autorite de sante",
    "sante publique france",
    "anses",
    "ecdc",
    "european centre for disease prevention and control",
    "cdc",
    "centers for disease control and prevention",
    "ema",
    "european medicines agency",
    "fda",
    "food and drug administration",
    "inserm",
    "nih",
    "national institutes of health",
    "efsa",
    "european food safety authority",
    "woah",
    "world organisation for animal health",
}

SOURCES_SCIENTIFIQUES = {
    "pubmed",
    "medline",
    "cochrane",
    "cochrane library",
    "nature",
    "science",
    "the lancet",
    "lancet",
    "nejm",
    "new england journal of medicine",
    "jama",
    "bmj",
    "plos medicine",
    "eurosurveillance",
    "clinical infectious diseases",
    "emerging infectious diseases",
}




SIGNAUX_IMPORTANTS = {
    "Événement épidémique": (
        "outbreak",
        "epidemic",
        "pandemic",
        "disease cluster",
        "community transmission",
        "sustained transmission",
        "flambee epidemique",
        "epidemie",
        "pandemie",
        "foyer de cas",
        "transmission communautaire",
    ),
    "Émergence ou réémergence": (
        "emerging pathogen",
        "new pathogen",
        "novel pathogen",
        "reemerging disease",
        "first detected",
        "first reported case",
        "agent pathogene emergent",
        "nouvel agent pathogene",
        "maladie reemergente",
        "premier cas signale",
    ),
    "Décision réglementaire": (
        "approved by",
        "regulatory approval",
        "marketing authorization",
        "emergency use authorization",
        "authorization granted",
        "autorisation de mise sur le marche",
        "autorisation d urgence",
        "approuve par",
    ),
    "Résultat clinique majeur": (
        "primary endpoint met",
        "reduced mortality",
        "mortality reduction",
        "improved overall survival",
        "superior efficacy",
        "clinically meaningful benefit",
        "critere principal atteint",
        "reduction de la mortalite",
        "amelioration de la survie globale",
        "benefice cliniquement pertinent",
    ),
    "Signal de sécurité": (
        "safety signal",
        "serious adverse event",
        "unexpected adverse event",
        "drug withdrawal",
        "product recall",
        "signal de securite",
        "evenement indesirable grave",
        "retrait du medicament",
        "rappel de produit",
    ),
    "Résistance antimicrobienne": (
        "antimicrobial resistance",
        "antibiotic resistance",
        "multidrug resistant",
        "extensively drug resistant",
        "pan drug resistant",
        "resistance aux antimicrobiens",
        "resistance aux antibiotiques",
        "multiresistant",
    ),
}


class ClassificateurOneHealth:
    """Classificateur déterministe, explicable et sans dépendance externe."""

    def classifier(self, article: Mapping[str, Any] | None) -> dict[str, Any]:
        article = article if isinstance(article, Mapping) else {}
        titre = self._normaliser(
            self._extraire_champ(article, ("titre", "title", "headline"))
        )
        texte = self._construire_texte(article)
        texte_integrite = self._construire_texte_integrite(article)
        source = str(
            self._extraire_champ(article, ("source", "publisher", "journal"))
        ).strip()

        categories, mots_categories = self._detecter_regles(
            texte,
            REGLES_CATEGORIES,
        )
        entites_infectieuses, mots_entites = self._detecter_entites_infectieuses(
            texte
        )
        if entites_infectieuses and "Maladies infectieuses" not in categories:
            categories.append("Maladies infectieuses")

        one_health, mots_one_health = self._detecter_regles(
            texte,
            REGLES_ONE_HEALTH,
        )
        preuves = self._detecter_preuves(texte)
        preuve, niveau_preuve, raison_preuve = self._selectionner_preuve(preuves)
        signaux, mots_signaux = self._detecter_regles_contextuelles(
            texte,
            SIGNAUX_IMPORTANTS,
        )
        portee_sanitaire, mots_portee = self._detecter_regles_contextuelles(
            texte,
            REGLES_PORTEE_SANITAIRE,
        )
        interventions, mots_interventions = self._detecter_regles(
            texte,
            REGLES_INTERVENTIONS,
        )
        stade_developpement, niveau_stade, mots_stade = (
            self._detecter_stade_developpement(texte)
        )
        qualites_etude, mots_qualite = self._detecter_regles(
            texte,
            REGLES_QUALITE_ETUDE,
        )
        qualites_methodologiques_v17, mots_qualite_v17 = self._detecter_regles(
            texte,
            REGLES_QUALITE_METHODOLOGIQUE_V17,
        )
        statut_publication = self._detecter_statut_publication(texte)
        integrite_publication, mots_integrite = self._detecter_integrite_publication(
            article=article,
            titre=titre,
            texte=texte,
            texte_integrite=texte_integrite,
        )
        resultats_quantitatifs, mots_quantitatifs = self._detecter_regles(
            texte,
            REGLES_RESULTATS_QUANTITATIFS,
        )
        strategies_analyse, mots_strategies = self._detecter_regles(
            texte,
            REGLES_STRATEGIE_ANALYSE,
        )
        analyses_v16, mots_analyses_v16 = self._detecter_regles(
            texte,
            REGLES_ANALYSES_STATISTIQUES_V16,
        )
        taux_attrition, mot_attrition = self._extraire_taux_attrition(texte)
        formats_documentaires, mots_formats = self._detecter_regles(
            texte_integrite,
            REGLES_FORMAT_DOCUMENTAIRE,
        )
        contenu_insuffisant = len(texte.split()) < SEUIL_CONTENU_INSUFFISANT
        maturite_resultats, mots_maturite = self._detecter_regles(
            texte,
            REGLES_MATURITE_RESULTATS,
        )
        taille_echantillon, mot_echantillon = self._extraire_taille_echantillon(texte)
        suivi_mois, mot_suivi = self._extraire_duree_suivi_mois(texte)
        donnees_projetees = self._contient_un_des(texte, MARQUEURS_DONNEES_PROJETEES)

        preuve, niveau_preuve, raison_preuve = self._ajuster_preuve_integrite(
            preuve=preuve,
            niveau_preuve=niveau_preuve,
            raison_preuve=raison_preuve,
            integrite_publication=integrite_publication,
        )

        importance, niveau_importance, raisons_importance = self._calculer_importance(
            article=article,
            texte=texte,
            titre=titre,
            source=source,
            categories=categories,
            one_health=one_health,
            niveau_preuve=niveau_preuve,
            preuve=preuve,
            signaux=signaux,
            entites_infectieuses=entites_infectieuses,
            interventions=interventions,
            stade_developpement=stade_developpement,
            niveau_stade=niveau_stade,
            qualites_etude=qualites_etude,
            qualites_methodologiques_v17=qualites_methodologiques_v17,
            statut_publication=statut_publication,
            portee_sanitaire=portee_sanitaire,
            integrite_publication=integrite_publication,
            resultats_quantitatifs=resultats_quantitatifs,
            formats_documentaires=formats_documentaires,
            contenu_insuffisant=contenu_insuffisant,
            maturite_resultats=maturite_resultats,
            taille_echantillon=taille_echantillon,
            suivi_mois=suivi_mois,
            donnees_projetees=donnees_projetees,
            strategies_analyse=strategies_analyse,
            analyses_v16=analyses_v16,
            taux_attrition=taux_attrition,
        )

        raisons = self._dedupliquer(
            [raison_preuve, *raisons_importance]
        )
        mots_detectes = sorted(
            set(
                mots_categories
                + mots_one_health
                + mots_signaux
                + mots_entites
                + mots_interventions
                + mots_stade
                + mots_qualite
                + mots_qualite_v17
                + mots_portee
                + mots_integrite
                + mots_quantitatifs
                + mots_strategies
                + mots_analyses_v16
                + ([mot_attrition] if mot_attrition else [])
                + mots_formats
                + mots_maturite
                + ([mot_echantillon] if mot_echantillon else [])
                + ([mot_suivi] if mot_suivi else [])
            ),
            key=self._normaliser,
        )

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

    def _construire_texte(self, article: Mapping[str, Any]) -> str:
        """Construit le corpus scientifique sans y injecter le nom de la source.

        Les valeurs textuelles peuvent être des chaînes, des listes de paragraphes
        ou de petits objets imbriqués issus d'un flux RSS/API.
        """
        champs = (
            self._extraire_champ(article, ("titre", "title", "headline")),
            self._extraire_champ(
                article,
                ("resume", "résumé", "abstract", "summary", "description"),
            ),
            self._extraire_champ(
                article,
                ("contenu", "content", "texte", "body", "full_text", "fulltext"),
            ),
            self._extraire_champ(
                article,
                ("mots_cles", "mots-clés", "keywords", "tags", "mesh_terms"),
            ),
        )
        texte_brut = " ".join(self._aplatir_valeur(champ) for champ in champs)
        return self._normaliser(texte_brut)

    @classmethod
    def _extraire_champ(
        cls,
        article: Mapping[str, Any],
        noms: Iterable[str],
    ) -> Any:
        """Retourne la première valeur réellement exploitable."""
        for nom in noms:
            valeur = article.get(nom)
            if cls._aplatir_valeur(valeur).strip():
                return valeur
        return ""

    @classmethod
    def _aplatir_valeur(cls, valeur: Any) -> str:
        """Convertit proprement une valeur hétérogène en texte déterministe."""
        if valeur is None:
            return ""
        if isinstance(valeur, str):
            # Les résumés RSS contiennent fréquemment du HTML et des entités.
            sans_html = re.sub(r"<[^>]+>", " ", html.unescape(valeur))
            return " ".join(sans_html.split())
        if isinstance(valeur, Mapping):
            return " ".join(
                cls._aplatir_valeur(element)
                for element in valeur.values()
                if element is not None
            )
        if isinstance(valeur, Iterable) and not isinstance(
            valeur,
            (bytes, bytearray),
        ):
            return " ".join(cls._aplatir_valeur(element) for element in valeur)
        return str(valeur)

    def _construire_texte_integrite(self, article: Mapping[str, Any]) -> str:
        """Construit un corpus limité aux métadonnées éditoriales pertinentes."""
        valeurs = [
            self._extraire_champ(article, ("titre", "title", "headline")),
        ]
        for nom in CHAMPS_STATUT_EDITORIAL:
            if nom in article:
                valeurs.append(article.get(nom))
        return self._normaliser(
            " ".join(self._aplatir_valeur(valeur) for valeur in valeurs)
        )

    def _detecter_integrite_publication(
        self,
        article: Mapping[str, Any],
        titre: str,
        texte: str,
        texte_integrite: str,
    ) -> tuple[list[str], list[str]]:
        """Détecte le statut propre de l'article sans sanctionner les citations.

        Les libellés courts comme « retraction notice » ou « corrigendum » sont
        fiables dans le titre ou les champs de statut. Dans le résumé et le corps,
        seules les formulations explicitement auto-référentielles sont retenues.
        """
        del article  # conservé dans la signature pour faciliter les extensions futures

        statuts_meta, mots_meta = self._detecter_regles(
            texte_integrite,
            REGLES_INTEGRITE_PUBLICATION,
        )
        statuts_corps, mots_corps = self._detecter_regles(
            texte,
            REGLES_INTEGRITE_CONTENU_EXPLICITE,
        )

        # Le titre normalisé est déjà inclus dans texte_integrite, mais ce contrôle
        # explicite documente la priorité accordée aux notices éditoriales titrées.
        statuts_titre, mots_titre = self._detecter_regles(
            titre,
            REGLES_INTEGRITE_PUBLICATION,
        )

        return (
            self._dedupliquer([*statuts_titre, *statuts_meta, *statuts_corps]),
            self._dedupliquer([*mots_titre, *mots_meta, *mots_corps]),
        )

    @staticmethod
    def _contexte_projete(texte: str, debut: int, fin: int) -> bool:
        """Indique si une valeur numérique appartient à un objectif futur."""
        contexte = texte[max(0, debut - 80):min(len(texte), fin + 35)]
        return any(
            re.search(rf"\b{re.escape(marqueur)}\b", contexte)
            for marqueur in MARQUEURS_DONNEES_PROJETEES
        )

    @classmethod
    def _extraire_taille_echantillon(cls, texte: str) -> tuple[int | None, str]:
        """Extrait le plus grand effectif observé, en excluant les effectifs cibles."""
        motifs = (
            r"\bn\s*[=:]\s*(\d{1,7})\b",
            r"\b(\d{1,7})\s+(?:patients|participants|subjects|individuals)\b",
            r"\b(?:enrolled|included|randomized|randomised)\s+(\d{1,7})\b",
            r"\b(\d{1,7})\s+(?:patients|participants|sujets|personnes)\b",
            r"\b(?:inclus|randomises|randomisees)\s+(\d{1,7})\b",
        )
        valeurs: list[tuple[int, str]] = []
        for motif in motifs:
            for correspondance in re.finditer(motif, texte):
                if cls._contexte_projete(
                    texte, correspondance.start(), correspondance.end()
                ):
                    continue
                try:
                    valeur = int(correspondance.group(1))
                except (TypeError, ValueError):
                    continue
                if 2 <= valeur <= 10_000_000:
                    valeurs.append((valeur, correspondance.group(0)))
        if not valeurs:
            return None, ""
        return max(valeurs, key=lambda element: element[0])

    @classmethod
    def _extraire_duree_suivi_mois(cls, texte: str) -> tuple[float | None, str]:
        """Extrait le suivi réellement rapporté, sans retenir les durées prévues."""
        motif = (
            r"\b(?:median\s+|mean\s+)?(?:follow\s*up|followup|suivi)"
            r"(?:\s+(?:of|was|de|median|moyen))?\s*"
            r"(\d+(?:[.,]\d+)?)\s*"
            r"(days?|weeks?|months?|years?|jours?|semaines?|mois|ans?)\b"
        )
        durees: list[tuple[float, str]] = []
        facteurs = {
            "day": 1 / 30.4375, "days": 1 / 30.4375,
            "jour": 1 / 30.4375, "jours": 1 / 30.4375,
            "week": 7 / 30.4375, "weeks": 7 / 30.4375,
            "semaine": 7 / 30.4375, "semaines": 7 / 30.4375,
            "month": 1.0, "months": 1.0, "mois": 1.0,
            "year": 12.0, "years": 12.0, "an": 12.0, "ans": 12.0,
        }
        for correspondance in re.finditer(motif, texte):
            if cls._contexte_projete(
                texte, correspondance.start(), correspondance.end()
            ):
                continue
            try:
                valeur = float(correspondance.group(1).replace(",", "."))
            except (TypeError, ValueError):
                continue
            unite = correspondance.group(2)
            mois = valeur * facteurs.get(unite, 0)
            if 0 < mois <= 1200:
                durees.append((mois, correspondance.group(0)))
        if not durees:
            return None, ""
        return max(durees, key=lambda element: element[0])

    def _detecter_regles(
        self,
        texte: str,
        regles: Mapping[str, Iterable[str]],
    ) -> tuple[list[str], list[str]]:
        elements_detectes: list[str] = []
        mots_detectes: list[str] = []

        for nom, expressions in regles.items():
            correspondances = [
                expression
                for expression in expressions
                if self._contient_expression(
                    texte,
                    self._normaliser(expression),
                )
            ]
            if correspondances:
                elements_detectes.append(nom)
                mots_detectes.extend(correspondances)

        return elements_detectes, self._dedupliquer(mots_detectes)

    def _detecter_regles_contextuelles(
        self,
        texte: str,
        regles: Mapping[str, Iterable[str]],
    ) -> tuple[list[str], list[str]]:
        """Détecte les signaux en écartant les occurrences explicitement niées."""
        elements_detectes: list[str] = []
        mots_detectes: list[str] = []

        for nom, expressions in regles.items():
            correspondances = [
                expression
                for expression in expressions
                if self._contient_expression_non_negatee(
                    texte,
                    self._normaliser(expression),
                )
            ]
            if correspondances:
                elements_detectes.append(nom)
                mots_detectes.extend(correspondances)

        return elements_detectes, self._dedupliquer(mots_detectes)

    def _detecter_entites_infectieuses(
        self,
        texte: str,
    ) -> tuple[list[str], list[str]]:
        groupes, mots = self._detecter_regles(
            texte,
            REGLES_ENTITES_INFECTIEUSES,
        )
        if not groupes:
            return [], []

        if not self._contient_un_des(texte, CONTEXTE_INFECTIEUX):
            return [], []

        return groupes, mots

    def _detecter_stade_developpement(
        self,
        texte: str,
    ) -> tuple[str, int, list[str]]:
        detections: list[tuple[str, int, list[str]]] = []

        for nom, expressions, niveau in REGLES_STADE_DEVELOPPEMENT:
            correspondances = [
                expression
                for expression in expressions
                if self._contient_expression(
                    texte,
                    self._normaliser(expression),
                )
            ]
            if correspondances:
                detections.append((nom, niveau, correspondances))

        if not detections:
            return "Non déterminé", 0, []

        meilleur = max(detections, key=lambda element: element[1])
        return meilleur

    def _detecter_statut_publication(self, texte: str) -> str:
        if self._contient_un_des(texte, TERMES_PROTOCOLE):
            return "Protocole"
        if self._contient_un_des(texte, TERMES_ANALYSE_SECONDAIRE):
            return "Analyse secondaire"
        return "Résultats principaux ou statut non précisé"

    def _detecter_preuves(self, texte: str) -> list[dict[str, Any]]:
        preuves: list[dict[str, Any]] = []

        for nom, expressions, niveau, priorite in REGLES_PREUVE:
            correspondances = [
                expression
                for expression in expressions
                if self._contient_expression(
                    texte,
                    self._normaliser(expression),
                )
            ]
            if correspondances:
                preuves.append(
                    {
                        "nom": nom,
                        "niveau": niveau,
                        "priorite": priorite,
                        "correspondances": correspondances,
                    }
                )

        if self._contient_un_des(texte, TERMES_PROTOCOLE):
            for preuve in preuves:
                preuve["niveau"] = min(preuve["niveau"], 1)
                preuve["priorite"] = min(preuve["priorite"], 15)
                preuve["nom"] = f"Protocole — {preuve['nom']}"

        return sorted(
            preuves,
            key=lambda element: (element["niveau"], element["priorite"]),
            reverse=True,
        )

    def _selectionner_preuve(
        self,
        preuves: list[dict[str, Any]],
    ) -> tuple[str, int, str]:
        if not preuves:
            return (
                "Non déterminé",
                0,
                "Le niveau de preuve n’a pas pu être déterminé automatiquement.",
            )

        meilleure = preuves[0]
        autres = self._dedupliquer(
            preuve["nom"] for preuve in preuves[1:]
        )

        raison = f"Niveau de preuve détecté : {meilleure['nom']}."
        if autres:
            raison += " Autres types d’étude repérés : " + ", ".join(autres) + "."

        return meilleure["nom"], meilleure["niveau"], raison

    @staticmethod
    def _ajuster_preuve_integrite(
        preuve: str,
        niveau_preuve: int,
        raison_preuve: str,
        integrite_publication: list[str],
    ) -> tuple[str, int, str]:
        """Déclasse la preuve avant le calcul d'importance selon l'intégrité éditoriale."""
        if "Article rétracté" in integrite_publication:
            return (
                f"Publication rétractée — {preuve}",
                0,
                "Publication rétractée : niveau de preuve ramené à zéro.",
            )

        if "Publication retirée" in integrite_publication:
            return (
                f"Publication retirée — {preuve}",
                min(niveau_preuve, 1),
                "Publication retirée : niveau de preuve fortement déclassé.",
            )

        if "Expression de préoccupation" in integrite_publication:
            return (
                f"Sous préoccupation éditoriale — {preuve}",
                min(niveau_preuve, 2),
                raison_preuve
                + " Une expression de préoccupation limite la confiance accordée.",
            )

        return preuve, niveau_preuve, raison_preuve

    @staticmethod
    def _extraire_taux_attrition(texte: str) -> tuple[float | None, str]:
        """Extrait le taux d'attrition explicite le plus élevé (0 à 100 %)."""
        motifs = (
            r"\b(?:loss to follow up|lost to follow up|attrition|dropout rate|withdrawal rate)"
            r"(?:\s+(?:was|of|reached|atteignait|etait de))?\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*%?",
            r"\b(\d+(?:[.,]\d+)?)\s*%?\s+(?:were )?(?:lost to follow up|lost to follow up|dropouts?|withdrawals?)\b",
            r"\b(?:taux d attrition|perdus de vue)"
            r"(?:\s+(?:de|etait de|atteignait))?\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*%?",
        )
        valeurs: list[tuple[float, str]] = []
        for motif in motifs:
            for correspondance in re.finditer(motif, texte):
                try:
                    valeur = float(correspondance.group(1).replace(",", "."))
                except (TypeError, ValueError):
                    continue
                if 0.0 <= valeur <= 100.0:
                    valeurs.append((valeur, correspondance.group(0)))
        if not valeurs:
            return None, ""
        return max(valeurs, key=lambda element: element[0])

    def _calculer_importance(
        self,
        article: Mapping[str, Any],
        texte: str,
        titre: str,
        source: str,
        categories: list[str],
        one_health: list[str],
        niveau_preuve: int,
        preuve: str,
        signaux: list[str],
        entites_infectieuses: list[str],
        interventions: list[str],
        stade_developpement: str,
        niveau_stade: int,
        qualites_etude: list[str],
        qualites_methodologiques_v17: list[str],
        statut_publication: str,
        portee_sanitaire: list[str],
        integrite_publication: list[str],
        resultats_quantitatifs: list[str],
        formats_documentaires: list[str],
        contenu_insuffisant: bool,
        maturite_resultats: list[str],
        taille_echantillon: int | None,
        suivi_mois: float | None,
        donnees_projetees: bool,
        strategies_analyse: list[str],
        analyses_v16: list[str],
        taux_attrition: float | None,
    ) -> tuple[int, str, list[str]]:
        score = 0
        raisons: list[str] = []

        source_officielle = self._source_officielle(source)
        source_scientifique = self._source_scientifique(source)
        if source_officielle:
            score += 2
            raisons.append(f"Source officielle détectée : {source}.")
        elif source_scientifique:
            score += 1
            raisons.append(f"Source scientifique reconnue détectée : {source}.")

        if integrite_publication:
            raisons.append(
                "Statut d’intégrité éditoriale détecté : "
                + ", ".join(integrite_publication)
                + "."
            )
            if "Article rétracté" in integrite_publication:
                raisons.append(
                    "Publication rétractée : exclusion de toute priorité scientifique."
                )
            elif "Publication retirée" in integrite_publication:
                raisons.append(
                    "Publication retirée : fiabilité fortement réduite."
                )
            elif "Expression de préoccupation" in integrite_publication:
                raisons.append(
                    "Expression de préoccupation éditoriale : prudence renforcée."
                )
            elif "Correction publiée" in integrite_publication:
                raisons.append(
                    "Correction éditoriale repérée : vérifier la version corrigée."
                )

        # Le niveau de preuve structure le score, mais ne suffit pas à lui seul
        # pour transformer une publication en priorité élevée.
        bonus_preuve = {0: 0, 1: 0, 2: 1, 3: 2, 4: 3, 5: 3}[niveau_preuve]
        score += bonus_preuve
        if niveau_preuve >= 4:
            raisons.append("Niveau de preuve élevé.")
        elif niveau_preuve == 3:
            raisons.append("Niveau de preuve intermédiaire.")

        if "Recommandations" in categories:
            score += 2
            raisons.append("Recommandation ou mise à jour de pratique détectée.")

        if "Essais cliniques" in categories:
            score += 1
            raisons.append("Étude interventionnelle ou essai clinique détecté.")

        if preuve in {"Méta-analyse", "Revue systématique", "Revue parapluie"}:
            score += 1
            raisons.append("Synthèse structurée de la littérature détectée.")

        poids_signaux = {
            "Événement épidémique": 4,
            "Émergence ou réémergence": 3,
            "Décision réglementaire": 3,
            "Résultat clinique majeur": 3,
            "Signal de sécurité": 4,
            "Résistance antimicrobienne": 2,
        }
        situation_stable = "Situation stable ou en amélioration" in portee_sanitaire
        for signal in signaux:
            poids_signal = poids_signaux.get(signal, 0)
            if situation_stable and signal == "Événement épidémique":
                poids_signal = max(1, poids_signal - 2)
            score += poids_signal
            raisons.append(f"Signal important détecté : {signal.lower()}.")

        signaux_titre, _ = self._detecter_regles_contextuelles(
            titre,
            SIGNAUX_IMPORTANTS,
        )
        if signaux_titre and not situation_stable:
            score += 1
            raisons.append(
                "Signal sanitaire central présent dans le titre : "
                + ", ".join(signaux_titre)
                + "."
            )

        if portee_sanitaire:
            raisons.append(
                "Portée sanitaire détectée : "
                + ", ".join(portee_sanitaire)
                + "."
            )

            poids_portee = {
                "Transmission accrue": 2,
                "Extension géographique": 1,
                "Gravité accrue": 2,
                "Pression hospitalière": 2,
                "Population vulnérable": 1,
                "Mesure de contrôle sanitaire": 1,
                "Situation stable ou en amélioration": -1,
            }
            elements_actifs = [
                element
                for element in portee_sanitaire
                if element != "Situation stable ou en amélioration"
            ]
            situation_stable = "Situation stable ou en amélioration" in portee_sanitaire

            ajustement_portee = sum(
                poids_portee.get(element, 0)
                for element in elements_actifs
            )
            if situation_stable:
                # Une formulation d'amélioration modère les autres signaux sans
                # effacer une gravité ou une pression hospitalière explicitement rapportée.
                ajustement_portee -= 1

            ajustement_portee = max(-1, min(ajustement_portee, 3))
            score = max(0, score + ajustement_portee)

            if ajustement_portee > 0:
                raisons.append(
                    f"Impact sanitaire contextuel pris en compte : +{ajustement_portee}."
                )
            elif ajustement_portee < 0:
                raisons.append(
                    "Situation stable ou en amélioration : priorité légèrement réduite."
                )

        if len(one_health) >= 2:
            score += 1
            raisons.append(
                "Dimension One Health transversale détectée : "
                + ", ".join(one_health)
                + "."
            )

        if interventions:
            raisons.append(
                "Intervention biomédicale caractérisée : "
                + ", ".join(interventions)
                + "."
            )

        if stade_developpement != "Non déterminé":
            raisons.append(
                f"Stade de développement détecté : {stade_developpement}."
            )
            if (
                niveau_stade >= 4
                and ("Vaccination" in categories or "Traitements" in categories)
            ):
                score += 1

        if (
            "Vaccination" in categories
            and interventions
            and niveau_stade >= 3
        ):
            raisons.append(
                "Développement vaccinal clinique avancé ou réglementaire détecté."
            )

        if (
            "Traitements" in categories
            and interventions
            and niveau_stade >= 3
        ):
            raisons.append(
                "Développement thérapeutique clinique avancé ou réglementaire détecté."
            )

        if qualites_etude:
            raisons.append(
                "Marqueurs méthodologiques détectés : "
                + ", ".join(qualites_etude)
                + "."
            )

        bonus_qualite = 0
        if "Multicentrique" in qualites_etude:
            bonus_qualite += 1
        if "Validation externe" in qualites_etude:
            bonus_qualite += 1
        if (
            "Aveugle" in qualites_etude
            and "Contrôle actif ou placebo" in qualites_etude
            and niveau_preuve >= 4
        ):
            bonus_qualite += 1
        if bonus_qualite:
            bonus_qualite = min(bonus_qualite, 2)
            score += bonus_qualite
            raisons.append(
                f"Qualité méthodologique renforcée : +{bonus_qualite}."
            )
        # V17 : qualité méthodologique avancée.
        if qualites_methodologiques_v17:
            raisons.append(
                "Marqueurs méthodologiques avancés détectés : "
                + ", ".join(qualites_methodologiques_v17)
                + "."
            )

            bonus_v17 = 0

            if "Randomisation avancée" in qualites_methodologiques_v17:
                bonus_v17 += 1
                raisons.append(
                    "Méthode de randomisation ou dissimulation de l’allocation "
                    "explicitement rapportée."
                )

            if (
                "Double aveugle" in qualites_methodologiques_v17
                or "Triple aveugle" in qualites_methodologiques_v17
                or "Évaluateur aveugle" in qualites_methodologiques_v17
            ):
                bonus_v17 += 1
                raisons.append(
                    "Procédure d’aveugle explicite : risque de biais de mesure réduit."
                )

            if "Comité indépendant" in qualites_methodologiques_v17:
                bonus_v17 += 1
                raisons.append(
                    "Comité indépendant de surveillance ou d’adjudication détecté."
                )

            if "Conformité GCP" in qualites_methodologiques_v17:
                raisons.append(
                    "Conformité aux bonnes pratiques cliniques, monitoring ou audit détecté."
                )

            # Le bonus V17 reste plafonné pour ne pas dominer le niveau de preuve.
            bonus_v17 = min(bonus_v17, 2)

            if bonus_v17 and niveau_preuve >= 3:
                score += bonus_v17
                raisons.append(
                    f"Qualité méthodologique avancée prise en compte : +{bonus_v17}."
                )

            if "Étude ouverte" in qualites_methodologiques_v17:
                criteres_subjectifs = self._contient_un_des(
                    texte,
                    TERMES_CRITERES_SUBJECTIFS,
                )

                if criteres_subjectifs and niveau_preuve >= 3:
                    score = max(0, score - 1)
                    raisons.append(
                        "Étude ouverte avec critère potentiellement subjectif : "
                        "risque de biais accru."
                    )
                else:
                    raisons.append(
                        "Étude ouverte détectée, sans pénalité automatique en "
                        "l’absence de critère subjectif explicite."
                    )

        if self._contient_un_des(texte, TERMES_ENREGISTREMENT):
            raisons.append("Enregistrement prospectif ou registre d’étude détecté.")

        if statut_publication == "Protocole":
            score = max(0, score - 2)
            raisons.append(
                "Article de protocole détecté : absence de résultats définitifs."
            )
        elif statut_publication == "Analyse secondaire":
            score = max(0, score - 1)
            raisons.append(
                "Analyse secondaire, post hoc ou de sous-groupe détectée."
            )

        if self._contient_un_des(texte, TERMES_LIMITATIONS_MAJEURES):
            score = max(0, score - 1)
            raisons.append(
                "Limitation méthodologique importante explicitement rapportée."
            )

        if resultats_quantitatifs:
            raisons.append(
                "Éléments quantitatifs détectés : "
                + ", ".join(resultats_quantitatifs)
                + "."
            )
            if (
                "Intervalle de confiance" in resultats_quantitatifs
                and "Mesure d'effet" in resultats_quantitatifs
                and niveau_preuve >= 3
            ):
                score += 1
                raisons.append(
                    "Résultat accompagné d’une mesure d’effet et d’un intervalle de confiance."
                )
            if (
                "Pertinence clinique" in resultats_quantitatifs
                and "Significativité statistique" in resultats_quantitatifs
                and not self._contient_un_des(texte, TERMES_RESULTAT_NEGATIF)
            ):
                score += 1
                raisons.append(
                    "Significativité statistique et pertinence clinique conjointement rapportées."
                )

        # V16 : stratégie d'analyse, robustesse et cohérence statistique.
        if strategies_analyse:
            raisons.append(
                "Stratégie d’analyse détectée : " + ", ".join(strategies_analyse) + "."
            )
            itt_presente = "Intention de traiter" in strategies_analyse
            mitt_presente = "Intention de traiter modifiée" in strategies_analyse
            pp_presente = "Per protocole" in strategies_analyse
            as_treated_presente = "Selon traitement reçu" in strategies_analyse
            if itt_presente and niveau_preuve >= 3:
                score += 1
                raisons.append(
                    "Analyse en intention de traiter : robustesse méthodologique renforcée."
                )
            elif mitt_presente:
                raisons.append(
                    "Analyse en intention de traiter modifiée : population analysée potentiellement restreinte."
                )
            if (pp_presente or as_treated_presente) and not (itt_presente or mitt_presente):
                score = max(0, score - 1)
                raisons.append(
                    "Conclusion reposant uniquement sur une analyse per-protocole ou selon traitement reçu : confiance réduite."
                )

        if analyses_v16:
            raisons.append(
                "Caractéristiques statistiques V16 détectées : "
                + ", ".join(analyses_v16)
                + "."
            )

        if "Analyse ajustée" in analyses_v16 and niveau_preuve >= 2:
            score += 1
            raisons.append(
                "Analyse ajustée ou multivariable explicitement rapportée."
            )

        if "Analyse de sensibilité" in analyses_v16:
            if self._contient_un_des(texte, TERMES_SENSIBILITE_CONFIRMATOIRE):
                score += 1
                raisons.append(
                    "Analyses de sensibilité concordantes : robustesse du résultat renforcée."
                )
            else:
                raisons.append(
                    "Analyse de sensibilité mentionnée sans confirmation explicite du résultat."
                )

        if "Critère composite" in analyses_v16:
            if self._contient_un_des(texte, TERMES_COMPOSITE_DISCORDANT):
                score = max(0, score - 1)
                raisons.append(
                    "Critère composite porté par des composantes discordantes ou non significatives : interprétation prudente."
                )
            else:
                raisons.append(
                    "Critère composite détecté : vérifier la contribution de chaque composante."
                )

        if "Attrition" in analyses_v16:
            if taux_attrition is None:
                raisons.append(
                    "Attrition ou pertes de suivi rapportées sans taux exploitable."
                )
            elif taux_attrition >= SEUIL_ATTRITION_ELEVEE:
                score = max(0, score - 2)
                raisons.append(
                    f"Attrition élevée explicitement rapportée ({taux_attrition:.1f} %) : risque important de biais."
                )
            elif taux_attrition >= SEUIL_ATTRITION_MODEREE:
                score = max(0, score - 1)
                raisons.append(
                    f"Attrition modérée explicitement rapportée ({taux_attrition:.1f} %) : prudence méthodologique."
                )
            else:
                raisons.append(
                    f"Faible attrition explicitement rapportée ({taux_attrition:.1f} %)."
                )

        conclusion_positive_forte = self._contient_un_des(
            texte, TERMES_CONCLUSION_POSITIVE_FORTE
        )
        non_significatif_explicite = self._contient_un_des(
            texte, TERMES_NON_SIGNIFICATIF_EXPLICITE
        )
        ic_inclut_nul = self._contient_un_des(
            texte, TERMES_IC_INCLUANT_VALEUR_NULLE
        )
        if conclusion_positive_forte and (non_significatif_explicite or ic_inclut_nul):
            score = max(0, score - 2)
            score = min(score, 5)
            raisons.append(
                "Contradiction statistique explicite : conclusion positive forte malgré un résultat non significatif ou un intervalle incluant la valeur nulle."
            )

        if self._contient_un_des(texte, TERMES_RESULTAT_NON_CONCLUANT):
            score = max(0, score - 1)
            raisons.append(
                "Résultat quantitatif imprécis, sous-dimensionné ou non concluant détecté."
            )

        if self._contient_un_des(texte, TERMES_RESULTAT_NEGATIF):
            score = max(0, score - 2)
            raisons.append(
                "Résultat négatif, non concluant ou arrêt de développement détecté."
            )

        principal_negatif = self._contient_un_des(texte, TERMES_CRITERE_PRINCIPAL_NEGATIF)
        principal_positif = self._contient_un_des(texte, TERMES_CRITERE_PRINCIPAL_POSITIF)
        secondaire_positif = self._contient_un_des(texte, TERMES_RESULTAT_SECONDAIRE_POSITIF)
        exploratoire = self._contient_un_des(texte, TERMES_EXPLORATOIRES)

        if principal_negatif and secondaire_positif:
            score = max(0, score - 2)
            score = min(score, 4)
            raisons.append(
                "Critère principal négatif malgré un résultat secondaire positif : priorité plafonnée."
            )
        elif principal_negatif:
            score = min(score, 4)
            raisons.append(
                "Critère de jugement principal non atteint : conclusions positives fortement limitées."
            )
        elif principal_positif:
            raisons.append("Critère de jugement principal explicitement atteint.")

        if exploratoire:
            score = max(0, score - 1)
            raisons.append(
                "Résultat exploratoire ou post hoc : absence de bonus confirmatoire."
            )

        if self._contient_un_des(texte, TERMES_NON_INFERIORITE + TERMES_EQUIVALENCE):
            if self._contient_un_des(texte, TERMES_MARGE_STATISTIQUE):
                raisons.append(
                    "Cadre de non-infériorité ou d’équivalence avec marge explicitement rapportée."
                )
            else:
                score = max(0, score - 1)
                raisons.append(
                    "Non-infériorité ou équivalence mentionnée sans marge explicite : prudence renforcée."
                )
        elif self._contient_un_des(texte, TERMES_SECURITE_RASSURANTE):
            raisons.append(
                "Profil de tolérance favorable rapporté, sans bonus d’efficacité."
            )

        if entites_infectieuses:
            raisons.append(
                "Entité infectieuse contextualisée détectée : "
                + ", ".join(entites_infectieuses)
                + "."
            )
            if signaux or "Antibiorésistance" in categories:
                score += 1

        if (
            not self._contient_un_des(texte, TERMES_RESULTAT_NEGATIF)
            and self._contient_un_des(texte, TERMES_CONFIRMATION)
        ):
            score += 1
            raisons.append("Formulation de résultat confirmé ou validé détectée.")
        elif self._contient_un_des(texte, TERMES_INCERTITUDE):
            score = max(0, score - 1)
            raisons.append(
                "Formulation prudente ou exploratoire détectée : importance réduite."
            )

        if maturite_resultats:
            raisons.append(
                "Maturité des résultats détectée : "
                + ", ".join(maturite_resultats)
                + "."
            )
            if (
                "Analyse finale" in maturite_resultats
                and "Analyse intermédiaire" not in maturite_resultats
                and niveau_preuve >= 3
            ):
                score += 1
                raisons.append("Résultats finaux rapportés pour une étude structurée.")
            elif "Analyse intermédiaire" in maturite_resultats:
                score = max(0, score - 1)
                raisons.append(
                    "Analyse intermédiaire ou résultats préliminaires : prudence renforcée."
                )

        if donnees_projetees and taille_echantillon is None and suivi_mois is None:
            raisons.append(
                "Données quantitatives planifiées détectées : aucun bonus d’effectif "
                "ou de suivi n’est accordé sans résultats observés."
            )

        if taille_echantillon is not None:
            raisons.append(f"Taille d’échantillon explicitement détectée : n={taille_echantillon}.")
            if taille_echantillon >= SEUIL_GRAND_ECHANTILLON and niveau_preuve >= 2:
                score += 1
                raisons.append("Effectif important explicitement rapporté.")
            elif taille_echantillon < SEUIL_PETIT_ECHANTILLON and niveau_preuve >= 2:
                score = max(0, score - 1)
                raisons.append("Très petit effectif explicitement rapporté.")

        if suivi_mois is not None:
            raisons.append(
                f"Durée de suivi explicitement détectée : environ {suivi_mois:.1f} mois."
            )
            if suivi_mois >= SEUIL_SUIVI_LONG_MOIS and niveau_preuve >= 3:
                score += 1
                raisons.append("Suivi d’au moins douze mois explicitement rapporté.")
            elif (
                suivi_mois < SEUIL_SUIVI_COURT_MOIS
                and niveau_preuve >= 3
                and ("Traitements" in categories or "Vaccination" in categories)
            ):
                score = max(0, score - 1)
                raisons.append("Suivi très court pour une intervention clinique.")

        score_existant = self._convertir_score(article.get("score", 0))
        if score_existant:
            # Le score amont reste un signal secondaire pour éviter qu'il ne
            # domine la classification scientifique.
            bonus_amont = min(score_existant, 3)
            score += bonus_amont
            raisons.append(f"Signal de pertinence amont pris en compte : +{bonus_amont}.")

        plafonds = [
            PLAFONDS_INTEGRITE[statut]
            for statut in integrite_publication
            if statut in PLAFONDS_INTEGRITE
        ]
        if plafonds:
            plafond_integrite = min(plafonds)
            score = min(score, plafond_integrite)
            raisons.append(
                f"Plafond d’intégrité éditoriale appliqué en fin de calcul : {plafond_integrite}/10."
            )

        if formats_documentaires:
            raisons.append(
                "Format documentaire détecté : "
                + ", ".join(formats_documentaires)
                + "."
            )
            plafond_format = min(
                PLAFONDS_FORMAT_DOCUMENTAIRE.get(format_documentaire, 10)
                for format_documentaire in formats_documentaires
            )
            if score > plafond_format:
                score = plafond_format
                raisons.append(
                    f"Priorité plafonnée à {plafond_format}/10 selon le format documentaire."
                )

        if contenu_insuffisant:
            score = min(score, 2)
            raisons.append(
                "Contenu textuel insuffisant pour une classification scientifique robuste."
            )

        score = max(0, min(score, 10))

        if score >= 9:
            niveau = "Priorité élevée"
        elif score >= 7:
            niveau = "Important"
        elif score >= 4:
            niveau = "À surveiller"
        elif score >= 1:
            niveau = "Information utile"
        else:
            niveau = "Veille documentaire"

        return score, niveau, self._dedupliquer(raisons)

    def _source_officielle(self, source: str) -> bool:
        source_normalisee = self._normaliser(source)
        if not source_normalisee:
            return False

        return any(
            self._contient_expression(source_normalisee, nom)
            for nom in SOURCES_OFFICIELLES
        )

    def _source_scientifique(self, source: str) -> bool:
        source_normalisee = self._normaliser(source)
        if not source_normalisee:
            return False

        return any(
            self._contient_expression(source_normalisee, nom)
            for nom in SOURCES_SCIENTIFIQUES
        )

    def _contient_expression_non_negatee(
        self,
        texte: str,
        expression: str,
    ) -> bool:
        """Recherche une expression en limitant la portée des négations.

        La fenêtre est exprimée en mots plutôt qu'en caractères. Une conjonction
        contrastive réinitialise la portée, ce qui réduit les faux négatifs dans
        les résumés comportant plusieurs propositions.
        """
        if not texte or not expression:
            return False

        motif = self._compiler_expression(expression)
        for correspondance in motif.finditer(texte):
            contexte = texte[:correspondance.start()].split()
            contexte = contexte[-12:]

            # Une rupture contrastive annule les négations situées avant elle.
            derniere_rupture = -1
            contexte_joint = " ".join(contexte)
            for rupture in MARQUEURS_RUPTURE_NEGATION:
                rupture_normalisee = self._normaliser(rupture)
                position = contexte_joint.rfind(rupture_normalisee)
                if position > derniere_rupture:
                    derniere_rupture = position
            if derniere_rupture >= 0:
                contexte_joint = contexte_joint[derniere_rupture:].strip()

            if any(
                self._contient_expression(contexte_joint, self._normaliser(exception))
                for exception in EXCEPTIONS_NEGATION
            ):
                return True

            est_negatee = any(
                self._contient_expression(
                    contexte_joint,
                    self._normaliser(negation),
                )
                for negation in TERMES_NEGATION_SIGNAL
            )
            if not est_negatee:
                return True

        return False

    def _contient_un_des(self, texte: str, expressions: Iterable[str]) -> bool:
        return any(
            self._contient_expression(texte, self._normaliser(expression))
            for expression in expressions
        )

    @staticmethod
    def _convertir_score(valeur: Any) -> int:
        try:
            return max(0, int(float(valeur)))
        except (TypeError, ValueError, OverflowError):
            return 0

    @staticmethod
    def _dedupliquer(elements: Iterable[Any]) -> list[Any]:
        resultat: list[Any] = []
        deja_vus: set[Any] = set()

        for element in elements:
            if element is None or element == "":
                continue
            if element not in deja_vus:
                deja_vus.add(element)
                resultat.append(element)

        return resultat

    @classmethod
    def _normaliser(cls, texte: Any) -> str:
        # La conversion préalable en chaîne permet de mettre en cache les
        # normalisations sans imposer que la valeur d'origine soit hashable.
        return cls._normaliser_chaine(str(texte or ""))

    @staticmethod
    @lru_cache(maxsize=8192)
    def _normaliser_chaine(texte: str) -> str:
        texte_normalise = unicodedata.normalize("NFKD", texte.lower())
        texte_sans_accents = "".join(
            caractere
            for caractere in texte_normalise
            if not unicodedata.combining(caractere)
        )
        texte_alphanumerique = re.sub(
            r"[^a-z0-9]+",
            " ",
            texte_sans_accents,
        )
        return " ".join(texte_alphanumerique.split())

    @staticmethod
    @lru_cache(maxsize=8192)
    def _compiler_expression(expression: str) -> re.Pattern[str]:
        motif = rf"(?<![a-z0-9]){re.escape(expression)}(?![a-z0-9])"
        return re.compile(motif)

    @classmethod
    def _contient_expression(cls, texte: str, expression: str) -> bool:
        if not texte or not expression:
            return False
        return cls._compiler_expression(expression).search(texte) is not None


classificateur_one_health = ClassificateurOneHealth()


def classifier_article(article: Mapping[str, Any] | None) -> dict[str, Any]:
    """Fonction publique utilisée par le reste du moteur."""
    return classificateur_one_health.classifier(article)