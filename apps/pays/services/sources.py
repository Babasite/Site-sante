import csv
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


API_BANQUE_MONDIALE = "https://api.worldbank.org/v2"
API_OMS_XMART = "https://xmart-api-public.who.int/DATA_/RELAY_WHS"
DELAI_REQUETE = 10

INDICATEURS_OMS_XMART = {
    "UHC_INDEX_REPORTED": "9A706FDUHC_INDEX_REPORTED",
    "SDGSUICIDE": "16BBF41SDGSUICIDE",
    "SDGPM25": "F810947SDGPM25",
    "WSH_DOMESTIC_WASTE_SAFELY_TREATED": (
        "A37BDD6WSH_DOMESTIC_WASTE_SAFELY_TREATED"
    ),
}

BASE_DIR = Path(__file__).resolve().parent.parent

FICHIER_INDICATEURS = (
    BASE_DIR / "data" / "indicateurs.csv"
)

FICHIER_NOUVELLES_SOURCES = (
    BASE_DIR / "data" / "nouvelles_sources.csv"
)


ANNEES_INDICATEURS = (
    2000,
    2010,
    2020,
    2026,
)

COLONNES_INDICATEURS = [
    "iso3",
    "year",
    "esperance_vie",
    "medecins",
    "uhc",
    "vaccination_dtp3",
    "sante_mentale",
    "services_veterinaires",
    "maladies_animales",
    "vaccination_animale",
    "bien_etre_animal",
    "faune_sauvage",
    "qualite_air",
    "qualite_eau",
    "biodiversite",
    "couverture_forestiere",
    "traitement_eaux_usees",
    "liberte_presse",
    "surveillance_epidemiologique",
    "partage_donnees",
    "preparation_pandemies",
    "gestion_crises",
]



def recuperer_codes_iso3_pays():
    """
    Récupère les codes ISO3 des pays depuis l'API
    officielle de la Banque mondiale.

    Les agrégats régionaux et mondiaux sont exclus.
    """
    parametres = urlencode({
        "format": "json",
        "per_page": 400,
    })

    url = f"{API_BANQUE_MONDIALE}/country?{parametres}"

    try:
        with urlopen(url, timeout=DELAI_REQUETE) as reponse:
            donnees = json.load(reponse)

    except (
        HTTPError,
        URLError,
        TimeoutError,
        json.JSONDecodeError,
        OSError,
    ):
        return []

    if (
        not isinstance(donnees, list)
        or len(donnees) < 2
        or not isinstance(donnees[1], list)
    ):
        return []

    codes = []

    for pays in donnees[1]:
        region = pays.get("region", {})
        code_region = str(region.get("id", "")).strip()
        code_iso3 = str(pays.get("id", "")).strip().upper()

        # La Banque mondiale utilise "NA" pour les agrégats.
        if code_region == "NA":
            continue

        if len(code_iso3) == 3 and code_iso3.isalpha():
            codes.append(code_iso3)

    return sorted(set(codes))


