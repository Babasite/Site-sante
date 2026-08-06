from pathlib import Path

from playwright.sync_api import (
    Error as PlaywrightError,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)


BASE_DIR = Path(__file__).resolve().parents[1]

DOSSIER_DOCUMENTS = (
    BASE_DIR
    / "data"
    / "documents_sources"
)

FICHIER_WOAH = (
    DOSSIER_DOCUMENTS
    / "WOAH.csv"
)

URL_WAHIS = (
    "https://wahis.woah.org/"
    "#/dashboards/qd-dashboard"
)


def cliquer_premier_element_visible(
    page,
    selecteurs,
    timeout=1_500,
):
    """
    Clique sur le premier élément visible correspondant
    à l'un des sélecteurs fournis.

    Retourne True lorsqu'un clic a été effectué.
    """
    for selecteur in selecteurs:
        try:
            elements = page.locator(selecteur)
            nombre = elements.count()

            for index in range(nombre):
                element = elements.nth(index)

                if element.is_visible(timeout=timeout):
                    element.click(timeout=5_000)
                    page.wait_for_timeout(800)
                    return True

        except PlaywrightError:
            continue

    return False


def fermer_fenetres_bloquantes(page):
    """
    Ferme les fenêtres de cookies ou autres modales
    susceptibles de bloquer les clics dans WAHIS.
    """
    selecteurs_boutons = [
        'button:has-text("Tout accepter")',
        'button:has-text("Accepter tout")',
        'button:has-text("J’accepte")',
        'button:has-text("J\'accepte")',
        'button:has-text("Accepter")',
        'button:has-text("Je refuse")',
        'button:has-text("Refuser")',
        'button:has-text("Continuer sans accepter")',
        'button:has-text("Fermer")',
        '[aria-label="Fermer"]',
        '[aria-label="Close"]',
        '.btn-close',
        '.close',
    ]

    for _ in range(4):
        if not cliquer_premier_element_visible(
            page,
            selecteurs_boutons,
        ):
            break

    modale = page.locator(
        'ngb-modal-window[role="dialog"]'
    )

    try:
        if modale.count() and modale.first.is_visible(
            timeout=1_000
        ):
            page.keyboard.press("Escape")
            page.wait_for_timeout(800)
    except PlaywrightError:
        pass


def ouvrir_onglet_export(page):
    """
    Ouvre l'onglet « Exporter les données ».
    """
    fermer_fenetres_bloquantes(page)

    onglets = page.get_by_role(
        "button",
        name="Exporter les données",
        exact=True,
    )

    nombre = onglets.count()

    for index in range(nombre):
        onglet = onglets.nth(index)

        try:
            if not onglet.is_visible(timeout=2_000):
                continue

            onglet.click(timeout=15_000)
            page.wait_for_timeout(2_000)
            return

        except PlaywrightError:
            fermer_fenetres_bloquantes(page)

            try:
                onglet.click(
                    timeout=15_000,
                    force=True,
                )
                page.wait_for_timeout(2_000)
                return
            except PlaywrightError:
                continue

    raise RuntimeError(
        "L'onglet « Exporter les données » "
        "n'a pas pu être ouvert."
    )


def trouver_bouton_export(page):
    """
    Recherche le bouton visible qui déclenche réellement
    le téléchargement du fichier CSV.
    """
    candidats = [
        page.get_by_role(
            "button",
            name="Exporter les données",
            exact=True,
        ),
        page.locator(
            'button:has-text("Exporter les données")'
        ),
    ]

    elements_visibles = []

    for candidat in candidats:
        try:
            for index in range(candidat.count()):
                element = candidat.nth(index)

                if element.is_visible(timeout=1_500):
                    elements_visibles.append(element)

        except PlaywrightError:
            continue

    if not elements_visibles:
        raise RuntimeError(
            "Le bouton bleu « Exporter les données » "
            "n'a pas été trouvé."
        )

    return elements_visibles[-1]


