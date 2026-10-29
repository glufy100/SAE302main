from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QFont, QPainter, QPen

from server.model.Decor import dessiner_arbre, dessiner_bloc
from server.model.VueCarrefourBase import VueCarrefourBase


class VueCarrefourT(VueCarrefourBase):
    """Dessine le carrefour en T (branches Ouest, Est et Sud) et ses feux."""

    def paintEvent(self, event):
        """Dessine la scene a chaque rafraichissement."""
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        largeur = self.width()

        peintre.fillRect(self.rect(), self.COULEUR_FOND)

        gauche, droite, centre_x, centre_y, bas_stem, epaisseur = geometrie = self._geometrie()
        haut_route = centre_y - epaisseur / 2
        bas_route = centre_y + epaisseur / 2
        feux, vehicules = self._etat_affichage(geometrie)

        self._dessiner_decor(peintre, largeur, gauche, droite, centre_x,
                             haut_route, bas_route, bas_stem, epaisseur)
        self._dessiner_routes(peintre, gauche, droite, centre_x, haut_route, bas_route, bas_stem, epaisseur)
        self._dessiner_refuges_urgence(peintre, geometrie)
        self._dessiner_marquages(
            peintre, gauche, droite, centre_x, centre_y, haut_route, bas_route, bas_stem, epaisseur
        )
        self._dessiner_feux(peintre, feux, gauche, droite, centre_x, haut_route, bas_route, epaisseur)

        self._dessiner_vehicules(
            peintre, vehicules, gauche, droite, centre_x, centre_y, bas_stem, epaisseur
        )

        peintre.end()

    def _dessiner_decor(
        self,
        peintre: QPainter,
        largeur: float,
        gauche: float,
        droite: float,
        centre_x: float,
        haut_route: float,
        bas_route: float,
        bas_stem: float,
        epaisseur: float,
    ) -> None:
        """Dessine le decor d'un quartier residentiel : trottoirs, maisons et arbres."""
        demi = epaisseur / 2

        # Trottoirs autour des routes.
        peintre.setPen(Qt.PenStyle.NoPen)
        peintre.setBrush(self.COULEUR_TROTTOIR)
        peintre.drawRect(QRectF(gauche - 8, haut_route - 8, droite - gauche + 16, epaisseur + 16))
        peintre.drawRect(QRectF(centre_x - demi - 8, bas_route, epaisseur + 16, bas_stem - bas_route + 8))

        # Garder les batiments hors des refuges sans decaler les trottoirs.
        haut_route -= epaisseur * 0.35
        bas_route += epaisseur * 0.35

        x_e = droite - epaisseur * 0.9   # position du feu E
        x_o = gauche + epaisseur * 0.7   # position du feu O

        # Maisons au-dessus de la route principale (a gauche du feu E) et un arbre au-dessus du feu E.
        dessiner_bloc(peintre, 20, 20, x_e - 45, haut_route - 30, True, self.COULEURS_TOITS, maisons=True)
        if haut_route - 110 > 50:
            dessiner_arbre(peintre, x_e, (20 + haut_route - 110) / 2, 11)

        # Maisons sous la route principale, de chaque cote de la branche sud.
        dessiner_bloc(
            peintre, x_o + 45, bas_route + 25, centre_x - demi - 30, bas_stem - 10,
            False, self.COULEURS_TOITS[1:] + self.COULEURS_TOITS[:1], maisons=True,
        )
        dessiner_bloc(
            peintre, centre_x + demi + 80, bas_route + 25, largeur - 20, bas_stem - 10,
            False, self.COULEURS_TOITS[2:] + self.COULEURS_TOITS[:2], maisons=True,
        )

        # Un arbre sous le feu O.
        if bas_stem - (bas_route + 121) > 20:
            dessiner_arbre(peintre, x_o, bas_route + 121, 11)

    def _dessiner_routes(
        self,
        peintre: QPainter,
        gauche: float,
        droite: float,
        centre_x: float,
        haut_route: float,
        bas_route: float,
        bas_stem: float,
        epaisseur: float,
    ) -> None:
        """Dessine la route principale et la branche sud."""
        peintre.setPen(Qt.PenStyle.NoPen)
        peintre.setBrush(self.COULEUR_ROUTE)
        peintre.drawRect(QRectF(gauche, haut_route, droite - gauche, epaisseur))
        peintre.drawRect(QRectF(centre_x - epaisseur / 2, bas_route, epaisseur, bas_stem - bas_route))

    def _dessiner_marquages(
        self,
        peintre: QPainter,
        gauche: float,
        droite: float,
        centre_x: float,
        centre_y: float,
        haut_route: float,
        bas_route: float,
        bas_stem: float,
        epaisseur: float,
    ) -> None:
        """Dessine les lignes blanches : tirets centraux et lignes d'arret."""
        demi = epaisseur / 2
        e_tiret = max(3.0, epaisseur * 0.035)
        e_arret = max(4.0, epaisseur * 0.05)
        ecart = epaisseur * 0.08

        # Tirets centraux : la route principale continue a travers le T,
        # la branche sud s'arrete avant la route principale.
        tirets = QPen(self.COULEUR_LIGNE, e_tiret)
        tirets.setDashPattern([3, 3])
        tirets.setCapStyle(Qt.PenCapStyle.FlatCap)
        peintre.setPen(tirets)
        peintre.drawLine(QPointF(gauche + ecart, centre_y), QPointF(droite - ecart, centre_y))
        peintre.drawLine(
            QPointF(centre_x, bas_route + e_arret + ecart), QPointF(centre_x, bas_stem - ecart)
        )

        # Lignes d'arret continues, du cote de circulation de chaque branche.
        arret = QPen(self.COULEUR_LIGNE, e_arret)
        arret.setCapStyle(Qt.PenCapStyle.FlatCap)
        peintre.setPen(arret)
        y_s = bas_route + e_arret / 2
        x_e = centre_x + demi + e_arret / 2
        x_o = centre_x - demi - e_arret / 2
        peintre.drawLine(QPointF(centre_x, y_s), QPointF(centre_x + demi, y_s))   # S
        peintre.drawLine(QPointF(x_e, haut_route), QPointF(x_e, centre_y))        # E
        peintre.drawLine(QPointF(x_o, centre_y), QPointF(x_o, bas_route))         # O

    def _dessiner_feux(
        self,
        peintre: QPainter,
        feux: dict,
        gauche: float,
        droite: float,
        centre_x: float,
        haut_route: float,
        bas_route: float,
        epaisseur: float,
    ) -> None:
        """Dessine les trois feux du T."""
        police = QFont()
        police.setPointSize(9)
        peintre.setFont(police)
        hauteur_boitier = 4 * self.RAYON + 8 + 12

        # S : a droite de la branche sud
        self._dessiner_feu(
            peintre, "S",
            centre_x + epaisseur * 0.85 + 30,
            bas_route + epaisseur * 0.6,
            feux.get("S") == "VERT",
        )
        # E : au-dessus de la branche est
        self._dessiner_feu(
            peintre, "E",
            droite - epaisseur * 0.9,
            haut_route - epaisseur * 0.35 - hauteur_boitier - 8,
            feux.get("E") == "VERT",
        )
        # O : en dessous de la branche ouest
        self._dessiner_feu(
            peintre, "O",
            gauche + epaisseur * 0.7,
            bas_route + epaisseur * 0.35 + 28,
            feux.get("O") == "VERT",
        )