def initialiser_fichier_indicateurs():
    """
    Crée ou complète indicateurs.csv avec une ligne
    pour chaque pays et chaque année de référence.

    Les valeurs déjà présentes sont conservées.
    Les lignes manquantes sont ajoutées avec des cellules vides.

    Retourne le nombre de lignes ajoutées.
    """
    FICHIER_INDICATEURS.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    lignes_existantes = {}
    colonnes_existantes = []

    if FICHIER_INDICATEURS.exists():
        try:
            with FICHIER_INDICATEURS.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as fichier:
                lecteur = csv.DictReader(fichier)
                colonnes_existantes = lecteur.fieldnames or []

                for ligne in lecteur:
                    iso3 = str(
                        ligne.get("iso3", "")
                    ).strip().upper()

                    try:
                        annee = int(ligne.get("year", ""))
                    except (TypeError, ValueError):
                        continue

                    if iso3:
                        lignes_existantes[(iso3, annee)] = ligne

        except (OSError, csv.Error):
            lignes_existantes = {}
            colonnes_existantes = []

    codes_iso3 = recuperer_codes_iso3_pays()

    if not codes_iso3:
        return 0

    colonnes = list(COLONNES_INDICATEURS)

    # Conserve d'éventuelles colonnes ajoutées plus tard.
    for colonne in colonnes_existantes:
        if colonne and colonne not in colonnes:
            colonnes.append(colonne)

    lignes_finales = []
    nombre_ajoute = 0

    for code_iso3 in codes_iso3:
        for annee in ANNEES_INDICATEURS:
            cle = (code_iso3, annee)

            if cle in lignes_existantes:
                ligne = {
                    colonne: lignes_existantes[cle].get(
                        colonne,
                        "",
                    )
                    for colonne in colonnes
                }
            else:
                ligne = {
                    colonne: ""
                    for colonne in colonnes
                }
                ligne["iso3"] = code_iso3
                ligne["year"] = annee
                nombre_ajoute += 1

            lignes_finales.append(ligne)

    try:
        with FICHIER_INDICATEURS.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as fichier:
            ecrivain = csv.DictWriter(
                fichier,
                fieldnames=colonnes,
            )
            ecrivain.writeheader()
            ecrivain.writerows(lignes_finales)

    except (OSError, csv.Error):
        return 0

    return nombre_ajoute


def recuperer_indicateur_banque_mondiale(code_pays, code_indicateur):
    """
    Récupère la valeur non vide la plus récente d'un indicateur
    dans l'API de la Banque mondiale.

    La fonction parcourt les années 2000 à 2026,
    ignore les cellules vides et retient l'année
    la plus récente réellement disponible.

    Retourne un nombre ou None.
    """
    if not isinstance(code_pays, str):
        return None

    code_pays = code_pays.strip().lower()

    if not code_pays:
        return None

    parametres = urlencode({
        "format": "json",
        "date": "2000:2026",
        "source": 2,
        "per_page": 100,
    })

    url = (
        f"{API_BANQUE_MONDIALE}/country/{code_pays}"
        f"/indicator/{code_indicateur}?{parametres}"
    )

    try:
        with urlopen(url, timeout=DELAI_REQUETE) as reponse:
            donnees = json.load(reponse)

    except (
        HTTPError,
        URLError,
        TimeoutError,
        json.JSONDecodeError,
        OSError,
    ):
        return None

    if (
        not isinstance(donnees, list)
        or len(donnees) < 2
        or not isinstance(donnees[1], list)
    ):
        return None

    meilleure_annee = None
    meilleure_valeur = None

    for ligne in donnees[1]:
        if not isinstance(ligne, dict):
            continue

        valeur = ligne.get("value")

        if valeur is None:
            continue

        try:
            annee = int(ligne.get("date", ""))
            valeur = float(valeur)
        except (TypeError, ValueError):
            continue

        if meilleure_annee is None or annee > meilleure_annee:
            meilleure_annee = annee
            meilleure_valeur = valeur

    return meilleure_valeur


def convertir_code_iso2_vers_iso3(code_pays):
    """
    Convertit un code pays ISO alpha-2 en ISO alpha-3
    grâce à l'API pays de la Banque mondiale.

    Exemple : fr -> FRA.
    """
    if not isinstance(code_pays, str):
        return None

    code_pays = code_pays.strip().lower()

    if not code_pays:
        return None

    url = (
        f"{API_BANQUE_MONDIALE}/country/{code_pays}"
        "?format=json"
    )

    try:
        with urlopen(url, timeout=DELAI_REQUETE) as reponse:
            donnees = json.load(reponse)

    except (
        HTTPError,
        URLError,
        TimeoutError,
        json.JSONDecodeError,
        OSError,
    ):
        return None

    if (
        not isinstance(donnees, list)
        or len(donnees) < 2
        or not donnees[1]
    ):
        return None

    code_iso3 = donnees[1][0].get("id")

    if not code_iso3:
        return None

    return str(code_iso3).upper()


