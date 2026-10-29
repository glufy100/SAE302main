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
