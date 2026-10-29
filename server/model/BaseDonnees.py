"""Enregistre les passages dans une base SQLite locale."""

import sqlite3

from server.config import DB_SQLITE_PATH


class BaseDonnees:
    """Une table suffit pour conserver les passages termines."""

    def __init__(self, chemin_sqlite=DB_SQLITE_PATH):
        self.chemin_sqlite = chemin_sqlite
        self.chemin_sqlite.parent.mkdir(parents=True, exist_ok=True)
        try:
            with sqlite3.connect(self.chemin_sqlite) as connexion:
                connexion.execute("""
                    CREATE TABLE IF NOT EXISTS circulation (
                        id INTEGER PRIMARY KEY,
                        type_vehicule TEXT,
                        direction TEXT,
                        temps_attente REAL
                    )
                """)
        except sqlite3.Error as erreur:
            print(f"Erreur lors de la creation de la table : {erreur}")
            raise

    def enregistrer_passage(self, vehicule):
        """Ajoute un vehicule qui a traverse le carrefour."""
        try:
            with sqlite3.connect(self.chemin_sqlite) as connexion:
                connexion.execute(
                    "INSERT INTO circulation (type_vehicule, direction, temps_attente) VALUES (?, ?, ?)",
                    (vehicule.type_vehicule, vehicule.direction, vehicule.temps_attente),
                )
        except sqlite3.Error as erreur:
            print(f"Erreur lors de l'enregistrement du passage : {erreur}")
            raise
