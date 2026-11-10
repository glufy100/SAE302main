"""Dessin partage par les carrefours en T et en croix."""

from dataclasses import replace

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from server.config import GEOMETRIE_SCENE
from server.model.EtatCarrefour import EtatCarrefour


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
    CONTOUR_VEHICULE = 1

    def __init__(self, etat: EtatCarrefour):
        if not isinstance(etat, EtatCarrefour):
            raise TypeError("etat doit etre une instance de EtatCarrefour")
        super().__init__()
        self.etat = etat
        self.setMinimumSize(700, 500)

    def _geometrie(self):
        """Repere commun aux routes et aux positions graphiques recues des clients."""
        return GEOMETRIE_SCENE

    def _etat_affichage(self, geometrie, haut_stem=None):
        with self.etat.verrou:
            return dict(self.etat.feux), [replace(v) for v in self.etat.vehicules.values()]

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

    def _dessiner_refuges_urgence(self, peintre, geometrie, haut_stem=None):
        """Bandes laterales ou se rangent les voitures devant une ambulance."""
        gauche, droite, cx, cy, bas, epaisseur = geometrie
        demi = epaisseur / 2
        bord = epaisseur * 0.85
        arret = demi + max(4.0, epaisseur * 0.05)
        refuges = {
            "S": QRectF(cx + demi, cy + arret, bord - demi, bas - cy - arret),
            "E": QRectF(cx + arret, cy - bord, droite - cx - arret, bord - demi),
            "O": QRectF(gauche, cy + demi, cx - arret - gauche, bord - demi),
        }
        if haut_stem is not None:
            refuges["N"] = QRectF(cx - bord, haut_stem, bord - demi, cy - arret - haut_stem)
        peintre.save()
        peintre.setPen(Qt.PenStyle.NoPen)
        peintre.setBrush(self.COULEUR_ROUTE.lighter(115))
        for direction in self.etat.trajets:
            peintre.drawRect(refuges[direction])
        peintre.restore()

    def _dessiner_vehicules(self, peintre, vehicules, gauche, droite, centre_x,
                            centre_y, bas_stem, epaisseur, haut_stem=None):
        """Dessine telles quelles les positions et orientations calculees par les clients."""
        for vehicule in vehicules:
            if vehicule.position_affichage is None:
                continue
            x, y, angle, longueur, largeur = vehicule.position_affichage
            peintre.save()
            peintre.translate(x, y)
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
