/**
 * moteur_recommandation.js
 * Version 1.0.0
 *
 * Emplacement conseillé :
 * accueil/static/accueil/js/moteur_recommandation.js
 *
 * Fichiers attendus :
 * - /static/accueil/data/sports.json
 * - /static/accueil/data/questions.json
 * - /static/accueil/data/profils_psychologiques.json (optionnel)
 *
 * Le moteur :
 * - charge les données JSON ;
 * - sélectionne 20 à 30 questions ;
 * - applique les conditions ;
 * - construit le profil utilisateur ;
 * - compare le profil aux disciplines ;
 * - renvoie un Top 10 avec score et explications.
 */

"use strict";

class MoteurRecommandation {
    constructor(options = {}) {
        this.urls = {
            sports: options.sportsUrl || "/static/accueil/data/sports.json",
            questions: options.questionsUrl || "/static/accueil/data/questions.json",
            profils:
                options.profilsUrl ||
                "/static/accueil/data/profils_psychologiques.json",
        };

        this.config = {
            minQuestions: Number(options.minQuestions || 20),
            maxQuestions: Number(options.maxQuestions || 30),
            nombreResultats: Number(options.nombreResultats || 10),
            poidsAxes: {
                cardio: 1,
                force: 1,
                technique: 1,
                souplesse: 1,
                equilibre: 1,
                coordination: 1,
                contact: 1.2,
                competition: 1.1,
                ...(options.poidsAxes || {}),
            },
        };

        this.axes = [
            "cardio",
            "force",
            "technique",
            "souplesse",
            "equilibre",
            "coordination",
            "contact",
            "competition",
        ];

        this.sports = [];
        this.questions = [];
        this.profilsPsychologiques = {};
        this.reponses = {};
        this.questionsPosees = [];
        this.profilUtilisateur = this.creerProfilVide();
        this.filtres = {};
        this.scoresFamilles = {};
        this.exclusionsFamilles = {};
    }

    creerProfilVide() {
        return this.axes.reduce((profil, axe) => {
            profil[axe] = 0;
            return profil;
        }, {});
    }

    async chargerJSON(url, obligatoire = true) {
        try {
            const response = await fetch(url, {
                headers: { Accept: "application/json" },
                cache: "no-store",
            });

            if (!response.ok) {
                throw new Error(
                    `Erreur HTTP ${response.status} lors du chargement de ${url}`
                );
            }

            return await response.json();
        } catch (erreur) {
            if (!obligatoire) {
                console.warn(`Fichier optionnel non chargé : ${url}`, erreur);
                return null;
            }
            throw erreur;
        }
    }

    extraireTableauSports(donnees) {
        if (Array.isArray(donnees)) {
            return donnees;
        }

        const clesPossibles = [
            "sports",
            "disciplines",
            "activites",
            "data",
            "items",
        ];

        for (const cle of clesPossibles) {
            if (Array.isArray(donnees?.[cle])) {
                return donnees[cle];
            }
        }

        throw new Error(
            "sports.json doit contenir un tableau ou une propriété sports/disciplines."
        );
    }

    extraireQuestions(donnees) {
        if (Array.isArray(donnees)) {
            return donnees;
        }

        if (Array.isArray(donnees?.questions)) {
            return donnees.questions;
        }

        throw new Error(
            "questions.json doit contenir un tableau ou une propriété questions."
        );
    }

    async initialiser() {
        const [sportsJSON, questionsJSON, profilsJSON] = await Promise.all([
            this.chargerJSON(this.urls.sports, true),
            this.chargerJSON(this.urls.questions, true),
            this.chargerJSON(this.urls.profils, false),
        ]);

        this.sports = this.extraireTableauSports(sportsJSON);
        this.questions = this.extraireQuestions(questionsJSON);
        this.profilsPsychologiques = profilsJSON || {};

        this.validerDonnees();

        return {
            sports: this.sports.length,
            questions: this.questions.length,
            profilsPsychologiquesCharges: Boolean(profilsJSON),
        };
    }

