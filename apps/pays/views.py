import json
from pathlib import Path

from django.contrib.staticfiles import finders
from django.http import Http404
from django.shortcuts import render

from .services.graphique import calculer_graphique_pays
from .services.spt import calculer_note_spt


BASE_DIR = Path(__file__).resolve().parent


def charger_json(chemin: Path) -> dict:
    """
    Charge un fichier JSON et retourne son contenu.

    Lève une erreur 404 si le fichier n'existe pas
    et une RuntimeError si le JSON est invalide.
    """
    if not chemin.exists():
        raise Http404(f"Fichier introuvable : {chemin}")

    try:
        with chemin.open("r", encoding="utf-8-sig") as fichier:
            return json.load(fichier)

    except json.JSONDecodeError as erreur:
        raise RuntimeError(
            f"Le fichier {chemin} contient un JSON invalide "
            f"à la ligne {erreur.lineno}, colonne {erreur.colno} : "
            f"{erreur.msg}"
        ) from erreur


def trouver_image_espece(identifiant: str) -> str | None:
    """
    Recherche une image portant le nom de l'identifiant de l'espèce.

    Exemple :
        apps/pays/static/images/moustique_tigre.png

    Formats acceptés :
        .png, .webp, .jpg et .jpeg

    Retourne le chemin utilisable avec la balise Django {% static %}
    ou None lorsqu'aucune image n'est disponible.
    """
    for extension in ("png", "webp", "jpg", "jpeg"):
        chemin_static = f"images/{identifiant}.{extension}"

        if finders.find(chemin_static):
            return chemin_static

    return None


def fiche_pays(request, slug):
    chemin_pays = BASE_DIR / "data" / "pays" / f"{slug}.json"
    chemin_pays_json = BASE_DIR / "data" / "pays.json"
    chemin_drapeaux = BASE_DIR / "data" / "drapeaux.json"

    chemin_catalogue_especes = (
        BASE_DIR
        / "data"
        / "especes_sentinelles_catalogue.json"
    )

    chemin_especes = (
        BASE_DIR
        / "data"
        / "especes_sentinelles.json"
    )

    # ------------------------------------------------------------------
    # Chargement des données du pays
    # ------------------------------------------------------------------

    if chemin_pays.exists():
        pays_data = charger_json(chemin_pays).copy()

    else:
        tous_les_pays = charger_json(chemin_pays_json)

        if slug not in tous_les_pays:
            raise Http404(f"Pays introuvable : {slug}")

        pays_data = tous_les_pays[slug].copy()

    # ------------------------------------------------------------------
    # Chargement des autres fichiers JSON
    # ------------------------------------------------------------------

    drapeaux = charger_json(chemin_drapeaux)

    catalogue_brut = charger_json(
        chemin_catalogue_especes
    )

    especes = charger_json(
        chemin_especes
    )

    # ------------------------------------------------------------------
    # Informations générales du pays
    # ------------------------------------------------------------------

    code = pays_data.get("code", "").strip().lower()

    if not code:
        raise RuntimeError(
            f"Le pays '{slug}' ne contient pas la clé 'code'."
        )

    reference = drapeaux.get(code)

    if reference is None:
        raise RuntimeError(
            f"Le code pays '{code}' est absent de drapeaux.json."
        )

    pays_data["nom"] = reference.get(
        "name",
        pays_data.get("nom", slug)
    )

    pays_data["drapeau_url"] = (
        f"https://flagcdn.com/w80/{code}.png"
    )

    # ------------------------------------------------------------------
    # Espèces sentinelles
    # ------------------------------------------------------------------

    catalogue = {
        espece["id"]: espece
        for espece in catalogue_brut.get("catalogue", [])
        if "id" in espece
    }

    identifiants = especes.get(code, [])

    especes_sentinelles = []

    for id_espece in identifiants:
        if id_espece not in catalogue:
            continue

        # Copie pour ne pas modifier directement le catalogue chargé.
        espece = catalogue[id_espece].copy()

        # Exemple de valeur obtenue :
        # "images/moustique_tigre.png"
        # Si le fichier n'existe pas, la valeur reste None et le template
        # affiche automatiquement l'emoji.
        espece["image"] = trouver_image_espece(id_espece)

        especes_sentinelles.append(espece)

    pays_data["especes_sentinelles"] = especes_sentinelles

    # ------------------------------------------------------------------
    # Calcul des notes SPT
    # ------------------------------------------------------------------

    notes_spt = calculer_note_spt(code)

    if notes_spt is None:
        notes_spt = {
            "note_sante_humaine": None,
            "note_sante_animale": None,
            "note_ecosysteme": None,
            "note_information_prevention": None,
            "note_spt_affichage": None,
            "note_spt": None,
            "note_finale": None,
            "indicateurs_sante_humaine": {},
            "indicateurs_sante_animale": {},
            "indicateurs_ecosysteme": {},
            "indicateurs_information_prevention": {},
            "valeurs_brutes": {},
        }

    pays_data.update(notes_spt)

    # ------------------------------------------------------------------
    # Graphique historique
    # ------------------------------------------------------------------

    graphique = calculer_graphique_pays(code)

    if graphique is None:
        graphique = {
            "annees": [2000, 2010, 2020, 2026],
            "sante_humaine": [],
            "sante_animale": [],
            "ecosysteme": [],
            "information_prevention": [],
        }

    # ------------------------------------------------------------------
    # Contexte envoyé au template
    # ------------------------------------------------------------------

    contexte = {
        "pays_data": pays_data,
        "graphique": graphique,
        **notes_spt,
    }

    # ------------------------------------------------------------------
    # Débogage temporaire
    # ------------------------------------------------------------------

    print("=" * 60)
    print("Slug :", slug)
    print("Code :", code)
    print("Référence :", reference)
    print("Notes SPT :", notes_spt)
    print("Graphique :", graphique)
    print("=" * 60)

    return render(
        request,
        "accueil/Pays/pays.html",
        contexte,
    )