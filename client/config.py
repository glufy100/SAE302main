"""Reglages propres aux vehicules clients."""

import os

# Les paquets Debian chargent ces variables depuis /etc/sae302/client.conf.
HOST = os.environ.get("SAE302_HOST", "127.0.0.1")
PORT = int(os.environ.get("SAE302_PORT", "5050"))


LIGNE_ARRET = 30
# La zone protegee tient compte de la taille des voitures a l'ecran.
DEBUT_CENTRE = 35
FIN_CENTRE = 70
# Fin de la premiere partie du virage, avant de couper la voie opposee.
POSITION_ATTENTE_GAUCHE = 40
FIN_DEPASSEMENT_DROITE = 60
PAS_RANGEMENT_URGENCE = 0.1
PAS_PREPARATION_DEPASSEMENT = 0.1

# Valeurs de repli sans interface et espacement dans la zone de croisement.
DISTANCE_SECURITE_DEFAUT = 20
DISTANCE_SORTIE = 20

PAS_AVANCEMENT = 1
PAS_SIMULATION = 0.08
