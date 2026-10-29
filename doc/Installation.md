# Documentation d'installation

Cette documentation explique comment installer le carrefour et les vehicules sur deux machines distinctes.

## 1. Prerequis

Avant de commencer, il faut avoir :

- Python 3 installe ;
- Git installe ;
- un terminal ;
- une connexion Internet sur la machine du carrefour pour installer PySide6.

Version recommandee :

```bash
python3 --version
```

Le cahier des charges indique Python 3.13. Le client utilise seulement la bibliotheque standard de Python ; le serveur a besoin d'une version compatible avec PySide6.

## 2. Recuperer le projet

Cloner le depot Git :

```bash
git clone <URL_DU_REPOSITORY>
cd SAE302
```

Pour deux VM, copier uniquement le dossier `server/` sur la machine du carrefour et le dossier `client/` sur la machine des vehicules. Aucun fichier Python n'est partage entre les deux dossiers.

Si le projet est deja sur la machine, aller simplement dans le dossier :

```bash
cd /chemin/vers/SAE302
```

## 3. Creer l'environnement virtuel

### macOS / Linux

```bash
python3 -m venv .venv
```

### Windows

```bash
python -m venv .venv
```

L'environnement virtuel concerne seulement le serveur. Le client n'a pas de dependance a installer.

## 4. Activer l'environnement virtuel

### macOS / Linux

```bash
source .venv/bin/activate
```

### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

### Windows CMD

```bat
.venv\Scripts\activate.bat
```

Quand l'environnement est active, le terminal affiche souvent `(.venv)` au debut de la ligne.

## 5. Installer les dependances

Depuis la racine du projet, sur la machine du carrefour :

```bash
pip install -r server/requirements.txt
```

## 6. Verifier l'installation

Lancer les tests :

```bash
python -m unittest discover -s tests
```

Sur macOS ou Linux, si `python` n'existe pas, utiliser :

```bash
python3 -m unittest discover -s tests
```

La commande lance la suite disponible dans le dossier `tests/`.

## 7. Lancer la simulation

### Methode simple

Depuis la racine du projet, le script `lancer_simulation.sh` demarre le serveur et son interface, puis lance les clients apres trois secondes :

```bash
./lancer_simulation.sh 3 0.4
```

Le premier argument est la densite des voitures (entier positif, ici `3`). Le second est la densite des urgences (valeur de `0` a `1`, ici `0.4`). Les deux valeurs sont facultatives et valent respectivement `3` et `0.4` par defaut.

Si le serveur est deja lance sur cette machine, passer `--clients-only` en premier argument pour ne lancer que les clients :

```bash
./lancer_simulation.sh --clients-only 3 0.4
```

Pour lancer seulement les clients sur une autre machine, copier le dossier `client/`, configurer `HOST` dans `client/config.py` avec l'adresse IP du serveur, puis lancer depuis la racine du dossier copie :

```bash
./client/lancer_simulation.sh 3 0.4
```

### Methode manuelle

Terminal 1 : lancer le serveur et l'interface graphique.

```bash
python -m server.carrefour
```

Terminal 2 : lancer les voitures normales.

```bash
python -m client.voiture 3
```

Terminal 3 : lancer une ambulance.

```bash
python -m client.urgence Ambulance N
```

Sur macOS ou Linux, si `python` n'existe pas, remplacer par `python3`.

### Deux machines / deux VM

Les deux machines doivent etre sur le meme reseau local. Copier seulement `server/` sur la machine du carrefour et seulement `client/` sur celle des vehicules. Les clients ont besoin uniquement de Python 3.

Sur la machine du carrefour, lancer le serveur avec son interface :

```bash
cd server
python3 -m pip install -r requirements.txt
./lancer_serveur.sh
```

Trouver l'adresse IP locale de cette machine. Sur la machine des vehicules, remplacer `HOST = "127.0.0.1"` dans `client/config.py` par cette adresse. Puis lancer ces deux commandes dans deux terminaux distincts :

