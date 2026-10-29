"""Verifie le redemarrage de files au vert jusqu'a la sortie du carrefour."""

import unittest
from unittest.mock import Mock

from server.config import LIGNE_ARRET
from server.model.EtatCarrefour import EtatCarrefour
from server.model.ServeurCarrefour import ServeurCarrefour
from server.model.TrajectoireVehicule import TrajectoireVehicule
from server.model.Vehicule import Vehicule
from server.model.VueCarrefourBase import VueCarrefourBase


class RedemarrageTest(unittest.TestCase):
    def test_distance_conservee_pour_deux_voitures_dans_la_meme_file(self):
        etat = EtatCarrefour()
        etat.distances_affichage['test'] = {'S': 6}
        premiere = Vehicule('Premiere', 'voiture', 'S', '1', manoeuvre='GAUCHE',
                             progression=45, engagee=True)
        suivante = Vehicule('Suivante', 'voiture', 'S', '2',
                            progression=39, engagee=True, manoeuvre='GAUCHE')
        etat.vehicules = {v.nom: v for v in (premiere, suivante)}
        serveur = ServeurCarrefour(etat)
        client = Mock()
        serveur._avancer_vehicule(client, suivante, 40)
        self.assertEqual(39, suivante.progression)
        client.sendall.assert_called_with(b'ATTENTE\n')

    def test_files_au_vert_sans_chevauchement_et_sans_blocage(self):
        for largeur, hauteur in ((700, 500), (1000, 600), (1400, 500)):
            geometrie = (largeur * .05, largeur * .95, largeur / 2,
                         hauteur * .47, hauteur * .94, min(largeur, hauteur) * .2)
            haut = hauteur * .06
            distances = VueCarrefourBase._distances_securite(geometrie, haut)
            for direction in ('N', 'S', 'E', 'O'):
                for manoeuvres in (('TOUT_DROIT',) * 4, ('DROITE',) * 4,
                                   ('GAUCHE',) * 4, ('DROITE', 'GAUCHE', 'TOUT_DROIT', 'DROITE')):
                    with self.subTest(taille=(largeur, hauteur), direction=direction, manoeuvres=manoeuvres):
                        etat = EtatCarrefour()
                        etat.distances_affichage['test'] = distances
                        etat.geometries_affichage['test'] = (geometrie, haut)
                        voitures = [Vehicule(str(i), 'voiture', direction, str(i),
                                             manoeuvre=manoeuvre,
                                             progression=LIGNE_ARRET - i * distances[direction])
                                    for i, manoeuvre in enumerate(manoeuvres)]
                        etat.vehicules = {v.nom: v for v in voitures}
                        serveur = ServeurCarrefour(etat)
                        client = Mock()
                        etat.feux[direction] = 'ROUGE'
                        serveur._avancer_vehicule(client, voitures[0], LIGNE_ARRET + 1)
                        self.assertEqual(LIGNE_ARRET, voitures[0].progression)
                        etat.feux[direction] = 'VERT'
                        # Les suiveuses demandent leur pas avant la voiture de tete,
                        # comme cela peut arriver avec des clients sur des threads differents.
                        for _ in range(600):
                            for voiture in reversed(voitures):
                                if voiture.progression < 100:
                                    serveur._avancer_vehicule(client, voiture, voiture.progression + 1)
                            contours = [TrajectoireVehicule.contour(v, geometrie, haut)
                                        for v in voitures if v.progression < 100]
                            for index, contour in enumerate(contours):
                                for autre in contours[index + 1:]:
                                    self.assertFalse(contour.intersects(autre))
                            if all(v.progression == 100 for v in voitures):
                                break
                        self.assertTrue(all(v.progression == 100 for v in voitures),
                                        [(v.nom, v.progression) for v in voitures])

    def test_croisement_oppose_ne_bloque_pas_les_voitures_face_a_face(self):
        geometrie = (50, 950, 500, 282, 564, 120)
        for manoeuvres in (('GAUCHE', 'GAUCHE'), ('GAUCHE', 'TOUT_DROIT'), ('GAUCHE', 'DROITE'),
                           ('TOUT_DROIT', 'TOUT_DROIT')):
            with self.subTest(manoeuvres=manoeuvres):
                etat = EtatCarrefour()
                etat.distances_affichage['test'] = VueCarrefourBase._distances_securite(geometrie, 36)
                etat.geometries_affichage['test'] = (geometrie, 36)
                voitures = [Vehicule(str(i), 'voiture', direction, str(i),
                                      manoeuvre=manoeuvre, progression=LIGNE_ARRET)
                            for i, (direction, manoeuvre) in enumerate(zip(('N', 'S'), manoeuvres))]
                etat.vehicules = {v.nom: v for v in voitures}
                serveur = ServeurCarrefour(etat)
                client = Mock()
                for _ in range(300):
                    for voiture in voitures:
                        if voiture.progression < 100:
                            serveur._avancer_vehicule(client, voiture, voiture.progression + 1)
                    if all(v.progression < 100 for v in voitures):
                        contours = [TrajectoireVehicule.contour(v, geometrie, 36) for v in voitures]
                        self.assertFalse(contours[0].intersects(contours[1]))
                    if all(v.progression == 100 for v in voitures):
                        break
                self.assertTrue(all(v.progression == 100 for v in voitures),
                                [v.progression for v in voitures])

    def test_arrivee_au_rouge_verifie_le_contour_avant_de_placer_sur_la_ligne(self):
        geometrie = (47, 893, 470, 272.6, 545.2, 116)
        for direction, progression in (('O', 37), ('E', 37), ('S', 38), ('N', 38)):
            with self.subTest(direction=direction):
                etat = EtatCarrefour()
                etat.geometries_affichage['test'] = (geometrie, 34.8)
                etat.distances_affichage['test'] = VueCarrefourBase._distances_securite(geometrie, 34.8)
                tete = Vehicule('Tete', 'voiture', direction, '1',
                                progression=progression, engagee=True)
                suivante = Vehicule('Suivante', 'voiture', direction, '2', progression=29)
                etat.vehicules = {v.nom: v for v in (tete, suivante)}
                etat.feux[direction] = 'ROUGE'
                serveur = ServeurCarrefour(etat)
                client = Mock()
                # Les deux voitures sont encore separees avant la demande.
                self.assertFalse(TrajectoireVehicule.mouvement_occupe(
                    suivante, 29, (tete,), ((geometrie, 34.8),)))
                serveur._avancer_vehicule(client, suivante, 30)
                self.assertEqual(29, suivante.progression)
                client.sendall.assert_called_with(b'ATTENTE\n')
                # La tete peut finir de degager la zone meme si le feu est rouge.
                for _ in range(100):
                    if tete.progression == 100:
                        break
                    serveur._avancer_vehicule(client, tete, tete.progression + 1)
                self.assertEqual(100, tete.progression)
                serveur._avancer_vehicule(client, suivante, 30)
                self.assertEqual(30, suivante.progression)
                serveur._avancer_vehicule(client, suivante, 31)
                self.assertEqual(30, suivante.progression)

    def test_urgence_au_sud_laisse_sortir_la_voiture_deja_engagee_a_est(self):
        from client.client_vehicule import prochaine_position

        geometrie = (47, 893, 470, 272.6, 545.2, 116)
        etat = EtatCarrefour()
        etat.geometries_affichage['test'] = (geometrie, 34.8)
        etat.distances_affichage['test'] = VueCarrefourBase._distances_securite(geometrie, 34.8)
        voitures = [
            Vehicule('Est-engagee', 'voiture', 'E', '1', progression=37, engagee=True),
            Vehicule('Est-suivante', 'voiture', 'E', '2', progression=29),
            Vehicule('Sud-tete', 'voiture', 'S', '3', manoeuvre='DROITE', progression=30),
            Vehicule('Ambulance', 'urgence', 'S', 'U', manoeuvre='GAUCHE',
                     progression=30 - etat.distance_securite('S'), prioritaire=True),
        ]
        etat.vehicules = {v.nom: v for v in voitures}
        etat.changer_feux('S')
        serveur = ServeurCarrefour(etat)
        client = Mock()
        terminees = set()
        for _ in range(400):
            for voiture in list(etat.vehicules.values()):
                demande = prochaine_position(voiture.progression, etat.feux[voiture.direction])
                serveur._avancer_vehicule(client, voiture, demande)
                if voiture.progression == 100:
                    terminees.add(voiture.nom)
                    del etat.vehicules[voiture.nom]
            if len(terminees) == 3:
                break
        self.assertEqual({'Est-engagee', 'Sud-tete', 'Ambulance'}, terminees)
        self.assertEqual(30, etat.vehicules['Est-suivante'].progression)