def convertir_iso3_vers_m49(code_iso3):
    """
    Convertit un code ISO alpha-3 en code numérique M49.

    La nouvelle API WHO Data utilise le code M49
    pour identifier les pays.
    """
    if not isinstance(code_iso3, str):
        return None

    code_iso3 = code_iso3.strip().upper()

    if len(code_iso3) != 3:
        return None

    try:
        import pycountry

        pays = pycountry.countries.get(
            alpha_3=code_iso3
        )

        if pays is None:
            return None

        code_numerique = getattr(
            pays,
            "numeric",
            None,
        )

        if not code_numerique:
            return None

        return int(code_numerique)

    except (ImportError, AttributeError, ValueError):
        return None


def extraire_valeur_oms(ligne):
    """
    Extrait la valeur centrale d'une ligne WHO Data.

    Les fichiers WHO utilisent des colonnes différentes
    selon l'unité de l'indicateur, par exemple :
    AMOUNT_N, RATE_PER_100_N ou RATE_PER_100000_N.
    """
    if not isinstance(ligne, dict):
        return None

    colonnes_prioritaires = (
        "AMOUNT_N",
        "INDEX_N",
        "PERCENT_N",
        "RATE_PER_100_N",
        "RATE_PER_1000_N",
        "RATE_PER_10000_N",
        "RATE_PER_100000_N",
        "VALUE_N",
        "NUMERIC_VALUE",
    )

    for colonne in colonnes_prioritaires:
        valeur = ligne.get(colonne)

        if valeur in (None, ""):
            continue

        try:
            return float(valeur)
        except (TypeError, ValueError):
            continue

    # Solution générique pour les autres unités WHO :
    # on retient une valeur centrale se terminant par _N,
    # mais jamais les bornes inférieure/supérieure _NL/_NU.
    for colonne, valeur in ligne.items():
        nom = str(colonne).upper()

        if not nom.endswith("_N"):
            continue

        if nom.endswith(("_NL", "_NU")):
            continue

        if nom.startswith("DIM_"):
            continue

        if valeur in (None, ""):
            continue

        try:
            return float(valeur)
        except (TypeError, ValueError):
            continue

    return None


def ligne_oms_est_totale(ligne):
    """
    Indique si une ligne correspond de préférence
    à la population totale, sans ventilation par sexe.
    """
    if not isinstance(ligne, dict):
        return False

    sexe = str(
        ligne.get("DIM_SEX", "")
    ).strip().upper()

    return sexe in (
        "",
        "TOTAL",
        "BTSX",
        "ALL",
        "BOTHSEX",
    )


def recuperer_indicateur_oms(code_pays, code_indicateur):
    """
    Récupère la dernière valeur nationale disponible
    depuis la nouvelle API WHO Data xMart.

    L'ancienne API ghoapi.azureedge.net est dépréciée.
    """
    code_iso3 = convertir_code_iso2_vers_iso3(
        code_pays
    )

    if code_iso3 is None:
        return None

    code_m49 = convertir_iso3_vers_m49(
        code_iso3
    )

    if code_m49 is None:
        return None

    identifiant = INDICATEURS_OMS_XMART.get(
        code_indicateur
    )

    if identifiant is None:
        return None

    filtre = (
        f"IND_ID eq '{identifiant}' "
        f"and DIM_GEO_CODE_M49 eq {code_m49} "
        "and DIM_GEO_CODE_TYPE eq 'COUNTRY'"
    )

    parametres = urlencode({
        "$filter": filtre,
        "$format": "json",
    })

    url = (
        f"{API_OMS_XMART}"
        f"?{parametres}"
    )

    try:
        with urlopen(
            url,
            timeout=DELAI_REQUETE,
        ) as reponse:
            donnees = json.load(reponse)

    except (
        HTTPError,
        URLError,
        TimeoutError,
        json.JSONDecodeError,
        OSError,
    ):
        return None

    if isinstance(donnees, dict):
        lignes = donnees.get("value", [])
    elif isinstance(donnees, list):
        lignes = donnees
    else:
        return None

    if not isinstance(lignes, list):
        return None

    candidats = []

    for ligne in lignes:
        if not isinstance(ligne, dict):
            continue

        try:
            annee = int(
                ligne.get("DIM_TIME", "")
            )
        except (TypeError, ValueError):
            continue

        valeur = extraire_valeur_oms(
            ligne
        )

        if valeur is None:
            continue

        candidats.append((
            annee,
            ligne_oms_est_totale(ligne),
            valeur,
        ))

    if not candidats:
        return None

    # Dernière année d'abord, puis ligne totale
    # avant une éventuelle ligne ventilée.
    candidats.sort(
        key=lambda element: (
            element[0],
            element[1],
        ),
        reverse=True,
    )

    return candidats[0][2]



