import csv
import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


# ============================================================================
# CONFIGURATION
# ============================================================================

API_BANQUE_MONDIALE = "https://api.worldbank.org/v2"
API_OMS_XMART = "https://xmart-api-public.who.int/DATA_/RELAY_WHS"

DELAI_REQUETE = 60
NOMBRE_TENTATIVES = 3
PAUSE_ENTRE_TENTATIVES = 3
TAILLE_PAGE_BANQUE_MONDIALE = 1000

INDICATEURS_OMS_XMART = {
    "UHC_INDEX_REPORTED": (
        "9A706FDUHC_INDEX_REPORTED"
    ),
    "SDGSUICIDE": (
        "16BBF41SDGSUICIDE"
    ),
    "SDGPM25": (
        "F810947SDGPM25"
    ),
    "WSH_DOMESTIC_WASTE_SAFELY_TREATED": (
        "A37BDD6WSH_DOMESTIC_WASTE_SAFELY_TREATED"
    ),
}

TAILLE_PAGE_OMS = 10_000

BASE_DIR = Path(__file__).resolve().parent.parent

FICHIER_INDICATEURS = (
    BASE_DIR / "data" / "indicateurs.csv"
)

FICHIER_NOUVELLES_SOURCES = (
    BASE_DIR / "data" / "nouvelles_sources.csv"
)

DOSSIER_DOCUMENTS_SOURCES = (
    BASE_DIR / "data" / "documents_sources"
)

FICHIER_RSF = (
    DOSSIER_DOCUMENTS_SOURCES / "RSF.csv"
)

FICHIER_WOAH = (
    DOSSIER_DOCUMENTS_SOURCES / "WOAH.csv"
)

ANNEES_HISTORIQUES = (2000, 2010, 2020)
ANNEE_ACTUELLE = 2026

# Les valeurs déjà renseignées dans indicateurs.csv
# sont prioritaires et ne doivent jamais être écrasées.
CELLULES_PRIORITAIRES = set()


INDICATEURS_BANQUE_MONDIALE = {
    "esperance_vie": "SP.DYN.LE00.IN",
    "medecins": "SH.MED.PHYS.ZS",
    "qualite_eau": "SH.H2O.SMDW.ZS",
    "biodiversite": "ER.PTD.TOTL.ZS",
    "couverture_forestiere": "AG.LND.FRST.ZS",
}


INDICATEURS_OMS = {
    "uhc": "UHC_INDEX_REPORTED",
    "sante_mentale": "SDGSUICIDE",
    "qualite_air": "SDGPM25",
    "traitement_eaux_usees": (
        "WSH_DOMESTIC_WASTE_SAFELY_TREATED"
    ),
}


# ============================================================================
# OUTILS GÉNÉRAUX
# ============================================================================

def telecharger_json(url):
    """
    Télécharge une réponse JSON avec plusieurs tentatives.

    Retourne le contenu JSON ou None si toutes
    les tentatives échouent.
    """
    for tentative in range(1, NOMBRE_TENTATIVES + 1):
        try:
            with urlopen(
                url,
                timeout=DELAI_REQUETE,
            ) as reponse:
                contenu = reponse.read()

            return json.loads(
                contenu.decode("utf-8-sig")
            )

        except (
            HTTPError,
            URLError,
            TimeoutError,
            json.JSONDecodeError,
            OSError,
        ) as erreur:
            print(
                f"Tentative {tentative}/"
                f"{NOMBRE_TENTATIVES} échouée : {erreur}"
            )

            if tentative < NOMBRE_TENTATIVES:
                time.sleep(PAUSE_ENTRE_TENTATIVES)

    return None


def convertir_nombre(valeur):
    """
    Convertit une valeur en nombre flottant.

    Retourne None si la valeur est vide ou invalide.
    """
    if valeur in (None, ""):
        return None

    try:
        return float(valeur)
    except (TypeError, ValueError):
        return None


