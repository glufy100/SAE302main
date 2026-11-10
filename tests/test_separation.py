"""Tests du protocole : les calculs sont locaux, le serveur stocke les rapports."""

from contextlib import contextmanager, redirect_stdout
from dataclasses import asdict
import io
import json
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from client import client_vehicule as reseau
from client.conduite import ConduiteVehicule, Perception, actualiser_affichage, proposer_arrivee
from client.config import LIGNE_ARRET
from server.model.BaseDonnees import BaseDonnees
from server.model.EtatCarrefour import EtatCarrefour
from server.model.ServeurCarrefour import ServeurCarrefour
from server.model.Vehicule import Vehicule


class SeparationTest(unittest.TestCase):
    def serveur(self):
        etat = EtatCarrefour()
        serveur = ServeurCarrefour(etat, host='127.0.0.1', port=0)
        serveur.demarrer()
        self.addCleanup(serveur.arreter)
        return etat, serveur

    @contextmanager
    def connexion(self, serveur):
        with socket.create_connection(('127.0.0.1', serveur.port), timeout=10) as client:
            with client.makefile('r', encoding='utf-8') as lecteur:
                yield client, lecteur

    def inscrire(self, connexion, nom, direction, manoeuvre='TOUT_DROIT', position=None):
        client, lecteur = connexion
        instantane = reseau.recevoir_instantane(client, lecteur)
        voiture = proposer_arrivee(nom, 'voiture', direction, manoeuvre, instantane)
        if position is not None:
            voiture.progression = position
            actualiser_affichage(voiture, Perception(instantane))
        self.assertEqual(['OK'], reseau.publier(client, lecteur, 'IDENTITE', voiture, instantane['revision']))
        return voiture

    def test_client_gere_sa_position_au_feu(self):
        self.assertEqual(LIGNE_ARRET, reseau.prochaine_position(LIGNE_ARRET, 'ROUGE'))
        self.assertEqual(LIGNE_ARRET + 1, reseau.prochaine_position(LIGNE_ARRET, 'VERT'))

    def test_client_signale_une_connexion_impossible(self):
        with patch('client.client_vehicule.socket.create_connection', side_effect=OSError('serveur absent')):
            with redirect_stdout(io.StringIO()) as sortie:
                reseau.simuler_vehicule('Test', 'voiture', 'N', 'TOUT_DROIT')
        self.assertIn('serveur absent', sortie.getvalue())
        self.assertNotIn('a traverse', sortie.getvalue())

    def test_serveur_enregistre_exactement_la_pose_calculee_par_le_client(self):
        etat, serveur = self.serveur()
        with self.connexion(serveur) as connexion:
            self.inscrire(connexion, 'Test', 'N', 'DROITE')
            instantane = reseau.recevoir_instantane(*connexion)
            perception = Perception(instantane)
            proposition, _ = ConduiteVehicule(perception).calculer(perception.vehicules['Test'])
            # Le serveur doit conserver la pose transmise, pas la recalculer.
            pose = proposition.position_affichage = (123.25, 456.75, -17.5, 32, 20.8)
            self.assertEqual(['OK'], reseau.publier(*connexion, 'POSITION', proposition, instantane['revision']))
            self.assertEqual(tuple(pose), etat.vehicules['Test'].position_affichage)
            self.assertEqual(proposition.progression, etat.vehicules['Test'].progression)
            self.assertFalse(hasattr(serveur, '_avancer_vehicule'))
            self.assertFalse(hasattr(serveur, '_ranger_pour_urgence'))
            self.assertFalse(hasattr(serveur, '_preparer_depassement'))

    def test_deux_clients_calculent_leur_place_et_reevaluent_un_etat_ancien(self):
        etat, serveur = self.serveur()
        with self.connexion(serveur) as c1, self.connexion(serveur) as c2:
            initial = reseau.recevoir_instantane(*c1)
            premier = proposer_arrivee('Premier', 'voiture', 'N', 'TOUT_DROIT', initial)
            second = proposer_arrivee('Second', 'voiture', 'N', 'DROITE', initial)
            self.assertEqual(0, second.progression)
            self.assertEqual(['OK'], reseau.publier(*c1, 'IDENTITE', premier, initial['revision']))
            self.assertEqual(['REESSAYER'], reseau.publier(*c2, 'IDENTITE', second, initial['revision']))
            self.assertNotIn('Second', etat.vehicules)
            nouveau = reseau.recevoir_instantane(*c2)
            second = proposer_arrivee('Second', 'voiture', 'N', 'DROITE', nouveau)
            self.assertLess(second.progression, 0)
            self.assertEqual(['OK'], reseau.publier(*c2, 'IDENTITE', second, nouveau['revision']))
            self.assertEqual(second.progression, etat.vehicules['Second'].progression)

    def test_deux_mouvements_concurrents_sont_recalcules_cote_client(self):
        etat, serveur = self.serveur()
        with self.connexion(serveur) as c1, self.connexion(serveur) as c2:
            self.inscrire(c1, 'Nord', 'N', 'GAUCHE', position=30)
            self.inscrire(c2, 'Sud', 'S', 'GAUCHE', position=30)
            instantane = reseau.recevoir_instantane(*c1)
            p1, p2 = Perception(instantane), Perception(instantane)
            nord, _ = ConduiteVehicule(p1).calculer(p1.vehicules['Nord'])
            sud, _ = ConduiteVehicule(p2).calculer(p2.vehicules['Sud'])
            self.assertEqual(31, nord.progression)
            self.assertEqual(31, sud.progression)
            self.assertEqual(['OK'], reseau.publier(*c1, 'POSITION', nord, instantane['revision']))
            self.assertEqual(['REESSAYER'], reseau.publier(*c2, 'POSITION', sud, instantane['revision']))
            nouveau = reseau.recevoir_instantane(*c2)
            perception = Perception(nouveau)
            sud, attente = ConduiteVehicule(perception).calculer(perception.vehicules['Sud'])
            self.assertTrue(attente)
            self.assertEqual(30, sud.progression)
            self.assertEqual(['OK'], reseau.publier(*c2, 'POSITION', sud, nouveau['revision']))
            self.assertEqual(30, etat.vehicules['Sud'].progression)

    def test_feu_modifie_invalide_la_proposition_client(self):
        etat, serveur = self.serveur()
        with self.connexion(serveur) as connexion:
            self.inscrire(connexion, 'Test', 'N', position=30)
            instantane = reseau.recevoir_instantane(*connexion)
            perception = Perception(instantane)
            proposition, _ = ConduiteVehicule(perception).calculer(perception.vehicules['Test'])
            etat.changer_feux('E')
            self.assertEqual(['REESSAYER'], reseau.publier(*connexion, 'POSITION', proposition, instantane['revision']))
            perception = Perception(reseau.recevoir_instantane(*connexion))
            proposition, attente = ConduiteVehicule(perception).calculer(perception.vehicules['Test'])
            self.assertTrue(attente)
            self.assertEqual(30, proposition.progression)
            self.assertFalse(proposition.engagee)

    def test_client_copie_seul_fonctionne_sans_pyside_ni_dossier_serveur(self):
        etat, serveur = self.serveur()
        with tempfile.TemporaryDirectory() as dossier:
            destination = Path(dossier) / 'client'
            shutil.copytree(Path(__file__).resolve().parents[1] / 'client', destination,
                            ignore=shutil.ignore_patterns('__pycache__'))
            code = f'''import sys
sys.path.insert(0, {str(destination)!r})
import client_vehicule as c
c.HOST = '127.0.0.1'
c.PORT = {serveur.port}
c._get_parametres_simulation = lambda: (30, 1, 0)
c.simuler_vehicule('Isole', 'voiture', 'N', 'DROITE')
assert not any(n.startswith(('PySide6', 'server')) for n in sys.modules)
'''
            resultat = subprocess.run([sys.executable, '-I', '-S', '-c', code], cwd=dossier,
                                      capture_output=True, text=True, timeout=20)
            self.assertEqual(0, resultat.returncode, resultat.stderr)
            self.assertIn('a traverse le carrefour', resultat.stdout)
            self.assertEqual(1, etat.passages_termines)

    def test_clients_concurrents_et_urgence_terminent_leurs_trajets(self):
        etat, serveur = self.serveur()
        with patch('client.client_vehicule.HOST', '127.0.0.1'), \
             patch('client.client_vehicule.PORT', serveur.port), \
             patch('client.client_vehicule._get_parametres_simulation', return_value=(30, 1, 0)), \
             redirect_stdout(io.StringIO()) as sortie:
            donnees = [('A', 'voiture', 'N', 'TOUT_DROIT'), ('B', 'voiture', 'N', 'DROITE'),
                       ('C', 'urgence', 'S', 'TOUT_DROIT')]
            threads = [threading.Thread(target=reseau.simuler_vehicule, args=d) for d in donnees]
            for t in threads:
                t.start()
            for t in threads:
                t.join(20)
            self.assertTrue(all(not t.is_alive() for t in threads), sortie.getvalue())
        self.assertEqual(3, etat.passages_termines, sortie.getvalue())
        self.assertEqual(1, etat.urgences_traitees)

    def test_attente_immobile_ne_change_pas_la_version_du_trafic(self):
        etat, serveur = self.serveur()
        etat.changer_feux('E')
        with self.connexion(serveur) as c1, self.connexion(serveur) as c2:
            self.inscrire(c1, 'Arretee', 'N', position=30)
            self.inscrire(c2, 'Approche', 'S')
            instantane = reseau.recevoir_instantane(*c1)
            perception = Perception(instantane)
            immobile, attente = ConduiteVehicule(perception).calculer(perception.vehicules['Arretee'])
            self.assertTrue(attente)
            self.assertEqual(['OK'], reseau.publier(*c1, 'POSITION', immobile, instantane['revision']))
            self.assertEqual(instantane['revision'], etat.revision)
            self.assertGreater(etat.temps_attente_total, 0)
            approche, _ = ConduiteVehicule(Perception(instantane)).calculer(perception.vehicules['Approche'])
            self.assertEqual(['OK'], reseau.publier(*c2, 'POSITION', approche, instantane['revision']))

    def test_serveur_copie_seul_ne_depend_pas_des_modules_de_calcul_client(self):
        with tempfile.TemporaryDirectory() as dossier:
            destination = Path(dossier) / 'server'
            shutil.copytree(Path(__file__).resolve().parents[1] / 'server', destination,
                            ignore=shutil.ignore_patterns('__pycache__', 'data'))
            code = f"""import sys
sys.path.insert(0, {dossier!r})
import server.carrefour
from server.model.EtatCarrefour import EtatCarrefour
from server.model.ServeurCarrefour import ServeurCarrefour
s = ServeurCarrefour(EtatCarrefour())
assert not any(n == 'client' or n.startswith('client.') for n in sys.modules)
"""
            resultat = subprocess.run([sys.executable, '-I', '-c', code], cwd=dossier,
                                      capture_output=True, text=True, timeout=10)
            self.assertEqual(0, resultat.returncode, resultat.stderr)

    def test_passage_enregistre_dans_sqlite(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / 'carrefour.sqlite3'
            etat = EtatCarrefour(BaseDonnees(chemin))
            voiture = Vehicule('Test', 'voiture', 'N', '1', progression=100, temps_attente=.16)
            etat.enregistrer_passage(voiture)
            with sqlite3.connect(chemin) as connexion:
                passages = connexion.execute('SELECT type_vehicule, direction, temps_attente FROM circulation').fetchall()
            self.assertEqual([('voiture', 'N', .16)], passages)

    def test_ancienne_table_sqlite_reste_intacte(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / 'carrefour.sqlite3'
            with sqlite3.connect(chemin) as connexion:
                connexion.execute('CREATE TABLE passages (nom TEXT NOT NULL)')
                connexion.execute("INSERT INTO passages VALUES ('Ancienne voiture')")
            etat = EtatCarrefour(BaseDonnees(chemin))
            etat.enregistrer_passage(Vehicule('Nouvelle', 'voiture', 'S', '2', progression=100))
            with sqlite3.connect(chemin) as connexion:
                self.assertEqual(('Ancienne voiture',), connexion.execute('SELECT nom FROM passages').fetchone())
                self.assertEqual(('S',), connexion.execute('SELECT direction FROM circulation').fetchone())

    def test_echec_sqlite_ne_compte_pas_le_passage(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / 'carrefour.sqlite3'
            with sqlite3.connect(chemin) as connexion:
                connexion.execute('CREATE TABLE circulation (id INTEGER PRIMARY KEY)')
            etat = EtatCarrefour(BaseDonnees(chemin))
            with redirect_stdout(io.StringIO()), self.assertRaises(sqlite3.Error):
                etat.enregistrer_passage(Vehicule('Test', 'voiture', 'N', '1', progression=100))
            self.assertEqual(0, etat.passages_termines)
