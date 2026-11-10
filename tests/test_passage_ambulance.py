"""Verifie le rangement a droite, le depassement et la reinsertion apres l'urgence."""

import unittest
from unittest.mock import Mock

from support_simulation import EtatSimulation as EtatCarrefour
from support_simulation import SimulateurClients as ClientsSimulation
from client.trajectoire import TrajectoireVehicule
from client.vehicule import Vehicule
from client.trajectoire import TrajectoireVehicule as VueCarrefourBase


class PassageAmbulanceTest(unittest.TestCase):
    def verifier_separation(self, etat, geometrie, haut):
        contours = [TrajectoireVehicule.contour(v, geometrie, haut)
                    for v in etat.vehicules.values() if v.progression < 100]
        for index, contour in enumerate(contours):
            for autre in contours[index + 1:]:
                self.assertFalse(contour.intersects(autre))

    def test_ambulance_depasse_la_file_puis_les_voitures_repartent(self):
        for taille in ((700, 500), (1000, 600)):
            for type_carrefour, direction in (('CROIX', 'N'), ('CROIX', 'S'), ('CROIX', 'E'),
                                              ('CROIX', 'O'), ('T', 'S'), ('T', 'E'), ('T', 'O')):
                with self.subTest(taille=taille, type=type_carrefour, direction=direction):
                    largeur, hauteur = taille
                    geometrie = (largeur * .05, largeur * .95, largeur / 2,
                                 hauteur * .47, hauteur * .94, min(taille) * .2)
                    haut = hauteur * .06 if type_carrefour == 'CROIX' else None
                    etat = EtatCarrefour(type_carrefour=type_carrefour)
                    distances = VueCarrefourBase._distances_securite(geometrie, haut)
                    etat.distances_affichage['test'] = distances
                    etat.geometries_affichage['test'] = (geometrie, haut)
                    manoeuvre = 'DROITE' if type_carrefour == 'T' and direction == 'S' else 'TOUT_DROIT'
                    file = [Vehicule(str(i), 'voiture', direction, str(i), manoeuvre=manoeuvre,
                                      progression=30 - i * distances[direction]) for i in range(3)]
                    ambulance = Vehicule('Ambulance', 'urgence', direction, 'U', manoeuvre=manoeuvre,
                                          progression=30 - 3 * distances[direction], prioritaire=True)
                    derriere = Vehicule('Derriere', 'voiture', direction, '4', manoeuvre=manoeuvre,
                                         progression=30 - 4 * distances[direction])
                    voitures = file + [ambulance, derriere]
                    etat.vehicules = {v.nom: v for v in voitures}
                    etat.changer_feux(direction)
                    clients = ClientsSimulation(etat)
                    client = Mock()
                    rangees = set()
                    depassees = set()
                    terminees = []
                    for _ in range(700):
                        for voiture in voitures:
                            if voiture.progression == 100:
                                continue
                            clients._avancer_vehicule(client, voiture, voiture.progression + 1)
                            self.verifier_separation(etat, geometrie, haut)
                            if voiture.decalage_urgence == 1:
                                rangees.add(voiture.nom)
                            if voiture.progression == 100:
                                terminees.append(voiture.nom)
                        for voiture in file:
                            if ambulance.progression > voiture.progression:
                                depassees.add(voiture.nom)
                        if all(v.progression == 100 for v in voitures):
                            break
                    self.assertEqual({'0', '1', '2'}, rangees)
                    self.assertEqual({'0', '1', '2'}, depassees)
                    self.assertEqual('Ambulance', terminees[0])
                    self.assertTrue(all(v.progression == 100 for v in voitures),
                                    [(v.nom, v.progression, v.decalage_urgence) for v in voitures])
                    self.assertTrue(all(v.decalage_urgence == 0 for v in voitures))

    def test_retour_sur_la_voie_meme_si_le_feu_est_rouge(self):
        etat = EtatCarrefour()
        voiture = Vehicule('Rangee', 'voiture', 'E', '1', progression=30, decalage_urgence=1)
        etat.vehicules[voiture.nom] = voiture
        clients = ClientsSimulation(etat)
        client = Mock()
        for _ in range(12):
            clients._avancer_vehicule(client, voiture, 30)
        self.assertEqual(0, voiture.decalage_urgence)
        self.assertEqual(30, voiture.progression)
        self.assertFalse(voiture.retour_voie)
        client.sendall.assert_called_with(b'ATTENTE\n')

    def test_voiture_deja_engagee_finit_son_passage(self):
        etat = EtatCarrefour()
        voiture = Vehicule('Engagee', 'voiture', 'N', '1', progression=75, engagee=True)
        ambulance = Vehicule('Urgence', 'urgence', 'N', 'U', progression=0, prioritaire=True)
        etat.vehicules = {v.nom: v for v in (voiture, ambulance)}
        clients = ClientsSimulation(etat)
        clients._avancer_vehicule(Mock(), voiture, 76)
        self.assertEqual(76, voiture.progression)
        self.assertEqual(0, voiture.decalage_urgence)

    def test_urgence_pendant_la_preparation_d_un_depassement(self):
        geometrie = (50, 950, 500, 282, 564, 120)
        etat = EtatCarrefour()
        etat.distances_affichage['test'] = VueCarrefourBase._distances_securite(geometrie, 36)
        etat.geometries_affichage['test'] = (geometrie, 36)
        gauche = Vehicule('Gauche', 'voiture', 'N', '1', manoeuvre='GAUCHE', progression=40, engagee=True)
        normale = Vehicule('Normale', 'voiture', 'N', '2', progression=25, depassement_droite=True)
        urgence = Vehicule('Urgence', 'urgence', 'N', 'U', progression=10, prioritaire=True)
        opposee = Vehicule('Opposee', 'voiture', 'S', '3', progression=30)
        etat.vehicules = {v.nom: v for v in (gauche, normale, urgence, opposee)}
        etat.changer_feux('N')
        clients = ClientsSimulation(etat)
        client = Mock()
        for _ in range(500):
            for voiture in (gauche, normale, urgence):
                if voiture.progression < 100:
                    clients._avancer_vehicule(client, voiture, voiture.progression + 1)
                self.verifier_separation(etat, geometrie, 36)
            if all(v.progression == 100 for v in (gauche, normale, urgence)):
                break
        self.assertTrue(all(v.progression == 100 for v in (gauche, normale, urgence)),
                        [(v.nom, v.progression, v.decalage_urgence, v.retour_voie) for v in (gauche, normale, urgence)])
        self.assertEqual(0, normale.decalage_urgence)
        self.assertEqual(30, opposee.progression)

    def test_voiture_normale_reste_derriere_une_voiture_rangee(self):
        for type_carrefour, direction, manoeuvre in (
                ('CROIX', 'N', 'TOUT_DROIT'), ('CROIX', 'S', 'TOUT_DROIT'),
                ('T', 'S', 'DROITE'), ('T', 'E', 'TOUT_DROIT'), ('T', 'O', 'TOUT_DROIT')):
            with self.subTest(type=type_carrefour, direction=direction):
                geometrie = (50, 950, 500, 282, 564, 120)
                haut = 36 if type_carrefour == 'CROIX' else None
                etat = EtatCarrefour(type_carrefour=type_carrefour)
                etat.geometries_affichage['test'] = (geometrie, haut)
                distances = TrajectoireVehicule._distances_securite(geometrie, haut)
                etat.distances_affichage['test'] = distances
                rangee = Vehicule('Rangee', 'voiture', direction, '1', manoeuvre=manoeuvre,
                                   progression=30, decalage_urgence=1)
                suivante = Vehicule('Suivante', 'voiture', direction, '2', manoeuvre=manoeuvre,
                                     progression=30-distances[direction])
                etat.vehicules = {v.nom: v for v in (rangee, suivante)}
                etat.changer_feux(direction)
                clients = ClientsSimulation(etat)
                # La voiture rangee n'a pas encore recu son prochain tour de calcul.
                # La suivante ne doit pas profiter du refuge pour depasser.
                clients._avancer_vehicule(Mock(), suivante, suivante.progression+1)
                self.assertEqual(30-distances[direction], suivante.progression)
                for _ in range(200):
                    for voiture in (suivante, rangee):
                        if voiture.progression < 100:
                            clients._avancer_vehicule(Mock(), voiture, voiture.progression+1)
                        self.verifier_separation(etat, geometrie, haut)
                self.assertEqual((100, 100), (rangee.progression, suivante.progression))

    def test_deux_urgences_successives_ne_coincent_pas_la_file(self):
        geometrie = (50, 950, 500, 282, 564, 120)
        etat = EtatCarrefour(type_carrefour='T')
        etat.geometries_affichage['test'] = (geometrie, None)
        distances = TrajectoireVehicule._distances_securite(geometrie)
        etat.distances_affichage['test'] = distances
        voitures = [Vehicule('Tete', 'voiture', 'E', '1', progression=30),
                    Vehicule('Urgence1', 'urgence', 'E', 'U', progression=26, prioritaire=True),
                    Vehicule('Suivante', 'voiture', 'E', '2', progression=22)]
        etat.vehicules = {v.nom: v for v in voitures}
        etat.changer_feux('E')
        clients = ClientsSimulation(etat)
        deuxieme = None
        for _ in range(500):
            # La suivante calcule avant la tete rangee : ordre qui reproduisait le bug.
            for voiture in reversed(voitures):
                if voiture.progression < 100:
                    clients._avancer_vehicule(Mock(), voiture, voiture.progression+1)
                self.verifier_separation(etat, geometrie, None)
            if voitures[1].progression == 100 and deuxieme is None:
                deuxieme = Vehicule('Urgence2', 'urgence', 'E', 'U', progression=0, prioritaire=True)
                voitures.append(deuxieme)
                etat.vehicules[deuxieme.nom] = deuxieme
            if deuxieme is not None and all(v.progression == 100 for v in voitures):
                break
        self.assertIsNotNone(deuxieme)
        self.assertTrue(all(v.progression == 100 for v in voitures),
                        [(v.nom, v.progression, v.decalage_urgence) for v in voitures])
