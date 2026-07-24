# Architecture cible

Le projet suit un monolithe Django modulaire : un seul projet et plusieurs applications métier.

## Applications

- `core` : pages et fonctionnalités réellement partagées.
- `accounts` : authentification, profils, rôles et permissions.
- `content` : pages et contenus éditoriaux.
- `monitoring` : veille scientifique, collecte, classification, traduction et exports.
- `recommendations` : questionnaires et moteur de recommandation.
- `tools` : outils interactifs indépendants.

## Principes

1. Une fonctionnalité métier appartient à une seule application.
2. `core` ne doit pas devenir un dossier fourre-tout.
3. Les traitements métier vont dans `services/`.
4. Les requêtes de lecture complexes vont dans `selectors/`.
5. Les traitements différés futurs vont dans `tasks/`.
6. Les templates globaux vont dans `templates/`; les pages métier restent dans leur application.
7. Les fichiers générés vont dans `var/` et ne sont pas versionnés.
8. Les données privées ou serveur ne doivent pas être placées dans `static/`.
