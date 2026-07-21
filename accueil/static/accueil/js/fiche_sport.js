"use strict";

document.addEventListener("DOMContentLoaded", function () {
    const CHEMIN_SPORTS =
        "/static/accueil/data/sports.json";

    const zoneChargement =
        document.getElementById("zone-chargement");

    const contenuFiche =
        document.getElementById("contenu-fiche");

    const messageErreur =
        document.getElementById("message-erreur");

    const messageErreurTexte =
        document.getElementById(
            "message-erreur-texte"
        );

    function afficherErreur(message) {
        if (zoneChargement) {
            zoneChargement.hidden = true;
        }

        if (contenuFiche) {
            contenuFiche.hidden = true;
        }

        if (messageErreurTexte) {
            messageErreurTexte.textContent =
                message ||
                "Une erreur est survenue.";
        }

        if (messageErreur) {
            messageErreur.hidden = false;
        }
    }

    function afficherContenu() {
        if (zoneChargement) {
            zoneChargement.hidden = true;
        }

        if (messageErreur) {
            messageErreur.hidden = true;
        }

        if (contenuFiche) {
            contenuFiche.hidden = false;
        }
    }

    function definirTexte(
        identifiant,
        valeur,
        valeurParDefaut
    ) {
        const element =
            document.getElementById(identifiant);

        if (!element) {
            return;
        }

        let texte = valeur;

        if (Array.isArray(valeur)) {
            texte = valeur.join(", ");
        }

        if (
            texte === undefined ||
            texte === null ||
            String(texte).trim() === ""
        ) {
            texte = valeurParDefaut;
        }

        element.textContent = String(texte);
    }

    function normaliserListe(valeur) {
        if (Array.isArray(valeur)) {
            return valeur
                .map(function (element) {
                    return String(
                        element ?? ""
                    ).trim();
                })
                .filter(Boolean);
        }

        if (
            typeof valeur === "string" &&
            valeur.trim() !== ""
        ) {
            return valeur
                .split(/[,;|]/)
                .map(function (element) {
                    return element.trim();
                })
                .filter(Boolean);
        }

        return [];
    }

    function afficherTags(
        identifiant,
        valeurs,
        texteParDefaut
    ) {
        const conteneur =
            document.getElementById(identifiant);

        if (!conteneur) {
            return;
        }

        const liste = normaliserListe(valeurs);

        conteneur.replaceChildren();

        if (liste.length === 0) {
            const texte =
                document.createElement("span");

            texte.textContent = texteParDefaut;
            conteneur.appendChild(texte);

            return;
        }

        liste.forEach(function (valeur) {
            const etiquette =
                document.createElement("span");

            etiquette.textContent = valeur;
            conteneur.appendChild(etiquette);
        });
    }

    function afficherListe(
        identifiant,
        valeurs,
        texteParDefaut
    ) {
        const conteneur =
            document.getElementById(identifiant);

        if (!conteneur) {
            return;
        }

        const liste = normaliserListe(valeurs);

        conteneur.replaceChildren();

        if (liste.length === 0) {
            conteneur.textContent =
                texteParDefaut;

            return;
        }

        const listeHTML =
            document.createElement("ul");

        liste.forEach(function (valeur) {
            const element =
                document.createElement("li");

            element.textContent = valeur;
            listeHTML.appendChild(element);
        });

        conteneur.appendChild(listeHTML);
    }

    function lireIdentifiantSport() {
        const segments =
            window.location.pathname
                .split("/")
                .filter(Boolean);

        const positionSport =
            segments.lastIndexOf("sport");

        if (
            positionSport !== -1 &&
            segments[positionSport + 1]
        ) {
            return decodeURIComponent(
                segments[positionSport + 1]
            );
        }

        const parametres =
            new URLSearchParams(
                window.location.search
            );

        return (
            parametres.get("id") ||
            parametres.get("sport") ||
            ""
        );
    }

    function normaliserIdentifiant(valeur) {
        return String(valeur || "")
            .trim()
            .toLowerCase()
            .normalize("NFD")
            .replace(
                /[\u0300-\u036f]/g,
                ""
            )
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/^-+|-+$/g, "");
    }

    function extraireSports(donnees) {
        if (Array.isArray(donnees)) {
            return donnees;
        }

        if (
            donnees &&
            Array.isArray(donnees.sports)
        ) {
            return donnees.sports;
        }

        return [];
    }

    function trouverSport(
        sports,
        identifiant
    ) {
        const identifiantNormalise =
            normaliserIdentifiant(
                identifiant
            );

        return sports.find(function (sport) {
            const identifiantsPossibles = [
                sport.id,
                sport.slug,
                sport.code,
                sport.nom,
            ];

            return identifiantsPossibles.some(
                function (valeur) {
                    return (
                        normaliserIdentifiant(
                            valeur
                        ) ===
                        identifiantNormalise
                    );
                }
            );
        });
    }

    function lireValeur(
        sport,
        nomsPossibles,
        valeurParDefaut
    ) {
        for (
            let index = 0;
            index < nomsPossibles.length;
            index += 1
        ) {
            const nom =
                nomsPossibles[index];

            if (
                Object.prototype.hasOwnProperty.call(
                    sport,
                    nom
                ) &&
                sport[nom] !== null &&
                sport[nom] !== undefined
            ) {
                return sport[nom];
            }
        }

        return valeurParDefaut;
    }

    function limiterNombre(
        valeur,
        minimum,
        maximum
    ) {
        const nombre = Number(valeur);

        if (!Number.isFinite(nombre)) {
            return minimum;
        }

        return Math.min(
            Math.max(nombre, minimum),
            maximum
        );
    }

    function afficherScore(
        identifiant,
        valeur
    ) {
        const note =
            limiterNombre(
                valeur,
                0,
                5
            );

        const texte = Number.isInteger(note)
            ? String(note)
            : note.toFixed(1);

        definirTexte(
            identifiant,
            texte,
            "0"
        );
    }

    function obtenirNiveau(
        valeur,
        libelleFaible,
        libelleFort
    ) {
        const nombre =
            limiterNombre(
                valeur,
                0,
                5
            );

        if (nombre <= 0) {
            return libelleFaible;
        }

        if (nombre <= 1) {
            return "Très faible";
        }

        if (nombre <= 2) {
            return "Faible";
        }

        if (nombre <= 3) {
            return "Modéré";
        }

        if (nombre <= 4) {
            return "Élevé";
        }

        return libelleFort;
    }

    function obtenirNiveauContact(valeur) {
        const nombre =
            limiterNombre(
                valeur,
                0,
                5
            );

        const niveaux = [
            "Sans contact",
            "Contact très léger",
            "Contact léger",
            "Contact modéré",
            "Contact important",
            "Contact très important",
        ];

        return niveaux[
            Math.round(nombre)
        ];
    }

    function obtenirNiveauCompetition(
        valeur
    ) {
        const nombre =
            limiterNombre(
                valeur,
                0,
                5
            );

        const niveaux = [
            "Non nécessaire",
            "Très facultative",
            "Facultative",
            "Possible",
            "Fréquente",
            "Très présente",
        ];

        return niveaux[
            Math.round(nombre)
        ];
    }

    function afficherSport(sport) {
        const nom = lireValeur(
            sport,
            ["nom", "name", "titre"],
            "Sport"
        );

        const famille = lireValeur(
            sport,
            [
                "famille",
                "categorie",
                "catégorie",
                "type",
            ],
            "Famille sportive"
        );

        const description = lireValeur(
            sport,
            [
                "description",
                "resume",
                "résumé",
            ],
            "Aucune description disponible."
        );

        definirTexte(
            "sport-nom",
            nom,
            "Sport"
        );

        definirTexte(
            "sport-famille",
            famille,
            "Famille sportive"
        );

        definirTexte(
            "sport-description",
            description,
            "Aucune description disponible."
        );

        document.title =
            `${nom} | Fiche sport`;

        afficherScore(
            "sport-cardio",
            lireValeur(
                sport,
                ["cardio", "endurance"],
                0
            )
        );

        afficherScore(
            "sport-force",
            lireValeur(
                sport,
                ["force", "puissance"],
                0
            )
        );

        afficherScore(
            "sport-technique",
            lireValeur(
                sport,
                [
                    "technique",
                    "technicite",
                    "technicité",
                ],
                0
            )
        );

        afficherScore(
            "sport-souplesse",
            lireValeur(
                sport,
                [
                    "souplesse",
                    "mobilite",
                    "mobilité",
                ],
                0
            )
        );

        afficherTags(
            "sport-developpe",
            lireValeur(
                sport,
                [
                    "developpe",
                    "développe",
                    "benefices",
                    "bénéfices",
                    "competences",
                    "compétences",
                ],
                []
            ),
            "Développement général"
        );

        afficherListe(
            "sport-ideal-pour",
            lireValeur(
                sport,
                [
                    "ideal_pour",
                    "idéal_pour",
                    "idealPour",
                    "public",
                ],
                []
            ),
            "Cette discipline peut convenir à différents profils."
        );

        afficherListe(
            "sport-qualites",
            lireValeur(
                sport,
                [
                    "qualites_requises",
                    "qualités_requises",
                    "qualites",
                    "qualités",
                    "qualites_recommandees",
                    "qualités_recommandées",
                ],
                []
            ),
            "Aucune qualité particulière n’est exigée pour débuter."
        );

        afficherTags(
            "sport-objectifs",
            lireValeur(
                sport,
                [
                    "objectifs",
                    "objectives",
                ],
                []
            ),
            "Bien-être général"
        );

        definirTexte(
            "sport-materiel",
            lireValeur(
                sport,
                [
                    "materiel",
                    "matériel",
                    "equipement",
                    "équipement",
                ],
                []
            ),
            "Aucun matériel particulier renseigné"
        );

        const contact = lireValeur(
            sport,
            [
                "contact",
                "niveau_contact",
            ],
            0
        );

        definirTexte(
            "sport-contact",
            obtenirNiveauContact(contact),
            "Sans contact"
        );

        const competition = lireValeur(
            sport,
            [
                "competition",
                "compétition",
            ],
            0
        );

        definirTexte(
            "sport-competition",
            obtenirNiveauCompetition(
                competition
            ),
            "Non nécessaire"
        );

        const coordination = lireValeur(
            sport,
            ["coordination"],
            0
        );

        definirTexte(
            "sport-coordination",
            obtenirNiveau(
                coordination,
                "Très faible",
                "Très élevée"
            ),
            "Non renseigné"
        );

        const equilibre = lireValeur(
            sport,
            [
                "equilibre",
                "équilibre",
            ],
            0
        );

        definirTexte(
            "sport-equilibre",
            obtenirNiveau(
                equilibre,
                "Très faible",
                "Très élevé"
            ),
            "Non renseigné"
        );

        afficherListe(
            "sport-eviter-si",
            lireValeur(
                sport,
                [
                    "eviter_si",
                    "éviter_si",
                    "precautions",
                    "précautions",
                ],
                []
            ),
            "Aucune précaution particulière renseignée."
        );

        afficherListe(
            "sport-contre-indications",
            lireValeur(
                sport,
                [
                    "contre_indications",
                    "contre-indications",
                    "contreindications",
                ],
                []
            ),
            "Aucune contre-indication particulière renseignée."
        );
    }

    async function chargerFicheSport() {
        const identifiant =
            lireIdentifiantSport();

        if (!identifiant) {
            throw new Error(
                "Aucun identifiant de sport n’a été fourni."
            );
        }

        const reponse = await fetch(
            CHEMIN_SPORTS,
            {
                headers: {
                    Accept: "application/json",
                },
                cache: "no-store",
            }
        );

        if (!reponse.ok) {
            throw new Error(
                "Le fichier sports.json n’a pas pu être chargé."
            );
        }

        const donnees =
            await reponse.json();

        const sports =
            extraireSports(donnees);

        if (sports.length === 0) {
            throw new Error(
                "Aucun sport n’est disponible dans sports.json."
            );
        }

        const sport =
            trouverSport(
                sports,
                identifiant
            );

        if (!sport) {
            throw new Error(
                "La discipline demandée est introuvable."
            );
        }

        afficherSport(sport);
        afficherContenu();
    }

    chargerFicheSport().catch(
        function (erreur) {
            console.error(
                "Erreur dans fiche_sport.js :",
                erreur
            );

            afficherErreur(
                erreur?.message ||
                "Une erreur est survenue pendant le chargement."
            );
        }
    );
});
