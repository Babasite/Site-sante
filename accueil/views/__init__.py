"""
===============================================================================
VUES GÉNÉRALES DU SITE
===============================================================================
Ce dossier Views contient uniquement les vues générales de l'application accueil.
Responsabilités :
    - page d'accueil ;
    - outils généraux ;
    - pages sport, nutrition, voyage, bricolage, etc. ;
    - pages d'information et de présentation du site ;
    - page de contact.

Les vues liées à la veille scientifique ne doivent PAS être ajoutées ici.

Pour toute fonctionnalité concernant :
    - le lancement de la veille ;
    - les résultats de veille ;
    - l'export PDF ;
    - le tableau de bord Rédacteur ;
    - l'historique ;
    - les résumés ou traductions manuelles ;

utiliser :

    apps/monitoring/views.py

IMPORTANT
---------
Avant d'ajouter une nouvelle vue ici, vérifier qu'elle concerne bien une page
générale du site. Si elle concerne la veille scientifique, utiliser
apps/monitoring/views.py.
===============================================================================
"""

from .Home import *
from .Outils import *
from .terrain import *
from .Apropos import *
from .Accueil import *
from .sauver import *
from .Jsnake import *
from .bouger import *
from .sedebrouiller import *
from .manger import *
from .Jtetris import *
from .Jspace import *
from .contact import *
from .Jcombat import *
from .pays import *
from .organisation import *
from .boutique import *
from .investissement import *