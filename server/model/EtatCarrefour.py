from dataclasses import asdict
import threading
from PySide6.QtCore import QObject, Signal

from server.config import GEOMETRIE_SCENE, HAUT_BRANCHE_NORD
from server.model.BaseDonnees import BaseDonnees
from server.model.Vehicule import Vehicule


class EtatCarrefour(QObject):
    """Stocke l'etat courant du carrefour."""

    change = Signal()

    def __init__(self, base_donnees: BaseDonnees | None = None, type_carrefour: str = "CROIX"):
        if not isinstance(base_donnees, (BaseDonnees, type(None))):
            raise TypeError("base_donnees doit etre une instance de BaseDonnees ou None")
        if type_carrefour not in ("CROIX", "T"):
            raise ValueError("type_carrefour doit etre CROIX ou T")
        super().__init__()
        self.type_carrefour = type_carrefour
        self.trajets = ({"N": ("TOUT_DROIT", "DROITE", "GAUCHE"),
                         "S": ("TOUT_DROIT", "DROITE", "GAUCHE"),
                         "E": ("TOUT_DROIT", "DROITE", "GAUCHE"),
                         "O": ("TOUT_DROIT", "DROITE", "GAUCHE")}
                        if type_carrefour == "CROIX" else
                        {"S": ("DROITE", "GAUCHE"),
                         "E": ("TOUT_DROIT", "GAUCHE"),
                         "O": ("TOUT_DROIT", "DROITE")})
        self.base_donnees = base_donnees
        self.verrou = threading.RLock()
        self.feux = {direction: "VERT" if direction in ("N", "S") and direction in self.trajets else "ROUGE"
                     for direction in ("N", "S", "E", "O")}
        self.revision = 0
        self.vehicules: dict[str, Vehicule] = {}
        self.priorite: str | None = None
        self.phase = "NS_VERT"
        self.temps_phase = 0
        self.passages_termines = 0
        self.urgences_traitees = 0
        self.temps_attente_total = 0.0
        self.prochain_identifiant_affichage = 1

    def instantane(self):
        """Transmet les donnees sans decider du mouvement des vehicules."""
        with self.verrou:
            return {"revision": self.revision, "feux": dict(self.feux),
                    "priorite": self.priorite, "trajets": self.trajets,
                    "scene": (GEOMETRIE_SCENE, HAUT_BRANCHE_NORD if self.type_carrefour == "CROIX" else None),
                    "vehicules": [asdict(v) for v in self.vehicules.values()]}

    def notifier(self) -> None:
        """Previent l'interface que l'etat a change."""
        self.change.emit()

    def etat_feu(self, direction: str) -> str:
        """Retourne la couleur du feu pour une direction."""
        with self.verrou:
            return self.feux.get(direction, "ROUGE")

    def changer_feux(self, direction_prioritaire: str | None) -> None:
        """Change les feux pour une urgence ou le trafic normal."""
        with self.verrou:
            if direction_prioritaire:
                self.feux = {direction: "VERT" if direction == direction_prioritaire else "ROUGE"
                             for direction in ("N", "S", "E", "O")}
                self.priorite = direction_prioritaire
                self.phase = "URGENCE"
            else:
                self.feux = {direction: "VERT" if direction in ("N", "S") and direction in self.trajets else "ROUGE"
                     for direction in ("N", "S", "E", "O")}
                self.priorite = None
                self.phase = "NS_VERT"
                self.temps_phase = 0
            self.revision += 1

    def avancer_cycle(self):
        """Fait tourner les feux, une fois le croisement libere."""
        transitions = {
            "NS_VERT": (6, "NS_ORANGE", ("N", "S"), "ORANGE"),
            "NS_ORANGE": (2, "EO_VERT", ("E", "O"), "VERT"),
            "EO_VERT": (6, "EO_ORANGE", ("E", "O"), "ORANGE"),
            "EO_ORANGE": (2, "NS_VERT", ("N", "S"), "VERT"),
        }
        with self.verrou:
            if self.priorite is not None:
                return
            self.temps_phase += 1
            duree, phase_suivante, directions, couleur = transitions[self.phase]
            if self.temps_phase < duree:
                return
            if self.phase.endswith("ORANGE") and any(
                v.dans_carrefour for v in self.vehicules.values()
            ):
                return
            self.phase = phase_suivante
            self.temps_phase = 0
            self.feux = {direction: couleur if direction in directions and direction in self.trajets else "ROUGE"
                         for direction in ("N", "S", "E", "O")}
            self.revision += 1
        self.notifier()

    def enregistrer_passage(self, vehicule: Vehicule) -> None:
        """Enregistre un vehicule qui a traverse."""
        if self.base_donnees:
            self.base_donnees.enregistrer_passage(vehicule)

        with self.verrou:
            self.passages_termines += 1
            if vehicule.prioritaire:
                self.urgences_traitees += 1

    def creer_identifiant_affichage(self) -> str:
        """Cree un petit numero pour l'affichage."""
        with self.verrou:
            identifiant = str(self.prochain_identifiant_affichage)
            self.prochain_identifiant_affichage += 1
            if self.prochain_identifiant_affichage > 9:
                self.prochain_identifiant_affichage = 1
            return identifiant
