from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QPen

from server.model.Decor import dessiner_bloc
from server.model.VueCarrefourBase import VueCarrefourBase


class VueCarrefour(VueCarrefourBase):
    """Dessine les quatre branches avec les memes conventions que le T."""

    def paintEvent(self, event):
        """Dessine les routes, les feux et les voitures de l'etat partage."""
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        peintre.fillRect(self.rect(), self.COULEUR_FOND)
        gauche, droite, centre_x, centre_y, bas, epaisseur = geometrie = self._geometrie()
        haut = self.height() * 0.06
        demi = epaisseur / 2
        feux, vehicules = self._etat_affichage(geometrie, haut)

        self._dessiner_decor(peintre, gauche, droite, haut, bas, centre_x, centre_y, demi)
        self._dessiner_routes(peintre, gauche, droite, haut, bas, centre_x, centre_y, epaisseur)
        self._dessiner_marquages(peintre, gauche, droite, haut, bas, centre_x, centre_y, epaisseur)
        self._dessiner_feux(peintre, gauche, droite, haut, bas, centre_x, centre_y, demi, feux)
        self._dessiner_vehicules(peintre, vehicules, *geometrie, haut)
        peintre.end()

    def _dessiner_decor(self, peintre, gauche, droite, haut, bas, centre_x, centre_y, demi):
        """Dessine un quartier de chaque cote des deux routes."""
        for index, (x1, y1, x2, y2) in enumerate((
            (gauche, haut, centre_x - demi - 35, centre_y - demi - 35),
            (centre_x + demi + 35, haut, droite, centre_y - demi - 35),
            (gauche, centre_y + demi + 35, centre_x - demi - 35, bas),
            (centre_x + demi + 35, centre_y + demi + 35, droite, bas),
        )):
            couleurs = self.COULEURS_TOITS[index:] + self.COULEURS_TOITS[:index]
            dessiner_bloc(peintre, x1, y1, x2, y2, index < 2, couleurs)

    def _dessiner_routes(self, peintre, gauche, droite, haut, bas, centre_x, centre_y, epaisseur):
        """Dessine les trottoirs puis les routes en croix."""
        peintre.setPen(Qt.PenStyle.NoPen)
        for couleur, marge in ((self.COULEUR_TROTTOIR, 8), (self.COULEUR_ROUTE, 0)):
            peintre.setBrush(couleur)
            peintre.drawRect(QRectF(gauche - marge, centre_y - epaisseur / 2 - marge,
                                   droite - gauche + 2 * marge, epaisseur + 2 * marge))
            peintre.drawRect(QRectF(centre_x - epaisseur / 2 - marge, haut - marge,
                                   epaisseur + 2 * marge, bas - haut + 2 * marge))

    def _dessiner_marquages(self, peintre, gauche, droite, haut, bas, centre_x, centre_y, epaisseur):
        """Interrompt les tirets au croisement et place les quatre lignes d'arret."""
        demi = epaisseur / 2
        e_arret = max(4.0, epaisseur * 0.05)
        ecart = epaisseur * 0.08
        tirets = QPen(self.COULEUR_LIGNE, max(3.0, epaisseur * 0.035))
        tirets.setDashPattern([3, 3])
        tirets.setCapStyle(Qt.PenCapStyle.FlatCap)
        peintre.setPen(tirets)
        for debut, fin in (
            (QPointF(gauche, centre_y), QPointF(centre_x - demi - ecart, centre_y)),
            (QPointF(centre_x + demi + ecart, centre_y), QPointF(droite, centre_y)),
            (QPointF(centre_x, haut), QPointF(centre_x, centre_y - demi - ecart)),
            (QPointF(centre_x, centre_y + demi + ecart), QPointF(centre_x, bas)),
        ):
            peintre.drawLine(debut, fin)
        arret = QPen(self.COULEUR_LIGNE, e_arret)
        arret.setCapStyle(Qt.PenCapStyle.FlatCap)
        peintre.setPen(arret)
        distance = demi + e_arret / 2
        for debut, fin in (
            (QPointF(centre_x - demi, centre_y - distance), QPointF(centre_x, centre_y - distance)),
            (QPointF(centre_x, centre_y + distance), QPointF(centre_x + demi, centre_y + distance)),
            (QPointF(centre_x + distance, centre_y - demi), QPointF(centre_x + distance, centre_y)),
            (QPointF(centre_x - distance, centre_y), QPointF(centre_x - distance, centre_y + demi)),
        ):
            peintre.drawLine(debut, fin)

    def _dessiner_feux(self, peintre, gauche, droite, haut, bas, centre_x, centre_y, demi, feux):
        """Utilise le meme dessin de feu que le carrefour en T."""
        for direction, x, y in (
            ("N", centre_x - demi - 30, haut),
            ("S", centre_x + demi + 30, bas - 70),
            ("E", droite - 35, centre_y - demi - 85),
            ("O", gauche + 35, centre_y + demi + 20),
        ):
            self._dessiner_feu(peintre, direction, x, y, feux[direction] == "VERT")
