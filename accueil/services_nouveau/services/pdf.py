from io import BytesIO
from pathlib import Path

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


COULEUR_PRINCIPALE = colors.HexColor("#00695C")
COULEUR_SECONDAIRE = colors.HexColor("#003366")
COULEUR_FOND = colors.HexColor("#F4F8FC")
COULEUR_CONVERGENCE = colors.HexColor("#F5FBF7")
COULEUR_BORDURE = colors.HexColor("#D9E1E5")
COULEUR_TEXTE_SECONDAIRE = colors.HexColor("#5F6B73")

NOMBRE_MAX_ARTICLES = 7
LARGEUR_CONTENU = 17.0 * cm


def generer_pdf_veille(veille):
    """
    Génère le PDF d'une veille quotidienne enregistrée.

    Retourne le contenu du PDF sous forme d'octets.
    """
    tampon = BytesIO()

    document = BaseDocTemplate(
        tampon,
        pagesize=A4,
        rightMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        topMargin=2.3 * cm,
        bottomMargin=2.1 * cm,
        title="Veille scientifique",
        author="Santé+",
    )

    largeur_page, hauteur_page = A4

    cadre = Frame(
        document.leftMargin,
        document.bottomMargin,
        document.width,
        document.height,
        id="cadre_principal",
    )

    modele_page = PageTemplate(
        id="modele_veille",
        frames=[cadre],
        onPage=_dessiner_entete_et_pied,
    )

    document.addPageTemplates([modele_page])

    styles = _creer_styles()
    elements = []

    _ajouter_en_tete_document(
        elements=elements,
        veille=veille,
        styles=styles,
    )

    _ajouter_resume(
        elements=elements,
        veille=veille,
        styles=styles,
    )

    _ajouter_convergence(
        elements=elements,
        veille=veille,
        styles=styles,
    )

    _ajouter_statistiques(
        elements=elements,
        veille=veille,
        styles=styles,
    )

    _ajouter_articles(
        elements=elements,
        veille=veille,
        styles=styles,
        largeur_disponible=document.width,
    )

    document.build(elements)

    contenu = tampon.getvalue()
    tampon.close()

    return contenu


