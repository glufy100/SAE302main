"""Geometrie 2D en Python standard : aucune dependance graphique sur les clients."""

from dataclasses import dataclass
from math import cos, sin, radians


@dataclass(frozen=True)
class Point:
    _x: float
    _y: float

    def x(self):
        return self._x

    def y(self):
        return self._y

    def __add__(self, autre):
        return Point(self._x + autre._x, self._y + autre._y)

    def __sub__(self, autre):
        return Point(self._x - autre._x, self._y - autre._y)

    def __mul__(self, nombre):
        return Point(self._x * nombre, self._y * nombre)

    def manhattanLength(self):
        return abs(self._x) + abs(self._y)


class Courbe:
    """Courbe de Bezier cubique utilisee pour les virages d'origine."""

    def __init__(self, debut):
        self.debut = debut

    def cubicTo(self, premier, second, fin):
        self.premier, self.second, self.fin = premier, second, fin

    def pointAtPercent(self, t):
        return (self.debut * ((1-t)**3) + self.premier * (3*(1-t)**2*t)
                + self.second * (3*(1-t)*t*t) + self.fin * (t**3))


class Rectangle:
    """Rectangle oriente et axes servant au test de separation des contours."""

    def __init__(self, centre, angle, longueur, largeur):
        self.cx, self.cy = centre.x(), centre.y()
        self.hx, self.hy = longueur / 2, largeur / 2
        c, s = cos(radians(angle)), sin(radians(angle))
        self.axes = ((c, s), (-s, c))
        ex, ey = self.hx * abs(c) + self.hy * abs(s), self.hx * abs(s) + self.hy * abs(c)
        self.bornes = (self.cx-ex, self.cy-ey, self.cx+ex, self.cy+ey)

    def intersects(self, autre):
        if not bornes_communes(self.bornes, autre.bornes):
            return False
        dx, dy = autre.cx-self.cx, autre.cy-self.cy
        for ax, ay in self.axes + autre.axes:
            rayon = sum(h * abs(x*ax+y*ay) for h, (x, y) in zip((self.hx, self.hy), self.axes))
            rayon += sum(h * abs(x*ax+y*ay) for h, (x, y) in zip((autre.hx, autre.hy), autre.axes))
            if abs(dx*ax+dy*ay) >= rayon - 1e-8:
                return False
        return True


def bornes_communes(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


class Contour:
    """Ensemble de rectangles, pour une voiture ou l'enveloppe de son trajet."""

    def __init__(self, rectangles=()):
        self.rectangles = tuple(rectangles)
        self.bornes = (min(r.bornes[0] for r in self.rectangles),
                       min(r.bornes[1] for r in self.rectangles),
                       max(r.bornes[2] for r in self.rectangles),
                       max(r.bornes[3] for r in self.rectangles)) if self.rectangles else None

    def united(self, autre):
        return Contour(self.rectangles + autre.rectangles)

    def intersects(self, autre):
        if self.bornes is None or autre.bornes is None or not bornes_communes(self.bornes, autre.bornes):
            return False
        return any(a.intersects(b) for a in self.rectangles for b in autre.rectangles)
