/* ==========================================================
   sons.js
   Gestion centralisée des sons du site
   ========================================================== */

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

/* -----------------------------
   Réglages généraux
------------------------------ */

Object.values(Sons).forEach(son => {
    son.preload = "auto";
});

/* -----------------------------
   Jouer un son
------------------------------ */

function jouerSon(nom, volume = 1) {

    const son = Sons[nom];

    if (!son)
        return;

    son.pause();
    son.currentTime = 0;
    son.volume = volume;

    son.play().catch(() => {});
}

/* -----------------------------
   Jouer sans couper le précédent
------------------------------ */

function jouerSonMultiple(nom, volume = 1) {

    const original = Sons[nom];

    if (!original)
        return;

    const son = original.cloneNode();

    son.volume = volume;

    son.play().catch(() => {});
}

/* -----------------------------
   Arrêter un son
------------------------------ */

function arreterSon(nom) {

    const son = Sons[nom];

    if (!son)
        return;

    son.pause();
    son.currentTime = 0;
}

/* -----------------------------
   Arrêter tous les sons
------------------------------ */

function arreterTousLesSons() {

    Object.values(Sons).forEach(son => {
        son.pause();
        son.currentTime = 0;
    });

}

/* -----------------------------
   Modifier le volume d'un son
------------------------------ */

function volumeSon(nom, volume) {

    if (Sons[nom])
        Sons[nom].volume = volume;

}

/* -----------------------------
   Modifier le volume global
------------------------------ */

function volumeGlobal(volume) {

    Object.values(Sons).forEach(son => {
        son.volume = volume;
    });

}