# Templates de l'application Accueil

Ce dossier contient les pages HTML affichées par Django.
Parfois les noms donnés sont différents des Views et Urls. 

## Structure générale

- `base.html` : structure commune du site, utilisée par les autres pages.
- `includes/` : petits éléments HTML réutilisés dans plusieurs pages.

---

## Pages principales

- `home.html` : page d'accueil principale "Santé Prévention Terrain".
- `notice.html` : page "accueil" appelée par la vue `notice`.
- `outils.html` : présentation des outils santés proposés.
- `terrain.html` : page d'accès aux Conseils et carte des pays.
- `apropos.html` : présentation du concepteur du site.
- `contact.html` : formulaire de contact.

---

## Terrain                 **IMPORTANT**

- `pompier.html` : page « Sauver », appelée par la vue `sauver.py`.

- `karate.html` : page « Bouger », appelé par la vue `bouger.py`.
- `miam.html` : page « Manger », appelé par la vue `miam.py`.

Pour les autres, les noms correspondent.

---

## Veille            

- La Veille est continuée dans `Apps/monitoring/service/classification` . Ses urls et views y sont. 

---

## Carte Pays

- La carte des Pays est continuée dans `Apps/pays` . Les urls concernant le développement poussé y sont.

