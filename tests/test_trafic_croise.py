"""Regression du blocage entre un virage engage et le nouveau vert d'une urgence."""

import random
import unittest
from unittest.mock import Mock

from client.client_vehicule import prochaine_position
from support_simulation import EtatSimulation as EtatCarrefour
from support_simulation import SimulateurClients as ClientsSimulation
from client.trajectoire import TrajectoireVehicule
from client.vehicule import Vehicule
from client.trajectoire import TrajectoireVehicule as VueCarrefourBase


class TraficCroiseTest(unittest.TestCase):
    def test_urgence_a_droite_ne_bloque_pas_le_virage_deja_engage(self):
        for type_carrefour in ('CROIX', 'T'):
            with self.subTest(type=type_carrefour):
                geometrie = (47, 893, 470, 268.37, 536.74, 114.2)
                haut = 34.26 if type_carrefour == 'CROIX' else None
                etat = EtatCarrefour(type_carrefour=type_carrefour)
                etat.geometries_affichage['test'] = (geometrie, haut)
                etat.distances_affichage['test'] = VueCarrefourBase._distances_securite(geometrie, haut)
                gauche = Vehicule('Engagee', 'voiture', 'E', '1', manoeuvre='GAUCHE', progression=40, engagee=True)
                suivante = Vehicule('Suivante', 'voiture', 'E', '2', progression=30, depassement_droite=True)
                urgence = Vehicule('Urgence', 'urgence', 'S', 'U', manoeuvre='DROITE', progression=30, prioritaire=True)
                voitures = (gauche, suivante, urgence)
                etat.vehicules = {v.nom: v for v in voitures}
                etat.changer_feux('S')
                clients = ClientsSimulation(etat)
                client = Mock()
                for _ in range(200):
                    for v in voitures:
                        if v.progression < 100:
                            clients._avancer_vehicule(client, v, prochaine_position(v.progression, etat.feux[v.direction]))
                        contours = [TrajectoireVehicule.contour(a, geometrie, haut)
                                    for a in voitures if a.progression < 100]
                        for index, contour in enumerate(contours):
                            for autre in contours[index + 1:]:
                                self.assertFalse(contour.intersects(autre))
                    if gauche.progression == urgence.progression == 100:
                        break
                self.assertEqual(100, gauche.progression)
                self.assertEqual(100, urgence.progression)
                self.assertEqual(30, suivante.progression)

    def test_quatre_branches_avec_urgence_et_drainage_complet(self):
        # Cette suite d'arrivees reproduisait un arret permanent apres 3 passages.
        hasard = random.Random(3)
        etat = EtatCarrefour()
        geometrie = (47, 893, 470, 268.37, 536.74, 114.2)
        haut = 34.26
        etat.geometries_affichage['test'] = (geometrie, haut)
        etat.distances_affichage['test'] = VueCarrefourBase._distances_securite(geometrie, haut)
        clients = ClientsSimulation(etat)
        client = Mock()
        for tick in range(1600):
            if tick < 600 and (tick % 25 == 0 or tick == 120):
                urgent = tick == 120
                direction = 'S' if urgent else ('N', 'S', 'E', 'O')[(tick // 25) % 4]
                manoeuvre = hasard.choice(etat.trajets[direction])
                position = 0
                while (voiture := clients._creer_vehicule(str(tick), 'urgence' if urgent else 'voiture',
                                                          direction, manoeuvre, position)) is None:
                    position -= 1
                if urgent:
                    voiture.prioritaire = True
                    etat.changer_feux(direction)
            voitures = list(etat.vehicules.values())
            hasard.shuffle(voitures)
            for voiture in voitures:
                clients._avancer_vehicule(client, voiture,
                                          prochaine_position(voiture.progression, etat.feux[voiture.direction]))
                if voiture.progression == 100:
                    etat.enregistrer_passage(voiture)
                    del etat.vehicules[voiture.nom]
                    if voiture.prioritaire:
                        etat.changer_feux(None)
            if tick % 12 == 0:
                etat.avancer_cycle()
            if tick >= 600 and not etat.vehicules:
                break
        self.assertEqual(25, etat.passages_termines)
        self.assertEqual(1, etat.urgences_traitees)
        self.assertEqual({}, etat.vehicules)
