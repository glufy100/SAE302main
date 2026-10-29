# Documentation technique - Carrefour intelligent

## 1. Presentation du projet

Ce projet est une simulation de carrefour intelligent realisee en Python.

Le but est de montrer comment un carrefour peut communiquer avec des vehicules normaux et un vehicule prioritaire. Quand une ambulance, un pompier ou une voiture de police arrive, elle envoie une demande de priorite au serveur. Le carrefour adapte alors ses feux pour faciliter son passage, puis revient au fonctionnement normal.

Le projet contient :

- un serveur TCP avec interface graphique ;
- des clients TCP pour les voitures normales ;
- un client TCP pour le vehicule prioritaire ;
- des statistiques simples et une base SQLite pour les passages ;
- des tests automatises simples.

## 2. Technologies utilisees

| Element | Technologie |
|---|---|
| Langage | Python 3 |
| Interface graphique | PySide6 |
| Communication reseau | sockets TCP |
| Concurrence | threading |
| Base de donnees | SQLite |
| Tests | unittest |

Les librairies `socket`, `threading`, `sqlite3`, `time` et `random` font partie de Python.

Les dossiers `server/` et `client/` fonctionnent separement. Chaque machine peut ne recevoir que son dossier. Le port doit etre configure de la meme facon cote client et serveur. Les parametres de simulation (ligne d'arret, pas d'avancement et delai) sont definis par le serveur et transmis aux clients au demarrage de chaque vehicule.

## 3. Structure du projet

```text
SAE302/
├── README.md
├── lancer_simulation.sh
├── Stack_Technique.md
├── requirements.txt
├── server/
│   ├── carrefour.py
│   ├── config.py
│   ├── requirements.txt
│   ├── lancer_serveur.sh
│   ├── model/
│   │   ├── BaseDonnees.py
│   │   ├── EtatCarrefour.py
│   │   ├── FenetreCarrefour.py
│   │   ├── ServeurCarrefour.py
│   │   ├── Vehicule.py
│   │   └── VueCarrefour.py
│   └── data/                 # Cree au lancement, contient carrefour.sqlite3
├── client/
│   ├── voiture.py
│   ├── urgence.py
│   ├── client_vehicule.py
│   ├── config.py
│   └── lancer_simulation.sh
├── tests/
│   └── test_separation.py
└── doc/
    ├── Installation.md
    ├── Documentation_Technique.md
    ├── Diagramme_Gantt.md
    ├── Stack_Technique.md
    └── Releve_Decisions_S40_2026.md
```

## 4. Installation

Depuis la racine du projet :

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Sur Windows :

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 5. Lancement

### Lancement manuel

Terminal 1 :

```bash
python3 -m server.carrefour
```

Terminal 2 :

```bash
python3 -m client.voiture 3
```

Terminal 3 :

```bash
python3 -m client.urgence Ambulance N
```

Les directions possibles sont :

- `N` : Nord ;
- `S` : Sud ;
- `E` : Est ;
- `O` : Ouest.

### Lancement automatique

```bash
bash lancer_simulation.sh 3
```

Le nombre `3` correspond a la densite de circulation.

## 6. Fonctionnement general

1. Le serveur du carrefour demarre sur `0.0.0.0:5050`.
2. L'interface graphique affiche le carrefour, les feux et les vehicules.
3. Les voitures normales se connectent au serveur avec une socket TCP.
4. Chaque voiture choisit sa direction et son virage, puis calcule son prochain pas.
5. Le serveur indique le feu et repond `OK` ou `ATTENTE` aux positions annoncees.
6. Si le feu est rouge, la voiture attend a la ligne d'arret.
7. Si un vehicule prioritaire demande la priorite, le serveur passe son feu au vert.
8. Apres son passage, les feux reviennent au cycle normal.
9. Les passages sont enregistres dans SQLite et les compteurs sont affiches en memoire.

## 7. Protocole TCP

Les messages sont envoyes en texte, avec le separateur `|`.

| Commande client | Exemple | Role |
|---|---|---|
| `IDENTITE` | `IDENTITE|Voiture-1|voiture|N|DROITE|0` | Declare le trajet et la position de depart choisis par le client |
| `IDENTITE` | `IDENTITE|Ambulance|urgence|N|TOUT_DROIT|0` | Declare une urgence |
| `GET_LIGNE_ARRET` | `GET_LIGNE_ARRET` | Demande la ligne d'arret configuree par le serveur |
| `GET_PAS_AVANCEMENT` | `GET_PAS_AVANCEMENT` | Demande le pas maximal d'avancement configure par le serveur |
| `GET_PAS_SIMULATION` | `GET_PAS_SIMULATION` | Demande le delai entre deux iterations configure par le serveur |
| `ETAT` | `ETAT` | Demande la couleur du feu |
| `URGENCE` | `URGENCE` | Demande la priorite |
| `POSITION` | `POSITION|31` | Annonce la prochaine position calculee par le vehicule |
| `TERMINE` | `TERMINE` | Signale la fin du passage |