def charger_fichier_csv(chemin_fichier):
    """
    Charge un fichier CSV d'indicateurs.

    Retourne :
    - la liste des colonnes ;
    - un dictionnaire indexé par (iso3, année).
    """
    if not chemin_fichier.exists():
        raise FileNotFoundError(
            f"Fichier introuvable : {chemin_fichier}"
        )

    with chemin_fichier.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as fichier:
        lecteur = csv.DictReader(fichier)
        colonnes = lecteur.fieldnames or []

        if "iso3" not in colonnes or "year" not in colonnes:
            raise RuntimeError(
                f"{chemin_fichier.name} doit contenir "
                "les colonnes 'iso3' et 'year'."
            )

        lignes = {}

        for ligne in lecteur:
            iso3 = str(
                ligne.get("iso3", "")
            ).strip().upper()

            try:
                annee = int(ligne.get("year", ""))
            except (TypeError, ValueError):
                continue

            if iso3:
                lignes[(iso3, annee)] = ligne

    return colonnes, lignes


def charger_nouvelles_sources():
    """
    Charge nouvelles_sources.csv.

    Si le fichier ne contient encore que l'en-tête,
    ses lignes sont initialisées à partir d'indicateurs.csv.
    Cela évite d'ajouter manuellement tous les pays.
    """
    colonnes_sources, lignes_sources = (
        charger_fichier_csv(
            FICHIER_NOUVELLES_SOURCES
        )
    )

    if lignes_sources:
        return colonnes_sources, lignes_sources

    colonnes_indicateurs, lignes_indicateurs = (
        charger_fichier_csv(
            FICHIER_INDICATEURS
        )
    )

    colonnes = list(colonnes_indicateurs)

    for colonne in colonnes_sources:
        if colonne and colonne not in colonnes:
            colonnes.append(colonne)

    lignes = {}

    for cle, ligne_indicateurs in lignes_indicateurs.items():
        nouvelle_ligne = {
            colonne: ""
            for colonne in colonnes
        }

        nouvelle_ligne["iso3"] = ligne_indicateurs.get(
            "iso3",
            "",
        )
        nouvelle_ligne["year"] = ligne_indicateurs.get(
            "year",
            "",
        )

        lignes[cle] = nouvelle_ligne

    return colonnes, lignes


def enregistrer_fichier_csv(
    chemin_fichier,
    colonnes,
    lignes,
):
    """
    Enregistre toutes les lignes dans le fichier CSV indiqué.
    """
    lignes_triees = sorted(
        lignes.values(),
        key=lambda ligne: (
            str(ligne.get("iso3", "")),
            int(ligne.get("year", 0)),
        ),
    )

    with chemin_fichier.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as fichier:
        ecrivain = csv.DictWriter(
            fichier,
            fieldnames=colonnes,
        )
        ecrivain.writeheader()
        ecrivain.writerows(lignes_triees)


def enregistrer_nouvelles_sources(colonnes, lignes):
    """
    Enregistre les données téléchargées uniquement dans
    nouvelles_sources.csv.

    indicateurs.csv n'est jamais modifié par ce script.
    """
    enregistrer_fichier_csv(
        FICHIER_NOUVELLES_SOURCES,
        colonnes,
        lignes,
    )


def ajouter_colonnes_manquantes(colonnes, lignes):
    """
    Ajoute les colonnes nécessaires si elles sont absentes.
    """
    colonnes_attendues = (
        list(INDICATEURS_BANQUE_MONDIALE.keys())
        + list(INDICATEURS_OMS.keys())
        + [
            "liberte_presse",
            "maladies_animales",
            "vaccination_animale",
            "faune_sauvage",
        ]
    )

    for colonne in colonnes_attendues:
        if colonne not in colonnes:
            colonnes.append(colonne)

    for ligne in lignes.values():
        for colonne in colonnes:
            ligne.setdefault(colonne, "")


def valeur_est_renseignee(valeur):
    """
    Indique si une cellule contient déjà une valeur exploitable.
    """
    if valeur is None:
        return False

    texte = str(valeur).strip()

    return texte not in ("", "-", "—", "–", "NA", "N/A")