    validerDonnees() {
        if (!this.sports.length) {
            throw new Error("Aucune discipline trouvée dans sports.json.");
        }

        if (!this.questions.length) {
            throw new Error("Aucune question trouvée dans questions.json.");
        }

        const idsQuestions = new Set();

        for (const question of this.questions) {
            if (!question.id) {
                throw new Error("Chaque question doit posséder un identifiant.");
            }

            if (idsQuestions.has(question.id)) {
                throw new Error(`Identifiant de question dupliqué : ${question.id}`);
            }

            idsQuestions.add(question.id);
        }
    }

    reinitialiser() {
        this.reponses = {};
        this.questionsPosees = [];
        this.profilUtilisateur = this.creerProfilVide();
        this.filtres = {};
        this.scoresFamilles = {};
        this.exclusionsFamilles = {};
    }

    normaliserTexte(valeur) {
        return String(valeur ?? "")
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .trim()
            .toLowerCase();
    }

    valeurReponse(questionId) {
        return this.reponses[questionId];
    }

    conditionSatisfaite(condition) {
        if (!condition) {
            return true;
        }

        if (Array.isArray(condition)) {
            return condition.every((item) => this.conditionSatisfaite(item));
        }

        if (condition.all) {
            return condition.all.every((item) =>
                this.conditionSatisfaite(item)
            );
        }

        if (condition.any) {
            return condition.any.some((item) =>
                this.conditionSatisfaite(item)
            );
        }

        const questionId =
            condition.question_id ||
            condition.questionId ||
            condition.question;

        const operateur = condition.operator || "equals";
        const attendu = condition.value;
        const obtenu = this.valeurReponse(questionId);

        if (obtenu === undefined) {
            return false;
        }

        switch (operateur) {
            case "equals":
                return this.normaliserTexte(obtenu) ===
                    this.normaliserTexte(attendu);

            case "not_equals":
                return this.normaliserTexte(obtenu) !==
                    this.normaliserTexte(attendu);

            case "contains":
                return Array.isArray(obtenu)
                    ? obtenu.some(
                          (valeur) =>
                              this.normaliserTexte(valeur) ===
                              this.normaliserTexte(attendu)
                      )
                    : this.normaliserTexte(obtenu).includes(
                          this.normaliserTexte(attendu)
                      );

            case "not_contains":
                return !this.conditionSatisfaite({
                    question_id: questionId,
                    operator: "contains",
                    value: attendu,
                });

            case "greater_than":
                return Number(obtenu) > Number(attendu);

            case "greater_or_equal":
                return Number(obtenu) >= Number(attendu);

            case "less_than":
                return Number(obtenu) < Number(attendu);

            case "less_or_equal":
                return Number(obtenu) <= Number(attendu);

            case "answered":
                return obtenu !== undefined && obtenu !== null && obtenu !== "";

            default:
                console.warn(`Opérateur de condition inconnu : ${operateur}`);
                return false;
        }
    }

    questionsDisponibles() {
        return this.questions
            .filter((question) => !this.questionsPosees.includes(question.id))
            .filter((question) => this.conditionSatisfaite(question.condition))
            .sort((a, b) => {
                const prioriteA = Number(a.priority || 0);
                const prioriteB = Number(b.priority || 0);

                if (prioriteA !== prioriteB) {
                    return prioriteB - prioriteA;
                }

                return String(a.id).localeCompare(String(b.id));
            });
    }

    prochaineQuestion() {
        if (this.questionsPosees.length >= this.config.maxQuestions) {
            return null;
        }

        const disponibles = this.questionsDisponibles();

        if (!disponibles.length) {
            return null;
        }

        const questionsPriorite5 = disponibles.filter(
            (question) => Number(question.priority || 0) === 5
        );

        if (questionsPriorite5.length) {
            return questionsPriorite5[0];
        }

        if (this.questionsPosees.length < this.config.minQuestions) {
            return disponibles[0];
        }

        const resultatsProvisoires = this.calculerResultats(
            Math.min(5, this.config.nombreResultats)
        );

        if (this.resultatsSontProches(resultatsProvisoires)) {
            return this.choisirQuestionDiscriminante(disponibles);
        }

        return null;
    }

