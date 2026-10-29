"""Verifie les trajectoires du carrefour en croix, partagees avec le T."""

import unittest
from server.config import LIGNE_ARRET
from server.model.Vehicule import Vehicule
from server.model.VueCarrefour import VueCarrefour


class PositionArretTest(unittest.TestCase):
    def test_arret_sur_les_quatre_branches_et_tailles(self):
        for largeur, hauteur in ((700, 500), (1000, 600), (1400, 800)):
            epaisseur = min(largeur, hauteur) * 0.2
            cx, cy = largeur / 2, hauteur * 0.47
            trait = max(4.0, epaisseur * 0.05)
            geometrie = (largeur * 0.05, largeur * 0.95, cx, cy, hauteur * 0.94, epaisseur)
            for direction in ("N", "S", "E", "O"):
                with self.subTest(taille=(largeur, hauteur), direction=direction):
                    v = Vehicule("Test", "voiture", direction, "1", progression=LIGNE_ARRET)
                    position, _, longueur, _ = VueCarrefour._position_vehicule(v, *geometrie, hauteur * 0.06)
                    avant = longueur / 2 + 0.5
                    bord = epaisseur / 2 + trait
                    ecarts = {
                        "N": cy - bord - (position.y() + avant),
                        "S": position.y() - avant - (cy + bord),
                        "E": position.x() - avant - (cx + bord),
                        "O": cx - bord - (position.x() + avant),
                    }
                    self.assertAlmostEqual(3.0, ecarts[direction])

    def test_tous_les_virages_sont_continus(self):
        geometrie = (50, 950, 500, 282, 564, 120)
        for direction in ("N", "S", "E", "O"):
            for manoeuvre in ("TOUT_DROIT", "GAUCHE", "DROITE"):
                precedente = None
                for progression in range(101):
                    v = Vehicule("Test", "voiture", direction, "1", manoeuvre=manoeuvre, progression=progression)
                    position = VueCarrefour._position_vehicule(v, *geometrie, 36)[0]
                    if precedente is not None:
                        self.assertLess((position - precedente).manhattanLength(), 20)
                    precedente = position
