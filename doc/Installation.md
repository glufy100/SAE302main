# Installation sur deux VM Debian 13

Le déploiement utilise **deux VM séparées** : une VM serveur avec bureau graphique
pour le carrefour et une VM client pour les véhicules. Le client n'a besoin que
d'un terminal. Les deux VM utilisent Debian 13 (Trixie) et Python 3.13.

## 1. Préparer le réseau

Connecter les VM au même réseau virtuel (réseau privé hôte, réseau interne avec
une seconde carte NAT pour Internet, réseau NAT partagé ou mode pont). Deux cartes
NAT isolées ne permettent généralement pas aux VM de communiquer directement.
APT doit avoir accès aux dépôts Debian pour installer les dépendances.

Exemple à adapter à votre réseau ; ces adresses doivent être attribuées aux VM :

| Machine | Adresse d'exemple | Rôle |
|---|---|---|
| VM serveur | `192.168.56.10` | Interface PySide6, feux, TCP, SQLite |
| VM client | `192.168.56.11` | Calcul et génération des véhicules |

Sur chaque VM, relever l'adresse avec `ip -br address`. Sur la VM serveur,
installer un environnement de bureau lors de l'installation de Debian, puis
ouvrir une session graphique. Le serveur s'exécute dans cette session, sous un
utilisateur normal. Il ne dispose pas de mode serveur sans interface.

Le seul port applicatif est **TCP 5050**, entrant sur la VM serveur. Si un
pare-feu est actif, autoriser ce port depuis la VM client selon son outil de
configuration. Aucun port entrant n'est nécessaire sur le client. Le protocole
n'a ni authentification ni chiffrement : utiliser le réseau de TP, sans exposer
le port sur Internet.

## 2. Obtenir les deux paquets `.deb`

### Paquets déjà publiés