    resultatsSontProches(resultats) {
        if (!Array.isArray(resultats) || resultats.length < 2) {
            return true;
        }

        const ecart =
            Number(resultats[0].compatibilite) -
            Number(resultats[1].compatibilite);

        return ecart < 8;
    }

    choisirQuestionDiscriminante(disponibles) {
        const priorite4 = disponibles.find(
            (question) => Number(question.priority || 0) === 4
        );

        if (priorite4) {
            return priorite4;
        }

        const priorite3 = disponibles.find(
            (question) => Number(question.priority || 0) === 3
        );

        return priorite3 || disponibles[0] || null;
    }

    enregistrerReponse(questionId, valeur) {
        const question = this.questions.find((q) => q.id === questionId);

        if (!question) {
            throw new Error(`Question inconnue : ${questionId}`);
        }

        this.reponses[questionId] = valeur;

        if (!this.questionsPosees.includes(questionId)) {
            this.questionsPosees.push(questionId);
        }

        this.recalculerProfil();
    }

    retirerReponse(questionId) {
        delete this.reponses[questionId];
        this.questionsPosees = this.questionsPosees.filter(
            (id) => id !== questionId
        );
        this.recalculerProfil();
    }

    recalculerProfil() {
        this.profilUtilisateur = this.creerProfilVide();
        this.filtres = {};
        this.scoresFamilles = {};
        this.exclusionsFamilles = {};

        for (const question of this.questions) {
            if (!(question.id in this.reponses)) {
                continue;
            }

            const valeur = this.reponses[question.id];
            this.appliquerEffetsQuestion(question, valeur);
        }
    }

    appliquerEffetsQuestion(question, valeur) {
        if (question.type === "scale") {
            this.appliquerEffetsEchelle(question, valeur);
            return;
        }

        const valeurs = Array.isArray(valeur) ? valeur : [valeur];

        for (const valeurChoisie of valeurs) {
            const choix = this.trouverChoix(question, valeurChoisie);

            if (choix) {
                this.appliquerEffets(choix);
            }
        }
    }

    trouverChoix(question, valeur) {
        const choix = question.choices || question.options || [];

        return choix.find((option) => {
            const identifiant =
                option.value ??
                option.id ??
                option.label ??
                option.texte ??
                option.nom;

            return (
                this.normaliserTexte(identifiant) ===
                this.normaliserTexte(valeur)
            );
        });
    }

    appliquerEffetsEchelle(question, valeur) {
        const cle = String(valeur);
        const echelle = question.scale || {};

        const effets = {
            profile:
                echelle.profile_map?.[cle] ||
                echelle.profil_map?.[cle] ||
                null,
            families:
                echelle.families_map?.[cle] ||
                echelle.familles_map?.[cle] ||
                null,
            exclude_families:
                echelle.exclude_families_map?.[cle] ||
                echelle.exclusions_familles_map?.[cle] ||
                null,
            filters:
                echelle.filters_map?.[cle] ||
                echelle.filtres_map?.[cle] ||
                null,
        };

        this.appliquerEffets(effets);
    }

    appliquerEffets(effets) {
        if (!effets || typeof effets !== "object") {
            return;
        }

        this.ajouterValeurs(
            this.profilUtilisateur,
            effets.profile || effets.profil
        );

        this.ajouterValeurs(
            this.scoresFamilles,
            effets.families || effets.familles
        );

        this.ajouterValeurs(
            this.exclusionsFamilles,
            effets.exclude_families || effets.exclusions_familles
        );

        this.fusionnerFiltres(
            effets.filters || effets.filtres || {}
        );
    }