def lire_derniere_valeur_dans_fichier(
    chemin_fichier,
    code_iso3,
    colonne_valeur,
    colonne_annee="year",
):
    """
    Lit la valeur non vide la plus récente d'un pays
    dans un fichier CSV donné.

    Retourne un tuple :
    (année, valeur)

    Retourne (None, None) si aucune donnée n'est disponible.
    """
    if not chemin_fichier.exists():
        return None, None

    meilleure_annee = None
    meilleure_valeur = None

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

                if iso3 != code_iso3:
                    continue

                try:
                    annee = int(
                        ligne.get(colonne_annee, "")
                    )
                    valeur = float(
                        ligne.get(colonne_valeur, "")
                    )
                except (TypeError, ValueError):
                    continue

                if (
                    meilleure_annee is None
                    or annee > meilleure_annee
                ):
                    meilleure_annee = annee
                    meilleure_valeur = valeur

    except (OSError, csv.Error):
        return None, None

    return meilleure_annee, meilleure_valeur


def lire_derniere_valeur_csv(
    code_pays,
    colonne_valeur,
    colonne_annee="year",
):
    """
    Recherche la dernière valeur disponible d'un indicateur.

    Ordre de priorité :
    1. apps/pays/data/indicateurs.csv
    2. apps/pays/data/nouvelles_sources.csv

    Si indicateurs.csv contient une valeur, elle est utilisée.
    Sinon, la dernière valeur archivée dans
    nouvelles_sources.csv est utilisée.
    """
    code_iso3 = convertir_code_iso2_vers_iso3(
        code_pays
    )

    if code_iso3 is None:
        return None

    _, valeur_indicateurs = (
        lire_derniere_valeur_dans_fichier(
            FICHIER_INDICATEURS,
            code_iso3,
            colonne_valeur,
            colonne_annee,
        )
    )

    if valeur_indicateurs is not None:
        return valeur_indicateurs

    _, valeur_nouvelles_sources = (
        lire_derniere_valeur_dans_fichier(
            FICHIER_NOUVELLES_SOURCES,
            code_iso3,
            colonne_valeur,
            colonne_annee,
        )
    )

    return valeur_nouvelles_sources


def recuperer_premiere_valeur(*fonctions):
    """
    Exécute les sources dans l'ordre fourni.

    Dès qu'une source renvoie une valeur valide,
    les suivantes ne sont pas interrogées.
    """
    for fonction in fonctions:
        try:
            valeur = fonction()
        except (
            HTTPError,
            URLError,
            TimeoutError,
            json.JSONDecodeError,
            OSError,
        ):
            valeur = None

        if valeur is not None:
            return valeur

    return None


# ============================================================================
# SANTÉ HUMAINE
# ============================================================================

def recuperer_esperance_vie(code_pays):
    """
    Dernière espérance de vie disponible, en années.

    Priorité :
    1. fichiers CSV locaux ;
    2. Banque mondiale.
    """
    return recuperer_premiere_valeur(
        lambda: lire_derniere_valeur_csv(
            code_pays,
            "esperance_vie",
        ),
        lambda: recuperer_indicateur_banque_mondiale(
            code_pays,
            "SP.DYN.LE00.IN",
        ),
    )


