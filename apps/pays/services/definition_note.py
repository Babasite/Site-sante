import math


NOTE_MIN = 0
NOTE_MAX = 20


def borner_note(note):
    """
    Limite une note entre 0 et 20
    et l'arrondit à l'entier le plus proche.
    """
    if note is None:
        return None

    return max(
        NOTE_MIN,
        min(NOTE_MAX, int(round(note))),
    )


def noter_lineaire(valeur, minimum, maximum):
    """
    Transforme une valeur comprise entre minimum et maximum
    en une note linéaire comprise entre 0 et 20.

    Toute valeur inférieure au minimum donne 0.
    Toute valeur supérieure au maximum donne 20.
    """
    if valeur is None:
        return None

    try:
        valeur = float(valeur)
    except (TypeError, ValueError):
        return None

    if maximum <= minimum:
        raise ValueError(
            "Le maximum doit être supérieur au minimum."
        )

    if valeur <= minimum:
        return 0

    if valeur >= maximum:
        return 20

    note = (
        (valeur - minimum)
        / (maximum - minimum)
        * 20
    )

    return borner_note(note)


def noter_lineaire_inverse(valeur, minimum, maximum):
    """
    Transforme une valeur en note inversée.

    Une valeur faible obtient une bonne note.
    Une valeur égale ou inférieure au minimum donne 20.
    Une valeur égale ou supérieure au maximum donne 0.
    """
    if valeur is None:
        return None

    note_directe = noter_lineaire(
        valeur,
        minimum,
        maximum,
    )

    if note_directe is None:
        return None

    return 20 - note_directe


def noter_par_paliers(
    valeur,
    largeur_palier,
    maximum=100,
):
    """
    Attribue une note de 0 à 20 par paliers réguliers.

    Exemple avec une largeur de 5 :
    0 à moins de 5 = 0
    5 à moins de 10 = 1
    ...
    100 = 20
    """
    if valeur is None:
        return None

    try:
        valeur = float(valeur)
    except (TypeError, ValueError):
        return None

    if largeur_palier <= 0:
        raise ValueError(
            "La largeur du palier doit être positive."
        )

    if valeur <= 0:
        return 0

    if valeur >= maximum:
        return 20

    note = math.floor(valeur / largeur_palier)

    return max(0, min(20, note))


def noter_par_paliers_inverse(
    valeur,
    largeur_palier,
    maximum,
):
    """
    Attribue une note inversée de 0 à 20 par paliers.

    Une valeur faible obtient une meilleure note.
    """
    if valeur is None:
        return None

    try:
        valeur = float(valeur)
    except (TypeError, ValueError):
        return None

    if largeur_palier <= 0:
        raise ValueError(
            "La largeur du palier doit être positive."
        )

    if valeur <= 0:
        return 20

    if valeur >= maximum:
        return 0

    diminution = math.floor(valeur / largeur_palier)

    return max(0, min(20, 20 - diminution))


# ============================================================================
# SANTÉ HUMAINE
# ============================================================================

def noter_esperance_vie(valeur):
    """
    60 ans ou moins : 0/20.
    85 ans ou plus : 20/20.
    Progression linéaire entre les deux.
    """
    return noter_lineaire(
        valeur,
        minimum=60,
        maximum=85,
    )


def noter_medecins(valeur):
    """
    Nombre de médecins pour 1 000 habitants.

    0 médecin : 0/20.
    5 médecins ou plus : 20/20.
    Un point par tranche de 0,25 médecin.
    """
    return noter_par_paliers(
        valeur,
        largeur_palier=0.25,
        maximum=5,
    )


def noter_uhc(valeur):
    """
    Indice UHC sur 100.

    Un point par tranche de 5 points.
    """
    return noter_par_paliers(
        valeur,
        largeur_palier=5,
        maximum=100,
    )


def noter_vaccination_dtp3(valeur):
    """
    Couverture vaccinale DTP3 en pourcentage.

    Un point par tranche de 5 %.
    """
    return noter_par_paliers(
        valeur,
        largeur_palier=5,
        maximum=100,
    )


def noter_sante_mentale(valeur):
    """
    Taux de suicide pour 100 000 habitants.

    0 à moins de 3 : 20/20.
    Chaque tranche supplémentaire de 3 retire un point.
    60 ou plus : 0/20.
    """
    return noter_par_paliers_inverse(
        valeur,
        largeur_palier=3,
        maximum=60,
    )


# ============================================================================
# SANTÉ ANIMALE
# ============================================================================