    ajouterValeurs(destination, valeurs) {
        if (!valeurs || typeof valeurs !== "object") {
            return;
        }

        for (const [cle, valeur] of Object.entries(valeurs)) {
            const nombre = Number(valeur);

            if (!Number.isFinite(nombre)) {
                continue;
            }

            destination[cle] = Number(destination[cle] || 0) + nombre;
        }
    }

    fusionnerFiltres(nouveauxFiltres) {
        for (const [cle, valeur] of Object.entries(nouveauxFiltres || {})) {
            if (typeof valeur === "boolean") {
                this.filtres[cle] = valeur;
                continue;
            }

            if (typeof valeur === "number") {
                const ancienneValeur = Number(this.filtres[cle] || 0);

                if (
                    cle.endsWith("_max") ||
                    cle.startsWith("budget_max")
                ) {
                    this.filtres[cle] =
                        ancienneValeur === 0
                            ? valeur
                            : Math.min(ancienneValeur, valeur);
                } else {
                    this.filtres[cle] = ancienneValeur + valeur;
                }

                continue;
            }

            this.filtres[cle] = valeur;
        }
    }

    normaliserProfilUtilisateur() {
        const profilNormalise = {};

        for (const axe of this.axes) {
            const valeur = Number(this.profilUtilisateur[axe] || 0);

            /*
             * Les réponses peuvent produire environ -20 à +20.
             * La formule ramène la préférence sur 0 à 5.
             */
            profilNormalise[axe] = this.limiter(
                2.5 + valeur / 8,
                0,
                5
            );
        }

        return profilNormalise;
    }

    lireValeurSport(sport, axe) {
        const chemins = [
            sport?.[axe],
            sport?.profil?.[axe],
            sport?.caracteristiques?.[axe],
            sport?.scores?.[axe],
        ];

        for (const valeur of chemins) {
            const nombre = Number(valeur);

            if (Number.isFinite(nombre)) {
                return this.limiter(nombre, 0, 5);
            }
        }

        return 2.5;
    }

    lireFamilleSport(sport) {
        return (
            sport.famille ||
            sport.categorie ||
            sport.category ||
            sport.groupe ||
            ""
        );
    }

    lireNomSport(sport) {
        return (
            sport.nom ||
            sport.name ||
            sport.titre ||
            sport.id ||
            "Discipline sans nom"
        );
    }

    lireIdSport(sport) {
        return (
            sport.id ||
            this.normaliserTexte(this.lireNomSport(sport))
                .replace(/[^a-z0-9]+/g, "-")
                .replace(/^-|-$/g, "")
        );
    }

    scoreAxesSport(sport, profilNormalise) {
        let somme = 0;
        let poidsTotal = 0;
        const details = {};

        for (const axe of this.axes) {
            const cible = Number(profilNormalise[axe]);
            const valeurSport = this.lireValeurSport(sport, axe);
            const poids = Number(this.config.poidsAxes[axe] || 1);
            const ecart = Math.abs(cible - valeurSport);
            const compatibiliteAxe = this.limiter(
                100 - (ecart / 5) * 100,
                0,
                100
            );

            details[axe] = {
                utilisateur: this.arrondir(cible, 2),
                sport: this.arrondir(valeurSport, 2),
                compatibilite: this.arrondir(compatibiliteAxe, 1),
            };

            somme += compatibiliteAxe * poids;
            poidsTotal += poids;
        }

        return {
            score: poidsTotal ? somme / poidsTotal : 0,
            details,
        };
    }

    scoreFamilleSport(sport) {
        const famille = this.lireFamilleSport(sport);
        const familleNormalisee = this.normaliserTexte(famille);

        let bonus = 0;
        let exclusion = 0;

        for (const [nomFamille, valeur] of Object.entries(
            this.scoresFamilles
        )) {
            if (
                familleNormalisee === this.normaliserTexte(nomFamille) ||
                familleNormalisee.includes(
                    this.normaliserTexte(nomFamille)
                )
            ) {
                bonus += Number(valeur || 0);
            }
        }

        for (const [nomFamille, valeur] of Object.entries(
            this.exclusionsFamilles
        )) {
            if (
                familleNormalisee === this.normaliserTexte(nomFamille) ||
                familleNormalisee.includes(
                    this.normaliserTexte(nomFamille)
                )
            ) {
                exclusion += Number(valeur || 0);
            }
        }

        return {
            bonus: this.limiter(bonus * 2, -25, 25),
            exclusion: this.limiter(exclusion * 4, 0, 80),
        };
    }

