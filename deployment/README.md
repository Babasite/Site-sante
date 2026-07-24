# Déploiement

Le projet est préparé pour fonctionner sans service d'intelligence artificielle et sans dépendre d'un hébergeur particulier.

## Développement local

```bash
python -m venv .venv
# Windows : .venv\\Scripts\\activate
# Linux/macOS : source .venv/bin/activate
pip install -r requirements/development.txt
python manage.py migrate
python manage.py runserver
```

Les réglages locaux sont sélectionnés par défaut. Le fichier `.env.example` documente les variables disponibles.

## Production

Variables minimales :

```text
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=<clé longue et aléatoire>
DJANGO_ALLOWED_HOSTS=<domaine>
DATABASE_URL=<URL PostgreSQL, facultative si SQLite est volontairement conservée>
```

Commandes habituelles :

```bash
pip install -r requirements/production.txt
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn config.wsgi:application
```

WhiteNoise sert les fichiers statiques. PostgreSQL est pris en charge via `DATABASE_URL`, tandis que SQLite reste disponible pour un hébergement très simple ou le développement.
