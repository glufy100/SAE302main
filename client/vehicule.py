from dataclasses import dataclass

if __package__:
    from .config import POSITION_ATTENTE_GAUCHE
else:
    from config import POSITION_ATTENTE_GAUCHE

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
    decalage_urgence: float = 0.0
    retour_voie: bool = False
    depassement_droite: bool = False
    preparation_depassement: float = 1.0
    dans_carrefour: bool = False
    position_affichage: tuple | None = None

    def virage_gauche_entame(self) -> bool:
        """La voiture a deja commence a tourner et libere la file tout droit."""
        return self.manoeuvre == "GAUCHE" and self.progression >= POSITION_ATTENTE_GAUCHE

    def direction_sortie(self) -> str:
        """Donne la route prise apres le carrefour."""
        if self.manoeuvre == "DROITE":
            return {"N": "O", "O": "S", "S": "E", "E": "N"}[self.direction]
        if self.manoeuvre == "GAUCHE":
            return {"N": "E", "E": "S", "S": "O", "O": "N"}[self.direction]
        return {"N": "S", "S": "N", "E": "O", "O": "E"}[self.direction]
