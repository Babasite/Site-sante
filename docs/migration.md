# Plan de migration

## Règle principale

Ne pas déplacer tous les fichiers simultanément. Après chaque lot : lancer le serveur, vérifier les pages et exécuter les tests.

## Ordre conseillé

1. Initialiser Git et sauvegarder la base de données.
2. Préparer `requirements/`, `.env.example` et les paramètres Django.
3. Migrer les fichiers statiques globaux.
4. Migrer les layouts et composants de templates.
5. Migrer les pages sans modèle de données.
6. Séparer les vues, formulaires et URL par application.
7. Déplacer les services métier.
8. Déplacer les modèles et leurs données en dernier.
9. Mettre à jour les tests.
10. Valider la nouvelle application avant de supprimer l'ancienne organisation.

## Attention aux modèles Django

Déplacer une classe de modèle d'une application à une autre change son `app_label` et peut provoquer la création de nouvelles tables. Une migration de données contrôlée sera nécessaire.