def recuperer_medecins(code_pays):
    """
    Dernier nombre de médecins disponible
    pour 1 000 habitants.

    Priorité :
    1. fichiers CSV locaux ;
    2. Banque mondiale.
    """
    return recuperer_premiere_valeur(
        lambda: lire_derniere_valeur_csv(
            code_pays,
            "medecins",
        ),
        lambda: recuperer_indicateur_banque_mondiale(
            code_pays,
            "SH.MED.PHYS.ZS",
        ),
    )


def recuperer_uhc(code_pays):
    """
    Dernier indice de couverture des services
    de santé essentiels, sur 100.

    Priorité :
    1. fichiers CSV locaux ;
    2. OMS.
    """
    return recuperer_premiere_valeur(
        lambda: lire_derniere_valeur_csv(
            code_pays,
            "uhc",
        ),
        lambda: recuperer_indicateur_oms(
            code_pays,
            "UHC_INDEX_REPORTED",
        ),
    )


def recuperer_vaccination_dtp3(code_pays):
    """
    Dernière couverture vaccinale DTP3 disponible,
    en pourcentage.

    Source : OMS / UNICEF - WUENIC.
    Colonne : vaccination_dtp3
    """
    return lire_derniere_valeur_csv(
        code_pays,
        "vaccination_dtp3",
    )


def recuperer_sante_mentale(code_pays):
    """
    Dernier taux de mortalité par suicide disponible,
    pour 100 000 habitants.

    Priorité :
    1. fichiers CSV locaux ;
    2. OMS.
    """
    return recuperer_premiere_valeur(
        lambda: lire_derniere_valeur_csv(
            code_pays,
            "sante_mentale",
        ),
        lambda: recuperer_indicateur_oms(
            code_pays,
            "SDGSUICIDE",
        ),
    )


# ============================================================================
# SANTÉ ANIMALE
# ============================================================================

def recuperer_services_veterinaires(code_pays):
    """
    Dernier ratio de vétérinaires officiels
    pour 100 000 unités de gros bétail.

    Source : WOAH - WAHIS.
    Colonne : services_veterinaires
    """
    return lire_derniere_valeur_csv(
        code_pays,
        "services_veterinaires",
    )


def recuperer_maladies_animales(code_pays):
    """
    Dernier nombre de foyers de maladies animales déclarés.

    Source : WOAH - WAHIS.
    Colonne : maladies_animales
    """
    return lire_derniere_valeur_csv(
        code_pays,
        "maladies_animales",
    )


def recuperer_vaccination_animale(code_pays):
    """
    Dernière couverture vaccinale animale disponible,
    en pourcentage.

    Source : WOAH - WAHIS.
    Colonne : vaccination_animale
    """
    return lire_derniere_valeur_csv(
        code_pays,
        "vaccination_animale",
    )


def recuperer_bien_etre_animal(code_pays):
    """
    Dernier score de bien-être animal disponible, sur 20.

    Source documentaire : FAOLEX.
    Colonne : bien_etre_animal
    """
    return lire_derniere_valeur_csv(
        code_pays,
        "bien_etre_animal",
    )


def recuperer_faune_sauvage(code_pays):
    """
    Dernière valeur de l'indicateur ODD 15.7.1.

    Source : ONU / UNODC / CITES.
    Colonne : faune_sauvage
    """
    return lire_derniere_valeur_csv(
        code_pays,
        "faune_sauvage",
    )


# ============================================================================
# ÉCOSYSTÈME
# ============================================================================

def recuperer_qualite_air(code_pays):
    """
    Récupère la concentration annuelle moyenne de PM2.5
    dans les zones urbaines, en µg/m³.

    Priorité :
    1. fichiers CSV locaux ;
    2. OMS.
    """
    return recuperer_premiere_valeur(
        lambda: lire_derniere_valeur_csv(
            code_pays,
            "qualite_air",
        ),
        lambda: recuperer_indicateur_oms(
            code_pays,
            "SDGPM25",
        ),
    )


