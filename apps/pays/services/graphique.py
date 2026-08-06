import csv

from . import definition_note
from . import sources


PENALITE_DONNEE_MANQUANTE = 5

ANNEES_GRAPHIQUE = (
    2000,
    2010,
    2020,
    2026,
)


INDICATEURS_SANTE_HUMAINE = {
    "esperance_vie": definition_note.noter_esperance_vie,
    "medecins": definition_note.noter_medecins,
    "uhc": definition_note.noter_uhc,
    "vaccination_dtp3": (
        definition_note.noter_vaccination_dtp3
    ),
    "sante_mentale": definition_note.noter_sante_mentale,
}


INDICATEURS_SANTE_ANIMALE = {
    "services_veterinaires": (
        definition_note.noter_services_veterinaires
    ),
    "maladies_animales": (
        definition_note.noter_maladies_animales
    ),
    "vaccination_animale": (
        definition_note.noter_vaccination_animale
    ),
    "bien_etre_animal": (
        definition_note.noter_bien_etre_animal
    ),
    "faune_sauvage": definition_note.noter_faune_sauvage,
}


INDICATEURS_ECOSYSTEME = {
    "qualite_air": definition_note.noter_qualite_air,
    "qualite_eau": definition_note.noter_qualite_eau,
    "biodiversite": definition_note.noter_biodiversite,

    # Dans les CSV, la colonne s'appelle couverture_forestiere.
    # Dans le calcul SPT, cet indicateur est noté comme déforestation.
    "couverture_forestiere": (
        definition_note.noter_deforestation
    ),

    "traitement_eaux_usees": (
        definition_note.noter_traitement_eaux_usees
    ),
}


INDICATEURS_INFORMATION_PREVENTION = {
    "liberte_presse": definition_note.noter_liberte_presse,
    "surveillance_epidemiologique": (
        definition_note.noter_surveillance_epidemiologique
    ),
    "partage_donnees": (
        definition_note.noter_partage_donnees
    ),
    "preparation_pandemies": (
        definition_note.noter_preparation_pandemies
    ),
    "gestion_crises": definition_note.noter_gestion_crises,
}


def convertir_nombre(valeur):
    """
    Convertit une cellule CSV en nombre flottant.

    Retourne None lorsque la cellule est vide ou invalide.
    """
    if valeur in (None, ""):
        return None

    try:
        return float(valeur)
    except (TypeError, ValueError):
        return None


def lire_ligne_csv(chemin_fichier, code_iso3, annee):
    """
    Lit la ligne exacte d'un pays et d'une année.

    Retourne un dictionnaire vide si aucune ligne n'existe.
    """
    if not chemin_fichier.exists():
        return {}

    try:
        with chemin_fichier.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as fichier:
            lecteur = csv.DictReader(fichier)

            for ligne in lecteur:
                iso3 = str(
                    ligne.get("iso3", "")
                ).strip().upper()

                try:
                    annee_ligne = int(
                        ligne.get("year", "")
                    )
                except (TypeError, ValueError):
                    continue

                if iso3 == code_iso3 and annee_ligne == annee:
                    return ligne

    except (OSError, csv.Error):
        return {}

    return {}


def fusionner_lignes(ligne_principale, ligne_secours):
    """
    Fusionne deux lignes.

    Priorité :
    1. valeur de indicateurs.csv ;
    2. valeur de nouvelles_sources.csv ;
    3. cellule vide.
    """
    colonnes = set(ligne_principale) | set(ligne_secours)
    resultat = {}

    for colonne in colonnes:
        valeur_principale = ligne_principale.get(
            colonne,
            "",
        )

        if valeur_principale not in (None, ""):
            resultat[colonne] = valeur_principale
        else:
            resultat[colonne] = ligne_secours.get(
                colonne,
                "",
            )

    return resultat


def recuperer_valeurs_annee(code_iso3, annee):
    """
    Récupère les valeurs historiques d'une année.

    indicateurs.csv est prioritaire.
    nouvelles_sources.csv sert de secours.
    """
    ligne_indicateurs = lire_ligne_csv(
        sources.FICHIER_INDICATEURS,
        code_iso3,
        annee,
    )

    ligne_nouvelles_sources = lire_ligne_csv(
        sources.FICHIER_NOUVELLES_SOURCES,
        code_iso3,
        annee,
    )

    return fusionner_lignes(
        ligne_indicateurs,
        ligne_nouvelles_sources,
    )


def calculer_note_indicateur(valeur, fonction_notation):
    """
    Calcule une note entière de 0 à 20.

    Une donnée absente reçoit la pénalité de 5.
    """
    valeur = convertir_nombre(valeur)
    note = fonction_notation(valeur)

    if note is None:
        return PENALITE_DONNEE_MANQUANTE

    return max(0, min(20, int(round(note))))


def calculer_note_pilier(valeurs, indicateurs):
    """
    Calcule la moyenne entière d'un pilier sur ses 5 indicateurs.
    """
    notes = [
        calculer_note_indicateur(
            valeurs.get(colonne),
            fonction_notation,
        )
        for colonne, fonction_notation in indicateurs.items()
    ]

    if not notes:
        return PENALITE_DONNEE_MANQUANTE

    return int(round(sum(notes) / len(notes)))


def calculer_graphique_pays(code_pays):
    """
    Prépare les données des quatre courbes historiques.

    code_pays doit être un code ISO alpha-2 :
    fr, de, ru, dz, etc.

    Retourne :
    {
        "annees": [2000, 2010, 2020, 2026],
        "sante_humaine": [...],
        "sante_animale": [...],
        "ecosysteme": [...],
        "information_prevention": [...],
    }
    """
    if not isinstance(code_pays, str):
        return None

    code_pays = code_pays.strip().lower()

    if not code_pays:
        return None

    code_iso3 = sources.convertir_code_iso2_vers_iso3(
        code_pays
    )

    if code_iso3 is None:
        return None

    graphique = {
        "annees": list(ANNEES_GRAPHIQUE),
        "sante_humaine": [],
        "sante_animale": [],
        "ecosysteme": [],
        "information_prevention": [],
    }

    for annee in ANNEES_GRAPHIQUE:
        valeurs = recuperer_valeurs_annee(
            code_iso3,
            annee,
        )

        graphique["sante_humaine"].append(
            calculer_note_pilier(
                valeurs,
                INDICATEURS_SANTE_HUMAINE,
            )
        )

        graphique["sante_animale"].append(
            calculer_note_pilier(
                valeurs,
                INDICATEURS_SANTE_ANIMALE,
            )
        )

        graphique["ecosysteme"].append(
            calculer_note_pilier(
                valeurs,
                INDICATEURS_ECOSYSTEME,
            )
        )

        graphique["information_prevention"].append(
            calculer_note_pilier(
                valeurs,
                INDICATEURS_INFORMATION_PREVENTION,
            )
        )

    return graphique