def enregistrer_telechargement(
    telechargement,
) -> Path:
    """
    Enregistre le téléchargement sous le nom fixe WOAH.csv.

    L'ancien fichier n'est supprimé qu'après la réussite
    du nouveau téléchargement.
    """
    nom_suggere = (
        telechargement.suggested_filename
        or ""
    )

    extension = Path(nom_suggere).suffix.lower()

    if extension and extension != ".csv":
        raise RuntimeError(
            "Le fichier téléchargé n'est pas un CSV : "
            f"{nom_suggere}"
        )

    fichier_temporaire = (
        DOSSIER_DOCUMENTS
        / "WOAH_nouveau.csv"
    )

    if fichier_temporaire.exists():
        fichier_temporaire.unlink()

    telechargement.save_as(
        fichier_temporaire
    )

    if not fichier_temporaire.exists():
        raise RuntimeError(
            "Le fichier WOAH temporaire n'a pas été créé."
        )

    if fichier_temporaire.stat().st_size == 0:
        fichier_temporaire.unlink(
            missing_ok=True
        )
        raise RuntimeError(
            "Le fichier WOAH téléchargé est vide."
        )

    fichier_temporaire.replace(
        FICHIER_WOAH
    )

    return FICHIER_WOAH


def telecharger_woah() -> Path | None:
    """
    Ouvre WAHIS, met Playwright en pause pour récupérer
    le sélecteur exact de l'onglet d'export, puis poursuit
    le téléchargement sous le nom fixe WOAH.csv.
    """
    DOSSIER_DOCUMENTS.mkdir(
        parents=True,
        exist_ok=True,
    )

    with sync_playwright() as playwright:
        navigateur = playwright.chromium.launch(
            headless=False,
            slow_mo=150,
        )

        contexte = navigateur.new_context(
            accept_downloads=True,
            viewport={
                "width": 1600,
                "height": 900,
            },
        )

        page = contexte.new_page()

        try:
            print("Ouverture de WAHIS...")

            page.goto(
                URL_WAHIS,
                wait_until="domcontentloaded",
                timeout=120_000,
            )

            page.wait_for_timeout(6_000)

            print(
                "L'inspecteur Playwright va s'ouvrir."
            )
            print(
                "Utilise Pick locator puis clique sur "
                "« Exporter les données »."
            )

            page.pause()

            fermer_fenetres_bloquantes(page)
            ouvrir_onglet_export(page)

            print()
            print("=" * 60)
            print("WAHIS est ouvert dans le navigateur.")
            print()
            print(
                "1. Laisse les filtres vides pour "
                "télécharger l'export global."
            )
            print(
                "2. Ne clique pas sur le bouton bleu "
                "« Exporter les données »."
            )
            print(
                "3. Reviens dans le terminal et "
                "appuie sur Entrée."
            )
            print("=" * 60)

            input(
                "Appuie sur Entrée lorsque l'export "
                "est prêt..."
            )

            fermer_fenetres_bloquantes(page)
            bouton_export = trouver_bouton_export(page)

            print("Téléchargement du fichier WOAH...")

            with page.expect_download(
                timeout=180_000,
            ) as attente_telechargement:
                try:
                    bouton_export.click(
                        timeout=20_000
                    )
                except PlaywrightError:
                    fermer_fenetres_bloquantes(page)
                    bouton_export.click(
                        timeout=20_000,
                        force=True,
                    )

            telechargement = (
                attente_telechargement.value
            )

            chemin_destination = (
                enregistrer_telechargement(
                    telechargement
                )
            )

            print()
            print("=" * 60)
            print("Téléchargement terminé.")
            print(
                "Le fichier précédent a été remplacé."
            )
            print("Fichier :", chemin_destination)
            print("=" * 60)

            return chemin_destination

        except PlaywrightTimeoutError as erreur:
            print(
                "WAHIS n'a pas répondu dans le délai "
                "prévu :",
                erreur,
            )
            return None

        except (
            PlaywrightError,
            RuntimeError,
            OSError,
        ) as erreur:
            print(
                "Le téléchargement WOAH a échoué :",
                erreur,
            )
            return None

        finally:
            contexte.close()
            navigateur.close()


if __name__ == "__main__":
    telecharger_woah()