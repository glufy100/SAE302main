# Serveur carrefour

Copier seulement ce dossier `server/` sur la machine du carrefour. Installer Python 3 et PySide6 :

```bash
python3 -m pip install -r requirements.txt
```

Depuis ce dossier, lancer le serveur et son interface sur le reseau local :

```bash
./lancer_serveur.sh
```

Sous Windows PowerShell, depuis le meme dossier :

```powershell
python carrefour.py
```

Le serveur ecoute sur `0.0.0.0:5050`. Le pare-feu doit autoriser les connexions TCP entrantes sur ce port. Pour changer de port, modifier `PORT` dans `server/config.py` et `client/config.py`. Le serveur fournit aux clients la ligne d'arrêt, le pas d'avancement et le délai de simulation via `GET_LIGNE_ARRET`, `GET_PAS_AVANCEMENT` et `GET_PAS_SIMULATION`. Les passages termines sont enregistres dans `server/data/carrefour.sqlite3`.

## Organisation de l'affichage

`TrajectoireVehicule` partage les positions et les contours entre le dessin et le serveur.
`VueCarrefourBase` contient le dessin commun des vehicules et des feux.
`VueCarrefourT` et `VueCarrefour` dessinent uniquement leur decor, leurs routes et leurs marquages,
avec les memes proportions. `PanneauCarrefour` partage les compteurs des deux onglets.
Le cycle des feux est gere dans `EtatCarrefour` et declenche par le minuteur de la fenetre.

Les files utilisent une distance calculee depuis la taille des voitures et la longueur de
chaque approche : au moins 6 pixels entre les contours, arrondis au prochain pas de simulation.
Le serveur utilise les dimensions de la vue associee a chaque carrefour. Les voitures demandent
une place libre point par point a leur arrivee, plutot que de reculer par blocs de 20 points.

Les deux onglets ont des trafics, des feux, des urgences et des compteurs independants.
Les vehicules selectionnent le T avec `CARREFOUR|T` avant leur identite ; sans selection,
ils rejoignent le carrefour en croix. Les deux simulations utilisent le meme port TCP.
`GET_TRAJETS` fournit les entrees et les manoeuvres autorisees par le carrefour selectionne.
Le T autorise seulement S vers E/O, E vers O/S et O vers E/S. Le serveur rejette un
trajet impossible des l'inscription, au lieu de masquer une voiture pendant sa traversee.

Le suivi reste actif apres la ligne d'arret. Chaque deplacement est refuse si le contour
oriente de la voiture, augmente de la marge de securite, touche une autre voiture.
Les trajets conflictuels sont reserves avant le depart de la ligne pour eviter un blocage
au milieu du croisement. Les trajets paralleles sans conflit peuvent avancer ensemble.

## Attente pendant le virage a gauche

La voiture suit la courbe de virage d'origine, avec les memes points de controle,
positions de voie et dimensions qu'avant l'ajout du rangement. Au vert, elle s'engage
sur cette courbe et peut attendre a `POSITION_ATTENTE_GAUCHE` (40), avant de couper
la circulation opposee. Elle reprend exactement la meme courbe quand la voie se libere.
Il n'y a pas de poche de rangement ni de changement de trajectoire pour le tourne-a-gauche.

Une voiture qui va tout droit prepare un depassement temporaire par la droite uniquement
si la voiture juste devant est deja engagee dans son virage a gauche (progression 40),
que le feu est vert et que la suivante est proche de la ligne. La preparation laterale
s'effectue par petits pas, a progression longitudinale fixe, pour eviter tout saut de position.
Un virage a droite ou un tout-droit intercale empeche ce declenchement, meme si un
tourne-a-gauche se trouve plus loin dans la file.
La voiture qui double retrouve sa trajectoire habituelle a `FIN_DEPASSEMENT_DROITE` (60). Le decalage a droite est termine avant la ligne, pour garder libre la fin du virage
meme si le feu change. Le feu rouge, les distances et les contours restent controles. Deux virages
a gauche en sens opposes sont reserves successivement pour eviter un blocage face a face.

## Laisser passer une ambulance

Les voitures non engagees devant une ambulance de la meme branche se rangent progressivement
a droite dans le refuge lateral. L'ambulance reste sur sa voie et depasse la file rangee.
Une voiture deja engagee termine sa traversee au lieu de se decaler au milieu du carrefour.

`decalage_urgence` varie de 0 (sur la voie) a 1 (sur le cote), par pas de
`PAS_RANGEMENT_URGENCE`. La progression longitudinale reste fixe pendant le rangement.
Apres le passage de l'ambulance, le serveur attend que toute la zone de reinsertion soit
libre avant de faire revenir la voiture, puis autorise sa reprise de route. Les mouvements
lateraux utilisent les memes controles de collision que les deplacements habituels.

Lorsqu'une urgence change les feux, la priorite a droite s'applique aux nouvelles entrees.
Une voiture deja engagee peut terminer son virage : elle ne doit pas attendre une ambulance
qui attend elle-meme que le carrefour se libere. L'espace protege devant une voiture
engagee couvre la fin de son trajet, y compris pendant une attente au milieu du virage.
