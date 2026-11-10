"""Reglages du serveur carrefour."""

import os
from pathlib import Path

BIND_HOST = os.environ.get("SAE302_BIND_HOST", "0.0.0.0")
PORT = int(os.environ.get("SAE302_PORT", "5050"))

DB_SQLITE_PATH = Path(os.environ.get(
    "SAE302_DB_PATH", Path(__file__).resolve().parent / "data" / "carrefour.sqlite3"
)).expanduser()

# Repere de dessin fixe transmis aux clients ; la vue Qt le met a l'echelle.
LARGEUR_SCENE = 1000
HAUTEUR_SCENE = 600
GEOMETRIE_SCENE = (50, 950, 500, 282, 564, 120)
HAUT_BRANCHE_NORD = 36
