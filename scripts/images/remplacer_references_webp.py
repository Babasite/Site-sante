from pathlib import Path
import re


RACINE = Path(__file__).resolve().parents[2]

DOSSIERS_A_ANALYSER = [
    RACINE / "accueil",
    RACINE / "apps",
    RACINE / "templates",
    RACINE / "static",
]

DOSSIERS_IMAGES = [
    RACINE / "accueil/static",
    RACINE / "apps/pays/static",
]

EXTENSIONS_FICHIERS = {
    ".html",
    ".css",
    ".js",
    ".json",
    ".py",
}

# Détecte les chemins terminant par .png, .jpg ou .jpeg.
# Les URL commençant par http:// ou https:// seront laissées intactes.
MOTIF_IMAGE = re.compile(
    r"(?P<chemin>(?:https?://)?[A-Za-z0-9_./\\-]+)"
    r"\.(?P<extension>png|jpe?g)\b",
    re.IGNORECASE,
)


def construire_alias_webp():
    """
    Construit la liste des chemins pour lesquels un fichier WebP existe.
    Plusieurs formes sont reconnues :
    - accueil/images/logo
    - accueil/static/accueil/images/logo
    - images/hippopotame
    - apps/pays/static/images/hippopotame
    """
    alias = set()
    noms_simples = {}

    for dossier_images in DOSSIERS_IMAGES:
        if not dossier_images.exists():
            continue

        for webp in dossier_images.rglob("*.webp"):
            chemin_absolu_sans_extension = webp.with_suffix("")

            # Chemin relatif à la racine du dépôt.
            alias.add(chemin_absolu_sans_extension.as_posix())

            # Chemin relatif au dossier static.
            try:
                alias.add(
                    chemin_absolu_sans_extension
                    .relative_to(dossier_images)
                    .as_posix()
                )
            except ValueError:
                pass

            # Nom simple (uniquement s'il est unique).
            nom_simple = webp.stem
            noms_simples.setdefault(nom_simple, 0)
            noms_simples[nom_simple] += 1

    for nom_simple, nombre in noms_simples.items():
        if nombre == 1:
            alias.add(nom_simple)

    return alias


def remplacer_dans_fichier(fichier, alias_webp):
    try:
        contenu = fichier.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print(f"IGNORÉ (encodage non UTF-8) : {fichier}")
        return 0

    compteur = 0

    def remplacer(correspondance):
        nonlocal compteur

        chemin_original = correspondance.group("chemin")

        # Ne jamais modifier les images provenant d'un site externe.
        if chemin_original.lower().startswith(("http://", "https://")):
            return correspondance.group(0)

        chemin_normalise = (
            chemin_original
            .replace("\\", "/")
            .lstrip("./")
            .lstrip("/")
        )

        candidats = {
            chemin_normalise,
            Path(chemin_normalise).name,
        }

        if not any(candidat in alias_webp for candidat in candidats):
            return correspondance.group(0)

        compteur += 1
        return f"{chemin_original}.webp"

    nouveau_contenu = MOTIF_IMAGE.sub(remplacer, contenu)

    if nouveau_contenu != contenu:
        fichier.write_text(nouveau_contenu, encoding="utf-8")

    return compteur


def main():
    alias_webp = construire_alias_webp()

    fichiers_modifies = 0
    references_remplacees = 0

    for dossier in DOSSIERS_A_ANALYSER:
        if not dossier.exists():
            continue

        for fichier in dossier.rglob("*"):
            if not fichier.is_file():
                continue

            if fichier.suffix.lower() not in EXTENSIONS_FICHIERS:
                continue

            nombre = remplacer_dans_fichier(
                fichier,
                alias_webp,
            )

            if nombre:
                fichiers_modifies += 1
                references_remplacees += nombre
                print(
                    f"OK {fichier} : "
                    f"{nombre} remplacement(s)"
                )

    print()
    print(f"Fichiers modifiés      : {fichiers_modifies}")
    print(f"Références remplacées  : {references_remplacees}")


if __name__ == "__main__":
    main()