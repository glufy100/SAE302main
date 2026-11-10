from dataclasses import dataclass

@dataclass
class Vehicule:
    """Donnees recues du client ; aucun calcul de conduite cote serveur."""

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
