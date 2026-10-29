from dataclasses import dataclass

@dataclass
class Vehicule:
    """Represente un vehicule connu du carrefour."""

    nom: str
    type_vehicule: str
    direction: str
    identifiant_affichage: str
    manoeuvre: str = "TOUT_DROIT"
    prioritaire: bool = False
    progression: int = 0
    engagee: bool = False
    temps_attente: float = 0.0

    def direction_sortie(self) -> str:
        """Donne la route prise apres le carrefour."""
        if self.manoeuvre == "DROITE":
            return {"N": "O", "O": "S", "S": "E", "E": "N"}[self.direction]
        if self.manoeuvre == "GAUCHE":
            return {"N": "E", "E": "S", "S": "O", "O": "N"}[self.direction]
        return {"N": "S", "S": "N", "E": "O", "O": "E"}[self.direction]