def noter_services_veterinaires(valeur):
    """
    Nombre de vétérinaires officiels pour
    100 000 unités de gros bétail.

    0 : 0/20.
    150 ou plus : 20/20.
    Progression linéaire entre les deux.
    """
    return noter_lineaire(
        valeur,
        minimum=0,
        maximum=150,
    )


def noter_maladies_animales(valeur):
    """
    Nombre de foyers de maladies animales déclarés.

    0 foyer : 20/20.
    Chaque tranche de 15 foyers retire un point.
    300 foyers ou plus : 0/20.
    """
    return noter_par_paliers_inverse(
        valeur,
        largeur_palier=15,
        maximum=300,
    )


def noter_vaccination_animale(valeur):
    """
    Couverture vaccinale animale en pourcentage.

    Un point par tranche de 5 %.
    """
    return noter_par_paliers(
        valeur,
        largeur_palier=5,
        maximum=100,
    )


def noter_bien_etre_animal(valeur):
    """
    Le score fourni par la source est déjà sur 20.
    """
    if valeur is None:
        return None

    try:
        valeur = float(valeur)
    except (TypeError, ValueError):
        return None

    return borner_note(valeur)


def noter_faune_sauvage(valeur):
    """
    Pression sanitaire déclarée dans la faune sauvage.

    La valeur correspond à la somme annuelle :
    - des cas déclarés dans la faune sauvage ;
    - des nouveaux foyers déclarés dans la faune sauvage.

    0 signalement : 20/20.
    Chaque tranche de 25 signalements retire un point.
    500 signalements ou plus : 0/20.
    """
    return noter_par_paliers_inverse(
        valeur,
        largeur_palier=25,
        maximum=500,
    )


# ============================================================================
# ÉCOSYSTÈME
# ============================================================================

def noter_qualite_air(valeur):
    """
    Concentration annuelle moyenne de PM2.5.

    5 µg/m³ ou moins : 20/20.
    50 µg/m³ ou plus : 0/20.
    Entre les deux : 20 paliers de 2,25 µg/m³.
    """
    if valeur is None:
        return None

    try:
        valeur = float(valeur)
    except (TypeError, ValueError):
        return None

    if valeur <= 5:
        return 20

    if valeur >= 50:
        return 0

    largeur_palier = (50 - 5) / 20
    diminution = math.ceil(
        (valeur - 5) / largeur_palier
    )

    return max(0, min(20, 20 - diminution))


def noter_qualite_eau(valeur):
    """
    Population utilisant une eau potable
    gérée en toute sécurité, en pourcentage.

    Un point par tranche de 5 %.
    """
    return noter_par_paliers(
        valeur,
        largeur_palier=5,
        maximum=100,
    )


def noter_biodiversite(valeur):
    """
    Part du territoire en aires protégées.

    0 % : 0/20.
    30 % ou plus : 20/20.
    Progression linéaire entre les deux.
    """
    return noter_lineaire(
        valeur,
        minimum=0,
        maximum=30,
    )


def noter_deforestation(valeur):
    """
    Couverture forestière du territoire.

    0 % : 0/20.
    40 % ou plus : 20/20.
    Progression linéaire entre les deux.
    """
    return noter_lineaire(
        valeur,
        minimum=0,
        maximum=40,
    )


def noter_traitement_eaux_usees(valeur):
    """
    Part des eaux usées domestiques
    traitées en toute sécurité.

    Un point par tranche de 5 %.
    """
    return noter_par_paliers(
        valeur,
        largeur_palier=5,
        maximum=100,
    )


# ============================================================================
# INFORMATION, PRÉVENTION ET SURVEILLANCE
# ============================================================================

def noter_liberte_presse(valeur):
    """
    Score RSF sur 100.

    Un point par tranche de 5 points.
    """
    return noter_par_paliers(
        valeur,
        largeur_palier=5,
        maximum=100,
    )


def noter_surveillance_epidemiologique(valeur):
    """
    Score SPAR sur 100.

    Un point par tranche de 5 points.
    """
    return noter_par_paliers(
        valeur,
        largeur_palier=5,
        maximum=100,
    )


def noter_partage_donnees(valeur):
    """
    Score SPAR sur 100.

    Un point par tranche de 5 points.
    """
    return noter_par_paliers(
        valeur,
        largeur_palier=5,
        maximum=100,
    )


def noter_preparation_pandemies(valeur):
    """
    Score SPAR sur 100.

    Un point par tranche de 5 points.
    """
    return noter_par_paliers(
        valeur,
        largeur_palier=5,
        maximum=100,
    )


def noter_gestion_crises(valeur):
    """
    Score SPAR sur 100.

    Un point par tranche de 5 points.
    """
    return noter_par_paliers(
        valeur,
        largeur_palier=5,
        maximum=100,
    )