def charger_cellules_prioritaires():
    """
    Repère les valeurs déjà renseignées dans indicateurs.csv.

    Ces cellules sont considérées comme prioritaires :
    actualisation_sources.py ne les écrasera pas dans
    nouvelles_sources.csv.
    """
    if not FICHIER_INDICATEURS.exists():
        return set()

    try:
        colonnes, lignes = charger_fichier_csv(
            FICHIER_INDICATEURS
        )
    except (
        FileNotFoundError,
        RuntimeError,
        OSError,
        csv.Error,
    ):
        return set()

    cellules = set()

    for (iso3, annee), ligne in lignes.items():
        for colonne in colonnes:
            if colonne in ("iso3", "year"):
                continue

            if valeur_est_renseignee(
                ligne.get(colonne)
            ):
                cellules.add(
                    (iso3, annee, colonne)
                )

    return cellules


def cellule_est_prioritaire(
    iso3,
    annee,
    colonne,
):
    """
    Vérifie si une cellule est protégée par indicateurs.csv.
    """
    return (
        iso3,
        annee,
        colonne,
    ) in CELLULES_PRIORITAIRES


def inscrire_series_dans_lignes(
    lignes,
    colonne,
    series_par_pays,
):
    """
    Inscrit les années historiques exactes et utilise
    la dernière valeur disponible pour la ligne 2026.
    """
    nombre_modifications = 0

    for iso3, valeurs_par_annee in series_par_pays.items():
        valeurs_valides = {
            annee: valeur
            for annee, valeur in valeurs_par_annee.items()
            if valeur is not None and annee <= ANNEE_ACTUELLE
        }

        if not valeurs_valides:
            continue

        for annee in ANNEES_HISTORIQUES:
            valeur = valeurs_valides.get(annee)
            cle = (iso3, annee)

            if (
                valeur is not None
                and cle in lignes
                and not cellule_est_prioritaire(
                    iso3,
                    annee,
                    colonne,
                )
            ):
                lignes[cle][colonne] = valeur
                nombre_modifications += 1

        derniere_annee = max(valeurs_valides)
        derniere_valeur = valeurs_valides[derniere_annee]
        cle_actuelle = (iso3, ANNEE_ACTUELLE)

        if (
            cle_actuelle in lignes
            and not cellule_est_prioritaire(
                iso3,
                ANNEE_ACTUELLE,
                colonne,
            )
        ):
            lignes[cle_actuelle][colonne] = derniere_valeur
            nombre_modifications += 1

    return nombre_modifications


# ============================================================================
# BANQUE MONDIALE
# ============================================================================

def telecharger_indicateur_banque_mondiale(
    code_indicateur,
):
    """
    Télécharge une série Banque mondiale pour tous les pays,
    entre 2000 et 2026, page par page.

    La pagination évite les réponses trop volumineuses
    qui provoquaient des délais d'attente.
    """
    resultat = {}
    page = 1
    nombre_pages = 1

    while page <= nombre_pages:
        parametres = urlencode({
            "format": "json",
            "date": "2000:2026",
            "source": 2,
            "per_page": TAILLE_PAGE_BANQUE_MONDIALE,
            "page": page,
        })

        url = (
            f"{API_BANQUE_MONDIALE}/country/all"
            f"/indicator/{code_indicateur}?{parametres}"
        )

        print(
            f"  Banque mondiale, page "
            f"{page}/{nombre_pages}..."
        )

        donnees = telecharger_json(url)

        if (
            not isinstance(donnees, list)
            or len(donnees) < 2
            or not isinstance(donnees[1], list)
        ):
            print(
                f"  Impossible de lire la page {page}."
            )
            break

        metadonnees = donnees[0]

        if isinstance(metadonnees, dict):
            try:
                nombre_pages = int(
                    metadonnees.get("pages", 1)
                )
            except (TypeError, ValueError):
                nombre_pages = 1

        for ligne in donnees[1]:
            if not isinstance(ligne, dict):
                continue

            iso3 = str(
                ligne.get("countryiso3code", "")
            ).strip().upper()

            if len(iso3) != 3:
                continue

            try:
                annee = int(ligne.get("date", ""))
            except (TypeError, ValueError):
                continue

            valeur = convertir_nombre(
                ligne.get("value")
            )

            if valeur is None:
                continue

            resultat.setdefault(
                iso3,
                {},
            )[annee] = valeur

        page += 1

    return resultat