| Reponse serveur | Exemple | Role |
|---|---|---|
| `FEU` | `FEU|N|VERT` | Donne seulement la couleur du feu |
| `PASSAGE_AUTORISE` | `PASSAGE_AUTORISE` | Autorise l'urgence |
| `OK` | `OK` | Position de depart ou deplacement accepte |
| `ATTENTE` | `ATTENTE` | Depart occupe ou deplacement refuse |
| Reponse numerique | `1` ou `0.08` | Valeur demandee par une commande `GET_*` |

Les commandes se terminent par un retour a la ligne. Chaque requete `GET_*` utilise une connexion TCP dediee : le serveur repond par la valeur numerique suivie d'un retour a la ligne, puis le client ferme cette connexion. Le client recupere ainsi la ligne d'arret, le pas d'avancement et le delai de simulation avant d'ouvrir sa connexion de circulation. Le client garde sa position dans son propre programme. Avec `OK`, il applique le pas qu'il a calcule ; avec `ATTENTE`, il garde sa position actuelle. A l'inscription, si la place de depart est prise, il choisit une place 20 % plus loin en arriere et reessaie. Le serveur ne renvoie jamais la position du vehicule : il en garde seulement une copie pour l'affichage et les regles de circulation.

## 8. Base de donnees et statistiques

`EtatCarrefour` garde trois compteurs en memoire : passages termines, urgences traitees et temps d'attente total. Ils sont remis a zero au prochain lancement. La base `server/data/carrefour.sqlite3` conserve chaque passage termine dans une table `circulation` : `id`, `type_vehicule`, `direction` et `temps_attente`. Une ancienne table `passages` peut rester dans une base deja utilisee ; elle n'est pas effacee.

```mermaid
erDiagram
    CIRCULATION {
        INTEGER id PK
        TEXT type_vehicule
        TEXT direction
        REAL temps_attente
    }
```

## 9. UML - Cas d'utilisation

```mermaid
flowchart LR
    utilisateur[Utilisateur]
    voiture[Voiture normale]
    urgence[Vehicule prioritaire]

    subgraph Systeme[Systeme carrefour intelligent]
        lancer[Lancer la simulation]
        afficher[Afficher le carrefour]
        connecter[Connecter un vehicule]
        avancer[Faire avancer un vehicule]
        attendre[Faire attendre au feu rouge]
        priorite[Demander la priorite]
        changer[Changer les feux]
        normal[Revenir au cycle normal]
        stats[Afficher les statistiques]
        sauvegarder[Enregistrer le passage]
    end

    utilisateur --> lancer
    utilisateur --> afficher
    voiture --> connecter
    voiture --> avancer
    voiture --> attendre
    urgence --> connecter
    urgence --> priorite
    priorite --> changer
    changer --> normal
    avancer --> stats
    normal --> sauvegarder
```

## 10. UML - Diagramme de classes

