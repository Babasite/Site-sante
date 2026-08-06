from pathlib import Path
from PIL import Image

RACINE = Path(__file__).resolve().parents[2]

EXTENSIONS = {".png", ".jpg", ".jpeg"}

DOSSIERS = [
    RACINE / "accueil/static",
    RACINE / "apps/pays/static",
]

converties = 0
ignorees = 0
erreurs = 0

for dossier in DOSSIERS:
    for fichier in dossier.rglob("*"):

        if fichier.suffix.lower() not in EXTENSIONS:
            continue

        sortie = fichier.with_suffix(".webp")

        if sortie.exists():
            ignorees += 1
            continue

        try:
            with Image.open(fichier) as im:

                if im.mode not in ("RGB", "RGBA"):
                    im = im.convert("RGBA")

                im.save(
                    sortie,
                    "WEBP",
                    quality=85,
                    method=6,
                )

            converties += 1
            print(f"✔ {fichier.relative_to(RACINE)}")

        except Exception as e:
            erreurs += 1
            print(f"✖ {fichier.relative_to(RACINE)} : {e}")

print()
print(f"Converties : {converties}")
print(f"Ignorées   : {ignorees}")
print(f"Erreurs    : {erreurs}")