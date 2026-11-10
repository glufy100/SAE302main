# Véhicules clients

## Paquet Debian 13 — VM client

[Télécharger le paquet client](https://github.com/glufy100/SAE302main/raw/refs/heads/main/dist/sae302-client_1.0.0_all.deb), puis se placer dans le dossier du téléchargement.

Sur la VM dédiée aux véhicules :

```bash
sudo apt update
sudo apt install ./sae302-client_1.0.0_all.deb
sudo nano /etc/sae302/client.conf
```

Configurer `SAE302_HOST` avec l'IP de la VM serveur et `SAE302_PORT=5050`.
Démarrer le serveur sur l'autre VM, puis lancer :

```bash
sae302-client 3 0.4
# Ou individuellement :
sae302-voiture 3 --carrefour T
sae302-urgence Ambulance S DROITE --carrefour T
```

La VM client n'a pas besoin de bureau graphique ni de PySide6. Voir le
[guide d'installation](../doc/Installation.md) pour construire les paquets et
configurer le réseau entre les deux VM Debian 13.

## Depuis les sources

Copier seulement ce dossier `client/` sur la machine des vehicules. Python 3 suffit ; PySide6 n'est pas necessaire.

Depuis ce dossier, sur macOS ou Linux :

```bash
./lancer_simulation.sh 3 0.4
```

Sur une autre machine, exporter `SAE302_HOST` avec l’adresse IP du carrefour avant de lancer le script (`export SAE302_HOST=192.168.56.10`, à adapter), ou modifier la valeur de repli dans `config.py`. Le premier argument règle la densité des voitures et le second la densité des ambulances, entre 0 et 1. Une seule ambulance generee automatiquement circule a la fois par carrefour. À `0.4`, chaque génération attend entre 7,5 et 22,5 secondes (moyenne 15 secondes), puis attend la fin du passage avant de recommencer. La ligne d'arret, le pas d'avancement et le delai sont definis localement dans `config.py`. Pour lancer chaque programme séparément :

```bash
python3 voiture.py 3
python3 urgence.py Ambulance N
```

Sur Windows PowerShell :

```powershell
python voiture.py 3
python urgence.py Ambulance N
```

Le port TCP vaut `5050` par défaut. Pour le changer, définir `SAE302_PORT` des deux côtés (dans les fichiers `/etc/sae302/*.conf` pour les paquets, ou dans l’environnement pour les sources). Les réglages de conduite restent dans `client/config.py`.

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

## Calculs executes sur les clients

- `conduite.py` : position de depart, regles de circulation, depassement a droite,
  rangement pour l'ambulance, reinsertion et attente pendant le virage a gauche.
- `trajectoire.py` : courbes d'origine, distances, contours et detection des collisions.
- `geometrie.py` : points, courbes et rectangles orientes, en Python standard.
- `vehicule.py` : etat local de chaque voiture.
- `client_vehicule.py` : lecture des instantanes et publication des rapports par TCP.

Le client lit `INSTANTANE`, calcule son prochain etat, puis envoie `POSITION` avec la
revision utilisee. Si le serveur repond `REESSAYER`, le client relit et recalcule.
Un arret ou une manoeuvre laterale sont aussi decides par le client. Le rapport contient
la pose graphique `[x, y, angle, longueur, largeur]` que le serveur affiche directement.

Les clients restent autonomes : aucun import du dossier serveur, aucune dependance PySide6.
Relancer les deux programmes apres une mise a jour du protocole.
