from server.model.PanneauCarrefour import PanneauCarrefour
from server.model.VueCarrefourT import VueCarrefourT


class OngletCarrefourT(PanneauCarrefour):
    """Presente le carrefour en T et les compteurs de sa simulation."""

    def __init__(self, etat):
        super().__init__(etat, VueCarrefourT(etat))
        self.setStyleSheet("background-color: #2b2b2b; color: white;")
