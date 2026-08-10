# Où j'en suis – Santé Prévention Terrain
#, ##, -, **...** : Syntaxe simple qui permet d'obtenir des titres, des listes et du texte en gras dans les outils qui affichent le Markdown (.md). Plus intéressant pour documentation que simple .txt
## 27/07/2026
#### Création du journal de bord
Aujourd'hui, je commence la rédaction du journal de bord du projet **Santé Prévention Terrain**.
Le projet a été créé le **8 juillet 2026** avec pour objectif de développer un site consacré à la santé, à la prévention et à la vie quotidienne, en proposant des contenus utiles, des outils interactifs et une veille scientifique destinée à rendre les connaissances accessibles.
Ce document a pour but de conserver une trace de l'évolution du projet, des choix techniques et des décisions prises au fil du développement.
---
## État actuel du projet
À ce jour, le projet est déjà bien avancé.
### Structure générale
Le site est développé avec **Django**.
Une architecture modulaire est progressivement mise en place tout en conservant le fonctionnement actuel afin de ne pas casser les fonctionnalités existantes.
Le projet est suivi avec **Git**, ce qui permet de conserver l'historique des développements.
---
### Identité graphique
Une identité visuelle a été définie.
Palette officielle :

* Vert foncé : `#214C35`
* Turquoise : `#008080`
* Bleu principal : `#2B6FB8`
* Bleu secondaire : `#2F80C9`
* Beige : `#EFE3C3`

Cette palette sera utilisée sur l'ensemble du site afin de conserver une identité graphique cohérente.
---
### Fonctionnalités déjà présentes
Le projet comprend notamment :
* une page d'accueil personnalisée ;
* un logo et une identité visuelle ;
* plusieurs rubriques consacrées à la santé et à la prévention ;
* une rubrique consacrée aux gestes de secours ;
* plusieurs jeux pédagogiques ;
* une rubrique autour de l'activité physique ;
* des outils destinés à faciliter la vie quotidienne ;
* une veille scientifique avec stockage des articles en base de données ;
* un espace rédacteur protégé permettant la gestion des veilles et des traductions ;
* un export PDF des veilles.
---
### Orientation du projet
Le site est conçu pour évoluer progressivement.
L'objectif est de proposer une plateforme réunissant :
* des conseils de prévention ;
* des informations scientifiques fiables ;
* des outils pratiques ;
* des jeux éducatifs ;
* une approche globale de la santé.
---
## Documentation
À partir d'aujourd'hui, le dossier `docs/` devient la documentation officielle du projet.
Les documents qui seront progressivement créés permettront de décrire :
* l'architecture ;
* les différentes applications Django ;
* la base de données ;
* la veille scientifique ;
* les outils ;
* la charte graphique ;
* les procédures d'installation et de déploiement.
---
## Prochaines étapes
Les prochaines évolutions seront ajoutées dans ce fichier sans supprimer les anciennes entrées.
Chaque séance de développement donnera lieu à une nouvelle section datée afin de conserver un historique complet de l'évolution du projet.

## 28/07/2026

### Amélioration de l'interface de la veille scientifique

Cette séance a principalement été consacrée à l'amélioration de l'ergonomie de la page **Veille scientifique**.

La télévision affichant le journal de veille a été retravaillée afin d'obtenir un rendu plus immersif. Le positionnement des articles, les transitions entre les différentes pages du journal ainsi que l'intégration graphique avec l'image du téléviseur ont été affinés.

Le personnage du reporter a également été amélioré avec l'ajout d'une bulle de dialogue de style bande dessinée. Son positionnement, son déclenchement au survol et son orientation ont été ajustés afin de donner un aspect plus naturel. Le texte a été réécrit dans un style volontairement « franglais » afin de conserver une touche humoristique tout en rappelant que les sources sont conservées dans leur langue d'origine.

Un travail a également été réalisé pour empêcher le contenu principal de passer sous la télévision lorsque la page devient plus longue. L'organisation de la mise en page est désormais plus robuste et laisse un espace réservé au téléviseur.

Enfin, une réflexion a été engagée sur l'amélioration de la lecture du journal de veille. L'idée retenue est l'ajout d'un bouton discret permettant de mettre en pause ou de reprendre le défilement automatique des articles. Le style graphique du bouton a été défini et son intégration dans l'interface est prévue, tandis que la logique JavaScript associée sera finalisée ultérieurement.

## 29/07/2026

### Réorganisation de l'architecture Django

Une séance de maintenance a été consacrée à la réorganisation de l'architecture du projet afin de clarifier les responsabilités des différentes applications Django. Les vues et les routes liées à la veille scientifique ont été définitivement séparées des pages générales du site, ce qui simplifie la maintenance et l'évolution future du code. Plusieurs doublons et références obsolètes ont également été supprimés ou corrigés, permettant de retrouver une structure plus cohérente. Cette réorganisation a été accompagnée d'une vérification progressive des chemins d'accès et des dépendances entre les différentes parties de l'application afin de garantir le bon fonctionnement du site.

## 30/07/2026

Avancement dans la Veille avec création du fichier pipeline.py dans apps\monitoring\service\classification comme organisateur.

Création de la carte des Pays de terrain avec organisation dans accueil\data\pays 

## 31/07/2026
Création de interface carte. Organisation finalement faite dans apps/pays et mise en place des variables à traiter. 

# Journal de développement

## 04/08/2026

# Sources de données

## WOAH

### Téléchargement

- Remplacement du téléchargement manuel par un fichier unique `WOAH.csv`.
- Téléchargement enregistré dans :
  `apps/pays/data/documents_sources/WOAH.csv`
