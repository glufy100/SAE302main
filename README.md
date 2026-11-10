# Carrefour intelligent — SAE 302

Simulation de deux carrefours connectés, **en croix et en T**, réalisée dans le
cadre de la SAE 302 « Développer des applications communicantes ».
Les véhicules normaux et prioritaires échangent avec le carrefour par sockets TCP.
Le passage d'une ambulance, d'un pompier ou d'un véhicule de police déclenche une
adaptation des feux.

## Architecture

Le déploiement utilise **deux VM Debian 13 séparées** :

| VM | Composants | Prérequis |
|---|---|---|
| Serveur | Feux, priorités, interface, rapports et SQLite | Python 3.13, PySide6, bureau graphique |
| Client | Générateurs et calcul de chaque véhicule | Python 3.13, terminal |

Les clients calculent les positions de départ, trajectoires, distances de sécurité,
collisions, virages à gauche, dépassements, rangements et réinsertions. Le serveur
transmet des instantanés, vérifie le format et la révision des rapports, puis affiche
les coordonnées reçues. Les deux carrefours ont leur propre trafic, leurs feux et
leurs compteurs, accessibles sur un seul port TCP : **5050** par défaut.

## Installer les paquets Debian

Les deux paquets sont disponibles dans [dist/](dist/) :

- [Télécharger le serveur](https://github.com/glufy100/SAE302main/raw/refs/heads/main/dist/sae302-server_1.0.0_all.deb)
- [Télécharger le client](https://github.com/glufy100/SAE302main/raw/refs/heads/main/dist/sae302-client_1.0.0_all.deb)
- [Empreintes SHA-256](dist/SHA256SUMS)

Copier chaque paquet sur la VM correspondante. Dans le dossier contenant le
paquet serveur, sur la **VM serveur**, ouvrir un terminal de la session graphique :

```bash
sudo apt update
sudo apt install ./sae302-server_1.0.0_all.deb
sae302-server
```

Sur la **VM client**, dans le dossier contenant son paquet :

```bash
sudo apt update
sudo apt install ./sae302-client_1.0.0_all.deb
sudo nano /etc/sae302/client.conf
```

Renseigner l'adresse réelle de la VM serveur, par exemple :

```ini
SAE302_HOST=192.168.56.10
SAE302_PORT=5050
```

Démarrer les véhicules après le serveur :

```bash
sae302-client 3 0.4
```

Les VM doivent pouvoir communiquer sur TCP 5050. Le serveur reste ouvert dans
sa session graphique et se lance sous l'utilisateur normal, sans `sudo`.
APT installe les dépendances nécessaires ; le client n'utilise pas PySide6.

Le [guide d'installation Debian 13](doc/Installation.md) explique le réseau
virtuel, la configuration des deux VM, les tests de connexion, les sauvegardes,
les mises à jour et la désinstallation.

## Commandes des véhicules

| Commande | Résultat |
|---|---|
| `sae302-client 3 0.4` | Voitures et ambulances sur les deux carrefours |
| `sae302-client 3 0.4 T` | Trafic uniquement sur le T |
| `sae302-client 3 0 CROIX` | Voitures uniquement sur la croix |
| `sae302-voiture 3 --carrefour T` | Générateur de voitures pour le T |
| `sae302-urgence Ambulance S DROITE --carrefour T` | Une ambulance entrant par le sud du T |

Le premier argument du lanceur est une densité de voitures entière, au moins 1.
Le deuxième est une densité d'urgences entre 0 et 1. Le troisième vaut `TOUS`,
`CROIX` ou `T`. Les commandes individuelles ciblent la croix par défaut.
La croix possède les branches `N`, `S`, `E`, `O` ; le T possède `S`, `E`, `O`.
Les générateurs demandent au serveur les trajets autorisés.

Arrêter les générateurs avec `Ctrl+C`, puis fermer la fenêtre du serveur.

## Développer depuis les sources

```bash
git clone https://github.com/glufy100/SAE302main.git
cd SAE302main
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m server.carrefour
```

Dans un autre terminal, depuis la racine du dépôt :

```bash
# Si le serveur se trouve sur une autre VM, adapter cette adresse.
export SAE302_HOST=127.0.0.1
bash client/lancer_simulation.sh 3 0.4
```

Le dossier `client/` peut être copié seul sur la VM des véhicules et utilisé avec
Python standard. Les lancements directs lisent les variables d'environnement et
les valeurs de repli des modules `config.py`. Les fichiers `/etc/sae302/*.conf`
sont chargés uniquement par les lanceurs des paquets Debian.
Les réglages de conduite sont définis dans `client/config.py`.

Pour le développement sur une seule machine, `bash lancer_simulation.sh 3 0.4`
lance le serveur et les générateurs. Le [guide](doc/Installation.md) présente aussi
l'installation depuis les sources avec les bindings Qt fournis par Debian.

## Construire les paquets et tester

Depuis la racine du dépôt :

```bash
python3 packaging/build_deb.py
python3 -m unittest discover -s tests
```

Le constructeur utilise Python standard, fonctionne sous Linux et macOS et produit
les deux `.deb` ainsi que `dist/SHA256SUMS`. Les paquets contiennent uniquement le
code du rôle concerné, sa configuration, ses lanceurs et sa documentation.

La suite de **55 tests** a été exécutée avec succès sous macOS, Python 3.11.9 et
PySide6 6.9.2. Elle couvre la conduite, les échanges TCP, la séparation des rôles,
SQLite et le contenu des paquets. **L'installation et le fonctionnement sur les
deux VM Debian 13 restent à valider** avec la procédure du guide.

## Données et statistiques

Chaque onglet affiche ses passages, ses urgences et son temps d'attente total.
Les compteurs sont remis à zéro au redémarrage. SQLite conserve les passages
terminés : type de véhicule, direction et temps d'attente.

- Depuis les sources : `server/data/carrefour.sqlite3` par défaut.
- Avec le paquet serveur : `~/.local/share/sae302/carrefour.sqlite3`, sauf
  configuration de `XDG_DATA_HOME` ou `SAE302_DB_PATH`.

## Documentation

- [Installation sur deux VM Debian 13](doc/Installation.md)
- [Documentation technique et diagrammes UML](doc/Documentation_Technique.md)
- [Commandes et modules clients](client/README.md)
- [Serveur et protocole TCP](server/README.md)
- [Planning prévisionnel](doc/Diagramme_Gantt.md)
- [Contraintes de bibliothèques du sujet](Stack_Technique.md)

Licence : [Apache 2.0](LICENSE).
