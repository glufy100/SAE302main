"""Verifie les trajets du T et leur separation du carrefour en croix."""

from dataclasses import asdict
import json
import contextlib
import io
import socket
import time
import unittest
from unittest.mock import patch

from client.client_vehicule import get_trajets, simuler_vehicule
from client.voiture import simuler_voiture
from server.model.EtatCarrefour import EtatCarrefour
from server.model.ServeurCarrefour import ServeurCarrefour
from client.trajectoire import TrajectoireVehicule
from client.vehicule import Vehicule


class TraficTTest(unittest.TestCase):
    def test_tous_les_trajets_autorises_restent_visibles_jusqua_la_sortie(self):
        etat = EtatCarrefour(type_carrefour='T')
        self.assertEqual({'S', 'E', 'O'}, set(etat.trajets))
        geometrie = (50, 950, 500, 282, 564, 120)
        trajets = 0
        for direction, manoeuvres in etat.trajets.items():
            for manoeuvre in manoeuvres:
                voiture = Vehicule('Test', 'voiture', direction, '1', manoeuvre=manoeuvre)
                self.assertNotEqual('N', voiture.direction_sortie())
                for progression in range(101):
                    voiture.progression = progression
                    self.assertIsNotNone(TrajectoireVehicule._position_vehicule(voiture, *geometrie))
                trajets += 1
        self.assertEqual(6, trajets)

    def test_generateur_utilise_uniquement_les_trajets_fournis_par_le_serveur(self):
        trajets = EtatCarrefour(type_carrefour='T').trajets
        choix = ('DROITE', 'TOUT_DROIT', 'TOUT_DROIT', 'GAUCHE', 'GAUCHE', 'DROITE')
        with patch('client.voiture.get_trajets', return_value=trajets), \
             patch('client.voiture.random.choice', side_effect=choix), \
             patch('client.voiture.simuler_vehicule') as simuler:
            for numero in range(1, 7):
                simuler_voiture(numero, 'T')
        for appel in simuler.call_args_list:
            _, _, direction, manoeuvre, carrefour = appel.args
            self.assertIn(manoeuvre, trajets[direction])
            self.assertEqual('T', carrefour)

    def test_serveur_refuse_un_trajet_nord_sur_le_t(self):
        etat = EtatCarrefour(type_carrefour='T')
        serveur = ServeurCarrefour(etat)
        for direction, manoeuvre in (('N', 'TOUT_DROIT'), ('S', 'TOUT_DROIT'),
                                     ('E', 'DROITE'), ('O', 'GAUCHE')):
            voiture = Vehicule('Test', 'voiture', direction, '1', manoeuvre=manoeuvre,
                               position_affichage=(100, 100, 0, 32, 20.8))
            with self.assertRaises(ValueError):
                serveur._enregistrer_rapport(json.dumps({'revision': etat.revision, 'vehicule': asdict(voiture)}))
        self.assertEqual({}, etat.vehicules)
        for _ in range(20):
            etat.avancer_cycle()
            self.assertEqual('ROUGE', etat.feux['N'])

    def test_protocole_separe_les_vehicules_feux_et_passages(self):
        croix = EtatCarrefour()
        etat_t = EtatCarrefour(type_carrefour='T')
        serveur = ServeurCarrefour(croix, host='127.0.0.1', port=0, etat_t=etat_t)
        serveur.demarrer()
        get_trajets.cache_clear()
        try:
            with patch('client.client_vehicule.HOST', '127.0.0.1'), \
                 patch('client.client_vehicule.PORT', serveur.port), \
                 patch('client.client_vehicule._get_parametres_simulation', return_value=(30, 1, 0)):
                self.assertEqual({d: list(m) for d, m in etat_t.trajets.items()}, get_trajets('T'))
                self.assertIn('N', get_trajets('CROIX'))
                with contextlib.redirect_stdout(io.StringIO()):
                    for direction, manoeuvres in etat_t.trajets.items():
                        for manoeuvre in manoeuvres:
                            etat_t.changer_feux(direction)
                            simuler_vehicule(f'{direction}-{manoeuvre}', 'voiture', direction, manoeuvre, 'T')
                    simuler_vehicule('Ambulance-T', 'urgence', 'S', 'DROITE', 'T')
                for _ in range(100):
                    if etat_t.passages_termines == 7 and not etat_t.vehicules:
                        break
                    time.sleep(.01)
                self.assertEqual(7, etat_t.passages_termines)
                self.assertEqual(1, etat_t.urgences_traitees)
                self.assertEqual(0, croix.passages_termines)
                self.assertIsNone(croix.priorite)
                self.assertEqual('ROUGE', croix.feux['E'])
                self.assertEqual({}, croix.vehicules)
                # Un trajet impossible est rejete avec une erreur, sans boucle de creation.
                with socket.create_connection(('127.0.0.1', serveur.port), timeout=2) as client:
                    with client.makefile('r', encoding='utf-8') as lecteur:
                        client.sendall(b'CARREFOUR|T\n')
                        self.assertEqual('OK', lecteur.readline().strip())
                        client.sendall(b'INSTANTANE\n')
                        instantane = json.loads(lecteur.readline().split('|', 1)[1])
                        interdite = Vehicule('Interdite', 'voiture', 'E', '', manoeuvre='DROITE',
                                             position_affichage=(100, 100, 0, 32, 20.8))
                        paquet = json.dumps({'revision': instantane['revision'], 'vehicule': asdict(interdite)})
                        client.sendall(('IDENTITE|' + paquet + '\n').encode())
                        self.assertTrue(lecteur.readline().startswith('ERREUR|'))
        finally:
            get_trajets.cache_clear()
            serveur.arreter()

    def test_generateurs_ambulances_ciblent_aussi_les_trajets_du_t(self):
        from client.urgence import main

        for direction, manoeuvre in (('S', 'DROITE'), ('E', 'GAUCHE'), ('O', 'TOUT_DROIT')):
            with self.subTest(direction=direction), \
                 patch('sys.argv', ['urgence.py', '--generer', '1', '--carrefour', 'T']), \
                 patch('client.urgence.get_trajets', return_value=EtatCarrefour(type_carrefour='T').trajets), \
                 patch('client.urgence.time.sleep', side_effect=[None, KeyboardInterrupt]), \
                 patch('client.urgence.random.choice', side_effect=[direction, manoeuvre]), \
                 patch('client.urgence.simuler_vehicule') as simuler, \
                 contextlib.redirect_stdout(io.StringIO()):
                main()
                simuler.assert_called_once_with('Ambulance-T-1', 'urgence', direction, manoeuvre, 'T')

    def test_urgence_manuelle_choisit_un_trajet_valide_par_defaut_a_est(self):
        from client.urgence import main

        with patch('sys.argv', ['urgence.py', 'Ambulance', 'E', '--carrefour', 'T']), \
             patch('client.urgence.get_trajets', return_value=EtatCarrefour(type_carrefour='T').trajets), \
             patch('client.urgence.simuler_vehicule') as simuler:
            main()
        simuler.assert_called_once_with('Ambulance', 'urgence', 'E', 'TOUT_DROIT', 'T')