```mermaid
classDiagram
    class Vehicule {
        +str nom
        +str type_vehicule
        +str direction
        +str identifiant_affichage
        +str manoeuvre
        +bool prioritaire
        +int progression
        +bool engagee
        +float temps_attente
        +direction_sortie() str
    }

    class BaseDonnees {
        +Path chemin_sqlite
        +enregistrer_passage(vehicule) None
    }

    class EtatCarrefour {
        +Signal change
        +Lock verrou
        +dict feux
        +dict vehicules
        +str priorite
        +str phase
        +int temps_phase
        +int passages_termines
        +int urgences_traitees
        +float temps_attente_total
        +int prochain_identifiant_affichage
        +notifier() None
        +etat_feu(direction) str
        +changer_feux(direction_prioritaire) None
        +enregistrer_attente(vehicule, duree) None
        +enregistrer_passage(vehicule) None
        +creer_identifiant_affichage() str
    }

    class ServeurCarrefour {
        +EtatCarrefour etat
        +str host
        +int port
        +socket socket_serveur
        +Event arret
        +demarrer() None
        +arreter() None
        -_accepter_clients() None
        -_gerer_client(client) None
        -_envoyer(client, message) None
        -_avancer_vehicule(client, vehicule, prochaine_position) None
        -_creer_vehicule(nom, type, direction, manoeuvre, position_depart) Vehicule
        -_axe(direction) str
        -_direction_a_droite(direction) str
        -_voie_sortie_occupee(vehicule, prochaine_position) bool
    }

    class ClientVehicule {
        <<module>>
        +_get_parametre(commande) float
        +get_ligne_arret() int
        +get_pas_avancement() int
        +get_pas_simulation() float
        +prochaine_position(position, feu, pas_avancement, ligne_arret) int
        +echanger(client, lecteur, message) list
        +simuler_vehicule(nom, type, direction, manoeuvre) None
    }

    class ConfigServeur {
        <<module>>
        +PORT int
        +LIGNE_ARRET int
        +PAS_AVANCEMENT int
        +PAS_SIMULATION float
        +DEBUT_CENTRE int
        +FIN_CENTRE int
    }

    class ConfigClient {
        <<module>>
        +HOST str
        +PORT int
    }

    class FenetreCarrefour {
        +ServeurCarrefour serveur
        +VueCarrefour vue
        +QLabel connexions_label
        +QLabel stats_label
        +actualiser() None
        +changer_cycle_normal() None
        +closeEvent(event) None
    }

    class VueCarrefour {
        +EtatCarrefour etat
        +paintEvent(event) None
    }

    class CarrefourMain {
        +configurer_plugins_qt() None
        +main() None
    }

    EtatCarrefour "1" o-- "*" Vehicule
    EtatCarrefour "1" o-- "0..1" BaseDonnees
    ServeurCarrefour "1" --> "1" EtatCarrefour
    ServeurCarrefour ..> Vehicule
    ClientVehicule ..> ServeurCarrefour : TCP
    ClientVehicule ..> ConfigClient
    ServeurCarrefour ..> ConfigServeur
    FenetreCarrefour "1" --> "1" ServeurCarrefour
    FenetreCarrefour "1" --> "1" VueCarrefour
    VueCarrefour "1" --> "1" EtatCarrefour
    BaseDonnees ..> Vehicule
    CarrefourMain ..> EtatCarrefour
    CarrefourMain ..> ServeurCarrefour
    CarrefourMain ..> FenetreCarrefour
    CarrefourMain ..> BaseDonnees
```

## 11. UML - Diagramme de composants

```mermaid
flowchart LR
    subgraph Clients[Machine des vehicules]
        voiture_py[voiture.py]
        urgence_py[urgence.py]
        logique[client_vehicule.py]
        config_client[client/config.py]
    end

    subgraph Serveur[Machine du carrefour]
        carrefour_py[carrefour.py]
        serveur[ServeurCarrefour]
        etat[EtatCarrefour]
        fenetre[FenetreCarrefour]
        vue[VueCarrefour]
        vehicule[Vehicule]
        db[BaseDonnees SQLite]
        config_serveur[server/config.py]
    end

    fichier[(server/data/carrefour.sqlite3)]

    voiture_py --> logique
    urgence_py --> logique
    logique -- TCP --> serveur
    config_client --> logique
    carrefour_py --> serveur
    carrefour_py --> fenetre
    serveur --> etat
    serveur --> vehicule
    config_serveur --> serveur
    fenetre --> vue
    fenetre --> etat
    vue --> etat
    etat --> db
    db --> fichier
```

## 12. UML - Sequence voiture normale

```mermaid
sequenceDiagram
    participant V as voiture.py
    participant C as client_vehicule.py
    participant S as ServeurCarrefour
    participant E as EtatCarrefour
    participant B as BaseDonnees
    participant I as Interface graphique

    loop Pour chacun des trois parametres de simulation
        C->>S: Nouvelle connexion TCP, commande GET_*
        S-->>C: Valeur numerique terminee par LF
        C-->>S: Fermeture de la connexion
    end
    V->>S: Connexion TCP de circulation
    V->>V: Choisir direction et virage
    V->>V: Choisir position de depart 0
    V->>S: IDENTITE|Voiture|voiture|N|DROITE|0
    opt Place de depart occupee
        S-->>V: ATTENTE
        V->>V: Reculer de 20
        V->>S: IDENTITE|Voiture|voiture|N|DROITE|-20
    end
    S->>E: creer identifiant + ajouter vehicule
    S-->>V: OK
    E-->>I: signal change

    loop Tant que position < 100
        V->>S: ETAT
        S-->>V: FEU|direction|couleur
        V->>V: Calculer prochain pas et s'arreter au rouge
        V->>S: POSITION|position_voulue
        S->>E: verifier le pas, les feux et les autres vehicules
        alt passage possible
            S->>E: copier la position annoncee
            S-->>V: OK
            V->>V: Appliquer la position calculee
        else attente obligatoire
            S->>E: enregistrer attente
            S-->>V: ATTENTE
        end
        E-->>I: signal change
    end

    V->>S: TERMINE
    S->>E: enregistrer passage
    E->>B: enregistrer passage dans SQLite
```

## 13. UML - Sequence vehicule prioritaire

