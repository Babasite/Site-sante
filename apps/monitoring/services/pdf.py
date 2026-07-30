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

# Nombre maximal de publications affichées dans le rapport PDF.
NOMBRE_MAX_PUBLICATIONS = 7


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
        "traduction": ParagraphStyle(
            "TraductionManuelle",
            parent=styles_base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=colors.HexColor("#30363A"),
            alignment=TA_LEFT,
            backColor=colors.HexColor("#F8F6FC"),
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

    Le résumé n'est volontairement pas placé dans un tableau :
    un Paragraph peut commencer dans l'espace disponible sur la page
    courante et continuer automatiquement sur la page suivante.
    """
    elements.append(
        Paragraph(
            "Résumé exécutif",
            styles["section"],
        )
    )
    elements.append(Spacer(1, 8))

    resume = (
        veille.resume_affiche
        or "Aucun résumé n'est disponible pour cette veille."
    )

    lignes = resume.splitlines()

    if len(lignes) > 4:
        resume = "\n".join(lignes[2:-3]).strip()

    elements.append(
        Paragraph(
            _texte_vers_html(resume),
            styles["resume_executif"],
        )
    )


def _ajouter_convergence(elements, veille, styles):
    """
    Ajoute la convergence des sources uniquement lorsqu'elle existe.

    Ce bloc peut lui aussi se répartir sur plusieurs pages.
    """
    convergence = (veille.convergence or "").strip()

    if not convergence:
        return

    elements.append(Spacer(1, 12))

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

    elements.append(Spacer(1, 12))


def _ajouter_statistiques(elements, veille, styles):
    """
    Ajoute le tableau récapitulatif de la collecte.
    """
    elements.append(Spacer(1, 12))

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
    Ajoute au maximum sept publications retenues.

    Pour chaque publication, le PDF affiche :
    - le titre publié ;
    - la source et la date ;
    - les catégories ;
    - les dimensions One Health ;
    - le niveau de preuve ;
    - le niveau d'importance ;
    - la traduction manuelle complète lorsqu'elle est publiée ;
    - le lien vers la publication originale.

    Les résumés automatiques ne sont pas affichés.
    """
    elements.append(
        Paragraph(
            "Publications retenues",
            styles["section"],
        )
    )

    # Le modèle ArticleVeille possède déjà l'ordre :
    # ordre croissant, puis score décroissant.
    articles = list(
        veille.articles.all()[:NOMBRE_MAX_PUBLICATIONS]
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
        _ajouter_publication(
            elements=elements,
            article=article,
            numero=numero,
            styles=styles,
            largeur_disponible=largeur_disponible,
        )


def _ajouter_publication(
    elements,
    article,
    numero,
    styles,
    largeur_disponible,
):
    """
    Ajoute une publication au rapport.
    """
    titre = _titre_publication(article)

    elements.append(
        Paragraph(
            _echapper(f"{numero}. {titre}"),
            styles["titre_article"],
        )
    )

    _ajouter_metadonnee(
        elements,
        "Source",
        article.source,
        styles,
    )

    _ajouter_metadonnee(
        elements,
        "Date",
        article.date_publication,
        styles,
    )

    _ajouter_metadonnee(
        elements,
        "Catégories",
        _liste_vers_texte(article.categories),
        styles,
    )

    _ajouter_metadonnee(
        elements,
        "One Health",
        _liste_vers_texte(article.one_health),
        styles,
    )

    if article.preuve and article.preuve != "Non déterminé":
        _ajouter_metadonnee(
            elements,
            "Niveau de preuve",
            article.preuve,
            styles,
        )

    _ajouter_metadonnee(
        elements,
        "Importance",
        article.niveau_importance,
        styles,
    )

    traduction = _traduction_manuelle_publiee(article)

    if traduction:
        elements.append(
            Paragraph(
                "<b>Traduction manuelle publiée</b><br/>"
                + _texte_vers_html(traduction),
                styles["traduction"],
            )
        )

    elements.append(
        Paragraph(
            _creer_lien_cliquable(article.lien),
            styles["lien"],
        )
    )

    _ajouter_separateur(
        elements,
        largeur_disponible,
    )


def _titre_publication(article):
    """
    Utilise le titre manuel lorsqu'il a été publié.

    À défaut, conserve le titre original. Le titre automatique n'est
    volontairement pas utilisé dans le PDF.
    """
    titre_manuel = (
        article.titre_traduit_manuel
        or ""
    ).strip()

    if article.traduction_manuelle_publiee and titre_manuel:
        return titre_manuel

    return article.titre or "Publication sans titre"


def _traduction_manuelle_publiee(article):
    """
    Retourne la traduction manuelle uniquement si sa publication
    a été explicitement validée dans l'interface de rédaction.
    """
    if not article.traduction_manuelle_publiee:
        return ""

    return (
        article.resume_traduit_manuel
        or ""
    ).strip()


def _ajouter_metadonnee(
    elements,
    libelle,
    valeur,
    styles,
):
    """
    Ajoute une ligne de métadonnée seulement si elle contient
    une valeur utile.
    """
    valeur = str(valeur or "").strip()

    if not valeur:
        return

    elements.append(
        Paragraph(
            f"<b>{_echapper(libelle)} :</b> "
            f"{_echapper(valeur)}",
            styles["meta"],
        )
    )


def _liste_vers_texte(valeurs):
    """
    Transforme une liste JSON en texte lisible.

    La fonction accepte également une chaîne pour rester robuste
    face à d'anciennes données enregistrées.
    """
    if not valeurs:
        return ""

    if isinstance(valeurs, (list, tuple, set)):
        valeurs_nettoyees = [
            str(valeur).strip()
            for valeur in valeurs
            if str(valeur).strip()
        ]
        return " • ".join(valeurs_nettoyees)

    return str(valeurs).strip()


def _ajouter_separateur(
    elements,
    largeur_disponible,
):
    """
    Ajoute une ligne discrète entre deux publications.
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