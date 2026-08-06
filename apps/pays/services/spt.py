from . import definition_note
from . import sources


PENALITE_PAR_DONNEE_MANQUANTE = 0.25
PENALITE_MAXIMALE = 5.0


def appliquer_penalite(note):
    """
    Conserve la note telle quelle.

    Une donnée manquante reste None et n'est plus remplacée
    artificiellement par une note de 5/20.
    """
    return note


def calculer_moyenne(notes):
    """
    Calcule la moyenne uniquement avec les notes disponibles.

    Les valeurs None sont exclues du calcul.
    Si aucune note n'est disponible, retourne 0.0.
    """
    notes_valides = [
        note
        for note in notes
        if note is not None
    ]

    if not notes_valides:
        return 0.0

    return round(
        sum(notes_valides) / len(notes_valides),
        1,
    )


def calculer_penalite_donnees_manquantes(nombre_manquantes):
    """
    Calcule la pénalité globale liée aux données manquantes.

    - 0,25 point retiré par donnée manquante ;
    - pénalité plafonnée à 5 points.
    """
    try:
        nombre_manquantes = int(nombre_manquantes)
    except (TypeError, ValueError):
        return 0.0

    if nombre_manquantes <= 0:
        return 0.0

    return min(
        PENALITE_MAXIMALE,
        nombre_manquantes
        * PENALITE_PAR_DONNEE_MANQUANTE,
    )


