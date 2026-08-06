# Nouvelle architecture — migration progressive

Le dossier `Site-sante` reste le projet principal à ouvrir dans VS Code.

## État actuel

- Le projet existant reste fonctionnel à la racine (`manage.py`, `config`, `accueil`, etc.).
- La nouvelle ossature est ajoutée autour (`apps`, `templates`, `static`, `tests`, `docs`, etc.).
- Une copie intégrale de l'organisation d'origine se trouve dans `ancienne_organisation/Site-sante`.
- Aucun contenu métier existant n'a été déplacé ou modifié.

## Important

Le fichier actuel `config/settings.py` reste en place afin de ne pas casser Django.
La séparation future en `config/settings/base.py`, `development.py`, `production.py` et `test.py` sera faite pendant une étape dédiée, avec adaptation de `manage.py`, `wsgi.py` et `asgi.py`.

## Commande de lancement actuelle

Depuis ce dossier :

```bash
python manage.py runserver
```

La migration vers `apps/` devra être progressive et testée après chaque déplacement.
