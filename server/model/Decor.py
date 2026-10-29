"""Petits dessins de decor (arbres, immeubles, maisons) pour les vues du carrefour."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen


def dessiner_arbre(peintre: QPainter, x: float, y: float, rayon: float = 11) -> None:
    """Dessine un arbre vu du dessus : un rond vert avec un reflet."""
    peintre.setPen(QPen(QColor("#3f7a3b"), 1.5))
    peintre.setBrush(QColor("#5f9e5a"))
    peintre.drawEllipse(QPointF(x, y), rayon, rayon)
    peintre.setPen(Qt.PenStyle.NoPen)
    peintre.setBrush(QColor("#7bbd75"))
    peintre.drawEllipse(QPointF(x - rayon * 0.3, y - rayon * 0.3), rayon * 0.45, rayon * 0.45)


def dessiner_rangee_arbres(peintre: QPainter, x0: float, x1: float, y: float, rayon: float = 11) -> None:
    """Dessine une rangee d'arbres regulierement espaces entre x0 et x1."""
    nombre = max(1, int((x1 - x0) // 46))
    pas = (x1 - x0) / nombre
    for i in range(nombre):
        dessiner_arbre(peintre, x0 + (i + 0.5) * pas, y, rayon)


def dessiner_immeuble(peintre: QPainter, x: float, y: float, largeur: float, hauteur: float, couleur: str) -> None:
    """Dessine le toit d'un immeuble vu du dessus."""
    toit = QColor(couleur)
    peintre.setPen(QPen(toit.darker(140), 2))
    peintre.setBrush(toit)
    peintre.drawRect(QRectF(x, y, largeur, hauteur))

    # Rebord du toit.
    peintre.setPen(QPen(toit.lighter(115), 1.5))
    peintre.setBrush(Qt.BrushStyle.NoBrush)
    peintre.drawRect(QRectF(x + 5, y + 5, largeur - 10, hauteur - 10))

    # Petits blocs techniques (climatisation, cheminees).
    if largeur >= 50 and hauteur >= 50:
        peintre.setPen(Qt.PenStyle.NoPen)
        peintre.setBrush(toit.darker(120))
        peintre.drawRect(QRectF(x + largeur * 0.15, y + hauteur * 0.2, 14, 14))
        peintre.drawRect(QRectF(x + largeur * 0.6, y + hauteur * 0.55, 18, 12))


def dessiner_maison(peintre: QPainter, x: float, y: float, largeur: float, hauteur: float, couleur: str) -> None:
    """Dessine le toit d'une maison a deux pans vu du dessus."""
    toit = QColor(couleur)
    moitie = largeur / 2
    peintre.setPen(QPen(toit.darker(140), 1.5))
    peintre.setBrush(toit)
    peintre.drawRect(QRectF(x, y, moitie, hauteur))
    peintre.setBrush(toit.darker(115))
    peintre.drawRect(QRectF(x + moitie, y, moitie, hauteur))

    # Faitage (ligne du haut du toit) et cheminee.
    peintre.setPen(QPen(toit.darker(160), 2))
    peintre.drawLine(QPointF(x + moitie, y), QPointF(x + moitie, y + hauteur))
    peintre.setPen(Qt.PenStyle.NoPen)
    peintre.setBrush(QColor("#6b4a3e"))
    peintre.drawRect(QRectF(x + largeur * 0.2, y + hauteur * 0.2, 8, 8))


def dessiner_bloc(
    peintre: QPainter,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    route_en_bas: bool,
    couleurs: list,
    maisons: bool = False,
) -> None:
    """Remplit un rectangle de batiments, avec une rangee d'arbres cote route.

    route_en_bas : True si la route est sous le rectangle, False si elle est au-dessus.
    """
    largeur, hauteur = x1 - x0, y1 - y0
    if largeur < 60 or hauteur < 70:
        return

    cible = 90 if maisons else 130
    nombre = max(1, round(largeur / cible))
    ecart = 14
    largeur_bat = (largeur - ecart * (nombre - 1)) / nombre
    hauteur_bat = min(hauteur * 0.68, 140)

    for i in range(nombre):
        hauteur_i = hauteur_bat * (0.85 if i % 2 else 1.0)
        x = x0 + i * (largeur_bat + ecart)
        y = y0 if route_en_bas else y1 - hauteur_i
        couleur = couleurs[i % len(couleurs)]
        if maisons:
            dessiner_maison(peintre, x, y, largeur_bat, hauteur_i, couleur)
        else:
            dessiner_immeuble(peintre, x, y, largeur_bat, hauteur_i, couleur)

    # Rangee d'arbres entre les batiments et la route.
    bande = hauteur - hauteur_bat
    y_arbres = y0 + hauteur_bat + bande / 2 if route_en_bas else y0 + bande / 2
    rayon = min(11, max(6, bande / 2 - 3))
    dessiner_rangee_arbres(peintre, x0, x1, y_arbres, rayon)