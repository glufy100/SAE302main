"""Serveur TCP et interface graphique du carrefour intelligent."""

import os
from pathlib import Path
import sys

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server.model.EtatCarrefour import EtatCarrefour
from server.model.ServeurCarrefour import ServeurCarrefour
from server.model.FenetreCarrefour import FenetreCarrefour
from server.model.OngletCarrefourT import OngletCarrefourT
from server.model.BaseDonnees import BaseDonnees

import PySide6
from PySide6.QtCore import QLibraryInfo, QTimer
from PySide6.QtWidgets import QApplication, QTabWidget


def configurer_plugins_qt() -> None:
    """Aide PySide6 a trouver les plugins Qt sur macOS."""
    chemins_possibles = []
    chemin_qt = QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)
    if chemin_qt:
        chemins_possibles.append(Path(chemin_qt))
    chemins_possibles.append(Path(PySide6.__file__).resolve().parent / "Qt" / "plugins")

    chemins_valides = [chemin for chemin in chemins_possibles if (chemin / "platforms").exists()]
    if chemins_valides:
        QApplication.setLibraryPaths([str(chemin) for chemin in chemins_valides])
        os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", str(chemins_valides[0] / "platforms"))


def main():
    """Lance le serveur et l'interface graphique."""
    configurer_plugins_qt()
    application = QApplication([])
    base_donnees = BaseDonnees()
    etat = EtatCarrefour(base_donnees)
    etat_t = EtatCarrefour(base_donnees, type_carrefour="T")
    serveur = ServeurCarrefour(etat, etat_t=etat_t)
    serveur.demarrer()

    fenetre = FenetreCarrefour(etat, serveur)

    onglets = QTabWidget()
    onglets.setTabPosition(QTabWidget.TabPosition.North)  # barre d'onglets en haut
    onglets.tabBar().setExpanding(False)                  # onglets alignés à gauche
    onglets.addTab(fenetre, "Carrefour en croix")
    onglets.addTab(OngletCarrefourT(etat_t), "Carrefour en T")
    timer_t = QTimer(onglets)
    timer_t.timeout.connect(etat_t.avancer_cycle)
    timer_t.start(1000)
    application.aboutToQuit.connect(serveur.arreter)
    onglets.setWindowTitle("Carrefour intelligent")
    onglets.resize(1000, 700)
    onglets.show()

    application.exec()


if __name__ == "__main__":
    main()