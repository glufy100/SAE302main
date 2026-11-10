# Carrefour intelligent

Projet réalisé dans le cadre de la SAE 302 – Développer des applications communicantes.

## Présentation

Ce projet consiste à réaliser une simulation simple d'un **carrefour intelligent et connecté**.

L'objectif est de permettre à un **véhicule prioritaire** (pompier, ambulance, police...) de communiquer avec le carrefour afin de faciliter son passage et réduire son temps d'attente.

La communication entre les différents programmes est réalisée avec des **sockets Python**.

## Technologies utilisées

- Python 3.13
- PySide6
- Sockets
- Threads
- Git / GitHub

## Installation sur deux VM Debian 13

Le déploiement prévu utilise deux VM séparées :

- **VM serveur** avec un bureau graphique : interface PySide6, feux, TCP et SQLite ;
- **VM client** avec un terminal : génération et calcul des véhicules, sans PySide6.

Construire les deux paquets Debian depuis la racine du dépôt :

```bash
python3 packaging/build_deb.py
```

Installer `dist/sae302-server_1.0.0_all.deb` sur la VM serveur :

```bash
sudo apt update
sudo apt install ./sae302-server_1.0.0_all.deb
sae302-server
```

Installer `dist/sae302-client_1.0.0_all.deb` sur la VM client, puis renseigner
l'IP de la VM serveur dans `/etc/sae302/client.conf` :

```bash
sudo apt update
sudo apt install ./sae302-client_1.0.0_all.deb
sudo nano /etc/sae302/client.conf
sae302-client 3 0.4
```

Lancer le serveur depuis sa session graphique, sans `sudo`, avant les clients.
Les VM doivent communiquer sur TCP 5050. APT installe les dépendances ; les paquets
utilisent les bindings PySide6 de Debian. Le guide décrit le réseau, la configuration,
les tests de connexion, les sauvegardes et l'installation depuis les sources :
[Installation Debian 13](doc/Installation.md).

## Lancement depuis les sources

Sur le serveur, installer les dépendances comme indiqué dans le guide d’installation.

Le projet est separe en deux dossiers autonomes : `server/` pour le carrefour et `client/` pour les vehicules. On peut copier seulement `client/` sur la machine des vehicules.

Depuis la racine du projet, lancer le serveur avec l'interface graphique :

```bash
python3 -m server.carrefour
```

Dans un autre terminal, lancer la generation automatique des voitures normales :

```bash
python3 -m client.voiture 3
```

Dans un troisieme terminal, lancer un vehicule prioritaire :

```bash
python3 -m client.urgence Ambulance N
```

Pour utiliser deux machines sur le meme reseau local, lancer sur la machine du carrefour :

```bash
./server/lancer_serveur.sh
```

Sur la machine des vehicules, copier le dossier `client/`, exporter `SAE302_HOST` avec l’adresse IP du carrefour, puis lancer depuis ce dossier :

```bash
export SAE302_HOST=192.168.56.10  # À adapter
bash lancer_simulation.sh 3 0.4
```

Les clients n'ont besoin que de Python 3 ; PySide6 est necessaire sur la machine du carrefour pour l'interface. Voir les modes d'emploi dans [client/README.md](client/README.md) et [server/README.md](server/README.md).

Les directions possibles sont `N`, `S`, `E` et `O`.

Pour lancer le serveur et les clients sur la meme machine depuis la racine :

```bash
./lancer_simulation.sh 3 0.4
```

Si le serveur est deja lance sur la meme machine, lancer seulement les clients avec :

```bash
./lancer_simulation.sh --clients-only 3 0.4
```

## Fonctionnement

- Le programme `server.carrefour` joue le role de serveur TCP et affiche le carrefour.
- Le programme `client.voiture` cree des voitures normales qui se connectent au serveur.
- Le programme `client.urgence` cree un vehicule prioritaire qui demande le passage.
- Les deux onglets ont chacun leur trafic, leurs feux et leurs compteurs.
- Les generateurs recuperent les trajets autorises aupres du serveur : le T utilise uniquement les branches S, E et O.
- Tous les calculs de voiture sont executes par les clients : place de depart, trajectoire, collisions, attente, depassement, rangement et reinsertion.
- Le serveur transmet les feux et le trafic, enregistre les rapports clients et affiche directement leurs coordonnees. Une revision protege les publications simultanees.
- Les parametres de conduite (ligne d'arret, pas, delai et manoeuvres) sont definis dans `client/config.py`.
- Quand une urgence est acceptee, le feu de sa direction passe au vert et les autres passent au rouge.
- Apres le passage du vehicule prioritaire, le carrefour revient au cycle normal des feux.
- Les voitures sont affichees avec un identifiant court de `1` a `9`.

## Base de donnees et statistiques

L'interface affiche le nombre de passages, le nombre d'urgences et le temps d'attente total. Chaque passage termine est aussi enregistre dans la base SQLite (`server/data/carrefour.sqlite3` depuis les sources, `~/.local/share/sae302/carrefour.sqlite3` avec le paquet, sauf configuration explicite) avec le type de vehicule, sa direction et son temps d'attente.

## Tests

Les tests automatises peuvent etre lances avec :

```bash
python3 -m unittest discover -s tests
```

## Documentation

La documentation complete du projet, avec les diagrammes UML, est disponible ici :

[Documentation technique](doc/Documentation_Technique.md)

La documentation d'installation est disponible ici :

[Documentation d'installation](doc/Installation.md)

Le diagramme de Gantt du projet est disponible ici :

[Diagramme de Gantt](doc/Diagramme_Gantt.md)

Les contraintes de bibliotheques autorisees sont conservees dans [Stack_Technique.md](Stack_Technique.md).
