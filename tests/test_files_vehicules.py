"""Verifie les distances des files et leur application par le clients."""

import unittest
from unittest.mock import Mock

from client.config import LIGNE_ARRET
from support_simulation import EtatSimulation as EtatCarrefour
from support_simulation import SimulateurClients as ClientsSimulation
from client.vehicule import Vehicule
from client.trajectoire import TrajectoireVehicule as VueCarrefourBase


class FilesVehiculesTest(unittest.TestCase):
    def test_ecart_de_la_file_reste_inferieur_a_une_voiture(self):
        for largeur, hauteur in ((700, 500), (1000, 600), (1400, 800), (1400, 500)):
            geometrie = (largeur * .05, largeur * .95, largeur / 2,
                         hauteur * .47, hauteur * .94, min(largeur, hauteur) * .2)
            for haut in (None, hauteur * .06):
                distances = VueCarrefourBase._distances_securite(geometrie, haut)
                for direction, distance in distances.items():
                    with self.subTest(taille=(largeur, hauteur), direction=direction, haut=haut):
                        positions = []
                        for rang in range(3):
                            v = Vehicule(str(rang), "voiture", direction, str(rang),
                                         progression=LIGNE_ARRET - rang * distance,
                                         manoeuvre="DROITE" if direction == "S" and haut is None else "TOUT_DROIT")
                            position, _, longueur, _ = VueCarrefourBase._position_vehicule(v, *geometrie, haut)
                            positions.append(position)
                        for devant, derriere in zip(positions, positions[1:]):
                            ecart = (devant - derriere).manhattanLength() - longueur - 1
                            self.assertGreaterEqual(ecart, 6 - 1e-8)
                            self.assertLess(ecart, longueur)

    def test_clients_utilise_la_distance_pour_creer_et_avancer(self):
        etat = EtatCarrefour()
        etat.distances_affichage["T"] = {"S": 6}
        clients = ClientsSimulation(etat)
        premiere = clients._creer_vehicule("Premiere", "voiture", "S", "DROITE", 0)
        self.assertIsNotNone(premiere)
        self.assertIsNone(clients._creer_vehicule("TropPres", "voiture", "S", "DROITE", -5))
        suivante = clients._creer_vehicule("Suivante", "voiture", "S", "DROITE", -6)
        self.assertIsNotNone(suivante)
        client = Mock()
        clients._avancer_vehicule(client, suivante, -5)
        client.sendall.assert_called_with(b"ATTENTE\n")
        clients._avancer_vehicule(client, premiere, 1)
        clients._avancer_vehicule(client, suivante, -5)
        client.sendall.assert_called_with(b"OK\n")
        self.assertEqual(-5, suivante.progression)

    def test_redimensionnement_respecte_les_deux_vues(self):
        etat = EtatCarrefour()
        etat.distances_affichage = {"T": {"S": 6}, "Croix": {"S": 7, "N": 8}}
        with etat.verrou:
            self.assertEqual(7, etat.distance_securite("S"))
            self.assertEqual(8, etat.distance_securite("N"))
            etat.distances_affichage["Croix"]["S"] = 5
            self.assertEqual(6, etat.distance_securite("S"))