    sportRespecteFiltresDurs(sport) {
        const famille = this.normaliserTexte(
            this.lireFamilleSport(sport)
        );

        const contact = this.lireValeurSport(sport, "contact");

        if (this.filtres.hard_no_contact === true && contact > 1.5) {
            return false;
        }

        if (
            this.filtres.non_swimmer >= 5 &&
            famille.includes("aquatique")
        ) {
            return false;
        }

        if (
            this.filtres.vertigo >= 5 &&
            (famille.includes("aerien") ||
                famille.includes("montagne") ||
                famille.includes("cirque"))
        ) {
            return false;
        }

        if (
            this.filtres.adaptive_required >= 5 &&
            !famille.includes("adapte")
        ) {
            return false;
        }

        return true;
    }

    scoreFiltresSouples(sport) {
        let ajustement = 0;
        const famille = this.normaliserTexte(
            this.lireFamilleSport(sport)
        );

        const contact = this.lireValeurSport(sport, "contact");
        const cardio = this.lireValeurSport(sport, "cardio");
        const force = this.lireValeurSport(sport, "force");

        if (Number(this.filtres.avoid_impacts || 0) >= 3 && contact >= 3) {
            ajustement -= 15;
        }

        if (Number(this.filtres.low_impact || 0) >= 3) {
            if (famille.includes("aquatique") || famille.includes("bien-etre")) {
                ajustement += 8;
            }

            if (contact >= 3 || cardio >= 4.5) {
                ajustement -= 10;
            }
        }

        if (Number(this.filtres.protect_cardio || 0) >= 3 && cardio >= 4) {
            ajustement -= 18;
        }

        if (Number(this.filtres.protect_knees || 0) >= 3) {
            if (
                famille.includes("endurance") ||
                famille.includes("athletisme") ||
                famille.includes("glisse")
            ) {
                ajustement -= 10;
            }
        }

        if (Number(this.filtres.protect_shoulders || 0) >= 3 && force >= 4) {
            ajustement -= 8;
        }

        if (Number(this.filtres.risk_tolerance || 0) <= -3) {
            if (
                famille.includes("aerien") ||
                famille.includes("mecanique") ||
                famille.includes("montagne")
            ) {
                ajustement -= 15;
            }
        }

        if (Number(this.filtres.risk_tolerance || 0) >= 3) {
            if (
                famille.includes("aerien") ||
                famille.includes("mecanique") ||
                famille.includes("montagne")
            ) {
                ajustement += 8;
            }
        }

        return this.limiter(ajustement, -35, 20);
    }

    calculerScoreSport(sport, profilNormalise) {
        if (!this.sportRespecteFiltresDurs(sport)) {
            return null;
        }

        const axes = this.scoreAxesSport(sport, profilNormalise);
        const famille = this.scoreFamilleSport(sport);
        const filtres = this.scoreFiltresSouples(sport);

        const scoreFinal = this.limiter(
            axes.score + famille.bonus - famille.exclusion + filtres,
            0,
            100
        );

        return {
            id: this.lireIdSport(sport),
            nom: this.lireNomSport(sport),
            famille: this.lireFamilleSport(sport),
            description: sport.description || "",
            compatibilite: this.arrondir(scoreFinal, 1),
            detailsAxes: axes.details,
            bonusFamille: famille.bonus,
            malusFamille: famille.exclusion,
            ajustementFiltres: filtres,
            explications: this.genererExplications(
                sport,
                profilNormalise,
                axes.details
            ),
            sport,
        };
    }

