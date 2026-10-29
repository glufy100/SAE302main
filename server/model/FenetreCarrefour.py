from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMainWindow
from server.model.EtatCarrefour import EtatCarrefour
from server.model.ServeurCarrefour import ServeurCarrefour
from server.model.VueCarrefour import VueCarrefour
from server.model.PanneauCarrefour import PanneauCarrefour


class FenetreCarrefour(QMainWindow):
    """Fenetre principale de la simulation."""

    def __init__(self, etat: EtatCarrefour, serveur: ServeurCarrefour):
        if not isinstance(etat, EtatCarrefour):
            raise TypeError("etat doit etre une instance de EtatCarrefour")
        if not isinstance(serveur, ServeurCarrefour):
            raise TypeError("serveur doit etre une instance de ServeurCarrefour")
        super().__init__()
        self.serveur = serveur
        self.setWindowTitle("Carrefour intelligent")
        self.vue = VueCarrefour(etat)
        self.panneau = PanneauCarrefour(etat, self.vue)
        self.setCentralWidget(self.panneau)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.changer_cycle_normal)
        self.timer.start(1000)

    def changer_cycle_normal(self):
        """Declenche une seconde du cycle des feux."""
        self.vue.etat.avancer_cycle()

    def closeEvent(self, event):
        """Ferme aussi le serveur quand la fenetre se ferme."""
        self.serveur.arreter()
        event.accept()
