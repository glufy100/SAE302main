# Diagramme de Gantt - Carrefour intelligent et connecte

Ce planning est construit a partir du cahier des charges du projet.

Il s'agit du planning previsionnel etabli au lancement du projet : les dates et l'etat des taches ne sont pas synchronises automatiquement avec le depot de code.

Il reprend les grandes etapes prevues entre septembre 2026 et decembre 2026, avec une repartition pour 2 personnes :

- **Louis** : backend, logique metier, sockets, threads, priorite, tests techniques ;
- **Maxence** : interface PyQt/PySide6, affichage du carrefour, feux, vehicules, documentation ;
- **Travail commun** : analyse, cahier des charges, integration, verification finale, presentation.

## Diagramme de Gantt

```mermaid
gantt
    title Planning du projet - Carrefour intelligent et connecte
    dateFormat  YYYY-MM-DD
    axisFormat  %d/%m
    excludes    weekends

    section Travail commun
    Analyse du besoin et QQOQCP                       :done, cadrage, 2026-09-01, 2026-09-14
    Cahier des charges                                :done, cdc, 2026-09-15, 2026-09-30
    Choix de l'architecture technique                 :done, archi, 2026-09-22, 2026-09-30
    Integration serveur / interface                   :integration, 2026-10-24, 2026-10-31

    section Louis - Backend et logique
    Creation du serveur carrefour                     :active, serveur, 2026-10-01, 2026-10-07
    Creation des clients voiture et urgence           :active, clients, 2026-10-03, 2026-10-09
    Communication par sockets TCP                     :active, sockets, 2026-10-06, 2026-10-14
    Gestion des connexions avec threads               :active, threads, 2026-10-08, 2026-10-15
    Gestion de la demande de priorite                 :priorite, 2026-10-17, 2026-10-28
    Retour au fonctionnement normal                   :retour, 2026-10-24, 2026-10-29
    Tests techniques serveur/client                   :tests1, 2026-10-29, 2026-11-05

    section Maxence - PyQt et interface
    Interface PySide6                                 :ihm, 2026-10-08, 2026-10-18
    Affichage du carrefour                            :carrefour, 2026-10-12, 2026-10-18
    Affichage des feux                                :feux, 2026-10-14, 2026-10-21
    Deplacement visuel des vehicules                  :deplacement, 2026-10-16, 2026-10-24
    Generation automatique des vehicules              :generation, 2026-10-22, 2026-10-27
    Statistiques et temps d'attente                   :stats, 2026-11-03, 2026-11-07
    Documentation technique                           :doc, 2026-11-01, 2026-11-10

    section Jalons
    Presentation de l'avancement             :milestone, jalon1, 2026-10-21, 0d
    Premiere version fonctionnelle           :milestone, beta, 2026-10-31, 0d

    section Tests et finalisation
    Tests et corrections en commun           :tests, 2026-10-29, 2026-11-05
    Verification sur machine propre          :verif, 2026-11-10, 2026-11-14
    Preparation du rendu                     :livraison, 2026-11-12, 2026-11-14
    Rendu final                              :milestone, rendu, 2026-11-15, 0d

    section Evaluation
    Preparation de la presentation orale     :oral, 2026-11-16, 2026-12-08
    Evaluation finale                        :milestone, evaluation, 2026-12-09, 0d
```

## Planning detaille

| Periode | Louis | Maxence | Livrable / jalon |
|---|---|---|---|
| 1 au 14 septembre 2026 | Analyse du besoin | Analyse du besoin | Besoin compris |
| 15 au 30 septembre 2026 | Architecture technique | Cahier des charges | Cahier des charges termine |
| 1 au 9 octobre 2026 | Serveur et clients TCP | Premiers tests d'interface | Base serveur/client |
| 6 au 15 octobre 2026 | Sockets TCP et threads | Preparation affichage graphique | Plusieurs vehicules connectes |
| 12 au 21 octobre 2026 | Stabilisation reseau | Interface PySide6, carrefour et feux | Premiere interface |
| 17 au 29 octobre 2026 | Vehicule prioritaire, priorite, retour normal | Deplacement visuel et integration | Prototype fonctionnel |
| 21 octobre 2026 | Presentation avancement | Presentation avancement | Prototype de base |
| 29 octobre au 5 novembre 2026 | Tests serveur/client | Tests interface/simulation | Version beta stabilisee |
| 1 au 10 novembre 2026 | Corrections techniques | Documentation technique | Documentation complete |
| 10 au 14 novembre 2026 | Verification machine propre | Preparation rendu | Livraison prete |
| 15 novembre 2026 | Rendu final | Rendu final | Projet rendu |
| 16 novembre au 8 decembre 2026 | Preparation orale technique | Preparation orale fonctionnelle | Support de presentation |
| 9 ou 10 decembre 2026 | Evaluation finale | Evaluation finale | Presentation du projet |

## Repartition du travail

| Membre | Responsabilites principales |
|---|---|
| Louis | backend, serveur TCP, clients, sockets, threads, logique de priorite urgence, tests reseau |
| Maxence | PyQt/PySide6, interface graphique, affichage du carrefour, feux, vehicules, statistiques, documentation |
| Les deux | cadrage, integration, tests finaux, preparation du rendu, presentation orale |

## Repartition par priorite MoSCoW

| Priorite | Taches concernees |
|---|---|
| Must have | serveur, clients, sockets TCP, threads, interface, feux, voitures, urgence, priorite, retour normal, tests, documentation |
| Should have | temps d'attente, statistiques simples |
| Could have | generation automatique, scenarios de circulation, mode jeu |
| Won't have | ville complete, IA, itineraire, donnees reelles, vrais feux de circulation |

## Remarque

Le mode jeu est indique dans le cahier des charges comme une fonctionnalite bonus. Il n'est donc pas place dans le chemin critique du planning.
