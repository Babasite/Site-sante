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
    """
    elements.append(
        Paragraph(
            "Résumé exécutif",
            styles["section"],
        )
    )

    resume = veille.resume or (
        "Aucun résumé n'est disponible pour cette veille."
    )

    bloc_resume = Table(
        [
            [
                Paragraph(
                    _texte_vers_html(resume),
                    styles["corps"],
                )
            ]
        ],
        colWidths=[17.0 * cm],
    )

    bloc_resume.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    COULEUR_FOND,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.7,
                    COULEUR_BORDURE,
                ),
                (
                    "LINEBEFORE",
                    (0, 0),
                    (0, -1),
                    4,
                    colors.HexColor("#0B6EFD"),
                ),
                ("LEFTPADDING", (0, 0), (-1, -1), 13),
                ("RIGHTPADDING", (0, 0), (-1, -1), 13),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )

    elements.append(bloc_resume)
    elements.append(Spacer(1, 13))


def _ajouter_convergence(elements, veille, styles):
    """
    Ajoute les convergences uniquement lorsqu'elles existent.
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

    bloc_convergence = Table(
        [
            [
                Paragraph(
                    _texte_vers_html(convergence),
                    styles["corps"],
                )
            ]
        ],
        colWidths=[17.0 * cm],
    )

    bloc_convergence.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    COULEUR_CONVERGENCE,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.7,
                    COULEUR_BORDURE,
                ),
                (
                    "LINEBEFORE",
                    (0, 0),
                    (0, -1),
                    4,
                    colors.HexColor("#198754"),
                ),
                ("LEFTPADDING", (0, 0), (-1, -1), 13),
                ("RIGHTPADDING", (0, 0), (-1, -1), 13),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )

    elements.append(bloc_convergence)
    elements.append(Spacer(1, 13))


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
    Ajoute tous les articles enregistrés dans la veille.
    """
    elements.append(
        Paragraph(
            "Publications retenues",
            styles["section"],
        )
    )

    articles = veille.articles.all()

    if not articles.exists():
        elements.append(
            Paragraph(
                "Aucune publication n'a été enregistrée.",
                styles["corps"],
            )
        )
        return

    for numero, article in enumerate(articles, start=1):
        titre = f"{numero}. {article.titre}"

        resume = article.resume or (
            "Aucun résumé n'est disponible."
        )

        contenu_article = [
            Paragraph(
                _echapper(titre),
                styles["titre_article"],
            ),
            Paragraph(
                (
                    f"<b>Source :</b> "
                    f"{_echapper(article.source)}"
                ),
                styles["meta"],
            ),
        ]

        if article.date_publication:
            contenu_article.append(
                Paragraph(
                    (
                        f"<b>Date :</b> "
                        f"{_echapper(article.date_publication)}"
                    ),
                    styles["meta"],
                )
            )

        contenu_article.extend(
            [
                Spacer(1, 5),
                Paragraph(
                    _texte_vers_html(resume),
                    styles["corps"],
                ),
                Paragraph(
                    _creer_lien_cliquable(article.lien),
                    styles["lien"],
                ),
            ]
        )

        # Les articles sont ajoutés comme des éléments séparés plutôt que
        # dans une cellule de tableau. Ainsi, un résumé long peut être
        # coupé naturellement sur plusieurs pages par ReportLab.
        # Une ligne de tableau ne peut pas être scindée et provoquait un
        # LayoutError dès qu'un article dépassait la hauteur d'une page.
        elements.extend(contenu_article)
        elements.append(Spacer(1, 8))
        elements.append(
            Table(
                [[""]],
                colWidths=[largeur_disponible],
                rowHeights=[0.7],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), COULEUR_BORDURE),
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
    accueil/static/accueil/images/logo.png
    """
    chemin_logo = (
        Path(settings.BASE_DIR)
        / "accueil"
        / "static"
        / "accueil"
        / "images"
        / "logo.png"
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
