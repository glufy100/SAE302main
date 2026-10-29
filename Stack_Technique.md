Stack Technique Officielle & Librairies Autorisées

Ce document retranscrit les contraintes de bibliotheques du sujet. Il decrit le cadre autorise, pas necessairement les composants effectivement employes par le code actuel.
Dans le cadre de la SAÉ 3.02, votre application doit être développée exclusivement en Python 3.x en vous appuyant sur la liste de librairies autorisées ci-dessous.
1. Interface Graphique (GUI)
Obligatoire
•	PyQt6 ou PySide6 (Binding officiel Qt)
•	Modules autorisés : PyQt6.QtWidgets, PyQt6.QtCore, PyQt6.QtGui
•	Pour la gestion d'affichage 2D des carrefours, l'usage de QGraphicsScene et QGraphicsView est fortement recommandé.
Interdiction : Les autres frameworks GUI (Tkinter, CustomTkinter, Pygame, Kivy, wxPython) sont interdits pour ce projet.
 
2. Communications Réseau (V2X / V2I)
Obligatoire
•	socket (Librairie standard Python - Sockets TCP / UDP)
•	select (Pour la gestion I/O multiplexée si nécessaire)
•	struct ou json (Pour la sérialisation/désérialisation des trames réseau)
Interdiction : l'usage de frameworks réseau haut niveau comme Twisted, Scapy ou de protocoles clé en main comme MQTT (paho-mqtt) est proscrit. Vous devez coder la couche transport/session par vous-mêmes sur des sockets brutes.
 
3. Concurrence & Multi-threading
Obligatoire
•	QThread & pyqtSignal / Signal (Recommandé pour une intégration propre avec l'IHM Qt).
•	threading (Librairie standard Python - Thread, Lock, Event).
Règle d'or de sécurité (Thread-Safety) : Il est strictement interdit de modifier directement les composants de l'IHM depuis un thread threading.Thread ou un thread worker. Toute mise à jour graphique en provenance du réseau ou de la simulation DOIT passer par le mécanisme de Signals / Slots de Qt.
 
4. Base de Données & Utilitaire
Autorisé
•	sqlite3 ou mariaDB (Pour le stockage local des métriques, statistiques et historiques de scénarios).
•	math, random, time, datetime (Librairies standards pour la simulation).
•	matplotlib ou pyqtgraph (Si vous souhaitez générer et intégrer des graphiques de statistiques dans votre IHM).
Gestion des dépendances (requirements.txt) :
Votre dépôt GitHub devra obligatoirement contenir à la racine un fichier requirements.txt répertoriant les versions exactes des librairies externes installées (ex: PyQt6==6.6.1). Toute librairie hors de cette liste entraînera un refus lors de la phase de recette anonyme par vos pairs.
