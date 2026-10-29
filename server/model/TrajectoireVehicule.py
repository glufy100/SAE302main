"""Geometrie des voitures partagee par le dessin et la validation des mouvements."""

from dataclasses import replace
from functools import lru_cache
from math import atan2, degrees

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainterPath, QTransform

from server.config import FIN_CENTRE, LIGNE_ARRET
from server.model.Vehicule import Vehicule


class TrajectoireVehicule:
    ECART_FILE = 6
    ECART_LIGNE = 3
    CONTOUR_VEHICULE = 1

    @staticmethod
    def _position_vehicule(vehicule, gauche, droite, centre_x, centre_y, bas_stem, epaisseur, haut_stem=None):
        """Suit la voie d'entree, le virage puis la voie de sortie.

        La progression de la ligne d'arret est independante de la taille
        de la fenetre. La branche nord est facultative pour la vue en T.
        """
        direction_sortie = vehicule.direction_sortie()
        if haut_stem is None and (vehicule.direction == "N" or direction_sortie == "N"):
            return None

        voie = epaisseur / 4
        demi = epaisseur / 2
        longueur = min(32.0, epaisseur * 0.32)
        largeur = longueur * 0.65
        # La ligne est centree une demi-epaisseur au-dela du bord de
        # la route : son bord exterieur est donc a une epaisseur complete.
        # On place l'avant du vehicule (et son contour de 1 px) a 3 px
        # de ce bord sur chaque branche.
        e_arret = max(4.0, epaisseur * 0.05)
        marge = (longueur / 2 + e_arret + TrajectoireVehicule.ECART_LIGNE
                 + TrajectoireVehicule.CONTOUR_VEHICULE / 2)
        entrees = {
            "E": (QPointF(droite, centre_y - voie),
                  QPointF(centre_x + demi + marge, centre_y - voie), QPointF(-1, 0)),
            "O": (QPointF(gauche, centre_y + voie),
                  QPointF(centre_x - demi - marge, centre_y + voie), QPointF(1, 0)),
            "S": (QPointF(centre_x + voie, bas_stem),
                  QPointF(centre_x + voie, centre_y + demi + marge), QPointF(0, -1)),
        }
        sorties = {
            "E": (QPointF(centre_x + demi + marge, centre_y + voie),
                  QPointF(droite, centre_y + voie), QPointF(1, 0)),
            "O": (QPointF(centre_x - demi - marge, centre_y - voie),
                  QPointF(gauche, centre_y - voie), QPointF(-1, 0)),
            "S": (QPointF(centre_x - voie, centre_y + demi + marge),
                  QPointF(centre_x - voie, bas_stem), QPointF(0, 1)),
        }
        entrees["N"] = (QPointF(centre_x - voie, haut_stem or 0),
                        QPointF(centre_x - voie, centre_y - demi - marge), QPointF(0, 1))
        sorties["N"] = (QPointF(centre_x + voie, centre_y - demi - marge),
                        QPointF(centre_x + voie, haut_stem or 0), QPointF(0, -1))
        debut, arret, sens_entree = entrees[vehicule.direction]
        fin_virage, fin, sens_sortie = sorties[direction_sortie]
        progression = vehicule.progression
        if progression <= LIGNE_ARRET:
            fraction = progression / LIGNE_ARRET
            position = debut + (arret - debut) * fraction
            sens = sens_entree
        elif progression < FIN_CENTRE:
            trajet = QPainterPath(arret)
            trajet.cubicTo(arret + sens_entree * demi,
                           fin_virage - sens_sortie * demi, fin_virage)
            fraction = (progression - LIGNE_ARRET) / (FIN_CENTRE - LIGNE_ARRET)
            position = trajet.pointAtPercent(fraction)
            sens = (trajet.pointAtPercent(min(1.0, fraction + 0.001))
                    - trajet.pointAtPercent(max(0.0, fraction - 0.001)))
        else:
            fraction = min(1.0, (progression - FIN_CENTRE) / (100 - FIN_CENTRE))
            position = fin_virage + (fin - fin_virage) * fraction
            sens = sens_sortie
        angle = degrees(atan2(sens.y(), sens.x()))
        return position, angle, longueur, largeur

    @staticmethod
    def contour(vehicule, geometrie, haut_stem):
        """Rectangle oriente, elargi d'une demi-distance de securite."""
        position = TrajectoireVehicule._position_vehicule(vehicule, *geometrie, haut_stem)
        if position is None:
            return QPainterPath()
        centre, angle, longueur, largeur = position
        marge = (TrajectoireVehicule.ECART_FILE + TrajectoireVehicule.CONTOUR_VEHICULE) / 2
        rectangle = QPainterPath()
        rectangle.addRect(QRectF(-longueur / 2 - marge, -largeur / 2 - marge,
                                longueur + 2 * marge, largeur + 2 * marge))
        transformation = QTransform()
        transformation.translate(centre.x(), centre.y())
        transformation.rotate(angle)
        return transformation.map(rectangle)

    @staticmethod
    def mouvement_occupe(vehicule, prochaine_position, autres, geometries):
        """Verifie chaque pas, y compris quand la voiture est deja engagee."""
        proposition = replace(vehicule, progression=prochaine_position)
        for geometrie, haut_stem in geometries:
            futur = TrajectoireVehicule.contour(proposition, geometrie, haut_stem)
            for autre in autres:
                if autre.nom == vehicule.nom or autre.progression >= 100:
                    continue
                if futur.intersects(TrajectoireVehicule.contour(autre, geometrie, haut_stem)):
                    return True
        return False

    @staticmethod
    @lru_cache(maxsize=256)
    def _zone_trajet(direction, manoeuvre, geometrie, haut_stem):
        """Enveloppe du trajet dans le croisement, partagee par les reservations."""
        zone = QPainterPath()
        voiture = Vehicule("trajet", "voiture", direction, "", manoeuvre=manoeuvre)
        for progression in range(LIGNE_ARRET, FIN_CENTRE + 1):
            voiture.progression = progression
            zone = zone.united(TrajectoireVehicule.contour(voiture, geometrie, haut_stem))
        return zone

    @staticmethod
    def trajets_en_conflit(vehicule, autre, geometries):
        """Reserve les trajets qui se croisent avant de quitter la ligne d'arret."""
        geometries = tuple(geometries)
        if not geometries:
            return True
        for geometrie, haut_stem in geometries:
            zone = TrajectoireVehicule._zone_trajet(
                vehicule.direction, vehicule.manoeuvre, geometrie, haut_stem)
            autre_zone = TrajectoireVehicule._zone_trajet(
                autre.direction, autre.manoeuvre, geometrie, haut_stem)
            if zone.intersects(autre_zone):
                return True
        return False
