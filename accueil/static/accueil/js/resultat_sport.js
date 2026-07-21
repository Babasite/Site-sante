"use strict";

document.addEventListener("DOMContentLoaded", async function () {
    const CLE_SESSION = "bouger_recommandation";

    const zoneChargement =
        document.getElementById("zone-chargement");

    const contenuResultats =
        document.getElementById("contenu-resultats");

    const messageErreur =
        document.getElementById("message-erreur");

    const messageErreurTexte =
        document.getElementById("message-erreur-texte");

    const profilUtilisateur =
        document.getElementById("profil-utilisateur");

    const listeRecommandations =
        document.getElementById("liste-recommandations");

    const nombreResultats =
        document.getElementById("nombre-resultats");

    function echapperHTML(valeur) {
        return String(valeur ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function afficherErreur(message) {
        if (zoneChargement) {
            zoneChargement.hidden = true;
        }

        if (contenuResultats) {
            contenuResultats.hidden = true;
        }

        if (messageErreurTexte) {
            messageErreurTexte.textContent =
                message ||
                "Une erreur est survenue pendant le chargement.";
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

        if (contenuResultats) {
            contenuResultats.hidden = false;
        }
    }

    function obtenirLibelleAxe(axe) {
        const libelles = {
            cardio: "Endurance",
            force: "Force",
            technique: "Technique",
            souplesse: "Souplesse",
            equilibre: "Équilibre",
            coordination: "Coordination",
            contact: "Contact physique",
            competition: "Compétition",
        };

        return libelles[axe] || axe;
    }

    function limiterNombre(valeur, minimum, maximum) {
        return Math.min(
            Math.max(Number(valeur), minimum),
            maximum
        );
    }

    function afficherProfil(profil) {
        if (!profilUtilisateur) {
            return;
        }

        const axes = [
            "cardio",
            "force",
            "technique",
            "souplesse",
            "equilibre",
            "coordination",
            "contact",
            "competition",
        ];

        profilUtilisateur.innerHTML = axes
            .map(function (axe) {
                const note = limiterNombre(
                    profil?.[axe] || 0,
                    0,
                    5
                );

                const pourcentage = Math.round(
                    note / 5 * 100
                );

                return `
                    <article class="profil-carte">
                        <h3 class="profil-carte__nom">
                            ${echapperHTML(
                                obtenirLibelleAxe(axe)
                            )}
                        </h3>

                        <p class="profil-carte__valeur">
                            ${note.toFixed(1)}/5
                        </p>

                        <div
                            class="profil-carte__barre"
                            role="progressbar"
                            aria-label="${echapperHTML(
                                obtenirLibelleAxe(axe)
                            )}"
                            aria-valuemin="0"
                            aria-valuemax="100"
                            aria-valuenow="${pourcentage}"
                        >
                            <span
                                class="profil-carte__progression"
                                style="width: ${pourcentage}%"
                            ></span>
                        </div>
                    </article>
                `;
            })
            .join("");
    }

    function afficherRang(index) {
        if (index === 0) {
            return "🥇";
        }

        if (index === 1) {
            return "🥈";
        }

        if (index === 2) {
            return "🥉";
        }

        return String(index + 1);
    }

    function afficherExplications(explications) {
        if (
            !Array.isArray(explications) ||
            explications.length === 0
        ) {
            return "";
        }

        return `
            <ul class="recommandation-carte__raisons">
                ${explications
                    .map(function (explication) {
                        return `
                            <li class="recommandation-carte__raison">
                                ${echapperHTML(explication)}
                            </li>
                        `;
                    })
                    .join("")}
            </ul>
        `;
    }

    function construireURLFiche(sportId) {
        const identifiant = encodeURIComponent(
            String(sportId || "").trim()
        );

        return `/bouger/sport/${identifiant}/`;
    }

    function creerCarteSport(resultat, index) {
        const identifiant =
            resultat.id ||
            resultat.sport?.id ||
            "";

        const nom =
            resultat.nom ||
            resultat.sport?.nom ||
            "Sport";

        const famille =
            resultat.famille ||
            resultat.sport?.famille ||
            "Famille non renseignée";

        const description =
            resultat.description ||
            resultat.sport?.description ||
            "Cette discipline correspond à plusieurs éléments de votre profil.";

        const compatibilite = Math.round(
            limiterNombre(
                resultat.compatibilite || 0,
                0,
                100
            )
        );

        const lienFiche =
            construireURLFiche(identifiant);

        return `
            <article class="recommandation-carte">

                <div
                    class="recommandation-carte__rang"
                    aria-label="Position ${index + 1}"
                >
                    ${afficherRang(index)}
                </div>

                <div class="recommandation-carte__contenu">

                    <h3>
                        ${echapperHTML(nom)}
                    </h3>

                    <p class="recommandation-carte__famille">
                        ${echapperHTML(famille)}
                    </p>

                    <p class="recommandation-carte__description">
                        ${echapperHTML(description)}
                    </p>

                    ${afficherExplications(
                        resultat.explications
                    )}

                </div>

                <div class="recommandation-carte__score">

                    <div>
                        <span class="recommandation-carte__pourcentage">
                            ${compatibilite} %
                        </span>

                        <span class="recommandation-carte__libelle">
                            Compatibilité
                        </span>
                    </div>

                    <a
                        class="recommandation-carte__lien"
                        href="${lienFiche}"
                    >
                        Voir la fiche
                    </a>

                </div>

            </article>
        `;
    }

    function afficherResultats(resultats) {
        if (!listeRecommandations) {
            return;
        }

        listeRecommandations.innerHTML = resultats
            .map(function (resultat, index) {
                return creerCarteSport(
                    resultat,
                    index
                );
            })
            .join("");

        if (nombreResultats) {
            const total = resultats.length;

            nombreResultats.textContent =
                total === 1
                    ? "1 discipline sélectionnée"
                    : `${total} disciplines sélectionnées`;
        }
    }

    async function chargerResultats() {
        if (
            typeof window.MoteurRecommandation !==
            "function"
        ) {
            throw new Error(
                "Le moteur de recommandation n'est pas chargé."
            );
        }

        const moteur =
            new window.MoteurRecommandation();

        await moteur.initialiser();

        const sessionTrouvee =
            moteur.chargerSession(CLE_SESSION);

        if (!sessionTrouvee) {
            throw new Error(
                "Aucun questionnaire terminé n'a été trouvé. Recommencez le questionnaire."
            );
        }

        const etat =
            moteur.obtenirEtat();

        if (
            !etat ||
            etat.nombreQuestionsPosees === 0
        ) {
            throw new Error(
                "La session enregistrée ne contient aucune réponse."
            );
        }

        const resultats =
            moteur.calculerResultats(10);

        if (
            !Array.isArray(resultats) ||
            resultats.length === 0
        ) {
            throw new Error(
                "Aucune recommandation n'a pu être calculée."
            );
        }

        afficherProfil(
            etat.profilNormalise || {}
        );

        afficherResultats(resultats);

        afficherContenu();
    }

    try {
        await chargerResultats();
    } catch (erreur) {
        console.error(
            "Erreur dans resultat_sport.js :",
            erreur
        );

        afficherErreur(
            erreur?.message ||
            "Une erreur est survenue pendant le chargement."
        );
    }
});