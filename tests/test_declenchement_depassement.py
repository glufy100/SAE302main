"""Le depassement depend de la voiture juste devant dans la file."""

import unittest
from unittest.mock import Mock

from support_simulation import EtatSimulation as EtatCarrefour
from support_simulation import SimulateurClients as ClientsSimulation
from client.trajectoire import TrajectoireVehicule
from client.vehicule import Vehicule
from client.trajectoire import TrajectoireVehicule as VueCarrefourBase


class DeclenchementDepassementTest(unittest.TestCase):
    def configurer(self, direction, manoeuvre_devant):
        etat = EtatCarrefour()
        geometrie = (50, 950, 500, 282, 564, 120)
        etat.geometries_affichage['test'] = (geometrie, 36)
        etat.distances_affichage['test'] = VueCarrefourBase._distances_securite(geometrie, 36)
        derriere = Vehicule('Derriere', 'voiture', direction, '1', progression=10)
        devant = Vehicule('Devant', 'voiture', direction, '2',
                          manoeuvre=manoeuvre_devant, progression=30)
        plus_loin = Vehicule('Plus-loin', 'voiture', direction, '3',
                             manoeuvre='GAUCHE', progression=55, engagee=True)
        # L'ordre du dictionnaire ne doit pas decider qui est juste devant.
        etat.vehicules = {v.nom: v for v in (plus_loin, derriere, devant)}
        etat.feux[direction] = 'ROUGE'
        return etat, ClientsSimulation(etat), derriere, devant, geometrie

    def test_pas_de_decalage_derriere_un_virage_a_droite_ou_un_tout_droit(self):
        for direction in ('N', 'S', 'E', 'O'):
            for manoeuvre in ('DROITE', 'TOUT_DROIT'):
                with self.subTest(direction=direction, manoeuvre=manoeuvre):
                    _, clients, voiture, _, geometrie = self.configurer(direction, manoeuvre)
                    client = Mock()
                    for _ in range(20):
                        clients._avancer_vehicule(client, voiture, voiture.progression + 1)
                        self.assertFalse(voiture.depassement_droite)
                    self.assertEqual(0, voiture.decalage_urgence)
                    reference = Vehicule('Reference', 'voiture', direction, '1', progression=voiture.progression)
                    self.assertEqual(TrajectoireVehicule._position_vehicule(reference, *geometrie, 36),
                                     TrajectoireVehicule._position_vehicule(voiture, *geometrie, 36))

    def test_depassement_prepare_si_la_voiture_juste_devant_est_engagee(self):
        for direction in ('N', 'S', 'E', 'O'):
            with self.subTest(direction=direction):
                etat, clients, voiture, devant, _ = self.configurer(direction, 'GAUCHE')
                devant.progression = 40
                devant.engagee = True
                etat.feux[direction] = 'VERT'
                voiture.progression = 30 - etat.distance_securite(direction)
                clients._avancer_vehicule(Mock(), voiture, voiture.progression + 1)
                self.assertTrue(voiture.depassement_droite)
                self.assertGreater(voiture.preparation_depassement, 0)
                self.assertLess(voiture.preparation_depassement, 1)

    def test_pas_de_preparation_loin_de_la_ligne(self):
        etat, clients, voiture, devant, geometrie = self.configurer('S', 'GAUCHE')
        devant.progression = 40
        devant.engagee = True
        etat.feux['S'] = 'VERT'
        for _ in range(10):
            clients._avancer_vehicule(Mock(), voiture, voiture.progression + 1)
            self.assertFalse(voiture.depassement_droite)
        reference = Vehicule('Reference', 'voiture', 'S', '1', progression=voiture.progression)
        self.assertEqual(TrajectoireVehicule._position_vehicule(reference, *geometrie, 36),
                         TrajectoireVehicule._position_vehicule(voiture, *geometrie, 36))

    def test_pas_de_decalage_avant_l_engagement_suffisant_du_virage(self):
        for progression in (30, 31, 35, 39):
            with self.subTest(progression=progression):
                etat, clients, voiture, devant, _ = self.configurer('S', 'GAUCHE')
                devant.progression = progression
                devant.engagee = progression > 30
                etat.feux['S'] = 'VERT'
                voiture.progression = 30 - etat.distance_securite('S')
                clients._avancer_vehicule(Mock(), voiture, voiture.progression + 1)
                self.assertFalse(voiture.depassement_droite)

    def test_pas_de_decalage_au_rouge_meme_si_le_virage_est_engage(self):
        etat, clients, voiture, devant, _ = self.configurer('S', 'GAUCHE')
        devant.progression = 40
        devant.engagee = True
        voiture.progression = 30 - etat.distance_securite('S')
        clients._avancer_vehicule(Mock(), voiture, voiture.progression + 1)
        self.assertFalse(voiture.depassement_droite)

    def test_decalage_progressif_sans_saut_ni_avance_pendant_la_preparation(self):
        etat, clients, voiture, devant, geometrie = self.configurer('S', 'GAUCHE')
        devant.progression = 40
        devant.engagee = True
        etat.feux['S'] = 'VERT'
        voiture.progression = depart = 30 - etat.distance_securite('S')
        precedent = TrajectoireVehicule._position_vehicule(voiture, *geometrie, 36)[0]
        for _ in range(10):
            clients._avancer_vehicule(Mock(), voiture, voiture.progression + 1)
            position = TrajectoireVehicule._position_vehicule(voiture, *geometrie, 36)[0]
            self.assertLessEqual((position - precedent).manhattanLength(), 4)
            self.assertEqual(depart, voiture.progression)
            precedent = position
        self.assertEqual(1, voiture.preparation_depassement)

    def test_pas_de_depassement_d_une_ambulance_qui_tourne_a_gauche(self):
        _, clients, voiture, devant, _ = self.configurer('N', 'GAUCHE')
        devant.prioritaire = True
        clients._avancer_vehicule(Mock(), voiture, 11)
        self.assertFalse(voiture.depassement_droite)
