"""Tests des programmes separes client et serveur."""

import contextlib
import io
import socket
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from client.client_vehicule import prochaine_position, simuler_vehicule
from client import config as config_client
from server import config as config_serveur
from server.model.BaseDonnees import BaseDonnees
from server.model.EtatCarrefour import EtatCarrefour
from server.model.FenetreCarrefour import FenetreCarrefour
from server.model.ServeurCarrefour import ServeurCarrefour
from server.model.Vehicule import Vehicule


class SeparationTest(unittest.TestCase):
    def test_constantes_du_protocole_identiques(self):
        self.assertEqual(config_client.PORT, config_serveur.PORT)

    def test_client_gere_sa_position_au_feu(self):
        self.assertEqual(config_serveur.LIGNE_ARRET, prochaine_position(config_serveur.LIGNE_ARRET, "ROUGE"))
        self.assertEqual(config_serveur.LIGNE_ARRET + 1, prochaine_position(config_serveur.LIGNE_ARRET, "VERT"))

    def test_client_signale_une_connexion_impossible(self):
        with patch("client.client_vehicule.socket.create_connection", side_effect=OSError("serveur absent")):
            with contextlib.redirect_stdout(io.StringIO()) as sortie:
                simuler_vehicule("Test", "voiture", "N", "TOUT_DROIT")
        self.assertIn("serveur absent", sortie.getvalue())
        self.assertNotIn("a traverse", sortie.getvalue())

    def test_le_serveur_ne_renvoie_pas_de_position(self):
        etat = EtatCarrefour()
        serveur = ServeurCarrefour(etat, host="127.0.0.1", port=0)
        serveur.demarrer()
        try:
            with socket.create_connection(("127.0.0.1", serveur.port), timeout=2) as voiture:
                lecteur = voiture.makefile("r", encoding="utf-8")
                voiture.sendall(b"IDENTITE|Test|voiture|N|DROITE|0\n")
                self.assertEqual("OK", lecteur.readline().strip())

                voiture.sendall(b"ETAT\n")
                self.assertEqual("FEU|N|VERT", lecteur.readline().strip())

                voiture.sendall(b"POSITION|1\n")
                self.assertEqual("OK", lecteur.readline().strip())
                self.assertEqual(1, etat.vehicules["Test"].progression)

                voiture.sendall(b"POSITION|100\n")
                self.assertEqual("ATTENTE", lecteur.readline().strip())
        finally:
            serveur.arreter()

    def test_deux_clients_choisissent_leur_place(self):
        etat = EtatCarrefour()
        serveur = ServeurCarrefour(etat, host="127.0.0.1", port=0)
        serveur.demarrer()
        try:
            with socket.create_connection(("127.0.0.1", serveur.port), timeout=2) as premier:
                with socket.create_connection(("127.0.0.1", serveur.port), timeout=2) as second:
                    lecteur1 = premier.makefile("r", encoding="utf-8")
                    lecteur2 = second.makefile("r", encoding="utf-8")
                    premier.sendall(b"IDENTITE|Premier|voiture|N|TOUT_DROIT|0\n")
                    self.assertEqual("OK", lecteur1.readline().strip())
                    second.sendall(b"IDENTITE|Second|voiture|N|DROITE|0\n")
                    self.assertEqual("ATTENTE", lecteur2.readline().strip())
                    second.sendall(b"IDENTITE|Second|voiture|N|DROITE|-20\n")
                    self.assertEqual("OK", lecteur2.readline().strip())
                    self.assertEqual(-20, etat.vehicules["Second"].progression)
        finally:
            serveur.arreter()

    def test_serveur_refuse_le_passage_au_rouge(self):
        etat = EtatCarrefour()
        serveur = ServeurCarrefour(etat)
        client = Mock()
        voiture = Vehicule("Rouge", "voiture", "E", "1", progression=config_serveur.LIGNE_ARRET)
        with etat.verrou:
            etat.vehicules[voiture.nom] = voiture

        serveur._avancer_vehicule(client, voiture, config_serveur.LIGNE_ARRET + 1)
        self.assertEqual(config_serveur.LIGNE_ARRET, voiture.progression)
        client.sendall.assert_called_with(b"ATTENTE\n")
        self.assertGreater(etat.temps_attente_total, 0)

    def test_voiture_perpendiculaire_attend_la_fin_du_croisement(self):
        etat = EtatCarrefour()
        serveur = ServeurCarrefour(etat)
        client = Mock()
        ancienne = Vehicule("Est", "voiture", "E", "1", progression=45, engagee=True)
        nouvelle = Vehicule("Nord", "voiture", "N", "2", progression=34)
        etat.vehicules = {ancienne.nom: ancienne, nouvelle.nom: nouvelle}
        etat.feux = {"N": "VERT", "S": "VERT", "E": "ROUGE", "O": "ROUGE"}

        serveur._avancer_vehicule(client, nouvelle, 35)
        self.assertEqual(34, nouvelle.progression)
        client.sendall.assert_called_with(b"ATTENTE\n")

        ancienne.progression = 71
        serveur._avancer_vehicule(client, nouvelle, 35)
        self.assertEqual(35, nouvelle.progression)
        client.sendall.assert_called_with(b"OK\n")

    def test_vert_oppose_attend_la_sortie_des_voitures_engagees(self):
        etat = EtatCarrefour()
        etat.phase = "NS_ORANGE"
        etat.temps_phase = 1
        etat.feux = {"N": "ORANGE", "S": "ORANGE", "E": "ROUGE", "O": "ROUGE"}
        voiture = Vehicule("Nord", "voiture", "N", "1", progression=45, engagee=True)
        etat.vehicules[voiture.nom] = voiture
        fenetre = Mock()
        fenetre.vue.etat = etat

        FenetreCarrefour.changer_cycle_normal(fenetre)
        self.assertEqual("NS_ORANGE", etat.phase)
        self.assertEqual("ROUGE", etat.feux["E"])

        voiture.progression = 71
        FenetreCarrefour.changer_cycle_normal(fenetre)
        self.assertEqual("EO_VERT", etat.phase)
        self.assertEqual("VERT", etat.feux["E"])

    def test_passage_enregistre_dans_sqlite(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "carrefour.sqlite3"
            etat = EtatCarrefour(BaseDonnees(chemin))
            voiture = Vehicule("Test", "voiture", "N", "1")
            etat.enregistrer_attente(voiture, 0.16)
            etat.enregistrer_passage(voiture)

            with sqlite3.connect(chemin) as connexion:
                passages = connexion.execute(
                    "SELECT type_vehicule, direction, temps_attente FROM circulation"
                ).fetchall()
            self.assertEqual([("voiture", "N", 0.16)], passages)

    def test_ancienne_table_sqlite_reste_intacte(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "carrefour.sqlite3"
            with sqlite3.connect(chemin) as connexion:
                connexion.execute("CREATE TABLE passages (nom TEXT NOT NULL)")
                connexion.execute("INSERT INTO passages VALUES ('Ancienne voiture')")

            etat = EtatCarrefour(BaseDonnees(chemin))
            etat.enregistrer_passage(Vehicule("Nouvelle", "voiture", "S", "2"))

            with sqlite3.connect(chemin) as connexion:
                ancien = connexion.execute("SELECT nom FROM passages").fetchone()
                nouveau = connexion.execute("SELECT direction FROM circulation").fetchone()
            self.assertEqual(("Ancienne voiture",), ancien)
            self.assertEqual(("S",), nouveau)

    def test_echec_sqlite_ne_compte_pas_le_passage(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "carrefour.sqlite3"
            with sqlite3.connect(chemin) as connexion:
                connexion.execute("CREATE TABLE circulation (id INTEGER PRIMARY KEY)")
            etat = EtatCarrefour(BaseDonnees(chemin))

            with contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(sqlite3.Error):
                    etat.enregistrer_passage(Vehicule("Test", "voiture", "N", "1"))
            self.assertEqual(0, etat.passages_termines)

    def test_voiture_et_urgence_completes(self):
        etat = EtatCarrefour()
        serveur = ServeurCarrefour(etat, host="127.0.0.1", port=0)
        serveur.demarrer()
        try:
            with patch("client.client_vehicule.HOST", "127.0.0.1"), patch("client.client_vehicule.PORT", serveur.port):
                with patch("client.client_vehicule._get_parametres_simulation", return_value=(config_serveur.LIGNE_ARRET, config_serveur.PAS_AVANCEMENT, 0)):
                    with contextlib.redirect_stdout(io.StringIO()):
                        simuler_vehicule("Voiture-Test", "voiture", "N", "DROITE")
                        simuler_vehicule("Ambulance-Test", "urgence", "E", "TOUT_DROIT")

            for _ in range(50):
                if etat.passages_termines == 2:
                    break
                time.sleep(0.01)
            self.assertEqual(2, etat.passages_termines)
            self.assertEqual(1, etat.urgences_traitees)
        finally:
            serveur.arreter()


if __name__ == "__main__":
    unittest.main()
