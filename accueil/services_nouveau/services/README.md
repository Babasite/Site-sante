# Nouveau dossier `services`

Ce dossier constitue la future architecture modulaire de la veille scientifique.

## Important

Ne remplace pas encore directement le dossier actuellement utilisé par Django.

Procédure recommandée :

1. Dans `accueil/`, renommer le dossier actuel `services` en `services_old`.
2. Copier ce nouveau dossier `services` dans `accueil/`.
3. Avant de lancer Django, recopier dans le nouveau dossier le contenu fonctionnel de :
   - `classification.py`
   - `traitement.py`
   - `resume_local.py`
   - `pdf.py`
4. Remplir ensuite les collecteurs un par un et les tester.
5. Ne supprimer `services_old` qu'après validation complète.

## Rôle des fichiers

- `collecte.py` : lance tous les collecteurs.
- `utilitaires.py` : fonctions communes HTTP, RSS, nettoyage et dates.
- `pubmed.py` : recherche principale dans PubMed.
- `has.py` : HAS.
- `anses.py` : ANSES.
- `sante_publique_france.py` : Santé publique France.
- `inserm.py` : Inserm.
- `oms.py` : OMS.
- `ecdc.py` : ECDC.
- `cdc.py` : CDC.
- `promed.py` : ProMED.
- `cochrane.py` : Cochrane, avec un faible volume.
- `arxiv.py` : arXiv, avec un faible volume.
- `classification.py` : catégories, preuve et importance.
- `traitement.py` : dédoublonnage, score et sélection.
- `resume_local.py` : résumé et traduction locale.
- `pdf.py` : rapport PDF.
- `export.py` : futurs exports.

## Ordre de remplissage prévu

1. `utilitaires.py`
2. `pubmed.py`
3. `collecte.py`
4. organismes français
5. OMS, ECDC et CDC
6. ProMED
7. Cochrane et arXiv
8. raccordement final avec `lancerveille.py`
