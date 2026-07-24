"use strict";

/* =========================================================
   QUESTIONS DU JEU « SAUVE QUI PEUT »
   60 questions réparties dans plusieurs catégories.
========================================================= */

window.SAUVE_QUI_PEUT_QUESTIONS = [
    {
        "question": "Avant d'approcher une victime, quelle est la première chose à vérifier ?",
        "bonneReponse": "L'absence de danger",
        "mauvaisesReponses": [
            "Son identité",
            "Son âge",
            "Son groupe sanguin"
        ],
        "explication": "Il faut d'abord éviter de devenir soi-même une victime.",
        "categorie": "Protection"
    },
    {
        "question": "Si la zone reste dangereuse, que faut-il faire ?",
        "bonneReponse": "Alerter sans s'exposer",
        "mauvaisesReponses": [
            "Courir vers la victime",
            "Déplacer tout le matériel",
            "Attendre sans rien faire"
        ],
        "explication": "On ne doit intervenir que si cela peut être fait sans danger.",
        "categorie": "Protection"
    },
    {
        "question": "Sur un accident de la route, quel danger faut-il particulièrement surveiller ?",
        "bonneReponse": "La circulation",
        "mauvaisesReponses": [
            "La couleur des véhicules",
            "La météo de demain",
            "Le niveau de carburant"
        ],
        "explication": "La circulation peut provoquer un suraccident.",
        "categorie": "Protection"
    },
    {
        "question": "Près d'un câble électrique tombé au sol, que faut-il faire ?",
        "bonneReponse": "Rester à distance et alerter",
        "mauvaisesReponses": [
            "Le pousser avec le pied",
            "Le déplacer à la main",
            "Verser de l'eau dessus"
        ],
        "explication": "Un câble électrique peut rester sous tension et être mortel.",
        "categorie": "Protection"
    },
    {
        "question": "Face à de la fumée épaisse, quelle conduite est la plus sûre ?",
        "bonneReponse": "Ne pas entrer et alerter",
        "mauvaisesReponses": [
            "Entrer rapidement",
            "Ouvrir toutes les portes",
            "Chercher seul l'origine"
        ],
        "explication": "Les fumées peuvent intoxiquer très rapidement.",
        "categorie": "Protection"
    },
    {
        "question": "Quel numéro permet de joindre le SAMU en France ?",
        "bonneReponse": "15",
        "mauvaisesReponses": [
            "13",
            "17",
            "19"
        ],
        "explication": "Le 15 permet de joindre le SAMU.",
        "categorie": "Alerte"
    },
    {
        "question": "Quel numéro permet de joindre les sapeurs-pompiers en France ?",
        "bonneReponse": "18",
        "mauvaisesReponses": [
            "14",
            "16",
            "19"
        ],
        "explication": "Le 18 permet de joindre les sapeurs-pompiers.",
        "categorie": "Alerte"
    },
    {
        "question": "Quel est le numéro d'urgence européen ?",
        "bonneReponse": "112",
        "mauvaisesReponses": [
            "110",
            "113",
            "115"
        ],
        "explication": "Le 112 est le numéro d'urgence utilisable dans l'Union européenne.",
        "categorie": "Alerte"
    },
    {
        "question": "Quel numéro est accessible notamment par SMS pour les personnes sourdes ou malentendantes ?",
        "bonneReponse": "114",
        "mauvaisesReponses": [
            "111",
            "115",
            "118"
        ],
        "explication": "Le 114 est destiné aux personnes sourdes ou malentendantes.",
        "categorie": "Alerte"
    },
    {
        "question": "Lors d'un appel aux secours, quelle information est indispensable ?",
        "bonneReponse": "Le lieu exact",
        "mauvaisesReponses": [
            "La marque du téléphone",
            "La profession du témoin",
            "La couleur des vêtements"
        ],
        "explication": "Les secours doivent pouvoir localiser précisément l'intervention.",
        "categorie": "Alerte"
    },
    {
        "question": "Quand faut-il raccrocher avec les secours ?",
        "bonneReponse": "Quand ils le demandent",
        "mauvaisesReponses": [
            "Dès qu'ils répondent",
            "Après dix secondes",
            "Dès que l'adresse est donnée"
        ],
        "explication": "Il faut répondre aux questions et ne raccrocher que sur leur indication.",
        "categorie": "Alerte"
    },
    {
        "question": "Une personne ne répond pas. Que faut-il vérifier ensuite ?",
        "bonneReponse": "Sa respiration",
        "mauvaisesReponses": [
            "Son téléphone",
            "Ses papiers",
            "Sa pointure"
        ],
        "explication": "Chez une victime inconsciente, il faut vérifier rapidement si elle respire normalement.",
        "categorie": "Bilan"
    },
    {
        "question": "Pour vérifier la conscience, que peut-on faire ?",
        "bonneReponse": "Lui parler et lui demander un geste comme de nous serrer la main",
        "mauvaisesReponses": [
            "Lui donner à boire",
            "La laisser seule",
            "Lui faire marcher"
        ],
        "explication": "On parle à la victime et on lui demande d'effectuer un geste simple.",
        "categorie": "Bilan"
    },
    {
        "question": "Une respiration très irrégulière ou avec des gasps doit être considérée comme quoi ?",
        "bonneReponse": "Une respiration anormale",
        "mauvaisesReponses": [
            "Un sommeil normal",
            "Une toux efficace",
            "Un signe rassurant"
        ],
        "explication": "Une respiration anormale peut correspondre à un arrêt cardiaque.",
        "categorie": "Bilan"
    },
    {
        "question": "Une victime inconsciente respire normalement. Que faut-il faire ?",
        "bonneReponse": "La placer sur le côté (PLS) et surveiller",
        "mauvaisesReponses": [
            "La faire boire",
            "La laisser sur le dos sans surveillance",
            "La mettre debout"
        ],
        "explication": "La position latérale de sécurité aide à garder les voies aériennes dégagées.",
        "categorie": "Inconscience"
    },
    {
        "question": "Après avoir placé une victime inconsciente sur le côté, que faut-il surveiller ?",
        "bonneReponse": "Sa respiration",
        "mauvaisesReponses": [
            "Sa montre",
            "Ses chaussures",
            "Son téléphone"
        ],
        "explication": "La respiration doit être vérifiée régulièrement jusqu'à l'arrivée des secours.",
        "categorie": "Inconscience"
    },
    {
        "question": "Une victime inconsciente doit-elle recevoir à boire ?",
        "bonneReponse": "Non, jamais",
        "mauvaisesReponses": [
            "Oui, toujours",
            "Seulement du café",
            "Seulement une boisson sucrée"
        ],
        "explication": "Une personne inconsciente risque de s'étouffer si on lui donne à boire.",
        "categorie": "Inconscience"
    },
    {
        "question": "Une victime ne respire plus (et n'a plus de pouls). Que faut-il faire ?",
        "bonneReponse": "Alerter et commencer les compressions",
        "mauvaisesReponses": [
            "Attendre dix minutes",
            "La faire marcher",
            "Lui donner à boire"
        ],
        "explication": "Il faut alerter, commencer la réanimation et demander un défibrillateur.",
        "categorie": "Arrêt cardiaque"
    },
    {
        "question": "Où place-t-on les mains pour les compressions thoraciques chez l'adulte ?",
        "bonneReponse": "Au centre de la poitrine",
        "mauvaisesReponses": [
            "Sur le ventre",
            "Sur le cou",
            "Sur l'épaule"
        ],
        "explication": "Les compressions se réalisent au centre de la poitrine.",
        "categorie": "Arrêt cardiaque"
    },
    {
        "question": "Pendant les compressions, les bras doivent être comment ?",
        "bonneReponse": "Tendus",
        "mauvaisesReponses": [
            "Croisés",
            "Derrière le dos",
            "Complètement relâchés"
        ],
        "explication": "Des bras tendus permettent d'appuyer verticalement et efficacement.",
        "categorie": "Arrêt cardiaque"
    },
    {
        "question": "Que faut-il faire si un défibrillateur est disponible ?",
        "bonneReponse": "L'allumer et suivre ses consignes",
        "mauvaisesReponses": [
            "Attendre un médecin pour l'ouvrir",
            "Le poser sans l'allumer",
            "Retirer sa batterie"
        ],
        "explication": "Le défibrillateur guide vocalement le sauveteur.",
        "categorie": "Défibrillateur"
    },
    {
        "question": "Pendant l'analyse du défibrillateur, que faut-il faire ?",
        "bonneReponse": "Ne pas toucher la victime",
        "mauvaisesReponses": [
            "Continuer à la déplacer",
            "Lui tenir la main",
            "Verser de l'eau"
        ],
        "explication": "Personne ne doit toucher la victime pendant l'analyse.",
        "categorie": "Défibrillateur"
    },
    {
        "question": "Après un choc délivré par le défibrillateur, que faut-il généralement reprendre ?",
        "bonneReponse": "Les compressions thoraciques",
        "mauvaisesReponses": [
            "La marche",
            "Un repas",
            "La prise de température"
        ],
        "explication": "Il faut suivre les consignes de l'appareil et reprendre la réanimation.",
        "categorie": "Défibrillateur"
    },
    {
        "question": "Une personne tousse efficacement pendant un étouffement. Que faire ?",
        "bonneReponse": "L'encourager à tousser",
        "mauvaisesReponses": [
            "La coucher",
            "Lui donner à boire",
            "Faire immédiatement des compressions"
        ],
        "explication": "Une toux efficace doit être encouragée et surveillée.",
        "categorie": "Étouffement"
    },
    {
        "question": "Quel signe évoque un étouffement grave ?",
        "bonneReponse": "La personne ne peut plus parler",
        "mauvaisesReponses": [
            "Elle parle normalement",
            "Elle rit",
            "Elle demande à boire"
        ],
        "explication": "L'impossibilité de parler ou de tousser efficacement est un signe de gravité.",
        "categorie": "Étouffement"
    },
    {
        "question": "Lors d'un étouffement grave (la victime ne peut plus tousser seule) chez un adulte conscient, quel geste vient en premier ?",
        "bonneReponse": "Des claques dans le dos",
        "mauvaisesReponses": [
            "Un verre d'eau",
            "Le faire courir",
            "Le coucher immédiatement"
        ],
        "explication": "On réalise d'abord des claques vigoureuses dans le dos.",
        "categorie": "Étouffement"
    },
    {
        "question": "Si les claques dans le dos sont inefficaces, que peut-on alterner ?",
        "bonneReponse": "Avec des compressions abdominales (Heimlich)",
        "mauvaisesReponses": [
            "Avec des boissons",
            "Avec des étirements",
            "Avec des massages des jambes"
        ],
        "explication": "Chez l'adulte conscient, on alterne claques dans le dos et compressions abdominales.",
        "categorie": "Étouffement"
    },
    {
        "question": "Une personne qui s'étouffe devient inconsciente, ne respire plus, n'a pas de pouls. Que faut-il faire ?",
        "bonneReponse": "L'allonger, alerter et réanimer",
        "mauvaisesReponses": [
            "La faire asseoir",
            "Lui donner du pain",
            "Attendre qu'elle se réveille"
        ],
        "explication": "Une perte de connaissance avec absence de respiration normale impose une réanimation.",
        "categorie": "Étouffement"
    },
    {
        "question": "Face à un saignement abondant accessible, quel est le premier geste ?",
        "bonneReponse": "Comprimer directement la plaie",
        "mauvaisesReponses": [
            "Faire marcher la victime",
            "Rincer pendant longtemps",
            "Attendre sans toucher"
        ],
        "explication": "Une compression directe aide à arrêter rapidement le saignement.",
        "categorie": "Hémorragie"
    },
    {
        "question": "Pour comprimer une plaie, que peut-on utiliser ?",
        "bonneReponse": "Un tissu propre ou une protection",
        "mauvaisesReponses": [
            "De la terre",
            "Un objet pointu",
            "Du papier journal sale"
        ],
        "explication": "Une protection limite le contact direct avec le sang.",
        "categorie": "Hémorragie"
    },
    {
        "question": "Une victime saigne abondamment. Quelle position est généralement adaptée ?",
        "bonneReponse": "Allongée",
        "mauvaisesReponses": [
            "Debout",
            "En train de courir",
            "Sur une chaise haute"
        ],
        "explication": "L'allonger réduit le risque de chute et aide à prévenir l'aggravation.",
        "categorie": "Hémorragie"
    },
    {
        "question": "Si un objet est planté dans une plaie, que faut-il faire ?",
        "bonneReponse": "Ne pas le retirer",
        "mauvaisesReponses": [
            "Le retirer rapidement",
            "Le tourner",
            "L'enfoncer davantage"
        ],
        "explication": "Le retrait pourrait aggraver le saignement ou les lésions.",
        "categorie": "Plaies"
    },
    {
        "question": "Après contact avec du sang, quel geste d'hygiène est important ?",
        "bonneReponse": "Se laver les mains",
        "mauvaisesReponses": [
            "Toucher son visage",
            "Manger immédiatement",
            "Partager une serviette"
        ],
        "explication": "Il faut nettoyer soigneusement les zones exposées.",
        "categorie": "Hémorragie"
    },
    {
        "question": "Quel est le premier réflexe face à une brûlure thermique récente ?",
        "bonneReponse": "La refroidir sous l'eau tempérée",
        "mauvaisesReponses": [
            "Mettre du beurre",
            "Appliquer de la glace directement",
            "Percer les cloques"
        ],
        "explication": "L'eau tempérée limite l'aggravation de la brûlure.",
        "categorie": "Brûlure"
    },
    {
        "question": "Combien de temps faut-il idéalement refroidir une brûlure ?",
        "bonneReponse": "Environ 15-20 minutes",
        "mauvaisesReponses": [
            "Quelques secondes",
            "Une minute maximum",
            "Toute la journée"
        ],
        "explication": "Un refroidissement prolongé, idéalement vingt minutes, aide à limiter les lésions.",
        "categorie": "Brûlure"
    },
    {
        "question": "Que faut-il éviter sur une brûlure ?",
        "bonneReponse": "La glace directement",
        "mauvaisesReponses": [
            "L'eau tempérée",
            "Une protection propre",
            "L'avis des secours"
        ],
        "explication": "La glace peut aggraver les lésions cutanées.",
        "categorie": "Brûlure"
    },
    {
        "question": "Faut-il percer les cloques d'une brûlure ?",
        "bonneReponse": "Non",
        "mauvaisesReponses": [
            "Oui, toujours",
            "Oui, avec une aiguille sale",
            "Seulement pour les grandes"
        ],
        "explication": "Les cloques protègent la peau et ne doivent pas être percées.",
        "categorie": "Brûlure"
    },
    {
        "question": "Une brûlure étendue ou située sur le visage nécessite quoi ?",
        "bonneReponse": "Un avis urgent des secours",
        "mauvaisesReponses": [
            "Un simple parfum",
            "Une promenade",
            "Aucune surveillance"
        ],
        "explication": "Certaines localisations ou étendues rendent une brûlure grave.",
        "categorie": "Brûlure"
    },
    {
        "question": "Une personne ressent une forte douleur dans la poitrine. Que faut-il faire ?",
        "bonneReponse": "L'installer au repos et alerter",
        "mauvaisesReponses": [
            "La faire courir",
            "Lui faire porter une charge",
            "Attendre plusieurs heures"
        ],
        "explication": "Une douleur thoracique peut annoncer une urgence cardiaque.",
        "categorie": "Malaise"
    },
    {
        "question": "Face à un malaise, quelle question est utile ?",
        "bonneReponse": "Depuis quand les signes ont commencé",
        "mauvaisesReponses": [
            "Quelle est sa couleur préférée",
            "Quel film elle aime",
            "Quelle marque elle porte"
        ],
        "explication": "L'heure de début des symptômes est une information importante pour les secours.",
        "categorie": "Malaise"
    },
    {
        "question": "Une personne présente soudain un visage asymétrique et parle difficilement. Que faut-il suspecter ?",
        "bonneReponse": "Un AVC",
        "mauvaisesReponses": [
            "Une simple fatigue certaine",
            "Une entorse",
            "Une brûlure"
        ],
        "explication": "Une asymétrie du visage et un trouble de la parole peuvent évoquer un AVC.",
        "categorie": "Malaise"
    },
    {
        "question": "En cas de suspicion d'AVC, quelle conduite adopter ?",
        "bonneReponse": "Alerter immédiatement",
        "mauvaisesReponses": [
            "Attendre le lendemain",
            "Faire marcher la personne",
            "Lui donner un repas"
        ],
        "explication": "La rapidité de prise en charge est essentielle.",
        "categorie": "Malaise"
    },
    {
        "question": "Une personne diabétique consciente dit faire une hypoglycémie. Que peut-on faire en attendant les secours ?",
        "bonneReponse": "Suivre ses habitudes si elle peut avaler (sucre)",
        "mauvaisesReponses": [
            "La forcer à marcher",
            "Lui donner quelque chose si elle est inconsciente",
            "La laisser seule"
        ],
        "explication": "Une personne consciente peut suivre son protocole habituel, sans jamais faire avaler une victime inconsciente.",
        "categorie": "Malaise"
    },
    {
        "question": "Pendant une crise convulsive, que faut-il faire en priorité ?",
        "bonneReponse": "Écarter les objets dangereux",
        "mauvaisesReponses": [
            "Bloquer fortement ses mouvements",
            "Mettre un objet dans sa bouche",
            "Lui donner à boire"
        ],
        "explication": "Il faut protéger la personne des blessures sans entraver ses mouvements.",
        "categorie": "Convulsions"
    },
    {
        "question": "Pendant une convulsion, faut-il mettre un objet dans la bouche ?",
        "bonneReponse": "Non, jamais",
        "mauvaisesReponses": [
            "Oui, toujours",
            "Seulement une cuillère",
            "Seulement un stylo"
        ],
        "explication": "Cela peut provoquer des blessures ou obstruer les voies aériennes.",
        "categorie": "Convulsions"
    },
    {
        "question": "Après une convulsion, si la personne respire mais reste inconsciente, que faire ?",
        "bonneReponse": "La placer sur le côté et surveiller",
        "mauvaisesReponses": [
            "La mettre debout",
            "La faire boire",
            "La laisser seule"
        ],
        "explication": "Il faut protéger les voies aériennes et surveiller la respiration.",
        "categorie": "Convulsions"
    },
    {
        "question": "Une personne a reçu un choc violent au cou ou au dos. Que faut-il éviter ?",
        "bonneReponse": "La déplacer s'il n'y a pas de danger immédiat",
        "mauvaisesReponses": [
            "La rassurer",
            "Alerter les secours",
            "Surveiller sa respiration"
        ],
        "explication": "Un déplacement inutile peut aggraver une lésion de la colonne vertébrale.",
        "categorie": "Traumatisme"
    },
    {
        "question": "En cas de suspicion de fracture d'un membre, que faut-il faire ?",
        "bonneReponse": "Éviter de mobiliser le membre",
        "mauvaisesReponses": [
            "Le remettre en place",
            "Le faire bouger plusieurs fois",
            "Faire courir la victime"
        ],
        "explication": "Il ne faut pas tenter de réaligner ou de mobiliser une fracture.",
        "categorie": "Traumatisme"
    },
    {
        "question": "Après un choc à la tête, quel signe impose une alerte urgente ?",
        "bonneReponse": "Une perte de connaissance",
        "mauvaisesReponses": [
            "Une chaussure sale",
            "Un vêtement froissé",
            "Une légère faim"
        ],
        "explication": "Une perte de connaissance après un traumatisme crânien est un signe de gravité.",
        "categorie": "Traumatisme"
    },
    {
        "question": "En cas de projection chimique dans l'œil, quel est le premier geste ?",
        "bonneReponse": "Rincer abondamment à l'eau",
        "mauvaisesReponses": [
            "Frotter l'œil",
            "Mettre une crème",
            "Fermer l'œil toute la journée"
        ],
        "explication": "Un rinçage immédiat et prolongé aide à éliminer le produit.",
        "categorie": "Accident domestique"
    },
    {
        "question": "En cas d'ingestion d'un produit toxique, faut-il faire vomir la personne ?",
        "bonneReponse": "Non, sauf instruction médicale",
        "mauvaisesReponses": [
            "Oui, systématiquement",
            "Oui, avec de l'eau salée",
            "Oui, en la faisant courir"
        ],
        "explication": "Faire vomir peut aggraver les lésions ; il faut appeler les secours ou un centre antipoison.",
        "categorie": "Intoxication"
    },
    {
        "question": "Face à une intoxication présumée, quel objet peut être utile aux secours ?",
        "bonneReponse": "L'emballage du produit",
        "mauvaisesReponses": [
            "Une photo de vacances",
            "Une chaussure",
            "Un livre"
        ],
        "explication": "L'emballage aide à identifier précisément le produit.",
        "categorie": "Intoxication"
    },
    {
        "question": "En cas de suspicion d'intoxication au monoxyde de carbone, que faut-il faire ?",
        "bonneReponse": "Sortir sans s'exposer et alerter",
        "mauvaisesReponses": [
            "Rester dormir",
            "Allumer une flamme",
            "Chercher longtemps la fuite"
        ],
        "explication": "Il faut quitter les lieux si possible sans danger et prévenir les secours.",
        "categorie": "Intoxication"
    },
    {
        "question": "Une personne est sortie de l'eau et ne respire plus (et on ne sent pas le pouls). Que faut-il faire ?",
        "bonneReponse": "Alerter et commencer la réanimation",
        "mauvaisesReponses": [
            "La suspendre par les pieds",
            "Attendre qu'elle tousse",
            "Lui donner à boire"
        ],
        "explication": "L'absence de respiration normale nécessite une réanimation immédiate.",
        "categorie": "Noyade"
    },
    {
        "question": "Pour secourir une personne dans l'eau, quelle règle est essentielle ?",
        "bonneReponse": "Ne pas se mettre soi-même en danger",
        "mauvaisesReponses": [
            "Plonger sans réfléchir",
            "Nager seul de nuit",
            "Retirer son moyen de flottaison"
        ],
        "explication": "Un sauvetage aquatique ne doit pas créer une seconde victime.",
        "categorie": "Noyade"
    },
    {
        "question": "En présence d'un départ de feu, quel numéro peut-on appeler ?",
        "bonneReponse": "18 ou 112",
        "mauvaisesReponses": [
            "13 uniquement",
            "16 uniquement",
            "19 uniquement"
        ],
        "explication": "Les pompiers sont joignables au 18 et les urgences européennes au 112.",
        "categorie": "Incendie"
    },
    {
        "question": "Dans un bâtiment enfumé, pourquoi faut-il rester près du sol si l'évacuation est possible ?",
        "bonneReponse": "L'air y est souvent moins enfumé",
        "mauvaisesReponses": [
            "Le sol est plus chaud",
            "Pour mieux courir",
            "Pour chercher des objets"
        ],
        "explication": "La fumée et les gaz chauds montent généralement.",
        "categorie": "Incendie"
    },
    {
        "question": "Si une porte est très chaude pendant un incendie, que faut-il faire ?",
        "bonneReponse": "Ne pas l'ouvrir",
        "mauvaisesReponses": [
            "L'ouvrir brusquement",
            "La frapper avec le pied",
            "Verser de l'huile dessus"
        ],
        "explication": "Une porte chaude peut cacher un feu important derrière elle.",
        "categorie": "Incendie"
    },
    {
        "question": "Lors d'une évacuation incendie, faut-il utiliser l'ascenseur ?",
        "bonneReponse": "Non",
        "mauvaisesReponses": [
            "Oui, toujours",
            "Oui, si on est pressé",
            "Oui, pour descendre plus vite"
        ],
        "explication": "Un ascenseur peut tomber en panne ou s'ouvrir sur une zone enfumée.",
        "categorie": "Incendie"
    },
    {
        "question": "Après avoir appelé les secours, que faut-il faire avec une victime consciente ?",
        "bonneReponse": "La rassurer et la surveiller",
        "mauvaisesReponses": [
            "La laisser seule",
            "Lui faire peur",
            "L'obliger à marcher"
        ],
        "explication": "Une présence calme permet de surveiller toute aggravation.",
        "categorie": "Surveillance"
    }
];