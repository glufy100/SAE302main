"""Dessin partage par les carrefours en T et en croix."""

from dataclasses import replace
from math import ceil

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from server.config import LIGNE_ARRET
from server.model.EtatCarrefour import EtatCarrefour
from server.model.Vehicule import Vehicule
from server.model.TrajectoireVehicule import TrajectoireVehicule


class VueCarrefourBase(QWidget):
    """Partage les voitures, les feux et les dimensions entre les deux vues."""

    COULEUR_FOND = QColor("#d3e6c5")
    COULEUR_TROTTOIR = QColor("#e0dcd0")
    COULEURS_TOITS = ["#c4694f", "#a65e5e", "#8a7f6a", "#b0553f", "#7a6a9a"]
    COULEUR_ROUTE = QColor("#37444c")
    COULEUR_LIGNE = QColor("#ffffff")
    COULEUR_BOITIER = QColor("#2b2b2b")
    COULEUR_CONTOUR = QColor("#2b2b2b")
    ROUGE_ALLUME = QColor("#d94a4a")
    ROUGE_ETEINT = QColor("#4a2a2a")
    VERT_ALLUME = QColor("#2e9e6b")
    VERT_ETEINT = QColor("#1f3a2e")

    RAYON = 12
    ECART_FILE = TrajectoireVehicule.ECART_FILE
    ECART_LIGNE = TrajectoireVehicule.ECART_LIGNE
    CONTOUR_VEHICULE = TrajectoireVehicule.CONTOUR_VEHICULE

    def __init__(self, etat: EtatCarrefour):
        if not isinstance(etat, EtatCarrefour):
            raise TypeError("etat doit etre une instance de EtatCarrefour")
        super().__init__()
        self.etat = etat
        self.setMinimumSize(700, 500)

    def _geometrie(self):
        """Dimensions communes, proportionnelles a la taille de la vue."""
        largeur, hauteur = self.width(), self.height()
        epaisseur = min(largeur, hauteur) * 0.2
        return (largeur * 0.05, largeur * 0.95, largeur / 2,
                hauteur * 0.47, hauteur * 0.94, epaisseur)

    def _etat_affichage(self, geometrie, haut_stem=None):
        """Copie l'etat et ajuste les distances a la taille reelle des voitures."""
        distances = self._distances_securite(geometrie, haut_stem)
        with self.etat.verrou:
            self.etat.distances_affichage[type(self).__name__] = distances
            self.etat.geometries_affichage[type(self).__name__] = (geometrie, haut_stem)
            feux = dict(self.etat.feux)
            vehicules = [replace(v) for v in self.etat.vehicules.values()]
        return feux, vehicules

    @staticmethod
    def _distances_securite(geometrie, haut_stem=None):
        """Convertit la longueur des voitures en points de progression."""
        distances = {}
        for direction in (("N", "S", "E", "O") if haut_stem is not None else ("S", "E", "O")):
            # Le trajet avant le feu est rectiligne et independant du virage.
            manoeuvre = "DROITE" if direction == "S" and haut_stem is None else "TOUT_DROIT"
            voiture = Vehicule("geometrie", "voiture", direction, "", manoeuvre=manoeuvre)
            depart = VueCarrefourBase._position_vehicule(voiture, *geometrie, haut_stem)
            voiture.progression = LIGNE_ARRET
            arret = VueCarrefourBase._position_vehicule(voiture, *geometrie, haut_stem)
            distance_approche = (arret[0] - depart[0]).manhattanLength()
            longueur = arret[2]
            # 6 px libres entre les contours des deux voitures.
            distances[direction] = ceil((longueur + VueCarrefourBase.CONTOUR_VEHICULE + VueCarrefourBase.ECART_FILE) * LIGNE_ARRET / distance_approche)
        return distances

    def _dessiner_feu(self, peintre: QPainter, lettre: str, x_centre: float, y_haut: float, vert: bool) -> None:
        """Dessine un feu : rond rouge en haut, rond vert en bas, un seul allume."""
        r = self.RAYON
        largeur_boitier = 2 * r + 12
        hauteur_boitier = 4 * r + 8 + 12

        # Boitier
        peintre.setPen(Qt.PenStyle.NoPen)
        peintre.setBrush(self.COULEUR_BOITIER)
        peintre.drawRoundedRect(
            QRectF(x_centre - largeur_boitier / 2, y_haut, largeur_boitier, hauteur_boitier), 8, 8
        )

        # Rond rouge (haut) et rond vert (bas)
        centre_rouge = QPointF(x_centre, y_haut + 6 + r)
        centre_vert = QPointF(x_centre, y_haut + 6 + 3 * r + 8)
        peintre.setPen(QPen(self.COULEUR_CONTOUR, 1.5))
        peintre.setBrush(self.ROUGE_ETEINT if vert else self.ROUGE_ALLUME)
        peintre.drawEllipse(centre_rouge, r, r)
        peintre.setBrush(self.VERT_ALLUME if vert else self.VERT_ETEINT)
        peintre.drawEllipse(centre_vert, r, r)

        # Lettre au-dessus du boitier
        peintre.setPen(self.COULEUR_CONTOUR)
        peintre.drawText(
            QRectF(x_centre - 20, y_haut - 22, 40, 20), Qt.AlignmentFlag.AlignCenter, lettre
        )

    _position_vehicule = staticmethod(TrajectoireVehicule._position_vehicule)

    def _dessiner_vehicules(self, peintre, vehicules, gauche, droite, centre_x,
                            centre_y, bas_stem, epaisseur, haut_stem=None):
        """Affiche les positions validees par le serveur, y compris les urgences."""
        for vehicule in vehicules:
            geometrie = self._position_vehicule(
                vehicule, gauche, droite, centre_x, centre_y, bas_stem, epaisseur, haut_stem
            )
            if geometrie is None:
                continue
            position, angle, longueur, largeur = geometrie
            peintre.save()
            peintre.translate(position)
            peintre.rotate(angle)
            peintre.setPen(QPen(self.COULEUR_CONTOUR, self.CONTOUR_VEHICULE))
            peintre.setBrush(QColor("#e9584f" if vehicule.prioritaire else "#3478bd"))
            peintre.drawRoundedRect(QRectF(-longueur / 2, -largeur / 2, longueur, largeur), 3, 3)
            # Pare-brise a l'avant pour rendre le sens de circulation visible.
            peintre.setBrush(QColor("#c6e4f3"))
            peintre.drawRect(QRectF(longueur * 0.15, -largeur * 0.35,
                                   longueur * 0.15, largeur * 0.7))
            peintre.rotate(-angle)
            peintre.setPen(QColor("white"))
            identifiant = "U" if vehicule.prioritaire else vehicule.identifiant_affichage
            peintre.drawText(QRectF(-8, -8, 16, 16), Qt.AlignmentFlag.AlignCenter, identifiant)
            peintre.restore()
