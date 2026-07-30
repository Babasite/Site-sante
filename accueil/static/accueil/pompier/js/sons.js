/* ==========================================================
   sons.js
   Gestion centralisée des sons du site
   ========================================================== */

(() => {
    "use strict";

    /* ----------------------------------------------------------
       Liste des sons disponibles
       ---------------------------------------------------------- */

    const Sons = {
        clic: new Audio("/static/accueil/sons/clic.mp3"),
        bonneReponse: new Audio("/static/accueil/sons/bonne_reponse.mp3"),
        mauvaiseReponse: new Audio("/static/accueil/sons/mauvaise_reponse.mp3"),
        victoire: new Audio("/static/accueil/sons/victoire.mp3"),
        defaite: new Audio("/static/accueil/sons/defaite.mp3"),
        bonus: new Audio("/static/accueil/sons/bonus.mp3"),
        explosion: new Audio("/static/accueil/sons/explosion.mp3"),
        erreur: new Audio("/static/accueil/sons/erreur.mp3"),
        chrono: new Audio("/static/accueil/sons/chrono.mp3"),
        niveau: new Audio("/static/accueil/sons/niveau.mp3")
    };

    /* ----------------------------------------------------------
       Volume général
       Valeur comprise entre 0 et 1
       ---------------------------------------------------------- */

    let volumeGeneral = 1;

    /* ----------------------------------------------------------
       État sonore général
       ---------------------------------------------------------- */

    let sonsActives = true;

    /* ----------------------------------------------------------
       Sécuriser une valeur de volume entre 0 et 1
       ---------------------------------------------------------- */

    function normaliserVolume(volume) {
        const valeur = Number(volume);

        if (Number.isNaN(valeur)) {
            return 1;
        }

        return Math.min(1, Math.max(0, valeur));
    }

    /* ----------------------------------------------------------
       Préchargement et réglages initiaux
       ---------------------------------------------------------- */

    Object.values(Sons).forEach((son) => {
        son.preload = "auto";
        son.volume = volumeGeneral;

        try {
            son.load();
        } catch (erreur) {
            console.warn("Impossible de précharger un son :", erreur);
        }
    });

    /* ----------------------------------------------------------
       Vérifier qu'un son existe
       ---------------------------------------------------------- */

    function obtenirSon(nom) {
        const son = Sons[nom];

        if (!son) {
            console.warn(`Son inconnu : ${nom}`);
            return null;
        }

        return son;
    }

    /* ----------------------------------------------------------
       Jouer un son en recommençant depuis le début

       Exemples :
       jouerSon("clic");
       jouerSon("explosion", 0.6);
       ---------------------------------------------------------- */

    function jouerSon(nom, volume = 1) {
        if (!sonsActives) {
            return;
        }

        const son = obtenirSon(nom);

        if (!son) {
            return;
        }

        const volumeFinal =
            normaliserVolume(volume) * normaliserVolume(volumeGeneral);

        son.pause();
        son.currentTime = 0;
        son.volume = volumeFinal;

        const lecture = son.play();

        if (lecture !== undefined) {
            lecture.catch((erreur) => {
                /*
                 * Les navigateurs peuvent bloquer les sons avant
                 * la première interaction de l'utilisateur.
                 */
                console.debug(
                    `Lecture du son "${nom}" bloquée ou impossible :`,
                    erreur
                );
            });
        }
    }

    /* ----------------------------------------------------------
       Jouer un son sans couper une lecture déjà en cours

       Recommandé pour :
       - les tirs rapides ;
       - les explosions ;
       - plusieurs bonus successifs.

       Exemples :
       jouerSonMultiple("clic", 0.3);
       jouerSonMultiple("explosion", 0.7);
       ---------------------------------------------------------- */

    function jouerSonMultiple(nom, volume = 1) {
        if (!sonsActives) {
            return;
        }

        const original = obtenirSon(nom);

        if (!original) {
            return;
        }

        const son = original.cloneNode(true);

        son.volume =
            normaliserVolume(volume) * normaliserVolume(volumeGeneral);

        const lecture = son.play();

        if (lecture !== undefined) {
            lecture.catch((erreur) => {
                console.debug(
                    `Lecture multiple du son "${nom}" impossible :`,
                    erreur
                );
            });
        }

        /*
         * Une fois terminé, le clone peut être libéré
         * automatiquement par le navigateur.
         */
        son.addEventListener(
            "ended",
            () => {
                son.remove();
            },
            { once: true }
        );
    }

    /* ----------------------------------------------------------
       Jouer un son en boucle

       Exemple :
       jouerSonEnBoucle("chrono", 0.4);
       ---------------------------------------------------------- */

    function jouerSonEnBoucle(nom, volume = 1) {
        if (!sonsActives) {
            return;
        }

        const son = obtenirSon(nom);

        if (!son) {
            return;
        }

        son.pause();
        son.currentTime = 0;
        son.loop = true;
        son.volume =
            normaliserVolume(volume) * normaliserVolume(volumeGeneral);

        const lecture = son.play();

        if (lecture !== undefined) {
            lecture.catch((erreur) => {
                console.debug(
                    `Lecture en boucle du son "${nom}" impossible :`,
                    erreur
                );
            });
        }
    }

    /* ----------------------------------------------------------
       Arrêter un son
       ---------------------------------------------------------- */

    function arreterSon(nom) {
        const son = obtenirSon(nom);

        if (!son) {
            return;
        }

        son.pause();
        son.currentTime = 0;
        son.loop = false;
    }

    /* ----------------------------------------------------------
       Mettre un son en pause sans revenir au début
       ---------------------------------------------------------- */

    function pauseSon(nom) {
        const son = obtenirSon(nom);

        if (!son) {
            return;
        }

        son.pause();
    }

    /* ----------------------------------------------------------
       Reprendre un son mis en pause
       ---------------------------------------------------------- */

    function reprendreSon(nom) {
        if (!sonsActives) {
            return;
        }

        const son = obtenirSon(nom);

        if (!son) {
            return;
        }

        const lecture = son.play();

        if (lecture !== undefined) {
            lecture.catch((erreur) => {
                console.debug(
                    `Reprise du son "${nom}" impossible :`,
                    erreur
                );
            });
        }
    }

    /* ----------------------------------------------------------
       Arrêter tous les sons
       ---------------------------------------------------------- */

    function arreterTousLesSons() {
        Object.values(Sons).forEach((son) => {
            son.pause();
            son.currentTime = 0;
            son.loop = false;
        });
    }

    /* ----------------------------------------------------------
       Modifier le volume d'un son précis
       ---------------------------------------------------------- */

    function volumeSon(nom, volume) {
        const son = obtenirSon(nom);

        if (!son) {
            return;
        }

        son.volume =
            normaliserVolume(volume) * normaliserVolume(volumeGeneral);
    }

    /* ----------------------------------------------------------
       Modifier le volume général
       ---------------------------------------------------------- */

    function volumeGlobal(volume) {
        volumeGeneral = normaliserVolume(volume);

        Object.values(Sons).forEach((son) => {
            son.volume = volumeGeneral;
        });
    }

    /* ----------------------------------------------------------
       Activer les sons
       ---------------------------------------------------------- */

    function activerSons() {
        sonsActives = true;
    }

    /* ----------------------------------------------------------
       Désactiver les sons
       ---------------------------------------------------------- */

    function desactiverSons() {
        sonsActives = false;
        arreterTousLesSons();
    }

    /* ----------------------------------------------------------
       Activer ou désactiver les sons
       Retourne true lorsque les sons sont activés
       ---------------------------------------------------------- */

    function basculerSons() {
        sonsActives = !sonsActives;

        if (!sonsActives) {
            arreterTousLesSons();
        }

        return sonsActives;
    }

    /* ----------------------------------------------------------
       Savoir si les sons sont activés
       ---------------------------------------------------------- */

    function sonsSontActives() {
        return sonsActives;
    }

    /* ----------------------------------------------------------
       Exposer les fonctions aux autres scripts du site
       ---------------------------------------------------------- */

    window.Sons = Sons;

    window.jouerSon = jouerSon;
    window.jouerSonMultiple = jouerSonMultiple;
    window.jouerSonEnBoucle = jouerSonEnBoucle;

    window.arreterSon = arreterSon;
    window.arreterTousLesSons = arreterTousLesSons;

    window.pauseSon = pauseSon;
    window.reprendreSon = reprendreSon;

    window.volumeSon = volumeSon;
    window.volumeGlobal = volumeGlobal;

    window.activerSons = activerSons;
    window.desactiverSons = desactiverSons;
    window.basculerSons = basculerSons;
    window.sonsSontActives = sonsSontActives;
})();