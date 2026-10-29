# Vehicules clients

Copier seulement ce dossier `client/` sur la machine des vehicules. Python 3 suffit ; PySide6 n'est pas necessaire.

Depuis ce dossier, sur macOS ou Linux :

```bash
./lancer_simulation.sh 3 0.4
```

Sur une autre machine, remplacer `HOST = "127.0.0.1"` dans `config.py` par l'adresse IP de la machine du carrefour avant de lancer le script. Le premier argument règle la densité des voitures et le second la densité des ambulances, entre 0 et 1. Une seule ambulance generee automatiquement circule a la fois par carrefour. À `0.4`, son intervalle moyen d'arrivée est de 15 secondes, avec une variation aléatoire de plus ou moins 50 %. La ligne d'arrêt, le pas d'avancement et le délai de simulation sont récupérés auprès du serveur via TCP au démarrage du véhicule. Pour lancer chaque programme séparément :

```bash
python3 voiture.py 3
python3 urgence.py Ambulance N
```

Sur Windows PowerShell :

```powershell
python voiture.py 3
python urgence.py Ambulance N
```

Le port TCP est fixe a `5050`. Pour le changer, modifier `PORT` dans `client/config.py` et `server/config.py`.

## Choisir le carrefour

Le script lance par defaut un trafic pour chacun des deux onglets. Pour generer seulement
le trafic du T, utiliser `./lancer_simulation.sh 3 0.4 T` (ou `CROIX` pour la croix).
Les densites s'appliquent a chaque carrefour selectionne.

Les programmes peuvent aussi etre lances directement :

```bash
python3 voiture.py 3 --carrefour T
python3 urgence.py --generer 0.4 --carrefour T
python3 urgence.py Ambulance S DROITE --carrefour T
```

Sans `--carrefour`, les programmes ciblent la croix. Les generateurs demandent au serveur
les trajets autorises avec `GET_TRAJETS`. Pour le T, les entrees sont S, E et O ; aucune
voiture ni ambulance n'est generee vers la branche nord absente.
