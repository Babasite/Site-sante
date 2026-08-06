# Architecture des applications

Chaque dossier de `apps/` correspond à une application Django indépendante. ("Veille" et "Carte des Pays")

---

## account

Gestion des utilisateurs :
- authentification ;
- profils ;
- permissions.

---

## core

Fonctions communes partagées entre plusieurs applications.

Une fonction est déplacée dans `core` uniquement lorsqu'elle est utilisée par plusieurs apps.

---

## monitoring ++

Veille scientifique.

Responsabilités :
- lancement de la veille (`lancerveille.py`) ;
- collecte des données ;
- classification des articles ;
- génération des résumés ;
- export des résultats.

Le dossier `services/` contient toute la logique métier de la veille.

---

## pays ++

Gestion des fiches pays.

Responsabilités :
- données JSON ;
- calcul de l'indice SPT ;
- graphiques ;
- espèces sentinelles ;
- recommandations ;
- affichage des fiches.

---

# Règles d'organisation

- Une fonctionnalité spécifique reste dans son app.
- Une fonction utilisée par plusieurs apps est déplacée dans `core`.
- Les données propres à une app restent dans son dossier `data/`.
- Les noms des dossiers Python restent simples (`services`, `views`, `models`, etc.).
- La documentation et les remarques sont écrites dans des fichiers `README.md`.