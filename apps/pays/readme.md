# Ok... donc premier dossier apps/pays que je crée entièrement avec son squelette.
Mon pays.html a déjà été créé dans accueil/template/jeu
Ses Views et Urls sont donc dans accueil/
J'ai créé l'interface et extrais les variables à modifier. Le projet "carte" continue ici.

# Module Pays
## Rôle
Cette app gère les fiches pays du projet SPT.
## Contenu
- `data/pays/` : données JSON des pays.
- `templates/pays/` : modèle HTML des fiches pays.
- `views.py` : charge les données d'un pays et les affiche.
- `urls.py` : routes des fiches pays.
## Fonctionnement
1. L'utilisateur ouvre `/pays/france/`.
2. La vue charge `france.json`.
3. Les données sont injectées dans `pays.html`.
4. La fiche est affichée.
## À faire
- [ ] Ajouter tous les drapeaux.
- [ ] Générer automatiquement les courbes du graphique.
- [ ] Calculer automatiquement l'indice SPT.
- [ ] Connecter les fiches à la veille sanitaire.
- [ ] Remplacer progressivement les données statiques par des données issues des sources.
## Remarques
Les fonctions susceptibles d'être réutilisées par d'autres apps (veille, comparateur, etc.) pourront être déplacées ultérieurement dans `apps/core`.
## A faire
resoudre pourquoi 
 pays_data["drapeau_url"] = reference.get("flag", "")    
 ne fonctionne pas dans apps/pays/viex.py

 Remplacé en attendant par : 
pays_data["drapeau_url"] = f"https://flagcdn.com/w80/{code}.png"