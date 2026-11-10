"""Verifie les trajectoires des voitures sur les trois branches du T."""

import unittest

from client.config import LIGNE_ARRET
from client.vehicule import Vehicule
from client.trajectoire import TrajectoireVehicule as VueCarrefourT


class TrajectoiresCarrefourTTest(unittest.TestCase):
    def position(self, direction, manoeuvre, progression, largeur=1000, hauteur=600):
        voiture = Vehicule("Test", "voiture", direction, "1",
                           manoeuvre=manoeuvre, progression=progression)
        return VueCarrefourT._position_vehicule(
            voiture, largeur * 0.05, largeur * 0.95, largeur / 2,
            hauteur * 0.47, hauteur * 0.94, min(largeur, hauteur) * 0.2,
        )

    def test_trajets_continus_sur_les_voies_aux_differentes_tailles(self):
        trajets = (("E", "TOUT_DROIT"), ("E", "GAUCHE"),
                   ("O", "TOUT_DROIT"), ("O", "DROITE"),
                   ("S", "GAUCHE"), ("S", "DROITE"))
        for largeur, hauteur in ((1000, 600), (700, 500), (1400, 800)):
            centre_x, centre_y = largeur / 2, hauteur * 0.47
            demi = min(largeur, hauteur) * 0.1
            for direction, manoeuvre in trajets:
                precedente = None
                for progression in range(101):
                    with self.subTest(taille=(largeur, hauteur), direction=direction,
                                      manoeuvre=manoeuvre, progression=progression):
                        position, _, _, _ = self.position(
                            direction, manoeuvre, progression, largeur, hauteur)
                        sur_route = (abs(position.y() - centre_y) <= demi
                                     or (abs(position.x() - centre_x) <= demi
                                         and position.y() >= centre_y))
                        self.assertTrue(sur_route)
                        if precedente is not None:
                            self.assertLess((position - precedente).manhattanLength(), largeur * 0.03)
                        precedente = position

    def test_voitures_approchent_et_quittent_le_carrefour(self):
        for direction, manoeuvre in (("E", "TOUT_DROIT"), ("O", "DROITE"), ("S", "GAUCHE")):
            debut = self.position(direction, manoeuvre, 0)[0]
            arret = self.position(direction, manoeuvre, 30)[0]
            fin = self.position(direction, manoeuvre, 100)[0]
            self.assertNotEqual(debut, arret)
            self.assertNotEqual(arret, fin)
        # Une file d'attente reste en amont de son point d'apparition.
        self.assertGreater(self.position("E", "TOUT_DROIT", -20)[0].x(), 950)

    def test_arret_juste_avant_la_ligne_sur_les_trois_branches(self):
        for largeur, hauteur in ((700, 500), (1000, 600), (1400, 800), (400, 300)):
            epaisseur = min(largeur, hauteur) * 0.2
            demi = epaisseur / 2
            trait = max(4.0, epaisseur * 0.05)
            centre_x, centre_y = largeur / 2, hauteur * 0.47
            for direction, manoeuvre in (("S", "DROITE"), ("S", "GAUCHE"),
                                         ("E", "TOUT_DROIT"), ("E", "GAUCHE"),
                                         ("O", "TOUT_DROIT"), ("O", "DROITE")):
                with self.subTest(taille=(largeur, hauteur), direction=direction, manoeuvre=manoeuvre):
                    position, _, longueur, _ = self.position(
                        direction, manoeuvre, LIGNE_ARRET, largeur, hauteur)
                    # Inclut le demi-pixel du contour de la carrosserie.
                    avant = longueur / 2 + 0.5
                    if direction == "S":
                        ecart = position.y() - avant - (centre_y + demi + trait)
                    elif direction == "E":
                        ecart = position.x() - avant - (centre_x + demi + trait)
                    else:
                        ecart = (centre_x - demi - trait) - (position.x() + avant)
                    self.assertAlmostEqual(3.0, ecart)

    def test_branche_nord_absente_du_t(self):
        self.assertIsNone(self.position("N", "TOUT_DROIT", 40))
        self.assertIsNone(self.position("S", "TOUT_DROIT", 60))
        self.assertIsNone(self.position("E", "DROITE", 60))
        self.assertIsNone(self.position("O", "GAUCHE", 60))


if __name__ == "__main__":
    unittest.main()