def _creer_styles():
    """
    Crée les styles typographiques utilisés dans le rapport.
    """
    styles_base = getSampleStyleSheet()

    return {
        "titre": ParagraphStyle(
            "TitreVeille",
            parent=styles_base["Title"],
            fontName="Helvetica-Bold",
            fontSize=23,
            leading=28,
            textColor=COULEUR_SECONDAIRE,
            alignment=TA_LEFT,
            spaceAfter=7,
        ),
        "date": ParagraphStyle(
            "DateVeille",
            parent=styles_base["Normal"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=14,
            textColor=COULEUR_TEXTE_SECONDAIRE,
            spaceAfter=17,
        ),
        "section": ParagraphStyle(
            "TitreSection",
            parent=styles_base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            textColor=COULEUR_PRINCIPALE,
            spaceBefore=10,
            spaceAfter=10,
        ),
        "corps": ParagraphStyle(
            "Corps",
            parent=styles_base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=colors.HexColor("#30363A"),
            alignment=TA_LEFT,
        ),
        "resume_executif": ParagraphStyle(
            "ResumeExecutif",
            parent=styles_base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=colors.HexColor("#30363A"),
            alignment=TA_LEFT,
            backColor=COULEUR_FOND,
            borderColor=colors.HexColor("#0B6EFD"),
            borderWidth=1,
            borderPadding=12,
            spaceAfter=13,
        ),
        "convergence": ParagraphStyle(
            "Convergence",
            parent=styles_base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=colors.HexColor("#30363A"),
            alignment=TA_LEFT,
            backColor=COULEUR_CONVERGENCE,
            borderColor=colors.HexColor("#198754"),
            borderWidth=1,
            borderPadding=12,
            spaceAfter=13,
        ),
        "traduction_manuelle": ParagraphStyle(
            "TraductionManuelle",
            parent=styles_base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=colors.HexColor("#30363A"),
            alignment=TA_LEFT,
            backColor=colors.HexColor("#F8F5FC"),
            borderColor=colors.HexColor("#6F42C1"),
            borderWidth=1,
            borderPadding=10,
            spaceBefore=7,
            spaceAfter=7,
        ),
        "titre_article": ParagraphStyle(
            "TitreArticle",
            parent=styles_base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=12.5,
            leading=16,
            textColor=COULEUR_SECONDAIRE,
            spaceAfter=7,
        ),
        "meta": ParagraphStyle(
            "MetaArticle",
            parent=styles_base["Normal"],
            fontName="Helvetica",
            fontSize=8.8,
            leading=12,
            textColor=COULEUR_TEXTE_SECONDAIRE,
            spaceAfter=4,
        ),
        "lien": ParagraphStyle(
            "LienArticle",
            parent=styles_base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#0B6EFD"),
            spaceBefore=6,
        ),
        "pied": ParagraphStyle(
            "PiedDocument",
            parent=styles_base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=COULEUR_TEXTE_SECONDAIRE,
            alignment=TA_CENTER,
        ),
    }


def _ajouter_en_tete_document(elements, veille, styles):
    """
    Ajoute le logo, le titre et la date de la veille.
    """
    logo = _charger_logo()

    if logo is not None:
        tableau_entete = Table(
            [
                [
                    logo,
                    Paragraph(
                        "VEILLE SCIENTIFIQUE",
                        styles["titre"],
                    ),
                ]
            ],
            colWidths=[3.2 * cm, 13.4 * cm],
        )

        tableau_entete.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )

        elements.append(tableau_entete)

    else:
        elements.append(
            Paragraph(
                "VEILLE SCIENTIFIQUE",
                styles["titre"],
            )
        )

    date_texte = veille.date_creation.strftime(
        "Veille du %d/%m/%Y à %H:%M"
    )

    elements.append(
        Paragraph(
            _echapper(date_texte),
            styles["date"],
        )
    )

    elements.append(
        Table(
            [[""]],
            colWidths=[17.4 * cm],
            rowHeights=[1],
            style=TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        COULEUR_PRINCIPALE,
                    )
                ]
            ),
        )
    )

    elements.append(Spacer(1, 16))


def _ajouter_resume(elements, veille, styles):
    """
    Ajoute le résumé exécutif.

    Le texte est placé dans un Paragraph plutôt que dans un tableau.
    ReportLab peut ainsi commencer le résumé sur la page courante,
    puis le poursuivre automatiquement sur la page suivante.
    """
    elements.append(
        Paragraph(
            "Résumé exécutif",
            styles["section"],
        )
    )

    resume = (
        veille.resume_affiche
        or "Aucun résumé n'est disponible pour cette veille."
    )

    elements.append(
        Paragraph(
            _texte_vers_html(resume),
            styles["resume_executif"],
        )
    )


def _ajouter_convergence(elements, veille, styles):
    """
    Ajoute les convergences uniquement lorsqu'elles existent.

    Comme le résumé exécutif, ce bloc peut se poursuivre
    naturellement sur la page suivante s'il est trop long.
    """
    convergence = (veille.convergence or "").strip()

    if not convergence:
        return

    elements.append(
        Paragraph(
            "Convergence des sources",
            styles["section"],
        )
    )

    elements.append(
        Paragraph(
            _texte_vers_html(convergence),
            styles["convergence"],
        )
    )


def _ajouter_statistiques(elements, veille, styles):
    """
    Ajoute le tableau récapitulatif de la collecte.
    """
    elements.append(
        Paragraph(
            "Tableau de la veille",
            styles["section"],
        )
    )

    donnees = [
        [
            Paragraph("<b>Indicateur</b>", styles["corps"]),
            Paragraph("<b>Valeur</b>", styles["corps"]),
        ],
        [
            Paragraph("Sources interrogées", styles["corps"]),
            Paragraph(
                str(veille.sources_interrogees),
                styles["corps"],
            ),
        ],
        [
            Paragraph("Articles récupérés", styles["corps"]),
            Paragraph(
                str(veille.articles_recuperes),
                styles["corps"],
            ),
        ],
        [
            Paragraph("Articles retenus", styles["corps"]),
            Paragraph(
                str(veille.nombre_articles),
                styles["corps"],
            ),
        ],
        [
            Paragraph("Doublons supprimés", styles["corps"]),
            Paragraph(
                str(veille.doublons_supprimes),
                styles["corps"],
            ),
        ],
        [
            Paragraph("Durée totale", styles["corps"]),
            Paragraph(
                f"{veille.duree_secondes:.1f} seconde(s)",
                styles["corps"],
            ),
        ],
    ]

    tableau = Table(
        donnees,
        colWidths=[11.2 * cm, 5.8 * cm],
        repeatRows=1,
    )

    tableau.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    COULEUR_PRINCIPALE,
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.6,
                    COULEUR_BORDURE,
                ),
                (
                    "BACKGROUND",
                    (0, 1),
                    (-1, -1),
                    colors.white,
                ),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    elements.append(tableau)
    elements.append(Spacer(1, 18))