def actualiser_banque_mondiale(colonnes, lignes):
    """
    Met à jour les cinq colonnes Banque mondiale.
    """
    total = 0

    for colonne, code_indicateur in (
        INDICATEURS_BANQUE_MONDIALE.items()
    ):
        print(
            f"Banque mondiale : {colonne} "
            f"({code_indicateur})..."
        )

        series = telecharger_indicateur_banque_mondiale(
            code_indicateur
        )

        total += inscrire_series_dans_lignes(
            lignes,
            colonne,
            series,
        )

        enregistrer_nouvelles_sources(
            colonnes,
            lignes,
        )

    return total


# ============================================================================
# OMS
# ============================================================================

def convertir_m49_vers_iso3(code_m49):
    """
    Convertit un code numérique M49 en code ISO alpha-3.

    La nouvelle API WHO Data xMart identifie les pays
    principalement avec leur code M49.
    """
    if code_m49 in (None, ""):
        return None

    try:
        code_numerique = str(
            int(code_m49)
        ).zfill(3)
    except (TypeError, ValueError):
        return None

    try:
        import pycountry

        pays = pycountry.countries.get(
            numeric=code_numerique
        )

        if pays is None:
            return None

        return pays.alpha_3

    except (ImportError, AttributeError):
        return None


def extraire_valeur_oms(ligne):
    """
    Extrait la valeur numérique centrale d'une ligne
    de l'API WHO Data xMart.

    Le nom de la colonne dépend de l'unité de mesure
    de l'indicateur.
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
        valeur = convertir_nombre(
            ligne.get(colonne)
        )

        if valeur is not None:
            return valeur

    for colonne, valeur_brute in ligne.items():
        nom_colonne = str(
            colonne
        ).upper()

        if not nom_colonne.endswith("_N"):
            continue

        if nom_colonne.endswith(
            ("_NL", "_NU")
        ):
            continue

        if nom_colonne.startswith("DIM_"):
            continue

        valeur = convertir_nombre(
            valeur_brute
        )

        if valeur is not None:
            return valeur

    return None


def ligne_oms_est_totale(ligne):
    """
    Privilégie les lignes nationales non ventilées
    par sexe lorsqu'elles sont disponibles.
    """
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


def telecharger_indicateur_oms(code_indicateur):
    """
    Télécharge une série OMS pour tous les pays
    depuis l'API publique WHO Data xMart.

    Seule cette fonction remplace l'ancien accès
    ghoapi.azureedge.net. Le format retourné reste :
    {
        "FRA": {
            2020: valeur,
            ...
        },
        ...
    }
    """
    identifiant_oms = (
        INDICATEURS_OMS_XMART.get(
            code_indicateur
        )
    )

    if identifiant_oms is None:
        print(
            "Indicateur OMS non configuré :",
            code_indicateur,
        )
        return {}

    filtre = (
        f"IND_ID eq '{identifiant_oms}' "
        "and DIM_GEO_CODE_TYPE eq 'COUNTRY'"
    )

    resultat_temporaire = {}
    position = 0

    while True:
        parametres = urlencode({
            "$filter": filtre,
            "$top": TAILLE_PAGE_OMS,
            "$skip": position,
            "$format": "json",
        })

        url = (
            f"{API_OMS_XMART}"
            f"?{parametres}"
        )

        print(
            "  OMS, lignes",
            position + 1,
            "à",
            position + TAILLE_PAGE_OMS,
            "...",
        )

        donnees = telecharger_json(url)

        if isinstance(donnees, dict):
            lignes_api = donnees.get(
                "value",
                [],
            )
        elif isinstance(donnees, list):
            lignes_api = donnees
        else:
            print(
                f"OMS indisponible "
                f"({code_indicateur})."
            )
            return {}

        if not isinstance(lignes_api, list):
            print(
                f"Réponse OMS invalide "
                f"({code_indicateur})."
            )
            return {}

        if not lignes_api:
            break

        for ligne in lignes_api:
            if not isinstance(ligne, dict):
                continue

            iso3 = convertir_m49_vers_iso3(
                ligne.get("DIM_GEO_CODE_M49")
            )

            if iso3 is None:
                continue

            try:
                annee = int(
                    ligne.get("DIM_TIME", "")
                )
            except (TypeError, ValueError):
                continue

            if (
                annee < 2000
                or annee > ANNEE_ACTUELLE
            ):
                continue

            valeur = extraire_valeur_oms(
                ligne
            )

            if valeur is None:
                continue

            cle = (iso3, annee)
            est_totale = ligne_oms_est_totale(
                ligne
            )

            precedente = resultat_temporaire.get(
                cle
            )

            if (
                precedente is None
                or (
                    est_totale
                    and not precedente[0]
                )
            ):
                resultat_temporaire[cle] = (
                    est_totale,
                    valeur,
                )

        if len(lignes_api) < TAILLE_PAGE_OMS:
            break

        position += TAILLE_PAGE_OMS

    resultat = {}

    for (
        iso3,
        annee,
    ), (
        _est_totale,
        valeur,
    ) in resultat_temporaire.items():
        resultat.setdefault(
            iso3,
            {},
        )[annee] = valeur

    return resultat


def actualiser_oms(colonnes, lignes):
    """
    Met à jour les quatre colonnes OMS.
    """
    total = 0

    for colonne, code_indicateur in (
        INDICATEURS_OMS.items()
    ):
        print(
            f"OMS : {colonne} "
            f"({code_indicateur})..."
        )

        series = telecharger_indicateur_oms(
            code_indicateur
        )

        total += inscrire_series_dans_lignes(
            lignes,
            colonne,
            series,
        )

        enregistrer_nouvelles_sources(
            colonnes,
            lignes,
        )

    return total


# ============================================================================
# REPORTERS SANS FRONTIÈRES
# ============================================================================

def charger_series_rsf():
    """
    Lit le fichier local RSF.csv placé dans documents_sources.

    Colonnes attendues :
    - Code : code ISO alpha-3 du pays ;
    - Year : année ;
    - Press Freedom Index : score RSF.

    Retourne un dictionnaire :
    {
        "FRA": {
            2020: 22.92,
            2021: 23.13,
        },
        ...
    }
    """
    if not FICHIER_RSF.exists():
        print(
            "Fichier RSF introuvable :",
            FICHIER_RSF,
        )
        return {}

    resultat = {}

    with FICHIER_RSF.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as fichier:
        lecteur = csv.DictReader(fichier)
        colonnes = lecteur.fieldnames or []

        colonnes_obligatoires = {
            "Code",
            "Year",
            "Press Freedom Index",
        }

        colonnes_absentes = (
            colonnes_obligatoires - set(colonnes)
        )

        if colonnes_absentes:
            raise RuntimeError(
                f"{FICHIER_RSF.name} ne contient pas "
                "les colonnes obligatoires : "
                + ", ".join(sorted(colonnes_absentes))
            )

        for ligne in lecteur:
            iso3 = str(
                ligne.get("Code", "")
            ).strip().upper()

            if len(iso3) != 3:
                continue

            try:
                annee = int(
                    ligne.get("Year", "")
                )
            except (TypeError, ValueError):
                continue

            if annee > ANNEE_ACTUELLE:
                continue

            valeur = convertir_nombre(
                ligne.get("Press Freedom Index")
            )

            if valeur is None:
                continue

            resultat.setdefault(
                iso3,
                {},
            )[annee] = valeur

    return resultat


def actualiser_rsf(colonnes, lignes):
    """
    Met à jour la colonne liberte_presse à partir de RSF.csv.

    Les années historiques exactes sont inscrites lorsqu'elles
    existent. Pour la ligne 2026, la dernière valeur disponible
    de chaque pays est utilisée.
    """
    print("RSF : liberte_presse...")

    series = charger_series_rsf()

    total = inscrire_series_dans_lignes(
        lignes,
        "liberte_presse",
        series,
    )

    enregistrer_nouvelles_sources(
        colonnes,
        lignes,
    )

    return total



# ============================================================================
# WOAH
# ============================================================================

ALIASES_PAYS_WOAH = {
    'afrique du sud': 'ZAF',
    'algerie': 'DZA',
    'allemagne': 'DEU',
    'arabie saoudite': 'SAU',
    'argentine': 'ARG',
    'australie': 'AUS',
    'autriche': 'AUT',
    'belgique': 'BEL',
    'bresil': 'BRA',
    'brunei': 'BRN',
    'bulgarie': 'BGR',
    'cameroun': 'CMR',
    'canada': 'CAN',
    'centrafricaine rep': 'CAF',
    'ceuta': 'ESP',
    'chili': 'CHL',
    'chine': 'CHN',
    'chine rep populaire de': 'CHN',
    'colombie': 'COL',
    'congo rep dem du': 'COD',
    'congo rep du': 'COG',
    'coree du nord': 'PRK',
    'coree du sud': 'KOR',
    'coree rep de': 'KOR',
    'coree rep pop dem de': 'PRK',
    'cote d ivoire': 'CIV',
    'croatie': 'HRV',
    'danemark': 'DNK',
    'dominicaine rep': 'DOM',
    'egypte': 'EGY',
    'espagne': 'ESP',
    'estonie': 'EST',
    'etats unis': 'USA',
    'etats unis d amerique': 'USA',
    'ethiopie': 'ETH',
    'federation de russie': 'RUS',
    'feroe iles': 'FRO',
    'finlande': 'FIN',
    'france': 'FRA',
    'grece': 'GRC',
    'hongrie': 'HUN',
    'iles falkland malvinas': 'FLK',
    'iles heard et mcdonald': 'HMD',
    'inde': 'IND',
    'indonesie': 'IDN',
    'iran': 'IRN',
    'iraq': 'IRQ',
    'irlande': 'IRL',
    'islande': 'ISL',
    'israel': 'ISR',
    'italie': 'ITA',
    'japon': 'JPN',
    'kazakhstan': 'KAZ',
    'kenya': 'KEN',
    'liban': 'LBN',
    'luxembourg': 'LUX',
    'maroc': 'MAR',
    'melilla': 'ESP',
    'mexique': 'MEX',
    'norvege': 'NOR',
    'nouvelle zelande': 'NZL',
    'palestine': 'PSE',
    'pays bas': 'NLD',
    'perou': 'PER',
    'pologne': 'POL',
    'portugal': 'PRT',
    'republique democratique du congo': 'COD',
    'republique du congo': 'COG',
    'republique tcheque': 'CZE',
    'roumanie': 'ROU',
    'royaume uni': 'GBR',
    'russie': 'RUS',
    'samoa occidental': 'WSM',
    'senegal': 'SEN',
    'serbie': 'SRB',
    'slovaquie': 'SVK',
    'slovenie': 'SVN',
    'suede': 'SWE',
    'suisse': 'CHE',
    'taipei chinois': 'TWN',
    'tcheque rep': 'CZE',
    'tunisie': 'TUN',
    'turkiye rep de': 'TUR',
    'turquie': 'TUR',
    'ukraine': 'UKR',
    'viet nam': 'VNM',
    'vietnam': 'VNM',
}


def normaliser_nom_pays(valeur):
    """
    Normalise un nom de pays pour faciliter les correspondances.
    """
    import unicodedata

    texte = str(valeur or "").strip().lower()

    texte = "".join(
        caractere
        for caractere in unicodedata.normalize("NFD", texte)
        if unicodedata.category(caractere) != "Mn"
    )

    for caractere in ("'", "’", "-", "(", ")", ",", "."):
        texte = texte.replace(caractere, " ")

    return " ".join(texte.split())


def construire_correspondance_pays_woah():
    """
    Construit une table nom de pays -> code ISO3.

    Les alias intégrés couvrent les principaux libellés français.
    Si pycountry est installé, ses traductions françaises complètent
    automatiquement la table pour la quasi-totalité des pays.
    """
    correspondance = dict(ALIASES_PAYS_WOAH)

    try:
        import gettext
        import pycountry

        traduction = gettext.translation(
            "iso3166-1",
            pycountry.LOCALES_DIR,
            languages=["fr"],
            fallback=True,
        )

        for pays in pycountry.countries:
            noms = {
                pays.name,
                getattr(pays, "official_name", ""),
                getattr(pays, "common_name", ""),
                traduction.gettext(pays.name),
                traduction.gettext(
                    getattr(pays, "official_name", "")
                ),
                traduction.gettext(
                    getattr(pays, "common_name", "")
                ),
            }

            for nom in noms:
                nom_normalise = normaliser_nom_pays(nom)

                if nom_normalise:
                    correspondance[nom_normalise] = pays.alpha_3

    except (ImportError, OSError):
        print(
            "Information : pycountry n'est pas installé. "
            "Les alias WOAH intégrés seront utilisés."
        )

    return correspondance


def convertir_nombre_woah(valeur):
    """
    Convertit une valeur WOAH en nombre.

    Les cellules vides, tirets et valeurs non numériques donnent 0.
    Les espaces de milliers et virgules décimales sont acceptés.
    """
    if valeur is None:
        return 0.0

    texte = str(valeur).strip()

    if texte in ("", "-", "—", "–", "NA", "N/A"):
        return 0.0

    texte = texte.replace("\u202f", "")
    texte = texte.replace("\xa0", "")
    texte = texte.replace(" ", "")
    texte = texte.replace(",", ".")

    try:
        return float(texte)
    except ValueError:
        return 0.0


def charger_series_woah():
    """
    Lit WOAH.csv une seule fois et calcule trois séries annuelles :

    - maladies_animales :
      somme des nouveaux foyers déclarés ;

    - vaccination_animale :
      100 × somme(Vaccinés) / somme(Sensibles),
      uniquement lorsque le total des animaux sensibles est positif,
      avec un résultat borné entre 0 et 100 ;

    - faune_sauvage :
      somme des cas et des nouveaux foyers pour les lignes dont
      la catégorie animale est « Sauvage ».

    Retourne un dictionnaire contenant les trois séries.
    """
    if not FICHIER_WOAH.exists():
        print(
            "Fichier WOAH introuvable :",
            FICHIER_WOAH,
        )
        return {
            "maladies_animales": {},
            "vaccination_animale": {},
            "faune_sauvage": {},
        }

    correspondance_pays = (
        construire_correspondance_pays_woah()
    )

    agregats = {}
    pays_non_reconnus = set()

    with FICHIER_WOAH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as fichier:
        lecteur = csv.DictReader(fichier)
        colonnes = lecteur.fieldnames or []

        colonnes_obligatoires = {
            "Pays",
            "Année",
            "Catégorie animale",
            "Nouveaux foyers",
            "Sensibles",
            "Cas",
            "Vaccinés",
        }

        colonnes_absentes = (
            colonnes_obligatoires - set(colonnes)
        )

        if colonnes_absentes:
            raise RuntimeError(
                f"{FICHIER_WOAH.name} ne contient pas "
                "les colonnes obligatoires : "
                + ", ".join(sorted(colonnes_absentes))
            )

        for ligne in lecteur:
            nom_pays = str(
                ligne.get("Pays", "")
            ).strip()

            nom_normalise = normaliser_nom_pays(
                nom_pays
            )

            iso3 = correspondance_pays.get(
                nom_normalise
            )

            if not iso3:
                if nom_pays:
                    pays_non_reconnus.add(nom_pays)
                continue

            try:
                annee = int(
                    ligne.get("Année", "")
                )
            except (TypeError, ValueError):
                continue

            if annee > ANNEE_ACTUELLE:
                continue

            cle = (iso3, annee)

            valeurs = agregats.setdefault(
                cle,
                {
                    "nouveaux_foyers": 0.0,
                    "sensibles": 0.0,
                    "vaccines": 0.0,
                    "faune_cas": 0.0,
                    "faune_foyers": 0.0,
                },
            )

            nouveaux_foyers = convertir_nombre_woah(
                ligne.get("Nouveaux foyers")
            )
            sensibles = convertir_nombre_woah(
                ligne.get("Sensibles")
            )
            vaccines = convertir_nombre_woah(
                ligne.get("Vaccinés")
            )
            cas = convertir_nombre_woah(
                ligne.get("Cas")
            )

            valeurs["nouveaux_foyers"] += nouveaux_foyers

            # Le ratio est calculé sur les totaux déclarés.
            # Les valeurs nulles ou manquantes ont déjà été converties en 0.
            if sensibles > 0:
                valeurs["sensibles"] += sensibles
                valeurs["vaccines"] += max(vaccines, 0.0)

            categorie = normaliser_nom_pays(
                ligne.get("Catégorie animale", "")
            )

            if categorie == "sauvage":
                valeurs["faune_cas"] += cas
                valeurs["faune_foyers"] += nouveaux_foyers

    if pays_non_reconnus:
        exemples = ", ".join(
            sorted(pays_non_reconnus)[:10]
        )

        print(
            "Pays WOAH non reconnus :",
            exemples,
        )

        if len(pays_non_reconnus) > 10:
            print(
                "... et",
                len(pays_non_reconnus) - 10,
                "autres.",
            )

    series = {
        "maladies_animales": {},
        "vaccination_animale": {},
        "faune_sauvage": {},
    }

    for (iso3, annee), valeurs in agregats.items():
        series["maladies_animales"].setdefault(
            iso3,
            {},
        )[annee] = int(
            round(valeurs["nouveaux_foyers"])
        )

        total_sensibles = valeurs["sensibles"]

        if total_sensibles > 0:
            taux_vaccination = (
                100.0
                * valeurs["vaccines"]
                / total_sensibles
            )

            taux_vaccination = max(
                0.0,
                min(100.0, taux_vaccination),
            )

            series["vaccination_animale"].setdefault(
                iso3,
                {},
            )[annee] = round(
                taux_vaccination,
                2,
            )

        pression_faune = (
            valeurs["faune_cas"]
            + valeurs["faune_foyers"]
        )

        series["faune_sauvage"].setdefault(
            iso3,
            {},
        )[annee] = int(
            round(pression_faune)
        )

    return series


def actualiser_woah(colonnes, lignes):
    """
    Met à jour les trois indicateurs WOAH dans
    nouvelles_sources.csv.
    """
    print("WOAH : lecture du fichier et calcul des indicateurs...")

    series = charger_series_woah()
    total = 0

    for colonne in (
        "maladies_animales",
        "vaccination_animale",
        "faune_sauvage",
    ):
        print(f"WOAH : {colonne}...")

        total += inscrire_series_dans_lignes(
            lignes,
            colonne,
            series.get(colonne, {}),
        )

    enregistrer_nouvelles_sources(
        colonnes,
        lignes,
    )

    return total


# ============================================================================
# ACTUALISATION GÉNÉRALE
# ============================================================================

def actualiser_sources():
    """
    Actualise nouvelles_sources.csv avec les données disponibles
    de la Banque mondiale, de l'OMS et des fichiers locaux
    RSF et WOAH.

    Les colonnes non encore automatisées sont conservées
    sans modification.

    Le fichier indicateurs.csv n'est jamais modifié.
    """
    global CELLULES_PRIORITAIRES

    print("Chargement de nouvelles_sources.csv...")

    CELLULES_PRIORITAIRES = (
        charger_cellules_prioritaires()
    )

    print(
        "Cellules prioritaires protégées :",
        len(CELLULES_PRIORITAIRES),
    )

    colonnes, lignes = charger_nouvelles_sources()
    ajouter_colonnes_manquantes(colonnes, lignes)

    print("Actualisation Banque mondiale...")
    modifications_banque_mondiale = (
        actualiser_banque_mondiale(colonnes, lignes)
    )

    print("Actualisation OMS...")
    modifications_oms = actualiser_oms(colonnes, lignes)

    print("Actualisation RSF...")
    modifications_rsf = actualiser_rsf(
        colonnes,
        lignes,
    )

    print("Actualisation WOAH...")
    modifications_woah = actualiser_woah(
        colonnes,
        lignes,
    )

    enregistrer_nouvelles_sources(colonnes, lignes)

    total = (
        modifications_banque_mondiale
        + modifications_oms
        + modifications_rsf
        + modifications_woah
    )

    print("=" * 60)
    print("Actualisation terminée.")
    print(
        "Valeurs Banque mondiale écrites :",
        modifications_banque_mondiale,
    )
    print(
        "Valeurs OMS écrites :",
        modifications_oms,
    )
    print(
        "Valeurs RSF écrites :",
        modifications_rsf,
    )
    print(
        "Valeurs WOAH écrites :",
        modifications_woah,
    )
    print("Total des valeurs écrites :", total)
    print("Fichier :", FICHIER_NOUVELLES_SOURCES)
    print("=" * 60)

    return total


if __name__ == "__main__":
    actualiser_sources()