def calculer_note_spt(code_pays):
    """
    Calcule les 20 indicateurs, les 4 piliers,
    la note SPT sur 80 et son affichage sur 20.

    Les données indisponibles sont exclues des moyennes.
    Une pénalité globale est ensuite appliquée selon leur nombre.

    code_pays doit être un code ISO alpha-2 :
    fr, de, br, us, etc.
    """
    if not isinstance(code_pays, str):
        return None

    code_pays = code_pays.strip().lower()

    if not code_pays:
        return None

    # =========================================================================
    # SANTÉ HUMAINE
    # =========================================================================

    valeur_esperance_vie = (
        sources.recuperer_esperance_vie(code_pays)
    )

    valeur_medecins = (
        sources.recuperer_medecins(code_pays)
    )

    valeur_uhc = (
        sources.recuperer_uhc(code_pays)
    )

    valeur_vaccination_dtp3 = (
        sources.recuperer_vaccination_dtp3(code_pays)
    )

    valeur_sante_mentale = (
        sources.recuperer_sante_mentale(code_pays)
    )

    notes_sante_humaine_brutes = {
        "esperance_vie": (
            definition_note.noter_esperance_vie(
                valeur_esperance_vie
            )
        ),
        "medecins": (
            definition_note.noter_medecins(
                valeur_medecins
            )
        ),
        "uhc": (
            definition_note.noter_uhc(
                valeur_uhc
            )
        ),
        "vaccination_dtp3": (
            definition_note.noter_vaccination_dtp3(
                valeur_vaccination_dtp3
            )
        ),
        "sante_mentale": (
            definition_note.noter_sante_mentale(
                valeur_sante_mentale
            )
        ),
    }

    notes_sante_humaine = {
        nom: appliquer_penalite(note)
        for nom, note in notes_sante_humaine_brutes.items()
    }

    note_humaine = calculer_moyenne(
        notes_sante_humaine_brutes.values()
    )

    # =========================================================================
    # SANTÉ ANIMALE
    # =========================================================================

    valeur_services_veterinaires = (
        sources.recuperer_services_veterinaires(
            code_pays
        )
    )

    valeur_maladies_animales = (
        sources.recuperer_maladies_animales(
            code_pays
        )
    )

    valeur_vaccination_animale = (
        sources.recuperer_vaccination_animale(
            code_pays
        )
    )

    valeur_bien_etre_animal = (
        sources.recuperer_bien_etre_animal(
            code_pays
        )
    )

    valeur_faune_sauvage = (
        sources.recuperer_faune_sauvage(
            code_pays
        )
    )

    notes_sante_animale_brutes = {
        "services_veterinaires": (
            definition_note.noter_services_veterinaires(
                valeur_services_veterinaires
            )
        ),
        "maladies_animales": (
            definition_note.noter_maladies_animales(
                valeur_maladies_animales
            )
        ),
        "vaccination_animale": (
            definition_note.noter_vaccination_animale(
                valeur_vaccination_animale
            )
        ),
        "bien_etre_animal": (
            definition_note.noter_bien_etre_animal(
                valeur_bien_etre_animal
            )
        ),
        "faune_sauvage": (
            definition_note.noter_faune_sauvage(
                valeur_faune_sauvage
            )
        ),
    }

    notes_sante_animale = {
        nom: appliquer_penalite(note)
        for nom, note in notes_sante_animale_brutes.items()
    }

    note_animale = calculer_moyenne(
        notes_sante_animale_brutes.values()
    )

    # =========================================================================
    # ÉCOSYSTÈME
    # =========================================================================

    valeur_qualite_air = (
        sources.recuperer_qualite_air(
            code_pays
        )
    )

    valeur_qualite_eau = (
        sources.recuperer_qualite_eau(
            code_pays
        )
    )

    valeur_biodiversite = (
        sources.recuperer_biodiversite(
            code_pays
        )
    )

    valeur_deforestation = (
        sources.recuperer_deforestation(
            code_pays
        )
    )

    valeur_traitement_eaux_usees = (
        sources.recuperer_traitement_eaux_usees(
            code_pays
        )
    )

    notes_ecosysteme_brutes = {
        "qualite_air": (
            definition_note.noter_qualite_air(
                valeur_qualite_air
            )
        ),
        "qualite_eau": (
            definition_note.noter_qualite_eau(
                valeur_qualite_eau
            )
        ),
        "biodiversite": (
            definition_note.noter_biodiversite(
                valeur_biodiversite
            )
        ),
        "deforestation": (
            definition_note.noter_deforestation(
                valeur_deforestation
            )
        ),
        "traitement_eaux_usees": (
            definition_note.noter_traitement_eaux_usees(
                valeur_traitement_eaux_usees
            )
        ),
    }

    notes_ecosysteme = {
        nom: appliquer_penalite(note)
        for nom, note in notes_ecosysteme_brutes.items()
    }

    note_ecosysteme = calculer_moyenne(
        notes_ecosysteme_brutes.values()
    )

    # =========================================================================
    # INFORMATION, PRÉVENTION ET SURVEILLANCE
    # =========================================================================

    valeur_liberte_presse = (
        sources.recuperer_liberte_presse(
            code_pays
        )
    )

    valeur_surveillance = (
        sources.recuperer_surveillance_epidemiologique(
            code_pays
        )
    )

    valeur_partage_donnees = (
        sources.recuperer_partage_donnees(
            code_pays
        )
    )

    valeur_preparation_pandemies = (
        sources.recuperer_preparation_pandemies(
            code_pays
        )
    )

    valeur_gestion_crises = (
        sources.recuperer_gestion_crises(
            code_pays
        )
    )

    notes_information_prevention_brutes = {
        "liberte_presse": (
            definition_note.noter_liberte_presse(
                valeur_liberte_presse
            )
        ),
        "surveillance_epidemiologique": (
            definition_note.noter_surveillance_epidemiologique(
                valeur_surveillance
            )
        ),
        "partage_donnees": (
            definition_note.noter_partage_donnees(
                valeur_partage_donnees
            )
        ),
        "preparation_pandemies": (
            definition_note.noter_preparation_pandemies(
                valeur_preparation_pandemies
            )
        ),
        "gestion_crises": (
            definition_note.noter_gestion_crises(
                valeur_gestion_crises
            )
        ),
    }

    notes_information_prevention = {
        nom: appliquer_penalite(note)
        for nom, note in (
            notes_information_prevention_brutes.items()
        )
    }

    note_information = calculer_moyenne(
        notes_information_prevention_brutes.values()
    )

    # =========================================================================
    # NOTE SPT
    # =========================================================================

    notes_piliers = [
        note_humaine,
        note_animale,
        note_ecosysteme,
        note_information,
    ]

    note_avant_penalite = round(
        sum(notes_piliers),
        2,
    )

    nombre_donnees_manquantes = sum(
        note is None
        for groupe in (
            notes_sante_humaine_brutes,
            notes_sante_animale_brutes,
            notes_ecosysteme_brutes,
            notes_information_prevention_brutes,
        )
        for note in groupe.values()
    )

    penalite_donnee_manquante = (
        calculer_penalite_donnees_manquantes(
            nombre_donnees_manquantes
        )
    )

    note_finale = round(
        max(
            0.0,
            note_avant_penalite
            - penalite_donnee_manquante,
        ),
        2,
    )

    note_spt_affichage = round(
        note_finale / 4,
        1,
    )

    return {
        "note_sante_humaine": note_humaine,
        "note_sante_animale": note_animale,
        "note_ecosysteme": note_ecosysteme,
        "note_information_prevention": note_information,
        "note_spt_affichage": note_spt_affichage,
        "note_spt": note_finale,
        "note_finale": note_finale,

        # Informations sur la pénalité
        "penalite_donnee_manquante": (
            penalite_donnee_manquante
        ),
        "penalite_par_donnee_manquante": (
            PENALITE_PAR_DONNEE_MANQUANTE
        ),
        "penalite_maximale": PENALITE_MAXIMALE,
        "note_avant_penalite": note_avant_penalite,
        "nombre_donnees_manquantes": (
            nombre_donnees_manquantes
        ),

        # Détail des notes utilisées dans le calcul.
        # Les valeurs absentes restent à None et sont exclues des moyennes.
        "indicateurs_sante_humaine": notes_sante_humaine,
        "indicateurs_sante_animale": notes_sante_animale,
        "indicateurs_ecosysteme": notes_ecosysteme,
        "indicateurs_information_prevention": (
            notes_information_prevention
        ),

        # Notes avant application de la pénalité,
        # utiles pour distinguer une donnée absente d'une vraie note.
        "indicateurs_bruts_sante_humaine": (
            notes_sante_humaine_brutes
        ),
        "indicateurs_bruts_sante_animale": (
            notes_sante_animale_brutes
        ),
        "indicateurs_bruts_ecosysteme": (
            notes_ecosysteme_brutes
        ),
        "indicateurs_bruts_information_prevention": (
            notes_information_prevention_brutes
        ),

        # Valeurs brutes utiles pour le débogage
        "valeurs_brutes": {
            "esperance_vie": valeur_esperance_vie,
            "medecins": valeur_medecins,
            "uhc": valeur_uhc,
            "vaccination_dtp3": valeur_vaccination_dtp3,
            "sante_mentale": valeur_sante_mentale,
            "services_veterinaires": (
                valeur_services_veterinaires
            ),
            "maladies_animales": valeur_maladies_animales,
            "vaccination_animale": valeur_vaccination_animale,
            "bien_etre_animal": valeur_bien_etre_animal,
            "faune_sauvage": valeur_faune_sauvage,
            "qualite_air": valeur_qualite_air,
            "qualite_eau": valeur_qualite_eau,
            "biodiversite": valeur_biodiversite,
            "deforestation": valeur_deforestation,
            "traitement_eaux_usees": (
                valeur_traitement_eaux_usees
            ),
            "liberte_presse": valeur_liberte_presse,
            "surveillance_epidemiologique": (
                valeur_surveillance
            ),
            "partage_donnees": valeur_partage_donnees,
            "preparation_pandemies": (
                valeur_preparation_pandemies
            ),
            "gestion_crises": valeur_gestion_crises,
        },
    }