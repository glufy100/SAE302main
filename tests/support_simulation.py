"""Banc de tests : execute les clients localement, sans socket ni calcul de conduite serveur."""

from dataclasses import asdict

from client.conduite import ConduiteVehicule, Perception, actualiser_affichage, position_depart_libre
from client.vehicule import Vehicule
from client.config import DISTANCE_SECURITE_DEFAUT, FIN_CENTRE
from server.config import GEOMETRIE_SCENE, HAUT_BRANCHE_NORD
from server.model.EtatCarrefour import EtatCarrefour as EtatServeur


class EtatSimulation(EtatServeur):
    """Permet aux anciens scenarios de varier les dimensions vues par les clients."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geometries_affichage = {}
        self.distances_affichage = {}

    def distance_securite(self, direction):
        return max((d[direction] for d in self.distances_affichage.values() if direction in d),
                   default=DISTANCE_SECURITE_DEFAUT)

    def avancer_cycle(self):
        for v in self.vehicules.values():
            # Ces scenarios modifient directement la progression au lieu de
            # passer par le rapport client ; actualiser leur indicateur de test.
            v.dans_carrefour = v.engagee and v.progression <= FIN_CENTRE
        super().avancer_cycle()


def perception_pour(etat):
    scene = next(iter(etat.geometries_affichage.values()),
                 (GEOMETRIE_SCENE, HAUT_BRANCHE_NORD if etat.type_carrefour == 'CROIX' else None))
    p = Perception({'feux': etat.feux, 'vehicules': [asdict(v) for v in etat.vehicules.values()], 'scene': scene})
    for direction in p.distances:
        if any(direction in d for d in etat.distances_affichage.values()):
            p.distances[direction] = etat.distance_securite(direction)
    return p


class SimulateurClients:
    """Adaptateur des scenarios historiques vers les calculs du client."""

    def __init__(self, etat):
        self.etat = etat

    def _avancer_vehicule(self, reponse_test, vehicule, prochaine_position):
        avant = vehicule.temps_attente
        proposition, attente = ConduiteVehicule(perception_pour(self.etat)).calculer(vehicule, prochaine_position)
        vehicule.__dict__.update(asdict(proposition))
        self.etat.temps_attente_total += vehicule.temps_attente - avant
        reponse_test.sendall(b'ATTENTE\n' if attente else b'OK\n')

    def _creer_vehicule(self, nom, type_vehicule, direction, manoeuvre, position_depart):
        if direction not in self.etat.trajets or manoeuvre not in self.etat.trajets[direction]:
            return None
        perception = perception_pour(self.etat)
        vehicule = Vehicule(nom, type_vehicule, direction, 'test', manoeuvre=manoeuvre, progression=position_depart)
        if not position_depart_libre(vehicule, perception):
            return None
        actualiser_affichage(vehicule, perception)
        self.etat.vehicules[nom] = vehicule
        return vehicule