```bash
cd client
python3 voiture.py 3
python3 urgence.py Ambulance N
```

Pour lancer automatiquement les voitures et une urgence sur cette deuxieme machine :

```bash
./lancer_simulation.sh 3 0.4
```

Le serveur ecoute sur `0.0.0.0:5050`. Le pare-feu de la machine du carrefour doit autoriser les connexions TCP entrantes sur ce port. Pour changer de port, modifier `PORT` dans `server/config.py` et `client/config.py`. La ligne d'arret, le pas d'avancement et le delai de simulation sont configures sur le serveur et communiques aux clients par TCP ; ils ne sont pas a dupliquer dans la configuration client.

Sur Windows PowerShell, les memes commandes s'ecrivent par exemple :

```powershell
python carrefour.py
```

Sur la deuxieme VM Windows, dans un autre terminal PowerShell :

```powershell
python voiture.py 3
```

## 8. Directions disponibles

Pour le vehicule prioritaire, les directions possibles sont :

| Direction | Signification |
|---|---|
| `N` | Nord |
| `S` | Sud |
| `E` | Est |
| `O` | Ouest |

Exemples :

```bash
cd client
python urgence.py Ambulance N
python urgence.py Police E
python urgence.py Pompier S
```

## 9. Base de donnees SQLite

Le serveur cree automatiquement `server/data/carrefour.sqlite3`. Cette base locale enregistre chaque passage termine avec le type de vehicule, la direction et son temps d'attente. Les compteurs de l'interface restent en memoire pendant la simulation.

## 10. Problemes frequents

### `python: command not found`

Sur macOS ou Linux, utiliser :

```bash
python3
```

Exemple :

```bash
python3 -m server.carrefour
```

### `No module named PySide6`

L'environnement virtuel n'est pas active ou les dependances ne sont pas installees.

Corriger avec :

```bash
source .venv/bin/activate
pip install -r server/requirements.txt
```

Sur Windows :

```powershell
.venv\Scripts\Activate.ps1
pip install -r server/requirements.txt
```

### Erreur Qt `Could not find the Qt platform plugin "cocoa"`

Cette erreur peut arriver sur macOS si PySide6 est mal installe dans l'environnement virtuel.

Solutions possibles :

```bash
pip uninstall PySide6 PySide6_Addons PySide6_Essentials shiboken6
pip install -r server/requirements.txt
```

Si le probleme continue, lancer avec le Python qui fonctionne sur la machine :

```bash
python3 -m server.carrefour
```

### Le port `5050` est deja utilise

Cela signifie qu'un serveur carrefour est probablement deja lance.

Fermer l'ancienne fenetre du carrefour ou arreter le terminal avec `Ctrl+C`.

## 11. Arreter la simulation

Pour arreter les clients ou le script automatique :

```text
Ctrl+C
```

Pour arreter le serveur, fermer la fenetre graphique ou faire `Ctrl+C` dans le terminal.

## 12. Commandes utiles

| Action | Commande |
|---|---|
| Installer les dependances du serveur | `pip install -r server/requirements.txt` |
| Lancer le serveur | `python -m server.carrefour` |
| Lancer les voitures | `python -m client.voiture 3` |
| Lancer une urgence | `python -m client.urgence Ambulance N` |
| Lancer serveur et clients | `./lancer_simulation.sh 3 0.4` |
| Lancer seulement les clients avec le serveur local deja actif | `./lancer_simulation.sh --clients-only 3 0.4` |
| Lancer les clients depuis un dossier client copie | `./client/lancer_simulation.sh 3 0.4` |
| Lancer les tests | `python -m unittest discover -s tests` |

## 13. Verification avant rendu

Avant de rendre le projet, verifier :

- l'environnement virtuel se cree correctement ;
- `pip install -r server/requirements.txt` fonctionne ;
- le serveur se lance ;
- les voitures se connectent ;
- l'urgence demande la priorite ;
- les tests passent ;
- la documentation est presente.