Le dossier [dist du dépôt GitHub](https://github.com/glufy100/SAE302main/tree/main/dist)
contient les deux paquets prêts à transférer vers les VM :

- [Paquet serveur](https://github.com/glufy100/SAE302main/raw/refs/heads/main/dist/sae302-server_1.0.0_all.deb)
- [Paquet client](https://github.com/glufy100/SAE302main/raw/refs/heads/main/dist/sae302-client_1.0.0_all.deb)
- [SHA256SUMS](https://github.com/glufy100/SAE302main/raw/refs/heads/main/dist/SHA256SUMS)

Pour vérifier les téléchargements sous Debian, placer ces trois fichiers dans
le même dossier, puis exécuter `sha256sum -c SHA256SUMS`. Les deux lignes doivent
indiquer `OK`. Copier ensuite chaque paquet sur sa VM comme indiqué ci-dessous.

### Reconstruire depuis les sources

Depuis la racine du dépôt, sur la machine qui possède les sources :

```bash
python3 packaging/build_deb.py
```

Cette commande fonctionne sous Linux ou macOS avec Python standard, sans root,
`pip` ni outil de compilation. Elle produit :

```text
dist/sae302-server_1.0.0_all.deb
dist/sae302-client_1.0.0_all.deb
dist/SHA256SUMS
```

Les paquets contiennent du Python et sont indépendants de l'architecture (`all`,
notamment amd64 et arm64). Leurs dépendances sont installées par APT sur Debian 13.
Ils n'embarquent ni environnement virtuel, ni historique SQLite, ni PySide6.

Copier le paquet serveur sur la VM serveur et le paquet client sur la VM client
(dossier partagé, clé USB ou `scp` si SSH est déjà installé). Exemple depuis la
machine de construction, avec vos noms d'utilisateurs et adresses :

```bash
scp dist/sae302-server_1.0.0_all.deb utilisateur@192.168.56.10:~/
scp dist/sae302-client_1.0.0_all.deb utilisateur@192.168.56.11:~/
```

## 3. Installer et lancer la VM serveur

Dans un terminal de la **session graphique de la VM serveur** :

```bash
cd ~
sudo apt update
sudo apt install ./sae302-server_1.0.0_all.deb
sudo nano /etc/sae302/server.conf
```

Configuration par défaut :

```ini
SAE302_BIND_HOST=0.0.0.0
SAE302_PORT=5050
```

`0.0.0.0` signifie écouter sur les interfaces réseau de la VM. Ce n'est pas
l'adresse à renseigner sur le client. Pour limiter l'écoute à la carte du TP,
remplacer cette valeur par l'adresse de cette carte.

Lancer **sans sudo** :

```bash
sae302-server
```

Le menu des applications propose aussi « Carrefour intelligent - Serveur ».
Garder la fenêtre ouverte : elle porte le serveur TCP et les deux onglets croix/T.
Ne pas lancer une deuxième instance sur le même port.

Dans un autre terminal du serveur, vérifier l'écoute :

```bash
ss -ltn 'sport = :5050'
```

## 4. Installer et configurer la VM client

Sur la **VM client** :

```bash
cd ~
sudo apt update
sudo apt install ./sae302-client_1.0.0_all.deb
sudo nano /etc/sae302/client.conf
```

Renseigner l'adresse réelle de la VM serveur :

```ini
SAE302_HOST=192.168.56.10
SAE302_PORT=5050
```

`127.0.0.1` désignerait la VM client elle-même et ne convient pas à ce déploiement.
Le port doit être identique sur les deux VM. Les fichiers `.conf` sont lus par
les lanceurs au démarrage ; après modification, relancer les programmes concernés.
Leur syntaxe est celle du shell : `NOM=valeur`, sans espace autour de `=`.

Tester le réseau et une réponse du protocole, depuis la VM client, en adaptant
l'adresse et le port à votre configuration :

```bash
python3 - <<'PY'
import socket
with socket.create_connection(("192.168.56.10", 5050), timeout=5) as connexion:
    connexion.sendall(b"GET_TRAJETS\n")
    with connexion.makefile("r", encoding="utf-8") as lecteur:
        print(lecteur.readline().strip())
PY
```

Une réponse `TRAJETS|...` confirme que le serveur applicatif est accessible.

## 5. Lancer les véhicules

Sur la VM client, après le démarrage du serveur :

```bash
sae302-client 3 0.4
```

Cette commande génère des voitures sur **les deux carrefours**, puis démarre les
générateurs d'ambulances après 8 secondes. Les arguments sont :

| Argument | Valeur par défaut | Sens |
|---|---|---|
| 1 | `3` | Densité des voitures, entier supérieur ou égal à 1 |
| 2 | `0.4` | Densité des urgences, de 0 à 1 ; 0 les désactive |
| 3 | `TOUS` | `TOUS`, `CROIX` ou `T` |

À `0.4`, l'attente aléatoire avant chaque ambulance est de 7,5 à 22,5 secondes
(moyenne 15 secondes). L'intervalle entre deux arrivées inclut aussi la durée du
passage précédent, car un générateur attend la fin de son ambulance.

Exemples :

```bash
sae302-client 3 0.4 T
sae302-client 3 0 CROIX
```

On peut aussi utiliser des terminaux distincts :

```bash
sae302-voiture 3 --carrefour T
sae302-urgence Ambulance S DROITE --carrefour T
```

Sans `--carrefour`, les commandes individuelles ciblent la croix. La croix dispose
des branches `N`, `S`, `E`, `O`. Le T dispose seulement de `S`, `E`, `O` ; les
manœuvres autorisées sont demandées au serveur avec `GET_TRAJETS`.

Contrôler dans l'interface serveur que les véhicules se déplacent, que les
urgences obtiennent la priorité et que les compteurs augmentent après leur sortie.
Pour arrêter : `Ctrl+C` sur le client, puis fermer la fenêtre du serveur.

## 6. Fichiers installés et données

| Chemin | Utilité |
|---|---|
| `/usr/share/sae302/server/` | Code serveur, installé en lecture seule pour l'utilisateur |
| `/usr/share/sae302/client/` | Code client |
| `/usr/bin/sae302-*` | Lanceurs |
| `/etc/sae302/server.conf` | Adresse d'écoute, port, chemin SQLite facultatif |
| `/etc/sae302/client.conf` | Adresse et port du serveur |
| `/usr/share/doc/sae302-server/` et `/usr/share/doc/sae302-client/` | Documentation et licence |
| `~/.local/share/sae302/carrefour.sqlite3` | Base de l'utilisateur qui lance le serveur |

Si `XDG_DATA_HOME` est défini, la base est placée dans
`$XDG_DATA_HOME/sae302/carrefour.sqlite3`. Une variable `SAE302_DB_PATH` dans
`server.conf` permet de choisir un autre chemin absolu accessible en écriture.
La base et sa table sont créées au premier lancement. Les compteurs de l'interface
repartent à zéro au redémarrage, les passages enregistrés dans SQLite restent.

Pour sauvegarder, arrêter le serveur, puis copier sa base :

```bash
cp ~/.local/share/sae302/carrefour.sqlite3 ~/carrefour-sauvegarde.sqlite3
```

## 7. Mise à jour et désinstallation

Pour une nouvelle version, reconstruire depuis les sources actualisées :

```bash
python3 packaging/build_deb.py --version 1.0.1
```

Arrêter les clients et le serveur, transférer les nouveaux paquets, puis installer
le paquet correspondant avec `sudo apt install ./sae302-…_1.0.1_all.deb` sur chaque
VM. Les deux composants doivent utiliser la même version du protocole. Les
fichiers de `/etc/sae302` sont déclarés comme fichiers de configuration Debian :
APT/dpkg gère leur conservation et demande quoi faire en cas de conflit.

Sur chaque VM, selon le paquet installé :

```bash
sudo apt remove sae302-client
# Sur la VM serveur :
sudo apt remove sae302-server
```

`apt purge` supprime aussi la configuration système du paquet concerné. La base
dans le dossier personnel est conservée, même après une purge.

## 8. Installation depuis les sources (alternative)

Cette méthode permet de développer sans installer de paquet. Copier `server/`
sur la VM serveur et `client/` sur la VM client, ou cloner le dépôt complet :

```bash
sudo apt update
sudo apt install git python3
git clone https://github.com/glufy100/SAE302main.git
cd SAE302main
```

Sur la VM serveur, installer les bindings Qt fournis par Debian puis lancer
depuis la session graphique :

```bash
sudo apt install python3-pyside6.qtwidgets
python3 -m server.carrefour
```

Sur la VM client, depuis la racine des sources :

```bash
export SAE302_HOST=192.168.56.10
export SAE302_PORT=5050
bash client/lancer_simulation.sh 3 0.4
```

Si seul le dossier client a été copié, se placer dedans et utiliser
`bash lancer_simulation.sh 3 0.4`. Si seul le dossier serveur a été copié, utiliser
`python3 carrefour.py` depuis ce dossier. Les programmes lancés directement ne
lisent pas `/etc/sae302/*.conf` : exporter les variables ou modifier les valeurs
de repli dans `client/config.py` et `server/config.py`. Sans `SAE302_DB_PATH`, le
serveur lancé depuis les sources utilise `server/data/carrefour.sqlite3`.

Pour retrouver la version PySide6 épinglée pour le développement (6.9.2), utiliser
un environnement virtuel à la place des bindings système :

```bash
sudo apt install python3-venv
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r server/requirements.txt
python -m server.carrefour
```

Les paquets `.deb` utilisent PySide6 fourni par Debian 13 (6.8.2.1), via
[`python3-pyside6.qtwidgets`](https://packages.debian.org/trixie/python3-pyside6.qtwidgets),
qui dépend de QtCore et QtGui. Aucun `pip install` système n'est nécessaire.

## 9. Dépannage et vérification

| Symptôme | Vérification / correction |
|---|---|
| Connexion refusée | Démarrer le serveur, vérifier `ss -ltn 'sport = :5050'` et le port configuré |
| Délai de connexion dépassé | Vérifier les IP, le réseau virtuel, le routage et le pare-feu |
| Erreur Qt / absence d'affichage | Ouvrir une session de bureau sur la VM serveur ; lancer sans sudo depuis son terminal |
| `No module named PySide6` | Pour le paquet, utiliser `sae302-server` et vérifier `apt install python3-pyside6.qtwidgets` ; pour un venv, installer ses requirements |
| Port déjà occupé | Fermer l'ancienne instance du serveur |
| SQLite non accessible en écriture | Lancer sous l'utilisateur normal et vérifier `SAE302_DB_PATH` et les droits du répertoire parent |
| APT ne trouve pas un paquet local | Se placer dans le bon dossier et conserver le préfixe `./` devant le `.deb` |

Sur une machine Debian 13 possédant le dépôt complet et PySide6 :

```bash
python3 -m unittest discover -s tests
python3 packaging/build_deb.py
dpkg-deb --info dist/sae302-server_1.0.0_all.deb
dpkg-deb --contents dist/sae302-client_1.0.0_all.deb
```

La validation finale du déploiement consiste à installer les paquets sur les deux
VM, recevoir `TRAJETS|...`, voir les véhicules dans les deux onglets et vérifier
l'enregistrement des passages après le lancement d'une ambulance.


## 10. État de la validation

La suite de 55 tests a réussi sous macOS avec Python 3.11.9 et PySide6 6.9.2.
Les contrôles des paquets vérifient le format des archives, la séparation des
rôles, les permissions, les empreintes MD5 internes, les fichiers de configuration,
la reproductibilité de la construction et les variables d'environnement.

Cette exécution ne valide pas encore l'installation APT ni l'interface avec les
bindings Qt de Debian 13. La recette sur les deux VM reste à réaliser :

- Installer chaque paquet sur une VM Debian 13 distincte.
- Lancer le serveur dans une session graphique, sans sudo.
- Obtenir une réponse `TRAJETS|...` depuis la VM client.
- Observer le trafic sur la croix et le T, puis le passage prioritaire d'une ambulance.
- Vérifier que les passages persistent dans SQLite après redémarrage du serveur.