- Remplacement automatique de l'ancien fichier après vérification du téléchargement.

### Intégration

Ajout de la lecture automatique du fichier WOAH dans `actualisation_sources.py`.

Les indicateurs suivants sont maintenant calculés automatiquement :

- maladies_animales
- vaccination_animale
- faune_sauvage

Mise en place d'une correspondance robuste des noms de pays entre WOAH et le projet.

---

## Priorité des sources

Modification du système afin qu'une valeur existante ne soit plus écrasée.

Ordre de priorité :

1. Banque mondiale
2. OMS
3. WOAH
4. Reporters sans frontières

Le premier indicateur disponible est conservé.

---

# OMS

Correction du téléchargement des indicateurs OMS.

Les indicateurs utilisés sont :

- Couverture sanitaire (UHC)
- Suicide
- PM2.5
- Eaux usées traitées

Les indicateurs SPAR restent indisponibles pour le moment.

---

# Calcul des notes

Refonte des barèmes dans `definition_note.py`.

Objectif :

- obtenir des notes plus représentatives de la capacité réelle des pays à préserver la santé ;
- éviter que les pays développés restent autour de 8/20.

## Barèmes modifiés

### Santé humaine

- Espérance de vie
- Nombre de médecins
- Santé mentale

### Santé animale

- Maladies animales
- Faune sauvage

### Écosystèmes

- Aires protégées
- Couverture forestière

Les autres barèmes restent inchangés.

---

# Données manquantes

Modification du calcul du SPT.

Avant :

- chaque donnée manquante recevait automatiquement 5/20.

Maintenant :

- seules les données disponibles sont utilisées pour calculer la moyenne ;
- une pénalité spécifique est appliquée selon le nombre de données manquantes.

Cela évite de fausser artificiellement les notes.

---

# Audit du SPT

Comparaison des résultats obtenus pour :

- France
- Libye
- Japon

Constats :

- les notes sont désormais beaucoup plus cohérentes ;
- la santé animale n'est plus systématiquement proche de 0 ;
- les pays développés obtiennent des notes plus réalistes.

Points restant à améliorer :

- récupération des indicateurs SPAR OMS ;
- services vétérinaires ;
- vaccination animale ;
- bien-être animal.

---

# État actuel des sources

Sources effectivement utilisées :

- Banque mondiale
- OMS
- WOAH
- Reporters sans frontières

Sources prévues mais pas encore exploitées :

- SPAR (OMS)
- UNICEF (DTP3)
- FAO
- IUCN
- Copernicus
- Transparency International

---

# Résultat

Le SPT repose maintenant sur :

- 20 indicateurs répartis en 4 piliers ;
- des mises à jour automatiques des principales sources ;
- un système de notation recalibré ;
- une priorité des sources évitant les écrasements de données ;
- une meilleure cohérence entre la note obtenue et la capacité du pays à préserver la santé.

## 06/08/2026

Reprise des template depuis hier pour un rendu plus moderne sans gros bouton et moins Boomer

## Phase 2 – Sécurisation de Django (terminée)

Objectif : préparer le projet à une mise en ligne sans modifier les fonctionnalités du site.

### Sauvegarde
- Sauvegarde complète du projet avant toute modification.
- Création d'une branche Git `sauvegarde-avant-nettoyage`.

### Configuration des environnements
- `manage.py` utilise désormais `config.settings.development` pour le développement local.
- `config/wsgi.py` utilise `config.settings.production` pour la production.
- `config/asgi.py` utilise également `config.settings.production`.

Cela permet de séparer clairement le développement et la mise en ligne.

### Vérification de la configuration de production
Mise en place et validation des protections suivantes :

- SECRET_KEY obligatoire.
- ALLOWED_HOSTS obligatoire.
- HTTPS prévu.
- Cookies de session sécurisés.
- Cookies CSRF sécurisés.
- HSTS activé.
- Prise en charge d'une base de données externe (PostgreSQL via `DATABASE_URL`).

### Dépendances
- Installation de `dj-database-url`.
- Retour à la version compatible avec le projet (`2.3.0`), conformément au fichier `requirements/production.txt`.
- Vérification de la cohérence des dépendances.

### Variables d'environnement testées
Création temporaire dans PowerShell de :
- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`

Ces variables ne sont pas enregistrées dans le dépôt Git. Elles disparaissent à la fermeture du terminal et seront définies définitivement chez l'hébergeur lors de la mise en ligne.

### Vérifications effectuées

Développement :

```bash
python manage.py check

La configuration de production est maintenant validée.
Le projet est prêt à poursuivre la phase de finalisation (responsive, nettoyage, tests et préparation du déploiement).

Conversion  des images lourdes

les anciennes images PNG ne sont plus dans le dépôt ;
toutes les pages utilisent des WebP ;
J'ai un script pour convertir de nouvelles images ;
et un script pour mettre à jour automatiquement les références si besoin ;
Tout est versionné dans Git.

Si je mets de nouvelles images, j'ai juste à executer : (pour obtenir les WebP manquants)
python .\scripts\images\convert_images_webp.py    
puis (pour remplacer les références)
python .\scripts\images\remplacer_references_webp.py
pour les convertir.

### 07/08/2026  ####

Mise en ligne sur Render et nom de domaine "spterrain" pris sur OVHcloud .

Nom de domaine → OVHcloud
Hébergement du site → Render
Code → GitHub
Adresse publique → spterrain.fr

amélioration du CSS sur téléphone

#### Fin du projet livré en 1 mois #####

Amélioration périodique envisagée maintenant pour amélioration du site.