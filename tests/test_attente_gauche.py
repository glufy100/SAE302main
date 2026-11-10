"""Verifie le debut du virage a gauche et le depassement pendant son attente."""

import unittest
from unittest.mock import Mock

from client.config import LIGNE_ARRET, POSITION_ATTENTE_GAUCHE
from support_simulation import EtatSimulation as EtatCarrefour
from support_simulation import SimulateurClients as ClientsSimulation
from client.trajectoire import TrajectoireVehicule
from client.vehicule import Vehicule
from client.trajectoire import TrajectoireVehicule as VueCarrefourBase


class AttenteGaucheTest(unittest.TestCase):
    def test_la_file_tout_droit_passe_pendant_l_attente_a_gauche(self):
        for taille in ((700, 500), (1000, 600), (1400, 500)):
            for type_carrefour, direction in (('CROIX', 'N'), ('CROIX', 'S'),
                                              ('CROIX', 'E'), ('CROIX', 'O'), ('T', 'E')):
                with self.subTest(taille=taille, type=type_carrefour, direction=direction):
                    largeur, hauteur = taille
                    geometrie = (largeur * .05, largeur * .95, largeur / 2,
                                 hauteur * .47, hauteur * .94, min(taille) * .2)
                    haut = hauteur * .06 if type_carrefour == 'CROIX' else None
                    etat = EtatCarrefour(type_carrefour=type_carrefour)
                    distances = VueCarrefourBase._distances_securite(geometrie, haut)
                    etat.distances_affichage['test'] = distances
                    etat.geometries_affichage['test'] = (geometrie, haut)
                    opposee = {'N': 'S', 'S': 'N', 'E': 'O', 'O': 'E'}[direction]
                    gauche = Vehicule('Gauche', 'voiture', direction, '1', manoeuvre='GAUCHE', progression=30)
                    tout_droit = Vehicule('Derriere', 'voiture', direction, '2',
                                           progression=30 - distances[direction])
                    en_face = Vehicule('En-face', 'voiture', opposee, '3', progression=30)
                    etat.vehicules = {v.nom: v for v in (gauche, tout_droit, en_face)}
                    etat.feux[direction] = etat.feux[opposee] = 'VERT'
                    clients = ClientsSimulation(etat)
                    client = Mock()
                    # Le vehicule en face reste en attente volontairement :
                    # le tourne-a-gauche doit lui ceder le passage.
                    for _ in range(250):
                        for voiture in (tout_droit, gauche):
                            if voiture.progression < 100:
                                clients._avancer_vehicule(client, voiture, voiture.progression + 1)
                        self.verifier_separation(etat, geometrie, haut)
                        if tout_droit.progression == 100:
                            break
                    self.assertEqual(POSITION_ATTENTE_GAUCHE, gauche.progression)
                    self.assertEqual(100, tout_droit.progression)
                    # Quand l'oppose se libere, la voiture termine son virage.
                    en_face.progression = 100
                    for _ in range(150):
                        if gauche.progression < 100:
                            clients._avancer_vehicule(client, gauche, gauche.progression + 1)
                    self.assertEqual(100, gauche.progression)

    def verifier_separation(self, etat, geometrie, haut):
        voitures = [v for v in etat.vehicules.values() if v.progression < 100]
        contours = [TrajectoireVehicule.contour(v, geometrie, haut) for v in voitures]
        for index, contour in enumerate(contours):
            for autre in contours[index + 1:]:
                self.assertFalse(contour.intersects(autre))

    def test_virage_inaccessible_au_rouge(self):
        etat = EtatCarrefour()
        voiture = Vehicule('Gauche', 'voiture', 'E', '1', manoeuvre='GAUCHE', progression=LIGNE_ARRET)
        etat.vehicules[voiture.nom] = voiture
        clients = ClientsSimulation(etat)
        client = Mock()
        clients._avancer_vehicule(client, voiture, LIGNE_ARRET + 1)
        self.assertEqual(LIGNE_ARRET, voiture.progression)
        self.assertFalse(voiture.engagee)
        client.sendall.assert_called_with(b'ATTENTE\n')

    def test_voiture_rangee_libere_le_carrefour_a_la_fin_du_vert(self):
        geometrie = (50, 950, 500, 282, 564, 120)
        for direction, opposee in (('N', 'S'), ('S', 'N'), ('E', 'O'), ('O', 'E')):
            with self.subTest(direction=direction):
                etat = EtatCarrefour()
                etat.geometries_affichage['test'] = (geometrie, 36)
                etat.distances_affichage['test'] = VueCarrefourBase._distances_securite(geometrie, 36)
                gauche = Vehicule('Gauche', 'voiture', direction, '1', manoeuvre='GAUCHE',
                                   progression=POSITION_ATTENTE_GAUCHE, engagee=True)
                opposee_arretee = Vehicule('Opposee', 'voiture', opposee, '2', progression=LIGNE_ARRET)
                etat.vehicules = {v.nom: v for v in (gauche, opposee_arretee)}
                etat.phase = 'NS_ORANGE' if direction in ('N', 'S') else 'EO_ORANGE'
                etat.feux = {d: 'ORANGE' if d in (direction, opposee) else 'ROUGE'
                             for d in ('N', 'S', 'E', 'O')}
                etat.temps_phase = 1
                etat.avancer_cycle()
                self.assertTrue(etat.phase.endswith('ORANGE'))
                clients = ClientsSimulation(etat)
                client = Mock()
                for _ in range(100):
                    if gauche.progression < 100:
                        clients._avancer_vehicule(client, gauche, gauche.progression + 1)
                    self.verifier_separation(etat, geometrie, 36)
                self.assertEqual(100, gauche.progression)
                etat.avancer_cycle()
                self.assertTrue(etat.phase.endswith('VERT'))

    def test_attente_deja_inclinee_dans_le_virage(self):
        geometrie = (50, 950, 500, 282, 564, 120)
        for type_carrefour, haut in (('CROIX', 36), ('T', None)):
            etat = EtatCarrefour(type_carrefour=type_carrefour)
            for direction, manoeuvres in etat.trajets.items():
                if 'GAUCHE' not in manoeuvres:
                    continue
                with self.subTest(type=type_carrefour, direction=direction):
                    voiture = Vehicule('Gauche', 'voiture', direction, '1',
                                       manoeuvre='GAUCHE', progression=LIGNE_ARRET)
                    debut, angle_debut, _, _ = TrajectoireVehicule._position_vehicule(voiture, *geometrie, haut)
                    voiture.progression = POSITION_ATTENTE_GAUCHE
                    attente, angle_attente, _, _ = TrajectoireVehicule._position_vehicule(voiture, *geometrie, haut)
                    rotation = (angle_attente - angle_debut + 180) % 360 - 180
                    self.assertLess(rotation, 0)
                    self.assertGreater(rotation, -90)
                    self.assertGreater((attente - debut).manhattanLength(), 30)

    def test_virage_conserve_les_points_de_la_courbe_d_origine(self):
        # Positions de reference du virage nord -> est, avant l'ajout du rangement.
        positions = {
            30: (470.0, 196.5),
            40: (479.609375, 239.859375),
            50: (505.25, 276.75),
            60: (542.140625, 302.390625),
            70: (585.5, 312.0),
        }
        for progression, (x, y) in positions.items():
            voiture = Vehicule('Gauche', 'voiture', 'N', '1', manoeuvre='GAUCHE', progression=progression)
            point, _, longueur, largeur = TrajectoireVehicule._position_vehicule(
                voiture, 50, 950, 500, 282, 564, 120, 36)
            self.assertAlmostEqual(x, point.x())
            self.assertAlmostEqual(y, point.y())
            self.assertEqual(32, longueur)
            self.assertAlmostEqual(20.8, largeur)