def _ajouter_articles(
    elements,
    veille,
    styles,
    largeur_disponible,
):
    """
    Ajoute les publications retenues.

    Règles d'affichage :
    - sept publications au maximum ;
    - titre manuel lorsqu'une traduction manuelle est publiée ;
    - aucune reprise du résumé automatique ;
    - traduction manuelle complète uniquement lorsqu'elle est publiée ;
    - catégories, One Health, niveau de preuve et importance affichés ;
    - lien original conservé.
    """
    elements.append(
        Paragraph(
            "Publications retenues",
            styles["section"],
        )
    )

    articles = (
        veille.articles
        .all()
        .order_by("ordre", "-score")[:NOMBRE_MAX_ARTICLES]
    )

    if not articles:
        elements.append(
            Paragraph(
                "Aucune publication n'a été enregistrée.",
                styles["corps"],
            )
        )
        return

    for numero, article in enumerate(articles, start=1):
        _ajouter_une_publication(
            elements=elements,
            article=article,
            numero=numero,
            styles=styles,
            largeur_disponible=largeur_disponible,
        )


def _ajouter_une_publication(
    elements,
    article,
    numero,
    styles,
    largeur_disponible,
):
    """
    Construit une publication de manière lisible et indépendante.
    """
    titre = _titre_article_a_afficher(article)

    elements.append(
        Paragraph(
            _echapper(f"{numero}. {titre}"),
            styles["titre_article"],
        )
    )

    _ajouter_meta_article(
        elements,
        "Source",
        getattr(article, "source", ""),
        styles,
    )

    if getattr(article, "date_publication", None):
        _ajouter_meta_article(
            elements,
            "Date",
            article.date_publication,
            styles,
        )

    _ajouter_liste_meta(
        elements,
        "Catégories",
        getattr(article, "categories", None),
        styles,
    )

    _ajouter_liste_meta(
        elements,
        "One Health",
        getattr(article, "one_health", None),
        styles,
    )

    preuve = getattr(article, "preuve", "")
    if preuve and preuve != "Non déterminé":
        _ajouter_meta_article(
            elements,
            "Niveau de preuve",
            preuve,
            styles,
        )

    importance = getattr(article, "niveau_importance", "")
    if importance:
        _ajouter_meta_article(
            elements,
            "Importance",
            importance,
            styles,
        )

    traduction = _traduction_manuelle_publiee(article)
    if traduction:
        elements.append(Spacer(1, 5))
        elements.append(
            Paragraph(
                "<b>Traduction manuelle publiée</b><br/>"
                + _texte_vers_html(traduction),
                styles["traduction_manuelle"],
            )
        )

    elements.append(
        Paragraph(
            _creer_lien_cliquable(getattr(article, "lien", "")),
            styles["lien"],
        )
    )

    _ajouter_separateur_article(
        elements,
        largeur_disponible,
    )


def _titre_article_a_afficher(article):
    """
    Retourne le titre manuel publié, sinon le titre habituel.
    """
    traduction_publiee = getattr(
        article,
        "traduction_manuelle_publiee",
        False,
    )

    titre_manuel = (
        getattr(article, "titre_traduit_manuel", "")
        or ""
    ).strip()

    if traduction_publiee and titre_manuel:
        return titre_manuel

    return (
        getattr(article, "titre_affiche", "")
        or getattr(article, "titre", "")
        or "Publication sans titre"
    )