    calculerResultats(nombre = this.config.nombreResultats) {
        const profilNormalise = this.normaliserProfilUtilisateur();

        return this.sports
            .map((sport) =>
                this.calculerScoreSport(sport, profilNormalise)
            )
            .filter(Boolean)
            .sort((a, b) => {
                if (b.compatibilite !== a.compatibilite) {
                    return b.compatibilite - a.compatibilite;
                }

                return a.nom.localeCompare(b.nom, "fr");
            })
            .slice(0, nombre);
    }

    genererExplications(sport, profilNormalise, detailsAxes) {
        const libelles = {
            cardio: "correspond à votre niveau d'endurance recherché",
            force: "correspond à votre intérêt pour le renforcement",
            technique: "offre le niveau de technicité que vous recherchez",
            souplesse: "correspond à votre objectif de mobilité",
            equilibre: "développe l'équilibre selon vos préférences",
            coordination: "sollicite la coordination à un niveau adapté",
            contact: "respecte votre préférence concernant le contact",
            competition: "correspond à votre intérêt pour la compétition",
        };

        const meilleuresCorrespondances = Object.entries(detailsAxes)
            .sort(
                (a, b) =>
                    b[1].compatibilite - a[1].compatibilite
            )
            .slice(0, 3)
            .map(([axe]) => libelles[axe]);

        const explications = [...meilleuresCorrespondances];

        const famille = this.lireFamilleSport(sport);

        if (famille && Number(this.scoresFamilles[famille] || 0) > 0) {
            explications.push(
                `appartient à la famille « ${famille} », qui vous attire`
            );
        }

        return [...new Set(explications)].slice(0, 4);
    }

    questionnaireTermine() {
        return (
            this.questionsPosees.length >= this.config.minQuestions &&
            this.prochaineQuestion() === null
        );
    }

    obtenirEtat() {
        return {
            nombreQuestionsPosees: this.questionsPosees.length,
            minQuestions: this.config.minQuestions,
            maxQuestions: this.config.maxQuestions,
            termine: this.questionnaireTermine(),
            profilBrut: { ...this.profilUtilisateur },
            profilNormalise: this.normaliserProfilUtilisateur(),
            filtres: { ...this.filtres },
            scoresFamilles: { ...this.scoresFamilles },
            exclusionsFamilles: { ...this.exclusionsFamilles },
        };
    }

    exporterSession() {
        return JSON.stringify(
            {
                version: "1.0.0",
                reponses: this.reponses,
                questionsPosees: this.questionsPosees,
            },
            null,
            2
        );
    }

    importerSession(sessionJSON) {
        const session =
            typeof sessionJSON === "string"
                ? JSON.parse(sessionJSON)
                : sessionJSON;

        this.reponses = session.reponses || {};
        this.questionsPosees = Array.isArray(session.questionsPosees)
            ? session.questionsPosees
            : Object.keys(this.reponses);

        this.recalculerProfil();
    }

    sauvegarderSession(cle = "bouger_recommandation") {
        localStorage.setItem(cle, this.exporterSession());
    }

    chargerSession(cle = "bouger_recommandation") {
        const contenu = localStorage.getItem(cle);

        if (!contenu) {
            return false;
        }

        this.importerSession(contenu);
        return true;
    }

    supprimerSession(cle = "bouger_recommandation") {
        localStorage.removeItem(cle);
    }

    limiter(valeur, minimum, maximum) {
        return Math.min(Math.max(Number(valeur), minimum), maximum);
    }

    arrondir(valeur, decimales = 1) {
        const facteur = 10 ** decimales;
        return Math.round(Number(valeur) * facteur) / facteur;
    }
}

/**
 * Exemple d'utilisation :
 *
 * const moteur = new MoteurRecommandation();
 *
 * await moteur.initialiser();
 *
 * let question = moteur.prochaineQuestion();
 *
 * moteur.enregistrerReponse(question.id, "Oui");
 *
 * question = moteur.prochaineQuestion();
 *
 * const resultats = moteur.calculerResultats(10);
 * console.log(resultats);
 */

window.MoteurRecommandation = MoteurRecommandation;