# Serveur carrefour

## Paquet Debian 13 — VM serveur

La VM serveur doit disposer d'un bureau graphique. Dans un terminal de cette session :

```bash
sudo apt update
sudo apt install ./sae302-server_1.0.0_all.deb
sae302-server
```

Lancer sans `sudo`. La configuration est dans `/etc/sae302/server.conf` :
`SAE302_BIND_HOST=0.0.0.0`, `SAE302_PORT=5050`. Autoriser le port TCP depuis la
VM client. L'interface doit rester ouverte pendant la simulation ; il n'y a pas
de service systemd ni de mode sans interface graphique.

Le paquet conserve SQLite dans `~/.local/share/sae302/carrefour.sqlite3`
(ou sous `$XDG_DATA_HOME` si défini). `SAE302_DB_PATH` permet de choisir un autre
chemin accessible en écriture. Voir le [guide deux VM Debian 13](../doc/Installation.md)
pour la construction, l'installation et la validation des paquets.

## Depuis les sources

Copier seulement le dossier `server/` sur la machine du carrefour. Sous Debian 13, installer Python 3 et les bindings Qt système :

```bash
sudo apt install python3 python3-pyside6.qtwidgets
python3 carrefour.py
```

Pour utiliser la version PySide6 épinglée dans `requirements.txt`, créer un environnement virtuel comme indiqué dans le guide d’installation.

Sous Windows PowerShell :

```powershell
python carrefour.py
```

Le serveur ecoute sur `0.0.0.0:5050`. Définir `SAE302_PORT` des deux côtés pour changer le port, et `SAE302_BIND_HOST` pour changer l’adresse d’écoute. Les lanceurs Debian lisent ces valeurs dans `/etc/sae302/*.conf` ; les lancements directs utilisent les variables d’environnement ou les valeurs de repli des fichiers `config.py`.

## Repartition des roles

Le serveur gere les feux, les demandes de priorite, les connexions, l'affichage et les statistiques.
Il ne calcule aucune avance, trajectoire, distance de securite, collision ou manoeuvre de voiture.
Ces calculs se trouvent dans les modules `client/conduite.py`, `client/trajectoire.py` et
`client/geometrie.py`. Les reglages de conduite sont dans `client/config.py`.

Chaque client envoie sa progression, ses indicateurs de conduite et sa pose graphique complete
`[x, y, angle, longueur, largeur]`. `VueCarrefourBase` dessine directement cette pose.
Le repere de route est fixe (1000 x 600) et la vue Qt met toute la scene a l'echelle lors
du redimensionnement : aucune trajectoire n'est recalculee par l'interface.

Les onglets en croix et en T ont chacun leur etat, leurs feux et leurs compteurs.
Le T autorise uniquement S vers E/O, E vers O/S et O vers E/S.

## Protocole TCP

Les messages sont des lignes `COMMANDE|contenu`. Les rapports et instantanes utilisent JSON.

| Commande | Role |
|---|---|
| `CARREFOUR|T` | Selectionne le T avant l'inscription ; la croix est selectionnee par defaut |
| `GET_TRAJETS` | Transmet les branches et manoeuvres permises par l'infrastructure |
| `INSTANTANE` | Renvoie feux, priorite, scene, rapports des voitures et revision du trafic |
| `IDENTITE|{revision, vehicule}` | Enregistre l'identite et la place de depart calculee par le client |
| `POSITION|{revision, vehicule}` | Enregistre l'etat complet calcule par le client |
| `URGENCE` | Modifie les feux pour un vehicule prioritaire |
| `TERMINE` | Enregistre un passage termine dans SQLite et confirme par `OK` |

Le serveur controle le format du rapport et sa revision, pas les calculs de conduite.
Si le trafic a change depuis l'instantane utilise, il repond `REESSAYER` ; le client relit
le trafic et recalcule. Deux propositions fondees sur le meme ancien etat ne peuvent donc
pas modifier le trafic simultanement. Un simple compteur d'attente ne change pas la revision.

Le client indique aussi s'il occupe encore le croisement. Le cycle des feux attend cet
indicateur avant d'ouvrir un axe oppose. Les passages sont conserves dans
`server/data/carrefour.sqlite3` depuis les sources, ou dans le dossier personnel avec le paquet ; les temps d'attente sont declares par les clients.

Ce protocole remplace l'ancien `POSITION|nombre` : relancer le serveur et les clients ensemble
apres la mise a jour.