def _traduction_manuelle_publiee(article):
    """
    Retourne uniquement la traduction manuelle explicitement publiée.
    """
    if not getattr(
        article,
        "traduction_manuelle_publiee",
        False,
    ):
        return ""

    return (
        getattr(article, "resume_traduit_manuel", "")
        or ""
    ).strip()


def _ajouter_meta_article(
    elements,
    libelle,
    valeur,
    styles,
):
    """
    Ajoute une ligne de métadonnée à une publication.
    """
    valeur = str(valeur or "").strip()

    if not valeur:
        return

    elements.append(
        Paragraph(
            f"<b>{_echapper(libelle)} :</b> {_echapper(valeur)}",
            styles["meta"],
        )
    )


def _ajouter_liste_meta(
    elements,
    libelle,
    valeurs,
    styles,
):
    """
    Ajoute une métadonnée pouvant être une liste ou une chaîne.
    """
    texte = _normaliser_liste(valeurs)

    if texte:
        _ajouter_meta_article(
            elements,
            libelle,
            texte,
            styles,
        )


def _normaliser_liste(valeurs):
    """
    Transforme une liste, un tuple ou une chaîne en texte lisible.
    """
    if not valeurs:
        return ""

    if isinstance(valeurs, (list, tuple, set)):
        return " • ".join(
            str(valeur).strip()
            for valeur in valeurs
            if str(valeur).strip()
        )

    return str(valeurs).strip()


def _ajouter_separateur_article(
    elements,
    largeur_disponible,
):
    """
    Ajoute l'espace et la ligne séparant deux publications.
    """
    elements.append(Spacer(1, 8))
    elements.append(
        Table(
            [[""]],
            colWidths=[largeur_disponible],
            rowHeights=[0.7],
            style=TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        COULEUR_BORDURE,
                    ),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            ),
        )
    )
    elements.append(Spacer(1, 12))


def _charger_logo():
    """
    Charge le logo du site s'il existe.

    Le chemin attendu correspond à :
    accueil/static/accueil/images/logo.webp
    """
    chemin_logo = (
        Path(settings.BASE_DIR)
        / "accueil"
        / "static"
        / "accueil"
        / "images"
        / "logo.webp"
    )

    if not chemin_logo.exists():
        return None

    try:
        image = Image(
            str(chemin_logo),
            width=2.7 * cm,
            height=2.7 * cm,
        )

        image.hAlign = "LEFT"

        return image

    except Exception:
        return None


def _dessiner_entete_et_pied(canvas, document):
    """
    Dessine le numéro de page et la mention de génération.
    """
    canvas.saveState()

    largeur_page, _ = A4

    canvas.setStrokeColor(COULEUR_BORDURE)
    canvas.setLineWidth(0.5)

    canvas.line(
        document.leftMargin,
        1.65 * cm,
        largeur_page - document.rightMargin,
        1.65 * cm,
    )

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(COULEUR_TEXTE_SECONDAIRE)

    canvas.drawString(
        document.leftMargin,
        1.15 * cm,
        "Rapport généré automatiquement par Santé+",
    )

    texte_page = f"Page {document.page}"

    largeur_texte = stringWidth(
        texte_page,
        "Helvetica",
        8,
    )

    canvas.drawString(
        largeur_page
        - document.rightMargin
        - largeur_texte,
        1.15 * cm,
        texte_page,
    )

    canvas.restoreState()


def _texte_vers_html(texte):
    """
    Échappe le texte et conserve les retours à la ligne.
    """
    texte = _echapper(texte)

    return texte.replace("\n", "<br/>")


def _echapper(texte):
    """
    Protège les caractères interprétés comme balises par ReportLab.
    """
    if texte is None:
        return ""

    return (
        str(texte)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _creer_lien_cliquable(lien):
    """
    Crée un lien cliquable compatible avec Paragraph.
    """
    lien = (lien or "").strip()

    if not lien:
        return "Lien non disponible"

    lien_echappe = _echapper(lien)

    return (
        f'<link href="{lien_echappe}" '
        f'color="#0B6EFD">'
        f"{lien_echappe}"
        f"</link>"
    )