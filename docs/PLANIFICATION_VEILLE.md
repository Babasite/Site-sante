# Planification automatique de la veille

Le projet contient la commande Django suivante :

```bash
python manage.py lancer_veille_quotidienne
```

Elle peut être appelée régulièrement sans créer de doublon :

- avant l'heure prévue, elle ne fait rien ;
- après l'heure prévue, elle lance la veille si aucune veille terminée n'existe aujourd'hui ;
- si le serveur ou le planificateur était indisponible à l'heure prévue, le prochain passage lance la veille ;
- si une veille est déjà en cours, elle ne lance pas une seconde exécution.

L'heure par défaut est 07:00, dans le fuseau Django (`Europe/Paris`). Pour la modifier :

```env
VEILLE_HEURE_AUTO=8
```

## Test manuel

```bash
python manage.py lancer_veille_quotidienne --heure 0
```

Pour forcer une exécution même si une veille existe déjà aujourd'hui :

```bash
python manage.py lancer_veille_quotidienne --force
```

## Cron Linux

Exécuter la vérification toutes les heures :

```cron
5 * * * * cd /chemin/vers/Site-sante && /chemin/vers/python manage.py lancer_veille_quotidienne >> var/logs/veille.log 2>&1
```

L'exécution horaire est volontaire : elle permet le rattrapage automatique après une indisponibilité.

## Hébergeur avec tâches planifiées

Créer une tâche planifiée exécutée toutes les heures avec la commande :

```bash
python manage.py lancer_veille_quotidienne
```

Ajouter `VEILLE_HEURE_AUTO` aux variables d'environnement de l'hébergeur.