```mermaid
sequenceDiagram
    participant U as urgence.py
    participant C as client_vehicule.py
    participant S as ServeurCarrefour
    participant E as EtatCarrefour
    participant B as BaseDonnees
    participant I as Interface graphique

    loop Pour chacun des trois parametres de simulation
        C->>S: Nouvelle connexion TCP, commande GET_*
        S-->>C: Valeur numerique terminee par LF
        C-->>S: Fermeture de la connexion
    end
    U->>S: Connexion TCP de circulation
    U->>U: Choisir position de depart
    U->>S: IDENTITE|Ambulance|urgence|N|TOUT_DROIT|0
    S->>E: ajouter vehicule
    S-->>U: OK

    U->>S: URGENCE
    S->>E: changer_feux(N)
    S-->>U: PASSAGE_AUTORISE
    E-->>I: signal change

    loop Passage de l'urgence
        U->>S: ETAT
        S-->>U: FEU|N|VERT
        U->>U: Calculer le prochain pas
        U->>S: POSITION|position_voulue
        S->>E: verifier et copier la position annoncee
        S-->>U: OK ou ATTENTE
        U->>U: Avancer seulement si OK
        E-->>I: signal change
    end

    U->>S: TERMINE
    S->>E: enregistrer_passage(ambulance)
    E->>B: enregistrer passage dans SQLite
    S->>E: changer_feux(None)
    E-->>I: retour trafic normal
```

## 14. UML - Cycle des feux

```mermaid
stateDiagram-v2
    [*] --> NS_VERT
    NS_VERT --> NS_ORANGE: apres 6 secondes
    NS_ORANGE --> EO_VERT: apres 2 secondes et liberation du centre
    EO_VERT --> EO_ORANGE: apres 6 secondes
    EO_ORANGE --> NS_VERT: apres 2 secondes et liberation du centre

    NS_VERT --> URGENCE: demande prioritaire
    NS_ORANGE --> URGENCE: demande prioritaire
    EO_VERT --> URGENCE: demande prioritaire
    EO_ORANGE --> URGENCE: demande prioritaire
    URGENCE --> NS_VERT: urgence terminee, cycle reinitialise
```

## 15. UML - Deploiement sur deux machines

```mermaid
flowchart LR
    subgraph MachineCarrefour[VM carrefour]
        gui[Interface PySide6]
        srv[Serveur TCP port 5050]
        sqlite[(SQLite local)]
    end

    subgraph MachineVehicules[VM vehicules]
        voitures[Generation voitures]
        urgence[Client urgence]
        logique[Logique de deplacement]
    end

    voitures --> logique
    urgence --> logique
    logique -- reseau local TCP --> srv
    srv --> gui
    srv --> sqlite
```

## 16. Regles de gestion principales

- Chaque vehicule calcule des pas de `1 %` et propose sa prochaine position au serveur.
- Le serveur refuse un saut trop grand ou un passage dangereux.
- Une voiture s'arrete a la ligne d'arret si son feu n'est pas vert.
- Une voiture garde une distance minimale avec les voitures devant elle.
- Le carrefour evite de faire entrer deux axes differents en meme temps.
- Une urgence rend sa direction verte et les autres rouges.
- Quand l'urgence a termine son passage, les feux reviennent au cycle normal.
- Le temps d'attente est augmente quand le serveur renvoie `ATTENTE`.

Pour utiliser deux VM, remplacer `HOST` dans `client/config.py` par l'IP du carrefour. Le serveur ecoute deja sur le reseau. Les clients n'ont pas besoin de PySide6.

## 17. Tests

Le fichier `tests/test_separation.py` contient des scenarios portant sur :

- la connexion d'une voiture normale ;
- la position calculee par le client et copiee par le serveur ;
- la priorite d'un vehicule d'urgence ;
- le refus d'un saut trop grand et d'un passage au rouge ;
- le trajet complet d'une voiture et d'une ambulance par TCP ;
- le choix d'une place de depart par deux clients.

Commande :

```bash
python3 -m unittest discover -s tests
```

## 18. Limites connues

- La simulation reste un prototype pour reseau local.
- Les vehicules ne suivent pas une vraie physique de circulation.
- Les trajets sont simplifies, y compris pour les virages.
- Il n'y a pas de gestion d'une ville complete.
- Il n'y a pas d'intelligence artificielle.

## 19. Ameliorations possibles

- Ajouter plusieurs scenarios de circulation.
- Ajouter un mode jeu.
- Ajouter un bouton dans l'interface pour lancer une urgence.
- Ajouter des graphiques de statistiques.
- Ameliorer le dessin du carrefour avec `QGraphicsScene`.

## 20. Planning

Le diagramme de Gantt du projet est disponible dans le fichier suivant :

[Diagramme de Gantt](Diagramme_Gantt.md)