def recuperer_qualite_eau(code_pays):
    """
    Récupère la proportion de la population utilisant
    des services d'eau potable gérés en toute sécurité,
    en pourcentage.

    Priorité :
    1. fichiers CSV locaux ;
    2. Banque mondiale.
    """
    return recuperer_premiere_valeur(
        lambda: lire_derniere_valeur_csv(
            code_pays,
            "qualite_eau",
        ),
        lambda: recuperer_indicateur_banque_mondiale(
            code_pays,
            "SH.H2O.SMDW.ZS",
        ),
    )


def recuperer_biodiversite(code_pays):
    """
    Récupère la proportion du territoire couverte
    par des aires protégées terrestres et marines,
    en pourcentage.

    Priorité :
    1. fichiers CSV locaux ;
    2. Banque mondiale.
    """
    return recuperer_premiere_valeur(
        lambda: lire_derniere_valeur_csv(
            code_pays,
            "biodiversite",
        ),
        lambda: recuperer_indicateur_banque_mondiale(
            code_pays,
            "ER.PTD.TOTL.ZS",
        ),
    )


def recuperer_deforestation(code_pays):
    """
    Récupère la superficie forestière en pourcentage
    de la superficie terrestre.

    Priorité :
    1. fichiers CSV locaux ;
    2. Banque mondiale.

    Cette donnée mesure la part de forêt restante.
    Elle ne mesure pas directement la variation annuelle
    de la déforestation.
    """
    return recuperer_premiere_valeur(
        lambda: lire_derniere_valeur_csv(
            code_pays,
            "couverture_forestiere",
        ),
        lambda: recuperer_indicateur_banque_mondiale(
            code_pays,
            "AG.LND.FRST.ZS",
        ),
    )


def recuperer_traitement_eaux_usees(code_pays):
    """
    Récupère la proportion des flux d'eaux usées
    domestiques traités en toute sécurité,
    en pourcentage.

    Priorité :
    1. fichiers CSV locaux ;
    2. OMS.
    """
    return recuperer_premiere_valeur(
        lambda: lire_derniere_valeur_csv(
            code_pays,
            "traitement_eaux_usees",
        ),
        lambda: recuperer_indicateur_oms(
            code_pays,
            "WSH_DOMESTIC_WASTE_SAFELY_TREATED",
        ),
    )

# ============================================================================
# INFORMATION, PRÉVENTION ET SURVEILLANCE
# ============================================================================

def recuperer_liberte_presse(code_pays):
    """
    Dernier score de liberté de la presse disponible,
    sur 100.

    Source : Reporters sans frontières.
    Colonne : liberte_presse
    """
    return lire_derniere_valeur_csv(
        code_pays,
        "liberte_presse",
    )


def recuperer_surveillance_epidemiologique(code_pays):
    """
    Dernier score SPAR de surveillance épidémiologique,
    sur 100.

    Source : OMS - SPAR.
    Colonne : surveillance_epidemiologique
    """
    return lire_derniere_valeur_csv(
        code_pays,
        "surveillance_epidemiologique",
    )


def recuperer_partage_donnees(code_pays):
    """
    Dernier score SPAR de partage des données, sur 100.

    Source : OMS - SPAR.
    Colonne : partage_donnees
    """
    return lire_derniere_valeur_csv(
        code_pays,
        "partage_donnees",
    )


def recuperer_preparation_pandemies(code_pays):
    """
    Dernier score SPAR de préparation aux pandémies,
    sur 100.

    Source : OMS - SPAR.
    Colonne : preparation_pandemies
    """
    return lire_derniere_valeur_csv(
        code_pays,
        "preparation_pandemies",
    )


def recuperer_gestion_crises(code_pays):
    """
    Dernier score SPAR de gestion des crises, sur 100.

    Source : OMS - SPAR.
    Colonne : gestion_crises
    """
    return lire_derniere_valeur_csv(
        code_pays,
        "gestion_crises",
    )